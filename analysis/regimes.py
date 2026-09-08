"""What a plant actually does, across scenarios: the decision regime map.

Answers the standing comments on the sensitivity note (``feedback-latest.md``):

* plot the **no-investment** case and say how much present value the switch
  recovers at the trigger;
* show **free allowances** alongside the carbon price rather than buried in
  ``alpha_v``;
* map opex, capex, carbon exposure, subsidy and allocation onto a **regime** -
  no investment, invest now, invest at the window, delayed, or wait for a
  better technology - so a reader can see which situation a plant is in;
* answer the four what-ifs: a carbon price that arrives a year late, free
  allocation that lasts a year longer, dearer fossil fuel, and the two
  together.

The model computes the *incremental* value of switching, so "no investment" is
the zero line by construction. That is exactly why it needs plotting: the
number a reader wants is not the increment but the bill they are already
carrying, and how much of it switching gets back.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Final

from timing_model.benefit import (
    CENTRAL_PATH,
    F_LAW2023,
    alpha_v,
    carbon_price_path,
    free_allocation_factor,
)
from timing_model.cost import reline_year
from timing_model.objective import discount, npv_curve
from timing_model.params import Params, ScenarioParams
from timing_model.primitives import effective_eps_inc
from timing_model.results import outputs

#: The five regimes a plant can be in, worst to most urgent, with the short
#: code used in the map (where a cell has room for one word, not five).
REGIMES: Final[tuple[str, ...]] = (
    "no investment",
    "wait for better technology",
    "delayed past the reline",
    "invest at the window",
    "invest now",
)
CODES: Final[Mapping[str, str]] = {
    "no investment": "none",
    "wait for better technology": "wait",
    "delayed past the reline": "delayed",
    "invest at the window": "window",
    "invest now": "now",
}


@dataclass(frozen=True)
class Regime:
    """The decision a scenario implies, and the evidence for it."""

    name: str
    t_star: int | None
    npv: float
    trigger: float
    crossing: int | None
    reason: str

    @property
    def rank(self) -> int:
        return REGIMES.index(self.name)

    @property
    def code(self) -> str:
        return CODES[self.name]


def no_investment_pv(p: Params, sc: ScenarioParams) -> float:
    """PV of the carbon bill if the plant never switches. EUR/t capacity.

    The incumbent emits ``eps_inc_eff`` per tonne of product and is handed
    ``alpha_v(t)`` of it free, so it pays for the rest at the prevailing price,
    every year to the horizon, discounted to ``t0``. The load factor bridges to
    capacity, exactly as it does in :func:`timing_model.benefit.annual_benefit`.

    This is the number the model never printed: not the value of switching, but
    the cost of not.
    """
    path = carbon_price_path(p, sc)
    eps = effective_eps_inc(p)
    return sum(
        discount(t, p) * sc.u * (1.0 - alpha_v(t, p, sc)) * eps * path[t]
        for t in range(p.common.t0, p.common.horizon_end + 1)
    )


def free_allocation_pv(p: Params, sc: ScenarioParams) -> float:
    """PV of the allowances the incumbent is given, at market value.

    The other half of the picture the comment asks for: what the plant is
    handed is as large as what it pays, and it disappears on a published
    schedule.
    """
    path = carbon_price_path(p, sc)
    eps = effective_eps_inc(p)
    return sum(
        discount(t, p) * sc.u * alpha_v(t, p, sc) * eps * path[t]
        for t in range(p.common.t0, p.common.horizon_end + 1)
    )


def recovery(p: Params, sc: ScenarioParams) -> dict[str, float]:
    """How much of the do-nothing bill the switch recovers, and where.

    Reported at the commitment year and at the year the price path reaches the
    trigger, because those are different years and the gap between them is the
    option premium.
    """
    o = outputs(p, sc)
    bill = no_investment_pv(p, sc)
    given = free_allocation_pv(p, sc)
    curve = npv_curve(p, sc)
    at_cross = curve.get(o.crossing_year) if o.crossing_year else None
    return {
        "do nothing, carbon bill": bill,
        "free allocation received": given,
        "net exposure": bill,
        "recovered at T*": o.npv0,
        "recovered at the crossing": at_cross if at_cross is not None else float("nan"),
        "share recovered at T*": o.npv0 / bill if bill else float("nan"),
    }


def classify(p: Params, sc: ScenarioParams) -> Regime:
    """Which of the five regimes this scenario is in.

    The taxonomy is the one the comment asks for, made operational:

    ``no investment``
        no commitment year exists - NPV(T) < 0 everywhere in the horizon.
    ``wait for better technology``
        the best year is at or beside the horizon: capex is still falling
        faster than the carbon price is rising, so the curve has not turned.
        Waiting is not caution here, it is the answer.
    ``delayed past the reline``
        the plant relines first and switches later. Capital is spent twice.
    ``invest at the window``
        the optimum falls between now and the reline - the intended case.
    ``invest now``
        the optimum is the first year available.
    """
    o = outputs(p, sc)
    if o.t_star is None:
        return Regime("no investment", None, o.npv0, o.trigger, o.crossing_year,
                      "NPV(T) < 0 for every year in the horizon")
    t_rel, t0, end = reline_year(p), p.common.t0, p.common.horizon_end
    if o.t_star >= end - 1:
        return Regime("wait for better technology", o.t_star, o.npv0, o.trigger,
                      o.crossing_year,
                      "the NPV curve has not turned by the horizon: learning "
                      "still outruns the carbon price")
    if o.t_star == t0:
        return Regime("invest now", o.t_star, o.npv0, o.trigger, o.crossing_year,
                      "the first available year is already the best one")
    if o.t_star > t_rel:
        return Regime("delayed past the reline", o.t_star, o.npv0, o.trigger,
                      o.crossing_year,
                      f"relines in {t_rel} and switches in {o.t_star}: the "
                      "reinvestment is spent and then stranded")
    return Regime("invest at the window", o.t_star, o.npv0, o.trigger,
                  o.crossing_year, f"between now and the {t_rel} reline")


# --------------------------------------------------------------- the scenario map

#: The five families the comment names, and the axis each is varied on.
AXES: Final[Mapping[str, tuple[str, tuple[float, ...]]]] = {
    "opex (hydrogen, EUR/kg)": ("p_H2", (2.0, 2.6, 4.0, 5.5, 7.0, 8.29)),
    "capex (multiple of I0)": ("I0_mult", (0.6, 0.8, 1.0, 1.2, 1.5)),
    "carbon exposure (path multiple)": ("price_scale", (0.6, 0.8, 1.0, 1.3, 1.6, 2.0)),
    "subsidy (s_max, EUR/t)": ("s_max", (0.0, 100.0, 200.0, 400.0, 660.0)),
    "free allocation": ("vintage", ("law2023", "com2026", "none")),
}


def _apply(axis: str, value: object, p: Params, sc: ScenarioParams
           ) -> tuple[Params, ScenarioParams]:
    """One axis moved, everything else held."""
    if axis == "p_H2":
        return p, replace(sc, p_H2=float(value))  # type: ignore[arg-type]
    if axis == "I0_mult":
        return p.with_sector(I0=Params().sector.I0 * float(value)), sc  # type: ignore[arg-type]
    if axis == "price_scale":
        return p, replace(sc, price_scale=float(value))  # type: ignore[arg-type]
    if axis == "s_max":
        return p.with_policy(s_max=float(value)), sc  # type: ignore[arg-type]
    if axis == "vintage":
        if value == "none":
            return p.with_policy(benchmark=0.0), sc
        return p, replace(sc, policy_vintage=str(value))
    raise ValueError(axis)


def axis_scan(axis: str, values: Sequence[object], p: Params | None = None,
              sc: ScenarioParams | None = None) -> list[tuple[object, Regime]]:
    """Regime along one axis, everything else at the base case."""
    p = p or Params()
    sc = sc or ScenarioParams(u=1.0)
    return [(v, classify(*_apply(axis, v, p, sc))) for v in values]


def corrected() -> tuple[Params, ScenarioParams]:
    """The defensible configuration: load factor, hot metal, real prices.

    The map is drawn here rather than on the published row because the
    published row invests in almost every cell, which tells a reader nothing.
    """
    return (Params().with_policy(kappa=0.94),
            ScenarioParams(u=0.85, price_basis="real"))


def regime_grid(x_axis: str = "p_H2", y_axis: str = "price_scale",
                xs: Sequence[float] = (2.0, 3.5, 5.0, 6.5, 8.29),
                ys: Sequence[float] = (0.4, 0.6, 1.0, 1.5, 2.0, 3.0),
                base: tuple[Params, ScenarioParams] | None = None,
                ) -> list[list[Regime]]:
    """Two axes at once: the map the comment asks for.

    Hydrogen price against carbon exposure is the pair that matters, because
    they are the two the plant does not control and the two that move the
    regime rather than the level.
    """
    p, sc = base or corrected()
    out = []
    for y in ys:
        row = []
        for x in xs:
            pp, ss = _apply(x_axis, x, p, sc)
            pp, ss = _apply(y_axis, y, pp, ss)
            row.append(classify(pp, ss))
        out.append(row)
    return out


# ------------------------------------------------------------------ the what-ifs

def _shifted_path(years: int) -> Mapping[int, float]:
    """The central path arriving ``years`` later: each anchor held one more year."""
    return {y: CENTRAL_PATH[max(min(CENTRAL_PATH), y - years)]
            if y - years in CENTRAL_PATH or y - years < min(CENTRAL_PATH)
            else CENTRAL_PATH[max(CENTRAL_PATH)]
            for y in CENTRAL_PATH}


def what_ifs() -> list[tuple[str, Regime, float]]:
    """The four questions asked, each against the base case.

    Returns ``(label, regime, delta NPV against base)``.
    """
    import timing_model.benefit as B

    p, sc = Params(), ScenarioParams(u=1.0)
    base = classify(p, sc)
    rows: list[tuple[str, Regime, float]] = [("base case", base, 0.0)]

    # 1. the carbon price arrives a year late
    original = B.carbon_price_path

    def late(pp: Params, ss: ScenarioParams) -> dict[int, float]:
        table = original(pp, ss)
        return {t: table[max(pp.common.t0, t - 1)] for t in table}

    try:
        B.carbon_price_path = late
        r = classify(p, sc)
        rows.append(("carbon price a year late", r, r.npv - base.npv))
    finally:
        B.carbon_price_path = original

    # 2. free allocation lasts a year longer
    original_f = B.free_allocation_factor

    def longer(t: int, ss: ScenarioParams) -> float:
        return original_f(max(min(F_LAW2023), t - 1), ss)

    try:
        B.free_allocation_factor = longer
        r = classify(p, sc)
        rows.append(("free allocation a year longer", r, r.npv - base.npv))
    finally:
        B.free_allocation_factor = original_f

    # 3. fossil fuel dearer: coke and PCI cost more, so avoiding them is worth more
    dearer = p.with_sector(c_avoided=p.sector.c_avoided * 1.3)
    r = classify(dearer, sc)
    rows.append(("fossil fuel +30 per cent", r, r.npv - base.npv))

    # 4. the two that cut against each other, together
    try:
        B.carbon_price_path = late
        B.free_allocation_factor = longer
        r = classify(dearer, sc)
        rows.append(("late price + longer allocation + dear fuel", r,
                     r.npv - base.npv))
    finally:
        B.carbon_price_path = original
        B.free_allocation_factor = original_f
    return rows


def allocation_table(p: Params | None = None, sc: ScenarioParams | None = None
                     ) -> list[tuple[int, float, float, float, float]]:
    """Year, price, free share, allowances given, carbon paid. EUR/t capacity.

    The comment asked for free allowances shown next to the carbon price rather
    than folded into a coefficient. This is that table.
    """
    p = p or Params()
    sc = sc or ScenarioParams(u=1.0)
    path = carbon_price_path(p, sc)
    eps = effective_eps_inc(p)
    rows = []
    for t in range(p.common.t0, p.common.horizon_end + 1):
        a = alpha_v(t, p, sc)
        rows.append((t, path[t], free_allocation_factor(t, sc),
                     sc.u * a * eps * path[t],
                     sc.u * (1.0 - a) * eps * path[t]))
    return rows


def main() -> int:
    """Print the counterfactual, the map, and the what-ifs."""
    p, sc = Params(), ScenarioParams(u=1.0)

    print("The cost of doing nothing\n" + "=" * 78)
    rec = recovery(p, sc)
    print(f"  Carbon bill if the plant never switches   "
          f"EUR {rec['do nothing, carbon bill']:>9,.0f} /t capacity, PV to 2026")
    print(f"  Allowances handed over free               "
          f"EUR {rec['free allocation received']:>9,.0f}")
    print(f"  Value recovered by switching at T*        "
          f"EUR {rec['recovered at T*']:>9,.0f}"
          f"   ({rec['share recovered at T*']:.0%} of the bill)")
    if rec["recovered at the crossing"] == rec["recovered at the crossing"]:
        print(f"  Value recovered if you wait for the trigger"
              f" EUR {rec['recovered at the crossing']:>8,.0f}")
    print("\n  The model reports the increment, so 'no investment' is the zero")
    print("  line. The bill above is what that zero line is hiding.\n")

    print("Carbon price and free allocation, side by side\n" + "=" * 78)
    print(f"  {'year':<6}{'EUA':>8}{'free':>8}{'given':>10}{'paid':>10}")
    for t, price, f, given, paid in allocation_table(p, sc):
        if t % 3 == 0 or t <= 2030:
            print(f"  {t:<6}{price:>8.1f}{f:>8.1%}{given:>10.1f}{paid:>10.1f}")
    print()

    print("Regime along each axis\n" + "=" * 78)
    for label, (axis, values) in AXES.items():
        print(f"\n  {label}")
        for value, reg in axis_scan(axis, values, p, sc):
            year = reg.t_star if reg.t_star else "-"
            print(f"    {str(value):<10}{reg.name:<28}T*={str(year):<6}"
                  f"NPV={reg.npv:>9,.0f}   {reg.reason}")

    print("\n\nRegime map: hydrogen price against carbon exposure\n" + "=" * 78)
    xs = (2.0, 3.5, 5.0, 6.5, 8.29)
    ys = (0.4, 0.6, 1.0, 1.5, 2.0, 3.0)
    grid = regime_grid("p_H2", "price_scale", xs, ys)
    print("  Drawn on the corrected configuration (u = 0.85, kappa = 0.94, real"
          " prices):\n  the published row invests in nearly every cell, which "
          "says nothing.\n")
    print(f"  {'carbon':<9}" + "".join(f"{f'H2 {x:g}':>10}" for x in xs))
    for y, row in zip(reversed(ys), reversed(grid), strict=True):
        print(f"  {f'x{y:g}':<9}" + "".join(f"{r.code:>10}" for r in row))
    print("\n  none = no investment · wait = wait for better technology ·")
    print("  delayed = past the reline · window = between now and it · now = 2026\n")

    print("What if\n" + "=" * 78)
    for label, reg, delta in what_ifs():
        year = reg.t_star if reg.t_star else "-"
        print(f"  {label:<42}{reg.name:<28}T*={str(year):<6}"
              f"NPV={reg.npv:>9,.0f}  ({delta:+,.0f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
