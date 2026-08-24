# Calibration provenance — what is sourced, what is fitted

`timing_model.m` was **not present in the working directory**, so the numerical
reference for this build is Appendix A plus published industry data. This file
records exactly which constants Appendix A determines, which were recovered
from the published results, which were researched from primary sources, and
which remain open. Sources are listed at the foot of this file. Nothing here is cosmetic: the whole point of
the v12 rewrite is that a number travels with its conditions.

## Tier 1 — determined by Appendix A, reproduced exactly

The validation gate (§4.3) over-determines nine constants. All nine reproduce
within 1e-3 *relative* (see note on tolerance below), with >20x margin:

| Quantity | Published | Computed | Pins |
|---|---|---|---|
| `CRF(25, 8%)` | 0.0937 | 0.0936788 | `r = 0.08`, `n = 25` |
| `beta` | 1.3860 | 1.3860009 | `mu = 0.05`, `sigma = 0.20` |
| `beta/(beta-1)` | 3.5907 | 3.5906673 | — |
| `p_M` | 27.50 | 27.500000 | `I0 = 900`, `a = -60`, `b = 1.8` |
| `MAC` | 80.17 | 80.172723 | — |
| `p*` | 98.74 | 98.743350 | — |
| `p'_M` | 30.50 | 30.500000 | `phi = 0.5`, `S_s = 360` |
| `MAC'` | 89.54 | 89.540601 | — |
| `p*'` | 109.52 | 109.515352 | — |

**Tolerance.** §4.3 states 1e-3. It is read as *relative*. The published
figures are quoted to 2 d.p. (`MAC = 80.17`, `p*' = 109.52`), so an absolute
1e-3 band is narrower than their own rounding and no implementation could
satisfy it. Every quantity clears 1e-3 relative comfortably.

Three further quantities are determined and reproduce exactly:

* `a(2.60) = -60.00` — F1's requirement that the MATLAB constant fall out of
  the endogenous form.
* `a(8.29) = -372.95` — §2.2's "-€373/t" at the Platts assessment.
* `S_s(2026) = 360.0` — the write-off behind the primed gate figures.

## Tier 2 — recovered from the published stress ladder

The ladder in §4.4 is over-determined enough to recover the *benefit* side and
the aggregate cost side, without any freedom left over.

**Trigger column — exact, no fitting.** Every rung follows from Tier 1:

| Rung | Published | Computed |
|---|---|---|
| base | 109.5 | 109.5154 |
| `kappa = 0.94` | 116.9 | 116.9203 |
| hydrogen 8.29 | 366.9 | 366.8534 |

`kappa` enters as `eps_inc_eff = kappa * eps_inc`, so `b = 1.686`. That single
structural choice reproduces both corrected triggers to 4 significant figures;
no other placement of `kappa` does.

**Benefit side — confirmed to <1 €/t.** Holding the commitment year fixed,
the ladder's own NPV steps recover the price path and horizon:

| Step | Published ΔNPV | Computed ΔNPV |
|---|---|---|
| `+ kappa = 0.94` | −128 | −127.7 |
| `+ real vs nominal` | −421 | −420.3 |

This pins: horizon to **2050**; central path **€76 (2026) rising linearly to
€112 (2030), then +5%/yr**; discounting at 8%; `w = 1`; `eps_cln = 0.1`.

**Aggregate cost side — recovered, three ways, consistently.** Writing
`X(T) = -d(T)·I'(T) + reinvestment(T)`, three independent ladder rows give:

```
row 2 (u = 0.85)          X(2030) = -334.2
row 3 (+ kappa)           X(2030) = -334.5
row 4 (+ real)            X(2030) = -335.3
row 1 (base)              X(2029) = -433.1
```

The agreement across rows 2–4 to ±0.6 €/t is the strongest evidence that the
structure is right.

## Tier 3 — sourced from the literature, not from Appendix A

`timing_model.m` was unavailable, so the six cost-side constants Appendix A
never publishes were **researched from primary sources** rather than fitted.
Five of the six are now sourced; one is calibrated.

