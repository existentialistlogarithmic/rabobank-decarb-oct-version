"""explorer.py -> explorer.html: the sourcing frontier, explorable.

Why this page exists
--------------------
``charts.html`` shows what the model does. This shows what the model *cannot*
do: hold the hydrogen price and the clean-route emission intensity independent.
:mod:`sourcing` ties them into one parameter; this page lets a reader move that
parameter and watch four things react at once - the value, the commitment year,
the trigger, and the gap against the published number.

How it stays honest
-------------------
The model is **not** reimplemented in JavaScript. Every number on the page is
computed here, in Python, by the same ``timing_model`` code the rest of the
build uses, and embedded as a grid; the page only selects and draws. A test
re-runs the model against a sample of embedded points and fails if they ever
disagree, so the page cannot drift from the model the way a hand-ported copy
would.

Grid: 9 member states x 11 green shares x 9 carbon-path multiples = 891 model
runs, about 11 seconds. Colours are the validated three-slot categorical
palette; the light-mode aqua sits below 3:1 on the light surface, so every mark
using it carries a direct label and the page ships a table view.
"""

from __future__ import annotations

import json
from typing import Final

import eurostat
import sourcing
from timing_model.benefit import carbon_price_path
from timing_model.params import Params, ScenarioParams
from timing_model.results import outputs

OUT: Final[str] = "explorer.html"


def build_payload() -> dict:
    """Every number the page can display, computed by the model, once."""
    series = eurostat.refresh(offline=True)
    geos = list(eurostat.STEEL_GEOS)
    thetas = [i / (sourcing.THETA_STEPS - 1) for i in range(sourcing.THETA_STEPS)]
    multiples = list(sourcing.CARBON_MULTIPLES)
    p, sc = Params(), ScenarioParams()
    base_out = outputs(p, sc)
    years = list(range(p.common.t0, p.common.horizon_end + 1))

    grid: dict[str, list[list[dict]]] = {}
    for geo in geos:
        by_multiple: list[list[dict]] = []
        for mult in multiples:
            row: list[dict] = []
            for theta in thetas:
                pt = sourcing.point(geo, theta, series, mult, with_curve=True)
                row.append({
                    "theta": round(pt.theta, 4),
                    "p": round(pt.p_h2, 3),
                    "eps": round(pt.eps_cln, 4),
                    "npv": round(pt.npv0, 1),
                    "t": pt.t_star,
                    "trig": round(pt.trigger, 2),
                    "curve": [round(v, 1) for _, v in pt.npv_by_year],
                })
            by_multiple.append(row)
        grid[geo] = by_multiple

    gaps = {}
    for geo in geos:
        model, consistent, theta = sourcing.feasibility_gap(geo, series)
        gaps[geo] = {"model": round(model, 1),
                     "consistent": round(consistent, 1),
                     "theta": None if theta is None else round(theta, 4)}

    endpoints = {geo: dict(zip(("green", "grey"),
                               (round(v, 3) for v in sourcing.endpoints(geo, series))))
                 for geo in geos}
    crossover = {geo: sourcing.crossover_multiple(geo, series) for geo in geos}
    framing = {geo: [round(v, 1) for v in sourcing.framing_gap(geo, series)]
               for geo in geos}

    return {
        "geos": geos,
        "thetas": [round(t, 4) for t in thetas],
        "multiples": multiples,
        "years": years,
        "grid": grid,
        "gaps": gaps,
        "endpoints": endpoints,
        "crossover": {k: (None if v is None else round(v, 3))
                      for k, v in crossover.items()},
        "framing": framing,
        "base": {
            "npv": round(base_out.npv0, 1),
            "t": base_out.t_star,
            "trigger": round(base_out.trigger, 2),
            "p": sc.p_H2,
            "eps": p.common.eps_cln,
            "eua2026": round(carbon_price_path(p, sc)[p.common.t0], 1),
            "grey_t": round(sourcing.grey_tonnes_per_tonne(), 4),
            "u": sc.u,
        },
    }


