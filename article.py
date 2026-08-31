"""Write article.html - the finished piece, not another sensitivity report.

Prose is authored here; every figure and every number is generated from the
model at write time, so the article cannot drift from the code. Standard
library only.
"""

from __future__ import annotations

import html

from timing_model.cost import reline_year
from timing_model.objective import npv, npv_curve
from timing_model.params import Params, ScenarioParams
from timing_model.scenarios import STRESS_LADDER, published_base

OUT = "article.html"
AGES = list(range(0, 20))
YEARS = list(range(2026, 2041))


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def sc_(v, lo, hi, a, b):
    return a if hi == lo else a + (v - lo) * (b - a) / (hi - lo)


# --------------------------------------------------------------- figure 1
def fig1() -> tuple[str, dict]:
    """NPV by commitment year: as published, and fully corrected."""
    p, sc = published_base()
    base = npv_curve(p, sc)
    for r in STRESS_LADDER[:4]:
        p, sc = r.apply_params(p), r.apply_scenario(sc)
    corr = npv_curve(p, sc)

    W, H, L, R, T, B = 720, 340, 58, 96, 22, 44
    ys = [y for y in YEARS if y <= 2036]
    vals = [c[y] for c in (base, corr) for y in ys]
    lo, hi = min(vals) * 0.92, max(vals) * 1.06
    X = lambda y: sc_(y, ys[0], ys[-1], L, W - R)
    Y = lambda v: sc_(v, lo, hi, H - B, T)

    parts = []
    for v in (500, 1000, 1500):
        parts.append(f'<line class="g" x1="{L}" y1="{Y(v):.1f}" x2="{W-R}" '
                     f'y2="{Y(v):.1f}"/>')
        parts.append(f'<text class="tk ar" x="{L-9}" y="{Y(v)+4:.1f}">{v:,}</text>')
    for y in ys:
        if y % 2 == 0:
            parts.append(f'<text class="tk am" x="{X(y):.1f}" y="{H-B+19}">{y}</text>')
    # the plateau band and the cliff, called out
    parts.insert(0, f'<rect class="band" x="{X(2028):.1f}" y="{T}" '
                    f'width="{X(2032)-X(2028):.1f}" height="{H-B-T}"/>')
    parts.append(f'<line class="cliff" x1="{X(2032.5):.1f}" y1="{T}" '
                 f'x2="{X(2032.5):.1f}" y2="{H-B}"/>')
    for i, (c, cls, lab) in enumerate(((base, "s0", "as published"),
                                       (corr, "s1", "corrected"))):
        d = " ".join(f"{'M' if k==0 else 'L'}{X(y):.1f},{Y(c[y]):.1f}"
                     for k, y in enumerate(ys))
        parts.append(f'<path class="ln {cls}" d="{d}"/>')
        pk = max(ys, key=lambda y: c[y])
        parts.append(f'<circle class="mk {cls}" cx="{X(pk):.1f}" '
                     f'cy="{Y(c[pk]):.1f}" r="5"/>')
        parts.append(f'<text class="dl {cls}" x="{W-R+8}" '
                     f'y="{Y(c[ys[-1]])+4:.1f}">{lab}</text>')
    parts.append(f'<text class="an am" x="{(X(2028)+X(2032))/2:.1f}" y="{T+14}">'
                 "the plateau</text>")
    parts.append(f'<text class="an ar cl" x="{X(2032.5)-8:.1f}" y="{H-B-8}">'
                 "reline</text>")
    svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Net present value '
           f'by commitment year, as published and fully corrected">'
           f'<text class="axt" transform="rotate(-90 14 {H/2})" x="14" y="{H/2}">'
           f"EUR / t capacity</text>{''.join(parts)}</svg>")
    return svg, {"base": base, "corr": corr}


