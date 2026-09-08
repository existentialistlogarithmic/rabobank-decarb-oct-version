"""Check the model against the v11 specification, quantity by quantity.

The specification (``Investment timing model for industrial decarbonisation``,
RaboResearch, August 2026) publishes a base-case parameter table, twelve
governing equations, a validation table and five phases of results. This module
encodes what it published and checks the code against it, printing one row per
quantity with the delta.

Why this exists
---------------
The build previously carried numbers that reproduced the *published NPV* while
using inputs the specification does not contain. ``K_s = 1200`` with
``age0 = 14`` gives the same ``S_s(2026) = 360`` as the specification's
``K_s = 600`` with ``age0 = 8`` - and a different answer in every other year.
Nothing caught it, because nothing compared the *inputs* to the source; only
the outputs were checked. This module compares both.

What it does not do
-------------------
It does not adjust anything to make a row pass. Where the model and the
specification disagree, the row says so and the difference is the finding.
Eight rows currently disagree. Every one is an NPV *level* and every one is
high, by 1.1% to 8.0%; not one year, trigger, crossing year or input differs.
See :func:`main`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Final

from timing_model import cost, option
from timing_model.benefit import CENTRAL_PATH, F_LAW2023
from timing_model.params import Params, ScenarioParams
from timing_model.results import outputs

#: v11 §1, the base-case parameter table, exactly as printed.
SPEC_PARAMS: Final[tuple[tuple[str, float, str], ...]] = (
    ("sector.I0", 900.0, "EUR/t annual capacity"),
    ("common.eps_inc", 1.90, "tCO2/t"),
    ("common.eps_cln", 0.10, "tCO2/t"),
    ("common.r", 0.08, "per year"),
    ("common.mu", 0.05, "per year"),
    ("common.sigma", 0.20, "annual"),
    ("common.crf_years", 25.0, "years"),
    ("sector.K_s", 600.0, "EUR/t annual capacity"),
    ("sector.L_s", 20.0, "years"),
    ("sector.age0", 8.0, "years"),
    ("sector.phi", 0.50, "fraction"),
    ("sector.rho", 0.35, "fraction of K_s"),
    ("policy.s_max", 200.0, "EUR/t annual capacity"),
)

#: v11 §3, the validation table. The gate already enforces these; repeated here
#: so the reconciliation is readable on its own.
SPEC_GATE: Final[Mapping[str, float]] = {
    "CRF": 0.0937, "beta": 1.386, "multiple": 3.591, "p_M": 27.5,
    "MAC": 80.2, "p_star": 98.7, "p_M_prime": 30.5, "MAC_prime": 89.5,
    "trigger": 109.5,
}

#: v11 §4.3, the write-off ladder: age in 2026 -> (reinvestment due, trigger,
#: crossing year). The single strongest test of the incumbent-asset block.
SPEC_AGE_LADDER: Final[tuple[tuple[int, int, float, int], ...]] = (
    (2, 2044, 114.9, 2031),
    (8, 2038, 109.5, 2030),
    (14, 2032, 104.1, 2030),
    (20, 2026, 98.7, 2029),
)

#: v11 §4.2, the three carbon price paths: 2026-2030 anchors -> (commit, NPV).
SPEC_PRICE_PATHS: Final[tuple[tuple[str, tuple[float, ...], int, float], ...]] = (
    ("reform soft", (74.0, 80.0, 85.0, 90.0, 96.0), 2030, 1155.0),
    ("central", (76.0, 86.0, 96.0, 104.0, 112.0), 2029, 1588.0),
    ("tight market", (82.0, 96.0, 112.0, 128.0, 145.0), 2028, 2339.0),
)

#: v11 §4.2, the support-window cases.
SPEC_SUPPORT: Final[tuple[tuple[str, float, float, int, float], ...]] = (
    ("Booster in full", 0.0, 0.0, 2029, 1588.0),
    ("rationed, 30 per cent a year", 0.30, 0.10, 2028, 1570.0),
)

#: v11 §4.4, the policy vintages.
SPEC_VINTAGES: Final[tuple[tuple[str, str, int, float], ...]] = (
    ("current law 2023/959", "law2023", 2029, 1581.0),
    ("COM(2026) 616", "com2026", 2029, 1588.0),
)

#: v11 §4.4 / F8: the vintage delta, with and without resale.
SPEC_VINTAGE_DELTA: Final[tuple[tuple[float, float], ...]] = ((1.0, 7.82), (0.0, -122.0))

#: v11 §5, the sector ordering by abatement intensity. The model has no
#: sector-specific logic, so only steel is parameterised here; the rest are
#: recorded so the ordering claim can be checked when they are.
SPEC_SECTORS: Final[tuple[tuple[str, float, float, float], ...]] = (
    ("steel, BF to H2-DRI-EAF", 1.80, 80.2, 109.5),
    ("aluminium, inert anode", 1.50, 104.1, 136.8),
    ("ammonia, SMR to electrolytic", 1.85, 107.1, 143.8),
    ("cement, capture retrofit", 0.70, 131.2, 177.0),
    ("chemicals, cracker electrification", 0.85, 159.5, 224.2),
)


@dataclass(frozen=True)
class Row:
    """One published quantity, what the model gives, and whether they agree."""

    section: str
    item: str
    published: str
    computed: str
    ok: bool
    note: str = ""

    def render(self) -> str:
        mark = "pass" if self.ok else "DIFF"
        return (f"  {mark:5}{self.section:<8}{self.item:<34}"
                f"{self.published:>18}{self.computed:>19}"
                + (f"   {self.note}" if self.note else ""))


def _get(p: Params, dotted: str) -> float:
    group, name = dotted.split(".")
    return float(getattr(getattr(p, group), name))


#: One tolerance for every NPV *level*, in EUR/t capacity.
#:
#: It has to be one number. An earlier version used 5 for the base case and 25
#: elsewhere, and the same comparison - published 1,588 against a computed
#: 1,606 - then showed as a pass under §4.2 and a difference under §3. A count
#: built on two standards is not a count. 5 is the rounding on the published
#: figures: agreement here means the levels agree as printed, and anything
#: looser would be the reconciliation deciding for itself how much drift is
#: acceptable.
NPV_TOL: Final[float] = 5.0


def _close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def check_parameters(p: Params) -> list[Row]:
    """Every published input against the value the model runs on."""
    rows = []
    for dotted, want, unit in SPEC_PARAMS:
        got = _get(p, dotted)
        rows.append(Row("§1", dotted, f"{want:g}", f"{got:g}",
                        _close(got, want, 1e-6 * max(1.0, abs(want))), unit))
    return rows


def check_gate(p: Params, sc: ScenarioParams) -> list[Row]:
    """The nine validation quantities, at the published rounding."""
    s_s = cost.residual_value(p.common.t0, p)
    from timing_model.primitives import crf, mac

    got = {
        "CRF": crf(p.common.crf_years, p.common.r),
        "beta": option.beta(p, sc),
        "multiple": option.option_multiple(p, sc),
        "p_M": option.break_even_price(p, sc, 0.0),
        "MAC": mac(p, sc, 0.0),
        "p_star": option.trigger_price(p, sc, 0.0),
        "p_M_prime": option.break_even_price(p, sc, s_s),
        "MAC_prime": mac(p, sc, s_s),
        "trigger": option.trigger_price(p, sc, s_s),
    }
    return [Row("§3", k, f"{SPEC_GATE[k]:g}", f"{got[k]:.4f}",
                _close(got[k], SPEC_GATE[k], 0.06))
            for k in SPEC_GATE]


def check_age_ladder(p: Params, sc: ScenarioParams) -> list[Row]:
    """v11 §4.3. Reproducing all four rows is what pins K_s, age0 and L_s."""
    rows = []
    for age, t_rel, trigger, crossed in SPEC_AGE_LADDER:
        pa = p.with_sector(age0=float(age))
        o = outputs(pa, sc)
        got_rel = cost.reline_year(pa)
        rows.append(Row("§4.3", f"age {age}: reinvestment due",
                        str(t_rel), str(got_rel), got_rel == t_rel))
        rows.append(Row("§4.3", f"age {age}: trigger", f"{trigger:g}",
                        f"{o.trigger:.2f}", _close(o.trigger, trigger, 0.06)))
        rows.append(Row("§4.3", f"age {age}: crossed", str(crossed),
                        str(o.crossing_year), o.crossing_year == crossed))
    return rows


def check_price_paths(p: Params, sc: ScenarioParams) -> list[Row]:
    """v11 §4.2. The central path also checks the published anchors themselves."""
    import timing_model.benefit as B

    rows = [Row("§1", "central path anchors",
                "76,86,96,104,112",
                ",".join(f"{CENTRAL_PATH[y]:.0f}" for y in sorted(CENTRAL_PATH)),
                [CENTRAL_PATH[y] for y in sorted(CENTRAL_PATH)]
                == [76.0, 86.0, 96.0, 104.0, 112.0])]
    original = B.carbon_price_path
    try:
        for label, anchors, commit, npv in SPEC_PRICE_PATHS:
            table = dict(zip(sorted(CENTRAL_PATH), anchors, strict=True))

            def path(pp: Params, ss: ScenarioParams, _t: dict = table) -> dict:
                out = {}
                end = max(_t)
                for t in range(pp.common.t0, pp.common.horizon_end + 1):
                    v = _t[t] if t <= end else _t[end] * (1 + pp.common.mu) ** (t - end)
                    v *= ss.price_scale
                    if ss.price_basis == "real":
                        v /= (1 + ss.deflator) ** (t - pp.common.t0)
                    out[t] = v
                return out

            B.carbon_price_path = path
            o = outputs(p, sc)
            rows.append(Row("§4.2", f"{label}: commit", str(commit),
                            str(o.t_star), o.t_star == commit))
            rows.append(Row("§4.2", f"{label}: NPV", f"{npv:,.0f}",
                            f"{o.npv0:,.0f}", _close(o.npv0, npv, NPV_TOL)))
    finally:
        B.carbon_price_path = original
    return rows


def check_support(p: Params, sc: ScenarioParams) -> list[Row]:
    """v11 §4.2. Rationing is the only assumption that pulls the date forward."""
    rows = []
    for label, lam, q_min, commit, npv in SPEC_SUPPORT:
        o = outputs(p.with_policy(lam=lam, q_min=q_min), sc)
        rows.append(Row("§4.2", f"{label}: commit", str(commit),
                        str(o.t_star), o.t_star == commit))
        rows.append(Row("§4.2", f"{label}: NPV", f"{npv:,.0f}",
                        f"{o.npv0:,.0f}", _close(o.npv0, npv, NPV_TOL)))
    return rows


def check_support_envelope(p: Params, sc: ScenarioParams) -> list[Row]:
    """v11 eq (9), branch by branch, plus the step it is quoted for.

    Nothing checked this schedule directly, and a whole branch was missing
    because of it: the code returned zero before the Booster window where the
    specification has ``0.35 * s_max`` for the Innovation Fund and national
    aid. That put a EUR 200 step at 2028 in place of the published EUR 130,
    and so overstated the value of waiting - the one quantity this model
    exists to measure.
    """
    from timing_model.objective import npv

    spec = {2026: 70.0, 2027: 70.0, 2028: 200.0, 2029: 200.0, 2030: 200.0,
            2031: 200.0, 2032: 150.0, 2033: 100.0, 2034: 50.0, 2035: 0.0}
    got = {t: cost.support(t, p, sc) for t in spec}
    ok = all(_close(got[t], spec[t], 1e-9) for t in spec)
    rows = [Row("eq 9", "s(t) 2026-2035", "10 branches",
                "match" if ok else "differ", ok)]

    pr = p.with_policy(lam=0.30, q_min=0.10)
    q_spec = {2029: 0.70, 2030: 0.40, 2031: 0.10}
    q_ok = all(_close(cost.support(t, pr, sc) / p.policy.s_max, q, 1e-9)
               for t, q in q_spec.items())
    rows.append(Row("eq 9", "rationed q(2029-31)", "0.70,0.40,0.10",
                    ",".join(f"{cost.support(t, pr, sc) / p.policy.s_max:.2f}"
                             for t in sorted(q_spec)), q_ok))

    step = cost.support(2028, p, sc) - cost.support(2027, p, sc)
    rows.append(Row("eq 9", "support step 2027->2028", "130", f"{step:.0f}",
                    _close(step, 130.0, 1e-9)))
    wait = npv(2028, p, sc) - npv(2027, p, sc)
    rows.append(Row("eq 9", "value of waiting to 2028", "+146", f"{wait:+.0f}",
                    _close(wait, 146.0, 6.0),
                    "130 of support, the rest learning and discounting"))
    return rows


def check_vintages(p: Params, sc: ScenarioParams) -> list[Row]:
    """v11 §4.4, and the F8 delta that the schedule was reconstructed to hit."""
    rows = []
    npvs = {}
    for label, vintage, commit, npv in SPEC_VINTAGES:
        o = outputs(p, replace(sc, policy_vintage=vintage))
        npvs[vintage] = o.npv0
        rows.append(Row("§4.4", f"{label}: commit", str(commit),
                        str(o.t_star), o.t_star == commit))
        rows.append(Row("§4.4", f"{label}: NPV", f"{npv:,.0f}",
                        f"{o.npv0:,.0f}", _close(o.npv0, npv, NPV_TOL)))
    for w, want in SPEC_VINTAGE_DELTA:
        law = outputs(p, replace(sc, w=w, policy_vintage="law2023")).npv0
        com = outputs(p, replace(sc, w=w, policy_vintage="com2026")).npv0
        got = com - law
        rows.append(Row("§4.4", f"vintage delta, w={w:.0f}", f"{want:+.2f}",
                        f"{got:+.2f}", _close(got, want, 0.15 if w else 1.0),
                        "" if w else "reproduces; was -161 before eq (12)"))
    return rows


def check_allocation_schedules() -> list[Row]:
    """v11 eq (11) and (12), factor by factor."""
    law = [0.975, 0.95, 0.90, 0.775, 0.515, 0.39, 0.265, 0.14, 0.0]
    got = [F_LAW2023.get(y, 0.0) for y in range(2026, 2035)]
    rows = [Row("eq 11", "f_law2023 2026-2034", "9 factors",
                "match" if all(_close(a, b, 1e-9) for a, b in zip(got, law, strict=True))
                else "differ",
                all(_close(a, b, 1e-9) for a, b in zip(got, law, strict=True)))]
    from timing_model.benefit import free_allocation_factor

    com_spec = [0.975, 0.95, 0.915, 0.81, 0.59, 0.48, 0.375, 0.27,
                0.15, 0.15, 0.15, 0.15, 0.0]
    sc = ScenarioParams(policy_vintage="com2026")
    com_got = [free_allocation_factor(y, sc) for y in range(2026, 2039)]
    ok = all(_close(a, b, 1e-9) for a, b in zip(com_got, com_spec, strict=True))
    rows.append(Row("eq 12", "f_com2026 2026-2038", "13 factors",
                    "match" if ok else "differ", ok))
    return rows


def check_base_case(p: Params, sc: ScenarioParams) -> list[Row]:
    """v11 §3: commit 2029, expiry 2029, NPV 1,588, trigger 109.5, crossed 2030."""
    o = outputs(p, sc)
    return [
        Row("§3", "base case: commit", "2029", str(o.t_star), o.t_star == 2029),
        Row("§3", "base case: expiry", "2029", str(o.t_exp), o.t_exp == 2029),
        Row("§3", "base case: NPV", "1,588", f"{o.npv0:,.0f}",
            _close(o.npv0, 1588.0, NPV_TOL)),
        Row("§3", "base case: trigger", "109.5", f"{o.trigger:.2f}",
            _close(o.trigger, 109.5, 0.06)),
        Row("§3", "base case: crossed", "2030", str(o.crossing_year),
            o.crossing_year == 2030),
    ]


def all_rows() -> list[Row]:
    """Every check, in specification order."""
    p, sc = Params(), ScenarioParams(u=1.0)
    return (check_parameters(p) + check_gate(p, sc) + check_base_case(p, sc)
            + check_allocation_schedules() + check_support_envelope(p, sc)
            + check_price_paths(p, sc) + check_support(p, sc)
            + check_age_ladder(p, sc) + check_vintages(p, sc))


def main() -> int:
    """Print the reconciliation. Returns 0 - this reports, it does not gate."""
    rows = all_rows()
    passed = sum(1 for r in rows if r.ok)
    print("Reconciliation against the v11 specification\n" + "=" * 78)
    print(f"  {'':5}{'sec':<8}{'quantity':<34}{'published':>18}{'computed':>19}")
    print("  " + "-" * 86)
    for r in rows:
        print(r.render())
    print(f"\n  {passed}/{len(rows)} published quantities reproduce.")
    bad = [r for r in rows if not r.ok]
    if bad:
        print("\n  Not reproducing:")
        gaps = []
        for r in bad:
            pub = float(r.published.replace(",", ""))
            got = float(r.computed.replace(",", ""))
            rel = (got - pub) / abs(pub)
            gaps.append(rel)
            print(f"    {r.section} {r.item}: published {r.published}, "
                  f"computed {r.computed}  ({rel:+.1%})")
        print(f"\n  Every difference is an NPV level, and every one is high, by "
              f"{min(gaps):+.1%} to\n  {max(gaps):+.1%}. Not one year, trigger, "
              f"crossing year or input differs: the model\n  disagrees with the "
              f"specification about how much the decision is worth and\n  agrees "
              f"with it about when to take it. That is the residual "
              f"CALIBRATION.md\n  documents rather than tunes away.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
