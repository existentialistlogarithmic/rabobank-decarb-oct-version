# Figures for the October article (Draft 2)

The six charts in Draft 2 are drawn from the same model run as every number in
the text. The model stays standard-library only; the drawing script needs
matplotlib, so it lives here rather than in `reporting/`.

```
python -c "from analysis import plant_case as pc; pc.export('plant_case.json')"
python docs/article/make_figures.py plant_case.json docs/article/figures
```

| File | Figure in Draft 2 |
|---|---|
| fig1.png | 1 · Share of emissions paid, current law vs July 2026 proposal |
| fig2.png | 2 · Cost of keeping the blast furnace: cash bill and full carbon value |
| fig3.png | 3 · What a 2029 switch is worth, central path |
| fig4.png | 4 · NPV by FID year, and the value of waiting in the 25 viable scenarios |
| fig6.png | 5 · One change at a time |
| fig5.png | 6 · Price paths, break-even and trigger |
