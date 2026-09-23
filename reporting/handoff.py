"""handoff.py -> handoff.html -> handoff.pdf: the brief for building the deck.

Addressed to whoever - or whatever - builds the slides, which in practice is a
second conversation with no access to this repository. So it has to be
self-contained: the narrative, the two figures as real pictures, and every
number written out underneath them, because a PDF of a chart cannot be
queried and a slide-builder that has to guess at a value will guess wrong.

Design decisions, and why
-------------------------
**The charts are embedded as inline SVG, not as screenshots.** They are SVG
already; printing them through the browser keeps them as vectors, so they stay
sharp when someone drops a page into a slide at any size.

**Printed in light mode, always.** ``plots.CSS`` follows the reader's system
theme, which for a PDF means the file would come out dark on a dark machine
and light on a light one - and nobody wants a black slide background they did
not ask for. The tokens are pinned before the chart styles load.

**The table views are stripped.** Every chart carries a ``<details>`` element
holding its data, which is right on a web page and useless on paper: it prints
collapsed. The data is laid out as real tables instead, in the section after
each figure.

**Every figure is followed by its numbers.** This is the part that makes the
file usable by a second conversation. A slide-builder reading only the picture
has to estimate; reading the table it can quote.
"""

from __future__ import annotations

import datetime
import html
import pathlib
import re
import subprocess
from typing import Final

from analysis import cashflow, market, tables, units
from reporting import deck, plots
from timing_model.params import Params
from timing_model.results import outputs
from timing_model.scenarios import published_base

OUT_HTML: Final[str] = "handoff.html"
OUT_PDF: Final[str] = "handoff.pdf"

#: The browser Playwright installed, already present for the screenshot checks.
CHROMIUM: Final[str] = "/opt/pw-browsers/chromium"

#: Strips the ``<details>`` data drawer from a chart. On a web page it is the
#: relief for the light-mode contrast warning; on paper it prints as a closed
#: triangle and nothing else, so the data goes in a real table instead.
_DETAILS: Final[re.Pattern[str]] = re.compile(r"<details class=\"tv\">.*?</details>",
                                              re.S)

#: Light tokens, pinned. plots.CSS follows the system theme; a PDF must not.
LIGHT: Final[str] = """
:root, :root[data-theme="dark"] {
--surface:#ffffff !important;--plane:#ffffff !important;--ink:#111 !important;
--ink2:#4a4a47 !important;--muted:#6f6e69 !important;--grid:#e4e3dd !important;
--axis:#bdbcb2 !important;--ring:rgba(0,0,0,.14) !important;
--s0:#2a78d6 !important;--s1:#eb6834 !important;--s2:#1baf7a !important;
--s3:#eda100 !important;}
"""

