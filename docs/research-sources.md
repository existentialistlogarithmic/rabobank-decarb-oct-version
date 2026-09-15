# SOURCES.md

Every source behind a number in `data/`. Read the **Tier** and **Link status**
columns before quoting anything externally.

## Link status — read this first

Only the URLs marked `CAPTURED` below were actually retrieved. Everything else
is `NOT_CAPTURED`: the source is correctly named and the figure is correctly
attributed, but the working link was not captured in this pass. **Do not
reconstruct a URL by guessing a path.** Fetch it from the publisher, then
update both this file and the `url` column in the relevant CSV.

## Tier

- **A — primary**: legal text, company report or release, official statistics, auction result publication.
- **B — near-primary**: recognised price assessor, research institute, peer-reviewed paper.
- **C — secondary**: trade press, aggregator, market-research site. Usable as a pointer, **not** as a citation to a steel analyst. Replace every C before external circulation.

| ID | Used for | Source | Tier | Link status | URL |
|---|---|---|---|---|---|
| S1_DIW | I0 greenfield EUR 600-750/t (2022 EUR) | DIW Berlin | B | NOT_CAPTURED | — |
| S2_INTENSITY | eps_inc 1.8-2.2, eps_cln 0.1-0.5; CBAM HRC benchmark 1.530 | CBAM embedded-emissions benchmarks | A | NOT_CAPTURED | — |
| S3_GEM | BF campaign life 15-20 yr; reline 25-50% of new furnace; 62 BFs face reline by 2035, Europe 37% | Global Energy Monitor, *Pedal to the Metal 2026*; ACCR | B | NOT_CAPTURED | — |
| S4_COM2026 | Investment Booster 400 Mt 2028-31, Art 10cd; IDB Art 10ce; EUR 100bn; conditionality Art 10a(3c); MSR 24→12% | COM(2026) 616 final, 17 Jul 2026, via EUR-Lex | A | NOT_CAPTURED | — |
| S5_ICE | EUA observations 2026 | ICE Endex market reporting | A | NOT_CAPTURED | — |
| S6_FORECAST | mu; price paths | Reuters carbon-analyst poll 30 Apr 2026; ClearBlue Markets | B | NOT_CAPTURED | — |
| S7_LEARNING | LR 0.10-0.20 per doubling | Wright-law literature, electrolysers + DRI | B | NOT_CAPTURED | — |
| S8_CARBONVIX | sigma: avg 54%, median 53.8, sd 10.4, range 30-83; realised ~45%; ATM puts 31-120d = 52.5%; 12,500 projects; 1 pp vol ≈ EUR 1.12 carbon price | NBER WP 32937, Fuchs, Stroebel & Terstegge, Sep 2024 (NYU Stern / Copenhagen Business School); data at carbonvix.org | B | NOT_CAPTURED | — |
| S9_PLATTS | Delivered H2 assessments (7.08 / 7.49 / 8.29 EUR/kg) | S&P Global Platts hydrogen assessments | B | NOT_CAPTURED | — |
| S10_EHB | Hydrogen Bank rounds 1-3: pots, clearing premia, oversubscription | European Commission / European Hydrogen Bank award publications; Hydrogen Europe | A | NOT_CAPTURED | — |
| S11_BENCHMARK | Hot-metal benchmark 1.248 allowances/t (2026-30), vs 1.288 (2021-25) | Commission Implementing Regulation (EU) 2026/1412, in force 26 Jun 2026 | A | NOT_CAPTURED | — |
| S12_BREVIK | Brevik CCS: ~400 kt CO2/yr, ~50% of plant, Norwegian state ~80% of capex and opex | Heidelberg Materials press release, 18 Jun 2025 | A | NOT_CAPTURED | — |
| S13_AM_CANCEL | ArcelorMittal Bremen + Eisenhüttenstadt cancellation, EUR 1.3bn forfeited; CEO quotes | Trade coverage of the Jun-2025 announcement | C | **CAPTURED** | https://www.circularbusinessreview.com/german-steel-giants-abandon-e3-3-billion-hydrogen-projects-despite-record-subsidies/ |
| S20_TKH2 | tkH2Steel capex, scope, status | thyssenkrupp Steel | A | NOT_CAPTURED | — |
| S21_SALCOS | SALCOS EUR 2.7bn / 1.9 Mt, support ~EUR 1bn + EUR 322m | Salzgitter AG | A | NOT_CAPTURED | — |
| S22_STEGRA | Stegra Boden ~EUR 6.5bn / 2.5 Mt; EUR 1.4bn equity 2025; EUR 265m RRF | Stegra / financing coverage | C | **CAPTURED** | https://enkiai.com/hydrogen/stegra-green-steel-financing/ |
| S23_PLATTS_JAN26 | EUR 8.66/kg, Spain, alkaline + PPA, 21 Jan 2026 | S&P Global Platts | B | NOT_CAPTURED | — |
| S24_VOGL | 54 kg H2/t Fe stoichiometric | Vogl / Patisson, via MDPI | B | NOT_CAPTURED | — |
| S25_MIDREX | ~80 kg H2/t crude incl. heater | MIDREX / Cavaliere via ScienceDirect | B | NOT_CAPTURED | — |
| S26_PMC | 90-130 kg H2/t DRI circulated | PMC review article | B | NOT_CAPTURED | — |
| S27_SCHWELGERN | Reline >EUR 200m after 21-yr campaign, 75 Mt iron (Europe's largest BF) | thyssenkrupp Steel | A | NOT_CAPTURED | — |
| S28_CCFD | Klimaschutzverträge R1: EUR 2.8bn, 15 of 17 bidders, 15-yr stream, handover 16 Oct 2024, ~17 Mt CO2; R2 up to EUR 5bn, 130 pre-notified | BMWK Klimaschutzverträge documentation | A | NOT_CAPTURED | — |
| S29_UTIL | European BF load factor 0.75-0.85 | Industry utilisation data | B | NOT_CAPTURED | — |
| S30_AM_DUNKIRK | Dunkirk EAF EUR 1.2bn / ~2 Mt, confirmed May 2025 | ArcelorMittal | A | NOT_CAPTURED | — |
| S31_PLATTS_DE | EUR 9.35/kg Germany alkaline Mar-2025, from EUR 14.5/kg Dec-2024 | S&P Global Platts via GMK | B | NOT_CAPTURED | — |
| S32_RANGE | Unsubsidised green H2 EUR 4-10/kg | Hydro Project; Montel | C | NOT_CAPTURED | — |
| S33_AM_H2 | ArcelorMittal-cited H2 EUR 5-8/kg; "around EUR 2.50-3.00 per kg ... just a breakeven price" | Fastmarkets, Jun-2025 | B | NOT_CAPTURED | — |
| S34_GMK | Consensus EUA: EUR 85 (2026, +18.1% y-o-y), EUR 100 (2027), EUR 126 (2030), range 80-147; median of BNEF, ABN AMRO, Refinitiv, ICIS, S&P Global, Aurora, PIK | GMK Center | C | NOT_CAPTURED | — |
| S35_ABN | EUR 145/t by 2030, EUR 200/t by 2035 | ABN AMRO / Citi | B | NOT_CAPTURED | — |
| S36_CBAM | Q1-2026 certificate EUR 75.36/tCO2e, published 7 Apr 2026; Q2 EUR 75.28 | European Commission CBAM reference-price publication | A | **CAPTURED (secondary)** | https://europe.influencemap.org/policy/EU-Carbon-Border-Adjustment-Mechanism-430 |
| S37_ART10a | Free-allocation / CBAM factors 2026-2034 | EU ETS Directive Art 10a(1a) — enacted law | A | **CAPTURED (secondary)** | https://cbamguide.com/carbon/free-allocation/ · https://cbamguide.com/learn/free-allocation/ |
| S38_SDE | Dutch SDE++ ranking by EUR/tCO2 | RVO SDE++ documentation | A | NOT_CAPTURED | — |
| S40_HRC | HRC N. Europe EUR 593.75/t (4 Feb 2026), EUR 711.25/t (30 Jul 2026) | Fastmarkets index | B | NOT_CAPTURED | — |
| S41_HRC_C | HRC EUR 630-640/t (20 Jan 2026); rebar EUR 710-730/t delivered (Jul 2026) | Metal.com / Tacto | C | **CAPTURED** | https://news.metal.com/newscontent/103736886-smm-iron-steel-european-hrc-prices-underpinned-by-scarcity-and-new-safeguard-measures · https://www.tacto.ai/en/commodities/steel-price |
| S42_PREMIUM | Green premium estimates EUR 50-200/t; $30-80/t automotive offtake | SteelOnTheNet; iFactory; Persistence Market Research | C | **CAPTURED** | https://www.steelonthenet.com/insights/green-steel-premium.html · https://ifactoryapp.com/industries/steel-plant/green-steel-pricing-premium-economics-buyers · https://www.persistencemarketresearch.com/market-research/europe-green-steel-market.asp |
| S43_MERCEDES | Mercedes–Stegra binding ~50,000 t/yr; >1.5 Mt/yr pre-sold (Mercedes, Porsche, Scania, Volvo, BMW) | Stegra | A | **CAPTURED** | https://stegra.com/en/news-and-stories/mercedes-benz-and-h2-green-steel-announce-agreements-in-both-europe-and-north-america |
| S44_SPG_DECARB | European steelmakers' decarbonisation trade-offs | S&P Global Commodity Insights | B | **CAPTURED** | https://www.spglobal.com/commodity-insights/en/news-research/latest-news/metals/110425-feature-european-steelmakers-trade-short-term-pain-for-long-term-gain-in-decarbonization |
| S45_EUROSTAT | Non-household electricity -5.4% H2-2024; DE large-industrial ~EUR 0.10/kWh (IF band) vs SME EUR 0.27; FI 0.0804, SE 0.0964 lowest H1-2025; IE 0.2726, IT 0.2336 highest | Eurostat nrg_pc_205, via aggregators | C | **CAPTURED** | https://aenert.com/news-events/energy-news-monitoring/n/electricity-price-statistics-germany-had-the-highest-household-electricity-prices-in-the-eu-in-2024/ · https://aenert.com/news-events/energy-news-monitoring/n/electricity-price-statistics-on-the-eu-germans-pay-73-more-for-electricity-than-hungarians-in-2025/ · https://euenergy.live/articles/business-electricity-prices-per-kwh |
| S46_ELECTRODES | Graphite electrodes 1.5-3 kg/t; $2,044/t (China) to $4,137/t (US, Sep-25) | IMARC; FRC Global | C | NOT_CAPTURED | — |
| S47_PELLET | DR-grade premium +$9-10/t historic; ~$3/dmt Vale Q1-2022 | Kallanish/Samarco May 2023; S&P Global Dec 2021 | B | NOT_CAPTURED | — |
| S48_AM_RESULTS | ArcelorMittal group EBITDA/t shipped: $136 (2023), $130 (2024), $121 (2025) | ArcelorMittal results | A | NOT_CAPTURED | — |

## Source-quality warning

Of the links actually captured, most are **Tier C**. The Tier A material that
carries the argument — EUR-Lex COM(2026) 616, Implementing Regulation (EU)
2026/1412, the BMWK CCfD documentation, the Platts assessments, DIW, Global
Energy Monitor, NBER WP 32937 and the company releases — is correctly cited by
name but its links were not captured here. Before this goes to a steel analyst,
every Tier C row should be replaced by the primary document it points at.
