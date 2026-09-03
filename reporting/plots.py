"""Charts for the timing model - standard library only, no matplotlib.

Writes a single self-contained ``charts.html``: theme-aware, hover tooltips,
legends, direct labels and a table view under every chart. Open it in a browser,
or in PyCharm right-click the file and Open in Browser.

Four charts, each carrying one finding:

1. NPV(T) - the decision itself, and how each correction moves the peak.
2. The price path against the trigger - the option premium expressed in time.
3. The cumulative stress ladder - how far the case falls, correction by correction.
4. The volatility ladder - why a CfD moves the client between regimes.

Palette: the reference categorical slots, validated for colour-vision
deficiency in both light and dark mode. Light mode puts slots 3 and 4 below
3:1 against the surface, so every series is also direct-labelled and every
chart carries a table view - identity is never colour alone.
"""

from __future__ import annotations

import html
import json
from collections.abc import Iterable, Sequence

from analysis.findings import (
    _d_npv_du,
    all_findings,
    lever_classes,
    output_correlations,
    rate_cancellation,
    reline_capture,
    utilisation_inversion,
)
from timing_model.benefit import carbon_price_path
from timing_model.objective import npv_curve
from timing_model.params import Params, ScenarioParams
from timing_model.scenarios import STRESS_LADDER, published_base, run_ladder, sigma_ladder

OUT = "charts.html"

W, H = 760, 380
PAD_L, PAD_R, PAD_T, PAD_B = 62, 118, 26, 46

#: Categorical slots 1-4, fixed order. Never cycled, never reassigned by rank.
SERIES_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SERIES_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500"]

#: Compact end-labels. The legend carries the full name; these only need to
#: tell the four lines apart at the right edge without running off the card.
SHORT = ["as published", "+ u=0.85", "+ kappa=0.94", "+ real"]


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def scale(v: float, lo: float, hi: float, a: float, b: float) -> float:
    """Map v from data range [lo,hi] onto pixel range [a,b]."""
    if hi == lo:
        return (a + b) / 2.0
    return a + (v - lo) * (b - a) / (hi - lo)


def nice_ticks(lo: float, hi: float, target: int = 6) -> list[float]:
    """Human-readable tick values spanning [lo, hi]."""
    if hi <= lo:
        return [lo]
    raw = (hi - lo) / target
    mag = 10.0 ** (len(str(int(abs(raw)))) - 1 if abs(raw) >= 1 else -1)
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=raw)
    start = step * (int(lo / step) - 1)
    out, v = [], start
    while v <= hi + step:
        if lo - step * 0.001 <= v <= hi + step * 0.001:
            out.append(round(v, 6))
        v += step
    return out or [lo, hi]


def declutter(
    labels: Sequence[tuple[float, int, str]], gap: float = 14.0
) -> list[tuple[float, int, str]]:
    """Push overlapping end-labels apart vertically, preserving their order.

    Direct labels are the relief for the light-mode contrast WARN, so they have
    to stay readable; two of these series sit within a few EUR of each other at
    the right edge and would otherwise overprint.
    """
    out = sorted(labels, key=lambda r: r[0])
    for k in range(1, len(out)):
        if out[k][0] - out[k - 1][0] < gap:
            out[k] = (out[k - 1][0] + gap, out[k][1], out[k][2])
    return out


def axes(
    xt: Sequence[tuple[float, str]], yt: Sequence[tuple[float, str]], y0: float
) -> str:
    """Recessive solid hairline grid, muted labels, one baseline."""
    p = []
    for py, lab in yt:
        p.append(f'<line class="grid" x1="{PAD_L}" y1="{py:.1f}" '
                 f'x2="{W - PAD_R}" y2="{py:.1f}"/>')
        p.append(f'<text class="tick ar" x="{PAD_L - 10}" y="{py + 4:.1f}">{esc(lab)}</text>')
    for px, lab in xt:
        p.append(f'<text class="tick am" x="{px:.1f}" y="{H - PAD_B + 20}">{esc(lab)}</text>')
    p.append(f'<line class="axis" x1="{PAD_L}" y1="{y0:.1f}" '
             f'x2="{W - PAD_R}" y2="{y0:.1f}"/>')
    return "".join(p)


def legend(names: Sequence[str], slots: Sequence[int]) -> str:
    """Always present for >= 2 series. Swatch carries colour, text stays ink."""
    if len(names) < 2:
        return ""
    items = "".join(
        f'<span class="lg"><i class="sw s{s}"></i>{esc(n)}</span>'
        for n, s in zip(names, slots, strict=False)
    )
    return f'<div class="legend">{items}</div>'


def table(headers: Sequence[str], rows: Iterable[Sequence[object]], cap: str) -> str:
    """The table view. Required relief wherever a series is sub-3:1 on light."""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows
    )
    return (f'<details class="tv"><summary>{esc(cap)}</summary>'
            f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
            f"</details>")