PAGE: Final[str] = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The hydrogen sourcing frontier</title>
<style>
:root {
  color-scheme: light;
  --surface-0: #f4f4f1;
  --surface-1: #fcfcfb;
  --border:    #d9d8d2;
  --text-primary:   #0b0b0b;
  --text-secondary: #52514e;
  --text-muted:     #7c7b74;
  --series-1: #2a78d6;
  --series-2: #eb6834;
  --series-3: #1baf7a;
  --critical: #d03b3b;
  --grid: #e6e5e0;
  --context: #b9b8b1;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --surface-0: #111110;
    --surface-1: #1a1a19;
    --border:    #35352f;
    --text-primary:   #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted:     #8d8c83;
    --series-1: #3987e5;
    --series-2: #d95926;
    --series-3: #199e70;
    --critical: #d03b3b;
    --grid: #2a2a26;
    --context: #55554e;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0: #111110;
  --surface-1: #1a1a19;
  --border:    #35352f;
  --text-primary:   #ffffff;
  --text-secondary: #c3c2b7;
  --text-muted:     #8d8c83;
  --series-1: #3987e5;
  --series-2: #d95926;
  --series-3: #199e70;
  --critical: #d03b3b;
  --grid: #2a2a26;
  --context: #55554e;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0 20px 72px;
  background: var(--surface-0); color: var(--text-primary);
  font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
main { max-width: 1140px; margin: 0 auto; }
h1 { font-size: 30px; line-height: 1.2; margin: 40px 0 8px; letter-spacing: -0.02em; }
h2 { font-size: 19px; margin: 40px 0 4px; letter-spacing: -0.01em; }
p  { margin: 10px 0; max-width: 74ch; color: var(--text-secondary); }
p.lede { font-size: 17px; color: var(--text-primary); }
.sub { color: var(--text-muted); font-size: 13.5px; margin: 2px 0 14px; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.9em; }

.tiles { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); margin: 26px 0 8px; }
.tile { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }
.tile .n { font-size: 27px; font-weight: 640; letter-spacing: -0.02em; display: block; }
.tile .l { font-size: 13px; color: var(--text-secondary); display: block; margin-top: 4px; }

.panel { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px 10px; margin: 14px 0; }
.row { display: grid; gap: 14px; grid-template-columns: 1fr; }
@media (min-width: 900px) { .row.two { grid-template-columns: 1.35fr 1fr; } }

.controls { display: flex; flex-wrap: wrap; gap: 18px 26px; align-items: flex-end;
  background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px;
  padding: 14px 18px; margin: 18px 0 6px; position: sticky; top: 0; z-index: 5; }
