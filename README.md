# timing_model

Python implementation of the RaboResearch industrial decarbonisation
investment-timing model (real options + NPV), following the v12 restructure
and coding specification.

A steel producer chooses a single year `T` to irreversibly switch from blast
furnace to H2-DRI-EAF. The model maximises `NPV(T)` over the horizon and
separately computes an uncertainty-adjusted carbon-price trigger via a
Dixit–Pindyck option multiple.

## Figure 1, explained from scratch

*The first chart in `charts.html`. If you know nothing about this model, start here.*

### The situation

A European steel producer runs a **blast furnace** — the traditional way of
making steel, which burns coal and emits a lot of CO₂. A cleaner alternative
exists: **H₂-DRI-EAF**, which uses hydrogen instead of coal. It is expensive to
build, currently more expensive to run, and **cannot be undone once built**.

The producer is not asking *whether* to switch. It is asking **when**. Switch
too early and you pay for expensive equipment and miss subsidies that have not
opened yet. Switch too late and you spend years paying a carbon bill you could
have avoided — and you may pay to rebuild a blast furnace you are about to
abandon.

### What the chart shows

- **Horizontal axis — the year the producer commits.** This is the year the
  board signs off and money is committed, not the year the plant starts
  running.
- **Vertical axis — what committing in that year is worth**, in euros per tonne
  of annual capacity, expressed in today's money. Higher is better.

So for every possible commitment year, the chart shows what committing in *that*
year would be worth. The **peak of a line is that line's best year.**

### The four lines

They are **cumulative**: each one adds a correction to the line above it. None
of them is a scenario or a guess — all four are fixes to errors in the
originally published version.

| Line | What it adds | Best year | Peak value |
|---|---|---|---|
| **Blue** — as published | The model as originally published | 2029 | €1,588 |
| **Orange** — + load factor | The original assumed the plant runs 100% of the time. Real blast furnaces run 75–85%. Set to 85%. | 2030 | €1,294 |
| **Green** — + hot metal | A units fix. The EU emissions benchmark is measured per tonne of *molten iron*; we were applying it to *finished steel*. | 2030 | €1,166 |
| **Yellow** — + real vs nominal | We discount future money at 8% *after inflation*, but the carbon price forecast was *before inflation*. Put both on the same basis. | 2031 | €754 |

The bottom line is the most defensible one.

### What it says about timing — two things

**1. The best year is not really a single year.** The top of the curve is almost
flat:

| Commit in | Worth | vs. the best year |
|---|---|---|
| 2028 | €1,573 | −1.0% |
| **2029** | **€1,588** | **best** |
| 2030 | €1,581 | −0.5% |
| 2031 | €1,556 | −2.0% |
| 2032 | €1,520 | −4.3% |

The difference between 2029 and 2030 is **€7 out of €1,588** — half of one
percent. Every input here is a forecast, so a half-percent gap is noise.
Quoting "2029" implies a precision the chart does not support. **The honest
answer is a window: 2028 to 2032.**

**2. But the deadline is real.** One year past the window:

> 2032: €1,520  →  2033: €1,062  —  **a €458 drop, about 30%, in one year**

That is the **reline**. A blast furnace must be stripped and rebuilt roughly
every 20 years; this one is due in 2032. Commit at or before the reline and the
producer never spends that money. Commit after and they have just paid to
rebuild a furnace they are about to shut — a loss taken twice, once in cash and
once in the saving given up.

The drop appears in **all four lines at almost the same size** (€423–458),
because unlike everything else in the model it does not depend on any forecast.
**It is a maintenance date.**

> **The peak is soft; the deadline is hard.** Do not argue about 2029 versus
> 2030. Do not miss 2032.

### One pattern worth noticing

As the corrections are applied, the best year moves 2029 → 2030 → 2030 → 2031.
Two years in total. The value goes €1,588 → €754 — **it more than halves.**

The corrections barely move the date and gut the value. **The date is robust;
the number is not.** If anyone quotes €1,588, that is the figure that will not
survive scrutiny — not the year.

### Before you use this

