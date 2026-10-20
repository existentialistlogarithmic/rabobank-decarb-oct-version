"""Free allocation after a switch: eq (4) against benchmark x activity accounting."""

from __future__ import annotations

from dataclasses import replace

import pytest

import timing_model.benefit as benefit
import timing_model.objective as objective
from analysis import allocation_check as ac
from timing_model.objective import discount
from timing_model.params import Params, ScenarioParams
from timing_model.results import outputs


def test_the_gap_is_exactly_the_residual_emissions_term() -> None:
    """Coded minus benchmark NPV(T*) = sum over t >= T* of d(t) * u * alpha * eps_cln * p."""
    p, sc = Params(), ScenarioParams(u=1.0)
    o = outputs(p, sc)
    with ac.accounting(ac.benchmark_benefit):
        fixed = outputs(p, sc).npv0
    term = sum(discount(t, p) * ac.residual_term(t, p, sc)
               for t in range(o.t_star, p.common.horizon_end + 1))
    assert o.npv0 - fixed == pytest.approx(term, rel=1e-9)


def test_with_resale_the_rulebook_does_not_move_the_switch_value() -> None:
    coded, fixed = ac.vintage_delta(1.0)
    assert coded == pytest.approx(7.70, abs=0.05)
    assert fixed == pytest.approx(0.0, abs=1e-9)


def test_without_resale_the_rulebook_matters() -> None:
    _coded, fixed = ac.vintage_delta(0.0)
    assert fixed < -100.0


def test_benchmark_accounting_lands_on_the_v11_level() -> None:
    """The published base drifts +1.1% from v11's 1,588; the accounting closes it."""
    with ac.accounting(ac.benchmark_benefit):
        fixed = outputs(Params(), ScenarioParams(u=1.0)).npv0
    assert abs(fixed - 1588.0) < 2.0


def test_the_context_manager_restores_the_model() -> None:
    before = (benefit.annual_benefit, objective.annual_benefit)
    with ac.accounting(ac.benchmark_benefit):
        assert objective.annual_benefit is ac.benchmark_benefit
    assert (benefit.annual_benefit, objective.annual_benefit) == before
    sc = replace(ScenarioParams(u=1.0))
    assert outputs(Params(), sc).npv0 == pytest.approx(1605.9, abs=0.05)
