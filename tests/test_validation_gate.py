"""Appendix A §4.3 - the validation gate.

These nine quantities are ground truth.  If they do not reproduce, the
implementation is wrong: do not adjust the expected values and do not loosen
the tolerance.
"""

from __future__ import annotations

import pytest

from timing_model.option import beta, break_even_price, option_multiple, trigger_price
from timing_model.params import Params, ScenarioParams
from timing_model.primitives import abatement_intensity, crf, mac, opex_penalty

#: Appendix A §4.3 states a tolerance of 1e-3.  It is read as *relative*: the
#: published figures are quoted to 2 d.p. (MAC = 80.17, p*' = 109.52), so an
#: absolute 1e-3 band is narrower than their own rounding and no implementation
#: could satisfy it.  Every gate quantity clears 1e-3 relative with >20x margin.
TOL = 1e-3

#: Static write-off used by the published gate figures (phi = 0.5, S_s = 360).
GATE_S_S = 360.0


@pytest.fixture
def p() -> Params:
    return Params()


@pytest.fixture
def sc() -> ScenarioParams:
    return ScenarioParams()


def test_crf_25yr_8pct(p: Params) -> None:
    """CRF(25, 8%) = 0.0937.  Diagnostic only (Appendix A §1.8)."""
    assert crf(p.common.crf_years, p.common.r) == pytest.approx(0.0937, rel=TOL)


def test_abatement_intensity(p: Params) -> None:
    """b = 1.9 - 0.1 = 1.8 tCO2/t.  Group I eq (1)."""
    assert abatement_intensity(p) == pytest.approx(1.8, abs=1e-12)


def test_beta(p: Params, sc: ScenarioParams) -> None:
    """beta = 1.3860.  Group V eq (13)."""
    assert beta(p, sc) == pytest.approx(1.3860, rel=TOL)


def test_option_multiple(p: Params, sc: ScenarioParams) -> None:
    """beta/(beta-1) = 3.5907.  Group V eq (13)."""
    assert option_multiple(p, sc) == pytest.approx(3.5907, rel=TOL)


def test_p_M_no_writeoff(p: Params, sc: ScenarioParams) -> None:
    """p_M = 27.50 EUR/tCO2 - break-even ignoring the incumbent asset."""
    assert break_even_price(p, sc, s_s=0.0) == pytest.approx(27.50, rel=TOL)


def test_mac_no_writeoff(p: Params, sc: ScenarioParams) -> None:
    """MAC = 80.17 EUR/tCO2.  Diagnostic only (Appendix A §1.8)."""
    assert mac(p, sc, s_s=0.0) == pytest.approx(80.17, rel=TOL)


def test_p_star_no_writeoff(p: Params, sc: ScenarioParams) -> None:
    """p* = 98.74 EUR/tCO2 = p_M * beta/(beta-1)."""
    assert trigger_price(p, sc, s_s=0.0) == pytest.approx(98.74, rel=TOL)


def test_p_M_prime(p: Params, sc: ScenarioParams) -> None:
    """p'_M = 30.50 EUR/tCO2 with phi = 0.5, S_s = 360.  Group V eq (12)."""
    assert break_even_price(p, sc, s_s=GATE_S_S) == pytest.approx(30.50, rel=TOL)


def test_mac_prime(p: Params, sc: ScenarioParams) -> None:
    """MAC' = 89.54 EUR/tCO2."""
    assert mac(p, sc, s_s=GATE_S_S) == pytest.approx(89.54, rel=TOL)


def test_p_star_prime(p: Params, sc: ScenarioParams) -> None:
    """p*' = 109.52 EUR/tCO2.  Group V eq (14) - the headline trigger."""
    assert trigger_price(p, sc, s_s=GATE_S_S) == pytest.approx(109.52, rel=TOL)


def test_a_falls_out_at_260(p: Params, sc: ScenarioParams) -> None:
    """Appendix A F1: a = -60 must fall out of a(p_H2) at p_H2 = 2.60."""
    assert opex_penalty(p, sc) == pytest.approx(-60.0, abs=1e-9)


def test_a_at_market_hydrogen(p: Params) -> None:
    """Platts 8.29 EUR/kg (Spain, 8 May 2026) gives a = -372.95 (§2.2: '-373')."""
    sc = ScenarioParams(p_H2=8.29)
    assert opex_penalty(p, sc) == pytest.approx(-372.95, abs=1e-9)


def test_option_multiple_zero_sigma_limit(p: Params, sc: ScenarioParams) -> None:
    """SPEC DEVIATION, Appendix A §1.7 eq (14).

    The note's sanity check reads "as sigma -> 0 the multiple -> 1 and the
    trigger collapses to break-even".  That holds only when the drift is also
    zero.  Under GBM with mu > 0 the positive root tends to ``r/mu``, so the
    multiple tends to ``r/(r-mu)`` = 0.08/0.03 = 2.667, not 1.  The option
    premium does not vanish with volatility while the price still drifts up:
    waiting is rewarded by the drift alone.
    """
    assert option_multiple(p, sc, sigma=1e-4) == pytest.approx(
        p.common.r / (p.common.r - p.common.mu), rel=1e-4
    )


def test_option_multiple_collapses_when_drift_and_sigma_vanish(
    p: Params, sc: ScenarioParams
) -> None:
    """With mu -> 0 as well, the multiple does collapse to 1 as the note claims."""
    driftless = p.with_common(mu=0.0)
    assert option_multiple(driftless, sc, sigma=1e-4) == pytest.approx(1.0, abs=1e-3)
