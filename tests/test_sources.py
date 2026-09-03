"""The provenance register must track the model, not describe a past version.

A bibliography is worth nothing if it can fall out of step with the code in
silence.  These tests are the mechanism that stops it: they check the register
against ``timing_model.params`` on every run, and - the part that matters -
they check that the checker itself still catches a planted error.
"""

from __future__ import annotations

import dataclasses

import pytest

from reporting import sources
from timing_model import benefit, params


def test_register_is_clean_against_the_code() -> None:
    """The headline claim of SOURCES.md, asserted rather than printed."""
    assert sources.audit() == []


def test_every_parameter_field_has_provenance() -> None:
    """A new input without a citation is a failure, not an oversight."""
    cited = {c.param for c in sources.REGISTER}
    missing = [
        f"{group}.{f.name}"
        for group, klass in sources._CLASSES.items()
        for f in dataclasses.fields(klass)
        if f"{group}.{f.name}" not in cited
    ]
    assert not missing, f"uncited parameters: {missing}"


def test_no_parameter_is_cited_twice() -> None:
    names = [c.param for c in sources.REGISTER]
    assert len(names) == len(set(names))


def test_every_claim_names_a_real_source_and_status() -> None:
    for c in sources.REGISTER:
        assert c.refs, f"{c.param} cites nothing"
        assert c.status in sources.STATUS, f"{c.param}: {c.status}"
        for ref in c.refs:
            assert ref in sources.SOURCES, f"{c.param} cites {ref}"


def test_no_orphan_bibliography_entries() -> None:
    """An entry nothing cites is a citation to a claim that no longer exists."""
    cited = {ref for c in sources.REGISTER for ref in c.refs}
    assert set(sources.SOURCES) == cited


@pytest.mark.parametrize(
    "bad, expect",
    [
        (sources.Claim("sector.I0", 950.0, "EUR/t", "gate", ("diw2082",), ""),
         "model runs"),
        (sources.Claim("sector.nonexistent", 1.0, "-", "gate", ("diw2082",), ""),
         "does not resolve"),
        (sources.Claim("sector.I0", 900.0, "EUR/t", "vibes", ("diw2082",), ""),
         "unknown status"),
        (sources.Claim("sector.I0", 900.0, "EUR/t", "gate", ("no_such_paper",), ""),
         "unknown source"),
    ],
)
def test_the_audit_catches_a_planted_error(
    monkeypatch: pytest.MonkeyPatch, bad: sources.Claim, expect: str
) -> None:
    """Negative control. A checker nobody has seen fail is not a checker."""
    planted = tuple(c for c in sources.REGISTER if c.param != bad.param) + (bad,)
    monkeypatch.setattr(sources, "REGISTER", planted)
    problems = sources.audit()
    assert any(expect in p for p in problems), problems


def test_a_moved_default_breaks_the_citation(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real failure mode: the model changes and the markdown does not."""
    assert sources.audit() == []

    @dataclasses.dataclass(frozen=True)
    class Moved(params.SectorParams):
        I0: float = 1000.0

    monkeypatch.setitem(sources._CLASSES, "sector", Moved)
    assert any("sector.I0" in p for p in sources.audit())


def test_the_phase_out_ladder_is_pinned_year_by_year() -> None:
    """F_LAW2023 is an input too, and the one most likely to be edited."""
    claim = next(c for c in sources.REGISTER if c.param == "benefit.F_LAW2023")
    assert sources._fmt_schedule(benefit.F_LAW2023) == claim.quoted


def test_unverified_claims_rest_on_an_unreachable_source() -> None:
    """The status has to mean something: no URL, or it is not 'unverified'."""
    flagged = sources.unverified()
    assert flagged, "the open items did not disappear; the register lost them"
    for c in flagged:
        assert any(sources.SOURCES[r].url is None for r in c.refs), c.param


def test_the_platts_assessment_is_never_quoted_as_sourced() -> None:
    """Open item 6. Licensed data taken from the spec, confirmed by nobody."""
    resting_on_platts = [c for c in sources.REGISTER if "platts_h2" in c.refs]
    assert resting_on_platts, "the 8.29 figure dropped out of the register"
    for c in resting_on_platts:
        assert c.status == "unverified", f"{c.param} claims {c.status}"


def test_the_com2026_floor_is_never_quoted_as_sourced() -> None:
    """Open item 7. The mechanism is confirmed; the annex has not been read."""
    for name in ("benefit.COM2026_FLOOR", "benefit.COM2026_FLOOR_YEARS"):
        c = next(c for c in sources.REGISTER if c.param == name)
        assert c.status == "unverified", f"{name} claims {c.status}"


def test_rendered_page_states_the_audit_result_and_cites_everything() -> None:
    text = sources.render()
    assert "**Audit:** clean" in text
    for key in sources.SOURCES:
        assert f"`{key}`" in text, f"{key} missing from the rendered page"
    for c in sources.REGISTER:
        assert f"`{c.param}`" in text, f"{c.param} missing from the rendered page"


def test_outputs_are_not_presented_as_sourceable() -> None:
    """The trap this project keeps having to restate."""
    text = sources.render()
    assert "NPV" in text and "outputs" in text
    assert "only" in text and "inputs can be sourced" in text
