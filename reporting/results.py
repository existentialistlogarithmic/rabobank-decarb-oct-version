"""results.py -> results.html: every table, named, explained, and sourced.

The page to open first. It walks the whole result set in order, and for each
table says what question it answers, how to read it, what the number actually
means, and which sources stand behind it - with the links that exist and an
honest marker where one does not.

Each table carries a short handle (``T2 NPV in money``, ``T4 opex``) so a
reader can point at one across a room. The contents list at the top is the
index; the handles are the addresses.

Generated from the same model run as every other artefact in this build, so a
figure here cannot drift from the one ``run_all.py`` prints. Standard library
only, like the rest of the reporting layer.
"""

from __future__ import annotations

import html
import pathlib
from collections.abc import Sequence
from typing import Final

from analysis import tables, units
from reporting import sources
from timing_model.params import Params
from timing_model.results import outputs
from timing_model.scenarios import published_base

OUT: Final[str] = "results.html"


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


#: What each table is for, in the reader's terms rather than the model's.
#: Keyed by the table's handle so a renamed table fails loudly here rather
#: than silently losing its explanation.
GUIDE: Final[dict[str, dict[str, str]]] = {
    "T0 status": {
        "look": "You want to know what was asked for and what actually got done.",
        "read": "Five rows, one per review comment. The status column is only "
                "ever DONE, PARTIAL or OPEN, and the last column names the "
                "specific missing document where something is not finished.",
        "means": "Three comments are closed, one is closed on the part that "
                 "was actionable, and two are blocked on data that was looked "
                 "for and not found. Nothing is marked done on the strength of "
                 "effort alone.",
    },
    "T1 units": {
        "look": "You saw a number like 900 or 1,606 and it looked far too small.",
        "read": "The middle column is what the model computes. The next column "
                "is that same figure as money for a 2.5 Mt/yr plant.",
        "means": "Every stock in this model is EUR per tonne of ANNUAL "
                 "capacity. It is not per tonne of steel and it is not a "
                 "total. The last two rows are deliberately marked n/a: a "
                 "carbon price and a per-tonne-of-product flow have different "
                 "denominators and do not scale with plant size.",
    },
    "T2 NPV in money": {
        "look": "You want the direct answer to 'how much is this worth'.",
        "read": "Four cases, from the published inputs down to the fully "
                "sourced ones. Read the per-tonne column and the money column "
                "together; they are the same statement.",
        "means": "Billions - but which number depends entirely on the inputs. "
                 "The published case says EUR 4.0bn for a 2.5 Mt/yr plant; the "
                 "sourced central case says EUR 1.3bn; the high case is "
                 "negative. Stegra's Boden is that size and cost EUR 6.5bn to "
                 "build, which is the sanity check the published row struggles "
                 "with.",
    },
    "T3 capex": {
        "look": "You want to know whether the capex assumption is defensible.",
        "read": "Each project's announced total, its capacity, and the two "
                "divided. The outcome column separates what is being built "
                "from what was cancelled.",
        "means": "Every project still BUILDING costs at least EUR 1,300/t of "
                 "capacity against the model's EUR 900. The two below it are "
                 "an EAF-only retrofit and a scheme ArcelorMittal cancelled "
                 "while forfeiting EUR 1.3bn of approved aid - different "
                 "scopes of work, not cheaper ways of doing the same one.",
    },
    "T4 opex": {
        "look": "You want to know whether the operating costs are real.",
        "read": "The first block is the model's entire opex delta. Everything "
                "below it is a cost line the model does not contain. The two "
                "hydrogen rows are ALTERNATIVES - buying and self-generating "
                "are never summed.",
        "means": "This is the weakest part of the model and the table says so. "
                 "The whole BF-BOF against H2-DRI-EAF difference is one "
                 "constant driven by the hydrogen price. EAF electricity alone "
                 "is EUR 89/t in Germany against EUR 47/t in Sweden - a spread "
                 "comparable to the entire published opex delta, on a line the "
                 "model does not have at all.",
    },
    "T5 energy": {
        "look": "You asked whether electricity is cheaper than gas.",
        "read": "Nine member states, both prices in the same unit, and the "
                "ratio. The last two columns are the hydrogen floors each "
                "price implies.",
        "means": "It is not - anywhere. Electricity runs 1.8x to 3.9x gas per "
                 "kWh, which is the whole reason a green hydrogen floor sits "
                 "above a grey one. Both columns EXCLUDE taxes and levies, and "
                 "that exclusion is the gap: the tax layer is what 'fiscal "
                 "harmonisation' would actually change and this build does not "
                 "have it.",
    },
    "T6 subsidy pots": {
        "look": "You want to know what public money is available and on what terms.",
        "read": "The SHAPE column is the one that matters. The legal column "
                "separates enacted instruments from proposals still in "
                "co-decision.",
        "means": "The model nets a EUR 200/t capacity LUMP off capex. The one "
                 "instrument here that is actually awarded and running - the "
                 "German CCfD - pays a STREAM per tonne of CO2 over fifteen "
                 "years. Those are different objects. The Investment Booster "
                 "and the Industrial Decarbonisation Bank are proposals, and "
                 "the EUR 100bn is Explanatory Memorandum framing.",
    },
    "T7 subsidy shape": {
        "look": "You want the stream and the lump compared without being averaged.",
        "read": "Each premium converted into the lump's own unit by eq (10), "
                "with the model's lump as the last row.",
        "means": "A CCfD-style stream is worth 1.3x to 3.3x the model's lump, "
                 "and the German instrument runs fifteen years rather than the "
                 "ten priced here - so every row understates it. Per-company "
                 "strike prices were never disclosed, so these are the "
                 "mechanism's range, not observed awards.",
    },
    "T8 market": {
        "look": "You want to know whether the model's assumptions still hold "
                "today, and what it costs where they do not.",
        "read": "Each row pairs a published assumption with a live "
                "observation carrying its own date. The money column converts "
                "the gap for a 2.5 Mt/yr plant where it converts at all; a "
                "dash means the quantity is a rate or a ratio and does not.",
        "means": "Stop at the volatility row. Sigma is the only parameter that "
                 "moves the trigger without moving the break-even, and one "
                 "year of auctions puts realised volatility half again above "
                 "the 0.20 the model runs on - which on the specification's "
                 "own ladder is five more years before the price path reaches "
                 "the trigger. The carbon price is above its 2026 anchor, "
                 "which is tens of millions a year on the plant's carbon bill "
                 "and makes waiting more expensive, not less. And the model "
                 "hands one plant a quarter of everything the Innovation Fund "
                 "has collected this year for every sector in Europe. Nothing "
                 "here feeds the model: it is a statement about the "
                 "assumptions, not a replacement for them.",
    },
    "T9 real pot": {
        "look": "You want the subsidy pot as money that exists, not money "
                "that was announced.",
        "read": "Receipts from the EU ETS auctions, year to date, by "
                "recipient. The plants column divides each row by the EUR 500m "
                "the model hands one reference plant, so the scale is legible "
                "without doing arithmetic.",
        "means": "The pot is real and large - EUR 27.5bn so far this year - "
                 "but it is not a fund this project can draw on. The "
                 "Directive's spending clause is a target on national budgets. "
                 "Read against T6: that table lists envelopes governments have "
                 "announced, this one lists cash the auctions have already "
                 "paid, and the two are different kinds of object.",
    },
}