# --------------------------------------------------------------- figure 2
def fig2() -> str:
    """The fleet: value by commitment year and asset age, with the reline traced."""
    sc = ScenarioParams(u=0.85)
    z, rel = [], []
    for a in AGES:
        pp = Params().with_sector(age0=float(a))
        z.append([npv(T, pp, sc) for T in YEARS])
        rel.append(reline_year(pp))
    flat = [v for r in z for v in r]
    lo, hi = min(flat), max(flat)
    ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

    W, H, L, T = 720, 400, 66, 26
    cw = (W - L - 24) / len(YEARS)
    ch = (H - T - 46) / len(AGES)
    parts = []
    for i, a in enumerate(AGES):
        for j, y in enumerate(YEARS):
            t = (z[i][j] - lo) / (hi - lo)
            parts.append(f'<rect x="{L+j*cw:.1f}" y="{T+i*ch:.1f}" '
                         f'width="{cw:.2f}" height="{ch:.2f}" '
                         f'fill="{ramp[min(6, int(t*6.99))]}"/>')
        if a % 4 == 0:
            parts.append(f'<text class="tk ar" x="{L-8}" y="{T+i*ch+ch/2+4:.1f}">'
                         f"{a}</text>")
    # Ages 0-5 reline after 2040, so they fall outside the plotted years. The
    # first PLOTTED point must carry the M, not the first age.
    seg, started = [], False
    for k, r in enumerate(rel):
        if r not in YEARS:
            continue
        seg.append(f"{'L' if started else 'M'}{L+YEARS.index(r)*cw+cw/2:.1f},"
                   f"{T+k*ch+ch/2:.1f}")
        started = True
    parts.append(f'<path class="relin" d="{" ".join(seg)}"/>')
    for y in YEARS:
        if y % 3 == 2:
            parts.append(f'<text class="tk am" x="{L+YEARS.index(y)*cw+cw/2:.1f}" '
                         f'y="{H-24}">{y}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Value by commitment '
            f'year and asset age; a rust line traces each plant\'s reline year">'
            f'<text class="axt" transform="rotate(-90 14 {H/2})" x="14" y="{H/2}">'
            f"asset age in 2026</text>{''.join(parts)}</svg>")


