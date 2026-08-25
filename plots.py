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
from dataclasses import replace
from typing import Iterable, Sequence

from timing_model.benefit import carbon_price_path
from timing_model.objective import npv_curve
from timing_model.params import Params, ScenarioParams
from timing_model.results import Outputs
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
        for n, s in zip(names, slots)
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
        + legend([l for l, _ in curves], range(4))
        + f'<svg viewBox="0 0 {W} {H}" role="img" class="plot" '
          f'data-pts="{esc(json.dumps(pts))}">'
          f'<text class="axt" transform="rotate(-90 16 {H / 2})" x="16" y="{H / 2}">'
          "EUR / t capacity</text>" + "".join(parts) +
        '<g class="hov" hidden><line class="cross"/></g></svg>'
        + table(["Year"] + [l for l, _ in curves],
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
"""


def build() -> str:
    """Assemble the page. Conditions ride along with every chart on it."""
    _, base = run_ladder()[0]
    cond = " · ".join(f"{k.replace('_', ' ')}: <b>{esc(v)}</b>"
                      for k, v in base.conditions.items())
    charts = chart_npv() + chart_trigger() + chart_ladder() + chart_sigma()
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Investment timing - charts</title>"
        f"<style>{CSS}</style></head><body><div class=\"wrap\">"
        "<h1>Industrial decarbonisation investment timing</h1>"
        "<p class=\"sub\">Steel: blast furnace to H2-DRI-EAF. Generated by "
        "<code>plots.py</code> - no third-party libraries.</p>"
        f"<p class=\"cond\">Every number on this page is conditional on: {cond}</p>"
        + charts +
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


if __name__ == "__main__":
    raise SystemExit(main())
