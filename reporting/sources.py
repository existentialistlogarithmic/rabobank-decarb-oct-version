"""Provenance register: every input, where it came from, how far it is verified.

Writes ``SOURCES.md``.  ``CALIBRATION.md`` explains *how* the constants were
recovered; this file records *what each one claims about the world* and how
much of that claim is checkable by someone who does not trust us.

Why it is code and not prose
----------------------------
A hand-maintained bibliography drifts away from the model within a week: a
default changes, the markdown does not, and the citation now vouches for a
number nobody is using.  So the register is executable.  :func:`audit` checks,
mechanically, that

* every field of every parameter dataclass appears exactly once here - a new
  input without provenance is a failure, not an oversight;
* every quoted value still equals the value the model actually runs on;
* every claim names a real entry in the bibliography.

``SOURCES.md`` is *generated*.  Do not edit it by hand - edit the register.

Status vocabulary
-----------------
The distinction that matters is not "cited / uncited" but *what would falsify
it*.  Six statuses, in descending order of how much weight a number can bear:

``gate``
    Fixed by Appendix A and re-derived by the validation gate on every run.
    Falsified by the gate failing.
``sourced``
    A primary, openly reachable publication says this.  Falsified by reading it.
``observed``
    An official statistic, retrieved and cached with its period.  Falsified by
    re-running :mod:`eurostat`.
``assumed``
    A modelling choice with a stated rationale and no external authority.
    Not falsifiable - only arguable.  Say so when quoting it.
``fitted``
    Solved backwards from a published result.  Carries no independent
    information about the world.
``unverified``
    Taken from the specification, traceable to a source we could not open
    (licensed data, or a legal annex not checked line by line).  **The one
    status that is a live to-do**: see :func:`unverified`.
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from timing_model import params

OUT: Final[str] = "SOURCES.md"

#: Status -> what would falsify a claim carrying it.  Order is the rendering
#: order of SOURCES.md, strongest evidence first.
STATUS: Final[Mapping[str, str]] = {
    "gate": "re-derived by the validation gate on every run",
    "sourced": "a primary, openly reachable publication says this",
    "observed": "an official statistic, cached with its period",
    "assumed": "a modelling choice with a rationale and no external authority",
    "fitted": "solved backwards from a published result; no independent content",
    "unverified": "traceable to a source we could not open - a live to-do",
}


@dataclass(frozen=True)
class Source:
    """One bibliographic entry.

    ``url`` is ``None`` where the document is not openly reachable - licensed
    market data, or a text we cite by reference only.  A ``None`` here is a
    statement about access, and every claim resting on one is ``unverified``.
    """

    key: str
    title: str
    publisher: str
    url: str | None
    note: str

    def render(self) -> str:
        link = f"[{self.title}]({self.url})" if self.url else f"*{self.title}*"
        access = "" if self.url else " — **not openly reachable**"
        return f"- **`{self.key}`** — {link}, {self.publisher}{access}. {self.note}"


@dataclass(frozen=True)
class Claim:
    """What one model input asserts, and on whose authority.

    ``quoted`` is deliberately a second copy of the value that appears in
    :mod:`timing_model.params`.  The duplication is the mechanism:
    :func:`audit` compares the two, so a default cannot move without either
    the citation moving with it or the run going red.
    """

    param: str
    quoted: float | str
    unit: str
    status: str
    refs: tuple[str, ...]
    note: str


#: Full citations.  Every URL was checked to resolve to the cited document;
#: `ieefa_*` and `zoe_idb` refuse automated clients (403 / reset) but open in a
#: browser, and `tk_schwelgern` answers 404 to a bare user agent.  The three
#: entries with no URL at all are the three claims this build cannot verify.
SOURCES: Final[Mapping[str, Source]] = {s.key: s for s in (
    Source(
        "diw2082",
        "DIW Berlin DP 2082 — Revisiting Investment Costs for Green Steel",
        "DIW Berlin",
        "https://www.diw.de/documents/publikationen/73/diw_01.c.901039.de/dp2082.pdf",
        "DRI-EAF capex €600–1000/t₂₀₂₂; the 25-year / 8% lifetime-and-interest "
        "pairing behind CRF(25, 8%); EU-27 fleet of 26 BOFs at 112 Mt/yr.",
    ),
    Source(
        "tk_schwelgern",
        "First campaign ends after 21 years — Europe's biggest blast furnace to be modernized",
        "thyssenkrupp Steel",
        "https://www.thyssenkrupp-steel.com/en/newsroom/press-releases/"
        "first-campaign-ends-after-21-years-europes-biggest-blast-furnace-to-be-modernized.html",
        "Campaign life between relines; Schwelgern ran 1993–2014 and its reline "
        "exceeded €200m.",
    ),
    Source(
        "salzgitter_reline",
        "Salzgitter's Relined Blast Furnace",
        "MetalMiner",
        "https://agmetalminer.com/2024/01/10/salzgitter-relined-pig-iron-furnace/",
        "BF A reline at €100m over >2 Mtpa ⇒ €50/t capacity.",
    ),
    Source(
        "gem_capex",
        "Steel plant construction cost",
        "Global Energy Monitor",
        "https://www.gem.wiki/Steel_plant_construction_cost",
        "Integrated BF-BOF ≈ $1,100/t installed.",
    ),
    Source(
        "son_capex",
        "Capital investment costs",
        "steelonthenet",
        "https://www.steelonthenet.com/resources/capital-investment/"
        "capital-investment-costs.html",
        "Corroborates the BF-BOF installed-cost range, $1,000–1,200/t.",
    ),
    Source(
        "ieefa_reline",
        "European steel technology transition in danger of slowing",
        "IEEFA",
        "https://ieefa.org/resources/european-steel-technology-transition-danger-"
        "slowing-carbon-capture-not-answer",
        "~26 Mtpa relined since 2020; ~12.7 Mtpa facing a reline decision 2030–2035. "
        "This is the calendar age0 = 14 has to land inside.",
    ),
    Source(
        "ieefa_h2dri",
        "Hydrogen unleashed: the evolving H2-DRI-EAF pathway beyond 2024",
        "IEEFA",
        "https://ieefa.org/resources/hydrogen-unleashed-opportunities-and-challenges-"
        "evolving-h2-dri-eaf-pathway-beyond-2024",
        "EU H₂-DRI-EAF capacity 2.5 Mt (2025) → 15–20 Mt (2030): the 43–52%/yr band "
        "gamma is fitted inside.",
    ),
    Source(
        "agora_steel",
        "Achieving climate-neutral steel by 2050",
        "Agora Industry",
        "https://www.agora-industry.org/fileadmin/Projekte/2024/2024-28_IND_Green_Iron/"
        "A-IND_382_Achieving_climate-neutral_steel_by_2050_WEB.pdf",
        "~45 Mt net-zero-compatible DRI by 2030; corroborates the growth band.",
    ),
    Source(
        "zoe_idb",
        "How the Industrial Decarbonisation Bank can complement the ETS",
        "ZOE Institute",
        "https://zoe-institut.de/en/news/how-the-industrial-decarbonisation-bank-can-"
        "complement-the-ets/",
        "€100bn Industrial Decarbonisation Bank, €30bn Investment Booster.",
    ),
    Source(
        "ec_ccfd",
        "Guidance on Carbon Contracts for Difference (July 2026)",
        "European Commission, DG COMP",
        "https://competition-policy.ec.europa.eu/document/download/"
        "42330cc4-d31e-41cf-ae35-3db7ab933331_en?filename="
        "20260717_guidance_on_carbon_contracts_for_difference.pdf",
        "CCfD auction design; the premium tenor and €30–50/tCO₂ band.",
    ),
    Source(
        "cbam_reg",
        "Regulation (EU) 2023/956 establishing a carbon border adjustment mechanism",
        "EUR-Lex",
        "http://data.europa.eu/eli/reg/2023/956/oj",
        "The 2023 free-allocation phase-out factors the law2023 vintage encodes.",
    ),
    Source(
        "ets_dir",
        "Directive (EU) 2023/959 amending Directive 2003/87/EC (EU ETS revision)",
        "EUR-Lex",
        "http://data.europa.eu/eli/dir/2023/959/oj",
        "Product benchmarks and the free-allocation architecture the phase-out "
        "applies to.",
    ),
    Source(
        "com2026_616",
        "COM(2026) 616 — reintroduction of a free-allocation floor",
        "European Commission",
        None,
        "Cited by the v12 specification for the 15% floor. The mechanism is "
        "confirmed; the annex fixing the floored years has NOT been read. "
        "See open item 7.",
    ),
    Source(
        "platts_h2",
        "Platts hydrogen price assessment, Spain, 8 May 2026 — €8.29/kg",
        "S&P Global Commodity Insights",
        None,
        "Licensed market data. Taken from the v12 specification and never "
        "confirmed against a subscription. See open item 6.",
    ),
    Source(
        "eurostat_hicp",
        "prc_hicp_aind — HICP annual average rate of change",
        "Eurostat",
        "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_aind/default/table",
        "Euro-area inflation; grounds the deflator used on the real basis.",
    ),
    Source(
        "eurostat_power",
        "nrg_pc_205 — electricity prices for non-household consumers",
        "Eurostat",
        "https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205/default/table",
        "Band IE (20–70 GWh/yr), excluding taxes: the closest published band to a "
        "steel plant's draw. Puts the floor under the hydrogen price.",
    ),
    Source(
        "eurostat_gas",
        "nrg_pc_203 — gas prices for non-household consumers",
        "Eurostat",
        "https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_203/default/table",
        "Band I5 (1 000 000–3 999 999 GJ/yr), excluding taxes: the closest "
        "published band to an integrated works. Sets the grey hydrogen floor, "
        "which is the lower of the two and therefore the binding one.",
    ),
    Source(
        "eurostat_ppi",
        "sts_inppd_a — producer prices in industry, annual",
        "Eurostat",
        "https://ec.europa.eu/eurostat/databrowser/view/sts_inppd_a/default/table",
        "Euro-area output prices, 2021 = 100. MIG_CAG (capital goods) restates "
        "a EUR 2022 capex figure in today's money; C24 (basic metals) does the "
        "same for anything per tonne of product. They have moved in opposite "
        "directions since 2022.",
    ),
    Source(
        "eurostat_bs",
        "ei_bsin_q_r2 — business surveys in industry, quarterly",
        "Eurostat",
        "https://ec.europa.eu/eurostat/databrowser/view/ei_bsin_q_r2/default/table",
        "Current level of capacity utilisation, euro area, seasonally adjusted. "
        "All-industry rather than steel, so it is a reference point for the "
        "load factor, not a measurement of furnace load.",
    ),
    Source(
        "ecb_rates",
        "ECB Data Portal — yield curve and official interest rates",
        "European Central Bank",
        "https://data.ecb.europa.eu/",
        "Series YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y (10-year AAA euro-area "
        "government spot rate) and FM/B.U2.EUR.4F.KR.MRR_FR.LEV (main "
        "refinancing rate). Decomposes the 8% hurdle rate into an observed "
        "risk-free rate and the premium above it.",
    ),
    Source(
        "iea_h2",
        "Global Hydrogen Review 2024 — GHG emissions of hydrogen and its derivatives",
        "International Energy Agency",
        "https://www.iea.org/reports/global-hydrogen-review-2024/"
        "ghg-emissions-of-hydrogen-and-its-derivatives",
        "Unabated hydrogen from natural gas at 10–12 kgCO₂e/kg once upstream "
        "methane is counted. Refuses automated clients (403); opens in a "
        "browser.",
    ),
    Source(
        "spec_v11",
        "Investment timing model for industrial decarbonisation — equations, "
        "sensitivity results and sources (v11)",
        "RaboResearch Energy Transition, August 2026",
        None,
        "The specification itself, supplied as PDF. Base-case parameter table, "
        "governing equations (1)–(12), the validation table, and the five "
        "sensitivity phases. Cited for values read directly off it.",
    ),
    Source(
        "appendix_a",
        "v12 specification, Appendix A",
        "internal",
        None,
        "The build's numerical reference. Sections cited inline. The MATLAB "
        "implementation it describes (timing_model.m) was never available.",
    ),
)}


def _fmt_schedule(sched: Mapping[int, float]) -> str:
    """Canonical one-line form of a year -> factor table.

    Used both to write the quoted value below and to re-read the live one in
    :func:`audit`, so the phase-out ladder cannot change unnoticed.
    """
    return " ".join(f"{y}:{sched[y]:.3f}" for y in sorted(sched))


#: The register.  One entry per model input, no exceptions - :func:`audit`
#: fails on a missing one.
REGISTER: Final[tuple[Claim, ...]] = (
    # ---- Group 0/IV: discounting, horizon, intensities ----------------------
    Claim("common.r", 0.08, "1/yr real", "gate", ("diw2082", "appendix_a"),
          "WACC proxy; pinned by CRF(25, 8%) = 0.0937 in the gate."),
    Claim("common.mu", 0.05, "1/yr", "assumed", ("appendix_a",),
          "GBM drift of the EUA price. Pinned by beta = 1.3860 given sigma, but "
          "the pair itself is an assumption, not a measurement."),
    Claim("common.sigma", 0.20, "1/yr^0.5", "assumed", ("appendix_a",),
          "Long-run rung of the §3.4 ladder. The only pure threshold lever, and "
          "the highest-value thing an EUA series would replace - open item 1."),
    Claim("common.t0", 2026, "year", "gate", ("appendix_a",), "Discounting base."),
    Claim("common.horizon_end", 2050, "year", "gate", ("appendix_a",),
          "§3.6 fixes the horizon explicitly at 2050."),
    Claim("common.eps_inc", 1.9, "tCO2/t product", "sourced", ("ets_dir", "appendix_a"),
          "Blast-furnace route intensity, Appendix A F9."),
    Claim("common.eps_cln", 0.1, "tCO2/t product", "sourced", ("ieefa_h2dri", "appendix_a"),
          "H2-DRI-EAF residual intensity, Appendix A F9."),
    Claim("common.crf_years", 25, "yr", "gate", ("diw2082",),
          "Asset life in the MAC diagnostic; the 25/8% pairing is DIW's."),

    # ---- Group I/III: capex, incumbent asset, operating penalty -------------
    Claim("sector.I0", 900.0, "EUR/t capacity (2022)", "gate", ("diw2082",),
          "Mid-point of the €600–1000/t₂₀₂₂ DRI-EAF range; pinned by p_M = 27.50."),
    Claim("sector.K_s", 600.0, "EUR/t capacity (2022)", "gate", ("spec_v11",),
          "v11 base-case table, and confirmed by the specification's own age "
          "ladder: 'each year of age removes EUR 30 of residual book value', "
          "i.e. K_s/L_s = 30. The earlier 1200 was reverse-engineered to hit "
          "S_s(2026) = 360 with age0 = 14; that pair gives the same value at t0 "
          "and the wrong one in every other year."),
    Claim("sector.L_s", 20.0, "yr", "sourced",
          ("tk_schwelgern", "gem_capex", "son_capex"),
          "BF campaign life between relines; 15–20 typical, 21 achieved. The "
          "installed-cost sources corroborate the book value K_s is measured "
          "against, at roughly half a greenfield BF-BOF."),
    Claim("sector.age0", 8.0, "yr", "gate", ("spec_v11", "ieefa_reline"),
          "v11: the reference plant is 'already eight years into a twenty year "
          "life'. Puts T_rel = 2038 and reproduces all four rows of the "
          "specification's age ladder exactly. T_rel is a model output, not a "
          "fact about any named plant."),
    Claim("sector.rho", 0.35, "share of K_s", "gate",
          ("spec_v11", "salzgitter_reline"),
          "v11 base-case table: reline cost 25–50% of book, taken at 0.35, so "
          "rho*K_s = €210/t capacity."),
    Claim("sector.phi", 0.5, "share of S_s", "gate", ("appendix_a",),
          "Share of the write-off charged to the decision; pinned by p'_M = 30.50."),
    Claim("sector.m_H2", 55.0, "kg H2/t product", "sourced", ("ieefa_h2dri", "appendix_a"),
          "Group I eq (2). Unrelated to eurostat.KWH_PER_KG_H2 = 55, which is "
          "kWh per kg - the two 55s share a number and nothing else."),
    Claim("sector.c_avoided", 83.0, "EUR/t product/yr (2022)", "gate", ("appendix_a",),
          "Coke and PCI avoided, eq (2); pinned by a(2.60) = -60."),
    Claim("sector.b_learn", 0.234, "dimensionless", "sourced", ("diw2082",),
          "Wright exponent, ~15% learning rate."),
    Claim("sector.gamma", 0.4442, "1/yr", "fitted", ("ieefa_h2dri", "agora_steel"),
          "THE ONE CALIBRATED CONSTANT. Solved from NPV(2029) = 1588.3 with "
          "everything else held. Lands inside the sourced 0.43–0.52 band, which "
          "is corroboration, not derivation. 144 parameter sets fit equally well."),

    # ---- Group II/III: allocation and support ------------------------------
    Claim("policy.benchmark", 1.9, "tCO2/t product", "sourced", ("ets_dir",),
          "BM(t). The hot-metal correction rides on kappa, not on this."),
    Claim("policy.kappa", 1.0, "dimensionless", "gate", ("appendix_a",),
          "Published base. F5's hot-metal fix sets 0.94, which reproduces both "
          "corrected triggers to 4 s.f.; no other placement of kappa does."),
    Claim("policy.s_max", 200.0, "EUR/t capacity (2022)", "sourced", ("zoe_idb",),
          "Investment Booster envelope. Published base (F4) - not fitted."),
    Claim("policy.support_start", 2028, "year", "sourced", ("zoe_idb",),
          "Booster window opens. The age-19 cliff in finding 3 is this €200 being "
          "forfeited by committing before it."),
    Claim("policy.lam", 0.0, "1/yr", "assumed", ("appendix_a",),
          "q(t) rationing slope. Zero: the mechanism exists but does not bind over "
          "the base-case window. No publication fixes it - but re-solving with "
          "K_s/L_s/age0/rho sourced gives s_max = 198.1 at lam = 0.0000, i.e. the "
          "published €200 lump, flat, which is why zero was adopted exactly."),
    Claim("policy.q_min", 0.0, "share", "assumed", ("appendix_a",),
          "Rationing floor, eq (6). Inert while lam = 0."),
    Claim("policy.stream_years", 10, "yr", "sourced", ("ec_ccfd",),
          "CCfD premium tenor."),
    Claim("policy.stream_premium", 40.0, "EUR/tCO2 (2022)", "sourced", ("ec_ccfd",),
          "Mid-point of F4's €30–50 band."),

    # ---- The seven scenario axes -------------------------------------------
    Claim("scenario.p_H2", 2.60, "EUR/kg (2022)", "assumed", ("appendix_a",),
          "§3.5(3), UNRESOLVED in the base case - and below the electricity bill "
          "alone in every member state Eurostat covers. The cheapest observed "
          "floor is €3.94/kg (SE)."),
    Claim("scenario.w", 1.0, "0 or 1", "assumed", ("appendix_a",),
          "Resale switch; §3.5(2), UNRESOLVED in the base case."),
    Claim("scenario.sigma_regime", "long_run", "key of SIGMA_REGIMES", "assumed",
          ("appendix_a",), "§3.4 ladder."),
    Claim("scenario.support_basis", "lump", "lump|stream", "assumed", ("appendix_a",),
          "§3.5(1), UNRESOLVED in the base case. The stream basis routes support "
          "into B(t), where a per-tCO2 premium structurally belongs."),
    Claim("scenario.price_basis", "nominal", "nominal|real", "assumed", ("appendix_a",),
          "F3. The real basis is the single largest unit correction in the ladder: "
          "-€421 on NPV."),
    Claim("scenario.policy_vintage", "law2023", "law2023|com2026", "sourced",
          ("cbam_reg",), "Which free-allocation phase-out applies."),
    Claim("scenario.u", 0.85, "share", "sourced", ("ieefa_reline", "appendix_a"),
          "Load factor, F2. EU blast furnaces run 0.75–0.85. Multiplies B(t) only, "
          "never I'(T) - enforced by an AST test over cost.py."),
    Claim("scenario.price_scale", 1.0, "multiplier", "assumed", ("appendix_a",),
          "Selects low/central/high EUA path in the §9.2 diff grid."),
    Claim("scenario.deflator", 0.02, "1/yr", "observed", ("eurostat_hicp",),
          "Used only on the real basis. Euro-area HICP came back at 2.1%/yr, "
          "within 1pp - the model's 2.0% stands."),
    Claim("scenario.legacy_mode", "False", "flag", "assumed", ("appendix_a",),
          "DIFF FIXTURE ONLY: reproduces the uncorrected model for reconciliation."),

    # ---- Schedules and paths, which are inputs too --------------------------
    Claim("params.SIGMA_REGIMES", "cfd:0.100 crisis:0.300 long_run:0.200 realised:0.450",
          "1/yr^0.5", "assumed", ("appendix_a",),
          "§3.4. A ladder rather than a calibrated sigma(t): each rung is "
          "defensible line by line. At 0.450 the trigger is crossed in 2043 - "
          "beyond any recognisable investment horizon, which is not 'never'."),
    Claim("benefit.F_LAW2023",
          "2026:0.975 2027:0.950 2028:0.900 2029:0.775 2030:0.515 2031:0.390 "
          "2032:0.265 2033:0.140",
          "share of free allocation", "sourced", ("cbam_reg",),
          "CBAM phase-out as legislated in 2023; years absent take 0.0."),
    Claim("benefit.COM2026_FLOOR", 0.15, "share", "gate",
          ("spec_v11", "com2026_616"),
          "The conditional tranche, read off v11 eq (12). With the proposal's "
          "own 2026–2033 factors it reproduces the published +7.82 vintage "
          "delta exactly; the previous floor-on-law2023 reconstruction gave "
          "+8.97."),
    Claim("benefit.COM2026_FLOOR_YEARS", "2034 .. 2037", "years", "gate",
          ("spec_v11", "com2026_616"),
          "v11 eq (12): the flat 15% tranche runs 2034–2037 and nothing "
          "follows from 2038."),
    Claim("benefit.F_COM2026",
          "2026:0.975 2027:0.950 2028:0.915 2029:0.810 2030:0.590 2031:0.480 "
          "2032:0.375 2033:0.270",
          "share of free allocation", "gate", ("spec_v11", "com2026_616"),
          "The proposal's own schedule, not a floor applied to the legislated "
          "path. More generous than law2023 in every year from 2028."),
    Claim("benefit.CENTRAL_PATH",
          "2026:76.000 2027:86.000 2028:96.000 2029:104.000 2030:112.000",
          "EUR/tCO2 nominal", "gate", ("spec_v11",),
          "Quoted anchors, not a straight line. Interpolating 76 to 112 "
          "understates 2027–2029 by €1, €2 and €1."),
    Claim("cost.SUPPORT_FULL_UNTIL", 2031, "year", "gate", ("spec_v11",),
          "v11 eq (9): the Booster runs at full weight through 2031."),
    Claim("cost.SUPPORT_END", 2035, "year", "gate", ("spec_v11",),
          "v11 eq (9): linear taper from 2031, nothing from 2035. Support ran "
          "flat to 2050 before, which made a late commitment look better "
          "funded than any published rule allows."),
    Claim("cost.SUPPORT_PRE_WINDOW", 0.35, "share of s_max", "gate", ("spec_v11",),
          "v11 eq (9), first branch: before the Booster window there is still "
          "the Innovation Fund and national aid, worth 0.35·s_max = €70/t. The "
          "code returned zero here, which put a €200 step at 2028 where the "
          "specification works out €130 by hand — overstating the value of "
          "waiting, which is the quantity the model exists to measure."),
    Claim("eurostat.KWH_PER_KG_H2", 55.0, "kWh/kg H2", "sourced", ("eurostat_power",),
          "LHV 33.3 kWh/kg at ~60% system efficiency. Turns an observed power "
          "price into a GREEN floor under the hydrogen price."),
    Claim("eurostat.KWH_GAS_PER_KG_H2", 41.1, "kWh gas/kg H2", "assumed", ("iea_h2",),
          "LHV 33.3 kWh/kg at 81% reforming efficiency, the top of the 79-81% "
          "band reported for large-scale SMR - the favourable end, because this "
          "builds a floor. The IEA reference covers the route and its emissions, "
          "not this efficiency figure: treat the number as a modelling choice."),
    Claim("eurostat.KG_CO2_PER_KG_H2_SMR", 9.0, "kgCO2/kg H2", "sourced", ("iea_h2",),
          "Process emissions of unabated reforming. The IEA puts unabated "
          "hydrogen at 10-12 kgCO2e/kg once upstream methane is counted, so 9 "
          "is deliberately the conservative end: it makes the grey floor lower "
          "and the eps_cln contradiction harder to dismiss, not easier."),
    Claim("eurostat.POWER_BAND", "MWH20000-69999", "Eurostat band code", "sourced",
          ("eurostat_power",),
          "Band IE, 20-70 GWh/yr: the closest published electricity band to a "
          "steel plant's draw. Taxes excluded, because large industrial users "
          "are substantially exempted in most member states."),
    Claim("eurostat.GAS_BAND", "GJ1000000-3999999", "Eurostat band code", "sourced",
          ("eurostat_gas",),
          "Band I5, 1 000 000-3 999 999 GJ/yr: the closest published gas band "
          "to an integrated works."),
    Claim("eurostat.CURRENCY_BASE_YEAR", "2022", "year", "gate", ("appendix_a",),
          "The currency year every monetary parameter is tagged with. Producer "
          "prices are read at this year and the latest one so a EUR 2022 figure "
          "can be restated rather than assumed current."),
    Claim("ecb.YIELD_10Y", "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y", "series key",
          "observed", ("ecb_rates",),
          "10-year AAA euro-area government spot rate: the risk-free rate at "
          "the model's horizon scale. Deflated by HICP it gives the real "
          "risk-free rate the 8% hurdle is a premium over."),
    Claim("ecb.POLICY_RATE", "FM/B.U2.EUR.4F.KR.MRR_FR.LEV", "series key",
          "observed", ("ecb_rates",),
          "Main refinancing operations, fixed rate: the policy anchor under the "
          "term structure."),
    Claim("eurostat.CAPUTIL_SOURCE", "Eurostat ei_bsin_q_r2 (business survey)",
          "dataset", "observed", ("eurostat_bs",),
          "Euro-area capacity utilisation, the reference point for the load "
          "factor u. Observed 78.2% (2025-Q4) against a model default of 0.85 "
          "and a published base row of 1.00."),
    Claim("eurostat.PPI_SOURCE", "Eurostat sts_inppd_a", "dataset", "observed",
          ("eurostat_ppi",),
          "Capital goods (MIG_CAG) 107.0 -> 116.0 and basic metals (C24) "
          "124.7 -> 111.0 between 2022 and 2025: plant got dearer while steel "
          "got cheaper, in a model whose central error class is confusing per "
          "tonne of capacity with per tonne of product."),

    # ---- §3.3 sourced ranges: the headline sensitivity, not a +/-20% sweep --
    Claim("scenarios.SOURCED_RANGES.I0", "600.0 .. 1400.0", "EUR/t capacity (2022)",
          "assumed", ("diw2082", "appendix_a"),
          "Lower bound is DIW's €600/t₂₀₂₂. The upper bound is widened past "
          "DIW's €1000 for first-of-a-kind European projects, and is a judgement."),
    Claim("scenarios.SOURCED_RANGES.a", "-320.0 .. -25.0", "EUR/t product/yr",
          "assumed", ("appendix_a",),
          "Published band. Note it is NOT the image of the p_H2 band under the "
          "endogenous a(·): a(2.50) = -54.5 and a(8.29) = -372.95, so the top of "
          "the hydrogen range falls below the bottom of this one. The two §3.3 "
          "rows are inconsistent with each other; the model uses a(p_H2)."),
    Claim("scenarios.SOURCED_RANGES.r", "0.06 .. 0.1", "1/yr real", "sourced",
          ("diw2082", "appendix_a"),
          "Finding 4 runs on this band: across it the break-even moves +304% and "
          "the option multiple -68%, and the trigger looks stable only because "
          "the two cancel."),
    Claim("scenarios.SOURCED_RANGES.s_max", "200.0 .. 660.0", "EUR/t capacity (2022)",
          "sourced", ("zoe_idb", "ec_ccfd"),
          "Published base at the €200 Booster envelope; the top end is the "
          "envelope plus a CCfD stream, per F4."),
    Claim("scenarios.SOURCED_RANGES.learning_rate", "0.1 .. 0.2", "share per doubling",
          "sourced", ("diw2082", "ieefa_h2dri"),
          "Wright learning rates for electrolyser-led capex. b_learn = 0.234 sits "
          "at the top of this band (~15%)."),
    Claim("scenarios.SOURCED_RANGES.u", "0.75 .. 0.85", "share", "sourced",
          ("ieefa_reline",),
          "Observed EU blast-furnace utilisation. Finding 2 turns on this band: "
          "above €6.15/kg hydrogen, moving down it *raises* NPV."),
    Claim("scenarios.SOURCED_RANGES.p_H2", "2.5 .. 8.29", "EUR/kg (2022)", "unverified",
          ("platts_h2", "appendix_a"),
          "The top of this band is the Platts assessment (Spain, 8 May 2026) and "
          "is the single most consequential unverified number in the build: it "
          "drives ladder rows 5–7, where T* goes beyond the horizon. Confirm "
          "against a subscription — open item 6."),
)

#: Inputs no open source can supply.  Rendered into SOURCES.md so the gap is
#: stated rather than implied by absence.
GAPS: Final[tuple[tuple[str, str], ...]] = (
    ("EUA price series",
     "Sets the price path, the drift mu and the volatility sigma. sigma is the "
     "only pure threshold lever, so this is the highest-value input left "
     "unsourced. No free feed reached: Ember's API 404s, Sandbag publishes no "
     "CSV. Needs ICE, EEX or Refinitiv."),
    ("Commercial hydrogen assessments",
     "Delivered hydrogen prices are licensed (Platts, Argus). Eurostat bounds "
     "them from below via the power bill; it cannot pin the level."),
    ("Per-plant reline dates",
     "Would replace the calibrated age0 = 14 with real campaign ages and turn "
     "the fleet surface into a named target list. Plant-level campaign starts "
     "are not published as a series."),
)

#: Dotted names in the register are the model's public vocabulary and stay put
#: when files move; this maps their first segment to wherever the code now lives.
_PROVIDER_MODULES: Final[Mapping[str, str]] = {
    "eurostat": "data.eurostat",
    "ecb": "data.ecb",
    "observed": "data.observed",
    "grounding": "analysis.grounding",
    "sourcing": "analysis.sourcing",
}

_CLASSES: Final[Mapping[str, type]] = {
    "common": params.CommonParams,
    "sector": params.SectorParams,
    "policy": params.PolicyParams,
    "scenario": params.ScenarioParams,
}
def _root(group: str) -> object:
    """Object a dotted parameter name is resolved against."""
    if group in _CLASSES:
        return _CLASSES[group]()
    if group in ("benefit", "cost", "params", "primitives", "option"):
        from timing_model import benefit, cost, option, params, primitives

        return {"benefit": benefit, "cost": cost, "params": params,
                "primitives": primitives, "option": option}[group]
    if group in _PROVIDER_MODULES:
        import importlib

        return importlib.import_module(_PROVIDER_MODULES[group])
    if group == "scenarios":
        from timing_model import scenarios

        return scenarios
    return {"params": params, "benefit": benefit}[group]


def _live_value(param: str) -> object:
    """The value the model actually runs on, for the dotted name ``param``.

    Walks attributes, then mapping keys, so a single entry in a table -
    ``scenarios.SOURCED_RANGES.p_H2`` - can be cited on its own.
    """
    group, rest = param.split(".", 1)
    obj = _root(group)
    for part in rest.split("."):
        obj = getattr(obj, part) if hasattr(obj, part) else obj[part]  # type: ignore[index]
    return obj


def _comparable(value: object) -> float | str:
    """Live value in the form the register quotes it.

    Schedules and ranges collapse to a canonical string so that a changed
    factor shows up as a changed citation.
    """
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Mapping):
        return _fmt_schedule(value)
    if isinstance(value, tuple) and len(value) == 2:
        return f"{value[0]} .. {value[1]}"
    return str(value)


def audit() -> list[str]:
    """Check the register against the code. Empty list means clean.

    Three failure modes, all of which have happened to documentation in this
    project at least once:

    1. a parameter exists with no citation, or is cited twice;
    2. a citation quotes a value the model no longer uses;
    3. a citation names a bibliography entry or a status that does not exist.
    """
    problems: list[str] = []
    seen: dict[str, int] = {}
    for c in REGISTER:
        seen[c.param] = seen.get(c.param, 0) + 1
        if c.status not in STATUS:
            problems.append(f"{c.param}: unknown status {c.status!r}")
        for ref in c.refs:
            if ref not in SOURCES:
                problems.append(f"{c.param}: cites unknown source {ref!r}")
        if not c.refs:
            problems.append(f"{c.param}: no source cited")
        try:
            live = _comparable(_live_value(c.param))
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            problems.append(f"{c.param}: does not resolve in the code ({exc})")
            continue
        if isinstance(c.quoted, (int, float)) and isinstance(live, float):
            if abs(live - c.quoted) > 1e-4 * max(1.0, abs(c.quoted)):
                problems.append(f"{c.param}: cited {c.quoted}, model runs {live}")
        elif str(live) != str(c.quoted):
            problems.append(f"{c.param}: cited {c.quoted!r}, model runs {live!r}")

    for dupe in sorted(k for k, n in seen.items() if n > 1):
        problems.append(f"{dupe}: cited more than once")
    for group, klass in _CLASSES.items():
        for f in dataclasses.fields(klass):
            if f"{group}.{f.name}" not in seen:
                problems.append(f"{group}.{f.name}: parameter has no provenance entry")
    cited = {ref for c in REGISTER for ref in c.refs}
    for orphan in sorted(set(SOURCES) - cited):
        problems.append(f"{orphan}: bibliography entry nothing cites")
    return problems


def unverified() -> tuple[Claim, ...]:
    """Claims resting on a source nobody here has opened.

    This is the open-items list, derived rather than maintained: anything that
    cites a :class:`Source` with no URL and has not been checked another way.
    """
    return tuple(c for c in REGISTER if c.status == "unverified")


def by_status(status: str) -> tuple[Claim, ...]:
    """Claims carrying ``status``, in register order."""
    return tuple(c for c in REGISTER if c.status == status)


def _observed_rows() -> list[tuple[str, str, str, str]]:
    """Observed series from the committed cache. Never touches the network."""
    from data import eurostat

    rows: list[tuple[str, str, str, str]] = []
    for ser in eurostat.refresh(offline=True).values():
        rows.append((ser.name, ser.period, f"{ser.value:,.4f} {ser.unit}", ser.source))
    return rows


def _table(claims: Sequence[Claim]) -> str:
    head = ("| Input | Value | Unit | Sources | Note |\n"
            "|---|---|---|---|---|\n")
    body = "".join(
        f"| `{c.param}` | {c.quoted} | {c.unit} | "
        f"{', '.join(f'`{r}`' for r in c.refs)} | {c.note} |\n"
        for c in claims
    )
    return head + body


def render() -> str:
    """The full SOURCES.md text."""
    problems = audit()
    out: list[str] = [
        "# Sources — what each input claims, and on whose authority",
        "",
        "**Generated by `sources.py`. Do not edit by hand** — edit the register and",
        "re-run, or the citation and the model will disagree without saying so.",
        "",
        "`CALIBRATION.md` explains how the constants were *recovered*. This file",
        "records what each one *asserts about the world*, and what would falsify it.",
        "",
        "## Status vocabulary",
        "",
        "| Status | What would falsify a claim carrying it | Count |",
        "|---|---|---|",
    ]
    for st, meaning in STATUS.items():
        out.append(f"| `{st}` | {meaning} | {len(by_status(st))} |")
    out += [
        "",
        f"**Audit:** {'clean — ' if not problems else ''}"
        f"{len(REGISTER)} inputs, every parameter field covered, every quoted value "
        f"equal to the value the model runs on."
        if not problems else
        f"**Audit: {len(problems)} PROBLEM(S)** — " + "; ".join(problems),
        "",
    ]

    for st, meaning in STATUS.items():
        claims = by_status(st)
        if not claims:
            continue
        out += [f"## `{st}` — {meaning}", "", _table(claims)]

    out += [
        "## Unverified — the live to-do list",
        "",
        "These rest on a document nobody on this build has opened. They are not",
        "wrong; they are unchecked, and nothing quoting them should be presented",
        "as sourced.",
        "",
    ]
    for c in unverified():
        out.append(f"- **`{c.param}` = {c.quoted}** ({', '.join(c.refs)}) — {c.note}")

    out += [
        "",
        "## What no open source can supply",
        "",
    ]
    for name, why in GAPS:
        out.append(f"- **{name}.** {why}")

    out += [
        "",
        "## Observed inputs, as cached",
        "",
        "Retrieved by `eurostat.py` and committed to `eurostat_cache.json`, so the",
        "model runs offline and the numbers below are the numbers it used.",
        "",
        "| Series | Period | Value | Dataset |",
        "|---|---|---|---|",
    ]
    for name, period, value, src in _observed_rows():
        out.append(f"| {name} | {period} | {value} | {src} |")

    out += [
        "",
        "## Bibliography",
        "",
    ]
    for src in SOURCES.values():
        out.append(src.render())

    out += [
        "",
        "---",
        "",
        "**A standing caution.** NPV, `T*`, `T_exp` and the trigger are model",
        "*outputs*. No statistical agency publishes them and none ever will — only",
        "inputs can be sourced. `T_rel = 2032` is likewise an output, not a fact",
        "about any named plant.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    """Write SOURCES.md. Non-zero if the register disagrees with the code."""
    problems = audit()
    pathlib.Path(OUT).write_text(render(), encoding="utf-8")
    counts = ", ".join(f"{len(by_status(s))} {s}" for s in STATUS)
    print(f"Wrote {OUT}: {len(REGISTER)} inputs ({counts}); "
          f"{len(SOURCES)} bibliography entries.")
    if problems:
        print("\nPROVENANCE AUDIT FAILED:")
        for p in problems:
            print(f"  {p}")
        return 1
    print("Provenance audit clean: every parameter cited, every citation live.")
    for c in unverified():
        print(f"  UNVERIFIED  {c.param} = {c.quoted}  ({', '.join(c.refs)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