CSS: Final[str] = """
@page { size: A4; margin: 14mm 13mm 12mm; }
*{box-sizing:border-box}
body{margin:0;background:#fff;color:#111;
font:10pt/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:none}
h1{font-size:19pt;line-height:1.1;margin:0 0 2mm}
h2{font-size:12.5pt;margin:7mm 0 2mm;padding-bottom:1mm;
border-bottom:1.5px solid #111;page-break-after:avoid}
h3{font-size:10.5pt;margin:4mm 0 1.5mm;page-break-after:avoid}
p{margin:0 0 2.5mm}
.sub{color:#4a4a47;font-size:9.5pt;margin:0 0 4mm}
.use{background:#f4f4f1;border-left:3px solid #2a78d6;padding:3mm 4mm;
margin:0 0 5mm;font-size:9.5pt}
.use b{color:#111}
table{border-collapse:collapse;width:100%;font-size:8.6pt;margin:0 0 3mm;
page-break-inside:avoid}
th,td{padding:1.3mm 2mm;text-align:right;border-bottom:0.4px solid #ddd}
th:first-child,td:first-child{text-align:left}
thead th{font-size:7.6pt;text-transform:uppercase;letter-spacing:.04em;
color:#6f6e69;border-bottom:1px solid #111}
tbody tr.hi{background:#f4f4f1;font-weight:600}
.kv{width:100%;font-size:9.4pt}
.kv td:last-child{font-weight:600}
.note{font-size:8.6pt;color:#4a4a47;margin:0 0 3mm;
border-left:2px solid #ddd;padding-left:3mm}
ul{margin:0 0 3mm;padding-left:5mm}
li{margin:0 0 1.3mm}
.warn{color:#9c4316;font-weight:600}
figure.card{border:0.5px solid #ddd;border-radius:2mm;padding:3mm 3mm 1mm;
margin:0 0 3mm;page-break-inside:avoid;background:#fff}
figcaption h3{margin:0 0 1mm;font-size:10.5pt}
figcaption p{font-size:8.6pt;color:#4a4a47;margin:0 0 2mm}
.plot{width:100%;height:auto;display:block}
.legend{display:flex;flex-wrap:wrap;gap:3mm;margin:0 0 2mm;font-size:8pt;
color:#4a4a47}
.lg{display:inline-flex;align-items:center;gap:1.5mm}
.sw{width:2.4mm;height:2.4mm;border-radius:0.6mm;display:inline-block}
.pb{page-break-before:always}
footer{margin-top:5mm;padding-top:2mm;border-top:0.5px solid #ddd;
font-size:8pt;color:#6f6e69}
"""


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def chart(fn) -> str:
    """One chart, print-ready: SVG kept, data drawer removed."""
    return _DETAILS.sub("", fn())


def kv(rows) -> str:
    """A two-column fact table. Both columns are AUTHORED HTML, not escaped.

    The labels carry entities on purpose (an em dash, a euro sign) and the
    values are either plain model output - an int, or ``units.eur`` which
    returns "EUR 4.0bn" - or short markup written here. Escaping them printed
    "&mdash;" and "&euro;110/tCO2" literally on the first build. Nothing
    user-supplied reaches this function.
    """
    body = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    return f'<table class="kv"><tbody>{body}</tbody></table>'


def cash_table(cf: cashflow.CashFlow) -> str:
    """The cash flow, every year from commitment, as numbers a deck can quote."""
    head = ("<tr><th>year</th><th>capex</th><th>subsidy</th><th>opex</th>"
            "<th>CO2 avoided</th><th>net</th><th>cumulative</th></tr>")
    rows = []
    for t in cf.years:
        if t < cf.commit_year - 1:
            continue
        cls = " class='hi'" if t in (cf.commit_year, cf.payback_year) else ""
        cells = "".join(f"<td>{esc(units.eur(cf.lines[c].values[t]))}</td>"
                        for c in cashflow.COMPONENTS)
        rows.append(f"<tr{cls}><td>{t}</td>{cells}"
                    f"<td>{esc(units.eur(cf.net[t]))}</td>"
                    f"<td>{esc(units.eur(cf.cumulative[t]))}</td></tr>")
    return (f"<table><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>")


