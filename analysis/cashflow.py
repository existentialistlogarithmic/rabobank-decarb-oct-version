"""The four inputs as trajectories over time, and the cash flow they produce.

Why this module exists
----------------------
A review comment, and the sharpest one so far: *the graphs and the tables are
one step before the visual analysis*. Capex, opex, subsidies and CO2 are all in
the model, but they are entangled inside the equations - a learning multiplier
here, a support window there, a free-allocation factor folded into a
coefficient - and the build reported the model's OUTPUTS without ever drawing
its INPUTS against time.

That matters because of who reads the result. An analyst reads NPV(T) and sees
a decision. A lender reads a cash flow: money out, money in, year by year,
cumulative, and when it turns positive. Debt is sized against that, not against
an optimum. So this module does the half step between the two - it unfolds the
model's boundary conditions into four annual trajectories, then adds them up
into the cash flow those trajectories imply.

The four lines, and their shapes
--------------------------------
``capex``
    Zero until the commitment year, then the whole switching cost at once:
    gross capex after learning, plus the forfeited residual book value, plus or
    minus the reline depending on which side of it the commitment falls. It is
    a spike, not a curve, because the model commits in one year.
``subsidy``
    Negative capex, paid in the commitment year, at whatever the support window
    is worth then. Its time shape is real and already in the model: eq (9) pays
    0.35*s_max before the window opens, full weight to 2031, then a linear
    taper to nothing by 2035. Committing a year late can cost real money.
``co2``
    The carbon cost avoided each year after the switch, net of the free
    allocation still being received, plus the resale term where permitted. This
    is the only one of the four that runs for the whole horizon, and it is what
    the whole case rests on.
``opex``
    The operating penalty, every year after the switch. **Flat**, because the
    model carries one constant. See the boundary note below; this is the line
    that does not yet have the shape it should.

What this module does NOT fix
-----------------------------
The opex trajectory is the honest gap. A real plant's operating cost falls as a
new asset beds in, rises as it ages and needs repair, jumps again at the switch
while people learn an unfamiliar technology, then settles lower as contracts
improve. The model has none of that: ``a`` is a single constant driven only by
the hydrogen price, so the line drawn here is flat and labelled flat. Giving it
a plausible curve would mean inventing the numbers this build exists to stop
inventing - it is hole H10 and review comment 5, still open.

Everything here is a re-presentation. No parameter changes, and the discounted
cash flow sums to the model's own NPV, which :mod:`analysis.verify` checks.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from timing_model.benefit import (
    alpha_v,
    carbon_price_path,
    support_stream_flow,
)
from timing_model.cost import reline_year, residual_value, support, switching_cost
from timing_model.objective import discount, npv
from timing_model.params import Params, ScenarioParams
from timing_model.primitives import (
    abatement_intensity,
    effective_eps_inc,
    opex_penalty,
)
from timing_model.scenarios import published_base

#: Plant the money columns are for, in Mt/yr - the same reference the rest of
#: the build uses, so a figure here is comparable with one in T1 or T2.
REFERENCE_MT: Final[float] = 2.5

#: The four components, in the order the conversation put them, with the sign
#: convention a cash flow uses: negative is money out.
COMPONENTS: Final[tuple[str, ...]] = ("capex", "subsidy", "opex", "co2")


@dataclass(frozen=True)
class Line:
    """One component's annual trajectory, in EUR per year for a real plant."""

    name: str
    unit: str
    values: dict[int, float]
    shape: str
    """What the line looks like and why - a spike, a step, a taper, a flat."""
    modelled: bool = True
    """False where the model has no time shape for this and the line is flat."""

    def total(self) -> float:
        return sum(self.values.values())

    def discounted(self, p: Params) -> float:
        return sum(discount(t, p) * v for t, v in self.values.items())


@dataclass(frozen=True)
class CashFlow:
    """The four lines, their annual sum, and what a lender reads off it."""

    commit_year: int
    mt_per_yr: float
    years: Sequence[int]
    lines: dict[str, Line]
    net: dict[int, float]
    cumulative: dict[int, float]
    payback_year: int | None
    payback_reason: str
    npv_check: tuple[float, float] = field(default=(0.0, 0.0))
    """(discounted sum here, the model's own NPV) - equal by construction."""

    def peak_exposure(self) -> tuple[int, float]:
        """The worst point of the cumulative curve: how deep, and when.

        The number a lender sizes against. Not the capex, which is only the
        first year's outflow - exposure keeps growing while the annual net is
        still negative, and the trough is the real financing requirement.
        """
        year = min(self.cumulative, key=lambda t: self.cumulative[t])
        return year, self.cumulative[year]


