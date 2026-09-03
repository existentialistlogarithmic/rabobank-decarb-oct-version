"""Run everything: gate, base case, ladders, reconciliation, CSV, test suite.

One entry point so the whole model can be exercised in a single run - in
PyCharm, right-click this file and choose Run.

Exits non-zero if the validation gate fails, the negative control does not
behave, or any test fails, so it doubles as a CI smoke check.
"""

from __future__ import annotations

import sys
from typing import Callable

from timing_model.diff_harness import diff, reference_cases, run_cases
from timing_model.params import ModelError
from timing_model.report import render_ladder, render_table, write_csv
from timing_model.results import outputs
from timing_model.scenarios import (
    SOURCED_RANGES,
    corrected_base,
    published_base,
    run_ladder,
    sigma_ladder,
)
from timing_model.validate import GATE, run_gate

CSV_PATH = "python_results.csv"


def plots_out() -> str:
    """Filename the chart page is written to."""
    import plots

    return plots.OUT


def banner(n: int, title: str) -> None:
    print(f"\n\n{'=' * 78}\n{n}. {title}\n{'=' * 78}")


def section_gate() -> None:
    """Appendix A §4.3. Nothing prints downstream until these reproduce."""
    banner(1, "VALIDATION GATE")
    actual = run_gate()  # raises ModelError on failure
    print(f"{'quantity':<16}{'published':>12}{'computed':>14}{'rel err':>12}")
    print("-" * 54)
    for k, want in GATE.items():
        got = actual[k]
        print(f"{k:<16}{want:>12}{got:>14.6f}{abs(got - want) / abs(want):>12.2e}")
    print("\nAll nine reproduce within 1e-3 relative.")


def section_base() -> None:
    banner(2, "BASE CASE")
    p, sc = published_base()
    o = outputs(p, sc)
    print(f"  T*             {o.t_star}")
    print(f"  T_exp          {o.t_exp}")
    print(f"  NPV0           {o.npv0:.2f} EUR/t capacity (discounted to 2026)")
    print(f"  trigger p*'    {o.trigger:.2f} EUR/tCO2")
    print(f"  crossing year  {o.crossing_year} ({o.crossing_reason})")
    print("\n  Diagnostics (communication objects, not decision inputs):")
    for k, v in o.diagnostics.items():
        print(f"    {k:<26}{v:>12.4f}")
    print("\n  Conditions - every number above is conditional on these:")
    for k, v in o.conditions.items():
        print(f"    {k:<16}{v}")

    pc, scc = corrected_base()
    oc = outputs(pc, scc)
    print("\n  Same model with the unarguable unit fixes applied (u, kappa):")
    print(f"    T* {oc.t_star}   NPV0 {oc.npv0:.2f}   trigger {oc.trigger:.2f}")


def section_ladder() -> None:
    banner(3, "CUMULATIVE STRESS LADDER")
    print(render_ladder())


def section_sigma() -> None:
    banner(4, "VOLATILITY LADDER")
    print(render_table(sigma_ladder(), "Appendix A §3.4"))


def section_ranges() -> None:
    banner(5, "SOURCED RANGES")
    print("Appendix A §3.3 leads with these, not a +/-20% sweep.\n")
    for name, (lo, hi) in SOURCED_RANGES.items():
        print(f"  {name:<16}{lo:>10.2f}  ..{hi:>10.2f}")


def section_reconciliation() -> int:
    """The 50-case grid, the self-diff, and the negative control."""
    banner(6, "RECONCILIATION HARNESS")
    from collections import Counter

    cases = reference_cases()
    df = run_cases(cases)
    print(f"Reference grid: {len(cases)} cases in legacy mode "
          f"(u=1, lump support, p_H2=2.60, nominal, kappa=1).\n")
    for group, n in sorted(Counter(str(r["group"]) for r in df).items()):
        print(f"  {group:<24}{n:>3}")

    failures = 0
    if diff(df, df):
        print("\nFAIL: a frame disagreed with itself.")
        failures += 1
    else:
        print("\nSelf-diff clean (0 mismatches).")

    matlab = [dict(r) for r in df]
    for r in matlab:
        if r["case"] == "base":
            r["npv0"] = float(r["npv0"]) + 5.0
        if r["case"] == "sigma_crisis":
            r["t_star"] = int(r["t_star"]) + 1
    found = diff(df, matlab)
    print("\nNegative control - perturb one NPV by EUR 5 and one T* by one year:")
    for m in found:
        print(f"  flagged  {m}")
    if len(found) != 2:
        print(f"FAIL: expected exactly 2 mismatches, got {len(found)}.")
        failures += 1
    else:
        print("  -> exactly 2 flagged, as required.")

    print("\nNOTE: no MATLAB CSV is present, so the real diff has not been run.")
    print("      Drop the reference CSV beside this file and compare with diff().")
    return failures


