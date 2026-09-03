"""Observed interest rates from the ECB Data Portal, with an offline cache.

The model discounts at ``r = 0.08`` real, described in the parameters as a
"WACC proxy". That is a defensible number, but until now nothing in the build
said what it is a proxy *for*, and finding 4 shows the whole trigger rests on
it: across the sourced 6-10% band the break-even moves +304% and the option
multiple -68%.

So this module fetches the two rates that decompose it - the risk-free term
structure and the policy rate - and :mod:`grounding` subtracts observed
inflation to state the risk premium the 8% actually embeds. It does not change
``r``. An observed risk-free rate is not a corporate hurdle rate, and pretending
otherwise would be the same error the hydrogen price makes.

Same offline rule as :mod:`eurostat`: fetch, cache, never raise on a network
failure.
"""

from __future__ import annotations

import pathlib
from typing import Final

from observed import Series, cache_read, cache_write, fetch_or_cache, get_json

CACHE = pathlib.Path(__file__).with_name("ecb_cache.json")
BASE = "https://data-api.ecb.europa.eu/service/data"

#: Daily spot rate, 10-year maturity, AAA-rated euro-area central government
#: bonds. The euro-area risk-free rate at the model's horizon scale.
YIELD_10Y: Final[str] = "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"

#: Main refinancing operations, fixed rate. The policy anchor under it.
POLICY_RATE: Final[str] = "FM/B.U2.EUR.4F.KR.MRR_FR.LEV"


def _latest(key: str) -> tuple[str, float]:
    """Most recent (period, value) from an ECB SDMX-JSON response."""
    doc = get_json(f"{BASE}/{key}?format=jsondata&lastNObservations=1")
    series = doc["dataSets"][0]["series"]
    observations = next(iter(series.values()))["observations"]
    periods = doc["structure"]["dimensions"]["observation"][0]["values"]
    index, point = next(iter(observations.items()))
    return periods[int(index)]["id"], float(point[0])


def long_term_rate(cache: dict, offline: bool = False) -> Series:
    """Euro-area 10-year AAA government bond spot rate, % per year, nominal."""
    return fetch_or_cache(
        "yield_10y", cache, offline,
        lambda: _latest(YIELD_10Y),
        "Euro-area 10Y AAA government bond yield", "% / yr nominal",
        "ECB Data Portal, yield curve",
    )


def policy_rate(cache: dict, offline: bool = False) -> Series:
    """ECB main refinancing operations rate, % per year."""
    return fetch_or_cache(
        "policy_rate", cache, offline,
        lambda: _latest(POLICY_RATE),
        "ECB main refinancing rate", "% / yr",
        "ECB Data Portal, official interest rates",
    )


def real_risk_free(nominal_pct: float, inflation_pct: float) -> float:
    """Fisher-deflated real risk-free rate, as a fraction per year.

    Exact Fisher, not the linear approximation: at these levels the difference
    is small, but the model's own guard is that ``r - mu`` must stay positive,
    and an approximation that flatters a rate is exactly what such a guard is
    there to catch.
    """
    return (1.0 + nominal_pct / 100.0) / (1.0 + inflation_pct / 100.0) - 1.0


def refresh(offline: bool = False) -> dict[str, Series]:
    """Fetch (or load) every series. Never raises on a network failure."""
    cache = cache_read(CACHE)
    out: dict[str, Series] = {}
    for name, fn in (("yield_10y", long_term_rate), ("policy_rate", policy_rate)):
        try:
            out[name] = fn(cache, offline)
        except LookupError:
            continue
    if not offline:
        cache_write(CACHE, cache)
    return out


def main() -> int:
    """Print the observed rates and the real risk-free rate they imply."""
    import eurostat

    rates = refresh()
    print("Observed interest rates\n" + "=" * 72)
    for series in rates.values():
        print(" ", series.cite())

    if "yield_10y" in rates:
        hicp = eurostat.refresh(offline=True)["hicp"]
        real = real_risk_free(rates["yield_10y"].value, hicp.value)
        print(f"\n  Real risk-free rate (Fisher, deflated by HICP {hicp.value:.1f}%):"
              f" {real * 100:.2f}%/yr")
        print(f"  The model discounts at 8.00% real, implying a risk premium of"
              f" {8.0 - real * 100:.2f}pp.")
        print("  That is a statement about the assumption, not a correction to it:")
        print("  a risk-free rate is not a hurdle rate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
