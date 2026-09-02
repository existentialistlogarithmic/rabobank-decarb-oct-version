"""Group IV - the deterministic decision.

Appendix A §1.6.  Everything here is in EUR per tonne of annual **capacity**,
discounted to ``t0`` (2026).  No option premium: a firm that ignores
irreversibility acts at ``T*``.
"""

from __future__ import annotations

from timing_model.benefit import annual_benefit
from timing_model.cost import reline_year, switching_cost
from timing_model.params import Params, ScenarioParams

__all__ = ["discount", "reinvestment_term", "benefit_pv", "npv", "npv_curve",
           "t_star", "t_exp", "delta", "t_exp_marginal"]


def discount(t: int, p: Params) -> float:
    """d(t) = (1+r)^-(t-2026). Dimensionless."""
    return (1.0 + p.common.r) ** (-(t - p.common.t0))


def reinvestment_term(T: int, p: Params) -> float:
    """+/- d(T_rel) * rho * K_s. EUR/t capacity. Second term of Group IV eq (9).

    Avoided reinvestment if the firm commits at or before the reline
    (``T <= T_rel``); paid if it commits after.  The sign flip makes the NPV
    curve discontinuous at ``T_rel``, which is precisely the mechanism that can
    give the curve two local maxima - see :func:`t_exp`.
    """
    t_rel = reline_year(p)
    magnitude = discount(t_rel, p) * p.sector.rho * p.sector.K_s
    return magnitude if T <= t_rel else -magnitude


def benefit_pv(T: int, p: Params, sc: ScenarioParams) -> float:
    """Sum_{t>=T} d(t)*B(t). EUR/t capacity, discounted to t0.

    UNIT BRIDGE.  ``B(t)`` is EUR/t **product** and this sum is read as EUR/t
    **capacity**; the conversion is the load factor ``u`` already applied
    inside :func:`timing_model.benefit.annual_benefit`.
    """
    return sum(
        discount(t, p) * annual_benefit(t, p, sc, commit_year=T)
        for t in range(T, p.common.horizon_end + 1)
    )


def npv(T: int, p: Params, sc: ScenarioParams) -> float:
    """NPV(T). EUR/t capacity, discounted to 2026. Group IV eq (9).

    ``NPV(T) = -d(T)*I'(T) +/- d(T_rel)*rho*K_s + Sum_{t>=T} d(t)*B(t)``
    """
    cost = switching_cost(T, p, sc).total
    return -discount(T, p) * cost + reinvestment_term(T, p) + benefit_pv(T, p, sc)


def npv_curve(p: Params, sc: ScenarioParams) -> dict[int, float]:
    """NPV(T) for every admissible commitment year. EUR/t capacity."""
    return {T: npv(T, p, sc) for T in range(p.common.t0, p.common.horizon_end + 1)}


def t_star(p: Params, sc: ScenarioParams) -> int:
    """T* = argmax_T NPV(T). Group IV eq (10). Ties break to the earliest year."""
    curve = npv_curve(p, sc)
    best = max(curve.values())
    return min(T for T, v in curve.items() if v == best)


def t_exp(p: Params, sc: ScenarioParams) -> int:
    """T_exp = argmax_T NPV(T). Group IV eq (11). Last year deferral adds value.

    Appendix A F7 changes this from ``min{T : Delta(T) < 0}``.  The old
    definition is correct only when the NPV curve has a single peak, and the
    support step (or the reline sign flip in :func:`reinvestment_term`) can
    give it two.  :func:`delta` is retained as a printed diagnostic, and
    :mod:`timing_model.validate` asserts the two definitions still agree in the
    base case so a future divergence is visible rather than silent.
    """
    return t_star(p, sc)


def delta(T: int, p: Params, sc: ScenarioParams) -> float:
    """Delta(T) = NPV(T+1) - NPV(T). EUR/t capacity. DIAGNOSTIC ONLY (F7)."""
    return npv(T + 1, p, sc) - npv(T, p, sc)


def t_exp_marginal(p: Params, sc: ScenarioParams) -> int | None:
    """min{T : Delta(T) < 0} - the SUPERSEDED definition, kept for the diagnostic.

    Returns ``None`` if the marginal test never turns negative in the horizon.
    """
    for T in range(p.common.t0, p.common.horizon_end):
        if delta(T, p, sc) < 0.0:
            return T
    return None
