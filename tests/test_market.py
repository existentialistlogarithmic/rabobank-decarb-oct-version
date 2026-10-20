"""The live data: that it parses, that it is the column it says, that it holds.

Two risks are specific to data arriving over a network, and neither is covered
by the rest of the suite.

The first is a **silent column shift**. The EU ETS auction results are an Excel
workbook, and EEX has rearranged it before. Reading a volume where a price
belongs would not raise anything - it would produce a number five orders of
magnitude wrong that still renders as a number. So the parser checks the header
row, and the arithmetic check below proves the mapping independently: a
uniform-price auction has exactly one clearing price, so revenue over volume
must equal the price column for every row.

The second is **a run that depends on the weather**. Every test here runs from
the committed cache, and the offline test asserts that no fetch is attempted.
"""

from __future__ import annotations

import datetime as dt
import zipfile
from io import BytesIO

import pytest

from analysis import market, tables
from data import eex, observed
from timing_model.params import Params


@pytest.fixture(scope="module")
def auctions() -> tuple[eex.Auction, ...]:
    """The auction record, parsed once. Network if available, else the cache."""
    try:
        return eex.auctions()
    except (ValueError, OSError):  # pragma: no cover - offline CI
        pytest.skip("no auction record reachable and none cached")


# ------------------------------------------- the columns are what we think

def test_revenue_over_volume_equals_the_clearing_price(auctions) -> None:
    """The proof that the price column is the price column.

    A uniform-price auction clears every successful bid at one price, so this
    derivation is redundant by construction - which is exactly why it is worth
    computing. If EEX inserted a column and the parser read the wrong cell,
    this identity would break on every row at once.
    """
    for a in auctions:
        assert a.volume_t > 0, a
        assert a.implied_price == pytest.approx(a.price, abs=0.01), a


def test_the_revenue_split_sums_to_the_revenue(auctions) -> None:
    """Each auction's per-recipient columns must account for all of its money.

    Tolerance is a euro per recipient: the workbook rounds each share to whole
    euros, so up to ~40 states and funds can drift the sum by tens of euros on
    a figure in the hundreds of millions.
    """
    for a in auctions:
        if not a.shares:
            continue
        assert sum(a.shares.values()) == pytest.approx(
            a.revenue_eur, abs=len(a.shares) + 1.0), a


#: A header row in the layout the parser was written against.
GOOD_HEADER = {"B": "Date", "G": "Auction Price EUR/tCO2",
               "L": "Auction Volume tCO2", "Y": "Total Revenue EUR",
               "Z": "Zone", "AA": "Germany\n(DE)"}


def test_a_moved_column_is_refused_rather_than_misread() -> None:
    """The negative control for the parser.

    Without this the header check is decoration. Shift the price one column to
    the right - exactly what inserting a column upstream would do - and the
    parser must raise rather than report a volume as a price.
    """
    moved = dict(GOOD_HEADER)
    moved["H"] = moved.pop("G")
    blob = _workbook([moved, {"B": "46287", "H": "85.53", "L": "1000",
                              "Y": "85530", "Z": "EU"}])
    with pytest.raises(ValueError, match="header"):
        eex.parse_report(blob)


def test_a_workbook_with_a_header_and_no_rows_is_refused() -> None:
    """An empty report is a failure, not an empty year."""
    with pytest.raises(ValueError, match="no auction rows"):
        eex.parse_report(_workbook([GOOD_HEADER]))


def test_an_empty_split_cell_is_not_read_as_a_string_index() -> None:
    """The bug this file was written to catch, pinned.

    A cell holding an empty string stores an *index* into the shared string
    table. Read without resolving the index, a blank recipient column returns
    whatever small integer that index happens to be - so a member state that
    received nothing from a national auction would report a few euros, and the
    split would no longer sum to the revenue.
    """
    rows = [GOOD_HEADER,
            {"B": "46287", "G": "85.53", "L": "1000", "Y": "85530",
             "Z": "DE", "AA": ""}]
    (auction,) = eex.parse_report(_workbook(rows))
    assert auction.shares == {}, "a blank share must be absent, not a stray number"
    assert auction.revenue_eur == pytest.approx(85_530.0)


def test_the_excel_epoch_is_the_one_excel_actually_uses() -> None:
    """1899-12-30, not 1900-01-01: Excel keeps the Lotus leap-year bug.

    Getting this wrong shifts every date by two days, which would quietly
    mislabel the period on an otherwise correct price.
    """
    assert dt.date(1899, 12, 30) == eex.EXCEL_EPOCH
    assert eex._to_date("46287") == "2026-09-22"


def test_auctions_come_back_newest_first(auctions) -> None:
    """`clearing_price` reads row zero, so the order is load-bearing."""
    dates = [a.date for a in auctions]
    assert dates == sorted(dates, reverse=True)


def test_every_auction_names_a_zone_and_a_date(auctions) -> None:
    for a in auctions:
        assert a.zone, a
        assert dt.date.fromisoformat(a.date)


