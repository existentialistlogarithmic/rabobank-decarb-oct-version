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

| File | Figure in Draft 3 |
|---|---|
| fig1.png | 1 · Announced investment and public support, first EU hydrogen-ready steel projects |
| fig2.png | 2 · Share of emissions paid, current law vs July 2026 proposal |
| fig3.png | 3 · Cost of keeping the blast furnace: cash bill and full carbon value |
| fig4.png | 4 · Value of a switch decided in 2029, central path |
| fig5.png | 5 · NPV by FID year, and the value of waiting in the viable scenarios |
| fig6.png | 6 · Carbon price paths, break-even and trigger |
| fig7.png | 7 · One change at a time |