CSS: Final[str] = """
:root{--ink:#1a1a19;--mut:#5f5f5c;--line:#e4e4e0;--bg:#fcfcfb;--card:#fff;
--acc:#2a78d6;--warn:#b4541f;--ok:#166d51}
@media (prefers-color-scheme:dark){:root{--ink:#eceae6;--mut:#a3a29d;
--line:#333330;--bg:#141413;--card:#1c1c1a;--acc:#6ba4ec;--warn:#e08a5a;
--ok:#4fbf94}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:40px 20px 80px}
h1{font-size:30px;line-height:1.2;margin:0 0 6px}
.sub{color:var(--mut);margin:0 0 28px}
h2{font-size:21px;margin:0 0 4px;scroll-margin-top:16px}
.tag{display:inline-block;font:600 12px/1 ui-monospace,monospace;
letter-spacing:.04em;color:var(--acc);border:1px solid var(--acc);
border-radius:4px;padding:5px 7px;margin-bottom:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:22px 24px;margin:0 0 22px}
.q{display:grid;grid-template-columns:132px 1fr;gap:6px 14px;margin:14px 0 18px}
.q dt{color:var(--mut);font-size:13px;text-transform:uppercase;
letter-spacing:.05em;padding-top:2px}
.q dd{margin:0}
.scroll{overflow-x:auto;margin:0 -4px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line);
white-space:nowrap}
th:first-child,td:first-child{text-align:left}
thead th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;
color:var(--mut);font-weight:600}
thead tr.u th{text-transform:none;letter-spacing:0;font-weight:400;
font-style:italic;border-bottom:2px solid var(--line)}
tbody tr:hover{background:rgba(127,127,127,.07)}
td.miss{color:var(--warn);font-weight:600}
.note{font-size:14px;color:var(--mut);margin:14px 0 0;
border-left:2px solid var(--line);padding-left:12px}
.srcs{margin:18px 0 0;font-size:13px}
.srcs h4{margin:0 0 7px;font-size:11px;text-transform:uppercase;
letter-spacing:.05em;color:var(--mut)}
.srcs li{margin:3px 0}
.srcs code{font-size:12px}
a{color:var(--acc)}
.nolink{color:var(--warn)}
ol.toc{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:18px 24px 18px 44px;margin:0 0 34px}
ol.toc li{margin:5px 0}
ol.toc code{font-size:12px;color:var(--acc)}
.hero{display:flex;gap:26px;flex-wrap:wrap;margin:0 0 24px}
.hero div{flex:1 1 150px}
.hero b{display:block;font-size:26px;line-height:1.15}
.hero span{font-size:13px;color:var(--mut)}
footer{color:var(--mut);font-size:13px;border-top:1px solid var(--line);
margin-top:40px;padding-top:18px}
@media(max-width:620px){.q{grid-template-columns:1fr}.wrap{padding:24px 16px 60px}}
"""


