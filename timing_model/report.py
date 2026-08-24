"""Tables and the CSV the MATLAB diff runs against.

Appendix A §4.1.  This module is the enforcement point for the conditional-
outputs mechanic: it refuses to render any row containing ``t_star`` or
``trigger`` unless the conditions are populated, and it prints them alongside.
"""

from __future__ import annotations

import argparse
from typing import Iterable, Mapping, Sequence

import pandas as pd

from timing_model.params import ModelError
from timing_model.results import CONDITION_KEYS, Outputs
from timing_model.scenarios import Rung, run_ladder, sigma_ladder

__all__ = ["HEADLINE_FIELDS", "row", "results_frame", "render_table",
           "render_ladder", "write_csv", "main"]

#: Fields that may never be printed without their conditions.
HEADLINE_FIELDS: frozenset[str] = frozenset({"t_star", "trigger"})


def _fmt_year(y: int | None) -> str:
    return str(y) if y is not None else "beyond"


def row(label: str, o: Outputs) -> dict[str, object]:
    """One flat record. Raises unless the conditions travel with it."""
    o.require_conditions()
    rec: dict[str, object] = {
        "scenario": label,
        "t_star": _fmt_year(o.t_star),
        "t_exp": _fmt_year(o.t_exp),
        "npv0_eur_per_t_capacity": round(o.npv0, 2),
        "trigger_eur_per_tco2": round(o.trigger, 2),
        "crossing_year": _fmt_year(o.crossing_year),
        "crossing_reason": o.crossing_reason,
    }
    rec.update({f"cond_{k}": o.conditions[k] for k in CONDITION_KEYS})
    rec["binding_guards"] = " | ".join(o.binding_guards) or "none"
    return rec


def results_frame(rows: Iterable[tuple[str, Outputs]]) -> pd.DataFrame:
    """Tabulate labelled outputs. Every row carries its conditions."""
    return pd.DataFrame([row(label, o) for label, o in rows])


def render_table(rows: Sequence[tuple[str, Outputs]], title: str = "") -> str:
    """Render a text table. Raises if any row would print a headline field bare.

    The conditions block is printed under the table rather than repeated on
    every line, but it is printed *unconditionally* - a table whose rows differ
    in their conditions gets one condition line per row.
    """
    df = results_frame(rows)
    cond_cols = [f"cond_{k}" for k in CONDITION_KEYS]
    shown = [c for c in df.columns if c not in cond_cols and c != "binding_guards"]
    if HEADLINE_FIELDS & set(shown) and not cond_cols:
        raise ModelError("headline fields present with no conditions block")

    out: list[str] = []
    if title:
        out += [title, "=" * len(title)]
    out.append(df[shown].to_string(index=False))
    out.append("")
    out.append("Conditions (every row above is conditional on these):")
    uniq = df[["scenario", *cond_cols]].drop_duplicates(subset=cond_cols)
    for _, r in uniq.iterrows():
        bits = ", ".join(f"{k}={r[f'cond_{k}']}" for k in CONDITION_KEYS)
        out.append(f"  [{r['scenario']}] {bits}")
    guards = [g for gs in df["binding_guards"] for g in gs.split(" | ") if g != "none"]
    if guards:
        out.append("")
        out.append("Binding guards:")
        out += [f"  - {g}" for g in dict.fromkeys(guards)]
    return "\n".join(out)


def render_ladder(ladder: Sequence[tuple[Rung, Outputs]] | None = None) -> str:
    """The cumulative stress ladder of Appendix A §4.4."""
    pairs = ladder if ladder is not None else run_ladder()
    return render_table(
        [(r.label, o) for r, o in pairs],
        "Cumulative stress ladder (each row adds one correction to the row above)",
    )


def write_csv(path: str, rows: Iterable[tuple[str, Outputs]]) -> pd.DataFrame:
    """Write ``python_results.csv`` in the schema the MATLAB diff expects."""
    df = results_frame(rows)
    df.to_csv(path, index=False)
    return df


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. ``--csv`` writes the frame the MATLAB diff runs against."""
    ap = argparse.ArgumentParser(description="timing_model report")
    ap.add_argument("--csv", metavar="PATH", nargs="?", const="python_results.csv")
    ap.add_argument("--sigma", action="store_true", help="print the volatility ladder")
    args = ap.parse_args(argv)

    pairs = run_ladder()
    print(render_ladder(pairs))
    if args.sigma:
        print()
        print(render_table(sigma_ladder(), "Volatility ladder (Appendix A §3.4)"))
    if args.csv:
        write_csv(args.csv, [(r.label, o) for r, o in pairs])
        print(f"\nwrote {args.csv}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
