"""The article's reference plant, in money: when does waiting stop paying?

Why this module exists
----------------------
The October draft of *The year waiting stops being free* quotes its headline
numbers from a "steel cross-check case" (annex eqs 1-8): a 2.5 Mt/yr plant,
3.5 MtCO2/yr avoided, 143 kt/yr of hydrogen, EUR 3bn of capex built over four
years. None of that case was in the repository, so none of the draft's numbers
could be re-run. This module is that case, written down once, with the review
corrections applied:

1. **Free allocation after the switch** (review comment, "IMPORTANT CHECK").
   EU free allocation is benchmark x historical activity x CBAM factor. Since
   Delegated Regulation (EU) 2024/873 the hot-metal benchmark also covers iron
   made by direct reduction, so a plant that switches keeps its allocation and
   can sell what it no longer surrenders. The carbon value of switching is then
   ``E x P(t)`` - the whole avoided bill plus the sold surplus - not
   ``E x P(t) x s(t)`` as the draft had it. ``allocation_after_switch="lost"``
   keeps the draft's reading as a sensitivity.
2. **Real, not nominal.** The draft discounted at 8% real but used nominal
   analyst prices. Every path here is deflated to 2026 euros first.
3. **One hydrogen intensity.** The draft took EUR 150m/yr of extra opex from
   55 kg H2/t and then EUR 143m per EUR 1/kg from 57.2 kg/t. Here the opex is
   built once from the plant's 143 kt/yr.
4. **The decision year is the FID, not first steel.** Capex runs T..T+3, the
   plant produces from T+4. Support depends on T (the repository's eq 9
   window), and the reline is avoided only if first steel comes before it.
5. **The July 2026 schedule.** COM(2026) 616 returns 15% of the phased-out
   allocation from 2028 and holds 15% to 2037 (the repository's eq 12). The
   draft's annex used a linear path to 2038 instead.

Layers
------
* deterministic: ``npv(T)``, ``npv_curve``, ``t_star``, ``marginal_value``,
  ``break_even``, ``payback``;
* option layer: ``lattice`` (exact, a binomial tree on the price level) and
  ``lsm`` (Longstaff-Schwartz least-squares Monte Carlo, the same problem by
  simulation - the two must agree, and a test checks they do);
* sensitivity: ``one_at_a_time``, ``sweep_81``, ``sobol``.

Units: EUR million, real 2026 euros, discounted at ``r`` to 2026. Prices are
EUR per tonne of CO2 in 2026 euros unless a name says ``nominal``.

Nothing here changes :mod:`timing_model`; it imports the allocation schedules,
the central path, the support window and the reline year from it so the two
cannot drift apart.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Final

from timing_model.benefit import CENTRAL_PATH, free_allocation_factor
from timing_model.cost import reline_year, support
from timing_model.params import Params, ScenarioParams

T0: Final[int] = 2026
HORIZON: Final[int] = 2050
#: Last decision year searched. First steel then lands in 2044, which leaves
#: seven operating years before the 2050 horizon - later than that, nothing
#: can pay back and the search would only report truncation.
LAST_DECISION: Final[int] = 2040

PATHS: Final[tuple[str, ...]] = ("stall", "central", "high")
RULEBOOKS: Final[tuple[str, ...]] = ("law2023", "com2026")

#: Nominal anchors of the pre-reform analyst outlook (ABN AMRO, Carbon Market
#: Strategist, 13 May 2026: EUR 138/t in 2030 and EUR 191/t in 2035, revised
#: down from 145 and 200). Interpolated linearly from the 2026 anchor shared
#: with the central path, then grown at the central path's drift.
HIGH_ANCHORS: Final[Mapping[int, float]] = {2026: 76.0, 2030: 138.0, 2035: 191.0}
#: Stall: the price stays at roughly its September-2026 level (EUR 85.6/t
#: average, GMK Center from ICE data), held flat in 2026 euros.
STALL_REAL: Final[float] = 85.0
#: Nominal drift after the last anchor - the repository's ``mu``.
DRIFT: Final[float] = Params().common.mu


@dataclass(frozen=True)
class Plant:
    """The reference plant: a standard EU H2-DRI-EAF facility. EUR m, Mt, kt."""

    capacity_mt: float = 2.5
    """Mt/yr of DRI-based steel. thyssenkrupp's first Duisburg DRI plant."""
    co2_avoided_mt: float = 3.5
    """MtCO2/yr the switch avoids at design output (thyssenkrupp: 'up to 3.5')."""
    h2_kt: float = 143.0
    """kt H2/yr (thyssenkrupp's 2024 tender volume; 57 kg per tonne)."""
    capex_eur_m: float = 3000.0
    """Capex, EUR m (about EUR 3bn for the Duisburg plant; EUR 1,200/t)."""
    build_years: int = 4
    """FID to first steel."""
    fuel_saving_eur_m: float = 207.5
    """Coke and coal avoided, net of extra power: EUR 83/t (repository c_avoided) x 2.5 Mt."""
    support_max_eur_m: float = 500.0
    """Capex grant at full weight: s_max = EUR 200/t capacity x 2.5 Mt."""
    reline_eur_m: float = 525.0
    """Blast-furnace reline avoided: rho x K_s = EUR 210/t capacity x 2.5 Mt."""
    reline_year: int = field(default_factory=lambda: reline_year(Params()))
    """Year the incumbent must be relined (repository T_rel = 2038)."""
    green_premium_eur_t: float = 0.0
    """Price premium on low-carbon steel, EUR/t. Zero: no premium assumed."""
    capex_drift: float = 0.0
    """Real change in capex per year of delay (negative = learning)."""