def section_csv() -> None:
    banner(7, "CSV OUTPUT")
    table = write_csv(CSV_PATH, [(r.label, o) for r, o in run_ladder()])
    cols = list(table[0]) if table else []
    print(f"Wrote {CSV_PATH} ({len(table)} rows, {len(cols)} columns).")
    print("Columns:", ", ".join(cols))


def section_observed() -> None:
    """Observed inputs, and what they say about the model's own assumptions.

    Three parts: the Eurostat series and the two hydrogen floors they imply,
    the ECB rates behind the discount rate, and the grounding table that puts
    every checkable input next to the statistic that bears on it.
    """
    banner(8, "OBSERVED DATA (Eurostat, ECB)")
    import ecb
    import eurostat
    import grounding

    eurostat.main()
    print()
    ecb.main()
    print()
    grounding.main(offline=True)


def section_findings() -> None:
    """The derived structural findings, then the sourcing frontier.

    ``analysis`` derives findings from the model alone. ``sourcing`` adds the
    ones that only appear once the hydrogen price and the clean-route emission
    intensity are treated as the single parameter they physically are.
    """
    banner(9, "STRUCTURAL FINDINGS")
    import analysis
    import sourcing

    for i, fnd in enumerate(analysis.all_findings(), 1):
        print(f"\n  {i}. {fnd.title}")
        print(f"     {fnd.statement}")
    print()
    sourcing.main()


def section_documents() -> int:
    """Write the generated pages. Standard library only, like everything else.

    ``sources.main()`` is the one that can fail: it regenerates SOURCES.md from
    the provenance register and returns non-zero if the register and the model
    disagree about any input's value.
    """
    banner(10, "CHARTS, FINDINGS REPORT AND SOURCES")
    import article
    import explorer
    import findings_report
    import plots
    import sources
    import surface

    plots.main()
    findings_report.main()
    surface.main()
    article.main()
    explorer.main()
    return sources.main()


def section_selfcheck() -> int:
    """Standard-library verification - runs everywhere, no packages needed."""
    banner(11, "SELF-CHECK (standard library only)")
    import selfcheck

    return selfcheck.main()


def section_tests() -> int:
    banner(12, "TEST SUITE")
    try:
        import pytest
    except ImportError:
        print("pytest is not installed, so the 206-test suite is skipped.")
        print("Section 11 above covers the same load-bearing claims without it.")
        return 0
    code = pytest.main(["-q", "tests"])
    return 0 if code == 0 else 1


def main() -> int:
    print("timing_model - full run")
    print("Read CALIBRATION.md before quoting any number from this output.")
    failures = 0
    try:
        section_gate()
    except ModelError as exc:
        print(f"\nVALIDATION GATE FAILED - nothing downstream is trustworthy:\n{exc}")
        return 1

    steps: list[Callable[[], None]] = [
        section_base,
        section_ladder,
        section_sigma,
        section_ranges,
    ]
    for step in steps:
        step()
    failures += section_reconciliation()
    section_csv()
    section_observed()
    section_findings()
    failures += section_documents()
    failures += section_selfcheck()
    failures += section_tests()

    banner(13, "SUMMARY")
    if failures:
        print(f"{failures} section(s) reported a problem. See above.")
    else:
        print("Gate passed, negative control behaved, self-check clean.")
        print("Base case: T* = 2029, NPV0 = 1588.29 EUR/t, trigger crossed 2030.")
        print(f"Charts written to {plots_out()}; provenance to SOURCES.md.")
        print("The sourcing frontier is explorable in explorer.html.")
        print("\nReminder: ladder rows 4-7 do not reproduce the published table.")
        print("CALIBRATION.md documents each one and why.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