# ----------------------------------------------------------------- chart 1
def chart_npv() -> str:
    """NPV(T) for the first four ladder rungs. Line: change over a continuum."""
    p, sc = published_base()
    states: list[tuple[str, Params, ScenarioParams]] = []
    for rung in STRESS_LADDER[:4]:
        p = rung.apply_params(p)
        sc = rung.apply_scenario(sc)
        states.append((rung.label, p, sc))

    curves = [(lab, npv_curve(pp, ss)) for lab, pp, ss in states]
    years = [t for t in sorted(curves[0][1]) if 2026 <= t <= 2040]
    vals = [c[t] for _, c in curves for t in years]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.08
    lo, hi = lo - pad, hi + pad

    def X(t: int) -> float:
        return scale(t, years[0], years[-1], PAD_L, W - PAD_R)

    def Y(v: float) -> float:
        return scale(v, lo, hi, H - PAD_B, PAD_T)

    yt = [(Y(v), f"{v:,.0f}") for v in nice_ticks(lo, hi)]
    xt = [(X(t), str(t)) for t in years if t % 2 == 0]
    parts = [axes(xt, yt, Y(max(lo, min(hi, 0.0))))]

    ends: list[tuple[float, int, str]] = []
    for i, (lab, c) in enumerate(curves):
        d = " ".join(f"{'M' if k == 0 else 'L'}{X(t):.1f},{Y(c[t]):.1f}"
                     for k, t in enumerate(years))
        parts.append(f'<path class="ln s{i}" d="{d}"/>')
        best = max(years, key=lambda t: c[t])
        parts.append(f'<circle class="mk s{i}" cx="{X(best):.1f}" '
                     f'cy="{Y(c[best]):.1f}" r="5"/>')
        ends.append((Y(c[years[-1]]), i, SHORT[i]))
    for y, i, lab in declutter(ends):
        parts.append(f'<text class="dl s{i}" x="{W - PAD_R + 8}" '
                     f'y="{y + 4:.1f}">{esc(lab)}</text>')

    pts = [{"x": round(X(t), 1), "t": t,
            "v": [round(c[t], 1) for _, c in curves]} for t in years]
    return (
        '<figure class="card">'
        "<figcaption><h3>NPV by commitment year</h3>"
        "<p>Peak = T*. Markers show each argmax; the step at 2032 is the reline, "
        "where avoided reinvestment flips to paid.</p></figcaption>"
        + legend([lab for lab, _ in curves], range(4))
        + f'<svg viewBox="0 0 {W} {H}" role="img" class="plot" '
          f'data-pts="{esc(json.dumps(pts))}">'
          f'<text class="axt" transform="rotate(-90 16 {H / 2})" x="16" y="{H / 2}">'
          "EUR / t capacity</text>" + "".join(parts) +
        '<g class="hov" hidden><line class="cross"/></g></svg>'
        + table(["Year"] + [lab for lab, _ in curves],
                ([t] + [f"{c[t]:,.0f}" for _, c in curves] for t in years),
                "Table view - NPV by year")
        + "</figure>"
    )


# ----------------------------------------------------------------- chart 2
def chart_trigger() -> str:
    """Price path against the trigger. One series, so no legend: the title names it."""
    p, sc = published_base()
    path = carbon_price_path(p, sc)
    _, base = run_ladder()[0]
    years = [t for t in sorted(path) if t <= 2040]
    hi = max(max(path[t] for t in years), base.trigger) * 1.10

    def X(t: int) -> float:
        return scale(t, years[0], years[-1], PAD_L, W - PAD_R)

    def Y(v: float) -> float:
        return scale(v, 0.0, hi, H - PAD_B, PAD_T)

    yt = [(Y(v), f"{v:,.0f}") for v in nice_ticks(0, hi)]
    xt = [(X(t), str(t)) for t in years if t % 2 == 0]
    d = " ".join(f"{'M' if k == 0 else 'L'}{X(t):.1f},{Y(path[t]):.1f}"
                 for k, t in enumerate(years))

    parts = [axes(xt, yt, Y(0.0)),
             f'<path class="ln s0" d="{d}"/>',
             f'<line class="thr" x1="{PAD_L}" y1="{Y(base.trigger):.1f}" '
             f'x2="{W - PAD_R}" y2="{Y(base.trigger):.1f}"/>',
             f'<text class="dl s1" x="{W - PAD_R + 8}" y="{Y(base.trigger) + 4:.1f}">'
             f'trigger {base.trigger:,.1f}</text>']
    if base.crossing_year:
        cx, cy = X(base.crossing_year), Y(path[base.crossing_year])
        parts.append(f'<circle class="mk s0" cx="{cx:.1f}" cy="{cy:.1f}" r="6"/>')
        parts.append(f'<text class="note am" x="{cx:.1f}" y="{cy - 14:.1f}">'
                     f"crossed {base.crossing_year}</text>")
    if base.t_star:
        tx = X(base.t_star)
        parts.append(f'<line class="mark" x1="{tx:.1f}" y1="{PAD_T}" '
                     f'x2="{tx:.1f}" y2="{H - PAD_B}"/>')
        parts.append(f'<text class="note am" x="{tx:.1f}" y="{PAD_T - 8}">'
                     f"T* {base.t_star}</text>")

    pts = [{"x": round(X(t), 1), "t": t, "v": [round(path[t], 1)]} for t in years]
    gap = (base.crossing_year or 0) - (base.t_star or 0)
    return (
        '<figure class="card">'
        "<figcaption><h3>Carbon price path against the commitment trigger</h3>"
        f"<p>T* and the crossing year differ by {gap} year(s). That gap is the "
        "option premium expressed in time, not an inconsistency.</p></figcaption>"
        f'<svg viewBox="0 0 {W} {H}" role="img" class="plot" '
        f'data-pts="{esc(json.dumps(pts))}" data-names="EUA price">'
        f'<text class="axt" transform="rotate(-90 16 {H / 2})" x="16" y="{H / 2}">'
        "EUR / tCO2</text>" + "".join(parts) +
        '<g class="hov" hidden><line class="cross"/></g></svg>'
        + table(["Year", "EUA price", "Trigger"],
                ([t, f"{path[t]:,.1f}", f"{base.trigger:,.1f}"] for t in years),
                "Table view - price path")
        + "</figure>"
    )


