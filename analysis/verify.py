"""Re-derive every number in the tables from its raw source, and check the unit.

The point of this module is that it does NOT call the function that produced
the figure. A checker that re-runs ``table_capex()`` and compares the result to
``table_capex()`` proves only that Python is deterministic. So each check here
writes the arithmetic out again, from the CSV cell or the cached series value,
and compares that against what the table prints.

Every check states the unit it is working in. A number that is right in the
wrong unit is the failure mode this whole build exists to catch, so the unit is
part of the assertion rather than a comment beside it.

What a FAIL means
-----------------
Either the table is wrong, or this file is. Both are worth knowing, and the
disagreement is printed with both sides so it can be settled by reading. This
reports; it does not gate - but ``run_all.py`` counts the failures.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Final

from analysis import sourced, tables
from data import eurostat
from data import sourced as src
from timing_model import cost, option
from timing_model.params import Params, ScenarioParams
from timing_model.primitives import crf
from timing_model.results import outputs
from timing_model.scenarios import published_base

#: Slack added to a half-ULP comparison for binary floating-point noise. Not a
#: tolerance in any meaningful sense - it is about 1e-9 of the value.
FLOAT_NOISE: Final[float] = 1e-9


def half_ulp(text: str) -> float:
    """Half the last displayed digit of ``text``, in the value's own units.

    This is the right tolerance for checking a printed figure, and a plain
    relative tolerance is not. A cell showing "47" is a correct rendering of
    anything in [46.5, 47.5); one showing "EUR 2.2bn" is correct for anything
    within 0.05bn. Comparing those at a fixed 0.5% would call a correctly
    rounded number an error - which is exactly what an earlier version of this
    file did, on ten cells that were all fine.

    So the assertion is: does the printed string round-trip to the derived
    value at the precision it actually shows? That accepts correct rounding and
    still catches a number that is genuinely wrong.
    """
    t = str(text).strip().lstrip("-")
    t = t.replace("EUR", "").replace("x", "").replace("%", "").strip()
    mult = 1.0
    if t.endswith("bn"):
        mult, t = 1e9, t[:-2]
    elif t.endswith("m"):
        mult, t = 1e6, t[:-1]
    t = t.replace(",", "").strip()
    decimals = len(t.split(".")[1]) if "." in t else 0
    return 0.5 * (10.0 ** -decimals) * mult


@dataclass(frozen=True)
class Check:
    """One re-derived number: where it came from and whether it agrees."""

    table: str
    item: str
    unit: str
    text: str
    """The cell exactly as printed. Its precision sets the tolerance."""
    derived: float
    how: str

    @property
    def printed(self) -> float:
        return _money(self.text) if "EUR" in self.text else _num(self.text)

    @property
    def ok(self) -> bool:
        """True when the cell is a correct rendering of the derived value."""
        slack = half_ulp(self.text) + FLOAT_NOISE * max(abs(self.derived), 1.0)
        return abs(self.printed - self.derived) <= slack

    def render(self) -> str:
        mark = "ok  " if self.ok else "FAIL"
        return (f"  {mark} {self.table:<16}{self.item:<34}"
                f"{self.printed:>13,.3f}{self.derived:>13,.3f}  {self.unit:<22}"
                f"{self.how}")


def _num(text: str) -> float:
    """The number a table cell prints, stripped of its formatting."""
    return float(str(text).replace(",", "").replace("x", "").replace("%", "")
                 .replace("EUR", "").replace("-EUR", "-").strip())


def _money(text: str) -> float:
    """EUR from a formatted string: 'EUR 2.2bn', '-EUR 310m', 'EUR 900'."""
    t = str(text).strip()
    sign = -1.0 if t.startswith("-") else 1.0
    t = t.lstrip("-").replace("EUR", "").strip()
    mult = 1.0
    if t.endswith("bn"):
        mult, t = 1e9, t[:-2]
    elif t.endswith("m"):
        mult, t = 1e6, t[:-1]
    return sign * float(t.replace(",", "")) * mult


# --------------------------------------------------------------- T1 and T2

def check_units_table() -> Iterator[Check]:
    """T1. Each stock against a fresh model call, and its money against x2.5e6."""
    p, sc = published_base()
    o = outputs(p, sc)
    t_star = o.t_star or p.common.t0
    sw = cost.switching_cost(t_star, p, sc)
    # Re-derived here rather than read from units.headline_in_money().
    want = {
        "capex I0 (before learning)": p.sector.I0,
        f"capex after learning to {t_star}": p.sector.I0 * cost.learning(t_star, p),
        "support s(T*)": cost.support(t_star, p, sc),
        "write-off phi*S_s(T*)": p.sector.phi * cost.residual_value(t_star, p),
        "reline R = rho*K_s": p.sector.rho * p.sector.K_s,
        "NPV of switching at T*": o.npv0,
    }
    for label, value, absolute, unit in tables.table_npv_units().rows:
        if unit != "EUR/t capacity":
            continue
        assert label in want, f"T1 row {label!r} has no independent derivation"
        yield Check("T1 units", label, "EUR/t capacity", value, want[label],
                    "fresh model call")
        yield Check("T1 units", f"{label} -> money", "EUR", absolute,
                    want[label] * tables.REFERENCE_MT * 1e6,
                    f"x {tables.REFERENCE_MT}e6 t/yr")
    # The two rows that must NOT be converted.
    rows = {r[0]: r for r in tables.table_npv_units().rows}
    yield Check("T1 units", "trigger stays a price", "EUR/tCO2",
                rows["trigger p*'"][1], o.trigger, "option.trigger_price")
    yield Check("T1 units", "sw.capex matches clamp", "EUR/t capacity",
                f"{sw.capex:.6f}", p.sector.I0 * cost.learning(t_star, p),
                "I0 * L(T*)")


def check_npv_cases() -> Iterator[Check]:
    """T2. Each case re-run from its CSV inputs, not from run_case()."""
    p0 = Params()
    for row in tables.table_npv_cases().rows:
        name, i0, ph2, npv, money, trig, _t = row
        if name == "base":
            p, sc = published_base()
        else:
            csv_i0 = src.value("I0", name)
            csv_a = src.value("a", name)
            assert csv_i0 is not None and csv_a is not None, name
            yield Check("T2 NPV", f"{name}: I0 from CSV", "EUR/t capacity",
                        i0, csv_i0, "data/sourced/parameters.csv")
            # a = -(55*p_H2 - 83), so p_H2 = (83 - a)/55.
            yield Check("T2 NPV", f"{name}: p_H2 inverts a", "EUR/kg",
                        ph2, (83.0 - csv_a) / 55.0, "(83 - a)/55")
            p = p0.with_sector(I0=csv_i0)
            sc = ScenarioParams(u=1.0, p_H2=(83.0 - csv_a) / 55.0)
        o = outputs(p, sc)
        yield Check("T2 NPV", f"{name}: NPV", "EUR/t capacity", npv,
                    o.npv0, "outputs() on CSV inputs")
        yield Check("T2 NPV", f"{name}: NPV in money", "EUR", money,
                    o.npv0 * tables.REFERENCE_MT * 1e6,
                    f"x {tables.REFERENCE_MT}e6 t/yr")
        s_s = cost.residual_value(p.common.t0, p)
        yield Check("T2 NPV", f"{name}: trigger", "EUR/tCO2", trig,
                    option.trigger_price(p, sc, s_s), "p_M' * beta/(beta-1)")


# ------------------------------------------------------------------ T3, T4

def check_capex() -> Iterator[Check]:
    """T3. Every per-tonne figure against the announced total over capacity."""
    by_project = {r["project"]: r for r in src.projects()}
    for row in tables.table_capex().rows:
        name = str(row[0])
        if name.startswith("--"):
            yield Check("T3 capex", "model I0", "EUR/t capacity", row[3],
                        Params().sector.I0, "params.sector.I0")
            continue
        r = by_project[name]
        total, mt = r.num("capex_EUR_absolute"), r.num("capacity_Mt_per_yr")
        assert total and mt
        yield Check("T3 capex", f"{name[:30]}: announced", "EUR",
                    row[1], total, "CSV capex_EUR_absolute")
        yield Check("T3 capex", f"{name[:30]}: per tonne", "EUR/t capacity",
                    row[3], total / (mt * 1e6), "announced / capacity")


def check_opex() -> Iterator[Check]:
    """T4. Each computed line re-derived from the cached series and the physics."""
    s = eurostat.refresh(offline=True)
    de, se = s["power_DE"].value, s["gas_DE"].value and s["power_SE"].value
    want = {
        "bought, at EUR 5.00/kg": (55.0 * 5.00, "55 kg/t x 5.00 EUR/kg"),
        "bought, at the base 2.60": (55.0 * 2.60, "55 kg/t x 2.60 EUR/kg"),
        "OR made on site, DE power": (55.0 * eurostat.KWH_PER_KG_H2 * de,
                                      "55 kg/t x 55 kWh/kg x power_DE"),
        "EAF electricity, DE": (650.0 * de, "650 kWh/t x power_DE"),
        "EAF electricity, SE": (650.0 * se, "650 kWh/t x power_SE"),
        "avoided BF-route costs": (-83.0, "c_avoided, an assumption"),
    }
    for row in tables.table_opex().rows:
        label = str(row[0]).strip()
        if label not in want:
            continue
        derived, how = want[label]
        yield Check("T4 opex", label[:32], "EUR/t product/yr", row[3], derived, how)


# ------------------------------------------------------------------ T5, T7

def check_energy() -> Iterator[Check]:
    """T5. Both prices against the cache, and both hydrogen floors re-derived."""
    s = eurostat.refresh(offline=True)
    for state, power, gas, ratio, green, grey in tables.table_power_vs_gas().rows:
        p_obs, g_obs = s[f"power_{state}"].value, s[f"gas_{state}"].value
        yield Check("T5 energy", f"{state}: electricity", "EUR/kWh",
                    power, p_obs, "eurostat cache power_*")
        yield Check("T5 energy", f"{state}: gas", "EUR/kWh", gas, g_obs,
                    "eurostat cache gas_*")
        yield Check("T5 energy", f"{state}: ratio", "dimensionless",
                    ratio, p_obs / g_obs, "power / gas")
        yield Check("T5 energy", f"{state}: green floor", "EUR/kg",
                    green, p_obs * eurostat.KWH_PER_KG_H2, "power x 55 kWh/kg")
        yield Check("T5 energy", f"{state}: grey floor", "EUR/kg", grey,
                    g_obs * eurostat.KWH_GAS_PER_KG_H2
                    + 76.0 * eurostat.KG_CO2_PER_KG_H2_SMR / 1000.0,
                    "gas x 41.1 + 76 x 9/1000")


def check_support_shape() -> Iterator[Check]:
    """T7. eq (10) written out again: premium x b x the annuity."""
    p = Params()
    b = p.common.eps_inc - p.common.eps_cln
    annuity = sum((1.0 + p.common.r) ** -k for k in range(sourced.STREAM_YEARS))
    for premium, worth, money, ratio in tables.table_support_shape().rows:
        if str(premium).startswith("the model"):
            yield Check("T7 support", "the lump", "EUR/t capacity", worth,
                        p.policy.s_max, "policy.s_max")
            continue
        pi = _num(premium)
        derived = pi * b * annuity
        yield Check("T7 support", f"stream at {pi:.0f}", "EUR/t capacity",
                    worth, derived, "pi x b x annuity(10, 8%)")
        yield Check("T7 support", f"stream at {pi:.0f} -> money", "EUR",
                    money, derived * tables.REFERENCE_MT * 1e6,
                    f"x {tables.REFERENCE_MT}e6 t/yr")
        yield Check("T7 support", f"stream at {pi:.0f} vs lump", "dimensionless",
                    ratio, derived / p.policy.s_max, "worth / s_max")


# ------------------------------------------------------- the gate, re-derived

def check_gate() -> Iterator[Check]:
    """The nine published quantities, from the closed forms rather than validate()."""
    import math

    p, sc = published_base()
    r, mu, sig = p.common.r, p.common.mu, p.common.sigma
    b = p.common.eps_inc - p.common.eps_cln
    s_s = cost.residual_value(p.common.t0, p)
    half = 0.5 - mu / sig**2
    beta = half + math.sqrt(half * half + 2.0 * r / sig**2)
    crf25 = r / (1.0 - (1.0 + r) ** -25)
    pm = (p.sector.I0 + 60.0 / r) * (r - mu) / b
    pm_prime = (p.sector.I0 + p.sector.phi * s_s + 60.0 / r) * (r - mu) / b
    for item, printed, derived, unit, how in (
        ("CRF(25, 8%)", crf(25.0, r), crf25, "1/yr", "r / (1-(1+r)^-25)"),
        ("beta", option.beta(p, sc), beta, "dimensionless", "GBM positive root"),
        ("multiple", option.option_multiple(p, sc), beta / (beta - 1.0),
         "dimensionless", "beta/(beta-1)"),
        ("p_M", option.break_even_price(p, sc, 0.0), pm, "EUR/tCO2",
         "(I0 - a/r)(r-mu)/b"),
        ("p_M'", option.break_even_price(p, sc, s_s), pm_prime, "EUR/tCO2",
         "(I0 + phi*S_s - a/r)(r-mu)/b"),
        ("trigger p*'", option.trigger_price(p, sc, s_s),
         pm_prime * beta / (beta - 1.0), "EUR/tCO2", "p_M' x multiple"),
        ("S_s(2026)", s_s, p.sector.K_s * (p.sector.L_s - p.sector.age0)
         / p.sector.L_s, "EUR/t capacity", "K_s (L_s - age)/L_s"),
    ):
        yield Check("gate", item, unit, f"{printed:.6f}", derived, how)


def all_checks() -> list[Check]:
    """Every re-derivation, in table order."""
    return [
        *check_gate(), *check_units_table(), *check_npv_cases(),
        *check_capex(), *check_opex(), *check_energy(), *check_support_shape(),
    ]


def main() -> int:
    """Print every check. Returns the number that failed."""
    checks = all_checks()
    bad = [c for c in checks if not c.ok]
    print("Every number re-derived from its raw source")
    print("=" * 78)
    print("  Each row below was computed a second time, from the CSV cell or the")
    print("  cached series rather than from the function that prints it. The unit")
    print("  is part of the check, not a note beside it.\n")
    print(f"  {'':5}{'table':<16}{'quantity':<34}{'printed':>13}{'derived':>13}"
          f"  {'unit':<22}how")
    print("  " + "-" * 118)
    for c in checks:
        print(c.render())
    print(f"\n  {len(checks) - len(bad)}/{len(checks)} re-derive exactly.")
    if bad:
        print("\n  DISAGREEMENTS - either the table is wrong or this file is:")
        for c in bad:
            print(f"    {c.table} {c.item}: printed {c.printed:,.4f}, "
                  f"derived {c.derived:,.4f} ({c.unit}) via {c.how}")
    return len(bad)


if __name__ == "__main__":
    raise SystemExit(main())
