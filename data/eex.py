"""The EU ETS carbon price and the money it raises, from the auction results.

Why this module exists
----------------------
Every other observed input in the build grounds an *assumption*. This one
grounds the model's state variable. ``p`` in eq (1) is the EUA price, and until
now the build had no observation of it at all - the specification's central
path (76, 86, 96, 104, 112 EUR/tCO2 for 2026-2030) was quoted from the v11
document and never once compared against what allowances actually clear at.
:mod:`eurostat` said as much in its own docstring: the EUA series "cannot be
sourced from open data and needs a market-data terminal". That was wrong.

EEX runs the primary market auctions for the EU ETS on behalf of the Member
States and publishes every clearing price, volume and the revenue each state
received, as an openly downloadable workbook, updated the same day. That is a
primary source in the strict sense used by ``sources.py``: not a report about
the market, the market's own settlement record.

What it yields
--------------
* **The clearing price** - EUR/tCO2, dated, which is ``p`` observed.
* **A twenty-auction mean** - because a single clearing price is a day's
  weather. The model's drift and volatility are annual; the mean is what a
  comparison against a path anchor can honestly use.
* **Auction revenue, year to date** - real money, in euros, and the closest
  thing in the build to an actual subsidy pot. Comment 4 asked how large the
  pot is and what shape it has; the announced envelopes in
  ``support_instruments.csv`` are political statements about the future, while
  this is cash that has already been received.
* **Revenue by member state** - the same money split by who got it, which is
  the layer at which a national support scheme is actually funded.
* **Realised volatility** - the annualised standard deviation of the log
  clearing price, estimated over the EU-wide auctions. The model's ``sigma``
  is the only parameter that moves the trigger without moving the break-even
  (finding 1), and it was assumed; this is the first evidence in the build
  about what it actually is.

Boundary: auction revenue is not earmarked for steel, or for industry, or for
decarbonisation beyond the ETS Directive's non-binding spending clause. It is
the size of the pot, not a commitment to spend it on this. The tables say so
wherever the figure appears.

Same offline rule as the other providers: fetch, cache, never raise on a
network failure.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import math
import pathlib
import re
import types
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from typing import Final

from data.observed import (
    Series,
    cache_read,
    cache_write,
    fetch_or_cache,
    get_bytes,
)

CACHE = pathlib.Path(__file__).with_name("eex_cache.json")

#: The auction report for the current compliance year. EEX republishes this
#: same URL after every auction, so it is always the live file rather than a
#: dated snapshot.
REPORT_URL: Final[str] = (
    "https://public.eex-group.com/eex/eua-auction-report/"
    "emission-spot-primary-market-auction-report-{year}-data.xlsx"
)

#: Landing page a reader should open to check any figure here by hand.
REPORT_PAGE: Final[str] = (
    "https://www.eex.com/en/market-data/market-data-hub/environmentals/"
    "eex-eua-primary-auction-spot-download"
)

SOURCE: Final[str] = "EEX EU ETS primary market auction report"

#: Excel's day zero. 1899-12-30, not 1900-01-01, because of the 1900 leap-year
#: bug Excel preserves for Lotus compatibility.
EXCEL_EPOCH: Final[dt.date] = dt.date(1899, 12, 30)

_NS: Final[str] = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

#: Column letters in the published layout. Held as a constant because EEX has
#: moved them before, and a silent column shift is the failure mode that would
#: put a volume where a price belongs - see :func:`_header_is_intact`.
COL_DATE: Final[str] = "B"
COL_ZONE: Final[str] = "Z"
COL_PRICE: Final[str] = "G"
COL_VOLUME: Final[str] = "L"
COL_REVENUE: Final[str] = "Y"

#: What each of those headers must say for the columns above to be believed.
EXPECTED_HEADERS: Final[dict[str, str]] = {
    COL_DATE: "Date",
    COL_ZONE: "Zone",
    COL_PRICE: "Auction Price",
    COL_VOLUME: "Auction Volume",
    COL_REVENUE: "Total Revenue",
}

#: Days in a year, for annualising a volatility estimated on calendar gaps.
#: Calendar days rather than trading days: the gaps between auctions are
#: measured on the calendar, so the scaling has to be too.
DAYS_PER_YEAR: Final[float] = 365.25

#: Fewest EU-wide auctions that will support a volatility estimate. Below this
#: the standard error swamps the estimate, and a volatility quoted without one
#: is worse than none.
MIN_VOL_SAMPLE: Final[int] = 30

#: How many auctions the smoothed price averages over. Twenty is about a
#: calendar month of auction days: long enough that one thin session cannot
#: move it, short enough to still be a statement about now.
MEAN_WINDOW: Final[int] = 20

#: Beneficiaries the tables report by name. The first five are the steel-making
#: member states the energy prices are read for; the last two are the two EU
#: funds the auction record pays directly, and ``IF`` is the Innovation Fund -
#: the instrument ``policy.s_max`` is modelled on. Its receipts here are the
#: only figure in the build that is both an actual subsidy pot and money that
#: has already been collected rather than announced.
REPORTED_ACCOUNTS: Final[tuple[str, ...]] = ("DE", "NL", "PL", "ES", "FR",
                                             "IF", "MF")

#: Accounts that are EU funds rather than member states, so a table never
#: reports them as national money.
EU_FUNDS: Final[frozenset[str]] = frozenset({"IF", "IX", "MF", "SF", "MX"})


@dataclass(frozen=True)
class Auction:
    """One cleared auction: when, for whom, at what price, for how much money.

    ``shares`` splits :attr:`revenue_eur` by who received it, keyed by the
    two-letter code the workbook prints in its header - member states, plus the
    Innovation, Modernisation and Social Climate Funds. It is populated for
    EU-wide auctions, where the ETS Directive's allocation key applies; a
    national auction carries a single entry for the state that held it.
    """

    date: str
    zone: str
    price: float
    volume_t: float
    revenue_eur: float
    shares: Mapping[str, float] = dataclasses.field(
        default_factory=lambda: types.MappingProxyType({}))

    @property
    def implied_price(self) -> float:
        """Revenue over volume. Must equal the clearing price; see the tests.

        A uniform-price auction has exactly one clearing price, so this is a
        redundant derivation - which is the point. It is the arithmetic check
        that the price column and the revenue column are the columns this
        module thinks they are.
        """
        return self.revenue_eur / self.volume_t if self.volume_t else 0.0


def _cells(sheet: ET.Element, strings: list[str]) -> list[dict[str, str]]:
    """Rows of the worksheet as ``{column letter: resolved text}``.

    A cell marked ``t="s"`` holds an *index* into the shared string table, not a
    value. Resolving that here rather than at each use site is the whole reason
    this function takes the string table: an empty string cell stores index 2
    as readily as a number does, so a caller that skipped the lookup would read
    ``EUR 2`` where the workbook says nothing at all - which is precisely the
    failure ``test_the_revenue_split_sums_to_the_revenue`` caught.
    """
    rows: list[dict[str, str]] = []
    for row in sheet.iter(f"{_NS}row"):
        cells: dict[str, str] = {}
        for cell in row.findall(f"{_NS}c"):
            ref = cell.get("r") or ""
            value = cell.find(f"{_NS}v")
            if value is None or value.text is None:
                continue
            text = value.text
            if cell.get("t") == "s":
                index = int(text)
                text = strings[index] if index < len(strings) else ""
            cells["".join(ch for ch in ref if ch.isalpha())] = text
        if cells:
            rows.append(cells)
    return rows


def _strings(archive: zipfile.ZipFile) -> list[str]:
    """The workbook's shared string table, flattened."""
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(t.text or "" for t in item.iter(f"{_NS}t")) for item in root]


