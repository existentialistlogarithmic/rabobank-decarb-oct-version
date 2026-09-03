"""Observed data: the cache, the floors it implies, and the model's answer to it.

Every test here runs offline, from the committed caches. That is the point:
a model whose outputs depend on whether a web service answered this morning is
not reproducible, and these tests fail if that ever stops being true.
"""

from __future__ import annotations

import pytest

from analysis import grounding
from data import ecb, eurostat, observed
from reporting import sources
from timing_model.params import Params, ScenarioParams

BASE_P_H2 = ScenarioParams().p_H2


@pytest.fixture(scope="module")
def series() -> dict[str, observed.Series]:
    return eurostat.refresh(offline=True)


@pytest.fixture(scope="module")
def rates() -> dict[str, observed.Series]:
    return ecb.refresh(offline=True)


def test_the_cache_covers_every_steel_state(series: dict) -> None:
    """A missing country would silently narrow the floor to the states we kept."""
    for geo in eurostat.STEEL_GEOS:
        assert f"power_{geo}" in series, geo
        assert f"gas_{geo}" in series, geo


def test_offline_series_say_they_are_cached(series: dict) -> None:
    """The citation has to record how the number arrived, not just who published it."""
    assert all(not s.live for s in series.values())
    assert all("cached" in s.cite() for s in series.values())


def test_offline_never_touches_the_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """The offline rule, enforced rather than trusted."""
    def explode(url: str) -> dict:
        raise AssertionError(f"offline run attempted a fetch: {url}")

    # Each provider binds get_json into its own namespace at import, so
    # patching observed alone would leave the real one reachable and this
    # test would pass without proving anything.
    for module in (observed, eurostat, ecb):
        monkeypatch.setattr(module, "get_json", explode)
    assert eurostat.refresh(offline=True)
    assert ecb.refresh(offline=True)
    assert grounding.groundings(offline=True)


def test_a_network_failure_falls_back_instead_of_raising() -> None:
    """A dead endpoint must degrade to the cache, not take the run down."""
    def fail() -> tuple[str, float]:
        raise TimeoutError("pretend the service is down")

    cache = {"k": {"period": "2025", "value": 1.5}}
    got = observed.fetch_or_cache("k", cache, False, fail, "x", "u", "src")
    assert got.value == 1.5 and got.live is False


def test_a_series_never_seen_online_raises_rather_than_inventing(
) -> None:
    """No cache, no default, no network: say so. Do not guess a number."""
    with pytest.raises(LookupError):
        observed.fetch_or_cache("unseen", {}, True, lambda: ("", 0.0), "x", "u", "s")


@pytest.mark.parametrize("geo", eurostat.STEEL_GEOS)
def test_green_hydrogen_costs_more_than_the_base_case_everywhere(
    geo: str, series: dict
) -> None:
    """Electricity alone exceeds EUR 2.60/kg in every state Eurostat covers."""
    floor = eurostat.hydrogen_power_floor(series[f"power_{geo}"].value)
    assert floor > BASE_P_H2, f"{geo}: green floor {floor:.2f}"


def test_the_base_case_is_reachable_only_as_grey_hydrogen() -> None:
    """The finding the gas series buys: EUR 2.60/kg is a fossil price.

    Below every green floor, and inside the range of grey floors - gas at
    best-in-class reforming plus the ETS cost of the CO2 it emits.
    """
    floors = grounding.hydrogen_floors(offline=True)
    green = [g for g, _ in floors.values()]
    grey = [y for _, y in floors.values()]
    assert min(green) > BASE_P_H2, min(green)
    assert min(grey) < BASE_P_H2, min(grey)
    assert max(grey) < min(green), "the two floors must not overlap"


def test_grey_hydrogen_contradicts_the_clean_route_intensity() -> None:
    """The price and the emission intensity cannot both be right."""
    p = Params()
    implied = grounding.grey_hydrogen_intensity()
    assert implied == pytest.approx(p.sector.m_H2 * 9.0 / 1000.0)
    assert implied > 4 * p.common.eps_cln, (
        f"grey hydrogen implies {implied:.2f} tCO2/t against eps_cln "
        f"{p.common.eps_cln}"
    )


