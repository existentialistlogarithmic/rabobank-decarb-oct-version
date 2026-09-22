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
Five questions, always in this order, because that is the order somebody
actually asks them:

1. **What am I looking at?** The marks and the axes, with units. A reader who
   stops here should at least not misread the picture.
2. **Where do the numbers come from?** The equation, the CSV, or the cached
   series - named specifically enough to go and check.
3. **How do I read it?** The procedure. Which direction is good, what the
   reference line is for, what to compare against what.
4. **What does it mean?** The conclusion the figure supports, stated plainly.
5. **What does it NOT show?** The caveat. This one is mandatory: a figure
   without a stated boundary gets over-read, and every figure here has a
   boundary.

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
    looking_at: str
    numbers_from: str
    how_to_read: str
    what_it_means: str
    not_shown: str

    def explanation(self) -> tuple[tuple[str, str], ...]:
        """The five parts, labelled, in the order a reader asks them."""
        return (
            ("What am I looking at", self.looking_at),
            ("Where the numbers come from", self.numbers_from),
            ("How to read it", self.how_to_read),
            ("What it means", self.what_it_means),
            ("What it does NOT show", self.not_shown),
        )


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
    # ------------------------------------------------ the structure underneath
    Figure(
        "levers", "The structure underneath", "Which knob moves which output",
        "If I change one input, what actually happens?",
        plots.chart_levers,
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

    charted = {fn for fn in dir(plots) if fn.startswith("chart_")}
    registered = {f.draw.__name__ for f in FIGURES}
    for missing in sorted(charted - registered):
        problems.append(f"plots.{missing} is not in the registry")
    return problems


def figure_keys(section: str) -> Sequence[str]:
    """Anchor ids within one section, in order. Used by both pages' contents."""
    return [f.key for f in FIGURES if f.section == section]