def _header_is_intact(row: dict[str, str]) -> bool:
    """Whether the header row still says what the column constants assume.

    EEX has rearranged this workbook before. Without this check a column
    insertion would not raise anything - it would quietly report an auction
    volume as a price, and every downstream figure would be wrong by five
    orders of magnitude while still looking like a number.
    """
    return all(row.get(column, "").startswith(expected)
               for column, expected in EXPECTED_HEADERS.items())


def _to_date(serial: str) -> str:
    """An Excel date serial as an ISO date."""
    return (EXCEL_EPOCH + dt.timedelta(days=int(float(serial)))).isoformat()


#: The code in a beneficiary header, e.g. "Germany\n(DE)" or "Innovation
#: Fund\n(IF)". Anchored to the end so a stray parenthesis in a country name
#: cannot match.
_ACCOUNT_CODE: Final[re.Pattern[str]] = re.compile(r"\(([A-Z]{2})\)\s*$")


def _accounts(header: dict[str, str]) -> dict[str, str]:
    """Column letter -> beneficiary code, for the revenue-split columns.

    These sit to the right of ``Zone`` and each carries a name and a
    parenthesised code. Reading them by code rather than by position is what
    lets the split survive the EU admitting a member state or adding a fund.
    """
    found: dict[str, str] = {}
    for column, text in header.items():
        match = _ACCOUNT_CODE.search(text.replace("\n", " "))
        if match and len(column) > 1:  # AA onwards; never a single-letter column
            found[column] = match.group(1)
    return found


