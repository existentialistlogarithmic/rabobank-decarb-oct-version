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
from reporting import article, explorer, findings_report, plots, sources, surface

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