def table_html(t: tables.Table) -> str:
    """One table as HTML, keeping the unit row the terminal version has."""
    head = "".join(f"<th>{esc(c.name)}</th>" for c in t.columns)
    unit = ""
    if any(c.unit for c in t.columns):
        unit = ("<tr class='u'>"
                + "".join(f"<th>{esc(c.unit)}</th>" for c in t.columns)
                + "</tr>")
    body = []
    for row in t.rows:
        cells = []
        for val in row:
            text = "" if val is None else str(val)
            cls = " class='miss'" if text.strip() == tables.MISSING else ""
            cells.append(f"<td{cls}>{esc(text)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (f"<div class='scroll'><table><thead><tr>{head}</tr>{unit}</thead>"
            f"<tbody>{''.join(body)}</tbody></table></div>")


def cite(ref: tables.SourceRef) -> tuple[str, str | None, str]:
    """(title, url, tier) for one citation, joining both registries.

    ``analysis`` may not import ``reporting``, so it resolves only the research
    package and leaves the rest unlinked. This is the layer that can see the
    model's own bibliography, so the join belongs here: a key the register
    knows gets its checked, live URL and its real title.
    """
    if ref.key in sources.SOURCES:
        s = sources.SOURCES[ref.key]
        return s.title, s.url, "model register"
    return ref.key, ref.url, ref.tier


