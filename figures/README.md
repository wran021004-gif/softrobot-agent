# Publication figure sources

The current manuscript uses nine figures. Figure 1 is the previously approved editable architecture drawing, preserved unchanged as fig01_research_framework.tex.

Figures 2–9 are editable TikZ/PGFPlots vector artworks integrated directly into the LaTeX manuscript:

- fig02_task_portfolio.tex — task coverage atlas.
- fig03_phs2d_mechanism.tex — independent nine-segment passive-mechanism response and topology/decision stages.
- fig04_gradient_validation.tex — implicit/finite-difference parity facets and relative discrepancy matrix.
- fig05_research_trajectories.tex — concise evidence-to-action studies.
- fig06_abc_comparison.tex — eleven-task three-mode status matrix and violation contrasts.
- fig07_reporter.tex — Reporter paired decisions and two evidence-sensitive cases.
- fig08_knowledge_skill.tex — original factor cells and additional checkpoint decisions.
- fig09_context.tex — historical input and cross-task context comparisons.

The original exported PDF files from older study snapshots remain in this directory for reference only and are not included by the current main.tex.

## Data and style

Numeric values derive from the committed paper_handoff/figure_data and supplementary_data. Tables and figures preserve all original task/Study identities and experimental scope. All diagrams use the palette defined in main.tex (sraNavy, sraMath, sraPhysical, sraDesign, sraPass, sraFail, sraGray, and sraLight). The figures are vector editable at the TeX source level; the compiled PDF is vector output.

Figure 3's upper strip deliberately depicts evidence-indexed mechanism stages, not an invented 3-D robot model. Common-camera native MuJoCo renders for four historical mechanism stages are a future visual enhancement; the ten-condition numeric panels are based on recorded independent physical evaluations.

Figure 4's matched M1/M2 experiment is prepared but has no executed results. Do not plot its unknown physical values.

To build the paper in a LaTeX environment containing IEEEtran and PGFPlots, run latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex. Figure and table labels and reference resolution should be checked after the full build. 
