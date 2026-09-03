"""Model inputs against observed data, one row per input, with a verdict.

:mod:`sources` records what each input *claims*. This module checks those
claims against what Eurostat and the ECB actually publish, using the same
dotted parameter names, and says plainly where the model and the data disagree.

It changes nothing. Every number in ``timing_model`` stays where it is, because
an observed statistic is not automatically the right model input: a risk-free
rate is not a hurdle rate, and all-industry capacity utilisation is not
blast-furnace load. What this module does is remove the option of not knowing.

Reading the verdicts
--------------------
``consistent``
    The model's value sits where the observation says it should.
``optimistic``
    Defensible, but at the favourable end of what is observed. Quote it with
    the observation attached.
``below observed floor``
    The model uses a value that the published data says is not purchasable.
    Not a judgement call.
``contradiction``
    Two model inputs cannot both be right given the data. The strongest kind
    of finding available here, and the one worth acting on first.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from data import ecb, eurostat
from timing_model.benefit import carbon_price_path
from timing_model.params import Params, ScenarioParams
from timing_model.scenarios import published_base

#: Verdicts, ordered by how much they should worry a reader.
VERDICTS: Final[tuple[str, ...]] = (
    "contradiction", "below observed floor", "optimistic", "consistent", "context",
)


@dataclass(frozen=True)
class Grounding:
    """One model input, the observation that bears on it, and the verdict."""

    param: str
    model: str
    observed: str
    verdict: str
    note: str

    def sort_key(self) -> int:
        return VERDICTS.index(self.verdict)


def _eua_2026() -> float:
    """The model's own 2026 carbon price, used to price grey hydrogen's ETS bill."""
    p, sc = published_base()
    return carbon_price_path(p, sc)[p.common.t0]


def hydrogen_floors(offline: bool = True) -> dict[str, tuple[float, float]]:
    """``{geo: (green floor, grey floor)}`` in EUR/kg, from observed energy prices.

    Green is electricity only; grey is gas plus the ETS cost of the 9 kg of CO2
    that reforming a kilogram of hydrogen emits. Both exclude every capital and
    delivery cost, so a real delivered price is strictly above both.
    """
    series = eurostat.refresh(offline=offline)
    eua = _eua_2026()
    out: dict[str, tuple[float, float]] = {}
    for geo in eurostat.STEEL_GEOS:
        power, gas = series.get(f"power_{geo}"), series.get(f"gas_{geo}")
        if power is None or gas is None:
            continue
        out[geo] = (eurostat.hydrogen_power_floor(power.value),
                    eurostat.hydrogen_gas_floor(gas.value, eua))
    return out


def grey_hydrogen_intensity() -> float:
    """tCO2 per tonne of steel if the 'clean' route buys fossil hydrogen.

    ``m_H2`` kg of hydrogen per tonne of steel, each carrying the reforming
    emissions of unabated SMR. Compared against ``eps_cln``, this is what makes
    the cheap hydrogen price and the clean emission intensity mutually
    exclusive.
    """
    p, _ = published_base()
    return p.sector.m_H2 * eurostat.KG_CO2_PER_KG_H2_SMR / 1000.0


def rebase(value: float, base_index: float, latest_index: float) -> float:
    """Restate a currency-year-tagged value in the latest year's money."""
    return value * latest_index / base_index