# ----------------------------------------------------------------- chart 3
def chart_ladder() -> str:
    """Cumulative stress ladder. One series, so one colour on every bar."""
    rows = [(r.label, o) for r, o in run_ladder()]
    vals = [o.npv0 for _, o in rows]
    lo, hi = min(min(vals), 0.0), max(vals)
    span = hi - lo
    lo, hi = lo - span * 0.06, hi + span * 0.10
    left, right = 224, W - 30
    top, bot = PAD_T + 6, H - 24
    step = (bot - top) / len(rows)
    bh = min(22.0, step * 0.62)

    def X(v: float) -> float:
        return scale(v, lo, hi, left, right)

    zero = X(0.0)
    parts = [f'<line class="axis" x1="{zero:.1f}" y1="{top}" '
             f'x2="{zero:.1f}" y2="{bot:.1f}"/>']
    for i, (lab, o) in enumerate(rows):
        cy = top + step * (i + 0.5)
        x = X(o.npv0)
        x0, x1 = (zero, x) if o.npv0 >= 0 else (x, zero)
        parts.append(f'<rect class="br s0" x="{x0:.1f}" y="{cy - bh / 2:.1f}" '
                     f'width="{max(abs(x1 - x0), 1.5):.1f}" height="{bh:.1f}" rx="4"/>')
        parts.append(f'<text class="cat ar" x="{left - 14}" y="{cy + 4:.1f}">'
                     f"{esc(lab)}</text>")
        star = str(o.t_star) if o.t_star else "beyond"
        # Place the value outside the bar end, but never let a short negative
        # bar push its label back into the category gutter.
        if o.npv0 >= 0 or (zero - x) < 70:
            lx, anc = (max(x, zero) + 8), "al"
        else:
            lx, anc = x - 8, "ar"
        parts.append(f'<text class="val {anc}" x="{lx:.1f}" y="{cy + 4:.1f}">'
                     f"{o.npv0:,.0f}  ({star})</text>")
    return (
        '<figure class="card">'
        "<figcaption><h3>Cumulative stress ladder</h3>"
        "<p>Each row adds one correction to the row above. Value is NPV0 in EUR/t "
        "capacity; T* in brackets. Four of the five push the same way, which is why "
        "the ladder compounds rather than averaging out.</p></figcaption>"
        f'<svg viewBox="0 0 {W} {H}" role="img" class="plot">' + "".join(parts) +
        "</svg>"
        + table(["Scenario", "T*", "NPV0 (EUR/t)", "Trigger (EUR/tCO2)", "Crossing"],
                ([lab, o.t_star or "beyond", f"{o.npv0:,.2f}", f"{o.trigger:,.2f}",
                  o.crossing_year or "beyond"] for lab, o in rows),
                "Table view - ladder")
        + "</figure>"
    )


