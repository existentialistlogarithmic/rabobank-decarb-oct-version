"""gallery.py -> gallery.html: every figure and table, titles and nothing else.

The contact sheet. All sixteen figures in argument order, then all ten tables,
with a sticky index over the lot - and no explanatory words anywhere: no
section ledes, no chart caption sentences, no notes under the plots. Each item
carries its title and a link to its full explanation in ``explained.html``,
and that is the whole page.

"No words" is enforced rather than intended. :func:`titles_only` strips the
two prose shapes ``plots.py`` bakes into every chart before the chart is
placed, and a test fails if either survives. Stripping rather than hiding with
CSS is deliberate: hidden text is still in the file, and "no words" should
mean no words.

What stays: the caption heading, the legend, the axis labels and the table
view under each chart. A legend is identity, an axis label is a unit, and a
table view is the data - none of them explains anything, and removing them
would make the figures unreadable rather than uncluttered.

Nothing here is new work. The figures come from ``figures.FIGURES`` and the
tables from ``analysis.tables.all_tables()`` via ``results.table_html``, so no
content lives only on this page and the three pages cannot drift apart.
Anchors match ``results.html``, so ``gallery.html#T3-capex`` and
``results.html#T3-capex`` are the same table.

The two interactive figures are linked rather than inlined: the 3D fleet
surface needs a canvas and a drag handler, and the frontier explorer embeds
891 model runs.
"""

from __future__ import annotations

import re
from typing import Final

from analysis import tables
from reporting import figures, plots, results

OUT: Final[str] = "gallery.html"

#: The two figures that are interactive rather than static, and therefore
#: linked from here rather than copied into it.
INTERACTIVE: Final[tuple[tuple[str, str, str], ...]] = (
    ("surface.html", "The fleet surface",
     "NPV over asset age and hydrogen price for the whole European fleet, on a "
     "canvas you can rotate. Drag to turn it; the peak ridge is the set of "
     "plants where timing is live right now."),
    ("explorer.html", "The sourcing frontier",
     "891 model runs embedded, with the hydrogen price and the clean-route "
     "emission intensity moved together as the single physical input they "
     "actually are. Pick a point and the whole result set updates."),
)

CSS: Final[str] = """
.wrap{max-width:1180px}
.toc-rail{position:sticky;top:0;z-index:5;background:var(--bg);
border-bottom:1px solid var(--line);margin:0 0 26px;padding:10px 0 9px}
.toc-rail ol{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;
gap:6px 16px;font-size:13px}
.toc-rail a{color:var(--mut);text-decoration:none;border-bottom:1px solid transparent}
.toc-rail a:hover{color:var(--acc);border-bottom-color:var(--acc)}
.toc-rail .sec{font-weight:600;color:var(--ink);cursor:default}
.grp{margin:0 0 10px;padding-top:6px}
.grp h2{margin:0 0 4px;font-size:20px}
.grp p{margin:0 0 18px;color:var(--mut);max-width:70ch;font-size:15px}
.qline{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;
margin:0 0 8px;padding-top:26px}
.qline .q{font-size:15px;font-weight:600}
.qline a.why{font-size:12px;color:var(--acc);text-decoration:none;
border:1px solid var(--line);border-radius:999px;padding:2px 9px;white-space:nowrap}
.qline a.why:hover{border-color:var(--acc)}
.links{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
gap:14px;margin:8px 0 0}
.links a.tile{display:block;padding:15px 17px;border:1px solid var(--line);
border-radius:10px;background:var(--card);text-decoration:none;color:inherit}
.links a.tile:hover{border-color:var(--acc)}
.links b{display:block;color:var(--acc);margin:0 0 5px}
.links span{color:var(--mut);font-size:14px}
.tbl{padding:16px 18px 12px;background:var(--card);border:1px solid var(--line);
border-radius:14px;margin:0 0 22px}
.tbl .tag{display:inline-block;font:600 11px/1 ui-monospace,monospace;
color:var(--mut);border:1px solid var(--line);border-radius:4px;
padding:3px 7px;margin:0 0 12px}
.scroll{overflow-x:auto;margin:0 -2px}
.tbl table{border-collapse:collapse;width:100%;font-size:13.5px}
.tbl th,.tbl td{padding:6px 10px;text-align:right;white-space:nowrap;
border-bottom:1px solid var(--line)}
.tbl th:first-child,.tbl td:first-child{text-align:left}
.tbl thead th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;
color:var(--mut);font-weight:600}
.tbl thead tr.u th{text-transform:none;letter-spacing:0;font-weight:400;
font-style:italic;border-bottom:2px solid var(--line)}
.tbl tbody tr:hover{background:rgba(127,127,127,.07)}
.tbl td.miss{color:var(--warn);font-weight:600}
@media (max-width:700px){.toc-rail ol{gap:5px 12px;font-size:12px}}
"""