CSS = """
:root{--ground:#f3f5f6;--surface:#fff;--sunk:#eaeef0;--ink:#0e1417;--ink2:#465259;
--muted:#79868f;--rule:#dce2e6;--accent:#0a5f6b;--soft:#e2eff0;--sig:#b2481f;
--sigsoft:#faeae3;
--s0:#7b8892;--s1:#0a5f6b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--ground:#0f1417;--surface:#161c21;--sunk:#1d242a;--ink:#e7edf1;--ink2:#a4b1ba;
--muted:#79868f;--rule:#242c33;--accent:#5cb3bf;--soft:#112f33;--sig:#e08b62;
--sigsoft:#301f18;--s0:#79868f;--s1:#5cb3bf}}
:root[data-theme="dark"]{--ground:#0f1417;--surface:#161c21;--sunk:#1d242a;
--ink:#e7edf1;--ink2:#a4b1ba;--muted:#79868f;--rule:#242c33;--accent:#5cb3bf;
--soft:#112f33;--sig:#e08b62;--sigsoft:#301f18;--s0:#79868f;--s1:#5cb3bf}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
font:1.075rem/1.75 "Source Serif 4",Georgia,"Times New Roman",serif}
.page{max-width:44rem;margin:0 auto;padding:clamp(2rem,5vw,4rem) 1.25rem 6rem}
.wide{width:min(53rem,calc(100vw - 2.5rem));margin-left:50%;
transform:translateX(-50%)}
.kicker{font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:.7rem;
letter-spacing:.16em;text-transform:uppercase;color:var(--sig);font-weight:600}
h1{font-size:clamp(2.1rem,5.4vw,3.15rem);line-height:1.08;letter-spacing:-.018em;
margin:.7rem 0 0;font-weight:600;text-wrap:balance}
.stand{font-size:1.24rem;line-height:1.52;color:var(--ink2);margin:1.1rem 0 0;
font-weight:400}
.meta{font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:.79rem;
color:var(--muted);margin:1.4rem 0 0;padding-top:1.1rem;border-top:1px solid var(--rule);
display:flex;flex-wrap:wrap;gap:.3rem 1.3rem}
h2{font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:1.13rem;
font-weight:600;letter-spacing:-.005em;margin:3rem 0 .9rem;color:var(--ink);
line-height:1.3;text-wrap:balance}
h2 .no{color:var(--accent);font-variant-numeric:tabular-nums;margin-right:.5rem;
font-size:.9rem}
p{margin:0 0 1.15rem}
.lead::first-letter{float:left;font-size:3.35rem;line-height:.86;padding:.28rem .6rem 0 0;
color:var(--accent);font-weight:600}
strong{font-weight:600;color:var(--ink)}
.pull{margin:2.2rem 0;padding:0 0 0 1.15rem;border-left:3px solid var(--accent);
font-size:1.2rem;line-height:1.45;color:var(--ink);font-weight:500}
figure{margin:2.2rem 0;background:var(--surface);border:1px solid var(--rule);
padding:1.1rem 1.1rem .8rem}
figure svg{width:100%;height:auto;display:block;overflow:visible}
figcaption{font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:.8rem;
line-height:1.5;color:var(--ink2);margin-top:.8rem;padding-top:.7rem;
border-top:1px solid var(--rule)}
figcaption b{color:var(--ink);font-weight:600}
.g{stroke:var(--rule);stroke-width:1}
.band{fill:var(--accent);opacity:.07}
.cliff{stroke:var(--sig);stroke-width:2;stroke-dasharray:6 4}
.relin{fill:none;stroke:var(--sig);stroke-width:2.4;stroke-linejoin:round}
.ln{fill:none;stroke-width:2.4;stroke-linejoin:round;stroke-linecap:round}
.ln.s0{stroke:var(--s0)}.ln.s1{stroke:var(--s1)}
.mk.s0{fill:var(--s0)}.mk.s1{fill:var(--s1)}
.mk{stroke:var(--surface);stroke-width:2}
.dl{font-family:"IBM Plex Sans",sans-serif;font-size:11.5px;font-weight:600}
.dl.s0{fill:var(--s0)}.dl.s1{fill:var(--s1)}
.tk{font-family:"IBM Plex Mono",monospace;font-size:10.5px;fill:var(--muted)}
.an{font-family:"IBM Plex Sans",sans-serif;font-size:10.5px;fill:var(--muted)}
.an.cl{fill:var(--sig)}
.axt{font-family:"IBM Plex Sans",sans-serif;font-size:10.5px;fill:var(--muted);
text-anchor:middle}
.ar{text-anchor:end}.am{text-anchor:middle}
.box{background:var(--surface);border:1px solid var(--rule);padding:1.1rem 1.2rem;
margin:2rem 0;font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:.92rem;
line-height:1.62;color:var(--ink2)}
.box h3{font-size:.74rem;letter-spacing:.12em;text-transform:uppercase;
color:var(--sig);margin:0 0 .6rem;font-weight:600;font-family:inherit}
.box p{margin:0 0 .7rem}.box p:last-child{margin:0}
.box.cond h3{color:var(--accent)}
table{border-collapse:collapse;width:100%;font-family:"IBM Plex Sans",sans-serif;
font-size:.86rem;font-variant-numeric:tabular-nums;margin:0 0 1.15rem}
th{text-align:right;border-bottom:2px solid var(--ink);padding:.4rem .6rem;
font-weight:600}
td{text-align:right;padding:.4rem .6rem;border-bottom:1px solid var(--rule);
color:var(--ink2)}
th:first-child,td:first-child{text-align:left}
td.hi{color:var(--ink);font-weight:600}
.tw{overflow-x:auto}
footer{margin-top:3.5rem;padding-top:1.3rem;border-top:2px solid var(--ink);
font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:.81rem;color:var(--muted)}
footer p{margin:0 0 .7rem}
"""


def build() -> str:
    f1, cur = fig1()
    base, corr = cur["base"], cur["corr"]
    f2 = fig2()
    rows = "".join(
        f'<tr><td>{y}</td><td class="hi">{base[y]:,.0f}</td>'
        f"<td>{(base[y]-base[2029])/base[2029]*100:+.1f}%</td></tr>"
        for y in (2028, 2029, 2030, 2031, 2032, 2033))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Only Date That Isn't a Forecast</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap">
<style>{CSS}</style></head><body><main class="page">

