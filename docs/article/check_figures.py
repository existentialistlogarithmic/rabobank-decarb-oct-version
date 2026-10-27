"""Cross-check the Draft 3 figures against the model run and their sources.

Every number a chart prints (end labels, bar labels, reference lines, counts in
titles) is recomputed here from the same JSON the charts are drawn from, and
compared with the value the article text quotes. Figure 1 is checked against
the project figures as published (the sources are listed in make_figures.py).

    python -c "from analysis import plant_case as pc; pc.export('plant_case.json')"
    python docs/article/check_figures.py plant_case.json

Exits non-zero on the first mismatch; prints one line per check otherwise.
"""

import json
import sys

FAILS = []


def check(name, got, want, tol=0.0):
    ok = abs(got - want) <= tol if isinstance(want, (int, float)) else got == want
    print(f"{'ok ' if ok else 'BAD'}  {name}: {got!r} (article: {want!r})")
    if not ok:
        FAILS.append(name)


def at(series, year):
    return series[str(year)]


def main(path):
    d = json.load(open(path, encoding="utf-8"))
    central = "Central (RaboResearch carbon price foresight)"
    high, stall = "Pre-reform outlook", "Price stall"

    # Figure 1 - capex and support, as published (EUR bn)
    sys.path.insert(0, "docs/article")
    from make_figures import PROJECTS
    published = {"thyssenkrupp": (3.0, 2.0), "Salzgitter": (2.7, 1.322), "Stegra": (6.5, 0.515),
                 "ArcelorMittal": (2.5, 1.3), "Reference": (3.0, 0.5)}
    for label, capex, support, _status in PROJECTS:
        key = label.split("\n")[0].split()[0]
        check(f"fig1 {key} capex", capex, published[key][0])
        check(f"fig1 {key} support", support, published[key][1])
    per_t = {"thyssenkrupp": 3.0e9 / 2.5e6, "Salzgitter": 2.7e9 / 1.9e6, "Stegra": 6.5e9 / 2.5e6}
    check("table1 capex/t at existing sites, low (EUR/t)", round(per_t["thyssenkrupp"], -2), 1200)
    check("table1 capex/t at existing sites, high (EUR/t)", round(per_t["Salzgitter"], -2), 1400)
    check("table1 greenfield capex/t (EUR/t)", round(per_t["Stegra"], -2), 2600)

    # Figure 2 - share paid, current law (Directive 2023/959) and the proposal
    law = {2026: 2.5, 2027: 5, 2028: 10, 2029: 22.5, 2030: 48.5, 2031: 61, 2032: 73.5, 2033: 86,
           2034: 100}
    for y, v in law.items():
        check(f"fig2 law {y} (% paid)", round(100 * at(d["allocation_paid"]["law2023"], y), 1), v)
    for y in range(2028, 2038):
        f_law = 1 - at(d["allocation_paid"]["law2023"], y)
        expect = 1 - round(f_law + 0.15 * (1 - f_law), 3)
        check(f"fig2 proposal {y} (15% of phased-out restored)",
              round(at(d["allocation_paid"]["com2026"], y), 2), round(expect, 2), tol=0.006)
    check("fig2 proposal 2038 (% paid)", round(100 * at(d["allocation_paid"]["com2026"], 2038)), 100)

    # Figure 3 - cash bill and carbon value, EUR m a year
    check("fig3 label 2026 cash bill", round(at(d["bills"][central], 2026)), 7)
    check("fig3 label 2026 carbon value", round(at(d["carbon_value"][central], 2026)), 266)
    check("text bill 2030 central (about)", round(at(d["bills"][central], 2030), -1), 150)
    check("text bill 2035 central (about)", round(at(d["bills"][central], 2035), -1), 360)
    check("text bill 2035 pre-reform (about)", round(at(d["bills"][high], 2035), -1), 540)
    check("text carbon value 2035 central (about)", round(at(d["carbon_value"][central], 2035), -1), 420)
    for name, want in ((high, 837), (central, 647), (stall, 298)):
        check(f"fig3 end label 2050 {name}", round(at(d["bills"][name], 2050)), want)

    # Figure 4 - value bridge, EUR bn, FID 2029, central
    w = d["waterfall"]
    for k, want in (("carbon value avoided", 2.8), ("extra operating cost", -1.0), ("capex", -2.1),
                    ("capex support", 0.4), ("reline avoided", 0.2)):
        check(f"fig4 {k}", round(w[k] / 1000, 1), want)
    check("fig4 NPV", round(w["NPV"] / 1000, 2), 0.35)
    check("fig4 bars sum to NPV", round(sum(v for k, v in w.items() if k != "NPV"), 6),
          round(w["NPV"], 6))

    # Figure 5 - NPV by FID year; the value of waiting in the viable scenarios
    cur = d["curves"]
    check("fig5 central best year", max(cur[central], key=lambda k: cur[central][k]), "2029")
    check("fig5 pre-reform best year", max(cur[high], key=lambda k: cur[high][k]), "2028")
    check("fig5 stall never positive", max(cur[stall].values()) < 0, True)
    viable = [r for r in d["sweep_marginal"] if r["t_star"] is not None]
    check("fig5 viable scenarios (title, caption, summary)", len(viable), 23)
    check("fig5 best years of viable scenarios", sorted({r["t_star"] for r in viable}),
          [2028, 2029, 2030, 2031])
    mv = {int(T): cur[central][str(int(T) + 1)] - v for T, v in cur[central].items()
          if str(int(T) + 1) in cur[central]}
    check("text waiting 2027->2028 (EUR m, about)", round(mv[2027], -1), 310)
    check("text drop 2034->2035 (EUR m, about)", round(mv[2034], -1), -280)
    check("text within EUR 20m of peak, 2028-2031",
          max(cur[central].values()) - min(cur[central][str(T)] for T in range(2028, 2032)) < 20, True)

    # Figure 6 - price paths, break-even and trigger (2026 euros)
    for name, key, want in ((high, "high", 239), (central, "central", 185), (stall, "stall", 85)):
        check(f"fig6 end label 2050 {name}", round(at(d["prices_real"][key], 2050)), want)
    check("fig6 break-even (FID 2029)", round(d["break_even_2029"]), 121)
    check("fig6 trigger at 20% volatility", round(d["constant_trigger_2029"]["0.2"]), 153)
    check("text trigger at 10% / 45%", (round(d["constant_trigger_2029"]["0.1"]),
                                        round(d["constant_trigger_2029"]["0.45"])), (133, 220))
    check("table2 pre-reform 2030/2035/2050",
          tuple(round(at(d["prices_real"]["high"], y)) for y in (2030, 2035, 2050)), (119, 155, 239))
    check("table2 central 2030/2035/2050",
          tuple(round(at(d["prices_real"]["central"], y)) for y in (2030, 2035, 2050)), (103, 120, 185))

    # Figure 7 - one change at a time, EUR bn and best FID year
    want7 = {"Hydrogen +EUR 1/kg": (-0.70, None), "Carbon price path -20%": (-0.50, None),
             "Capex +20%": (-0.38, None), "No capex support": (-0.35, 2033),
             "Cost of capital 10%": (-0.29, 2031), "Reline EUR 150m, not 525m": (-0.15, 2029),
             "Free allocation lost on switching": (-0.11, 2031), "Build one year longer": (-0.06, 2028)}
    for label, _group, dv, _t0, t1 in d["one_at_a_time"]:
        check(f"fig7 {label}", (round(dv / 1000, 2), t1), want7[label])

    # Table 3 - carbon CfD
    cc = d["ccfd"]
    check("table3 110: NPV, commit 2028, never, net payment",
          (round(cc["110.0"]["npv_star"]), round(100 * cc["110.0"]["commit_2028"]),
           round(100 * cc["110.0"]["never"]), round(cc["110.0"]["net_payment"], -1)),
          (-55, 27, 69, -450))
    check("table3 120", (round(cc["120.0"]["npv_star"], -1), round(100 * cc["120.0"]["commit_2028"]),
                         round(100 * cc["120.0"]["never"]), round(cc["120.0"]["net_payment"], -1)),
          (150, 91, 7, -200))
    check("table3 130", (round(cc["130.0"]["npv_star"], -1), round(100 * cc["130.0"]["commit_2028"]),
                         round(100 * cc["130.0"]["never"]), round(cc["130.0"]["net_payment"])),
          (350, 100, 0, 2))
    check("text IRR (2029, central)", round(100 * d["irr_central_2029"]), 10)

    print(f"\n{len(FAILS)} mismatches")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
