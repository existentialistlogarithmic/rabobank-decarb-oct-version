"""Tables and the CSV the MATLAB diff runs against.

Appendix A §4.1.  This module is the enforcement point for the conditional-
outputs mechanic: it refuses to render any row containing ``t_star`` or
``trigger`` unless the conditions are populated, and it prints them alongside.
"""

from __future__ import annotations

import argparse
import csv
from typing import Iterable, Sequence

from timing_model.params import ModelError
from timing_model.results import CONDITION_KEYS, Outputs
from timing_model.scenarios import Rung, run_ladder, sigma_ladder

__all__ = ["HEADLINE_FIELDS", "row", "results_table", "render_table",
           "render_ladder", "write_csv", "main", "Table"]

#: A table is a list of flat records. Deliberately stdlib-only: every equation
#: in this model is closed-form, so nothing here needs a dataframe library.
Table = list[dict[str, object]]

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


def results_table(rows: Iterable[tuple[str, Outputs]]) -> Table:
    """Tabulate labelled outputs. Every row carries its conditions."""
    return [row(label, o) for label, o in rows]


def _columns(table: Table) -> list[str]:
    """Column order, taken from the first record."""
    return list(table[0]) if table else []


def _render_grid(table: Table, columns: Sequence[str]) -> str:
    """Right-aligned fixed-width text grid, no third-party formatter."""
    widths = {
        c: max(len(str(c)), *(len(str(r[c])) for r in table)) if table else len(str(c))
        for c in columns
    }
    lines = ["  ".join(str(c).rjust(widths[c]) for c in columns)]
    lines += [
        "  ".join(str(r[c]).rjust(widths[c]) for c in columns) for r in table
    ]
    return "\n".join(lines)


def render_table(rows: Sequence[tuple[str, Outputs]], title: str = "") -> str:
    """Render a text table. Raises if any row would print a headline field bare.

    The conditions block is printed under the table rather than repeated on
    every line, but it is printed *unconditionally* - a table whose rows differ
    in their conditions gets one condition line per row.
    """
    table = results_table(rows)
    cond_cols = [f"cond_{k}" for k in CONDITION_KEYS]
    shown = [c for c in _columns(table) if c not in cond_cols and c != "binding_guards"]
    if HEADLINE_FIELDS & set(shown) and not cond_cols:
        raise ModelError("headline fields present with no conditions block")

    out: list[str] = []
    if title:
        out += [title, "=" * len(title)]
    out.append(_render_grid(table, shown))
    out.append("")
    out.append("Conditions (every row above is conditional on these):")
    seen: set[tuple[object, ...]] = set()
    for r in table:
        key = tuple(r[c] for c in cond_cols)
        if key in seen:
            continue
        seen.add(key)
        bits = ", ".join(f"{k}={r[f'cond_{k}']}" for k in CONDITION_KEYS)
        out.append(f"  [{r['scenario']}] {bits}")
    guards = [
        g
        for r in table
        for g in str(r["binding_guards"]).split(" | ")
        if g != "none"
    ]
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


def write_csv(path: str, rows: Iterable[tuple[str, Outputs]]) -> Table:
    """Write ``python_results.csv`` in the schema the MATLAB diff expects."""
    table = results_table(rows)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_columns(table))
        writer.writeheader()
        writer.writerows(table)
    return table


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
        table = write_csv(args.csv, [(r.label, o) for r, o in pairs])
        print(f"\nwrote {args.csv} ({len(table)} rows)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