.ctl { display: flex; flex-direction: column; gap: 6px; }
.ctl > span { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.chips { display: flex; flex-wrap: wrap; gap: 5px; }
.chip { font: inherit; font-size: 13px; padding: 4px 11px; border-radius: 999px; cursor: pointer;
  background: transparent; color: var(--text-secondary); border: 1px solid var(--border); }
.chip[aria-pressed="true"] { background: var(--series-1); border-color: var(--series-1); color: #fff; font-weight: 600; }
.chip:focus-visible, .toggle:focus-visible, input:focus-visible { outline: 2px solid var(--series-1); outline-offset: 2px; }
input[type=range] { width: 210px; accent-color: var(--series-1); }
.val { font-variant-numeric: tabular-nums; font-weight: 600; font-size: 13.5px; color: var(--text-primary); }
.toggle { font: inherit; font-size: 13px; padding: 5px 12px; border-radius: 7px; cursor: pointer;
  background: transparent; color: var(--text-secondary); border: 1px solid var(--border); }

svg { display: block; width: 100%; height: auto; overflow: visible; }
.axis text { fill: var(--text-muted); font-size: 11px; }
.axis line, .axis path { stroke: var(--grid); }
.axis-title { fill: var(--text-secondary); font-size: 11.5px; }
.mark-label { fill: var(--text-primary); font-size: 11.5px; font-variant-numeric: tabular-nums; }
.legend { display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 4px 0 10px; font-size: 12.5px; color: var(--text-secondary); }
.legend i { width: 11px; height: 11px; border-radius: 3px; display: inline-block; vertical-align: -1px; margin-right: 6px; }

.tip { position: fixed; pointer-events: none; opacity: 0; transition: opacity .09s;
  background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 9px 11px; font-size: 12.5px; line-height: 1.5; color: var(--text-primary);
  box-shadow: 0 6px 22px rgba(0,0,0,.16); z-index: 30; max-width: 280px; }
.tip b { font-variant-numeric: tabular-nums; }
.tip .k { color: var(--text-muted); }

table { border-collapse: collapse; width: 100%; font-size: 13px; font-variant-numeric: tabular-nums; }
th, td { text-align: right; padding: 5px 9px; border-bottom: 1px solid var(--border); white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--text-muted); font-weight: 600; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.05em; }
.scroll { overflow-x: auto; }
.note { font-size: 13px; color: var(--text-muted); border-left: 2px solid var(--border); padding-left: 14px; margin: 14px 0; }
.footer { margin-top: 48px; padding-top: 18px; border-top: 1px solid var(--border); font-size: 12.5px; color: var(--text-muted); }
</style>
</head>
<body>
<main>
<h1>The hydrogen sourcing frontier</h1>
<p class="lede">The model asks for a hydrogen price and a clean-route emission
intensity as two independent inputs. In the world they are one input. Hydrogen
is bought somewhere between reformed gas and electrolysed power, and where you
buy it sets <em>both</em> the price and the emissions. Tying them together moves
the value, the commitment year and the trigger at once — and it says a
quarter to a third of the published NPV was never available.</p>

<div class="tiles" id="tiles"></div>

<div class="controls">
  <label class="ctl"><span>Member state</span><span class="chips" id="geos"></span></label>
  <label class="ctl"><span>Green share of hydrogen</span>
    <input type="range" id="theta" min="0" max="10" step="1" value="0" aria-describedby="thetaOut">
    <span class="val" id="thetaOut"></span></label>
  <label class="ctl"><span>Carbon path</span>
    <input type="range" id="mult" min="0" max="8" step="1" value="0" aria-describedby="multOut">
    <span class="val" id="multOut"></span></label>
  <label class="ctl"><span>&nbsp;</span>
    <button class="toggle" id="tableBtn" aria-expanded="false">Show data table</button></label>
</div>

<div class="row two">
  <div class="panel">
    <h2>Value along the frontier</h2>
    <p class="sub">NPV at the best commitment year, against the green share of
      hydrogen. The dashed rule is the model's published NPV, which assumes a
      grey price with green emissions.</p>
    <div class="legend" id="legendA"></div>
    <svg id="chartA" viewBox="0 0 640 380" role="img" aria-label="NPV against green hydrogen share"></svg>
  </div>
  <div class="panel">
    <h2>When to commit</h2>
    <p class="sub">NPV by commitment year at the selected sourcing point. The
      marked year is <code>T*</code>.</p>
    <svg id="chartB" viewBox="0 0 460 380" role="img" aria-label="NPV by commitment year"></svg>
  </div>
</div>

<div class="row two">
  <div class="panel">
    <h2>What green hydrogen needs to win</h2>
    <p class="sub">The 2026 carbon price at which all-green overtakes all-grey on
      NPV. The model's own path starts at €76 and its trigger is €109.52.</p>
    <svg id="chartC" viewBox="0 0 640 330" role="img" aria-label="Carbon price at which green overtakes grey, by member state"></svg>
  </div>
  <div class="panel">
    <h2>Sourcing moves the year</h2>
    <p class="sub">Optimal commitment year at each end of the frontier.</p>
    <div class="legend" id="legendD"></div>
    <svg id="chartD" viewBox="0 0 460 330" role="img" aria-label="Optimal commitment year, all-grey against all-green"></svg>
  </div>
</div>

<div class="panel" id="tableWrap" hidden>
  <h2>Data table</h2>
  <p class="sub">The selected member state, every green share, at the selected carbon path.</p>
  <div class="scroll"><table id="table"></table></div>
</div>

<div class="note" id="method"></div>
<div class="footer">Generated by <code>explorer.py</code> from
<code>timing_model</code> and cached Eurostat/ECB series. Every value is computed
in Python and embedded; this page selects and draws, it does not model.</div>
</main>
<div class="tip" id="tip" role="status" aria-live="polite"></div>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
const D = JSON.parse(document.getElementById("payload").textContent);
const NS = "http://www.w3.org/2000/svg";
const tip = document.getElementById("tip");
let geo = "DE", ti = 0, mi = 0;

const eur = n => "\\u20ac" + Math.round(n).toLocaleString("en-GB");
const pct = n => (n * 100).toFixed(1) + "%";
const cur = () => D.grid[geo][mi][ti];
const yearOf = t => t === null ? "beyond horizon" : t;

function el(tag, attrs, text) {
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text !== undefined) n.textContent = text;
  return n;
}
function showTip(evt, html) {
  tip.innerHTML = html; tip.style.opacity = 1;
  const r = tip.getBoundingClientRect();
  let x = evt.clientX + 14, y = evt.clientY - 12;
  if (x + r.width > innerWidth - 8) x = evt.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = innerHeight - r.height - 8;
  tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px";
}
const hideTip = () => { tip.style.opacity = 0; };

