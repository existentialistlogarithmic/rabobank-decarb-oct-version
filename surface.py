"""The fleet surface: NPV over commitment year and asset age, in 3D.

Writes ``surface.html`` - a rotatable Canvas surface plus a flat heatmap of the
same grid. Standard library only on the Python side; the rendering is plain
Canvas 2D with a painter's algorithm, no WebGL and no libraries.

Why 3D here, when it is usually the wrong choice: this data genuinely is a
surface over two continuous parameters, and its *shape* is the finding. A
diagonal cliff traces the reline year across the fleet, and the highest ground
runs along the near side of that cliff. Ridges and cliffs are what a surface
shows and a table does not. Exact values still come from the heatmap and the
table underneath - the 3D view is for the shape, never for reading numbers off.
"""

from __future__ import annotations

import html
import json

from timing_model.cost import reline_year
from timing_model.objective import npv
from timing_model.params import Params, ScenarioParams

OUT = "surface.html"
AGES = list(range(0, 20))
YEARS = list(range(2026, 2041))


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def grid() -> tuple[list[list[float]], list[int]]:
    """NPV[age][year] in EUR/t capacity, plus the reline year for each age."""
    sc = ScenarioParams(u=0.85)
    z: list[list[float]] = []
    rel: list[int] = []
    for a in AGES:
        p = Params().with_sector(age0=float(a))
        z.append([npv(T, p, sc) for T in YEARS])
        rel.append(reline_year(p))
    return z, rel


CSS = """
:root{--ground:#f4f6f7;--surface:#fff;--sunk:#eef1f3;--ink:#0f1519;--ink2:#48555e;
--muted:#7b8892;--rule:#dde3e7;--accent:#0a5f6b;--signal:#b2481f;
--r1:#cde2fb;--r2:#9ec5f4;--r3:#6da7ec;--r4:#3987e5;--r5:#256abf;--r6:#184f95;--r7:#0d366b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--ground:#11161a;--surface:#181e23;--sunk:#1f262c;--ink:#e8eef2;--ink2:#a6b3bc;
--muted:#7b8892;--rule:#262e35;--accent:#5cb3bf;--signal:#e08b62;
--r1:#0d366b;--r2:#184f95;--r3:#256abf;--r4:#3987e5;--r5:#6da7ec;--r6:#9ec5f4;--r7:#cde2fb}}
:root[data-theme="dark"]{--ground:#11161a;--surface:#181e23;--sunk:#1f262c;
--ink:#e8eef2;--ink2:#a6b3bc;--muted:#7b8892;--rule:#262e35;--accent:#5cb3bf;
--signal:#e08b62;--r1:#0d366b;--r2:#184f95;--r3:#256abf;--r4:#3987e5;--r5:#6da7ec;
--r6:#9ec5f4;--r7:#cde2fb}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
font:1rem/1.65 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
.page{max-width:60rem;margin:0 auto;padding:2.5rem 1.25rem 5rem}
h1{font-family:"Source Serif 4",Georgia,serif;font-size:clamp(1.7rem,4vw,2.4rem);
margin:0 0 .5rem;line-height:1.15;text-wrap:balance;font-weight:600}
h2{font-family:"Source Serif 4",Georgia,serif;font-size:1.25rem;margin:2.5rem 0 .5rem;
font-weight:600}
.eyebrow{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.7rem;
letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
p{margin:0 0 1rem;max-width:66ch;color:var(--ink2)}
p strong{color:var(--ink)}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:2px;
padding:1rem;margin:1rem 0 0}
canvas{display:block;width:100%;height:auto;touch-action:none;cursor:grab}
canvas:active{cursor:grabbing}
.bar{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin:0 0 .8rem}
button{font:inherit;font-size:.83rem;padding:.35rem .7rem;border-radius:2px;
border:1px solid var(--rule);background:var(--sunk);color:var(--ink);cursor:pointer}
button:hover{border-color:var(--accent)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button[aria-pressed="true"]{background:var(--accent);color:#fff;border-color:var(--accent)}
.hint{font-size:.8rem;color:var(--muted);margin-left:auto}
.scale{display:flex;align-items:center;gap:.5rem;font-size:.78rem;color:var(--ink2);
margin:.8rem 0 0;font-variant-numeric:tabular-nums}
.ramp{display:flex;height:11px;flex:1;max-width:16rem;border-radius:2px;overflow:hidden}
.ramp i{flex:1}
table{border-collapse:collapse;font-size:.74rem;font-variant-numeric:tabular-nums;
width:100%}
th,td{padding:.15rem .3rem;text-align:right;white-space:nowrap}
thead th{border-bottom:2px solid var(--ink);color:var(--ink);font-weight:600}
tbody th{text-align:left;color:var(--ink2);font-weight:400}
td{color:var(--ink2)}
td.cliff{box-shadow:inset 2px 0 0 var(--signal)}
.tblwrap{overflow-x:auto}
details{margin-top:1rem}summary{cursor:pointer;color:var(--ink2);font-size:.86rem}
footer{margin-top:3rem;padding-top:1.2rem;border-top:1px solid var(--rule);
font-size:.83rem;color:var(--muted)}
"""

