# Handoff — steel decarbonisation investment-timing model

The running state of the build. Everything below is verified as of the last
commit on this branch.

**Repo:** `existentialistlogarithmic/rabobank-decarbonization-final-version`
**Branch:** `main` (single branch; history was flattened to one root commit)

**Run everything:** `python run_all.py` (13 sections, ~40 s). Python 3.11+,
**zero dependencies**; `pytest` and `ruff` optional. Currently **273 tests +
40 self-checks** green, ruff clean, `run_all` exits 0.

**Read in this order:** this file → `CALIBRATION.md` (sourced vs fitted) →
`SOURCES.md` (generated; what each input claims and what would falsify it).

---

## 1. What this is

A real-options investment-timing model. A European steel producer picks one year
`T` to switch irreversibly from blast furnace to H2-DRI-EAF. The model maximises
`NPV(T)` and separately computes a carbon-price trigger via a Dixit–Pindyck
option multiple. Four outputs: `T*`, `T_exp`, the trigger `p*'`, and the year the
price path crosses it.

Built from a v12 specification. The MATLAB reference (`timing_model.m`) was
**never available**, which is the root of most open items below.

## 2. Files

| Path | What it is |
|---|---|
| `timing_model/` | The model. 11 modules in strict group order (params → primitives → benefit → cost → objective → option → validate → results → scenarios → report). Import direction enforced by an AST test. |
| `data/observed.py` | Shared series type and the offline caching contract |
| `data/eurostat.py` | Energy prices, producer prices, capacity utilisation → `data/eurostat_cache.json` |
| `data/ecb.py` | Yield curve and policy rate → `data/ecb_cache.json` |
| `analysis/findings.py` | Derives the five structural findings + their evidence |
| `analysis/grounding.py` | Model inputs vs observed data, one verdict per row |
| `analysis/sourcing.py` | The hydrogen sourcing frontier: `p_H2` and `eps_cln` as one input |
| `analysis/reconcile.py` | The model against every quantity the v11 specification published |
| `analysis/units.py` | The denominator, restored: EUR/t capacity → money for a real plant |
| `analysis/sourced.py` | The published base case against the Sept-2026 sourced recalibration |
| `data/sourced.py` + `data/sourced/*.csv` | The research pass's parameters, projects, H2 prices, support shapes |
| `docs/research-*.md` | That pass's findings, sources with tiers, and its documented holes |
| `reporting/sources.py` | → `SOURCES.md`, the provenance register — audited against the code on every run |
| `reporting/plots.py` | → `charts.html`, 9 SVG charts, no matplotlib |
| `reporting/surface.py` | → `surface.html`, rotatable 3D fleet surface (Canvas) |
| `reporting/findings_report.py` | → `findings.html`, the derivations in full |
| `reporting/article.py` | → `article.html`, **the finished article** |
| `reporting/explorer.py` | → `explorer.html`, the frontier, interactive (891 embedded model runs) |
| `reporting/deck.py` | → `deck.html`, the 40-minute talk: 20 slides in 8 sections, timed to 39 min; every figure carries its equation |
| `selfcheck.py` | 40 stdlib assertions (works without pytest) |
| `CALIBRATION.md` | What is sourced vs fitted — **read before quoting anything** |
| `SOURCES.md` | Generated. What each input claims and what would falsify it |
| `ARTICLE.md` | Article outline / writing plan |

**Layer rule:** `timing_model` (0) ← `data` (1) ← `analysis` (2) ← `reporting` (3).
Imports run downwards only and `tests/test_layering.py` asserts it. `data/` may
not import the model at all — an observation must not depend on what the model
does with it.

## 3. Locked numbers (verified — do not re-derive)

**Validation gate (all reproduce to 1e-3 relative):** CRF(25,8%) 0.0937 · β 1.3860
· β/(β−1) 3.5907 · p_M 27.50 · MAC 80.17 · p* 98.74 · p'_M 30.50 · MAC' 89.54 ·
**p*' 109.52**

