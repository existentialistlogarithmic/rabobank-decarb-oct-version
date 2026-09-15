"""Standard-library verification of the model's load-bearing claims.

The pytest suite in ``tests/`` is the real thing. This file exists
for environments where third-party packages cannot be installed: it re-checks
the claims that must not silently break, using nothing but the standard
library, and reports pass/fail per claim.

Run directly, or let ``run_all.py`` call it.
"""

from __future__ import annotations

import ast
import pathlib
from collections.abc import Callable
from dataclasses import replace

from timing_model.benefit import free_allocation_factor
from timing_model.cost import residual_value, switching_cost
from timing_model.diff_harness import diff, reference_cases, run_cases
from timing_model.objective import t_exp_marginal, t_star
from timing_model.option import crossing_year
from timing_model.params import ModelError, Params, ScenarioParams
from timing_model.report import render_table, row
from timing_model.results import Outputs, outputs
from timing_model.scenarios import published_base, run_ladder, sigma_ladder
from timing_model.validate import GATE, run_gate, run_guards

PKG = pathlib.Path(__file__).resolve().parent / "timing_model"

_results: list[tuple[bool, str, str]] = []


def check(name: str) -> Callable[[Callable[[], None]], Callable[[], None]]:
    """Register a claim. The body raises AssertionError to fail it."""

    def deco(fn: Callable[[], None]) -> Callable[[], None]:
        try:
            fn()
            _results.append((True, name, ""))
        except Exception as exc:  # noqa: BLE001 - report, do not propagate
            _results.append((False, name, f"{type(exc).__name__}: {exc}"))
        return fn

    return deco


def close(a: float, b: float, rel: float = 1e-3) -> bool:
    return abs(a - b) <= rel * abs(b)


@check("validation gate: all nine published quantities")
def _gate() -> None:
    actual = run_gate()
    for k, want in GATE.items():
        assert close(actual[k], want), f"{k}: {actual[k]} vs {want}"


@check("a(p_H2) endogenous: -60 at 2.60, -372.95 at 8.29")
def _a() -> None:
    from timing_model.primitives import opex_penalty

    p, _ = published_base()
    assert abs(opex_penalty(p, ScenarioParams(p_H2=2.60)) + 60.0) < 1e-9
    assert abs(opex_penalty(p, ScenarioParams(p_H2=8.29)) + 372.95) < 1e-9


@check("S_s(2026) = 360, the write-off behind p*' = 109.52")
def _ss() -> None:
    p, _ = published_base()
    assert abs(residual_value(p.common.t0, p) - 360.0) < 1e-9


@check("base case: T* 2029, T_exp 2029, NPV0 1605.9, crossed 2030")
def _base() -> None:
    p, sc = published_base()
    o = outputs(p, sc)
    assert o.t_star == 2029, o.t_star
    assert o.t_exp == 2029, o.t_exp
    assert abs(o.npv0 - 1605.9) < 0.05, o.npv0
    assert o.crossing_year == 2030, o.crossing_year
    assert close(o.trigger, 109.52), o.trigger


@check("T_exp: argmax and the marginal test agree in the base case")
def _texp() -> None:
    p, sc = published_base()
    assert t_star(p, sc) == t_exp_marginal(p, sc) == 2029


@check("stress ladder: trigger column exact on all seven rungs")
def _ladder_trigger() -> None:
    want = [109.5, 109.5, 116.9, 116.9, 366.9, 366.9, 366.9]
    got = [o.trigger for _, o in run_ladder()]
    for g, w in zip(got, want, strict=False):
        assert abs(g - w) < 0.05, f"{g} vs {w}"


@check("stress ladder: rows 1-3 reproduce T* and NPV")
def _ladder_rows() -> None:
    rows = run_ladder()
    for i, (t, npv) in enumerate([(2029, 1606), (2029, 1302), (2030, 1174)]):
        _, o = rows[i]
        assert o.t_star == t, f"row {i+1} T* {o.t_star} vs {t}"
        assert abs(o.npv0 - npv) < 0.6, f"row {i+1} NPV {o.npv0} vs {npv}"


