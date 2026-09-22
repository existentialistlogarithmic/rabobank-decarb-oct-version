"""explained.py -> explained.html: every figure and table, explained in full.

``gallery.html`` is the contact sheet - everything, nothing between the items.
This is the opposite: the same sixteen figures and the same ten tables, each
followed by everything a reader needs to not misread it. It is the one page
that has all of it.

Five questions per item, always in the same order, because that is the order
people actually ask them: what am I looking at, where do the numbers come from,
how do I read it, what does it mean, and what does it NOT show. The fifth is
the one that earns the page. Every figure and every table in this build has a
boundary - a comparison that is not like-for-like, a row that does not
reproduce, a cell the research pass could not fill - and one without its
boundary stated gets over-read every time.

Figures and tables fill those five parts from different places, which is the
point rather than an inconsistency:

* a **figure** carries typed prose in ``figures.FIGURES``, because its axes and
  its reading procedure cannot be derived from the drawing;
* a **table** fills them from structured data it already has - its columns and
  units give "what am I looking at", its citation list gives "where the numbers
  come from", and its own notes give the boundary. Only the middle two are
  prose, read from ``results.GUIDE``, the same dict ``results.html`` renders,
  so the two pages cannot disagree about what a table means.

That asymmetry is also why the tables belong here at all: a table can name the
document behind each figure, and most charts cannot.
"""

from __future__ import annotations

from typing import Final

from analysis import tables, units
from reporting import figures, plots, results
from timing_model.params import Params
from timing_model.results import outputs
from timing_model.scenarios import published_base

OUT: Final[str] = "explained.html"

#: The three denominators every figure on the page is in one of. Printed once,
#: up front, because mixing them up is the single most common misreading in the
#: build and no per-figure caption can fix it retrospectively.
UNITS: Final[tuple[tuple[str, str, str], ...]] = (
    ("EUR / t capacity",
     "a stock: capex, support, the NPV itself",
     "Per tonne of ANNUAL nameplate capacity. Multiply by annual tonnes and "
     "the denominator cancels exactly - this is the only one of the three that "
     "converts to a total."),
    ("EUR / t product / yr",
     "a flow: the opex penalty, energy lines",
     "Per tonne of steel actually made, per year. Does NOT scale with plant "
     "size the way a stock does, and must never be added to one."),
    ("EUR / tCO2",
     "a price: the carbon path, the trigger",
     "Per tonne of CO2. A price, not a quantity of money the plant holds. It "
     "has no plant-size conversion at all."),
)

CSS: Final[str] = """
.wrap{max-width:900px}
.toc{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:18px 22px;margin:0 0 30px}
.toc h4{margin:14px 0 6px;font-size:11px;text-transform:uppercase;
letter-spacing:.05em;color:var(--mut)}
.toc h4:first-child{margin-top:0}
.toc ol{margin:0;padding-left:20px}
.toc li{margin:4px 0}
.toc a{color:var(--acc);text-decoration:none}
.toc a:hover{text-decoration:underline}
.toc .q{color:var(--mut)}
.grp{border-top:2px solid var(--ink);margin:46px 0 0;padding:14px 0 0}
.grp h2{margin:0 0 5px;font-size:21px}
.grp p{margin:0;color:var(--mut);max-width:70ch}
.fig{margin:34px 0 0}
.fig .head{margin:0 0 10px}
.fig .head .n{font:600 11px/1 ui-monospace,monospace;color:var(--mut);
border:1px solid var(--line);border-radius:4px;padding:3px 6px;margin-right:9px}
.fig .head .q{font-size:17px;font-weight:600}
.why{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:6px 22px 16px;margin:16px 0 0}
.why dl{display:grid;grid-template-columns:200px 1fr;gap:2px 20px;margin:0}
.why dt{color:var(--mut);font-size:12px;text-transform:uppercase;
letter-spacing:.04em;padding:13px 0 0;border-top:1px solid var(--line)}
.why dd{margin:0;padding:13px 0 0;border-top:1px solid var(--line);
max-width:66ch;line-height:1.55}
.why dl>dt:first-of-type,.why dl>dt:first-of-type+dd{border-top:0}
.why dd.warn{color:var(--warn)}
.units{width:100%;border-collapse:collapse;margin:0 0 30px;font-size:14px}
.units th,.units td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);
vertical-align:top}
.units thead th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;
color:var(--mut)}
.units code{color:var(--acc);white-space:nowrap}
.units td:last-child{color:var(--mut)}
.tbl{padding:16px 18px 12px}
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
.why .srcs{margin:0}
.why .srcs h4{margin:0 0 6px;font-size:11px;text-transform:uppercase;
letter-spacing:.05em;color:var(--mut)}
.why .srcs ul{margin:0;padding-left:18px}
.why .srcs li{margin:3px 0}
.why .srcs code{font-size:12px}
.why .srcs a{color:var(--acc)}
.why .srcs .nolink{color:var(--warn)}
.why .srcs .note{font-size:13px;color:var(--mut);margin:8px 0 0}
.top{font-size:12px;color:var(--mut);text-decoration:none;margin-left:10px}
.top:hover{color:var(--acc)}
@media (max-width:760px){.why dl{grid-template-columns:1fr;gap:0}
.why dt{padding-top:14px}.why dd{padding-top:3px;border-top:0}}
"""


