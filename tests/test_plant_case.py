"""The article's reference plant: identities, corrections and pinned headlines.

Three kinds of test. Identities that must hold whatever the inputs (NPV is the
discounted cash flow, prices enter linearly, the waterfall sums). Corrections
that the review asked for and that must not silently revert (allocation kept
after a switch, real prices, one hydrogen intensity, the FID-year support
window). And the headline numbers the article quotes, so a change to any input
fails here before it reaches a page.
"""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from analysis import plant_case as pc

C = pc.CENTRAL


# ------------------------------------------------------------------ identities


def test_npv_is_the_discounted_cash_flow() -> None:
    for T in (2026, 2029, 2034, 2035):
        flows = pc.cash_flows(T, C)
        assert pc.npv(T, C) == pytest.approx(
            sum(v / 1.08 ** (t - 2026) for t, v in flows.items()), rel=1e-12)


def test_waterfall_sums_to_npv() -> None:
    for T in (2028, 2029, 2033, 2036):
        w = pc.waterfall(T, C)
        assert w["NPV"] == pytest.approx(pc.npv(T, C), abs=1e-6)


@pytest.mark.parametrize("x", [0.0, 0.37, 1.0, 1.9])
def test_prices_enter_linearly(x: float) -> None:
    """The option layer relies on NPV(T; x) = a + b x exactly."""
    a, b = pc.linear_in_x(2030, C)
    assert pc.npv(2030, C, x) == pytest.approx(a + b * x, rel=1e-12, abs=1e-9)


def test_break_even_zeroes_the_npv() -> None:
    for T in (2026, 2029, 2032):
        be = pc.break_even(T, C)
        flat = replace(C, path="stall", price_scale=be / pc.STALL_REAL)
        assert pc.npv(T, flat) == pytest.approx(0.0, abs=1e-6)


def test_hydrogen_break_even_zeroes_the_npv() -> None:
    h = pc.h2_break_even(2029, C)
    assert pc.npv(2029, replace(C, p_h2=h)) == pytest.approx(0.0, abs=1e-6)


def test_capex_pv_for_a_2029_decision() -> None:
    """EUR 750m a year over 2029-2032, discounted at 8% to 2026: EUR 2.13bn."""
    w = pc.waterfall(2029, C)
    assert -w["capex"] == pytest.approx(750 * sum(1.08 ** -k for k in range(3, 7)))
    assert -w["capex"] == pytest.approx(2129.7, abs=0.1)


# ----------------------------------------------------------------- corrections


def test_prices_are_deflated_to_2026_euros() -> None:
    """The draft discounted at 8% real against nominal analyst prices."""
    real = pc.price_path(C)
    assert real[2030] == pytest.approx(112.0 / 1.02 ** 4)
    assert pc.nominal_path("high")[2030] == pytest.approx(138.0)
    assert pc.nominal_path("high")[2035] == pytest.approx(191.0)


def test_one_hydrogen_intensity_drives_the_opex() -> None:
    """EUR 143m per EUR 1/kg and the level at EUR 2.60 come from the same 143 kt."""
    lo = pc.extra_opex(replace(C, p_h2=2.60))
    hi = pc.extra_opex(replace(C, p_h2=3.60))
    assert hi - lo == pytest.approx(143.0)
    assert lo == pytest.approx(143.0 * 2.60 - 207.5)


def test_retained_allocation_makes_the_rulebook_irrelevant_to_the_switch() -> None:
    """With a technology-neutral benchmark the switch is worth E x P whatever f(t) is."""
    for T in (2027, 2029, 2033):
        law = pc.npv(T, replace(C, rulebook="law2023"))
        com = pc.npv(T, replace(C, rulebook="com2026"))
        assert law == pytest.approx(com, abs=1e-9)


def test_lost_allocation_makes_the_proposal_cost_the_switch_value() -> None:
    lost = replace(C, allocation_after_switch="lost")
    law = pc.npv(2029, replace(lost, rulebook="law2023"))
    com = pc.npv(2029, replace(lost, rulebook="com2026"))
    assert com < law < pc.npv(2029, C)