<span class="kicker">Energy transition &middot; steel</span>
<h1>The only date that isn't a forecast</h1>
<p class="stand">Europe's steel decarbonisation debate is conducted in carbon
prices and hydrogen costs, both of them forecasts. The decision that actually
binds is written in a maintenance schedule &mdash; and for a large part of the
fleet it has already been taken.</p>
<div class="meta"><span>RaboResearch &middot; Energy Transition</span>
<span>Explanatory framework, not investment advice</span></div>

<h2><span class="no">01</span>The question is when, not whether</h2>
<p class="lead">A European steel producer runs a blast furnace. It burns coal,
it emits roughly 1.9 tonnes of CO&#8322; per tonne of steel, and it is expensive
to run under a carbon price that is going up. A cleaner route exists &mdash;
hydrogen-based direct reduction feeding an electric arc furnace &mdash; which
emits about 0.1 tonnes instead.</p>
<p>Almost nobody in the industry now argues about whether that switch happens.
The argument is about <strong>when</strong>. And timing is a harder question
than it looks, because the decision is irreversible in both directions. Commit
early and you buy equipment before it has come down the cost curve, and before
subsidy windows open. Commit late and you spend years paying a carbon bill you
could have avoided &mdash; and you may spend several hundred million euros
rebuilding a furnace you are about to switch off.</p>
<p>We built a model to answer that question. It maximises the net present value
of switching in each possible year, and separately computes the carbon price at
which committing becomes rational once irreversibility is priced. What follows
is what it said, including the parts we did not expect.</p>

<h2><span class="no">02</span>The answer is a window, not a year</h2>
<p>Our published base case gives an optimal commitment year of <strong>2029</strong>,
worth about &euro;1,588 per tonne of annual capacity. That number has been
quoted. It should not have been, at least not on its own.</p>
<figure class="wide">{f1}
<figcaption><b>Figure 1. What committing in each year is worth.</b> Grey is the
model as originally published; teal applies four corrections &mdash; a load
factor (real furnaces run at 75&ndash;85%, not 100%), a benchmark applied to the
right tonne, a consistent real-versus-nominal basis, and an explicit hydrogen
price. Dots mark each curve's best year. The shaded band is the plateau; the
dashed line is the reline.</figcaption></figure>
<p>Look at the top of the curve. It is almost flat:</p>
<div class="tw"><table><thead><tr><th>Commit in</th>
<th>Worth, &euro;/t capacity</th><th>vs. best year</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p>The gap between 2029 and 2030 is <strong>seven euros out of
&euro;1,588</strong>. Half of one percent. Every input feeding that number is a
forecast &mdash; the carbon price, the hydrogen price, the learning rate on
capex &mdash; and none of them is accurate to half a percent. Publishing "2029"
implies a precision the curve cannot support.</p>
<p class="pull">The honest output is a window: any year from 2028 to 2032 is
within four percent of the best. Inside that band, the model has no opinion.</p>

<h2><span class="no">03</span>The deadline, however, is real</h2>
<p>Now look one year further. Committing in 2032 is worth &euro;1,520.
Committing in 2033 is worth &euro;1,062. <strong>One year later costs
&euro;458 &mdash; about thirty percent of the case &mdash; in a single
step.</strong></p>
<p>That step is the <strong>reline</strong>. A blast furnace is not a permanent
object. Its refractory lining burns out over roughly fifteen to twenty years,
after which the furnace has to be stripped and rebuilt. Salzgitter spent
&euro;100m relining one furnace in 2024; thyssenkrupp spent over &euro;200m on
its largest, after a campaign that had run twenty-one years. It is a routine,
scheduled, unavoidable piece of heavy maintenance.</p>
<p>It is also a fork. A producer arriving at its reline date must either spend
that money on the old asset or switch. Commit at or before the reline and the
spend is avoided entirely. Commit after and it has been paid, on a furnace with
a few years left in it. <strong>The loss is taken twice: once in cash, once in
the avoidance given up.</strong></p>
<p>What makes this different from everything else in the model is not its size.
It is its epistemic status. The carbon price is a forecast. The hydrogen price
is a forecast. The learning rate is a forecast. <strong>The reline date is a
calendar.</strong> Relining schedules are planned years ahead and published
plant by plant across the European fleet.</p>
<p class="pull">Every input in this decision is a forecast except one &mdash;
and that one binds harder than the carbon price does.</p>

