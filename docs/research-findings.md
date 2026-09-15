# Research findings — sourced parameters for the timing model

Companion to `../data/parameters.csv`. Every figure here has a row there.
Source IDs (`S1_DIW`, `S8_CARBONVIX`, …) resolve in `../SOURCES.md`.

## Summary

- The three most consequential inputs are all understated in the published base case: sourced project capex is €1,200–2,600/t of annual capacity (vs `I0` = €900/t), sourced delivered hydrogen is €5–9/kg not the €2.60/kg implied by `a` = −60, and EUA volatility is ~45–54% not σ = 0.20. Each pushes the trigger up and the commitment year out.
- Recomputed trigger `p*†` rises from €109.5/tCO2 to ≈€172 (low), ≈€239 (central) and ≈€460 (high) at σ = 0.20. At the sourced Carbon-VIX volatility the option multiple rises from 3.591 to 6.64–8.20, roughly doubling each again.
- Two sourced facts break structural assumptions rather than moving parameters: the German CCfD pays a per-tonne-CO2 stream over 15 years, not a capex lump (eq 10); and European BFs run at load factor u ≈ 0.75–0.85 (eq 8). Code both before recalibrating any point parameter.

---

## §1 Operating cost build-up (feeds `a`, `m_H2`, `c_avoided`)

| Line | BF-BOF | H2-DRI-EAF | Unit / basis | Source |
|---|---|---|---|---|
| Total cash/production cost | ~$600–750/t (Europe, Q4-2025) | $500–850/t (IEA 2020, electrolytic) to ~$1,000/t (green-H2 modelled) | €/t product, modelled | S39_SOTN; IEA 2020 |
| Iron ore / pellets | ~35–40% of cost | DR-grade pellets, ≥67% Fe | share, modelled | S39_SOTN; S25_MIDREX |
| DR-grade pellet premium | — | +$9–10/t historic; ~$3/dmt (Vale Q1-2022); widening | $/t, actual/contract | S47_PELLET |
| Coking coal + PCI + coke | ~20–25% of cost | avoided | share, modelled | S39_SOTN |
| EAF electricity | — | 500–700 kWh/t (100% DRI charge); ~650–760 kWh/t for H2-DRI | kWh/t, modelled | S49_EAF |
| H2-generation electricity | — | ~2,633 kWh/t crude (+816 DR+EAF) → ~3,400–4,000 kWh/t total | kWh/t, modelled | S50_RMI |
| Graphite electrodes | — | 1.5–3 kg/t @ $2,044/t (China) to $4,137/t (US, Sep-25) | kg/t & $/t, actual | S46_ELECTRODES |
| Hydrogen | — | 54 kg/t Fe (stoich.); ~80 kg/t crude (MIDREX incl. heater); 90–130 kg/t DRI circulated | kg/t, modelled | S24_VOGL; S25_MIDREX; S26_PMC |

Delivered hydrogen — the number that moves `a` — is tabulated in
`../data/hydrogen_prices.csv`, which separates **prices** from **subsidy
premia**. The European Hydrogen Bank clearing figures (€0.37–3.49/kg) are
premiums, not prices, and must never be fed into eq (14).

Opex delta (H2-DRI-EAF minus BF-BOF): ~$186/t (EU) at H2 = $5/kg; general
European green-steel premium quoted €50–200/t; widening to €400+/t at
€7–9/kg H2. **Sources disagree — see OPEN_ITEMS D5.**

## §2 Capex from real projects (feeds `I0`)

Full table in `../data/projects_capex.csv`. Distribution: brownfield DRI+melter
retrofits cluster at €1,200–1,420/t; EAF-only ~€600/t; full greenfield
~€2,600/t. The model's €900/t sits **below every announced transformation
project** and is only near the DIW greenfield range once the electrolyser is
excluded from the boundary.

