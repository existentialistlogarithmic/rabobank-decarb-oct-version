"""The finalised tables, one per review comment, every column carrying its unit.

Why this module exists
----------------------
The review comments are, underneath, all the same complaint: a number was
quoted without enough of its context to be checked. ``I0 = 900`` without its
denominator. An opex delta without the industry lines that make it up. A
subsidy pot without its shape. So every table here states, in its own header,
what unit each column is in - and where a figure is a rate per tonne of annual
capacity, the absolute money for a real plant sits next to it.

The rule the tables follow
--------------------------
A cell is one of three things and always says which:

``a number``
    computed by the model, or read from a row in ``data/``.
``MISSING``
    the research pass looked and did not find it. The hole's ID is given, and
    the cell stays empty rather than being filled with something plausible.
``a range``
    sources disagree. Both ends are shown with the disagreement ID; no midpoint
    is taken, because the midpoint of two incompatible boundaries is not a
    measurement of anything.

Nothing in here recalibrates the model. ``Params()`` still carries the published
base case; these tables report what is known about it and what is not.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from analysis import sourced, units
from data import eurostat
from data import sourced as src
from timing_model.params import Params
from timing_model.results import outputs
from timing_model.scenarios import published_base

#: Plant size the absolute-money columns use, in Mt/yr. Stegra's Boden, so the
#: totals sit beside a project somebody actually built.
REFERENCE_MT: Final[float] = 2.5

#: Marker for a figure the research pass looked for and did not find. Never
#: replaced with an estimate: a documented hole beats a plausible invention.
MISSING: Final[str] = "MISSING"


#: Research source ids whose documents are trade press or aggregators. They
#: point at the right fact but must not be cited to a steel analyst; the
#: research pass grades them Tier C in docs/research-sources.md.
TIER_C: Final[frozenset[str]] = frozenset({
    "S13_AM_CANCEL", "S22_STEGRA", "S32_RANGE", "S34_GMK", "S41_HRC_C",
    "S42_PREMIUM", "S45_EUROSTAT", "S46_ELECTRODES",
})


@dataclass(frozen=True)
class SourceRef:
    """One citation behind a table: its key, and the URL if one was captured.

    ``url`` is None where the research pass named the source correctly but did
    not capture a working link. That is the difference between *attributed* and
    *checked*, and it is shown rather than smoothed over.

    Only the research package is resolved here. The model's own bibliography
    lives in ``reporting/sources.py``, which this layer must not import - the
    reporting layer joins the two, and :func:`reporting.results.cite` is where
    that happens.
    """

    key: str
    url: str | None
    tier: str

    @property
    def linked(self) -> bool:
        return bool(self.url)


def _research_urls() -> dict[str, str]:
    """source_id -> the one URL the research pass actually captured for it."""
    found: dict[str, str] = {}
    for _table, row in src.all_rows():
        if row.linked and row.source_id:
            found.setdefault(row.source_id, row.url)
    return found


def resolve(*keys: str) -> list[SourceRef]:
    """Citations for the given ids, resolved as far as this layer can see.

    A key the research CSVs do not link is left with ``url = None`` and the
    tier that says why. The reporting layer fills in anything that belongs to
    the model's own register.
    """
    research = _research_urls()
    out = []
    for key in keys:
        url = research.get(key)
        tier = "Tier C" if key in TIER_C else ("Tier A/B" if url else "unlinked")
        out.append(SourceRef(key, url, tier))
    return out


@dataclass(frozen=True)
class Column:
    """One column, and the unit every cell in it is expressed in."""

    name: str
    unit: str = ""
    width: int = 14
    align: str = ">"

    #: Two spaces between every column, so a full-width cell never runs into
    #: its neighbour. Widths below are content widths, not including this.
    GAP: Final[str] = "  "

    def head(self) -> str:
        return f"{self.name[: self.width]:{self.align}{self.width}}" + self.GAP

    def unit_head(self) -> str:
        return f"{self.unit[: self.width]:{self.align}{self.width}}" + self.GAP

    def cell(self, value: object) -> str:
        text = "" if value is None else str(value)
        return f"{text[: self.width]:{self.align}{self.width}}" + self.GAP


@dataclass(frozen=True)
class Table:
    """A titled table whose header always carries units, plus its caveats."""

    name: str
    """Short indicative handle, e.g. "T3 capex". What to say when pointing."""
    title: str
    columns: Sequence[Column]
    rows: Sequence[Sequence[object]]
    notes: Sequence[str] = field(default_factory=tuple)
    sources: Sequence[SourceRef] = field(default_factory=tuple)

    def render(self) -> str:
        out = [f"[{self.name}]  {self.title}", "=" * 78]
        out.append("  " + "".join(c.head() for c in self.columns))
        if any(c.unit for c in self.columns):
            out.append("  " + "".join(c.unit_head() for c in self.columns))
        out.append("  " + "-" * sum(c.width + len(Column.GAP) for c in self.columns))
        for row in self.rows:
            out.append("  " + "".join(
                col.cell(val) for col, val in zip(self.columns, row, strict=True)))
        for note in self.notes:
            out.append(f"\n  {note}")
        if self.sources:
            out.append("\n  Sources:")
            for ref in self.sources:
                where = ref.url or f"see SOURCES.md / docs ({ref.tier})"
                out.append(f"    {ref.key:<16}{where}")
        return "\n".join(out)


# ------------------------------------------------------- comment 2: the units

def table_npv_units() -> Table:
    """Every headline figure with its unit AND the money it is for a real plant.

    Comment 2: *why is it thousands, no way EUR 1,000 per tonne.* Because it is
    not per tonne of steel and it is not a total - it is per tonne of ANNUAL
    capacity, and the absolute column is what makes that checkable.
    """
    rows = []
    for label, (per_t, total) in units.headline_in_money(REFERENCE_MT).items():
        rows.append([label, f"{per_t:,.0f}", units.eur(total), "EUR/t capacity"])
    p, sc = published_base()
    o = outputs(p, sc)
    rows.append(["trigger p*'", f"{o.trigger:,.2f}", "n/a - it is a price",
                 "EUR/tCO2"])
    rows.append(["opex penalty a", f"{-60:,.0f}", "n/a - it is a flow",
                 "EUR/t product/yr"])
    return Table(
        "T1 units",
        "Comment 2 - what unit is the NPV in, and what is that in money?",
        [Column("quantity", "", 34, "<"), Column("value", "as quoted", 12),
         Column(f"for {REFERENCE_MT:g} Mt/yr", "absolute", 22),
         Column("unit", "", 20, "<")],
        rows,
        [f"Read the middle column, not the left one. EUR 900/t of ANNUAL capacity"
         f" is\n  {units.eur(units.absolute(900, REFERENCE_MT))} for a "
         f"{REFERENCE_MT:g} Mt/yr works. Stegra's Boden is that size and cost "
         "EUR 6.5bn.",
         "Only the EUR/t-capacity rows convert to money this way. A price "
         "(EUR/tCO2)\n  and a flow (EUR/t product/yr) have different "
         "denominators and do not.",
         "Scaling is linear: halve the plant, halve the absolute column."],
        resolve("S20_TKH2", "S21_SALCOS", "S22_STEGRA", "S30_AM_DUNKIRK", "S13_AM_CANCEL"),
    )


def table_npv_cases() -> Table:
    """The NPV itself, in money, across every sourced case.

    The table to reach for when the question is simply *how much is it worth*.
    The per-tonne column is what the model computes; the money column is that
    times a real plant's annual tonnes. They are one statement, not two.
    """
    base_npv = sourced.run_case("base").out.npv0
    cen = sourced.run_case("central")
    rows = []
    for c in sourced.all_cases():
        rows.append([
            c.name, f"{c.I0:,.0f}", f"{c.p_H2:.2f}", f"{c.out.npv0:,.0f}",
            units.eur(units.absolute(c.out.npv0, REFERENCE_MT)),
            f"{c.out.trigger:.1f}", str(c.out.t_star or "none"),
        ])
    per_mt = units.eur(units.absolute(base_npv, 1.0))
    return Table(
        "T2 NPV in money",
        "How much money is the NPV? Billions - and it depends which inputs you use",
        [Column("case", "", 10, "<"), Column("I0", "EUR/t cap", 11),
         Column("p_H2", "EUR/kg", 9), Column("NPV", "EUR/t cap", 11),
         Column("NPV, 2.5 Mt/yr", "EUR absolute", 18),
         Column("trigger", "EUR/tCO2", 11), Column("T*", "year", 7)],
        rows,
        ["The NPV is a RATE - EUR per tonne of ANNUAL capacity. Multiply by annual"
         "\n  tonnes and it is money: the fifth column. About " + per_mt + " per Mt/yr"
         "\n  of capacity in the published case.",
         "Stegra's Boden is exactly 2.5 Mt/yr and cost EUR 6.5bn to build. The"
         "\n  published case says the switch alone is worth "
         + units.eur(units.absolute(base_npv, REFERENCE_MT)) + " on a modelled spend"
         "\n  of " + units.eur(units.absolute(Params().sector.I0, REFERENCE_MT))
         + ". The sourced central case says "
         + units.eur(units.absolute(cen.out.npv0, REFERENCE_MT)) + " on "
         + units.eur(units.absolute(cen.I0, REFERENCE_MT)) + ".",
         "So 'how much money' is a RANGE across these four rows, not one figure."
         "\n  Which end you believe is the whole argument."],
        resolve("S20_TKH2", "S21_SALCOS", "S22_STEGRA", "S9_PLATTS", "diw2082"),
    )


# ------------------------------------------------------- comment 3: real cases

def outcome(status: str) -> str:
    """Three states, from the free-text status column.

    ``sourced._is_live`` answers a narrower question - is this project under
    construction - and groups Dunkirk with the cancelled scheme because it is
    EAF-only, which is right for that comparison and wrong as a label. Dunkirk
    was confirmed, not stopped. This keeps the two apart.
    """
    s = status.lower()
    if "cancelled" in s:
        return "CANCELLED"
    if "construction" in s or "commissioning" in s:
        return "BUILDING"
    if "confirmed" in s:
        return "CONFIRMED"
    return status[:10]


def table_capex() -> Table:
    """Announced projects: absolute, capacity, per-tonne, boundary, outcome.

    Comment 3: *land the equations on real cases, different companies.* The
    boundary column is what stops this being five numbers in a row - EUR 600/t
    and EUR 2,600/t describe different scopes of work.
    """
    rows = []
    for r in src.projects():
        total = r.num("capex_EUR_absolute")
        mt = r.num("capacity_Mt_per_yr")
        per_t = r.num("capex_EUR_per_t_capacity")
        if total is None or not mt or per_t is None:
            continue
        aid = r.num("public_support_EUR")
        rows.append([
            r["project"][:26], units.eur(total), f"{mt:g}", f"{per_t:,.0f}",
            units.eur(aid) if aid else "-",
            outcome(r["status"]),
        ])
    p = Params()
    rows.append(["-- this model, I0 --",
                 units.eur(units.absolute(p.sector.I0, REFERENCE_MT)),
                 f"{REFERENCE_MT:g}", f"{p.sector.I0:,.0f}", "-", "-"])
    return Table(
        "T3 capex",
        "Comment 3 - capex from real projects, not a single assumed number",
        [Column("project", "", 28, "<"), Column("announced", "EUR total", 12),
         Column("capacity", "Mt/yr", 10), Column("capex", "EUR/t cap", 11),
         Column("public aid", "EUR total", 12), Column("outcome", "", 10)],
        rows,
        ["Every project BUILDING costs at least EUR 1,300/t of capacity. The two"
         "\n  at or below the model's EUR 900 are Dunkirk - confirmed, but EAF only,"
         "\n  no DRI and no electrolyser - and Bremen, which ArcelorMittal CANCELLED,"
         "\n  forfeiting EUR 1.3bn of approved German aid. Neither is a cheaper way"
         "\n  of doing the same work.",
         "The per-tonne column is the absolute divided by the capacity, which is"
         "\n  why EUR 900/t and EUR 2.2bn are the same kind of statement.",
         "Boundaries differ and are not comparable line for line: Dunkirk is EAF"
         "\n  only; tkH2Steel excludes the electrolyser; Boden includes 700-800 MW"
         "\n  of it plus rolling. See data/sourced/projects_capex.csv."],
        resolve("S20_TKH2", "S21_SALCOS", "S22_STEGRA", "S30_AM_DUNKIRK", "S13_AM_CANCEL"),
    )


# ------------------------------------------ comments 1 and 5: the opex stack

def table_opex() -> Table:
    """The opex delta, line by line: what the model has, and what it is missing.

    Comments 1 and 5: *make sure the opex is actually related to the industry.*
    The model collapses the whole BF-BOF vs H2-DRI-EAF difference into
    ``a = -(55*p_H2 - 83)`` - one hydrogen term and one lumped credit. This
    table puts the real cost lines beside it, computes the ones the build has
    data for, and marks the rest.
    """
    series = eurostat.refresh(offline=True)
    de_power = series["power_DE"].value
    se_power = series["power_SE"].value
    h2_at_5 = 55.0 * 5.00

    onsite_de = 55.0 * eurostat.KWH_PER_KG_H2 * de_power
    rows = [
        ["HYDROGEN - pick ONE of the two", "", "", "", ""],
        ["  bought, at EUR 5.00/kg", "in a", "55 kg/t x EUR 5.00",
         f"{h2_at_5:,.0f}", "S9_PLATTS"],
        ["  bought, at the base 2.60", "in a", "55 kg/t x EUR 2.60",
         f"{55.0 * 2.60:,.0f}", "S9_PLATTS"],
        ["  OR made on site, DE power", "NOT in a",
         f"3,025 kWh/t x {de_power:.4f}", f"{onsite_de:,.0f}", "eurostat"],
        ["", "", "", "", ""],
        ["EVERYTHING ELSE - all additive", "", "", "", ""],
        ["  avoided BF-route costs", "in a", "lumped, not derived", "-83",
         "assumption"],
        ["  EAF electricity, DE", "NOT in a", f"650 kWh/t x {de_power:.4f}",
         f"{650.0 * de_power:,.0f}", "S49/eurostat"],
        ["  EAF electricity, SE", "NOT in a", f"650 kWh/t x {se_power:.4f}",
         f"{650.0 * se_power:,.0f}", "S49/eurostat"],
        ["  graphite electrodes", "NOT in a", "1.5-3 kg/t x $2.0-4.1k/t",
         "3 - 12", "S46"],
        ["  DR-grade pellet premium", "NOT in a", "$3-10/t over BF grade",
         "3 - 10", "S47 (D4)"],
        ["  scrap, alloys, lime", "NOT in a", "not quantified", MISSING, "H10"],
        ["  avoided coking coal/PCI/coke", "NOT in a", "20-25% of BF cost",
         MISSING, "H10"],
        ["  refractories, labour, maint.", "NOT in a", "not quantified",
         MISSING, "H10"],
    ]
    return Table(
        "T4 opex",
        "Comments 1 and 5 - the opex delta, and how much of it the model carries",
        [Column("cost line", "", 31, "<"), Column("status", "", 9, "<"),
         Column("basis", "", 24, "<"), Column("value", "EUR/t prod/yr", 13),
         Column("source", "", 13, "<")],
        rows,
        ["THE EITHER/OR MATTERS. Buying hydrogen and making it on site are"
         "\n  alternatives, not additions - 55 kg/t at 55 kWh/kg is 3,025 kWh/t, the"
         "\n  same energy the merchant price already pays for. Adding both would"
         "\n  double-count the largest line in the table, which is the class of"
         "\n  boundary error this whole exercise exists to catch.",
         "The model's whole opex delta is `a`: one hydrogen row and the lumped"
         "\n  credit. Everything marked NOT in a is a real cost line it omits.",
         "The electricity rows are computed from this build's own Eurostat cache,"
         "\n  so they are observations, not estimates - and they are large: EAF power"
         f"\n  alone is EUR {650.0 * de_power:,.0f}/t in Germany against EUR "
         f"{650.0 * se_power:,.0f}/t in Sweden. That spread alone is"
         f"\n  EUR {650.0 * (de_power - se_power):,.0f}/t, comparable to the entire "
         "published opex delta of EUR -60/t.",
         "The rows marked MISSING are hole H10: no single techno-economic study"
         "\n  covering BOTH routes at ONE consistent boundary was found. Assembling"
         "\n  them from sources with different boundaries would invent the number"
         "\n  comment 5 asks us to stop inventing, so they stay empty.",
         "Until H10 closes, c_avoided = 83 is an assumption, not a sum."],
        resolve("eurostat_power", "S9_PLATTS", "S47_PELLET", "S46_ELECTRODES"),
    )


# ------------------------------------------- comment 1: fiscal, power vs gas

def table_power_vs_gas() -> Table:
    """Industrial electricity against industrial gas, per state, per kWh.

    Comment 1 asks whether *electricity is cheaper than gas*. Per unit of
    delivered energy, excluding taxes, it is not - anywhere. That is the whole
    reason a green hydrogen floor sits above a grey one, and it is observed
    data rather than an assumption.
    """
    series = eurostat.refresh(offline=True)
    rows = []
    for geo in eurostat.STEEL_GEOS:
        power = series[f"power_{geo}"].value
        gas = series[f"gas_{geo}"].value
        green = eurostat.hydrogen_power_floor(power)
        grey = eurostat.hydrogen_gas_floor(gas, 76.0)
        rows.append([geo, f"{power:.4f}", f"{gas:.4f}", f"{power / gas:.1f}x",
                     f"{green:.2f}", f"{grey:.2f}"])
    rows.sort(key=lambda r: float(r[1]))
    return Table(
        "T5 energy",
        "Comment 1 - is electricity cheaper than gas? Not per kWh, nowhere",
        [Column("state", "", 8, "<"), Column("electricity", "EUR/kWh", 14),
         Column("gas", "EUR/kWh", 12), Column("ratio", "power/gas", 12),
         Column("green H2", "EUR/kg", 12), Column("grey H2", "EUR/kg", 12)],
        rows,
        ["Both price columns EXCLUDE taxes and levies (Eurostat bands IE and I5,"
         "\n  2025-S2). Electricity runs 2-4x gas per kWh in every member state.",
         "The two hydrogen columns are FLOORS, not prices: green is power x 55"
         "\n  kWh/kg and nothing else; grey is gas x 41.1 kWh/kg plus its ETS bill"
         "\n  at EUR 76/tCO2. Electrolyser capex, compression and transport are"
         "\n  excluded from both, so the real gap is wider than shown.",
         "WHAT IS MISSING (holes H6, H9): the decomposition into energy / network"
         "\n  charges / taxes / levies / exemptions, and the ETS indirect-cost"
         "\n  compensation each state pays. Those are exactly what 'fiscal"
         "\n  harmonisation' would change, and the model has no tax layer at all."],
        resolve("eurostat_power", "eurostat_gas", "iea_h2"),
    )


# ---------------------------------------------------- comment 4: the subsidy

def table_subsidies() -> Table:
    """Instruments by SHAPE, and what each is worth as a stock per tonne.

    Comment 4: *the subsidy pot and the shape of it.* A lump off capex and a
    stream per tonne of CO2 are different objects; eq (10) converts the second
    into the first's units so they can be compared without being averaged.
    """
    rows = []
    for r in src.support():
        pot = r.num("pot_EUR")
        raw = r.get("pot_EUR", "")
        if pot:
            pot_text = units.eur(pot)
        elif "allowance" in raw:
            pot_text = "400m allow."
        else:
            pot_text = MISSING
        basis = r.get("state_aid_basis", "") + " " + r.get("status", "")
        law = "PROPOSAL" if "PROPOSAL" in basis.upper() else "in force"
        strike = r.get("strike_or_clearing", "")
        rows.append([
            r["instrument"][:32], pot_text, r["SHAPE"][:18],
            r.get("duration_years", "") or "-",
            (MISSING if strike in ("NOT_CAPTURED", "NOT_DISCLOSED", "PENDING")
             else strike[:12] or "-"),
            law,
        ])
    return Table(
        "T6 subsidy pots",
        "Comment 4 - the subsidy pot, and its shape",
        [Column("instrument", "", 33, "<"), Column("pot", "total", 13),
         Column("shape", "", 19, "<"), Column("years", "", 6),
         Column("strike", "per unit", 12, "<"), Column("legal", "", 9, "<")],
        rows,
        ["SHAPE is the column that matters. The model nets a EUR 200/t capacity"
         "\n  LUMP off capex; the German CCfD - the one instrument here actually"
         "\n  awarded and running - pays a STREAM per tonne of CO2 over fifteen years.",
         "READ THE LEGAL COLUMN. The Investment Booster and the Industrial"
         "\n  Decarbonisation Bank are COM(2026) 616 proposals in co-decision, not"
         "\n  enacted law, and the EUR 100bn is Explanatory Memorandum framing -"
         "\n  appropriated against announced was not verified. Modelling either as"
         "\n  enacted would be a policy assumption wearing a data label.",
         "Strike prices marked MISSING are hole H1: the German awards are public,"
         "\n  the per-company strikes are not. So the stream's value below is derived"
         "\n  from the mechanism, never from an observed award."],
        resolve("S28_CCFD", "S10_EHB", "S4_COM2026"),
    )


def table_support_shape() -> Table:
    """eq (10): a per-tCO2 stream expressed in the lump's own units."""
    lump = Params().policy.s_max
    rows = []
    for premium in (20.0, 30.0, 40.0, 50.0):
        worth = sourced.support_shape(premium)
        rows.append([f"{premium:,.0f}", f"{worth:,.0f}",
                     units.eur(units.absolute(worth, REFERENCE_MT)),
                     f"{worth / lump:.1f}x"])
    rows.append(["the model's lump", f"{lump:,.0f}",
                 units.eur(units.absolute(lump, REFERENCE_MT)), "1.0x"])
    return Table(
        "T7 subsidy shape",
        "Comment 4 - what a CCfD-style stream is worth against the model's lump",
        [Column("premium", "EUR/tCO2", 18, "<"), Column("worth", "EUR/t cap", 12),
         Column(f"for {REFERENCE_MT:g} Mt/yr", "absolute", 20),
         Column("vs lump", "ratio", 10)],
        rows,
        ["eq (10): premium x b x sum of (1+r)^-k over 10 years, b = 1.8, r = 8%."
         "\n  The German instrument runs FIFTEEN years, so these understate it.",
         "Per-company strike prices were not disclosed (hole H1), so the premium"
         "\n  column is the mechanism's range, not an observed award."],
        resolve("S28_CCFD", "ec_ccfd", "zoe_idb"),
    )