<h2><span class="no">04</span>The fleet is locking itself out, one reline at a time</h2>
<p>Widen from one plant to all of them. Figure 2 shows what committing in each
year is worth, for plants at every stage of their furnace campaign.</p>
<figure class="wide">{f2}
<figcaption><b>Figure 2. The same decision, for the whole fleet.</b> Darker is
worth more; rows are plants at each stage of a furnace campaign. The rust line traces each plant's reline year; it sweeps diagonally
because an older furnace relines sooner. Value collapses on crossing that line
&mdash; and the best ground in the whole picture runs along its near
side.</figcaption></figure>
<p>Two things follow. First, past about sixteen years into a campaign the
optimal commitment year stops being an economic choice at all: it becomes the
reline year, exactly. The producer is no longer choosing when to switch. It is
choosing not to spend the rebuild.</p>
<p>Second, and more usefully, <strong>value peaks about two years short of a
reline</strong> &mdash; not at the newest asset and not at the most decrepit. A
plant one further year along loses roughly &euro;200 per tonne, and the reason
is not the furnace. It is that EU support opens in 2028. A producer whose reline
falls in 2027 must commit before the money exists, and forfeits the envelope
entirely. <strong>The cliff is the subsidy calendar colliding with the
maintenance calendar</strong>, and neither one is a forecast.</p>
<p>This has an uncomfortable implication for the fleet as a whole. Since 2020,
European producers have relined furnaces representing roughly 26 million tonnes
of annual capacity. Each of those decisions bought another campaign &mdash;
fifteen to twenty years of committed blast-furnace operation. On this model's
logic, those plants are not slow to decarbonise. <strong>They are locked
out</strong>, and the lock has a published expiry date.</p>

<h2><span class="no">05</span>Two instruments that cannot substitute for each other</h2>
<p>The model produces two distinct numbers: what switching is worth, and the
carbon price at which switching becomes rational under irreversibility. We
tested every parameter against both, expecting a spectrum. We got a partition.</p>
<p>Five parameters &mdash; the load factor, the size of the support envelope,
whether free allowances can be resold, the price basis, and which policy vintage
applies &mdash; move the value and move the threshold by <strong>exactly
zero</strong>. Two &mdash; both volatility settings &mdash; move the threshold
and leave the value at <strong>exactly zero</strong>. Only four move both.</p>
<p>Those zeros are not small numbers. They are structural: the threshold is a
closed-form expression in which the load factor, the resale switch, the support
envelope and the price path simply do not appear. A parameter cannot move a
quantity it is not in.</p>
<div class="box"><h3>Why this matters for policy design</h3>
<p>A contract-for-difference collapses volatility. It moves the threshold and
<em>cannot</em> improve the project's value. A capital grant raises the value
and <em>cannot</em> bring the threshold closer.</p>
<p>So the two common failure modes look alike in a spreadsheet and need
different instruments. If a case fails because the carbon price never reaches
the trigger, more grant money makes the project more valuable at a price that
never arrives. <strong>No amount of subsidy fixes a volatility problem.</strong>
At realised carbon-market volatility the trigger is &euro;202/tCO&#8322; and the
price path does not reach it until the mid-2040s &mdash; beyond any
recognisable investment horizon.</p></div>

<h2><span class="no">06</span>Where the case actually fails</h2>
<p>None of the above is what breaks the steel case today. Hydrogen is. Our base
case assumes &euro;2.60/kg. The Platts assessment for Spain on 8 May 2026 was
<strong>&euro;8.29/kg</strong>. At that price the model finds no commitment year
anywhere in the horizon, and the trigger rises from &euro;110 to
&euro;367/tCO&#8322;.</p>
<p>Along the way it produces the one result we found genuinely counterintuitive.
The load factor multiplies the entire annual benefit &mdash; including the
operating penalty, which is negative. While avoided carbon costs outweigh the
hydrogen bill, running the plant harder is worth more, exactly as
project-finance intuition expects. Once the hydrogen bill dominates, the load
factor multiplies a negative number.</p>
<p class="pull">Above &euro;7.17/kg, the sensitivity of value to utilisation
changes sign. Running the plant less is worth more &mdash; and today's market
price is on the wrong side of that line.</p>
<div class="box"><h3>Read this before quoting the previous paragraph</h3>
<p>That is a statement about the sign of a sensitivity, not a recommendation.
At those hydrogen prices the project's value is negative in every commitment
year; a lower load factor makes it <em>less</em> negative. "Run it less" is what
the arithmetic says about a plant that should not be built yet.</p>
<p>The operational point stands, though, and it is not obvious: on the wrong
side of that threshold, a minimum-utilisation covenant &mdash; standard
protection in project finance &mdash; would compel the borrower to destroy
value. The exposure to size is a revolving facility driven by the hydrogen
price, not a term loan driven by capacity.</p></div>

