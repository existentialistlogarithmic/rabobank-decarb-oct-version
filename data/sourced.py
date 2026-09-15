"""The recalibration package's sourced parameters, read off committed CSVs.

A September 2026 research pass went back to primary and near-primary documents
for every input the published base case assumes, and returned six CSVs. They
live in ``data/sourced/`` and this module reads them. Like the rest of
``data/``, it knows nothing about the model: it returns rows, and
:mod:`analysis.sourced` decides what they mean.

Why this is a separate layer from :mod:`reporting.sources`
----------------------------------------------------------
The provenance register in ``reporting/sources.py`` records what the *running
model* asserts and audits that the citation still equals the value in use.
These CSVs are something else: a set of *candidate* values the model does not
currently run on, carried so the published case and the sourced case can be put
side by side. Folding them into the register would claim the model uses them.

The link problem, stated once
-----------------------------
Almost every row carries ``url = NOT_CAPTURED``: the source is named and the
figure is attributed to it, but the working link was not captured in the
research pass. In this project's status vocabulary that is ``unverified``, not
``sourced`` - the distinction the whole register exists to preserve. Anything
built on these rows has to say so, which is why :func:`link_coverage` exists
and why :mod:`analysis.sourced` prints it before any result.
"""

from __future__ import annotations

import csv
import pathlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Final

DIR: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parent / "sourced"

#: The marker the research pass used for a source it named but did not link.
NOT_CAPTURED: Final[str] = "NOT_CAPTURED"


@dataclass(frozen=True)
class Row:
    """One CSV row, with the two fields every table shares.

    ``fields`` keeps the whole row so a caller can reach a column this class
    does not name, without a second read of the file.
    """

    source_id: str
    url: str
    fields: dict[str, str]

    def __getitem__(self, key: str) -> str:
        return self.fields[key]

    def get(self, key: str, default: str = "") -> str:
        return self.fields.get(key, default)

    @property
    def linked(self) -> bool:
        """True when the research pass actually captured a working URL."""
        return bool(self.url) and self.url != NOT_CAPTURED

    def num(self, key: str) -> float | None:
        """A numeric column, or None where the cell is blank or a marker."""
        raw = self.fields.get(key, "").strip()
        if not raw or raw.upper() in {NOT_CAPTURED, "PENDING", "NOT_DISCLOSED"}:
            return None
        try:
            return float(raw)
        except ValueError:
            return None


def read(table: str) -> list[Row]:
    """Rows of ``data/sourced/<table>.csv``, in file order."""
    path = DIR / f"{table}.csv"
    with open(path, encoding="utf-8", newline="") as fh:
        return [
            Row(r.get("source_id", ""), r.get("url", ""), dict(r))
            for r in csv.DictReader(fh)
        ]


def parameters() -> list[Row]:
    """Every model symbol with its base and sourced low/central/high cases."""
    return read("parameters")


def parameter(symbol: str, case: str) -> Row | None:
    """One row of :func:`parameters`, or None if that case was not sourced."""
    for row in parameters():
        if row["symbol"] == symbol and row["case"] == case:
            return row
    return None


def value(symbol: str, case: str) -> float | None:
    """The value of one parameter case, or None if it was not sourced."""
    row = parameter(symbol, case)
    return row.num("value") if row else None


def projects() -> list[Row]:
    """Announced EU transformation projects, with capex per tonne of capacity."""
    return read("projects_capex")


def hydrogen() -> list[Row]:
    """Delivered hydrogen assessments AND auction premia - check the column.

    ``is_price_or_subsidy`` separates the two. A Hydrogen Bank clearing figure
    is a subsidy premium and must never be fed to the opex penalty as if it
    were a price; :func:`hydrogen_prices` does that filtering.
    """
    return read("hydrogen_prices")


def hydrogen_prices() -> list[Row]:
    """Only the rows that are actually prices, never the subsidy premia."""
    return [r for r in hydrogen() if r.get("is_price_or_subsidy") == "price"]


def support() -> list[Row]:
    """Subsidy instruments, with the SHAPE column that distinguishes them.

    The shape is the point: an instrument paying a stream per tonne of CO2 over
    fifteen years is not the same object as a capex lump, however similar the
    headline pot looks.
    """
    return read("support_instruments")


def carbon_prices() -> list[Row]:
    """Model paths, analyst consensus and observed EUA / CBAM prints."""
    return read("carbon_prices")


def free_allocation() -> list[Row]:
    """Both policy vintages, with the verification status of each year.

    ``f_law2023`` is enacted law (Art 10a(1a)). ``f_com2026`` from 2028 is
    marked ``com2026_RECONSTRUCTED``: a pending proposal reconstructed from the
    confirmed mechanism, not a legal annex anybody read.
    """
    return read("free_allocation")


TABLES: Final[Sequence[str]] = (
    "parameters", "projects_capex", "hydrogen_prices",
    "support_instruments", "carbon_prices", "free_allocation",
)


def all_rows() -> Iterator[tuple[str, Row]]:
    """Every row of every table, tagged with the table it came from."""
    for table in TABLES:
        for row in read(table):
            yield table, row


def link_coverage() -> tuple[int, int]:
    """(rows with a captured URL, rows in total) across every table.

    Printed before any result derived from these files. A reader who sees the
    coverage first cannot mistake a named source for a checked one.
    """
    rows = list(all_rows())
    return sum(1 for _, r in rows if r.linked), len(rows)


def main() -> int:
    """Print what was loaded and how much of it is actually linked."""
    print("Sourced parameter package (data/sourced/)")
    print("=" * 78)
    for table in TABLES:
        rows = read(table)
        linked = sum(1 for r in rows if r.linked)
        print(f"  {table:<22}{len(rows):>4} rows  {linked:>3} linked")
    got, total = link_coverage()
    print(f"\n  {got}/{total} rows carry a captured URL ({got / total:.0%}).")
    print("  The rest name their source without a link, which is 'unverified'")
    print("  in this project's vocabulary - not 'sourced'. See")
    print("  docs/research-sources.md for the tier of each, and")
    print("  docs/research-open-items.md for what could not be found at all.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