#: The two prose shapes ``plots.py`` bakes into every chart: the sentence under
#: the caption heading, and the note paragraphs under the plot. This page shows
#: titles only, so both are removed at render rather than hidden with CSS -
#: hiding them would leave the words in the file, and "no words" should mean no
#: words. The heading itself, the legend and the axis labels stay: a legend is
#: identity and an axis label is a unit, and neither is an explanation.
_CAPTION_PROSE: Final = re.compile(r"(<figcaption>.*?</h3>)<p>.*?</p>", re.S)
_NOTE = re.compile(r'<p class="note">.*?</p>', re.S)


def titles_only(html: str) -> str:
    """One chart with its explanatory prose removed, title intact."""
    return _NOTE.sub("", _CAPTION_PROSE.sub(r"\1", html))


def contents() -> str:
    """A sticky rail of every figure, grouped, that follows the reader down."""
    items: list[str] = []
    for name, _lede, figs in figures.by_section():
        items.append(f'<li class="sec">{plots.esc(name)}</li>')
        items.extend(
            f'<li><a href="#{plots.esc(f.key)}">{plots.esc(f.title)}</a></li>'
            for f in figs
        )
    items.append(f'<li class="sec">{plots.esc(figures.TABLE_SECTION[0])}</li>')
    items.extend(
        f'<li><a href="#{plots.esc(figures.table_anchor(t.name))}">'
        f"{plots.esc(t.name)}</a></li>"
        for t in tables.all_tables()
    )
    return f'<nav class="toc-rail"><ol>{"".join(items)}</ol></nav>'


def build() -> str:
    """Every figure and table, in argument order, under its title and nothing else."""
    body: list[str] = []
    for name, _lede, figs in figures.by_section():
        body.append(f'<section class="grp"><h2>{plots.esc(name)}</h2></section>')
        for f in figs:
            body.append(
                f'<div class="qline" id="{plots.esc(f.key)}">'
                f'<span class="q">{plots.esc(f.title)}</span>'
                f'<a class="why" href="explained.html#{plots.esc(f.key)}">'
                "explain &rarr;</a></div>"
                + titles_only(f.draw())
            )

    name, _lede = figures.TABLE_SECTION
    body.append(f'<section class="grp"><h2>{plots.esc(name)}</h2></section>')
    for t in tables.all_tables():
        anchor = figures.table_anchor(t.name)
        body.append(
            f'<div class="qline" id="{plots.esc(anchor)}">'
            f'<span class="q">{plots.esc(t.name)}</span>'
            f'<a class="why" href="explained.html#{plots.esc(anchor)}">'
            "explain &rarr;</a></div>"
            f'<div class="card tbl">{results.table_html(t)}</div>'
        )

    tiles = "".join(
        f'<a class="tile" href="{plots.esc(href)}"><b>{plots.esc(title)}</b></a>'
        for href, title, _note in INTERACTIVE
    )
    body.append(
        '<section class="grp" id="interactive"><h2>Interactive</h2></section>'
        f'<div class="links">{tiles}</div>'
    )

    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Investment timing - every figure and table</title>"
        f"<style>{plots.CSS}{figures.THEME_BRIDGE}{CSS}</style></head><body><div class=\"wrap\">"
        "<h1>Every figure and table</h1>"
        + contents() + "".join(body) +
        "<footer>Explanatory framework, not investment advice. "
        "Every figure and table here is explained in full in "
        "<code>explained.html</code>.</footer>"
        f'</div><script>{plots.JS}</script></body></html>'
    )


def main() -> int:
    """Write gallery.html next to the other generated pages."""
    problems = figures.check_complete()
    if problems:
        for p in problems:
            print(f"  registry problem: {p}")
        return 1
    page = build()
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"Wrote {OUT} ({len(figures.FIGURES)} figures + "
          f"{len(tables.all_tables())} tables, {len(page) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
