"""The validation gate and the feasibility guards.

Appendix A §3.6 and §4.3.  Guards **raise**; they never return a flag.  The
only things returned are the *binding* guards - conditions that are legal but
are a modelling signal the reader must see (Appendix A §3.6: "support exceeding
gross capex is a modelling signal, not a free plant").
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Final, Sequence

from timing_model.benefit import free_allocation_factor
from timing_model.cost import residual_value, switching_cost
from timing_model.objective import npv_curve, t_exp_marginal, t_star
from timing_model.option import beta, break_even_price, option_multiple, trigger_price
from timing_model.params import (
    CommonParams,
    ModelError,
    Params,
    PolicyParams,
    ScenarioParams,
    SectorParams,
)
from timing_model.primitives import abatement_intensity, crf, mac, opex_penalty

__all__ = ["GATE", "GATE_S_S", "run_gate", "run_guards", "check_currency_tags",
           "validated", "GATE_TOL"]

#: Relative tolerance.  Appendix A §4.3 says 1e-3; read as relative because the
#: published figures are quoted to 2 d.p. and an absolute 1e-3 band would be
#: narrower than their own rounding.  Every quantity clears it with >20x margin.
GATE_TOL: Final[float] = 1e-3

#: Static write-off behind the primed gate figures.
GATE_S_S: Final[float] = 360.0

#: Appendix A §4.3.  Nothing prints before these reproduce.
GATE: Final[dict[str, float]] = {
    "CRF(25,8%)": 0.0937,
    "beta": 1.3860,
    "beta/(beta-1)": 3.5907,
    "p_M": 27.50,
    "MAC": 80.17,
    "p_star": 98.74,
    "p_M_prime": 30.50,
    "MAC_prime": 89.54,
    "p_star_prime": 109.52,
}


def _gate_actuals(p: Params, sc: ScenarioParams) -> dict[str, float]:
    return {
        "CRF(25,8%)": crf(p.common.crf_years, p.common.r),
        "beta": beta(p, sc),
        "beta/(beta-1)": option_multiple(p, sc),
        "p_M": break_even_price(p, sc, s_s=0.0),
        "MAC": mac(p, sc, s_s=0.0),
        "p_star": trigger_price(p, sc, s_s=0.0),
        "p_M_prime": break_even_price(p, sc, s_s=GATE_S_S),
        "MAC_prime": mac(p, sc, s_s=GATE_S_S),
        "p_star_prime": trigger_price(p, sc, s_s=GATE_S_S),
    }


def run_gate(p: Params | None = None, sc: ScenarioParams | None = None) -> dict[str, float]:
    """Reproduce the nine published quantities or raise. Appendix A §4.3.

    Must be called against the *published* parameterisation - the gate figures
    are defined at ``u = 1``, ``kappa = 1``, ``p_H2 = 2.60``.  Returns the
    actuals so a caller can print them.
    """
    p = p or Params()
    sc = sc or ScenarioParams()
    actual = _gate_actuals(p, sc)
    bad = [
        f"{k}: expected {GATE[k]}, got {actual[k]:.6f} "
        f"(rel {abs(actual[k] - GATE[k]) / abs(GATE[k]):.2e})"
        for k in GATE
        if abs(actual[k] - GATE[k]) > GATE_TOL * abs(GATE[k])
    ]
    if bad:
        raise ModelError("validation gate failed:\n  " + "\n  ".join(bad))
    return actual


def check_currency_tags(*objs: object) -> None:
    """Every monetary field must carry a currency-year tag. Appendix A §3.6.

    DIW capex is 2022 euros; project figures are as-reported.  A field whose
    unit mentions EUR must not be tagged ``n/a``.
    """
    missing: list[str] = []
    for obj in objs:
        if not is_dataclass(obj):
            continue
        for f in fields(obj):
            unit = str(f.metadata.get("unit", ""))
            if "EUR" in unit and f.metadata.get("ccy_year", "n/a") == "n/a":
                missing.append(f"{type(obj).__name__}.{f.name}")
    if missing:
        raise ModelError(
            "monetary fields missing a currency-year tag: " + ", ".join(missing)
        )


def run_guards(p: Params, sc: ScenarioParams) -> list[str]:
    """Run the feasibility guard list. Raises on violation; returns binding notes.

    Appendix A §3.6.  A *violation* stops the run.  A *binding* guard is legal
    but must travel with the result, so it is returned and lands in
    ``Outputs.binding_guards``.
    """
    binding: list[str] = []
    r, mu = p.common.r, p.common.mu
    sigma = sc.resolved_sigma() if sc.sigma_regime else p.common.sigma

    if r - mu < 0.005:
        raise ModelError(
            f"r - mu = {r - mu:.4f} < 0.005: p'_M changes sign and the "
            "growing-perpetuity inversion is undefined"
        )
    if sigma <= 0.0:
        raise ModelError(f"sigma = {sigma} must be strictly positive")
    if 2.0 * r / (sigma * sigma) >= 500.0:
        raise ModelError(
            f"2r/sigma^2 = {2 * r / sigma ** 2:.1f} >= 500: the discriminant is "
            "numerically unsafe at this volatility"
        )
    b = beta(p, sc)
    if b <= 1.0:
        raise ModelError(f"beta = {b:.6f} <= 1: beta/(beta-1) blows up or goes negative")
    if not (0.0 < sc.u <= 1.0):
        raise ModelError(f"u = {sc.u} outside (0, 1]")
    if abatement_intensity(p) <= 0.0:
        raise ModelError("b = kappa*eps_inc - eps_cln must be strictly positive")

    years = range(p.common.t0, p.common.horizon_end + 1)
    prev = 1.0
    for t in years:
        f = free_allocation_factor(t, sc)
        if not (0.0 <= f <= 1.0):
            raise ModelError(f"f_v({t}) = {f} outside [0, 1]")
        if f > prev + 1e-12:
            raise ModelError(
                f"f_v({t}) = {f} > f_v({t - 1}) = {prev}: allocation schedule "
                "must be monotone non-increasing"
            )
        prev = f

    clamped: list[int] = []
    for T in years:
        if residual_value(T, p) < 0.0:
            raise ModelError(f"S_s({T}) < 0: residual value must not go negative")
        if switching_cost(T, p, sc).clamp_binds:
            clamped.append(T)
    if clamped:
        binding.append(
            f"capex clamp binds in {clamped[0]}-{clamped[-1]}: support exceeds "
            "gross capex (a modelling signal, not a free plant)"
        )

    if sc.legacy_mode:
        binding.append(
            "legacy_mode: DIFF FIXTURE ONLY - reproduces the uncorrected model "
            "(u=1, lump support, p_H2=2.60, nominal, kappa=1). Not a supported "
            "configuration."
        )
        expected = dict(u=1.0, support_basis="lump", p_H2=2.60, price_basis="nominal")
        wrong = {k: getattr(sc, k) for k, v in expected.items() if getattr(sc, k) != v}
        if wrong or p.policy.kappa != 1.0:
            raise ModelError(
                f"legacy_mode set but the configuration is not legacy: {wrong} "
                f"kappa={p.policy.kappa}"
            )

    if sc.price_basis == "real":
        binding.append(
            "real price basis: the path is deflated but (r - mu) is NOT "
            "re-derived; Appendix A F3 warns the real basis contaminates the "
            "gap, so the trigger is unchanged by this row by construction"
        )

    marginal = t_exp_marginal(p, sc)
    argmax = t_star(p, sc)
    if marginal is not None and marginal != argmax:
        binding.append(
            f"T_exp definitions diverge: argmax = {argmax} but "
            f"min{{T : Delta(T)<0}} = {marginal}. The NPV curve is not "
            "single-peaked; the argmax definition governs (Appendix A F7)."
        )
    curve = npv_curve(p, sc)
    if max(curve.values()) < 0.0:
        binding.append(
            "no commitment year in the horizon: NPV(T) < 0 for every T to "
            f"{p.common.horizon_end}"
        )
    return binding


def validated(p: Params, sc: ScenarioParams, *, gate: bool = True) -> list[str]:
    """Gate, then currency tags, then guards. Returns the binding guards."""
    if gate:
        run_gate()
    check_currency_tags(p.common, p.sector, p.policy, sc)
    return run_guards(p, sc)
