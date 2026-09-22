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
    explained,
    explorer,
    findings_report,
    gallery,
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
    (gallery, "gallery.html", 40_000, "<svg"),
    (explained, "explained.html", 60_000, "<svg"),
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


def test_the_brief_carries_the_live_market_section() -> None:
    """The brief is the page most people read, so the live check belongs on it.

    All three rows, with the volatility one named as the consequential one -
    it is the only live observation that changes the timing answer.
    """
    page = brief.build()
    assert "Does it still hold today?" in page
    for row in ("Carbon price.", "Volatility", "The pot."):
        assert row in page, f"the brief dropped the {row} row"
    assert "not a path to 2050" in page, "the no-recalibration caveat is missing"


def test_the_brief_stays_two_pages_of_content() -> None:
    """Length is the feature, and the live section is what nearly broke it.

    The PDF is printed by Chromium and its page count cannot be asserted
    without it, so the proxy is the rendered size: the section pushed the HTML
    past two A4 pages once already and the typography had to be tightened.
    """
    assert len(brief.build()) < 11_000


def test_the_brief_quotes_the_live_verification_count() -> None:
    """The count must come from running the checks, not from memory."""
    from analysis import verify as vf

    n = len(vf.all_checks())
    assert f"{n}/{n} agree" in brief.build()


# ------------------------------------------- the figure registry and its pages

def test_the_registry_is_complete() -> None:
    """A chart with no explanation is the failure both new pages exist to stop.

    `check_complete` is what makes that structural rather than a matter of
    remembering: it fails on a duplicate key, a chart in plots.py that nobody
    registered, an answer too short to be an answer, and a question that is not
    a question.
    """
    from reporting import figures

    assert not figures.check_complete()


def test_every_chart_in_plots_is_registered() -> None:
    """The specific drift this prevents: a sixteenth chart and a fifteen-chart page."""
    from reporting import figures, plots

    charted = {n for n in dir(plots) if n.startswith("chart_")}
    registered = {f.draw.__name__ for f in figures.FIGURES}
    assert charted == registered, charted ^ registered


def test_every_figure_states_what_it_does_not_show() -> None:
    """The row that earns the explainer. Enforced, because it is the skippable one."""
    from reporting import figures

    for f in figures.FIGURES:
        assert len(f.not_shown.split()) >= 12, f.key


def test_every_figure_carries_a_full_explanation() -> None:
    """300 words each, because below that an explanation states the conclusion
    and skips the mechanism - which is the failure these pages exist to fix."""
    from reporting import figures

    for f in figures.FIGURES:
        assert f.words() >= figures.MIN_WORDS, f"{f.key}: {f.words()} words"


def test_every_table_carries_a_full_explanation() -> None:
    """The same floor for tables, counted over the typed theory and the notes.

    The derived halves - the column list and the citation block - carry the
    rest, so only these two are prose somebody had to write.
    """
    from analysis import tables as tbl
    from reporting import figures

    for t in tbl.all_tables():
        theory = figures.TABLE_THEORY.get(t.name)
        assert theory is not None, t.name
        words = len(theory.split()) + sum(len(str(n).split()) for n in t.notes)
        assert words >= figures.MIN_WORDS, f"{t.name}: {words} words"


def test_the_theory_is_not_a_restatement_of_the_caption() -> None:
    """A theory row that repeated the caption would pass the word count.

    Checked by requiring the mechanism's own vocabulary: each figure's theory
    has to name something the caption does not - an equation, an estimator, a
    parameter, an identity.
    """
    from reporting import figures

    machinery = ("beta", "Bellman", "annuity", "derivative", "discount",
                 "Spearman", "efficiency", "denominator", "increment",
                 "boundary", "identity", "allocation", "auction", "option",
                 "variance", "index", "constant", "correction")
    for f in figures.FIGURES:
        assert any(w in f.theory for w in machinery), f.key
        assert f.theory != f.what_it_means, f.key


def test_the_gallery_holds_every_figure_on_one_page(tmp_path: pathlib.Path) -> None:
    """The complaint: the graphs were spread across five files."""
    from reporting import figures, gallery

    assert gallery.main() == 0
    page = (tmp_path / "gallery.html").read_text(encoding="utf-8")
    assert page.count("<svg") >= len(figures.FIGURES)
    for f in figures.FIGURES:
        assert f'id="{f.key}"' in page, f.key
        # Titles, not questions: the gallery carries no explanatory words.
        assert f.title in page, f.key
    for href, _title, _note in gallery.INTERACTIVE:
        assert href in page, f"{href} is not linked from the gallery"


def test_the_explainer_answers_all_five_questions_per_figure(
    tmp_path: pathlib.Path,
) -> None:
    from analysis import tables as tbl
    from reporting import explained, figures

    assert explained.main() == 0
    page = (tmp_path / "explained.html").read_text(encoding="utf-8")
    for f in figures.FIGURES:
        assert f'id="{f.key}"' in page, f.key
        for label, _text in f.explanation():
            assert label in page, f"{f.key}: {label}"
    # Every figure AND every table gets the same six parts.
    assert page.count("What it does NOT show") == (
        len(figures.FIGURES) + len(tbl.all_tables()))
    assert page.count("The theory behind it") == (
        len(figures.FIGURES) + len(tbl.all_tables()))


def test_the_explainer_holds_the_tables_as_well_as_the_figures(
    tmp_path: pathlib.Path,
) -> None:
    """The request this answers: one page with both, fully explained.

    Before this, gallery.html and explained.html were graphs only and
    results.html was tables only - so nothing had both, and the reader had to
    know which file to open.
    """
    from analysis import tables as tbl
    from reporting import explained, figures

    page = explained.build()
    for t in tbl.all_tables():
        anchor = figures.table_anchor(t.name)
        assert f'id="{anchor}"' in page, t.name
        # Escaped, not raw: several titles contain an apostrophe.
        assert plots.esc(t.title) in page, t.name
    assert page.count('class="card tbl"') == len(tbl.all_tables())