# ----------------------------------------------------------------- chart 4
def chart_sigma() -> str:
    """Trigger by volatility regime. Ordered categories, single series."""
    rows = sigma_ladder()
    hi = max(o.trigger for _, o in rows) * 1.18
    left, right = 150, W - 40
    top, bot = PAD_T + 6, H - 30
    step = (bot - top) / len(rows)
    bh = min(26.0, step * 0.58)

    def X(v: float) -> float:
        return scale(v, 0.0, hi, left, right)

    parts = [f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{bot:.1f}"/>']
    for i, (name, o) in enumerate(rows):
        cy = top + step * (i + 0.5)
        parts.append(f'<rect class="br s0" x="{left:.1f}" y="{cy - bh / 2:.1f}" '
                     f'width="{max(X(o.trigger) - left, 1.5):.1f}" '
                     f'height="{bh:.1f}" rx="4"/>')
        parts.append(f'<text class="cat ar" x="{left - 14}" y="{cy + 4:.1f}">'
                     f"{esc(name.replace('_', ' '))}</text>")
        cross = o.crossing_year or "beyond horizon"
        parts.append(f'<text class="val al" x="{X(o.trigger) + 8:.1f}" '
                     f'y="{cy + 4:.1f}">{o.trigger:,.1f}   crosses {esc(cross)}</text>')
    return (
        '<figure class="card">'
        "<figcaption><h3>Trigger by volatility regime</h3>"
        "<p>A CfD does not adjust the case at the margin - it moves the client "
        "between regimes. Bar is the trigger; the label gives the year the path "
        "reaches it.</p></figcaption>"
        f'<svg viewBox="0 0 {W} {H}" role="img" class="plot">' + "".join(parts) +
        "</svg>"
        + table(["Regime", "Trigger (EUR/tCO2)", "Crossing year"],
                ([n.replace("_", " "), f"{o.trigger:,.2f}",
                  o.crossing_year or "beyond horizon"] for n, o in rows),
                "Table view - volatility")
        + "</figure>"
    )


CSS = """
:root{--surface:#fcfcfb;--plane:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;
--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,.10);
--s0:#2a78d6;--s1:#eb6834;--s2:#1baf7a;--s3:#eda100;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--surface:#1a1a19;--plane:#0d0d0d;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;
--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);
--s0:#3987e5;--s1:#d95926;--s2:#199e70;--s3:#c98500;}}
:root[data-theme="dark"]{--surface:#1a1a19;--plane:#0d0d0d;--ink:#fff;
--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;
--ring:rgba(255,255,255,.10);
--s0:#3987e5;--s1:#d95926;--s2:#199e70;--s3:#c98500;}
*{box-sizing:border-box}
body{margin:0;padding:28px 20px 60px;background:var(--plane);color:var(--ink);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;}
.wrap{max-width:860px;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 4px}
.sub{color:var(--ink2);margin:0 0 6px}
.cond{color:var(--ink2);font-size:.83rem;background:var(--surface);
border:1px solid var(--ring);border-radius:10px;padding:10px 13px;margin:14px 0 26px}
.cond b{color:var(--ink);font-weight:600}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:14px;
padding:18px 18px 14px;margin:0 0 22px}
figcaption h3{margin:0 0 3px;font-size:1.02rem}
figcaption p{margin:0 0 10px;color:var(--ink2);font-size:.86rem;max-width:66ch}
.plot{width:100%;height:auto;display:block;overflow:visible}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin:2px 0 8px;font-size:.82rem;
color:var(--ink2)}
.lg{display:inline-flex;align-items:center;gap:6px}
.sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.grid{stroke:var(--grid);stroke-width:1}
.axis{stroke:var(--axis);stroke-width:1}
.mark{stroke:var(--axis);stroke-width:1}
.thr{stroke:var(--s1);stroke-width:2;stroke-dasharray:7 5}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.mk{stroke:var(--surface);stroke-width:2}
.br{stroke:var(--surface);stroke-width:2}
.tick{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.cat{fill:var(--ink2);font-size:12px}
.val{fill:var(--ink2);font-size:11.5px;font-variant-numeric:tabular-nums}
.note{fill:var(--ink2);font-size:11px}
.axt{fill:var(--muted);font-size:11px;text-anchor:middle}
.dl{font-size:11.5px;font-weight:600}
.ar{text-anchor:end}.am{text-anchor:middle}.al{text-anchor:start}
.s0{color:var(--s0)}.s1{color:var(--s1)}.s2{color:var(--s2)}.s3{color:var(--s3)}
path.s0,line.s0{stroke:var(--s0)}path.s1,line.s1{stroke:var(--s1)}
path.s2,line.s2{stroke:var(--s2)}path.s3,line.s3{stroke:var(--s3)}
circle.s0,rect.s0{fill:var(--s0)}circle.s1,rect.s1{fill:var(--s1)}
circle.s2,rect.s2{fill:var(--s2)}circle.s3,rect.s3{fill:var(--s3)}
text.s0{fill:var(--s0)}text.s1{fill:var(--s1)}text.s2{fill:var(--s2)}
text.s3{fill:var(--s3)}
i.s0{background:var(--s0)}i.s1{background:var(--s1)}i.s2{background:var(--s2)}
i.s3{background:var(--s3)}
.cross{stroke:var(--axis);stroke-width:1}
.tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--ink);
border:1px solid var(--ring);border-radius:8px;padding:7px 10px;font-size:12px;
box-shadow:0 4px 14px rgba(0,0,0,.14);opacity:0;transition:opacity .08s;z-index:9}
.tip b{font-variant-numeric:tabular-nums}
.tv{margin-top:8px;font-size:.83rem;color:var(--ink2)}
.tv summary{cursor:pointer;color:var(--ink2)}
.tv table{border-collapse:collapse;margin-top:8px;width:100%}
.tv th,.tv td{text-align:right;padding:3px 8px;border-bottom:1px solid var(--grid);
font-variant-numeric:tabular-nums}
.tv th:first-child,.tv td:first-child{text-align:left}
.tvw{overflow-x:auto}
footer{color:var(--muted);font-size:.8rem;margin-top:8px}
.band{fill:var(--s1);opacity:.07}
.cell{stroke:var(--surface);stroke-width:2}
.cell.pos{fill:var(--s0)}.cell.neg{fill:#e34948}.cell.mid{fill:var(--axis)}
.cellv{fill:var(--ink);font-size:12px;font-variant-numeric:tabular-nums;
paint-order:stroke;stroke:var(--surface);stroke-width:3px}
.scale{display:flex;align-items:center;gap:6px;font-size:.78rem;color:var(--ink2);
margin:2px 0 10px}
.scale i{width:26px;height:11px;border-radius:3px;display:inline-block}
.scale i.neg{background:#e34948}.scale i.mid{background:var(--axis)}
.scale i.pos{background:var(--s0)}
h2{font-size:1.22rem;margin:34px 0 4px}
.findings{margin-top:10px}
.fnd{background:var(--surface);border:1px solid var(--ring);border-radius:14px;
padding:16px 18px;margin:0 0 16px}
.fnd h3{margin:0 0 8px;font-size:1.02rem;display:flex;gap:10px;align-items:baseline}
.num{display:inline-flex;align-items:center;justify-content:center;min-width:22px;
height:22px;border-radius:6px;background:var(--s0);color:#fff;font-size:.76rem;
font-weight:700;flex:0 0 auto}
.claim{font-weight:600;color:var(--ink);margin:0 0 8px}
.fnd p{margin:0 0 9px;color:var(--ink2);font-size:.9rem;max-width:74ch}
.fnd .tv table td:first-child{color:var(--ink2)}
.fnd .tv table td{text-align:left}
[data-tip]{cursor:crosshair}
.lead{stroke:var(--axis);stroke-width:1}
"""

JS = """
const tip=document.createElement('div');tip.className='tip';document.body.append(tip);
document.querySelectorAll('svg.plot[data-pts]').forEach(svg=>{
  const pts=JSON.parse(svg.dataset.pts);
  const names=(svg.dataset.names||'').split('|').filter(Boolean);
  const g=svg.querySelector('.hov'),line=svg.querySelector('.cross');
  const lab=[...svg.querySelectorAll('text.dl')].map(t=>t.textContent);
  const series=names.length?names:lab;
  svg.addEventListener('pointermove',e=>{
    const r=svg.getBoundingClientRect(),vb=svg.viewBox.baseVal;
    const x=(e.clientX-r.left)/r.width*vb.width;
    let best=pts[0];for(const p of pts)if(Math.abs(p.x-x)<Math.abs(best.x-x))best=p;
    g.hidden=false;line.setAttribute('x1',best.x);line.setAttribute('x2',best.x);
    line.setAttribute('y1',26);line.setAttribute('y2',vb.height-46);
    tip.innerHTML='<b>'+best.t+'</b><br>'+best.v.map((v,i)=>
      (series[i]||'value')+': <b>'+v.toLocaleString()+'</b>').join('<br>');
    tip.style.opacity=1;
    tip.style.left=Math.min(e.clientX+14,innerWidth-190)+'px';
    tip.style.top=(e.clientY-10)+'px';
  });
  svg.addEventListener('pointerleave',()=>{g.hidden=true;tip.style.opacity=0;});
});
document.querySelectorAll('[data-tip]').forEach(el=>{
  el.addEventListener('pointerenter',e=>{
    tip.textContent=el.dataset.tip;tip.style.opacity=1;
    tip.style.left=Math.min(e.clientX+14,innerWidth-230)+'px';
    tip.style.top=(e.clientY-10)+'px';});
  el.addEventListener('pointermove',e=>{
    tip.style.left=Math.min(e.clientX+14,innerWidth-230)+'px';
    tip.style.top=(e.clientY-10)+'px';});
  el.addEventListener('pointerleave',()=>{tip.style.opacity=0;});
});
"""


def build() -> str:
    """Assemble the page. Conditions ride along with every chart on it."""
    _, base = run_ladder()[0]
    cond = " · ".join(f"{k.replace('_', ' ')}: <b>{esc(v)}</b>"
                      for k, v in base.conditions.items())
    charts = (chart_npv() + chart_trigger() + chart_ladder() + chart_sigma())
    struct = ("<h2>Structure: what moves what</h2>"
              + chart_levers() + chart_inversion() + chart_capture()
              + chart_cancellation() + chart_correlations())
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Investment timing - charts</title>"
        f"<style>{CSS}</style></head><body><div class=\"wrap\">"
        "<h1>Industrial decarbonisation investment timing</h1>"
        "<p class=\"sub\">Steel: blast furnace to H2-DRI-EAF. Generated by "
        "<code>plots.py</code> - no third-party libraries.</p>"
        f"<p class=\"cond\">Every number on this page is conditional on: {cond}</p>"
        + "<h2>The decision</h2>" + charts + struct + findings_html() +
        "<footer>Explanatory framework, not investment advice. Read "
        "CALIBRATION.md before quoting any figure: the cost-side learning rate is "
        "calibrated, not sourced, and ladder rows 4-7 do not reproduce the "
        "published table.</footer>"
        f"</div><script>{JS}</script></body></html>"
    )


