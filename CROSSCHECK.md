# Cross-check: the October article against the code

*20 October 2026. Draft 1 of "The year waiting stops being free" (internal, with
Pablo's and Achelijn's comments of 8–13 October) checked against this
repository; Draft 2 rewritten on the corrected numbers.*

**In short.** Draft 1's headline numbers came from a "steel cross-check case"
(its annex, eqs 1–8) that was not in the repository, so none of them could be
re-run. That case is now `analysis/plant_case.py`, with 29 tests that pin every
number Draft 2 quotes. Writing it down exposed six errors in the draft's model
and one in the core model, and resolved Pablo's "IMPORTANT CHECK": under current
EU rules a plant that switches **keeps** its free allocation, so the carbon value
of switching is the full `E x P(t)`, not `E x P(t) x s(t)`. The 2029 result
survives on the central path, but for a different reason (the support window and
the reline calendar, not the CBAM phase-out), and the switch only pays if
hydrogen costs about EUR 3/kg or less.

Reproduce everything below with:

```
python -m analysis.plant_case          # every number in Draft 2
python -m analysis.allocation_check    # eq (4) against benchmark x activity
python -m pytest tests/test_plant_case.py tests/test_allocation_check.py
```

---

## 1. What was wrong, and what was done

| # | Where | Problem | Done |
|---|---|---|---|
| 1 | Draft annex | The case the article quotes from was not in the repo; no number could be re-run | Added `analysis/plant_case.py` (deterministic NPV by FID year, break-evens, payback, waterfall, lattice + Longstaff–Schwartz option layer, one-at-a-time, 81-scenario sweep, Sobol indices, CCfD) and `tests/test_plant_case.py` |
| 2 | Draft annex, footnote 3 (comment #159) | Assumed a switching plant **loses** its free allocation, so the switch saves only `E·P·s(t)`. Since Delegated Regulation (EU) 2024/873 the hot-metal benchmark covers DRI (Implementing Regulation (EU) 2026/1412, recital 9), and allocation is benchmark × historical activity, not emissions | Base case: allocation retained, surplus sold at the market price of the year (comment #140). "Lost" kept as a sensitivity. Consequence: the free-allocation rulebook no longer changes the value of switching, only the cash bill of doing nothing |
| 3 | Draft annex | 8% **real** discount rate applied to **nominal** analyst prices (the repo's own correction ladder flags this) | All paths deflated at 2%/yr to 2026 euros |
| 4 | Draft annex eq (3) | Two hydrogen intensities: EUR 150m at EUR 2.60/kg (55 kg/t) plus EUR 143m per EUR 1/kg (57.2 kg/t) | One intensity: 143 kt/yr; opex = 143 × p_H2 − 207.5 (EUR 164m at EUR 2.60/kg) |
| 5 | Draft text, "turns negative around 2029" | Explained by the 22.5% → 48.5% CBAM step in 2029–30, but with a four-year build a 2029 FID produces steel in 2033; the plant pays the bill during construction whatever it decides. The core model has no construction lag at all (benefit starts in the commitment year) | Plant case decides an FID year, builds 2029–32, produces from 2033. The 2029 result holds on the central path, driven by the support window (opens 2028, tapers from 2032) and the 2038 reline |
| 6 | Draft footnote 2 | Proposal schedule taken as linear to 100% over 2034–38; the repo's eq (12) (and secondary sources) hold 15% free over 2034–37 and end in 2038 | Uses eq (12) |
| 7 | Draft "timing is more robust" | Used the −0.96 correlation between T* and NPV across 81 scenarios as evidence; the repo's finding 5 shows that correlation is manufactured by the grid | Removed. Draft 2's timing claim rests on the sweep itself: all 25 viable scenarios have their best FID year in 2028–2031 |
| 8 | Draft method | Claimed a Longstaff–Schwartz option layer and a Sobol decomposition; neither existed in this repo | Both implemented; LSM is checked against an exact binomial lattice (agree within 0.3% on the central case) |
| 9 | Draft Table 2 | CfD "brings aluminium forward, delays ammonia": no calibrated sector model exists here (open item H4) | Dropped. Replaced by a steel CCfD strike analysis (Draft 2, Table 3). Bring the sector model into the repo to reinstate it |
| 10 | Core model, eq (4) | `B(t)` adds `u·α·ε_cln·p`: the clean route's residual emissions are treated as covered free while the incumbent's whole allocation is also sold | Reported, not applied (`analysis/allocation_check.py`). It is the whole of the published "+7.82 vintage delta with resale"; removing it moves the base NPV 1,605.9 → 1,589.1 (v11 printed 1,588) and closes five of the eight NPV-level gaps. Applying it moves every published level and the fitted `gamma`, so it is a team decision |
| 11 | `analysis/verify.py` | `check_market` downloaded the EEX auction workbook while `brief.build()` rendered a page — the failure `test_rendering_a_page_never_touches_the_network` exists to catch | Renders now use rows already loaded in the process (`eex.loaded_auctions`); only the stand-alone verifier fetches |
| 12 | `tests/test_market.py` | The EU-only volatility test needs the live auction record and failed offline | Skips with a reason when the record is unreachable |

Full suite after the changes: 302 test functions, 419 cases, all passing
offline (network-only tests skip); `selfcheck.py` 42/42.

## 2. Draft 1's numbers against the re-run

Draft 2 basis: allocation retained, 2026 euros, FID-year model, paths as in
Draft 2 Table 2.

| Draft 1 | Re-run | Why it moved |
|---|---|---|
| Cash bill today about EUR 7m | EUR 7m | — |
| Bill about EUR 700m/yr from 2035 (current law, "analyst" path) | EUR 559m in 2035, EUR 610m in 2038 (pre-reform outlook) | Path re-attributed to ABN AMRO and revised (138/191, May 2026); deflated |
| Just under EUR 500m by 2038 (proposal, working path) | EUR 457m in 2038 (central) | Deflated |
| Almost EUR 300m if prices stall | EUR 298m from 2038 | Stall at EUR 85/t in 2026 euros |
| Do-nothing liability EUR 2.2–4.8bn | EUR 2.0–4.5bn | As above |
| Liability EUR 1,900 / 1,300 / 900 per t | EUR 1,780 / 1,260 / 810 | Dropped from Draft 2 |
| PV of building the plant EUR 2.1bn | EUR 2.1bn | — |
| Switch recovers EUR 1.6bn of 4.8bn (a third), current law | EUR 1.3bn of 4.5bn (29%), pre-reform outlook | Allocation retained, real prices |
| EUR 0.3bn of 3.2bn (8%), proposal | EUR 0.35bn of 3.1bn (11%), central | Same |
| Stall destroys EUR 0.7bn | EUR −0.74bn (FID 2029) | — |
| Peak funding EUR 2.5bn | EUR 2.5bn | — |
| Payback 2037 / 2039 / 2047 | 2038 / 2040 / 2047 | — |
| Break-even EUR 118/t (law), 124/t (proposal) | EUR 121/t for a 2029 FID under either rulebook; EUR 122 / 131 if allocation were lost | Retained allocation makes the rulebook irrelevant |
| Analyst path passes break-even in 2029; working path in 2033 | Pre-reform outlook passes EUR 121 in 2030; central path in 2036 (2026 euros) | Deflation |
| Capex +20%: −EUR 0.4bn | −EUR 0.38bn, and no FID year then pays | — |
| One-year delay: −EUR 0.15bn | −EUR 0.06bn | FID-year model |
| Carbon −20%: −EUR 0.8bn | −EUR 0.50bn | Real prices |
| Hydrogen +EUR 1/kg: −EUR 0.85bn | −EUR 0.70bn | One intensity, 2050 horizon |
| July 2026 proposal: −EUR 1.35bn | Zero through allocation (retained); −EUR 0.15bn if allocation were lost. The pre-reform vs central path gap is EUR 0.95bn, but that mixes two analysts' views | Draft 1 mixed a rule change with a price-path change |
| Hydrogen at EUR 5/kg turns value negative | −EUR 1.68bn at FID 2029; no year pays | — |
| Marginal value of waiting negative around 2029 | Confirmed on the central path (+EUR 309m to 2028, ≈0 to 2029, negative after) | Mechanism changed, see §1 row 5 |
| Correlation −0.96 | Removed | §1 row 7 |
| CfD: aluminium forward, ammonia delayed | Not reproducible here | §1 row 9 |

## 3. Sources corrected (from the research pass of 20 October)

- The "EUR 145/t by 2030, EUR 200/t by 2035" path is ABN AMRO's (16 September
  2025), not Citi's; ABN AMRO revised it to 138/191 on 13 May 2026. Draft 2 uses
  the revision and labels it "pre-reform outlook".
- ClearBlue Markets' EUR 138.5/t for 2035 under the proposal is confirmed (23
  July 2026). The latest Reuters poll (31 July 2026) has 2030 at EUR 109.11/t.