function ticks(lo, hi, n) {
  const raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw) || mag * 10;
  const out = []; for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(v);
  return out;
}
function frame(svg, w, h, m) {
  svg.innerHTML = "";
  return { x0: m.l, x1: w - m.r, y0: h - m.b, y1: m.t };
}
function axes(svg, f, xt, yt, xfmt, yfmt, xtitle, ytitle) {
  const g = el("g", { class: "axis" });
  yt.forEach(([v, y]) => {
    g.appendChild(el("line", { x1: f.x0, x2: f.x1, y1: y, y2: y }));
    g.appendChild(el("text", { x: f.x0 - 8, y: y + 4, "text-anchor": "end" }, yfmt(v)));
  });
  xt.forEach(([v, x]) => g.appendChild(el("text", { x, y: f.y0 + 18, "text-anchor": "middle" }, xfmt(v))));
  g.appendChild(el("line", { x1: f.x0, x2: f.x1, y1: f.y0, y2: f.y0 }));
  svg.appendChild(g);
  if (xtitle) svg.appendChild(el("text", { class: "axis-title", x: (f.x0 + f.x1) / 2, y: f.y0 + 38, "text-anchor": "middle" }, xtitle));
  if (ytitle) svg.appendChild(el("text", { class: "axis-title", x: f.x0, y: f.y1 - 14, "text-anchor": "start" }, ytitle));
}
const path = pts => pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");