def test_proposal_schedule_is_the_repository_schedule() -> None:
    """15% of the phased-out allocation back from 2028, 15% held to 2037, none in 2038."""
    assert pc.payable_share(2030, "law2023") == pytest.approx(0.485)
    assert pc.payable_share(2030, "com2026") == pytest.approx(0.41)
    for t in range(2034, 2038):
        assert pc.payable_share(t, "com2026") == pytest.approx(0.85)
    assert pc.payable_share(2038, "com2026") == pytest.approx(1.0)


def test_support_follows_the_decision_year() -> None:
    assert pc.grant(2027, C) == pytest.approx(175.0)
    assert pc.grant(2029, C) == pytest.approx(500.0)
    assert pc.grant(2033, C) == pytest.approx(250.0)
    assert pc.grant(2035, C) == 0.0


def test_reline_is_avoided_only_if_first_steel_comes_first() -> None:
    assert pc.waterfall(2034, C)["reline avoided"] > 0.0
    assert pc.waterfall(2035, C)["reline avoided"] == 0.0


# ----------------------------------------------------------------- option layer


def test_lsm_agrees_with_the_exact_lattice() -> None:
    exact, _ = pc.lattice(C)
    sim = pc.lsm(C, n_paths=20000)
    assert sim.value == pytest.approx(exact, rel=0.03)


def test_trigger_sits_above_break_even() -> None:
    """Break-even is a floor, not the trigger."""
    _, trig = pc.lattice(C)
    for T in (2028, 2029, 2030):
        a, b = pc.linear_in_x(T, C)
        assert trig[T] > -a / b


def test_volatility_raises_the_trigger() -> None:
    t = [pc.lattice(replace(C, sigma=s))[1][2029] for s in (0.10, 0.20, 0.30)]
    assert t[0] < t[1] < t[2]
    k = [pc.constant_price_trigger(2029, replace(C, sigma=s)) for s in (0.10, 0.20, 0.30)]
    assert pc.break_even(2029, C) < k[0] < k[1] < k[2]


def test_a_ccfd_at_the_path_removes_the_value_of_waiting() -> None:
    cc = replace(C, ccfd_strike=130.0)
    value, _ = pc.lattice(cc)
    static = max(pc.npv_curve(cc).values())
    assert value == pytest.approx(static, abs=5.0)


# ------------------------------------------------------- the article's numbers


def test_headline_scenarios() -> None:
    n = {name: (pc.t_star(c), max(pc.npv_curve(c).values()))
         for name, c in pc.SCENARIOS.items()}
    assert n["Pre-reform outlook"][0] == 2028
    assert n["Pre-reform outlook"][1] == pytest.approx(1369, abs=1)
    assert n["Central (RaboResearch working path)"][0] == 2029
    assert n["Central (RaboResearch working path)"][1] == pytest.approx(351, abs=1)
    assert n["Price stall"][0] is None


def test_the_cost_of_doing_nothing() -> None:
    bill = pc.do_nothing_bill(C)
    assert bill[2026] == pytest.approx(3.5 * 76.0 * 0.025)
    assert pc.pv(bill, 0.08) == pytest.approx(3100, abs=60)
    assert pc.pv(pc.carbon_value(C), 0.08) == pytest.approx(4700, abs=60)


def test_hydrogen_gate_is_about_three_euros() -> None:
    assert pc.h2_break_even(2029, C) == pytest.approx(3.0, abs=0.05)


def test_waiting_stops_paying_in_2029_on_the_central_path() -> None:
    mv = pc.marginal_value(C)
    assert mv[2027] > 0 and mv[2028] > -1.0
    assert all(mv[T] < 0 for T in range(2029, 2036))


def test_every_viable_sweep_scenario_commits_in_2028_to_2031() -> None:
    rows = pc.sweep_81()
    viable = [r for r in rows if r.t_star is not None]
    assert len(viable) == 25
    assert {r.t_star for r in viable} <= set(range(2028, 2032))


def test_peak_funding_is_the_same_in_every_scenario() -> None:
    for c in pc.SCENARIOS.values():
        assert pc.payback(2029, c).peak_funding == pytest.approx(-2500.0)


def test_central_irr_clears_the_hurdle() -> None:
    r = pc.irr(2029, C)
    assert r is not None and r > C.r and math.isclose(r, 0.101, abs_tol=0.002)


