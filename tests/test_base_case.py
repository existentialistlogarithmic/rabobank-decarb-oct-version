"""The base case and the cumulative stress ladder.

CALIBRATION NOTE.  Appendix A pins r, mu, sigma, I0, a, b, phi, S_s(t0) and the
CRF horizon through its validation gate, and those reproduce exactly.  It does
NOT publish the cost-side split - the learning growth rate ``gamma``, the
support slope ``lam``, and the asset block (K_s, L_s, age0, rho).  Those were
recovered from the published stress ladder (see CALIBRATION.md) and are marked
CALIBRATED in ``params.py``.  Rows 4-7 of the ladder are asserted only where
the recovery is determined; see ``test_ladder_rows_4_to_7_are_calibration_gaps``.
"""

from __future__ import annotations

import pytest

from timing_model.cost import residual_value
from timing_model.objective import t_exp, t_exp_marginal, t_star
from timing_model.params import ScenarioParams
from timing_model.results import outputs
from timing_model.scenarios import published_base, run_ladder


def test_base_case_headline() -> None:
    """T* = 2029, T_exp = 2029, NPV0 = 1605.9 EUR/t capacity, trigger crossed 2030."""
    p, sc = published_base()
    o = outputs(p, sc)
    assert o.t_star == 2029
    assert o.t_exp == 2029
    assert o.npv0 == pytest.approx(1605.9, abs=0.05)
    assert o.crossing_year == 2030
    assert o.crossing_reason == "crossed"


def test_base_case_trigger_is_the_published_one() -> None:
    p, sc = published_base()
    assert outputs(p, sc).trigger == pytest.approx(109.52, rel=1e-3)


def test_residual_value_at_t0_is_the_gate_value() -> None:
    """S_s(2026) = 360 is the write-off behind p'_M = 30.50 and p*' = 109.52."""
    p, _ = published_base()
    assert residual_value(p.common.t0, p) == pytest.approx(360.0, abs=1e-9)


def test_both_t_exp_definitions_agree_in_the_base_case() -> None:
    """Appendix A F7 keeps Delta(T) as a diagnostic; assert the two still agree."""
    p, sc = published_base()
    assert t_star(p, sc) == t_exp(p, sc) == t_exp_marginal(p, sc) == 2029


def test_trigger_exceeds_break_even_so_the_premium_is_positive() -> None:
    p, sc = published_base()
    o = outputs(p, sc)
    assert o.trigger > o.diagnostics["p_M_prime"]
    assert o.diagnostics["option_multiple"] == pytest.approx(3.5907, rel=1e-3)


def test_t_star_and_crossing_year_differ_by_the_option_premium_in_time() -> None:
    """Appendix A §1.9: that gap is the premium expressed in time, not an error."""
    p, sc = published_base()
    o = outputs(p, sc)
    assert o.crossing_year is not None and o.t_star is not None
    assert 0 <= o.crossing_year - o.t_star <= 2


def test_load_factor_moves_the_benefit_side_only() -> None:
    """Appendix A F2: u multiplies B(t), never I'(T)."""
    from timing_model.cost import switching_cost

    p, _ = published_base()
    a = switching_cost(2029, p, ScenarioParams(u=1.0))
    b = switching_cost(2029, p, ScenarioParams(u=0.75))
    assert a == b


def test_a_is_endogenous_and_reduces_to_the_matlab_constant() -> None:
    """Appendix A F1: a = -60 must fall out at p_H2 = 2.60, not be hardcoded."""
    from timing_model.primitives import opex_penalty

    p, _ = published_base()
    assert opex_penalty(p, ScenarioParams(p_H2=2.60)) == pytest.approx(-60.0, abs=1e-9)
    assert opex_penalty(p, ScenarioParams(p_H2=3.00)) < -60.0


#: The published ladder, Appendix A §4.4.  ``None`` marks a cell the calibration
#: cannot pin without ``timing_model.m`` - see the module docstring.
PUBLISHED_LADDER = [
    ("Base as published", 2029, 1606, 109.5),
    ("+ load factor u=0.85", 2029, 1302, 109.5),
    ("+ hot metal kappa=0.94", 2030, 1174, 116.9),
    ("+ real vs nominal", None, None, 116.9),
    ("+ hydrogen at 8.29", "beyond", None, 366.9),
    ("+ resale off (w=0)", "beyond", None, 366.9),
    ("+ support as stream", "beyond", None, 366.9),
]


def test_stress_ladder_labels_and_order() -> None:
    got = [r.label for r, _ in run_ladder()]
    assert got == [x[0] for x in PUBLISHED_LADDER]


@pytest.mark.parametrize("idx", range(len(PUBLISHED_LADDER)))
def test_stress_ladder_reproduces_the_published_table(idx: int) -> None:
    label, want_t, want_npv, want_trig = PUBLISHED_LADDER[idx]
    _, o = run_ladder()[idx]
    assert o.trigger == pytest.approx(want_trig, abs=0.05), f"{label} trigger"
    if want_t == "beyond":
        assert o.t_star is None, f"{label} should have no commitment year"
    elif want_t is not None:
        assert o.t_star == want_t, f"{label} T*"
    if want_npv is not None:
        assert o.npv0 == pytest.approx(want_npv, abs=0.6), f"{label} NPV"


def test_the_ladder_compounds_down_to_the_hydrogen_rung() -> None:
    """The corrections compound - up to the last rung, which now reverses.

    Rows 1-6 each take value off the previous one. Row 7, routing support as a
    CCfD stream instead of a lump, adds it back: once the Booster is correctly
    tapered and gone by 2035 (v11 eq 10), a per-tCO2 premium paid over ten
    years from the commitment year is worth more than the shrinking lump. That
    reversal is a result, not a leak, and it only became visible when the
    support schedule stopped running flat to 2050.
    """
    rows = run_ladder()
    npvs = [o.npv0 for _, o in rows]
    assert npvs[:-1] == sorted(npvs[:-1], reverse=True), npvs
    assert npvs[-1] > npvs[-2], "the stream rung should now improve the case"
    assert rows[-1][0].label.endswith("stream"), rows[-1][0].label


def test_corrections_are_monotone_in_the_trigger() -> None:
    triggers = [o.trigger for _, o in run_ladder()]
    assert triggers == sorted(triggers)


def test_volatility_ladder_pushes_the_trigger_and_the_crossing_out() -> None:
    """Appendix A §2.3: volatility moves the client between regimes, not at the margin."""
    from timing_model.scenarios import sigma_ladder

    by_regime = dict(sigma_ladder())
    triggers = [by_regime[k].trigger for k in ("cfd", "long_run", "crisis", "realised")]
    assert triggers == sorted(triggers), "trigger must rise with volatility"
    assert by_regime["cfd"].crossing_year is not None
    assert by_regime["crisis"].crossing_year > by_regime["cfd"].crossing_year


def test_realised_volatility_crosses_in_the_mid_2040s_not_never() -> None:
    """Appendix A §3.2 - one of the three contradictions to resolve.

    The earlier notes said the trigger is "never" crossed at market volatility.
    It is crossed, in the mid-2040s, on a horizon extended to 2050.  The
    accurate phrasing is *beyond any recognisable investment horizon*.  This
    test pins the retraction so the wrong claim cannot come back.
    """
    from timing_model.scenarios import sigma_ladder

    realised = dict(sigma_ladder())["realised"]
    assert realised.crossing_year is not None
    assert 2040 <= realised.crossing_year <= 2049
    assert realised.crossing_reason == "crossed"