# ---------------------------------------------------------- the offline rule

def test_offline_never_touches_the_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same rule as the other providers, enforced rather than trusted."""
    def explode(url: str) -> bytes:
        raise AssertionError(f"offline run attempted a fetch: {url}")

    for module in (observed, eex):
        monkeypatch.setattr(module, "get_bytes", explode)
    assert eex.refresh(offline=True)


def test_offline_series_say_they_are_cached() -> None:
    """A number's provenance includes how it arrived, not only who published it."""
    for series in eex.refresh(offline=True).values():
        assert not series.live
        assert "cached" in series.cite()


def test_the_cache_carries_the_price_and_the_pot() -> None:
    """A thinned cache would make T8 and T9 silently incomplete."""
    cached = eex.refresh(offline=True)
    for key in ("clearing_price", "price_mean", "revenue_ytd", "volume_ytd"):
        assert key in cached, key
    assert "revenue_IF" in cached, "the Innovation Fund row is what T8 turns on"


# ------------------------------------------------------------- the gaps

def test_every_gap_states_a_unit_and_a_period() -> None:
    """A bare number with no date is the thing this whole module argues against."""
    gaps = market.all_gaps(offline=True)
    assert len(gaps) >= 3
    for g in gaps:
        assert g.unit.strip(), g.what
        assert g.period.strip(), g.what
        assert g.money_is.strip(), g.what


def test_a_money_gap_is_money_and_a_rate_gap_is_not() -> None:
    """The distinction T1 exists to protect, applied to the live rows too."""
    by_name = {g.what: g for g in market.all_gaps(offline=True)}
    carbon = next(g for n, g in by_name.items() if n.startswith("EUA price"))
    assert carbon.money is not None and carbon.unit == "EUR/tCO2"
    rate = next(g for n, g in by_name.items() if n.startswith("discount rate"))
    assert rate.money is None, "a rate has no absolute; it must not get one"


def test_the_carbon_gap_money_is_the_gap_times_what_the_plant_emits() -> None:
    """Written out again rather than trusting the function that computed it."""
    g = market.carbon_gap(offline=True)
    _year, anchor = market.anchor_for()
    emissions = market.REFERENCE_MT * 1e6 * Params().common.eps_inc
    assert emissions == pytest.approx(4_750_000.0)
    assert g.money == pytest.approx((g.observed - anchor) * emissions)
    assert g.assumed == anchor


def test_the_support_gap_multiplies_the_rate_out_before_comparing() -> None:
    """EUR 200/t against a fund's receipts is a unit error; EUR 500m is not."""
    g = market.support_gap(offline=True)
    assert g.assumed == pytest.approx(200.0 * market.REFERENCE_MT * 1e6)
    assert g.assumed == pytest.approx(500e6)
    assert g.unit == "EUR"


def test_the_pot_totals_at_least_the_rows_it_breaks_out() -> None:
    """The named recipients are a subset of everyone, so they cannot exceed it."""
    rows = market.pot(offline=True)
    total = next(a for c, a, _ in rows if c.startswith("ALL"))
    named = sum(a for c, a, _ in rows if not c.startswith("ALL"))
    assert 0 < named < total


def test_the_live_layer_changes_no_model_input() -> None:
    """The load-bearing promise: reporting a gap must not move a parameter.

    Run the whole live layer, then check the published defaults are untouched.
    A module that quietly substituted today's carbon price for the path anchor
    would be indistinguishable from this one in every other test.
    """
    before = (Params().policy.s_max, Params().common.eps_inc, Params().sector.I0)
    market.all_gaps(offline=True)
    market.pot(offline=True)
    tables.table_market()
    tables.table_pot()
    after = (Params().policy.s_max, Params().common.eps_inc, Params().sector.I0)
    assert before == after
    _year, anchor = market.anchor_for()
    assert anchor == 76.0, "the 2026 anchor is published, not observed"


# ------------------------------------------------------------- the tables

def test_the_two_live_tables_are_on_the_list() -> None:
    names = [t.name for t in tables.all_tables()]
    assert "T8 market" in names and "T9 real pot" in names


def test_the_live_tables_cite_a_reachable_url() -> None:
    """These are the only tables whose source is fetched rather than quoted."""
    for table in (tables.table_market(), tables.table_pot()):
        urls = [s.url for s in table.sources if s.url]
        assert any("eex" in u for u in urls), table.name


def test_the_pot_table_says_the_money_is_not_earmarked() -> None:
    """The caveat that stops T9 being read as a funding commitment."""
    notes = " ".join(tables.table_pot().notes)
    assert "NOT earmarked" in notes
    assert "Directive" in notes


def test_the_market_table_says_it_feeds_nothing() -> None:
    notes = " ".join(tables.table_market().notes)
    assert "Nothing in this table feeds the model" in notes


# --------------------------------------------------------------- helpers

