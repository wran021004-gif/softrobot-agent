# Merge from the user's actual Overleaf source

Source: uploaded `softrobot_agent_overleaf_draft_v0_1(1).zip` (15 files). The IEEEtran main document and nine `sections/` filenames are preserved. The prose has been substantially reorganized around C1/C2/C3 as requested.

## Modified existing files
- `README_Overleaf_CN.md`
- `figures/README.md`
- `main.tex`
- `references.bib`
- `sections/01_introduction.tex`
- `sections/02_related_work.tex`
- `sections/03_problem_formulation.tex`
- `sections/04_architecture.tex`
- `sections/05_mathematical_methods.tex`
- `sections/06_experimental_setup.tex`
- `sections/07_results.tex`
- `sections/08_discussion.tex`
- `sections/09_conclusion.tex`

## Unchanged existing files
- `EVIDENCE_AUDIT_NOTES.md`
- `tables/README.md`

## New files
- `C1_C2_C3_MAP.md`
- `EXPERIMENT_MATRIX.md`
- `SOURCE_AND_CLAIM_BOUNDARIES.md`
- `appendices/A_experiment_protocol.tex`
- `appendices/B_additional_task_portfolio.tex`
- `figures/download_original_figures.ps1`
- `figures/original_assets_manifest.json`
- `prepare_with_original_figures.ps1`

## Original experiment figures
The uploaded ZIP contained no experiment image binaries. To avoid fabricated or reconstructed results, the source package does not embed any image binary. Instead, `figures/original_assets_manifest.json` stores the exported branch paths and Git blob SHA-1 values. The Windows one-step script downloads and checks these exact PDFs, then produces a complete Overleaf ZIP. No new plotting or simulation is invoked.