**Base case:** T* 2029 · NPV0 €1,605.94/t capacity · trigger €109.52/tCO₂ ·
crossed 2030 · T_rel 2038

**NPV by year (base):** 2026 1,380 | 2028 1,604 | **2029 1,606** | 2030 1,589 |
2031 1,557 | 2038 1,058 | 2039 712

**Correction ladder** (cumulative; T*, NPV, trigger): base 2029/1606/109.5 →
+load factor 0.85 2029/1303/109.5 → +hot metal κ=0.94 2030/1174/116.9 → +real
2031/755/116.9 → +H₂ €8.29 beyond/−129/366.9

**Reconciliation against the v11 spec:** 54/62 published quantities reproduce.
All eight differences are NPV *levels*, all high, by +1.1% to +8.0%; every
input, commitment year, trigger and crossing year reproduces, including the
full §4.3 age ladder. One tolerance (`NPV_TOL = 5`) judges every level. Run
`python -m analysis.reconcile`.

**Observed data (26 series, cached; Eurostat retrieved 2026-09-03, ECB 2026-09-07).** Euro-area HICP
2.1%/yr · capacity utilisation 78.2% (2025-Q4) · capital-goods PPI 107.0→116.0
and basic-metals PPI 124.7→111.0 (2022→2025) · ECB 10Y AAA 3.39% nominal,
1.26% real.

Industrial electricity €/kWh (band IE, excl. taxes, 2025-S2): SE 0.0716 · FR
0.0782 · ES 0.0991 · PL 0.1058 · BE 0.1115 · NL 0.1134 · DE 0.1363 · AT 0.1419 ·
IT 0.1463. Industrial gas €/kWh (band I5): NL 0.0319 · DE 0.0353 · ES 0.0362 ·
BE 0.0370 · AT 0.0385 · SE 0.0389 · FR 0.0391 · IT 0.0408 · PL 0.0408

**Green H₂ floors** (power only, 55 kWh/kg): SE 3.94 · FR 4.30 · ES 5.45 · DE
7.50 · IT 8.05. Break-even €5.27/kg → **case exists only in Sweden and France**;
Spain misses by €0.18. Where it exists, T* is set by the reline (2038).

**Grey H₂ floors** (gas at 41.1 kWh/kg + 9 kgCO₂ at €76/t): €2.00–2.36/kg. So
€2.60/kg is not a green price anywhere — it is roughly the unabated fossil
price. See finding 6.

## 4. The findings

Findings 1–5 are structural, derived by `analysis/findings.py` from the model
itself. Findings 6–9 come from the observed-data layer and are reported by
`analysis/grounding.py` with a verdict each.

1. **Levers are orthogonal, exactly.** 5 params move NPV and the trigger by
   0.000%; 2 move the trigger and NPV by 0.000%; 4 move both. Structural — the
   trigger formula doesn't contain load factor, resale, support or price path.
   ⇒ a CfD and a grant are complements, not substitutes.
2. **Utilisation inverts at €6.15/kg H₂.** Above it, running the plant *less*
   raises NPV. (Caveat: sign of a sensitivity on an NPV-negative case.)
3. **Reline capture from age 17.** For ages 0–16 the year is set by economics;
   from 17 on, T* equals the reline year exactly — the calendar decides.
4. **Rate "robustness" is cancellation.** r 6→10%: break-even +304%, multiple
   −68%, product +29%.
5. **The correlation matrix misleads.** Across 81 scenarios the strongest
   opposition is T* vs NPV0 at −0.96 — an artefact of the ensemble, not of the
   model, which finding 1 shows has orthogonal levers.

**From the observed data** (`analysis/grounding.py`, verdict in brackets):

