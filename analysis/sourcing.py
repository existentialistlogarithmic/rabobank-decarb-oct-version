"""The hydrogen sourcing frontier: what happens when p_H2 and eps_cln are tied.

The model treats the hydrogen price and the clean route's emission intensity as
two independent inputs. Physically they are one. Hydrogen is bought somewhere on
a line between two observable endpoints:

* **grey** - reformed from natural gas at the Eurostat industrial gas price,
  emitting 9 kgCO2 per kg of hydrogen;
* **green** - electrolysed at the Eurostat industrial electricity price,
  emitting nothing at the plant.

One parameter - the green share ``theta`` - fixes both the price and the
intensity:

``p_H2(theta) = theta * green + (1 - theta) * grey_gas``
``eps_cln(theta) = eps_cln_base + (1 - theta) * m_H2 * 9 / 1000``

Everything in this module is that substitution and its consequences.

The accounting boundary, and why gas is priced without its ETS cost
-------------------------------------------------------------------
Reforming emits CO2 once. It can be charged in one of two places and must not
be charged in both:

* through ``eps_cln``, as the steelmaker's own emission, priced by the model's
  carbon path with free allocation applied - **the framing used here**;
* inside the hydrogen price, as a merchant supplier's ETS cost passed through -
  the framing the base case implicitly uses, since EUR 2.60/kg is roughly the
  gas cost plus the 2026 carbon price.

So ``grey_gas`` here is the gas cost alone. Charging the ETS cost in the price
*and* keeping ``eps_cln = 0.1`` is not a third framing; it is the double-count
the base case makes in reverse - paying for the carbon once while booking the
abatement as if it never happened.

The two framings are not equivalent, and the difference is structural rather
than presentational: a carbon cost embedded in ``p_H2`` is **frozen**, because
``p_H2`` is a scalar held constant to 2050, while the same cost charged through
``eps_cln`` **escalates** with the carbon price path like everything else in the
model. See :func:`framing_gap`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Final

from data import eurostat
from timing_model.params import Params, ScenarioParams
from timing_model.results import outputs

#: Green share values the frontier is evaluated on. Eleven is enough to see the
#: shape and cheap enough to rebuild the page on every run.
THETA_STEPS: Final[int] = 11

#: Carbon-path multiples the explorer offers. 1.0 is the model's central path.
CARBON_MULTIPLES: Final[tuple[float, ...]] = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0)


@dataclass(frozen=True)
class SourcingPoint:
    """One point on the frontier: a consistent (price, intensity) pair and its result."""

    geo: str
    theta: float
    p_h2: float
    eps_cln: float
    t_star: int | None
    npv0: float
    trigger: float
    npv_by_year: tuple[tuple[int, float], ...] = ()


def grey_tonnes_per_tonne(p: Params | None = None) -> float:
    """tCO2 per tonne of steel if every kilogram of hydrogen is reformed.

    ``m_H2`` kg of hydrogen per tonne of steel at 9 kgCO2 each. With the model's
    defaults this is 0.495 tCO2/t - five times ``eps_cln``.
    """
    p = p or Params()
    return p.sector.m_H2 * eurostat.KG_CO2_PER_KG_H2_SMR / 1000.0


def endpoints(geo: str, series: Mapping[str, object] | None = None) -> tuple[float, float]:
    """``(green, grey_gas)`` hydrogen cost in EUR/kg for one member state.

    Both are floors from observed energy prices: no electrolyser or reformer
    capital cost, no compression, storage or transport. ``grey_gas`` excludes
    the ETS cost of the reforming emissions, which this module charges through
    ``eps_cln`` instead - see the module docstring.
    """
    s = series if series is not None else eurostat.refresh(offline=True)
    green = s[f"power_{geo}"].value * eurostat.KWH_PER_KG_H2  # type: ignore[union-attr]
    grey = s[f"gas_{geo}"].value * eurostat.KWH_GAS_PER_KG_H2  # type: ignore[union-attr]
    return green, grey


def point(geo: str, theta: float, series: Mapping[str, object] | None = None,
          scale: float = 1.0, with_curve: bool = False) -> SourcingPoint:
    """Run the model at the consistent (price, intensity) pair for ``theta``."""
    green, grey = endpoints(geo, series)
    price = theta * green + (1.0 - theta) * grey
    eps = Params().common.eps_cln + (1.0 - theta) * grey_tonnes_per_tonne()
    p = Params().with_common(eps_cln=eps)
    sc = replace(ScenarioParams(), p_H2=price, price_scale=scale)
    o = outputs(p, sc)
    curve: tuple[tuple[int, float], ...] = ()
    if with_curve:
        from timing_model.objective import npv_curve

        curve = tuple(sorted(npv_curve(p, sc).items()))
    return SourcingPoint(geo, theta, price, eps, o.t_star, o.npv0, o.trigger, curve)


def frontier(geo: str, steps: int | None = None, scale: float = 1.0,
             series: Mapping[str, object] | None = None,
             with_curves: bool = False) -> list[SourcingPoint]:
    """The whole frontier for one member state, all-grey to all-green.

    ``steps`` defaults to :data:`THETA_STEPS` read at call time, so a test that
    shrinks the grid gets a smaller frontier rather than the value that happened
    to be bound when this module was imported.
    """
    n = THETA_STEPS if steps is None else steps
    s = series if series is not None else eurostat.refresh(offline=True)
    return [point(geo, i / (n - 1), s, scale, with_curves) for i in range(n)]


def theta_at_price(geo: str, price: float,
                   series: Mapping[str, object] | None = None) -> float | None:
    """Green share implied by a hydrogen price, or ``None`` if unreachable.

    ``None`` means the price sits outside the observed endpoints entirely: below
    the gas cost of reforming, or above the electricity cost of electrolysis.
    """
    green, grey = endpoints(geo, series)
    if not grey <= price <= green:
        return None
    return (price - grey) / (green - grey)


def feasibility_gap(geo: str, series: Mapping[str, object] | None = None
                    ) -> tuple[float, float, float | None]:
    """``(model NPV, frontier NPV at the same price, theta)``.

    The model's own hydrogen price, held fixed, with the emission intensity made
    consistent with it. The difference is what the independent-inputs assumption
    is worth - the part of the published NPV that no sourcing decision can buy.
    """
    s = series if series is not None else eurostat.refresh(offline=True)
    sc = ScenarioParams()
    model = outputs(Params(), sc).npv0
    theta = theta_at_price(geo, sc.p_H2, s)
    if theta is None:
        return model, float("nan"), None
    return model, point(geo, theta, s).npv0, theta


def crossover_multiple(geo: str, series: Mapping[str, object] | None = None,
                       hi: float = 200.0, iterations: int = 24) -> float | None:
    """Carbon-path multiple at which all-green first beats all-grey on NPV.

    Returns ``None`` if green never overtakes within ``hi`` times the central
    path - which would mean the abatement is worth less than the energy premium
    at any carbon price a reader would take seriously.
    """
    s = series if series is not None else eurostat.refresh(offline=True)

    def green_wins(scale: float) -> bool:
        return point(geo, 1.0, s, scale).npv0 > point(geo, 0.0, s, scale).npv0

    if not green_wins(hi):
        return None
    lo = 1.0
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        if green_wins(mid):
            hi = mid
        else:
            lo = mid
    return hi


def framing_gap(geo: str, series: Mapping[str, object] | None = None
                ) -> tuple[float, float]:
    """``(merchant NPV, onsite NPV)`` for the same grey hydrogen.

    Identical molecules, identical emissions, identical plant. The only
    difference is where the carbon is charged - and therefore whether it
    escalates with the carbon price or stays frozen at its 2026 level inside a
    constant ``p_H2``.
    """
    s = series if series is not None else eurostat.refresh(offline=True)
    green, grey = endpoints(geo, s)
    p, sc = Params(), ScenarioParams()
    from timing_model.benefit import carbon_price_path

    eua = carbon_price_path(p, sc)[p.common.t0]
    merchant_price = grey + eua * eurostat.KG_CO2_PER_KG_H2_SMR / 1000.0
    merchant = outputs(p, replace(sc, p_H2=merchant_price)).npv0
    onsite = point(geo, 0.0, s).npv0
    return merchant, onsite


def _fmt_year(year: int | None) -> str:
    return str(year) if year is not None else "beyond"


def main() -> int:
    """Print the frontier, the crossover and the two gaps."""
    series = eurostat.refresh(offline=True)
    geos: Sequence[str] = eurostat.STEEL_GEOS
    grey_t = grey_tonnes_per_tonne()

    print("The hydrogen sourcing frontier\n" + "=" * 78)
    print(f"  One parameter, not two: theta = green share. All-grey adds "
          f"{grey_t:.2f} tCO2/t")
    print(f"  to the clean route ({grey_t / Params().common.eps_cln:.0f}x eps_cln) "
          f"and subtracts the price difference.\n")

    print(f"  {'geo':<5}{'grey EUR/kg':>12}{'green EUR/kg':>13}"
          f"{'T* grey':>9}{'T* green':>10}{'NPV grey':>10}{'NPV green':>11}")
    for geo in geos:
        green_p, grey_p = endpoints(geo, series)
        lo, hi = point(geo, 0.0, series), point(geo, 1.0, series)
        print(f"  {geo:<5}{grey_p:>12.2f}{green_p:>13.2f}"
              f"{_fmt_year(lo.t_star):>9}{_fmt_year(hi.t_star):>10}"
              f"{lo.npv0:>10.0f}{hi.npv0:>11.0f}")

    print("\n  Sourcing is a TIMING lever, not only a cost one: the commitment")
    print("  year moves by years across the frontier, in a model that treats the")
    print("  hydrogen price as a scenario axis rather than a decision.\n")

    print("Carbon price at which green overtakes grey\n" + "=" * 78)
    p, sc = Params(), ScenarioParams()
    from timing_model.benefit import carbon_price_path

    base_2026 = carbon_price_path(p, sc)[p.common.t0]
    rows = []
    for geo in geos:
        mult = crossover_multiple(geo, series)
        rows.append((geo, mult))
    for geo, mult in sorted(rows, key=lambda r: (r[1] is None, r[1] or 0.0)):
        if mult is None:
            print(f"  {geo:<5}green never overtakes at any credible carbon price")
        else:
            print(f"  {geo:<5}{mult:>6.2f}x the central path "
                  f"(EUR {base_2026 * mult:>4.0f}/tCO2 in 2026)")
    print("\n  At the model's own carbon path, fossil hydrogen wins on NPV in")
    print("  every member state. The ordering is set by the absolute green-minus-")
    print("  grey SPREAD in EUR/kg, not by the power-to-gas ratio - the two give")
    print("  different orderings, and the spread is the one that matches. The")
    print("  crossover condition compares a price difference against an abatement")
    print("  difference, so a ratio never enters it.\n")

    print("What the independent-inputs assumption is worth\n" + "=" * 78)
    print(f"  {'geo':<5}{'theta at 2.60':>14}{'model NPV':>11}"
          f"{'consistent':>12}{'overstated by':>15}")
    for geo in geos:
        model, feasible, theta = feasibility_gap(geo, series)
        if theta is None:
            print(f"  {geo:<5}{'unreachable':>14}")
            continue
        print(f"  {geo:<5}{theta:>14.2f}{model:>11.0f}{feasible:>12.0f}"
              f"{model - feasible:>10.0f} ({(model - feasible) / model:>5.1%})")

    print("\nWhere the carbon is charged\n" + "=" * 78)
    print("  Same molecules, same emissions. A cost inside a constant p_H2 is")
    print("  frozen at 2026; the same cost inside eps_cln escalates with the path.\n")
    print(f"  {'geo':<5}{'merchant':>10}{'onsite':>9}{'gap':>8}{'gap %':>8}")
    for geo in geos:
        merchant, onsite = framing_gap(geo, series)
        print(f"  {geo:<5}{merchant:>10.0f}{onsite:>9.0f}"
              f"{merchant - onsite:>8.0f}{(merchant - onsite) / merchant:>8.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
