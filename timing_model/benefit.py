"""Group II - the annual money: what switching is worth per year.

Appendix A §1.4.  One equation, in EUR per tonne of **product** per year.

Imports only :mod:`timing_model.params` and :mod:`timing_model.primitives`
(Groups 0 and I).  It must not reach forward into Group III or IV.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from timing_model.params import ModelError, Params, ScenarioParams
from timing_model.primitives import abatement_intensity, effective_eps_inc, opex_penalty

__all__ = [
    "carbon_price_path",
    "free_allocation_factor",
    "alpha_v",
    "support_stream_flow",
    "annual_benefit",
    "F_LAW2023",
    "COM2026_FLOOR",
    "COM2026_FLOOR_YEARS",
]

#: CBAM phase-out of free allocation as legislated in 2023.  Years absent from
#: the table take 0.0 (full phase-out from 2034).
F_LAW2023: Final[Mapping[int, float]] = {
    2026: 0.975,
    2027: 0.950,
    2028: 0.900,
    2029: 0.775,
    2030: 0.515,
    2031: 0.390,
    2032: 0.265,
    2033: 0.140,
}

#: COM(2026) 616 reintroduces a floor of 15%.  Appendix A open item 2: this is
#: RECONSTRUCTED from the confirmed reintroduction mechanism and has not been
#: checked against the legal annex.  Ten floored years reproduces F8's "10 terms".
COM2026_FLOOR: Final[float] = 0.15
COM2026_FLOOR_YEARS: Final[tuple[int, int]] = (2033, 2042)

#: Central nominal EUA path: linear 76 -> 112 over 2026-2030, then +mu per year.
_P_2026: Final[float] = 76.0
_P_2030: Final[float] = 112.0
_RAMP_END: Final[int] = 2030


def carbon_price_path(p: Params, sc: ScenarioParams) -> dict[int, float]:
    """EUA price by year. EUR/tCO2. Central path of the July note.

    Nominal basis: EUR 76 in 2026 rising linearly to EUR 112 in 2030, then
    growing at the GBM drift ``mu`` to the horizon.

    Real basis (Appendix A F3): the same path deflated at
    :attr:`ScenarioParams.deflator`.  Note that F3 also warns the real basis
    contaminates ``(r - mu)``; this function deflates the **path only** and
    ``price_scale`` selects the low/central/high path of the §9.2 diff grid.

    leaves ``(r - mu)`` alone, which is what the published stress ladder does
    (its trigger is unchanged by the real-vs-nominal row).  See
    :mod:`timing_model.validate` for the guard that records this.
    """
    ramp = (_P_2030 - _P_2026) / (_RAMP_END - p.common.t0)
    out: dict[int, float] = {}
    for t in range(p.common.t0, p.common.horizon_end + 1):
        if t <= _RAMP_END:
            nominal = _P_2026 + ramp * (t - p.common.t0)
        else:
            nominal = _P_2030 * (1.0 + p.common.mu) ** (t - _RAMP_END)
        nominal *= sc.price_scale
        if sc.price_basis == "real":
            nominal /= (1.0 + sc.deflator) ** (t - p.common.t0)
        out[t] = nominal
    return out


def free_allocation_factor(t: int, sc: ScenarioParams) -> float:
    """f_v(t) in [0, 1], monotone non-increasing. Group II eq (3).

    ``law2023`` is the CBAM phase-out as legislated; ``com2026`` applies a 15%
    floor over :data:`COM2026_FLOOR_YEARS`.  The floor is applied as a maximum
    against the legislated path so the series stays monotone non-increasing -
    a naive floor would step *up* from 0.14 in 2033 and trip the guard.
    """
    base = F_LAW2023.get(t, 0.0)
    if sc.policy_vintage == "law2023":
        return base
    if sc.policy_vintage == "com2026":
        lo, hi = COM2026_FLOOR_YEARS
        return max(base, COM2026_FLOOR) if lo <= t <= hi else base
    raise ModelError(f"unknown policy_vintage {sc.policy_vintage!r}")


def alpha_v(t: int, p: Params, sc: ScenarioParams) -> float:
    """alpha_v(t) = [BM(t)/eps_inc_eff] * f_v(t). Group II eq (3).

    Share of the incumbent's emissions still received free.  Dimensionless.
    """
    return (p.policy.benchmark / effective_eps_inc(p)) * free_allocation_factor(t, sc)


def support_stream_flow(
    t: int, commit_year: int | None, p: Params, sc: ScenarioParams
) -> float:
    """Support premium as a FLOW. EUR/t product/yr. Appendix A F4.

    The Investment Booster pays a premium per tCO2 abated, i.e. a flow.  Under
    ``support_basis='stream'`` it is routed here, into ``B(t)``, where it
    structurally belongs, instead of being netted from a stock of capex.
    Paid for :attr:`PolicyParams.stream_years` from the commitment year.

    Returns 0.0 under the ``lump`` basis; see
    :func:`timing_model.cost.support` for that branch.
    """
    if sc.support_basis != "stream" or commit_year is None:
        return 0.0
    if not (commit_year <= t < commit_year + p.policy.stream_years):
        return 0.0
    return p.policy.stream_premium * abatement_intensity(p)


def annual_benefit(
    t: int, p: Params, sc: ScenarioParams, commit_year: int | None = None
) -> float:
    """B(t). EUR/t **product** per year. Group II eq (4).

    ``B(t) = u * [ a + (1-alpha)*b*p_t + w*alpha*eps_inc*p_t ]``

    Three terms: the firm pays more to operate (``a``), avoids the carbon it no
    longer emits net of what it was given free, and - if resale is permitted
    (``w=1``) - sells the allowances it no longer needs.

    UNIT BRIDGE.  ``u`` is the load factor and is the *only* bridge from EUR per
    tonne of annual **capacity** (in which capex and every NPV are denominated)
    to EUR per tonne of **product** (in which this flow is denominated).  It
    multiplies ``B(t)`` and never ``I'(T)`` - Appendix A F2.  Its absence from
    the MATLAB reference biases the model systematically toward committing too
    early.

    ``commit_year`` is used only by the ``stream`` support basis; the pure
    Group II flow does not depend on the decision.
    """
    price = carbon_price_path(p, sc)[t]
    alpha = alpha_v(t, p, sc)
    b = abatement_intensity(p)
    eps_inc = effective_eps_inc(p)
    a = opex_penalty(p, sc)
    gross = (
        a
        + (1.0 - alpha) * b * price
        + sc.w * alpha * eps_inc * price
        + support_stream_flow(t, commit_year, p, sc)
    )
    return sc.u * gross
