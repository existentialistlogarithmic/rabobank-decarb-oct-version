"""Real observed inputs from Eurostat, with an offline cache.

The model must run with no network, so this fetches once, caches to
``eurostat_cache.json``, and falls back to the cache (or to documented
defaults) whenever the network is unavailable. Nothing here is required for
``run_all.py`` to pass.

What can and cannot be sourced
------------------------------
NPV, the trigger and T* are model **outputs**. No statistical agency publishes
them and none ever will. What official statistics can do is replace *inputs*,
which is what this module does:

* **Deflator** - euro-area HICP. The model's real-versus-nominal correction is
  the single largest unit error in the published version, and it turns on this
  number.
* **Industrial electricity price** - the binding input under the hydrogen
  price, because electrolysis is mostly a way of buying electricity.

Two inputs cannot be sourced from open data and need a market-data terminal:
the EUA price series (which sets the price path, the drift and the volatility)
and commercial hydrogen price assessments.
"""

from __future__ import annotations

import json
import pathlib
import urllib.error
import urllib.request
from dataclasses import dataclass

CACHE = pathlib.Path(__file__).with_name("eurostat_cache.json")
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
TIMEOUT = 25

#: kWh of electricity per kg of hydrogen, system basis. Hydrogen's lower
#: heating value is 33.3 kWh/kg; at ~60% system efficiency that is ~55 kWh/kg.
#: NOT to be confused with the model's m_H2 = 55 kg of hydrogen per tonne of
#: steel - the two 55s are unrelated quantities that happen to share a number.
KWH_PER_KG_H2 = 55.0

#: Steel-producing member states, plus two low-price comparators.
STEEL_GEOS = ("ES", "DE", "NL", "FR", "SE", "AT", "BE", "IT", "PL")


@dataclass(frozen=True)
class Series:
    """One observed series: what it is, when, and where it came from."""

    name: str
    period: str
    value: float
    unit: str
    source: str
    live: bool

    def cite(self) -> str:
        tag = "fetched" if self.live else "cached"
        return f"{self.name}: {self.value:,.4f} {self.unit} ({self.period}, {self.source}, {tag})"


def _get(dataset: str, **params: str) -> dict:
    q = "&".join(f"{k}={v}" for k, v in {"format": "JSON", **params}.items())
    with urllib.request.urlopen(f"{BASE}/{dataset}?{q}", timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def _latest(doc: dict) -> tuple[str, float]:
    """Most recent (period, value) from a Eurostat JSON-stat response."""
    labels = list(doc["dimension"]["time"]["category"]["label"].values())
    vals = doc["value"]
    for i in range(len(labels) - 1, -1, -1):
        if str(i) in vals:
            return labels[i], float(vals[str(i)])
    raise KeyError("no observations in response")


def _cache_read() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}


def _cache_write(d: dict) -> None:
    CACHE.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")


def hicp_inflation(cache: dict, offline: bool = False) -> Series:
    """Euro-area HICP annual rate of change, %. Grounds the deflator."""
    key = "hicp_ea"
    if not offline:
        try:
            doc = _get("prc_hicp_aind", geo="EA", coicop="CP00", unit="RCH_A_AVG",
                       lastTimePeriod="1")
            period, value = _latest(doc)
            cache[key] = {"period": period, "value": value}
            return Series("Euro-area HICP inflation", period, value, "% / yr",
                          "Eurostat prc_hicp_aind", True)
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError, OSError):
            pass
    c = cache.get(key, {"period": "2025", "value": 2.1})
    return Series("Euro-area HICP inflation", c["period"], c["value"], "% / yr",
                  "Eurostat prc_hicp_aind", False)


def industrial_power(geo: str, cache: dict, offline: bool = False) -> Series:
    """Electricity price for a large industrial user, EUR/kWh excluding taxes.

    Band IE (20-70 GWh a year) is the closest published band to a steel plant's
    draw; taxes and levies are excluded because large industrial users in most
    member states are substantially exempted from them.
    """
    key = f"power_{geo}"
    if not offline:
        try:
            doc = _get("nrg_pc_205", geo=geo, currency="EUR",
                       nrg_cons="MWH20000-69999", tax="X_TAX", unit="KWH",
                       lastTimePeriod="1")
            period, value = _latest(doc)
            cache[key] = {"period": period, "value": value}
            return Series(f"{geo} industrial electricity", period, value,
                          "EUR/kWh", "Eurostat nrg_pc_205 band IE, excl. taxes", True)
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError, OSError):
            pass
    c = cache.get(key)
    if c is None:
        raise LookupError(f"no cached electricity price for {geo}; run online once")
    return Series(f"{geo} industrial electricity", c["period"], c["value"],
                  "EUR/kWh", "Eurostat nrg_pc_205 band IE, excl. taxes", False)


def hydrogen_power_floor(power_eur_per_kwh: float) -> float:
    """EUR/kg of hydrogen from electricity alone. A FLOOR, not a price.

    Excludes electrolyser capital cost, stack replacement, compression,
    storage, transport, and every other cost of delivering hydrogen to a
    furnace. Real delivered hydrogen is strictly above this number, which is
    what makes it useful: it bounds the input from below using official
    statistics rather than a forecast.
    """
    return power_eur_per_kwh * KWH_PER_KG_H2


def refresh(offline: bool = False) -> dict[str, Series]:
    """Fetch (or load) every series. Never raises on a network failure."""
    cache = _cache_read()
    out: dict[str, Series] = {"hicp": hicp_inflation(cache, offline)}
    for geo in STEEL_GEOS:
        try:
            out[f"power_{geo}"] = industrial_power(geo, cache, offline)
        except LookupError:
            continue
    if not offline:
        _cache_write(cache)
    return out


def main() -> int:
    """Print the observed inputs and the hydrogen floor they imply."""
    s = refresh()
    print("Observed inputs\n" + "=" * 66)
    print(" ", s["hicp"].cite())
    print(f"    model deflator is 2.0%/yr - "
          f"{'consistent' if abs(s['hicp'].value - 2.0) < 1.0 else 'REVIEW'}\n")

    print("Hydrogen cost floor from electricity alone\n" + "=" * 66)
    print(f"  {KWH_PER_KG_H2:.0f} kWh/kg, system basis. Excludes electrolyser capex,")
    print("  compression, storage and transport - delivered cost is strictly above.\n")
    print(f"  {'':4}{'EUR/kWh':>9}{'floor EUR/kg':>14}{'vs base 2.60':>14}")
    rows = [(g, s[f"power_{g}"]) for g in STEEL_GEOS if f"power_{g}" in s]
    for g, ser in sorted(rows, key=lambda r: r[1].value):
        fl = hydrogen_power_floor(ser.value)
        print(f"  {g:<4}{ser.value:>9.4f}{fl:>14.2f}{fl / 2.60:>13.1f}x")
    if rows:
        lo = min(hydrogen_power_floor(r[1].value) for r in rows)
        print(f"\n  Cheapest floor anywhere: EUR {lo:.2f}/kg — "
              f"{lo / 2.60:.1f}x the base-case assumption of EUR 2.60/kg.")
        print("  The base case is below the electricity bill alone, everywhere.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
