# Codex task: synchronize Phase-1 TRO manuscript into the existing Overleaf project

## Role and target
You are working inside the user's local Windows repository `D:\softrobot-agent`. The authoritative manuscript source is GitHub branch `origin/paper/manuscript-phase1-20261116`. Its intended content is a Phase-1 TRO-style manuscript restructure with Figure 1 frozen, seven first-pass vector results figures, consistent mathematical notation, and a complete 11-task A/B/C descriptive comparison.

**Execute the synchronization, not just describe it, provided the existing Overleaf Git remote and authorization can be verified.** Do not invent an Overleaf URL or claim a push succeeded without a successful remote update.

## Safe startup
1. Inspect `git status --short`, `git worktree list`, `git remote -v`, and the current repository layout. Protect all uncommitted work. Do not reset, clean, stash or overwrite user files without explicit evidence and approval.
2. Fetch `origin paper/manuscript-phase1-20261116` and record the exact source HEAD. The latest pushed source contains `PAPER_STYLE_GUIDE.md`, `PAPER_FIGURE_TABLE_PLAN.md`, `figures/fig02_task_portfolio.pdf` through `figures/fig08_context_comparison.pdf`, and corresponding editable SVGs.
3. Identify the already configured Overleaf project remote (and its actual branch) in the relevant paper worktree. Overleaf edits may be ahead of the last local commit. Fetch and inspect before proposing a push. Never force-push. If no authenticated Overleaf remote or project mapping exists, stop only the remote-write step, report exactly what credential/URL is missing, and leave all verified local files ready.

## Sync scope
Copy or reconcile the following from the authoritative Phase-1 source into the existing Overleaf project, respecting its actual root layout:
- `main.tex`, `references.bib`.
- The compiled sections, as selected by `main.tex`: `sections/01_introduction.tex`, `02_related_work.tex`, `03_problem_formulation.tex`, `04_method.tex`, `06_experimental_setup.tex`, `07_results.tex`, `09_discussion.tex`, `10_conclusion.tex`.
- `appendices/A_experiment_protocol.tex`, `B_additional_task_portfolio.tex`, `C_evidence_provenance.tex`, `D_architecture_ablation_protocol.tex`.
- `figures/fig02_task_portfolio.pdf`, `fig03_phs2d_mechanism.pdf`, `fig04_gradient_validation.pdf`, `fig05_research_trajectories.pdf`, `fig06_abc_comparison.pdf`, `fig07_architecture_ablation.pdf`, `fig08_context_comparison.pdf`; preserve the corresponding `.svg` editable assets in the project as well when possible.
- `PAPER_STYLE_GUIDE.md` and `PAPER_FIGURE_TABLE_PLAN.md` may be kept as editorial references outside the compiled TeX inputs.

**Figure 1 is frozen.** Before and after synchronization, compare the current approved Figure-1 editable source and PDF/SVG against the original. Do not replace it, redraw it, rename its nodes, change its captions in a way that changes meaning, or silently switch from the actual approved file to the repo's older assets. The Phase-1 branch's `figures/fig01_research_framework.tex` is blob-identical to the previous manuscript baseline, but the Overleaf project might hold a separate approved SVG. Preserve whichever artifact is actually approved on Overleaf; if needed only modify the non-Figure-1 inclusion path while preserving the figure itself.

Do not upload the entire experiment Store or the many `paper_handoff` CSV/JSON records to Overleaf; they are publication source data and remain in GitHub. Do not blindly rerun `figures/generate_paper_figures.py` over the committed vector assets: the script is an alternative draft plotting implementation and is not pixel-identical to this Phase-1 rendering.

## Scientific and stylistic invariants
- Main Agent owns scientific decisions. PPRP is deterministic mathematical problem compilation. M0--M3 are complementary analysis semantics, not a mandatory pipeline. Mathematical and physical evidence are independent. Reporter is read-only. A direct physical-test path is available without prior mathematical analysis.
- The FULL portfolio is eleven task cases T01--T10 plus **PHS-2D-7S**, with **30/30 required conditions passed**. The independent **PHS-2D-9S** mechanism study is not the FULL PHS case; it has **10/10 signed-loading cases**, minimum loaded-point displacement **11.155 mm**, maximum projected tip displacement **3.068 mm**, and maximum ratio **0.1093**.
- The 18 derivative pairs are six signed-loading branches times three metrics on one common normalized modulus direction; maximum discrepancy **0.1191%**.
- The 11x3 comparison uses A=LLM-only, B=direct mathematical tools, C=historical FULL. Preserve qualification failures, incomplete cases and protocol-deviant T03-B/T05-B rather than counting them as standard comparable successes.
- Reporter / Knowledge-Skill / Context are decision-only replays, not downstream physical tasks. Historical Provider actual usage at C035/C037 is distinct from the six cross-task Gateway pairs whose actual usage is unavailable. Do not substitute local token estimates as Provider usage or billing.
- Only Figure 1 is the fixed visual anchor. Align Figs. 2--8 to its semantics and `PAPER_STYLE_GUIDE.md`: navy #26384B Main, teal #527F7B math, slate #70849A physical, ochre #B08A59 structure, green #557663 pass, brick #A35D55 failure, gray #929BA4 baseline. White backgrounds, no decorative gradients, consistent figure labels and Helvetica/Arial-style typography.

## Compile, inspect and deliver
1. Ensure all included `.tex`, figure PDFs, TeX macros and bibliography keys resolve.
2. Compile with IEEEtran pdfLaTeX/latexmk (or the existing Overleaf settings). If compilation is blocked, report exact errors and preserve the synced source. Do not fill errors by suppressing missing scientific results.
3. Inspect the generated PDF, especially Figure 1's complete unchanged content, Figures 2--8, Table I, line widths at double-column size, captions, equation overflow and float/page breaks. Fix layout problems without modifying Figure 1 or numeric evidence.
4. Phase-1 Figure 3 already shows actual recorded centerlines and signed-load curves. The native 3D rendering of intermediate candidates remains a separate last-mile task: add only model-accurate renders from the archived XML/Journal at one camera/scale; do not invent them. This should not block synchronization of the currently completed paper.
5. After successful local compile and diff review, commit the intended manuscript changes on the existing Overleaf working branch and push normally to the verified Overleaf Git remote. No force push; if the remote has advanced, fetch and reconcile and recompile first.
6. Final response must state: authoritative GitHub source SHA, Overleaf project remote name/branch, exact pushed commit SHA (or explicit remote blocker), compilation result, any unresolved warnings, and whether Figure 1 was confirmed byte-identical/preserved.

Do not start new scientific experiments or change frozen task evaluators. Prioritize the written paper and figures; unresolved physical M1/M2 paired replay and hardware results remain outside the current compiled empirical claims.