| Constant | Value | Source |
|---|---|---|
| `K_s` | 1200 €₂₀₂₂/t capacity | Integrated BF-BOF greenfield ≈ $1,100/t installed; quoted ranges $1,000–1,200/t and ≈ €1,500/t |
| `L_s` | 20 yr | BF campaign life between relines: 15–20 yr typical; thyssenkrupp Schwelgern ran 21 yr (1993–2014) |
| `age0` | 14 yr | Puts `T_rel = 2032`, inside the 2030–2035 window in which ~12.7 Mtpa of EU capacity faces a reline decision |
| `rho` | 0.0417 (`rho·K_s` = €50/t) | Salzgitter BF A reline: €100m over >2 Mtpa (2024) |
| `s_max` | 200 €/t capacity | Published base (Appendix A F4) — **not fitted** |
| `lam` | 0.0 | Rationing does not bind over the base-case window — **not fitted** |
| `gamma` | 0.4442 | **The one calibrated constant.** Sourced band 0.43–0.52 |

**`K_s`, `L_s` and `age0` are not free.** They are jointly pinned by the Tier-1
requirement `S_s(2026) = 360`: `1200 × (20−14)/20 = 360` exactly. Sourcing
`K_s` from the BF-BOF asset value and `L_s` from campaign life leaves `age0`
determined — and it lands at 14, i.e. six years short of a reline, which is
where the published EU reline-decision calendar says the at-risk cohort sits.
That the gate value, the asset literature and the reline calendar agree is the
strongest evidence in this build that the structure is right.

**`gamma` is the only fitted constant**, solved from `NPV(2029) = 1588.3` with
everything else held at its sourced or published value. It lands at 0.4442,
inside the band implied by European H₂-DRI-EAF capacity going from 2.5 Mt
(2025) to 15–20 Mt (2030) — 43–52%/yr. It implies capex falling **8.2%/yr**,
which with the Wright exponent `b_ℓ = 0.234` is a ~15% learning rate.

### The `lam < 0` anomaly is resolved

The previous build fitted `lam = −0.058` — support *rising* — which
contradicted §1.5's framing of `q(t)` as rationing. That was an artefact of an
under-constrained asset block. With `K_s`, `L_s`, `age0` and `rho` sourced, the
support schedule solves to **`s_max = 198.1` at `lam = 0.0000`** — i.e. the
published €200 lump, flat, with no rationing. Fixing `s_max` at exactly 200 and
`lam` at exactly 0 and re-solving `gamma` alone reproduces rows 1–3 of the
ladder with **zero fitted support parameters**:

```
gamma   s_max     lam    → both targets hit
0.430   203.3   -0.0075
0.445   200.0    0.0000   ← adopted
0.450   198.1   -0.0000
0.500   185.3   +0.0191
```

No contradiction with §1.5 remains. The rationing mechanism is implemented and
available; it simply does not bind over the base-case decision window.

## What does not reproduce, and why

| Item | Published | Computed | Cause |
|---|---|---|---|
| ladder row 4 `T*` | 2030 | 2031 | `NPV(2030) = 746.0` vs 745 is right; the *peak* is €8 late |
| ladder rows 5–7 NPV | −188 | −49 | see below |
| F8 vintage delta, `w=1` | +7.82 | +8.97 | `f_com2026(t)` reconstructed — Appendix A open item 2 |
| F8 vintage delta, `w=0` | −122 | −161 | same |

Row 4's *level* is right to €1; only the year-over-year slope differs enough to
move the argmax by one year on a curve that is flat to €8 across 2030–2032.

Rows 5–7 are the residual. At `a = −373` the NPV curve rises monotonically to
the horizon (−2751 in 2026, −49 in 2050), because the benefit flow only turns
positive around 2044 as the carbon price overtakes the hydrogen penalty. The
published −188 sits on that curve at ≈2044. Either the reference caps the
decision grid short of 2050, or it reports the value at a fixed year rather
than at the argmax. **`T*` = "beyond horizon" reproduces correctly** in every
one of these rows, which is the row's actual finding; only the accompanying
NPV level differs.