/* ---------- A: value along the frontier ---------- */
function drawA() {
  const svg = document.getElementById("chartA"), f = frame(svg, 640, 380, { l: 58, r: 18, t: 26, b: 52 });
  const rows = D.geos.map(g => D.grid[g][mi]);
  let lo = Math.min(D.base.npv, ...rows.flat().map(d => d.npv));
  let hi = Math.max(D.base.npv, ...rows.flat().map(d => d.npv));
  const pad = (hi - lo) * 0.12 || 1; lo -= pad; hi += pad;
  const X = t => f.x0 + t * (f.x1 - f.x0);
  const Y = v => f.y0 - (v - lo) / (hi - lo) * (f.y0 - f.y1);
  const yt = ticks(lo, hi, 5).map(v => [v, Y(v)]);
  const xt = [0, 0.25, 0.5, 0.75, 1].map(v => [v, X(v)]);
  axes(svg, f, xt, yt, v => (v * 100).toFixed(0) + "%", eur, "green share of hydrogen", "NPV \\u20ac/t capacity");

  if (Y(0) > f.y1 && Y(0) < f.y0)
    svg.appendChild(el("line", { x1: f.x0, x2: f.x1, y1: Y(0), y2: Y(0), stroke: "var(--text-muted)", "stroke-width": 1, "stroke-dasharray": "1 3" }));

  D.geos.filter(g => g !== geo).forEach(g => {
    svg.appendChild(el("path", { d: path(D.grid[g][mi].map(d => [X(d.theta), Y(d.npv)])),
      fill: "none", stroke: "var(--context)", "stroke-width": 1.25, opacity: 0.85 }));
  });

  svg.appendChild(el("line", { x1: f.x0, x2: f.x1, y1: Y(D.base.npv), y2: Y(D.base.npv),
    stroke: "var(--critical)", "stroke-width": 2, "stroke-dasharray": "6 4" }));
  svg.appendChild(el("text", { class: "mark-label", x: f.x1, y: Y(D.base.npv) - 7, "text-anchor": "end",
    fill: "var(--critical)" }, "published " + eur(D.base.npv)));

  const me = D.grid[geo][mi];
  svg.appendChild(el("path", { d: path(me.map(d => [X(d.theta), Y(d.npv)])),
    fill: "none", stroke: "var(--series-1)", "stroke-width": 2.5, "stroke-linejoin": "round" }));

  const gap = D.gaps[geo];
  if (gap.theta !== null && mi === 0) {
    const gx = X(gap.theta), gy = Y(gap.consistent);
    svg.appendChild(el("line", { x1: gx, x2: gx, y1: gy, y2: Y(D.base.npv),
      stroke: "var(--critical)", "stroke-width": 1.5, "stroke-dasharray": "2 3" }));
    svg.appendChild(el("circle", { cx: gx, cy: gy, r: 5.5, fill: "var(--critical)",
      stroke: "var(--surface-1)", "stroke-width": 2 }));
    const dy = gy - Y(D.base.npv) > 40 ? -10 : 22;
    svg.appendChild(el("text", { class: "mark-label", x: Math.min(gx + 9, f.x1 - 4), y: (gy + Y(D.base.npv)) / 2 + dy / 6,
      "text-anchor": gx > (f.x0 + f.x1) / 2 ? "end" : "start", fill: "var(--critical)" },
      "\\u2212" + eur(gap.model - gap.consistent) + " (" + pct((gap.model - gap.consistent) / gap.model) + ")"));
  }

  me.forEach((d, i) => {
    const cx = X(d.theta), cy = Y(d.npv);
    svg.appendChild(el("circle", { cx, cy, r: i === ti ? 6 : 3.5,
      fill: "var(--series-1)", stroke: "var(--surface-1)", "stroke-width": 2 }));
    const hit = el("circle", { cx, cy, r: 15, fill: "transparent", style: "cursor:pointer" });
    hit.addEventListener("mousemove", e => showTip(e,
      "<b>" + geo + "</b> \\u2014 " + (d.theta * 100).toFixed(0) + "% green<br>" +
      "<span class='k'>hydrogen</span> <b>\\u20ac" + d.p.toFixed(2) + "/kg</b><br>" +
      "<span class='k'>eps_cln</span> <b>" + d.eps.toFixed(3) + "</b> tCO\\u2082/t<br>" +
      "<span class='k'>NPV</span> <b>" + eur(d.npv) + "</b>/t capacity<br>" +
      "<span class='k'>T*</span> <b>" + yearOf(d.t) + "</b><br>" +
      "<span class='k'>trigger</span> <b>\\u20ac" + d.trig.toFixed(0) + "</b>/tCO\\u2082"));
    hit.addEventListener("mouseleave", hideTip);
    hit.addEventListener("click", () => { ti = i; document.getElementById("theta").value = i; render(); });
    svg.appendChild(hit);
  });

  document.getElementById("legendA").innerHTML =
    "<span><i style='background:var(--series-1)'></i>" + geo + "</span>" +
    "<span><i style='background:var(--context)'></i>other member states</span>" +
    "<span><i style='background:var(--critical)'></i>published NPV (infeasible pair)</span>";
}

/* ---------- B: NPV by commitment year ---------- */
function drawB() {
  const svg = document.getElementById("chartB"), f = frame(svg, 460, 380, { l: 60, r: 16, t: 26, b: 52 });
  const d = cur(), c = d.curve;
  let lo = Math.min(...c), hi = Math.max(...c);
  const pad = (hi - lo) * 0.12 || 1; lo -= pad; hi += pad;
  const X = y => f.x0 + (y - D.years[0]) / (D.years.length - 1) * (f.x1 - f.x0);
  const Y = v => f.y0 - (v - lo) / (hi - lo) * (f.y0 - f.y1);
  const yt = ticks(lo, hi, 5).map(v => [v, Y(v)]);
  const xt = D.years.filter(y => y % 6 === 0).map(y => [y, X(y)]);
  axes(svg, f, xt, yt, v => v, eur, "commitment year", "NPV \\u20ac/t capacity");
  if (Y(0) > f.y1 && Y(0) < f.y0)
    svg.appendChild(el("line", { x1: f.x0, x2: f.x1, y1: Y(0), y2: Y(0), stroke: "var(--text-muted)", "stroke-width": 1, "stroke-dasharray": "1 3" }));
  svg.appendChild(el("path", { d: path(c.map((v, i) => [X(D.years[i]), Y(v)])),
    fill: "none", stroke: "var(--series-1)", "stroke-width": 2.5, "stroke-linejoin": "round" }));
  if (d.t !== null) {
    const k = D.years.indexOf(d.t);
    svg.appendChild(el("line", { x1: X(d.t), x2: X(d.t), y1: f.y0, y2: Y(c[k]), stroke: "var(--series-2)", "stroke-width": 1.5, "stroke-dasharray": "3 3" }));
    svg.appendChild(el("circle", { cx: X(d.t), cy: Y(c[k]), r: 6, fill: "var(--series-2)", stroke: "var(--surface-1)", "stroke-width": 2 }));
    svg.appendChild(el("text", { class: "mark-label", x: X(d.t), y: Y(c[k]) - 13, "text-anchor": "middle" }, "T* " + d.t));
  }
  c.forEach((v, i) => {
    const hit = el("rect", { x: X(D.years[i]) - 7, y: f.y1, width: 14, height: f.y0 - f.y1, fill: "transparent" });
    hit.addEventListener("mousemove", e => showTip(e,
      "<b>commit " + D.years[i] + "</b><br><span class='k'>NPV</span> <b>" + eur(v) + "</b>/t capacity"));
    hit.addEventListener("mouseleave", hideTip);
    svg.appendChild(hit);
  });
}

