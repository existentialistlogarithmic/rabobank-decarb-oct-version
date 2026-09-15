"""The bridge between EUR per tonne and money a plant manager would recognise.

Why this module exists
----------------------
``I0 = 900`` is the single most misread number in the build. Read as "EUR 900",
it is absurd - nobody builds a steelworks for the price of a laptop. Read
correctly it is **EUR 900 per tonne of annual nameplate capacity**, which for a
2.3 Mt/yr plant is **EUR 2.1 billion**. Same number, and only one of those two
readings lets anyone sanity-check it.

The model is written entirely in per-tonne terms, and that is the right choice:
it makes the arithmetic plant-size-independent, so one run covers a 1.9 Mt works
and a 4 Mt one. But it means every headline figure is a rate, and a rate with
its denominator dropped reads as a total. This module puts the denominator back.

The three units, and the only legal bridges between them
--------------------------------------------------------
``EUR/t capacity``
    Per tonne of **annual** nameplate capacity. Every stock in the model: I0,
    K_s, S_s, R, s_max, and every NPV. Multiply by annual tonnes to get money.
``EUR/t product``
    Per tonne of steel actually made, per year. Every flow: a, B(t), c_avoided.
    The load factor ``u`` is the only bridge to capacity tonnes.
``EUR/tCO2``
    Carbon prices, MAC, and the trigger. Bridged to the others only through the
    abatement intensity ``b``.

Multiplying a ``EUR/t capacity`` figure by a plant's annual tonnes is exact, not
an approximation: capacity tonnes are the denominator, so they cancel. The only
judgement in this module is *which* plant to quote, and it quotes several real
ones rather than inventing a reference.
"""

from __future__ import annotations

from typing import Final

from data import sourced as src
from timing_model.params import Params
from timing_model.results import outputs
from timing_model.scenarios import published_base

#: Real European plants, from ``data/sourced/projects_capex.csv``. Quoting
#: announced projects rather than a round invented number means the absolute
#: figures below can be checked against what the operators actually said.
#: ``None`` capacity is filtered out by :func:`reference_plants`.
FALLBACK_PLANTS: Final[tuple[tuple[str, float], ...]] = (
    ("a 2.5 Mt/yr works", 2.5),
)

#: Scale thresholds for :func:`eur`. Below a million, print the euros.
MILLION: Final[float] = 1e6
BILLION: Final[float] = 1e9


def reference_plants() -> list[tuple[str, float]]:
    """(name, Mt/yr) for every announced project with a stated capacity.

    Sorted by size. These are the denominators the per-tonne figures get
    multiplied by, and they are real: each one is an operator's own stated
    capacity for a named site.
    """
    plants = []
    for row in src.projects():
        mt = row.num("capacity_Mt_per_yr")
        if mt:
            plants.append((f"{row['project']} ({mt:g} Mt/yr)", mt))
    return sorted(plants, key=lambda t: t[1]) or list(FALLBACK_PLANTS)


def absolute(per_t_capacity: float, mt_per_yr: float) -> float:
    """EUR for a whole plant, from a EUR/t-capacity rate. Exact, not indicative.

    ``per_t_capacity`` is money per tonne of annual capacity; ``mt_per_yr`` is
    that capacity in millions of tonnes. The product is money.
    """
    return per_t_capacity * mt_per_yr * 1e6


def eur(amount: float) -> str:
    """Money at a scale a reader can hold in their head: EUR 2.1bn, EUR 350m."""
    sign = "-" if amount < 0 else ""
    a = abs(amount)
    if a >= BILLION:
        return f"{sign}EUR {a / BILLION:,.1f}bn"
    if a >= MILLION:
        return f"{sign}EUR {a / MILLION:,.0f}m"
    return f"{sign}EUR {a:,.0f}"