@check("stress ladder: hydrogen rows have no commitment year")
def _ladder_beyond() -> None:
    for _, o in run_ladder()[4:]:
        assert o.t_star is None and o.crossing_reason == "beyond horizon"


@check("ladder compounds down to the last rung, where the stream reverses it")
def _cumulative() -> None:
    """Rows 1-6 compound; row 7 adds value back.

    Once support is tapered and gone by 2035 (v11 eq 10), a ten-year CCfD
    stream beats the shrinking lump. A result, not a leak.
    """
    npvs = [o.npv0 for _, o in run_ladder()]
    assert npvs[:-1] == sorted(npvs[:-1], reverse=True), npvs
    assert npvs[-1] > npvs[-2], npvs


@check("sigma=0.45 crosses in the mid-2040s, not 'never'")
def _sigma() -> None:
    o = dict(sigma_ladder())["realised"]
    assert o.crossing_year is not None and 2040 <= o.crossing_year <= 2049


@check("guard: r - mu < 0.005 raises")
def _guard_rmu() -> None:
    p, sc = published_base()
    try:
        run_guards(p.with_common(mu=0.0785), sc)
    except ModelError:
        return
    raise AssertionError("did not raise")


@check("guard: u outside (0, 1] raises")
def _guard_u() -> None:
    p, _ = published_base()
    for bad in (0.0, -0.1, 1.01):
        try:
            run_guards(p, ScenarioParams(u=bad))
        except ModelError:
            continue
        raise AssertionError(f"u={bad} did not raise")


@check("guard: allocation schedule monotone non-increasing in [0,1]")
def _guard_f() -> None:
    p, _ = published_base()
    for vintage in ("law2023", "com2026"):
        sc = ScenarioParams(policy_vintage=vintage)
        prev = 1.0
        for t in range(p.common.t0, p.common.horizon_end + 1):
            f = free_allocation_factor(t, sc)
            assert 0.0 <= f <= 1.0 and f <= prev + 1e-12, f"{vintage} at {t}"
            prev = f


@check("guard: residual value never negative past the reline")
def _guard_ss() -> None:
    p, _ = published_base()
    for T in range(p.common.t0, p.common.horizon_end + 1):
        assert residual_value(T, p) >= 0.0, T


@check("guard: capex clamp is recorded when it binds")
def _guard_clamp() -> None:
    p, sc = published_base()
    rich = p.with_policy(s_max=5000.0)
    assert switching_cost(2030, rich, sc).clamp_binds
    assert any("clamp binds" in n for n in run_guards(rich, sc))


@check("support envelope: all four branches of v11 eq (9), and the 2028 step")
def _support_envelope() -> None:
    """The branch that was missing: 0.35*s_max before the Booster window.

    Its absence put a EUR 200 step at 2028 where the specification works out
    EUR 130, so the model paid the plant EUR 70/t to wait a year - inside the
    one calculation it exists to perform. It survived because s(t) is a
    schedule, and only the two support scenarios' outputs were ever compared,
    both of which commit inside the window.
    """
    from timing_model.cost import support

    p, sc = published_base()
    want = {2026: 70.0, 2027: 70.0, 2028: 200.0, 2031: 200.0,
            2032: 150.0, 2034: 50.0, 2035: 0.0}
    for t, s in want.items():
        assert abs(support(t, p, sc) - s) < 1e-9, f"s({t}) = {support(t, p, sc)}, want {s}"
    step = support(2028, p, sc) - support(2027, p, sc)
    assert abs(step - 130.0) < 1e-9, step
    pr = p.with_policy(lam=0.30, q_min=0.10)
    for t, q in ((2029, 0.70), (2030, 0.40), (2031, 0.10)):
        assert abs(support(t, pr, sc) / p.policy.s_max - q) < 1e-9, t


