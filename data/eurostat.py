"""Real observed inputs from Eurostat, with an offline cache.

Fetches once, caches to ``eurostat_cache.json``, and falls back to the cache
whenever the network is unavailable.  Nothing here is required for
``run_all.py`` to pass.

What can and cannot be sourced
------------------------------
NPV, the trigger and T* are model **outputs**. No statistical agency publishes
them and none ever will. What official statistics can do is replace *inputs*,
which is what this module does:

* **Deflator** - euro-area HICP. The model's real-versus-nominal correction is
  the single largest unit error in the published version, and it turns on this
  number.
* **Industrial electricity price** - the binding input under a green hydrogen
  price, because electrolysis is mostly a way of buying electricity.
* **Industrial gas price** - the binding input under a *grey* hydrogen price,
  which is the cheaper floor and therefore the one that decides whether
  EUR 2.60/kg is defensible at all.
* **Producer prices, capital goods and basic metals** - what a EUR 2022 figure
  is worth today, which is not the same question as consumer inflation, and is
  a different question again for a plant than for the steel it makes. The two
  indices have moved in opposite directions since 2022.
* **Capacity utilisation** - what European industry actually runs at, against
  the model's load factor.

One input still cannot be sourced from open data and needs a market-data
terminal: commercial hydrogen price assessments.

The EUA price used to be on that list, on the assumption that a carbon price
means a futures curve behind a paywall. It does not: EEX publishes every
primary-market auction the EU ETS holds, with the clearing price and the money
each member state received, the same day it clears. :mod:`eex` reads it, and
the grey-hydrogen floor below is now charged at the observed price rather than
at the specification's path anchor.
"""

from __future__ import annotations

import pathlib
from typing import Final

from data.observed import Series, cache_read, cache_write, fetch_or_cache, get_json

CACHE = pathlib.Path(__file__).with_name("eurostat_cache.json")
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

#: kWh of electricity per kg of hydrogen, system basis. Hydrogen's lower
#: heating value is 33.3 kWh/kg; at ~60% system efficiency that is ~55 kWh/kg.
#: NOT to be confused with the model's m_H2 = 55 kg of hydrogen per tonne of
#: steel - the two 55s are unrelated quantities that happen to share a number.
KWH_PER_KG_H2: Final[float] = 55.0

#: kWh of natural gas per kg of hydrogen from steam methane reforming: the
#: 33.3 kWh/kg lower heating value at 81% process efficiency, the top of the
#: 79-81% band reported for large-scale SMR. Deliberately the *favourable* end,
#: because this builds a floor and a floor takes the best case available.
KWH_GAS_PER_KG_H2: Final[float] = 41.1

#: kg CO2 per kg of hydrogen from unabated SMR - process emissions only. The
#: IEA puts unabated hydrogen at 10-12 kgCO2e/kg once upstream methane is
#: counted, so 9 is the conservative end of the range on purpose. Charged at
#: the ETS price, this is what makes grey hydrogen a floor under a *European*
#: hydrogen price rather than a global one.
KG_CO2_PER_KG_H2_SMR: Final[float] = 9.0

#: Steel-producing member states, plus two low-price comparators.
STEEL_GEOS: Final[tuple[str, ...]] = ("ES", "DE", "NL", "FR", "SE", "AT", "BE", "IT", "PL")

#: Consumption band IE (20-70 GWh/yr): the closest published electricity band
#: to a steel plant's draw.
POWER_BAND: Final[str] = "MWH20000-69999"

#: Consumption band I5 (1 000 000-3 999 999 GJ/yr): the closest published gas
#: band to an integrated works.
GAS_BAND: Final[str] = "GJ1000000-3999999"

#: The currency year every monetary parameter in the model is tagged with.
#: Producer prices are read at this year and at the latest one, so a EUR 2022
#: figure can be restated in today's money instead of being assumed current.
CURRENCY_BASE_YEAR: Final[str] = "2022"

