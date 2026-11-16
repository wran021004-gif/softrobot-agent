# Publication figure assets

Figure 1 (`figures/fig01_research_framework.tex`) is the approved frozen architecture source and must not be edited.

Figures 2–8 are committed as **editable vector SVG** plus **vector PDF** using the normalized paper-handoff records:
- `fig02_task_portfolio.pdf` / `.svg`: eleven-case FULL portfolio (including seven-segment PHS-2D).
- `fig03_phs2d_mechanism.pdf` / `.svg`: independent nine-segment model, stored physical centerlines and ten signed-load responses (native 3D renders still to be added).
- `fig04_gradient_validation.pdf` / `.svg`: 18 local implicit-vs-finite-difference derivatives.
- `fig05_research_trajectories.pdf` / `.svg`: selected research decision nodes and their archived outcomes.
- `fig06_abc_comparison.pdf` / `.svg`: complete 11 × 3 research-mode status matrix and scoped violations.
- `fig07_architecture_ablation.pdf` / `.svg`: Reporter and Knowledge/Skill decision replays.
- `fig08_context_comparison.pdf` / `.svg`: historical usage and six cross-task decision/evidence comparisons.

The current PDF/SVG asset pair is the approved Phase-1 rendition and is referenced from `sections/07_results.tex`. The older exports in this directory belong to the v0.4 manuscript and are retained for provenance only. The optional `generate_paper_figures.py` script is a **draft alternative plotting implementation**, not a pixel-identical reproduction of the committed Phase-1 vector assets; do not run it over the committed PDFs without verifying task identity, grouping, layout, and numeric consistency first.

For canonical symbols, names and palette, use `PAPER_STYLE_GUIDE.md`. For figure evidence and last-mile native render requirements, use `PAPER_FIGURE_TABLE_PLAN.md` and `paper_handoff/figure_manifest.md`.

Do not replace missing values with zero; do not pool heterogeneous physical errors; do not relabel local token-count estimates as Provider usage; do not combine seven- and nine-segment PHS studies. 
