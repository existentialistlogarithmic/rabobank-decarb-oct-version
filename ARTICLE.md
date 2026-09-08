# Article outline — working table of contents

*A writing plan, not a draft. Each section states what it has to establish, the
figure that carries it, and the one sentence the reader should leave with. Word
budgets total ~2,800.*

**Working titles**

- *The deadline is the only date that isn't a forecast*
- *When, not whether: reading a steel decarbonisation decision*
- *Five things the timing model says that nobody asked it*

**Standfirst (draft).** Every input in a decarbonisation investment case is a
forecast except one. That one — the date a blast furnace must be rebuilt — turns
out to set the decision more tightly than the carbon price does. Along the way,
the model says three things that invert standard project-finance intuition.

---

## 1. The question is when, not whether

**Establishes:** the setup, in plain language, for a reader with no background.
A producer runs a blast furnace; a clean route exists; it is irreversible. The
question is timing.
**Figure:** none — keep it prose.
**Budget:** 200 words.
**Leave with:** *This is a timing problem, and timing problems have deadlines.*

## 2. What we published, and what was wrong with it

**Establishes:** four corrections, none of them a scenario — a load factor that
was implicitly 100%, a benchmark applied to the wrong tonne, a real rate against
a nominal price path, and an opex penalty that hid a hydrogen forecast.
**Figure:** Figure 1, all four curves.
**Evidence:** €1,588 → €754 as the corrections stack.
**Budget:** 350 words.
**Leave with:** *The corrections move the date by two years and halve the value.*

## 3. The answer is a window, not a year

**Establishes:** the peak is flat — 2028–2032 all within 4.3%, 2029 vs 2030 just
€7 on €1,588. Publishing a single year is false precision when every input is a
forecast.
**Figure:** Figure 1, annotated on the plateau.
**Budget:** 300 words.
**Leave with:** *Anyone quoting a single optimal year is over-reading the curve.*

## 4. …with a hard close

**Establishes:** €458, about 30%, lost in the single step from 2032 to 2033 —
the reline. Near-identical across all four corrected lines, because unlike
everything else it isn't a forecast. Then widen to the fleet: the same edge
sweeps diagonally across every plant.
**Figure:** the fleet surface (`surface.html`) — the reline as a ridge, with the
high ground on its near side. Use the plan view in print, the 3D interactively.
**Evidence:** capture region from age 16; value peaks at age 18.
**Budget:** 450 words. *This is the article's spine — give it the most room.*
**Leave with:** *The peak is soft; the deadline is hard.*

## 5. Which lever actually does what

**Establishes:** the orthogonal split. Five parameters move value and leave the
threshold at exactly 0.000%; two move the threshold and leave value at exactly
0.000%. It is structure — those symbols are absent from the trigger formula.
**Figure:** the lever map. Orthogonality shows as points hugging the axes.
**Budget:** 400 words.
**Leave with:** *A CfD and a grant are complements. No amount of grant money
fixes a volatility problem.*

## 6. Where the case actually fails, and why utilisation inverts

**Establishes:** hydrogen, not carbon, is the binding constraint. Then the
counterintuitive part: above €6.15/kg the sensitivity of value to the load
factor changes sign, because the load factor multiplies a flow that has gone
negative. Today's market price is on the wrong side.
**Figure:** the inversion chart, zero-crossing marked, Platts at €8.29.
**Budget:** 400 words.
**Caveat that must appear in-line, not in a footnote:** this is the sign of a
sensitivity on a case that is NPV-negative throughout — not advice to build a
plant and idle it.
**Leave with:** *A minimum-utilisation covenant would be pointed backwards.*

## 7. Two things we would have got wrong

**Establishes:** method, briefly. (a) The trigger looks insensitive to the
discount rate, but that is a +304% and a −68% movement nearly cancelling — a
cancellation fails differently from a robustness. (b) A correlation matrix over
our own scenario grid says value and threshold are coupled at −0.87, which the
structure says is false; the ensemble manufactured it.
**Figure:** the rate decomposition, three series indexed to a common base.
**Budget:** 350 words.
**Leave with:** *Report the two factors, not the product; and never infer
mechanism from a correlation over a grid you chose yourself.*

## 8. What this means for origination

**Establishes:** the banker bridge. FID is not the financing date — a term sheet
is negotiated 18–24 months ahead. The reline calendar is published per plant, so
this converts to a target list. The best client is not the newest or the oldest
asset but the one about two years short of a reline.
**Figure:** reuse the fleet surface, plan view, read as a screening map.
**Budget:** 300 words.
**Leave with:** *The origination window is now; the target list is a maintenance
schedule.*

## 9. What we are not claiming

**Establishes:** the conditions, stated plainly rather than buried. Every number
is conditional on hydrogen at €2.60/kg, resale permitted, lump support, nominal
prices. The cost-side parameters are calibrated, not sourced. Three decisions
remain open for the team.
**Figure:** none.
**Budget:** 250 words.
**Leave with:** *These are conditional results, and the conditions are the
finding as much as the numbers are.*

---

## Figures, in order of use

| # | Figure | Source | Carries |
|---|---|---|---|
| 1 | NPV by commitment year, four corrections | `charts.html` | §2, §3 |
| 2 | The fleet surface | `surface.html` | §4, §8 |
| 3 | Lever map | `charts.html` | §5 |
| 4 | Utilisation inversion | `charts.html` | §6 |
| 5 | Rate decomposition | `charts.html` | §7 |

## Before submitting

- [ ] Every headline number re-run from `analysis.py`, not transcribed
- [ ] Conditions line on every table and figure caption
- [ ] §6 caveat is in the body text, not a footnote
- [ ] "never" replaced with "beyond any recognisable investment horizon" throughout
- [ ] Sector claims limited to ordering; no quantitative triggers for non-steel
- [ ] Calibration status stated where the reline date first appears (§4)