def _workbook(rows: list[dict[str, str]]) -> bytes:
    """A minimal .xlsx carrying ``rows``, keyed by column letter.

    Every cell is written as a shared string, which is how the real workbook
    stores its text and - importantly - its blanks. Built here rather than
    committed as a fixture so the negative controls stay readable: what is
    being tested is which header the parser accepts, and a binary fixture
    would hide that.
    """
    strings = sorted({v for row in rows for v in row.values()})
    index = {s: i for i, s in enumerate(strings)}
    cells = []
    for r, row in enumerate(rows, start=1):
        body = "".join(f'<c r="{col}{r}" t="s"><v>{index[val]}</v></c>'
                       for col, val in row.items())
        cells.append(f'<row r="{r}">{body}</row>')
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml",
                   f'<sst xmlns="{ns}">'
                   + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<worksheet xmlns="{ns}"><sheetData>'
                   + "".join(cells) + "</sheetData></worksheet>")
    return buf.getvalue()


# --------------------------------------------- what the volatility implies

def test_the_volatility_snaps_to_a_published_rung() -> None:
    """Off-ladder sigma would be a recalibration; the ladder is the spec's own.

    `volatility_implies` must return a rung that exists in Appendix A §3.4,
    never an interpolation between two of them.
    """
    from timing_model.params import SIGMA_REGIMES

    rung, sigma, out = market.volatility_implies(offline=True)
    assert rung in SIGMA_REGIMES
    assert sigma == SIGMA_REGIMES[rung]
    assert out.crossing_year is not None


def test_the_realised_volatility_is_above_the_assumed_one() -> None:
    """The finding, pinned. If this ever flips, the note in T8 is wrong.

    Deliberately an inequality rather than a value: the number moves with every
    auction, but the direction is what the table asserts in words.
    """
    g = market.volatility_gap(offline=True)
    assert g.observed > g.assumed, (
        "T8 and the brief both say realised volatility runs above the assumed "
        f"0.20; observed {g.observed:.3f}")
    assert 0.05 < g.observed < 1.5, "an implausible sigma means a parsing error"


def test_a_later_crossing_is_what_the_higher_sigma_buys() -> None:
    """Higher volatility raises the trigger, so the crossing moves out.

    The sign is the whole argument: more uncertainty makes the option to wait
    worth more. A build where this came out the other way would be broken in a
    way no cell-level check would catch.
    """
    from timing_model.results import outputs
    from timing_model.scenarios import published_base

    base = outputs(*published_base())
    _rung, _sigma, at_rung = market.volatility_implies(offline=True)
    assert at_rung.trigger > base.trigger
    assert at_rung.crossing_year > base.crossing_year


def test_the_volatility_uses_eu_wide_auctions_only() -> None:
    """Mixing auction pools would read the spread between them as movement.

    The national pools are much smaller and clear on their own calendar, so
    interleaving all three inflates sigma with an artefact. Checked by
    confirming the estimate over everything differs from the published one.
    """
    import math

    try:
        rows = eex.auctions()
    except (ValueError, OSError) as exc:
        pytest.skip(f"needs the live EEX auction record: {exc}")
    everything = sorted(rows, key=lambda a: a.date)
    total, n = 0.0, 0
    for earlier, later in zip(everything, everything[1:], strict=False):
        days = (dt.date.fromisoformat(later.date)
                - dt.date.fromisoformat(earlier.date)).days
        if days <= 0:
            continue
        total += (math.log(later.price / earlier.price) ** 2
                  / (days / eex.DAYS_PER_YEAR))
        n += 1
    mixed = math.sqrt(total / n)
    published = eex.realised_volatility(eex.cache_read(eex.CACHE), offline=True)
    assert mixed != pytest.approx(published.value, rel=0.01), (
        "the EU-only filter is not doing anything; check the zone column")


def test_too_few_auctions_is_refused_rather_than_estimated() -> None:
    """A sigma from five observations is noise wearing a number's clothes."""
    assert eex.MIN_VOL_SAMPLE >= 30


# --------------------------------------- the render layer never fetches

def test_rendering_a_page_never_touches_the_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pages render from the snapshot, not from whatever answers right now.

    Building six pages used to mean six rounds of HTTP, and - worse - two
    artefacts built minutes apart could quote different numbers for the same
    quantity. The refresh belongs to `run_all.py` section 8; everything
    downstream reads the committed caches.

    Patched at each provider's own namespace, because they bind the fetch
    helpers at import and patching `observed` alone would leave the real ones
    reachable.
    """
    from data import ecb, eurostat
    from reporting import brief, plots

    def explode(url: str) -> object:
        raise AssertionError(f"a render reached for the network: {url}")

    for module in (observed, eex):
        monkeypatch.setattr(module, "get_bytes", explode)
    for module in (observed, eurostat, ecb):
        monkeypatch.setattr(module, "get_json", explode)

    assert tables.table_market().rows
    assert tables.table_pot().rows
    assert "<svg" in plots.chart_carbon_gap()
    assert "<svg" in plots.chart_pot()
    assert "Does it still hold today?" in brief.build()
