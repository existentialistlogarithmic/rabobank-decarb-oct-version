"""The sourcing frontier, and the guarantee that the explorer page shows the model.

Two jobs. First, pin the findings: they are the point of the module and the
kind of result that quietly inverts when someone edits a constant. Second, make
it impossible for ``explorer.html`` to disagree with ``timing_model`` - the page
embeds precomputed numbers, and a page that drifts from its model is worse than
no page.
"""

from __future__ import annotations

import pytest

from analysis import sourcing
from data import eurostat
from reporting import explorer
from timing_model.params import Params, ScenarioParams

GEOS = eurostat.STEEL_GEOS


@pytest.fixture(scope="module")
def series() -> dict:
    return eurostat.refresh(offline=True)


# ---------------------------------------------------------------- the frontier

@pytest.mark.parametrize("geo", GEOS)
def test_the_endpoints_are_the_observed_energy_costs(geo: str, series: dict) -> None:
    green, grey = sourcing.endpoints(geo, series)
    assert grey == pytest.approx(series[f"gas_{geo}"].value * eurostat.KWH_GAS_PER_KG_H2)
    assert green == pytest.approx(series[f"power_{geo}"].value * eurostat.KWH_PER_KG_H2)
    assert grey < green, "grey is the cheaper endpoint in every observed state"


@pytest.mark.parametrize("geo", GEOS)
def test_theta_interpolates_price_and_intensity_together(geo: str, series: dict) -> None:
    """One parameter, two consequences - that is the whole claim."""
    green, grey = sourcing.endpoints(geo, series)
    lo, hi = sourcing.point(geo, 0.0, series), sourcing.point(geo, 1.0, series)
    assert lo.p_h2 == pytest.approx(grey)
    assert hi.p_h2 == pytest.approx(green)
    assert hi.eps_cln == pytest.approx(Params().common.eps_cln)
    assert lo.eps_cln == pytest.approx(
        Params().common.eps_cln + sourcing.grey_tonnes_per_tonne())
    mid = sourcing.point(geo, 0.5, series)
    assert mid.p_h2 == pytest.approx((green + grey) / 2)
    assert mid.eps_cln == pytest.approx((lo.eps_cln + hi.eps_cln) / 2)


@pytest.mark.parametrize("geo", GEOS)
def test_value_falls_as_hydrogen_gets_greener(geo: str, series: dict) -> None:
    """FINDING: at the model's own carbon path, fossil hydrogen wins on NPV.

    Monotone, in every member state. If this ever stops holding the headline
    changes, so it is pinned rather than described.
    """
    npvs = [pt.npv0 for pt in sourcing.frontier(geo, series=series)]
    assert npvs == sorted(npvs, reverse=True), npvs


@pytest.mark.parametrize("geo", GEOS)
def test_green_never_wins_at_the_central_carbon_path(geo: str, series: dict) -> None:
    mult = sourcing.crossover_multiple(geo, series)
    assert mult is not None, f"{geo}: green never overtakes at any credible price"
    assert mult > 1.0, f"{geo}: green already wins at the central path"


def test_the_crossover_ordering_follows_the_price_SPREAD_not_the_ratio(
    series: dict,
) -> None:
    """The ranking is observed data, and the mechanism is a difference.

    Switching to green costs ``m_H2 * (green - grey)`` per tonne of steel per
    year and buys back ``delta_b * p`` of carbon. Both sides are differences, so
    the crossover follows the absolute EUR/kg spread. The power-to-gas *ratio*
    is the intuitive quantity and it gives a different, wrong ordering - which
    is asserted too, because "obvious" is how the wrong one gets published.
    """
    rows = []
    for geo in GEOS:
        green, grey = sourcing.endpoints(geo, series)
        mult = sourcing.crossover_multiple(geo, series)
        rows.append({"geo": geo, "spread": green - grey,
                     "ratio": green / grey, "mult": mult})
    by_crossover = [r["geo"] for r in sorted(rows, key=lambda r: r["mult"])]
    by_spread = [r["geo"] for r in sorted(rows, key=lambda r: r["spread"])]
    by_ratio = [r["geo"] for r in sorted(rows, key=lambda r: r["ratio"])]
    assert by_spread == by_crossover, (
        "the spread no longer explains the ordering; re-derive the mechanism "
        f"before quoting it. spread={by_spread} crossover={by_crossover}")
    assert by_ratio != by_crossover, (
        "the ratio now matches too, so the distinction this test documents no "
        "longer bites; check whether the prose should still draw it")


def test_sweden_is_the_cheapest_place_to_go_green(series: dict) -> None:
    best = min(GEOS, key=lambda g: sourcing.crossover_multiple(g, series) or 1e9)
    assert best == "SE"


@pytest.mark.parametrize("geo", GEOS)
def test_sourcing_moves_the_commitment_year(geo: str, series: dict) -> None:
    """FINDING: hydrogen sourcing is a timing lever, not only a cost one."""
    lo = sourcing.point(geo, 0.0, series)
    hi = sourcing.point(geo, 1.0, series)
    horizon = Params().common.horizon_end
    late = horizon + 2 if hi.t_star is None else hi.t_star
    assert lo.t_star is not None
    assert late > lo.t_star, f"{geo}: T* did not move ({lo.t_star} -> {hi.t_star})"