def sources_html(refs: Sequence[tables.SourceRef]) -> str:
    """The citations, with the links that exist and a marker where none does."""
    if not refs:
        return ""
    items = []
    for ref in refs:
        title, url, tier = cite(ref)
        if url:
            extra = "" if tier == "model register" else f" <em>({esc(tier)})</em>"
            items.append(f"<li><code>{esc(ref.key)}</code> &mdash; "
                         f"<a href='{esc(url)}' rel='noopener'>{esc(title)}</a>"
                         f"{extra}</li>")
        else:
            items.append(f"<li><code>{esc(ref.key)}</code> &mdash; "
                         f"<span class='nolink'>named but not linked</span> "
                         f"&mdash; see <code>docs/research-sources.md</code></li>")
    return ("<div class='srcs'><h4>Sources</h4><ul>" + "".join(items) + "</ul>"
            "<p class='note'>A source with no link was correctly attributed by "
            "the research pass but its working URL was not captured. In this "
            "project that is <em>unverified</em>, not <em>sourced</em>, and "
            "nothing built on one has been promoted into the provenance "
            "register.</p></div>")


def section(t: tables.Table) -> str:
    """One table, with the three questions a reader actually has."""
    g = GUIDE.get(t.name)
    if g is None:
        raise KeyError(
            f"table {t.name!r} has no entry in GUIDE. A table without an "
            "explanation is the thing this page exists to prevent."
        )
    notes = "".join(
        f"<p class='note'>{esc(n).replace(chr(10), ' ')}</p>" for n in t.notes)
    return (
        f"<section class='card' id='{esc(t.name.replace(' ', '-'))}'>"
        f"<div class='tag'>{esc(t.name)}</div>"
        f"<h2>{esc(t.title)}</h2>"
        "<dl class='q'>"
        f"<dt>Look here when</dt><dd>{esc(g['look'])}</dd>"
        f"<dt>How to read it</dt><dd>{esc(g['read'])}</dd>"
        f"<dt>What it means</dt><dd>{esc(g['means'])}</dd>"
        "</dl>"
        + table_html(t) + notes + sources_html(t.sources)
        + "</section>"
    )


def build() -> str:
    """The whole page, from one model run."""
    all_t = tables.all_tables()
    o = outputs(*published_base())
    money = units.eur(units.absolute(o.npv0, tables.REFERENCE_MT))
    capex = units.eur(units.absolute(Params().sector.I0, tables.REFERENCE_MT))
    toc = "".join(
        f"<li><a href='#{esc(t.name.replace(' ', '-'))}'>"
        f"<code>{esc(t.name)}</code></a> &mdash; {esc(t.title)}</li>"
        for t in all_t)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Results, step by step</title><style>{CSS}</style></head><body>
<div class="wrap">
<h1>Results, step by step</h1>
<p class="sub">Every table in the build, named so you can point at it, with
what it answers and what stands behind it. Generated from the same model run
as <code>charts.html</code> and <code>deck.html</code>.</p>

<div class="hero">
<div><b>{esc(o.t_star)}</b><span>commitment year T*</span></div>
<div><b>{esc(money)}</b><span>NPV for a {tables.REFERENCE_MT:g} Mt/yr plant,
published case</span></div>
<div><b>{esc(capex)}</b><span>its modelled capex, same plant</span></div>
<div><b>&euro;{o.trigger:,.0f}</b><span>trigger, per tCO&#8322;</span></div>
</div>

<p>The single thing to hold on to: <b>every euro figure in this build is a rate
per tonne of <em>annual capacity</em></b>, not a total and not a price per tonne
of steel. Multiply by a plant's annual tonnes and it becomes money &mdash; which
is what the absolute columns below do, at {tables.REFERENCE_MT:g} Mt/yr
throughout.</p>

<ol class="toc">{toc}</ol>
{''.join(section(t) for t in all_t)}
<footer>Explanatory framework, not investment advice. Read
<code>CALIBRATION.md</code> before quoting any figure: the cost-side learning
rate is calibrated rather than sourced, ladder rows 4&ndash;7 do not reproduce
the published table, and only 9 of 98 rows in the September 2026 research pass
carry a working link.</footer>
</div></body></html>
"""


def main() -> int:
    """Write results.html next to the other generated pages."""
    page = build()
    pathlib.Path(OUT).write_text(page, encoding="utf-8")
    print(f"Wrote {OUT} ({len(tables.all_tables())} tables, "
          f"{len(page) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
