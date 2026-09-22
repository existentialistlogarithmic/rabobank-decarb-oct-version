"""One registry of every figure in the build, and what each one means.

Why this module exists
----------------------
There were sixteen charts and no single place that said what any of them
showed. The captions carried a sentence each, which is enough for someone who
already knows the model and not nearly enough for anyone else, and the figures
themselves were spread across five generated pages - so "have a look at the
graphs" meant opening five files and knowing which.

This registry fixes both halves at once. It holds each figure's drawing
function next to its explanation, and two pages render from it:

``gallery.py``
    every figure, one page, organised into sections. The contact sheet.
``explained.py``
    the same figures, each followed by the full explanation. The reference.

Because both pages read the same tuple, a figure cannot appear in one and not
the other, and a figure added without an explanation fails
:func:`check_complete` rather than rendering a picture nobody can read.

The shape of an explanation
---------------------------
Six questions, always in this order, because that is the order somebody
actually asks them:

1. **What am I looking at?** The marks and the axes, with units. A reader who
   stops here should at least not misread the picture.
2. **The theory behind it.** The mechanism, in its own terms - the Bellman
   equation behind beta, the annuity behind eq (10), why a Spearman rank
   correlation rather than a Pearson one. This is the part that separates a
   caption from an explanation, and it is why the floor is 300 words: below
   that, a writer states the conclusion and skips the machinery, which leaves
   a reader unable to tell a sound figure from a plausible one.
3. **Where do the numbers come from?** The equation, the CSV, or the cached
   series - named specifically enough to go and check.
4. **How do I read it?** The procedure. Which direction is good, what the
   reference line is for, what to compare against what.
5. **What does it mean?** The conclusion the figure supports, stated plainly.
6. **What does it NOT show?** The caveat. Mandatory: a figure without a stated
   boundary gets over-read, and every figure here has a boundary.

Tables get the same six, but fill them differently - see :data:`TABLE_THEORY`.
Only the theory has to be written; a table's columns give part one, its
citation list gives part three, and its own notes give part six.

Nothing in this module computes a result. It points at the functions that do.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from reporting import plots

#: Both pages here inherit ``plots.CSS`` so the charts inside them look like
#: the charts everywhere else. But ``plots.CSS`` names its tokens ``--surface``
#: / ``--plane`` / ``--ink2`` / ``--ring``, while the prose pages were written
#: against ``results.py``'s names, and an undefined custom property does not
#: error - it silently inherits, which is how a section heading ended up
#: rendering in the body grey. So the two vocabularies are bridged explicitly,
#: and the two colours ``plots.CSS`` has no token for at all are defined here
#: for both themes rather than hard-coded into a rule.
#:
#: The same hazard applies to class names, and did: ``plots.CSS`` already uses
#: ``.band`` for an SVG shading rectangle at ``opacity:.07``, so the section
#: headings on both pages first rendered at 7% opacity - present, correct, and
#: invisible. Both pages use ``.grp`` instead. Anything new here needs a name
#: that is not already in ``plots.CSS``.

#: Words of explanation every figure and every table must carry. Three hundred
#: is not a style rule: below it an explanation states the conclusion and skips
#: the mechanism, which is exactly the failure these pages exist to fix. A
#: reader who cannot see why beta/(beta-1) is a multiple, or why a Spearman
#: rank correlation was the right statistic, cannot tell a sound figure from a
#: plausible one - and the plausible ones are the dangerous ones.
MIN_WORDS: Final[int] = 300

#: The token and class-name bridge described above.
THEME_BRIDGE: Final[str] = """
:root{--bg:var(--plane);--card:var(--surface);--line:var(--ring);
--mut:var(--ink2);--acc:#2a78d6;--warn:#b4541f}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--acc:#6ba4ec;--warn:#e08a5a}}
:root[data-theme="dark"]{--acc:#6ba4ec;--warn:#e08a5a}
"""


@dataclass(frozen=True)
class Figure:
    """One figure: how to draw it, and the five things a reader needs told."""

    key: str
    """Anchor id. Stable, so a link into either page keeps working."""
    section: str
    title: str
    """Short name for the contents list. Not the chart's own heading."""
    question: str
    """The question this figure exists to answer, in the reader's words."""
    draw: Callable[[], str]
    theory: str
    """The mechanism the figure is a picture of, in its own terms.

    Not a restatement of the caption. This is where the real-options
    machinery, the estimator, or the accounting identity behind the marks gets
    written down, because a reader who does not know why beta/(beta-1) is a
    multiple cannot tell a sound chart from a plausible one.
    """
    looking_at: str
    numbers_from: str
    how_to_read: str
    what_it_means: str
    not_shown: str

    def explanation(self) -> tuple[tuple[str, str], ...]:
        """The six parts, labelled, in the order a reader asks them."""
        return (
            ("What am I looking at", self.looking_at),
            ("The theory behind it", self.theory),
            ("Where the numbers come from", self.numbers_from),
            ("How to read it", self.how_to_read),
            ("What it means", self.what_it_means),
            ("What it does NOT show", self.not_shown),
        )

    def words(self) -> int:
        """Words of explanation this figure carries, across all six parts."""
        return sum(len(text.split()) for _label, text in self.explanation())


#: Section order, and what each group of figures is for. The order is the order
#: of the argument, not the order the charts were written: the decision first,
#: then the objections to it, then the live check, then the structure
#: underneath.
SECTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("The decision",
     "Five figures on the decision itself: what the model maximises, when the "
     "threshold is reached, what the alternative costs, and how far the answer "
     "falls once the corrections are applied one at a time."),
    ("The review comments",
     "Four figures, one per review comment that had a table but no picture. "
     "Capex against real projects, the opex lines the model leaves out, the "
     "electricity-against-gas comparison, and the subsidy's shape."),
    ("The model against the market",
     "Two figures drawn from data fetched at build time - the EU ETS auction "
     "record. Neither feeds the model. They say whether its assumptions still "
     "hold, and what the gap is worth in euros."),
    ("The business case",
     "Three figures that do the half step between the model and the way a "
     "lender reads a project: the four inputs unfolded into trajectories over "
     "time, the cash flow they add up to, and what the subsidy is worth in "
     "each possible commitment year. Everything here is already inside the "
     "model's equations - this is where it gets drawn."),
    ("The structure underneath",
     "Five figures on how the model behaves rather than what it concludes: "
     "which input moves which output, where a coefficient changes sign, and "
     "which quantities are really the same quantity."),
)


FIGURES: Final[tuple[Figure, ...]] = (
    # ------------------------------------------------------- the decision
    Figure(
        "npv-curve", "The decision", "NPV against commitment year",
        "Which year does the model actually pick, and by how much?",
        plots.chart_npv,
        "The object being maximised is not a project NPV but an INCREMENT: "
        "NPV(T) is the discounted value of switching at year T minus the value "
        "of carrying on unchanged, so the do-nothing path is the origin rather "
        "than a competitor. Each year's value is the discounted benefit stream "
        "B(t) - the carbon cost avoided by moving from 1.9 to 0.1 tCO2 per "
        "tonne, valued at the price path and net of free allocation - less the "
        "switching cost I'(T), which is capex after Wright-style learning, "
        "plus the forfeited residual book value phi*S_s(T), less any support, "
        "and less or plus the reline depending on whether the switch lands "
        "before or after it. Maximising over T is the NPV rule applied to "
        "timing rather than to a yes/no choice, and it is deliberately NOT the "
        "real-options answer: it treats the price path as known. The peak "
        "exists because two forces pull against each other - capex falls with "
        "learning and the carbon price rises, both rewarding delay, while "
        "discounting and the shrinking remaining horizon punish it. Where they "
        "balance is T*. The step at the reline year is the accounting fact "
        "that reinvestment avoided before it becomes reinvestment paid after "
        "it.",
        "Four lines, one per rung of the correction ladder. The horizontal "
        "axis is the commitment year T, from 2026 to the 2050 horizon. The "
        "vertical axis is NPV(T) in EUR per tonne of ANNUAL nameplate capacity "
        "- not per tonne of steel and not a total. Each line's peak is the "
        "year that rung would commit in.",
        "``objective.npv_curve`` evaluated at every year in the horizon, for "
        "each of the first four rungs of ``scenarios.STRESS_LADDER``. T* is "
        "the argmax over that curve, which is one of the model's four "
        "published outputs.",
        "Read across to find each peak, then read down to see what the peak is "
        "worth. The shape matters more than the level: a flat top means the "
        "year is barely determined and a year either side costs almost "
        "nothing, while a sharp peak means timing is the decision. Compare the "
        "lines vertically at a fixed year to see what one correction costs.",
        "The peak is genuinely interior - the model is not saying 'now' or "
        "'never', it is picking a year, which is the whole point of the "
        "exercise. The corrections move the level far more than they move the "
        "peak, so the published T* survives inputs that halve the value.",
        "The no-investment case. NPV(T) is an INCREMENT over carrying on as "
        "before, so the do-nothing scenario is the zero line here and its size "
        "is invisible. That is exactly what the recovery chart below is for.",
    ),
    Figure(
        "trigger", "The decision", "Price path against the trigger",
        "When does the carbon price get high enough to justify committing?",
        plots.chart_trigger,
        "This is Dixit-Pindyck rather than NPV. Under irreversibility and "
        "uncertainty, committing kills an option that has value, so the "
        "correct threshold is not the break-even price p'_M but p'_M times "
        "beta/(beta-1). Beta is the positive root of the fundamental quadratic "
        "(1/2)sigma^2*beta*(beta-1) + mu*beta - r = 0, which comes out of the "
        "Bellman equation for the value of waiting when the price follows "
        "geometric Brownian motion with drift mu and volatility sigma. Beta is "
        "always greater than one, so the multiple always exceeds one, and it "
        "rises as sigma rises and falls as r rises. At the base parameters "
        "beta is about 1.386 and the multiple about 3.59 - the price must "
        "reach roughly three and a half times break-even before committing "
        "beats waiting. The economics: an irreversible commitment is the "
        "exercise of a perpetual American call whose underlying is the carbon "
        "price, and exercising at break-even throws away the premium. The "
        "crossing year is where the assumed price path first reaches that "
        "threshold, which is the real-options counterpart of T* and usually "
        "later.",
        "One line - the carbon price path in EUR per tonne of CO2 - against a "
        "horizontal rule at the Dixit-Pindyck trigger price. The horizontal "
        "axis is the year. The crossing is where the path meets the rule.",
        "The path is ``benefit.carbon_price_path``, which interpolates the "
        "specification's published anchors (76, 86, 96, 104, 112 EUR/tCO2 for "
        "2026-2030) rather than fitting a line through them. The rule is "
        "``option.trigger_price`` = p*'_M x beta/(beta-1), the real-options "
        "threshold.",
        "Find where the line crosses the rule; that year is the crossing year, "
        "the model's fourth output. Then compare it with T* from the NPV "
        "curve: the gap between them is the option premium expressed in TIME "
        "rather than in money, and it is the single most useful number on the "
        "page for an investment committee.",
        "The trigger sits well above the break-even price, and the distance is "
        "not a rounding error - the option multiple beta/(beta-1) is about "
        "3.6, so waiting is worth roughly three and a half times the "
        "break-even gap. A rule that ignored irreversibility would commit far "
        "too early.",
        "Any uncertainty about the path itself. The path is drawn as a single "
        "deterministic line because that is how the specification publishes "
        "it; the uncertainty lives in sigma, which sets the trigger's height, "
        "not in a fan around this line.",
    ),
    Figure(
        "recovery", "The decision", "The switch against doing nothing",
        "What is the increment measured FROM, and how much of it is recovered?",
        plots.chart_recovery,
        "The accounting point the model's own framing obscures. Because "
        "NPV(T) is an increment, the do-nothing case is identically zero in "
        "every other figure - not because doing nothing is costless, but "
        "because it is the baseline the increment is measured from. That is a "
        "modelling convention, not a finding, and it systematically hides the "
        "scale of what is already being carried: an incumbent blast furnace "
        "emitting 1.9 tCO2 per tonne of steel faces a discounted carbon "
        "liability over the horizon that runs to hundreds of euros per tonne "
        "of capacity, growing as free allocation phases out under the ETS "
        "Directive and CBAM replaces it. Re-basing turns the question from "
        "'is this investment worth making' into 'how much of a bill I am "
        "already paying does it take back', which is the form an incumbent "
        "actually faces. The recovered share is NPV(T*) over that discounted "
        "liability. It is not a rate of return and must not be read as one: "
        "the denominator is a cost avoided, not capital employed.",
        "Two quantities on one axis in EUR per tonne of capacity: the "
        "do-nothing carbon bill, drawn as the cost it actually is rather than "
        "as a zero line, and the switch's NPV read against it. The trigger "
        "point is marked.",
        "``regimes.recovery``, which discounts the incumbent route's carbon "
        "bill over the horizon and puts the model's own NPV(T*) beside it.",
        "Read the do-nothing bar first - that is the exposure the plant "
        "already carries by not deciding. Then read the recovered share "
        "against it. The question the figure answers is not 'is the switch "
        "worth something' but 'how much of a bill I am paying anyway does it "
        "take back'.",
        "This is the figure that answers the standing review comment directly. "
        "Doing nothing is not free and not neutral; it is a large discounted "
        "liability, and the switch recovers a definite share of it. Framing "
        "the decision as an increment over zero hides exactly that.",
        "Any route other than the two compared. This is blast furnace against "
        "H2-DRI-EAF; scrap-based EAF, CCS retrofits and closure are not on the "
        "chart and are not in the model.",
    ),
    Figure(
        "ladder", "The decision", "The cumulative stress ladder",
        "How far does the case fall once the corrections are applied?",
        plots.chart_ladder,
        "A cumulative rather than a one-at-a-time sensitivity, and the "
        "difference matters. Moving each input alone and reporting the "
        "individual effects lets a reader mentally add them up, which is "
        "wrong whenever the model is non-linear - and this one is, because T* "
        "is re-solved at every rung. Each rung here keeps every correction "
        "above it and re-optimises, so the drop between two bars is that "
        "correction's marginal cost GIVEN the others, not its effect in "
        "isolation. The ordering is deliberate: the unarguable unit fixes "
        "come first (the load factor u multiplying the benefit stream only, "
        "and the hot-metal correction kappa), then the corrections that are "
        "defensible but contestable, then the sourced input ranges. Reading "
        "top to bottom is therefore reading from 'nobody disputes this' to "
        "'this is where the argument is'. The monotone fall is itself the "
        "finding: independent corrections, each justified separately, all "
        "point the same way, which is the signature of an optimistic base "
        "case rather than of noise.",
        "One bar per rung, in the order the corrections are applied "
        "cumulatively - each rung keeps every correction above it. The axis is "
        "NPV at that rung's own T*, in EUR per tonne of capacity.",
        "``scenarios.run_ladder`` over ``STRESS_LADDER``: the unit fixes "
        "first, then the ones that are arguable, each re-solving T* rather "
        "than holding the published year fixed.",
        "Read top to bottom as a sequence, not as independent scenarios. The "
        "drop between two adjacent bars is what that one correction costs, "
        "given everything above it has already been applied - which is not the "
        "same as that correction's effect in isolation.",
        "The case does not survive the corrections intact, and the fall is "
        "monotone: every correction points the same way. That directional "
        "consistency is the finding, more than any individual level.",
        "Rows 4-7 do not reproduce the published ladder - computed NPV -49 "
        "against a published -188. CALIBRATION.md documents each disagreement "
        "and why. Read the shape, not the absolute levels of the lower rungs.",
    ),
    Figure(
        "sigma", "The decision", "The volatility ladder",
        "How much does uncertainty alone move the threshold?",
        plots.chart_sigma,
        "Sigma is unique among the model's inputs: it moves the trigger "
        "without moving the break-even price at all. Break-even depends on "
        "capex, the abatement, the opex penalty and the discount rate; sigma "
        "appears nowhere in it. Sigma enters only through beta, the positive "
        "root of (1/2)sigma^2*beta*(beta-1) + mu*beta - r = 0, and therefore "
        "only through the multiple beta/(beta-1). So everything this figure "
        "shows is option value in the strict sense - the price of keeping the "
        "decision open, with no change to the underlying economics of "
        "switching. Higher volatility makes waiting worth more because the "
        "payoff is convex in the price: the upside of a favourable move is "
        "captured in full while the downside is capped by not committing. "
        "That is why a contract-for-difference is worth more than its cash "
        "value. A CfD does not only transfer money; by removing price "
        "variance it moves the plant down this ladder, cutting the threshold "
        "the price must reach. The rungs are four defensible regimes, not a "
        "fitted sigma(t).",
        "One bar per volatility regime, ordered by sigma: cfd (0.10), long_run "
        "(0.20), crisis (0.30), realised (0.45). The axis is the trigger price "
        "in EUR per tonne of CO2.",
        "``scenarios.sigma_ladder``, re-solving the trigger at each rung of "
        "``params.SIGMA_REGIMES``. Sigma enters through beta, the positive "
        "root of the Bellman equation, and then through the option multiple "
        "beta/(beta-1).",
        "Read the spread, not any single bar. Sigma is the only input in the "
        "model that changes the trigger WITHOUT changing the break-even price, "
        "so everything you see here is pure option value - the price of "
        "keeping the decision open.",
        "A contract-for-difference does not just subsidise; it moves the plant "
        "between rungs of this ladder by removing price variance. That is a "
        "different mechanism from a grant and it is worth more than its cash "
        "value, which is the argument this figure exists to support.",
        "Which rung is right. The ladder is four defensible points, not a "
        "fitted sigma(t). The live figure in the market section is the first "
        "evidence in the build about where on this ladder the world actually "
        "sits.",
    ),
    # ------------------------------------------------- the review comments
    Figure(
        "capex", "The review comments", "Announced capex, by outcome",
        "Is EUR 900/t of capacity a realistic number for a real project?",
        plots.chart_capex_projects,
        "The theory here is about boundaries, not about finance. A capex "
        "figure only means something with its scope attached, and announced "
        "project totals are drawn at wildly different boundaries: some include "
        "the electrolyser, some assume merchant hydrogen; some include rolling "
        "and finishing, some stop at the EAF; some are greenfield on serviced "
        "land, some are brownfield retrofits inheriting utilities and a grid "
        "connection. Dividing an announced total by an announced capacity "
        "gives EUR per tonne of ANNUAL capacity, which is the model's own I0 "
        "unit and makes projects of different sizes comparable - but only "
        "within a boundary. The outcome column carries the second piece of "
        "theory: survivorship. A cancelled project's announced cost is not "
        "evidence about what building one costs, because it was never built; "
        "it is evidence about what a firm was willing to claim before "
        "stopping. Treating the surviving projects as the population, and "
        "reading the cheap outliers for their scope rather than their price, "
        "is the whole method.",
        "One horizontal bar per announced European project, in EUR per tonne "
        "of ANNUAL capacity, coloured by outcome - under construction, "
        "confirmed, or cancelled. The dashed rule is the model's own I0.",
        "``data/sourced/projects_capex.csv``, five named projects with their "
        "announced total and announced capacity. The per-tonne figure is "
        "DERIVED as total divided by capacity rather than read from the CSV's "
        "own per-tonne column, which is rounded and disagrees with itself by "
        "up to 2%.",
        "Compare each bar against the dashed rule. Then read the outcome "
        "colour before drawing any conclusion from a bar that sits below it - "
        "the two cheap projects are a cancelled scheme and an EAF-only "
        "retrofit, which are different scopes of work rather than cheaper ways "
        "of doing the same work.",
        "Every project still being built costs at least EUR 1,300/t of "
        "capacity against the model's EUR 900. The assumption is not absurd, "
        "but it sits at the bottom of the observed range and the model's "
        "answer is sensitive to it.",
        "Comparable boundaries. Dunkirk is EAF only; tkH2Steel excludes the "
        "electrolyser; Boden includes 700-800 MW of one plus rolling. The bars "
        "are not like for like and the note under the chart says which is "
        "which.",
    ),
    Figure(
        "opex", "The review comments", "The opex lines, and the missing ones",
        "Is the operating cost actually tied to the steel industry?",
        plots.chart_opex_stack,
        "The model collapses the entire operating-cost difference between "
        "two production routes into one constant, a. Its theory: a = -(m_H2 * "
        "p_H2 - c_avoided), that is, hydrogen consumed per tonne at the "
        "hydrogen price, less the coke and pulverised coal the blast-furnace "
        "route no longer buys. Everything else is assumed to net out. That is "
        "a strong assumption and this figure is the audit of it. The lines "
        "marked 'NOT in a' are real, sourced industrial costs the "
        "specification does not carry on either side: DR-grade pellet "
        "premium, which is material because direct reduction needs higher-"
        "grade ore than a blast furnace; EAF electricity; graphite electrodes; "
        "scrap and alloys. The either/or on hydrogen is a physical identity "
        "rather than a modelling choice: 55 kg of hydrogen at roughly 55 kWh "
        "per kg is about 3,025 kWh per tonne of steel, which is the same "
        "energy the merchant price already pays for. Counting both the "
        "purchase and the on-site production double-counts one input.",
        "Cost lines in EUR per tonne of steel PRODUCT per year - a different "
        "denominator from every capex figure on this page. Lines the model's "
        "coefficient `a` actually contains are marked separately from lines it "
        "does not.",
        "The hydrogen and electricity lines are computed from the cached "
        "Eurostat prices and the model's own 55 kg H2 per tonne; the avoided "
        "blast-furnace costs are the specification's lumped constant. The "
        "sources are named line by line in T4.",
        "Read the 'in a' marks first: that is the whole of what the model's "
        "opex penalty contains. Everything marked 'NOT in a' is a real "
        "industrial cost the model does not carry. And on the hydrogen lines, "
        "pick ONE - buying hydrogen and making it on site are alternatives, "
        "not additions.",
        "The model's opex is one lumped constant driven only by the hydrogen "
        "price. That is comment 5, and it is still open: closing it needs a "
        "line-by-line stack for both routes at one consistent boundary, which "
        "the research pass looked for and did not find.",
        "A complete cost stack for either route. The bars shown are the lines "
        "that could be sourced, not the full cost of making steel by either "
        "method. Do not total them.",
    ),
    Figure(
        "power-gas", "The review comments", "Electricity against gas",
        "Is electricity cheaper than gas?",
        plots.chart_power_vs_gas,
        "Two competing hydrogen production routes set two different floors, "
        "and the comparison has to be per unit of delivered energy or it means "
        "nothing. Electrolysis consumes about 55 kWh of electricity per kg of "
        "hydrogen at realistic system efficiency - hydrogen's lower heating "
        "value is 33.3 kWh/kg, so that is roughly 60% efficient. Steam "
        "methane reforming consumes about 41.1 kWh of gas per kg at 81% "
        "process efficiency, the favourable end of the reported band, and "
        "emits about 9 kg of CO2 per kg of hydrogen, which inside the ETS "
        "carries a price. So the green floor is the power price times 55 and "
        "the grey floor is the gas price times 41.1 plus the emissions at the "
        "carbon price. Both are FLOORS in the strict sense: they are energy "
        "cost alone, with no electrolyser or reformer capex, no compression, "
        "no storage and no delivery, so any real price is strictly above "
        "whichever floor binds. That is what makes a floor an argument - it "
        "cannot be argued down.",
        "Paired bars for nine steel-producing member states, both in EUR per "
        "kWh so they sit on ONE axis: industrial electricity and industrial "
        "gas, excluding taxes and levies.",
        "Eurostat ``nrg_pc_205`` band IE (20-70 GWh/yr) for electricity and "
        "``nrg_pc_203`` band I5 for gas, both excluding taxes, read from the "
        "committed cache with their period.",
        "Compare the two bars within each state, not across states. The ratio "
        "is the answer to the question; the level differences between "
        "countries are a separate and much noisier story.",
        "No. Electricity runs roughly 2x to 4x gas per kWh in every member "
        "state without exception. That is why a green hydrogen floor sits "
        "above a grey one, and it is observed data rather than an assumption.",
        "The tax layer. These prices EXCLUDE taxes, levies, network charges "
        "and the ETS indirect-cost compensation each state pays - which is "
        "precisely what 'fiscal harmonisation' would change. The model has no "
        "tax layer at all (holes H6 and H9).",
    ),
    Figure(
        "support-shape", "The review comments", "A stream against a lump",
        "Does the SHAPE of the subsidy matter, not just its size?",
        plots.chart_support_shape,
        "Two instruments delivering the same headline generosity are not "
        "worth the same, because a lump and a stream have different shapes in "
        "time and different risk. The model nets a one-off s_max off capex at "
        "the moment of commitment. A carbon contract-for-difference instead "
        "pays a premium per tonne of CO2 abated, every year, for a contracted "
        "tenor. Equation (10) converts the second into the first's units: the "
        "premium times the abatement b = eps_inc - eps_cln, times the annuity "
        "factor sum over k of (1+r)^-k for the tenor. At an 8% discount rate a "
        "ten-year annuity is worth about 6.7 years of payments, so a EUR 40 "
        "per tCO2 premium on 1.8 tCO2 per tonne comes to roughly EUR 480 per "
        "tonne of capacity against a EUR 200 lump. Two further asymmetries are "
        "not in the arithmetic and both favour the stream: it pays only if the "
        "plant actually abates, so it is performance-linked rather than "
        "front-loaded, and it removes carbon price variance, which by the "
        "sigma argument lowers the trigger as well as raising the value.",
        "Bars showing what a CCfD-style per-tCO2 stream is worth once "
        "converted into the capex lump's own unit, EUR per tonne of ANNUAL "
        "capacity, at several premium levels. The dashed rule is the model's "
        "EUR 200/t lump.",
        "Equation (10): the premium times the abatement b = eps_inc - eps_cln, "
        "times a ten-year annuity at the model's 8% discount rate. The premium "
        "range is the mid-point band from the Commission's CCfD guidance.",
        "Read each bar against the dashed rule. The ratio in the label is how "
        "many times the model's lump that stream is worth - so a bar at 2.0x "
        "means the same policy delivered as a stream is worth twice what the "
        "model credits it with.",
        "Shape is not presentation, it is value. A stream is worth 1.3x to "
        "3.3x the lump the model nets off capex, and the German instrument "
        "runs fifteen years rather than the ten priced here, so every bar "
        "understates it.",
        "Per-company strike prices. Those were never disclosed (hole H1), so "
        "these are the mechanism's range rather than observed awards. No bar "
        "here is a contract anyone actually signed.",
    ),
    # ----------------------------------------- the model against the market
    Figure(
        "carbon-gap", "The model against the market",
        "The assumed price path against the auctions",
        "Is the carbon price the model assumes anywhere near the real one?",
        plots.chart_carbon_gap,
        "A price path is an assumption and an auction is an observation, and "
        "the figure keeps them apart on purpose. The EU ETS is a cap-and-trade "
        "system: the cap sets supply, member states auction a share of the "
        "allowances through EEX, and the clearing price is the marginal bid "
        "that exhausts the volume on offer. That is a uniform-price sealed-bid "
        "auction, so every successful bidder pays the same clearing price and "
        "revenue divided by volume must equal it exactly - which is how this "
        "build proves it is reading the right column. A single session is "
        "noisy, so the rule is the volume-weighted mean of the last twenty, "
        "weighted because national auctions are a fraction of the size of the "
        "EU-wide ones and an unweighted mean would let a small Polish session "
        "count as much as a full EU one. The observation is drawn as a "
        "threshold, not a sixth bar, because one year of spot clearing prices "
        "is not a forecast: it says where the path starts, not where it goes.",
        "One bar per published central-path anchor, 2026 to 2030, in EUR per "
        "tonne of CO2. The dashed rule is the volume-weighted mean clearing "
        "price of the last twenty EU ETS auctions.",
        "The bars are ``benefit.CENTRAL_PATH``, quoted from the v11 "
        "specification. The rule is ``data.eex``, which reads the EEX "
        "primary-market auction report - the settlement record of the auctions "
        "EEX runs for the Member States, republished the day each one clears.",
        "The observation is a RULE and not a sixth bar, deliberately: it is "
        "not a replacement for the 2026 anchor. Read which anchors fall below "
        "the line and which above; the bars below it are years the "
        "specification assumed would be cheaper than the market already is.",
        "The market is running above the 2026 anchor, which on the reference "
        "plant's 4.75 MtCO2 a year is tens of millions on the carbon bill. "
        "That makes waiting DEARER, not cheaper - it pulls the decision in.",
        "A forecast. One year of auctions is not a price path to 2050, and "
        "nothing here is fed back into the model: ``Params()`` still carries "
        "the published anchors and a test asserts it.",
    ),
    Figure(
        "pot", "The model against the market", "The subsidy pot that exists",
        "How big is the pot really, and what share would one plant take?",
        plots.chart_pot,
        "A subsidy envelope that has been announced and money that has been "
        "received are different kinds of object, and only the second has a "
        "shape you can check. Under the ETS Directive a share of allowances is "
        "auctioned rather than allocated free; the proceeds go to member "
        "states by an allocation key, with defined slices to the Innovation "
        "Fund and the Modernisation Fund. Those funds are the instruments the "
        "model's s_max is modelled on - the Innovation Fund in particular, "
        "which awards competitively against applications rather than "
        "distributing by formula. The theory this figure tests is one of "
        "scale: the model hands a single 2.5 Mt/yr plant EUR 200 per tonne of "
        "capacity, which multiplied out is EUR 500m, and the question is "
        "whether an instrument of that size can plausibly do that for one "
        "works while remaining open to every other sector in Europe. The "
        "Directive's spending clause is a non-binding target on national "
        "budgets, not an entitlement, so no bar here is money this project "
        "could draw on.",
        "One horizontal bar per recipient of EU ETS auction revenue this year, "
        "in euros actually received - member states and the two EU funds. The "
        "dashed rule is what the model hands a single reference plant.",
        "The per-auction revenue split in the EEX workbook, summed by "
        "recipient over every auction so far this year. The rule is "
        "``policy.s_max`` = EUR 200/t capacity multiplied out at 2.5 Mt/yr.",
        "Read each bar against the rule to see how many plant-sized packages "
        "that recipient's receipts would fund. Then find the Innovation Fund - "
        "that is the instrument the model's s_max is actually modelled on, and "
        "it is the only bar the comparison is strictly fair against.",
        "The pot is real and large, but the model's claim on it is not small: "
        "one works takes about a quarter of everything the Innovation Fund has "
        "collected this year, for every sector in Europe. That is a statement "
        "about priority, not just about size.",
        "Any entitlement. None of this money is earmarked for steel - the ETS "
        "Directive's spending clause is a non-binding target on national "
        "budgets. No bar here is money this project could draw on.",
    ),
    # --------------------------------------------------- the business case
    Figure(
        "inputs-over-time", "The business case",
        "The four inputs over time",
        "What do capex, opex, subsidies and CO2 actually look like year by year?",
        plots.chart_inputs_over_time,
        "The model's four economic inputs are all present but entangled: "
        "capex sits inside I'(T) behind a learning multiplier, the subsidy "
        "inside eq (9)'s window, the operating penalty inside the coefficient "
        "a, and the carbon term inside B(t) net of a free-allocation factor. "
        "Unfolding them means evaluating each at every year rather than only "
        "at the optimum, and applying the right denominator to each: capex and "
        "support are per tonne of ANNUAL CAPACITY, so they multiply by "
        "nameplate tonnes; the opex penalty and the carbon flow are per tonne "
        "of PRODUCT per year, so they multiply by nameplate times the load "
        "factor. Applying one blended factor to all four is precisely the unit "
        "error the build exists to prevent, so the two conversions are done "
        "separately. The sign convention is a cash flow's rather than the "
        "model's: money out is negative, which is why capex points down and "
        "the subsidy points up against it. Each panel is scaled to its own "
        "data because the quantities differ by more than an order of "
        "magnitude, and a shared axis would render the operating line "
        "invisible next to a two-billion-euro spike.",
        "Four stacked panels sharing one year axis, each with its own scale, "
        "in EUR per year for a 2.5 Mt/yr plant. Capex and subsidy are bars "
        "because they happen in single years; opex and CO2 are lines because "
        "they run continuously. Two verticals mark the commitment year and "
        "the payback year.",
        "``analysis.cashflow.trajectories``, which evaluates "
        "``cost.switching_cost``, ``cost.support``, "
        "``primitives.opex_penalty`` and the carbon half of "
        "``benefit.annual_benefit`` at every year in the horizon.",
        "Read each panel for its SHAPE, not against the others - the scales "
        "differ deliberately. Then read the two verticals across all four: "
        "everything to the left of the commitment year is zero because the "
        "model's NPV is an increment over carrying on unchanged, and the "
        "whole case is what happens to the right of it.",
        "The story a lender expects and the story the model tells are "
        "different in one specific place. Capex is a single spike rather than "
        "a construction profile, the subsidy lands with it, and the carbon "
        "line steepens because the price rises AND free allocation phases out "
        "at the same time. The second capex bar is the avoided reline.",
        "The opex shape. The line is FLAT because the model carries one "
        "constant driven only by the hydrogen price. A real plant's operating "
        "cost falls as a new asset beds in, rises as it ages and needs "
        "repair, jumps again at the switch while an unfamiliar technology is "
        "learned, then settles lower as contracts improve. None of that is "
        "here - it is hole H10 and review comment 5, open, and drawing a "
        "plausible curve would invent the numbers this build exists to stop "
        "inventing.",
    ),
    Figure(
        "cash-flow", "The business case", "The decision as a cash flow",
        "What does this look like to someone sizing debt against it?",
        plots.chart_cash_flow,
        "This is the same object as the NPV curve, re-presented in the form a "
        "lender uses, and the equivalence is exact rather than approximate: "
        "discounting this annual series at the model's own 8% real rate "
        "returns NPV(T*) to the cent, which ``analysis.verify`` checks on "
        "every build. What changes is not the arithmetic but which features "
        "are visible. An NPV is a single number that has already integrated "
        "over time, so it hides the two quantities debt is actually sized "
        "against: the trough of the cumulative curve, which is the financing "
        "requirement, and the year it crosses zero, which is the payback "
        "period. Note that the trough is deeper than the capex alone - the "
        "cumulative keeps falling for as long as the annual net stays "
        "negative, so peak exposure is a distinct number from the "
        "investment. Everything is real rather than nominal, so the payback "
        "year is in constant purchasing power and is not flattered by "
        "inflation, and the series is undiscounted: discounting is what turns "
        "it back into the NPV.",
        "Two stacked panels on a shared year axis. Above: the net annual cash "
        "flow in EUR per year, as bars. Below: the running cumulative, in "
        "EUR, as a line. Verticals mark the commitment year and the year the "
        "cumulative turns positive.",
        "``analysis.cashflow.build``, which sums the four trajectories, "
        "accumulates them, and finds the first year at or after commitment "
        "where the cumulative is non-negative.",
        "Read the trough first - that is what has to be financed. Then the "
        "crossing - that is the payback period, and many lenders have a hard "
        "limit on it well short of the asset's life. The bars above tell you "
        "how fast: tall early bars pull the crossing in, and the bars grow "
        "here because the carbon term grows.",
        "The case is financeable on this reading, and the payback period is "
        "far shorter than the asset's life - but the whole of it rests on the "
        "carbon line, which is the one input the firm does not control. The "
        "bars are small in the first years and grow: this is a project whose "
        "returns are back-loaded by policy, not by construction.",
        "Debt service, tax, working capital and the revenue side of the "
        "business. This is the INCREMENT from switching, not the plant's cash "
        "flow: steel revenue, raw materials and everything else that does not "
        "change between the two routes nets out of it by construction. A real "
        "sizing exercise starts here and adds the rest.",
    ),
    Figure(
        "subsidy-window", "The business case", "The subsidy window",
        "What is the support worth if we commit in a different year?",
        plots.chart_subsidy_window,
        "Equation (9) makes support an explicit function of the commitment "
        "year, in three regimes: 0.35 of the maximum before the Investment "
        "Booster window opens, full weight through 2031, then a linear taper "
        "to nothing by 2035. That time dependence is the mechanism behind one "
        "of the model's more counter-intuitive results - the age-19 cliff in "
        "finding 3 - where committing slightly too early forfeits the whole "
        "of the Booster and the NPV falls off a step. The pre-window floor is "
        "not decoration: it represents the Innovation Fund and national aid, "
        "which exist before the Booster does, and an earlier version of this "
        "code returned zero there. That bug paid the plant to wait and "
        "overstated the value of delay, which is the single quantity the "
        "model exists to measure. This figure is the opportunity map rather "
        "than a cash flow: it shows what each possible commitment year is "
        "worth in support alone, holding everything else aside.",
        "One panel of bars, in EUR for a 2.5 Mt/yr plant, against the "
        "commitment year rather than against calendar time. Verticals mark "
        "T*, the end of full weight, and the year support reaches zero.",
        "``analysis.cashflow.support_window``, which evaluates "
        "``cost.support`` at every admissible commitment year, multiplied out "
        "at the reference plant size.",
        "Read the steps rather than the levels. The jump where the window "
        "opens is what a year's delay is worth before the decision, and the "
        "taper is what a year's delay costs after 2031. Then compare against "
        "T*: the model's chosen year sits inside the full-weight band, which "
        "is not a coincidence.",
        "Subsidy timing is a first-order term in this decision, not an "
        "administrative detail. The step at the window's opening is worth "
        "hundreds of millions to a plant of this size, which is larger than "
        "most of the input uncertainties the stress ladder tests.",
        "Whether any of this money would actually be awarded. This is a "
        "published rule applied to a hypothetical plant, not an allocation: "
        "T6 lists the instruments and their legal status, and T9 shows what "
        "the auctions have actually paid out. The Innovation Fund awards "
        "competitively against applications, so no plant is entitled to this.",
    ),
    # ------------------------------------------------ the structure underneath
    Figure(
        "levers", "The structure underneath", "Which knob moves which output",
        "If I change one input, what actually happens?",
        plots.chart_levers,
        "Whether two outputs are separately controllable is a structural "
        "question about the model, not a matter of taste, and it has a clean "
        "answer here. The break-even price p'_M depends on capex, the "
        "abatement, the opex flow and the discount rate. The option multiple "
        "beta/(beta-1) depends on sigma, mu and r. Only r appears in both. So "
        "an input that enters only the cost side moves value and leaves the "
        "threshold alone; an input that enters only the stochastic "
        "specification does the reverse; and r is the one genuine coupling. "
        "Plotting the measured percentage change in NPV against the measured "
        "percentage change in the trigger makes that algebra visible as "
        "geometry: near-orthogonality shows up as points hugging the axes. "
        "The classification is mechanical, read off the two measured changes "
        "rather than assigned from the algebra, which is what makes the figure "
        "a check on the implementation and not merely an illustration of it - "
        "a coding error that leaked sigma into the cost side would show as a "
        "point off both axes.",
        "A scatter. Horizontal axis: the percentage change in the trigger "
        "price from moving that lever. Vertical axis: the percentage change in "
        "NPV. Colour is the class - value only, threshold only, or both.",
        "``findings.lever_classes``, which perturbs each input in turn and "
        "records both outputs. The classification is mechanical, from the two "
        "measured changes, not assigned by hand.",
        "Points hugging the vertical axis move value and leave the threshold "
        "alone; points hugging the horizontal axis do the reverse. A point "
        "near the origin is a lever that does nothing. Only levers off BOTH "
        "axes trade one output against the other.",
        "The model's inputs separate cleanly into two almost disjoint groups. "
        "That is not obvious a priori and it is useful: it means an argument "
        "about value and an argument about timing can be had independently, "
        "with different inputs.",
        "Interactions. Each lever is moved on its own from the base case, so "
        "the map says nothing about what two simultaneous changes do. The "
        "stress ladder is the cumulative view.",
    ),
    Figure(
        "inversion", "The structure underneath", "Where the load factor flips sign",
        "Can running the plant harder make the case WORSE?",
        plots.chart_inversion,
        "The load factor u is the share of nameplate capacity actually "
        "produced, and Appendix A F2 requires it to multiply the benefit "
        "stream B(t) only, never the cost side I'(T) - capex is committed per "
        "tonne of capacity whether or not the capacity runs. Given that, the "
        "derivative of NPV with respect to u is the discounted sum of the "
        "per-tonne margin of the clean route over the incumbent. That margin "
        "has two parts of opposite sign: the carbon cost avoided, which is "
        "positive and fixed by the abatement and the price path, and the "
        "operating penalty a, which is negative and grows linearly with the "
        "hydrogen price at 55 kg per tonne. Below the crossing price the first "
        "dominates and running harder helps. Above it the second dominates, "
        "the derivative turns negative, and every additional tonne makes the "
        "case worse - the plant is paying more for hydrogen than the carbon it "
        "saves is worth. The crossing is where the two exactly cancel, and it "
        "sits uncomfortably close to the sourced central hydrogen price.",
        "One line: the derivative of NPV with respect to the load factor u, "
        "against the hydrogen price in EUR/kg. The axis crossing at zero is "
        "the whole subject of the chart.",
        "``findings._d_npv_du`` evaluated across the hydrogen price range, on "
        "the corrected configuration (kappa = 0.94, u = 0.85, real prices).",
        "Find where the line crosses zero - about EUR 6.15/kg. Left of it, "
        "running the plant harder helps. Right of it, the derivative is "
        "negative and running it harder hurts.",
        "Above roughly EUR 6/kg of hydrogen, higher utilisation destroys "
        "value: the clean route's operating penalty outweighs the extra "
        "abatement, so every additional tonne makes the case worse. The "
        "sourced central hydrogen price sits near that boundary, which is "
        "uncomfortable and worth knowing.",
        "Whether the plant can choose u. The chart treats utilisation as a "
        "dial; in practice it is set by order books and by the furnace, and "
        "the model has no capacity-constraint layer.",
    ),
    Figure(
        "capture", "The structure underneath", "Where the reline captures T*",
        "Does the decision year come from economics or from the furnace?",
        plots.chart_capture,
        "A blast furnace must be relined roughly every twenty years, and the "
        "reline is a large lumpy reinvestment. That creates a natural option "
        "date: switching instead of relining avoids the reinvestment, so "
        "committing at the reline is cheaper than committing a year after it "
        "by the whole reline cost. The model represents this as a term in the "
        "switching cost that changes sign at the reline year, which is what "
        "produces the step visible in the NPV curve. The theory question is "
        "when that lump stops being one consideration among several and "
        "becomes the entire answer. For a young asset the reline is far off, "
        "discounting flattens it, and T* is set by the balance of learning "
        "against the rising carbon price - genuine economics. For an old "
        "enough asset the reline dominates every other term and T* simply "
        "equals the reline year: the model is no longer choosing, it is "
        "reporting the maintenance calendar. Knowing which side of that "
        "boundary a specific plant sits on is a precondition for quoting T* "
        "for it at all.",
        "Two lines against the asset's starting age: the model's chosen "
        "commitment year T*, and the year the blast furnace is due its reline. "
        "The axis is the calendar year.",
        "``findings.reline_capture``, which re-solves the model across the "
        "whole range of starting ages and records both years at each.",
        "Follow the two lines from left to right. They converge, and past a "
        "certain age they coincide exactly. From that point the model is no "
        "longer choosing a year on economic grounds - it is reporting the "
        "reline date.",
        "For an old enough asset the timing answer is mechanical, not "
        "economic. That is a boundary on where this model is informative at "
        "all, and it should be checked before quoting T* for any specific "
        "plant.",
        "Real reline dates. The asset age is a model parameter, not a survey "
        "of the European fleet; per-plant reline calendars were not obtainable "
        "and remain an open item.",
    ),
    Figure(
        "cancellation", "The structure underneath", "Two effects that cancel",
        "Why does the discount rate barely move the trigger?",
        plots.chart_cancellation,
        "The trigger is a product of two factors that respond to the "
        "discount rate in opposite directions, and the figure is about what "
        "that does to a naive sensitivity analysis. Raising r raises the "
        "break-even price, because future benefits are discounted harder while "
        "capex is paid up front - across 6-10% the break-even moves about "
        "+304%. Raising r also lowers the option multiple, because waiting "
        "costs more when capital is dearer: beta rises with r, and "
        "beta/(beta-1) falls as beta rises, giving about -68%. Their product "
        "moves only about +29%. Indexing all three to 100 at the lowest rate "
        "is what lets quantities of completely different scale share one axis; "
        "a second y-axis would be the wrong answer and would invite reading a "
        "crossing point that has no meaning. The methodological warning is "
        "general: testing a composite output alone can certify an input as "
        "unimportant while both of its components are violently sensitive, so "
        "a sensitivity analysis should test the parts, not only the product.",
        "Three lines against the discount rate, all INDEXED to 100 at the "
        "lowest rate so they share one axis: the break-even price, the option "
        "multiple, and their product, the trigger.",
        "``findings.rate_cancellation``, re-solving across r from 6% to 10%. "
        "Indexing is what lets three quantities of wildly different scale "
        "share an axis - a second y-scale would be the wrong answer.",
        "Watch the two input lines diverge - one rises steeply, the other "
        "falls steeply - and then watch the product line stay comparatively "
        "flat. The near-cancellation is the point.",
        "Across the 6-10% band the break-even moves +304% and the option "
        "multiple -68%, and the trigger they multiply to moves only +29%. A "
        "sensitivity that tested the trigger alone would conclude the discount "
        "rate hardly matters, which would be badly wrong about the mechanism.",
        "Any reason the cancellation should hold outside this band or under a "
        "different drift. It is an arithmetic coincidence of this "
        "parameterisation, not a structural law.",
    ),
    Figure(
        "correlations", "The structure underneath", "Which outputs are one output",
        "Are the four reported outputs actually four different things?",
        plots.chart_correlations,
        "The model reports four outputs - T*, T_exp, the trigger and the "
        "crossing year - and it is tempting to read agreement among them as "
        "corroboration. This figure tests whether they are independent "
        "readings at all. Spearman rank correlation rather than Pearson, for "
        "two reasons: two of the four are years, which are ordinal and "
        "integer-valued rather than continuous, and the relationships between "
        "them are monotone but not linear, so a Pearson coefficient would "
        "understate a perfectly systematic dependence. The correlations are "
        "computed across the whole scenario grid rather than along one path, "
        "so a saturated off-diagonal cell says the two outputs carry the same "
        "information over the entire space the model is exercised on. Where "
        "that happens they are one answer with two faces, and quoting both as "
        "if they agreed independently overstates the evidence. The diverging "
        "palette with a neutral midpoint at zero is the correct encoding for a "
        "quantity with a meaningful centre and two signed directions; a "
        "sequential ramp would hide the sign.",
        "A rank-correlation heatmap over the model's outputs. Diverging blue "
        "to red with a neutral midpoint at zero - the cells are correlation "
        "coefficients, dimensionless, between -1 and +1.",
        "``findings.output_correlations``, Spearman rank correlations computed "
        "across the full scenario grid rather than on one path.",
        "Look for saturated cells away from the diagonal. A cell near +1 or -1 "
        "means those two outputs are carrying the same information, and "
        "reporting both gives a false sense of corroboration.",
        "The four outputs are not four independent readings. Some of them move "
        "together almost perfectly, which is why the build reports T*, T_exp, "
        "the trigger and the crossing year as one answer with four faces "
        "rather than four separate results.",
        "Causation, and behaviour outside the grid. Rank correlation over a "
        "scenario sweep says these move together here; it does not say one "
        "drives the other.",
    ),
)


def inline(text: str) -> str:
    """Escape ``text`` for HTML, turning ``literals`` into real code spans.

    The explanations are written in the same double-backtick convention as
    every docstring in the build, because they are read in the source as often
    as in the browser. Rendered naively that convention leaks: the page shows
    the backticks. Escaping happens first, so a literal cannot smuggle markup
    through this.
    """
    return re.sub(r"``([^`]+)``", r"<code>\1</code>", plots.esc(text))


#: What the tables half of both pages is called, and what it is for. The
#: figures answer "what does this look like"; the tables answer "what is the
#: number, and on whose authority" - which is why every one of them carries its
#: sources and the figures mostly do not.
TABLE_SECTION: Final[tuple[str, str]] = (
    "The tables",
    "Ten tables, one per review comment plus the live market pair. Where a "
    "figure shows a shape, a table gives the figure and names the document it "
    "came from. Every column states its unit in its own header, and a cell the "
    "research pass looked for and did not find is left marked MISSING rather "
    "than filled with something plausible.",
)


def table_anchor(name: str) -> str:
    """A table handle as a URL anchor. Matches the one ``results.html`` uses.

    Shared so a link into any of the three pages lands in the same place -
    ``results.html#T3-capex`` and ``explained.html#T3-capex`` are the same
    table, and a reader following one should not have to guess at the other.
    """
    return name.replace(" ", "-")


def by_section() -> list[tuple[str, str, list[Figure]]]:
    """Figures grouped in :data:`SECTIONS` order: (name, lede, figures)."""
    out = []
    for name, lede in SECTIONS:
        out.append((name, lede, [f for f in FIGURES if f.section == name]))
    return out


def check_complete() -> list[str]:
    """Problems with the registry itself. Empty means it is sound.

    Checked rather than trusted, because the failure this registry exists to
    prevent - a figure with no explanation - is invisible in the rendered page:
    it just looks like a chart somebody forgot to caption.
    """
    problems: list[str] = []
    keys = [f.key for f in FIGURES]
    if len(keys) != len(set(keys)):
        problems.append(f"duplicate figure keys: {keys}")

    known = {name for name, _ in SECTIONS}
    drawn = {f.title for f in FIGURES}
    if len(drawn) != len(FIGURES):
        problems.append("two figures share a title; the contents list would lie")

    for f in FIGURES:
        if f.section not in known:
            problems.append(f"{f.key}: section {f.section!r} is not in SECTIONS")
        if not f.question.endswith("?"):
            problems.append(f"{f.key}: the question is not a question")
        for label, text in f.explanation():
            if len(text.split()) < 12:
                problems.append(f"{f.key}: '{label}' is too thin to be an answer")
        if f.words() < MIN_WORDS:
            problems.append(
                f"{f.key}: {f.words()} words of explanation, below the "
                f"{MIN_WORDS} this build requires")

    from analysis import tables as _tbl

    for t in _tbl.all_tables():
        theory = TABLE_THEORY.get(t.name)
        if theory is None:
            problems.append(f"table {t.name!r} has no entry in TABLE_THEORY")
            continue
        # The derived halves - the column list and the notes - carry the rest
        # of a table's explanation, so the typed part needs less than a
        # figure's to clear the same total.
        prose = len(theory.split()) + sum(len(str(n).split()) for n in t.notes)
        if prose < MIN_WORDS:
            problems.append(
                f"table {t.name!r}: {prose} words of explanation, below the "
                f"{MIN_WORDS} this build requires")

    charted = {fn for fn in dir(plots) if fn.startswith("chart_")}
    registered = {f.draw.__name__ for f in FIGURES}
    for missing in sorted(charted - registered):
        problems.append(f"plots.{missing} is not in the registry")
    return problems


def figure_keys(section: str) -> Sequence[str]:
    """Anchor ids within one section, in order. Used by both pages' contents."""
    return [f.key for f in FIGURES if f.section == section]


#: The theory behind each table, keyed by its handle.
#:
#: The figures carry their theory as a field because a chart has no other place
#: to put it. A table carries most of its explanation already - its columns
#: give the shape, its citation list gives the provenance, its notes give the
#: boundary - so only this one part has to be written, and it is written here
#: rather than in ``analysis/tables.py`` because the layering forbids that
#: module from knowing anything about how it will be presented.
TABLE_THEORY: Final[dict[str, str]] = {
    "T0 status": (
        "A status table is an epistemic claim, not a project-management "
        "artefact, and the vocabulary is deliberately narrow: DONE, PARTIAL "
        "or OPEN, with nothing in between and no percentages. The reason is "
        "that effort and completion are different quantities, and a "
        "'90% done' row records the first while implying the second. A "
        "comment is DONE only when someone who disbelieved it could check it "
        "and be satisfied. It is PARTIAL when the part that could be closed "
        "with available evidence was closed and the rest was not. It is OPEN "
        "when the work needed a document that does not exist or was not "
        "obtainable - and then the blocker column names the specific hole, so "
        "the reader can see whether it is a matter of more effort or of an "
        "absent source. That distinction is the whole point. Two of the five "
        "comments here are blocked on documents the research pass looked for "
        "and did not find, and no amount of further modelling closes them; "
        "filling them with a plausible construction would convert a known gap "
        "into an unknown error, which is strictly worse. The table is "
        "therefore also a defence against a particular failure mode: a build "
        "that answers the easy comments thoroughly, goes quiet on the hard "
        "ones, and reads as complete. The blocker IDs are the load-bearing "
        "part: they point at docs/research-open-items.md, where each hole "
        "records what was searched for, where, and why the search failed, so "
        "a later reader can reopen it without repeating the work."),
    "T1 units": (
        "Dimensional analysis, applied to a model whose central error class "
        "is a confused denominator. Three units appear and only one of them "
        "converts to money for a plant. A STOCK in EUR per tonne of annual "
        "nameplate capacity multiplied by annual tonnes gives euros, exactly, "
        "because the denominator cancels - that is why EUR 900/t of capacity "
        "is EUR 2.2bn for a 2.5 Mt/yr works and not, as the number invites, a "
        "trivial sum. A FLOW in EUR per tonne of product per year has a "
        "different denominator: it scales with what the plant actually makes, "
        "which is capacity times the load factor, so it does not convert the "
        "same way and must never be added to a stock. A PRICE in EUR per "
        "tonne of CO2 has no plant-size conversion at all; it is an "
        "intensive quantity, like a temperature. The rows marked n/a are "
        "marked so on purpose rather than left blank, because a blank cell in "
        "a money column reads as zero. This is the table the whole 'why is it "
        "thousands' objection resolves to, and the resolution is that the "
        "figure was never per tonne of steel. The practical rule that falls "
        "out of this: before doing arithmetic on any two numbers in this "
        "build, check that they share a denominator. Adding a stock to a "
        "flow, or scaling a price by plant size, produces a quantity with no "
        "dimensional meaning at all - and such a number still renders "
        "perfectly well in a table, which is why the check has to be "
        "deliberate rather than visual."),
    "T2 NPV in money": (
        "The same model run on four different input sets, which is a "
        "statement about epistemic rather than stochastic uncertainty. The "
        "sigma ladder handles the second - what the answer is given that the "
        "carbon price is random. This handles the first: what the answer is "
        "given that we are not certain what the inputs are. The four cases "
        "span the published specification's values at one end and the "
        "September 2026 research pass's primary-document values at the other, "
        "with the hydrogen price doing most of the work because the operating "
        "penalty a is linear in it at 55 kg per tonne. The result is a range "
        "that crosses zero, and a range that crosses zero is a qualitatively "
        "different object from a point estimate with error bars: it means the "
        "sign of the answer is not determined by the model but by which "
        "inputs you accept. Reporting the midpoint would be the one clearly "
        "wrong summary, since the midpoint of two incompatible input sets is "
        "not a measurement of anything. The money column exists because a "
        "per-tonne figure invites the misreading T1 was built to prevent. "
        "Note also what does NOT move much across the four cases: the "
        "commitment year. The corrections change the level of the answer far "
        "more than they change its timing, which is worth knowing because "
        "timing is what the model was built to determine and value is the "
        "part it is least equipped to defend."),
    "T3 capex": (
        "Comparing announced project costs requires two corrections that are "
        "easy to skip. The first is the denominator: an absolute total means "
        "nothing without the capacity it buys, so every row is divided out to "
        "EUR per tonne of annual capacity, which is the model's own I0 unit. "
        "That figure is derived here from the two primary numbers rather than "
        "read from the source CSV's own per-tonne column, because that column "
        "is rounded to two or three significant figures and disagrees with "
        "its own absolute-over-capacity by up to 2% - Bremen states 700 "
        "against its own 714. The second correction is scope. These projects "
        "draw their boundaries in different places: one excludes the "
        "electrolyser, another includes 700-800 MW of it plus rolling, a "
        "third is an EAF-only retrofit with no direct reduction at all. A "
        "per-tonne figure makes sizes comparable; it does not make scopes "
        "comparable, and the cheap rows are cheap mostly because they bought "
        "less. Underneath both sits survivorship: a cancelled project's "
        "announced cost is evidence about what a firm was prepared to claim, "
        "not about what building one costs. The model's own I0 is included "
        "as a row rather than a footnote, so the assumption sits in the same "
        "column as the evidence and can be read against it without the "
        "reader having to hold a number in their head while scanning."),
    "T4 opex": (
        "The model compresses the entire operating-cost difference between "
        "two production routes into a single constant a = -(m_H2 * p_H2 - "
        "c_avoided): hydrogen bought per tonne at the hydrogen price, less "
        "the coke and pulverised coal the blast furnace no longer buys. "
        "Everything else is assumed to net out between the routes. This "
        "table is the audit of that assumption, and it is organised around "
        "one distinction - whether a cost line is inside a or outside it. "
        "The lines outside are not small and not obviously symmetric: the "
        "DR-grade pellet premium, which exists because direct reduction needs "
        "higher-grade ore than a blast furnace tolerates; EAF electricity, "
        "which differs by a factor of two between Germany and Sweden; "
        "graphite electrodes; scrap and alloys. The hydrogen block carries a "
        "physical identity that must not be double-counted: 55 kg per tonne "
        "at about 55 kWh per kg is roughly 3,025 kWh per tonne of steel, the "
        "same energy the merchant hydrogen price already pays for, so buying "
        "hydrogen and making it on site are alternatives and adding both "
        "counts one input twice."),
    "T5 energy": (
        "Two hydrogen production routes imply two cost floors, and the "
        "comparison is only meaningful per unit of delivered energy. "
        "Electrolysis needs about 55 kWh of electricity per kg of hydrogen at "
        "realistic system efficiency - hydrogen's lower heating value is 33.3 "
        "kWh/kg, so that is roughly 60%. Steam methane reforming needs about "
        "41.1 kWh of gas per kg at 81% process efficiency, the favourable end "
        "of the reported band, chosen deliberately because a floor should "
        "take the best case available to the thing it bounds. Reforming also "
        "emits about 9 kg of CO2 per kg of hydrogen, which inside the ETS "
        "carries a price, and that term is what makes the grey floor a "
        "European floor rather than a global one. Both columns are FLOORS in "
        "the strict sense: energy cost alone, with no electrolyser or "
        "reformer capex, no compression, storage or delivery. Any real price "
        "is therefore strictly above whichever floor binds, which is what "
        "gives a floor its argumentative force - it cannot be negotiated "
        "downwards, only shown to be irrelevant. What the floors then show "
        "is an uncomfortable result for the specification: the green floor "
        "exceeds the base-case hydrogen price everywhere in Europe, while "
        "the grey floor brackets it. The base case is reachable only as "
        "unabated fossil hydrogen, which emits about 0.49 tCO2 per tonne of "
        "steel - five times the clean-route intensity the model credits. "
        "Either the price is wrong or the intensity is; they cannot both be "
        "right."),
    "T6 subsidy pots": (
        "Policy instruments are sorted here by SHAPE rather than by size, "
        "because shape is what determines value and size is what gets "
        "announced. A LUMP is paid once, usually against capex, and is worth "
        "its face value discounted from the payment date. A STREAM pays per "
        "unit of output or abatement over a contracted tenor, so its value is "
        "the payment times an annuity factor, and it is contingent on the "
        "plant actually performing. An ALLOWANCE is not cash at all: free "
        "allocation is an in-kind transfer whose value moves with the carbon "
        "price, which means it is worth most exactly when the case for "
        "switching is strongest. The legal column carries a second dimension "
        "that is routinely collapsed in press coverage: whether an instrument "
        "is enacted law, a proposal still in co-decision, or framing in an "
        "explanatory memorandum. Those are not degrees of the same thing. A "
        "proposal's headline figure is a negotiating position, and quoting it "
        "beside an enacted envelope as though both were money implies a "
        "commitment that does not exist. The MISSING cells in the per-tonne "
        "column are the honest consequence: converting an envelope into a "
        "rate needs a capacity to divide by, and for an instrument not yet "
        "awarded to a named project there is no such capacity. An estimate "
        "there would look like a measurement, so the cell stays empty and "
        "the hole is given an ID."),
    "T7 subsidy shape": (
        "Equation (10) converts a per-tCO2 stream into the capex lump's own "
        "unit so the two can be compared at all: the premium times the "
        "abatement b = eps_inc - eps_cln, times the annuity factor sum over k "
        "of (1+r)^-k across the tenor. At 8% a ten-year annuity is worth "
        "about 6.7 years of payments, so the conversion is not a small "
        "adjustment - a EUR 40 per tCO2 premium on 1.8 tCO2 per tonne of "
        "product comes to several hundred euros per tonne of capacity against "
        "a EUR 200 lump. Two asymmetries sit outside the arithmetic and both "
        "favour the stream. It pays only if the plant abates, so it is "
        "performance-linked rather than front-loaded, which is why a "
        "government can offer more of it per euro of expected cost. And it "
        "removes carbon-price variance, which by the sigma argument lowers "
        "the option value of waiting and therefore the trigger itself - an "
        "effect a lump cannot have at any size, because a lump does not touch "
        "the distribution of the price. The conversion does assume the plant "
        "abates the full b = 1.8 tCO2 per tonne for the whole tenor, which is "
        "the most favourable reading available to the stream - a ramp-up, an "
        "outage or a lower realised abatement all reduce it, and none of them "
        "touches a lump. Note also what the annuity factor is sensitive to: "
        "it is computed at the model's own 8% discount rate, so a firm with a "
        "higher cost of capital values the stream lower and the lump "
        "relatively higher, while a public body discounting at a sovereign "
        "rate values it the other way round. The same instrument is therefore "
        "worth different amounts to the two parties negotiating it, which is "
        "part of why contracts-for-difference exist at all: the state can "
        "sell certainty more cheaply than the firm can buy it."),
    "T8 market": (
        "Every other table in this set reasons inside the model. This one "
        "reasons about the distance between the model and the world on the "
        "day it is run, which is a different question and the one a reader "
        "asks first. Each row pairs a published assumption with an "
        "observation carrying its own date, and states the gap in euros "
        "wherever the gap converts to euros - a carbon price eight euros "
        "above its anchor is abstract, while the same gap times the reference "
        "plant's 4.75 MtCO2 a year is not. The volatility row is the "
        "consequential one, because sigma is the only parameter that moves "
        "the trigger without moving the break-even, so it is the only live "
        "observation that changes WHEN rather than merely how much. It has no "
        "money column on purpose: sigma acts through beta and the option "
        "multiple, so its effect is not a multiplication and quoting a euro "
        "figure would imply an arithmetic that does not exist. Nothing here "
        "is fed back into the model, because one year of observations is not "
        "a path to 2050."),
    "T9 real pot": (
        "The distinction this table rests on is between money announced and "
        "money received, which are different kinds of object with different "
        "evidential status. T6 lists envelopes: political statements about "
        "future spending, some enacted, some still proposals, all of them "
        "revisable. This lists receipts: cash the EU ETS auctions have "
        "already paid, by recipient, from the settlement record. Under the "
        "ETS Directive a share of allowances is auctioned rather than "
        "allocated free, and the proceeds are distributed to member states by "
        "an allocation key with defined slices to the Innovation Fund and the "
        "Modernisation Fund. Member states receive twice - from their own "
        "national auctions and from their share of the EU-wide ones - and "
        "counting only the first would report the Netherlands, which holds no "
        "national auctions at all, as receiving nothing. The plants column "
        "divides each row by what the model hands one reference plant, which "
        "turns an abstract billion into a unit of scale. None of it is "
        "earmarked: the Directive's spending clause is a non-binding target "
        "on national budgets, not an entitlement any project can draw on."),
}