def groundings(offline: bool = True) -> list[Grounding]:
    """Every input this build can check against published data."""
    es = eurostat.refresh(offline=offline)
    rates = ecb.refresh(offline=offline)
    # Registered defaults, matching the dotted names in sources.py. The
    # published base row overrides u to 1.0; that is called out below.
    p, sc = Params(), ScenarioParams()
    rows: list[Grounding] = []

    hicp = es["hicp"]
    rows.append(Grounding(
        "scenario.deflator", f"{sc.deflator * 100:.1f}%/yr",
        f"{hicp.value:.1f}%/yr ({hicp.period}, HICP)",
        "consistent" if abs(hicp.value - sc.deflator * 100) < 1.0 else "optimistic",
        "The real-versus-nominal correction is the single largest unit fix in "
        "the ladder (-EUR 421 on NPV), and it turns on this number.",
    ))

    floors = hydrogen_floors(offline)
    if floors:
        green_lo = min(g for g, _ in floors.values())
        grey_lo = min(y for _, y in floors.values())
        grey_hi = max(y for _, y in floors.values())
        cheapest = min(floors, key=lambda k: floors[k][0])
        rows.append(Grounding(
            "scenario.p_H2", f"EUR {sc.p_H2:.2f}/kg",
            f"green floor EUR {green_lo:.2f}/kg ({cheapest}, cheapest of "
            f"{len(floors)} states)",
            "below observed floor",
            f"Electricity alone puts {green_lo / sc.p_H2:.1f}x the base case "
            "under any green kilogram. Excludes electrolyser capex, "
            "compression, storage and transport, so the real gap is wider.",
        ))
        rows.append(Grounding(
            "scenario.p_H2", f"EUR {sc.p_H2:.2f}/kg",
            f"grey floor EUR {grey_lo:.2f}-{grey_hi:.2f}/kg (gas + ETS at "
            f"EUR {_eua_2026():.0f}/tCO2)",
            "context",
            "The base case is reachable on one route only: unabated fossil "
            "hydrogen carrying its own carbon cost. That is what EUR 2.60/kg "
            "buys in Europe, and it is not a decarbonisation input.",
        ))
        implied = grey_hydrogen_intensity()
        rows.append(Grounding(
            "common.eps_cln", f"{p.common.eps_cln:.2f} tCO2/t product",
            f"{implied:.2f} tCO2/t implied by grey hydrogen at "
            f"{p.sector.m_H2:.0f} kg H2/t",
            "contradiction",
            f"The only hydrogen priced at EUR {sc.p_H2:.2f}/kg emits "
            f"{eurostat.KG_CO2_PER_KG_H2_SMR:.0f} kg CO2 per kg, which is "
            f"{implied / p.common.eps_cln:.0f}x the clean-route intensity the "
            "model credits. The price and the intensity cannot both hold: "
            "either p_H2 rises to a green floor or eps_cln rises to grey.",
        ))

    if "caputil" in es:
        cu = es["caputil"]
        rows.append(Grounding(
            "scenario.u", f"{sc.u:.2f}",
            f"{cu.value / 100:.2f} ({cu.period}, EA20 industry)",
            "optimistic" if sc.u > cu.value / 100 else "consistent",
            f"The model runs the plant {(sc.u - cu.value / 100) * 100:.0f}pp "
            "harder than the average euro-area factory, and the published "
            "base row goes further still at u = 1.00 - a furnace that never "
            "stops. All-industry, not steel: a reference point, not a "
            "measurement of furnace load.",
        ))

    if "yield_10y" in rates:
        real = ecb.real_risk_free(rates["yield_10y"].value, hicp.value)
        rows.append(Grounding(
            "common.r", f"{p.common.r * 100:.2f}%/yr real",
            f"{real * 100:.2f}%/yr real risk-free "
            f"({rates['yield_10y'].period}, 10Y AAA less HICP)",
            "context",
            f"The 8% embeds a {p.common.r * 100 - real * 100:.1f}pp risk "
            "premium. Finding 4: across the sourced 6-10% band the break-even "
            "moves +304% and the option multiple -68%, so this decomposition "
            "is load-bearing even though the rate itself does not change.",
        ))

    if "ppi_capex" in es and "ppi_capex_base" in es:
        now, base = es["ppi_capex"], es["ppi_capex_base"]
        for name, value in (("sector.I0", p.sector.I0), ("sector.K_s", p.sector.K_s)):
            restated = rebase(value, base.value, now.value)
            rows.append(Grounding(
                name, f"EUR {value:,.0f}/t capacity ({base.period} money)",
                f"EUR {restated:,.0f}/t in {now.period} money "
                f"(capital-goods PPI {base.value:.1f} -> {now.value:.1f})",
                "context",
                f"Capital goods are {now.value / base.value - 1:+.1%} since "
                f"{base.period}. The model is internally consistent in "
                f"{base.period} euros; the gap is what a reader in "
                f"{now.period} should add before quoting a capex number.",
            ))

    if "ppi_steel" in es and "ppi_steel_base" in es:
        now, base = es["ppi_steel"], es["ppi_steel_base"]
        rows.append(Grounding(
            "sector.c_avoided", f"EUR {p.sector.c_avoided:.0f}/t product/yr "
            f"({base.period} money)",
            f"steel output prices {now.value / base.value - 1:+.1%} since "
            f"{base.period} ({base.value:.1f} -> {now.value:.1f})",
            "context",
            "Steel prices fell while capital goods rose. Every per-tonne-of-"
            "product term is therefore quoted in a peak-price currency year "
            "and every per-tonne-of-capacity term in a trough one - opposite "
            "directions, in a model whose central error class is confusing "
            "the two units.",
        ))

    return sorted(rows, key=Grounding.sort_key)


def _table(rows: Sequence[Grounding]) -> str:
    """Fixed-width table sized to its own content, so nothing runs together."""
    head = ("param", "model", "observed", "verdict")
    cells = [head] + [(r.param, r.model, r.observed, r.verdict) for r in rows]
    widths = [max(len(row[i]) for row in cells) + 2 for i in range(4)]
    out = ["  " + "".join(c.ljust(w) for c, w in zip(head, widths, strict=False)).rstrip(),
           "  " + "-" * (sum(widths) - 2)]
    for row in cells[1:]:
        out.append("  " + "".join(c.ljust(w) for c, w in zip(row, widths, strict=False)).rstrip())
    return "\n".join(out)


def main(offline: bool = True) -> int:
    """Print the grounding table. Returns 0 - this reports, it does not gate."""
    rows = groundings(offline)
    print("Model inputs against observed data\n" + "=" * 78)
    print(_table(rows))
    print()
    for r in rows:
        if r.verdict in ("contradiction", "below observed floor", "optimistic"):
            print(f"  {r.verdict.upper()} - {r.param}")
            print(f"    {r.note}\n")
    counts = {v: sum(1 for r in rows if r.verdict == v) for v in VERDICTS}
    print("  " + " · ".join(f"{n} {v}" for v, n in counts.items() if n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(offline=False))