6. **€2.60/kg is a fossil hydrogen price** [contradiction]. Below every green
   floor (€3.94–8.05) and inside the grey band (€2.00–2.36 = gas + ETS). Grey
   hydrogen emits 9 kgCO₂/kg, i.e. **0.49 tCO₂/t steel at 55 kg H₂/t — 5× the
   `eps_cln = 0.1` the model credits the clean route with.** The price and the
   intensity cannot both hold. This is the single most actionable thing the
   data says; see open item 10.
7. **`u = 0.85` is optimistic** [optimistic]. Euro-area capacity utilisation is
   **78.2%** (2025-Q4). The published base row runs `u = 1.00` — a furnace that
   never stops. All-industry, not steel: a reference point, not a measurement.
8. **The currency year cuts both ways** [context]. Since 2022 capital goods are
   **+8.4%** while steel output prices are **−11.0%**. Every €/t-capacity term
   is quoted in a trough currency year and every €/t-product term in a peak one
   — in a model whose central error class is confusing the two units.
9. **The 8% hurdle rate is a 6.8pp risk premium** [context]. ECB 10Y AAA is
   3.39% nominal, 1.26% real after HICP. Finding 4 says the trigger's apparent
   robustness to `r` is cancellation, so this decomposition is load-bearing.

**From the sourcing frontier** (`analysis/sourcing.py`; `p_H2` and `eps_cln`
tied into one parameter, the green share θ):

10. **Fossil hydrogen wins on NPV everywhere, monotonically in θ.** At the
    model's own carbon path, going greener only ever costs value. Green needs
    **2.0× (SE, €152/tCO₂) to 6.5× (IT, €496/tCO₂)** the central 2026 price to
    overtake grey. The ordering follows the **absolute €/kg spread** between the
    routes, **not** the power-to-gas ratio — the ratio gives a different, wrong
    ordering, and a test asserts both halves of that.
11. **Sourcing moves `T*` by up to 17 years** — 2028 all-grey, 2032 (SE/FR) to
    2045 (AT/IT) all-green. It is a timing lever the model treats as a cost axis.
12. **The published pair costs 22.6–33.5% of NPV.** €2.60/kg with `eps_cln = 0.1`
    is a grey price with green emissions — off the frontier entirely. Hold the
    price, make the intensity consistent, and NPV falls by that much. This is
    finding 6 quantified.

## 4b. The sourced recalibration (September 2026)

A research pass went back to primary and near-primary documents for every input
the published base case assumes. Its data is in `data/sourced/`, its narrative
in `docs/research-findings.md`, its holes in `docs/research-open-items.md`.
`analysis/sourced.py` runs the model on it and prints the comparison;
`python -m analysis.sourced`.

**The published base case is not wrong arithmetically. It is optimistic on
every input that matters, and the errors compound in one direction.**

| case | I0 | p_H2 | a | trigger | T* | NPV | crossing |
|---|---|---|---|---|---|---|---|
| published | 900 | 2.60 | −60 | 109.5 | 2029 | 1,606 | 2030 |
| low | 1,200 | 3.69 | −120 | 172.4 | 2031 | 991 | 2039 |
| central | 1,420 | 5.00 | −192 | **239.4** | 2038 | 537 | **2046** |
| high | 2,600 | 8.65 | −393 | 460.4 | — | −124 | beyond |

All four rows reproduce the research pass's own table to €0.1, and the `a(p_H2)`
curve matches at five separate prices — the two sides are the same arithmetic on
different inputs, which is what makes the comparison usable.

**Capex.** Every project still under construction or commissioning costs
≥ €1,300/t capacity (tkH2Steel 1,300 · SALCOS 1,420 · Stegra 2,600). The two at
or below the model's €900 are an EAF-only retrofit (Dunkirk, €600) and a scheme
ArcelorMittal **cancelled**, forfeiting €1.3bn of approved German aid (Bremen +
Eisenhüttenstadt, €700). Note the package's own prose says €900 "sits below
every announced transformation project"; its table does not support that —
Bremen is €700. The defensible claim is about the survivors.

