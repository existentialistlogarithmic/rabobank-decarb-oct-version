# Figures for the October article (Draft 3)

The seven charts in Draft 3 are drawn from the same model run as every number
in the text, except Figure 1, whose project figures are listed with their
sources at the top of `make_figures.py`. The model stays standard-library only;
the drawing script needs matplotlib, so it lives here rather than in
`reporting/`.

```
python -c "from analysis import plant_case as pc; pc.export('plant_case.json')"
python docs/article/make_figures.py plant_case.json docs/article/figures
python docs/article/check_figures.py plant_case.json   # 77 checks, exits 1 on a mismatch
```

The file names keep Draft 3's numbering; the figure numbers changed in later drafts.

| File | Figure in Draft 3 | Figure in Draft 10 |
|---|---|---|
| fig_plant.png | – | 3 · The reference plant: inputs, outputs, and performance (block diagram; numbers from `Plant` and `Case`) |
| fig1.png | 1 · Announced investment and public support, first EU hydrogen-ready steel projects | 2 |
| fig2.png | 2 · Share of emissions paid, current law vs July 2026 proposal | 1 |
| fig3.png | 3 · Cost of keeping the blast furnace | 4 · direct and implied emission costs |
| fig4.png | 4 · Value of a switch decided in 2029, central path | 5 · Value of a DID taken in 2029 |
| fig5.png | 5 · NPV by FID year, and the value of waiting in the viable scenarios | 6 |
| fig6.png | 6 · Carbon price paths, break-even and trigger | 7 |
| fig7.png | 7 · One change at a time | 8 |

Draft 10 renamed two measures at Pablo's request: the "cash bill" is now *direct emission
costs* and the "full carbon value" is *implied emission costs*; the decision to switch is the
*decarbonization investment decision (DID)*.