def main() -> int:
    """Write charts.html next to this script."""
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build())
    print(f"Wrote {OUT}")
    print("Open it in a browser (in PyCharm: right-click the file -> Open in Browser).")
    return 0



# ================================================================ findings
CLASS_SLOT = {"value only": 0, "threshold only": 1, "both": 2, "inert": 3}


def chart_levers() -> str:
    """Lever map: %NPV against %trigger. Orthogonality is visible as axis-hugging.

    Scatter uses the all-pairs colour rule, so it is capped at the first three
    categorical slots - which is exactly the number of classes.
    """
    levers = lever_classes()
    xs = [lv.d_trigger_pct for lv in levers]
    ys = [lv.d_npv_pct for lv in levers]
    xr = max(abs(min(xs)), abs(max(xs))) * 1.35 or 1
    yr = max(abs(min(ys)), abs(max(ys))) * 1.30 or 1

    def X(v: float) -> float:
        return scale(v, -xr, xr, PAD_L, W - PAD_R)

    def Y(v: float) -> float:
        return scale(v, -yr, yr, H - PAD_B, PAD_T)

    yt = [(Y(v), f"{v:+.0f}%") for v in nice_ticks(-yr, yr, 5)]
    xt = [(X(v), f"{v:+.0f}%") for v in nice_ticks(-xr, xr, 5)]
    parts = [axes(xt, yt, Y(0.0)),
             f'<line class="axis" x1="{X(0.0):.1f}" y1="{PAD_T}" '
             f'x2="{X(0.0):.1f}" y2="{H - PAD_B}"/>']
    marks = [(Y(lv.d_npv_pct), i, lv.name) for i, lv in enumerate(levers)]
    label_y = {i: y for y, i, _ in declutter(marks, gap=15.0)}
    mid_x = (PAD_L + W - PAD_R) / 2
    for i, lv in enumerate(levers):
        sl = CLASS_SLOT[lv.klass]
        cx, cy = X(lv.d_trigger_pct), Y(lv.d_npv_pct)
        tip = (f"{lv.name} - {lv.klass} | NPV {lv.d_npv_pct:+.3f}% "
               f"| trigger {lv.d_trigger_pct:+.3f}%")
        parts.append(f'<circle class="mk s{sl}" cx="{cx:.1f}" cy="{cy:.1f}" r="6" '
                     f'data-tip="{esc(tip)}"><title>{esc(tip)}</title></circle>')
        ly = label_y[i]
        # Crowded centre: flip the label to the left once past midway, and draw a
        # hairline leader wherever the nudge moved it off its own marker.
        right = cx > mid_x
        lx = cx - 11 if right else cx + 11
        anc = "ar" if right else "al"
        if abs(ly - cy) > 2:
            parts.append(f'<line class="lead" x1="{cx:.1f}" y1="{cy:.1f}" '
                         f'x2="{lx + (4 if right else -4):.1f}" y2="{ly - 4:.1f}"/>')
        parts.append(f'<text class="val {anc}" x="{lx:.1f}" y="{ly:.1f}">'
                     f"{esc(lv.name)}</text>")
    return (
        '<figure class="card">'
        "<figcaption><h3>Lever map: which knob moves which output</h3>"
        "<p>Every point on the vertical axis changes the decision's value and its "
        "threshold by <em>exactly</em> zero percent. Every point on the horizontal "
        "axis does the reverse. Only four levers sit off both axes.</p>"
        "</figcaption>"
        + legend(["value only", "threshold only", "moves both"], [0, 1, 2])
        + f'<svg viewBox="0 0 {W} {H}" role="img" class="plot">'
          f'<text class="axt" transform="rotate(-90 16 {H / 2})" x="16" y="{H / 2}">'
          "change in NPV</text>"
          f'<text class="axt" x="{W / 2}" y="{H - 6}">change in trigger</text>'
        + "".join(parts) + "</svg>"
        + table(["Lever", "d NPV %", "d trigger %", "Class"],
                ([lv.name, f"{lv.d_npv_pct:+.3f}", f"{lv.d_trigger_pct:+.3f}", lv.klass]
                 for lv in levers),
                "Table view - levers")
        + "</figure>"
    )