**Support shape.** The German CCfD pays a stream per tCO₂ over 15 years, not a
capex lump. At b = 1.8, r = 8%, 10 years: €261/t at €20/tCO₂ rising to €652/t at
€50 — 1.3× to 3.3× the model's €200 lump. Strike prices were not disclosed (H1),
so the premium is inferred from the mechanism, not observed.

**ρ is contested by a factor of three.** Spec 0.35 (R = €210/t) against
Schwelgern's implied 0.08–0.17 (R ≈ €48–102/t). R is a reason to wait, so this
does not cancel.

**σ = 0.20 is a choice, not an observation.** Carbon-VIX puts realised EUA
volatility near 0.45 and the headline average at 0.54, range 0.30–0.83. Across
that range the option multiple runs 2.92 → 14.97, moving the trigger more than
every cost parameter combined.

**Independent confirmation:** `data/sourced/free_allocation.csv` matches both
`F_LAW2023` and `F_COM2026` exactly — but marks `com2026` from 2028
`RECONSTRUCTED`, i.e. a pending proposal, not the legal annex. Our register
cites it to `spec_v11` without that qualifier.

**The provenance caveat, which governs all of the above.** Only **9 of 98**
research rows (9%) carry a captured URL. The rest name a source correctly
without linking it — `unverified` in this project's vocabulary, not `sourced`.
Nothing here has been promoted into `reporting/sources.py`, and
`tests/test_recalibration.py` fails if link coverage rises above 50% without
someone revisiting the statuses. Of the links that *were* captured, most are
Tier C trade press.

## 5. OPEN ITEMS — what to work on next

### Blocked without external data
1. **EUA price series** → measured σ and µ instead of an assumed 4-rung ladder.
   σ is the *only* pure threshold lever (finding 1), so this is the highest-value
   upgrade left. No free feed reachable (Ember API 404, Sandbag no CSV). Needs
   ICE/EEX/Refinitiv.
2. **Per-plant reline dates** → turns `surface.html` into a named target list and
   replaces the calibrated 2032 with real dates.

### Blocked without `timing_model.m`
3. **Ladder rows 4–7 don't reproduce.** Computed NPV −49 vs published −188.
   Rows 1–3 reproduce exactly.
4. **50-case MATLAB diff never run.** Harness + negative control are built and
   tested; no reference CSV exists.
5. **`gamma = 0.4442` is the one fitted constant.** 144 parameter sets fit the
   published ladder equally well. `K_s`/`L_s`/`age0`/`rho` are sourced but jointly
   pinned by `S_s(2026)=360`.

### Doable now
6. **Verify the €8.29/kg Platts figure.** Licensed data taken from the spec.
   Registered as `scenarios.SOURCED_RANGES.p_H2`, status `unverified`, and a test
   in `tests/test_sources.py`
   fails if anything ever quotes it as sourced. Confirm against a subscription.
7. ~~`f_com2026(t)` unchecked against the legal annex.~~ **CLOSED.** Read off
   v11 eq (12); the delta is now +7.70/−122.26 against a published +7.82/−122.
8. **Non-steel sectors** have had no calibration or units review. Publish
   ordering only.
9. **`charts.html` is 9 figures long** — wants sectioning or splitting.
10. **Resolve the `p_H2` / `eps_cln` contradiction** (findings 6, 12). A
    modelling decision, not a data problem: either raise `p_H2` to a green
    floor, which weakens the case, or raise `eps_cln` toward grey, which removes
    most of the abatement the model is valuing. Doing neither means publishing
    two inputs that the observed data says cannot both be true, at a cost of
    22.6–33.5% of NPV. `analysis/grounding.py` flags it and a self-check fails if the
    flag ever disappears without the inputs changing.
11. **Feed the frontier back into the ladder.** `analysis/sourcing.py` runs beside the
    model, not inside it: `timing_model/scenarios.py` still treats `p_H2` as an independent
    axis. Making θ the axis would change the published ladder, so it is a
    decision, not a refactor.

