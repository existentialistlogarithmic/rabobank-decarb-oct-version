"""The finalised tables: units in every header, and no invented cells.

These tables are the answer to the review comments, so the tests are about the
two things that would make them dishonest rather than merely ugly: a column
without its unit, and a cell filled in where the underlying figure is a
documented hole.
"""

from __future__ import annotations

from analysis import tables
from timing_model.params import Params


def test_every_money_or_quantity_column_declares_its_unit() -> None:
    """A number column without a unit is the defect this module exists to fix.

    Label columns (project, status, source) legitimately have none; anything
    holding a quantity must say what it is measured in.
    """
    unitless_ok = {
        "project", "instrument", "status", "source", "shape", "outcome",
        "quantity", "unit", "comment", "what exists now", "blocked by", "#",
        "state", "cost line", "basis", "legal", "years", "premium",
    }
    for table in tables.all_tables():
        for col in table.columns:
            if col.name.lower() in unitless_ok:
                continue
            assert col.unit, f"{table.title}: column {col.name!r} has no unit"


def test_no_cell_overflows_its_column() -> None:
    """Truncation silently changes a number. Catch it as a layout bug."""
    for table in tables.all_tables():
        for row in table.rows:
            assert len(row) == len(table.columns), table.title
            for col, val in zip(table.columns, row, strict=True):
                text = "" if val is None else str(val)
                assert len(text) <= col.width, (
                    f"{table.title}: {text!r} is {len(text)} chars in a "
                    f"{col.width}-wide column ({col.name})"
                )


def test_headers_do_not_overflow_either() -> None:
    for table in tables.all_tables():
        for col in table.columns:
            assert len(col.name) <= col.width, f"{table.title}: {col.name}"
            assert len(col.unit) <= col.width, f"{table.title}: {col.unit}"


def test_the_absolute_column_is_the_per_tonne_figure_times_the_capacity() -> None:
    """Comment 2. The whole point of the table is that these two agree."""
    from analysis import units

    table = tables.table_npv_units()
    checked = 0
    for label, value, absolute, unit in table.rows:
        if unit != "EUR/t capacity":
            continue
        per_t = float(value.replace(",", ""))
        want = units.eur(units.absolute(per_t, tables.REFERENCE_MT))
        assert absolute == want, f"{label}: {absolute} vs {want}"
        checked += 1
    assert checked >= 5, "the units table lost its EUR/t-capacity rows"


def test_a_price_and_a_flow_are_not_converted_to_a_total() -> None:
    """Only capacity-denominated stocks scale by plant size.

    The trigger is EUR/tCO2 and `a` is EUR/t product/yr. Multiplying either by
    annual tonnes would produce a confident, meaningless number.
    """
    rows = {r[0]: r for r in tables.table_npv_units().rows}
    assert "n/a" in rows["trigger p*'"][2]
    assert "n/a" in rows["opex penalty a"][2]


def test_a_confirmed_project_is_not_reported_as_stopped() -> None:
    """Dunkirk was confirmed in May 2025; an earlier version called it STOPPED.

    `sourced._is_live` answers "is it under construction", which is the right
    question for the capex comparison and the wrong label for this column.
    """
    assert tables.outcome("confirmed") == "CONFIRMED"
    assert tables.outcome("CANCELLED") == "CANCELLED"
    assert tables.outcome("under construction; H2 tender paused") == "BUILDING"
    assert tables.outcome("commissioning") == "BUILDING"
    names = {r[0]: r[-1] for r in tables.table_capex().rows}
    assert names["Dunkirk EAF"] == "CONFIRMED"
    assert names["Bremen + Eisenhuettenstadt"] == "CANCELLED"


def test_the_opex_table_keeps_the_two_hydrogen_routes_apart() -> None:
    """Buying hydrogen and making it on site are alternatives, not additions.

    55 kg/t at 55 kWh/kg is 3,025 kWh/t - the same energy the merchant price
    already pays for. A table that let a reader sum both columns would
    double-count its own largest line.
    """
    table = tables.table_opex()
    labels = [str(r[0]) for r in table.rows]
    assert any("pick ONE" in lbl for lbl in labels)
    assert any(lbl.strip().startswith("OR made on site") for lbl in labels)
    assert any("EITHER/OR" in n for n in table.notes)


def test_missing_cells_are_never_given_a_number() -> None:
    """A hole stays a hole. This is the rule the module is built around."""
    for table in tables.all_tables():
        for row in table.rows:
            for val in row:
                text = str(val) if val is not None else ""
                if tables.MISSING in text:
                    assert text.strip() == tables.MISSING, (
                        f"{table.title}: {text!r} mixes a hole with a value"
                    )


def test_proposals_are_not_presented_as_enacted_law() -> None:
    """COM(2026) 616 is in co-decision. The EUR 100bn is framing, not budget."""
    rows = {str(r[0]): r for r in tables.table_subsidies().rows}
    booster = next(v for k, v in rows.items() if "Booster" in k)
    bank = next(v for k, v in rows.items() if "Decarbonisation Bank" in k)
    assert booster[-1] == "PROPOSAL"
    assert bank[-1] == "PROPOSAL"
    ccfd = next(v for k, v in rows.items() if "Klimaschutz" in k)
    assert ccfd[-1] == "in force"


def test_electricity_is_dearer_than_gas_per_kwh_in_every_state() -> None:
    """Comment 1, answered from observed data rather than assumed.

    If this ever flips, the green-vs-grey hydrogen ordering flips with it and
    several findings need re-reading - so it is pinned rather than assumed.
    """
    table = tables.table_power_vs_gas()
    assert len(table.rows) == 9
    for state, power, gas, ratio, green, grey in table.rows:
        assert float(power) > float(gas), state
        assert float(ratio.rstrip("x")) >= 1.5, state
        assert float(green) > float(grey), f"{state}: green floor below grey"


def test_the_stream_beats_the_lump_at_every_plausible_premium() -> None:
    lump = Params().policy.s_max
    for premium, worth, _absolute, ratio in tables.table_support_shape().rows:
        if premium.startswith("the model"):
            assert float(worth.replace(",", "")) == lump
            continue
        assert float(worth.replace(",", "")) > lump
        assert float(ratio.rstrip("x")) > 1.0


def test_all_five_comments_appear_with_a_status() -> None:
    rows = tables.table_comment_status().rows
    assert [r[0] for r in rows] == ["1", "2", "3", "4", "5"]
    for row in rows:
        assert row[2] in {"DONE", "PARTIAL", "OPEN"}, row
        assert row[3], "every comment needs a statement of what exists"


def test_the_tables_report_without_gating() -> None:
    assert tables.main() == 0