/* ---------- C: crossover carbon price ---------- */
function drawC() {
  const svg = document.getElementById("chartC"), f = frame(svg, 640, 330, { l: 42, r: 96, t: 20, b: 46 });
  const rows = D.geos.map(g => [g, D.crossover[g] === null ? null : D.crossover[g] * D.base.eua2026])
    .sort((a, b) => (a[1] === null) - (b[1] === null) || a[1] - b[1]);
  const hi = Math.max(...rows.map(r => r[1] || 0)) * 1.06;
  const X = v => f.x0 + v / hi * (f.x1 - f.x0);
  const bh = (f.y0 - f.y1) / rows.length;
  const g = el("g", { class: "axis" });
  ticks(0, hi, 5).forEach(v => {
    g.appendChild(el("line", { x1: X(v), x2: X(v), y1: f.y1, y2: f.y0 }));
    g.appendChild(el("text", { x: X(v), y: f.y0 + 17, "text-anchor": "middle" }, eur(v)));
  });
  svg.appendChild(g);
  svg.appendChild(el("text", { class: "axis-title", x: (f.x0 + f.x1) / 2, y: f.y0 + 38, "text-anchor": "middle" },
    "2026 EUA price at which green hydrogen overtakes grey (\\u20ac/tCO\\u2082)"));

  [[D.base.eua2026, "path starts \\u20ac76", 20], [D.base.trigger, "trigger \\u20ac110", 7]].forEach(([v, lab, up]) => {
    svg.appendChild(el("line", { x1: X(v), x2: X(v), y1: f.y1 - up - 3, y2: f.y0, stroke: "var(--critical)", "stroke-width": 1.5, "stroke-dasharray": "4 3" }));
    svg.appendChild(el("text", { class: "mark-label", x: X(v) + 4, y: f.y1 - up, fill: "var(--critical)", "font-size": 10.5 }, lab));
  });

  rows.forEach(([g2, v], i) => {
    const y = f.y1 + i * bh + 3, h = bh - 6;
    svg.appendChild(el("text", { class: "mark-label", x: f.x0 - 8, y: y + h / 2 + 4, "text-anchor": "end",
      "font-weight": g2 === geo ? 700 : 400 }, g2));
    if (v === null) return;
    const r = el("rect", { x: f.x0, y, width: Math.max(2, X(v) - f.x0), height: h, rx: 4,
      fill: g2 === geo ? "var(--series-1)" : "var(--context)" });
    r.addEventListener("mousemove", e => showTip(e, "<b>" + g2 + "</b><br><span class='k'>green wins above</span> <b>\\u20ac" +
      Math.round(v) + "</b>/tCO\\u2082 in 2026<br><span class='k'>that is</span> <b>" + D.crossover[g2].toFixed(1) +
      "\\u00d7</b> the model's central path"));
    r.addEventListener("mouseleave", hideTip);
    svg.appendChild(r);
    svg.appendChild(el("text", { class: "mark-label", x: X(v) + 8, y: y + h / 2 + 4 },
      eur(v) + "  (" + D.crossover[g2].toFixed(1) + "\\u00d7)"));
  });
}

