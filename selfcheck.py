"""Standard-library verification of the model's load-bearing claims.

The pytest suite in ``tests/`` is the real thing - 91 tests. This file exists
for environments where third-party packages cannot be installed: it re-checks
the claims that must not silently break, using nothing but the standard
library, and reports pass/fail per claim.

Run directly, or let ``run_all.py`` call it.
"""

from __future__ import annotations

import ast
import pathlib
from dataclasses import replace
from typing import Callable

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


@check("base case: T* 2029, T_exp 2029, NPV0 1588.3, crossed 2030")
def _base() -> None:
    p, sc = published_base()
    o = outputs(p, sc)
    assert o.t_star == 2029, o.t_star
    assert o.t_exp == 2029, o.t_exp
    assert abs(o.npv0 - 1588.3) < 0.05, o.npv0
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
    for g, w in zip(got, want):
        assert abs(g - w) < 0.05, f"{g} vs {w}"


@check("stress ladder: rows 1-3 reproduce T* and NPV")
def _ladder_rows() -> None:
    rows = run_ladder()
    for i, (t, npv) in enumerate([(2029, 1588), (2030, 1294), (2030, 1166)]):
        _, o = rows[i]
        assert o.t_star == t, f"row {i+1} T* {o.t_star} vs {t}"
        assert abs(o.npv0 - npv) < 0.6, f"row {i+1} NPV {o.npv0} vs {npv}"


@check("stress ladder: hydrogen rows have no commitment year")
def _ladder_beyond() -> None:
    for _, o in run_ladder()[4:]:
        assert o.t_star is None and o.crossing_reason == "beyond horizon"


@check("ladder is cumulative: no rung improves the case")
def _cumulative() -> None:
    npvs = [o.npv0 for _, o in run_ladder()]
    assert npvs == sorted(npvs, reverse=True), npvs


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
    year, reason = crossing_year(400.0, {y: 50.0 for y in range(2026, 2051)}, 2050)
    assert year is None and reason == "beyond horizon" and "never" not in reason


@check("report refuses to print a headline number without its conditions")
def _conditions() -> None:
    bare = Outputs(2029, 2029, 1588.3, 109.52, 2030)
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
    from analysis import lever_classes

    ls = lever_classes()
    klasses = {l.klass for l in ls}
    assert "value only" in klasses and "threshold only" in klasses, klasses
    # the defining property: a value-only lever moves the trigger by EXACTLY zero
    for l in ls:
        if l.klass == "value only":
            assert abs(l.d_trigger_pct) < 1e-9, f"{l.name} trigger {l.d_trigger_pct}"
        if l.klass == "threshold only":
            assert abs(l.d_npv_pct) < 1e-9, f"{l.name} NPV {l.d_npv_pct}"


@check("finding: volatility is a pure threshold lever, support a pure value lever")
def _instruments() -> None:
    from analysis import lever_classes

    by = {l.name: l for l in lever_classes()}
    assert by["volatility -> CfD"].klass == "threshold only"
    assert by["support s_max x2"].klass == "value only"


@check("finding: utilisation inverts at a hydrogen price inside the sourced range")
def _inversion() -> None:
    from analysis import utilisation_inversion

    flip = utilisation_inversion()
    assert flip is not None, "no sign flip found"
    assert 2.5 <= flip <= 20.0, flip


@check("finding: a reline capture region exists and T* equals T_rel inside it")
def _capture() -> None:
    from analysis import reline_capture

    rc = reline_capture()
    assert rc.capture_from is not None
    for age, t_rel, t_star, _ in rc.rows:
        if age >= rc.capture_from:
            assert t_star == t_rel, f"age {age}: T* {t_star} != reline {t_rel}"


@check("finding: trigger stability under r is cancellation of two larger moves")
def _cancellation() -> None:
    from analysis import rate_cancellation

    rs = rate_cancellation()
    assert rs.d_break_even_pct > 0 and rs.d_multiple_pct < 0, "not opposing"
    assert abs(rs.d_trigger_pct) < abs(rs.d_break_even_pct) / 4, "no cancellation"


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