def parse_report(blob: bytes) -> tuple[Auction, ...]:
    """Every successful auction in the workbook, newest first.

    Raises :class:`ValueError` if the header row does not match the column
    layout this module was written against, rather than returning plausible
    nonsense.
    """
    with zipfile.ZipFile(BytesIO(blob)) as archive:
        strings = _strings(archive)
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows = _cells(sheet, strings)

    header = next((r for r in rows if _header_is_intact(r)), None)
    if header is None:
        raise ValueError(
            f"{SOURCE}: no row matches the expected header layout "
            f"{EXPECTED_HEADERS}; the published columns have moved")

    accounts = _accounts(header)
    out: list[Auction] = []
    for row in rows[rows.index(header) + 1:]:
        try:
            zone = row.get(COL_ZONE, "")
            shares: dict[str, float] = {}
            for column, code in accounts.items():
                try:
                    amount = float(row[column])
                except (KeyError, ValueError):
                    continue
                if amount:
                    shares[code] = shares.get(code, 0.0) + amount
            out.append(Auction(
                date=_to_date(row[COL_DATE]),
                zone=str(zone),
                price=float(row[COL_PRICE]),
                volume_t=float(row[COL_VOLUME]),
                revenue_eur=float(row[COL_REVENUE]),
                shares=types.MappingProxyType(shares),
            ))
        except (KeyError, ValueError, IndexError):
            continue  # a spacer, a footnote, or an auction that did not clear
    if not out:
        raise ValueError(f"{SOURCE}: header found but no auction rows under it")
    return tuple(sorted(out, key=lambda a: a.date, reverse=True))


_loaded: dict[int, tuple[Auction, ...]] = {}


def auctions(year: int | None = None) -> tuple[Auction, ...]:
    """The published auctions for ``year``, downloaded once per process.

    Falls back to the previous year's report in January, when the current
    year's file exists but may hold no cleared auction yet.
    """
    year = year or dt.date.today().year
    if year not in _loaded:
        try:
            _loaded[year] = parse_report(get_bytes(REPORT_URL.format(year=year)))
        except (ValueError, OSError) as exc:
            if year == dt.date.today().year:
                _loaded[year] = auctions(year - 1)
            else:
                raise ValueError(f"{SOURCE}: {exc}") from exc
    return _loaded[year]


# ------------------------------------------------------------------- series

def clearing_price(cache: dict, offline: bool = False) -> Series:
    """The most recent EUA auction clearing price, EUR/tCO2.

    This is the model's ``p`` observed. It is a single session, so read it with
    :func:`price_mean` beside it, not on its own.
    """
    def latest() -> tuple[str, float]:
        a = auctions()[0]
        return a.date, a.price

    return fetch_or_cache(
        "eua_clearing_price", cache, offline, latest,
        "EUA auction clearing price", "EUR/tCO2", SOURCE)


def price_mean(cache: dict, offline: bool = False) -> Series:
    """Volume-weighted mean clearing price over the last :data:`MEAN_WINDOW`.

    Volume-weighted rather than a plain mean because the national auctions are
    a fraction of the size of the EU-wide ones, and an unweighted average would
    let a small Polish session count as much as a full EU one.
    """
    def mean() -> tuple[str, float]:
        window = auctions()[:MEAN_WINDOW]
        volume = sum(a.volume_t for a in window)
        if not volume:
            raise ValueError("no volume in the averaging window")
        weighted = sum(a.price * a.volume_t for a in window) / volume
        return f"{window[-1].date}..{window[0].date}", weighted

    return fetch_or_cache(
        "eua_price_mean", cache, offline, mean,
        f"EUA clearing price, {MEAN_WINDOW}-auction volume-weighted mean",
        "EUR/tCO2", SOURCE)


def realised_volatility(cache: dict, offline: bool = False) -> Series:
    """Annualised volatility of the EUA price, from the auction series itself.

    EU-wide auctions only. The national auctions clear a different, much
    smaller pool on their own calendar, and interleaving all three would read
    the spread between pools as price movement - variance that is an artefact
    of which auction happened to be next, not of the price.

    Irregularly spaced, so the estimator divides each squared log return by the
    time between the two auctions rather than assuming a fixed step:
    ``sigma^2 = mean(ln(p_t/p_s)^2 / (t - s))`` in years. Under the geometric
    Brownian motion the model assumes, that is the maximum-likelihood estimate
    of the diffusion coefficient.

    This is *realised* volatility over one year of auctions. It is not the
    implied volatility of an option on the price, and it is not a forecast to
    2050. The model's sigma stays where the specification put it; what this
    number does is say how far that assumption is from one year's evidence.
    """
    def estimate() -> tuple[str, float]:
        rows = [a for a in auctions() if a.zone.upper() == "EU"]
        if len(rows) < MIN_VOL_SAMPLE:
            raise ValueError(
                f"{len(rows)} EU auctions is too few for a volatility estimate")
        rows = sorted(rows, key=lambda a: a.date)
        total, n = 0.0, 0
        for earlier, later in zip(rows, rows[1:], strict=False):
            days = (dt.date.fromisoformat(later.date)
                    - dt.date.fromisoformat(earlier.date)).days
            if days <= 0 or earlier.price <= 0 or later.price <= 0:
                continue
            total += math.log(later.price / earlier.price) ** 2 / (days / DAYS_PER_YEAR)
            n += 1
        if not n:
            raise ValueError("no usable consecutive pairs")
        return f"{rows[0].date}..{rows[-1].date}", math.sqrt(total / n)

    return fetch_or_cache(
        "eua_volatility", cache, offline, estimate,
        "EUA realised volatility, EU-wide auctions", "1/yr^0.5", SOURCE)


