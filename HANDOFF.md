# Handoff — steel decarbonisation investment-timing model

The running state of the build. Everything below is verified as of the last
commit on this branch.

**Run everything:** `python run_all.py` (13 sections). Python 3.11+, **zero
dependencies**; `pytest` optional. Currently **219 tests + 38 self-checks** green.

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
| `reporting/sources.py` | → `SOURCES.md`, the provenance register — audited against the code on every run |
| `reporting/plots.py` | → `charts.html`, 9 SVG charts, no matplotlib |
| `reporting/surface.py` | → `surface.html`, rotatable 3D fleet surface (Canvas) |
| `reporting/findings_report.py` | → `findings.html`, the derivations in full |
| `reporting/article.py` | → `article.html`, **the finished article** |
| `reporting/explorer.py` | → `explorer.html`, the frontier, interactive (891 embedded model runs) |
| `selfcheck.py` | 38 stdlib assertions (works without pytest) |
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

**Base case:** T* 2029 · NPV0 €1,588.29/t capacity · trigger €109.52/tCO₂ ·
crossed 2030 · T_rel 2032

**NPV by year (base):** 2026 1,252 | 2028 1,573 | **2029 1,588** | 2030 1,581 |
2031 1,556 | 2032 1,520 | 2033 1,062

**Correction ladder** (cumulative; T*, NPV, trigger): base 2029/1588/109.5 →
+load factor 0.85 2030/1294/109.5 → +hot metal κ=0.94 2030/1166/116.9 → +real
2031/754/116.9 → +H₂ €8.29 beyond/−49/366.9

**Observed data (26 series, cached; retrieved 2026-09-03).** Euro-area HICP
2.1%/yr · capacity utilisation 78.2% (2025-Q4) · capital-goods PPI 107.0→116.0
and basic-metals PPI 124.7→111.0 (2022→2025) · ECB 10Y AAA 3.36% nominal,
1.23% real.

Industrial electricity €/kWh (band IE, excl. taxes, 2025-S2): SE 0.0716 · FR
0.0782 · ES 0.0991 · PL 0.1058 · BE 0.1115 · NL 0.1134 · DE 0.1363 · AT 0.1419 ·
IT 0.1463. Industrial gas €/kWh (band I5): NL 0.0319 · DE 0.0353 · ES 0.0362 ·
BE 0.0370 · AT 0.0385 · SE 0.0389 · FR 0.0391 · IT 0.0408 · PL 0.0408

**Green H₂ floors** (power only, 55 kWh/kg): SE 3.94 · FR 4.30 · ES 5.45 · DE
7.50 · IT 8.05. Break-even €5.27/kg → **case exists only in Sweden and France**;
Spain misses by €0.18. Where it exists, T* = 2032 = the reline.

**Grey H₂ floors** (gas at 41.1 kWh/kg + 9 kgCO₂ at €76/t): €2.00–2.36/kg. So
€2.60/kg is not a green price anywhere — it is roughly the unabated fossil
price. See finding 6.

## 4. The findings

Findings 1–5 are structural, derived by `analysis.py` from the model itself.
Findings 6–9 come from the observed-data layer and are reported by
`grounding.py` with a verdict each.

1. **Levers are orthogonal, exactly.** 5 params move NPV and the trigger by
   0.000%; 2 move the trigger and NPV by 0.000%; 4 move both. Structural — the
   trigger formula doesn't contain load factor, resale, support or price path.
   ⇒ a CfD and a grant are complements, not substitutes.
2. **Utilisation inverts at €7.17/kg H₂.** Above it, running the plant *less*
   raises NPV. (Caveat: sign of a sensitivity on an NPV-negative case.)
3. **Reline capture from age 16.** T* = T_rel exactly. Value peaks at age 18;
   the age-19 cliff is the €200 support forfeited by committing before 2028.
4. **Rate "robustness" is cancellation.** r 6→10%: break-even +304%, multiple
   −68%, product +29%.
5. **The correlation matrix misleads.** NPV vs trigger reads −0.87 across 81
   scenarios, contradicting finding 1. The ensemble manufactured it.

**From the observed data** (`grounding.py`, verdict in brackets):

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
   3.36% nominal, 1.23% real after HICP. Finding 4 says the trigger's apparent
   robustness to `r` is cancellation, so this decomposition is load-bearing.

**From the sourcing frontier** (`sourcing.py`; `p_H2` and `eps_cln` tied into
one parameter, the green share θ):

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
   fails if anything ever quotes it as sourced. Confirm against a subscription.
7. **`f_com2026(t)` unchecked against the legal annex.** Computes +8.97/−161 vs
   published +7.82/−122. Structure right (10 terms, ~18× ratio, sign flip);
   levels differ. Registered as `benefit.COM2026_FLOOR` and
   `COM2026_FLOOR_YEARS`, both `unverified`.
8. **Non-steel sectors** have had no calibration or units review. Publish
   ordering only.
9. **`charts.html` is 9 figures long** — wants sectioning or splitting.
10. **Resolve the `p_H2` / `eps_cln` contradiction** (findings 6, 12). A
    modelling decision, not a data problem: either raise `p_H2` to a green
    floor, which weakens the case, or raise `eps_cln` toward grey, which removes
    most of the abatement the model is valuing. Doing neither means publishing
    two inputs that the observed data says cannot both be true, at a cost of
    22.6–33.5% of NPV. `grounding.py` flags it and a self-check fails if the
    flag ever disappears without the inputs changing.
11. **Feed the frontier back into the ladder.** `sourcing.py` runs beside the
    model, not inside it: `scenarios.py` still treats `p_H2` as an independent
    axis. Making θ the axis would change the published ladder, so it is a
    decision, not a refactor.

## 6. Known traps

- **€/t capacity vs €/tCO₂ are different units.** The single largest error class
  in this project. Never conflate.
- **NPV is a model output** — no statistical agency publishes it. Only *inputs*
  can be sourced.
- **`T_rel = 2032` is a model output**, not a fact about any plant.
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