# ------------------------------------------------------- all five, at a glance

def table_comment_status() -> Table:
    """Every review comment, what was done, and what blocks the rest."""
    rows = [
        ["1", "capex/opex/revenues/fiscal", "PARTIAL",
         "capex, revenue, carbon, subsidy done; no tax layer", "H6, H9"],
        ["2", "fix the NPV, why thousands", "DONE",
         "units restored; EUR 900/t = EUR 2.2bn at 2.5 Mt/yr", "H3 for EV/t"],
        ["3", "real cases, diff companies", "DONE",
         "5 named projects, capex + boundary + outcome", "-"],
        ["4", "subsidy pot and its shape", "DONE",
         "SHAPE column; stream valued against the lump", "H1 strikes"],
        ["5", "opex tied to the industry", "OPEN",
         "still one lumped hydrogen-driven constant", "H10"],
    ]
    return Table(
        "T0 status",
        "All five review comments (newcomments.md), and where each stands",
        [Column("#", "", 4, "<"), Column("comment", "", 30, "<"),
         Column("status", "", 10, "<"), Column("what exists now", "", 52, "<"),
         Column("blocked by", "", 12, "<")],
        rows,
        ["Blockers are IDs in docs/research-open-items.md. H10 is the one that"
         "\n  matters most: a line-by-line BF-BOF vs H2-DRI-EAF opex stack at a"
         "\n  single consistent boundary. Without it, comment 5 cannot be closed"
         "\n  honestly - only plausibly."],
        resolve("S4_COM2026"),
    )


def all_tables() -> list[Table]:
    """Every finalised table, in the order the comments are numbered."""
    return [
        table_comment_status(),
        table_npv_units(),
        table_npv_cases(),
        table_capex(),
        table_opex(),
        table_power_vs_gas(),
        table_subsidies(),
        table_support_shape(),
    ]


def main() -> int:
    """Print every table. Reports; does not gate."""
    for i, table in enumerate(all_tables()):
        if i:
            print("\n")
        print(table.render())
    print("\n\n  Every column above states its unit in the header. Where a cell is")
    print("  MISSING it is a documented hole, not a zero and not an estimate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