The reline date is set by cost-side parameters that are **calibrated, not taken
from the reference implementation** — see `CALIBRATION.md`. The *shape* of the
chart is sound, and the reline mechanism is real, but the exact year differs
plant by plant. Relining schedules are published per plant, so this is one
input that can be checked rather than forecast.

## Observed inputs, and the hydrogen floor

`eurostat.py` pulls two real series from Eurostat's open API and caches them, so
the model still runs with no network.

**What real data can and cannot do here.** NPV, the trigger and `T*` are model
*outputs* — no statistical agency publishes them. Official statistics can
replace *inputs*, and two matter:

- **Euro-area HICP** grounds the deflator. Latest: **2.1%/yr**, against the
  model's assumed 2.0% — consistent, so the largest unit correction stands.
- **Industrial electricity prices** (band IE, 20–70 GWh/yr, excluding taxes)
  put a hard floor under the hydrogen price, because electrolysis is mostly a
  way of buying electricity.

At roughly 55 kWh per kg of hydrogen, the electricity bill *alone* — before
electrolyser capex, compression, storage or transport — comes to:

| | Sweden | France | Spain | Poland | Netherlands | Germany | Italy |
|---|---|---|---|---|---|---|---|
| €/kWh | 0.072 | 0.078 | 0.099 | 0.106 | 0.113 | 0.136 | 0.146 |
| **€/kg floor** | **3.94** | **4.30** | **5.45** | **5.82** | **6.24** | **7.50** | **8.05** |

**The base case assumes €2.60/kg. That is below the electricity bill alone, in
every European steel-producing country** — 1.5× under even in Sweden, the
cheapest. This is not a forecast disagreement; it is an arithmetic floor from
official statistics, and it independently corroborates the €8.29/kg market
assessment as being in the right region.

Two inputs **cannot** be sourced from open data and need a market-data
terminal: the EUA price series (which sets the price path, drift `mu` and
volatility `sigma`) and commercial hydrogen assessments.

## The article

`article.py` writes **`article.html`** — the finished piece, roughly 2,200
words, with all three figures generated from the model and from Eurostat at
write time, so the text cannot drift from the code.

**Thesis:** the base case assumes hydrogen at €2.60/kg, which is below the cost
of the electricity needed to make it in every European steel-producing country.
Replace that assumption with the observed floor and the sector case becomes a
map: a commitment year exists in Sweden and France, is a coin toss in Spain, and
does not exist anywhere else. Where it does exist, the year is 2032 — a reline
date, not an economic optimum.

## Findings

`analysis.py` **derives** these rather than asserting them; each returns the
evidence that produced it, and each is pinned by a check in `selfcheck.py` so it
cannot silently break. `findings_report.py` writes **`findings.html`**, which
explains every one in full — the mechanism, why it matters, and what would break
it — with every number pulled live from the model.

**1. The levers are orthogonal, and the split is exact.** Five parameters move
the decision's *value* and its threshold by exactly 0.000%; two move the
*threshold* and leave value at exactly 0.000%; only four move both. It is
structure, not approximation — the trigger is
`(I0 + phi*S_s - a/r)(r - mu)/b x beta/(beta-1)`, a formula the load factor,
resale switch, support envelope and price basis do not appear in. So a CfD moves
the threshold and *cannot* improve value; a grant moves value and *cannot* bring
the trigger closer. **No amount of grant money fixes a volatility problem.**

**2. Utilisation inverts from asset to liability at €7.17/kg hydrogen.**
`dNPV/du` changes sign there — above it, running the plant *less* raises NPV,
because the load factor multiplies a benefit flow that has gone negative. The
May 2026 market price of €8.29/kg is on the wrong side, so a minimum-utilisation
covenant would be pointed backwards. (Read the caveat in `findings.html`: this
is the sign of a sensitivity on a case that is NPV-negative throughout, not
advice to build a plant and idle it.)

**3. Past 16 years into a campaign, `T*` stops being a choice.** From that age
the optimal year equals the reline year *exactly* — the calendar takes the
decision. Value peaks at age 18, two years short of a reline, and the cliff one
year later is the €200 support envelope forfeited by committing before the 2028
window opens, not the steel.

