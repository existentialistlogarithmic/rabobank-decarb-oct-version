"""The scenario map and the counterfactual the sensitivity note asked for."""

from __future__ import annotations

import pytest

from analysis import regimes
from timing_model.params import Params, ScenarioParams

BASE = (Params(), ScenarioParams(u=1.0))


def test_doing_nothing_has_a_price_and_it_is_large() -> None:
    """The number the model never printed: the bill the zero line hides."""
    bill = regimes.no_investment_pv(*BASE)
    given = regimes.free_allocation_pv(*BASE)
    assert bill > 0 and given > 0
    assert bill > given, "the incumbent pays more than it is handed"
    rec = regimes.recovery(*BASE)
    assert 0.0 < rec["share recovered at T*"] < 1.0


def test_free_allocation_and_the_carbon_bill_cross_over() -> None:
    """Comment 2: show the allowances, not just the price.

    They start worth more than the bill and end worth nothing, and the year
    they cross is the year the carbon price starts being a cost rather than a
    transfer.
    """
    rows = regimes.allocation_table(*BASE)
    given = {t: g for t, _p, _f, g, _paid in rows}
    paid = {t: pd for t, _p, _f, _g, pd in rows}
    assert given[2026] > paid[2026], "free allocation should dominate early"
    assert paid[2035] > given[2035], "and be gone by the mid-2030s"
    crossover = min(t for t in given if paid[t] > given[t])
    assert 2028 <= crossover <= 2032, crossover


def test_every_regime_name_has_a_code_and_a_rank() -> None:
    assert set(regimes.CODES) == set(regimes.REGIMES)
    assert len({regimes.CODES[r] for r in regimes.REGIMES}) == len(regimes.REGIMES)


def test_the_base_case_invests_at_the_window() -> None:
    r = regimes.classify(*BASE)
    assert r.name == "invest at the window"
    assert r.t_star == 2029 and r.reason


def test_expensive_hydrogen_kills_the_case() -> None:
    """The regime has to be able to say no, or it is not a classification."""
    r = regimes.classify(Params(), ScenarioParams(u=1.0, p_H2=8.29))
    assert r.name == "no investment"
    assert r.t_star is None


def test_a_high_enough_carbon_price_pulls_it_to_now() -> None:
    r = regimes.classify(Params(), ScenarioParams(u=1.0, price_scale=2.0))
    assert r.name == "invest now"
    assert r.t_star == Params().common.t0


def test_the_map_has_a_frontier_not_one_colour() -> None:
    """A map where every cell says the same thing is not a map.

    Drawn on the corrected configuration for exactly this reason.
    """
    grid = regimes.regime_grid()
    names = {cell.name for row in grid for cell in row}
    assert len(names) >= 2, names
    assert "no investment" in names


def test_the_map_is_monotone_in_both_directions() -> None:
    """Cheaper hydrogen never makes the case worse; nor does a higher price.

    If this fails the map is not readable as a frontier and something in the
    classification is non-monotone.
    """
    xs = (2.0, 3.5, 5.0, 6.5, 8.29)
    ys = (0.4, 0.6, 1.0, 1.5, 2.0, 3.0)
    grid = regimes.regime_grid("p_H2", "price_scale", xs, ys)
    for row in grid:                       # dearer hydrogen, weakly worse
        ranks = [c.rank for c in row]
        assert ranks == sorted(ranks, reverse=True), ranks
    for col in zip(*grid, strict=True):    # higher carbon price, weakly better
        ranks = [c.rank for c in col]
        assert ranks == sorted(ranks), ranks


@pytest.mark.parametrize("label", [
    "carbon price a year late",
    "free allocation a year longer",
    "fossil fuel +30 per cent",
])
def test_each_what_if_is_answered(label: str) -> None:
    rows = {lab: (reg, delta) for lab, reg, delta in regimes.what_ifs()}
    assert label in rows
    reg, _delta = rows[label]
    assert reg.name in regimes.REGIMES


def test_a_late_carbon_price_costs_value_and_longer_allocation_adds_it() -> None:
    """The signs are the finding, and they are not both what you would guess.

    Delay costs. A longer free allocation *helps* the switcher, because with
    resale on the allowances are an asset - the policy-neutrality result of
    finding 1, arriving from a different direction.
    """
    rows = {lab: delta for lab, _reg, delta in regimes.what_ifs()}
    assert rows["carbon price a year late"] < 0
    assert rows["free allocation a year longer"] > 0
    assert rows["fossil fuel +30 per cent"] > 0


def test_the_what_ifs_change_no_registered_default() -> None:
    before = (Params(), ScenarioParams())
    regimes.what_ifs()
    assert (Params(), ScenarioParams()) == before