def auction_revenue(cache: dict, offline: bool = False) -> Series:
    """Total money raised at auction so far this year, EUR.

    Not earmarked for steel or for industry. This is the size of the pot, and
    the tables that quote it say so on the same row.
    """
    def total() -> tuple[str, float]:
        rows = auctions()
        return f"{rows[-1].date}..{rows[0].date}", sum(a.revenue_eur for a in rows)

    return fetch_or_cache(
        "eua_revenue_ytd", cache, offline, total,
        "EU ETS auction revenue, year to date", "EUR", SOURCE)


def auction_volume(cache: dict, offline: bool = False) -> Series:
    """Allowances sold at auction so far this year, tCO2."""
    def total() -> tuple[str, float]:
        rows = auctions()
        return f"{rows[-1].date}..{rows[0].date}", sum(a.volume_t for a in rows)

    return fetch_or_cache(
        "eua_volume_ytd", cache, offline, total,
        "EU ETS auction volume, year to date", "tCO2", SOURCE)


def account_revenue(code: str, cache: dict, offline: bool = False) -> Series:
    """Auction revenue received by one beneficiary so far this year, EUR.

    Counts both halves of the record: the national auctions a member state
    holds for itself, and its share of the EU-wide auctions under the ETS
    Directive's allocation key. Reporting only the first would have understated
    the Netherlands to zero - it holds no national auctions at all - while
    Germany, which does, would have looked like the largest recipient.

    For an EU fund (``IF``, ``MF``, ``SF``) there is no national half and the
    figure is the whole of what the auctions paid it.
    """
    def total() -> tuple[str, float]:
        rows = auctions()
        amount = sum(a.shares.get(code.upper(), 0.0) for a in rows)
        if not amount:
            raise ValueError(f"no auction revenue attributed to {code!r}")
        return f"{rows[-1].date}..{rows[0].date}", amount

    kind = "EU fund" if code.upper() in EU_FUNDS else "member state"
    return fetch_or_cache(
        f"eua_revenue_{code}", cache, offline, total,
        f"EU ETS auction revenue, {code} ({kind})", "EUR", SOURCE)


def refresh(offline: bool = False) -> dict[str, Series]:
    """Fetch (or load) every series. Never raises on a network failure."""
    cache = cache_read(CACHE)
    out: dict[str, Series] = {}
    plain = (("clearing_price", clearing_price), ("price_mean", price_mean),
             ("volatility", realised_volatility),
             ("revenue_ytd", auction_revenue), ("volume_ytd", auction_volume))
    for name, fn in plain:
        try:
            out[name] = fn(cache, offline)
        except LookupError:
            continue
    for code in REPORTED_ACCOUNTS:
        try:
            out[f"revenue_{code}"] = account_revenue(code, cache, offline)
        except LookupError:
            continue
    if not offline:
        cache_write(CACHE, cache)
    return out


def main() -> int:
    """Print the auction record: what cleared, and who received the money.

    Reports the observation only. Comparing it against the model's price path
    is ``analysis.market``'s job, not this module's - a provider that knew what
    the model assumed would be one step from shaping a series to suit it.
    """
    observed = refresh()
    print("Observed EU ETS auction results\n" + "=" * 72)
    for series in observed.values():
        print(" ", series.cite())

    if "revenue_ytd" in observed and "volume_ytd" in observed:
        pot = observed["revenue_ytd"].value
        volume = observed["volume_ytd"].value
        print(f"\n  Raised at auction so far this year: EUR {pot:,.0f}")
        print(f"  on {volume:,.0f} tCO2, i.e. EUR {pot / volume:,.2f}/tCO2 "
              "averaged over the year.")
        print("  NOT earmarked for steel, for industry, or for any one plant.")
    if "revenue_IF" in observed:
        fund = observed["revenue_IF"].value
        print(f"\n  The Innovation Fund received EUR {fund:,.0f} of that.")
        print("  It is money collected rather than an envelope announced,")
        print("  which is what makes it a different kind of figure from the")
        print("  instruments listed in data/sourced/support_instruments.csv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