@dataclass(frozen=True)
class Case:
    """One scenario: a price path, a rulebook, and the operating assumptions."""

    path: str = "central"
    rulebook: str = "law2023"
    allocation_after_switch: str = "retained"
    p_h2: float = 2.60
    r: float = 0.08
    inflation: float = 0.02
    price_scale: float = 1.0
    sigma: float = 0.20
    support_scale: float = 1.0
    ccfd_strike: float | None = None
    """Real EUR/tCO2 paid on avoided emissions for ``ccfd_years``; None = no CCfD."""
    ccfd_years: int = 15
    plant: Plant = field(default_factory=Plant)

    def with_plant(self, **kw: object) -> Case:
        return replace(self, plant=replace(self.plant, **kw))


# ----------------------------------------------------------------- inputs


def nominal_path(name: str) -> dict[int, float]:
    """EUA price by year, nominal EUR/t, for the two analyst-based paths."""
    out: dict[int, float] = {}
    if name == "central":
        last = max(CENTRAL_PATH)
        for t in range(T0, HORIZON + 1):
            out[t] = (CENTRAL_PATH[t] if t <= last
                      else CENTRAL_PATH[last] * (1.0 + DRIFT) ** (t - last))
        return out
    if name == "high":
        years = sorted(HIGH_ANCHORS)
        for t in range(T0, HORIZON + 1):
            if t >= years[-1]:
                out[t] = HIGH_ANCHORS[years[-1]] * (1.0 + DRIFT) ** (t - years[-1])
                continue
            lo = max(y for y in years if y <= t)
            hi = min(y for y in years if y > t)
            w = (t - lo) / (hi - lo)
            out[t] = HIGH_ANCHORS[lo] + w * (HIGH_ANCHORS[hi] - HIGH_ANCHORS[lo])
        return out
    raise ValueError(f"no nominal anchors for path {name!r}")


def price_path(c: Case) -> dict[int, float]:
    """EUA price by year in 2026 euros. EUR/tCO2."""
    if c.path == "stall":
        base = dict.fromkeys(range(T0, HORIZON + 1), STALL_REAL)
    elif c.path in ("central", "high"):
        base = {t: v / (1.0 + c.inflation) ** (t - T0)
                for t, v in nominal_path(c.path).items()}
    else:
        raise ValueError(f"unknown path {c.path!r}; expected one of {PATHS}")
    return {t: v * c.price_scale for t, v in base.items()}


def allocation(t: int, rulebook: str) -> float:
    """Share of the avoidable emissions still covered free, f(t). 0..1."""
    return free_allocation_factor(t, ScenarioParams(policy_vintage=rulebook))


def payable_share(t: int, rulebook: str) -> float:
    """s(t) = 1 - f(t): the share of emissions a CBAM-sector plant pays for."""
    return 1.0 - allocation(t, rulebook)


def discount(t: int, r: float) -> float:
    return (1.0 + r) ** (-(t - T0))


def grant(T: int, c: Case) -> float:
    """Capex support for a decision in year T, EUR m (repository eq 9 window)."""
    p = Params()
    share = support(T, p, ScenarioParams()) / p.policy.s_max
    return c.plant.support_max_eur_m * share * c.support_scale


def extra_opex(c: Case) -> float:
    """Extra operating cost of the clean route, EUR m/yr (hydrogen less fuel saved)."""
    return c.plant.h2_kt * c.p_h2 - c.plant.fuel_saving_eur_m


# -------------------------------------------------------- the do-nothing side


def do_nothing_bill(c: Case) -> dict[int, float]:
    """Cash carbon bill on the avoidable emissions, EUR m/yr: E x P x s(t)."""
    prices = price_path(c)
    return {t: c.plant.co2_avoided_mt * prices[t] * payable_share(t, c.rulebook)
            for t in prices}


def carbon_value(c: Case) -> dict[int, float]:
    """Full carbon value of the avoidable emissions, EUR m/yr: E x P.

    With a technology-neutral benchmark this, not the cash bill, is what
    continuing to emit costs: every allowance used is one that could be sold.
    """
    prices = price_path(c)
    return {t: c.plant.co2_avoided_mt * prices[t] for t in prices}


def pv(series: Mapping[int, float], r: float, start: int = T0) -> float:
    return sum(v * discount(t, r) for t, v in series.items() if t >= start)


# --------------------------------------------------------- the switch side


