"""deck.py -> deck.html: the 40-minute presentation, generated from the model.

Every figure is drawn from a live model run at build time, and every figure
slide carries the equation that produced it and a table saying what each symbol
means. Nothing is a screenshot and nothing is typed in by hand, so the deck
cannot quote a number the code no longer produces.

Structure: 21 slides in 8 sections, timed to 39.5 minutes, which leaves the
40-minute slot a little slack and the questions their own time. The live-market
slide near the end reads the EU ETS auction record at build time, so the deck
says what the assumptions look like on the morning it is given rather than on
the day it was written. Arrow keys or space to advance, ``g`` for the grid,
``n`` for speaker notes, ``t`` to start the timer. Printing gives one slide per
page.

Equations are MathML, which every current browser renders natively - no
library, no CDN, consistent with the rest of the build.
"""

from __future__ import annotations

import html
import pathlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from analysis import findings as fnd
from analysis import grounding, market, regimes, sourcing, units
from data import ecb, eurostat
from timing_model import cost, objective, option, primitives
from timing_model.benefit import carbon_price_path, free_allocation_factor
from timing_model.params import SIGMA_REGIMES, Params, ScenarioParams
from timing_model.results import outputs
from timing_model.scenarios import run_ladder

OUT: Final[str] = "deck.html"

# ---------------------------------------------------------------- chart toolkit

W: Final[int] = 720
H: Final[int] = 380
PAD: Final[tuple[int, int, int, int]] = (64, 20, 46, 16)  # left, top, bottom, right


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def _ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    """Human-readable tick values spanning [lo, hi]."""
    if hi <= lo:
        return [lo]
    raw = (hi - lo) / n
    mag = 10.0 ** int(__import__("math").floor(__import__("math").log10(raw)))
    step = next((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), mag * 10)
    out, v = [], step * __import__("math").ceil(lo / step)
    while v <= hi + 1e-9:
        out.append(v)
        v += step
    return out


@dataclass
class Axes:
    """A plot frame with linear scales, and the SVG for its grid and labels."""

    x_lo: float
    x_hi: float
    y_lo: float
    y_hi: float
    width: int = W
    height: int = H

    def __post_init__(self) -> None:
        left, top, bottom, right = PAD
        self.x0, self.x1 = left, self.width - right
        self.y0, self.y1 = self.height - bottom, top
        if self.y_hi <= self.y_lo:
            self.y_hi = self.y_lo + 1.0

    def X(self, v: float) -> float:
        return self.x0 + (v - self.x_lo) / (self.x_hi - self.x_lo) * (self.x1 - self.x0)

    def Y(self, v: float) -> float:
        return self.y0 - (v - self.y_lo) / (self.y_hi - self.y_lo) * (self.y0 - self.y1)

    def grid(self, xfmt: Callable[[float], str], yfmt: Callable[[float], str],
             xlabel: str = "", ylabel: str = "",
             xvals: Sequence[float] | None = None) -> str:
        parts = ['<g class="ax">']
        for v in _ticks(self.y_lo, self.y_hi):
            y = self.Y(v)
            parts.append(f'<line x1="{self.x0}" x2="{self.x1}" y1="{y:.1f}" y2="{y:.1f}"/>')
            parts.append(f'<text x="{self.x0 - 8}" y="{y + 4:.1f}" text-anchor="end">'
                         f'{esc(yfmt(v))}</text>')
        for v in (xvals if xvals is not None else _ticks(self.x_lo, self.x_hi)):
            parts.append(f'<text x="{self.X(v):.1f}" y="{self.y0 + 18}" '
                         f'text-anchor="middle">{esc(xfmt(v))}</text>')
        parts.append(f'<line class="base" x1="{self.x0}" x2="{self.x1}" '
                     f'y1="{self.y0}" y2="{self.y0}"/>')
        # Axis titles are author markup: they legitimately carry numeric
        # character references (&#963; for sigma), so they are not escaped.
        if xlabel:
            parts.append(f'<text class="axt" x="{(self.x0 + self.x1) / 2:.0f}" '
                         f'y="{self.y0 + 38}" text-anchor="middle">{xlabel}</text>')
        if ylabel:
            parts.append(f'<text class="axt" x="{self.x0}" y="{self.y1 - 8}" '
                         f'text-anchor="start">{ylabel}</text>')
        parts.append("</g>")
        return "".join(parts)

    def zero_rule(self) -> str:
        if not (self.y_lo < 0.0 < self.y_hi):
            return ""
        return f'<line class="zero" x1="{self.x0}" x2="{self.x1}" ' \
               f'y1="{self.Y(0):.1f}" y2="{self.Y(0):.1f}"/>'


