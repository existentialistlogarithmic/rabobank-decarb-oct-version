# Handoff — steel decarbonisation investment-timing model

The running state of the build. Everything below is verified as of the last
commit on this branch.

**Run everything:** `python run_all.py` (13 sections). Python 3.11+, **zero
dependencies**; `pytest` optional. Currently **107 tests + 30 self-checks** green.

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

| File | What it is |
|---|---|
| `timing_model/` | The model. 11 modules in strict group order (params → primitives → benefit → cost → objective → option → validate → results → scenarios → report). Import direction enforced by an AST test. |
| `analysis.py` | Derives the five structural findings + their evidence |
| `eurostat.py` | Observed inputs, cached offline in `eurostat_cache.json` |
| `sources.py` | → `SOURCES.md`, the provenance register — audited against the code on every run |
| `plots.py` | → `charts.html`, 9 SVG charts, no matplotlib |
| `surface.py` | → `surface.html`, rotatable 3D fleet surface (Canvas) |
| `findings_report.py` | → `findings.html`, the derivations in full |
| `article.py` | → `article.html`, **the finished article** |
| `selfcheck.py` | 30 stdlib assertions (works without pytest) |
| `CALIBRATION.md` | What is sourced vs fitted — **read before quoting anything** |
| `SOURCES.md` | Generated. What each input claims and what would falsify it |
| `ARTICLE.md` | Article outline / writing plan |

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

**Eurostat (retrieved 2026-09-01):** euro-area HICP 2.1%/yr. Industrial
electricity €/kWh (band IE, excl. taxes, 2025-S2): SE 0.0716 · FR 0.0782 · ES
0.0991 · PL 0.1058 · BE 0.1115 · NL 0.1134 · DE 0.1363 · AT 0.1419 · IT 0.1463

**Hydrogen floors** (power only, 55 kWh/kg): SE 3.94 · FR 4.30 · ES 5.45 · DE
7.50 · IT 8.05. Break-even €5.27/kg → **case exists only in Sweden and France**;
Spain misses by €0.18. Where it exists, T* = 2032 = the reline.

## 4. The five findings

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