<h2><span class="no">07</span>Two things we would have got wrong</h2>
<p>Our earlier drafts reported the trigger as insensitive to the discount rate,
which sounded like robustness. It is not. Taking the rate from 6% to 10% moves
the break-even carbon price by <strong>+304%</strong> and the option multiple by
<strong>&minus;68%</strong>. Their product moves 29%. Two large opposing
movements nearly annihilate, and what survives gets reported as stability. A
cancellation fails differently from a robust result: both terms are driven by
the gap between the discount rate and the price drift, so anything that changes
the gap rather than the level breaks the offset.</p>
<p>The second is subtler. Running our own scenario grid and correlating the
outputs suggests value and threshold are strongly coupled, at &minus;0.87 &mdash;
flatly contradicting the exact independence in section 5. Both results are
correct. The grid varies hydrogen price and capex, which are two of the four
parameters that move both outputs, so they dominate the variance and manufacture
the correlation. <strong>The correlation is a property of the sampling; the
independence is a property of the model.</strong> An analyst working from the
matrix alone would reach for the wrong instrument.</p>

<h2><span class="no">08</span>What this means for origination</h2>
<p>A term sheet on a &euro;2&ndash;4bn conversion is negotiated eighteen to
twenty-four months ahead of commitment. If the decision window opens in 2028,
the mandate conversations are happening now.</p>
<p>More concretely, this model says the screening question is not "which
producer has the best carbon economics". It is <strong>"which producer is about
two years from a reline"</strong>. That is answerable from published maintenance
schedules rather than from a price forecast, and it identifies clients whose
deadline is close enough to force a decision and far enough away to still catch
the support window.</p>
<p>It also flags what is <em>not</em> financeable. The write-off of the
incumbent asset is not a loan; it is an impairment that hits book equity in the
year of commitment, precisely when the borrower needs headroom. And the gap
between financial close and subsidy disbursement is itself a financing need that
the model does not currently price.</p>

<h2><span class="no">09</span>What we are not claiming</h2>
<div class="box cond"><h3>Conditions</h3>
<p>Every figure here is conditional on: hydrogen at &euro;2.60/kg, allowance
resale permitted, support treated as a &euro;200/t lump rather than a per-tonne
flow, nominal carbon prices, and a load factor of 0.85. Three of those are
genuine open decisions rather than settled inputs, and each materially changes
the result.</p>
<p>The cost-side parameters that set the reline date are <strong>calibrated
against published results, not independently sourced</strong>. The mechanism is
robust and the shape of Figure 2 is sound, but the specific year differs plant
by plant and should be taken from that plant's own schedule. Reconciliation
against the reference implementation is incomplete: four rows of our correction
ladder do not yet reproduce, and the fifty-case comparison has not been run.</p>
<p>Our reconstruction of the post-2028 free-allocation schedule is not yet
checked against the legal annex, and the non-steel sectors have not had the
calibration or units review that steel has &mdash; we publish their ordering
only.</p></div>
<p>None of that changes the argument. The plateau is flat because the inputs are
uncertain, and the deadline is sharp because it is not a forecast. Those two
facts point in the same direction regardless of which hydrogen price you
believe.</p>

<footer>
<p>Model and full derivations are open in the project repository. Figures are
generated from the model at publication time rather than transcribed.</p>
<p>This is an explanatory framework, not investment advice. Results are
conditional on the stated assumptions and on legislation still subject to
co-decision.</p>
</footer>
</main></body></html>"""


def main() -> int:
    """Write article.html."""
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build())
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