def test_the_conservative_emission_factor_understates_the_contradiction() -> None:
    """9 kgCO2/kg is the low end; the IEA's 10-12 would make the gap wider.

    Pinned so nobody 'improves' the factor upward and reports a stronger
    finding than the conservative choice supports.
    """
    assert eurostat.KG_CO2_PER_KG_H2_SMR == 9.0


def test_capacity_utilisation_is_below_the_model_load_factor(series: dict) -> None:
    """u = 0.85 is at the optimistic end of what European industry runs at."""
    observed_u = series["caputil"].value / 100.0
    assert 0.5 < observed_u < 1.0, observed_u
    assert ScenarioParams().u > observed_u


def test_capital_goods_and_steel_prices_moved_in_opposite_directions(
    series: dict,
) -> None:
    """Why the currency year matters differently for capacity and for product."""
    capex = series["ppi_capex"].value / series["ppi_capex_base"].value
    steel = series["ppi_steel"].value / series["ppi_steel_base"].value
    assert capex > 1.0 > steel, (capex, steel)


def test_rebasing_restates_a_currency_year(series: dict) -> None:
    base, now = series["ppi_capex_base"].value, series["ppi_capex"].value
    assert grounding.rebase(900.0, base, now) == pytest.approx(900.0 * now / base)
    assert grounding.rebase(900.0, base, base) == 900.0


def test_the_real_risk_free_rate_is_below_the_hurdle_rate(
    series: dict, rates: dict
) -> None:
    """Otherwise the 8% would embed a negative risk premium."""
    real = ecb.real_risk_free(rates["yield_10y"].value, series["hicp"].value)
    assert 0.0 < real < Params().common.r


def test_fisher_deflation_is_exact_not_linear() -> None:
    """At r - mu guard tolerances the approximation is not good enough."""
    assert ecb.real_risk_free(5.0, 2.0) == pytest.approx(1.05 / 1.02 - 1.0)
    assert ecb.real_risk_free(5.0, 2.0) < 0.03


def test_adopting_the_observed_rate_would_trip_the_models_own_guard(
    series: dict, rates: dict
) -> None:
    """Why grounding reports rather than overwrites, in one assertion.

    The observed real risk-free rate is below the model's drift, so swapping it
    in for `r` makes `r - mu` negative and the feasibility guard raises. A
    risk-free rate is not a hurdle rate, and the model already knows it.
    """
    from timing_model.params import ModelError
    from timing_model.validate import run_guards

    real = ecb.real_risk_free(rates["yield_10y"].value, series["hicp"].value)
    p, sc = Params(), ScenarioParams()
    assert real < p.common.mu, "the guard argument below depends on this ordering"
    with pytest.raises(ModelError):
        run_guards(p.with_common(r=real), sc)
    assert p.common.r - p.common.mu >= 0.005, "the shipped rate clears the guard"


def test_every_grounding_names_a_registered_parameter() -> None:
    """The grounding table and the provenance register share one vocabulary."""
    registered = {c.param for c in sources.REGISTER}
    for row in grounding.groundings(offline=True):
        assert row.param in registered, f"{row.param} is grounded but not cited"


def test_every_grounding_carries_a_known_verdict() -> None:
    for row in grounding.groundings(offline=True):
        assert row.verdict in grounding.VERDICTS, row.verdict
        assert row.note.strip(), f"{row.param} has no note"


def test_groundings_lead_with_the_worst_news() -> None:
    """A table that buries the contradiction under the reassurance is worse than none."""
    rows = grounding.groundings(offline=True)
    keys = [r.sort_key() for r in rows]
    assert keys == sorted(keys)
    assert rows[0].verdict == "contradiction"


def test_the_grounding_layer_changes_no_model_input() -> None:
    """Reporting a disagreement is not the same as resolving it."""
    before = (Params(), ScenarioParams())
    grounding.groundings(offline=True)
    assert (Params(), ScenarioParams()) == before
