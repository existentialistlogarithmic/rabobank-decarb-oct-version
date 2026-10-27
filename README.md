# timing_model — steel decarbonisation investment timing

Python implementation of the RaboResearch industrial decarbonisation
investment-timing model (real options + NPV), following the v12 restructure and
coding specification.

A European integrated steel producer has to pick one year `T` to switch
irreversibly from blast furnace to H2-DRI-EAF. The model picks it two ways —
by maximising NPV over the commitment year, and by a Dixit–Pindyck real-options
trigger on the carbon price — and reports where the two disagree.

Python 3.11+. **No third-party dependencies.** `pytest` is optional.

```
python run_all.py     # 13 sections, exits non-zero if anything fails
                      # ~40 s from the caches; longer on a cold fetch
```

Read `CALIBRATION.md` before quoting a number, and `SOURCES.md` before calling
one sourced.

---

## Contents

| Section | |
|---|---|
| [What it computes](#what-it-computes) | the four outputs, and why there are four |
| [Repository layout](#repository-layout) | four layers, import direction enforced |
| [Running it](#running-it) | entry points and generated artefacts |
| [Where the numbers come from](#where-the-numbers-come-from) | sourced / observed / assumed / fitted |
| [Results](#results) | base case and the correction ladder |
| [Findings](#findings) | twelve, in three groups |
| [The sourcing frontier](#the-sourcing-frontier) | the largest single correction |
| [Verification](#verification) | what is tested, and what that does not cover |
| [Known limitations](#known-limitations) | what does not reproduce, and why |

---

## What it computes

Four outputs, because the decision has two halves and each half has a "when"
and a "whether".

| Output | Question | Contains an option premium? |
|---|---|---|
| `T*` | Which year maximises NPV? | No |
| `T_exp` | Last year in which deferral still adds value | No |
| `p*'` | Carbon price at which committing beats waiting | Yes |
| crossing year | First year the price path reaches `p*'` | Yes |

`T*` and the crossing year routinely differ by one to two years. That gap is
the option premium expressed in time, not an inconsistency. The report layer
refuses to print either without the conditions it was computed under.

**Unit discipline.** The largest error class in this project is euros per tonne
of *annual capacity* against euros per tonne of *product*. Capex, support and
every NPV are per tonne of capacity; the operating penalty, the benefit flow
and the carbon terms are per tonne of product. The load factor `u` is the only
bridge between them — it multiplies `B(t)` and never `I'(T)` — and an AST test
fails the build if `cost.py` so much as names it.

## Repository layout

Four layers. Imports run one way only, and `tests/test_layering.py` walks the
AST to prove it, so you can stop reading at any layer boundary and still have
something that runs.

```
timing_model/        the model — 11 modules in strict group order
  params.py            dataclasses; every field carries unit, currency year, source
  primitives.py        Group I:   b, a(p_H2), CRF, MAC        [MAC is diagnostic]
  benefit.py           Group II:  alpha_v(t), B(t)
  cost.py              Group III: L(T), s(T), S_s(T), I'(T)
  objective.py         Group IV:  npv(T), t_star, t_exp, delta(T)
  option.py            Group V:   p'_M, beta, trigger, crossing_year
  validate.py          gate + feasibility guards; raises, never returns a flag
  results.py           Outputs, welded to the conditions they hold under
  scenarios.py         ladder, storylines, sourced ranges, legacy fixture
  diff_harness.py      50 reference cases + the MATLAB diff
  report.py            tables + CSV

data/                observed inputs — may NOT import the model
  observed.py          shared series type; the fetch-then-cache contract
  eurostat.py          energy prices, producer prices, capacity utilisation
  ecb.py               yield curve and policy rate
  eex.py               EU ETS auction record: the carbon price, and who got the money
  *_cache.json         committed, so the model runs with no network

analysis/            studies that run on the model without changing it
  findings.py          the five structural findings and their evidence
  grounding.py         each input vs the statistic that bears on it, with a verdict
  sourcing.py          the hydrogen sourcing frontier
  regimes.py           the scenario map: which decision each situation implies
  reconcile.py         the model against every published v11 quantity
  market.py            the model against the live market, in euros
  cashflow.py          the four inputs over TIME, and the cash flow they make
  plant_case.py        the October article's 2.5 Mt plant in money: every number it quotes
  allocation_check.py  eq (4)'s carbon terms against benchmark x activity allocation

reporting/           generated deliverables — nothing imports these
  sources.py           -> SOURCES.md, the provenance register (audited)
  brief.py             -> brief.html + brief.pdf, the two-page version to send on
  handoff.py           -> handoff.pdf, the deck brief: 2 figures + all the data
  results.py           -> results.html, START HERE: every table, named and explained
  figures.py           the figure registry: every chart + its full explanation
  gallery.py           -> gallery.html, all 19 figures + 10 tables, titles only
  explained.py         -> explained.html, the same 29, 300+ words on each
  plots.py             -> charts.html, 19 SVG charts, no matplotlib
  surface.py           -> surface.html, rotatable 3D fleet surface
  findings_report.py   -> findings.html, the derivations in full
  article.py           -> article.html, the written piece
  explorer.py          -> explorer.html, the interactive frontier
  deck.py              -> deck.html, the 40-minute talk

run_all.py           every section, in order
selfcheck.py         38 stdlib assertions, for when pytest is unavailable
```

`data/` sitting *below* the model is deliberate. If a provider could import
`timing_model`, it would be a short step to shaping a series to suit an
assumption, so a test forbids it outright.

## Running it

```
python run_all.py               # gate, ladders, reconciliation, pages, checks
python selfcheck.py             # 42 assertions, standard library only
python -m pytest tests          # 305 test functions, 420 cases after parametrisation
python -m analysis.sourcing     # the frontier, as a table
python -m analysis.grounding    # inputs against observed data
python -m analysis.regimes      # the scenario map and the what-ifs
python -m analysis.reconcile    # the model against the v11 specification
python -m reporting.brief       # -> brief.pdf, two pages, for sending on
python -m reporting.handoff     # -> handoff.pdf, self-contained deck brief
python -m analysis.verify       # re-derive every table cell from its raw source
python -m reporting.results     # -> results.html, the step-by-step walkthrough
python -m reporting.gallery     # -> gallery.html, every graph and table, no prose
python -m reporting.explained   # -> explained.html, 300+ words on each of them
python -m analysis.tables       # the finalised tables, one per review comment
python -m analysis.units        # what the per-tonne figures are in actual money
python -m analysis.sourced      # the published case against the sourced one
python -m analysis.market       # assumptions vs the live market, in money
python -m analysis.cashflow     # capex/opex/subsidy/CO2 by year -> payback
python -m analysis.plant_case   # every number in the October article, re-run
python -m analysis.allocation_check  # free allocation after a switch: eq (4) checked
python -m data.eex              # what the EU ETS auctions cleared at, and paid out
python -m data.sourced          # what the research pass returned, and how much is linked
python -m reporting.explorer    # rebuild explorer.html
python -m reporting.deck        # rebuild deck.html
```

Generated artefacts land at the repo root and are gitignored: `charts.html`,
`findings.html`, `surface.html`, `article.html`, `explorer.html`, `deck.html`,
`python_results.csv`. `SOURCES.md` is generated too but committed, because it
is meant to be read in the repository — do not edit it by hand.

The validation gate runs first and raises on failure. Nothing downstream prints
if the nine published quantities do not reproduce: a number that has not been
checked against its reference is worse than no number.

## Where the numbers come from

`reporting/sources.py` holds one entry per model input and generates
`SOURCES.md`. It is executable rather than prose because a hand-maintained
bibliography drifts within a week — a default moves, the markdown does not, and
the citation now vouches for a number nobody uses. `audit()` fails the run if
any parameter is uncited, cited twice, or quotes a value the model no longer
runs on.

Inputs are classified by **what would falsify them**, not by whether a link
exists:

| Status | Count | Meaning |
|---|---|---|
| `gate` | 20 | re-derived by the validation gate, or read off the specification |
| `sourced` | 21 | a primary, openly reachable publication says this |
| `observed` | 7 | an official statistic, cached with its period |
| `assumed` | 17 | a modelling choice with a rationale and no external authority |
| `fitted` | 1 | solved backwards from a published result |
| `unverified` | 1 | rests on a document nobody here has opened |

The one fitted constant is `gamma = 0.4442`, the H2-DRI capacity growth rate,
solved from `NPV(2029) = 1605.9` with everything else held at its sourced or
published value. It lands inside the 43–52%/yr band implied by published EU
capacity plans, which is corroboration, not derivation.

One `unverified` entry remains: the €8.29/kg Platts assessment, which is
licensed market data taken from the specification. A test fails if it is ever
presented as sourced. The COM(2026) allocation schedule used to be the other
two — it is now read off the specification's own annex.

### The live half

Three sources are fetched rather than quoted, and cached so a run with no
network produces the same numbers and says it did:

| Source | What it grounds |
|---|---|
| Eurostat | industrial electricity and gas, producer prices, HICP, capacity utilisation |
| ECB | the yield curve and policy rate behind the 8% hurdle |
| **EEX** | the EU ETS auction record: the carbon price, its realised volatility, and the money every member state and fund received |

The EEX feed is the one that grounds the model's own state variable. `p` in
eq (1) is the EUA price and the build had no observation of it at all until
`data/eex.py`; the note here used to say a carbon price needed a market-data
terminal, which was wrong. `analysis/market.py` puts each observation next to
the assumption it bears on and states the gap in euros — `T8 market` on
`results.html`.

**It recalibrates nothing.** `Params()` still carries the published base case
and every other table is unchanged by what cleared this morning. The gap is
reported; the parameter is left alone, and a test asserts that.

### Observed data

26 series from Eurostat and the ECB, fetched once and committed to
`data/*_cache.json`. A test patches each provider's fetch function to raise and
asserts an offline run still produces every number — a model whose output
depends on whether a web service answered this morning is not reproducible.

| Series | Grounds |
|---|---|
| Euro-area HICP | the deflator (2.1% observed against 2.0% assumed) |
| Industrial electricity, band IE, 9 states | the green hydrogen floor |
| Industrial gas, band I5, 9 states | the grey hydrogen floor |
| Producer prices, capital goods and basic metals | currency-year restatement |
| Capacity utilisation, euro area | the load factor |
| ECB 10Y AAA yield, policy rate | the discount rate's decomposition |

`analysis/grounding.py` puts each input next to the statistic that bears on it
and states a verdict — `consistent`, `optimistic`, `below observed floor`, or
`contradiction`. It changes nothing. An observed statistic is not automatically
the right model input: a risk-free rate is not a hurdle rate, and all-industry
utilisation is not blast-furnace load. Adopting the observed real risk-free
rate as `r` would trip the model's own `r − mu` guard, and there is a test that
demonstrates it.

## Results

Base case, exactly as published:

| | |
|---|---|
| `T*` | 2029 |
| NPV at `T*` | €1,605.94 / t capacity, discounted to 2026 |
| trigger `p*'` | €109.52 / tCO₂ |
| crossing year | 2030 |

The peak is nearly flat — 2028 gives €1,604 and 2030 gives €1,589 — so 2029 is
a window, not a date. The cliff comes later and is sharp: €1,058 in 2038 and
€712 in 2039, because the reline falls due and the €200/t support window has
long closed.

**Correction ladder**, cumulative, each row adding one fix:

| Row | `T*` | NPV | trigger |
|---|---|---|---|
| published base | 2029 | 1,606 | 109.5 |
| + load factor 0.85 | 2029 | 1,303 | 109.5 |
| + hot-metal conversion κ = 0.94 | 2030 | 1,174 | 116.9 |
| + real rather than nominal | 2031 | 755 | 116.9 |
| + hydrogen at €8.29/kg | beyond horizon | −129 | 366.9 |

Every commitment year, trigger and crossing year in the specification
reproduces. The NPV *levels* run about one per cent high; see
[Known limitations](#known-limitations).

## Findings

Twelve, in three groups. Each is derived by code, printed by `run_all.py`, and
pinned by a test so it cannot invert silently.

**Structural** — `analysis/findings.py`, from the model alone:

1. **The levers are exactly orthogonal.** Five parameters move NPV and leave
   the trigger at 0.000%; two move the trigger and leave NPV at 0.000%; four
   move both. The trigger formula does not contain the load factor, resale,
   support or the price path. A CfD and a grant are therefore complements, not
   substitutes — they act on different halves of the decision.
2. **Utilisation inverts at €6.15/kg hydrogen.** Above it, running the plant
   *less* raises NPV, because `u` multiplies a flow that has gone negative. A
   covenant written around a minimum utilisation would point the wrong way.
   (Caveat: this is the sign of a sensitivity on an NPV-negative case.)
3. **Past 17 years into a campaign, `T*` stops being a choice.** For ages 0–16
   the year is set by economics; from 17 on it equals the reline date exactly
   and the calendar decides.
4. **The trigger's robustness to the discount rate is cancellation.** Taking
   `r` from 6% to 10% moves the break-even +304% and the option multiple −68%.
   Report the two factors, not the product.
5. **The correlation matrix would mislead you.** Across 81 scenarios the
   strongest opposition is `T*` against NPV at −0.96. Read as a statement about
   levers it contradicts finding 1; the ensemble manufactured it, and the
   structure says the true value is zero.

**From observed data** — `analysis/grounding.py`:

6. **€2.60/kg is a fossil hydrogen price.** It sits below every green floor
   (€3.94–8.05/kg, electricity alone) and inside the grey band (€2.00–2.36/kg,
   gas plus its ETS cost). Grey hydrogen emits 9 kgCO₂/kg, i.e. 0.49 tCO₂ per
   tonne of steel at 55 kg H₂/t — five times the `eps_cln = 0.1` the model
   credits the clean route with. **The price and the intensity cannot both
   hold.**
7. **`u = 0.85` is optimistic.** Euro-area capacity utilisation is 78.2%
   (2025-Q4). The published base row runs `u = 1.00`, a furnace that never
   stops.
8. **The currency year cuts both ways.** Since 2022 capital goods are +8.4%
   while steel output prices are −11.0%. Per-capacity terms are quoted in a
   trough year and per-product terms in a peak one, in a model whose central
   error class is confusing the two.
9. **The 8% hurdle rate is a 6.8pp risk premium.** The ECB 10Y AAA yield is
   3.39% nominal, 1.26% real after HICP. Given finding 4, that decomposition is
   load-bearing.

**From the sourcing frontier** — `analysis/sourcing.py`, below.

## The sourcing frontier

The model asks for a hydrogen price and a clean-route emission intensity as two
independent inputs. Physically they are one: hydrogen is bought somewhere
between reformed gas and electrolysed power, and where you buy it sets the
price *and* the emissions. Tie them to a single parameter, the green share `θ`:

```
p_H2(θ)    = θ·green + (1−θ)·grey_gas
eps_cln(θ) = 0.1 + (1−θ)·0.495
```

Reforming emits CO₂ once, so it is charged once — through `eps_cln`, where the
model's carbon path and free allocation apply to it. That is why `grey_gas` is
the gas cost *without* its ETS component; charging it in the price as well
would double-count. The base case does the reverse: it takes the grey price and
books the green emissions.

10. **Fossil hydrogen wins on NPV in every member state, monotonically in θ.**
    Going green buys abatement worth `Δb·p` and costs `m_H2·(green − grey)`;
    at €76–112/tCO₂ the cost side wins. Green needs 2.0× the central path in
    Sweden and 6.5× in Italy to overtake:

    | | SE | FR | ES | PL | BE | NL | DE | AT | IT |
    |---|---|---|---|---|---|---|---|---|---|
    | 2026 EUA needed | €152 | €193 | €308 | €322 | €359 | €383 | €471 | €484 | €496 |
    | × central path | 2.0 | 2.5 | 4.1 | 4.2 | 4.7 | 5.0 | 6.2 | 6.4 | 6.5 |

    The ordering follows the **absolute €/kg spread** between the two routes,
    not the power-to-gas ratio. Both sides of the crossover are differences, so
    no ratio enters it, and the ratio ordering is genuinely different — PL/ES
    and DE/AT/IT swap. A test asserts that the spread explains the ordering
    *and* that the ratio does not, because "obvious" is how the wrong mechanism
    gets published.
11. **Sourcing moves the commitment year by up to 17 years** — 2028 all-grey,
    2032 (SE, FR) to 2045 (AT, IT) all-green. It is a timing lever, and the
    model treats it as a cost axis.
12. **The published pair costs 22.6–33.5% of NPV.** €2.60/kg with
    `eps_cln = 0.1` is not a point anyone can occupy. Hold the price, make the
    intensity consistent with it, and NPV falls by that much. That share of the
    published number was never available at any sourcing decision.

`explorer.html` makes this explorable: pick a member state, drag the green
share and the carbon path, and watch value, commitment year and trigger move
together against the published NPV. The model is **not** reimplemented in
JavaScript — 891 runs are computed in Python and embedded, the page selects and
draws, and a test recomputes every embedded point and fails if the two ever
disagree.

## The talk

`deck.html` is a presentation generated from the same model run — 20 slides in
eight sections timed to 39 minutes, with speaker notes (`n`), a slide grid (`g`)
and a rehearsal timer (`t`). It prints one slide per page.

Every figure in it is drawn from a live model run at build time, and **every
figure slide carries the equation that produced it plus a table saying what
each symbol means and what value it takes here**. Equations are MathML, which
browsers render natively — no library, no CDN. Tests assert the timings sum
into the slot, that no figure appears without an equation, and that the
headline numbers on the title slide match a fresh `outputs()` call.

## Verification

| Layer | What it covers |
|---|---|
| validation gate | nine published quantities to 1e-3 relative, before anything prints |
| feasibility guards | `r − mu`, `u ∈ (0,1]`, monotone allocation, non-negative residual, capex clamp — all raise, never return a flag |
| 305 test functions | units, layering, findings, provenance, observed and live data, the specification, generated pages, the article's plant case — 420 cases after parametrisation |
| 42 self-checks | the same load-bearing claims with no third-party packages |
| diff harness | 50-case grid, self-diff, and a negative control that must flag exactly two |
| `analysis/verify.py` | 145 table cells re-derived from the raw CSV cell or cached series, compared at the precision each one displays |
| `ruff` | clean on `F, E, W, I, UP, B, C4, SIM, RET`; config and exceptions in `pyproject.toml` |

Three of those exist because of specific misses. `tests/test_reporting.py`
builds every page, because a variable rename once passed the linter and the
whole unit suite and then broke three pages: code that only runs inside
`run_all.py` is code that is tested nowhere. The provenance audit exists
because editing docs by string replacement silently no-ops on a miss, which
cost three README sections once. And `tests/test_market.py` proves the auction
workbook's columns are the columns the parser thinks they are — by checking
that revenue ÷ volume equals the price column on every row, which it must,
because a uniform-price auction has exactly one clearing price. That check
found a real bug: blank cells in the per-recipient columns store an index into
the workbook's shared string table, and reading the index as a number gave
states that received nothing a few euros each.

**What none of this covers.** The model has never been diffed against the
MATLAB reference, because there is no reference. The harness, the fixture and
the negative control are built and tested; drop a reference CSV beside them and
`diff()` completes.

## Reading the units

Every stock in the model — capex, support, write-off, and every NPV — is **EUR
per tonne of annual nameplate capacity**. Not per tonne of steel, and not a
total. `I0 = 900` is therefore not €900; it is **€2.2bn for a 2.5 Mt/yr works**.

That is checkable, and `analysis/units.py` checks it: each per-tonne figure in
`data/sourced/projects_capex.csv` came from an operator's announced total
divided by their announced capacity, so dividing again has to land back on it.

| project | announced | capacity | €/t capacity |
|---|---|---|---|
| Dunkirk EAF | €1.2bn | 2.0 Mt/yr | 600 |
| Bremen + Eisenhüttenstadt | €2.5bn | 3.5 Mt/yr | 700 |
| tkH2Steel Duisburg | €3.0bn | 2.3 Mt/yr | 1,300 |
| SALCOS stage 1 | €2.7bn | 1.9 Mt/yr | 1,420 |
| Boden (Stegra) | €6.5bn | 2.5 Mt/yr | 2,600 |
| **this model, `I0`** | **€2.2bn** | 2.5 Mt/yr | **900** |

Flows are a different denominator: `a`, `B(t)` and `c_avoided` are per tonne of
steel **made**, per year, and the load factor `u` is the only bridge between the
two families. An AST test fails the build if `cost.py` so much as names `u`.

## The sourced recalibration

`analysis/sourced.py` puts the published base case next to one built from
primary documents (`data/sourced/`, narrative in `docs/research-findings.md`).
It reports; it does not recalibrate. `Params()` still carries the published
case and the gate still reproduces the published nine.

| case | I0 | p_H2 | a | trigger | T* | NPV | crossing |
|---|---|---|---|---|---|---|---|
| published | 900 | 2.60 | −60 | 109.5 | 2029 | 1,606 | 2030 |
| low | 1,200 | 3.69 | −120 | 172.4 | 2031 | 991 | 2039 |
| central | 1,420 | 5.00 | −192 | **239.4** | 2038 | 537 | **2046** |
| high | 2,600 | 8.65 | −393 | 460.4 | — | −124 | beyond |

The base case is not wrong arithmetically. It is optimistic on every input that
matters, and the errors compound the same way: capex below every surviving
project, a hydrogen price that is a fossil price, a furnace that never stops,
and a volatility that is a choice. All four rows reproduce the research pass's
own table to €0.1.

Three findings are structural rather than numerical. Support is a **stream**
(the German CCfD pays per tCO₂ over fifteen years; at €20–50/tCO₂ that is
€261–652/t of capacity against a €200 lump). Capex is a **distribution with a
scope boundary** — whether the electrolyser is inside it moves the figure about
2×. And every project still being built costs ≥ €1,300/t; the two under €900 are
an EAF-only retrofit and a scheme ArcelorMittal cancelled, forfeiting €1.3bn of
approved aid.

**Provenance caveat.** 9 of 98 research rows carry a captured URL. The rest name
a source without linking it — `unverified` here, not `sourced`. Nothing has been
promoted into the register, and a test fails if link coverage rises above 50%
without the statuses being revisited.

## The October article: the reference plant in money

`analysis/plant_case.py` is the "steel cross-check case" the October draft of
the article quotes from, written down so its numbers can be re-run: a 2.5 Mt/yr
H2-DRI-EAF plant, 3.5 MtCO2/yr avoided, 143 kt/yr of hydrogen, EUR 3bn of capex
built over four years from the FID. It reuses this model's allocation
schedules, central path, support window and reline year, and adds what the
article needs and the per-tonne model does not have: a construction lag, real
2026 euros throughout, and an option layer solved two ways (an exact binomial
lattice and Longstaff-Schwartz least-squares Monte Carlo, which a test holds
within 3% of each other).

Review corrections it carries, each pinned by a test: a switching plant keeps
its free allocation (the hot-metal benchmark has covered DRI since Delegated
Regulation (EU) 2024/873), so the carbon value of switching is `E x P`, not
`E x P x s(t)`; nominal analyst prices are deflated before discounting at 8%
real; one hydrogen intensity drives the opex. The pre-reform path is anchored
on BloombergNEF's April 2026 estimates (non-bank sources only, from Draft 3),
and two sensitivities came out of the 27 October source check: a reline at
recent-reline cost (EUR 150m rather than the v11 EUR 525m) and the scale of
operating costs the model does not separate out.

`docs/article/` draws the seven Draft 3 figures from `plant_case.export()` and
`docs/article/check_figures.py` recomputes everything they print and the text
quotes (77 checks). `CROSSCHECK.md` maps every review comment and tracked edit
to Draft 3, logs the source check, and lists what is still open.

## Known limitations

`analysis/reconcile.py` checks the model against every quantity the v11
specification published — inputs as well as outputs — and `run_all.py` prints
the result. **54 of 62 reproduce.** All eight that do not are NPV *levels*, and
all eight are high, by 1.1% to 8.0%:

| Item | Published | Computed | Gap |
|---|---|---|---|
| base case NPV | 1,588 | 1,606 | +1.1% |
| soft / central / tight price paths | 1,155 / 1,588 / 2,339 | 1,247 / 1,606 / 2,370 | +8.0% / +1.1% / +1.3% |
| Booster in full / rationed 30%/yr | 1,588 / 1,570 | 1,606 / 1,604 | +1.1% / +2.2% |
| policy vintages, law2023 / com2026 | 1,581 / 1,588 | 1,606 / 1,614 | +1.6% / +1.6% |

Not one input, commitment year, trigger or crossing year differs. One tolerance
judges all eight (`NPV_TOL = 5`, the rounding on the published figures); an
earlier version used 5 for the base case and 25 elsewhere, so the identical
1,588-vs-1,606 comparison read as a pass in one section and a difference in
another, and a test now pins the single standard.

Closing the level gap by moving an input would break the §4.3 age ladder, which
reproduces exactly across twelve values and is the stronger constraint. So it is
documented rather than tuned away.

**Free allocation after the switch.** `analysis/allocation_check.py` shows
that eq (4) adds `u * alpha * eps_cln * p` to the carbon value of switching:
the clean route's residual emissions are treated as covered free while the
incumbent's whole allocation is also sold. With allocation tied to activity
rather than emissions, the value with resale is `b * p`. The term is small,
but it is the whole of the "+7.82 vintage delta with resale", and removing it
moves the base NPV from 1,605.9 to 1,589.1, onto the v11 figure of 1,588 (five
of the eight NPV-level gaps close). It is reported, not applied, because it
moves every published level and the fitted `gamma`; the decision is the team's.

Three places where the specification's own text does not hold, all pinned by
tests:

- **As `σ → 0` the option multiple does not go to 1.** It goes to `r/(r−mu)` =
  2.667. Waiting is rewarded by the drift alone; the multiple collapses to 1
  only if the drift is zero too.
- **"Never" is wrong for the trigger at market volatility.** At `σ = 0.45` the
  trigger is €202.5 and the path crosses it in 2043. The correct phrasing is
  "beyond any recognisable investment horizon".
- **The eq (11) hand check conflates doublings with years.** Eq (2) works
  Wright's law over *doublings* and gets 0.614 at three of them — which is how
  `I0 = 900` is derived. The worked NPV then reuses 0.62 for a commitment three
  *years* out, which would need deployed capacity to double annually. The model
  converts through the deployment growth rate: three years at `gamma = 0.4442`
  is 1.59 doublings, so `L(2029) = 0.773`.

The published §3.3 ranges for `a` and `p_H2` also contradict each other: the
`a` band is (−320, −25), but `a(2.50) = −54.5` and `a(8.29) = −372.95`, so the
top of the hydrogen band falls below the bottom of the `a` band. The model uses
the endogenous `a(p_H2)`.

## Three decisions the code will not make for you

Appendix A §3.5 reserves these. They are left at their published values so that
they have to be chosen deliberately rather than inherited.

1. **Support basis** — a lump-sum capex grant or a per-tCO₂ stream. The stream
   belongs in `B(t)` structurally; the lump is what was published.
2. **Resale** — `w = 1` drives the entire policy-neutrality finding. Without it
   the headline result reverses sign.
3. **Whether €2.60/kg is reported as the base case at all.** Findings 6 and 12
   say it is a fossil price carrying green emissions, at a cost of a quarter to
   a third of the NPV.

## Status

The validation gate, the trigger column, the benefit side and ladder rows 1–3
reproduce exactly. Rows 4–7 do not, and each is documented with its cause.
`timing_model.m` was never available, so five of the six cost-side constants
were sourced from published industry data and one was calibrated.

`HANDOFF.md` carries the locked numbers, the open items and the traps.