def chart_inversion() -> str:
    """dNPV/du against hydrogen price, crossing zero. The sign flip is the story."""
    p = Params().with_policy(kappa=0.94)
    sc = ScenarioParams(u=0.85, price_basis="real")
    flip = utilisation_inversion()
    hs = [2.0 + i * 0.5 for i in range(int((14.0 - 2.0) / 0.5) + 1)]
    ds = [_d_npv_du(p, sc, h) for h in hs]
    lo, hi = min(ds), max(ds)
    pad = (hi - lo) * 0.10
    lo, hi = lo - pad, hi + pad

    def X(v: float) -> float:
        return scale(v, hs[0], hs[-1], PAD_L, W - PAD_R)

    def Y(v: float) -> float:
        return scale(v, lo, hi, H - PAD_B, PAD_T)

    yt = [(Y(v), f"{v:,.0f}") for v in nice_ticks(lo, hi, 5)]
    xt = [(X(h), f"{h:.0f}") for h in hs if abs(h - round(h)) < 1e-9 and int(h) % 2 == 0]
    d = " ".join(f"{'M' if k == 0 else 'L'}{X(h):.1f},{Y(v):.1f}"
                 for k, (h, v) in enumerate(zip(hs, ds, strict=False)))
    parts = [axes(xt, yt, Y(0.0)), f'<path class="ln s0" d="{d}"/>']
    if flip:
        fx = X(flip)
        parts.append(f'<line class="mark" x1="{fx:.1f}" y1="{PAD_T}" '
                     f'x2="{fx:.1f}" y2="{H - PAD_B}"/>')
        parts.append(f'<circle class="mk s1" cx="{fx:.1f}" cy="{Y(0.0):.1f}" r="6"/>')
        parts.append(f'<text class="note am s1" x="{fx:.1f}" y="{PAD_T - 8}">'
                     f"sign flip {flip:.2f}</text>")
    px = X(8.29)
    parts.append(f'<line class="thr" x1="{px:.1f}" y1="{PAD_T}" '
                 f'x2="{px:.1f}" y2="{H - PAD_B}"/>')
    parts.append(f'<text class="note am s1" x="{px:.1f}" y="{PAD_T + 14}">'
                 "Platts 8.29</text>")
    pts = [{"x": round(X(h), 1), "t": f"{h:.2f} EUR/kg", "v": [round(v, 1)]}
           for h, v in zip(hs, ds, strict=False)]
    return (
        '<figure class="card">'
        "<figcaption><h3>Utilisation: asset or liability?</h3>"
        f"<p>Sensitivity of NPV to the load factor. It crosses zero at EUR "
        f"{flip:.2f}/kg - above that, running the plant <em>less</em> raises NPV. "
        "The May 2026 market price sits on the wrong side of the crossing.</p>"
        "</figcaption>"
        f'<svg viewBox="0 0 {W} {H}" role="img" class="plot" '
        f'data-pts="{esc(json.dumps(pts))}" data-names="dNPV/du">'
        f'<text class="axt" transform="rotate(-90 16 {H / 2})" x="16" y="{H / 2}">'
        "dNPV / du</text>"
        f'<text class="axt" x="{W / 2}" y="{H - 6}">hydrogen price, EUR/kg</text>'
        + "".join(parts) +
        '<g class="hov" hidden><line class="cross"/></g></svg>'
        + table(["p_H2 (EUR/kg)", "dNPV/du"],
                ([f"{h:.2f}", f"{v:,.1f}"] for h, v in zip(hs, ds, strict=False)),
                "Table view - utilisation sensitivity")
        + "</figure>"
    )