## 6. Known traps

- **€/t capacity vs €/tCO₂ are different units.** The single largest error class
  in this project. Never conflate.
- **Never print a per-tonne figure without its denominator.** `I0 = 900` read
  as "€900" is absurd and invites the reader to dismiss the model; read as
  €900 **per tonne of annual capacity** it is **€2.2bn** for a 2.5 Mt/yr works,
  the same order as the announced projects. `analysis/units.py` does the
  conversion and proves it round-trips off the real announcements
  (€3.0bn ÷ 2.3 Mt = €1,300/t). Run `python -m analysis.units`.
- **NPV is a model output** — no statistical agency publishes it. Only *inputs*
  can be sourced.
- **`T_rel = 2038` is a model output**, not a fact about any plant.
- **A constraint that pins a product does not pin its factors.** `K_s·(L_s−age0)`
  was pinned by `S_s(2026)=360`; the factors chosen were both wrong and it took
  the specification's age ladder to show it. Check inputs, not just outputs.
- **Don't write "never"** about the trigger. At σ=0.45 it's crossed in 2043;
  correct phrasing is "beyond any recognisable investment horizon".
- **The σ half of finding 1 is definitional** (the NPV layer is deterministic by
  construction). The other half is substantive.
- Editing docs with `str.replace()` **silently no-ops on a miss** — this already
  lost three README sections once. Assert the anchor exists. `SOURCES.md` is
  generated for exactly this reason; don't hand-edit it.
- **The crossover ordering follows the price SPREAD, not the ratio.** Both
  sides of the condition are differences. The ratio is the intuitive quantity
  and it ranks the countries differently.
- **`explorer.html` embeds precomputed model output; it does not model.** Never
  reimplement `timing_model` in JavaScript — a test recomputes every embedded
  point and exists to keep that true.
- **A page that only runs inside `run_all.py` is tested nowhere.** A rename
  once passed ruff and the whole unit suite and broke three pages.
  `tests/test_reporting.py` now builds every one of them.
- **A published *schedule* needs checking branch by branch, not by its
  outputs.** `s(t)` (v11 eq 9) was missing its first branch — `0.35·s_max`
  before the Booster window — for the whole life of the build. Both support
  scenarios commit inside the window, so both reproduced their published years
  and the gap never showed. It put a €200 step at 2028 where the spec has €130,
  i.e. the model paid the plant €70/t to wait a year. `reconcile.py` now walks
  every branch of eq (9), plus the €130 step and the +€146 value of waiting.
- **One tolerance per quantity class, or the count means nothing.**
  `reconcile.py` briefly judged the base-case NPV at ±5 and the scenario NPVs
  at ±25, so the identical 1,588-vs-1,606 comparison read as a pass in §4.2 and
  a difference in §3. `NPV_TOL` is now single and a test enforces it.
- **The spec's eq (11) hand check conflates doublings with years** (0.62 at
  three years would need capacity to double annually). The model converts
  through `gamma`; `L(2029) = 0.773`. Pinned by a test so nobody "fixes" it.
- **Observed statistics are not automatically model inputs.** A risk-free rate
  is not a hurdle rate; all-industry utilisation is not furnace load. The
  grounding layer reports disagreements and changes nothing — deliberately.
- **The §3.3 `a` band and the §3.3 `p_H2` band are inconsistent with each
  other.** The published `a` range is (−320, −25), but `a(2.50) = −54.5` and
  `a(8.29) = −372.95`, so the top of the hydrogen band falls below the bottom of
  the `a` band. The model uses the endogenous `a(p_H2)`.

## 7. Suggested next prompt

> I'm continuing work on the steel decarbonisation timing model. Read
> `HANDOFF.md`, `CALIBRATION.md` and `SOURCES.md` first. I want to work on
> [ITEM]. Don't re-derive the locked numbers in HANDOFF.md §3 — they're
> verified. Run `python run_all.py` to confirm the baseline before changing
> anything.