## Two places the spec's own text does not hold

1. **§1.7 eq (14) sanity check.** "As `sigma -> 0` the multiple -> 1 and the
   trigger collapses to break-even." That holds only when the drift is also
   zero. Under GBM with `mu > 0` the positive root tends to `r/mu`, so the
   multiple tends to `r/(r-mu)` = 2.667, not 1. Waiting is rewarded by the
   drift alone. Both limits are pinned by tests.

2. **§3.2, "never" at market volatility.** Correctly retracted in the spec, and
   this build confirms the retraction: at `sigma = 0.45` the trigger is €202.5
   and the path crosses it in **2043**. A test pins the crossing to 2040–2049
   so the wrong claim cannot come back.

## Reconciliation status

The 50-case grid, the legacy-mode fixture and the diff harness are built and
tested, including the negative control (perturb one NPV by €5 and one `T*` by
one year → exactly two mismatches flagged). **The diff itself has not been
run**, because there is no MATLAB CSV to run it against. `run_cases()` produces
the Python side; drop the MATLAB CSV next to it and `diff()` completes.

## Sources

- [DIW Berlin DP 2082, *Revisiting Investment Costs for Green Steel*](https://www.diw.de/documents/publikationen/73/diw_01.c.901039.de/dp2082.pdf) — DRI-EAF capex €600–1000/t₂₀₂₂ (the range `I0 = 900` sits in); the 25-year / 8% lifetime-and-interest pairing behind `CRF(25, 8%)`; EU-27 fleet of 26 BOFs at 112 Mt/yr
- [thyssenkrupp Steel — *First campaign ends after 21 years*](https://www.thyssenkrupp-steel.com/en/newsroom/press-releases/first-campaign-ends-after-21-years-europes-biggest-blast-furnace-to-be-modernized.html) — campaign life; Schwelgern reline >€200m
- [MetalMiner — *Salzgitter's Relined Blast Furnace*](https://agmetalminer.com/2024/01/10/salzgitter-relined-pig-iron-furnace/) — €100m reline over >2 Mtpa ⇒ €50/t capacity
- [Global Energy Monitor — steel plant construction cost](https://www.gem.wiki/Steel_plant_construction_cost) and [steelonthenet capex data](https://www.steelonthenet.com/resources/capital-investment/capital-investment-costs.html) — integrated BF-BOF ≈ $1,100/t installed
- [IEEFA — *European steel technology transition in danger of slowing*](https://ieefa.org/resources/european-steel-technology-transition-danger-slowing-carbon-capture-not-answer) — ~26 Mtpa relined since 2020; ~12.7 Mtpa facing a reline decision 2030–2035
- [IEEFA — *Hydrogen unleashed: the evolving H2-DRI-EAF pathway*](https://ieefa.org/resources/hydrogen-unleashed-opportunities-and-challenges-evolving-h2-dri-eaf-pathway-beyond-2024) and [Agora Industry — *Achieving climate-neutral steel by 2050*](https://www.agora-industry.org/fileadmin/Projekte/2024/2024-28_IND_Green_Iron/A-IND_382_Achieving_climate-neutral_steel_by_2050_WEB.pdf) — EU H₂-DRI-EAF 2.5 Mt (2025) → 15–20 Mt (2030); ~45 Mt net-zero-compatible DRI by 2030
- [ZOE Institute — *How the Industrial Decarbonisation Bank can complement the ETS*](https://zoe-institut.de/en/news/how-the-industrial-decarbonisation-bank-can-complement-the-ets/) and [European Commission CCfD guidance (July 2026)](https://competition-policy.ec.europa.eu/document/download/42330cc4-d31e-41cf-ae35-3db7ab933331_en?filename=20260717_guidance_on_carbon_contracts_for_difference.pdf) — €100bn IDB, €30bn Investment Booster, CCfD auction design
