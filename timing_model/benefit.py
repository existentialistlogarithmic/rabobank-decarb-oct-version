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
    "CENTRAL_PATH",
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

#: COM(2026) 616, v11 eq (12).  The proposal has its OWN 2026-2033 factors -
#: it is not a floor applied to the legislated path - then a flat 15% tranche
#: for 2034-2037 and nothing from 2038.  Read off the specification's annex;
#: reproduces the published +7.82 vintage delta exactly.
F_COM2026: Final[Mapping[int, float]] = {
    2026: 0.975, 2027: 0.950, 2028: 0.915, 2029: 0.810,
    2030: 0.590, 2031: 0.480, 2032: 0.375, 2033: 0.270,
}
COM2026_FLOOR: Final[float] = 0.15
COM2026_FLOOR_YEARS: Final[tuple[int, int]] = (2034, 2037)

#: Central nominal EUA path, v11 §1: the published anchors for 2026-2030, then
#: +mu per year. These are quoted values (Reuters, ClearBlue), NOT a linear
#: interpolation - reading them off a straight line understates 2027-2029 by
#: EUR 1, 2 and 1 respectively.
CENTRAL_PATH: Final[Mapping[int, float]] = {
    2026: 76.0, 2027: 86.0, 2028: 96.0, 2029: 104.0, 2030: 112.0,
}
_RAMP_END: Final[int] = 2030


def carbon_price_path(p: Params, sc: ScenarioParams) -> dict[int, float]:
    """EUA price by year. EUR/tCO2. Central path of the July note.

    Nominal basis: the published anchors 76, 86, 96, 104, 112 for 2026-2030,
    then growing at the GBM drift ``mu`` to the horizon.

    Real basis (Appendix A F3): the same path deflated at
    :attr:`ScenarioParams.deflator`.  Note that F3 also warns the real basis
    contaminates ``(r - mu)``; this function deflates the **path only** and
    ``price_scale`` selects the low/central/high path of the §9.2 diff grid.

    leaves ``(r - mu)`` alone, which is what the published stress ladder does
    (its trigger is unchanged by the real-vs-nominal row).  See
    :mod:`timing_model.validate` for the guard that records this.
    """
    out: dict[int, float] = {}
    anchor = CENTRAL_PATH[_RAMP_END]
    for t in range(p.common.t0, p.common.horizon_end + 1):
        if t <= _RAMP_END:
            nominal = CENTRAL_PATH[t]
        else:
            nominal = anchor * (1.0 + p.common.mu) ** (t - _RAMP_END)
        nominal *= sc.price_scale
        if sc.price_basis == "real":
            nominal /= (1.0 + sc.deflator) ** (t - p.common.t0)
        out[t] = nominal
    return out


def free_allocation_factor(t: int, sc: ScenarioParams) -> float:
    """f_v(t) in [0, 1], monotone non-increasing. Group II eq (3).

    ``law2023`` is the CBAM phase-out as legislated; ``com2026`` is the
    proposal's own schedule (eq 12), which is more generous year by year and
    then holds a flat 15% conditional tranche over
    :data:`COM2026_FLOOR_YEARS` before ending.  Both are monotone
    non-increasing, which the guard checks.
    """
    if sc.policy_vintage == "law2023":
        return F_LAW2023.get(t, 0.0)
    if sc.policy_vintage == "com2026":
        lo, hi = COM2026_FLOOR_YEARS
        if lo <= t <= hi:
            return COM2026_FLOOR
        return F_COM2026.get(t, 0.0)
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