def test_numbers_quoted_in_draft_2() -> None:
    """Every further figure the October rewrite quotes, at the precision it quotes it."""
    from analysis.plant_case import H2_RENEWABLE, SCENARIOS

    hi, st = SCENARIOS["Pre-reform outlook"], SCENARIOS["Price stall"]
    bill_c, bill_h = pc.do_nothing_bill(C), pc.do_nothing_bill(hi)
    assert round(bill_c[2030], -1) == 150 and round(bill_c[2035], -1) == 360
    assert round(bill_h[2035], -1) == 560
    assert round(pc.pv(bill_h, 0.08) / 1000, 1) == 4.5
    assert round(pc.pv(pc.do_nothing_bill(st), 0.08) / 1000, 1) == 2.0
    law = pc.pv(pc.do_nothing_bill(replace(C, rulebook="law2023")), 0.08)
    assert round((law - pc.pv(bill_c, 0.08)) / 1000, 1) == 0.2
    cv = pc.carbon_value(C)
    assert round(cv[2026]) == 266 and round(cv[2035], -1) == 420

    w = pc.waterfall(2029, C)
    assert round(w["carbon value avoided"] / 1000, 1) == 2.8
    assert round(-w["extra operating cost"] / 1000, 1) == 1.0
    assert round(w["capex support"] / 1000, 1) == 0.4
    assert round(w["reline avoided"] / 1000, 1) == 0.2
    assert round(pc.npv(2029, hi) / 1000, 1) == 1.3
    assert round(pc.npv(2029, st) / 1000, 1) == -0.7
    assert [pc.payback(2029, c).payback_year for c in (hi, C, st)] == [2038, 2040, 2047]
    assert round(pc.break_even(2029, replace(C, p_h2=H2_RENEWABLE)), -1) == 340

    mv = pc.marginal_value(C)
    assert round(mv[2027] / 1000, 2) == 0.31 and round(-mv[2034] / 1000, 2) == 0.28
    curve = pc.npv_curve(C)
    assert max(curve.values()) - min(curve[T] for T in range(2028, 2032)) < 20

    trig = {s: pc.constant_price_trigger(2029, replace(C, sigma=s)) for s in (0.10, 0.20, 0.45)}
    assert round(pc.break_even(2029, C)) == 121
    assert round(trig[0.20]) == 153 and round(trig[0.10]) == 133 and round(trig[0.45]) == 220
    assert round(trig[0.20] / pc.break_even(2029, C) - 1, 2) in (0.26, 0.27)
    res = pc.lsm(C)
    assert round(res.never, 2) in (0.42, 0.43, 0.44)

    rows = pc.sweep_81()
    by_h2 = {h: sum(1 for r in rows if r.p_h2 == h and r.t_star) for h in pc.SWEEP_H2}
    assert by_h2 == {2.60: 16, 3.80: 8, 5.00: 1}
    assert not [r for r in rows if r.path == "stall" and r.t_star]

    lost_law = pc.npv(2029, replace(C, allocation_after_switch="lost", rulebook="law2023"))
    lost_com = pc.npv(2029, replace(C, allocation_after_switch="lost", rulebook="com2026"))
    assert round(lost_law / 1000, 2) == 0.32 and round(lost_com / 1000, 2) == 0.17


def test_ccfd_table() -> None:
    rows = {}
    for k in (110.0, 120.0, 130.0):
        cc = replace(C, ccfd_strike=k)
        sim = pc.lsm(cc, n_paths=10000)
        rows[k] = (pc.t_star(cc), max(pc.npv_curve(cc).values()), sim.exercise.get(2028, 0.0),
                   sim.never, pc.ccfd_net_payment(cc))
    assert rows[110.0][0] is None and round(rows[110.0][4] / 1000, 2) == -0.45
    assert rows[120.0][0] == 2028 and round(rows[120.0][1] / 1000, 2) == 0.15
    assert rows[130.0][0] == 2028 and abs(rows[130.0][4]) < 10
    assert rows[130.0][2] > 0.99 and rows[120.0][2] > 0.85 and rows[110.0][3] > 0.5