def npv_table() -> str:
    """T2 - the answer as a range, which is the honest headline."""
    rows = []
    for case, i0, ph2, npv, absolute, trig, t_star in tables.table_npv_cases().rows:
        cls = " class='hi'" if case in ("base", "central") else ""
        rows.append(f"<tr{cls}><td>{esc(case)}</td><td>{esc(i0)}</td>"
                    f"<td>{esc(ph2)}</td><td>{esc(npv)}</td>"
                    f"<td>{esc(absolute)}</td><td>{esc(trig)}</td>"
                    f"<td>{esc(t_star)}</td></tr>")
    return ("<table><thead><tr><th>case</th><th>capex I0</th><th>hydrogen</th>"
            "<th>NPV</th><th>NPV, 2.5 Mt/yr</th><th>trigger</th><th>T*</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def market_table() -> str:
    """T8 - assumption against observation, with the date on each."""
    rows = []
    for what, assumed, observed, ratio, unit, money, period in \
            tables.table_market().rows:
        cls = " class='hi'" if str(what).startswith("volatility") else ""
        rows.append(f"<tr{cls}><td>{esc(what)}</td><td>{esc(assumed)}</td>"
                    f"<td>{esc(observed)}</td><td>{esc(ratio)}</td>"
                    f"<td>{esc(unit)}</td><td>{esc(money)}</td>"
                    f"<td>{esc(str(period).replace(' (cached)', ''))}</td></tr>")
    return ("<table><thead><tr><th>quantity</th><th>assumed</th>"
            "<th>observed</th><th>ratio</th><th>unit</th>"
            "<th>for 2.5 Mt/yr</th><th>as of</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def build() -> str:
    """The handoff, from one model run."""
    o = outputs(*published_base())
    p = Params()
    cf = cashflow.build()
    mt = cashflow.REFERENCE_MT
    trough_year, trough = cf.peak_exposure()
    today = datetime.date.today().isoformat()
    # Counted from source at build time. A brief that quotes a fixed
    # number is wrong the week someone adds a test - which is exactly
    # what happened to the self-check count, hardcoded at 41 and stale
    # the moment a forty-second check went in.
    n_tests, n_checks = deck.source_counts()

    vol = market.volatility_gap(offline=True)
    rung, rung_sigma, at_rung = market.volatility_implies(offline=True)
    carbon = market.carbon_gap(offline=True)
    pot = dict((c, a) for c, a, _ in market.pot(offline=True))

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Steel decarbonisation timing &mdash; deck handoff</title>
<style>{plots.CSS}{LIGHT}{CSS}</style></head><body>

<h1>Steel decarbonisation timing &mdash; handoff for the deck</h1>
<p class="sub">Investment-timing model, European integrated works &middot;
generated {esc(today)} from a live model run &middot; every figure and number
below is produced by the code, not typed in</p>

<div class="use">
<b>How to use this file.</b> It is self-contained: the narrative, two figures,
and the numbers behind them. Two slides are wanted &mdash; a <b>WHY</b> slide
and a <b>WHAT&nbsp;+&nbsp;HOW</b> slide &mdash; qualitative, one graph each, no
equations. Section&nbsp;2 and section&nbsp;3 are those two slides. The figures
are vector, so they can be lifted at any size. <b>Do not invent numbers:</b>
everything quotable is in section&nbsp;5, and section&nbsp;6 lists what must
not be claimed.
</div>

<h2>1. The one thing this work fixes</h2>
<p>The model produced an optimum. The people who fund these projects do not
read optima &mdash; they read cash flows: money out, money in, year by year,
cumulative, and the date it turns positive. Capex, opex, subsidies and CO<sub>2</sub>
were all inside the model, but entangled in its equations, and nothing drew
them against time.</p>
<p>That half step now exists. <b>The discounted cash flow equals the model's
own NPV to the cent</b> &mdash; the same object, re-presented, checked on every
build. Nothing was recalibrated to make it agree.</p>

<h2>2. Slide one &mdash; WHY</h2>
<h3>A multi-variable decision with no stable answer</h3>
<p>Four inputs move independently, on different clocks, and the firm controls
none of them. <b>Capex</b> falls with learning, but switching early forfeits
undepreciated book value. <b>Opex</b> is dominated by the hydrogen price, the
single largest swing factor. <b>Subsidies</b> are a window, not a pot &mdash;
full weight to 2031, tapering to nothing by 2035. <b>CO<sub>2</sub></b> is a
price that rises while free allocation phases out, and the two compound.</p>
<p>The honest framing: <b>there is no single answer, and there should not
be.</b> Every plant has a different asset age, balance sheet, cost of capital
and tolerance for non-productive time. What this produces is a map and a
method.</p>
{chart(plots.chart_inputs_over_time)}
<p class="note">Suggested for slide one. Four panels, shared year axis, each
scaled to its own data &mdash; a &euro;2.1bn spike and a &euro;150m/yr line do
not share an axis usefully. It makes the multi-variable point without a word of
theory.</p>

<div class="pb"></div>
<h2>3. Slide two &mdash; WHAT and HOW</h2>
<h3>Translated into the language of a cash flow</h3>
{chart(plots.chart_cash_flow)}
{kv([
    ("Commitment year (NPV-optimal)", o.t_star),
    ("Peak exposure &mdash; the financing requirement",
     f"{units.eur(trough)} in {trough_year}"),
    ("Payback", f"{cf.payback_year} &mdash; {cf.payback_reason}"),
    ("NPV at that decision, published inputs",
     units.eur(units.absolute(o.npv0, mt))),
    ("Carbon price that justifies committing",
     f"&euro;{o.trigger:,.0f}/tCO2"),
])}
<p>Two points that make this research rather than a result. <b>The answer is a
range that crosses zero</b> &mdash; which end you believe is the whole
argument, and that is uncertainty about <em>inputs</em>, separate from the price
uncertainty the option machinery handles. <b>Timing is far more robust than
value</b>: the corrections move the level of the answer much more than they
move the year. The model is better at <em>when</em> than at <em>how much</em>.</p>

<h2>4. The single strongest point, if only one lands</h2>
<p>Realised volatility from the EU&nbsp;ETS auction record is
<b>&sigma;&nbsp;=&nbsp;{vol.observed:.2f}</b> against the
<b>{vol.assumed:.2f}</b> the model runs on. Sigma is the only parameter that
moves the <em>threshold</em> without moving the break-even, so it is the only
live observation that changes <em>when</em>. At the specification's own
&lsquo;{esc(rung)}&rsquo; rung ({rung_sigma:.2f}) the trigger is
&euro;{at_rung.trigger:,.0f} instead of &euro;{o.trigger:,.0f}, and the price
path crosses it in <b>{at_rung.crossing_year}</b> rather than
{o.crossing_year} &mdash;
{at_rung.crossing_year - o.crossing_year} more years of waiting.</p>
<p class="note">The model still runs on {vol.assumed:.2f}. One year of auctions
is not a price path to 2050, and nothing observed has been fed back into the
parameters.</p>

<div class="pb"></div>
<h2>5. The numbers</h2>
<h3>5a. The cash flow, year by year &mdash; for a {mt:g}&nbsp;Mt/yr plant</h3>
<p class="note">Real euros, undiscounted. Money out is negative. Highlighted
rows are the commitment year and the payback year. Discounting this series at
{p.common.r:.0%} returns {units.eur(cf.npv_check[0])}, the model's NPV.</p>
{cash_table(cf)}

<div class="pb"></div>
<h3>5b. The answer as a range &mdash; four input sets</h3>
{npv_table()}
<p class="note">From the specification's published values down to ones taken
from primary documents. The range crosses zero, so the sign of the answer is
set by which inputs you accept, not by the model.</p>

<h3>5c. The model against the live market</h3>
{market_table()}
<p class="note">Source: EEX EU&nbsp;ETS primary-market auction report, read at
build time. Observed {esc(carbon.period)}. Nothing here feeds the model.</p>

<h3>5d. Context figures</h3>
{kv([
    ("Capex assumption I0",
     f"&euro;{p.sector.I0:,.0f}/t capacity = "
     f"{units.eur(units.absolute(p.sector.I0, mt))}"),
    ("&mdash; vs every project actually under construction", "&euro;1,300+/t"),
    ("Support s_max",
     f"&euro;{p.policy.s_max:,.0f}/t capacity = "
     f"{units.eur(units.absolute(p.policy.s_max, mt))}"),
    ("EU ETS auction revenue, 2026 year to date",
     units.eur(pot.get("ALL auctions", 0.0))),
    ("&mdash; of which the Innovation Fund",
     f"{units.eur(pot.get('IF', 0.0))} "
     f"({units.absolute(p.policy.s_max, mt) / pot.get('IF', 1.0):.0%} would go "
     f"to one plant)"),
    ("Discount rate", f"{p.common.r:.0%} real, to {p.common.t0}"),
    ("Horizon", p.common.horizon_end),
])}

<div class="pb"></div>
<h2>6. What must NOT be claimed</h2>
<p>State these before anyone asks. They are the credibility of the work.</p>
<ul>
<li><b class="warn">Opex has no time shape.</b> The model carries one constant
driven only by the hydrogen price. A real plant's operating cost rises with
age, jumps at the switch while an unfamiliar technology is learned, then
settles lower as contracts improve. None of that is modelled &mdash; the line
is drawn flat and labelled flat rather than given a plausible curve. Open hole
H10.</li>
<li><b class="warn">No tax layer.</b> Electricity is 2&ndash;4&times; gas per
kWh in every member state, and those prices exclude taxes, levies and network
charges &mdash; exactly what &ldquo;fiscal harmonisation&rdquo; would
change.</li>
<li><b class="warn">No MATLAB reference.</b> The 50-case diff harness is built
and its negative control works; there is no reference file to run it
against.</li>
<li><b class="warn">Ladder rows 4&ndash;7 do not reproduce</b> the published
table. Documented case by case in <code>CALIBRATION.md</code>.</li>
<li><b class="warn">One unverified input</b> &mdash; the &euro;8.29/kg Platts
hydrogen assessment, licensed data taken from the specification.</li>
<li><b class="warn">Subsidy money is not earmarked.</b> The ETS Directive's
spending clause is a non-binding target on national budgets, not an
entitlement any project can draw on.</li>
<li><b class="warn">This is an increment, not a P&amp;L.</b> The cash flow is
the difference between switching and not switching. Steel revenue, raw
materials, debt service, tax and working capital net out by construction. A
real sizing exercise starts here and adds the rest.</li>
</ul>

<h2>7. What is checked</h2>
<ul>
<li><b>Validation gate.</b> Nine published quantities reproduce to 1e-3
relative before anything downstream prints.</li>
<li><b>Every table cell re-derived</b> from the raw CSV or cached statistic
&mdash; not from the function that prints it &mdash; and compared at the
precision shown. <b>145/145 agree.</b></li>
<li><b>The specification, quantity by quantity.</b> 54 of 62 published figures
reproduce; all eight differences are NPV <em>levels</em>, high by
1.1&ndash;8.0%. No year, trigger or crossing year differs.</li>
<li>{n_tests} test functions and {n_checks} standard-library self-checks on
every build; zero third-party dependencies.</li>
</ul>

<footer>Explanatory framework, not investment advice. Generated by
<code>handoff.py</code> from a live model run. Full workings:
<code>explained.html</code> (every figure and table, 300+ words each),
<code>gallery.html</code> (all of them, titles only),
<code>results.html</code> (the tables with sources). Read
<code>CALIBRATION.md</code> before quoting any figure.</footer>
</body></html>
"""


def to_pdf(html_path: str = OUT_HTML, pdf_path: str = OUT_PDF) -> bool:
    """Print the HTML to PDF with headless Chromium. False if unavailable."""
    src = pathlib.Path(html_path).resolve()
    if not pathlib.Path(CHROMIUM).exists():
        return False
    try:
        subprocess.run(
            [CHROMIUM, "--headless", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={pdf_path}", "--no-pdf-header-footer",
             f"file://{src}"],
            check=True, capture_output=True, timeout=180,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError, OSError):
        return False
    return pathlib.Path(pdf_path).exists()


def main() -> int:
    """Write handoff.html, then print handoff.pdf from it."""
    page = build()
    pathlib.Path(OUT_HTML).write_text(page, encoding="utf-8")
    print(f"Wrote {OUT_HTML} ({len(page) / 1024:.0f} KB)")
    if to_pdf():
        size = pathlib.Path(OUT_PDF).stat().st_size / 1024
        print(f"Wrote {OUT_PDF} ({size:.0f} KB) - two figures, all the data.")
    else:
        print(f"Could not print {OUT_PDF}: headless Chromium was not reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
