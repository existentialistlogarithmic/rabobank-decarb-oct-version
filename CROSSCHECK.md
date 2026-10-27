# Cross-check: the October article against the review comments, the sources and the code

*27 October 2026, for Draft 3 of the article (now titled "When waiting stops
paying: The forces shaping industrial electrification investment decisions in
the EU"). Section 7 keeps the 20 October cross-check that produced Draft 2.*

**In short.** Draft 3 follows Pablo's table of contents exactly and closes the
gaps Draft 2 left against his comments and tracked edits (section 1). Every
factual claim was re-checked against a primary or high-quality source on 27
October (section 2), and the draft now reflects what changed since 20 October
(section 3). At the authors' request, no ABN AMRO source is used: the
pre-reform price path is re-anchored on BloombergNEF's April 2026 estimates,
which moves a few pre-reform numbers (section 4). The seven figures were
recomputed against the model run by a script; that check found one rounding
error in Table 2, now fixed (section 5). Two assumptions deserve a team
decision before publication: the EUR 525m reline credit, which is two to four
times recent relines, and the operating costs the model does not separate out
(section 6).

Reproduce:

```
python -m analysis.plant_case                         # every number in the article
python -c "from analysis import plant_case as pc; pc.export('plant_case.json')"
python docs/article/make_figures.py plant_case.json docs/article/figures
python docs/article/check_figures.py plant_case.json  # 77 checks, 0 mismatches
python -m pytest tests/test_plant_case.py
```

Word count (title through conclusion, including the summary, headings, figure
and table captions and source lines; excluding footnotes, table cells, the
annex and the acronyms page): **3,155**, under the 3,300 limit. The annex of
model equations adds 804 words of reference material.

---

## 1. Draft 3 against every comment and tracked edit in Draft 1

71 comments (34 Pablo, 37 Achelijn) and the tracked edits. ✓ done in Draft 3;
◐ partly; ✗ open.

| # | From | Comment (short) | Draft 3 | |
|---|---|---|---|---|
| 0, 1 | Pablo | Title must be more specific (CORE); "The driving forces shaping the industrial electrification investment decision in the EU context" | "When waiting stops paying: The forces shaping industrial electrification investment decisions in the EU"; Draft 1's title kept as the conclusion heading | ✓ |
| 2 | Pablo | Frame problem and findings within the method; his alternative summary; "neither time nor value can be robust" | Summary follows his text: four forces (capex, opex shift, ETS price, timing of support), the model named, the 2.5Mt plant, lessons for cement/ammonia/aluminum, three findings including "and the rules behind them"; "robust" removed everywhere | ✓ |
| 3 | Achelijn | Flow sentence at the end of the summary | "We set out the scope and method, then the findings and implications." | ✓ |
| 5 | Pablo | ToC: Scope of research and problem formulation → Short methods → Key findings (cost of doing nothing; when waiting stops paying; what moves the decision and what moves value) → Implications for investors and other decision-makers → Conclusion → Annex | Followed heading for heading. Scope holds the type of investment, its components with definitions and typical values (Table 1, Figure 1) and the strategic relevance; Short methods holds the formulation and only the parametrization the findings need | ✓ |
| 46 | Pablo | References for "proven"; name pilot plants and commercial projects with status | HYBRIT pilot (>5,000 t of hydrogen-reduced iron); Salzgitter (H1 2027) and thyssenkrupp (end-2027) starting mainly on gas; Stegra's new capital need; Tata Steel's deadline; ArcelorMittal's exit — all sourced, status as of October 2026 | ✓ |
| 47 | Pablo | Generic drivers first, then the steel parametrization | "The investment we analyze" is generic; the standard EU facility is parametrized in Short methods | ✓ |
| 48, 49 | Achelijn | Cross-check plants; source for ArcelorMittal | Re-verified 27 Oct; ArcelorMittal's own release and Argus | ✓ |
| 61 | Pablo | A section that starts with a finding and ends with input data | Inputs only in Scope/Methods, findings only in Key findings | ✓ |
| 62 | Pablo | Seminal source | Dixit & Pindyck (1994); McDonald & Siegel (1986) | ✓ |
| 67, 83 | Achelijn | Sources for the structural variables and for "why steel" | Every statement sourced (IP/26/1596, ICAP, Inercomp, ACER, IEA, Euronews); "why steel" answered by the public project data (Figure 1) | ✓ |
| 73, 82 | Achelijn | "Who is we"; "we use steel as…" | "the question each firm faces individually: commit now, or later?"; "we analyze a 2.5Mt/year hydrogen-based steel plant" | ✓ |
| 80, 117 | Achelijn, Pablo | Table of the example plant; solid examples, no names, "standard EU facility" | Table 1 gives typical values with solid, named examples (thyssenkrupp, Salzgitter, Stegra, ArcelorMittal in Figure 1) and a separate, unnamed reference-plant column; the text says where the reference sits against the examples (support at the low end, reline at the high end) | ✓ |
| 109 | Pablo | Be clear about research question, formulation, inputs, results, relevance | Research question stated explicitly; time frame defined (FID 2026–2040, cash flows to 2050); inputs in Tables 1–2 before any result | ✓ |
| 112, 114 | Achelijn | Is the analyst-path statement good? Mention the stall? | Pre-reform path re-sourced to BloombergNEF (April 2026); stall kept as the low boundary (September–October level) | ✓ |
| 116 | Achelijn | Simplify method language | Rewritten in plain terms; equations in the annex | ✓ |
| 119, 121 | Pablo | Results under "Key findings"; the bill is a boundary condition | Both | ✓ |
| 124, 126, 139, 194, 198 | Pablo, Achelijn | Which law, which proposal; links | Directive (EU) 2023/959; COM(2026) 616 / IP/26/1596; EUR-Lex and Commission links | ✓ |
| 125 | Pablo | Define every term before use; "start by saying we consider these 3 paths" | Three paths defined in Methods before any result; Acronyms and units page added | ✓ |
| 130 | Achelijn | "Today's money" | "present value" defined; real prices are "2026 euros" throughout | ✓ |
| 131 | Achelijn | Consistent number formatting | EUR Xm below EUR 1bn, EUR X.Xbn above; EUR/t, EUR/kg | ✓ |
| 133, 158 | Pablo, Achelijn | One consistent term; "acting how" | "the switch" and "FID year", defined once | ✓ |
| 140 | Pablo | Depends on the selling price of unused allowances | In the body: "assuming surplus allowances sell at the market price of the year they are issued" | ✓ |
| 152, 153 | Achelijn, Pablo | IRR | Reported (10%); defined in annex eq (12); footnote separates it from the recovered share | ✓ |
| 159 | Pablo | IMPORTANT CHECK: a switched plant keeps/sells allowances and pays no bill | Confirmed: since Delegated Regulation 2024/873 DRI sits under the hot-metal benchmark, so allocation is retained; the switch is worth the full carbon value E×P; cash bill and carbon value shown separately (Figure 3) | ✓ |
| 170, 172, 174 | Achelijn | Expand; "where? in the model"; meaning | "In the model, 2029 is the year waiting stops being free: before it, waiting is worth more than investing; after it, every year of delay gives up value" | ✓ |
| 173 | Pablo | Separate what is in the model from reality ("while in reality X and Z, in our model D and F") | Paragraph in that exact form in Methods | ✓ |
| 178, 206 | Achelijn | Fix figure sources | Every figure and table has a source line; no ABN AMRO | ✓ |
| 180 | Pablo | Unclear that timing moves "linearly" while value fluctuates | "That stability comes not from markets but from the calendar we model … If the calendar changes, the timing moves with it." | ✓ |
| 181, 219 | Pablo | Main results, then a sensitivity analysis with an introduction; the one-at-a-time chart should open it | The third finding opens with the introduction to the tests, then Figure 7 | ✓ |
| 182, 183 | Achelijn, Pablo | "Timing" and "value" undefined; results before their origin | Defined in Methods; the three tests are described before their results | ✓ |
| 189–193, 195, 196 | Achelijn | Relevance of the sweep and the correlation; "curve"; "move how" | Correlation and loose phrases removed; the 81-scenario result stated plainly | ✓ |
| 199, 202 | Pablo | "Exception to what"; give break-even and trigger proper names and logic | "Break-even is a floor, not a trigger", both defined; annex eqs (11), (17) | ✓ |
| 200 | Pablo | Give the path a specific name, e.g. "RaboResearch carbon prices foresight" | "RaboResearch carbon price foresight (central)" in text, tables and figures | ✓ |
| 208 | Pablo | Companies wait for other reasons | "Companies wait for many reasons the model omits… In the model, two remain…" | ✓ |
| 223, 226, 228 | Achelijn | CfD wording; overstated; other industries | Rephrased; other sectors described qualitatively | ✓ |
| 229 | Pablo | Sector sign inversion of a CfD: "very interesting, let's discuss" | Not reproducible: no calibrated sector models in the repository (open item 1) | ✗ |
| 234, 237, 238, 242, 245, 248 | Pablo, Achelijn | Avoid advice; triggers vs forecasts; grid-permit opportunity cost; hypothesis phrasing | Explicit not-advice line; triggers complement forecasts; grid deadline caveat; ArcelorMittal quoted in its own words | ✓ |
| 235 | Pablo | Re-draft the implications together | Draft 3 is a starting point for that session | ◐ |
| 251 | Achelijn | LaTeX formatting | All 23 model equations in the annex, typeset from LaTeX as native Word equations, each with what it is used for; stand-alone `.tex`/`.pdf` delivered too | ✓ |

Tracked edits:

| Edit | Draft 3 | |
|---|---|---|
| Pablo: "Technology and policy are mostly in place; the investment case faces structural uncertainty" | Standfirst | ✓ |
| Pablo: define the type of investment; shaping factors include revenues (demand for carbon-free products, Made in EU policies) | Scope: the four forces plus "Revenues could become a fifth force" (Industrial Accelerator Act low-carbon requirements; the July 2026 steel trade regime) and why trade protection does not change the value of switching | ✓ |
| Pablo: "technology or policy framework", "formulated on investable terms" | Kept, aligned with the published RaboResearch article ("availability") | ✓ |
| Pablo: "requires an investment close to EUR 3bn … returns highly likely to depend on variables the company does not control" | Content in Table 1 and the irreversibility paragraph; the sentence itself cut for length | ◐ |
| Pablo: energy-system scenarios "in a holistic cost minimization way" vs the question each firm faces; "To help illustrate…" | Methods, first paragraph, with the link to the scenario-review article | ✓ |
| Pablo: "in a given year"; realistic sizing; "Business As Usual" emissions; yearly share; "time frame (define it)"; "What happens with revenues?" | All in Scope/Methods | ✓ |
| Pablo: "Before it … after it" | When waiting stops paying | ✓ |
| Pablo: "Acknowledging the structural uncertainty…" | Opening of the sensitivity tests | ✓ |
| Pablo: "or any base technology with high carbon intensity"; "today relatively small"; proposal "delays" the phase-out | Cost of doing nothing; Figure 2 | ✓ |
| Pablo: "a timely one has the potential to recover"; "assuming that the selling price of the non-used allowances equals the market price when issued"; "hydrogen-based OPEX of XXX" | "A timely switch can recover part of this cost"; the allowance assumption in the body; "runs on hydrogen at an extra EUR 164m a year" | ✓ |
| Pablo: "confirms the role of the EU ETS as an industry policy tool. However, it is not enough to decide the optimal timing" | First sentences of "When waiting stops paying", sourced to Enerdata | ✓ |
| Pablo: "optimal investment timing … more stable than the corresponding NPV"; "the reason lies in the cost structure" | Summary and sensitivity section | ✓ |
| Pablo: "Because CO2 price risk dominates … CfDs are a straightforward way to manage the associated risks" | The re-run shows hydrogen, not carbon, dominates value (Sobol ≈ 0.52 vs 0.22); Draft 3 says what CCfDs do (act on the value of waiting) and points to hydrogen contracts for the larger risk | ◐ (corrected by the model) |
| Pablo: "Cement has to rely on carbon capture"; "to the extent possible" | Both | ✓ |
| Achelijn: "Somewhere in the intro include the capex graph" | Figure 1: announced investment and public support of the first EU projects, with the reference plant | ✓ |
| Achelijn: "zero crossing across the 81 scenarios, and the result under the July 2026 proposal" | Figure 5 (right panel); the proposal's effect stated (none through allocation, only through the carbon price) | ✓ |
| Achelijn: "also add explanation of IRR" | Annex eq (12) | ✓ |

## 2. Verification log (sources read on 27 October 2026)

| Claim in Draft 3 | Source | Status |
|---|---|---|
| EU industry's challenge is no longer technology or policy availability but investable terms | RaboResearch, Ruiz & de Zeeuw, 1 Oct 2026 | Verified (wording aligned to "availability") |
| Energy-system scenarios are "what if", not forecasts | RaboResearch, Ruiz & Hutters, 26 Mar 2026 | Verified |
| HYBRIT pilot: >5,000 t of hydrogen-reduced iron | Vattenfall, 26 Aug 2024 | Verified |
| Salzgitter stage 1: ~EUR 2.7bn, EUR 1.322bn support, 1.9Mt, start H1 2027 mainly on gas; stages 2–3 decisions 2028–2029 | ms-aktuell 20 Sep 2026; Eurometal 23 Sep 2025; Salzgitter 2023 releases (EUR 1bn; EUR 2.2–2.4bn budget then) | Verified; the repository's EUR 2.7bn and EUR 1.322bn are right |
| thyssenkrupp: ~EUR 3bn, EUR 2bn support (two-thirds), 2.5Mt DRI, >3.5Mt CO2, start end-2027 on gas; hydrogen condition relaxed | GMK Center 14 Aug 2026 (Reuters); industriemagazin; GMK Center Mar 2023; thyssenkrupp release 16 Feb 2024 (143,000 t of hydrogen) | Verified. The repository's `projects_capex.csv` has 2.3Mt, not 2.5Mt (not used by the article) |
| thyssenkrupp paused its tender because prices were "significantly higher than assumed" | Eurometal, 26 Mar 2025 | Verified (tender volume there: up to 151,000 t/yr; the 143,000 t demand is thyssenkrupp's own figure) |
| Stegra: EUR 1.4bn round closed 24 Jun 2026; Sep 2026: needs more capital, costs "significantly higher than assumed"; EUR 265m Swedish aid + EUR 250m Innovation Fund; ~EUR 6.5bn financing; 2.4–2.5Mt | Stegra; ESG Today 1 Oct 2026; GMK Center 28 Jun 2024; CINEA 3 Apr 2025; Hydrogen Fuel News 4 Sep 2025; cleanthinking 30 Jun 2026 | Verified; updated |
| ArcelorMittal dropped Bremen/Eisenhüttenstadt DRI despite EUR 1.3bn; EUR 2.5bn planned; "even with the financial support, the business case … is not strong enough" | ArcelorMittal, 19 Jun 2025; GMK Center 26 Feb 2024; Argus | Verified; now quoted |
| Tata Steel/Dutch state deadline extended to 1 Mar 2027; up to EUR 2bn | NL Times, 25 Sep 2026 | New, verified |
| July 2026 proposal: LRF 3.7% (2031–35), 1.7% (2036–40); 15% of phased-out allocation from 2028; phase-out to 2038; allocation conditional on investment from 2031; EUR 100bn IDB; Investment Booster 2028–30 | IP/26/1596; ICAP; ClearBlue 23 Jul 2026; Inercomp 23 Jul 2026 | Verified |
| Council: debate 12 Oct; position aimed for December; leaders want completion by Q1 2027; MSR deal 20 Oct (threshold 400m → 700m) | Council meeting page; S&P Global 5 Oct 2026; Council press release 834/26 | Verified; MSR deal new |
| Gas: war involving Iran (from 28 Feb 2026), Hormuz closed, Qatari LNG under force majeure; TTF ~EUR 96/MWh on 26 Oct, +234% since January | Al Jazeera 24 Mar 2026; Euronews 27 Oct 2026; The Deep Dive 28 Sep 2026 | New, verified |
| Carbon prices: Sep 2026 average EUR 85.6/t; EUR 88.3/t on 12 Oct; EUR 82–87/t over the month to 23 Oct (EUR 84.50 Dec-26) | GMK Center 15 Oct 2026; CemNet 23 Oct 2026 | Verified; stall path (EUR 85/t) still at the market level |
| Analyst consensus 2030: EUR 109.11/t (nine analysts, 31 Jul 2026) | Reuters poll (AOL, Euronext syndication) | Verified; no October poll published yet |
| ClearBlue: EUR 138.5/t in 2035 under the proposal | ClearBlue Markets, 23 Jul 2026 | Verified |
| Enerdata: ~EUR 100/t in 2030 and EUR 180/t in 2040 after the proposal; "transforms the ETS … into a major industrial policy instrument" | Enerdata executive briefing, 2026 | New (replaces the bank note) |
| BloombergNEF pre-proposal: EUR 142/t in 2031, up to EUR 185/t in 2035 | Eurometal (Kallanish), 18 Apr 2026 | New (replaces the bank outlook) |
| Hydrogen 2025: conventional just over EUR 2/kg, abated EUR 2.80/kg, renewable ~EUR 8/kg (HYDRIX ~EUR 8.20) | ACER 2025 monitoring report via pv magazine, 3 Dec 2025 | Verified |
| New low-emissions hydrogen FIDs fell below 0.8 Mtpa (2025) | IEA Global Hydrogen Review 2026 | Verified |
| German climate protection contracts: 15 awarded Oct 2024, up to EUR 2.8bn, 15 years, repayments when cheaper; 2026 round EUR 5bn, bids by 7 Sep, awards by 31 Dec, max EUR 550/t | BMWK 15 Oct 2024; PNO Innovation; Rödl & Partner 27 May 2026 | Verified; second round new |
| Commission CCfD guidance, 17 Jul 2026 | DG Competition document; EU Reporter 21 Jul 2026 | Verified |
| Industrial Accelerator Act (4 Mar 2026): low-carbon requirements for steel in public procurement; adoption not before 2027 | COM(2026) 100; Cooley; Eurometal | New, verified |
| Steel trade regime from 1 Jul 2026: quotas −47%, 50% out-of-quota duty, melt-and-pour | Council adoption, Adnkronos 8 Jun 2026 | New, verified |
| CBAM factor schedule (current law) and CBAM certificate prices | Directive (EU) 2023/959 Art 10a(1a); Q3 2026 certificate price EUR 82.32/t (carboncredits.com) | Verified |
| IDB should cover the operating-cost gap through CCfDs | Clean Air Task Force, 14 Jul 2026 | New; added for the opex-vs-capex point Pablo raised |
| Recent blast-furnace relines: Salzgitter A ~EUR 100m (2Mt, 2023); thyssenkrupp Schwelgern 2 >EUR 200m (~4Mt, 2014) | Oilprice/Salzgitter 11 Jan 2024; thyssenkrupp 16 May 2014 | New; drives open item 3 |

Pablo's LinkedIn link (Tomas Wyns, "Quantum tunnelling: OPEX to CAPEX") could
not be read: LinkedIn blocks automated access and the post is not indexed.
The CATF report above makes the closely related argument; paste the post's
text to have it reflected directly.

## 3. What is new since Draft 2 and where it went

- **Energy shock.** European gas more than tripled since January (Hormuz) →
  "Why it matters now"; the hydrogen reference (EUR 2.60/kg) is now even more
  favorable to the switch, which the Methods say.
- **Projects.** Stegra's capital need; Salzgitter's 2027 start on gas and higher
  support; thyssenkrupp's relaxed hydrogen condition; Tata Steel's extension →
  "Why it matters now", Figure 1.
- **Rules.** Council timeline; MSR deal; allocation conditional on investment
  from 2031 → "Why it matters now", footnotes.
- **Revenues.** Industrial Accelerator Act; July 2026 steel trade regime →
  Scope ("fifth force").
- **Policy design.** Germany's EUR 5bn second CCfD round, awards by year-end →
  "What moves the decision"; conclusion's "what to watch".
- **Carbon prices.** October levels confirm the stall path; Enerdata's
  post-proposal path confirms the central path out to 2040.

## 4. Model changes for Draft 3 and what they moved

1. **Pre-reform path re-anchored on BloombergNEF** (EUR 142/t in 2031, up to
   EUR 185/t in 2035, nominal; shared 2026 start; 5% drift after 2035).

   | Pre-reform outlook | Draft 2 | Draft 3 |
   |---|---|---|
   | Price 2030 / 2035 / 2050, 2026 euros | 128 / 160 / 247 | 119 / 155 / 239 |
   | Cash bill 2035; PV of the bill | EUR 559m; EUR 4.5bn | EUR 542m; EUR 4.3bn |
   | NPV 2029; best year (NPV) | EUR 1.30bn; 2028 (1.37bn) | EUR 1.18bn; 2028 (1.24bn) |
   | Recovered share; payback | 29%; 2038 | 27%; 2038 |
   | 81-scenario sweep: viable (by hydrogen 2.60/3.80/5.00) | 25 (16/8/1) | 23 (16/7/0) |
   | Value range of viable scenarios | EUR 45m–2.7bn | EUR 64m–2.5bn |

   Central path, stall, every central-case number, the option layer, the
   one-at-a-time results and the CCfD table are unchanged.
2. **Central path renamed** "RaboResearch carbon price foresight" (comment 200).
3. **Two sensitivities added**, from the verification: a EUR 150m reline
   (NPV 2029 EUR 202m, best year still 2029, the 2034→2035 drop halves to
   EUR 136m, 21 of 81 scenarios viable, hydrogen break-even EUR 2.84/kg), and
   the scale of unmodelled operating costs (each EUR 10/t a year: −EUR 148m on
   a 2029 switch).
4. `Plant.fuel_saving_eur_m` was described as "net of extra power"; it is the
   repository's `c_avoided`, an assumption rather than a sum (open item H10).
   Docstring corrected.

Tests: `tests/test_plant_case.py` pins every Draft 3 number (30 test cases);
full suite 420 cases, all passing offline (network-only tests skip).

## 5. Figure cross-check

`docs/article/check_figures.py` recomputes everything the charts print and the
text quotes from the same export the charts are drawn from: 77 checks.

| Figure | What was checked | Result |
|---|---|---|
| 1 Investment and support | Each bar against the published figure; EUR/t in Table 1 (1,200; 1,420; 2,600) | ✓ Legend changed from "capex" to "announced investment": Stegra's EUR 6.5bn is financing lined up, and its costs have risen since |
| 2 Share paid | Current law year by year against Directive 2023/959; proposal against "15% of the phased-out allocation restored, 2028–2037" | ✓ (proposal factors are rounded: 0.81, 0.59, 0.48, 0.375, 0.27) |
| 3 Cost of keeping the furnace | 2026 labels (EUR 7m, 266m); 2050 end labels; text values for 2030/2035 | ✓ |
| 4 Value bridge | Bars and their sum against the NPV (EUR 351m) | ✓ |
| 5 NPV by FID year; value of waiting | Best years (2029, 2028, none); 23 viable scenarios, all with best year 2028–2031; the count in the panel title is now computed, not typed | ✓ |
| 6 Prices, break-even, trigger | End labels; EUR 121/t; EUR 153/t; Table 2 values | **Table 2 had the central 2030 price as 104; it is 103.47 → 103.** Fixed. Draft 2 carried the same slip |
| 7 One change at a time | All eight bars and best years against the text | ✓ |
| Table 3 | NPV, commitment shares, net payments | ✓ |

## 6. Open for the team

1. **Sector models** for the CfD sign inversion (comment 229).
2. **Implications section**: Pablo's joint redraft (comment 235).
3. **Reline credit.** The v11 convention (25–50% of a new furnace) gives
   EUR 525m; recent European relines cost EUR 100m (2Mt) to over EUR 200m (4Mt).
   At EUR 150m the switch is worth EUR 200m, not EUR 350m, and the best year
   is unchanged. Draft 3 shows both; choose the base case.
4. **Operating costs not separated out** (H10): furnace electricity, electrodes
   and pellet premiums sit inside `c_avoided`. With 2026 power prices this is
   material: each EUR 10/t a year costs about EUR 150m of value.
5. **Hydrogen reference** EUR 2.60/kg is from 2025 cost data; with gas at
   EUR 90+/MWh, gas-based hydrogen costs more today. Consider a 2026 point.
6. **Legal text**: the year-by-year CBAM factors in COM(2026) 616 and how
   authorities treat a switchover under Implementing Regulation 2019/1842
   Art. 5; the 2031 investment condition (top-10% plants exempt).
7. **Repository data outside the article** still list a bank outlook
   (`data/sourced/carbon_prices.csv`, `docs/research-*.md`); the article does
   not use it. Remove repo-wide if the source rule applies there too.
8. `data/sourced/projects_capex.csv`: thyssenkrupp capacity 2.3Mt → 2.5Mt.

## Final check of Draft 4 (27 October, afternoon)

Draft 4 is Draft 3 with Achelijn's edits (header stamp, label, byline, the
model no longer called "RaboResearch's", research question in bold). Every
number was re-run against `plant_case.py`; every number that differs between
Draft 4 and the checked version is listed here:

| Where | Draft 4 | Checked | Why |
|---|---|---|---|
| Cost of doing nothing | proposal lowers the bill PV by "about EUR 200m" | about EUR 240m (central path) | 3,384.6 − 3,148.7 = 236; the test now pins 240 |
| Table 1, carbon price | allowances at EUR 82–87/t | EUR 82–88/t | GMK Center has EUR 88.3/t on 12 October |
| Calendar sentence | "the reline" | "the reline in 2038" | explicit |
| Footnote 1 | CINEA, no date | 3 April 2025 | |
| Footnote 31 | "see footnote on the central path" | "see footnote 25" | |

Wording fixed for accuracy: Salzgitter deferred *decisions* on stages 2–3 to
2028–2029 (Eurometal, Hydrogen Central); the gas price "more than tripled from
its January level" (the source compares with January, not with March); the
central and BloombergNEF paths are nominal, then converted to 2026 euros; cement
uses carbon capture, not electrification. Figures 5 and 7 now use true minus
signs; Figure 1 gives ArcelorMittal's country. Table A1 was tightened so it no
longer leaves two rows on a last page in Word. `check_figures.py`: 77 checks,
0 mismatches; `tests/test_plant_case.py`: 30 passed.

---

## 7. History: the 20 October cross-check (Draft 1 → Draft 2)

Draft 1's headline numbers came from a "steel cross-check case" that was not
in the repository. It became `analysis/plant_case.py`, and writing it down
exposed these errors, all fixed in Draft 2:

| # | Where | Problem | Done |
|---|---|---|---|
| 1 | Draft annex | Case not in the repo; nothing could be re-run | `analysis/plant_case.py` + tests |
| 2 | Footnote 3 (comment 159) | Assumed a switching plant loses its allocation | Allocation retained (DRI under the hot-metal benchmark since Delegated Regulation 2024/873); carbon value E×P; "lost" as a sensitivity |
| 3 | Annex | 8% real discount rate on nominal prices | Paths deflated at 2% a year |
| 4 | Annex eq (3) | Two hydrogen intensities (55 and 57.2 kg/t) | One: 143kt a year |
| 5 | "Turns negative around 2029" | Explained by the 2029–30 CBAM step, ignoring the four-year build | FID-year model; 2029 holds, driven by the support window and the reline |
| 6 | Footnote 2 | Proposal schedule linear to 2038 | 15% held 2034–37, none from 2038 |
| 7 | "Timing is more robust" | Rested on a correlation manufactured by the grid | Removed |
| 8 | Method | LSM and Sobol claimed but absent | Implemented; LSM checked against an exact lattice |
| 9 | Table 2 | Sector CfD effects with no model behind them | Dropped; steel CCfD analysis instead |
| 10 | Core model eq (4) | Clean-route residual emissions treated as covered while the incumbent's allocation is sold | Reported (`analysis/allocation_check.py`), not applied |
| 11–12 | `analysis/verify.py`, `tests/test_market.py` | Network access during a render; offline test failure | Fixed |
