"""What the market says today, against what the model assumes, in money.

Why this module exists
----------------------
Everything else in ``analysis/`` reasons about the model. This reasons about
the gap between the model and the world on the day it is run, which is a
different question and the one a reader asks first: *is this still true?*

Three gaps are worth stating, and each is stated in euros rather than in a
rate, because a rate is what made ``I0 = 900`` unreadable in the first place:

1. **The carbon price.** The specification anchors 2026 at EUR 76/tCO2. The
   EU ETS auctions clear daily and publish the price. The difference, times
   what the reference plant emits, is money on the plant's carbon bill this
   year.
2. **The pot.** ``policy.s_max`` is EUR 200/t of capacity, which for the
   reference plant is EUR 500m of public support. The Innovation Fund - the
   instrument that number is modelled on - publishes what it has actually
   received from the auctions. One is a claim on the other.
3. **Energy.** The clean route buys electricity; the incumbent buys gas. The
   comparison only means anything per unit of energy, and both prices are
   observed rather than assumed.

What this module does NOT do
----------------------------
It does not recalibrate anything. ``Params()`` still carries the published base
case and every result elsewhere in the build is unchanged by what the auction
cleared at this morning. A year of observations is not a path to 2050, and
substituting today's price for the specification's would replace a documented
assumption with an undocumented one. The gap is reported; the model is left
alone. Where a reader should draw a conclusion from the gap, the note says so
in words rather than moving a number quietly.

Who fetches, and who reads the cache
------------------------------------
``offline=False`` fetches. That belongs to exactly one place: ``run_all.py``
section 8, and running ``python -m analysis.market`` by hand. Everything that
*renders* - the tables, the charts, the brief, the deck - passes
``offline=True`` and reads the committed caches instead.

This is not only about speed, though building six pages used to mean six
rounds of HTTP. A page whose contents depend on whether a web service answered
while it was being written is not reproducible, and two pages built minutes
apart could quote different numbers for the same quantity. So the refresh
happens once, up front, and every artefact in a run is rendered from the same
snapshot. ``tests/test_market.py`` asserts it.
"""

from __future__ import annotations

import contextlib
import datetime as dt
from dataclasses import dataclass, replace
from typing import Final

from analysis import units
from data import ecb, eex, eurostat
from data.observed import Series
from timing_model.benefit import CENTRAL_PATH
from timing_model.params import SIGMA_REGIMES, Params
from timing_model.results import Outputs, outputs
from timing_model.scenarios import published_base

#: Plant the money columns are for, in Mt/yr. The same reference the rest of
#: the build uses, so a figure here is comparable with one in T1 or T2.
REFERENCE_MT: Final[float] = 2.5

#: Member states the national money column reports. Steel-producing states
#: plus the two EU funds the auction record pays directly.
REPORTED: Final[tuple[str, ...]] = eex.REPORTED_ACCOUNTS


@dataclass(frozen=True)
class Gap:
    """One assumption, one observation, and the money between them."""

    what: str
    assumed: float
    observed: float
    unit: str
    money: float | None
    money_is: str
    series: Series | None = None

    @property
    def delta(self) -> float:
        return self.observed - self.assumed

    @property
    def ratio(self) -> float:
        """Observed over assumed. 1.0 means the assumption still holds."""
        return self.observed / self.assumed if self.assumed else float("nan")

    @property
    def period(self) -> str:
        return self.series.period if self.series else "n/a"

    @property
    def live(self) -> bool:
        """Whether this run reached the source, or read the committed cache."""
        return bool(self.series and self.series.live)

    def show(self, value: float) -> str:
        """A value in this gap's unit, abbreviated when it is money.

        A carbon price wants two decimals and a fund's receipts want "EUR 2.0bn";
        printing either in the other's format is how a figure stops being read.
        """
        return units.eur(value) if self.unit == "EUR" else f"{value:,.2f}"


def anchor_for(year: int | None = None) -> tuple[int, float]:
    """The specification's central-path anchor for ``year``, and the year used.

    The path runs 2026-2030. Past its end the last anchor is carried forward,
    which is what the model itself does, and the year returned says which
    anchor answered so a table never implies an anchor that was not published.
    """
    year = year or dt.date.today().year
    if year in CENTRAL_PATH:
        return year, float(CENTRAL_PATH[year])
    last = max(CENTRAL_PATH)
    return last, float(CENTRAL_PATH[last])


def annual_emissions(mt_per_yr: float = REFERENCE_MT, p: Params | None = None) -> float:
    """tCO2 a year from the incumbent route at this size.

    The blast-furnace intensity, not the clean one: this is the bill the plant
    pays *before* it switches, which is the bill a carbon price is charged on
    while the decision is still open.
    """
    p = p or Params()
    return mt_per_yr * 1e6 * p.common.eps_inc


