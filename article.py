"""Write article.html - the finished piece, not another sensitivity report.

Prose is authored here; every figure and every number is generated from the
model at write time, so the article cannot drift from the code. Standard
library only.
"""

from __future__ import annotations

import html

import eurostat
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


# ------------------------------------------------- observed hydrogen floor
CORRECTED = Params().with_policy(kappa=0.94)


def country_cases() -> tuple[list[tuple[str, float, int | None, float]], float]:
    """For each member state: power-only H2 floor, and whether a case exists.

    Returns rows of (geo, floor EUR/kg, T* or None, best NPV) plus the
    hydrogen price at which a commitment year first appears.
    """
    obs = eurostat.refresh(offline=True)
    rows = []
    for k, v in obs.items():
        if not k.startswith("power_"):
            continue
        fl = eurostat.hydrogen_power_floor(v.value)
        sc = ScenarioParams(u=0.85, p_H2=fl, price_basis="real")
        c = npv_curve(CORRECTED, sc)
        T = max(c, key=c.get)
        rows.append((k[-2:], fl, T if c[T] > 0 else None, c[T]))
    rows.sort(key=lambda r: r[1])
    lo, hi = 1.0, 9.0
    for _ in range(50):
        m = (lo + hi) / 2
        sc = ScenarioParams(u=0.85, p_H2=m, price_basis="real")
        cc = npv_curve(CORRECTED, sc)
        if max(cc.values()) > 0:
            lo = m
        else:
            hi = m
    return rows, (lo + hi) / 2


def fig_floor(rows, breakeven: float) -> str:
    """Power-only hydrogen floor by country, against the break-even price."""
    W, H, L, T, B = 720, 340, 74, 26, 46
    hi = max(max(r[1] for r in rows), breakeven) * 1.16
    X = lambda v: sc_(v, 0, hi, L, W - 150)
    step = (H - T - B) / len(rows)
    bh = min(19.0, step * 0.66)
    parts = []
    refs = ((2.60, "assumed 2.60", "asum"),
            (breakeven, f"break-even {breakeven:.2f}", "be"))
    for v, lab, cls in refs:                      # behind the bars and labels
        parts.append(f'<line class="rule {cls}" x1="{X(v):.1f}" y1="{T}" '
                     f'x2="{X(v):.1f}" y2="{H-B}"/>')
        parts.append(f'<text class="an am {cls}" x="{X(v):.1f}" y="{H-B+17}">{lab}</text>')
    for i, (g, fl, ts, _) in enumerate(rows):
        cy = T + step * (i + 0.5)
        ok = fl < breakeven
        parts.append(f'<rect class="bar {"ok" if ok else "no"}" x="{L}" '
                     f'y="{cy-bh/2:.1f}" width="{X(fl)-L:.1f}" height="{bh:.1f}"/>')
        parts.append(f'<text class="tk ar" x="{L-9}" y="{cy+4:.1f}">{g}</text>')
        parts.append(f'<text class="val" x="{X(fl)+8:.1f}" y="{cy+4:.1f}">'
                     f'{fl:.2f}  {"case exists" if ok else "no case"}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Power-only hydrogen '
            f'cost floor by country against the break-even price">'
            f"{''.join(parts)}</svg>")

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
.bar{stroke:var(--surface);stroke-width:2}
.bar.ok{fill:var(--accent)}.bar.no{fill:var(--s0)}
.rule{stroke-width:2}.rule.be{stroke:var(--sig);stroke-dasharray:6 4}
.rule.asum{stroke:var(--ink2);stroke-dasharray:2 4}
.an.be{fill:var(--sig)}.an.asum{fill:var(--ink2)}
.val{font-family:"IBM Plex Sans",sans-serif;font-size:11px;fill:var(--ink2);
font-variant-numeric:tabular-nums}
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
    rows, be = country_cases()
    live = [r for r in rows if r[2] is not None]
    dead = [r for r in rows if r[2] is None]
    cheapest = rows[0]
    hicp = eurostat.refresh(offline=True)["hicp"]
    f0 = fig_floor(rows, be)
    f1, cur = fig1()
    base = cur["base"]
    f2 = fig2()
    ctab = "".join(
        f'<tr><td>{g}</td><td>{fl:,.2f}</td>'
        f'<td class="{"hi" if ts else ""}">{ts if ts else "none"}</td>'
        f"<td>{v:,.0f}</td></tr>" for g, fl, ts, v in rows)
    names = {"SE": "Sweden", "FR": "France", "ES": "Spain", "PL": "Poland",
             "BE": "Belgium", "NL": "the Netherlands", "DE": "Germany",
             "AT": "Austria", "IT": "Italy"}
    livenames = " and ".join(names[g] for g, *_ in live)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Below the Electricity Bill</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap">
