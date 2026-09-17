"""Every generated page must actually build.

This suite exists because of a real miss: a variable rename passed the linter
and the whole unit suite, then broke three pages at once, because nothing
called their ``main()``. Charts are code. Code that only runs in
``run_all.py`` is code that is tested nowhere.

Each test writes into a temporary directory, so a test run never overwrites the
artefacts at the repo root.
"""

from __future__ import annotations

import pathlib
import unittest.mock as mock

import pytest

from analysis import sourcing
from reporting import (
    article,
    brief,
    deck,
    explorer,
    findings_report,
    plots,
    results,
    sources,
    surface,
)

#: (module, filename, smallest plausible size, a marker only a real page has).
#: The marker differs by page on purpose: charts.html is SVG, findings.html is
#: a prose-and-tables derivation with no figures of its own, surface.html is a
#: canvas. Asserting "<svg" everywhere would have been a test that describes a
#: page nobody built.
PAGES = [
    (plots, "charts.html", 20_000, "<svg"),
    (findings_report, "findings.html", 20_000, "<table"),
    (surface, "surface.html", 10_000, "<canvas"),
    (article, "article.html", 10_000, "<svg"),
    (results, "results.html", 20_000, "<table"),
]


@pytest.fixture(autouse=True)
def _in_tmp_dir(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("module, filename, min_bytes, marker",
                         PAGES, ids=[m.__name__.split(".")[-1] for m, _, _, _ in PAGES])
def test_the_page_builds_and_is_not_a_stub(
    module: object, filename: str, min_bytes: int, marker: str,
    tmp_path: pathlib.Path,
) -> None:
    assert module.main() == 0  # type: ignore[attr-defined]
    out = tmp_path / filename
    assert out.exists(), f"{filename} was not written"
    text = out.read_text(encoding="utf-8")
    assert len(text) > min_bytes, f"{filename} is {len(text)} bytes; a stub"
    assert marker in text, f"{filename} has no {marker}"
    assert "NameError" not in text and "Traceback" not in text


def test_the_explorer_builds(tmp_path: pathlib.Path) -> None:
    """Same check for the explorer, on a reduced grid so the suite stays quick."""
    with mock.patch.object(sourcing, "THETA_STEPS", 3), \
         mock.patch.object(sourcing, "CARBON_MULTIPLES", (1.0, 2.0)):
        assert explorer.main() == 0
    text = (tmp_path / "explorer.html").read_text(encoding="utf-8")
    assert len(text) > 20_000
    assert 'id="payload"' in text and "<svg" in text


def test_the_deck_builds_and_is_timed_for_the_slot(tmp_path: pathlib.Path) -> None:
    """40 minutes means 40 minutes: the timings are data, so they are checked."""
    assert deck.main() == 0
    text = (tmp_path / "deck.html").read_text(encoding="utf-8")
    assert len(text) > 40_000
    slides = deck.build_slides()
    total = sum(s.minutes for s in slides)
    assert 34.0 <= total <= 40.0, f"deck runs {total} min; the slot is 40"
    assert len(slides) >= 15
    assert all(s.notes.strip() for s in slides), "every slide needs a speaker note"
    assert all(0.5 <= s.minutes <= 5.0 for s in slides), "no slide is a whole act"


def test_every_deck_figure_carries_its_equation() -> None:
    """The brief: each graph says which equation produced it and what the
    symbols mean. A figure without one is a picture, not an explanation."""
    for s in deck.build_slides():
        if "<svg" not in s.body:
            continue
        assert "<math" in s.body, f"slide '{s.title}' has a figure but no equation"
        assert "<figcaption" in s.body, f"slide '{s.title}' has an unlabelled figure"


def test_the_deck_defines_the_symbols_it_uses() -> None:
    """Every equation-bearing slide in the model section explains its terms."""
    model_slides = [s for s in deck.build_slides() if s.section == "The model"]
    assert len(model_slides) >= 4
    for s in model_slides:
        assert "table class='sym'" in s.body or 'table class="sym"' in s.body, s.title


def test_the_deck_quotes_the_model_not_a_memory(tmp_path: pathlib.Path) -> None:
    """Headline numbers on the title slide must match a live model run."""
    from timing_model.params import Params, ScenarioParams
    from timing_model.results import outputs

    base = outputs(Params(), ScenarioParams(u=1.0))
    title = deck.build_slides()[0].body
    assert str(base.t_star) in title
    assert f"{base.npv0:,.0f}" in title
    assert str(base.crossing_year) in title


def test_the_charts_show_the_no_investment_case_against_the_switch() -> None:
    """The standing comment, checked on the artefact rather than the intent.

    "Plot also the no-investment scenario, the curve of the investment
    scenario, the trigger point, and how much PV value you recover." All four
    have to be on the page, carrying the model's own numbers - a chart that
    quietly stopped drawing the do-nothing line would still look fine.
    """
    from analysis.regimes import recovery
    from timing_model.scenarios import published_base

    p, sc = published_base()
    rec = recovery(p, sc)
    card = plots.chart_recovery()
    assert f"{rec['do nothing, carbon bill']:,.0f}" in card
    assert f"{rec['share recovered at T*']:.0%}" in card
    assert f"{rec['recovered at the crossing']:,.0f}" in card
    assert "trigger reached" in card
    assert card.count("<path class=\"ln") == 1, "the switch curve is missing"


def test_the_provenance_register_regenerates(tmp_path: pathlib.Path) -> None:
    assert sources.main() == 0
    text = (tmp_path / "SOURCES.md").read_text(encoding="utf-8")
    assert "**Audit:** clean" in text and "## Bibliography" in text


def test_no_page_leaks_a_python_repr(tmp_path: pathlib.Path) -> None:
    """A stray object repr in a page means a format string lost its value.

    Matched on word boundaries: "nan" is a substring of "finance", which is a
    word this project uses a lot.
    """
    import re

    # Shapes a leaked value takes, not the words themselves: "None of that
    # touches the central point" is a sentence, not a formatting bug.
    leaks = (r"<object object", r"0x[0-9a-f]{6,}", r"<class '", r"NoneType",
             r"\bnan\b", r">None<", r"None%", r"None/", r"\u20acNone")
    for module, filename, _, _ in PAGES:
        module.main()  # type: ignore[attr-defined]
        text = (tmp_path / filename).read_text(encoding="utf-8")
        for leak in leaks:
            found = re.search(leak, text)
            assert found is None, (
                f"{filename} leaked {found.group(0)!r} at offset {found.start()}"
                f": ...{text[max(0, found.start() - 60):found.start() + 60]}...")


def test_every_chart_declares_the_unit_of_its_axes() -> None:
    """The complaint this answers: a EUR axis that does not say EUR of what.

    Three charts shipped with bare labels - "change in NPV", "change in
    trigger", "dNPV / du" - so a reader could not tell a percentage from a
    euro. Every axis title must now name a unit, a dimensionless index, or a
    year.
    """
    import re

    page = plots.build()
    labels = re.findall(r'class="axt[^"]*"[^>]*>([^<]+)</text>', page)
    assert len(labels) >= 12, f"only {len(labels)} axis titles found"
    unit_words = ("EUR", "%", "year", "index", "kWh", "kg", "tCO2", "rate r",
                  "Mt", "tonne")
    for label in labels:
        assert any(w in label for w in unit_words), f"axis {label!r} has no unit"


def test_the_review_comment_charts_are_on_the_page() -> None:
    """Each comment that has a table now also has a picture.

    A table answers the question; a chart is what gets looked at. These four
    were tables only until someone asked where the graphs were.
    """
    page = plots.build()
    for heading in ("Capex: what the announced projects actually cost",
                    "Opex: the cost lines, and the ones the model leaves out",
                    "Is electricity cheaper than gas",
                    "Subsidy: a stream is not a lump"):
        assert heading in page, f"missing chart: {heading}"


def test_the_capacity_charts_say_annual_capacity_not_just_eur() -> None:
    """EUR/t of ANNUAL capacity is the distinction the whole units pass is for.

    An axis reading "EUR per tonne" would re-open exactly the misreading that
    made EUR 900 look like pocket change.
    """
    for chart in (plots.chart_capex_projects(), plots.chart_support_shape()):
        assert "ANNUAL capacity" in chart
    assert "steel PRODUCT" in plots.chart_opex_stack()


def test_the_money_context_travels_with_the_per_tonne_charts() -> None:
    """A per-tonne bar without its absolute is the original complaint again."""
    from analysis import units

    capex = plots.chart_capex_projects()
    assert units.eur(units.absolute(900.0, 2.5)) in capex
    support = plots.chart_support_shape()
    assert units.eur(units.absolute(200.0, 2.5)) in support


def test_the_results_page_explains_every_table_it_prints() -> None:
    """A table on the page without a written explanation defeats its purpose.

    `section()` raises on a missing GUIDE entry rather than rendering a bare
    table, so this catches a new table added without the three questions
    answered - which is the failure mode the page exists to prevent.
    """
    from analysis import tables as tbl

    for t in tbl.all_tables():
        assert t.name in results.GUIDE, f"{t.name} has no GUIDE entry"
        for key in ("look", "read", "means"):
            assert results.GUIDE[t.name][key].strip(), f"{t.name}: empty {key}"


def test_every_table_has_an_indicative_handle() -> None:
    """The handles are how a reader points at a table across a room."""
    from analysis import tables as tbl

    names = [t.name for t in tbl.all_tables()]
    assert len(names) == len(set(names)), f"duplicate handles: {names}"
    for name in names:
        assert name.startswith("T"), name
        assert len(name.split()) >= 2, f"{name!r} is a number, not a handle"


def test_the_page_links_the_sources_it_can_and_flags_the_rest() -> None:
    """Both halves matter: real links, and an honest marker where none exists."""
    page = results.build()
    assert "https://www.diw.de" in page, "a live model-register link is missing"
    assert "named but not linked" in page, "unlinked sources are not being flagged"
    assert "unverified" in page and "sourced" in page


def test_the_npv_money_table_is_on_the_page_with_billions() -> None:
    """The question that prompted the page: how much money is the NPV."""
    from analysis import tables as tbl
    from analysis import units

    page = results.build()
    assert "T2 NPV in money" in page
    for case in ("base", "central"):
        npv = tbl.sourced.run_case(case).out.npv0
        assert units.eur(units.absolute(npv, tbl.REFERENCE_MT)) in page


def test_the_brief_builds_and_stays_short(tmp_path: pathlib.Path) -> None:
    """Two pages is the whole point of the brief. Length is a feature."""
    assert brief.main() == 0
    page = (tmp_path / "brief.html").read_text(encoding="utf-8")
    assert len(page) < 20_000, "the brief is growing into a report"
    assert "<table" in page and "per tonne of annual nameplate" in page


def test_the_brief_leads_with_money_not_a_rate() -> None:
    """Someone reading this once needs the total, not EUR/t of capacity."""
    from analysis import sourced as an_sourced
    from analysis import tables as tbl
    from analysis import units

    page = brief.build()
    for case in ("base", "central"):
        npv = an_sourced.run_case(case).out.npv0
        assert units.eur(units.absolute(npv, tbl.REFERENCE_MT)) in page


def test_the_brief_states_what_is_not_checked() -> None:
    """A two-page summary that drops the caveats is worse than no summary."""
    page = brief.build()
    for caveat in ("Provenance", "Operating costs", "No tax layer",
                   "No MATLAB reference"):
        assert caveat in page, f"the brief dropped: {caveat}"
    assert "unverified" in page


def test_the_brief_quotes_the_live_verification_count() -> None:
    """The count must come from running the checks, not from memory."""
    from analysis import verify as vf

    n = len(vf.all_checks())
    assert f"{n}/{n} agree" in brief.build()
