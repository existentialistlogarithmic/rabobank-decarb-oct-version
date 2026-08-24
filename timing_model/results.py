"""Composition layer: the four outputs, welded to their conditions.

Appendix A §4.2.  The recurring failure in this project is that ``T*`` and the
trigger get quoted without the assumptions they are conditional on.  The fix is
mechanical: :class:`Outputs` is frozen, always carries
:attr:`Outputs.conditions`, and :mod:`timing_model.report` refuses to render a
row containing ``t_star`` or ``trigger`` unless the conditions are populated and
printed alongside.

Sits above Group V so that Groups I-V keep their forward-only import order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from timing_model.benefit import carbon_price_path
from timing_model.cost import residual_value, switching_cost
from timing_model.objective import npv, npv_curve, t_exp, t_exp_marginal, t_star
from timing_model.option import (
    BEYOND_HORIZON,
    beta,
    break_even_price,
    crossing_year,
    option_multiple,
    trigger_price,
)
from timing_model.params import ModelError, Params, ScenarioParams
from timing_model.validate import validated

__all__ = ["Outputs", "outputs", "CONDITION_KEYS"]

#: Every condition that must travel with a headline number.
CONDITION_KEYS: tuple[str, ...] = (
    "h2_price",
    "sigma_regime",
    "resale",
    "price_basis",
    "support_basis",
)


@dataclass(frozen=True)
class Outputs:
    """The four outputs of Appendix A §1.9, plus the conditions and guards.

    ``t_star`` and ``t_exp`` contain no option premium; ``trigger`` and
    ``crossing_year`` do.  ``t_star`` and the crossing year routinely differ by
    one to two years: that gap is the option premium expressed in time, not an
    inconsistency.
    """

    t_star: int | None
    """argmax_T NPV(T), or None when no commitment year exists in the horizon."""
    t_exp: int | None
    """Last year in which deferral still adds value. Appendix A F7: = argmax."""
    npv0: float
    """max_T NPV(T). EUR/t **capacity**, discounted to 2026."""
    trigger: float
    """p*' = p'_M * beta/(beta-1). EUR/tCO2."""
    crossing_year: int | None
    """First year the price path reaches the trigger; None => beyond horizon."""
    conditions: Mapping[str, str] = field(default_factory=dict)
    """Never optional in practice - report.py refuses to print without it."""
    binding_guards: tuple[str, ...] = ()
    diagnostics: Mapping[str, float] = field(default_factory=dict)
    """MAC, Delta(T*), beta, p'_M - communication objects, not decision inputs."""
    crossing_reason: str = "crossed"

    def require_conditions(self) -> None:
        """Raise unless every condition is populated. Called by the report layer."""
        missing = [k for k in CONDITION_KEYS if not self.conditions.get(k)]
        if missing:
            raise ModelError(
                "refusing to render a headline result without its conditions; "
                f"missing: {', '.join(missing)}"
            )


def _conditions(p: Params, sc: ScenarioParams) -> dict[str, str]:
    return {
        "h2_price": f"{sc.p_H2:.2f} EUR/kg",
        "sigma_regime": f"{sc.sigma_regime} ({sc.resolved_sigma():.2f})",
        "resale": "permitted (w=1)" if sc.w else "restricted (w=0)",
        "price_basis": (
            "nominal"
            if sc.price_basis == "nominal"
            else f"real, deflated {sc.deflator:.0%}"
        ),
        "support_basis": (
            f"lump {p.policy.s_max:.0f} EUR/t capacity"
            if sc.support_basis == "lump"
            else f"stream {p.policy.stream_premium:.0f} EUR/tCO2 x "
            f"{p.policy.stream_years}yr"
        ),
    }


def outputs(p: Params, sc: ScenarioParams, *, gate: bool = True) -> Outputs:
    """T*, T_exp, NPV0, trigger, crossing year - with their conditions attached.

    Appendix A §4.2.  Runs the gate and the guards first: nothing is computed
    for printing until the published quantities reproduce.
    """
    binding = tuple(validated(p, sc, gate=gate))

    curve = npv_curve(p, sc)
    best = max(curve.values())
    has_case = best >= 0.0
    star: int | None = t_star(p, sc) if has_case else None
    expiry: int | None = t_exp(p, sc) if has_case else None

    # The trigger is a threshold quoted TODAY - "at what carbon price does an
    # irreversible switch become rational" - so the write-off is read at t0,
    # not at the decision year.  S_s(2026) = 360 is exactly the value behind
    # the published p'_M = 30.50 and p*' = 109.52 (Appendix A §4.3).
    s_s = residual_value(p.common.t0, p)
    trig = trigger_price(p, sc, s_s=s_s)
    year, reason = crossing_year(
        trig, carbon_price_path(p, sc), p.common.horizon_end
    )

    diagnostics = {
        "beta": beta(p, sc),
        "option_multiple": option_multiple(p, sc),
        "p_M_prime": break_even_price(p, sc, s_s=s_s),
        "S_s_at_t0": s_s,
        "delta_at_t_star": (
            npv(star + 1, p, sc) - npv(star, p, sc)
            if star is not None and star < p.common.horizon_end
            else float("nan")
        ),
        "t_exp_marginal": float(t_exp_marginal(p, sc) or float("nan")),
        "switching_cost_at_t_star": switching_cost(
            star if star is not None else p.common.t0, p, sc
        ).total,
    }
    return Outputs(
        t_star=star,
        t_exp=expiry,
        npv0=best,
        trigger=trig,
        crossing_year=year,
        conditions=_conditions(p, sc),
        binding_guards=binding,
        diagnostics=diagnostics,
        crossing_reason=reason,
    )