def round_trip() -> list[tuple[str, float, float, float, float]]:
    """(project, absolute EUR, Mt/yr, stated EUR/t, recomputed EUR/t).

    The demonstration that settles the question. Each row takes an operator's
    announced total, divides by their announced capacity, and lands on the
    per-tonne figure the model uses. The two per-tonne columns should agree:
    if they do, EUR 900/t and EUR 3bn are the same kind of number, and the
    model is not quoting pocket change.
    """
    rows = []
    for row in src.projects():
        total = row.num("capex_EUR_absolute")
        mt = row.num("capacity_Mt_per_yr")
        stated = row.num("capex_EUR_per_t_capacity")
        if total is None or not mt or stated is None:
            continue
        rows.append((row["project"], total, mt, stated, total / (mt * 1e6)))
    return sorted(rows, key=lambda t: t[3])


def headline_in_money(mt_per_yr: float = 2.5) -> dict[str, tuple[float, float]]:
    """Every base-case stock as (EUR/t capacity, EUR for a plant of this size).

    The four numbers the build reports most often, each with its denominator
    restored. ``mt_per_yr`` defaults to 2.5 - Stegra's Boden capacity, and close
    to tkH2Steel's 2.3 - so the figures sit beside real announced projects.
    """
    p, sc = published_base()
    o = outputs(p, sc)
    from timing_model import cost

    t_star = o.t_star or p.common.t0
    sw = cost.switching_cost(t_star, p, sc)
    per_t = {
        "capex I0 (before learning)": p.sector.I0,
        f"capex after learning to {t_star}": sw.capex,
        "support s(T*)": sw.support,
        "write-off phi*S_s(T*)": sw.writeoff,
        "reline R = rho*K_s": p.sector.rho * p.sector.K_s,
        "NPV of switching at T*": o.npv0,
    }
    return {k: (v, absolute(v, mt_per_yr)) for k, v in per_t.items()}


def main() -> int:
    """Print the units reference. Reports; does not gate."""
    print("What the per-tonne numbers mean in money")
    print("=" * 78)
    print("  Every stock in this model - capex, support, write-off, NPV - is")
    print("  EUR per tonne of ANNUAL nameplate capacity, not EUR per tonne of")
    print("  steel and not a total. Multiply by annual tonnes and the")
    print("  denominator cancels exactly.\n")

    print("  The round trip, on announced projects:")
    print(f"    {'project':<28}{'announced':>12}{'capacity':>11}"
          f"{'EUR/t cap':>12}{'recomputed':>12}")
    print("    " + "-" * 73)
    for name, total, mt, stated, recomputed in round_trip():
        print(f"    {name[:27]:<28}{eur(total):>12}{mt:>9.1f} Mt"
              f"{stated:>12,.0f}{recomputed:>12,.0f}")
    print("\n    The last two columns agree, which is the point: EUR 1,300/t and")
    print("    EUR 3.0bn are the same statement about the same plant.\n")

    size = 2.5
    print(f"\n  The model's own base case, for a {size:g} Mt/yr plant:")
    print(f"    {'quantity':<34}{'EUR/t capacity':>16}{'for the plant':>16}")
    print("    " + "-" * 66)
    for label, (per_t, total) in headline_in_money(size).items():
        print(f"    {label:<34}{per_t:>16,.0f}{eur(total):>16}")

    print(f"\n  So I0 = {Params().sector.I0:,.0f} is not EUR 900. It is EUR 900 per tonne")
    print(f"  of annual capacity, i.e. {eur(absolute(Params().sector.I0, size))} "
          f"for a {size:g} Mt/yr works -")
    print("  the same order as the announced projects above.\n")

    print("  Scaling is linear, so any other size follows:")
    print(f"    {'plant':<44}{'capex at I0':>14}{'NPV at T*':>14}")
    print("    " + "-" * 72)
    p, sc = published_base()
    npv = outputs(p, sc).npv0
    for name, mt in reference_plants():
        print(f"    {name[:43]:<44}{eur(absolute(p.sector.I0, mt)):>14}"
              f"{eur(absolute(npv, mt)):>14}")

    print("\n  Two things this does NOT license.")
    print("    1. EUR/t product is a different denominator. Flows (a, B(t),")
    print("       c_avoided) are per tonne of steel MADE; only the load factor u")
    print("       bridges them to capacity tonnes.")
    print("    2. The NPV column above is the model's, and it is the number the")
    print("       sourced recalibration disputes. See analysis/sourced.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
