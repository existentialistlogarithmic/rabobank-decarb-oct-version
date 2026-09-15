# OPEN_ITEMS.md

Two lists. Neither is to be filled in by guessing. A documented hole beats a
plausible-looking invention.

## A. Genuine source disagreements — carry both, do not reconcile

| ID | Quantity | Number 1 | Number 2 | Why they differ |
|---|---|---|---|---|
| D1 | EUA 2030 | EUR 126 (GMK consensus median, range 80-147) | EUR 145 (ABN AMRO / Citi) | Different reform assumptions. The model path implies ~EUR 112, below both. |
| D2 | Delivered green H2 | EUR 8.66/kg (Platts, Spain, Jan-26) | EUR 9.35/kg (Platts, Germany, Mar-25) | Geography, electrolyser type, PPA structure. Neither is a transacted delivered contract. |
| D3 | H2 per tonne | 54 kg/t Fe (stoichiometric) | ~80 kg/t crude (MIDREX incl. heater); 90-130 kg/t DRI circulated | Different boundaries: reduction only vs incl. heating vs gas circulated but not consumed. **The model's m_H2 = 55 sits at the stoichiometric end and is probably low.** |
| D4 | DR-grade pellet premium | ~$3/dmt (Vale, Q1-2022) | $9-10/t (typical, Kallanish/Samarco 2023) | Contract vs spot, period, and a premium that has been widening. |
| D5 | Total green-steel opex delta | EUR 50-200/t | EUR 400+/t | Entirely driven by the H2 price assumed. Not independent of D2. |
| D6 | Reline cost | rho = 0.25-0.50 of a new furnace (GEM) | ~EUR 50/t capacity implied by Schwelgern (rho ≈ 0.08-0.17) | Absolute vs per-tonne basis, and furnace size. Materially changes the eq (11) credit. |

## B. What could NOT be found — documented holes

| ID | Missing | Why it matters | What would close it |
|---|---|---|---|
| H1 | Per-company CCfD strike prices (EUR/tCO2), round 1 | This is the single most structurally important instrument. Without strikes, `s_max` as a stream is inferred from eq (10) at assumed pi = 30-50, not observed. | BMWK award documentation / FOI |
| H2 | Actual green-steel offtake contract prices | The whole of §3 rests on estimates. Mercedes/Stegra volumes are public; prices are not. | Company disclosure; none expected |
| H3 | EV per tonne of annual capacity, time series, for AM / Salzgitter / voestalpine / SSAB / Tata Europe / TKSE | The requested NPV sanity check cannot be completed without it. A EUR 1,588/t NPV should be checkable against what the market pays per tonne of capacity. | Company reports + market cap + net debt, assembled by hand |
| H4 | Ammonia, aluminium, chemicals-cracker parameters for eq (16) | Only cement is sourced. The four non-steel sectors remain uncalibrated; **their ordering only.** | Sector capex and abatement studies |
| H5 | Dutch SDE++ steel clearing prices | Requested explicitly in §6. | RVO SDE++ result publications |
| H6 | Eurostat nrg_pc_205 / nrg_pc_203 nine-state decomposition (DE, FR, NL, BE, ES, IT, SE, AT, PL) into energy / network / taxes / levies / exemptions | The whole of §5 — the fiscal layer the model currently omits — is only at aggregate level. | Eurostat direct extraction |
| H7 | COM(2026) 616 reprofiled free-allocation percentages for t ≥ 2028 | `data/free_allocation.csv` marks these `com2026_RECONSTRUCTED`. The **enacted** Art 10a(1a) vector is verified and matches `f_law2023` exactly. The 2038-extension percentages are a pending proposal reconstructed from the confirmed mechanism. | The legal annex to COM(2026) 616 |
| H8 | CBAM export-rebate question | Requested in §5. Not included in the enacted text; COM(2025) 990 Temporary Decarbonisation Fund pending. | Legislative tracking |
| H9 | ETS indirect cost compensation rates per member state, per tonne of steel | Requested in §5. | State-aid guidelines + national schemes |
| H10 | Line-by-line BF-BOF vs H2-DRI-EAF opex at a single consistent boundary | §1 was answered from several sources with different boundaries, so `c_avoided = 83` remains an assumption rather than a sum. | One consistent techno-economic study |

## C. Things that are proposals, not law — do not model as enacted

- ETS Investment Booster (Art 10cd), Industrial Decarbonisation Bank (Art 10ce), the EUR 100bn framing, the free-allocation phase-out moving to 2038, and the 15%-reintroduction mechanism all come from **COM(2026) 616 final, 17 July 2026 — a proposal in co-decision.**
- The enacted law is Art 10a(1a): 97.5 / 95 / 90 / 77.5 / 51.5 / 39 / 26.5 / 14% for 2026-2033, 0% from 2034.
- Carry both vintages as the switch `v` already in the model. Do not collapse them.