@check("units: EUR/t capacity times annual tonnes is money, and the round trip closes")
def _units_bridge() -> None:
    """The misreading this guards: I0 = 900 read as EUR 900.

    It is EUR 900 per tonne of ANNUAL capacity - EUR 2.2bn for a 2.5 Mt/yr
    works. The check that settles it is the round trip: every per-tonne figure
    in the projects table came from an announced total divided by an announced
    capacity, so dividing them again has to land back on it.
    """
    from analysis import units

    assert units.absolute(900.0, 2.5) == 2.25e9
    assert units.eur(2.25e9) == "EUR 2.2bn"
    rows = units.round_trip()
    assert len(rows) >= 4, "the projects table lost rows"
    for name, total, mt, stated, recomputed in rows:
        assert abs(recomputed - stated) <= 0.03 * stated, (
            f"{name}: {total:,.0f} over {mt} Mt gives {recomputed:,.0f}, "
            f"table says {stated:,.0f}"
        )


@check("guard: gate failure raises rather than returning a flag")
def _guard_gate() -> None:
    p, sc = published_base()
    try:
        run_gate(p.with_sector(I0=1000.0), sc)
    except ModelError:
        return
    raise AssertionError("did not raise")


@check("crossing year returns a reason, never the string 'never'")
def _never() -> None:
    year, reason = crossing_year(400.0, dict.fromkeys(range(2026, 2051), 50.0), 2050)
    assert year is None and reason == "beyond horizon" and "never" not in reason


@check("report refuses to print a headline number without its conditions")
def _conditions() -> None:
    bare = Outputs(2029, 2029, 1605.9, 109.52, 2030)
    for fn in (lambda: row("bare", bare), lambda: render_table([("bare", bare)])):
        try:
            fn()
        except ModelError:
            continue
        raise AssertionError("rendered a bare result")
    p, sc = published_base()
    good = outputs(p, sc)
    for key in good.conditions:
        partial = dict(good.conditions)
        partial[key] = ""
        try:
            row("partial", replace(good, conditions=partial))
        except ModelError:
            continue
        raise AssertionError(f"missing {key} not caught")


@check("diff harness: 50 cases, self-diff clean, negative control flags two")
def _diff() -> None:
    assert len(reference_cases()) == 50
    py = run_cases()
    assert diff(py, py) == []
    matlab = [dict(r) for r in py]
    for r in matlab:
        if r["case"] == "base":
            r["npv0"] = float(r["npv0"]) + 5.0
        if r["case"] == "sigma_crisis":
            r["t_star"] = int(r["t_star"]) + 1
    found = diff(py, matlab)
    assert len(found) == 2, [str(m) for m in found]
    assert {m.field for m in found} == {"npv0", "t_star"}