def carbon_flow(t: int, p: Params, sc: ScenarioParams) -> float:
    """Carbon cost avoided in year t, EUR per tonne of product.

    The benefit's carbon half, separated from the operating penalty so the two
    can be drawn as different lines. ``(1-alpha)*b*price`` is the abatement the
    firm was paying for and no longer is; ``w*alpha*eps_inc*price`` is the free
    allocation it can sell once it stops needing it.
    """
    price = carbon_price_path(p, sc)[t]
    alpha = alpha_v(t, p, sc)
    return ((1.0 - alpha) * abatement_intensity(p) * price
            + sc.w * alpha * effective_eps_inc(p) * price)


def trajectories(
    commit_year: int,
    p: Params | None = None,
    sc: ScenarioParams | None = None,
    mt_per_yr: float = REFERENCE_MT,
) -> dict[str, Line]:
    """The four inputs as annual money flows for a real plant.

    Signs are a cash flow's, not the model's: money out is negative. Capex and
    the write-off are outflows, the subsidy is an inflow against them, the
    operating penalty is an outflow every year, and the avoided carbon is an
    inflow every year.

    Per-tonne-of-CAPACITY quantities are multiplied by nameplate tonnes;
    per-tonne-of-PRODUCT flows are multiplied by tonnes actually made, which is
    nameplate times the load factor. Conflating the two is the error the whole
    units pass exists to prevent, so the two denominators are applied
    separately here rather than through one factor.
    """
    p = p or Params()
    sc = sc or ScenarioParams(u=1.0)
    nameplate = mt_per_yr * 1e6
    product = nameplate * sc.u
    years = list(range(p.common.t0, p.common.horizon_end + 1))

    sw = switching_cost(commit_year, p, sc)
    t_rel = reline_year(p)

    capex: dict[int, float] = dict.fromkeys(years, 0.0)
    # The write-off is part of what committing costs, so it lands with the
    # capex rather than in a fifth line nobody asked for.
    capex[commit_year] = -(sw.capex + sw.writeoff) * nameplate
    # The reline: avoided if the switch lands on or before it, paid if after.
    reline = p.sector.rho * p.sector.K_s * nameplate
    capex[t_rel] = capex.get(t_rel, 0.0) + (reline if t_rel >= commit_year
                                            else -reline)

    subsidy: dict[int, float] = dict.fromkeys(years, 0.0)
    subsidy[commit_year] = sw.support * nameplate

    a = opex_penalty(p, sc)
    opex = {t: (a * product if t >= commit_year else 0.0) for t in years}

    co2 = {
        t: ((carbon_flow(t, p, sc)
             + support_stream_flow(t, commit_year, p, sc)) * product
            if t >= commit_year else 0.0)
        for t in years
    }

    return {
        "capex": Line(
            "Capex", "EUR/yr", capex,
            "A spike in the commitment year - gross capex after learning plus "
            "the forfeited book value - with the reline added or subtracted at "
            f"{t_rel} depending on which side of it the switch falls. The "
            "model commits in one year, so there is no construction profile."),
        "subsidy": Line(
            "Subsidy", "EUR/yr", subsidy,
            "Paid against capex in the commitment year, at whatever the "
            "support window is worth then: eq (9) pays 0.35 of the maximum "
            "before the window opens, full weight to 2031, then a linear taper "
            "to nothing by 2035. Committing late costs real money."),
        "opex": Line(
            "Opex penalty", "EUR/yr", opex,
            "FLAT - and that is a limitation, not a finding. The model carries "
            "one constant driven only by the hydrogen price. A real plant's "
            "operating cost rises with age, jumps again at the switch while "
            "the technology is learned, then settles lower as contracts "
            "improve. None of that is here (hole H10).",
            modelled=False),
        "co2": Line(
            "CO2 avoided", "EUR/yr", co2,
            "Rises with the carbon price path AND with the phase-out of free "
            "allocation, which is why it steepens rather than tracking the "
            "price alone. The only one of the four that runs for the whole "
            "horizon, and the line the case rests on."),
    }


