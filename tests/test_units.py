"""The denominator, and what happens when it goes missing.

`I0 = 900` read as "EUR 900" is absurd; read as "EUR 900 per tonne of annual
capacity" it is EUR 2.2bn for a 2.5 Mt/yr works. Same number. This module
exists because the second reading is the only one that can be sanity-checked,
and the build kept printing the first.
"""

from __future__ import annotations

import pytest

from analysis import units
from data import sourced as src
from timing_model.params import Params


def test_capacity_tonnes_cancel_exactly() -> None:
    """The bridge is multiplication, not an estimate.

    EUR/t of annual capacity times annual tonnes is money, with the denominator
    cancelling. Anything that made this approximate would mean the model's unit
    discipline had a hole in it.
    """
    assert units.absolute(900.0, 2.5) == pytest.approx(2.25e9)
    assert units.absolute(1.0, 1.0) == pytest.approx(1e6)
    assert units.absolute(0.0, 4.0) == 0.0
    # Linear in both arguments, so any size follows from any other.
    assert units.absolute(900.0, 5.0) == pytest.approx(2 * units.absolute(900.0, 2.5))


def test_the_round_trip_recovers_the_per_tonne_figures() -> None:
    """Announced total / announced capacity = the EUR/t the model uses.

    This is the demonstration that settles "900 of what": every per-tonne
    figure in the data came from a real absolute number divided by a real
    capacity, so the two are the same statement.

    The tolerance is 3% because the source table rounds. Four of the five rows
    agree to better than 0.5%; Bremen is the outlier at 2%, where EUR 2.5bn
    over 3.5 Mt is 714 and the table states 700 - two significant figures, not
    a different number.
    """
    rows = units.round_trip()
    assert len(rows) >= 4, "the projects table lost rows"
    loose = 0
    for name, total, mt, stated, recomputed in rows:
        assert total > 1e8, f"{name}: an announced capex under EUR 100m is suspect"
        assert 0.5 < mt < 20.0, f"{name}: {mt} Mt/yr is not a steel plant"
        assert recomputed == pytest.approx(stated, rel=0.03), name
        if recomputed != pytest.approx(stated, rel=0.005):
            loose += 1
    assert loose <= 1, (
        f"{loose} rows disagree by more than 0.5%. One rounded row is expected; "
        "several means a capacity or a total is wrong, not rounded."
    )


def test_money_is_printed_at_a_scale_a_reader_can_hold() -> None:
    assert units.eur(2.25e9) == "EUR 2.2bn"
    assert units.eur(5e8) == "EUR 500m"
    assert units.eur(900.0) == "EUR 900"
    assert units.eur(-3.1e8) == "-EUR 310m"
    assert units.eur(0.0) == "EUR 0"


def test_every_reference_plant_is_a_real_announced_project() -> None:
    """No invented round numbers: the denominators are operators' own figures."""
    plants = units.reference_plants()
    assert plants, "the reference set is empty"
    capacities = {r.num("capacity_Mt_per_yr") for r in src.projects()}
    for name, mt in plants:
        assert mt in capacities, f"{name} is not in projects_capex.csv"
        assert f"{mt:g} Mt/yr" in name, "the size belongs in the label"


def test_the_headline_stocks_all_carry_a_money_figure() -> None:
    """Every EUR/t-capacity stock the build quotes, with its total.

    If a new stock is reported without passing through here, it goes out as a
    bare rate again - which is the failure this module was written for.
    """
    table = units.headline_in_money(2.5)
    for key in ("capex I0 (before learning)", "support s(T*)",
                "reline R = rho*K_s", "NPV of switching at T*"):
        assert key in table, key
    per_t, total = table["capex I0 (before learning)"]
    assert per_t == Params().sector.I0
    assert total == pytest.approx(units.absolute(per_t, 2.5))


def test_the_model_npv_exceeds_what_a_real_plant_of_that_size_cost() -> None:
    """The sanity check the units make possible, stated as a test.

    Stegra's Boden is 2.5 Mt/yr and cost EUR 6.5bn. The published base case
    says the switch alone is worth EUR 4.0bn on a plant of that size, against
    a modelled spend of EUR 2.2bn. Putting the denominator back is what makes
    that comparison available at all - and it is the substance of the review
    comment that the NPV cannot be right.
    """
    boden = next(r for r in src.projects() if r["project"] == "Boden")
    built = boden.num("capex_EUR_absolute")
    mt = boden.num("capacity_Mt_per_yr")
    assert built and mt
    _per_t, model_capex = units.headline_in_money(mt)["capex I0 (before learning)"]
    _per_t, model_npv = units.headline_in_money(mt)["NPV of switching at T*"]
    assert model_capex < built, (
        "the model's capex is no longer below what Boden actually cost; "
        "the recalibration note in CALIBRATION.md needs revisiting"
    )
    assert model_npv > model_capex, "the published case's NPV/capex ratio moved"


def test_the_units_reference_reports_without_gating() -> None:
    assert units.main() == 0