<style>{CSS}</style></head><body><main class="page">

<span class="kicker">Energy transition &middot; steel</span>
<h1>Below the electricity bill</h1>
<p class="stand">Europe's green steel case rests on a hydrogen price of
&euro;2.60 a kilo. Official electricity statistics say that is less than the
power it takes to make it &mdash; in every steel-producing country in the
Union. What survives is not a sector case. It is a map of two countries and a
maintenance schedule.</p>
<div class="meta"><span>RaboResearch &middot; Energy Transition</span>
<span>Explanatory framework, not investment advice</span></div>

<h2><span class="no">01</span>The question is when, not whether</h2>
<p class="lead">A European steel producer runs a blast furnace. It emits roughly
1.9 tonnes of CO&#8322; per tonne of steel. A cleaner route exists &mdash;
hydrogen-based direct reduction feeding an electric arc furnace &mdash; at about
0.1 tonnes instead. Almost nobody argues about whether that switch happens. The
argument is about <strong>when</strong>, and it is a hard question because the
decision cannot be undone in either direction.</p>
<p>We built a model to answer it: maximise the value of switching in each
possible year, and separately compute the carbon price at which committing
becomes rational once irreversibility is priced. Then we went looking for the
assumption most likely to be load-bearing. It was not the carbon price.</p>

<h2><span class="no">02</span>A number that does not survive the electricity bill</h2>
<p>Making hydrogen by electrolysis is, in cost terms, mostly a way of buying
electricity. Hydrogen carries about 33 kWh of energy per kilo, and a real
system delivers it at roughly 60% efficiency &mdash; so <strong>about 55 kWh of
electricity per kilo of hydrogen</strong>. That number is not a forecast. It is
thermodynamics and a plant efficiency.</p>
<p>Eurostat publishes what large industrial users actually pay for electricity,
excluding taxes and levies. Multiply the two.</p>
<figure class="wide">{f0}
<figcaption><b>Figure 1. The hydrogen price floor, from official electricity
prices.</b> Electricity cost alone at 55 kWh/kg, for a large industrial user
(band IE, 20&ndash;70 GWh a year, excluding taxes), latest Eurostat half-year.
Teal bars clear the break-even hydrogen price of
&euro;{be:.2f}/kg; grey bars do not. The dotted line is the
&euro;2.60/kg the base case assumes.</figcaption></figure>
<p>The cheapest electricity in European steel, in {names[cheapest[0]]}, implies a
floor of <strong>&euro;{cheapest[1]:.2f} per kilo</strong>. That is
{cheapest[1]/2.60:.1f} times the assumed price. And this is a floor in the
strict sense: it excludes the electrolyser, its stack replacements,
compression, storage and every metre of pipe between the electrolyser and the
furnace. Delivered hydrogen is strictly more expensive than this, everywhere.</p>
<p class="pull">The base case assumes a hydrogen price below the cost of the
electricity needed to make it &mdash; in all nine countries. That is not a
forecast disagreement. It is an arithmetic floor from official statistics.</p>
<p>It also settles an argument we had been having internally. A commercial
assessment put Spanish hydrogen at &euro;8.29/kg in May 2026, which we had been
treating as a pessimistic stress case against a &euro;2.60 base. The electricity
data says the assessment is in the right region and <strong>the base case is
the outlier</strong>.</p>

