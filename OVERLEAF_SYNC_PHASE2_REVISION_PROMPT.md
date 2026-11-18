# Codex task: synchronize Phase-2 TRO manuscript revision to the existing Overleaf project

## Authoritative source and destination

- GitHub source branch: paper/manuscript-phase2-revision-20261118
- Source commit at task creation: read the current remote branch HEAD; do not assume a stale SHA.
- Local repository: D:\softrobot-agent
- Existing Overleaf Git remote: overleaf
- Overleaf branch: main
- Last reported Overleaf commit before this revision: 1f158b9d14d3bd7bd98f8bf798ffef032181080a

Execute the synchronization if the configured remote and authentication are available. Do not merely provide instructions. Do not force-push.

## 1. Safe preparation

1. Inspect git status, worktrees, remotes, and the current paper worktree. Protect all uncommitted files.
2. Fetch the GitHub source branch and Overleaf main. Confirm the current Overleaf HEAD before editing; if it has advanced since the reported commit, reconcile from its current state.
3. Work in a clean dedicated worktree or a clean paper worktree. Do not reset, clean, or overwrite unrelated files.
4. The GitHub branch contains the Phase-2 manuscript revision and selected native PNGs. It does not contain the full experiment archive.

## 2. Files to synchronize

Synchronize these manuscript sources from the Phase-2 branch:
- main.tex and references.bib.
- sections/01_introduction.tex, 02_related_work.tex, 03_problem_formulation.tex, 04_method.tex, 06_experimental_setup.tex, 07_results.tex, 09_discussion.tex, 10_conclusion.tex.
- appendices/A_experiment_protocol.tex, B_additional_task_portfolio.tex, C_evidence_provenance.tex, D_architecture_ablation_protocol.tex.
- tables/table1_physical_portfolio.tex and tables/table2_abc_comparison.tex.
- figures/fig02_structure_evolution.tex, fig03_research_trajectory.tex, fig04_physical_execution.tex.
- figures/fig05_gradient_validation.pdf/.svg, fig06_architecture_ablation.pdf/.svg, fig07_context_comparison.pdf/.svg.
- figures/native/*.png (the 16 selected MuJoCo renders and recorded task plots).
- PAPER_STYLE_GUIDE.md and PAPER_FIGURE_TABLE_PLAN.md may be retained as editorial references outside the compiled inputs.

Do not upload the complete runs/multitask-paper-data-20261118 archive, SQLite stores, full decision traces, or the supplementary data directory. The selected image assets are already the intended compact paper subset.

## 3. Figure 1 is immutable

The existing Overleaf project contains the approved Figure 1 PDF and SVG and its own inclusion environment. Preserve the actual approved Overleaf:
- figures/fig01_research_framework.pdf
- figures/fig01_research_framework.svg
- complete figure environment, graphics path, dimensions, placement, caption and label.

Do not import the older GitHub TikZ drawing over the Overleaf figure. Do not regenerate, redraw, recolor, relabel, crop, rename, or replace Figure 1. Keep the selected-parameter notation mapping in surrounding manuscript text if needed, but do not alter the figure artwork.

The previous Phase-2 synchronization verified that the approved Figure 1 PDF/SVG were byte-identical to the Overleaf starting files. Preserve that result.

## 4. Scientific and naming invariants

- Reader-facing PHS naming is always PHS-2D. Do not show segment-count suffixes in the main text, table labels, captions, or legends. Preserve exact Study IDs only in internal source metadata.
- The FULL portfolio is T01--T10 plus PHS-2D, with 30/30 required conditions passing. T10's two frozen-input controls are separate.
- PHS-2D selected ten-load result: minimum loaded-point displacement 14.798 mm; maximum projected tip displacement 4.347 mm; maximum ratio 0.1538.
- The separate local sensitivity audit contains 18 derivative pairs (six loading branches × three metrics) along one common material-parameter direction; maximum relative discrepancy 0.1191%. Do not claim 18 independent parameter directions.
- T07: four required conditions and 35 original hard constraints pass. The displayed root-shape candidates are the actual models in the archive.
- T04: complete 22-s figure-eight, RMSE 0.688 mm, maximum error 1.021 mm.
- T09: 0.5-s depth/force hold, maximum depth error 0.0528 mm, force error 0.00247 N.
- T10: one common feedback recipe passes three required impact conditions; two frozen-input controls are separate failures.
- A/B/FULL matrix: FULL is the historical reference. A: seven valid failures, three incomplete, one qualification failure. B: five valid failures, one incomplete, three qualification failures, two passes. T03-B is the marked direct-mathematical-only protocol variant; T05-B is a standard B pass.
- Decision-only Reporter, K/S and Context studies are not additional physical task successes.
- Provider-reported token usage must remain distinct from local text-token estimates and unavailable Gateway usage.
- The selected T04/T07/T10 timelines are archived task-study records and do not add independent task trials.

## 5. Figure and table style

- Figure 1 remains unchanged.
- Figures 2--4 use the actual selected MuJoCo renders and saved task plots. Keep the native rendering, white ground, lighting and shadows.
- Figures 5--7 retain the existing quantitative vector assets under the new numbering.
- Tables I and II use booktabs: no vertical rules, no colored cells, grouped rows, readable 9-pt-scale text, and bold passing/best results. Do not convert them to cards or dashboards.
- Captions should be concise. Do not add source hashes, long caveats, or tiny explanatory paragraphs to the figures.
- Use PHS-2D consistently in all reader-facing labels.

## 6. Compile and visually inspect

1. Ensure all input files, figures, table inputs, macros, and bibliography references resolve.
2. Compile using the existing Overleaf-compatible IEEEtran toolchain (pdfLaTeX, BibTeX, repeated pdfLaTeX until references stabilize).
3. Inspect the generated PDF at print scale:
   - Figure 1 unchanged and complete.
   - Figures 2--4: images have consistent alignment, no clipping, readable panel labels, and no stretched aspect ratios.
   - Figures 5--7: captions and axis labels readable.
   - Tables I and II: no vertical rules or cell shading, no overflow, proper group separators, bold pass results.
   - Check equations, references, float placement, and page breaks.
4. Fix layout issues without changing scientific values or Figure 1. Do not shrink fonts below readable print size to force a fit.
5. Record any remaining nonfatal Underfull/Overfull notices.

## 7. Commit and push

After reviewing the diff and successful compile:
1. Commit the intended manuscript update on the existing Overleaf main history.
2. Push only a normal fast-forward update to overleaf/main. Never force-push.
3. If the Overleaf remote has advanced, fetch and reconcile, then recompile before pushing.
4. Confirm the remote HEAD with git ls-remote overleaf refs/heads/main.
5. Leave the GitHub source branch unchanged.

## 8. Final report

Report:
- GitHub source branch and exact source SHA.
- Overleaf remote, branch, and pushed commit SHA.
- Compile result and final page count.
- Remaining warnings, if any.
- Confirmation that Figure 1 was preserved.
- Whether the final PDF corresponds to the exact pushed source.

If credentials or the Overleaf remote are unavailable, stop only the remote push step and state the exact blocker. Do not claim a successful Overleaf upload without verifying the remote HEAD.