# ------------------------------------------------------- what the gap is worth

@pytest.mark.parametrize("geo", GEOS)
def test_the_published_pair_is_off_the_frontier(geo: str, series: dict) -> None:
    """FINDING: EUR 2.60/kg with eps_cln 0.1 is not a point anyone can occupy.

    At the model's own price the consistent intensity is far above 0.1, and the
    NPV difference is what the independent-inputs assumption is worth.
    """
    model, consistent, theta = sourcing.feasibility_gap(geo, series)
    assert theta is not None and 0.0 < theta < 1.0
    assert consistent < model
    share = (model - consistent) / model
    assert 0.15 < share < 0.45, f"{geo}: gap {share:.1%} outside the reported band"


def test_a_price_outside_the_observed_endpoints_has_no_green_share(series: dict) -> None:
    assert sourcing.theta_at_price("DE", 0.10, series) is None
    assert sourcing.theta_at_price("DE", 99.0, series) is None


@pytest.mark.parametrize("geo", GEOS)
def test_where_the_carbon_is_charged_changes_the_answer(geo: str, series: dict) -> None:
    """A cost frozen inside a constant p_H2 is worth more than one that escalates."""
    merchant, onsite = sourcing.framing_gap(geo, series)
    assert merchant > onsite
    assert 0.05 < (merchant - onsite) / merchant < 0.30


def test_the_frontier_changes_no_registered_default(series: dict) -> None:
    before = (Params(), ScenarioParams())
    sourcing.frontier("DE", series=series)
    assert (Params(), ScenarioParams()) == before


# ------------------------------------------------------------ the page itself

@pytest.fixture(scope="module")
def small_payload() -> dict:
    """A reduced grid: same code path, few enough runs to check every point."""
    import unittest.mock as mock

    with mock.patch.object(sourcing, "THETA_STEPS", 3), \
         mock.patch.object(sourcing, "CARBON_MULTIPLES", (1.0, 2.0)):
        return explorer.build_payload()


def test_every_embedded_point_reproduces_from_the_model(small_payload: dict) -> None:
    """The guarantee: the page cannot drift from timing_model.

    Each embedded cell is recomputed by the same function that produced it and
    compared. A JavaScript reimplementation is exactly what this forbids.
    """
    series = eurostat.refresh(offline=True)
    for geo in small_payload["geos"]:
        for mi, mult in enumerate(small_payload["multiples"]):
            for ti, theta in enumerate(small_payload["thetas"]):
                cell = small_payload["grid"][geo][mi][ti]
                fresh = sourcing.point(geo, theta, series, mult, with_curve=True)
                assert cell["npv"] == pytest.approx(fresh.npv0, abs=0.05)
                assert cell["t"] == fresh.t_star
                assert cell["trig"] == pytest.approx(fresh.trigger, abs=0.05)
                assert cell["p"] == pytest.approx(fresh.p_h2, abs=5e-3)
                assert cell["eps"] == pytest.approx(fresh.eps_cln, abs=5e-4)
                assert len(cell["curve"]) == len(small_payload["years"])


def test_the_payload_carries_the_published_point_for_comparison(
    small_payload: dict,
) -> None:
    from timing_model.results import outputs

    base = outputs(Params(), ScenarioParams())
    assert small_payload["base"]["npv"] == pytest.approx(base.npv0, abs=0.05)
    assert small_payload["base"]["p"] == ScenarioParams().p_H2
    assert small_payload["base"]["eps"] == Params().common.eps_cln


def test_the_page_is_self_contained(small_payload: dict) -> None:
    """No CDN, no fonts, no fetch: it has to open from a file:// URL forever."""
    html = explorer.render(small_payload)
    for forbidden in ("<link", "<img", " src=", "fetch(", "XMLHttpRequest",
                      "@import", "import("):
        assert forbidden not in html, forbidden
    # The only absolute URL allowed is the SVG namespace, which loads nothing.
    urls = [u for u in html.split('"') if u.startswith(("http://", "https://"))]
    assert set(urls) <= {"http://www.w3.org/2000/svg"}, urls


def test_the_payload_cannot_close_its_own_script_element(small_payload: dict) -> None:
    """A '</script>' inside the JSON would end the block and break the page."""
    poisoned = dict(small_payload)
    poisoned["geos"] = ["</script><script>alert(1)</script>"]
    html = explorer.render(poisoned)
    # The page has exactly two script elements; the payload adds no third.
    assert html.count("</script>") == 2
    assert "<\\/script>" in html, "the closing tag was not escaped"
    body = html.split('type="application/json">')[1].split("</script>")[0]
    assert "</script>" not in body


def test_the_page_offers_a_table_view(small_payload: dict) -> None:
    """The light-mode aqua is below 3:1, so the relief rule requires one."""
    html = explorer.render(small_payload)
    assert 'id="tableWrap"' in html and "<table" in html
