"""Group I - primitives: what a tonne emits and what it costs.

Appendix A §1.3.  Contains no decision.  This module imports nothing from the
rest of the package: it is the bottom of the dependency order.

:func:`crf` and :func:`mac` live here for convenience but are **diagnostics
only** (Appendix A §1.8).  They are reconciliation and communication objects
that let the result be compared with the abatement-cost literature; they are
not inputs to ``T*`` or ``p*'``.
"""

from __future__ import annotations

from timing_model.params import Params, ScenarioParams

__all__ = [
    "effective_eps_inc",
    "abatement_intensity",
    "opex_penalty",
    "crf",
    "mac",
    "total_switching_stock",
]


def effective_eps_inc(p: Params) -> float:
    """Incumbent intensity after the hot-metal correction. tCO2/t product.

    Appendix A F5.  The EU ETS benchmark of 1.248 allowances is defined per
    tonne of **hot metal**, while the model runs on **crude steel**; ``kappa``
    (~0.94) is the conversion.  ``kappa = 1.0`` reproduces the uncorrected model.
    """
    return p.policy.kappa * p.common.eps_inc


def abatement_intensity(p: Params) -> float:
    """b = eps_inc_eff - eps_cln. tCO2/t product. Group I eq (1).

    The denominator of every threshold in Group V, and the single parameter
    that orders the sectors.
    """
    return effective_eps_inc(p) - p.common.eps_cln


def opex_penalty(p: Params, sc: ScenarioParams) -> float:
    """a(p_H2) = -(m_H2 * p_H2 - c_avoided). EUR/t product/yr. Group I eq (2).

    Negative: the clean route costs more to run.  Endogenous in ``p_H2``
    (Appendix A F1) - the MATLAB reference hardcodes ``a = -60``, which embeds
    a hydrogen price of EUR 2.60/kg.  Making the dependence explicit converts a
    hidden forecast into a visible input; this is the largest single mover in
    the model.
    """
    return -(p.sector.m_H2 * sc.p_H2 - p.sector.c_avoided)


def crf(years: int, r: float) -> float:
    """Capital recovery factor. 1/yr. Appendix A §1.8 - DIAGNOSTIC ONLY.

    ``CRF = r(1+r)^n / ((1+r)^n - 1)``.  Annualises a stock of capex so it can
    be compared with a flow; it does not enter the timing decision.
    """
    if r <= 0.0:
        return 1.0 / years
    g = (1.0 + r) ** years
    return r * g / (g - 1.0)


def total_switching_stock(p: Params, s_s: float) -> float:
    """I0 + phi*S_s. EUR/t capacity.

    The gross cost of switching before learning and support, including the
    share of the incumbent write-off charged to the decision.
    """
    return p.sector.I0 + p.sector.phi * s_s


def mac(p: Params, sc: ScenarioParams, s_s: float = 0.0) -> float:
    """MAC = (CRF*(I0 + phi*S_s) - a) / b. EUR/tCO2. DIAGNOSTIC ONLY.

    UNIT BRIDGE.  ``CRF * I0`` is EUR per tonne **capacity** per year while
    ``a`` is EUR per tonne **product** per year; the literature convention is
    to compare them at a load factor of 1.0, so the load factor ``u`` is
    deliberately *not* applied here.  That is why MAC is a communication object
    and not a decision input (Appendix A §1.8).
    """
    annualised = crf(p.common.crf_years, p.common.r) * total_switching_stock(p, s_s)
    return (annualised - opex_penalty(p, sc)) / abatement_intensity(p)
