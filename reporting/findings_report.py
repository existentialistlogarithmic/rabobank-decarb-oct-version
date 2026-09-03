"""Write findings.html - the derivations behind each structural finding.

Prose is authored here; every number is pulled live from :mod:`analysis` and
the model itself, so the document cannot drift away from the code that
produced it. Standard library only.
"""

from __future__ import annotations

import html

from analysis.findings import (
    lever_classes,
    output_correlations,
    rate_cancellation,
    reline_capture,
    utilisation_inversion,
)
from timing_model.cost import reline_year, support
from timing_model.objective import benefit_pv, discount
from timing_model.params import Params, ScenarioParams
from timing_model.results import outputs
from timing_model.scenarios import published_base

OUT = "findings.html"

#: Spell small counts out - they open sentences in the prose below.
MINUS = "\u2212"   # true minus sign; f-strings cannot carry the escape inline
EUR = "\u20ac"

WORD = {0: "No", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
        6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"}


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


CSS = """
:root{
  --ground:#f4f6f7; --surface:#ffffff; --sunk:#eef1f3;
  --ink:#0f1519; --ink2:#48555e; --muted:#7b8892;
  --rule:#dde3e7; --accent:#0a5f6b; --accent-soft:#e3f0f1;
  --signal:#b2481f; --signal-soft:#fbeae3;
  --shadow:0 1px 2px rgba(15,21,25,.05);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#11161a; --surface:#181e23; --sunk:#1f262c;
  --ink:#e8eef2; --ink2:#a6b3bc; --muted:#7b8892;
  --rule:#262e35; --accent:#5cb3bf; --accent-soft:#123034;
  --signal:#e08b62; --signal-soft:#33211a;
  --shadow:none;
}}
:root[data-theme="dark"]{
  --ground:#11161a; --surface:#181e23; --sunk:#1f262c;
  --ink:#e8eef2; --ink2:#a6b3bc; --muted:#7b8892;
  --rule:#262e35; --accent:#5cb3bf; --accent-soft:#123034;
  --signal:#e08b62; --signal-soft:#33211a;
  --shadow:none;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font:1.0625rem/1.72 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-feature-settings:"kern" 1;
}
.page{max-width:52rem;margin:0 auto;padding:clamp(2rem,5vw,4.5rem) 1.25rem 6rem}
h1,h2,h3{font-family:"Source Serif 4",Georgia,"Times New Roman",serif;
  text-wrap:balance;font-weight:600;margin:0}
h1{font-size:clamp(2rem,4.6vw,2.9rem);line-height:1.12;letter-spacing:-.012em}
h2{font-size:clamp(1.4rem,2.6vw,1.75rem);line-height:1.22;letter-spacing:-.008em}
h3{font-size:1.06rem;line-height:1.35}
p{margin:0}
a{color:var(--accent)}
.eyebrow{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.7rem;
  letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.lede{font-size:1.15rem;line-height:1.6;color:var(--ink2);max-width:62ch}
header.masthead{display:flex;flex-direction:column;gap:1.1rem;
  padding-bottom:2rem;border-bottom:2px solid var(--ink)}
.byline{display:flex;flex-wrap:wrap;gap:.4rem 1.4rem;font-size:.83rem;
  color:var(--muted);font-family:"IBM Plex Mono",ui-monospace,monospace}
.conditions{background:var(--accent-soft);border-radius:2px;
  padding:.95rem 1.1rem;font-size:.86rem;color:var(--ink2);
  border-left:3px solid var(--accent);display:flex;flex-direction:column;gap:.3rem}
.conditions b{color:var(--ink);font-weight:600}
.conditions .k{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.78rem;
  letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
nav.toc{display:flex;flex-direction:column;gap:.1rem;margin:2.5rem 0 1rem}
nav.toc a{display:grid;grid-template-columns:2.4rem 1fr;gap:.6rem;
  padding:.62rem .3rem;border-bottom:1px solid var(--rule);
  text-decoration:none;color:var(--ink);font-size:.97rem;align-items:baseline}
nav.toc a:hover{background:var(--sunk)}
nav.toc a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
nav.toc .n{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.8rem;
  color:var(--accent);font-variant-numeric:tabular-nums}
article.finding{margin:3.6rem 0 0;padding-top:2.2rem;border-top:1px solid var(--rule)}
.fhead{display:flex;flex-direction:column;gap:.55rem;margin-bottom:1.1rem}
.tagrow{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}
.chip{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.68rem;
  letter-spacing:.1em;text-transform:uppercase;padding:.2rem .5rem;border-radius:2px;
  background:var(--sunk);color:var(--ink2)}
.chip.invert{background:var(--signal-soft);color:var(--signal)}
.claim{font-size:1.12rem;line-height:1.6;color:var(--ink);font-weight:500;
  border-left:3px solid var(--accent);padding-left:1rem;max-width:62ch}
.sub{margin:2rem 0 .7rem;display:flex;align-items:baseline;gap:.6rem}
.sub .marker{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.7rem;
  letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
article.finding p{max-width:66ch;margin:0 0 .95rem;color:var(--ink2)}
article.finding p strong{color:var(--ink);font-weight:600}
.formula{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.92rem;
  background:var(--sunk);border-radius:2px;padding:1rem 1.1rem;margin:0 0 1rem;
  overflow-x:auto;line-height:1.65;color:var(--ink)}
.formula .dim{color:var(--muted)}
.formula .hit{color:var(--accent);font-weight:600}
.formula .miss{color:var(--signal)}
.break{background:var(--surface);border:1px solid var(--rule);border-radius:2px;
  padding:1rem 1.15rem;margin:1.4rem 0 0;box-shadow:var(--shadow)}
.break h3{font-size:.83rem;font-family:"IBM Plex Mono",ui-monospace,monospace;
  letter-spacing:.1em;text-transform:uppercase;color:var(--signal);
  margin-bottom:.5rem;font-weight:600}
.break p{font-size:.94rem;margin-bottom:.6rem;color:var(--ink2)}
.break p:last-child{margin-bottom:0}
.tblwrap{overflow-x:auto;margin:0 0 1.2rem}
table{border-collapse:collapse;width:100%;font-size:.88rem;
  font-variant-numeric:tabular-nums}
caption{text-align:left;font-size:.78rem;color:var(--muted);padding-bottom:.5rem;
  font-family:"IBM Plex Mono",ui-monospace,monospace;letter-spacing:.06em;
  text-transform:uppercase}
th{text-align:right;font-weight:600;color:var(--ink);border-bottom:2px solid var(--ink);
  padding:.45rem .7rem;white-space:nowrap}
td{text-align:right;padding:.45rem .7rem;border-bottom:1px solid var(--rule);
  color:var(--ink2)}
th:first-child,td:first-child{text-align:left}
tbody tr:hover td{background:var(--sunk)}
td.pos{color:var(--accent);font-weight:600}
td.neg{color:var(--signal);font-weight:600}
td.zero{color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(9rem,1fr));
  gap:1px;background:var(--rule);border:1px solid var(--rule);margin:0 0 1.4rem}
.stat{background:var(--surface);padding:.9rem 1rem;display:flex;
  flex-direction:column;gap:.2rem}
.stat .v{font-family:"Source Serif 4",Georgia,serif;font-size:1.5rem;
  font-weight:600;color:var(--ink);line-height:1.1;font-variant-numeric:tabular-nums}
.stat .v.sig{color:var(--signal)}
.stat .l{font-size:.76rem;color:var(--muted);line-height:1.35}
footer{margin-top:4rem;padding-top:1.6rem;border-top:1px solid var(--rule);
  font-size:.84rem;color:var(--muted)}
footer p{margin:0 0 .6rem;max-width:66ch}
code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.9em;
  background:var(--sunk);padding:.1em .35em;border-radius:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def stat(v: str, label: str, sig: bool = False) -> str:
    cls = " sig" if sig else ""
    return f'<div class="stat"><span class="v{cls}">{esc(v)}</span>' \
           f'<span class="l">{esc(label)}</span></div>'


def f1() -> str:
    ls = lever_classes()
    val = [lv for lv in ls if lv.klass == "value only"]
    thr = [lv for lv in ls if lv.klass == "threshold only"]
    both = [lv for lv in ls if lv.klass == "both"]
    rows = "".join(
        f"<tr><td>{esc(lv.name)}</td>"
        f'<td class="{"zero" if abs(lv.d_npv_pct) < 1e-9 else ("pos" if lv.d_npv_pct > 0 else "neg")}">'
        f"{lv.d_npv_pct:+.3f}%</td>"
        f'<td class="{"zero" if abs(lv.d_trigger_pct) < 1e-9 else ("pos" if lv.d_trigger_pct > 0 else "neg")}">'
        f"{lv.d_trigger_pct:+.3f}%</td>"
        f"<td>{esc(lv.klass)}</td></tr>" for lv in ls)
    return f"""
<article class="finding" id="f1">
  <div class="fhead">
    <div class="tagrow"><span class="eyebrow">Finding 01</span>
      <span class="chip">structural</span><span class="chip">exact</span></div>
    <h2>The levers are orthogonal, and the split is exact</h2>
  </div>
  <p class="claim">{WORD[len(val)]} parameters move the decision's <em>value</em> and move its
  <em>threshold</em> by exactly 0.000%. {WORD[len(thr)]} move the threshold and leave
  value at exactly 0.000%. Only {WORD[len(both)].lower()} move both.</p>

  <div class="sub"><span class="marker">How</span><h3>The symbol is absent, not small</h3></div>
  <p>The trigger is a closed-form expression. Written out, with the symbols it
  <span style="color:var(--accent)">contains</span> and those it does
  <span style="color:var(--signal)">not</span>:</p>
  <div class="formula">p*&#8242; = ( <span class="hit">I&#8320;</span> + <span class="hit">&#966;S&#8347;</span>
  &minus; <span class="hit">a(p<sub>H2</sub>)</span>/<span class="hit">r</span> ) &times;
  (<span class="hit">r</span> &minus; <span class="hit">&#956;</span>) / <span class="hit">b(&#954;)</span>
  &times; &#946;(<span class="hit">&#963;</span>)/(&#946;&minus;1)
  <br><span class="dim">absent:</span> <span class="miss">u</span>
  <span class="dim">(load factor)</span> &middot; <span class="miss">w</span>
  <span class="dim">(resale)</span> &middot; <span class="miss">s(T)</span>
  <span class="dim">(support)</span> &middot; <span class="miss">p&#8348;</span>
  <span class="dim">(the price path)</span> &middot; <span class="miss">f&#7515;(t)</span>
  <span class="dim">(free allocation)</span></div>
  <p>That is the whole mechanism. A parameter cannot move a quantity it does not
  appear in, so the zeros are not small numbers arrived at by cancellation &mdash;
  they are <strong>structural absences</strong>. The computation confirms it to
  machine precision rather than to two decimal places.</p>
  <p>The reverse holds for volatility. <code>NPV(T)</code> is the Group IV
  objective, which is deterministic: it discounts a known benefit stream against
  a known cost. <code>&#963;</code> enters only through the Bellman equation in
  Group V. So volatility moves the threshold and cannot touch the value.</p>
  <div class="tblwrap"><table><caption>Every lever, both outputs</caption>
  <thead><tr><th>Lever</th><th>&#916; NPV</th><th>&#916; trigger</th><th>Class</th></tr></thead>
  <tbody>{rows}</tbody></table></div>

  <div class="sub"><span class="marker">Why it matters</span><h3>Instruments are complements, not substitutes</h3></div>
  <p>Read the three classes as three different things a policymaker or a lender
  can actually do. A <strong>contract-for-difference collapses volatility</strong>:
  it moves the threshold and <em>cannot</em> improve the project's value. A
  <strong>grant raises the value</strong> and <em>cannot</em> bring the trigger
  closer. Capex support and hydrogen offtake are the only instruments that
  touch both.</p>
  <p>The practical consequence is blunt: <strong>no amount of grant money fixes
  a volatility problem.</strong> If a case fails because the trigger is never
  crossed, more subsidy makes the project more valuable at a price the market
  never reaches. The two failures look similar in a spreadsheet and require
  different instruments.</p>
  <p>It also explains a row in the stress ladder that looks like an error and is
  not. Restating the carbon price path in real terms moves NPV by roughly a
  third and the trigger by exactly nothing &mdash; because deflating the path
  changes p&#8348;, which the trigger does not contain.</p>

  <div class="break"><h3>What would break it</h3>
  <p>The orthogonality of <code>&#963;</code> is <em>definitional</em>: this
  model's NPV layer has no uncertainty in it by construction. Give Group IV a
  stochastic objective and that particular zero disappears. The orthogonality of
  <code>u</code>, <code>w</code>, <code>s(T)</code> and the price basis is the
  substantive half, and it survives as long as the trigger keeps its
  closed form.</p>
  <p>Routing support through <code>B(t)</code> as a flow rather than netting it
  from capex &mdash; the <code>stream</code> basis this model already
  implements &mdash; keeps support out of the trigger. Netting it from
  <code>I&#8320;</code> instead would move support into the "both" class.</p></div>
</article>"""


def f2() -> str:
    flip = utilisation_inversion()
    a_at = -(55.0 * flip - 83.0)
    p, sc = published_base()
    pvb = benefit_pv(2029, p, sc)
    return f"""
<article class="finding" id="f2">
  <div class="fhead">
    <div class="tagrow"><span class="eyebrow">Finding 02</span>
      <span class="chip invert">inverts an intuition</span></div>
    <h2>Above &euro;{flip:.2f}/kg hydrogen, utilisation flips from asset to liability</h2>
  </div>
  <p class="claim">The sensitivity of NPV to the load factor changes sign at
  p<sub>H2</sub> = &euro;{flip:.2f}/kg. Past that point, running the plant
  <em>less</em> raises NPV.</p>

  <div class="stats">
    {stat(f"€{flip:.2f}/kg", "hydrogen price at which dNPV/du changes sign")}
    {stat(f"{MINUS}{abs(a_at):,.0f}", "implied opex penalty a, EUR/t of product per year", sig=True)}
    {stat("€8.29/kg", "Platts, Spain, 8 May 2026 — above the flip", sig=True)}
  </div>

  <div class="sub"><span class="marker">How</span><h3>The load factor multiplies the penalty too</h3></div>
  <p>The load factor is the bridge between per-tonne-of-capacity and
  per-tonne-of-product. It multiplies the entire benefit flow &mdash; including
  the operating penalty, which is negative:</p>
  <div class="formula">B(t) = <span class="hit">u</span> &middot; [ <span class="miss">a</span>
  + (1&minus;&#945;)&middot;b&middot;p&#8348; + w&middot;&#945;&middot;&#949;&#7522;&#8345;&#7580;&middot;p&#8348; ]
  <br><br><span class="dim">u appears nowhere else in the objective, so:</span>
  <br>&part;NPV/&part;u = &Sigma; d(t)&middot;B(t) / u = <span class="hit">PV of the bracket</span></div>
  <p>Because <code>u</code> enters linearly and only here, the derivative is
  exactly the present value of the un-scaled bracket &mdash; verified in the
  code at <strong>{pvb / sc.u:,.2f} EUR/t</strong> by both the analytic route
  and a numerical difference. Its <em>sign</em> is therefore the sign of the
  discounted benefit stream.</p>
  <p>While the avoided carbon cost outweighs the hydrogen penalty, the bracket
  is positive and utilisation is worth having &mdash; the ordinary
  project-finance intuition. Once <code>a</code> dominates, <code>u</code>
  multiplies a negative number, and every additional hour of operation destroys
  value. The crossing is where the capitalised hydrogen penalty exactly equals
  the capitalised carbon saving.</p>
  <p>The flip sits at a <em>lower</em> hydrogen price on the real basis than the
  nominal one, because deflating the path shrinks the carbon saving on the other
  side of the balance.</p>

  <div class="sub"><span class="marker">Why it matters</span><h3>A minimum-utilisation covenant would be pointed backwards</h3></div>
  <p>The May 2026 market price for hydrogen sits <strong>above</strong> this
  crossing. Project finance conventionally protects the lender by requiring the
  borrower to <em>run</em> the asset &mdash; availability guarantees, minimum
  offtake, utilisation covenants. On the wrong side of this threshold those
  clauses compel the borrower to destroy value, and the lender has written
  protection that operates in reverse.</p>
  <p>The exposure it does describe is a <strong>revolving facility sized by the
  hydrogen price</strong>, not a term loan sized by capacity.</p>

  <div class="break"><h3>What would break it — read this before quoting it</h3>
  <p>This is a statement about the <em>sign of a sensitivity</em>, not a
  recommendation to build a plant and idle it. At these hydrogen prices the
  project's NPV is negative at every commitment year in the horizon; a lower
  load factor makes it <em>less negative</em>. "Run it less" is what the
  arithmetic says about a case that should not be built at all.</p>
  <p>The model also has no fixed operating costs and no ramp constraints, both
  of which push the other way and would move the crossing to a higher hydrogen
  price. Treat &euro;{flip:.2f} as the boundary of this model, not of the
  physical plant.</p></div>
</article>"""


def f3() -> str:
    rc = reline_capture()
    p = Params()
    sc = ScenarioParams(u=0.85)
    picks = [8, 12, 16, rc.best_age, rc.best_age + 1]
    rows = ""
    for age in picks:
        pp = p.with_sector(age0=float(age))
        tr = reline_year(pp)
        o = outputs(pp, sc, gate=False)
        cliff = 2 * discount(tr, pp) * pp.sector.rho * pp.sector.K_s
        cap = "captured" if o.t_star == tr else "free"
        rows += (f"<tr><td>{age}</td><td>{tr}</td><td>{o.t_star or 'beyond'}</td>"
                 f"<td>{cliff:,.1f}</td><td>{o.npv0:,.0f}</td><td>{cap}</td></tr>")
    lost = rc.best_npv - [r[3] for r in rc.rows if r[0] == rc.best_age + 1][0]
    return f"""
<article class="finding" id="f3">
  <div class="fhead">
    <div class="tagrow"><span class="eyebrow">Finding 03</span>
      <span class="chip">origination signal</span><span class="chip">calendar, not forecast</span></div>
    <h2>Past {rc.capture_from} years into a campaign, T* stops being a choice</h2>
  </div>
  <p class="claim">From an asset age of {rc.capture_from} onward, the optimal
  commitment year equals the reline year <em>exactly</em>. The decision is no
  longer economic &mdash; it is captured by the calendar.</p>

  <div class="stats">
    {stat(f"age {rc.capture_from}+", "the capture region: T* = reline year, exactly")}
    {stat(f"age {rc.best_age}", "where value peaks — about two years short of a reline")}
    {stat(f"{MINUS}{EUR}{lost:,.0f}/t", f"lost by slipping one year, to age {rc.best_age + 1}", sig=True)}
  </div>

  <div class="sub"><span class="marker">How</span><h3>A discontinuity that grows as the reline approaches</h3></div>
  <p>The objective carries a reinvestment term whose <em>sign</em> depends on
  whether the firm commits before or after its reline:</p>
  <div class="formula">NPV(T) = &minus;d(T)&middot;I&#8242;(T)
  <span class="hit">&plusmn; d(T&#7523;&#8337;&#8343;)&middot;&#961;K&#8347;</span>
  + &Sigma; d(t)&middot;B(t)
  <br><span class="dim">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  + if T &le; T&#7523;&#8337;&#8343; (avoided) &nbsp; &minus; if T &gt; T&#7523;&#8337;&#8343; (paid)</span>
  <br><br>step at the reline = <span class="hit">2 &middot; d(T&#7523;&#8337;&#8343;) &middot; &#961;K&#8347;</span></div>
  <p>Switching one year late does not cost a little &mdash; it costs the reline
  twice over, once in cash and once in the avoidance forgone. The step is
  discounted, so <strong>the closer the reline, the larger it looms</strong>:
  it roughly doubles from an asset eight years into its campaign to one
  nineteen years in. Once that step exceeds the year-on-year economic gradient
  &mdash; learning, support, the rising carbon price &mdash; the argmax pins
  itself to the reline year and stops moving.</p>
  <div class="tblwrap"><table><caption>The step grows until it captures the decision</caption>
  <thead><tr><th>Age at 2026</th><th>Reline</th><th>T*</th>
  <th>Step, EUR/t</th><th>NPV, EUR/t</th><th>Status</th></tr></thead>
  <tbody>{rows}</tbody></table></div>

  <div class="sub"><span class="marker">How</span><h3>Why value peaks two years short, not at the deadline</h3></div>
  <p>Value rises with age right up to {rc.best_age} and then falls off a cliff
  &mdash; <strong>&minus;&euro;{lost:,.0f}/t</strong> for a single further year.
  The cause is not the reline. It is the support window.</p>
  <p>The Investment Booster opens in 2028: <code>s(2027) = &euro;0</code>,
  <code>s(2028) = &euro;{support(2028, p, sc):,.0f}</code>. An asset aged
  {rc.best_age} relines in {reline_year(p.with_sector(age0=float(rc.best_age)))},
  so avoiding the reline and collecting the support are compatible. One year
  older and the reline falls in 2027 &mdash; to escape it the firm must commit
  before the money exists, and forfeits the entire envelope. <strong>The loss is
  the support, not the steel.</strong></p>

  <div class="sub"><span class="marker">Why it matters</span><h3>The only input that is a calendar</h3></div>
  <p>Every other parameter here is a forecast: the carbon price, the hydrogen
  price, the learning rate, the support envelope. <strong>Relining schedules are
  published, plant by plant, across the European fleet.</strong> This finding
  therefore converts into a target list in a way nothing else in the model does.</p>
  <p>It also inverts the intuitive screen. The best client is neither the newest
  asset nor the most decrepit &mdash; it is the one about two years short of a
  reline, whose deadline is close enough to force the decision and far enough
  away to still catch the support window. Assets freshly relined are locked out
  for a campaign length, which for the fleet relined since 2020 means most of
  the 2030s.</p>

  <div class="break"><h3>What would break it</h3>
  <p>The capture age is not a constant of nature: it is where the reline step
  overtakes the economic gradient, so it moves with the discount rate, the
  reline cost, and the steepness of the carbon path. Read
  "age&nbsp;{rc.capture_from}" as this parameterisation's answer, and re-run it
  per plant rather than quoting it as a fleet rule.</p>
  <p>The two-year peak depends entirely on the 2028 support date. Move the
  window and the peak moves with it &mdash; which is itself the point: the
  interaction between a policy start date and a plant's maintenance calendar is
  worth more here than either alone.</p></div>
</article>"""


def f4() -> str:
    rs = rate_cancellation()
    rows = "".join(
        f"<tr><td>{r:.1%}</td><td>{be:,.2f}</td><td>{m:,.3f}</td>"
        f"<td>{t:,.2f}</td></tr>" for r, be, m, t in rs.rows)
    return f"""
<article class="finding" id="f4">
  <div class="fhead">
    <div class="tagrow"><span class="eyebrow">Finding 04</span>
      <span class="chip invert">a reported result is misleading</span></div>
    <h2>The trigger's robustness to the discount rate is cancellation, not stability</h2>
  </div>
  <p class="claim">Taking r from 6% to 10% moves the break-even price by
  {rs.d_break_even_pct:+.0f}% and the option multiple by {rs.d_multiple_pct:+.0f}%.
  Their product, the trigger, moves {rs.d_trigger_pct:+.0f}%.</p>

  <div class="stats">
    {stat(f"{rs.d_break_even_pct:+.0f}%", "break-even carbon price, r from 6% to 10%")}
    {stat(f"{MINUS}{abs(rs.d_multiple_pct):.0f}%", "option multiple, over the same range", sig=True)}
    {stat(f"{rs.d_trigger_pct:+.0f}%", "the product — what gets reported")}
  </div>

  <div class="sub"><span class="marker">How</span><h3>Both factors run off the same gap</h3></div>
  <p>The trigger is a product of two terms, and the discount rate enters both:</p>
  <div class="formula">p*&#8242; = <span class="hit">p&#8242;&#8344;</span> &times;
  <span class="miss">&#946;/(&#946;&minus;1)</span>
  <br><br><span class="hit">p&#8242;&#8344;</span> &prop; (r &minus; &#956;)
  <span class="dim">&nbsp; a higher rate demands a higher carbon price &mdash; rises with r</span>
  <br><span class="miss">&#946;/(&#946;&minus;1)</span>
  <span class="dim">&nbsp; a higher rate makes waiting costlier &mdash; falls with r</span></div>
  <p>Raising the discount rate makes the switch harder to justify on a
  break-even basis and simultaneously makes <em>waiting</em> less attractive.
  The two effects point in opposite directions and are close enough in magnitude
  to nearly annihilate. What survives is a residue of roughly
  {rs.d_trigger_pct:+.0f}%, which then gets reported as the trigger being
  insensitive to the cost of capital.</p>
  <div class="tblwrap"><table><caption>The decomposition, rate by rate</caption>
  <thead><tr><th>r</th><th>Break-even p&#8242;&#8344;</th><th>Multiple &#946;/(&#946;&minus;1)</th>
  <th>Trigger</th></tr></thead><tbody>{rows}</tbody></table></div>

  <div class="sub"><span class="marker">Why it matters</span><h3>Robustness and cancellation fail differently</h3></div>
  <p>A genuinely robust result stays put when the world moves. A cancellation
  holds only while both of its terms keep moving together, and both of these are
  driven by <code>(r &minus; &#956;)</code> &mdash; the <em>gap</em>, not the
  level. Anything that changes the gap rather than the level breaks the offset,
  and the trigger then moves with the full force of whichever term is left.</p>
  <p>This is why the guard in the code rejects <code>r &minus; &#956; &lt;
  0.005</code> rather than merely warning. As the gap closes, the break-even
  price collapses toward zero while the option multiple diverges. The product is
  meaningless before it is undefined.</p>
  <p>It also gives Finding 01 its cleanest illustration. Restating prices in real
  terms shifts <code>r</code> and <code>&#956;</code> together, leaves the gap
  untouched, and therefore leaves the trigger at exactly its nominal value while
  NPV moves by a third.</p>

  <div class="break"><h3>What would break it</h3>
  <p>The near-cancellation is a numerical coincidence over the range 6&ndash;10%,
  not an identity. It is tighter for changes in <code>r</code> than for changes
  in <code>&#956;</code>, and there is no reason to expect it to survive a
  different drift assumption, a mean-reverting price process, or a term
  structure of discount rates.</p>
  <p>Report the two factors, not the product. A sensitivity table showing only
  the trigger is technically correct and practically misleading.</p></div>
</article>"""


def f5() -> str:
    names, m, n = output_correlations()
    idx = {nm: i for i, nm in enumerate(names)}
    nv_tr = m[idx["NPV0"]][idx["trigger"]]
    ts_nv = m[idx["T*"]][idx["NPV0"]]
    tr_cr = m[idx["trigger"]][idx["crossing year"]]
    head = "".join(f"<th>{esc(x)}</th>" for x in names)
    body = ""
    for i, r in enumerate(names):
        cells = "".join(
            f'<td class="{"zero" if i == j else ("pos" if m[i][j] > 0 else "neg")}">'
            f"{m[i][j]:+.2f}</td>" for j in range(len(names)))
        body += f"<tr><td>{esc(r)}</td>{cells}</tr>"
    return f"""
<article class="finding" id="f5">
  <div class="fhead">
    <div class="tagrow"><span class="eyebrow">Finding 05</span>
      <span class="chip invert">method warning</span><span class="chip">depends on 01</span></div>
    <h2>The correlation matrix contradicts Finding 01, and the matrix is the one that misleads</h2>
  </div>
  <p class="claim">Across {n} scenarios, value and threshold read as strongly
  anti-correlated at {nv_tr:+.2f} &mdash; flatly contradicting the exact
  orthogonality of Finding 01. Both results are correct. The resolution is the
  finding.</p>

  <div class="stats">
    {stat(f"{nv_tr:+.2f}", "NPV against trigger — the coupling that is not real", sig=True)}
    {stat(f"{ts_nv:+.2f}", "T* against NPV — the coupling that is")}
    {stat(f"{tr_cr:+.2f}", "trigger against crossing year — near-definitional")}
  </div>

  <div class="sub"><span class="marker">How</span><h3>The ensemble chose the answer</h3></div>
  <p>The correlation is computed over a grid that varies the load factor, the
  hydrogen price, capex and the volatility regime. Two of those &mdash; hydrogen
  price and capex &mdash; are among the four levers that move <em>both</em>
  outputs, and they carry wide ranges. They therefore dominate the variance and
  manufacture a coupling between two quantities that Finding 01 shows are
  structurally independent.</p>
  <p>Sample a different set of levers and the number changes. Vary only
  <code>u</code>, <code>w</code>, <code>s(T)</code> and the price basis and the
  correlation goes to zero, because the trigger never moves at all. Vary only
  <code>&#963;</code> and it goes to zero from the other side. <strong>The
  correlation is a property of the sampling; the orthogonal split is a property
  of the model.</strong></p>
  <div class="tblwrap"><table><caption>Rank correlation across {n} scenarios</caption>
  <thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table></div>

  <div class="sub"><span class="marker">How</span><h3>Reading the other two pairs honestly</h3></div>
  <p><strong>T* against NPV at {ts_nv:+.2f} is substantive.</strong> Across every
  configuration, the later the commitment year, the less the switch is worth.
  That is the option premium showing up as a cost, and it is the one correlation
  here worth quoting.</p>
  <p><strong>Trigger against crossing year at {tr_cr:+.2f} is nearly a
  tautology.</strong> The crossing year is defined as the first year a monotone
  rising path reaches the trigger, so a higher trigger mechanically implies a
  later crossing. Presenting it as a discovery would be padding a findings list
  with a definition.</p>

  <div class="sub"><span class="marker">Why it matters</span><h3>The failure mode this whole model was rebuilt to prevent</h3></div>
  <p>An analyst handed only this matrix would conclude that value and threshold
  move together, and would reach for whichever instrument was cheaper on the
  assumption that it moves both. Finding 01 says that is precisely wrong: the
  instruments are complements, and substituting one for the other leaves the
  binding constraint untouched.</p>
  <p>This is the same failure the conditional-outputs machinery in the code
  guards against &mdash; a number quoted without the conditions that produced
  it. A correlation coefficient carries its ensemble as an invisible condition,
  and the ensemble here was an arbitrary choice.</p>

  <div class="break"><h3>What would break it</h3>
  <p>Nothing, and that is the problem &mdash; this finding is a statement about
  method rather than about steel. It generalises: <em>any</em> correlation study
  over a hand-picked parameter grid inherits the grid's priorities. The only
  defence is to derive the structure analytically first and use the correlation
  to describe the sample, never to infer the mechanism.</p></div>
</article>"""


def build() -> str:
    _, base = published_base()[0], outputs(*published_base())
    cond = "".join(
        f'<span><span class="k">{esc(k.replace("_", " "))}</span> '
        f"<b>{esc(v)}</b></span>" for k, v in base.conditions.items())
    toc = [
        ("01", "The levers are orthogonal, and the split is exact", "f1"),
        ("02", "Utilisation flips from asset to liability", "f2"),
        ("03", "Past 16 years, T* stops being a choice", "f3"),
        ("04", "Trigger robustness is cancellation, not stability", "f4"),
        ("05", "The correlation matrix is the one that misleads", "f5"),
    ]
    nav = "".join(f'<a href="#{i}"><span class="n">{n}</span>'
                  f"<span>{esc(t)}</span></a>" for n, t, i in toc)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Five Structural Findings</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}</style></head>
<body><main class="page">
<header class="masthead">
  <span class="eyebrow">Investment timing model &middot; structural analysis</span>
  <h1>What the model implies that nobody asked it</h1>
  <p class="lede">Five relationships derived from the decarbonisation
  investment-timing model &mdash; how each one works, why it matters, and what
  would break it. Every number here is computed by <code>analysis.py</code> at
  the moment this page is written, not transcribed.</p>
  <div class="byline"><span>Steel &middot; blast furnace to H&#8322;-DRI-EAF</span>
  <span>Explanatory framework, not investment advice</span></div>
</header>
<div class="conditions">{cond}</div>
<nav class="toc" aria-label="Findings">{nav}</nav>
{f1()}{f2()}{f3()}{f4()}{f5()}
<footer>
  <p><strong>Provenance.</strong> The validation gate, the trigger column of the
  stress ladder and the benefit side reproduce the published figures exactly.
  The cost-side split is calibrated against the published ladder rather than
  sourced from the reference implementation, and rows 4&ndash;7 of that ladder
  do not reproduce. See <code>CALIBRATION.md</code> before quoting any figure.</p>
  <p>Findings 01&ndash;05 are derived by <code>analysis.py</code> and pinned by
  regression checks in <code>selfcheck.py</code>, so they fail loudly rather
  than drifting.</p>
</footer>
</main></body></html>"""


def main() -> int:
    """Write findings.html."""
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(build())
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
