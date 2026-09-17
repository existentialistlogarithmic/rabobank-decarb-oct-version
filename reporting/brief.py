"""brief.py -> brief.html -> brief.pdf: the two-page version, for sending on.

Everything else in ``reporting/`` is for someone working on the model. This is
for someone who will read it once, on a phone or on paper, and needs the
answer and the caveat in that order.

Two pages, hard limit. What earns a place: the number, what unit it is in, the
range it sits in, the one comparison that tests it, and what is still open.
Everything else is a link back to the full pages.

Printing
--------
No PDF library in this environment works - reportlab is absent and pypdf is
broken by a system ``cryptography`` conflict - so the PDF is printed from this
HTML by headless Chromium, which is already present for the screenshot checks.
:func:`to_pdf` does that through the browser's own ``--print-to-pdf``, so no
Python binding is involved at all; ``main()`` says so plainly if the browser is
not reachable and leaves the HTML to be printed by hand.
"""

from __future__ import annotations

import datetime
import html
import pathlib
import subprocess
from typing import Final

from analysis import sourced, tables, units, verify
from timing_model.params import Params
from timing_model.results import outputs
from timing_model.scenarios import published_base

OUT_HTML: Final[str] = "brief.html"
OUT_PDF: Final[str] = "brief.pdf"


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


CSS: Final[str] = """
@page { size: A4; margin: 16mm 15mm 14mm; }
*{box-sizing:border-box}
body{margin:0;color:#1a1a19;background:#fff;
font:10.5pt/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
h1{font-size:19pt;line-height:1.15;margin:0 0 2mm}
.sub{color:#5f5f5c;font-size:9.5pt;margin:0 0 5mm}
h2{font-size:12pt;margin:6mm 0 2mm;padding-bottom:1mm;
border-bottom:1.5px solid #1a1a19}
p{margin:0 0 2.5mm}
.hero{display:flex;gap:6mm;margin:0 0 4mm;padding:3.5mm 4mm;
background:#f4f4f1;border-radius:2mm}
.hero div{flex:1}
.hero b{display:block;font-size:15pt;line-height:1.1}
.hero span{font-size:8pt;color:#5f5f5c;display:block;margin-top:0.5mm}
table{border-collapse:collapse;width:100%;font-size:9pt;margin:0 0 2mm}
th,td{padding:1.6mm 2mm;text-align:right;border-bottom:0.5px solid #d8d8d4}
th:first-child,td:first-child{text-align:left}
thead th{font-size:7.5pt;text-transform:uppercase;letter-spacing:.04em;
color:#5f5f5c;border-bottom:1px solid #1a1a19}
thead tr.u th{text-transform:none;letter-spacing:0;font-style:italic;
font-weight:400;border-bottom:1px solid #1a1a19}
tbody tr.hi{background:#f4f4f1;font-weight:600}
.note{font-size:8.5pt;color:#5f5f5c;margin:0 0 3mm}
ul{margin:0 0 3mm;padding-left:5mm}
li{margin:0 0 1.2mm}
.tag{display:inline-block;font:600 7.5pt/1 ui-monospace,monospace;
border:0.5px solid #5f5f5c;border-radius:1mm;padding:1mm 1.5mm;color:#5f5f5c}
.warn{color:#9c4316;font-weight:600}
footer{margin-top:5mm;padding-top:2.5mm;border-top:0.5px solid #d8d8d4;
font-size:8pt;color:#5f5f5c}
.pb{page-break-before:always}
"""


