"""Group V - the option layer: what uncertainty adds.

Appendix A §1.7.  Groups I-IV describe a firm that acts at break-even.  A firm
facing an irreversible decision under a stochastic carbon price should not.
"""

from __future__ import annotations

import math

from timing_model.params import ModelError, Params, ScenarioParams
from timing_model.primitives import (
    abatement_intensity,
    opex_penalty,
    total_switching_stock,
)

__all__ = [
    "resolve_sigma",
    "beta",
    "option_multiple",
    "break_even_price",
    "trigger_price",
    "crossing_year",
    "BEYOND_HORIZON",
]

#: Reason string returned instead of a crossing year.  Appendix A §3.2 forbids
#: the word "never": at sigma = 0.45 the trigger *is* crossed, in the mid-2040s.
BEYOND_HORIZON = "beyond horizon"


def resolve_sigma(p: Params, sc: ScenarioParams, sigma: float | None = None) -> float:
    """Volatility actually in force. Resolution order: override > regime > common."""
    if sigma is not None:
        return sigma
    if sc.sigma_regime:
        return sc.resolved_sigma()
    return p.common.sigma


def beta(p: Params, sc: ScenarioParams, sigma: float | None = None) -> float:
    """Positive root of (1/2)s^2 b(b-1) + mu*b - r = 0. Group V eq (13). Base 1.3860.

    From the Bellman equation for the option to wait under GBM.
    """
    s = resolve_sigma(p, sc, sigma)
    r, mu = p.common.r, p.common.mu
    if s <= 0.0:
        raise ModelError("sigma must be strictly positive to solve for beta")
    v = s * s
    k = mu / v
    return 0.5 - k + math.sqrt((k - 0.5) ** 2 + 2.0 * r / v)


def option_multiple(p: Params, sc: ScenarioParams, sigma: float | None = None) -> float:
    """beta/(beta-1). Dimensionless. Base 3.5907.

    As ``sigma -> 0`` the multiple tends to 1 and the trigger collapses to
    break-even: no uncertainty, no premium.
    """
    b = beta(p, sc, sigma)
    if b <= 1.0:
        raise ModelError(f"beta = {b:.6f} <= 1; the option multiple is undefined")
    return b / (b - 1.0)


def break_even_price(p: Params, sc: ScenarioParams, s_s: float) -> float:
    """p'_M = (I0 + phi*S_s - a/r) * (r - mu) / b. EUR/tCO2. Group V eq (12).

    The bracket is the total cost of switching with the annual opex penalty
    capitalised (``-a/r``); multiplying by ``(r-mu)/b`` inverts the growing-
    perpetuity result to give the carbon price that just pays for it.

    UNIT BRIDGE.  The bracket is EUR/t **capacity** and ``b`` is tCO2/t
    **product**; the published threshold follows the literature convention of
    reading them at a load factor of 1.0, so ``u`` does not enter here.
    """
    r, mu = p.common.r, p.common.mu
    if r - mu < 0.005:
        raise ModelError(
            f"r - mu = {r - mu:.4f} < 0.005; the growing-perpetuity inversion "
            "is undefined and p'_M changes sign"
        )
    stock = total_switching_stock(p, s_s)
    capitalised = stock - opex_penalty(p, sc) / r
    return capitalised * (r - mu) / abatement_intensity(p)


def trigger_price(
    p: Params, sc: ScenarioParams, s_s: float, sigma: float | None = None
) -> float:
    """p*' = p'_M * beta/(beta-1). EUR/tCO2. Group V eq (14). Base 109.52."""
    return break_even_price(p, sc, s_s) * option_multiple(p, sc, sigma)


def crossing_year(
    trigger: float, path: dict[int, float], horizon_end: int
) -> tuple[int | None, str]:
    """First year the price path reaches ``trigger``.

    Returns ``(year, reason)``.  When the trigger is not reached by
    ``horizon_end`` the year is ``None`` and the reason is
    :data:`BEYOND_HORIZON` - never the string "never" (Appendix A §3.2).
    """
    for t in sorted(y for y in path if y <= horizon_end):
        if path[t] >= trigger:
            return t, "crossed"
    return None, BEYOND_HORIZON
