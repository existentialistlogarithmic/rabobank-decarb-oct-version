# timing_model

Python implementation of the RaboResearch industrial decarbonisation
investment-timing model (real options + NPV), following the v12 restructure
and coding specification.

A steel producer chooses a single year `T` to irreversibly switch from blast
furnace to H2-DRI-EAF. The model maximises `NPV(T)` over the horizon and
separately computes an uncertainty-adjusted carbon-price trigger via a
Dixit–Pindyck option multiple.

## Four outputs, and why there are four

| Output | Question it answers | Contains option premium? |
|---|---|---|
| Trigger `p*'` (€/tCO₂) | At what carbon price does an irreversible switch become rational? | Yes |
| Crossing year | When does the *path* reach that price? | Yes, plus a price forecast |
| `T*` | Which year maximises NPV? | No |
| `T_exp` | Last year in which deferral still adds value | No |

`T*` and the crossing year routinely differ by one to two years. **That gap is
the option premium expressed in time, not an inconsistency.**

## Layout — the group order is the deliverable

```
timing_model/
  params.py        # dataclasses; every field carries unit, currency-year, source
  primitives.py    # Group I:   b, a(p_H2), CRF, MAC   [MAC diagnostic only]
  benefit.py       # Group II:  alpha_v(t), B(t)
  cost.py          # Group III: L(T), s(T), S_s(T), I_prime(T)
  objective.py     # Group IV:  npv(T), t_star, t_exp, delta(T)
  option.py        # Group V:   p_M_prime, beta, trigger, crossing_year
  validate.py      # gate + feasibility guards; raises, never returns a flag
  results.py       # Outputs, welded to its conditions
  scenarios.py     # ladder, storylines, sourced ranges, legacy fixture
  diff_harness.py  # 50 reference cases + the MATLAB diff
  report.py        # tables + CSV
```

Imports point forward only, and `tests/test_layering.py` asserts it by walking
the AST. `cost.py` cannot import `objective.py`; `primitives.py` reaches
nothing but the parameter container; `cost.py` may not so much as name the load
factor `u`.

## Usage

**Python 3.11+ and nothing else.** The package has zero third-party
dependencies — no numpy, no pandas, no solver libraries. Every equation is
closed-form or a small argmax over ~25 years, and a test asserts the package
imports nothing outside the standard library. If you cannot install packages,
everything below still works.

```bash
python run_all.py                          # EVERYTHING: gate, ladders, diff, self-check
python selfcheck.py                        # 21 load-bearing claims, stdlib only

python plots.py                            # charts -> charts.html (open in a browser)
python -m timing_model.report              # just the cumulative stress ladder
python -m timing_model.report --sigma      # plus the volatility ladder
python -m timing_model.report --csv        # writes python_results.csv
```

`pytest` is the only optional extra, and runs the full 91-test suite in
`tests/`. Without it, `selfcheck.py` verifies the same load-bearing claims —
gate, base case, ladder, guards, conditions mechanic, negative control,
layering — using only the standard library. `run_all.py` runs the self-check
always and the pytest suite when it is available.

### PyCharm

1. **Open** the repository root as the project (the folder containing
   `pyproject.toml`) — not the `timing_model/` package folder, or imports
   will not resolve.
2. **Interpreter:** Settings → Project → Python Interpreter — any 3.11+
   interpreter works. **No packages need installing.** If PyCharm offers to
   install `requirements.txt`, that is only `pytest`, and it is optional.
3. **Tests:** if you have pytest, set Settings → Tools → Python Integrated
   Tools → Default test runner = **pytest**, then right-click `tests/` → Run.
   If you cannot install it, right-click `selfcheck.py` → Run instead.
4. **Run everything at once:** right-click `run_all.py` in the Project pane →
   **Run 'run_all'**. That executes, in order: the validation gate, the base
   case, the stress ladder, the volatility ladder, the sourced ranges, the
   50-case reconciliation harness with its negative control, the CSV write,
   and the full test suite. It exits non-zero if the gate fails, the negative
   control misbehaves, or any test fails, so it also works as a CI smoke check.
5. **Running just the report:** use a *module* run configuration, not a script one —
   Run → Edit Configurations → **+** → Python, switch the target dropdown from
   *Script path* to **Module name**, and enter `timing_model.report`. Put any
   flags (`--csv`, `--sigma`) in *Parameters*. Running `report.py` as a plain
   script also works because PyCharm puts the content root on `sys.path`, but
   the module configuration is what matches the documented entry point.

`pip install -e .` is optional and only needed to import `timing_model` from
outside the project.

## The conditional-outputs mechanic

The recurring failure this rewrite exists to fix is that `T*` and the trigger
get quoted without the assumptions they are conditional on. `Outputs` is
frozen and always carries `conditions`; `report.py` **refuses to render** any
row containing `t_star` or `trigger` unless every condition is populated, and
prints them under the table. Tests cover each condition key individually.

## Three decisions the code will not make for you

Appendix A §3.5 reserves these to the team. All branches are implemented and
none is silently defaulted — each is surfaced in the printed conditions of
every row:

1. **Support basis** — €200 lump or ~€600 stream. `support_basis` switches
   between netting a stock from capex (`"lump"`, which the MATLAB diff needs)
   and routing the premium into `B(t)` where a flow belongs (`"stream"`).
2. **Resale** — `w = 1` drives the entire policy-neutrality finding. Without
   it the headline result reverses sign.
3. **Whether €2.60/kg hydrogen is reported as the base case at all.** The
   market was €8.29/kg on 8 May 2026.

## Status

Read `CALIBRATION.md` before quoting any number from this build.
`timing_model.m` was not in the working directory, so five of the six cost-side
constants were sourced from published industry data and one (the learning
growth rate) calibrated. The validation gate, the trigger column
and the benefit side reproduce exactly, as do ladder rows 1–3; rows 4–7 do not,
and the reasons are documented case by case with sources.
