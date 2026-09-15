"""The sourced-parameter package, and the line between named and checked.

`data/sourced/` carries a research pass that went back to primary documents for
every input the published base case assumes. These tests do two jobs. First,
they pin the arithmetic: the recomputed triggers have to reproduce, or the
comparison is worthless. Second, and more importantly, they stop the package's
figures from quietly acquiring a provenance they do not have - 9% of its rows
carry a working link, and a named source is not a checked one.
"""

from __future__ import annotations

import pytest

from analysis import sourced
from data import sourced as src
from timing_model.params import Params

# --------------------------------------------------------------- the loader

def test_every_table_loads_and_carries_its_provenance_columns() -> None:
    """A row without a source_id is a number from nowhere."""
    for table in src.TABLES:
        rows = src.read(table)
        assert rows, f"{table} is empty"
        for row in rows:
            assert "source_id" in row.fields, f"{table} has no source_id column"
            assert "url" in row.fields, f"{table} has no url column"


def test_every_csv_is_well_formed() -> None:
    """A stray comma shifts every column after it and nothing else notices.

    The package arrived with exactly that: an unquoted comma in a note field of
    `carbon_prices.csv`, which put a fragment of prose into an overflow column.
    Quoting fixed it; this keeps the next one from landing silently.
    """
    import csv

    for table in src.TABLES:
        path = src.DIR / f"{table}.csv"
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            width = len(reader.fieldnames or [])
            for line, row in enumerate(reader, start=2):
                assert None not in row, (
                    f"{table}.csv line {line}: more fields than the {width} "
                    "headers - an unquoted comma shifts every column after it"
                )
                short = [k for k, v in row.items() if v is None]
                assert not short, f"{table}.csv line {line}: missing {short}"


def test_link_coverage_is_reported_and_is_low() -> None:
    """The caveat this whole module exists to preserve.

    If someone captures the missing URLs this test starts failing, which is the
    correct moment to revisit every claim built on these rows and upgrade its
    status from `unverified`. Failing on *improvement* is deliberate.
    """
    got, total = src.link_coverage()
    assert total > 50, "the package shrank; check data/sourced is intact"
    assert got < total * 0.5, (
        f"{got}/{total} rows now carry a URL. If the research pass was "
        "re-run with links captured, re-read docs/research-sources.md and "
        "move the affected claims out of 'unverified'."
    )


def test_a_subsidy_premium_is_never_returned_as_a_price() -> None:
    """The trap the hydrogen table is shaped to prevent.

    European Hydrogen Bank clearing figures are EUR 0.37-3.49/kg. They are
    premiums paid on top of a price, not prices. Feeding one to the opex
    penalty would make hydrogen look an order of magnitude cheaper than it is.
    """
    prices = src.hydrogen_prices()
    assert prices, "the hydrogen price table lost its price rows"
    for row in prices:
        assert row["is_price_or_subsidy"] == "price"
        assert row.num("value") is not None and row.num("value") > 2.0, row["observation"]
    premia = [r for r in src.hydrogen() if r not in prices]
    assert premia, "the subsidy premia disappeared; the distinction is the point"
    for row in premia:
        assert "SUBSIDY" in row["is_price_or_subsidy"]


def test_markers_do_not_parse_as_numbers() -> None:
    """NOT_CAPTURED, PENDING and NOT_DISCLOSED are absences, not values."""
    for _table, row in src.all_rows():
        for key in row.fields:
            raw = row.get(key, "").strip().upper()
            if raw in {"NOT_CAPTURED", "PENDING", "NOT_DISCLOSED"}:
                assert row.num(key) is None, f"{key}={raw} parsed as a number"


# ------------------------------------------------------- the recomputation

@pytest.mark.parametrize(
    ("case", "trigger", "crossing"),
    [("base", 109.5, 2030), ("low", 172.4, 2039),
     ("central", 239.4, 2046), ("high", 460.4, None)],
)
def test_the_sourced_trigger_table_reproduces(
    case: str, trigger: float, crossing: int | None
) -> None:
    """The research pass's own headline table, recomputed by this model.

    It reproduces to a tenth of a euro on all four rows, which is what makes
    the comparison usable: the two sides differ because their inputs differ,
    not because they are two different pieces of arithmetic.
    """
    c = sourced.run_case(case)
    assert c.out.trigger == pytest.approx(trigger, abs=0.1)
    assert c.out.crossing_year == crossing


