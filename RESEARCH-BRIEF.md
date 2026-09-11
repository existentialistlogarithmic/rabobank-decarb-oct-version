# Research brief — real steel-industry numbers for the timing model

Paste the block below into Claude Research. It is written to be self-contained:
Research starts with no knowledge of this repository.

---

I am calibrating an investment-timing model for European steel decarbonisation
(blast furnace + BOF → hydrogen DRI + EAF) and I need real industry numbers to
replace assumed ones. I need figures I can put in a model and defend to a steel
analyst, not narrative.

**Units contract — apply it to every number you return.** Steel costs get
quoted in three different units that are routinely conflated, so for every
figure state explicitly which one it is:

- **€/t product** — per tonne of crude or finished steel actually produced.
- **€/t capacity** — per tonne of *annual* nameplate capacity (how capex is
  normally quoted).
- **€ absolute** — total for a named project, with the capacity it serves.

Also give, for every number: the **currency year** (nominal 2022? real 2025?),
the **geography**, the **period**, and whether it is an actual, a contracted
price, a company guidance figure, or an analyst estimate. Where a source
gives a range, give the range and its endpoints' sources rather than a
midpoint. Where sources disagree materially, say so and give both — do not
reconcile them for me.

## 1. Operating cost build-up, per tonne of steel

I need a line-by-line opex comparison between the incumbent BF-BOF route and
the H2-DRI-EAF route, in €/t of crude steel. Right now my model collapses the
entire opex difference into one lumped constant driven only by the hydrogen
price, which I believe is wrong. Please give me the actual cost stack for each
route:

**BF-BOF route:** iron ore (sinter feed / BF-grade pellets), coking coal and
PCI, coke (if bought), limestone/fluxes, scrap charge in the BOF, electricity,
natural gas, oxygen, refractories, labour, maintenance, and ETS cost at a
stated EUA price.

**H2-DRI-EAF route:** **DR-grade pellets** (this is the one I most need — the
DR-grade premium over BF-grade pellets, in $/t or €/t, and how thin the DR-grade
supply market is), hydrogen (kg per tonne of DRI and per tonne of steel),
natural gas where the DRI plant runs on gas initially, **EAF electricity in
kWh/t** and the €/MWh it is charged at, graphite electrodes, scrap charge ratio
in the EAF, alloys, lime, refractories, labour, maintenance.

Specifically:
- kg of hydrogen per tonne of DRI and per tonne of finished steel — the range
  in the literature and why it varies.
- kWh per tonne for the EAF, and separately for the electrolyser if hydrogen is
  made on site.
- The DR-grade pellet premium, historically and now, and who can actually
  supply DR-grade ore at scale.
- What a realistic **delivered** hydrogen cost is for a European steel plant
  in 2026–2035, separating (a) merchant/contracted supply, (b) on-site
  electrolysis at industrial power prices, (c) imported ammonia-cracked or
  pipeline hydrogen. I need to know at what price hydrogen is actually being
  contracted, not modelled LCOH.

## 2. Capex, from real projects

For every announced European H2-DRI-EAF or DRI-EAF project, give me: operator,
site, country, **announced capex in € and the capacity in Mt/yr it serves**,
what scope that capex covers (DRI shaft only? DRI + EAF? including electrolyser,
grid connection, casting?), the date of the announcement, current status
(operating / under construction / FID taken / delayed / cancelled), and the
subsidy awarded.

Include at least: thyssenkrupp (Duisburg, tkH2Steel), Salzgitter (SALCOS),
ArcelorMittal (Bremen, Eisenhüttenstadt, Dunkirk, Gijón, Sestao), Stegra /
H2 Green Steel (Boden), SSAB (Oxelösund, Luleå, Raahe), voestalpine (Linz,
Donawitz — greentec steel), Tata Steel (IJmuiden), Dillinger/Saarstahl
(Power4Steel), Liberty Steel, and any others you find.

**The cancellations and delays matter as much as the FIDs.** Where a project
was paused, cancelled or descoped, give the stated reason and the date. I want
to know what the revealed reservation price looks like.

Derive and give me explicitly: **€ of capex per tonne of annual capacity** for
each project, and the distribution across them.

## 3. Revenue side and the green premium