**4. The trigger's robustness to the discount rate is cancellation.** Taking `r`
from 6% to 10% moves the break-even price **+304%** and the option multiple
**−68%**; the product moves **+29%**. Report the two factors, not the product.

**5. The correlation matrix would mislead you.** Across 81 scenarios value and
threshold read as anti-correlated at −0.87, contradicting finding 1. Both are
right: the ensemble varies the two levers that move *both* outputs, so it
manufactures the coupling. The correlation is a property of the sampling; the
orthogonal split is a property of the model.

## Charts

`plots.py` writes a self-contained `charts.html` — theme-aware, hover tooltips,
legends, direct labels and a table view under every chart. No matplotlib, no
pandas: the SVG is generated directly. Four charts on the decision (NPV by year,
price path against trigger, the stress ladder, the volatility ladder) and five
on the findings above.

The categorical palette is validated for colour-vision deficiency in both light
and dark mode. Light mode puts two series below 3:1 against the surface, so
every series is also direct-labelled and every chart carries a table view —
identity is never colour alone.

## The fleet surface

`surface.py` writes `surface.html`: net present value as a surface over **both**
the commitment year and the plant's age, rotatable in the browser. Every other
chart fixes one and varies the other.

Three-dimensional charts are usually the wrong choice, and the test is whether
the *shape* is the finding. Here it is. A diagonal cliff traces the reline year
across the fleet — older plants reline sooner — and the highest ground runs
along its near side. That is Finding 3 for every plant at once instead of one at
a time. Exact values come from the flat heatmap underneath; the 3D view is for
the shape, never for reading numbers off.

Rendered with plain Canvas 2D and a painter's algorithm. No WebGL, no libraries,
and the projection re-fits itself to the frame so the surface cannot overflow at
any angle you drag to.

## Four outputs, and why there are four

| Output | Question it answers | Contains option premium? |
|---|---|---|
| Trigger `p*'` (€/tCO₂) | At what carbon price does an irreversible switch become rational? | Yes |
| Crossing year | When does the *path* reach that price? | Yes, plus a price forecast |
| `T*` | Which year maximises NPV? | No |
| `T_exp` | Last year in which deferral still adds value | No |

`T*` and the crossing year routinely differ by one to two years. **That gap is
the option premium expressed in time, not an inconsistency.**

## Layout — the group order is the deliverable

```
timing_model/
  params.py        # dataclasses; every field carries unit, currency-year, source
  primitives.py    # Group I:   b, a(p_H2), CRF, MAC   [MAC diagnostic only]
  benefit.py       # Group II:  alpha_v(t), B(t)
  cost.py          # Group III: L(T), s(T), S_s(T), I_prime(T)
  objective.py     # Group IV:  npv(T), t_star, t_exp, delta(T)
  option.py        # Group V:   p_M_prime, beta, trigger, crossing_year
  validate.py      # gate + feasibility guards; raises, never returns a flag
  results.py       # Outputs, welded to its conditions
  scenarios.py     # ladder, storylines, sourced ranges, legacy fixture
  diff_harness.py  # 50 reference cases + the MATLAB diff
  report.py        # tables + CSV
eurostat.py            # observed inputs from Eurostat, cached for offline use
analysis.py            # derives the structural findings
findings_report.py     # -> findings.html, the findings written out in full
plots.py               # -> charts.html, nine charts, no matplotlib
surface.py             # -> surface.html, the fleet surface in rotatable 3D
article.py             # -> article.html, THE FINISHED PIECE
ARTICLE.md             # working table of contents for the write-up
selfcheck.py           # 26 stdlib assertions, for when pytest is unavailable
run_all.py             # runs everything above in one go
```

Imports point forward only, and `tests/test_layering.py` asserts it by walking
the AST. `cost.py` cannot import `objective.py`; `primitives.py` reaches
nothing but the parameter container; `cost.py` may not so much as name the load
factor `u`.

## Usage