/* ---------- D: T* at each end of the frontier ---------- */
function drawD() {
  const svg = document.getElementById("chartD"), f = frame(svg, 460, 330, { l: 42, r: 58, t: 20, b: 46 });
  const last = D.years[D.years.length - 1];
  const val = t => t === null ? last + 2 : t;
  const last_t = D.thetas.length - 1;
  const rows = D.geos.map(g => [g, val(D.grid[g][mi][0].t), val(D.grid[g][mi][last_t].t)]);
  const lo = Math.min(...rows.flatMap(r => [r[1], r[2]])) - 1;
  const hi = Math.max(...rows.flatMap(r => [r[1], r[2]])) + 1;
  const X = v => f.x0 + (v - lo) / (hi - lo) * (f.x1 - f.x0);
  const bh = (f.y0 - f.y1) / rows.length;
  const g = el("g", { class: "axis" });
  ticks(lo, hi, 4).forEach(v => {
    g.appendChild(el("line", { x1: X(v), x2: X(v), y1: f.y1, y2: f.y0 }));
    g.appendChild(el("text", { x: X(v), y: f.y0 + 17, "text-anchor": "middle" }, v.toFixed(0)));
  });
  svg.appendChild(g);
  svg.appendChild(el("text", { class: "axis-title", x: (f.x0 + f.x1) / 2, y: f.y0 + 38, "text-anchor": "middle" }, "optimal commitment year T*"));
  rows.forEach(([g2, a, b], i) => {
    const y = f.y1 + i * bh + bh / 2;
    svg.appendChild(el("text", { class: "mark-label", x: f.x0 - 8, y: y + 4, "text-anchor": "end",
      "font-weight": g2 === geo ? 700 : 400 }, g2));
    svg.appendChild(el("line", { x1: X(a), x2: X(b), y1: y, y2: y, stroke: "var(--context)", "stroke-width": 2 }));
    [[a, "var(--series-2)", "grey"], [b, "var(--series-3)", "green"]].forEach(([v, col, lab]) => {
      const c = el("circle", { cx: X(v), cy: y, r: 5.5, fill: col, stroke: "var(--surface-1)", "stroke-width": 2 });
      c.addEventListener("mousemove", e => showTip(e, "<b>" + g2 + "</b> \\u2014 all-" + lab + "<br><span class='k'>T*</span> <b>" +
        (v > last ? "beyond horizon" : v) + "</b>"));
      c.addEventListener("mouseleave", hideTip);
      svg.appendChild(c);
    });
    svg.appendChild(el("text", { class: "mark-label", x: X(Math.max(a, b)) + 9, y: y + 4, "font-size": 10.5 },
      (b - a === 0 ? "same" : (b - a > 0 ? "+" : "") + (b - a) + "yr")));
  });
  document.getElementById("legendD").innerHTML =
    "<span><i style='background:var(--series-2)'></i>all-grey (\\u03b8 = 0)</span>" +
    "<span><i style='background:var(--series-3)'></i>all-green (\\u03b8 = 1)</span>";
}

/* ---------- tiles, table, method ---------- */
function drawTiles() {
  const gaps = D.geos.map(g => (D.gaps[g].model - D.gaps[g].consistent) / D.gaps[g].model);
  const xs = D.geos.map(g => D.crossover[g]).filter(v => v !== null);
  const last = D.years[D.years.length - 1];
  const shifts = D.geos.map(g => {
    const lastT = D.thetas.length - 1;
    const a = D.grid[g][0][0].t === null ? last + 2 : D.grid[g][0][0].t;
    const b = D.grid[g][0][lastT].t === null ? last + 2 : D.grid[g][0][lastT].t;
    return b - a;
  });
  document.getElementById("tiles").innerHTML = [
    ["<span class='n'>" + pct(Math.min(...gaps)) + "\\u2013" + pct(Math.max(...gaps)) + "</span>",
     "of the published NPV rests on a hydrogen price and an emission intensity that cannot both hold"],
    ["<span class='n'>" + Math.min(...xs).toFixed(1) + "\\u2013" + Math.max(...xs).toFixed(1) + "\\u00d7</span>",
     "the carbon price green hydrogen needs before it beats fossil hydrogen on NPV"],
    ["<span class='n'>up to " + Math.max(...shifts) + " years</span>",
     "that sourcing alone moves the optimal commitment year \\u2014 a timing lever the model treats as a cost axis"],
  ].map(([n, l]) => "<div class='tile'>" + n + "<span class='l'>" + l + "</span></div>").join("");
}

