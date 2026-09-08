"""Parameter objects for the investment-timing model.

Part 4 §4.1. Every field carries unit, currency-year and source in its
``metadata`` so that a units review (Appendix A, open item 5) can be run
mechanically rather than by reading prose.

Unit discipline
---------------
The single largest class of error in this project is per-tonne-**capacity**
against per-tonne-**product**:

* ``I0``, ``K_s``, ``s_max`` and every NPV are **EUR per tonne of annual
  capacity**.
* ``a``, ``B(t)`` and the carbon terms are **EUR per tonne of product**.
* :attr:`ScenarioParams.u` is the *only* bridge between the two.  See
  :func:`timing_model.benefit.annual_benefit`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Final, Literal

__all__ = [
    "Meta",
    "CommonParams",
    "SectorParams",
    "PolicyParams",
    "ScenarioParams",
    "Params",
    "SupportBasis",
    "PriceBasis",
    "PolicyVintage",
    "SIGMA_REGIMES",
    "ModelError",
]

SupportBasis = Literal["lump", "stream"]
PriceBasis = Literal["nominal", "real"]
PolicyVintage = Literal["law2023", "com2026"]


class ModelError(ValueError):
    """Raised by :mod:`timing_model.validate` when a guard binds.

    Guards raise; they never return a flag (Appendix A §3.6, §4.3).
    """


def Meta(unit: str, ccy_year: str | None, source: str) -> Mapping[str, str]:
    """Field metadata: unit, currency-year tag, provenance.

    ``ccy_year`` is ``None`` for dimensionless or non-monetary fields.
    Appendix A §3.6 requires a currency-year tag on every monetary input.
    """
    return {"unit": unit, "ccy_year": ccy_year or "n/a", "source": source}


#: Volatility ladder (Appendix A §3.4, §4.4 axis 3).  Deliberately a ladder
#: rather than a calibrated sigma(t): each rung is defensible line by line.
SIGMA_REGIMES: Final[Mapping[str, float]] = {
    "cfd": 0.10,
    "long_run": 0.20,
    "crisis": 0.30,
    "realised": 0.45,
}


@dataclass(frozen=True)
class CommonParams:
    """Discounting, horizon and emission intensities. Group I / IV."""

    r: float = field(
        default=0.08, metadata=Meta("1/yr, real", None, "July theory note; WACC proxy")
    )
    mu: float = field(
        default=0.05, metadata=Meta("1/yr", None, "GBM drift of the EUA price")
    )
    sigma: float = field(
        default=0.20,
        metadata=Meta("1/yr^0.5", None, "long-run rung of the ladder, Appendix A §3.4"),
    )
    t0: int = field(default=2026, metadata=Meta("year", None, "discounting base"))
    horizon_end: int = field(
        default=2050,
        metadata=Meta("year", None, "Appendix A §3.6: horizon explicitly 2050"),
    )
    eps_inc: float = field(
        default=1.9,
        metadata=Meta("tCO2/t product", None, "Appendix A F9; blast-furnace route"),
    )
    eps_cln: float = field(
        default=0.1,
        metadata=Meta("tCO2/t product", None, "Appendix A F9; H2-DRI-EAF route"),
    )
    crf_years: int = field(
        default=25, metadata=Meta("yr", None, "asset life used for the MAC diagnostic")
    )


@dataclass(frozen=True)
class SectorParams:
    """Capex, incumbent asset and the operating-penalty primitives. Group I / III."""

    I0: float = field(
        default=900.0,
        metadata=Meta("EUR/t capacity", "2022", "DIW capex, 2022 euros"),
    )
    K_s: float = field(
        default=600.0,
        metadata=Meta(
            "EUR/t capacity",
            "2022",
            "v11 base-case table. Confirmed by the specification's own age "
            "ladder: 'each year of age removes EUR 30 of residual book value', "
            "i.e. K_s / L_s = 30",
        ),
    )
    L_s: float = field(
        default=20.0,
        metadata=Meta(
            "yr",
            None,
            "blast-furnace campaign life between relines; 15-20 typical, "
            "21 achieved at thyssenkrupp Schwelgern 1993-2014",
        ),
    )
    age0: float = field(
        default=8.0,
        metadata=Meta(
            "yr",
            None,
            "v11 reference plant: 'already eight years into a twenty year "
            "life'. Puts T_rel = 2038 and reproduces all four rows of the "
            "specification's age ladder exactly",
        ),
    )
    rho: float = field(
        default=0.35,
        metadata=Meta(
            "share of K_s",
            None,
            "v11 base-case table: reline cost 25 to 50 per cent of book. "
            "rho*K_s = EUR 210/t capacity",
        ),
    )
    phi: float = field(
        default=0.5,
        metadata=Meta("share of S_s", None, "share of write-off charged to the decision"),
    )
    m_H2: float = field(
        default=55.0, metadata=Meta("kg H2/t product", None, "Appendix A Group I eq (2)")
    )
    c_avoided: float = field(
        default=83.0,
        metadata=Meta("EUR/t product/yr", "2022", "coke and PCI avoided, eq (2)"),
    )
    b_learn: float = field(
        default=0.234,
        metadata=Meta("dimensionless", None, "Wright exponent, ~15% learning rate"),
    )
    gamma: float = field(
        default=0.4442,
        metadata=Meta(
            "1/yr",
            None,
            "cumulative H2-DRI capacity growth. THE ONE CALIBRATED CONSTANT; "
            "sourced band 0.43-0.52 from EU H2-DRI-EAF 2.5 Mt (2025) -> "
            "15-20 Mt (2030). Implies capex falling 8.2%/yr",
        ),
    )


@dataclass(frozen=True)
class PolicyParams:
    """Free allocation and the support schedule. Group II / III."""

    benchmark: float = field(
        default=1.9,
        metadata=Meta("tCO2/t product", None, "BM(t); see kappa for the hot-metal fix"),
    )
    kappa: float = field(
        default=1.0,
        metadata=Meta("dimensionless", None, "Appendix A F5; 0.94 corrects hot metal"),
    )
    s_max: float = field(
        default=200.0,
        metadata=Meta(
            "EUR/t capacity", "2022", "Investment Booster envelope, published base"
        ),
    )
    support_start: int = field(
        default=2028, metadata=Meta("year", None, "Booster window opens")
    )
    lam: float = field(
        default=0.0,
        metadata=Meta(
            "1/yr",
            None,
            "q(t) rationing slope. Zero: the mechanism exists but does not "
            "bind over the base-case decision window",
        ),
    )
    q_min: float = field(
        default=0.0, metadata=Meta("share", None, "rationing floor, Appendix A eq (6)")
    )
    stream_years: int = field(
        default=10, metadata=Meta("yr", None, "CCfD premium tenor under the stream basis")
    )
    stream_premium: float = field(
        default=40.0,
        metadata=Meta("EUR/tCO2", "2022", "Booster premium, Appendix A F4 (30-50)"),
    )


@dataclass(frozen=True)
class ScenarioParams:
    """The seven axes of Appendix A §4.4, plus the legacy-diff switch."""

    p_H2: float = field(
        default=2.60,
        metadata=Meta("EUR/kg", "2022", "Appendix A §3.5(3) - UNRESOLVED base case"),
    )
    w: float = field(
        default=1.0,
        metadata=Meta("0 or 1", None, "resale switch; §3.5(2) - UNRESOLVED base case"),
    )
    sigma_regime: str = field(
        default="long_run", metadata=Meta("key of SIGMA_REGIMES", None, "§3.4 ladder")
    )
    support_basis: SupportBasis = field(
        default="lump",
        metadata=Meta("lump|stream", None, "§3.5(1) - UNRESOLVED base case"),
    )
    price_basis: PriceBasis = field(
        default="nominal", metadata=Meta("nominal|real", None, "Appendix A F3")
    )
    policy_vintage: PolicyVintage = field(
        default="law2023", metadata=Meta("law2023|com2026", None, "Appendix A F8")
    )
    u: float = field(
        default=0.85,
        metadata=Meta("share", None, "load factor, Appendix A F2; EU BF run 0.75-0.85"),
    )
    price_scale: float = field(
        default=1.0,
        metadata=Meta("multiplier", None, "low/central/high EUA path, §9.2 diff grid"),
    )
    deflator: float = field(
        default=0.02, metadata=Meta("1/yr", None, "used only when price_basis='real'")
    )
    legacy_mode: bool = field(
        default=False,
        metadata=Meta("flag", None, "DIFF FIXTURE ONLY - reproduces the uncorrected model"),
    )

    def resolved_sigma(self) -> float:
        """Volatility implied by :attr:`sigma_regime`."""
        try:
            return SIGMA_REGIMES[self.sigma_regime]
        except KeyError as exc:
            raise ModelError(
                f"unknown sigma_regime {self.sigma_regime!r}; "
                f"expected one of {sorted(SIGMA_REGIMES)}"
            ) from exc


@dataclass(frozen=True)
class Params:
    """The full parameter bundle handed to every Group II-V function."""

    common: CommonParams = field(default_factory=CommonParams)
    sector: SectorParams = field(default_factory=SectorParams)
    policy: PolicyParams = field(default_factory=PolicyParams)

    def with_common(self, **kw: object) -> Params:
        """Return a copy with ``kw`` applied to :attr:`common`."""
        return replace(self, common=replace(self.common, **kw))

    def with_sector(self, **kw: object) -> Params:
        """Return a copy with ``kw`` applied to :attr:`sector`."""
        return replace(self, sector=replace(self.sector, **kw))

    def with_policy(self, **kw: object) -> Params:
        """Return a copy with ``kw`` applied to :attr:`policy`."""
        return replace(self, policy=replace(self.policy, **kw))
