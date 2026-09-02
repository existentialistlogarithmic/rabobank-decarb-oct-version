"""Reconciliation harness and its negative control.

Appendix A §4.3.  A reconciliation that can only report agreement is not
informative, so the harness is itself tested for its ability to disagree.
"""

from __future__ import annotations

import pytest

from timing_model.diff_harness import (
    NPV_TOL,
    diff,
    reference_cases,
    run_cases,
)
from timing_model.params import ScenarioParams
from timing_model.scenarios import corrected_base


def test_grid_has_fifty_cases() -> None:
    assert len(reference_cases()) == 50


def test_case_names_are_unique() -> None:
    names = [c.name for c in reference_cases()]
    assert len(set(names)) == len(names)


def test_grid_covers_every_named_axis() -> None:
    groups = {c.group for c in reference_cases()}
    assert groups == {
        "base",
        "price paths",
        "asset ages",
        "volatility",
        "+/-20% core",
        "r/mu",
        "load factor",
        "hydrogen ladder",
        "policy vintage",
        "sectors (provisional)",
        "phi",
    }


def test_grid_runs_in_legacy_mode() -> None:
    """The 50 cases predate the corrections; the diff must not apply them."""
    base = next(c for c in reference_cases() if c.name == "base")
    assert base.scenario.legacy_mode
    assert base.scenario.u == 1.0
    assert base.scenario.support_basis == "lump"
    assert base.scenario.p_H2 == 2.60
    assert base.scenario.price_basis == "nominal"
    assert base.params.policy.kappa == 1.0


def test_diff_of_a_frame_with_itself_is_empty() -> None:
    df = run_cases()
    assert diff(df, df) == []


def test_negative_control_flags_exactly_two_mismatches() -> None:
    """Perturb one NPV by EUR 5 and one T* by one year; both must be flagged."""
    py = run_cases()
    matlab = [dict(r) for r in py]
    for r in matlab:
        if r["case"] == "base":
            r["npv0"] = float(r["npv0"]) + 5.0
        if r["case"] == "sigma_crisis":
            r["t_star"] = int(r["t_star"]) + 1

    found = diff(py, matlab)
    assert len(found) == 2, f"expected exactly 2, got {[str(m) for m in found]}"
    by_field = {m.field: m for m in found}
    assert by_field["npv0"].case == "base"
    assert by_field["npv0"].matlab - by_field["npv0"].python == pytest.approx(5.0)
    assert by_field["t_star"].case == "sigma_crisis"
    assert by_field["t_star"].matlab - by_field["t_star"].python == 1


def test_diff_reports_cases_missing_from_either_side() -> None:
    py = run_cases()
    matlab = [dict(r) for r in py if r["case"] != "base"]
    found = diff(py, matlab)
    assert [m.case for m in found] == ["base"]
    assert found[0].matlab == "missing"


def test_npv_tolerance_is_tighter_than_the_negative_control_perturbation() -> None:
    assert NPV_TOL < 5.0


def test_a_perturbation_inside_tolerance_is_not_flagged() -> None:
    py = run_cases()
    matlab = [dict(r) for r in py]
    for r in matlab:
        if r["case"] == "base":
            r["npv0"] = float(r["npv0"]) + NPV_TOL / 2.0
    assert diff(py, matlab) == []


def test_every_reference_case_yields_a_commitment_year_in_legacy_mode() -> None:
    """Legacy mode keeps every case bankable - which is the point of the rewrite.

    At u=1, nominal prices and kappa=1 even the EUR 8.29/kg hydrogen case still
    shows a commitment year.  The case only disappears once the corrections are
    applied, which is why the ladder and not this grid is the honest headline.
    """
    rows = run_cases()
    assert all(int(r["t_star"]) > 0 for r in rows)


def test_beyond_horizon_is_encoded_as_minus_one_not_dropped() -> None:
    """A case with no commitment year must still appear in the frame, as -1."""
    from dataclasses import replace

    from timing_model.diff_harness import Case

    p, sc = corrected_base()
    hopeless = Case(
        "no_case",
        "probe",
        p,
        replace(sc, p_H2=8.29, price_basis="real"),
    )
    rows = run_cases([hopeless])
    assert len(rows) == 1
    assert rows[0]["t_star"] == -1
    assert rows[0]["crossing_year"] == -1
