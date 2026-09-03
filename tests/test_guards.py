"""Feasibility guards. Appendix A §3.6 - these stop the run, they do not warn."""

from __future__ import annotations

import pytest

from timing_model.benefit import free_allocation_factor
from timing_model.cost import residual_value, switching_cost
from timing_model.objective import t_exp, t_star
from timing_model.option import BEYOND_HORIZON, crossing_year
from timing_model.params import ModelError, Params, ScenarioParams
from timing_model.validate import check_currency_tags, run_gate, run_guards, validated


@pytest.fixture
def p() -> Params:
    return Params()


@pytest.fixture
def sc() -> ScenarioParams:
    return ScenarioParams(u=1.0)


def test_r_minus_mu_margin_raises(p: Params, sc: ScenarioParams) -> None:
    """r - mu < 0.005: p'_M changes sign; the inversion is undefined."""
    with pytest.raises(ModelError, match="r - mu"):
        run_guards(p.with_common(mu=0.0785), sc)


def test_r_minus_mu_just_inside_the_margin_is_accepted(p: Params, sc: ScenarioParams) -> None:
    run_guards(p.with_common(mu=0.075), sc)


def test_non_positive_sigma_raises(p: Params) -> None:
    """An empty regime falls back to CommonParams.sigma, which must be > 0."""
    with pytest.raises(ModelError, match="strictly positive"):
        run_guards(p.with_common(sigma=0.0), ScenarioParams(u=1.0, sigma_regime=""))


def test_unknown_sigma_regime_raises() -> None:
    with pytest.raises(ModelError, match="sigma_regime"):
        ScenarioParams(sigma_regime="made_up").resolved_sigma()


def test_discriminant_guard(p: Params, sc: ScenarioParams) -> None:
    """2r/sigma^2 < 500 - numerical guard on the discriminant at very low sigma.

    The four ladder rungs are all safe (the lowest, the CfD rung at 0.10, gives
    16); the guard exists for a hand-set sigma below ~0.018.
    """
    with pytest.raises(ModelError, match="discriminant"):
        run_guards(p.with_common(sigma=0.017), ScenarioParams(u=1.0, sigma_regime=""))


def test_load_factor_domain(p: Params) -> None:
    for bad in (0.0, -0.1, 1.01):
        with pytest.raises(ModelError, match="outside"):
            run_guards(p, ScenarioParams(u=bad))


def test_residual_value_never_negative_past_the_reline(p: Params) -> None:
    """age_eff = (T - T_rel) mod L_s keeps S_s >= 0 on the reinvestment branch."""
    for T in range(p.common.t0, p.common.horizon_end + 1):
        assert residual_value(T, p) >= 0.0


def test_residual_value_restarts_a_campaign_after_the_reline(p: Params) -> None:
    from timing_model.cost import reline_year

    t_rel = reline_year(p)
    assert residual_value(t_rel, p) == pytest.approx(0.0, abs=1e-9)
    assert residual_value(t_rel + 1, p) > 0.0


def test_allocation_schedule_is_monotone_and_bounded(p: Params) -> None:
    for vintage in ("law2023", "com2026"):
        sc = ScenarioParams(u=1.0, policy_vintage=vintage)
        prev = 1.0
        for t in range(p.common.t0, p.common.horizon_end + 1):
            f = free_allocation_factor(t, sc)
            assert 0.0 <= f <= 1.0
            assert f <= prev + 1e-12, f"{vintage} f({t}) rose to {f}"
            prev = f


def test_capex_clamp_binds_and_is_recorded(p: Params, sc: ScenarioParams) -> None:
    """Support exceeding gross capex is a signal, not a free plant."""
    rich = p.with_policy(s_max=5000.0)
    cost = switching_cost(2030, rich, sc)
    assert cost.clamp_binds
    assert cost.total == pytest.approx(cost.writeoff)
    notes = run_guards(rich, sc)
    assert any("clamp binds" in n for n in notes)


def test_crossing_year_returns_none_and_a_reason_not_never() -> None:
    path = dict.fromkeys(range(2026, 2051), 50.0)
    year, reason = crossing_year(400.0, path, 2050)
    assert year is None
    assert reason == BEYOND_HORIZON
    assert "never" not in reason


def test_crossing_year_finds_the_first_crossing() -> None:
    path = {2026: 76.0, 2027: 85.0, 2028: 94.0, 2029: 103.0, 2030: 112.0}
    assert crossing_year(109.52, path, 2050) == (2030, "crossed")


def test_currency_tags_present_on_every_monetary_field(p: Params, sc: ScenarioParams) -> None:
    check_currency_tags(p.common, p.sector, p.policy, sc)


def test_currency_tag_violation_is_detected() -> None:
    from dataclasses import dataclass, field

    from timing_model.params import Meta

    @dataclass(frozen=True)
    class Bad:
        x: float = field(default=1.0, metadata=Meta("EUR/t capacity", None, "nowhere"))

    with pytest.raises(ModelError, match="currency-year"):
        check_currency_tags(Bad())


def test_t_exp_definitions_agree_in_the_base_case(p: Params, sc: ScenarioParams) -> None:
    """Appendix A F7: the two agree in the base case. Assert it so divergence shows."""
    from timing_model.objective import t_exp_marginal

    assert t_exp(p, sc) == t_star(p, sc) == t_exp_marginal(p, sc) == 2029


def test_legacy_mode_must_actually_be_legacy(p: Params) -> None:
    bad = ScenarioParams(u=0.85, legacy_mode=True)
    with pytest.raises(ModelError, match="not legacy"):
        run_guards(p, bad)


def test_gate_failure_raises_rather_than_returning_a_flag(p: Params, sc: ScenarioParams) -> None:
    with pytest.raises(ModelError, match="validation gate failed"):
        run_gate(p.with_sector(I0=1000.0), sc)


def test_validated_returns_binding_guards_only(p: Params, sc: ScenarioParams) -> None:
    assert isinstance(validated(p, sc), list)