def units_table() -> str:
    """The three denominators, once, before any figure is shown."""
    rows = "".join(
        f"<tr><td><code>{plots.esc(u)}</code></td><td>{plots.esc(what)}</td>"
        f"<td>{figures.inline(note)}</td></tr>"
        for u, what, note in UNITS
    )
    return ('<table class="units"><thead><tr><th>unit</th><th>what it measures</th>'
            f"<th>what it does</th></tr></thead><tbody>{rows}</tbody></table>")


def contents() -> str:
    """Numbered contents, grouped, each entry carrying the question it answers."""
    parts: list[str] = ['<nav class="toc">']
    n = 0
    for name, _lede, figs in figures.by_section():
        parts.append(f"<h4>{plots.esc(name)}</h4><ol>")
        for f in figs:
            n += 1
            parts.append(
                f'<li value="{n}"><a href="#{plots.esc(f.key)}">'
                f"{plots.esc(f.title)}</a> &mdash; "
                f'<span class="q">{plots.esc(f.question)}</span></li>')
        parts.append("</ol>")

    name, _lede = figures.TABLE_SECTION
    parts.append(f"<h4>{plots.esc(name)}</h4><ol>")
    for t in tables.all_tables():
        n += 1
        parts.append(
            f'<li value="{n}"><a href="#{plots.esc(figures.table_anchor(t.name))}">'
            f"{plots.esc(t.name)}</a> &mdash; "
            f'<span class="q">{plots.esc(t.title)}</span></li>')
    parts.append("</ol></nav>")
    return "".join(parts)


def section(fig: figures.Figure, number: int) -> str:
    """One figure, then the five answers. The last one is styled as a warning.

    The fifth row is deliberately the visually loudest: it is the one a reader
    skips, and it is the one that stops the figure being quoted for something
    it does not support.
    """
    rows = []
    for label, text in fig.explanation():
        warn = ' class="warn"' if label.startswith("What it does NOT") else ""
        rows.append(f"<dt>{plots.esc(label)}</dt>"
                    f"<dd{warn}>{figures.inline(text)}</dd>")
    return (
        f'<div class="fig" id="{plots.esc(fig.key)}">'
        f'<div class="head"><span class="n">{number:02d}</span>'
        f'<span class="q">{plots.esc(fig.question)}</span>'
        f'<a class="top" href="#top">top &uarr;</a></div>'
        + fig.draw()
        + f'<div class="why"><dl>{"".join(rows)}</dl></div></div>'
    )


def table_shape(t: tables.Table) -> str:
    """What the reader is looking at, derived from the table rather than typed.

    Generated from ``t.columns`` so it cannot go stale: a column renamed or a
    unit changed shows up here on the next build. Typing this sentence out per
    table would have been four lines shorter and wrong within a month.
    """
    cols = ", ".join(
        f"<b>{plots.esc(c.name)}</b>"
        + (f" ({plots.esc(c.unit)})" if c.unit else "")
        for c in t.columns
    )
    missing = sum(
        1 for row in t.rows for v in row
        if str(v).strip() == tables.MISSING
    )
    gap = ("" if not missing else
           f" {missing} cell{'s' if missing != 1 else ''} "
           f"read <b>{tables.MISSING}</b>: the research pass looked and did "
           "not find them, and they are left empty rather than estimated.")
    return (f"{len(t.rows)} rows. Columns, with the unit each is measured in: "
            f"{cols}.{gap}")


