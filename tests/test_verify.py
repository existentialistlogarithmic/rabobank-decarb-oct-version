"""The verifier, and proof that it would notice.

A checker that always passes is indistinguishable from no checker. So the
load-bearing test here is the negative control: perturb a cell and confirm the
check goes red. Everything else is about the tolerance being the right *kind*
of tolerance - half the last displayed digit, not a fixed percentage.
"""

from __future__ import annotations

import pytest

from analysis import verify


def test_every_number_re_derives_from_its_raw_source() -> None:
    """The headline claim: no cell disagrees with its own primary figures."""
    bad = [c for c in verify.all_checks() if not c.ok]
    assert not bad, [
        f"{c.table} {c.item}: printed {c.printed}, derived {c.derived} ({c.unit})"
        for c in bad
    ]


def test_the_verifier_covers_every_table_that_holds_numbers() -> None:
    """A table nobody checks is a table nobody has verified."""
    covered = {c.table for c in verify.all_checks()}
    for expected in ("gate", "T1 units", "T2 NPV", "T3 capex", "T4 opex",
                     "T5 energy", "T7 support"):
        assert expected in covered, f"nothing re-derives {expected}"
    assert len(verify.all_checks()) > 100


def test_every_check_states_a_unit_and_a_method() -> None:
    """'Right number, wrong unit' is the failure this build exists to catch."""
    for c in verify.all_checks():
        assert c.unit.strip(), f"{c.table} {c.item} has no unit"
        assert c.how.strip(), f"{c.table} {c.item} does not say how it was derived"


# ------------------------------------------------------- the negative control

@pytest.mark.parametrize(
    ("text", "derived", "ok"),
    [
        # Correct renderings at the precision shown.
        ("47", 46.54, True),
        ("47", 47.49, True),
        ("1.8x", 1.8406, True),
        ("EUR 2.2bn", 2.25e9, True),
        ("EUR 652m", 652_219_912.0, True),
        ("1,606", 1605.94, True),
        # Wrong by more than the last displayed digit.
        ("47", 46.2, False),
        ("47", 52.0, False),
        ("1.8x", 1.91, False),
        ("EUR 2.2bn", 2.4e9, False),
        ("EUR 652m", 655_000_000.0, False),
        ("1,606", 1604.9, False),
    ],
)
def test_the_tolerance_is_half_the_last_displayed_digit(
    text: str, derived: float, ok: bool
) -> None:
    """A fixed percentage is the wrong tolerance for a printed figure.

    An earlier version used 0.5% relative and called ten correctly rounded
    cells errors - "EUR 2.2bn" against 2.25e9 is a 2.3% gap and a perfectly
    good rendering. The question is whether the cell round-trips at the
    precision it shows, which is what these cases pin.
    """
    c = verify.Check("t", "i", "unit", text, derived, "how")
    assert c.ok is ok, f"{text!r} vs {derived}: expected ok={ok}"


def test_a_perturbed_cell_is_caught() -> None:
    """The negative control. Without this the suite proves nothing.

    Move a figure by more than its displayed precision and the check must go
    red - separately for a per-tonne rate, an absolute in billions, and a
    dimensionless ratio, because each parses differently.
    """
    for text, derived in (("1,606", 1606.0), ("EUR 4.0bn", 4.0e9),
                          ("2.0x", 2.0), ("0.0716", 0.0716)):
        good = verify.Check("t", "i", "u", text, derived, "how")
        assert good.ok, f"{text} should match {derived}"
        nudged = derived * 1.05 + 1e-6
        bad = verify.Check("t", "i", "u", text, nudged, "how")
        assert not bad.ok, f"{text} vs {nudged} should have been caught"


def test_half_ulp_reads_the_scale_suffix() -> None:
    """bn and m are part of the precision, not decoration."""
    assert verify.half_ulp("EUR 2.2bn") == pytest.approx(0.05e9)
    assert verify.half_ulp("EUR 652m") == pytest.approx(0.5e6)
    assert verify.half_ulp("-EUR 310m") == pytest.approx(0.5e6)
    assert verify.half_ulp("1,606") == pytest.approx(0.5)
    assert verify.half_ulp("0.0716") == pytest.approx(0.00005)
    assert verify.half_ulp("3.9x") == pytest.approx(0.05)


def test_the_capex_per_tonne_is_derived_not_read() -> None:
    """The last disagreement the verifier found, and how it was settled.

    `data/sourced/projects_capex.csv` carries a per-tonne column rounded to two
    or three significant figures, and it disagrees with its own
    absolute-over-capacity by up to 2% - Bremen states 700 against its own 714.
    The table now derives the ratio from the two primary figures, so it is
    self-consistent; `units.round_trip()` still compares the CSV's stated
    column against the derivation as a data-quality check on the source.
    """
    from analysis import tables
    from data import sourced as src

    by_name = {r["project"]: r for r in src.projects()}
    for row in tables.table_capex().rows:
        name = str(row[0])
        if name.startswith("--"):
            continue
        r = by_name[name]
        total, mt = r.num("capex_EUR_absolute"), r.num("capacity_Mt_per_yr")
        assert total and mt
        printed = float(str(row[3]).replace(",", ""))
        assert printed == pytest.approx(total / (mt * 1e6), abs=0.5), name


def test_the_verifier_reports_its_failure_count() -> None:
    """main() returns the number of disagreements so run_all can count them."""
    assert verify.main() == 0
