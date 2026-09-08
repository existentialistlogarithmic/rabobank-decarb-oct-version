"""The conditional-outputs mechanic.

The recurring failure in this project is that results get quoted without their
conditions.  These tests make that mechanically impossible: a table that would
print ``t_star`` or ``trigger`` without them must raise.
"""

from __future__ import annotations

import dataclasses

import pytest

from timing_model.params import ModelError
from timing_model.report import HEADLINE_FIELDS, render_table, results_table, row
from timing_model.results import CONDITION_KEYS, Outputs, outputs
from timing_model.scenarios import published_base, run_ladder


def _bare() -> Outputs:
    """An Outputs with no conditions - the thing the report layer must refuse."""
    return Outputs(
        t_star=2029, t_exp=2029, npv0=1605.9, trigger=109.52, crossing_year=2030
    )


def test_outputs_is_frozen() -> None:
    o = _bare()
    with pytest.raises(dataclasses.FrozenInstanceError):
        o.t_star = 2030  # type: ignore[misc]


def test_row_refuses_an_outputs_with_no_conditions() -> None:
    with pytest.raises(ModelError, match="without its conditions"):
        row("bare", _bare())


def test_table_refuses_an_outputs_with_no_conditions() -> None:
    with pytest.raises(ModelError, match="without its conditions"):
        render_table([("bare", _bare())])


@pytest.mark.parametrize("missing", CONDITION_KEYS)
def test_every_single_missing_condition_is_caught(missing: str) -> None:
    p, sc = published_base()
    good = outputs(p, sc)
    partial = dict(good.conditions)
    partial[missing] = ""
    broken = dataclasses.replace(good, conditions=partial)
    with pytest.raises(ModelError, match=missing):
        row("partial", broken)


def test_a_real_result_carries_every_condition() -> None:
    p, sc = published_base()
    o = outputs(p, sc)
    assert set(CONDITION_KEYS) <= set(o.conditions)
    assert all(o.conditions[k] for k in CONDITION_KEYS)


def test_rendered_table_prints_the_conditions_alongside() -> None:
    text = render_table([(r.label, o) for r, o in run_ladder()])
    assert "Conditions" in text
    for token in ("h2_price", "sigma_regime", "resale", "price_basis", "support_basis"):
        assert token in text


def test_rendered_table_prints_binding_guards() -> None:
    """Guards reach the page. The ladder itself no longer binds the capex clamp.

    It used to, because support ran flat to 2050 while capex fell with
    learning, so eventually support exceeded gross capex. Under the
    specification's schedule (v11 eq 10) support is gone by 2035 and the clamp
    never binds on the published ladder - so the clamp is exercised here on a
    scenario built to bind it, rather than on a row that only bound by accident.
    """
    from timing_model.params import Params, ScenarioParams
    from timing_model.results import outputs

    text = render_table([(r.label, o) for r, o in run_ladder()])
    assert "Binding guards" in text

    rich = Params().with_policy(s_max=5000.0)
    o = outputs(rich, ScenarioParams(u=1.0))
    assert any("clamp binds" in g for g in o.binding_guards), o.binding_guards
    assert "clamp binds" in render_table([("clamped", o)])


def test_headline_fields_are_the_ones_that_need_guarding() -> None:
    assert {"t_star", "trigger"} == HEADLINE_FIELDS
    table = results_table([(r.label, o) for r, o in run_ladder()])
    for k in CONDITION_KEYS:
        assert all(f"cond_{k}" in r for r in table)


def test_the_three_unresolved_decisions_are_visible_in_every_row() -> None:
    """Appendix A §3.5 - support basis, resale, and whether 2.60 is the base case.

    Option (b) of §3.5(3) is defensible only if the label is on every table,
    not in a footnote.  So: on every row.
    """
    table = results_table([(r.label, o) for r, o in run_ladder()])
    for key in ("cond_h2_price", "cond_resale", "cond_support_basis"):
        assert all(r[key] for r in table), f"{key} empty on some row"
        assert all(len(str(r[key])) > 0 for r in table)
