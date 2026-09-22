# Handoff: two slides, 11:45

**Purpose.** Everything a deck needs, in one file, so a PPT can be built from
this without opening the model. Pablo covers the industry situation and the
regulatory/subsidy landscape; these two slides are the *what we are doing to
understand how a client should decide*, framed as live, ongoing research.

**Audience.** Internal colleagues — no clients, no external stakeholders.
Several of them think in cash flows and debt sizing, not in real options.

**The brief, verbatim from the conversation:** *what / why / how*, qualitative,
one or two graphs at most, primary results welcome. No equations on the slide.

---

## 1. The one thing to get right

> *"The graphs and the tables are one step before the visual analysis."*

That was the sharpest note, and it is now fixed. Capex, opex, subsidies and CO2
were all in the model but **entangled inside the equations** — a learning
multiplier here, a support window there, a free-allocation factor folded into a
coefficient. The build reported the model's *outputs* and never drew its
*inputs* against time.

The gap matters because of who reads it:

| reader | reads | wants |
|---|---|---|
| analyst | NPV(T) | the optimum |
| **lender** | **cash flow** | **the trough, and the payback date** |

`analysis/cashflow.py` now does that half step. **The discounted cash flow
equals the model's NPV to the cent** — it is the same object, re-presented, and
a test checks it on every build. Nothing was recalibrated.

---

## 2. Slide 1 — WHY (the problem)

**Headline:** *A multi-variable decision with no stable answer.*

The point to land: this is not a model that produces a number. Four inputs move
independently, on different clocks, and none of them is controlled by the firm:

- **Capex** — falls with learning, but the plant forfeits undepreciated book
  value the earlier it switches
- **Opex** — the hydrogen price, which is the single largest swing factor
- **Subsidies** — a *window*, not a pot: worth full weight to 2031, tapering to
  nothing by 2035
- **CO2** — a price that rises *and* a free allocation that phases out, which
  compound

Then the honest framing Pablo asked for: **there is no solution, and there
should not be one.** Every plant has a different asset age, a different balance
sheet, a different cost of capital and a different tolerance for
non-productive time. What the work produces is a *map* and a *method*, not an
answer.

**Suggested single visual:** the four-panel input chart
(`inputs-over-time` in `gallery.html` / `explained.html`). It shows four
different shapes on one shared timeline and makes the multi-variable point
without a word of theory.

---

## 3. Slide 2 — WHAT and HOW (the result)

**Headline:** *Translated into the language of a cash flow.*

Lead with the numbers, for a 2.5 Mt/yr European integrated works, real euros:

| | |
|---|---|
| Commitment year (NPV-optimal) | **2029** |
| Peak exposure — the financing requirement | **EUR 1.2bn**, in 2029 |
| Payback | **2033**, four years after committing |
| NPV at that decision | **EUR 4.0bn** (published inputs) |
| …on fully sourced inputs | **EUR 1.3bn**, and negative at the top of the range |

Then the two points that make it research rather than a result:

1. **The answer is a range that crosses zero.** Which end you believe is the
   whole argument — that is an *epistemic* uncertainty about inputs, separate
   from the price uncertainty the real-options machinery handles.
2. **Timing is far more robust than value.** The corrections move the level of
   the answer much more than they move the year. That is worth saying out loud:
   the model is better at *when* than at *how much*.

**Suggested single visual:** the cash-flow chart (`cash-flow`) — annual net
above, cumulative below, with the commitment year and the payback year marked.
This is the chart that speaks to the debt-sizing audience.

**If there is room for a third:** the heat maps / sensitivity surface
(`explorer.html`, `surface.html`) as "the map, not the answer" — these are the
strategy-family framing (least-risky vs fastest-return vs most-ambitious).

---

## 4. Numbers you may be asked for

All live from the model as of the last build. Every one is re-derived from its
raw source by `analysis/verify.py` — **145/145 cells agree**.

| quantity | value | note |
|---|---|---|
| T* (commitment year) | 2029 | NPV-optimal |
| Trigger price | EUR 110/tCO2 | real-options threshold |
| Crossing year | 2030 | when the price path reaches it |
| Capex assumption I0 | EUR 900/t capacity = **EUR 2.2bn** | vs EUR 1,300+/t for every project actually under construction |
| Support s_max | EUR 200/t capacity = **EUR 500m** | ~25% of the Innovation Fund's entire 2026 intake |
| Peak exposure | EUR 1.2bn (2029) | deeper than capex alone |
| Payback | 2033 | 4 years |
| **Observed carbon price** | **EUR 84.02/tCO2** | EU ETS auctions, 20-session VWAP, vs EUR 76 assumed |
| **Observed volatility** | **sigma 0.31** | vs 0.20 assumed — puts the crossing at 2035, not 2030 |
| EU ETS auction revenue 2026 YTD | EUR 27.5bn | of which Innovation Fund EUR 2.0bn |

### The one live number worth a sentence

Realised volatility from the auction record is **0.31 against the 0.20 the
model runs on**. Sigma is the only parameter that moves the *threshold* without
moving the break-even, so it is the only live observation that changes *when*.
At the specification's own "crisis" rung the trigger is EUR 140 instead of
EUR 110 and the crossing moves from 2030 to **2035** — five more years of
waiting. The model still runs on 0.20: one year of auctions is not a path to
2050.

---

## 5. What NOT to claim

Say these before anyone asks. They are the credibility of the whole thing.

- **Opex has no time shape.** The model carries one constant driven only by the
  hydrogen price. A real plant's operating cost rises with age, jumps at the
  switch while the technology is learned, then settles. That is hole H10 /
  review comment 5, still open — the line is drawn flat and labelled flat
  rather than given a plausible curve.
- **No tax layer.** Electricity is 2–4x gas per kWh in every member state, and
  those prices exclude taxes, levies and network charges — exactly what
  "fiscal harmonisation" would change.
- **No MATLAB reference.** The 50-case diff harness is built and its negative
  control works; there is no reference file to run it against.
- **Ladder rows 4–7 do not reproduce** the published table. Documented case by
  case in `CALIBRATION.md`.
- **One unverified input** — the EUR 8.29/kg Platts hydrogen assessment,
  licensed data taken from the specification.
- **Subsidy money is not earmarked.** The ETS Directive's spending clause is a
  non-binding target on national budgets, not an entitlement any project can
  draw on.

---

## 6. Where the assets are

| file | what it holds |
|---|---|
| `gallery.html` | all 19 figures + 10 tables, titles only — for picking a visual |
| `explained.html` | the same, each with 300+ words including the theory |
| `results.html` | the ten tables with their sources |
| `brief.pdf` | two pages, the version to send on |
| `charts.html` | the chart page with hover and table views |
| `explorer.html`, `surface.html` | the interactive maps |

To export a figure for a slide: open `gallery.html`, find it in the index, and
screenshot it — every chart is inline SVG, so it scales cleanly. The
`explain →` link on each goes to its full write-up.

To rebuild everything: `python run_all.py` (13 sections; ~40 s offline, a few
minutes on a cold run that fetches Eurostat, the ECB and the EEX auction
record).

---

## 7. A note on the framing

Pablo's test was whether the work can be *landed* rather than only abstracted.
The cash-flow translation is the answer to that: same model, same numbers, but
expressed as money out, money in, a trough and a date. If a slide can only
carry one idea, carry that one — **we can hand a banker the thing they
actually size against, and it is the same object as the option-value result.**
