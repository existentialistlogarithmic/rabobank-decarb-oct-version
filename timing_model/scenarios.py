"""Scenario axes, the cumulative stress ladder, and the sourced ranges.

Appendix A §3.3, §4.4.  The seven axes are first-class, not buried parameters,
because they change conclusions rather than numbers.

The cross-product is deliberately NOT built.  The corrections are not
independent and four of the five push the same direction, so the ladder - each
row adding one correction to the row above - is the honest presentation.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Final

from timing_model.params import SIGMA_REGIMES, Params, ScenarioParams
from timing_model.results import Outputs, outputs

__all__ = [
    "Rung",
    "STRESS_LADDER",
    "run_ladder",
    "SOURCED_RANGES",
    "STORYLINES",
    "published_base",
    "legacy_fixture",
    "corrected_base",
    "sigma_ladder",
]

#: Sourced ranges - Appendix A §3.3 replaces the +/-20% sweep as the headline
#: sensitivity.  Twenty per cent is a convention, not a measurement.
SOURCED_RANGES: Final[Mapping[str, tuple[float, float]]] = {
    "I0": (600.0, 1400.0),
    "a": (-320.0, -25.0),
    "r": (0.06, 0.10),
    "s_max": (200.0, 660.0),
    "learning_rate": (0.10, 0.20),
    "u": (0.75, 0.85),
    "p_H2": (2.50, 8.29),
}


def published_base() -> tuple[Params, ScenarioParams]:
    """The base case exactly as published: u = 1, kappa = 1, nominal, p_H2 = 2.60.

    This is the row the July note quotes.  It is NOT the recommended
    configuration - see :func:`corrected_base`.
    """
    return Params(), ScenarioParams(u=1.0)


def corrected_base() -> tuple[Params, ScenarioParams]:
    """Every Appendix A §3.1 correction applied except the three undecided ones.

    Load factor and hot-metal conversion are applied because they are unarguable
    unit fixes.  The support basis, resale switch and hydrogen price are left at
    their published values because Appendix A §3.5 reserves those three to the
    team; they must be chosen explicitly, not inherited.
    """
    return Params().with_policy(kappa=0.94), ScenarioParams(u=0.85)


def legacy_fixture() -> tuple[Params, ScenarioParams]:
    """DIFF FIXTURE ONLY. Reproduces the uncorrected model for the MATLAB diff.

    The 50 reference cases were produced before the F1-F5 corrections, so the
    diff must run at ``u=1.0, support_basis='lump', p_H2=2.60,
    price_basis='nominal', kappa=1.0``.  Isolated here and flagged by a guard in
    :mod:`timing_model.validate`; it is not a supported configuration.
    """
    return Params().with_policy(kappa=1.0), ScenarioParams(
        u=1.0,
        support_basis="lump",
        p_H2=2.60,
        price_basis="nominal",
        legacy_mode=True,
    )


@dataclass(frozen=True)
class Rung:
    """One rung of the cumulative stress ladder."""

    label: str
    apply_params: Callable[[Params], Params] = lambda p: p
    apply_scenario: Callable[[ScenarioParams], ScenarioParams] = lambda s: s
    note: str = ""


#: Appendix A §4.4.  Each rung is applied ON TOP of every rung above it.
STRESS_LADDER: Final[Sequence[Rung]] = (
    Rung("Base as published", note="u=1, kappa=1, nominal, p_H2=2.60, w=1, lump"),
    Rung(
        "+ load factor u=0.85",
        apply_scenario=lambda s: replace(s, u=0.85),
        note="F2: EU blast furnaces run 0.75-0.85; absence biased the model early",
    ),
    Rung(
        "+ hot metal kappa=0.94",
        apply_params=lambda p: p.with_policy(kappa=0.94),
        note="F5: the 1.248 benchmark is per tonne hot metal, not crude steel",
    ),
    Rung(
        "+ real vs nominal",
        apply_scenario=lambda s: replace(s, price_basis="real"),
        note="F3: r=8% is real; the 76-112 path is nominal",
    ),
    Rung(
        "+ hydrogen at 8.29",
        apply_scenario=lambda s: replace(s, p_H2=8.29),
        note="F1: Platts assessment, Spain, 8 May 2026",
    ),
    Rung(
        "+ resale off (w=0)",
        apply_scenario=lambda s: replace(s, w=0.0),
        note="F6: the policy package is worth -122 rather than +8 without resale",
    ),
    Rung(
        "+ support as stream",
        apply_scenario=lambda s: replace(s, support_basis="stream"),
        note="F4: the Booster pays a premium per tCO2 - a flow, not a stock",
    ),
)


def run_ladder(
    ladder: Sequence[Rung] = STRESS_LADDER,
) -> list[tuple[Rung, Outputs]]:
    """Apply each rung cumulatively and return (rung, outputs) in order."""
    p, sc = published_base()
    out: list[tuple[Rung, Outputs]] = []
    for rung in ladder:
        p = rung.apply_params(p)
        sc = rung.apply_scenario(sc)
        out.append((rung, outputs(p, sc)))
    return out


def sigma_ladder(
    p: Params | None = None, sc: ScenarioParams | None = None
) -> list[tuple[str, Outputs]]:
    """The volatility ladder of Appendix A §3.4, in place of a calibrated sigma(t).

    Above sigma ~ 0.30 the trigger is not crossed in the horizon: Appendix A
    §2.3 reads that as "no bankable case exists without a CfD or equivalent".
    """
    p = p or Params()
    sc = sc or ScenarioParams(u=1.0)
    return [
        (name, outputs(p, replace(sc, sigma_regime=name))) for name in SIGMA_REGIMES
    ]


#: Appendix A §3.2: "waiting never remains free beyond 2030" is true across the
#: three price paths and FALSE across the storylines - geopolitical escalation
#: gives T_exp = 2031.  The claim must be narrowed wherever it appears.
STORYLINES: Final[Mapping[str, Mapping[str, object]]] = {
    "central": {"p_H2": 2.60, "sigma_regime": "long_run", "w": 1.0},
    "cfd_backed": {"p_H2": 2.60, "sigma_regime": "cfd", "w": 1.0},
    "geopolitical_escalation": {"p_H2": 4.50, "sigma_regime": "crisis", "w": 1.0},
    "market_hydrogen": {"p_H2": 8.29, "sigma_regime": "realised", "w": 1.0},
    "resale_restricted": {"p_H2": 2.60, "sigma_regime": "long_run", "w": 0.0},
}