JS = r"""
const D=window.__SURF__, ages=D.ages, years=D.years, z=D.z, rel=D.rel;
let lo=Infinity, hi=-Infinity;
for(const row of z) for(const v of row){ if(v<lo)lo=v; if(v>hi)hi=v; }
const cv=document.getElementById('surf'), ctx=cv.getContext('2d');
let az=-0.62, el=0.72, dragging=false, px=0, py=0;
const ramp=['--r1','--r2','--r3','--r4','--r5','--r6','--r7'].map(v=>
  getComputedStyle(document.documentElement).getPropertyValue(v).trim());
const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();

function size(){
  const w=cv.clientWidth, h=Math.round(w*0.62), r=devicePixelRatio||1;
  cv.width=w*r; cv.height=h*r; ctx.setTransform(r,0,0,r,0,0); return {w,h};
}
function raw(i,j,v){
  // Model space -> rotated space. Plan is unit-square; z deliberately
  // compressed so the terrain reads as terrain, not as a crumpled sheet.
  const nx=(j/(years.length-1)-0.5), ny=(i/(ages.length-1)-0.5);
  const nz=((v-lo)/(hi-lo)-0.5)*0.55;
  const ca=Math.cos(az), sa=Math.sin(az);
  const rx=nx*ca-ny*sa, ry=nx*sa+ny*ca;
  const ce=Math.cos(el), se=Math.sin(el);
  return {x:rx, y:ry*ce-nz*se, d:ry*se+nz*ce};
}
let fit={s:1,ox:0,oy:0};
function refit(w,h){
  // Fit whatever the current rotation produces into the frame, so the surface
  // can never overflow the canvas at any angle the user drags to.
  let x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity;
  for(let i=0;i<ages.length;i++) for(let j=0;j<years.length;j++){
    const p=raw(i,j,z[i][j]);
    if(p.x<x0)x0=p.x; if(p.x>x1)x1=p.x; if(p.y<y0)y0=p.y; if(p.y>y1)y1=p.y;
  }
  const pad=54;
  const s=Math.min((w-pad*2)/(x1-x0||1),(h-pad*2)/(y1-y0||1));
  fit={s, ox:w/2-((x0+x1)/2)*s, oy:h/2+((y0+y1)/2)*s};
}
function project(i,j,v){
  const p=raw(i,j,v);
  return {x:fit.ox+p.x*fit.s, y:fit.oy-p.y*fit.s, d:p.d};
}
function colour(v){
  const t=(v-lo)/(hi-lo);
  return ramp[Math.max(0,Math.min(ramp.length-1,Math.round(t*(ramp.length-1))))];
}
function draw(){
  const {w,h}=size();
  ctx.clearRect(0,0,w,h);
  refit(w,h);
  const quads=[];
  for(let i=0;i<ages.length-1;i++) for(let j=0;j<years.length-1;j++){
    const pts=[project(i,j,z[i][j]),project(i,j+1,z[i][j+1]),
               project(i+1,j+1,z[i+1][j+1]),project(i+1,j,z[i+1][j])];
    const mid=(z[i][j]+z[i][j+1]+z[i+1][j+1]+z[i+1][j])/4;
    quads.push({pts,mid,d:(pts[0].d+pts[1].d+pts[2].d+pts[3].d)/4,
                cliff: years[j] === rel[i]});
  }
  quads.sort((a,b)=>a.d-b.d);                 // painter's algorithm, far first
  const stroke=css('--surface');
  for(const q of quads){
    ctx.beginPath(); ctx.moveTo(q.pts[0].x,q.pts[0].y);
    for(let k=1;k<4;k++) ctx.lineTo(q.pts[k].x,q.pts[k].y);
    ctx.closePath();
    ctx.fillStyle=colour(q.mid); ctx.fill();
    ctx.strokeStyle=stroke; ctx.lineWidth=0.6; ctx.stroke();
  }
  // The reline traced as one continuous ridge line, drawn over the surface.
  ctx.beginPath();
  let started=false;
  for(let i=0;i<ages.length;i++){
    const j=years.indexOf(rel[i]);
    if(j<0) continue;
    const p=project(i,j,z[i][j]);
    started ? ctx.lineTo(p.x,p.y) : ctx.moveTo(p.x,p.y);
    started=true;
  }
  ctx.strokeStyle=css('--signal'); ctx.lineWidth=2.4;
  ctx.lineJoin='round'; ctx.stroke();
  ctx.fillStyle=css('--muted');
  ctx.font='11px "IBM Plex Mono",ui-monospace,monospace';
  const corner=(i,j)=>project(i,j,z[i][j]);
  const c00=corner(0,0), c0n=corner(0,years.length-1);
  const cn0=corner(ages.length-1,0), cnn=corner(ages.length-1,years.length-1);
  const tag=(p,t)=>{const m=ctx.measureText(t).width;
    ctx.fillText(t, Math.max(4,Math.min(w-m-4,p.x-m/2)), Math.max(12,Math.min(h-4,p.y-9)));};
  tag(c00,'age 0 / '+years[0]); tag(c0n,'age 0 / '+years[years.length-1]);
  tag(cn0,'age '+ages[ages.length-1]+' / '+years[0]);
  tag(cnn,'age '+ages[ages.length-1]+' / '+years[years.length-1]);
}
function press(id,a,e){document.getElementById(id).addEventListener('click',()=>{
  az=a;el=e;document.querySelectorAll('.bar button[data-view]').forEach(b=>
    b.setAttribute('aria-pressed', b.id===id?'true':'false'));draw();});}
cv.addEventListener('pointerdown',e=>{dragging=true;px=e.clientX;py=e.clientY;
  cv.setPointerCapture(e.pointerId);});
cv.addEventListener('pointermove',e=>{ if(!dragging) return;
  az-=(e.clientX-px)*0.008; el=Math.max(0.08,Math.min(1.45,el+(e.clientY-py)*0.006));
  px=e.clientX;py=e.clientY;draw();});
cv.addEventListener('pointerup',()=>{dragging=false;});
press('v-iso',-0.62,0.72); press('v-cliff',-1.30,1.15); press('v-top',0,0.06);
addEventListener('resize',draw);
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',()=>{
  ramp.length=0;['--r1','--r2','--r3','--r4','--r5','--r6','--r7'].forEach(v=>
    ramp.push(css(v)));draw();});
draw();
"""