def test_the_opex_penalty_inverts_cleanly() -> None:
    """`a` and the hydrogen price have to stay the same statement.

    The research quotes `a` directly; the model takes a price and derives `a`
    through eq (14). If the inversion drifted, the sourced cases would be run
    at a hydrogen price that does not correspond to the `a` they cite.
    """
    from timing_model.benefit import opex_penalty
    from timing_model.params import ScenarioParams

    p = Params()
    for case in ("low", "central", "high"):
        a = src.value("a", case)
        _, sc = sourced.case_params(case)
        assert opex_penalty(p, ScenarioParams(u=1.0, p_H2=sc.p_H2)) == pytest.approx(a)


def test_the_published_case_is_still_what_the_model_runs_on() -> None:
    """This module compares; it must never quietly recalibrate.

    Every other page in the build reports the published base case. If importing
    the research changed `Params()`, the validation gate and every published
    figure would move without anybody deciding that they should.
    """
    p = Params()
    assert p.sector.I0 == 900.0
    assert p.sector.rho == 0.35
    assert p.policy.s_max == 200.0
    assert sourced.run_case("base").out.trigger == pytest.approx(109.52, abs=0.01)


# ------------------------------------------------------------- the findings

def test_every_project_still_being_built_costs_more_than_the_model_assumes() -> None:
    """The capex finding, stated so it survives a new row in the CSV.

    The research pass's own prose says EUR 900 'sits below every announced
    transformation project', but its table has Bremen at EUR 700 - a DRI+EAF
    scheme, and cancelled. The defensible claim is about the survivors.
    """
    rows = sourced.capex_by_boundary()
    live = [v for _n, v, _b, s in rows if sourced._is_live(s)]
    dead = [v for _n, v, _b, s in rows if not sourced._is_live(s)]
    assert live and dead
    assert min(live) > Params().sector.I0, "a live project came in under I0"
    assert max(dead) < min(live), "the cancelled/EAF-only set is no longer the cheap one"


def test_support_as_a_stream_is_worth_multiples_of_the_lump() -> None:
    """eq (10). The structural point, not a parameter tweak."""
    lump = Params().policy.s_max
    assert sourced.support_shape(30.0) == pytest.approx(391.0, abs=1.0)
    assert sourced.support_shape(50.0) == pytest.approx(652.0, abs=1.0)
    assert sourced.support_shape(30.0) / lump > 1.9


def test_the_volatility_ladder_spans_the_observed_range() -> None:
    """sigma = 0.20 is a choice. The observed range moves the multiple 5x."""
    ladder = {round(s, 2): (b, m, t) for s, b, m, t in sourced.sigma_ladder()}
    assert ladder[0.10][1] == pytest.approx(2.920, abs=0.005)
    assert ladder[0.20][1] == pytest.approx(3.591, abs=0.005)
    assert ladder[0.45][1] == pytest.approx(6.640, abs=0.005)
    assert ladder[0.54][1] == pytest.approx(8.202, abs=0.005)
    assert ladder[0.83][1] == pytest.approx(14.970, abs=0.01)
    assert ladder[0.45][2] == pytest.approx(202.5, abs=0.1)


def test_the_reline_disagreement_is_carried_not_averaged() -> None:
    """D6. A factor of three, on a term that is a reason to wait."""
    spec_rho, spec_r, src_rho, src_r = sourced.rho_disagreement()
    assert spec_rho == 0.35
    assert 0.08 <= src_rho <= 0.17
    assert spec_r / src_r > 2.5


def test_the_free_allocation_csv_confirms_both_model_schedules() -> None:
    """Independent confirmation of the two vintages the model already carries.

    `f_law2023` is enacted law and matches exactly. `f_com2026` matches too,
    but the CSV marks it RECONSTRUCTED from 2028 - a pending proposal, which is
    a weaker claim than the model's citation currently implies.
    """
    from timing_model.benefit import F_COM2026, F_LAW2023

    reconstructed = 0
    for row in src.free_allocation():
        year = int(row["year"])
        if (law := row.num("f_law2023")) is not None and year in F_LAW2023:
            assert F_LAW2023[year] == pytest.approx(law), year
        if (com := row.num("f_com2026")) is not None and year in F_COM2026:
            assert F_COM2026[year] == pytest.approx(com), year
        if "RECONSTRUCTED" in row["verification_status"]:
            reconstructed += 1
    assert reconstructed, "the proposal/law distinction was lost"


def test_the_comparison_reports_without_gating() -> None:
    """It is a report, not a guard: a disagreement must not fail the run."""
    assert sourced.main() == 0
