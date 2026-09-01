# Presentation

The complete 20-minute presentation is in `presentation.tex`; the compiled
version is `presentation.pdf`. It contains 17 slides and is written in English.

The deck reuses the Phase 4 and Phase 5 figures through relative paths to the
`results/` directory. Compile it from this directory with two LuaLaTeX passes:

```bash
lualatex -interaction=nonstopmode -halt-on-error presentation.tex
lualatex -interaction=nonstopmode -halt-on-error presentation.tex
```

The Metropolis Beamer theme, TikZ, `booktabs`, and `tabularx` must be available
in the TeX installation. The figures are intentionally included as full-slide
images so that their original 16:9 layout remains unchanged.
