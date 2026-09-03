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
python run_all.py     # 13 sections, ~40 s, exits non-zero if anything fails
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
  *_cache.json         committed, so the model runs with no network

analysis/            studies that run on the model without changing it
  findings.py          the five structural findings and their evidence
  grounding.py         each input vs the statistic that bears on it, with a verdict
  sourcing.py          the hydrogen sourcing frontier

reporting/           generated deliverables — nothing imports these
  sources.py           -> SOURCES.md, the provenance register (audited)
  plots.py             -> charts.html, nine SVG charts, no matplotlib
  surface.py           -> surface.html, rotatable 3D fleet surface
  findings_report.py   -> findings.html, the derivations in full
  article.py           -> article.html, the written piece
  explorer.py          -> explorer.html, the interactive frontier

run_all.py           every section, in order
selfcheck.py         38 stdlib assertions, for when pytest is unavailable
```

`data/` sitting *below* the model is deliberate. If a provider could import
`timing_model`, it would be a short step to shaping a series to suit an
assumption, so a test forbids it outright.

## Running it

```
python run_all.py               # gate, ladders, reconciliation, pages, checks
python selfcheck.py             # 38 assertions, standard library only
python -m pytest tests          # 219 tests
python -m analysis.sourcing     # the frontier, as a table
python -m analysis.grounding    # inputs against observed data
python -m reporting.explorer    # rebuild explorer.html
```

Generated artefacts land at the repo root and are gitignored: `charts.html`,
`findings.html`, `surface.html`, `article.html`, `explorer.html`,
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
| `gate` | 9 | re-derived by the validation gate on every run |
| `sourced` | 24 | a primary, openly reachable publication says this |
| `observed` | 5 | an official statistic, cached with its period |
| `assumed` | 17 | a modelling choice with a rationale and no external authority |
| `fitted` | 1 | solved backwards from a published result |
| `unverified` | 3 | rests on a document nobody here has opened |

The one fitted constant is `gamma = 0.4442`, the H2-DRI capacity growth rate,
solved from `NPV(2029) = 1588.3` with everything else held at its sourced or
published value. It lands inside the 43–52%/yr band implied by published EU
capacity plans, which is corroboration, not derivation.

The three `unverified` entries are the live to-do list: the €8.29/kg Platts
assessment (licensed, taken from the specification), and the COM(2026)
free-allocation floor and its year range (mechanism confirmed, annex not read
line by line). Tests fail if any of them is ever presented as sourced.

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
| NPV at `T*` | €1,588.29 / t capacity, discounted to 2026 |
| trigger `p*'` | €109.52 / tCO₂ |
| crossing year | 2030 |

The peak is nearly flat — 2028 gives €1,573 and 2030 gives €1,581 — so 2029 is
a window, not a date. One year past it the picture changes sharply: 2033 drops
to €1,062, because the €200/t support window has closed and the reline decision
has already been taken.

**Correction ladder**, cumulative, each row adding one fix:

| Row | `T*` | NPV | trigger |
|---|---|---|---|
| published base | 2029 | 1,588 | 109.5 |
| + load factor 0.85 | 2030 | 1,294 | 109.5 |
| + hot-metal conversion κ = 0.94 | 2030 | 1,166 | 116.9 |
| + real rather than nominal | 2031 | 754 | 116.9 |
| + hydrogen at €8.29/kg | beyond horizon | −49 | 366.9 |

Rows 1–3 reproduce the published table exactly. Rows 4–7 do not; see
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
2. **Utilisation inverts at €7.17/kg hydrogen.** Above it, running the plant
   *less* raises NPV, because `u` multiplies a flow that has gone negative. A
   covenant written around a minimum utilisation would point the wrong way.
   (Caveat: this is the sign of a sensitivity on an NPV-negative case.)
3. **Past 16 years into a campaign, `T*` stops being a choice.** It equals the
   reline date exactly. Value peaks at age 18; the cliff at age 19 is the €200
   of support forfeited by committing before the window opens in 2028.
4. **The trigger's robustness to the discount rate is cancellation.** Taking
   `r` from 6% to 10% moves the break-even +304% and the option multiple −68%.
   Report the two factors, not the product.
5. **The correlation matrix would mislead you.** Across 81 scenarios NPV and
   the trigger correlate −0.87, contradicting finding 1. The ensemble
   manufactured the correlation; the structure says the true value is zero.

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
   3.36% nominal, 1.23% real after HICP. Given finding 4, that decomposition is
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

## Verification

| Layer | What it covers |
|---|---|
| validation gate | nine published quantities to 1e-3 relative, before anything prints |
| feasibility guards | `r − mu`, `u ∈ (0,1]`, monotone allocation, non-negative residual, capex clamp — all raise, never return a flag |
| 219 pytest tests | units, layering, findings, provenance, observed data, generated pages |
| 38 self-checks | the same load-bearing claims with no third-party packages |
| diff harness | 50-case grid, self-diff, and a negative control that must flag exactly two |
| `ruff` | clean on `F, E, W, I, UP, B, C4, SIM, RET`; config and exceptions in `pyproject.toml` |

Two of those exist because of specific misses. `tests/test_reporting.py` builds
every page, because a variable rename once passed the linter and the whole unit
suite and then broke three pages: code that only runs inside `run_all.py` is
code that is tested nowhere. And the provenance audit exists because editing
docs by string replacement silently no-ops on a miss, which cost three README
sections once.

**What none of this covers.** The model has never been diffed against the
MATLAB reference, because there is no reference. The harness, the fixture and
the negative control are built and tested; drop a reference CSV beside them and
`diff()` completes.

## Known limitations

| Item | Published | Computed | Cause |
|---|---|---|---|
| ladder row 4 `T*` | 2030 | 2031 | level right to €1; the peak is €8 late on a curve that is flat across 2030–2032 |
| ladder rows 5–7 NPV | −188 | −49 | at `a = −373` the curve rises monotonically to 2050 and the published value sits on it around 2044. `T*` = "beyond horizon" reproduces, which is the row's actual finding |
| F8 vintage delta | +7.82 / −122 | +8.97 / −161 | `f_com2026(t)` reconstructed, not read off the legal annex |

Two places where the specification's own text does not hold, both pinned by
tests:

- **As `σ → 0` the option multiple does not go to 1.** It goes to `r/(r−mu)` =
  2.667. Waiting is rewarded by the drift alone; the multiple collapses to 1
  only if the drift is zero too.
- **"Never" is wrong for the trigger at market volatility.** At `σ = 0.45` the
  trigger is €202.5 and the path crosses it in 2043. The correct phrasing is
  "beyond any recognisable investment horizon".

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