- thyssenkrupp's Duisburg DRI plant starts at the end of 2027, initially on
  natural gas; its hydrogen tender was paused in March 2025. Stegra closed a
  EUR 1.4bn round in June 2026. Salzgitter deferred SALCOS stages 2–3 to
  2028–2029. ArcelorMittal's Bremen/Eisenhüttenstadt exit (June 2025) is confirmed.
- IP/26/1596: LRF 3.7% (2031–35) and 1.7% (2036–40); CBAM-sector phase-out
  extended to 2038 with 15% restored from 2028; EUR 100bn Industrial
  Decarbonisation Bank. "ETS Investment Booster ≈ EUR 30bn" is ClearBlue's
  valuation of 400 million allowances, not a Commission figure — dropped.
- Hydrogen costs: ACER 2025 monitoring report — conventional just over EUR
  2/kg, abated EUR 2.80/kg, renewable about EUR 8/kg.
- Still to check against the legal text: the year-by-year COM(2026) 616 annex
  schedule, and how competent authorities treat a BF-to-DRI switchover under
  the activity-level rules (Regulation (EU) 2019/1842, Art. 5).

## 4. Review comments and what Draft 2 does with them

| # | From | Comment | Draft 2 |
|---|---|---|---|
| 0–1 | Pablo | Title must be more specific (CORE) | "When waiting stops paying: The forces that set the timing of EU heavy industry's decarbonization investment"; Draft 1's title kept as the conclusion heading |
| 2–3 | Pablo, Achelijn | Reframe summary around the forces and the method; "timing can be more stable than NPV under a fixed framework"; add the flow | Summary rewritten on Pablo's structure; third finding phrased as stability within the modelled calendar; closing flow sentence |
| 5 | Pablo | ToC moves back and forth; proposed structure | Draft 2 follows it: decision and relevance → method → key findings → sensitivity → implications → conclusion → annex |
| 46–48 | Pablo, Achelijn | "Technically proven" needs references; cross-check plants | HYBRIT pilot (>5,000 t) for pilot scale; status of Stegra, thyssenkrupp, SALCOS with sources |
| 47 | Pablo | Generic drivers first, then the steel parametrization | "One investment, four forces" (generic), then "A standard EU facility" |
| 49, 67, 83 | Achelijn | Sources | Footnoted (26 footnotes, 30+ sources) |
| 61 | Pablo | Section starts with a finding, ends with input data | Restructured: inputs in Method, findings in Key findings |
| 62 | Pablo | Seminal source | Dixit & Pindyck (1994); McDonald & Siegel (1986) |
| 73, 82 | Achelijn | "Who is we"; "we use steel as…" | Rephrased |
| 80, 117 | Achelijn, Pablo | Table of the example plant; no names, "standard EU facility" | Table 1, "standard EU facility", bases given as public project data |
| 109, 125, 200 | Pablo | Inputs vs results; define the paths before using them; give the analyst path a name | "Scenarios are boundary conditions, not forecasts"; three named paths and two rulebooks defined in Table 2 before any result |
| 112, 114 | Achelijn | Is the analyst-path statement good? Mention the stall? | Re-attributed (ABN AMRO, revised); stall kept as a labelled stress test |
| 116 | Achelijn | Simplify the method language | Method section rewritten in plain terms |
| 119, 121 | Pablo | Results under "key findings"; the carbon bill is a boundary condition | "Key findings" section; the bill introduced explicitly as a boundary condition |
| 124, 126, 139, 194, 198 | Pablo, Achelijn | Which law? Which proposal? Links | Directive (EU) 2023/959 Art. 10a(1a); COM(2026) 616 / IP/26/1596, defined at first mention, with EUR-Lex and Commission links |
| 130 | Achelijn | Define "today's money" | Present value defined in the text |
| 131 | Achelijn | Consistent number formatting | EUR Xm / EUR X.Xbn / EUR X/t throughout |
| 133 | Pablo | One consistent term | "The switch", defined once; "FID year" for timing |
| 140, 159 | Pablo | Selling price of unused allowances; IMPORTANT CHECK | Allocation retained after the switch, surplus sold at that year's price; cost of doing nothing shown both as cash bill and full carbon value |
| 152–153 | Achelijn, Pablo | IRR | Real IRR reported (10% central); footnote distinguishes it from the recovered share |
| 158, 170, 174 | Achelijn | Define "acting"; expand; meaning | Rewritten |
| 172–173 | Achelijn, Pablo | "In the model"; information value not in the model | Two layers stated explicitly: the deterministic layer buys no information; the option layer adds price information; rule uncertainty is handled by scenarios |
| 178, 206 | Achelijn | Fix figure sources | Every figure and table carries a source line |
| 180–183 | Pablo, Achelijn | Results and sensitivity mixed; "timing" and "value" undefined | Sensitivity is its own section with an introduction; value and timing defined in the method |
| 189–193, 195–196 | Achelijn | Relevance of the 81 scenarios and the correlation; unclear "curve" | Correlation removed; 81-scenario result stated in plain terms |
| 199, 202 | Pablo | "Exception to what"; name break-even and trigger properly | "Break-even is a floor, not a trigger", with both defined |
| 208 | Pablo | Companies wait for other reasons too | Stated; the model's notion of rational waiting is scoped |
| 219 | Pablo | One-at-a-time chart introduces sensitivity | Figure 5 opens the sensitivity section |
| 223, 226, 228–229 | Achelijn, Pablo | CfD wording overstated; other industries; the sign inversion is interesting | Sector sign inversion not reproducible here (see §1 row 9); replaced by a steel CCfD strike analysis; other sectors described qualitatively |
| 234–235, 237–238, 242, 245, 248 | Pablo, Achelijn | Avoid advice; triggers vs forecasts; grid permit opportunity cost; hypothesis phrasing | Implications rewritten as analysis with an explicit not-advice line; Pablo wanted to redraft this section together — Draft 2's version is a starting point |
| 251 | Achelijn | LaTeX formatting | Annex equations are native Word equations |
| — | Achelijn (inline) | Capex graph in the intro | Not included (word limit); Figure 3 shows capex in the value bridge |

## 5. Open for the team

1. **Hydrogen price.** Draft 2 keeps EUR 2.60/kg as the reference (between
   conventional and abated hydrogen) and says so; the switch breaks even at
   EUR 3.0/kg on the central path. Whether to lead with that reference is the
   README's third open decision.
2. **Benchmark accounting in the core model** (§1 row 10).
3. **Sector models** for any cross-sector CfD claim (open item H4).
4. **Legal confirmations**: the COM(2026) 616 annex schedule, and the
   treatment of a switchover under the activity-level rules.