#: Dataset labels carried into every citation, kept as constants so the
#: provenance register in sources.py can pin them.
CAPUTIL_SOURCE: Final[str] = "Eurostat ei_bsin_q_r2 (business survey)"
PPI_SOURCE: Final[str] = "Eurostat sts_inppd_a"


def _query(dataset: str, **params: str) -> dict:
    q = "&".join(f"{k}={v}" for k, v in {"format": "JSON", **params}.items())
    return get_json(f"{BASE}/{dataset}?{q}")


def _latest(doc: dict) -> tuple[str, float]:
    """Most recent (period, value) from a Eurostat JSON-stat response."""
    labels = list(doc["dimension"]["time"]["category"]["label"].values())
    values = doc["value"]
    for i in range(len(labels) - 1, -1, -1):
        if str(i) in values:
            return labels[i], float(values[str(i)])
    raise KeyError("no observations in response")


def hicp_inflation(cache: dict, offline: bool = False) -> Series:
    """Euro-area HICP annual rate of change, %. Grounds the deflator."""
    return fetch_or_cache(
        "hicp_ea", cache, offline,
        lambda: _latest(_query("prc_hicp_aind", geo="EA", coicop="CP00",
                               unit="RCH_A_AVG", lastTimePeriod="1")),
        "Euro-area HICP inflation", "% / yr", "Eurostat prc_hicp_aind",
        default={"period": "2025", "value": 2.1},
    )


def industrial_power(geo: str, cache: dict, offline: bool = False) -> Series:
    """Electricity price for a large industrial user, EUR/kWh excluding taxes.

    Band IE (20-70 GWh a year) is the closest published band to a steel plant's
    draw; taxes and levies are excluded because large industrial users in most
    member states are substantially exempted from them.
    """
    return fetch_or_cache(
        f"power_{geo}", cache, offline,
        lambda: _latest(_query("nrg_pc_205", geo=geo, currency="EUR",
                               nrg_cons=POWER_BAND, tax="X_TAX", unit="KWH",
                               lastTimePeriod="1")),
        f"{geo} industrial electricity", "EUR/kWh",
        "Eurostat nrg_pc_205 band IE, excl. taxes",
    )


def industrial_gas(geo: str, cache: dict, offline: bool = False) -> Series:
    """Natural gas price for a very large industrial user, EUR/kWh excl. taxes.

    Band I5 (1 000 000-3 999 999 GJ a year). Gas is the reductant the incumbent
    route is being compared against and the feedstock of the cheapest hydrogen
    anyone can actually buy, so it bounds ``p_H2`` from below harder than
    electricity does.
    """
    return fetch_or_cache(
        f"gas_{geo}", cache, offline,
        lambda: _latest(_query("nrg_pc_203", geo=geo, currency="EUR",
                               nrg_cons=GAS_BAND, tax="X_TAX", unit="KWH",
                               lastTimePeriod="1")),
        f"{geo} industrial gas", "EUR/kWh",
        "Eurostat nrg_pc_203 band I5, excl. taxes",
    )


def _ppi(nace: str, label: str, cache: dict, offline: bool, year: str | None) -> Series:
    """Producer price index, 2021 = 100, for one NACE aggregate.

    ``year`` pins a single year (used to read the model's currency-year base);
    ``None`` takes the latest published year.
    """
    window = {"time": year} if year else {"lastTimePeriod": "1"}
    return fetch_or_cache(
        f"ppi_{nace.lower()}" + (f"_{year}" if year else ""), cache, offline,
        lambda: _latest(_query("sts_inppd_a", geo="EA20", nace_r2=nace,
                               indic_bt="PRC_PRR_DOM", s_adj="NSA", unit="I21",
                               **window)),
        f"Euro-area producer prices, {label}", "index 2021=100",
        f"{PPI_SOURCE} {nace}",
    )