def cash_flows(T: int, c: Case, x: float = 1.0) -> dict[int, float]:
    """Cash flow of a switch decided in year T, EUR m, by year.

    ``x`` scales every market carbon price from T on (the option layer's state
    variable); 1.0 is the scenario path itself.
    """
    pl = c.plant
    prices = price_path(c)
    first = T + pl.build_years
    capex = pl.capex_eur_m * (1.0 + pl.capex_drift) ** (T - T0)
    flows = dict.fromkeys(range(T0, HORIZON + 1), 0.0)
    for k in range(pl.build_years):
        if T + k <= HORIZON:
            flows[T + k] -= capex / pl.build_years
    if T <= HORIZON:
        flows[T] += grant(T, c)
    opex = extra_opex(c)
    for t in range(first, HORIZON + 1):
        in_ccfd = c.ccfd_strike is not None and t < first + c.ccfd_years
        price = c.ccfd_strike if in_ccfd else prices[t] * x
        covered = (1.0 if c.allocation_after_switch == "retained"
                   else payable_share(t, c.rulebook))
        flows[t] += pl.co2_avoided_mt * price * covered
        flows[t] -= opex
        flows[t] += pl.capacity_mt * pl.green_premium_eur_t
    if first <= pl.reline_year <= HORIZON:
        flows[pl.reline_year] += pl.reline_eur_m
    return flows


def npv(T: int, c: Case, x: float = 1.0) -> float:
    """NPV of switching with FID in year T, EUR m, real, discounted to 2026."""
    return pv(cash_flows(T, c, x), c.r)


def linear_in_x(T: int, c: Case) -> tuple[float, float]:
    """(a, b) with npv(T, c, x) == a + b*x exactly. Prices enter linearly."""
    a = npv(T, c, 0.0)
    return a, npv(T, c, 1.0) - a


def decision_years(last: int = LAST_DECISION) -> range:
    return range(T0, last + 1)


def npv_curve(c: Case, last: int = LAST_DECISION) -> dict[int, float]:
    return {T: npv(T, c) for T in decision_years(last)}


def t_star(c: Case, last: int = LAST_DECISION) -> int | None:
    """Best FID year; None if no year in the window has a positive NPV."""
    curve = npv_curve(c, last)
    best = max(curve.values())
    if best <= 0.0:
        return None
    return min(T for T, v in curve.items() if v == best)


def marginal_value(c: Case, last: int = LAST_DECISION) -> dict[int, float]:
    """Value of waiting one more year: NPV(T+1) - NPV(T), EUR m."""
    curve = npv_curve(c, last + 1)
    return {T: curve[T + 1] - curve[T] for T in decision_years(last)}


def break_even(T: int, c: Case) -> float:
    """Constant real carbon price at which a switch decided in T is worth zero.

    Solved exactly: with a flat price the NPV is linear in the price level.
    """
    flat = replace(c, path="stall", price_scale=1.0)
    lo = npv(T, flat, 0.0)
    hi = npv(T, flat, 1.0)
    return -lo / (hi - lo) * STALL_REAL


@dataclass(frozen=True)
class Payback:
    peak_funding: float
    """Most negative point of the cumulative cash flow, EUR m (undiscounted)."""
    peak_year: int
    payback_year: int | None
    cumulative: dict[int, float]


def payback(T: int, c: Case) -> Payback:
    flows = cash_flows(T, c)
    running, cumulative = 0.0, {}
    for t in sorted(flows):
        running += flows[t]
        cumulative[t] = running
    peak_year = min(cumulative, key=lambda t: cumulative[t])
    back = next((t for t in sorted(cumulative)
                 if t > peak_year and cumulative[t] >= 0.0), None)
    return Payback(cumulative[peak_year], peak_year, back, cumulative)


def waterfall(T: int, c: Case) -> dict[str, float]:
    """The NPV of a switch decided in T, split into its forces. EUR m, PV 2026."""
    pl = c.plant
    r = c.r
    first = T + pl.build_years
    prices = price_path(c)
    capex = pl.capex_eur_m * (1.0 + pl.capex_drift) ** (T - T0)
    out = {
        "carbon value avoided": 0.0,
        "extra operating cost": 0.0,
        "capex": -sum(capex / pl.build_years * discount(T + k, r)
                      for k in range(pl.build_years)),
        "capex support": grant(T, c) * discount(T, r),
        "reline avoided": (pl.reline_eur_m * discount(pl.reline_year, r)
                           if first <= pl.reline_year else 0.0),
    }
    for t in range(first, HORIZON + 1):
        in_ccfd = c.ccfd_strike is not None and t < first + c.ccfd_years
        price = c.ccfd_strike if in_ccfd else prices[t]
        covered = (1.0 if c.allocation_after_switch == "retained"
                   else payable_share(t, c.rulebook))
        out["carbon value avoided"] += pl.co2_avoided_mt * price * covered * discount(t, r)
        out["extra operating cost"] -= (extra_opex(c) - pl.capacity_mt
                                        * pl.green_premium_eur_t) * discount(t, r)
    out["NPV"] = sum(out.values())
    return out


def h2_break_even(T: int, c: Case) -> float:
    """Hydrogen price (EUR/kg) at which a switch decided in T is worth zero."""
    base = npv(T, replace(c, p_h2=0.0))
    slope = npv(T, replace(c, p_h2=1.0)) - base
    return -base / slope