def chart_capture() -> str:
    """T* and the reline year against asset age. They converge, then coincide."""
    rc = reline_capture()
    ages = [r[0] for r in rc.rows]
    rel = [r[1] for r in rc.rows]
    star = [r[2] if r[2] else 2051 for r in rc.rows]
    lo, hi = min(min(rel), min(star)) - 1, max(max(rel), max(star)) + 1

    def X(v: float) -> float:
        return scale(v, ages[0], ages[-1], PAD_L, W - PAD_R)

    def Y(v: float) -> float:
        return scale(v, lo, hi, H - PAD_B, PAD_T)

    yt = [(Y(v), f"{v:.0f}") for v in nice_ticks(lo, hi, 6)]
    xt = [(X(a), str(a)) for a in ages if a % 2 == 0]
    parts = [axes(xt, yt, H - PAD_B)]
    if rc.capture_from is not None:
        x0 = X(rc.capture_from - 0.5)
        parts.append(f'<rect class="band" x="{x0:.1f}" y="{PAD_T}" '
                     f'width="{W - PAD_R - x0:.1f}" height="{H - PAD_B - PAD_T:.1f}"/>')
        parts.append(f'<text class="note" x="{x0 + 8:.1f}" y="{PAD_T + 14}">'
                     f"capture region - T* = reline year</text>")
    for i, (ser, lab) in enumerate(((rel, "reline year"), (star, "T*"))):
        d = " ".join(f"{'M' if k == 0 else 'L'}{X(a):.1f},{Y(v):.1f}"
                     for k, (a, v) in enumerate(zip(ages, ser, strict=False)))
        parts.append(f'<path class="ln s{i}" d="{d}"/>')
    bx = X(rc.best_age)
    parts.append(f'<circle class="mk s2" cx="{bx:.1f}" '
                 f'cy="{Y(star[ages.index(rc.best_age)]):.1f}" r="6"/>')
    parts.append(f'<text class="note am s2" x="{bx:.1f}" y="{PAD_T - 8}">'
                 f"best value: age {rc.best_age}</text>")
    pts = [{"x": round(X(a), 1), "t": f"age {a}", "v": [r, s]}
           for a, r, s in zip(ages, rel, star, strict=False)]
    return (
        '<figure class="card">'
        "<figcaption><h3>When the calendar takes the decision</h3>"
        f"<p>From age {rc.capture_from} onward the optimal commitment year is the "
        "reline year exactly. Value peaks two years short of a reline - not at "
        "the newest asset, and not at the oldest.</p></figcaption>"
        + legend(["reline year", "T*"], [0, 1])
        + f'<svg viewBox="0 0 {W} {H}" role="img" class="plot" '
          f'data-pts="{esc(json.dumps(pts))}" data-names="reline year|T*">'
          f'<text class="axt" transform="rotate(-90 16 {H / 2})" x="16" y="{H / 2}">'
          "year</text>"
          f'<text class="axt" x="{W / 2}" y="{H - 6}">asset age at 2026, years</text>'
        + "".join(parts) +
        '<g class="hov" hidden><line class="cross"/></g></svg>'
        + table(["Age at 2026", "Reline year", "T*", "NPV"],
                ([a, tr, ts or "beyond", f"{v:,.0f}"] for a, tr, ts, v in rc.rows),
                "Table view - reline capture")
        + "</figure>"
    )


