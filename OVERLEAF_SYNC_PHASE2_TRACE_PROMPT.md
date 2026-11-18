# Codex: synchronize evidence-guided TRO manuscript to the existing Overleaf project

## Authoritative sources and destination

- GitHub repository: wran021004-gif/softrobot-agent
- Source branch: origin/paper/manuscript-phase2-revision-20261118
- Source HEAD: fetch and record the current branch head; do not rely on an old commit.
- Local Windows working repository: D:\softrobot-agent
- Existing Overleaf Git remote: overleaf; target branch main.
- Last known successful Overleaf deployment: 1f158b9d14d3bd7bd98f8bf798ffef032181080a. Always fetch the actual current remote HEAD.

Execute the actual synchronization, compilation, visual review and normal fast-forward push when access is available. Never claim deployment before verifying overleaf/main.

## 1. Safe preparation

1. Inspect the local worktrees, modified files and remotes. Preserve all unrelated uncommitted work; do not reset, clean or force-push.
2. Fetch the source branch and Overleaf main. Work in a dedicated clean worktree cloned from the current Overleaf main, not by clobbering the local paper branch.
3. Compare the current Overleaf source with the GitHub Phase-2 revision. Existing Overleaf-specific layout fixes may be ahead of GitHub. Reconcile rather than blindly replacing them.

## 2. Synchronize the current manuscript

Import the intended updated publication source:
- main.tex, including the restrained TraceNavy / TraceTeal / TraceSlate color definitions.
- Eight active sections selected by main.tex, four appendices, references.bib and valid cited references.
- tables/table1_physical_portfolio.tex and tables/table2_abc_comparison.tex.
- figures/fig02_structure_evolution.tex, fig03_research_trajectory.tex, fig04_physical_execution.tex.
- Existing quantitative vector figures used by Results: fig05_gradient_validation.pdf (and SVG), fig06_architecture_ablation.pdf (and SVG), fig07_context_comparison.pdf (and SVG).
- The 16 original selected native MuJoCo PNG assets under figures/native/ already tracked on the source branch.
- Style guidance and paper plan can be retained as editorial sources outside the compiled TeX inputs.

Do not upload the full 188-image / 25-video archive, experimental SQLite Stores, intermediate XML database, or unrelated report directories.

## 3. Absolute Figure-1 preservation

Preserve the approved Figure 1 that already exists on Overleaf:
- figures/fig01_research_framework.pdf and .svg byte-for-byte.
- Its existing complete LaTeX figure environment, inclusion path, dimensions, placement, caption and label.
Do not replace the approved Figure 1 with the old GitHub TikZ source; do not regenerate the diagram.

## 4. Reader-facing narrative

The central evidence story is:
- Figure 2: PHS-2D and T07 native morphology evolution, with succinct evidence-grounded Agent finding, actual action and physical outcome.
- Figure 3: T04 and T10 trace panels combine Agent output, action, native MuJoCo states and quantitative curves.
- Figure 4: T09 actual contact-state sequence + force/depth trace + contact-execution decision.
- Figure 5: local mathematical derivative check.
- Figure 6: Reporter / Knowledge-Skill decision evaluation.
- Figure 7: hierarchical context costs and evidence quality.
- Table I: eleven-task physical results grouped like a conventional IEEE benchmark table.
- Table II: eleven-task A/B/FULL outcomes grouped by task family.

No dashboard cards, rounded blocks, tinted table cells, gradient fills, extensive footnotes in plots, or oversized in-figure titles. Keep captions concise. Source-data identifiers are not displayed as visual metadata.

All reader-visible PHS task labels use PHS-2D, without segment-count suffixes. The PHS physical portfolio metrics (14.798 mm loaded-point minimum, 4.347 mm max tip displacement, max ratio 0.1538) are from one selected ten-condition study, while the 18-pair gradient audit is from a separate PHS-2D study. Keep internal Study sources distinct and do not imply these were one continuous candidate or directly comparable paired experiment.

A/B/FULL task portfolio: FULL satisfies all 30 required conditions. The T03-B direct-mathematical-only variant is indicated by a dagger, explained in the Table II caption. Report valid physical failures, incomplete and qualification failures distinctly. The two T10 frozen-input controls are outside its three required cases.

Agent output text is an extracted or concise paraphrased public research decision, not invented raw internal thinking. The T04 all-4 N inadmissible initialization and 0.20 to 0.21 N restart are from archived decisions. T10 morphology stays fixed during its control-route change. Avoid creating unrecorded experiment/structure transitions.

## 5. Compile and visually inspect

1. Compile with the existing project IEEEtran pdfLaTeX + BibTeX + pdfLaTeX passes until references settle.
2. Inspect PDF pages with Figures 2–4 at 100% and 200% zoom. In particular, confirm:
   - Three native PHS images, two T07 images and their Agent/action statements are aligned without text wrapping over images.
   - T04 earlier and final MuJoCo snapshots plus tracking plot, followed by readable agent observation/action/result.
   - T10 preimpact/pulse/recovery sequence and control comparison plot are correctly aligned, not presenting different robot structures.
   - T09 native contact sequence and force/depth plot remain legible at final double-column width.
3. Check Tables I/II for booktabs-only horizontal grouping, no vertical lines or shading, accurate numbers, no overfull rows/columns. Prefer natural font sizes and better column widths; do not force full-page resize into tiny fonts.
4. Check all floats, captions, references, equations, missing graphics, missing fonts, overfull hboxes and page/column balance. Reuse the previous successful Overleaf Figure 1 verbatim.
5. If layout adjustments are needed, edit the Overleaf local copy with the same scientific content; commit those layout corrections. Do not rewrite data, modify thresholds, or add fabricated diagram elements.
6. Verify no Figures 2–4 are compiled from the obsolete old PDFs. Figure 5–7 should still use the accurate quantitative vector files.
7. A final reader-facing terminology scan should find PHS-2D without 7S/9S suffixes in active TeX and figure labels; source archives may retain exact Study IDs.

## 6. Push and report

Commit only the scoped manuscript, table and figure changes to the fetched Overleaf main history.
Push by a normal fast-forward, never force. If remote main advanced, fetch and reconcile then recompile before pushing.
Confirm the remote commit with git ls-remote overleaf refs/heads/main.
Return: GitHub source SHA, Overleaf commit SHA, page count, compile warnings, figure/table layout review, confirmation that Figure 1 was untouched, and any missing data/asset blockers. Do not state synchronization succeeded until remote verification completes.