def basic_metals_ppi(cache: dict, offline: bool = False,
                     year: str | None = None) -> Series:
    """Output prices of the basic-metals sector (NACE C24).

    This is what a tonne of steel *sells* for, so it bears on the benefit side
    and on the currency year of anything quoted per tonne of product. It is the
    wrong index for capital cost - see :func:`capital_goods_ppi`, and note the
    two move in opposite directions.
    """
    return _ppi("C24", "basic metals", cache, offline, year)


def capital_goods_ppi(cache: dict, offline: bool = False,
                      year: str | None = None) -> Series:
    """Output prices of capital goods (MIG_CAG): what building a plant costs.

    HICP says what a euro buys in a shop. This says what a euro buys in plant
    and equipment, which is the relevant question for a ``EUR 2022`` capex
    figure being quoted in 2026.
    """
    return _ppi("MIG_CAG", "capital goods", cache, offline, year)


def capacity_utilisation(cache: dict, offline: bool = False) -> Series:
    """Current level of capacity utilisation in industry, %, euro area.

    From the harmonised business survey. It is all-industry, not steel, so it
    is a reference point rather than a measurement of blast-furnace load - but
    it is the only regularly published European utilisation series there is.
    """
    return fetch_or_cache(
        "caputil_ea", cache, offline,
        lambda: _latest(_query("ei_bsin_q_r2", geo="EA20", indic="BS-ICU-PC",
                               s_adj="SA", lastTimePeriod="8")),
        "Euro-area capacity utilisation, industry", "%",
        CAPUTIL_SOURCE,
    )


def hydrogen_power_floor(power_eur_per_kwh: float) -> float:
    """EUR/kg of GREEN hydrogen from electricity alone. A FLOOR, not a price.

    Excludes electrolyser capital cost, stack replacement, compression,
    storage, transport, and every other cost of delivering hydrogen to a
    furnace. Real delivered hydrogen is strictly above this number, which is
    what makes it useful: it bounds the input from below using official
    statistics rather than a forecast.
    """
    return power_eur_per_kwh * KWH_PER_KG_H2


def hydrogen_gas_floor(gas_eur_per_kwh: float, eua_eur_per_t: float = 0.0) -> float:
    """EUR/kg of GREY hydrogen from gas, optionally carrying its ETS cost.

    The same discipline as :func:`hydrogen_power_floor`: gas at best-in-class
    reforming efficiency and nothing else - no reformer capex, no compression,
    no transport. With ``eua_eur_per_t`` supplied it also charges the 9 kg of
    CO2 that reforming a kilogram of hydrogen emits, which is the difference
    between a global floor and a European one.

    This is the *lower* of the two floors, so it is the one that decides
    whether a quoted hydrogen price is defensible.
    """
    return gas_eur_per_kwh * KWH_GAS_PER_KG_H2 + eua_eur_per_t * KG_CO2_PER_KG_H2_SMR / 1000.0


def refresh(offline: bool = False) -> dict[str, Series]:
    """Fetch (or load) every series. Never raises on a network failure."""
    cache = cache_read(CACHE)
    out: dict[str, Series] = {"hicp": hicp_inflation(cache, offline)}
    for name, fn in (("caputil", capacity_utilisation),):
        try:
            out[name] = fn(cache, offline)
        except LookupError:
            continue
    for name, fn in (("ppi_steel", basic_metals_ppi), ("ppi_capex", capital_goods_ppi)):
        for suffix, year in (("", None), ("_base", CURRENCY_BASE_YEAR)):
            try:
                out[name + suffix] = fn(cache, offline, year)
            except LookupError:
                continue
    for geo in STEEL_GEOS:
        for prefix, fn in (("power", industrial_power), ("gas", industrial_gas)):
            try:
                out[f"{prefix}_{geo}"] = fn(geo, cache, offline)
            except LookupError:
                continue
    if not offline:
        cache_write(CACHE, cache)
    return out