**Python 3.11+ and nothing else.** The package has zero third-party
dependencies — no numpy, no pandas, no solver libraries. Every equation is
closed-form or a small argmax over ~25 years, and a test asserts the package
imports nothing outside the standard library. If you cannot install packages,
everything below still works.

```bash
python run_all.py                          # EVERYTHING: gate, ladders, diff, self-check
python selfcheck.py                        # 26 load-bearing claims, stdlib only

python eurostat.py                         # observed inputs + the hydrogen floor
python analysis.py                         # the five findings, with evidence
python plots.py                            # charts -> charts.html
python findings_report.py                  # findings.html, the full write-up
python surface.py                          # surface.html, the 3D fleet surface
python article.py                          # article.html, the finished article
python -m timing_model.report              # just the cumulative stress ladder
python -m timing_model.report --sigma      # plus the volatility ladder
python -m timing_model.report --csv        # writes python_results.csv
```

`pytest` is the only optional extra, and runs the full 91-test suite in
`tests/`. Without it, `selfcheck.py` verifies the same load-bearing claims —
gate, base case, ladder, guards, conditions mechanic, negative control,
layering — using only the standard library. `run_all.py` runs the self-check
always and the pytest suite when it is available.

### PyCharm

1. **Open** the repository root as the project (the folder containing
   `pyproject.toml`) — not the `timing_model/` package folder, or imports
   will not resolve.
2. **Interpreter:** Settings → Project → Python Interpreter — any 3.11+
   interpreter works. **No packages need installing.** If PyCharm offers to
   install `requirements.txt`, that is only `pytest`, and it is optional.
3. **Tests:** if you have pytest, set Settings → Tools → Python Integrated
   Tools → Default test runner = **pytest**, then right-click `tests/` → Run.
   If you cannot install it, right-click `selfcheck.py` → Run instead.
4. **Run everything at once:** right-click `run_all.py` in the Project pane →
   **Run 'run_all'**. That executes, in order: the validation gate, the base
   case, the stress ladder, the volatility ladder, the sourced ranges, the
   50-case reconciliation harness with its negative control, the CSV write,
   and the full test suite. It exits non-zero if the gate fails, the negative
   control misbehaves, or any test fails, so it also works as a CI smoke check.
5. **Running just the report:** use a *module* run configuration, not a script one —
   Run → Edit Configurations → **+** → Python, switch the target dropdown from
   *Script path* to **Module name**, and enter `timing_model.report`. Put any
   flags (`--csv`, `--sigma`) in *Parameters*. Running `report.py` as a plain
   script also works because PyCharm puts the content root on `sys.path`, but
   the module configuration is what matches the documented entry point.

`pip install -e .` is optional and only needed to import `timing_model` from
outside the project.

## The conditional-outputs mechanic

The recurring failure this rewrite exists to fix is that `T*` and the trigger
get quoted without the assumptions they are conditional on. `Outputs` is
frozen and always carries `conditions`; `report.py` **refuses to render** any
row containing `t_star` or `trigger` unless every condition is populated, and
prints them under the table. Tests cover each condition key individually.

## Three decisions the code will not make for you

Appendix A §3.5 reserves these to the team. All branches are implemented and
none is silently defaulted — each is surfaced in the printed conditions of
every row:

1. **Support basis** — €200 lump or ~€600 stream. `support_basis` switches
   between netting a stock from capex (`"lump"`, which the MATLAB diff needs)
   and routing the premium into `B(t)` where a flow belongs (`"stream"`).
2. **Resale** — `w = 1` drives the entire policy-neutrality finding. Without
   it the headline result reverses sign.
3. **Whether €2.60/kg hydrogen is reported as the base case at all.** The
   market was €8.29/kg on 8 May 2026.

## Status

Read `CALIBRATION.md` before quoting any number from this build.
`timing_model.m` was not in the working directory, so five of the six cost-side
constants were sourced from published industry data and one (the learning
growth rate) calibrated. The validation gate, the trigger column
and the benefit side reproduce exactly, as do ladder rows 1–3; rows 4–7 do not,
and the reasons are documented case by case with sources.