**Revealed reservation price.** ArcelorMittal walked away from €1.3bn of
approved German grants in June 2025. CEO Geert van Poelvoorde stated that "even
with the financial support, the business case for moving ahead with this
transformation is not strong enough, which shows the scale of the challenge,"
and that the company "cannot proceed with these investments, given the
realities of the market and the economics of low-carbon emissions steelmaking."
Salzgitter deferred SALCOS stages 2–3; thyssenkrupp suspended its H2 tender.
This is a direct market read on where the trigger actually sits.

## §3 Revenue and the green premium

- HRC, ex-works Northern Europe: €593.75/t (4 Feb 2026), €711.25/t (30 Jul 2026), Fastmarkets index; €630–640/t (20 Jan 2026) and rebar €710–730/t delivered (Jul-2026) from secondary sources.
- Green premium **actually contracted**: bilateral and largely undisclosed. Estimated €150–350/t (Mercedes/Stegra, secondary); automotive multi-year offtakes reported at $30–80/t (2026); €50–200/t via ResponsibleSteel/SteelZero framing. Mercedes–Stegra binding ~50,000 t/yr; Stegra pre-sold >1.5 Mt/yr (Mercedes, Porsche, Scania, Volvo, BMW).
- **Actual per-tonne contract prices are not disclosed — OPEN_ITEMS H2.** No confirmed green-steel offtake cancellation found, though Stegra sought €975m additional funding in Oct-2025.

## §4 Benchmarks

