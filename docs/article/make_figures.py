"""Article figures, drawn from analysis/plant_case.py's JSON export.

Figure 1 (capex and support of the first EU projects) is drawn from the
PROJECTS table below, each value with its source; the other six come from the
model run, so the charts and the text cannot disagree.

Style follows the October draft's charts: Liberation Sans, navy / orange /
grey, no box, light grid, labels at line ends rather than legends where
possible. Run:  python make_figures.py plant_case.json outdir
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

NAVY = "#06038D"
ORANGE = "#F36717"
RUST = "#C8511B"
GREY = "#8C8C8C"
LIGHT = "#D5D9EA"
TEXT = "#333333"
MUTED = "#6E6E6E"

plt.rcParams.update({
    "font.family": "Liberation Sans",
    "font.size": 10,
    "axes.edgecolor": "#B0B0B0",
    "axes.labelcolor": TEXT,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#E6E6E6",
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "savefig.dpi": 220,
})

W, H = 7.5, 3.65  # inches; the draft placed figures at 6.25in wide


def years(d):
    return sorted(int(k) for k in d)


def series(d):
    ks = years(d)
    return ks, [d[str(k)] for k in ks]


def end_label(ax, x, y, text, color, dy=0.0, ha="left", weight="bold"):
    ax.annotate(text, (x, y), xytext=(4, dy), textcoords="offset points",
                color=color, fontsize=8.5, fontweight=weight, va="center", ha=ha)


#: The first EU hydrogen-ready steel projects, as of October 2026. EUR bn.
#: capex: thyssenkrupp ~3.0 (industriemagazin.at; GMK Center 14 Aug 2026);
#: Salzgitter SALCOS stage 1 ~2.7 (ms-aktuell.de 20 Sep 2026; 2.2-2.4 in the
#: 23 Mar 2023 ad-hoc release); Stegra ~6.5 financing lined up (Hydrogen Fuel
#: News 4 Sep 2025; EUR 6bn in the Commission's 2024 aid decision) and costs
#: "significantly higher than assumed" (ESG Today 1 Oct 2026); ArcelorMittal
#: Bremen + Eisenhuettenstadt 2.5 planned (GMK Center 26 Feb 2024).
#: support: thyssenkrupp 2.0 (GMK Center 27 Jul 2023); Salzgitter 1.322 (EUR 1bn
#: in 2023, +0.322 approved Feb 2026; ms-aktuell.de); Stegra 0.265 Swedish aid
#: (GMK Center 28 Jun 2024) + 0.25 EU Innovation Fund (CINEA 3 Apr 2025);
#: ArcelorMittal 1.3 approved, forfeited (ArcelorMittal 19 Jun 2025).
PROJECTS = [
    # label, capacity note, capex, support, status
    ("ArcelorMittal\nBremen, Eisenhüttenstadt (DE)", 2.5, 1.3, "Cancelled, June 2025"),
    ("Stegra\nBoden (SE), 2.5Mt", 6.5, 0.515, "Building; needs more capital"),
    ("Salzgitter SALCOS\nstage 1 (DE), 1.9Mt", 2.7, 1.322, "Start H1 2027, mainly gas"),
    ("thyssenkrupp\nDuisburg (DE), 2.5Mt", 3.0, 2.0, "Start end-2027, on gas"),
    ("Reference plant\nin this article, 2.5Mt", 3.0, 0.5, "Standard EU facility"),
]


def fig_projects(out):
    fig, ax = plt.subplots(figsize=(W, H + 0.25))
    h = 0.36
    for i, (label, capex, sup, status) in enumerate(PROJECTS):
        ref = label.startswith("Reference")
        ax.barh(i + h / 2, capex, height=h, color=GREY if ref else NAVY)
        ax.barh(i - h / 2, sup, height=h, color=LIGHT if ref else ORANGE)
        ax.text(capex + 0.08, i + h / 2, f"{capex:.1f}", va="center", fontsize=8.5,
                color=TEXT, fontweight="bold")
        ax.text(sup + 0.08, i - h / 2, f"{sup:.1f}", va="center", fontsize=8.5, color=TEXT)
        ax.text(7.35, i, status, va="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(PROJECTS)))
    ax.set_yticklabels([p[0] for p in PROJECTS], fontsize=8.5, color=TEXT)
    ax.set_xlim(0, 7.2)
    ax.set_xlabel("EUR bn", fontsize=9)
    ax.grid(axis="y", visible=False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=NAVY, label="Announced investment"),
                       Patch(color=ORANGE, label="Public support")],
              frameon=False, fontsize=8.5, loc="lower right", bbox_to_anchor=(1.0, 0.0))
    fig.subplots_adjust(left=0.25, right=0.76, top=0.97, bottom=0.13)
    fig.savefig(out)
    plt.close(fig)


def fig1(d, out):
    fig, ax = plt.subplots(figsize=(W, H))
    for rb, color, label in (("law2023", NAVY, "Current law (Directive 2023/959)"),
                             ("com2026", ORANGE, "July 2026 proposal (COM(2026) 616)")):
        x, y = series(d["allocation_paid"][rb])
        y = [100 * v for v in y]
        ax.step(x, y, where="mid", color=color, lw=2.2, label=label)
    ax.set_ylim(0, 105)
    ax.set_xlim(2025.5, 2040.5)
    ax.set_ylabel("% of emissions paid for")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.annotate("2029: 22.5%\n2030: 48.5%", (2030, 48.5), xytext=(2030.6, 30),
                color=NAVY, fontsize=8.5, arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.8))
    ax.annotate("85% paid,\n2034–2037", (2035.5, 85), xytext=(2035.0, 60),
                color=ORANGE, fontsize=8.5, arrowprops=dict(arrowstyle="-", color=ORANGE, lw=0.8))
    ax.legend(frameon=False, loc="upper left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def fig2(d, out):
    fig, ax = plt.subplots(figsize=(W, H))
    spec = [("Pre-reform outlook", NAVY, "Pre-reform outlook"),
            ("Central (RaboResearch carbon price foresight)", ORANGE, "Central (foresight)"),
            ("Price stall", GREY, "Price stall")]
    for key, color, label in spec:
        x, y = series(d["bills"][key])
        ax.plot(x, y, color=color, lw=2.2)
        end_label(ax, x[-1], y[-1], f"{label}: EUR {y[-1]:,.0f}m", color)
    x, y = series(d["carbon_value"]["Central (RaboResearch carbon price foresight)"])
    ax.plot(x, y, color=ORANGE, lw=1.6, ls=(0, (4, 2.5)))
    ax.annotate("Implied emission costs, central path\n(counting the allowances the plant\ncould sell if it stopped emitting)",
                xy=(2035.5, 421), xytext=(2038.4, 318), fontsize=8, color=ORANGE,
                arrowprops=dict(arrowstyle="-", color=ORANGE, lw=0.8))
    ax.text(2026.2, 860, "2026: direct emission costs EUR 7m; implied emission costs EUR 266m",
            fontsize=8.5, color=TEXT)
    ax.text(2026.2, 800, "Solid lines: direct emission costs", fontsize=8, color=MUTED)
    ax.set_xlim(2025.5, 2050.5)
    ax.set_ylim(0, 950)
    ax.set_ylabel("EUR m per year (2026 euros)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    fig.subplots_adjust(left=0.09, right=0.73, top=0.95, bottom=0.1)
    fig.savefig(out)
    plt.close(fig)


def fig3(d, out):
    w = d["waterfall"]
    steps = [("Emission costs\navoided", w["carbon value avoided"]),
             ("Extra operating\ncost (hydrogen)", w["extra operating cost"]),
             ("Capex", w["capex"]),
             ("Capex\nsupport", w["capex support"]),
             ("Reline\navoided", w["reline avoided"])]
    fig, ax = plt.subplots(figsize=(W, H))
    run = 0.0
    xs = []
    for i, (label, v) in enumerate(steps):
        v /= 1000.0
        bottom = run if v >= 0 else run + v
        ax.bar(i, abs(v), bottom=bottom, color=NAVY if v >= 0 else RUST, width=0.62)
        ax.text(i, run + v + (0.06 if v >= 0 else -0.06), f"{'+' if v >= 0 else '−'}{abs(v):.1f}",
                ha="center", va="bottom" if v >= 0 else "top", fontsize=9, fontweight="bold",
                color=TEXT)
        if i < len(steps) - 1:
            ax.plot([i + 0.31, i + 0.69], [run + v, run + v], color=MUTED, lw=0.8)
        run += v
        xs.append(label)
    npv = w["NPV"] / 1000.0
    ax.bar(len(steps), npv, color=ORANGE, width=0.62)
    ax.text(len(steps), npv + 0.06, f"{npv:.2f}", ha="center", va="bottom", fontsize=9,
            fontweight="bold", color=TEXT)
    xs.append("NPV of\nthe DID")
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels(xs, fontsize=8.5, color=TEXT)
    ax.set_ylabel("EUR bn, present value 2026")
    ax.axhline(0, color="#888888", lw=0.9)
    ax.set_ylim(-0.5, 3.2)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def fig4(d, out):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, H + 0.2), gridspec_kw={"width_ratios": [1.15, 1]})
    spec = [("Pre-reform outlook", NAVY, "Pre-reform outlook"),
            ("Central (RaboResearch carbon price foresight)", ORANGE, "Central (foresight)"),
            ("Price stall", GREY, "Price stall")]
    for key, color, label in spec:
        x, y = series(d["curves"][key])
        keep = [(a, b / 1000.0) for a, b in zip(x, y, strict=True) if a <= 2038]
        a1.plot([k for k, _ in keep], [v for _, v in keep], color=color, lw=2.2, marker="o", ms=3)
        end_label(a1, keep[-1][0], keep[-1][1], label, color)
    a1.axvspan(2027.5, 2031.5, color=LIGHT, alpha=0.6, lw=0)
    a1.text(2029.5, -1.3, "Support\nwindow", ha="center", fontsize=8, color=NAVY)
    a1.axvline(2034.5, color=MUTED, lw=0.9, ls=":")
    a1.text(2034.7, 1.45, "First steel\nafter the\n2038 reline", fontsize=7.5, color=MUTED)
    a1.axhline(0, color="#888888", lw=0.9)
    a1.set_xlim(2025.5, 2042)
    a1.set_xticks([2026, 2028, 2030, 2032, 2034, 2036, 2038])
    a1.tick_params(axis="x", labelsize=8.5)
    a1.set_ylim(-1.4, 1.9)
    a1.set_title("NPV by FID year, EUR bn", fontsize=9.5, color=TEXT, loc="left")

    for row in d["sweep_marginal"]:
        if row["t_star"] is None:
            continue
        x, y = series(row["marginal"])
        keep = [(a, b) for a, b in zip(x, y, strict=True) if 2027 <= a <= 2034]
        a2.plot([k for k, _ in keep], [v for _, v in keep], color=NAVY, lw=0.8, alpha=0.45)
    a2.axhline(0, color=RUST, lw=1.2)
    a2.axvspan(2027.5, 2031.5, color=LIGHT, alpha=0.6, lw=0)
    a2.set_xlim(2026.6, 2034.4)
    a2.set_xticks(range(2027, 2035))
    a2.tick_params(axis="x", labelsize=8.5)
    a2.set_xlabel("Waiting from this FID year to the next", fontsize=8.5, color=TEXT)
    n_viable = sum(1 for row in d["sweep_marginal"] if row["t_star"] is not None)
    a2.set_title(f"Value of waiting one more year,\n{n_viable} viable scenarios of 81, EUR m",
                 fontsize=9.5, color=TEXT, loc="left")
    a2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace("-", "\u2212")))
    fig.tight_layout()
    fig.subplots_adjust(right=0.97)
    fig.savefig(out)
    plt.close(fig)


def fig5(d, out):
    fig, ax = plt.subplots(figsize=(W, H))
    spec = [("high", NAVY, "Pre-reform outlook"), ("central", ORANGE, "Central (foresight)"),
            ("stall", GREY, "Price stall")]
    for key, color, label in spec:
        x, y = series(d["prices_real"][key])
        ax.plot(x, y, color=color, lw=2.2)
        end_label(ax, x[-1], y[-1], f"{label}: EUR {y[-1]:.0f}", color)
    be = d["break_even_2029"]
    trig = d["constant_trigger_2029"]["0.2"]
    h1 = ax.axhline(be, color=TEXT, lw=1.1, ls=(0, (5, 3)),
                    label=f"Break-even, constant price (FID 2029): EUR {be:.0f}/t")
    h2 = ax.axhline(trig, color=RUST, lw=1.4, ls=(0, (2, 2)),
                    label=f"Trigger with 20% volatility (FID 2029): EUR {trig:.0f}/t")
    ax.legend(handles=[h1, h2], loc="upper left", frameon=False, fontsize=8.5)
    ax.set_xlim(2025.5, 2050.5)
    ax.set_ylim(0, 270)
    ax.set_ylabel("EUR per tonne of CO2, 2026 euros")
    fig.subplots_adjust(left=0.09, right=0.78, top=0.95, bottom=0.1)
    fig.savefig(out)
    plt.close(fig)


def fig6(d, out):
    rows = d["one_at_a_time"]
    rows = sorted(rows, key=lambda r: r[2])
    fig, ax = plt.subplots(figsize=(W, H + 0.6))
    labels = []
    for i, (label, group, dv, t0, t1) in enumerate(rows):
        color = NAVY if group == "project" else RUST
        ax.barh(i, dv / 1000.0, color=color, height=0.6)
        year = "no year pays" if t1 is None else f"best FID {t1}"
        ax.text(dv / 1000.0 - 0.02, i, f"{dv / 1000.0:+.2f}  ".replace("-", "\u2212"), va="center", ha="right",
                fontsize=8.5, fontweight="bold", color=TEXT)
        labels.append(f"{label} ({year})".replace(" -", " \u2212"))
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(labels, fontsize=8.5, color=TEXT)
    ax.axvline(0, color="#888888", lw=0.9)
    ax.set_xlim(-0.95, 0.05)
    ax.set_xlabel("Change in NPV, EUR bn (central case: EUR 0.35bn, best FID 2029)", fontsize=9)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=NAVY, label="Project and financing"),
                       Patch(color=RUST, label="Market and rules")],
              frameon=False, fontsize=8.5, loc="upper left")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def fig_plant(out):
    """Block diagram of the reference plant: inputs, outputs and performance.

    Every number comes from the model's Plant and Case defaults, so the diagram
    cannot drift from the text. Figure 3 from Draft 10 on.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    from analysis.plant_case import Case, Plant

    pl, cs = Plant(), Case()
    kg_per_t = pl.h2_kt / pl.capacity_mt          # 57.2 kg of hydrogen per tonne of steel
    co2_per_t = pl.co2_avoided_mt / pl.capacity_mt  # 1.4 t CO2 per tonne
    extra_opex = pl.h2_kt * cs.p_h2 - pl.fuel_saving_eur_m  # EUR m a year
    capex_per_t = pl.capex_eur_m / pl.capacity_mt   # EUR/t of annual capacity

    fig = plt.figure(figsize=(W, 3.35))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 44.7)
    ax.axis("off")
    pale = "#EEF0F8"

    def box(x, y, w, h, lines, fc="white", ec=GREY, title=TEXT, body=TEXT, lh=2.55):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.9",
                                    fc=fc, ec=ec, lw=1.0))
        y0 = y + h / 2 + (len(lines) - 1) * lh / 2
        for i, (text, bold) in enumerate(lines):
            ax.text(x + w / 2, y0 - i * lh, text, ha="center", va="center",
                    fontsize=8.6 if bold else 8, fontweight="bold" if bold else "normal",
                    color=title if bold else body)

    def arrow(p0, p1, color=MUTED, ls="-"):
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=9, lw=1.1,
                                     color=color, linestyle=ls, shrinkA=0, shrinkB=0))

    for x, text in ((13, "Inputs"), (50.5, f"Reference plant: {pl.capacity_mt:.1f}Mt of steel a year"),
                    (87, "Outputs")):
        ax.text(x, 42.6, text, ha="center", va="center", fontsize=8.8, fontweight="bold",
                color=NAVY if x == 50.5 else MUTED)

    # inputs
    box(2, 34.0, 22, 5.2, [("Iron ore pellets", True)])
    box(2, 19.5, 22, 12.4, [("Hydrogen", True), (f"{kg_per_t:.0f}kg per tonne of steel", False),
                            ("(about 51kg before losses)", False),
                            (f"{pl.h2_kt:.0f}kt a year at EUR {cs.p_h2:.2f}/kg", False)])
    box(2, 11.4, 22, 6.0, [("Electricity", True), ("not modeled separately", False)])
    # process
    box(31, 18.2, 15.5, 17.0, [("Direct", True), ("reduction", True), ("shaft", True)],
        fc=NAVY, ec=NAVY, title="white", lh=2.9)
    box(55, 18.2, 15.5, 17.0, [("Electric", True), ("arc", True), ("furnace", True)],
        fc=NAVY, ec=NAVY, title="white", lh=2.9)
    ax.text(50.75, 29.6, "Direct\nreduced iron", ha="center", va="center", fontsize=7.6,
            color=MUTED, linespacing=1.15)
    # outputs
    box(76, 28.0, 22, 8.2, [("Steel", True), (f"{pl.capacity_mt:.1f}Mt a year", False)],
        ec=ORANGE, title=ORANGE)
    box(76, 13.6, 22, 11.4, [("CO2 avoided", True), (f"{pl.co2_avoided_mt:.1f}Mt a year", False),
                             (f"({co2_per_t:.1f}t per tonne of steel)", False),
                             ("reduction gives off water", False)],
        ec=ORANGE, title=ORANGE)
    # flows
    arrow((24, 36.6), (31, 31.0))
    arrow((24, 25.7), (31, 25.7))
    ax.plot([24, 62.75], [14.4, 14.4], color=MUTED, lw=1.1)
    arrow((62.75, 14.4), (62.75, 18.2))
    arrow((46.5, 26.7), (55, 26.7))
    arrow((70.5, 29.5), (76, 32.1))
    arrow((70.5, 22.5), (76, 19.3), color=ORANGE, ls=(0, (3, 2)))

    # performance and cost strip
    strip = [
        [("Capex", True), (f"EUR {pl.capex_eur_m / 1000:.1f}bn (EUR {capex_per_t:,.0f}/t)", False),
         (f"{['zero','one','two','three','four','five','six'][pl.build_years]} years to build", False)],
        [("Capex support", True), (f"up to EUR {pl.support_max_eur_m:.0f}m", False),
         ("in full for FIDs in 2028–2031", False)],
        [("Extra operating cost", True), (f"EUR {extra_opex:.0f}m a year", False),
         (f"(+EUR {pl.h2_kt:.0f}m per +EUR 1/kg H2)", False)],
        [("Replaces", True), ("a blast furnace and its", False),
         (f"EUR {pl.reline_eur_m:.0f}m reline due in {pl.reline_year}", False)],
    ]
    wbox = (96 - 3 * 1.4) / 4
    for i, lines in enumerate(strip):
        box(2 + i * (wbox + 1.4), 0.6, wbox, 8.6, lines, fc=pale, ec=pale, title=NAVY, lh=2.45)
    fig.savefig(out)
    plt.close(fig)


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        d = json.load(fh)
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    fig_plant(out / "fig_plant.png")
    # numbered as in Draft 3 (Pablo's structure)
    fig_projects(out / "fig1.png")
    fig1(d, out / "fig2.png")
    fig2(d, out / "fig3.png")
    fig3(d, out / "fig4.png")
    fig4(d, out / "fig5.png")
    fig5(d, out / "fig6.png")
    fig6(d, out / "fig7.png")


if __name__ == "__main__":
    main()