def irr(T: int, c: Case) -> float | None:
    """Real internal rate of return of a switch decided in T (bisection).

    Relates the cash flows to the capital employed; not the same question as
    NPV against the cost of capital, which is why the article reports both.
    """
    flows = cash_flows(T, c)

    def value(rate: float) -> float:
        return sum(v * (1.0 + rate) ** (-(t - T0)) for t, v in flows.items())

    lo, hi = -0.5, 1.0
    if value(lo) * value(hi) > 0:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if value(lo) * value(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# ------------------------------------------------------------ option layer


@dataclass(frozen=True)
class OptionResult:
    value: float
    """Value of the investment opportunity with optimal timing, EUR m (PV 2026)."""
    static_best: float
    """max(0, best deterministic NPV) - what committing to a fixed year is worth."""
    exercise: dict[int, float]
    """Share of price paths that commit in each year."""
    never: float
    """Share that never commits by the last decision year."""

    @property
    def flexibility(self) -> float:
        return self.value - self.static_best

    def quantile_year(self, q: float) -> int | None:
        acc = 0.0
        for T in sorted(self.exercise):
            acc += self.exercise[T]
            if acc >= q - 1e-12:
                return T
        return None


def lattice(c: Case, last: int = LAST_DECISION, steps_per_year: int = 24
            ) -> tuple[float, dict[int, float]]:
    """Exact option value and trigger by backward induction on a binomial tree.

    The state is x, the ratio of the market price to the scenario path. Under a
    mean-preserving GBM, E[P_t | x_T] = path_t * x_T, so the value of
    committing in T is ``a_T + b_T * x_T`` (:func:`linear_in_x`) and the
    problem is one-dimensional. Payoffs are already in 2026 money, so the
    continuation needs no further discounting.

    Returns (value at x = 1 in 2026, {T: trigger x*_T}); the trigger is the
    lowest x at which committing in T beats waiting (inf if it never does).
    It is interpolated in log x between the two nodes that bracket the switch
    from waiting to committing, so it does not jump with the node spacing.
    The 2026 trigger is not resolved (the tree has a single node there).
    """
    dt = 1.0 / steps_per_year
    up = math.exp(c.sigma * math.sqrt(dt))
    down = 1.0 / up
    q = (1.0 - down) / (up - down)
    n_total = (last - T0) * steps_per_year
    coef = {T: linear_in_x(T, c) for T in decision_years(last)}

    def xs(n: int) -> list[float]:
        return [up ** (2 * j - n) for j in range(n + 1)]

    a, b = coef[last]
    values = [max(a + b * x, 0.0) for x in xs(n_total)]
    triggers: dict[int, float] = {last: (-a / b if b > 0 else math.inf)}
    for n in range(n_total - 1, -1, -1):
        values = [q * values[j + 1] + (1 - q) * values[j] for j in range(n + 1)]
        if n % steps_per_year == 0:
            T = T0 + n // steps_per_year
            a, b = coef[T]
            nodes = xs(n)
            gain = [a + b * x - v for x, v in zip(nodes, values, strict=True)]
            star = math.inf
            for j in range(n + 1):
                if a + b * nodes[j] > 0.0 and gain[j] >= 0.0:
                    star = nodes[j]
                    if j > 0 and gain[j - 1] < 0.0:
                        lo, hi = math.log(nodes[j - 1]), math.log(nodes[j])
                        w = -gain[j - 1] / (gain[j] - gain[j - 1])
                        star = max(math.exp(lo + w * (hi - lo)),
                                   -a / b if b > 0 else 0.0)
                    break
            for j in range(n + 1):
                values[j] = max(values[j], a + b * nodes[j])
            triggers[T] = star
    return values[0], dict(sorted(triggers.items()))


def constant_price_trigger(T: int, c: Case) -> float:
    """Constant real carbon price at which committing in T beats waiting.

    The option-layer counterpart of :func:`break_even`: both treat the price
    as flat in 2026 euros, so the two are directly comparable and their ratio
    is the premium uncertainty adds.
    """
    flat = replace(c, path="stall", price_scale=1.0)
    _, trig = lattice(flat)
    return trig[T] * STALL_REAL


def _solve3(m: list[list[float]], v: list[float]) -> list[float]:
    """Solve a 3x3 linear system by Cramer's rule (normal equations of LSM)."""
    def det(a: list[list[float]]) -> float:
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
                - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(m)
    if abs(d) < 1e-12:
        return [sum(v) / max(len(v), 1), 0.0, 0.0]
    out = []
    for i in range(3):
        mi = [row[:] for row in m]
        for r_ in range(3):
            mi[r_][i] = v[r_]
        out.append(det(mi) / d)
    return out


def lsm(c: Case, n_paths: int = 20000, seed: int = 20261020,
        last: int = LAST_DECISION) -> OptionResult:
    """Longstaff-Schwartz least-squares Monte Carlo for the same problem.

    Simulates x on annual steps (antithetic pairs), regresses the realised
    continuation value on (1, x, x^2) over in-the-money paths, and commits
    where the immediate value beats the fitted continuation. Returns the value
    and the distribution of commitment years.
    """
    rng = random.Random(seed)
    years = list(decision_years(last))
    half = n_paths // 2
    paths: list[list[float]] = []
    for _ in range(half):
        x_up, x_dn = [1.0], [1.0]
        for _t in years[1:]:
            z = rng.gauss(0.0, 1.0)
            drift = -0.5 * c.sigma ** 2
            x_up.append(x_up[-1] * math.exp(drift + c.sigma * z))
            x_dn.append(x_dn[-1] * math.exp(drift - c.sigma * z))
        paths.extend((x_up, x_dn))
    coef = [linear_in_x(T, c) for T in years]

    cash = [max(coef[-1][0] + coef[-1][1] * p[-1], 0.0) for p in paths]
    when: list[int | None] = [years[-1] if v > 0 else None for v in cash]
    for i in range(len(years) - 2, -1, -1):
        a, b = coef[i]
        pays = [a + b * p[i] for p in paths]
        itm = [k for k, v in enumerate(pays) if v > 0.0]
        if not itm:
            continue
        if i == 0:
            cont = sum(cash) / len(cash)
            if pays[0] > cont:
                cash = [pays[0]] * len(paths)
                when = [years[0]] * len(paths)
            break
        # normal equations for continuation ~ c0 + c1 x + c2 x^2
        s = [[0.0] * 3 for _ in range(3)]
        rhs = [0.0] * 3
        for k in itm:
            x = paths[k][i]
            basis = (1.0, x, x * x)
            for u_ in range(3):
                rhs[u_] += basis[u_] * cash[k]
                for v_ in range(3):
                    s[u_][v_] += basis[u_] * basis[v_]
        c0, c1, c2 = _solve3(s, rhs)
        for k in itm:
            x = paths[k][i]
            if pays[k] >= c0 + c1 * x + c2 * x * x:
                cash[k] = pays[k]
                when[k] = years[i]
    value = sum(cash) / len(cash)
    counts: dict[int, float] = dict.fromkeys(years, 0.0)
    for w in when:
        if w is not None:
            counts[w] += 1.0 / len(when)
    never = sum(1 for w in when if w is None) / len(when)
    static = max(0.0, max(npv(T, c) for T in years))
    return OptionResult(value, static, counts, never)


# ------------------------------------------------------------- sensitivity


@dataclass(frozen=True)
class Shock:
    label: str
    group: str
    """'project' (engineering, contracts) or 'market & rules' (prices, policy)."""
    case: Case


def one_at_a_time(base: Case) -> list[Shock]:
    """The one-change-at-a-time stress set, each applied to ``base`` alone."""
    pl = base.plant
    return [
        Shock("Capex +20%", "project", base.with_plant(capex_eur_m=pl.capex_eur_m * 1.2)),
        Shock("Build one year longer", "project",
              base.with_plant(build_years=pl.build_years + 1)),
        Shock("No capex support", "project", replace(base, support_scale=0.0)),
        Shock("Cost of capital 10%", "project", replace(base, r=0.10)),
        Shock("Carbon price path -20%", "market & rules", replace(base, price_scale=0.8)),
        Shock("Hydrogen +EUR 1/kg", "market & rules", replace(base, p_h2=base.p_h2 + 1.0)),
        Shock("Free allocation lost on switching", "market & rules",
              replace(base, allocation_after_switch="lost")),
    ]


def ccfd_net_payment(c: Case) -> float:
    """PV of what a two-way carbon CfD pays the plant over its term, EUR m.

    Positive: the state pays on balance; negative: the plant pays back. Taken
    along the scenario path for the decision year :func:`t_star` (or 2029).
    """
    if c.ccfd_strike is None:
        return 0.0
    T = t_star(c) or 2029
    first = T + c.plant.build_years
    prices = price_path(c)
    return sum(c.plant.co2_avoided_mt * (c.ccfd_strike - prices[t]) * discount(t, c.r)
               for t in range(first, min(first + c.ccfd_years, HORIZON + 1)))


@dataclass(frozen=True)
class SweepRow:
    path: str
    p_h2: float
    capex: float
    r: float
    t_star: int | None
    npv_star: float
    marginal: dict[int, float]


SWEEP_H2: Final[tuple[float, ...]] = (2.60, 3.80, 5.00)
SWEEP_CAPEX: Final[tuple[float, ...]] = (2400.0, 3000.0, 3600.0)
SWEEP_R: Final[tuple[float, ...]] = (0.06, 0.08, 0.10)


def sweep_81(base: Case | None = None) -> list[SweepRow]:
    """3 carbon paths x 3 hydrogen prices x 3 capex levels x 3 discount rates."""
    base = base or Case()
    rows = []
    for path in PATHS:
        for h2 in SWEEP_H2:
            for capex in SWEEP_CAPEX:
                for r in SWEEP_R:
                    c = replace(base, path=path, p_h2=h2, r=r).with_plant(capex_eur_m=capex)
                    ts = t_star(c)
                    curve = npv_curve(c)
                    rows.append(SweepRow(path, h2, capex, r, ts, max(curve.values()),
                                         marginal_value(c)))
    return rows


#: Ranges for the variance decomposition: (low, high), sampled uniformly.
SOBOL_RANGES: Final[Mapping[str, tuple[float, float]]] = {
    "carbon price scale": (0.75, 1.25),
    "hydrogen EUR/kg": (2.60, 5.00),
    "capex EUR m": (2400.0, 3600.0),
    "build years": (3.5, 5.5),
    "discount rate": (0.06, 0.10),
    "capex support EUR m": (0.0, 1000.0),
}


def _apply(base: Case, v: Sequence[float]) -> Case:
    scale, h2, capex, build, r, grant_m = v
    return replace(base, price_scale=scale, p_h2=h2, r=r,
                   support_scale=grant_m / base.plant.support_max_eur_m
                   ).with_plant(capex_eur_m=capex, build_years=int(round(build)))


def sobol(base: Case, T: int, n: int = 2048, seed: int = 7
          ) -> dict[str, tuple[float, float]]:
    """First-order and total Sobol indices of NPV(T) over :data:`SOBOL_RANGES`.

    Saltelli sampling with the Jansen total-effect and Saltelli (2010)
    first-order estimators. Returns {input: (S_i, S_Ti)}.
    """
    rng = random.Random(seed)
    names = list(SOBOL_RANGES)

    def draw() -> list[float]:
        return [lo + (hi - lo) * rng.random() for lo, hi in SOBOL_RANGES.values()]

    def f(v: Sequence[float]) -> float:
        return npv(T, _apply(base, v))

    A = [draw() for _ in range(n)]
    Bm = [draw() for _ in range(n)]
    fA = [f(a) for a in A]
    fB = [f(b) for b in Bm]
    mean = (sum(fA) + sum(fB)) / (2 * n)
    var = sum((y - mean) ** 2 for y in fA + fB) / (2 * n - 1)
    out = {}
    for i, name in enumerate(names):
        fAB = [f(A[j][:i] + [Bm[j][i]] + A[j][i + 1:]) for j in range(n)]
        first = sum(fB[j] * (fAB[j] - fA[j]) for j in range(n)) / n / var
        total = sum((fA[j] - fAB[j]) ** 2 for j in range(n)) / (2 * n) / var
        out[name] = (first, total)
    return out


# ---------------------------------------------------------------- reporting

#: The three scenarios the article names. Each is a carbon price path with the
#: rulebook it belongs to: the pre-reform outlook was formed under current law;
#: the central path already prices in the July 2026 proposal, and so does the
#: stall, which is a stress test on the central world.
SCENARIOS: Final[Mapping[str, Case]] = {
    "Pre-reform outlook": Case(path="high", rulebook="law2023"),
    "Central (RaboResearch working path)": Case(path="central", rulebook="com2026"),
    "Price stall": Case(path="stall", rulebook="com2026"),
}
CENTRAL: Final[Case] = SCENARIOS["Central (RaboResearch working path)"]

#: Hydrogen reference points (EUR/kg), ACER European hydrogen markets 2025
#: monitoring report: conventional SMR hydrogen a little over 2.00, abated
#: (CCS) 2.80, renewable about 8 (range 7-10) in 2025.
H2_CONVENTIONAL: Final[float] = 2.00
H2_ABATED: Final[float] = 2.80
H2_RENEWABLE: Final[float] = 8.00


def eur(x: float) -> str:
    """EUR m -> 'EUR 1.6bn' / 'EUR 450m'."""
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1000.0:
        return f"{sign}EUR {x / 1000.0:.1f}bn"
    return f"{sign}EUR {x:,.0f}m"


def article_numbers() -> dict[str, object]:
    """Every number the article quotes, computed once. Keys are stable."""
    out: dict[str, object] = {}
    c = CENTRAL
    out["opex_at_reference_h2"] = extra_opex(c)
    out["opex_per_eur_kg"] = c.plant.h2_kt
    for name, sc in SCENARIOS.items():
        bill = do_nothing_bill(sc)
        cv = carbon_value(sc)
        curve = npv_curve(sc)
        ts = t_star(sc)
        T = ts or 2029
        pb = payback(T, sc)
        out[name] = {
            "bill_2026": bill[2026], "bill_2030": bill[2030], "bill_2035": bill[2035],
            "bill_2038": bill[2038], "bill_pv": pv(bill, sc.r),
            "carbon_value_2026": cv[2026], "carbon_value_2035": cv[2035],
            "carbon_value_pv": pv(cv, sc.r),
            "t_star": ts, "npv_star": max(curve.values()), "npv_2029": curve[2029],
            "curve": curve, "peak_funding": pb.peak_funding, "peak_year": pb.peak_year,
            "payback_year": pb.payback_year,
            "recovered_share_2029": curve[2029] / pv(bill, sc.r),
        }
    for rb in RULEBOOKS:
        out[f"bill_pv_central_{rb}"] = pv(do_nothing_bill(replace(c, rulebook=rb)), c.r)
    out["marginal_central"] = marginal_value(c)
    out["waterfall_central_2029"] = waterfall(2029, c)
    out["break_even_2029"] = break_even(2029, c)
    out["break_even_2029_lost_law"] = break_even(
        2029, replace(c, allocation_after_switch="lost", rulebook="law2023"))
    out["break_even_2029_lost_com"] = break_even(
        2029, replace(c, allocation_after_switch="lost", rulebook="com2026"))
    out["break_even_2029_renewable_h2"] = break_even(2029, replace(c, p_h2=H2_RENEWABLE))
    out["h2_break_even_2029_central"] = h2_break_even(2029, c)
    out["h2_break_even_2028_high"] = h2_break_even(2028, SCENARIOS["Pre-reform outlook"])
    val, trig = lattice(c)
    res = lsm(c)
    prices = price_path(c)
    out["option_value_lattice"] = val
    out["option_value_lsm"] = res.value
    out["static_best"] = res.static_best
    out["flexibility"] = res.flexibility
    out["commit_share_2028_2031"] = sum(res.exercise[T] for T in range(2028, 2032))
    out["commit_never"] = res.never
    out["commit_median"] = res.quantile_year(0.5)
    out["exercise"] = res.exercise
    out["trigger_eur"] = {T: x * prices[T] for T, x in trig.items() if math.isfinite(x)}
    out["path_eur"] = {T: prices[T] for T in trig}
    out["trigger_by_sigma_2029"] = {
        s_: lattice(replace(c, sigma=s_))[1][2029] * prices[2029]
        for s_ in (0.10, 0.20, 0.30, 0.45)}
    out["constant_trigger_2029"] = {
        s_: constant_price_trigger(2029, replace(c, sigma=s_))
        for s_ in (0.10, 0.20, 0.30, 0.45)}
    out["never_by_sigma"] = {s_: lsm(replace(c, sigma=s_), n_paths=10000).never
                             for s_ in (0.10, 0.20, 0.30, 0.45)}
    shocks = []
    ts0 = t_star(c)
    v0 = max(npv_curve(c).values())
    for s_ in one_at_a_time(c):
        cur = npv_curve(s_.case)
        shocks.append((s_.label, s_.group, max(cur.values()) - v0, ts0, t_star(s_.case)))
    out["one_at_a_time"] = shocks
    rows = sweep_81()
    viable = [r for r in rows if r.t_star is not None]
    out["sweep_viable"] = len(viable)
    out["sweep_t_star_range"] = (min(r.t_star for r in viable), max(r.t_star for r in viable))
    out["sweep_npv_range"] = (min(r.npv_star for r in viable), max(r.npv_star for r in viable))
    out["sweep_viable_by_h2"] = {h: sum(1 for r in viable if r.p_h2 == h) for h in SWEEP_H2}
    out["sweep_viable_by_path"] = {pa: sum(1 for r in viable if r.path == pa) for pa in PATHS}
    out["sweep_rows"] = rows
    out["sobol_2029"] = sobol(c, 2029)
    ccfd = {}
    for k in (110.0, 120.0, 130.0):
        cc = replace(c, ccfd_strike=k)
        v, _tr = lattice(cc)
        r_ = lsm(cc, n_paths=10000)
        ccfd[k] = {"t_star": t_star(cc), "npv_star": max(npv_curve(cc).values()),
                   "option": v, "commit_2028": r_.exercise.get(2028, 0.0),
                   "never": r_.never, "net_payment": ccfd_net_payment(cc)}
    out["ccfd"] = ccfd
    return out


def report(print_: Callable[[str], None] = print) -> None:  # pragma: no cover - prose
    """Print every number the article quotes."""
    p = print_
    n = article_numbers()
    c = CENTRAL
    pl = c.plant
    p("The article's reference plant, re-run\n" + "=" * 78)
    p(f"  {pl.capacity_mt} Mt/yr H2-DRI-EAF, {pl.co2_avoided_mt} MtCO2/yr avoided, "
      f"{pl.h2_kt:.0f} kt H2/yr, capex {eur(pl.capex_eur_m)} over {pl.build_years} yr")
    p(f"  2026 euros, r = {c.r:.0%}, inflation {c.inflation:.0%}, horizon {HORIZON}; "
      f"extra opex at EUR {c.p_h2:.2f}/kg = {eur(n['opex_at_reference_h2'])}/yr "
      f"(+EUR {n['opex_per_eur_kg']:.0f}m per EUR 1/kg)\n")

    p("1. Price paths, 2026 euros (EUR/t)")
    for path in PATHS:
        pp = price_path(Case(path=path))
        p(f"   {path:<8}" + "".join(f"{y}:{pp[y]:6.1f}  "
                                    for y in (2026, 2030, 2035, 2040, 2050)))

    p("\n2. The cost of doing nothing")
    for name in SCENARIOS:
        d = n[name]
        p(f"   {name:<38} cash bill {eur(d['bill_2026'])} (2026) -> {eur(d['bill_2030'])}"
          f" (2030) -> {eur(d['bill_2035'])} (2035); PV {eur(d['bill_pv'])}; carbon value"
          f" {eur(d['carbon_value_2026'])} -> {eur(d['carbon_value_2035'])}, PV "
          f"{eur(d['carbon_value_pv'])}")
    p(f"   central path: bill PV {eur(n['bill_pv_central_law2023'])} under current law, "
      f"{eur(n['bill_pv_central_com2026'])} under the July 2026 proposal")

    p("\n3. NPV by FID year, best year, payback")
    for name in SCENARIOS:
        d = n[name]
        p(f"   {name:<38} T* {d['t_star']}  NPV* {eur(d['npv_star'])}  NPV(2029) "
          f"{eur(d['npv_2029'])}  peak {eur(d['peak_funding'])} in {d['peak_year']}, "
          f"payback {d['payback_year']}, recovered {d['recovered_share_2029']:.0%}")
        p("      " + " ".join(f"{T}:{v:6.0f}" for T, v in d["curve"].items() if T <= 2036))
    p("   marginal value of waiting (central): "
      + " ".join(f"{T}:{v:+.0f}" for T, v in n["marginal_central"].items() if T <= 2035))

    p("\n4. Waterfall, central, FID 2029")
    for k, v in n["waterfall_central_2029"].items():
        p(f"   {k:<24}{eur(v):>12}")

    p("\n5. Break-even (constant 2026-euro price, FID 2029)")
    p(f"   allocation retained {n['break_even_2029']:.1f}; lost, current law "
      f"{n['break_even_2029_lost_law']:.1f}; lost, July 2026 proposal "
      f"{n['break_even_2029_lost_com']:.1f}; with renewable H2 at EUR {H2_RENEWABLE:.0f}/kg "
      f"{n['break_even_2029_renewable_h2']:.0f}")
    p(f"   hydrogen break-even: central FID 2029 EUR {n['h2_break_even_2029_central']:.2f}/kg;"
      f" pre-reform FID 2028 EUR {n['h2_break_even_2028_high']:.2f}/kg")

    p("\n6. Option layer (sigma 20%)")
    p(f"   value: lattice {eur(n['option_value_lattice'])}, LSM {eur(n['option_value_lsm'])};"
      f" static {eur(n['static_best'])}; flexibility {eur(n['flexibility'])}")
    p(f"   commit 2028-31 {n['commit_share_2028_2031']:.0%}, never {n['commit_never']:.0%},"
      f" median {n['commit_median']}")
    p("   trigger vs path (EUR/t): " + " ".join(
        f"{T}:{n['trigger_eur'][T]:.0f}/{n['path_eur'][T]:.0f}"
        for T in sorted(n['trigger_eur']) if T <= 2035))
    p(f"   constant-price break-even (FID 2029) {n['break_even_2029']:.0f}; trigger by sigma: "
      + " ".join(f"{s_:.2f}:{v:.0f}" for s_, v in n["constant_trigger_2029"].items()))
    p("   FID-year trigger on the central path, 2029, by sigma: " + " ".join(
        f"{s_:.2f}:{v:.0f}" for s_, v in n["trigger_by_sigma_2029"].items())
      + " | never: " + " ".join(f"{s_:.2f}:{v:.0%}" for s_, v in n["never_by_sigma"].items()))

    p("\n7. One change at a time (central)")
    for label, group, dv, t0_, t1_ in n["one_at_a_time"]:
        p(f"   {label:<36}{group:<16} value {dv:+7.0f}  best year {t0_} -> {t1_}")

    p("\n8. 81-scenario sweep")
    p(f"   viable {n['sweep_viable']}/81; best year {n['sweep_t_star_range']}; value "
      f"{eur(n['sweep_npv_range'][0])} to {eur(n['sweep_npv_range'][1])}")
    p(f"   viable by hydrogen {n['sweep_viable_by_h2']}; by path {n['sweep_viable_by_path']}")
    p("   Sobol (NPV, FID 2029): " + "; ".join(
        f"{k} {v[0]:.2f}/{v[1]:.2f}" for k, v in n["sobol_2029"].items()))

    p("\n9. Carbon CfD, 15 years from first steel (central)")
    for k, d in n["ccfd"].items():
        p(f"   strike {k:.0f}: best year {d['t_star']} NPV {eur(d['npv_star'])}; option "
          f"{eur(d['option'])}; commit 2028 {d['commit_2028']:.0%}, never {d['never']:.0%}; "
          f"net state payment {eur(d['net_payment'])}")


def export(path: str) -> None:  # pragma: no cover - writes a file
    """Write every series the article's figures draw, as JSON."""
    import json

    n = article_numbers()
    c = CENTRAL
    data = {
        "allocation_paid": {rb: {t: payable_share(t, rb) for t in range(T0, 2041)}
                            for rb in RULEBOOKS},
        "prices_real": {pa: price_path(Case(path=pa)) for pa in PATHS},
        "prices_nominal": {pa: nominal_path(pa) for pa in ("central", "high")},
        "bills": {name: do_nothing_bill(sc) for name, sc in SCENARIOS.items()},
        "carbon_value": {name: carbon_value(sc) for name, sc in SCENARIOS.items()},
        "curves": {name: npv_curve(sc) for name, sc in SCENARIOS.items()},
        "waterfall": n["waterfall_central_2029"],
        "break_even_2029": n["break_even_2029"],
        "constant_trigger_2029": n["constant_trigger_2029"],
        "trigger_eur": n["trigger_eur"],
        "exercise": n["exercise"],
        "one_at_a_time": n["one_at_a_time"],
        "sweep_marginal": [
            {"path": r.path, "p_h2": r.p_h2, "capex": r.capex, "r": r.r,
             "t_star": r.t_star, "npv_star": r.npv_star, "marginal": r.marginal}
            for r in n["sweep_rows"]],
        "ccfd": n["ccfd"],
        "sobol": n["sobol_2029"],
        "irr_central_2029": irr(2029, c),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, default=str)


def main() -> int:  # pragma: no cover - entry point
    report()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