<h2><span class="no">03</span>What is left is a geography, not a sector</h2>
<p>Put each country's floor back through the model &mdash; corrected for load
factor, for the hot-metal benchmark, and for a consistent real price basis. A
commitment year first appears at a hydrogen price of
<strong>&euro;{be:.2f}/kg</strong>. Above that, there is no year in the horizon
in which switching is worth more than not switching.</p>
<div class="tw"><table><thead><tr><th>Country</th>
<th>Power-only floor, &euro;/kg</th><th>Commitment year</th>
<th>Value, &euro;/t capacity</th></tr></thead><tbody>{ctab}</tbody></table></div>
<p><strong>{livenames} clear the bar. Nobody else does.</strong> Spain misses it
by {abs(dead[0][1]-be):.2f} of a euro &mdash; well inside the error of any
number on this page, so read it as a coin toss rather than a verdict. The rest
of the fleet is not marginal; it is a long way underwater, and the gap is
electricity prices rather than anything to do with steel.</p>
<p>Two cautions, both of which cut against the survivors. These floors ignore
every hydrogen cost except the power, so {names[live[0][0]]} and
{names[live[1][0]]} clear the bar only on the assumption that hydrogen costs
nothing beyond its electricity. And the two countries that qualify are the two
with the most hydro and nuclear on their systems &mdash; which is a statement
about their grids, not about their steelmakers.</p>

<h2><span class="no">04</span>Even where the case exists, a maintenance date sets it</h2>
<p>Look at the commitment years in that table. Where a case survives at all, it
is <strong>2032</strong> &mdash; and 2032 is not an economic optimum. It is the
year our reference plant must reline.</p>
<p>A blast furnace is not a permanent object. Its refractory lining burns out
over fifteen to twenty years, after which the furnace is stripped and rebuilt.
Salzgitter spent &euro;100m on one in 2024; thyssenkrupp spent over &euro;200m
on its largest, after a campaign of twenty-one years. It is routine, scheduled,
unavoidable heavy maintenance &mdash; and it is a fork. Arrive at it and you
either spend the money on the old asset or you switch.</p>
<figure class="wide">{f1}
<figcaption><b>Figure 2. What committing in each year is worth.</b> Grey is the
model as first published; teal applies the corrections. The shaded band is the
plateau &mdash; every year in it sits within four percent of the best, so the
model has no real opinion inside it. The dashed line is the reline, and one
year past it costs &euro;{base[2032]-base[2033]:,.0f} per tonne in a single
step.</figcaption></figure>
<p>Notice the asymmetry. The top of the curve is nearly flat: committing in
2029 is worth &euro;{base[2029]:,.0f} and committing in 2030 is worth
&euro;{base[2030]:,.0f} &mdash; seven euros apart on fifteen hundred. Every
input feeding those numbers is a forecast, and none is accurate to half a
percent. But one year past the reline costs thirty percent.</p>
<p class="pull">The peak is soft because the inputs are uncertain. The deadline
is sharp because it is not a forecast at all &mdash; it is a calendar.</p>
<p>That is the one input in this model that can be checked rather than
projected. Relining schedules are planned years ahead and published plant by
plant across the European fleet.</p>

<h2><span class="no">05</span>The fleet is locking itself out</h2>
<figure class="wide">{f2}
<figcaption><b>Figure 3. The same decision, for every plant.</b> Darker is worth
more; rows are plants at each stage of a furnace campaign. The rust line traces
each plant's reline year &mdash; it sweeps diagonally because an older furnace
relines sooner. Value collapses on crossing it, and the best ground runs along
its near side.</figcaption></figure>
<p>Past about sixteen years into a campaign, the optimal year stops being a
choice at all: it becomes the reline year exactly. The producer is not choosing
when to switch. It is choosing not to spend the rebuild.</p>
<p>Value peaks about two years short of a reline &mdash; not at the newest asset
and not at the most decrepit. A plant one year further along loses roughly
&euro;200 a tonne, and the reason is not the furnace. EU support opens in 2028,
so a producer whose reline falls in 2027 must commit before the money exists.
<strong>The cliff is the subsidy calendar colliding with the maintenance
calendar</strong>, and neither is a forecast.</p>
<p>Since 2020, European producers have relined furnaces representing roughly 26
million tonnes of annual capacity. Each of those decisions bought another
campaign. On this model's logic those plants are not slow to decarbonise
&mdash; <strong>they are locked out, and the lock has a published expiry
date.</strong></p>