def observed_carbon_price(offline: bool = False) -> tuple[float, str]:
    """The EUA price to charge grey hydrogen's emissions at, and where it came from.

    Read from the auction record and from nothing else. The floor this feeds is
    the argument that EUR 2.60/kg can only be unabated fossil hydrogen, and
    that argument is stronger the more of it rests on an observation: charging
    the emissions at an assumed price would make the conclusion partly an
    artefact of the assumption.

    Deliberately does NOT fall back to the specification's price path. This
    module sits in ``data``, which answers *what is true* and may not read what
    the model assumes - see ``test_observed_data_does_not_depend_on_the_model``.
    With no observation reachable and none cached it returns zero and says so,
    which understates the grey floor rather than inventing a carbon price; the
    floor is still a floor, just a lower one, and the caption says which.
    """
    from data import eex

    try:
        series = eex.price_mean(eex.cache_read(eex.CACHE), offline)
    except (LookupError, ValueError, OSError):
        return 0.0, "no auction observation reachable; the ETS bill is omitted"
    tag = "fetched" if series.live else "cached"
    return series.value, f"observed EUA auction mean, {series.period}, {tag}"


def main(offline: bool = False) -> int:
    """Print the observed inputs and the two hydrogen floors they imply."""
    s = refresh(offline)
    print("Observed inputs\n" + "=" * 72)
    for key in ("hicp", "caputil", "ppi_steel", "ppi_steel_base",
                "ppi_capex", "ppi_capex_base"):
        if key in s:
            print(" ", s[key].cite())
    print()

    carbon, carbon_where = observed_carbon_price(offline)

    print("Hydrogen cost floors from energy alone\n" + "=" * 72)
    print(f"  Green: {KWH_PER_KG_H2:.0f} kWh of electricity per kg, system basis.")
    print(f"  Grey:  {KWH_GAS_PER_KG_H2:.1f} kWh of gas per kg at 81% reforming")
    print(f"         efficiency, plus {KG_CO2_PER_KG_H2_SMR:.0f} kg CO2 at "
          f"EUR {carbon:.2f}/t")
    print(f"         ({carbon_where}).")
    print("  Both exclude every capital and delivery cost, so a real price is")
    print("  strictly above whichever floor applies.\n")

    header = f"  {'':4}{'green EUR/kg':>14}{'grey EUR/kg':>13}{'lower floor':>13}{'vs 2.60':>10}"
    print(header)
    rows = []
    for geo in STEEL_GEOS:
        power, gas = s.get(f"power_{geo}"), s.get(f"gas_{geo}")
        if power is None or gas is None:
            continue
        green = hydrogen_power_floor(power.value)
        grey = hydrogen_gas_floor(gas.value, carbon)
        rows.append((geo, green, grey, min(green, grey)))
    for geo, green, grey, floor in sorted(rows, key=lambda r: r[3]):
        print(f"  {geo:<4}{green:>14.2f}{grey:>13.2f}{floor:>13.2f}{floor / 2.60:>9.1f}x")

    if rows:
        green_lo = min(r[1] for r in rows)
        grey_lo, grey_hi = min(r[2] for r in rows), max(r[2] for r in rows)
        print(f"\n  Green floors run EUR {green_lo:.2f}-{max(r[1] for r in rows):.2f}/kg: "
              f"the cheapest is {green_lo / 2.60:.1f}x the base case, so EUR 2.60/kg")
        print("  is not a green hydrogen price anywhere in Europe.")
        print(f"\n  Grey floors run EUR {grey_lo:.2f}-{grey_hi:.2f}/kg, i.e. EUR 2.60/kg is")
        print("  approximately the cost of UNABATED FOSSIL hydrogen carrying its ETS")
        print("  bill. That is the only way the base-case price is reachable - and it")
        print(f"  emits {KG_CO2_PER_KG_H2_SMR:.0f} kg CO2 per kg of hydrogen, which at "
              f"55 kg H2 per tonne of")
        print(f"  steel is {KG_CO2_PER_KG_H2_SMR * 55 / 1000:.2f} tCO2/t - five times the "
              f"0.1 tCO2/t the model credits")
        print("  the clean route with. Either the price is wrong or the intensity is.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