function drawTable() {
  const rows = D.grid[geo][mi];
  document.getElementById("table").innerHTML =
    "<thead><tr><th>green share</th><th>hydrogen \\u20ac/kg</th><th>eps_cln tCO\\u2082/t</th>" +
    "<th>NPV \\u20ac/t</th><th>T*</th><th>trigger \\u20ac/tCO\\u2082</th></tr></thead><tbody>" +
    rows.map(d => "<tr><td>" + (d.theta * 100).toFixed(0) + "%</td><td>" + d.p.toFixed(2) +
      "</td><td>" + d.eps.toFixed(3) + "</td><td>" + d.npv.toFixed(0) + "</td><td>" +
      yearOf(d.t) + "</td><td>" + d.trig.toFixed(1) + "</td></tr>").join("") + "</tbody>";
}

function render() {
  const d = cur();
  document.getElementById("thetaOut").textContent =
    (d.theta * 100).toFixed(0) + "% green \\u2014 \\u20ac" + d.p.toFixed(2) + "/kg, eps_cln " + d.eps.toFixed(3);
  document.getElementById("multOut").textContent =
    D.multiples[mi].toFixed(1) + "\\u00d7 \\u2014 \\u20ac" + Math.round(D.base.eua2026 * D.multiples[mi]) + "/tCO\\u2082 in 2026";
  document.querySelectorAll("#geos .chip").forEach(c => c.setAttribute("aria-pressed", c.dataset.geo === geo));
  drawTiles(); drawA(); drawB(); drawC(); drawD(); drawTable();
  document.getElementById("method").innerHTML =
    "<b>Method.</b> Green hydrogen is the Eurostat industrial electricity price at " +
    "55&nbsp;kWh/kg; grey is the Eurostat industrial gas price at 41.1&nbsp;kWh/kg, with its " +
    "9&nbsp;kgCO\\u2082/kg charged through <code>eps_cln</code> rather than inside the price, so the " +
    "carbon is counted once and escalates with the path. Both are floors: no electrolyser or " +
    "reformer capital cost, no compression, storage or transport, so every hydrogen price here is " +
    "an underestimate and the frontier is the most favourable version of this trade-off. " +
    "All other parameters stay at their registered defaults (load factor " + D.base.u +
    "). Published NPV " + eur(D.base.npv) + " assumes \\u20ac" + D.base.p.toFixed(2) +
    "/kg with eps_cln " + D.base.eps + " \\u2014 a grey price with green emissions.";
}

const chips = document.getElementById("geos");
D.geos.forEach(g => {
  const b = document.createElement("button");
  b.className = "chip"; b.textContent = g; b.dataset.geo = g;
  b.setAttribute("aria-pressed", g === geo);
  b.addEventListener("click", () => { geo = g; render(); });
  chips.appendChild(b);
});
const thetaEl = document.getElementById("theta"), multEl = document.getElementById("mult");
thetaEl.max = D.thetas.length - 1;
multEl.max = D.multiples.length - 1;
thetaEl.addEventListener("input", e => { ti = +e.target.value; render(); });
multEl.addEventListener("input", e => { mi = +e.target.value; render(); });
document.getElementById("tableBtn").addEventListener("click", e => {
  const w = document.getElementById("tableWrap"), open = w.hidden;
  w.hidden = !open; e.target.setAttribute("aria-expanded", String(open));
  e.target.textContent = open ? "Hide data table" : "Show data table";
});
addEventListener("scroll", hideTip, { passive: true });
render();
</script>
</body>
</html>
"""


def render(payload: dict) -> str:
    """The page, with the grid embedded."""
    blob = json.dumps(payload, separators=(",", ":"))
    # </script> inside a JSON blob would close the host element early.
    return PAGE.replace("__PAYLOAD__", blob.replace("</", "<\\/"))


def main() -> int:
    """Build the grid and write explorer.html."""
    payload = build_payload()
    html = render(payload)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    runs = len(payload["geos"]) * len(payload["thetas"]) * len(payload["multiples"])
    print(f"Wrote {OUT} ({runs} model runs embedded, {len(html) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