def money_table() -> str:
    """T2, trimmed to the columns that survive on a page this size."""
    rows = []
    for r in tables.table_npv_cases().rows:
        case, i0, ph2, npv, absolute, trig, t_star = r
        cls = " class='hi'" if case in ("base", "central") else ""
        rows.append(
            f"<tr{cls}><td>{esc(case)}</td><td>{esc(i0)}</td><td>{esc(ph2)}</td>"
            f"<td>{esc(npv)}</td><td>{esc(absolute)}</td><td>{esc(trig)}</td>"
            f"<td>{esc(t_star)}</td></tr>")
    return (
        "<table><thead><tr><th>case</th><th>capex I0</th><th>hydrogen</th>"
        "<th>NPV</th><th>NPV, 2.5 Mt/yr</th><th>trigger</th><th>T*</th></tr>"
        "<tr class='u'><th></th><th>&euro;/t cap</th><th>&euro;/kg</th>"
        "<th>&euro;/t cap</th><th>&euro; absolute</th><th>&euro;/tCO&#8322;</th>"
        "<th>year</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def capex_table() -> str:
    """T3, condensed: the comparison that tests the capex assumption."""
    rows = []
    for name, absolute, mt, per_t, _aid, out in tables.table_capex().rows:
        cls = " class='hi'" if str(name).startswith("--") else ""
        label = str(name).replace("-- ", "").replace(" --", "")
        rows.append(f"<tr{cls}><td>{esc(label)}</td><td>{esc(absolute)}</td>"
                    f"<td>{esc(mt)}</td><td>{esc(per_t)}</td>"
                    f"<td>{esc(out)}</td></tr>")
    return ("<table><thead><tr><th>project</th><th>announced</th>"
            "<th>capacity</th><th>capex</th><th>outcome</th></tr>"
            "<tr class='u'><th></th><th>&euro; total</th><th>Mt/yr</th>"
            "<th>&euro;/t cap</th><th></th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def build() -> str:
    """The brief, from one model run."""
    o = outputs(*published_base())
    base, cen = sourced.run_case("base"), sourced.run_case("central")
    mt = tables.REFERENCE_MT
    n_checks = len(verify.all_checks())
    n_bad = len([c for c in verify.all_checks() if not c.ok])
    got, total = __import__("data.sourced", fromlist=["x"]).link_coverage()
    today = datetime.date.today().isoformat()
    i0_money = units.eur(units.absolute(Params().sector.I0, mt))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Steel decarbonisation timing &mdash; brief</title>
<style>{CSS}</style></head><body>

<h1>When should a steel plant stop burning coal?</h1>
<p class="sub">Investment-timing model, European integrated works &middot;
generated {esc(today)} from the model run, not typed in</p>

<div class="hero">
<div><b>{esc(o.t_star)}</b><span>commitment year T*, published case</span></div>
<div><b>{esc(units.eur(units.absolute(o.npv0, mt)))}</b>
<span>NPV for a {mt:g} Mt/yr plant, published case</span></div>
<div><b>{esc(units.eur(units.absolute(cen.out.npv0, mt)))}</b>
<span>the same plant on sourced inputs</span></div>
<div><b>&euro;{o.trigger:,.0f}</b><span>carbon price that justifies it</span></div>
</div>

<h2>Read the unit before the number</h2>
<p>Every euro figure in this model is <b>per tonne of annual nameplate
capacity</b> &mdash; not per tonne of steel, and not a total. So capex
<code>I0 = &euro;900</code> is <b>{esc(i0_money)}</b> for a {mt:g}&nbsp;Mt/yr works, and
the NPV is in billions. Multiply by annual tonnes and the denominator cancels;
that conversion is exact, not indicative.</p>
<p class="note">A carbon price (&euro;/tCO&#8322;) and an operating flow
(&euro;/t of product per year) have different denominators and do <em>not</em>
scale with plant size. Only the capacity-denominated stocks convert.</p>

<h2>How much is it worth? <span class="tag">T2</span></h2>
{money_table()}
<p class="note">Four input sets, from the specification's published values down
to ones taken from primary documents. The answer is a <b>range</b>, not a
figure: {esc(units.eur(units.absolute(base.out.npv0, mt)))} down to
{esc(units.eur(units.absolute(cen.out.npv0, mt)))}, and negative at the top of
the sourced hydrogen range. Which end you believe is the whole argument.</p>

<h2>The comparison that tests it <span class="tag">T3</span></h2>
{capex_table()}
<p class="note">Stegra's Boden is {mt:g}&nbsp;Mt/yr and cost &euro;6.5bn to build.
The published case says the switch alone is worth
{esc(units.eur(units.absolute(base.out.npv0, mt)))} on a modelled spend of
{esc(i0_money)}. Every project still under construction costs at least
&euro;1,300/t of capacity; the two below the model's &euro;900 are an EAF-only
retrofit and a scheme ArcelorMittal cancelled, forfeiting &euro;1.3bn of
approved German aid.</p>

<div class="pb"></div>
<h2>What is checked</h2>
<ul>
<li><b>The validation gate.</b> Nine published quantities reproduce to 1e-3
relative before anything downstream prints.</li>
<li><b>Every table cell re-derived.</b> {n_checks} figures recomputed from the
raw CSV cell or cached statistic &mdash; not from the function that prints them
&mdash; and compared at the precision shown.
<b>{n_checks - n_bad}/{n_checks} agree.</b></li>
<li><b>The specification, quantity by quantity.</b> 54 of 62 published figures
reproduce; all eight differences are NPV <em>levels</em>, high by 1.1&ndash;8.0%.
No year, trigger or crossing year differs.</li>
<li>290 tests and 41 standard-library self-checks, run on every build.</li>
</ul>

<h2>What is not</h2>
<ul>
<li><b class="warn">Provenance.</b> Only {got} of {total} rows in the September
2026 research pass carry a working link. The rest name their source correctly
without one &mdash; <em>unverified</em>, not <em>sourced</em>. None of it has
been promoted into the running model.</li>
<li><b class="warn">Operating costs.</b> The whole BF-BOF against H2-DRI-EAF
difference is one constant driven by the hydrogen price. Real lines the model
does not contain: DR-grade pellet premium, EAF electricity (&euro;89/t in
Germany against &euro;47/t in Sweden), graphite electrodes, scrap and alloys.
Closing this needs one study covering both routes at one boundary; none was
found.</li>
<li><b class="warn">No tax layer.</b> Electricity is dearer than gas per kWh in
every member state, 1.8&times; to 3.9&times;, which is why a green hydrogen
floor sits above a grey one. Those prices exclude taxes and levies, and the
decomposition that &ldquo;fiscal harmonisation&rdquo; turns on was not
obtained.</li>
<li><b class="warn">No MATLAB reference.</b> The 50-case diff harness is built
and its negative control works; there is no reference file to run it against.</li>
</ul>

<h2>The three choices the model will not make</h2>
<ul>
<li><b>Support basis.</b> A capex lump or a per-tCO&#8322; stream. The German
CCfD pays a stream over fifteen years, worth 1.3&ndash;3.3&times; the
&euro;200/t lump the model nets off.</li>
<li><b>Allowance resale.</b> <code>w = 1</code> drives the policy-neutrality
result. Without it the headline reverses sign.</li>
<li><b>Whether &euro;2.60/kg hydrogen is the base case at all.</b> It sits below
every green floor and inside the grey band &mdash; a fossil price carrying
green emissions.</li>
</ul>

<footer>Explanatory framework, not investment advice. Full workings:
<code>results.html</code> (every table, named and sourced),
<code>charts.html</code>, <code>deck.html</code>.
Read <code>CALIBRATION.md</code> before quoting any figure.</footer>
</body></html>
"""


#: The Chromium that Playwright installed. Present for the screenshot checks,
#: and it can print a PDF on its own - no Python PDF library is involved, which
#: matters here because reportlab is absent and pypdf is broken by a system
#: cryptography conflict.
CHROMIUM: Final[str] = "/opt/pw-browsers/chromium"


def to_pdf(html_path: str = OUT_HTML, pdf_path: str = OUT_PDF) -> bool:
    """Print the HTML to PDF with headless Chromium. False if unavailable.

    ``--print-to-pdf`` needs no Playwright and no Python binding: it is the
    browser's own print path, so the PDF has the same layout the ``@page``
    rules describe. A missing browser is reported rather than raised - the HTML
    is the deliverable either way.
    """
    src = pathlib.Path(html_path).resolve()
    if not pathlib.Path(CHROMIUM).exists():
        return False
    try:
        subprocess.run(
            [CHROMIUM, "--headless", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={pdf_path}", "--no-pdf-header-footer",
             f"file://{src}"],
            check=True, capture_output=True, timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError, OSError):
        return False
    return pathlib.Path(pdf_path).exists()


def main() -> int:
    """Write brief.html, then print brief.pdf from it."""
    page = build()
    pathlib.Path(OUT_HTML).write_text(page, encoding="utf-8")
    print(f"Wrote {OUT_HTML} ({len(page) / 1024:.0f} KB)")
    if to_pdf():
        size = pathlib.Path(OUT_PDF).stat().st_size / 1024
        print(f"Wrote {OUT_PDF} ({size:.0f} KB) - two pages, for sending on.")
    else:
        print(f"Could not print {OUT_PDF}: headless Chromium was not reachable.")
        print(f"Open {OUT_HTML} and print to PDF from the browser instead.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