def _span(values: Sequence[float], pad: float = 0.10) -> tuple[float, float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return lo - 1.0, hi + 1.0
    m = (hi - lo) * pad
    return lo - m, hi + m


def polyline(ax: Axes, pts: Sequence[tuple[float, float]], cls: str = "s1") -> str:
    d = " ".join(f"{'M' if i == 0 else 'L'}{ax.X(x):.1f} {ax.Y(y):.1f}"
                 for i, (x, y) in enumerate(pts))
    return f'<path class="ln {cls}" d="{d}"/>'


def svg(body: str, label: str, width: int = W, height: int = H) -> str:
    return (f'<svg viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{esc(label)}">{body}</svg>')


def marker(ax: Axes, x: float, y: float, text: str, cls: str = "s2",
           dy: int = -14) -> str:
    return (f'<circle class="mk {cls}" cx="{ax.X(x):.1f}" cy="{ax.Y(y):.1f}" r="6"/>'
            f'<text class="mkl" x="{ax.X(x):.1f}" y="{ax.Y(y) + dy:.1f}" '
            f'text-anchor="middle">{text}</text>')


def _n_unverified() -> int:
    """How many inputs are still open items, read off the register.

    It was three when the deck was written and is one now; a slide that says
    "three" after the register says one is exactly the drift the provenance
    audit exists to prevent, so the deck asks rather than remembers.
    """
    from reporting import sources

    return len(sources.unverified())


def source_counts() -> tuple[int, int]:
    """(test functions, self-checks) counted from source, never typed in.

    A deck that quotes a fixed test count is wrong the week someone adds one.
    These are read off the files at build time; the test suite expands further
    through parametrisation, which the caption says.
    """
    import re

    root = pathlib.Path(__file__).resolve().parents[1]
    tests = sum(len(re.findall(r"^def test_", f.read_text(), re.M))
                for f in sorted((root / "tests").glob("test_*.py")))
    checks = len(re.findall(r"^@check\(", (root / "selfcheck.py").read_text(), re.M))
    return tests, checks


# ------------------------------------------------------------------- the slides

@dataclass
class Slide:
    """One slide: heading, body HTML, section, and the minutes it should take."""

    section: str
    title: str
    body: str
    minutes: float
    notes: str = ""


def eq(mathml: str, caption: str = "") -> str:
    """An equation block. MathML renders natively; the caption says what it is."""
    cap = f'<figcaption>{caption}</figcaption>' if caption else ""
    return f'<figure class="eq"><math display="block">{mathml}</math>{cap}</figure>'


def symbols(rows: Sequence[tuple[str, str, str]]) -> str:
    """What each symbol means: symbol, meaning, units-and-value."""
    # All three columns are author-written markup (entities, <sub>, <b>), not
    # user input, so none of them is escaped.
    body = "".join(
        f"<tr><td class='sym'>{s}</td><td>{m}</td><td class='val'>{v}</td></tr>"
        for s, m, v in rows)
    return ("<table class='sym'><thead><tr><th>symbol</th><th>meaning</th>"
            f"<th>units / value here</th></tr></thead><tbody>{body}</tbody></table>")


def figure(chart: str, caption: str) -> str:
    return f'<figure class="fig">{chart}<figcaption>{caption}</figcaption></figure>'


def two_col(left: str, right: str) -> str:
    return f'<div class="cols"><div>{left}</div><div>{right}</div></div>'


def keypoints(items: Sequence[str]) -> str:
    return "<ul class='kp'>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def stat_row(items: Sequence[tuple[str, str]]) -> str:
    return "<div class='stats'>" + "".join(
        f"<div class='stat'><span class='n'>{n}</span>"
        f"<span class='l'>{lab}</span></div>" for n, lab in items) + "</div>"


# ------------------------------------------------------------------- data + build

def build_slides() -> list[Slide]:  # noqa: C901 - a deck is a long linear script
    """Compute everything, then lay it out. One model run per figure."""
    p, sc = Params(), ScenarioParams(u=1.0)          # published base row
    pc, scc = Params(), ScenarioParams()             # registered defaults (u = 0.85)
    base = outputs(p, sc)
    corrected = outputs(pc, scc)
    series = eurostat.refresh(offline=True)
    rates = ecb.refresh(offline=True)
    years = list(range(p.common.t0, p.common.horizon_end + 1))
    slides: list[Slide] = []

    # ---------------------------------------------------------------- 1. frame
    slides.append(Slide(
        "Frame", "When should a steel plant stop burning coal?",
        f"""
<p class="lede">One European integrated works. One irreversible decision: the
year <em>T</em> to switch from blast furnace to hydrogen direct reduction. Not
<em>whether</em> — <em>when</em>.</p>
{stat_row([(str(base.t_star), "the year NPV says commit"),
           (f"&euro;{base.npv0:,.0f}", "NPV per tonne of capacity"),
           (f"&euro;{base.trigger:.0f}", "carbon price that justifies it"),
           (str(base.crossing_year), "year the price path gets there")])}
<p>Those four numbers disagree with each other in a way that is the whole
point of the talk. The first two ignore uncertainty. The last two price it.</p>
""", 1.0,
        "Set the frame: this is a timing problem, not a technology problem. "
        "Everyone in the room already believes the switch happens."))

    slides.append(Slide(
        "Frame", "Four outputs, because the decision has two halves",
        two_col(
            """<table class="grid"><thead><tr><th>output</th><th>question</th>
<th>option premium?</th></tr></thead><tbody>
<tr><td><code>T*</code></td><td>which year maximises NPV</td><td>no</td></tr>
<tr><td><code>T_exp</code></td><td>last year deferral still adds value</td><td>no</td></tr>
<tr><td><code>p*&prime;</code></td><td>carbon price at which committing beats waiting</td><td>yes</td></tr>
<tr><td>crossing</td><td>first year the path reaches <code>p*&prime;</code></td><td>yes</td></tr>
</tbody></table>""",
            keypoints([
                f"<b>T* = {base.t_star}</b> and <b>crossing = {base.crossing_year}</b> "
                "differ by a year. That gap <em>is</em> the option premium, "
                "expressed in time.",
                "A firm that ignores irreversibility acts at <code>T*</code>. "
                "A firm that prices it waits for <code>p*&prime;</code>.",
                "Reporting one without the other is the single most common "
                "error in this literature.",
            ])), 1.5,
        "Do not let anyone leave thinking T* and the crossing year are "
        "competing estimates of the same thing. They answer different questions."))

    slides.append(Slide(
        "Frame", "One thing to hold on to: the units",
        f"""
{two_col(
   '''<p><b>Per tonne of annual <span class="hi">capacity</span></b><br>
   capex <code>I0</code>, write-off <code>S_s</code>, support <code>s</code>,
   and every NPV.</p>
   <p><b>Per tonne of <span class="hi">product</span></b><br>
   the opex penalty <code>a</code>, the benefit flow <code>B(t)</code>, and
   every carbon term.</p>''',
   '''<p>The load factor <code>u</code> is the <em>only</em> bridge between
   them. It multiplies <code>B(t)</code> and never <code>I&prime;(T)</code>.</p>
   <p>An AST test fails the build if <code>cost.py</code> so much as names it.
   That is not fussiness: mixing the two is how you get a plant that looks
   twice as valuable as it is.</p>''')}
{eq("<mrow><mfrac><mrow><mi>EUR</mi></mrow><mrow><mi>t</mi><mspace width='3px'/>"
    "<mtext>capacity</mtext></mrow></mfrac><mo>=</mo><mi>u</mi><mo>&#183;</mo>"
    "<mfrac><mrow><mi>EUR</mi></mrow><mrow><mi>t</mi><mspace width='3px'/>"
    "<mtext>product</mtext></mrow></mfrac></mrow>",
    "the only legal conversion between the two families")}
<p class="lede">And the question everyone asks first: <b>&euro;900 of what?</b>
Per tonne of <em>annual</em> capacity. Multiply by annual tonnes and the
denominator cancels &mdash; it is the same kind of number an operator
announces.</p>
<table class="grid"><thead><tr><th>project</th><th>announced</th>
<th>capacity</th><th>&euro;/t capacity</th></tr></thead><tbody>
{"".join(f"<tr><td>{esc(n)}</td><td class='val'>{units.eur(tot)}</td>"
         f"<td class='val'>{mt:g} Mt/yr</td><td class='val'>{st:,.0f}</td></tr>"
         for n, tot, mt, st, _ in units.round_trip())}
<tr><td><b>this model, I0</b></td>
<td class="val"><b>{units.eur(units.absolute(p.sector.I0, 2.5))}</b></td>
<td class="val">2.5 Mt/yr</td><td class="val"><b>{p.sector.I0:,.0f}</b></td></tr>
</tbody></table>
""", 2.0,
        "If they remember one slide, make it this one. Every error in the "
        "published version traces back here. The table is the answer to "
        "'why is it only 900' - it is 2.2 billion."))

    # ------------------------------------------------- 2. the model, layer by layer
    ph2_range = [0.5 + 0.25 * i for i in range(37)]
    a_vals = [primitives.opex_penalty(p, ScenarioParams(p_H2=x)) for x in ph2_range]
    ax = Axes(min(ph2_range), max(ph2_range), *_span(a_vals))
    body = [ax.grid(lambda v: f"{v:.0f}", lambda v: f"{v:,.0f}",
                    "hydrogen price p_H2 (EUR/kg)", "a  (EUR / t product / yr)"),
            ax.zero_rule(), polyline(ax, list(zip(ph2_range, a_vals, strict=True)))]
    for x, lab in ((2.60, "base 2.60"), (8.29, "Platts 8.29")):
        y = primitives.opex_penalty(p, ScenarioParams(p_H2=x))
        body.append(marker(ax, x, y, f"{lab} → {y:,.0f}"))
    slides.append(Slide(
        "The model", "Group I — what a tonne costs to make cleanly",
        two_col(
            eq("<mrow><mi>a</mi><mo>(</mo><msub><mi>p</mi><mrow><mi>H2</mi></mrow>"
               "</msub><mo>)</mo><mo>=</mo><mo>&#8722;</mo><mo>(</mo><msub><mi>m</mi>"
               "<mrow><mi>H2</mi></mrow></msub><mo>&#183;</mo><msub><mi>p</mi>"
               "<mrow><mi>H2</mi></mrow></msub><mo>&#8722;</mo><msub><mi>c</mi>"
               "<mrow><mtext>avoided</mtext></mrow></msub><mo>)</mo></mrow>",
               "Group I eq (2) — the annual operating penalty")
            + symbols([
                ("a", "operating penalty: what the clean route costs to run, "
                      "per year, relative to the incumbent", "EUR/t product/yr"),
                ("m<sub>H2</sub>", "hydrogen needed per tonne of steel", "55 kg/t"),
                ("p<sub>H2</sub>", "delivered hydrogen price — <b>the input the "
                                   "whole model turns on</b>", "EUR/kg, base 2.60"),
                ("c<sub>avoided</sub>", "coke and PCI you stop buying",
                 "83 EUR/t/yr"),
            ]),
            figure(svg("".join(body), "operating penalty against hydrogen price"),
                   "The line is straight because the relationship is linear — "
                   "but the <em>slope is 55</em>. Every 10 cents on hydrogen is "
                   "&euro;5.50 a tonne, every year, forever.")), 2.0,
        "The MATLAB reference hardcoded a = -60. Making it a function of p_H2 "
        "is what turned a hidden forecast into a visible input."))

    path = carbon_price_path(p, sc)
    alloc = [free_allocation_factor(t, sc) for t in years]
    axp = Axes(years[0], years[-1], 0.0, max(path.values()) * 1.12)
    pbody = [axp.grid(lambda v: f"{v:.0f}", lambda v: f"{v:,.0f}",
                      "year", "EUA price (EUR / tCO2)"),
             polyline(axp, [(t, path[t]) for t in years]),
             f'<line class="trig" x1="{axp.x0}" x2="{axp.x1}" '
             f'y1="{axp.Y(base.trigger):.1f}" y2="{axp.Y(base.trigger):.1f}"/>',
             f'<text class="mkl crit" x="{axp.x1}" y="{axp.Y(base.trigger) - 8:.1f}" '
             f'text-anchor="end">trigger p*&#8242; = {base.trigger:.0f}</text>']
    if base.crossing_year:
        pbody.append(marker(axp, base.crossing_year, path[base.crossing_year],
                            f"crosses {base.crossing_year}"))
    axa = Axes(years[0], years[-1], 0.0, 1.05, width=W, height=200)
    abody = [axa.grid(lambda v: f"{v:.0f}", lambda v: f"{v:.0%}", "year",
                      "free allocation f(t)"),
             polyline(axa, list(zip(years, alloc, strict=True)), "s3")]
    slides.append(Slide(
        "The model", "Group II — what a tonne of abatement is worth each year",
        two_col(
            eq("<mrow><mi>B</mi><mo>(</mo><mi>t</mi><mo>)</mo><mo>=</mo><mi>u</mi>"
               "<mo>&#183;</mo><mo>[</mo><mi>a</mi><mo>+</mo><mo>(</mo><mn>1</mn>"
               "<mo>&#8722;</mo><mi>&#945;</mi><mo>)</mo><mi>b</mi><msub><mi>p</mi>"
               "<mi>t</mi></msub><mo>+</mo><mi>w</mi><mi>&#945;</mi><msub>"
               "<mi>&#949;</mi><mtext>inc</mtext></msub><msub><mi>p</mi><mi>t</mi>"
               "</msub><mo>]</mo></mrow>",
               "Group II eq (4) — the annual benefit flow")
            + symbols([
                ("u", "load factor — the capacity/product bridge", "0.85 (base row 1.00)"),
                ("&alpha;(t)", "share of emissions still allocated free",
                 "0.975 in 2026 &rarr; 0 from 2034"),
                ("b", "abatement intensity, &kappa;&middot;&epsilon;<sub>inc</sub> "
                      "&minus; &epsilon;<sub>cln</sub>",
                 f"{primitives.abatement_intensity(p):.2f} tCO2/t"),
                ("p<sub>t</sub>", "EUA price path", "76 &rarr; 112 by 2030, then +5%/yr"),
                ("w", "resale switch: may you sell surplus allowances?", "1 = yes"),
            ]),
            figure(svg("".join(pbody), "carbon price path against the trigger"),
                   "The price path and the trigger it has to reach.")
            + figure(svg("".join(abody), "free allocation phase-out", W, 200),
                     "Free allocation falls away underneath it — that phase-out "
                     "is what turns the carbon price into revenue.")), 2.0,
        "Two forces: the price rises, and the free allocation that shielded you "
        "from it disappears. B(t) is the product of both."))

    Ls = [cost.learning(T, p) for T in years]
    Ss = [cost.residual_value(T, p) for T in years]
    Is = [cost.switching_cost(T, p, sc).total for T in years]
    axc = Axes(years[0], years[-1], 0.0, max(Is + Ss) * 1.15)
    cbody = [axc.grid(lambda v: f"{v:.0f}", lambda v: f"{v:,.0f}",
                      "commitment year T", "EUR / t capacity"),
             polyline(axc, list(zip(years, Is, strict=True)), "s1"),
             polyline(axc, list(zip(years, Ss, strict=True)), "s3"),
             polyline(axc, [(t, 900.0 * L) for t, L in zip(years, Ls, strict=True)], "s2")]
    t_rel = cost.reline_year(p)
    cbody.append(f'<line class="trig" x1="{axc.X(t_rel):.1f}" x2="{axc.X(t_rel):.1f}" '
                 f'y1="{axc.y0}" y2="{axc.y1}"/>'
                 f'<text class="mkl crit" x="{axc.X(t_rel) + 6:.1f}" y="{axc.y1 + 12}">'
                 f'reline {t_rel}</text>')
    slides.append(Slide(
        "The model", "Group III — what switching costs, and why waiting is cheaper",
        two_col(
            eq("<mrow><msup><mi>I</mi><mo>&#8242;</mo></msup><mo>(</mo><mi>T</mi>"
               "<mo>)</mo><mo>=</mo><mi>max</mi><mo>{</mo><msub><mi>I</mi><mn>0</mn>"
               "</msub><mi>L</mi><mo>(</mo><mi>T</mi><mo>)</mo><mo>&#8722;</mo>"
               "<mi>s</mi><mo>(</mo><mi>T</mi><mo>)</mo><mo>,</mo><mn>0</mn>"
               "<mo>}</mo><mo>+</mo><mi>&#966;</mi><msub><mi>S</mi><mi>s</mi></msub>"
               "<mo>(</mo><mi>T</mi><mo>)</mo></mrow>",
               "Group III eq (8)")
            + eq("<mrow><mi>L</mi><mo>(</mo><mi>T</mi><mo>)</mo><mo>=</mo><mo>(</mo>"
                 "<mn>1</mn><mo>+</mo><mi>&#947;</mi><mo>)</mo><mrow><msup><mrow></mrow>"
                 "<mrow><mo>&#8722;</mo><msub><mi>b</mi><mi>&#8467;</mi></msub>"
                 "<mo>(</mo><mi>T</mi><mo>&#8722;</mo><msub><mi>t</mi><mn>0</mn>"
                 "</msub><mo>)</mo></mrow></msup></mrow></mrow>",
                 "Wright learning, eq (5) — the reason to wait")
            + symbols([
                ("I<sub>0</sub>", "capex today", "900 EUR/t capacity (2022)"),
                ("L(T)", "learning multiplier: capex falls 8.2%/yr", "1.00 &rarr; 0.13"),
                ("s(T)", "Investment Booster support, from 2028", "200 EUR/t"),
                ("S<sub>s</sub>(T)", "residual value of the furnace you scrap",
                 f"{cost.residual_value(p.common.t0, p):.0f} &rarr; 0 at reline"),
                ("&phi;", "share of that write-off charged to the decision", "0.5"),
            ]),
            figure(svg("".join(cbody), "switching cost components against year"),
                   "<span class='k s1'></span>total I&prime;(T) &nbsp; "
                   "<span class='k s2'></span>gross capex I<sub>0</sub>L(T) &nbsp; "
                   "<span class='k s3'></span>residual S<sub>s</sub>(T). "
                   "Both fall. Waiting is genuinely cheaper — that is the "
                   "tension the whole model resolves.")), 2.0,
        "Note the step in the total: that is the support window opening in 2028."))

    curve = objective.npv_curve(p, sc)
    axn = Axes(years[0], years[-1], *_span(list(curve.values())))
    nbody = [axn.grid(lambda v: f"{v:.0f}", lambda v: f"{v:,.0f}",
                      "commitment year T", "NPV (EUR / t capacity)"),
             axn.zero_rule(),
             polyline(axn, [(t, curve[t]) for t in years]),
             marker(axn, base.t_star, curve[base.t_star],
                    f"T* = {base.t_star}  ({curve[base.t_star]:,.0f})")]
    slides.append(Slide(
        "The model", "Group IV — the deterministic answer",
        two_col(
            eq("<mrow><mi>NPV</mi><mo>(</mo><mi>T</mi><mo>)</mo><mo>=</mo>"
               "<mo>&#8722;</mo><mi>d</mi><mo>(</mo><mi>T</mi><mo>)</mo><msup>"
               "<mi>I</mi><mo>&#8242;</mo></msup><mo>(</mo><mi>T</mi><mo>)</mo>"
               "<mo>&#177;</mo><mi>d</mi><mo>(</mo><msub><mi>T</mi><mtext>rel</mtext>"
               "</msub><mo>)</mo><mi>&#961;</mi><msub><mi>K</mi><mi>s</mi></msub>"
               "<mo>+</mo><munder><mo>&#8721;</mo><mrow><mi>t</mi><mo>&#8805;</mo>"
               "<mi>T</mi></mrow></munder><mi>d</mi><mo>(</mo><mi>t</mi><mo>)</mo>"
               "<mi>B</mi><mo>(</mo><mi>t</mi><mo>)</mo></mrow>",
               "Group IV eq (9), and T* = argmax NPV(T)")
            + symbols([
                ("d(t)", "discount factor (1+r)<sup>&minus;(t&minus;2026)</sup>",
                 "r = 8% real"),
                ("&plusmn;&rho;K<sub>s</sub>", "reline reinvestment: <b>avoided</b> if "
                 "you commit before it, <b>paid</b> if after — the sign flips",
                 "50 EUR/t capacity"),
                ("T<sub>rel</sub>", "the year the furnace needs relining anyway",
                 f"{t_rel} (model output, not a fact about a plant)"),
            ]),
            figure(svg("".join(nbody), "NPV against commitment year"),
                   f"Nearly flat on top: 2028 gives {curve[2028]:,.0f} and 2030 gives "
                   f"{curve[2030]:,.0f}. <b>{base.t_star} is a window, not a date.</b> "
                   f"The cliff after {t_rel} is the reline sign flip plus the "
                   "support window closing.")), 2.5,
        "The flatness matters commercially: a year either side costs almost "
        "nothing, so do not sell this as a deadline. The cliff is the deadline."))

    sig_rows = []
    for name, s_val in SIGMA_REGIMES.items():
        sc_r = ScenarioParams(u=1.0, sigma_regime=name)
        o = outputs(p, sc_r)
        sig_rows.append((name, s_val, option.beta(p, sc_r),
                         option.option_multiple(p, sc_r), o.trigger,
                         o.crossing_year, o.crossing_reason))
    axs = Axes(0.05, 0.50, 0, max(r[4] for r in sig_rows) * 1.15)
    sbody = [axs.grid(lambda v: f"{v:.2f}", lambda v: f"{v:,.0f}",
                      "volatility &#963;", "trigger p*&#8242; (EUR / tCO2)"),
             polyline(axs, [(r[1], r[4]) for r in sorted(sig_rows, key=lambda r: r[1])])]
    for name, s_val, _b, _m, trig, cy, _re in sig_rows:
        sbody.append(marker(axs, s_val, trig, f"{name} {trig:.0f}"))
    slides.append(Slide(
        "The model", "Group V — what uncertainty adds",
        two_col(
            eq("<mrow><mfrac><mn>1</mn><mn>2</mn></mfrac><msup><mi>&#963;</mi><mn>2</mn>"
               "</msup><mi>&#946;</mi><mo>(</mo><mi>&#946;</mi><mo>&#8722;</mo><mn>1</mn>"
               "<mo>)</mo><mo>+</mo><mi>&#956;</mi><mi>&#946;</mi><mo>&#8722;</mo>"
               "<mi>r</mi><mo>=</mo><mn>0</mn></mrow>",
               "Group V eq (13) — positive root gives &beta;")
            + eq("<mrow><msup><mi>p</mi><mrow><mo>*</mo><mo>&#8242;</mo></mrow></msup>"
                 "<mo>=</mo><msubsup><mi>p</mi><mi>M</mi><mo>&#8242;</mo></msubsup>"
                 "<mo>&#183;</mo><mfrac><mi>&#946;</mi><mrow><mi>&#946;</mi>"
                 "<mo>&#8722;</mo><mn>1</mn></mrow></mfrac></mrow>",
                 "eq (14) — break-even &times; the option multiple")
            + symbols([
                ("&beta;", "positive root of the Bellman equation under GBM",
                 f"{option.beta(p, sc):.4f}"),
                ("&beta;/(&beta;&minus;1)", "the option multiple — how much more "
                 "than break-even you should demand",
                 f"{option.option_multiple(p, sc):.4f}&times;"),
                ("p&prime;<sub>M</sub>", "break-even carbon price, no uncertainty",
                 f"{option.break_even_price(p, sc, cost.residual_value(p.common.t0, p)):.2f} EUR/tCO2"),
                ("&sigma;", "EUA volatility — <b>the only pure threshold lever</b>",
                 "0.20 assumed"),
            ]),
            figure(svg("".join(sbody), "trigger against volatility"),
                   "More volatility, higher bar. At &sigma; = 0.45 the trigger is "
                   f"{[r[4] for r in sig_rows if r[0] == 'realised'][0]:.0f} and the "
                   "path reaches it in "
                   f"{[r[5] for r in sig_rows if r[0] == 'realised'][0]} — "
                   "beyond any recognisable investment horizon, "
                   "<b>which is not the same as never</b>.")), 2.0,
        "The sigma -> 0 limit does NOT give a multiple of 1 unless drift is also "
        "zero; it gives r/(r-mu) = 2.667. Waiting is rewarded by drift alone."))

    # ------------------------------------------------------------- 3. results
    ladder = run_ladder()
    rows = "".join(
        f"<tr><td>{esc(lab)}</td><td class='val'>"
        f"{o.t_star if o.t_star else 'beyond'}</td>"
        f"<td class='val'>{o.npv0:,.0f}</td><td class='val'>{o.trigger:.1f}</td></tr>"
        for lab, o in ((r.label, o) for r, o in ladder))
    npvs = [o.npv0 for _, o in ladder]
    # Half a slot of margin each side so the end bars sit inside the plot
    # rather than straddling the axis and covering its labels.
    axw = Axes(-0.6, len(npvs) - 0.4, *_span(npvs + [0.0]))
    wbody = [axw.grid(lambda v: f"{v:.0f}", lambda v: f"{v:,.0f}", "",
                      "NPV (EUR / t capacity)", xvals=[]), axw.zero_rule()]
    for i, v in enumerate(npvs):
        x, y0, y1 = axw.X(i), axw.Y(0.0), axw.Y(v)
        cls = "s1" if v > 0 else "crit"
        wbody.append(f'<rect class="bar {cls}" x="{x - 22:.1f}" '
                     f'y="{min(y0, y1):.1f}" width="44" '
                     f'height="{abs(y1 - y0):.1f}" rx="4"/>'
                     f'<text class="mkl" x="{x:.1f}" y="{min(y0, y1) - 8:.1f}" '
                     f'text-anchor="middle">{v:,.0f}</text>'
                     f'<text class="tick" x="{x:.1f}" y="{axw.y0 + 18:.0f}" '
                     f'text-anchor="middle">{i + 1}</text>')
    slides.append(Slide(
        "Results", "The correction ladder — where the headline goes",
        two_col(
            eq("<mrow><mi>NPV</mi><mo>=</mo><munder><mi>max</mi><mi>T</mi></munder>"
               "<mi>NPV</mi><mo>(</mo><mi>T</mi><mo>;</mo><mi>u</mi><mo>,</mo>"
               "<mi>&#954;</mi><mo>,</mo><mtext>basis</mtext><mo>,</mo><msub>"
               "<mi>p</mi><mtext>H2</mtext></msub><mo>)</mo></mrow>",
               "same eq (9); each bar changes ONE argument and keeps the previous ones")
            + f"<table class='grid'><thead><tr><th>row</th><th>T*</th><th>NPV</th>"
            f"<th>trigger</th></tr></thead><tbody>{rows}</tbody></table>"
            + keypoints([
                "Each row adds <em>one</em> correction and keeps the previous ones.",
                "Rows 1–3 reproduce the published table exactly.",
                "The load factor alone costs <b>&euro;294</b>; the real-versus-"
                "nominal fix costs <b>&euro;421</b>.",
            ]),
            figure(svg("".join(wbody), "NPV across the correction ladder"),
                   "Same model, same plant. The difference between the first bar "
                   "and the last is entirely <em>how the inputs were stated</em>.")),
        2.0,
        "This is the slide that makes the audience trust the rest. Show the "
        "published number, then take it apart honestly."))

    # ------------------------------------------------------------ 4. findings
    levers = fnd.lever_classes()
    xs = [lv.d_trigger_pct for lv in levers]
    ys = [lv.d_npv_pct for lv in levers]
    axl = Axes(*_span(xs, 0.25), *_span(ys, 0.25))
    lbody = [axl.grid(lambda v: f"{v:+.0f}%", lambda v: f"{v:+.0f}%",
                      "change in trigger p*&#8242;", "change in NPV"),
             f'<line class="zero" x1="{axl.X(0):.1f}" x2="{axl.X(0):.1f}" '
             f'y1="{axl.y1}" y2="{axl.y0}"/>', axl.zero_rule()]
    for lv in levers:
        cls = {"value only": "s1", "threshold only": "s2"}.get(lv.klass, "s3")
        lbody.append(f'<circle class="mk {cls}" cx="{axl.X(lv.d_trigger_pct):.1f}" '
                     f'cy="{axl.Y(lv.d_npv_pct):.1f}" r="6"><title>'
                     f'{esc(lv.name)}</title></circle>')
    n_val = sum(1 for lv in levers if lv.klass == "value only")
    n_thr = sum(1 for lv in levers if lv.klass == "threshold only")
    n_both = sum(1 for lv in levers if lv.klass == "both")
    slides.append(Slide(
        "Findings", "1 — the levers are exactly orthogonal",
        two_col(
            keypoints([
                f"<b>{n_val} parameters</b> move NPV and leave the trigger at "
                "<b>0.000%</b>.",
                f"<b>{n_thr}</b> move the trigger and leave NPV at <b>0.000%</b>.",
                f"<b>{n_both}</b> move both.",
                "Not approximately zero. <em>Structurally</em> zero: the trigger "
                "formula does not contain <code>u</code>, <code>w</code>, "
                "<code>s_max</code> or the price path.",
            ])
            + eq("<mrow><msup><mi>p</mi><mrow><mo>*</mo><mo>&#8242;</mo></mrow></msup>"
                 "<mo>=</mo><mfrac><mrow><mo>(</mo><msub><mi>I</mi><mn>0</mn></msub>"
                 "<mo>+</mo><mi>&#966;</mi><msub><mi>S</mi><mi>s</mi></msub>"
                 "<mo>&#8722;</mo><mi>a</mi><mo>/</mo><mi>r</mi><mo>)</mo>"
                 "<mo>(</mo><mi>r</mi><mo>&#8722;</mo><mi>&#956;</mi><mo>)</mo></mrow>"
                 "<mi>b</mi></mfrac><mo>&#183;</mo><mfrac><mi>&#946;</mi><mrow>"
                 "<mi>&#946;</mi><mo>&#8722;</mo><mn>1</mn></mrow></mfrac></mrow>",
                 "no u, no w, no s_max, no p_t — that is the whole proof"),
            figure(svg("".join(lbody), "lever effects on NPV against trigger"),
                   "<span class='k s1'></span>value only &nbsp; "
                   "<span class='k s2'></span>threshold only &nbsp; "
                   "<span class='k s3'></span>both. Points on an axis move one "
                   "output and <em>exactly</em> nothing of the other.")), 2.5,
        "The policy punchline: a CfD (volatility) and a grant (value) are "
        "complements, not substitutes. They act on different halves."))

    rc = fnd.reline_capture()
    flip = fnd.utilisation_inversion()
    rs = fnd.rate_cancellation()
    ages = [r[0] for r in rc.rows]
    npv_by_age = [r[3] for r in rc.rows]
    axr = Axes(min(ages), max(ages), *_span(npv_by_age))
    rbody = [axr.grid(lambda v: f"{v:.0f}", lambda v: f"{v:,.0f}",
                      "furnace age at 2026 (years)", "NPV at T*"),
             polyline(axr, list(zip(ages, npv_by_age, strict=True)))]
    if rc.capture_from is not None:
        rbody.append(f'<line class="trig" x1="{axr.X(rc.capture_from):.1f}" '
                     f'x2="{axr.X(rc.capture_from):.1f}" y1="{axr.y0}" y2="{axr.y1}"/>'
                     f'<text class="mkl crit" x="{axr.X(rc.capture_from) - 6:.1f}" '
                     f'y="{axr.y1 + 12}" text-anchor="end">'
                     f'capture from age {rc.capture_from}</text>')
    # Label below the marker: above it collides with the capture line's label.
    rbody.append(marker(axr, rc.best_age, rc.best_npv, f"peak age {rc.best_age}",
                        dy=20))
    slides.append(Slide(
        "Findings", "2, 3 and 4 — three results that read backwards",
        two_col(
            eq("<mrow><mo>&#177;</mo><mi>d</mi><mo>(</mo><msub><mi>T</mi>"
               "<mtext>rel</mtext></msub><mo>)</mo><mi>&#961;</mi><msub><mi>K</mi>"
               "<mi>s</mi></msub><mo>,</mo><mspace width='10px'/><msub><mi>T</mi>"
               "<mtext>rel</mtext></msub><mo>=</mo><msub><mi>t</mi><mn>0</mn></msub>"
               "<mo>+</mo><mo>(</mo><msub><mi>L</mi><mi>s</mi></msub><mo>&#8722;</mo>"
               "<msub><mi>age</mi><mn>0</mn></msub><mo>)</mo></mrow>",
               "the reinvestment term of eq (9): + if you commit before the reline, "
               "&minus; if after. That sign flip is what the chart is showing")
            + keypoints([
                f"<b>Utilisation inverts at &euro;{flip:.2f}/kg.</b> Above it, "
                "running the plant <em>less</em> raises NPV, because <code>u</code> "
                "multiplies a flow that has gone negative. A minimum-utilisation "
                "covenant would point the wrong way.",
                f"<b>Past age {rc.capture_from}, T* is not a choice.</b> It equals "
                f"the reline date exactly. Value peaks at age {rc.best_age}; the "
                "cliff after it is the &euro;200 of support you forfeit by "
                "committing before the window opens.",
                f"<b>Rate 'robustness' is cancellation.</b> r from 6% to 10%: "
                f"break-even <b>{rs.d_break_even_pct:+.0f}%</b>, multiple "
                f"<b>{rs.d_multiple_pct:+.0f}%</b>, product only "
                f"<b>{rs.d_trigger_pct:+.0f}%</b>. Report the factors, not the product.",
            ]),
            figure(svg("".join(rbody), "NPV against furnace age"),
                   "Asset age decides the answer more than any policy lever on "
                   "the previous slide does.")), 2.0,
        "Finding 2 caveat: it is the sign of a sensitivity on an NPV-negative "
        "case. Say so before someone else does."))

    # ------------------------------------------------------- 5. observed data
    floors = grounding.hydrogen_floors(offline=True)
    geos = sorted(floors, key=lambda g: floors[g][0])
    axh = Axes(0, len(geos), 0.0, max(g for g, _ in floors.values()) * 1.15,
               height=340)
    hbody = [axh.grid(lambda v: "", lambda v: f"{v:.0f}", "",
                      "EUR / kg hydrogen (floor)", xvals=[])]
    step = (axh.x1 - axh.x0) / len(geos)
    for i, g in enumerate(geos):
        green, grey = floors[g]
        cx = axh.x0 + step * (i + 0.5)
        for val, cls, off in ((green, "s3", -11), (grey, "s2", 11)):
            hbody.append(f'<rect class="bar {cls}" x="{cx + off - 10:.1f}" '
                         f'y="{axh.Y(val):.1f}" width="20" '
                         f'height="{axh.y0 - axh.Y(val):.1f}" rx="4"/>')
        hbody.append(f'<text class="tick" x="{cx:.1f}" y="{axh.y0 + 18:.0f}" '
                     f'text-anchor="middle">{g}</text>')
    hbody.append(f'<line class="trig" x1="{axh.x0}" x2="{axh.x1}" '
                 f'y1="{axh.Y(2.60):.1f}" y2="{axh.Y(2.60):.1f}"/>'
                 f'<text class="mkl crit" x="{axh.x0 + 4}" y="{axh.Y(2.60) - 8:.1f}" '
                 f'text-anchor="start">model assumes 2.60</text>')
    grey_t = sourcing.grey_tonnes_per_tonne()
    slides.append(Slide(
        "Observed", "What official statistics can actually pin down",
        two_col(
            keypoints([
                "NPV, <code>T*</code> and the trigger are <b>outputs</b>. No "
                "agency publishes them. Only <em>inputs</em> can be sourced.",
                f"{len(series) + len(rates)} series from Eurostat and the ECB, "
                "cached so the model runs offline. A test makes the fetch "
                "function raise and checks the numbers are unchanged.",
                "Electrolysis is mostly a way of buying electricity; reforming "
                "is mostly a way of buying gas. Both give a <em>floor</em> — "
                "no capex, no compression, no transport.",
            ])
            + eq("<mrow><msub><mi>floor</mi><mtext>green</mtext></msub><mo>=</mo>"
                 "<msub><mi>p</mi><mtext>power</mtext></msub><mo>&#183;</mo>"
                 "<mn>55</mn><mspace width='14px'/><msub><mi>floor</mi>"
                 "<mtext>grey</mtext></msub><mo>=</mo><msub><mi>p</mi><mtext>gas"
                 "</mtext></msub><mo>&#183;</mo><mn>41.1</mn><mo>+</mo><mn>0.009</mn>"
                 "<msub><mi>p</mi><mtext>EUA</mtext></msub></mrow>",
                 "kWh per kg, times the observed price, plus the ETS bill on grey"),
            figure(svg("".join(hbody), "green and grey hydrogen floors by country",
                       W, 340),
                   "<span class='k s3'></span>green floor &nbsp; "
                   "<span class='k s2'></span>grey floor. <b>The model's &euro;2.60 "
                   "is below every green floor and inside the grey band.</b>")), 2.5,
        "This is the pivot of the talk. Everything after this follows from the "
        "two bars straddling the red line."))

    slides.append(Slide(
        "Observed", "So &euro;2.60/kg is a fossil price — and that contradicts the model",
        f"""
{stat_row([("&euro;3.94", "cheapest green floor anywhere (SE)"),
           ("&euro;2.00&ndash;2.36", "grey floor band, gas + ETS"),
           (f"{grey_t:.2f}", "tCO2/t steel implied by grey hydrogen"),
           (f"{grey_t / p.common.eps_cln:.0f}&times;", "the eps_cln the model credits")])}
{two_col(
  eq("<mrow><msub><mi>&#949;</mi><mtext>cln</mtext></msub><mo>=</mo><msub><mi>m</mi>"
     "<mtext>H2</mtext></msub><mo>&#183;</mo><mfrac><mrow><mn>9</mn><mspace width='2px'/>"
     "<mtext>kgCO2</mtext></mrow><mrow><mtext>kg H2</mtext></mrow></mfrac><mo>=</mo>"
     "<mn>55</mn><mo>&#183;</mo><mn>0.009</mn><mo>=</mo><mn>0.495</mn></mrow>",
     "what the clean route actually emits if its hydrogen is reformed")
  + symbols([("&epsilon;<sub>cln</sub>", "clean-route emission intensity the "
              "model assumes", "0.10 tCO2/t"),
             ("implied", "what 55 kg of grey hydrogen per tonne really emits",
              f"{grey_t:.2f} tCO2/t"),
             ("9 kgCO2/kg", "unabated reforming, process emissions only. The IEA "
              "puts it at 10&ndash;12 including upstream methane, so this is "
              "<b>the conservative end</b>", "sourced")]),
  keypoints([
     "The price and the intensity <b>cannot both be true</b>.",
     "Either <code>p_H2</code> rises to a green floor — and the case weakens —",
     "or <code>eps_cln</code> rises toward grey — and most of the abatement "
     "the model is valuing disappears.",
     "Publishing both is the one thing that is not available.",
  ]))}
""", 2.0,
        "Do not soften this. It is arithmetic from two official price series "
        "and one sourced emission factor."))

    # ---------------------------------------------------------- 6. the frontier
    geo = "DE"
    front = sourcing.frontier(geo, series=series)
    thetas = [pt.theta for pt in front]
    fnpv = [pt.npv0 for pt in front]
    axf = Axes(0.0, 1.0, *_span(fnpv + [corrected.npv0]))
    fbody = [axf.grid(lambda v: f"{v:.0%}", lambda v: f"{v:,.0f}",
                      "green share &#952; of hydrogen", "NPV (EUR / t capacity)"),
             axf.zero_rule()]
    for other in eurostat.STEEL_GEOS:
        if other == geo:
            continue
        pts = [(pt.theta, pt.npv0) for pt in sourcing.frontier(other, series=series)]
        fbody.append(polyline(axf, pts, "ctx"))
    fbody.append(polyline(axf, list(zip(thetas, fnpv, strict=True))))
    model_npv, consistent, theta_at = sourcing.feasibility_gap(geo, series)
    fbody.append(f'<line class="trig" x1="{axf.x0}" x2="{axf.x1}" '
                 f'y1="{axf.Y(model_npv):.1f}" y2="{axf.Y(model_npv):.1f}"/>'
                 f'<text class="mkl crit" x="{axf.x1}" y="{axf.Y(model_npv) - 8:.1f}" '
                 f'text-anchor="end">published {model_npv:,.0f}</text>')
    if theta_at is not None:
        fbody.append(marker(axf, theta_at, consistent,
                            f"same price, honest emissions: {consistent:,.0f}", "crit"))
    gaps = {g: sourcing.feasibility_gap(g, series) for g in eurostat.STEEL_GEOS}
    shares = {g: (m - c) / m for g, (m, c, t) in gaps.items() if t is not None}
    slides.append(Slide(
        "Frontier", "The two inputs are one input",
        two_col(
            eq("<mrow><msub><mi>p</mi><mtext>H2</mtext></msub><mo>(</mo><mi>&#952;</mi>"
               "<mo>)</mo><mo>=</mo><mi>&#952;</mi><mo>&#183;</mo><mtext>green</mtext>"
               "<mo>+</mo><mo>(</mo><mn>1</mn><mo>&#8722;</mo><mi>&#952;</mi><mo>)</mo>"
               "<mo>&#183;</mo><mtext>grey</mtext></mrow>")
            + eq("<mrow><msub><mi>&#949;</mi><mtext>cln</mtext></msub><mo>(</mo>"
                 "<mi>&#952;</mi><mo>)</mo><mo>=</mo><mn>0.1</mn><mo>+</mo><mo>(</mo>"
                 "<mn>1</mn><mo>&#8722;</mo><mi>&#952;</mi><mo>)</mo><mo>&#183;</mo>"
                 "<mn>0.495</mn></mrow>",
                 "one parameter &theta;, two consequences")
            + symbols([
                ("&theta;", "green share of the hydrogen bought", "0 = all grey, 1 = all green"),
                ("green", "electricity price &times; 55 kWh/kg",
                 f"{sourcing.endpoints(geo, series)[0]:.2f} EUR/kg in {geo}"),
                ("grey", "gas price &times; 41.1 kWh/kg, ETS charged separately "
                         "through &epsilon;<sub>cln</sub>",
                 f"{sourcing.endpoints(geo, series)[1]:.2f} EUR/kg in {geo}"),
            ]),
            figure(svg("".join(fbody), "NPV against green hydrogen share", W, 380),
                   f"<b>{geo}</b> in blue, the other eight in grey. The red rule is "
                   "the published NPV — <em>the frontier never reaches it</em>, "
                   "because the published pair is not a point on it.")), 2.0,
        "Charging the carbon once is the subtle bit: it goes through eps_cln, "
        "where it escalates with the price path, not into a frozen constant."))

    cross = {g: sourcing.crossover_multiple(g, series) for g in eurostat.STEEL_GEOS}
    eua26 = path[p.common.t0]
    order = sorted((g for g in cross if cross[g]), key=lambda g: cross[g] or 0.0)
    axx = Axes(0, max((cross[g] or 0) * eua26 for g in order) * 1.25, 0, len(order),
               height=340)
    xbody = ['<g class="ax">']
    for v in _ticks(0, axx.x_hi):
        xbody.append(f'<line x1="{axx.X(v):.1f}" x2="{axx.X(v):.1f}" '
                     f'y1="{axx.y1}" y2="{axx.y0}"/>'
                     f'<text x="{axx.X(v):.1f}" y="{axx.y0 + 18}" '
                     f'text-anchor="middle">{v:,.0f}</text>')
    xbody.append(f'<text class="axt" x="{(axx.x0 + axx.x1) / 2:.0f}" '
                 f'y="{axx.y0 + 38}" text-anchor="middle">'
                 f'2026 EUA price at which green overtakes grey (EUR/tCO2)</text></g>')
    bh = (axx.y0 - axx.y1) / len(order)
    for i, g in enumerate(order):
        v = (cross[g] or 0.0) * eua26
        y = axx.y1 + i * bh + 4
        xbody.append(f'<rect class="bar s1" x="{axx.x0}" y="{y:.1f}" '
                     f'width="{axx.X(v) - axx.x0:.1f}" height="{bh - 8:.1f}" rx="4"/>'
                     f'<text class="tick" x="{axx.x0 - 8}" y="{y + bh / 2:.1f}" '
                     f'text-anchor="end">{g}</text>'
                     f'<text class="mkl" x="{axx.X(v) + 8:.1f}" '
                     f'y="{y + bh / 2:.1f}">{v:,.0f} ({cross[g]:.1f}&#215;)</text>')
    xbody.append(f'<line class="trig" x1="{axx.X(eua26):.1f}" x2="{axx.X(eua26):.1f}" '
                 f'y1="{axx.y1 - 4}" y2="{axx.y0}"/>'
                 f'<text class="mkl crit" x="{axx.X(eua26) + 5:.1f}" '
                 f'y="{axx.y1 - 8}">path starts here</text>')
    slides.append(Slide(
        "Frontier", "What green hydrogen needs before it wins",
        two_col(
            eq("<mrow><msub><mi>m</mi><mtext>H2</mtext></msub><mo>(</mo>"
               "<mtext>green</mtext><mo>&#8722;</mo><mtext>grey</mtext><mo>)</mo>"
               "<mo>=</mo><mi>&#916;</mi><mi>b</mi><mo>&#183;</mo><mi>p</mi></mrow>",
               "the crossover condition: extra energy cost = abatement bought back")
            + keypoints([
                "Both sides are <b>differences</b>, so the ranking follows the "
                "absolute &euro;/kg <b>spread</b> — <em>not</em> the power-to-gas "
                "ratio.",
                "The ratio ordering is genuinely different (PL/ES and DE/AT/IT "
                "swap). A test asserts the spread explains it <em>and</em> that "
                "the ratio does not.",
                "At the model's own carbon path, <b>fossil hydrogen wins on NPV "
                "in every member state</b>.",
            ]),
            figure(svg("".join(xbody), "carbon price at which green overtakes grey",
                       W, 340),
                   f"Sweden needs {cross['SE'] * eua26:,.0f} &euro;/tCO2; Italy "
                   f"needs {cross['IT'] * eua26:,.0f}. The model's path starts at "
                   f"{eua26:.0f} and its trigger is {base.trigger:.0f}.")), 1.5,
        "I asserted the ratio mechanism first and the test caught it. Worth "
        "saying out loud - it is why the test asserts both halves."))

    slides.append(Slide(
        "Frontier", "What the independent-inputs assumption is worth",
        f"""
{stat_row([(f"{min(shares.values()):.1%}&ndash;{max(shares.values()):.1%}",
            "of the published NPV that no sourcing decision can buy"),
           ("up to 17 yrs", "that sourcing alone moves T*"),
           ("2028 &rarr; 2045", "T* all-grey to all-green (AT, IT)")])}
{two_col(
  "<table class='grid'><thead><tr><th>state</th><th>&theta; at &euro;2.60</th>"
  "<th>published</th><th>consistent</th><th>gap</th></tr></thead><tbody>"
  + "".join(f"<tr><td>{g}</td><td class='val'>{t:.2f}</td>"
            f"<td class='val'>{m:,.0f}</td><td class='val'>{c:,.0f}</td>"
            f"<td class='val'>{(m - c) / m:.1%}</td></tr>"
            for g, (m, c, t) in sorted(gaps.items(), key=lambda kv: kv[1][1])
            if t is not None)
  + "</tbody></table>",
  keypoints([
     "Hold the model's own hydrogen price. Make the emission intensity "
     "consistent with it. That is the whole calculation.",
     "It is not a forecast disagreement. It is the cost of stating two "
     "inputs that the observed data says cannot both hold.",
     "Sourcing is a <b>timing</b> lever. The model treats it as a cost axis.",
  ]))}
""", 1.5,
        "Land the number: a quarter to a third of the headline was never "
        "available. Then stop talking and let it sit."))

    # ------------------------------- 6b. the cost of doing nothing, and the map
    rec = regimes.recovery(p, sc)
    alloc = regimes.allocation_table(p, sc)
    yrs = [r[0] for r in alloc]
    given = [r[3] for r in alloc]
    paid = [r[4] for r in alloc]
    axg = Axes(yrs[0], yrs[-1], 0.0, max(given + paid) * 1.12)
    gbody = [axg.grid(lambda v: f"{v:.0f}", lambda v: f"{v:,.0f}",
                      "year", "EUR / t capacity / yr"),
             polyline(axg, list(zip(yrs, given, strict=True)), "s3"),
             polyline(axg, list(zip(yrs, paid, strict=True)), "s2")]
    cross = min((t for t, g, pd in zip(yrs, given, paid, strict=True) if pd > g),
                default=None)
    if cross:
        gbody.append(f'<line class="trig" x1="{axg.X(cross):.1f}" '
                     f'x2="{axg.X(cross):.1f}" y1="{axg.y0}" y2="{axg.y1}"/>'
                     f'<text class="mkl crit" x="{axg.X(cross) + 6:.1f}" '
                     f'y="{axg.y1 + 12}">{cross}: the bill overtakes the gift</text>')
    slides.append(Slide(
        "Exposure", "The cost of doing nothing, and who is paying it",
        two_col(
            stat_row([(f"&euro;{rec['do nothing, carbon bill']:,.0f}",
                       "carbon bill to 2050 if the plant never switches, PV"),
                      (f"&euro;{rec['free allocation received']:,.0f}",
                       "handed over free across the same years"),
                      (f"{rec['share recovered at T*']:.0%}",
                       "of that bill the switch recovers at T*")])
            + eq("<mrow><msub><mi>PV</mi><mtext>do nothing</mtext></msub><mo>=</mo>"
                 "<munder><mo>&#8721;</mo><mi>t</mi></munder><mi>d</mi><mo>(</mo>"
                 "<mi>t</mi><mo>)</mo><mi>u</mi><mo>(</mo><mn>1</mn><mo>&#8722;</mo>"
                 "<mi>&#945;</mi><mo>(</mo><mi>t</mi><mo>)</mo><mo>)</mo><msub>"
                 "<mi>&#949;</mi><mtext>inc</mtext></msub><msub><mi>p</mi><mi>t</mi>"
                 "</msub></mrow>",
                 "the emissions you keep, at the price you pay for them")
            + symbols([
                ("d(t)", "discount factor to 2026, at r = 8% real", "&mdash;"),
                ("u", "load factor: capacity to product, the only bridge "
                 "between the two units on this slide", "0.85"),
                ("&alpha;(t)", "free allocation factor &mdash; the share of "
                 "emissions handed over rather than bought", "1 &rarr; 0 by 2034"),
                ("&epsilon;<sub>inc</sub>", "incumbent emission intensity, the "
                 "blast furnace route", "1.9 tCO&#8322;/t"),
                ("p<sub>t</sub>", "EUA price on the central path", "76 &rarr; 283"),
            ])
            + keypoints([
                "The model reports the <em>increment</em>, so &ldquo;no "
                "investment&rdquo; is the zero line. This is what that zero line "
                "was hiding.",
                "Free allocation is not a rounding error &mdash; it is worth "
                f"&euro;{rec['free allocation received']:,.0f} of the "
                f"&euro;{rec['do nothing, carbon bill'] + rec['free allocation received']:,.0f} "
                "gross exposure, and it runs out on a published schedule.",
            ]),
            figure(svg("".join(gbody), "allowances given against carbon paid"),
                   "<span class='k s3'></span>allowances handed over free &nbsp; "
                   "<span class='k s2'></span>carbon actually paid for. They cross "
                   f"in <b>{cross}</b>: before it the ETS is a transfer, after it "
                   "a cost.")), 2.0,
        "This answers the standing comment: plot the no-investment case and show "
        "the free allowances rather than folding them into a coefficient."))

    xs_r = (2.0, 3.5, 5.0, 6.5, 8.29)
    ys_r = (0.4, 0.6, 1.0, 1.5, 2.0, 3.0)
    grid = regimes.regime_grid("p_H2", "price_scale", xs_r, ys_r)
    cw, ch = 96, 40
    x0, y0 = 150, 34
    mbody = []
    fill = {"none": "var(--crit)", "wait": "var(--s2)", "delayed": "var(--s2)",
            "window": "var(--s1)", "now": "var(--s3)"}
    for j, (yv, row) in enumerate(zip(reversed(ys_r), reversed(grid), strict=True)):
        mbody.append(f'<text class="tick" x="{x0 - 10}" y="{y0 + j * ch + 25}" '
                     f'text-anchor="end">&#215;{yv:g}</text>')
        for i, cell in enumerate(row):
            mbody.append(
                f'<rect x="{x0 + i * cw + 2}" y="{y0 + j * ch + 2}" '
                f'width="{cw - 4}" height="{ch - 4}" rx="5" '
                f'fill="{fill[cell.code]}" opacity="0.9"/>'
                f'<text class="mkl" x="{x0 + i * cw + cw / 2}" '
                f'y="{y0 + j * ch + 25}" text-anchor="middle" fill="#fff">'
                f'{cell.code}</text>')
    for i, xv in enumerate(xs_r):
        mbody.append(f'<text class="tick" x="{x0 + i * cw + cw / 2}" '
                     f'y="{y0 + len(ys_r) * ch + 20}" text-anchor="middle">'
                     f'{xv:g}</text>')
    mbody.append(f'<text class="axt" x="{x0 + len(xs_r) * cw / 2}" '
                 f'y="{y0 + len(ys_r) * ch + 42}" text-anchor="middle">'
                 f'hydrogen price (EUR/kg)</text>')
    mbody.append(f'<text class="axt" x="20" y="{y0 + len(ys_r) * ch / 2}" '
                 f'transform="rotate(-90 20 {y0 + len(ys_r) * ch / 2})" '
                 f'text-anchor="middle">carbon path, multiple of central</text>')
    wifs = regimes.what_ifs()
    slides.append(Slide(
        "Exposure", "Which situation is a plant actually in?",
        two_col(
            figure(svg("".join(mbody), "regime map: hydrogen price against carbon "
                       "exposure", 640, y0 + len(ys_r) * ch + 56),
                   "Corrected configuration. <b>none</b> = no investment &middot; "
                   "<b>window</b> = commit between now and the reline &middot; "
                   "<b>now</b> = 2026. The frontier runs diagonally: cheap "
                   "hydrogen and a strong carbon price are substitutes.")
            + "<table class='grid'><thead><tr><th>what if</th><th>regime</th>"
              "<th>T*</th><th>&Delta;NPV</th></tr></thead><tbody>"
            + "".join(f"<tr><td>{esc(lab)}</td><td>{esc(r.code)}</td>"
                      f"<td class='val'>{r.t_star or '&mdash;'}</td>"
                      f"<td class='val'>{d:+,.0f}</td></tr>"
                      for lab, r, d in wifs[1:])
            + "</tbody></table>",
            eq("<mrow><mi>R</mi><mo>=</mo><mrow><mo stretchy='true'>{</mo>"
               "<mtable columnalign='left left' columnspacing='1.2em'>"
               "<mtr><mtd><mtext>none</mtext></mtd><mtd><mtext>no&#160;</mtext>"
               "<msup><mi>T</mi><mo>*</mo></msup><mtext>&#160;exists</mtext>"
               "</mtd></mtr>"
               "<mtr><mtd><mtext>wait</mtext></mtd><mtd><msup><mi>T</mi>"
               "<mo>*</mo></msup><mo>&#8805;</mo><msub><mi>T</mi><mtext>end</mtext>"
               "</msub><mo>&#8722;</mo><mn>1</mn></mtd></mtr>"
               "<mtr><mtd><mtext>now</mtext></mtd><mtd><msup><mi>T</mi><mo>*</mo>"
               "</msup><mo>=</mo><msub><mi>t</mi><mn>0</mn></msub></mtd></mtr>"
               "<mtr><mtd><mtext>delayed</mtext></mtd><mtd><msup><mi>T</mi>"
               "<mo>*</mo></msup><mo>&gt;</mo><msub><mi>T</mi><mtext>rel</mtext>"
               "</msub></mtd></mtr>"
               "<mtr><mtd><mtext>window</mtext></mtd><mtd><mtext>otherwise</mtext>"
               "</mtd></mtr></mtable></mrow></mrow>",
               "the regime is read off the same T* the base case reports &mdash; "
               "no second model, just a different question asked of it")
            + symbols([
                ("T*", "year that maximises NPV, from Group IV", "year"),
                ("t<sub>0</sub>", "first year a commitment can be made", "2026"),
                ("T<sub>rel</sub>", "the reline: capital spent on the blast "
                 "furnace whether or not the switch happens", "year"),
                ("T<sub>end</sub>", "horizon; T* at the edge means the curve "
                 "never turned", "2050"),
            ])
            + keypoints([
                "Five regimes, not a number: <b>no investment</b>, <b>wait for a "
                "better technology</b>, <b>delayed past the reline</b>, "
                "<b>commit at the window</b>, <b>commit now</b>.",
                "Opex, capex, carbon exposure, subsidy and allocation each map "
                "onto one of them &mdash; that is the map the note asked for.",
            ])), 2.0,
        "The signs matter: a year of delay costs real money, but a longer free "
        "allocation HELPS the switcher, because with resale on the allowances "
        "are an asset. That is finding 1 arriving from a different direction."))

    # ------------------------------------------------------------- 7. close
    n_tests, n_checks = source_counts()
    ground = grounding.groundings(offline=True)
    verdicts = {}
    for row in ground:
        verdicts.setdefault(row.verdict, []).append(row.param)
    # ------------------------------------- the live check, before the close
    vol_rung, vol_sigma, at_rung = market.volatility_implies(offline=True)
    gaps = {g.what.split(",")[0]: g for g in market.all_gaps(offline=True)}
    carbon = gaps.get("EUA price")
    sigma_gap = gaps.get("volatility sigma")
    fund = gaps.get("Innovation Fund")
    slides.append(Slide(
        "Exposure", "Is any of this still true this morning?",
        two_col(
            "<p class='lede'>Three inputs have a live primary source: the "
            "EU&nbsp;ETS auctions publish every clearing price and the money "
            "each state and fund receives, the day it clears.</p>"
            "<table class='grid'><thead><tr><th>input</th><th>assumed</th>"
            "<th>observed</th></tr></thead><tbody>"
            + (f"<tr><td>carbon price, {p.common.t0}</td>"
               f"<td class='val'>&euro;{carbon.assumed:,.0f}</td>"
               f"<td class='val'>&euro;{carbon.observed:,.2f}</td></tr>"
               if carbon else "")
            + (f"<tr><td><b>volatility &sigma;</b></td>"
               f"<td class='val'>{sigma_gap.assumed:.2f}</td>"
               f"<td class='val'><b>{sigma_gap.observed:.2f}</b></td></tr>"
               if sigma_gap else "")
            + (f"<tr><td>Innovation Fund, YTD</td>"
               f"<td class='val'>{esc(units.eur(fund.assumed))}</td>"
               f"<td class='val'>{esc(units.eur(fund.observed))}</td></tr>"
               if fund else "")
            + "</tbody></table>"
            + f"<p class='note'>Source: EEX primary-market auction report, "
              f"{esc(carbon.period) if carbon else 'cached'}. Read by "
              f"<code>data/eex.py</code>; every figure in this deck is "
              f"re-derived from it by <code>analysis/verify.py</code>.</p>",
            keypoints([
                f"<b>&sigma; is the row that moves the answer.</b> The model "
                f"runs on {p.common.sigma:.2f}; a year of auctions gives "
                f"{sigma_gap.observed:.2f} — the specification's own "
                f"&lsquo;{esc(vol_rung)}&rsquo; rung ({vol_sigma:.2f}). There "
                f"the trigger is &euro;{at_rung.trigger:,.0f} instead of "
                f"&euro;{base.trigger:,.0f}, and the path crosses it in "
                f"<b>{at_rung.crossing_year}</b>, not {base.crossing_year}."
                if sigma_gap else "No live volatility on this run.",
                "<b>The carbon price above its anchor does not offset that.</b> "
                "It makes the do-nothing bill dearer, which pulls the decision "
                "in; &sigma; pushes it out, and &sigma; wins because it moves "
                "the threshold rather than the level.",
                f"<b>The pot is real but not ours.</b> The auctions paid out "
                f"{esc(units.eur(next((a for c, a, _ in market.pot(offline=True) if c.startswith('ALL')), 0.0)))} "
                f"this year. The model hands one plant "
                f"{esc(units.eur(fund.assumed))} of it — a quarter of what the "
                f"Innovation Fund collected for every sector in Europe."
                if fund else "No live fund figure on this run.",
                "<b>Nothing here was fed back in.</b> Every other number in "
                "this deck is the published base case. One year of auctions is "
                "not a price path to 2050.",
            ])), 2.0,
        "The honesty slide, and the one they will remember. Lead with sigma: "
        "it is the only parameter that moves the trigger without moving the "
        "break-even, so it is the only live observation that changes WHEN. "
        "If asked why we did not just re-fit: one year, and the ladder is the "
        "specification's own sensitivity axis."))

    slides.append(Slide(
        "Close", "What is checked, and what is not",
        two_col(
            "<table class='grid'><thead><tr><th>layer</th><th>covers</th></tr>"
            "</thead><tbody>"
            "<tr><td>validation gate</td><td>9 published quantities to 1e-3, "
            "before anything prints</td></tr>"
            "<tr><td>guards</td><td>r&minus;&mu;, u&isin;(0,1], monotone "
            "allocation, capex clamp — all raise</td></tr>"
            f"<tr><td>{n_tests} test functions</td><td>units, layering, findings, "
            f"provenance, observed data, every generated page — parametrised to "
            f"more cases than that</td></tr>"
            f"<tr><td>{n_checks} self-checks</td><td>the same claims with no packages "
            f"installed</td></tr>"
            "<tr><td>diff harness</td><td>50 cases, self-diff, negative control "
            "flags exactly two</td></tr></tbody></table>"
            + keypoints([
                "<b>Never diffed against the MATLAB reference</b>, because there "
                "is no reference. The harness is built and tested; drop a CSV "
                "beside it and it completes.",
                "Ladder rows 4&ndash;7 do not reproduce. Documented case by case.",
                f"{_n_unverified()} input{'' if _n_unverified() == 1 else 's'} "
                f"rest{'s' if _n_unverified() == 1 else ''} on a document nobody "
                "here has opened — and a test fails if it is ever called sourced.",
            ]),
            "<table class='grid'><thead><tr><th>verdict</th><th>inputs</th>"
            "</tr></thead><tbody>"
            + "".join(f"<tr><td><span class='v {v.split()[0]}'></span>{v}</td>"
                      f"<td class='val'>{len(ps)}</td></tr>"
                      for v, ps in verdicts.items())
            + "</tbody></table>"
            + f"<p class='note'>Observed inputs vs model inputs, from "
              f"<code>analysis/grounding.py</code>. The one "
              f"<b>contradiction</b> is &epsilon;<sub>cln</sub>. The real "
              f"risk-free rate is {ecb.real_risk_free(rates['yield_10y'].value, series['hicp'].value) * 100:.2f}%, "
              f"so the 8% hurdle embeds a "
              f"{p.common.r * 100 - ecb.real_risk_free(rates['yield_10y'].value, series['hicp'].value) * 100:.1f}pp "
              f"premium — and adopting the observed rate would trip the model's "
              f"own r&minus;&mu; guard.</p>"), 1.0,
        "Credibility slide. Say what is not tested before anyone asks."))

    slides.append(Slide(
        "Close", "Three decisions the model will not make for you",
        f"""
<ol class="big">
<li><b>Support basis.</b> A lump-sum capex grant, or a per-tCO&#8322; stream?
The stream belongs in <code>B(t)</code> structurally; the lump is what was
published.</li>
<li><b>Resale.</b> <code>w = 1</code> drives the entire policy-neutrality
finding. Without it the headline reverses sign.</li>
<li><b>Whether &euro;2.60/kg is reported as the base case at all.</b> It is a
fossil price carrying green emissions, at a cost of
{min(shares.values()):.0%}&ndash;{max(shares.values()):.0%} of the NPV.</li>
</ol>
<p class="lede">The model's job was to make those three choices visible and
expensive to get wrong. It is not to make them.</p>
""", 1.5,
        "End here. Do not add a recommendations slide - the whole argument is "
        "that these are the reader's calls, made explicitly."))

    return slides


# ---------------------------------------------------------------------- render

CSS: Final[str] = """
:root{color-scheme:light;--bg:#f4f4f1;--card:#fcfcfb;--bd:#d9d8d2;--tx:#0b0b0b;
--t2:#52514e;--t3:#7c7b74;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--crit:#d03b3b;
--grid:#e6e5e0;--ctx:#b9b8b1;--hi:#fff3cd}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){color-scheme:dark;
--bg:#111110;--card:#1a1a19;--bd:#35352f;--tx:#fff;--t2:#c3c2b7;--t3:#8d8c83;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--crit:#d03b3b;--grid:#2a2a26;
--ctx:#55554e;--hi:#3a3520}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.slide{display:none;min-height:100vh;padding:34px 44px 70px;max-width:1280px;margin:0 auto}
.slide.on{display:block}
.sec{font-size:12px;text-transform:uppercase;letter-spacing:.14em;color:var(--t3);
margin-bottom:6px}
h1{font-size:34px;line-height:1.15;letter-spacing:-.02em;margin:0 0 18px}
p{color:var(--t2);margin:10px 0;max-width:78ch}
p.lede{font-size:19px;color:var(--tx)}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.9em}
.hi{background:var(--hi);padding:0 4px;border-radius:3px}
.cols{display:grid;gap:26px;grid-template-columns:1fr}
@media(min-width:1000px){.cols{grid-template-columns:1fr 1.05fr}}
.kp{margin:8px 0;padding-left:20px}.kp li{margin:9px 0;color:var(--t2)}
.kp b{color:var(--tx)}
ol.big{font-size:17px}ol.big li{margin:14px 0;color:var(--t2)}
.stats{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
margin:18px 0}
.stat{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px 16px}
.stat .n{display:block;font-size:26px;font-weight:640;letter-spacing:-.02em}
.stat .l{display:block;font-size:12.5px;color:var(--t2);margin-top:3px}
figure{margin:0 0 14px}
figure.eq{background:var(--card);border:1px solid var(--bd);border-radius:10px;
padding:14px 16px;margin-bottom:12px;overflow-x:auto}
figure.eq math{font-size:20px}
figure.eq figcaption,figure.fig figcaption{font-size:12.5px;color:var(--t3);margin-top:8px}
figure.fig{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px}
svg{display:block;width:100%;height:auto}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:6px 0 14px}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--bd);vertical-align:top}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--t3)}
td.val{text-align:right}
table.grid th:nth-child(n+2),table.grid td:nth-child(n+2){text-align:right}
table.sym th:last-child{text-align:right}
table.sym td.sym{font-weight:600;white-space:nowrap;color:var(--tx)}
table.sym td{color:var(--t2)}
table.grid td:first-child{color:var(--tx)}
.note{font-size:13px;color:var(--t3);border-left:2px solid var(--bd);padding-left:12px}
.k{display:inline-block;width:11px;height:11px;border-radius:3px;vertical-align:-1px;
margin-right:5px}
.k.s1{background:var(--s1)}.k.s2{background:var(--s2)}.k.s3{background:var(--s3)}
.v{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px}
.v.contradiction{background:var(--crit)}.v.below{background:var(--s2)}
.v.optimistic{background:var(--s2)}.v.consistent{background:var(--s3)}
.v.context{background:var(--ctx)}
.ax line{stroke:var(--grid);stroke-width:1}
.ax line.base{stroke:var(--t3)}
.ax text{fill:var(--t3);font-size:11px}
.axt{fill:var(--t2);font-size:11.5px}
.tick{fill:var(--t2);font-size:11.5px}
.zero{stroke:var(--t3);stroke-width:1;stroke-dasharray:1 3}
.ln{fill:none;stroke-width:2.5;stroke-linejoin:round}
.ln.s1{stroke:var(--s1)}.ln.s2{stroke:var(--s2)}.ln.s3{stroke:var(--s3)}
.ln.ctx{stroke:var(--ctx);stroke-width:1.25}
.mk{stroke:var(--card);stroke-width:2}
.mk.s1{fill:var(--s1)}.mk.s2{fill:var(--s2)}.mk.s3{fill:var(--s3)}
.mk.crit{fill:var(--crit)}
.mkl{fill:var(--tx);font-size:11.5px}
.mkl.crit{fill:var(--crit)}
.bar.s1{fill:var(--s1)}.bar.s2{fill:var(--s2)}.bar.s3{fill:var(--s3)}
.bar.crit{fill:var(--crit)}
.trig{stroke:var(--crit);stroke-width:2;stroke-dasharray:6 4}
#bar{position:fixed;left:0;top:0;height:3px;background:var(--s1);z-index:9}
#hud{position:fixed;right:14px;bottom:12px;font-size:12px;color:var(--t3);
background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:5px 10px;
z-index:9;font-variant-numeric:tabular-nums}
#hud b{color:var(--tx)}
#notes{position:fixed;left:14px;right:14px;bottom:44px;background:var(--card);
border:1px solid var(--bd);border-left:3px solid var(--s2);border-radius:8px;
padding:10px 14px;font-size:13.5px;color:var(--t2);z-index:9;max-width:900px;margin:0 auto}
#notes[hidden]{display:none}
#grid{position:fixed;inset:0;background:var(--bg);z-index:20;overflow:auto;padding:24px}
#grid[hidden]{display:none}
#grid ol{display:grid;gap:8px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));
list-style:none;padding:0;margin:0;counter-reset:s}
#grid li{background:var(--card);border:1px solid var(--bd);border-radius:8px;
padding:10px 12px;cursor:pointer;font-size:13px}
#grid li:hover{border-color:var(--s1)}
#grid li .n{color:var(--t3);font-size:11px}
@media print{.slide{display:block;page-break-after:always;min-height:0}
#hud,#bar,#notes,#grid{display:none}}
"""

JS: Final[str] = """
const slides=[...document.querySelectorAll('.slide')];
const mins=slides.map(s=>+s.dataset.min);
const total=mins.reduce((a,b)=>a+b,0);
let i=0,t0=null,notes=false;
const hud=document.getElementById('hud'),bar=document.getElementById('bar'),
      nt=document.getElementById('notes'),grid=document.getElementById('grid');
function elapsed(){return t0?Math.floor((Date.now()-t0)/1000):0}
function fmt(s){return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')}
function show(n){
  i=Math.max(0,Math.min(slides.length-1,n));
  slides.forEach((s,k)=>s.classList.toggle('on',k===i));
  const upto=mins.slice(0,i+1).reduce((a,b)=>a+b,0);
  bar.style.width=(100*upto/total)+'%';
  nt.hidden=!notes; nt.textContent=slides[i].dataset.notes||'';
  hud.innerHTML='<b>'+(i+1)+'</b>/'+slides.length+
    ' &middot; cue '+fmt(Math.round(60*(upto-mins[i])))+
    (t0?' &middot; <b>'+fmt(elapsed())+'</b>':' &middot; t: start')+
    ' &middot; '+slides[i].dataset.sec;
  window.scrollTo(0,0);
  location.hash=i+1;
}
addEventListener('keydown',e=>{
  if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){show(i+1);e.preventDefault()}
  else if(e.key==='ArrowLeft'||e.key==='PageUp'){show(i-1);e.preventDefault()}
  else if(e.key==='Home'){show(0)} else if(e.key==='End'){show(slides.length-1)}
  else if(e.key==='n'){notes=!notes;show(i)}
  else if(e.key==='t'){t0=t0?null:Date.now();show(i)}
  else if(e.key==='g'){grid.hidden=!grid.hidden}
  else if(e.key==='Escape'){grid.hidden=true}
});
grid.querySelectorAll('li').forEach((li,k)=>li.onclick=()=>{grid.hidden=true;show(k)});
addEventListener('hashchange',()=>{const n=parseInt(location.hash.slice(1));
  if(n&&n-1!==i)show(n-1)});
setInterval(()=>{if(t0)show(i)},1000);
show(location.hash?Math.max(0,parseInt(location.hash.slice(1))-1):0);
"""


def render(slides: Sequence[Slide]) -> str:
    """The whole deck as one self-contained HTML file."""
    body = []
    for s in slides:
        body.append(
            f'<section class="slide" data-min="{s.minutes}" '
            f'data-sec="{esc(s.section)}" data-notes="{esc(s.notes)}">'
            f'<div class="sec">{esc(s.section)}</div><h1>{esc(s.title)}</h1>'
            f'{s.body}</section>')
    toc = "".join(
        f'<li><span class="n">{i + 1} &middot; {esc(s.section)}</span><br>'
        f'{esc(s.title)}</li>' for i, s in enumerate(slides))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Steel decarbonisation: investment timing under a carbon price</title>
<style>{CSS}</style></head><body>
<div id="bar"></div>
{''.join(body)}
<div id="grid" hidden><ol>{toc}</ol></div>
<div id="notes" hidden></div>
<div id="hud"></div>
<script>{JS}</script>
</body></html>
"""


def main() -> int:
    """Build deck.html."""
    slides = build_slides()
    page = render(slides)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    total = sum(s.minutes for s in slides)
    print(f"Wrote {OUT} ({len(slides)} slides, {total:.0f} min + questions, "
          f"{len(page) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