def build(
    commit_year: int | None = None,
    p: Params | None = None,
    sc: ScenarioParams | None = None,
    mt_per_yr: float = REFERENCE_MT,
) -> CashFlow:
    """The whole cash flow for committing in ``commit_year``, defaulting to T*."""
    p = p or Params()
    sc = sc or ScenarioParams(u=1.0)
    if commit_year is None:
        from timing_model.objective import t_star

        commit_year = t_star(p, sc)

    lines = trajectories(commit_year, p, sc, mt_per_yr)
    years = sorted(next(iter(lines.values())).values)
    net = {t: sum(line.values[t] for line in lines.values()) for t in years}

    cumulative: dict[int, float] = {}
    running = 0.0
    for t in years:
        running += net[t]
        cumulative[t] = running

    payback_year, reason = None, "cumulative never turns positive by the horizon"
    for t in years:
        if t >= commit_year and cumulative[t] >= 0.0:
            payback_year, reason = t, f"{t - commit_year} years after committing"
            break

    discounted = sum(discount(t, p) * net[t] for t in years)
    model_npv = npv(commit_year, p, sc) * mt_per_yr * 1e6
    return CashFlow(commit_year, mt_per_yr, years, lines, net, cumulative,
                    payback_year, reason, (discounted, model_npv))


def do_nothing(
    p: Params | None = None,
    sc: ScenarioParams | None = None,
    mt_per_yr: float = REFERENCE_MT,
) -> dict[int, float]:
    """The carbon bill the incumbent route pays each year by not switching.

    The model's NPV is an increment, so this is identically the zero line
    inside it. Drawn separately because a lender comparing two cases needs to
    see both, and because "the alternative is free" is the misreading the
    increment convention invites.
    """
    p = p or Params()
    sc = sc or ScenarioParams(u=1.0)
    product = mt_per_yr * 1e6 * sc.u
    prices = carbon_price_path(p, sc)
    return {
        t: -(1.0 - alpha_v(t, p, sc)) * effective_eps_inc(p) * prices[t] * product
        for t in range(p.common.t0, p.common.horizon_end + 1)
    }


def support_window(
    p: Params | None = None, sc: ScenarioParams | None = None
) -> dict[int, float]:
    """What the subsidy would be worth for each possible commitment year.

    Not a cash flow: a map of the OPPORTUNITY. It is the eq (9) shape drawn
    directly, and it says what committing in one year rather than another is
    worth in support alone, before any other consideration.
    """
    p = p or Params()
    sc = sc or ScenarioParams(u=1.0)
    return {t: support(t, p, sc)
            for t in range(p.common.t0, p.common.horizon_end + 1)}


def book_value(p: Params | None = None) -> dict[int, float]:
    """Residual book value of the incumbent asset, EUR/t capacity, by year.

    The straight-line decline behind the write-off term. It is why committing
    early is expensive in a way the capex number alone does not show: the
    earlier the switch, the more undepreciated book value is forfeited.
    """
    p = p or Params()
    return {t: residual_value(t, p)
            for t in range(p.common.t0, p.common.horizon_end + 1)}


def main() -> int:
    """Print the cash flow the way a lender would want to read it."""
    from analysis import units

    cf = build()
    p, sc = published_base()
    print("The business case as a cash flow\n" + "=" * 78)
    print(f"  Commit in {cf.commit_year}, {cf.mt_per_yr:g} Mt/yr plant, "
          f"real EUR, discounted at {p.common.r:.0%} to {p.common.t0}.\n")

    print(f"  {'year':<7}{'capex':>13}{'subsidy':>12}{'opex':>13}"
          f"{'CO2 avoided':>14}{'net':>13}{'cumulative':>14}")
    print("  " + "-" * 84)
    shown = [cf.commit_year - 1, cf.commit_year, cf.commit_year + 1,
             cf.commit_year + 5, 2035, 2040, 2050]
    for t in [y for y in cf.years if y in shown]:
        row = "".join(f"{units.eur(cf.lines[c].values[t]):>13}"
                      if c != "opex" else f"{units.eur(cf.lines[c].values[t]):>13}"
                      for c in COMPONENTS)
        print(f"  {t:<7}{row}{units.eur(cf.net[t]):>13}"
              f"{units.eur(cf.cumulative[t]):>14}")

    trough_year, trough = cf.peak_exposure()
    print(f"\n  Peak exposure     {units.eur(trough)} in {trough_year}")
    print(f"  Payback           {cf.payback_year or 'not within the horizon'}"
          f"  ({cf.payback_reason})")
    here, model = cf.npv_check
    print(f"  Discounted sum    {units.eur(here)}")
    print(f"  Model NPV(T*)     {units.eur(model)}   "
          f"(agree to {abs(here - model):,.2f})")

    print("\n  Lines that are real shapes in the model:")
    for name in COMPONENTS:
        line = cf.lines[name]
        mark = " " if line.modelled else "!"
        print(f"   {mark} {line.name:<14}{line.shape.split('.')[0]}.")
    print("\n  ! The opex line is FLAT because the model carries one constant.")
    print("    A real plant's operating cost has a shape; this one does not.")
    print("    Hole H10, review comment 5 - open, and not filled by invention.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
