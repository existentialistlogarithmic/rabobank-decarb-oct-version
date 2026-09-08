"""Group III - the cost of acting in year T.

Appendix A §1.5.  Three effects, all in EUR per tonne of annual **capacity**,
all evaluated at the chosen commitment year.

The load factor ``u`` does NOT appear anywhere in this module: it bridges to
per-tonne-of-product and capex is per-tonne-of-capacity (Appendix A F2).

Nothing here may import from :mod:`timing_model.objective`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from timing_model.params import Params, ScenarioParams

__all__ = ["learning", "support", "reline_year", "residual_value", "switching_cost",
           "SwitchingCost"]


def learning(T: int, p: Params) -> float:
    """L(T), Wright-law capex multiplier. Dimensionless. Group III eq (5).

    ``L(T) = (1 + gamma)^(-b_learn * (T - t0))`` - cumulative deployed capacity
    grows at ``gamma`` per year and unit cost falls with exponent ``b_learn``
    (0.234, i.e. a ~15% learning rate).  Capex falls the longer you wait: this
    is the model's main reason to defer.
    """
    return (1.0 + p.sector.gamma) ** (-p.sector.b_learn * (T - p.common.t0))


#: v11 eq (9): full weight through 2031, linear taper, gone from 2035.
SUPPORT_FULL_UNTIL: Final[int] = 2031
SUPPORT_END: Final[int] = 2035

#: v11 eq (9), the first branch: before the Booster window opens there is still
#: the Innovation Fund and national aid, worth ``0.35 * s_max``. The code used
#: to return zero here, which put the whole EUR 200 into a single step at 2028
#: instead of the EUR 130 the specification works out by hand ("the jump of
#: EUR 130/t between 2027 and 2028 is the origin of the 'waiting to 2028 is
#: worth +EUR 146' step"). Overstating that step overstates the case for
#: waiting, which is the one thing this model exists to measure.
SUPPORT_PRE_WINDOW: Final[float] = 0.35


def support(T: int, p: Params, sc: ScenarioParams) -> float:
    """s(T). EUR/t capacity. Group III eq (6).

    v11 eq (9), all four branches:

    ==================  ==========================================
    ``T < 2028``        ``0.35 * s_max`` (Innovation Fund, national aid)
    ``2028 <= T <= 2031``  ``s_max * q(T)`` (the Booster window, full weight)
    ``2031 < T < 2035``    ``s_max * q(T) * (2035 - T)/4`` (linear taper)
    ``T >= 2035``          ``0``
    ==================  ==========================================

    with rationing ``q(t) = max{q_min, 1 - lam*(t - support_start)}``.  The
    published base case is the unrationed branch (``lam = 0``); ``lam = 0.30``
    with ``q_min = 0.10`` is the specification's "pool depletes 30 per cent a
    year" case, giving q = 0.70, 0.40, 0.10 in 2029-2031.

    Two branches were missing at different times.  The taper and the end date
    came first: support used to run flat to 2050, which made a late commitment
    look better funded than any published rule allows.  The pre-window floor
    came second: it used to be zero, which put a EUR 200 step at 2028 where the
    specification has EUR 130.

    Returns 0.0 under ``support_basis='stream'``: the premium is a flow and is
    routed into ``B(t)`` instead (Appendix A F4 - do not net a flow from a
    stock).  See :func:`timing_model.benefit.support_stream_flow`.
    """
    if sc.support_basis == "stream":
        return 0.0
    if T >= SUPPORT_END:
        return 0.0
    if p.policy.support_start > T:
        return p.policy.s_max * SUPPORT_PRE_WINDOW
    q = max(p.policy.q_min, 1.0 - p.policy.lam * (T - p.policy.support_start))
    if T > SUPPORT_FULL_UNTIL:
        q *= (SUPPORT_END - T) / (SUPPORT_END - SUPPORT_FULL_UNTIL)
    return p.policy.s_max * q


def reline_year(p: Params) -> int:
    """T_rel = t0 + (L_s - age0). The date the incumbent must be relined.

    Appendix A §2.1: the most bankable variable in the model - relining
    schedules are published plant by plant, so unlike everything else this is a
    calendar rather than a forecast.
    """
    return int(p.common.t0 + (p.sector.L_s - p.sector.age0))


def residual_value(T: int, p: Params) -> float:
    """S_s(T). EUR/t capacity. Group III eq (7).

    ``S_s(T) = K_s * max{L_s - age(T), 0} / L_s``, switching to the
    reinvestment branch after the reline: past ``T_rel`` the effective age is
    ``(T - T_rel) mod L_s``, so a freshly relined asset starts a new campaign
    with full book value rather than going negative (Appendix A §3.6).
    """
    t_rel = reline_year(p)
    if t_rel >= T:
        remaining = p.sector.L_s - (p.sector.age0 + (T - p.common.t0))
    else:
        remaining = p.sector.L_s - ((T - t_rel) % p.sector.L_s)
    return p.sector.K_s * max(remaining, 0.0) / p.sector.L_s


@dataclass(frozen=True)
class SwitchingCost:
    """Decomposition of I'(T), for the banker bridge of Appendix A §2.2."""

    capex: float
    """I0 * L(T). EUR/t capacity. Senior debt / project finance."""
    support: float
    """s(T). EUR/t capacity. Grants and CCfD premia - arrive AFTER FID."""
    writeoff: float
    """phi * S_s(T). EUR/t capacity. Not financeable: an equity/covenant event."""
    total: float
    """I'(T). EUR/t capacity."""
    clamp_binds: bool
    """True when support exceeded gross capex and the max(., 0) clamp bound."""


def switching_cost(T: int, p: Params, sc: ScenarioParams) -> SwitchingCost:
    """I'(T) = max{I0*L(T) - s(T), 0} + phi*S_s(T). EUR/t capacity. Group III eq (8).

    The clamp is recorded rather than silently applied: support exceeding gross
    capex is a modelling signal, not a free plant (Appendix A §3.6).
    """
    gross = p.sector.I0 * learning(T, p)
    s = support(T, p, sc)
    net = gross - s
    clamp_binds = net < 0.0
    writeoff = p.sector.phi * residual_value(T, p)
    return SwitchingCost(
        capex=gross,
        support=s,
        writeoff=writeoff,
        total=max(net, 0.0) + writeoff,
        clamp_binds=clamp_binds,
    )