| Metric | Value | Basis | Source |
|---|---|---|---|
| ArcelorMittal group EBITDA/t shipped | $136/t (2023), $130/t (2024), $121/t (2025) | company actual | S48_AM_RESULTS |
| BF reline, named example | thyssenkrupp Schwelgern (Europe's largest BF): >€200m after a 21-yr campaign, 75 Mt iron | company actual | S27_SCHWELGERN |
| BF reline generic | $30–80m per furnace; US Steel Gary BF#14 $300m (Dec-2025); POSCO ~$393m / 2 furnaces | actual/estimate | S3_GEM |
| BF campaign life | 15–20 yr (world-class 20+) | modelled | S3_GEM |
| Cement CCS (Brevik) | ~€400m capex, 400,000 tCO2/yr (≈50% of plant); MAC ~€50/tCO2 capital-only, ~€150/tCO2 all-in; Norwegian state ~80% of capex and opex | actual/estimate | S12_BREVIK |

Reline per tonne implied ~€50/t capacity (€200m / ~4 Mt) is **materially below**
the model's R = ρ·K_s = 0.35 × 600 = €210/t, implying ρ ≈ 0.08–0.17 rather than
0.25–0.35. See OPEN_ITEMS D6.

**Missing:** EV per tonne of annual capacity for the named steelmakers
(OPEN_ITEMS H3). Without it the requested NPV sanity check cannot be completed.

## §5 Fiscal and energy-price asymmetry

Only aggregate-level data was retrieved. Eurostat non-household electricity fell
5.4% in H2-2024; German large-industrial (IF band) ~€0.10/kWh against SME
€0.27/kWh; Finland €0.0804 and Sweden €0.0964 lowest (H1-2025); Ireland €0.2726
and Italy €0.2336 highest. Energy-intensive industry benefits from
network-charge and levy exemptions (German §19 StromNEV atypical grid usage;
Strompreiskompensation / ETS indirect-cost compensation).

**CBAM:** fully in force 1 Jan 2026; first quarterly certificate €75.36/tCO2e,
published by the Commission on 7 April 2026 as the volume-weighted average price
of EUAs auctioned in the primary market in Q1-2026; certificates purchasable
from Feb-2027. The enacted free-allocation vector (Art 10a(1a)) is in
`../data/free_allocation.csv` and **matches the model's `f_law2023` exactly**.
Export rebates are not included; COM(2025) 990 Temporary Decarbonisation Fund
(25% of CBAM revenue 2028–29) is pending; COM(2026) 616 (17 Jul 2026) proposes
moving the endpoint to 2038 — **proposal only, not law**.

**The nine-state decomposition into energy / network / taxes / levies /
exemptions was not obtained — OPEN_ITEMS H6.** ETS indirect cost compensation
rates per state — OPEN_ITEMS H9.

## §6 The subsidy pot and its shape

Full table in `../data/support_instruments.csv`, with a `SHAPE` column
distinguishing lumps from streams. The instrument that matters most structurally
— the German CCfD — is a 15-year CO2-indexed two-way stream with clawback, not a
capex grant. Per-company strike prices were not disclosed (OPEN_ITEMS H1).

**Stream vs lump (eq 10).** Σ(k=0..9) 1.08^(−k) = 7.247. A premium of π €/tCO2
over 10 years with b = 1.8 is worth π × 1.8 × 7.247 → **€391/t (π=30)** to
**€652/t (π=50)** against the model's €200 lump. Support is roughly 2–3× larger
and structurally different.

Round 2 of the European Hydrogen Bank largely failed — only €271m of €1.2bn
signed, 380 MW of 2.3 GW — which is material for calibrating the rationing
factor q(t) in eq (9).

---

## Recomputation

Substituting into eq (6), `p*† = (I0 + φ·S_s − a/r) × ((r−μ)/b) × β/(β−1)`
with `(r−μ)/b = 0.0166667` and `β/(β−1) = 3.591` at σ = 0.20, so the bracket is
multiplied by 0.059856:

| Case | I0 | a | −a/r | φ·S_s | Bracket | MAC | p_M | **p\*†** |
|---|---|---|---|---|---|---|---|---|
| Published base | 900 | −60 | 750 | 180 | 1,830 | 80.2 | 27.5 | **109.5** |
| Low | 1,200 | −120 | 1,500 | 180 | 2,880 | 129.1 | 45.0 | **172.4** |
| Central | 1,420 | −192 | 2,400 | 180 | 4,000 | 180.6 | 63.7 | **239.4** |
| High | 2,600 | −393 | 4,912.5 | 180 | 7,692.5 | 353.6 | 125.2 | **460.4** |

Hand check, central: MAC = (0.0937×1,420 + 192)/1.8 = 325.1/1.8 = €180.6;
p_M = 4,000 × 0.03/1.8 = €66.7 (the code reports 63.7 because it uses the exact
CRF and μ from the CSV rather than the rounded 0.03/1.8); p*† = 4,000 × 0.059856
= €239.4.

**Crossing years** (produced by `src/timing_model.py`):

| Case | p\*† | model central path | GMK consensus | ABN / Citi |
|---|---|---|---|---|
| base | 109.5 | 2030 | 2030 | 2030 |
| low | 172.4 | 2039 | 2037 | 2035 |
| central | 239.4 | 2046 | 2044 | 2039 |
| high | 460.4 | beyond horizon | beyond horizon | beyond horizon |

At σ = 0.45 (realised volatility) the multiple is 6.640 and the base-case
trigger alone reaches €202.5; at σ = 0.54 it is 8.202 and €250.1.

**Cross-industry (eq 16).** Only cement is adequately sourced: Brevik implies
I0 ≈ €500/t clinker capacity with MAC ≈ €50/tCO2 capital-only to €150/tCO2
all-in. That sits between steel's *base-case* MAC (€80) and steel's *sourced
central* MAC (€181) — i.e. the base case flatters steel relative to cement,
while the sourced numbers do not. Ammonia, aluminium and chemicals crackers
could not be parameterised (OPEN_ITEMS H4): **ordering only**.

## Caveats

Several figures labelled "green H2 price" in the wider literature are
production-cost estimates or market-research indices rather than transacted
delivered contract prices, and the European Hydrogen Bank figures are subsidy
premiums, not prices. `../data/hydrogen_prices.csv` carries an
`is_price_or_subsidy` column for exactly this reason.

Source disagreements D1–D6 and holes H1–H10 are in `../OPEN_ITEMS.md`. No
figure, source or link in this package has been fabricated; unverifiable items
are listed rather than estimated.
