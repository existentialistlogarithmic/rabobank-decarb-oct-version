# Calibration provenance — what is sourced, what is fitted

`timing_model.m` was **not present in the working directory**, so the numerical
reference for this build is Appendix A alone. This file records exactly which
constants Appendix A determines, which were recovered from the published
results, and which remain open. Nothing here is cosmetic: the whole point of
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

## Tier 3 — CALIBRATED, not sourced. **This is what needs `timing_model.m`.**

`X(2029)` and `X(2030)` are two equations. The cost side has six unknowns that
Appendix A never publishes:

| Constant | Value used | Status |
|---|---|---|
| `gamma` (cumulative-capacity growth) | 0.3940 | **fitted** |
| `lam` (support slope) | −0.0580 | **fitted** |
| `K_s` | 600 €/t capacity | chosen |
| `L_s` | 15 yr (BF campaign life) | chosen |
| `age0` | 6 yr | chosen |
| `rho` | 0.20 | chosen |

`K_s`, `L_s`, `age0` are jointly constrained by `S_s(2026) = 360` (Tier 1) and
were chosen for defensibility — a 15-year blast-furnace campaign, six years
elapsed, giving `T_rel = 2035`. `gamma` and `lam` were then solved to hit
`NPV(2029) = 1588.3` and the `u = 0.85` row at 1294.

A search over the constrained space found **144 parameter sets** that fit
equally well. The split is genuinely under-determined; only the aggregate is
recoverable.

### The one result that looks wrong, and is a real question

Every one of those 144 sets requires **`lam < 0` — support *rising* over
time**. §1.5 frames `q(t) = max{q_min, 1 - lam(t-2028)}` as *rationing*, i.e.
support falling. No positive `lam` reproduces the published `X(2029)` and
`X(2030)` together.

Either the reference model ramps support (CCfD auctions growing into the
Booster window, which is arguable) or one of my Tier-3 choices is wrong. This
is the first thing to check against `timing_model.m`.

It has a visible consequence: the capex clamp binds from 2040 and is reported
as a binding guard on every run. Under §3.6 that is correct behaviour —
"support exceeding gross capex is a modelling signal, not a free plant" — but
here the signal is pointing at the calibration, not at the world.

## What does not reproduce, and why

| Item | Published | Computed | Cause |
|---|---|---|---|
| ladder row 4 `T*` | 2030 | 2031 | Tier-3 slope; `NPV(2030) = 745.7` vs 745 is right, the *peak* is one year late |
| ladder rows 5–7 NPV | −188 | −82 | same, compounded; `T*` = "beyond" reproduces correctly |
| F8 vintage delta, `w=1` | +7.82 | +8.97 | `f_com2026(t)` is reconstructed — Appendix A open item 2 |
| F8 vintage delta, `w=0` | −122 | −161 | same |

On F8 the **structure** reproduces: exactly **10 terms** differ between the
vintages, and the `w=0` effect is ~18x the `w=1` effect and opposite in sign —
which is the policy-neutrality finding. The levels depend on `f_com2026(t)`
for `t >= 2028`, which Appendix A open item 2 flags as reconstructed from the
confirmed 15% reintroduction mechanism and not yet checked against the legal
annex. It is implemented as a 15% floor over 2033–2042 (ten years — which is
what makes the term count come out right) applied as a maximum against the
legislated path, so the series stays monotone non-increasing.

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