def table_section(t: tables.Table, number: int) -> str:
    """One table, then the same five answers the figures get.

    The mapping is deliberate rather than cosmetic. A table's "where the
    numbers come from" is its citation list, which every table already carries
    and most figures do not; its "what it does NOT show" is its own notes,
    which are where the MISSING markers and the not-comparable warnings live.
    So the five parts are filled from structured data the table already has,
    and the only prose read from ``results.GUIDE`` is the middle two - the same
    text ``results.html`` shows, from the same dict, so the two pages cannot
    disagree about what a table means.
    """
    g = results.GUIDE.get(t.name)
    if g is None:
        raise KeyError(
            f"table {t.name!r} has no entry in results.GUIDE. A table without "
            "an explanation is what both these pages exist to prevent.")
    notes = " ".join(str(n).replace("\n", " ") for n in t.notes)
    rows = (
        ("What am I looking at", table_shape(t)),
        ("Where the numbers come from", results.sources_html(t.sources)
         or "Computed by the model from its own parameters; no external "
            "citation applies."),
        ("How to read it", figures.inline(g["read"])),
        ("What it means", figures.inline(g["means"])),
        ("What it does NOT show", figures.inline(notes) if notes else
         "No caveat is recorded for this table."),
    )
    cells = []
    for label, text in rows:
        warn = ' class="warn"' if label.startswith("What it does NOT") else ""
        cells.append(f"<dt>{plots.esc(label)}</dt><dd{warn}>{text}</dd>")
    return (
        f'<div class="fig" id="{plots.esc(figures.table_anchor(t.name))}">'
        f'<div class="head"><span class="n">{number:02d}</span>'
        f'<span class="q">{plots.esc(t.title)}</span>'
        f'<a class="top" href="#top">top &uarr;</a></div>'
        f'<div class="card tbl"><div class="tag">{plots.esc(t.name)}</div>'
        f"{results.table_html(t)}</div>"
        f'<div class="why"><dl>{"".join(cells)}</dl></div></div>'
    )


def build() -> str:
    """The whole explainer: units first, then every figure with its five answers."""
    o = outputs(*published_base())
    p = Params()
    body: list[str] = []
    n = 0
    for name, lede, figs in figures.by_section():
        body.append(f'<section class="grp"><h2>{plots.esc(name)}</h2>'
                    f"<p>{figures.inline(lede)}</p></section>")
        for f in figs:
            n += 1
            body.append(section(f, n))

    name, lede = figures.TABLE_SECTION
    body.append(f'<section class="grp"><h2>{plots.esc(name)}</h2>'
                f"<p>{figures.inline(lede)}</p></section>")
    for t in tables.all_tables():
        n += 1
        body.append(table_section(t, n))

    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Investment timing - everything explained</title>"
        f"<style>{plots.CSS}{figures.THEME_BRIDGE}{CSS}</style></head><body><div class=\"wrap\" id=\"top\">"
        "<h1>Everything, explained</h1>"
        '<p class="sub">Every figure <b>and every table</b> the model '
        "produces &mdash; the same sixteen charts as <code>gallery.html</code> "
        "and the same ten tables as <code>results.html</code> &mdash; each "
        "followed by what it shows, where its numbers come from, how to read "
        "it, what it means, and what it does not show, which is the row worth "
        "reading twice. This is the one page that has all of it.</p>"
        f'<p class="cond">Published base case: T* = <b>{o.t_star}</b> &middot; '
        f"NPV0 <b>{o.npv0:,.0f}</b> EUR/t capacity "
        f"(<b>{units.eur(units.absolute(o.npv0, 2.5))}</b> for a 2.5 Mt/yr "
        f"plant) &middot; trigger <b>{o.trigger:,.2f}</b> EUR/tCO2 &middot; "
        f"crossing <b>{o.crossing_year}</b> &middot; discounting at "
        f"<b>{p.common.r:.0%}</b> real to {p.common.t0}.</p>"
        "<h2>Read the unit before the number</h2>"
        '<p class="sub">Every figure below is in one of three units, and they '
        "do not convert into each other. Confusing the first two is what made "
        "<code>I0 = 900</code> look like pocket change; it is EUR 900 per tonne "
        "of annual capacity, which is "
        f"<b>{units.eur(units.absolute(p.sector.I0, 2.5))}</b> for a 2.5 Mt/yr "
        "works.</p>"
        + units_table() + contents() + "".join(body) +
        "<footer>Explanatory framework, not investment advice. Every figure is "
        "drawn from a live model run at build time, so none of them can quote a "
        "number the code no longer produces. Read <code>CALIBRATION.md</code> "
        "for which constants are sourced and which are fitted, and "
        "<code>SOURCES.md</code> for what each input claims and what would "
        "falsify it.</footer>"
        f'</div><script>{plots.JS}</script></body></html>'
    )


def main() -> int:
    """Write explained.html next to the other generated pages."""
    problems = figures.check_complete()
    if problems:
        for problem in problems:
            print(f"  registry problem: {problem}")
        return 1
    page = build()
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"Wrote {OUT} ({len(figures.FIGURES)} figures + "
          f"{len(tables.all_tables())} tables, all explained, "
          f"{len(page) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