def chart_cancellation() -> str:
    """The two factors and their product, indexed to a common base.

    Three quantities on wildly different scales. Indexing to 100 at the lowest
    rate puts them on ONE axis - never a second y-scale.
    """
    rs = rate_cancellation(rates=(0.06, 0.065, 0.07, 0.075, 0.08, 0.085, 0.09,
                                  0.095, 0.10))
    rates = [r[0] for r in rs.rows]
    series = [("break-even p'_M", [r[1] for r in rs.rows]),
              ("option multiple", [r[2] for r in rs.rows]),
              ("trigger (product)", [r[3] for r in rs.rows])]
    idx = [(n, [v / vals[0] * 100.0 for v in vals]) for n, vals in series]
    flat = [v for _, vals in idx for v in vals]
    lo, hi = min(flat) * 0.95, max(flat) * 1.05

    def X(v: float) -> float:
        return scale(v, rates[0], rates[-1], PAD_L, W - PAD_R)

    def Y(v: float) -> float:
        return scale(v, lo, hi, H - PAD_B, PAD_T)

    yt = [(Y(v), f"{v:,.0f}") for v in nice_ticks(lo, hi, 6)]
    xt = [(X(r), f"{r:.1%}") for r in rates if round(r * 1000) % 10 == 0]
    parts = [axes(xt, yt, Y(100.0))]
    ends = []
    for i, (n, vals) in enumerate(idx):
        d = " ".join(f"{'M' if k == 0 else 'L'}{X(r):.1f},{Y(v):.1f}"
                     for k, (r, v) in enumerate(zip(rates, vals, strict=False)))
        parts.append(f'<path class="ln s{i}" d="{d}"/>')
        ends.append((Y(vals[-1]), i, n))
    for y, i, n in declutter(ends):
        parts.append(f'<text class="dl s{i}" x="{W - PAD_R + 8}" '
                     f'y="{y + 4:.1f}">{esc(n)}</text>')
    pts = [{"x": round(X(r), 1), "t": f"r = {r:.1%}",
            "v": [round(vals[k], 1) for _, vals in idx]}
           for k, r in enumerate(rates)]
    return (
        '<figure class="card">'
        "<figcaption><h3>Cancellation, not robustness</h3>"
        f"<p>All three indexed to 100 at r = 6% so they share one axis. Over "
        f"6-10% the break-even price moves {rs.d_break_even_pct:+.0f}% and the "
        f"option multiple {rs.d_multiple_pct:+.0f}%; their product, the trigger, "
        f"moves {rs.d_trigger_pct:+.0f}%. Reporting only the product hides "
        "both.</p></figcaption>"
        + legend([n for n, _ in idx], [0, 1, 2])
        + f'<svg viewBox="0 0 {W} {H}" role="img" class="plot" '
          f'data-pts="{esc(json.dumps(pts))}" '
          f'data-names="{esc("|".join(n for n, _ in idx))}">'
          f'<text class="axt" transform="rotate(-90 16 {H / 2})" x="16" y="{H / 2}">'
          "index, r = 6% is 100</text>"
          f'<text class="axt" x="{W / 2}" y="{H - 6}">real discount rate r</text>'
        + "".join(parts) +
        '<g class="hov" hidden><line class="cross"/></g></svg>'
        + table(["r", "break-even", "multiple", "trigger"],
                ([f"{r:.1%}", f"{be:,.2f}", f"{m:,.3f}", f"{t:,.2f}"]
                 for r, be, m, t in rs.rows),
                "Table view - rate decomposition")
        + "</figure>"
    )


def chart_correlations() -> str:
    """Rank-correlation heatmap. Diverging blue<->red with a neutral midpoint."""
    names, m, n = output_correlations()
    k = len(names)
    cell, x0, y0 = 62, 210, PAD_T + 14
    parts = []
    for i in range(k):
        parts.append(f'<text class="cat ar" x="{x0 - 12}" '
                     f'y="{y0 + cell * i + cell / 2 + 4:.1f}">{esc(names[i])}</text>')
        parts.append(f'<text class="cat am" x="{x0 + cell * i + cell / 2:.1f}" '
                     f'y="{y0 - 8}">{esc(names[i])}</text>')
        for j in range(k):
            v = m[i][j]
            cls = "pos" if v > 0.02 else ("neg" if v < -0.02 else "mid")
            op = min(abs(v), 1.0) * 0.88 + 0.06
            tip = f"{names[i]} vs {names[j]}: {v:+.2f}"
            parts.append(
                f'<rect class="cell {cls}" x="{x0 + cell * j + 1:.1f}" '
                f'y="{y0 + cell * i + 1:.1f}" width="{cell - 2}" height="{cell - 2}" '
                f'rx="4" style="opacity:{op:.2f}" data-tip="{esc(tip)}">'
                f"<title>{esc(tip)}</title></rect>")
            parts.append(f'<text class="cellv am" x="{x0 + cell * j + cell / 2:.1f}" '
                         f'y="{y0 + cell * i + cell / 2 + 4:.1f}">{v:+.2f}</text>')
    return (
        '<figure class="card">'
        "<figcaption><h3>What moves against what</h3>"
        f"<p>Rank correlation across {n} scenarios. T* against NPV is the "
        "strongest opposition: the later you commit, the less it is worth. Read "
        "this <em>with</em> the lever map - the apparent value/threshold coupling "
        "here is an artefact of which levers the ensemble varies.</p>"
        "</figcaption>"
        '<div class="scale"><i class="neg"></i>-1'
        '<i class="mid"></i>0<i class="pos"></i>+1</div>'
        f'<svg viewBox="0 0 {W} 320" role="img" class="plot">' + "".join(parts) +
        "</svg>"
        + table(["Pair", "Rank correlation"],
                ((f"{names[i]} vs {names[j]}", f"{m[i][j]:+.2f}")
                 for i in range(k) for j in range(i + 1, k)),
                "Table view - correlations")
        + "</figure>"
    )


def findings_html() -> str:
    """The prose findings, each with the evidence that produced it."""
    out = ['<section class="findings"><h2>Findings</h2>']
    for i, f in enumerate(all_findings(), 1):
        ev = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>"
                     for k, v in f.evidence[:24])
        out.append(
            f'<article class="fnd"><h3><span class="num">{i}</span>{esc(f.title)}</h3>'
            f'<p class="claim">{esc(f.statement)}</p>'
            f"<p>{esc(f.detail)}</p>"
            f'<details class="tv"><summary>Evidence</summary>'
            f"<table><tbody>{ev}</tbody></table></details></article>")
    out.append("</section>")
    return "".join(out)


if __name__ == "__main__":
    raise SystemExit(main())