def heatmap(z: list[list[float]], rel: list[int]) -> str:
    """The flat companion: same grid, values readable, cliff marked."""
    head = "".join(f"<th>{y}</th>" for y in YEARS)
    body = ""
    for i, a in enumerate(AGES):
        cells = ""
        for j, y in enumerate(YEARS):
            cls = ' class="cliff"' if y == rel[i] else ""
            cells += f"<td{cls}>{z[i][j]:,.0f}</td>"
        body += f"<tr><th>age {a}</th>{cells}</tr>"
    return (f'<div class="tblwrap"><table><thead><tr><th>Asset age</th>{head}</tr>'
            f"</thead><tbody>{body}</tbody></table></div>")


def build() -> str:
    z, rel = grid()
    flat = [v for row in z for v in row]
    lo, hi = min(flat), max(flat)
    best = max(((v, i, j) for i, row in enumerate(z) for j, v in enumerate(row)))
    data = json.dumps({"ages": AGES, "years": YEARS, "z": [[round(v, 1) for v in r]
                                                           for r in z], "rel": rel})
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Fleet Surface</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}</style></head><body><main class="page">
<span class="eyebrow">Investment timing &middot; the whole fleet at once</span>
<h1>Every plant, every commitment year, one surface</h1>
<p>Each of the earlier charts fixes an asset and varies the year, or fixes a
year and varies an asset. This varies both. The height is what committing in
that year is worth, in euros per tonne of annual capacity, for a plant that
many years into its furnace campaign.</p>
<p><strong>The diagonal edge is the reline.</strong> It is drawn in rust, and it
sweeps across the fleet because an older plant relines sooner. Commit on the
near side and the rebuild is avoided; step over it and the value falls away.
<strong>The high ground runs along the near side of that edge</strong> &mdash;
which is the whole of Finding 03 in one picture, for every plant at once rather
than one at a time.</p>
<div class="card">
  <div class="bar">
    <button id="v-iso" data-view aria-pressed="true">Isometric</button>
    <button id="v-cliff" data-view aria-pressed="false">Side on</button>
    <button id="v-top" data-view aria-pressed="false">Plan</button>
    <span class="hint">drag to rotate</span>
  </div>
  <canvas id="surf" role="img"
    aria-label="Three-dimensional surface of net present value over commitment
    year and asset age. A diagonal cliff marks the reline year; the highest
    values run along its near side."></canvas>
  <div class="scale"><span>{lo:,.0f}</span><span class="ramp">
    <i style="background:var(--r1)"></i><i style="background:var(--r2)"></i>
    <i style="background:var(--r3)"></i><i style="background:var(--r4)"></i>
    <i style="background:var(--r5)"></i><i style="background:var(--r6)"></i>
    <i style="background:var(--r7)"></i></span><span>{hi:,.0f} EUR/t</span></div>
</div>
<h2>The same grid, flat, with the numbers</h2>
<p>Use this one to read values. The 3D view is for the shape; a rotated surface
is a poor instrument for looking anything up. The rust edge marks each plant's
reline year. The best cell on the whole surface is
<strong>age {best[1]}, committing {YEARS[best[2]]}, at
&euro;{best[0]:,.0f}/t</strong>.</p>
{heatmap(z, rel)}
<footer><p>Load factor 0.85, hydrogen at &euro;2.60/kg, resale permitted,
nominal prices, lump support. Every figure is conditional on those. The reline
timing rests on calibrated cost-side parameters &mdash; see
<code>CALIBRATION.md</code>.</p></footer>
</main>
<script>window.__SURF__={data};</script>
<script>{JS}</script>
</body></html>"""


def main() -> int:
    """Write surface.html."""
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build())
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
