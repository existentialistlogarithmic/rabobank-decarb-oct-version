"""The specification is the reference. This checks we still agree with it.

`analysis/reconcile.py` encodes what the v11 specification published - inputs
as well as outputs - and compares. These tests pin the state of that comparison
so a drift in either direction is visible: a row that starts passing is as
interesting as one that stops.
"""

from __future__ import annotations

import pytest

from analysis import reconcile
from timing_model.params import Params


def test_every_published_input_matches_the_model() -> None:
    """v11 §1. The parameter table is the part nothing used to check.

    K_s = 1200 with age0 = 14 gave the right S_s(2026) and the wrong value in
    every other year; it survived because only outputs were compared.
    """
    bad = [r for r in reconcile.check_parameters(Params()) if not r.ok]
    assert not bad, [f"{r.item}: spec {r.published}, model {r.computed}" for r in bad]


def test_the_validation_table_reproduces() -> None:
    """v11 §3, all nine quantities."""
    from timing_model.params import ScenarioParams

    bad = [r for r in reconcile.check_gate(Params(), ScenarioParams(u=1.0)) if not r.ok]
    assert not bad, [r.item for r in bad]


def test_the_age_ladder_reproduces_exactly() -> None:
    """v11 §4.3, twelve values across four ages.

    This is what pins the incumbent-asset block: reinvestment year, trigger and
    crossing year for ages 2, 8, 14 and 20. Nothing else in the specification
    constrains K_s and age0 separately.
    """
    from timing_model.params import ScenarioParams

    rows = reconcile.check_age_ladder(Params(), ScenarioParams(u=1.0))
    assert len(rows) == 12
    bad = [r for r in rows if not r.ok]
    assert not bad, [f"{r.item}: spec {r.published}, model {r.computed}" for r in bad]


def test_both_allocation_schedules_match_the_annex() -> None:
    """v11 eq (11) and (12), factor by factor. Closes the old open item 7."""
    bad = [r for r in reconcile.check_allocation_schedules() if not r.ok]
    assert not bad, [r.item for r in bad]


def test_the_support_envelope_matches_equation_nine_branch_by_branch() -> None:
    """v11 eq (9). Nothing checked this schedule, and a branch went missing.

    The code returned zero before the Booster window where the specification
    has `0.35 * s_max` for the Innovation Fund and national aid. The published
    step from 2027 to 2028 is EUR 130; with the branch missing the model had
    EUR 200 there, and so paid the plant EUR 70/t to wait one more year.
    """
    from timing_model.params import ScenarioParams

    bad = [r for r in reconcile.check_support_envelope(Params(), ScenarioParams(u=1.0))
           if not r.ok]
    assert not bad, [f"{r.item}: spec {r.published}, model {r.computed}" for r in bad]


def test_support_is_never_zero_inside_the_published_window() -> None:
    """The branch that went missing, asserted directly rather than by table.

    Stated as a property so it survives a rewrite of `support()`: from 2026 to
    2034 inclusive the specification funds *something*, and 2035 is the first
    year it funds nothing.
    """
    from timing_model.cost import SUPPORT_END, support
    from timing_model.params import ScenarioParams

    p, sc = Params(), ScenarioParams(u=1.0)
    for t in range(p.common.t0, SUPPORT_END):
        assert support(t, p, sc) > 0.0, f"s({t}) is zero inside the window"
    assert support(SUPPORT_END, p, sc) == 0.0


def test_learning_converts_years_to_doublings_rather_than_counting_them() -> None:
    """The spec's own hand check conflates the two; the model must not.

    v11 eq (2) works `2**(-b_l * n)` over n *doublings* and gets 0.614 at three
    of them. The eq (11) hand check then reuses 0.62 for a commitment three
    *years* out, which would need capacity to double every year. The model
    converts through the deployment growth rate instead: three years at
    gamma = 0.444 is 1.59 doublings, giving L(2029) = 0.773, not 0.62. Pinned
    so nobody 'corrects' the model towards the arithmetic in the companion.
    """
    import math

    from timing_model.cost import learning

    p = Params()
    years = 3
    doublings = years * math.log2(1.0 + p.sector.gamma)
    assert doublings == pytest.approx(1.59, abs=0.01)
    assert learning(p.common.t0 + years, p) == pytest.approx(
        2.0 ** (-p.sector.b_learn * doublings), rel=1e-12)
    assert learning(p.common.t0 + years, p) == pytest.approx(0.7726, abs=5e-4)


def test_every_commitment_year_reproduces() -> None:
    """Across price paths, support cases and policy vintages.

    The timing is what the model is for, and it reproduces everywhere the
    specification published a year - including the two cases where the year
    differs from the base (soft prices give 2030, rationing gives 2028).
    """
    bad = [r for r in reconcile.all_rows()
           if r.item.endswith(("commit", "crossed", "reinvestment due")) and not r.ok]
    assert not bad, [f"{r.section} {r.item}" for r in bad]


def test_the_disagreements_are_npv_levels_and_nothing_else() -> None:
    """Eight rows differ. Every one is a level, none is a year or a threshold.

    Pinned deliberately: if a *year* ever starts disagreeing, that is a
    different and much worse problem than a level running one per cent high.
    """
    failing = [r for r in reconcile.all_rows() if not r.ok]
    assert failing, "if everything reproduces, update this test and CALIBRATION.md"
    for r in failing:
        assert "NPV" in r.item, f"{r.section} {r.item} is not an NPV level"


def test_every_npv_level_is_judged_by_the_same_tolerance() -> None:
    """The bug this guards: two tolerances made the same comparison pass and fail.

    Published 1,588 against a computed 1,606 appeared as a pass under §4.2 and
    a difference under §3, because the base case used 5 and the scenario rows
    used 25. Whatever ``NPV_TOL`` is set to, one number decides all of them.
    """
    levels = [r for r in reconcile.all_rows() if r.item.endswith("NPV")]
    assert len(levels) == 8
    for r in levels:
        gap = abs(float(r.computed.replace(",", "")) - float(r.published.replace(",", "")))
        assert r.ok == (gap <= reconcile.NPV_TOL), f"{r.section} {r.item} gap {gap}"


def test_the_reconciliation_reports_without_gating() -> None:
    """It is a report, not a guard: a difference must not fail the run."""
    assert reconcile.main() == 0


def test_the_npv_levels_run_high_by_about_one_per_cent() -> None:
    """Quantified so it cannot quietly drift into something worse."""
    from timing_model.params import ScenarioParams
    from timing_model.results import outputs

    npv = outputs(Params(), ScenarioParams(u=1.0)).npv0
    assert npv == pytest.approx(1605.9, abs=0.5)
    assert 0.005 < (npv - 1588.0) / 1588.0 < 0.02