def carbon_gap(offline: bool = False) -> Gap:
    """Observed EUA clearing price against the path anchor, and what it costs.

    The money column is the difference on the reference plant's annual carbon
    bill at the incumbent route's intensity - EUR/tCO2 times tCO2 a year, which
    is money per year and is labelled as such rather than folded into the
    stock figures the NPV tables carry.
    """
    year, assumed = anchor_for()
    series = eex.price_mean(eex.cache_read(eex.CACHE), offline)
    delta = series.value - assumed
    return Gap(
        f"EUA price, {year}", assumed, series.value, "EUR/tCO2",
        delta * annual_emissions(), "a year on the reference plant's carbon bill",
        series)


def support_gap(offline: bool = False) -> Gap:
    """The modelled support for one plant against the Innovation Fund's receipts.

    ``policy.s_max`` is a rate on capacity; the fund's intake is money. They
    are only comparable once the rate is multiplied out, which is the whole
    point of doing it here: EUR 200/t sounds modest and EUR 500m against a
    EUR 2bn fund does not.

    ``assumed`` is what the model hands one plant; ``observed`` is what the
    instrument collected year to date. The ratio is a share of a pot, so it is
    dimensionless and the money column repeats the claim in euros.
    """
    claim = units.absolute(Params().policy.s_max, REFERENCE_MT)
    series = eex.account_revenue("IF", eex.cache_read(eex.CACHE), offline)
    return Gap(
        "Innovation Fund, YTD", claim, series.value, "EUR",
        claim, "the model's support for ONE plant, at s_max = EUR 200/t capacity",
        series)


def volatility_gap(offline: bool = False) -> Gap:
    """The assumed sigma against one year of realised auction volatility.

    Finding 1 makes this the most consequential row in the table: sigma is the
    only parameter that moves the trigger without moving the break-even, so it
    is pure option value. The specification assumes 0.20; the auctions are the
    first evidence in the build about what it actually is.

    No money column. Sigma enters through beta and the option multiple, so its
    effect on money is not a multiplication - it is the whole timing result,
    and quoting a euro figure here would imply an arithmetic that does not
    exist. What it changes is *when*, and the note in T8 says so.
    """
    series = eex.realised_volatility(eex.cache_read(eex.CACHE), offline)
    return Gap("volatility sigma", Params().common.sigma, series.value,
               "1/yr^0.5", None,
               "no money column: sigma moves the trigger, not the break-even",
               series)


def volatility_implies(offline: bool = False) -> tuple[str, float, Outputs]:
    """Which rung of the published sigma ladder the observation lands on.

    Deliberately snapped to a rung rather than run at the observed sigma
    directly. The ladder is the specification's own sensitivity axis, each rung
    defended line by line in Appendix A §3.4, and quoting a crossing year from
    it is quoting the specification back to itself. Re-running the model at an
    off-ladder sigma would be a recalibration, which is the one thing this
    module does not do.

    Returns the rung name, its sigma, and the model outputs at that rung.
    """
    series = eex.realised_volatility(eex.cache_read(eex.CACHE), offline)
    rung = min(SIGMA_REGIMES, key=lambda k: abs(SIGMA_REGIMES[k] - series.value))
    p, sc = published_base()
    return rung, SIGMA_REGIMES[rung], outputs(p, replace(sc, sigma_regime=rung))


def rate_gap(offline: bool = False) -> Gap:
    """The 8% real hurdle rate against the observed real risk-free rate.

    Not a correction: a risk-free rate is not a hurdle rate, and the difference
    is the risk premium rather than an error. Stated because finding 4 shows
    the trigger moves further on ``r`` than on anything else in the model, so
    what ``r`` embeds is worth writing down in the same place as the prices.
    """
    rates = ecb.refresh(offline)
    hicp = eurostat.refresh(offline=True)["hicp"]
    nominal = rates["yield_10y"]
    real = ecb.real_risk_free(nominal.value, hicp.value) * 100.0
    return Gap("discount rate r", 8.0, real, "% / yr real", None,
               "no money column: a rate is not a stock", nominal)


def energy_gap(geo: str = "DE", offline: bool = False) -> Gap:
    """Industrial electricity against industrial gas, per unit of energy.

    Comment 1 asked whether electricity is cheaper than gas. Per kWh it is not,
    anywhere in Europe, and the ratio is the answer. ``assumed`` is the gas
    price and ``observed`` the power price so the ratio reads as "power costs
    this many times gas" without a sign flip.
    """
    cache = eurostat.cache_read(eurostat.CACHE)
    power = eurostat.industrial_power(geo, cache, offline)
    gas = eurostat.industrial_gas(geo, cache, offline)
    return Gap(f"power vs gas, {geo}", gas.value, power.value, "EUR/kWh",
               None, "no money column: this is a price ratio", power)


