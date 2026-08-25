"""Reconciliation against the MATLAB reference (``timing_model.m``).

Appendix A open item 1 and §4.3.  Builds the 50 reference cases, runs them in
**legacy mode** (the reference CSV predates the F1-F5 corrections), and diffs a
Python result frame against a MATLAB one.

A reconciliation that can only report agreement is not informative, so
:func:`diff` is exercised by a negative control in the test suite: perturb one
NPV by EUR 5 and one ``T*`` by one year, and exactly two mismatches must be
flagged.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final, Sequence

from timing_model.report import Table
from timing_model.params import Params, ScenarioParams
from timing_model.results import Outputs, outputs
from timing_model.scenarios import legacy_fixture

__all__ = ["Case", "reference_cases", "run_cases", "diff", "Mismatch",
           "NPV_TOL", "SECTORS"]

#: EUR/t capacity.  Tighter than the EUR 5 perturbation of the negative control.
NPV_TOL: Final[float] = 0.5

#: Appendix A §3.3: publish the ORDERING only; the triggers are provisional and
#: have not been through the calibration or units review that steel has.
SECTORS: Final[dict[str, dict[str, float]]] = {
    "steel": {"eps_inc": 1.9, "I0": 900.0},
    "cement": {"eps_inc": 0.85, "I0": 700.0},
    "chemicals": {"eps_inc": 1.3, "I0": 1100.0},
    "aluminium": {"eps_inc": 1.6, "I0": 1250.0},
    "glass": {"eps_inc": 0.6, "I0": 550.0},
}


@dataclass(frozen=True)
class Case:
    """One reference case in the diff grid."""

    name: str
    group: str
    params: Params
    scenario: ScenarioParams


def reference_cases() -> list[Case]:
    """The 50 reference cases of Appendix A §9.2, in legacy mode.

    Groups: base, price paths, asset ages, volatility ladder, +/-20% core
    params, r/mu, load factor, hydrogen ladder, policy vintage, sectors, phi.

    LEGACY MODE.  These were produced under the uncorrected model, so every case
    runs at ``u=1.0, support_basis='lump', p_H2=2.60, price_basis='nominal',
    kappa=1.0``.  Deviations below are the axis under test only.
    """
    p0, s0 = legacy_fixture()
    cases: list[Case] = [Case("base", "base", p0, s0)]

    for tag, scale in (("low", 0.80), ("high", 1.25)):
        cases.append(
            Case(f"price_{tag}", "price paths", p0, replace(s0, price_scale=scale))
        )

    for age in (0.0, 3.0, 6.0, 9.0, 12.0):
        cases.append(
            Case(f"age0_{age:g}", "asset ages", p0.with_sector(age0=age), s0)
        )

    for regime in ("cfd", "long_run", "crisis", "realised"):
        cases.append(
            Case(f"sigma_{regime}", "volatility", p0, replace(s0, sigma_regime=regime))
        )

    core = {
        "I0": (p0.sector.I0, "sector"),
        "K_s": (p0.sector.K_s, "sector"),
        "b_learn": (p0.sector.b_learn, "sector"),
        "rho": (p0.sector.rho, "sector"),
        "s_max": (p0.policy.s_max, "policy"),
        "c_avoided": (p0.sector.c_avoided, "sector"),
    }
    for name, (base, holder) in core.items():
        for tag, mult in (("lo", 0.8), ("hi", 1.2)):
            kw = {name: base * mult}
            pp = p0.with_sector(**kw) if holder == "sector" else p0.with_policy(**kw)
            cases.append(Case(f"{name}_{tag}20", "+/-20% core", pp, s0))

    for r in (0.06, 0.07, 0.09, 0.10):
        cases.append(Case(f"r_{r:.2f}", "r/mu", p0.with_common(r=r), s0))
    for mu in (0.02, 0.03, 0.04):
        cases.append(Case(f"mu_{mu:.2f}", "r/mu", p0.with_common(mu=mu), s0))

    for u in (0.75, 0.80, 0.90):
        cases.append(
            Case(f"u_{u:.2f}", "load factor", p0, replace(s0, u=u, legacy_mode=False))
        )

    for ph2 in (2.00, 3.00, 4.00, 6.00, 8.29):
        cases.append(
            Case(
                f"h2_{ph2:.2f}",
                "hydrogen ladder",
                p0,
                replace(s0, p_H2=ph2, legacy_mode=False),
            )
        )

    for vintage in ("law2023", "com2026"):
        for w in (0.0, 1.0):
            if vintage == "law2023" and w == 1.0:
                continue  # identical to base
            cases.append(
                Case(
                    f"{vintage}_w{w:.0f}",
                    "policy vintage",
                    p0,
                    replace(s0, policy_vintage=vintage, w=w),
                )
            )

    for name, spec in SECTORS.items():
        if name == "steel":
            continue
        pp = p0.with_common(eps_inc=spec["eps_inc"]).with_sector(I0=spec["I0"])
        pp = pp.with_policy(benchmark=spec["eps_inc"])
        cases.append(Case(f"sector_{name}", "sectors (provisional)", pp, s0))

    for phi in (0.0, 0.25, 0.75, 1.0):
        cases.append(Case(f"phi_{phi:.2f}", "phi", p0.with_sector(phi=phi), s0))

    return cases


def run_cases(cases: Sequence[Case] | None = None) -> Table:
    """Run the grid and return the CSV schema the MATLAB diff expects.

    A plain list of records - see :data:`timing_model.report.Table`.
    """
    cases = cases if cases is not None else reference_cases()
    rows: Table = []
    for c in cases:
        o: Outputs = outputs(c.params, c.scenario, gate=False)
        rows.append(
            {
                "case": c.name,
                "group": c.group,
                # -1 encodes "beyond horizon" so the column stays integral for
                # the exact-match comparison in diff().
                "t_star": o.t_star if o.t_star is not None else -1,
                "npv0": round(o.npv0, 6),
                "trigger": round(o.trigger, 6),
                "crossing_year": (
                    o.crossing_year if o.crossing_year is not None else -1
                ),
            }
        )
    return rows


@dataclass(frozen=True)
class Mismatch:
    """One disagreement between the Python and MATLAB result frames."""

    case: str
    field: str
    python: object
    matlab: object

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.case}.{self.field}: python={self.python} matlab={self.matlab}"


def diff(
    python_rows: Table, matlab_rows: Table, npv_tol: float = NPV_TOL
) -> list[Mismatch]:
    """Compare two result frames case by case.

    ``t_star`` and ``crossing_year`` must match exactly; ``npv0`` and
    ``trigger`` within ``npv_tol``.  Cases present in one frame and not the
    other are reported as mismatches rather than skipped.
    """
    out: list[Mismatch] = []
    pi = {str(r["case"]): r for r in python_rows}
    mi = {str(r["case"]): r for r in matlab_rows}
    for case in sorted(set(pi) | set(mi)):
        if case not in pi:
            out.append(Mismatch(case, "case", "missing", "present"))
            continue
        if case not in mi:
            out.append(Mismatch(case, "case", "present", "missing"))
            continue
        a, b = pi[case], mi[case]
        for fld in ("t_star", "crossing_year"):
            if int(a[fld]) != int(b[fld]):
                out.append(Mismatch(case, fld, int(a[fld]), int(b[fld])))
        for fld in ("npv0", "trigger"):
            if abs(float(a[fld]) - float(b[fld])) > npv_tol:
                out.append(Mismatch(case, fld, float(a[fld]), float(b[fld])))
    return out
