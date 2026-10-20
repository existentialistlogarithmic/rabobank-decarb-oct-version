"""Free allocation after the switch: the eq (4) carbon terms, checked.

The review's "IMPORTANT CHECK" asked whether a plant that has switched still
pays for, or can sell, its allowances. Under EU rules free allocation is
benchmark x historical activity level x CBAM factor - it does not follow the
plant's own emissions - and since Delegated Regulation (EU) 2024/873 the
hot-metal benchmark also covers iron made by direct reduction. So the
allocation an incumbent receives, ``A(t) = alpha(t) * eps_inc`` per tonne,
stays with the site after the switch.

Do nothing:   pays  (eps_inc - A) * p
Switch, w=1:  pays  (eps_cln - A) * p      (negative: sells the surplus)
Switch, w=0:  pays   eps_cln * p           (allocation lost on switching)

so the carbon value of switching is

    w = 1:  (eps_inc - eps_cln) * p                 = b * p
    w = 0:  (eps_inc - eps_cln) * p - A * p         = b * p - alpha * eps_inc * p

Eq (4) as coded writes ``(1 - alpha) * b * p + w * alpha * eps_inc * p``,
which is the right-hand side above plus ``alpha * eps_cln * p``: the clean
route's residual emissions are treated as covered free *and* the incumbent's
whole allocation is sold. The term is small (eps_cln = 0.1), and it is exactly
what produces the +7.8 "vintage delta with resale": with allocation tied to
activity, the July 2026 rulebook cannot change what switching is worth.

This module reports; it changes nothing in :mod:`timing_model`. The published
base still reproduces, and the gate (nine quantities, none of which use B(t))
is unaffected. Adopting the accounting is a decision for the team, because it
moves every published NPV level - towards the v11 figures, as it happens.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace

import timing_model.benefit as benefit
import timing_model.objective as objective
from timing_model.params import Params, ScenarioParams
from timing_model.primitives import abatement_intensity, effective_eps_inc, opex_penalty
from timing_model.results import outputs


def benchmark_benefit(
    t: int, p: Params, sc: ScenarioParams, commit_year: int | None = None
) -> float:
    """B(t) with allocation as benchmark x activity. EUR/t product/yr."""
    price = benefit.carbon_price_path(p, sc)[t]
    alpha = benefit.alpha_v(t, p, sc)
    gross = (
        opex_penalty(p, sc)
        + abatement_intensity(p) * price
        - (1.0 - sc.w) * alpha * effective_eps_inc(p) * price
        + benefit.support_stream_flow(t, commit_year, p, sc)
    )
    return sc.u * gross


def residual_term(t: int, p: Params, sc: ScenarioParams) -> float:
    """What eq (4) adds over the benchmark accounting: u * alpha * eps_cln * p."""
    price = benefit.carbon_price_path(p, sc)[t]
    return sc.u * benefit.alpha_v(t, p, sc) * p.common.eps_cln * price


@contextmanager
def accounting(fn: Callable[..., float]) -> Iterator[None]:
    """Temporarily route the objective through ``fn`` (both import sites)."""
    saved = (benefit.annual_benefit, objective.annual_benefit)
    benefit.annual_benefit = fn
    objective.annual_benefit = fn
    try:
        yield
    finally:
        benefit.annual_benefit, objective.annual_benefit = saved


@dataclass(frozen=True)
class Comparison:
    label: str
    published: float | None
    coded: float
    benchmark: float


def compare() -> list[Comparison]:
    """NPV(T*) as coded and under benchmark accounting, for the v11 rows."""
    p, sc = Params(), ScenarioParams(u=1.0)
    cases = [
        ("base case (law 2023/959)", None, sc),
        ("vintage: current law 2023/959", 1581.0, replace(sc, policy_vintage="law2023")),
        ("vintage: COM(2026) 616", 1588.0, replace(sc, policy_vintage="com2026")),
        ("resale off, current law", None, replace(sc, w=0.0, policy_vintage="law2023")),
        ("resale off, COM(2026) 616", None, replace(sc, w=0.0, policy_vintage="com2026")),
    ]
    out = []
    for label, published, scen in cases:
        coded = outputs(p, scen).npv0
        with accounting(benchmark_benefit):
            fixed = outputs(p, scen).npv0
        out.append(Comparison(label, published, coded, fixed))
    return out


def vintage_delta(w: float) -> tuple[float, float]:
    """(as coded, benchmark accounting): NPV(com2026) - NPV(law2023) at T*."""
    p = Params()
    law = ScenarioParams(u=1.0, w=w, policy_vintage="law2023")
    com = replace(law, policy_vintage="com2026")
    coded = outputs(p, com).npv0 - outputs(p, law).npv0
    with accounting(benchmark_benefit):
        fixed = outputs(p, com).npv0 - outputs(p, law).npv0
    return coded, fixed


def main() -> int:  # pragma: no cover - prose
    print("Free allocation after the switch: eq (4) checked\n" + "=" * 78)
    print("  eq (4) as coded adds u*alpha*eps_cln*p to the carbon value of switching.")
    print("  Allocation is benchmark x activity, so with resale the value is b*p.\n")
    print(f"  {'case':<34}{'v11':>8}{'as coded':>11}{'benchmark':>11}")
    for row in compare():
        pub = f"{row.published:,.0f}" if row.published else "-"
        print(f"  {row.label:<34}{pub:>8}{row.coded:>11,.1f}{row.benchmark:>11,.1f}")
    for w in (1.0, 0.0):
        coded, fixed = vintage_delta(w)
        print(f"\n  vintage delta (COM(2026) - law), w={w:.0f}: as coded {coded:+.2f}, "
              f"benchmark accounting {fixed:+.2f}")
    print("\n  With resale the July 2026 rulebook does not change what switching is")
    print("  worth; the +7.8 'delta' is the residual-emissions term. Without resale")
    print("  it matters a great deal, which is why the resale question is decisive.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