@check("layering: cost.py imports neither objective nor the load factor u")
def _layering() -> None:
    tree = ast.parse((PKG / "cost.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "objective" not in (node.module or ""), "cost imports objective"
        if isinstance(node, ast.Attribute):
            assert node.attr != "u", "cost.py reads the load factor"


@check("no third-party imports anywhere in the package")
def _stdlib_only() -> None:
    banned = {"numpy", "pandas", "scipy"}
    for path in sorted(PKG.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            assert not (banned & set(names)), f"{path.name} imports {names}"


@check("finding: lever classes are exactly disjoint (value / threshold / both)")
def _orthogonal() -> None:
    from analysis.findings import lever_classes

    ls = lever_classes()
    klasses = {lever.klass for lever in ls}
    assert "value only" in klasses and "threshold only" in klasses, klasses
    # the defining property: a value-only lever moves the trigger by EXACTLY zero
    for lever in ls:
        if lever.klass == "value only":
            assert abs(lever.d_trigger_pct) < 1e-9, f"{lever.name} trigger {lever.d_trigger_pct}"
        if lever.klass == "threshold only":
            assert abs(lever.d_npv_pct) < 1e-9, f"{lever.name} NPV {lever.d_npv_pct}"


@check("finding: volatility is a pure threshold lever, support a pure value lever")
def _instruments() -> None:
    from analysis.findings import lever_classes

    by = {lv.name: lv for lv in lever_classes()}
    assert by["volatility -> CfD"].klass == "threshold only"
    assert by["support s_max x2"].klass == "value only"


@check("finding: utilisation inverts at a hydrogen price inside the sourced range")
def _inversion() -> None:
    from analysis.findings import utilisation_inversion

    flip = utilisation_inversion()
    assert flip is not None, "no sign flip found"
    assert 2.5 <= flip <= 20.0, flip


@check("finding: a reline capture region exists and T* equals T_rel inside it")
def _capture() -> None:
    from analysis.findings import reline_capture

    rc = reline_capture()
    assert rc.capture_from is not None
    for age, t_rel, best_year, _ in rc.rows:
        if age >= rc.capture_from:
            assert best_year == t_rel, f"age {age}: T* {best_year} != reline {t_rel}"


@check("finding: trigger stability under r is cancellation of two larger moves")
def _cancellation() -> None:
    from analysis.findings import rate_cancellation

    rs = rate_cancellation()
    assert rs.d_break_even_pct > 0 and rs.d_multiple_pct < 0, "not opposing"
    assert abs(rs.d_trigger_pct) < abs(rs.d_break_even_pct) / 4, "no cancellation"


@check("observed data: the base-case hydrogen price is below the power bill everywhere")
def _h2_floor() -> None:
    """Eurostat industrial power alone puts EUR 2.60/kg out of reach.

    Runs from the committed cache, so it needs no network.
    """
    from data import eurostat

    s = eurostat.refresh(offline=True)
    floors = {k[-2:]: eurostat.hydrogen_power_floor(v.value)
              for k, v in s.items() if k.startswith("power_")}
    assert len(floors) >= 5, floors
    assert min(floors.values()) > 2.60, f"cheapest floor {min(floors.values()):.2f}"


@check("observed data: EUR 2.60/kg is reachable only as unabated fossil hydrogen")
def _grey_hydrogen() -> None:
    """Gas prices put the base case below every green floor and inside the grey band.

    Runs from the committed caches, so it needs no network.
    """
    from analysis import grounding
    from timing_model.params import ScenarioParams

    floors = grounding.hydrogen_floors(offline=True)
    assert len(floors) >= 5, floors
    green = [g for g, _ in floors.values()]
    grey = [y for _, y in floors.values()]
    base = ScenarioParams().p_H2
    assert min(green) > base, f"cheapest green floor {min(green):.2f}"
    assert min(grey) < base < min(green), (min(grey), base, min(green))


@check("observed data: grey hydrogen contradicts the clean-route intensity")
def _intensity_contradiction() -> None:
    """The strongest thing the observed data says: two inputs cannot both hold."""
    from analysis import grounding

    implied = grounding.grey_hydrogen_intensity()
    assert implied > 4 * Params().common.eps_cln, implied
    verdicts = {r.param: r.verdict for r in grounding.groundings(offline=True)}
    assert verdicts.get("common.eps_cln") == "contradiction", verdicts


@check("observed data: the hurdle rate is above the observed real risk-free rate")
def _risk_premium() -> None:
    from data import ecb, eurostat

    rates = ecb.refresh(offline=True)
    hicp = eurostat.refresh(offline=True)["hicp"].value
    real = ecb.real_risk_free(rates["yield_10y"].value, hicp)
    assert 0.0 < real < Params().common.r, real


@check("observed data: every grounded input is also a cited input")
def _grounding_vocabulary() -> None:
    """The grounding table and the provenance register share one set of names."""
    from analysis import grounding
    from reporting import sources

    registered = {c.param for c in sources.REGISTER}
    for grounded in grounding.groundings(offline=True):
        assert grounded.param in registered, grounded.param
        assert grounded.verdict in grounding.VERDICTS, grounded.verdict


@check("frontier: value falls as hydrogen gets greener, in every member state")
def _frontier_monotone() -> None:
    """FINDING: at the model's own carbon path, fossil hydrogen wins on NPV.

    The consequence of tying p_H2 and eps_cln into one parameter. Pinned
    because the headline inverts if it ever stops holding.
    """
    from analysis import sourcing
    from data import eurostat

    s = eurostat.refresh(offline=True)
    for geo in eurostat.STEEL_GEOS:
        npvs = [pt.npv0 for pt in sourcing.frontier(geo, series=s)]
        assert npvs == sorted(npvs, reverse=True), f"{geo}: {npvs}"


@check("frontier: the published price/intensity pair is not on it")
def _frontier_gap() -> None:
    """A fifth to a third of the published NPV rests on an unreachable pair."""
    from analysis import sourcing
    from data import eurostat

    s = eurostat.refresh(offline=True)
    shares = []
    for geo in eurostat.STEEL_GEOS:
        model, consistent, theta = sourcing.feasibility_gap(geo, s)
        assert theta is not None and 0.0 < theta < 1.0, (geo, theta)
        assert consistent < model, (geo, consistent, model)
        shares.append((model - consistent) / model)
    assert min(shares) > 0.15 and max(shares) < 0.45, (min(shares), max(shares))


@check("frontier: sourcing moves the commitment year, not just the value")
def _frontier_timing() -> None:
    from analysis import sourcing
    from data import eurostat

    s = eurostat.refresh(offline=True)
    horizon = Params().common.horizon_end
    for geo in eurostat.STEEL_GEOS:
        lo, hi = sourcing.point(geo, 0.0, s), sourcing.point(geo, 1.0, s)
        late = horizon + 2 if hi.t_star is None else hi.t_star
        assert lo.t_star is not None and late > lo.t_star, (geo, lo.t_star, hi.t_star)


@check("frontier: green never wins at the central carbon path")
def _frontier_crossover() -> None:
    """Every member state needs a multiple of the model's own path."""
    from analysis import sourcing
    from data import eurostat

    s = eurostat.refresh(offline=True)
    mults = {g: sourcing.crossover_multiple(g, s) for g in ("SE", "IT")}
    assert all(m is not None and m > 1.0 for m in mults.values()), mults
    assert mults["SE"] < mults["IT"], mults


@check("provenance: every input cited, every citation equal to the running model")
def _provenance() -> None:
    """SOURCES.md is generated from a register that is checked against the code.

    The failure this prevents: a default moves, the bibliography does not, and
    the citation now vouches for a number nobody is using.
    """
    from reporting import sources

    problems = sources.audit()
    assert not problems, "; ".join(problems)


@check("provenance: licensed and unread sources are flagged, never quoted as sourced")
def _unverified() -> None:
    """The Platts assessment is an open item, not a fact.

    The COM(2026) floor used to be flagged here too. v11 eq (12) gives the
    proposal its own factor schedule, so that claim now cites the
    specification and is no longer a to-do; the licensed price assessment
    still is, and nothing may quote it as sourced.
    """
    from reporting import sources

    flagged = {c.param for c in sources.unverified()}
    assert flagged, "the open items did not disappear; the register lost them"
    for c in sources.unverified():
        assert any(sources.SOURCES[r].url is None for r in c.refs), c.param
    for c in sources.REGISTER:
        if "platts_h2" in c.refs:
            assert c.status == "unverified", f"{c.param} claims {c.status}"
        if c.status == "sourced":
            reachable = [r for r in c.refs if sources.SOURCES[r].url is not None]
            assert reachable, f"{c.param} is 'sourced' on unreachable {c.refs}"


@check("observed data: the model deflator matches euro-area HICP within 1pp")
def _deflator() -> None:
    from data import eurostat

    hicp = eurostat.refresh(offline=True)["hicp"].value
    assert abs(hicp - 2.0) < 1.0, hicp


def main() -> int:
    """Print each claim and return 0 only if every one passed."""
    print(f"selfcheck - {len(_results)} claims, standard library only\n")
    width = max(len(n) for _, n, _ in _results)
    for ok, name, err in _results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(width)}"
              + (f"   {err}" if err else ""))
    failed = [n for ok, n, _ in _results if not ok]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