- European HRC and rebar prices, 2020–2026, and the current level.
- **Green steel premium actually contracted** — not survey willingness-to-pay.
  Who has signed offtake at a premium, at what €/t, for what volume and tenor.
  Automotive in particular (Mercedes, BMW, Volvo, Scania) and construction.
- How much of the premium survives once the buyer's own CBAM/Scope 3 position
  is accounted for.
- Whether any green steel offtake has been renegotiated or cancelled, and why.

## 4. Benchmarks I can sanity-check a per-tonne NPV against

This is the sanity check I most need. Give me, for European steelmakers:

- **EBITDA per tonne of crude steel** through the cycle — peak, trough and
  mid-cycle — for ArcelorMittal (Europe segment), Salzgitter, voestalpine,
  SSAB, Tata Steel Europe, Thyssenkrupp Steel Europe. 2015–2026.
- **Enterprise value per tonne of annual capacity** for the same companies,
  currently and at a few historical points.
- **Replacement cost per tonne of annual capacity** for an integrated mill, and
  for an EAF mini-mill, as used in the industry.
- Typical **maintenance capex per tonne** and the cost of a **blast furnace
  reline** per tonne of capacity, with named examples.

And the cross-industry comparison: the same abatement-decision economics for
**cement** (Brevik, Heidelberg Materials; Holcim), **ammonia**, **aluminium**
and **chemicals crackers** — capex per tonne of capacity, abatement cost per
tonne of CO₂, and where each sits on the EU's marginal abatement cost curve.
I want to know whether steel's numbers are in line with its neighbours.

## 5. Fiscal and energy-price asymmetry

My model has no tax or levy layer and I think that is a material omission.

- Industrial **electricity** prices for large consumers by member state,
  decomposed into energy, network charges, taxes, levies and exemptions —
  Germany, France, Netherlands, Belgium, Spain, Italy, Sweden, Austria, Poland.
- Industrial **natural gas** prices for the same states, decomposed the same way.
- **Is electricity actually cheaper than gas per unit of useful energy for an
  industrial user in each of these states, and what does the tax and levy
  structure do to that comparison?** This is the specific question. Include the
  Energy Taxation Directive's minimum rates and where it has got to, national
  electricity tax reductions for energy-intensive industry, and network-charge
  exemptions.
- **ETS indirect cost compensation** (state aid guidelines): which states pay
  it, at what rate, and what it is worth per tonne of steel.
- CBAM: the phase-in schedule, how the free-allocation phase-out interacts with
  it, and the current state of the export-rebate question.

## 6. The subsidy pot and its shape

I want to model the *shape* of public support, not just its size. For each
instrument below give: total pot in €, the award mechanism (competitive
auction? first-come? negotiated?), the disbursement profile over time
(lump at FID? per tonne of CO₂ abated over N years? per tonne of output?),
the cap per project, the state-aid basis, and — where it has run — **what the
awards actually cleared at**.

- EU Innovation Fund, including the auction-as-a-service rounds.
- European Hydrogen Bank auctions — **clearing prices in €/kg, both rounds**,
  volumes, and which winners were steel-linked.
- IPCEI Hydrogen and IPCEI on steel.
- German **Klimaschutzverträge** (carbon contracts for difference) — first
  bidding round results, strike prices, contract length, the clawback and
  indexation mechanics. This is the one I care most about structurally.
- Dutch SDE++ — how the ranking-by-€/tCO₂ mechanism works and what it has
  cleared at.
- The Clean Industrial Deal / Industrial Decarbonisation Bank as currently
  legislated, and its €100bn framing — what is actually appropriated versus
  announced.
- Any per-project state aid approvals for the steel projects in §2, with
  amounts and conditions.

For the mechanisms that pay **per tonne of CO₂ abated over time** rather than
as a capex grant, I specifically need the contract length, the strike price,
and how the payment is trued up against the actual ETS price — because whether
support is a lump sum or a stream changes my model's answer structurally.

## 7. What I want back

1. A table per section, with every figure carrying unit, currency year,
   geography, period, source and a link.
2. Where a number is an estimate rather than an observation, say so in the row.
3. A short list of the places where the sources genuinely disagree, with both
   numbers.
4. A short list of what you **could not** find, stated plainly — I would rather
   carry a documented hole than a plausible-looking invention.

Do not give me policy recommendations, and do not tell me whether the
transition is a good idea. I need the input numbers.