<h2><span class="no">06</span>Which instrument actually moves this</h2>
<p>The model produces two distinct numbers: what switching is worth, and the
carbon price at which it becomes rational under irreversibility. We tested every
parameter against both, expecting a spectrum. We got a partition.</p>
<p>Five parameters &mdash; load factor, support envelope, allowance resale,
price basis, policy vintage &mdash; move the value and move the threshold by
<strong>exactly zero</strong>. Two, both volatility settings, move the threshold
and leave the value at <strong>exactly zero</strong>. Only four move both. Those
zeros are structural, not small: the threshold is a closed-form expression that
does not contain the load factor, the resale switch, the support envelope or the
price path.</p>
<div class="box"><h3>Why this matters for instrument design</h3>
<p>A contract-for-difference collapses volatility. It moves the threshold and
<em>cannot</em> improve the project's value. A capital grant raises the value and
<em>cannot</em> bring the threshold closer. The two common failure modes look
alike in a spreadsheet and need different instruments.</p>
<p>Neither of them, though, is the binding constraint here. A hydrogen cost floor
is not a threshold problem or a value problem &mdash; it is an input price.
<strong>No carbon contract and no capital grant moves an electricity price.</strong>
The instrument that would is one aimed at industrial power costs, which is a
different policy conversation from the one the sector is currently having.</p></div>

<h2><span class="no">07</span>Two things we would have got wrong</h2>
<p>Our earlier drafts reported the trigger as insensitive to the discount rate,
which sounded like robustness. Taking the rate from 6% to 10% moves the
break-even carbon price <strong>+304%</strong> and the option multiple
<strong>&minus;68%</strong>; their product moves 29%. Two large opposing
movements nearly annihilate, and the residue gets reported as stability. A
cancellation fails differently from a robust result: both terms run off the gap
between the discount rate and the price drift, so anything that changes the gap
rather than the level breaks it.</p>
<p>The second is subtler. Correlating outputs across our own scenario grid
suggests value and threshold are coupled at &minus;0.87, contradicting the exact
independence above. Both are correct. The grid varies hydrogen price and capex,
two of the four parameters that move both outputs, so they dominate the variance
and manufacture the correlation. <strong>The correlation is a property of the
sampling; the independence is a property of the model.</strong></p>

<h2><span class="no">08</span>What this means for origination</h2>
<p>A term sheet on a &euro;2&ndash;4bn conversion is negotiated eighteen to
twenty-four months ahead of commitment. That makes the screening question
narrower than the sector conversation suggests, and answerable from published
data rather than forecasts. It has two filters, in this order:</p>
<p><strong>First, electricity.</strong> On today's industrial power prices the
arithmetic only works where power is cheapest. That is a shorter list than
"European steel", and it is checkable each half-year as Eurostat updates.</p>
<p><strong>Second, the reline calendar.</strong> Within that list, the client
worth a conversation is the one roughly two years short of a rebuild &mdash;
close enough that the deadline forces a decision, far enough that the support
window is still open.</p>
<p>It also flags what is not financeable. The write-off of the incumbent asset is
not a loan; it is an impairment landing on book equity in the year of
commitment, exactly when the borrower needs headroom.</p>

<h2><span class="no">09</span>What we are not claiming</h2>
<div class="box cond"><h3>Conditions</h3>
<p>The electricity floors are power-only and therefore optimistic by
construction; they are a lower bound on hydrogen cost, not an estimate of it.
They use band IE industrial prices excluding taxes, which suits a large steel
plant but is not a contracted price &mdash; a producer with a long-term PPA may
do better, and one exposed to spot may do worse. Euro-area inflation is
{hicp.value:.1f}% ({hicp.period}, Eurostat), consistent with the 2% deflator the
model uses.</p>
<p>Model results remain conditional on allowance resale being permitted, support
treated as a lump rather than a per-tonne flow, and a load factor of 0.85. The
cost-side parameters that set the reline date are <strong>calibrated against
published results, not independently sourced</strong>: the mechanism is robust
and Figure 3's shape is sound, but the specific year must come from each plant's
own schedule. Reconciliation against the reference implementation is incomplete
&mdash; four rows of our correction ladder do not yet reproduce and the
fifty-case comparison has not been run. Our reconstruction of the post-2028
free-allocation schedule is not yet checked against the legal annex, and
non-steel sectors have not had the calibration this one has, so we publish their
ordering only.</p></div>
<p>None of that touches the central point. A hydrogen price below the cost of
the electricity that makes it is not a modelling assumption that needs
sensitivity analysis. It is an assumption that needs replacing &mdash; and when
you replace it, the European steel case stops being a question about carbon
prices and becomes a question about power prices and maintenance schedules.</p>

<footer>
<p>Electricity and inflation data from Eurostat, retrieved via its public API and
cached with the model. Figures are generated from the model at publication time
rather than transcribed. Model and derivations are open in the project
repository.</p>
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