def test_a_table_in_the_explainer_carries_its_sources(tmp_path: pathlib.Path) -> None:
    """A table's "where the numbers come from" is its citation list.

    That is the part a figure mostly cannot supply and a table always can, so
    it is the reason the tables belong on this page rather than only on
    results.html.
    """
    from analysis import tables as tbl
    from reporting import explained

    page = explained.build()
    sourced = [t for t in tbl.all_tables() if t.sources]
    assert len(sourced) >= 5
    assert page.count("<h4>Sources</h4>") == len(sourced)
    assert "https://" in page, "no live source link reached the page"


def test_the_table_shape_line_is_derived_not_typed() -> None:
    """Generated from t.columns, so a renamed column cannot go stale."""
    from analysis import tables as tbl
    from reporting import explained

    t = next(x for x in tbl.all_tables() if x.name == "T3 capex")
    shape = explained.table_shape(t)
    assert f"{len(t.rows)} rows" in shape
    for col in t.columns:
        assert col.name in shape, col.name
        if col.unit:
            assert col.unit in shape, col.unit


def test_the_gallery_holds_the_tables_too(tmp_path: pathlib.Path) -> None:
    """"Which one has all the graphs AND tables" - this one, and the explainer."""
    from analysis import tables as tbl
    from reporting import figures, gallery

    page = gallery.build()
    for t in tbl.all_tables():
        assert f'id="{figures.table_anchor(t.name)}"' in page, t.name
    assert page.count('class="card tbl"') == len(tbl.all_tables())


def test_the_table_anchors_match_the_results_page() -> None:
    """A link into any of the three pages must land on the same table.

    results.html builds its ids by the same rule; if either side changes it,
    every cross-page link silently stops resolving - the page still loads, it
    just ignores the fragment.
    """
    from analysis import tables as tbl
    from reporting import figures, results

    page = results.build()
    for t in tbl.all_tables():
        assert f"id='{figures.table_anchor(t.name)}'" in page, t.name


def test_the_explainer_leads_with_the_three_denominators(
    tmp_path: pathlib.Path,
) -> None:
    """Units first, because no per-figure caption fixes that misreading later."""
    from reporting import explained

    page = explained.build()
    for unit, _what, _note in explained.UNITS:
        assert unit in page, unit
    assert "EUR 2.2bn" in page, "the worked conversion for I0 is missing"


def test_the_two_pages_cross_link(tmp_path: pathlib.Path) -> None:
    """Each is useless without the other; the links are how a reader finds out."""
    from reporting import explained, figures, gallery

    assert "explained.html" in gallery.build()
    assert "gallery.html" in explained.build()
    first = figures.FIGURES[0].key
    assert f"explained.html#{first}" in gallery.build()


def test_no_reST_literal_leaks_into_either_page() -> None:
    """The explanations use the docstring convention; the pages must not show it.

    Written in double backticks so they read in the source as well as in the
    browser, and rendered to <code> spans. A leaked ``literal`` means the
    rendering path was skipped somewhere.
    """
    import re

    from reporting import explained, gallery

    for name, page in (("gallery", gallery.build()), ("explained", explained.build())):
        leaked = re.findall(r"``[^`\n]{1,60}``", page)
        assert not leaked, f"{name}.html shows reST literals: {leaked[:3]}"
    assert "<code>" in explained.build()


def test_the_new_pages_do_not_collide_with_the_chart_stylesheet() -> None:
    """`.band` is an SVG shading class in plots.CSS at 7% opacity.

    Both pages first used it for their section headings, which rendered them
    invisible - present, correct, and unreadable. This pins the specific
    collision rather than the general rule, because the general rule is not
    checkable and this one bit.
    """
    from reporting import explained, gallery, plots

    assert ".band{" in plots.CSS, "the collision this guards moved; re-check both pages"
    for name, css in (("gallery", gallery.CSS), ("explained", explained.CSS)):
        assert ".band" not in css, f"{name}.CSS reuses a plots.CSS class name"


def test_the_gallery_carries_titles_and_no_explanatory_prose() -> None:
    """"Only titles" means the words are gone, not hidden with CSS.

    The three prose shapes that would otherwise ride along: the sentence under
    each chart's caption heading, the note paragraphs under the plot, and the
    section ledes. Legends, axis labels and the table views stay - a legend is
    identity and an axis label is a unit, and neither explains anything.
    """
    import re

    from analysis import tables as tbl
    from reporting import figures, gallery

    page = gallery.build()
    assert '<p class="note">' not in page, "chart notes survived into the gallery"
    assert "</h3><p>" not in page, "a caption paragraph survived into the gallery"
    for _name, lede in figures.SECTIONS:
        assert lede not in page, "a section lede survived into the gallery"
    assert figures.TABLE_SECTION[1] not in page

    # But every title is present, and so is every figure and table.
    assert len(re.findall(r"<figcaption><h3>", page)) == len(figures.FIGURES)
    for f in figures.FIGURES:
        assert f.title in page, f.key
    for t in tbl.all_tables():
        assert t.name in page, t.name


def test_stripping_prose_leaves_the_chart_intact() -> None:
    """The negative control for titles_only: it must remove words, not marks."""
    from reporting import gallery, plots

    full = plots.chart_npv()
    bare = gallery.titles_only(full)
    assert "<svg" in bare and bare.count("<path") == full.count("<path")
    assert "NPV by commitment year" in bare, "the title was stripped too"
    assert "<p class=\"note\">" not in bare
    assert len(bare) < len(full), "nothing was removed"
