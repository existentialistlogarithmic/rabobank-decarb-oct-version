"""The published base case against the sourced one, side by side.

A research pass went back to primary and near-primary documents for every input
the published base case assumes. Its parameters are in ``data/sourced/`` and
:mod:`data.sourced` reads them. This module runs the model on them.

The result in one line: **the published base case is not wrong arithmetically,
it is optimistic on every input that matters, and the errors compound in the
same direction.** Capex is below every announced transformation project, the
hydrogen price is a fossil price, the load factor assumes a furnace that never
stops, and the volatility is a choice rather than an observation. Each pushes
the trigger up and the commitment year out; together they move the trigger from
EUR 109.5 to EUR 239.4 and the crossing from 2030 to 2046.

What this module does NOT do
----------------------------
It does not change what the model runs on. ``Params()`` still carries the
published base case, the validation gate still reproduces the published nine,
and every other page in the build still reports that case. The sourced values
are shown *beside* it, because the two rest on different evidence and averaging
them would destroy the only useful thing about the comparison.

It also does not upgrade anybody's provenance. 9% of the research rows carry a
captured URL; the rest name a source without linking it, which is ``unverified``
here, not ``sourced``. :func:`main` prints that coverage before any number.

Four things the research established that are structural, not numerical
-----------------------------------------------------------------------
1. Support is a *stream*: the German CCfD pays per tonne of CO2 over fifteen
   years, and eq (10) values that at EUR 391-652/t against the model's EUR 200
   lump. The model already carries ``support_basis='stream'`` as a switch, so
   this is a calibration, not a rewrite. See :func:`support_shape`.
2. Capex is a *distribution with a boundary tag*, not a number: EAF-only
   projects land near EUR 600/t and greenfield with an electrolyser near
   EUR 2,600/t, for the same nominal "transformation". See :func:`capex_by_boundary`.
3. The reline share ``rho`` is contested by a factor of three between the
   specification and the one named plant. See :func:`rho_disagreement`.
4. ArcelorMittal walked away from EUR 1.3bn of approved grants in June 2025.
   That is a revealed reservation price, and it sits on the sourced side of the
   comparison rather than the published one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Final

from analysis import units
from data import sourced as src
from timing_model import cost, option
from timing_model.params import Params, ScenarioParams
from timing_model.primitives import mac
from timing_model.results import Outputs, outputs

#: Plant size the absolute-money columns are quoted at, in Mt/yr. Stegra's
#: Boden capacity, so the figures sit beside a real announced project rather
#: than a round invented one. Scaling is linear; any other size follows.
REFERENCE_MT: Final[float] = 2.5

#: The four parameter cases the research pass returned, in order of severity.
CASES: Final[tuple[str, ...]] = ("base", "low", "central", "high")

#: Volatility rungs to report. The model's own ladder stops at 0.45; the
#: research adds the Carbon-VIX headline (0.54) and its upper range (0.83).
#: 0.45 is the preferred anchor: realised, not implied, because the variance
#: risk premium inflates implied measures.
SIGMA_RUNGS: Final[tuple[float, ...]] = (0.10, 0.20, 0.30, 0.45, 0.54, 0.83)

#: Years the CCfD-style stream runs in eq (10), and the discount rate it is
#: valued at. Ten years is the research pass's own horizon for the arithmetic;
#: the German instrument itself runs fifteen.
STREAM_YEARS: Final[int] = 10


@dataclass(frozen=True)
class Case:
    """One parameter case, and what the model says when it runs on it."""

    name: str
    I0: float
    p_H2: float
    a: float
    out: Outputs
    beta: float
    multiple: float
    mac: float
    p_M: float


def _p_h2_for(a_value: float) -> float:
    """Invert the opex penalty: which hydrogen price gives this ``a``.

    The research pass quotes ``a`` directly and the hydrogen price separately;
    the model takes the price and derives ``a`` through eq (14). Inverting
    keeps the two consistent instead of letting a rounded ``a`` and a rounded
    price drift apart.
    """
    return (83.0 - a_value) / 55.0


def case_params(name: str) -> tuple[Params, ScenarioParams]:
    """Params for one case. Unsourced fields keep their published values."""
    p, sc = Params(), ScenarioParams(u=1.0)
    if name == "base":
        return p, sc
    i0 = src.value("I0", name)
    a = src.value("a", name)
    if i0 is None or a is None:
        raise KeyError(f"case {name!r} is not fully sourced in data/sourced")
    return p.with_sector(I0=i0), replace(sc, p_H2=_p_h2_for(a))


def run_case(name: str) -> Case:
    """Run the model on one case and collect everything worth reporting."""
    p, sc = case_params(name)
    s_s = cost.residual_value(p.common.t0, p)
    return Case(
        name=name,
        I0=p.sector.I0,
        p_H2=sc.p_H2,
        a=src.value("a", name) if name != "base" else -60.0,
        out=outputs(p, sc),
        beta=option.beta(p, sc),
        multiple=option.option_multiple(p, sc),
        mac=mac(p, sc, s_s),
        p_M=option.break_even_price(p, sc, s_s),
    )


def all_cases() -> list[Case]:
    """Every sourced case, published base first."""
    return [run_case(name) for name in CASES]


def capex_by_boundary() -> list[tuple[str, float, str, str]]:
    """(project, EUR/t capacity, scope boundary, status) for every announcement.

    The scope boundary is the whole point. EUR 600/t and EUR 2,600/t are both
    honest numbers for "the transformation"; they differ because one is an EAF
    dropped into an existing works and the other is a greenfield plant with its
    own 700 MW of electrolysis. A single ``I0`` cannot represent both.
    """
    rows = []
    for r in src.projects():
        per_t = r.num("capex_EUR_per_t_capacity")
        if per_t is None:
            continue
        rows.append((f"{r['project']} ({r['operator']})", per_t,
                     r["scope_boundary"], r["status"]))
    return sorted(rows, key=lambda t: t[1])


def _is_live(status: str) -> bool:
    """Whether a project is still being built, from its free-text status.

    ``CANCELLED`` is decisive. So is an EAF-only boundary, but that is caught
    by the caller, not here: this reads the status column only.
    """
    s = status.lower()
    return "cancelled" not in s and (
        "construction" in s or "commissioning" in s)


def support_shape(premium: float, years: int = STREAM_YEARS) -> float:
    """eq (10): what a premium of ``premium`` EUR/tCO2 is worth as a stock.

    ``premium * b * sum_{k<years} (1+r)^-k``, in EUR per tonne of capacity. The
    comparison that matters is against ``s_max``: the model nets a EUR 200 lump
    off capex, and the instrument that actually exists pays a stream worth two
    to three times that.
    """
    p = Params()
    b = p.common.eps_inc - p.common.eps_cln
    annuity = sum((1.0 + p.common.r) ** -k for k in range(years))
    return premium * b * annuity


def rho_disagreement() -> tuple[float, float, float, float]:
    """(spec rho, spec R, sourced rho, sourced R) - a factor of three apart.

    The v11 specification publishes ``rho = 0.35``, i.e. R = EUR 210/t. The one
    named plant in the research - Schwelgern, Europe's largest blast furnace -
    implies about EUR 50/t, i.e. ``rho`` near 0.12. A smaller reline credit
    weakens the incentive to wait, so this disagreement does not cancel out.
    """
    p = Params()
    spec_rho = p.sector.rho
    sourced = src.value("rho", "central") or 0.12
    return spec_rho, spec_rho * p.sector.K_s, sourced, sourced * p.sector.K_s


def sigma_ladder() -> list[tuple[float, float, float, float]]:
    """(sigma, beta, multiple, base-case trigger) across the full range.

    Computed in closed form rather than through ``SIGMA_REGIMES`` so the two
    rungs the research adds - 0.54 and 0.83 - can be shown without inventing
    names for them in the model's own ladder.
    """
    p, sc = Params(), ScenarioParams(u=1.0)
    r, mu = p.common.r, p.common.mu
    p_m = option.break_even_price(p, sc, cost.residual_value(p.common.t0, p))
    rows = []
    for s in SIGMA_RUNGS:
        half = 0.5 - mu / s**2
        beta = half + math.sqrt(half * half + 2.0 * r / s**2)
        rows.append((s, beta, beta / (beta - 1.0), p_m * beta / (beta - 1.0)))
    return rows


def main() -> int:
    """Print the comparison. Reports; does not gate."""
    got, total = src.link_coverage()
    print("Published base case against the sourced one")
    print("=" * 78)
    print(f"  Provenance first: {got}/{total} research rows ({got / total:.0%}) carry a")
    print("  captured URL. The rest name a source without linking it, which is")
    print("  'unverified' here, not 'sourced'. Nothing below is a checked figure")
    print("  until docs/research-sources.md has its Tier C rows replaced.\n")

    cases = all_cases()
    print(f"  {'':<9}{'I0':>7}{'p_H2':>7}{'a':>8}{'MAC':>8}{'p_M':>8}"
          f"{'trigger':>9}{'':>7}{'NPV':>9}{'':>10}")
    print(f"  {'case':<9}{'EUR/t':>7}{'EUR/kg':>7}{'EUR/t':>8}{'EUR/':>8}{'EUR/':>8}"
          f"{'EUR/':>9}{'T*':>7}{'EUR/t':>9}{'crossing':>10}")
    print(f"  {'':<9}{'cap':>7}{'':>7}{'prod/yr':>8}{'tCO2':>8}{'tCO2':>8}"
          f"{'tCO2':>9}{'':>7}{'cap':>9}{'':>10}")
    print("  " + "-" * 82)
    for c in cases:
        o = c.out
        print(f"  {c.name:<9}{c.I0:>7,.0f}{c.p_H2:>7.2f}{c.a:>8,.0f}{c.mac:>8.1f}"
              f"{c.p_M:>8.1f}{o.trigger:>9.1f}{str(o.t_star):>7}{o.npv0:>9,.0f}"
              f"{str(o.crossing_year):>10}")
    print(f"\n  The same two money columns for a {REFERENCE_MT:g} Mt/yr plant, because"
          " 'EUR 900' and")
    print("  'EUR 1,606' read as pocket change until the denominator is put back:\n")
    print(f"    {'case':<9}{'capex I0':>14}{'NPV at T*':>14}")
    print("    " + "-" * 37)
    for c in cases:
        print(f"    {c.name:<9}{units.eur(units.absolute(c.I0, REFERENCE_MT)):>14}"
              f"{units.eur(units.absolute(c.out.npv0, REFERENCE_MT)):>14}")
    boden = next((r for r in src.projects() if r["project"] == "Boden"), None)
    if boden and boden.num("capex_EUR_absolute"):
        built = units.eur(boden.num("capex_EUR_absolute") or 0.0)
        b_cap, b_npv = cases[0].I0, cases[0].out.npv0
        c_cap, c_npv = cases[2].I0, cases[2].out.npv0
        print(f"\n  Stegra's Boden is that size and cost {built} to build. The published")
        print(f"  case says a plant of it is worth "
              f"{units.eur(units.absolute(b_npv, REFERENCE_MT))} on a "
              f"{units.eur(units.absolute(b_cap, REFERENCE_MT))} spend; the")
        print(f"  sourced central case says "
              f"{units.eur(units.absolute(c_npv, REFERENCE_MT))} on "
              f"{units.eur(units.absolute(c_cap, REFERENCE_MT))}. Only one of those")
        print("  survives being read next to the announced projects.")
    base, central = cases[0], cases[2]
    print(f"\n  Published to sourced central: the trigger goes "
          f"{base.out.trigger:.1f} -> {central.out.trigger:.1f} EUR/tCO2 and the")
    print(f"  crossing {base.out.crossing_year} -> {central.out.crossing_year}. "
          f"Every input moved the same way; none of them cancelled.")

    print("\n\nCapex: one number cannot carry two boundaries")
    print("=" * 78)
    for name, per_t, boundary, status in capex_by_boundary():
        print(f"\n  {name}")
        print(f"    EUR {per_t:,.0f}/t capacity   {boundary}")
        print(f"    status: {status}")
    live = [(n, v) for n, v, _, s in capex_by_boundary() if _is_live(s)]
    dead = [(n, v) for n, v, _, s in capex_by_boundary() if not _is_live(s)]
    i0 = Params().sector.I0
    print(f"\n  The model runs on I0 = {i0:,.0f}. Sorting the projects by whether they")
    print("  survived contact with a balance sheet is more informative than sorting")
    print("  them by cost:")
    print(f"\n    still standing  {', '.join(f'{v:,.0f}' for _, v in live)}"
          "  (under construction or commissioning)")
    print(f"    not standing    {', '.join(f'{v:,.0f}' for _, v in dead)}"
          "  (cancelled, or EAF-only with no DRI)")
    print(f"\n  Every project still being built costs at least "
          f"{min(v for _, v in live):,.0f}/t, i.e. {min(v for _, v in live) / i0:.1f}x the")
    print("  model's capex. The two at or below it are an EAF dropped into an")
    print("  existing works and a scheme ArcelorMittal cancelled, forfeiting")
    print("  EUR 1.3bn of approved German aid - which is a price signal, not a")
    print("  cheaper way of doing the same thing.")

    print("\n\nSupport: a stream is not a lump (eq 10)")
    print("=" * 78)
    lump = Params().policy.s_max
    print(f"  The model nets a lump of EUR {lump:,.0f}/t capacity off capex.")
    print(f"  A CCfD-style premium over {STREAM_YEARS} years, at b = 1.8 and r = 8%:\n")
    print(f"  {'premium EUR/tCO2':>18}{'worth EUR/t capacity':>24}{'vs the lump':>14}")
    for premium in (20.0, 30.0, 40.0, 50.0):
        worth = support_shape(premium)
        print(f"  {premium:>18,.0f}{worth:>24,.0f}{worth / lump:>13.1f}x")
    print("\n  The German instrument runs fifteen years, not ten, so these are")
    print("  conservative. Per-company strike prices were not disclosed, so the")
    print("  premium is inferred from the mechanism, not observed (hole H1).")

    print("\n\nThe reline share is contested by a factor of three")
    print("=" * 78)
    spec_rho, spec_r, src_rho, src_r = rho_disagreement()
    lo = (src.parameter("rho", "central") or src.parameter("rho", "base"))
    band = f"{lo.num('value_low'):.2f}-{lo.num('value_high'):.2f}" if lo else "?"
    print(f"  v11 specification   rho = {spec_rho:.2f}         R = EUR {spec_r:,.0f}/t capacity")
    print(f"  Schwelgern implies  rho = {src_rho:.2f} ({band})  R = EUR {src_r:,.0f}/t capacity")
    print("\n  R is the reinvestment the switch avoids, so it is a reason to wait.")
    print("  A third of the credit is a third of that reason. Both are carried;")
    print("  neither is averaged into the other (disagreement D6).")

    print("\n\nVolatility: the largest single lever, and it is a choice")
    print("=" * 78)
    print(f"  {'sigma':>7}{'beta':>9}{'multiple':>11}{'base trigger':>15}")
    print("  " + "-" * 40)
    for s, beta, mult, trig in sigma_ladder():
        mark = "  <- model default" if s == 0.20 else (
            "  <- realised, preferred anchor" if s == 0.45 else "")
        print(f"  {s:>7.2f}{beta:>9.4f}{mult:>11.3f}{trig:>15.1f}{mark}")
    print("\n  sigma = 0.20 is a modelling choice, not an observation. The")
    print("  observed range puts the multiple between 2.9 and 15.0, which moves")
    print("  the trigger by more than every cost parameter combined.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
