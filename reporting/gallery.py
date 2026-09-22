"""gallery.py -> gallery.html: every figure in the build, on one page.

The complaint this answers: the graphs were scattered. Five generated pages
each carried some of them - ``charts.html`` had sixteen, ``article.html`` drew
its own, the deck had more, ``surface.html`` and ``explorer.html`` were
interactive and separate - so "show me the graphs" meant opening five files and
knowing in advance which one held the figure you wanted.

This is the contact sheet: all sixteen figures, in argument order, with a
sticky contents list that follows you down the page and a link to each one's
full explanation in ``explained.html``. Nothing here is new work - it renders
``figures.FIGURES``, the same registry the explainer uses, so the two pages
cannot drift apart.

The two interactive figures stay where they are and are linked rather than
inlined: the 3D fleet surface needs a canvas and a drag handler, and the
frontier explorer embeds 891 model runs. Copying either into this page would
double its weight for a worse version of each.
"""

from __future__ import annotations

from typing import Final

from reporting import figures, plots
from timing_model.results import outputs
from timing_model.scenarios import published_base

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
@media (max-width:700px){.toc-rail ol{gap:5px 12px;font-size:12px}}
"""


def contents() -> str:
    """A sticky rail of every figure, grouped, that follows the reader down."""
    items: list[str] = []
    for name, _lede, figs in figures.by_section():
        items.append(f'<li class="sec">{plots.esc(name)}</li>')
        items.extend(
            f'<li><a href="#{plots.esc(f.key)}">{plots.esc(f.title)}</a></li>'
            for f in figs
        )
    return f'<nav class="toc-rail"><ol>{"".join(items)}</ol></nav>'


def build() -> str:
    """Every static figure, in argument order, each under the question it answers."""
    o = outputs(*published_base())
    body: list[str] = []
    for name, lede, figs in figures.by_section():
        body.append(f'<section class="grp"><h2>{plots.esc(name)}</h2>'
                    f"<p>{figures.inline(lede)}</p></section>")
        for f in figs:
            body.append(
                f'<div class="qline" id="{plots.esc(f.key)}">'
                f'<span class="q">{plots.esc(f.question)}</span>'
                f'<a class="why" href="explained.html#{plots.esc(f.key)}">'
                "full explanation &rarr;</a></div>"
                + f.draw()
            )

    tiles = "".join(
        f'<a class="tile" href="{plots.esc(href)}"><b>{plots.esc(title)}</b>'
        f"<span>{figures.inline(note)}</span></a>"
        for href, title, note in INTERACTIVE
    )
    body.append(
        '<section class="grp" id="interactive"><h2>Interactive, on their own pages</h2>'
        "<p>Two figures are not static pictures and are linked rather than "
        "copied in: inlining either would double this page's weight for a "
        "worse version of it.</p></section>"
        f'<div class="links">{tiles}</div>'
    )

    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Investment timing - every figure</title>"
        f"<style>{plots.CSS}{figures.THEME_BRIDGE}{CSS}</style></head><body><div class=\"wrap\">"
        "<h1>Every figure, one page</h1>"
        '<p class="sub">All sixteen charts the model produces, in the order the '
        "argument runs: the decision, the objections to it, the live check "
        "against the market, and the structure underneath. Generated by "
        "<code>gallery.py</code> - no third-party libraries. Each figure links "
        "to its full explanation in <code>explained.html</code>.</p>"
        f'<p class="cond">Published base case: T* = <b>{o.t_star}</b> &middot; '
        f"NPV0 <b>{o.npv0:,.0f}</b> EUR/t capacity &middot; trigger "
        f"<b>{o.trigger:,.2f}</b> EUR/tCO2 &middot; crossing "
        f"<b>{o.crossing_year}</b>. Every figure is drawn from a live model run "
        "at build time.</p>"
        + contents() + "".join(body) +
        "<footer>Explanatory framework, not investment advice. Read "
        "<code>CALIBRATION.md</code> before quoting any figure, and "
        "<code>explained.html</code> before drawing a conclusion from one: "
        "every chart here has a stated boundary and several are easy to "
        "over-read without it.</footer>"
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
    print(f"Wrote {OUT} ({len(figures.FIGURES)} figures, {len(page) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