def all_gaps(offline: bool = False) -> list[Gap]:
    """Every gap, in the order a reader should meet them."""
    out: list[Gap] = []
    for fn in (carbon_gap, volatility_gap, support_gap, rate_gap):
        try:
            out.append(fn(offline))
        except (LookupError, KeyError, ValueError, OSError):
            continue
    with contextlib.suppress(LookupError, KeyError, ValueError, OSError):
        out.append(energy_gap("DE", offline))
    return out


def pot(offline: bool = False) -> list[tuple[str, float, str]]:
    """Who received the auction money this year: (account, EUR, what it is).

    The total first, then the named beneficiaries. Member states and EU funds
    are labelled differently because they are not the same kind of recipient -
    a state's receipts go to its budget under a non-binding spending clause,
    while the Innovation Fund is a competitive instrument that awards against
    applications.
    """
    cache = eex.cache_read(eex.CACHE)
    rows: list[tuple[str, float, str]] = []
    try:
        total = eex.auction_revenue(cache, offline)
        rows.append(("ALL auctions", total.value, "every member state and fund"))
    except LookupError:
        return rows
    for code in REPORTED:
        try:
            series = eex.account_revenue(code, cache, offline)
        except LookupError:
            continue
        kind = ("EU fund, awarded competitively" if code in eex.EU_FUNDS
                else "member state, to the national budget")
        rows.append((code, series.value, kind))
    return rows


def main(offline: bool = False) -> int:
    """Print the gaps, in money, with the date each observation carries."""
    print("The model against the market, today\n" + "=" * 78)
    gaps = all_gaps(offline)
    if not gaps:
        print("  No observation could be reached and none is cached.")
        return 0

    head = (f"  {'quantity':<30}{'assumed':>14}{'observed':>14}"
            f"{'ratio':>8}  {'unit':<16}{'as of':<24}")
    print(head)
    print("  " + "-" * (len(head) - 2))
    for g in gaps:
        tag = "" if g.live else " (cached)"
        print(f"  {g.what:<30}{g.show(g.assumed):>14}{g.show(g.observed):>14}"
              f"{g.ratio:>8.2f}  {g.unit:<16}{g.period + tag:<24}")

    print("\n  What the gaps are worth:")
    for g in gaps:
        if g.money is None:
            print(f"    {g.what:<30}{'-':>14}  {g.money_is}")
        else:
            print(f"    {g.what:<30}{units.eur(g.money):>14}  {g.money_is}")

    try:
        rung, rung_sigma, at_rung = volatility_implies(offline)
        base = outputs(*published_base())
        print("\n  What the volatility row is worth, in years rather than euros:")
        print(f"  one year of auctions puts sigma at "
              f"{next(g.observed for g in gaps if g.what.startswith('volatility')):.2f}, "
              f"nearest the specification's")
        print(f"  '{rung}' rung ({rung_sigma:.2f}), not the 'long_run' base it "
              f"runs on ({Params().common.sigma:.2f}).")
        print(f"  At that rung the trigger is {at_rung.trigger:,.2f} rather than "
              f"{base.trigger:,.2f} EUR/tCO2, and the")
        print(f"  price path crosses it in {at_rung.crossing_year} rather than "
              f"{base.crossing_year} - {at_rung.crossing_year - base.crossing_year} "
              "years of extra waiting.")
        print("  Finding 1: sigma is the only pure threshold lever, so this is the")
        print("  live observation that matters most. The model still runs on 0.20.")
    except (LookupError, KeyError, ValueError, OSError):
        pass

    support = next((g for g in gaps if g.what.startswith("Innovation Fund")), None)
    if support and support.observed:
        share = support.assumed / support.observed
        print(f"\n  Read the support row as a share, not a ratio: "
              f"{units.eur(support.assumed)} for one plant is")
        print(f"  {share:.1%} of everything the Innovation Fund has collected this "
              f"year ({units.eur(support.observed)}).")
        print("  The fund is Europe-wide and every sector competes for it, so a "
              "quarter of")
        print("  it going to a single works is a claim about priority, not just "
              "about size.")

    rows = pot(offline)
    if rows:
        print("\n  Auction revenue this year - real money, already collected:")
        for code, amount, kind in rows:
            print(f"    {code:<14}{units.eur(amount):>12}   {kind}")
        print("\n  NOT earmarked for steel. The ETS Directive's spending clause is")
        print("  a target on member states, not a commitment to any one plant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
