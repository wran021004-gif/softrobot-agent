# Paper Figure and Table Plan — v1.2

## Manuscript positioning

Primary claim: **physics-grounded agentic research for soft-robot co-design**.

The central scientific contribution is autonomous research organization: selecting a physical question, compiling it into a task-conditioned mathematical problem, choosing a valid analysis or physical test, and using separate mathematical and physical evidence to decide the next design/control action.

Structure–control decoupling, M0–M3 sensitivity, optimization, and diagnosis are the technical research substrate and scientific actions. Do not present the paper as merely a new continuum-robot controller or a generic morphology optimizer.

## Publication precedents and what to borrow

1. **Ghareeb et al., Nature (2026), “A multi-agent system for automating scientific discovery.”** Figure 1 introduces the architecture/workflow; Figures 2–4 then follow the discovery cycle through hypotheses, experiments, analysis, and validation. Component ablations are placed in Extended Data, with blinded human/LLM evaluation and explicit sample sizes. Adopt this architecture → representative research cycle → component evaluation narrative. Do not copy the biological content or claim comparable experimental autonomy. DOI: 10.1038/s41586-026-10652-y.
2. **Chen et al., RSS XXII (2026), “Bridging Language and Physics: Automated Design of Continuum Robots with Large Language Models” (AID-SR).** This is the closest continuum-robot reference: it uses simulator-derived physical feedback for LLM design, reports a 14-task portfolio, and includes three fabricated designs. It motivates a visible task-coverage figure and a separate hardware-validation figure. Our distinction is the explicit scientific-question/PPRP layer, task-conditioned mathematical analysis, and independent evidence paths—not the first LLM-based continuum-robot design. DOI: 10.15607/RSS.2026.XXII.194.
3. **SoftZoo, ICLR (2023), and Evolution Gym, NeurIPS (2021).** Their benchmark presentation organizes outcomes across task/environment families rather than collapsing heterogeneous tasks into one raw-error average. Use a compact task-condition matrix and retain task-specific metrics. SoftZoo: OpenReview id Xyme9p1rpZw; Evolution Gym: NeurIPS 2021.
4. **Feng et al., Nature Reviews Methods Primers (2026), “Agentic AI systems for scientific discovery.”** Its figure sequence separates overview, operational architecture, case construction, result analysis, and applications. Use the same hierarchy: framework first, then physical research cases, then architecture-level evaluation. DOI: 10.1038/s43586-026-00534-y.

## Main figures

### Figure 1 — Physics-grounded agentic research framework
- Source: the user's final approved editable architecture SVG; Codex must locate the actual SVG in the project workspace.
- Four regions: (a) Agentic Research, (b) Mathematical Research, (c) Design & Physical Validation, (d) Evidence & Feedback.
- Preserve the distinction between Main Agent decision authority, deterministic PPRP compilation, parallel M0–M3 semantics, independent mathematical/physical evidence, optional direct physical test, and read-only Reporter.
- Keep the SVG editable and retain a vector PDF for LaTeX.

### Figure 2 — Eleven-task physical research portfolio
- Use a matrix with one row per T01–T10/PHS-2D.
- Columns: task family, active/passive, morphology/actuation family, required conditions, principal physical metric, and outcome.
- Add small native-rendered structure thumbnails only where exact source assets exist.
- Show 30/30 required conditions as the portfolio-level count; keep T10's two frozen controls separate.
- Do not compute a pooled mean across heterogeneous task errors.

### Figure 3 — PHS-2D mechanism-guided design evolution
- Show a small number of actual candidate stages (e.g. F0/F1, finite-load/geometry diagnosis, guide-clearance revision, material refinement, final F8), selected from the original candidate and research-process records.
- Pair each structural stage with its discriminating observation: tendon slackness/local response, finite-load settling, route/solid intersection, connector clearance, loaded-point margin, and final ten-condition acceptance.
- Treat the sequence as evidence-driven research decisions, not a monotonic optimizer convergence curve.
- Use only exact MuJoCo/native-rendered source assets and frozen values from the nine-segment Round-3 package.

### Figure 4 — Local implicit-gradient consistency
- Scatter plot: KKT-based implicit task-metric derivatives versus re-equilibration finite differences.
- 18 points = six loading branches × three task metrics.
- Include the y=x reference and a compact relative-discrepancy panel/labels.
- Caption must state that all 18 pairs follow one common Young's-modulus direction across the nine segments; they are not 18 independent design-parameter gradients.
- Highlight maximum relative discrepancy 0.1191223%.

### Figure 5 — Representative autonomous research trajectories
- Four concise rows: PHS-2D, T04, T07, T10.
- Each row follows observation → hypothesis → selected mathematical/physical investigation → design/control action → independently evaluated outcome.
- PHS-2D emphasizes the local-to-finite-load-to-route-geometry change.
- T04 emphasizes route and initialization changes before full 22-s tracking.
- T07 emphasizes rejection of the longer structure, route revision, and condition-specific control initialization.
- T10 emphasizes the switch to native state feedback/LQR.
- Keep each row to a few evidence-backed nodes; do not turn the figure into a dense trace dump.

### Figure 6 — Architecture component decision replays
- Panel (a), Reporter: paired OFF/ON dumbbell/slope plot for all six checkpoints; annotate mean 3.433→3.733 (+0.300), median paired difference 0, wins/ties/losses 2/4/0. A second compact panel may show the five dimension-level paired differences and unsupported-claim count 2→0.
- Panel (b), Knowledge/Skill: two 2×2 heatmaps, one for T04 and one for T07, showing historical-experience utilization 0/3/3/3. Explicitly show that decision quality, evidence consistency, and actionability are all 4 in every cell.
- Do not add significance stars, error bars, or inferential language.
- Existing detailed SVGs: `knowledge_skill/figure_data/T04_knowledge_skill_2x2.svg` and `T07_knowledge_skill_2x2.svg`. Retain these as detailed supplementary figures if the main figure uses a compact summary.

### Figure 7 — Flat versus hierarchical context
- Panel (a), E2/C035: accepted-inference actual input 675,802 versus 78,785 (88.34% reduction), blind score 4.0 versus 3.8, and zero evidence reads.
- Panel (b), E2-R2/C037: cumulative actual input 877,197 versus 174,298 (80.13% reduction), blind score 3.4 versus 3.6, and key-evidence coverage 5/5 versus 3/5.
- Panel (c): actual hierarchical retrieval path L0 → three parallel L3 reads; label that no L1/L2 reads occurred.
- Annotate C042 as excluded before inference by the preregistered capacity gate.
- Never mix actual Provider usage and generic tokenizer proxies in the same unlabeled axis. E2 uses accepted-inference actual usage because the rejected initial request has no usage; E2-R2 uses cumulative actual usage for all accepted requests.

### Figure 8 — Physical-robot validation
- Use selected existing hardware photographs, task frames, and synchronized measured signals.
- Keep platform configuration, task protocol, trial count, and measurements separate from MuJoCo results.
- Do not infer hardware performance from simulation trajectories.

## Main tables

- **Table I — Task portfolio:** 11 task cases, family, required-condition count, active/passive type.
- **Table II — FULL physical outcomes:** task-specific metrics and required-condition completion; T10 frozen controls separate.
- **Table III — Representative A/B/C comparison:** T01/T04/T07; identify C as historical FULL and preserve the task-wise scope.
- **Table IV — Architecture decision-replay summary:** Reporter, Knowledge/Skill, E2, E2-R2; include unit of analysis, sample count, score/cost outcome, and measurement basis.

## Supplementary / appendix figures and tables

- Full T04 and T07 2×2 Knowledge/Skill plots (existing SVG/PDF).
- Full six-pair Reporter score table and per-dimension differences.
- E2/E2-R2 per-request token accounting, blind score dimensions, coverage, and retrieval records.
- Full ten-condition PHS-2D metrics and the 18 derivative pairs.
- Full A/B/C task-wise condition table and resource records.

## Data source map (source branch: paper/p0-dataset-20261114; source commit: b97bee811)

- Root index: `paper_experiment_data/architecture_ablation/PLOTTING_INDEX.json`
- Reporter: `reporter_on_off/pairwise_results.csv`, `scores_unblinded.csv`, `figure_data/reporter_comparison_table.csv`, `token_costs.csv`, `REPORTER_ABLATION_SUMMARY.md`
- E1 Knowledge/Skill: `knowledge_skill/figure_data/factorial_results.csv`, `factorial_effects.csv`, `interaction_effects.csv`, `execution_accounting.json`, `figure_data/T04_knowledge_skill_2x2.svg`, `figure_data/T07_knowledge_skill_2x2.svg`
- E2: `context_flat_vs_l0_l3/figure_data/figure_data.json`, `decision_scores.csv`, `token_request_accounting.json`, `figure_layout_suggestion.md`
- E2-R2: `context_flat_vs_l0_l3_v2/figure_data/pairwise_results.csv`, `decision_scores.csv`, `retrieval_path.csv`, `token_accounting_per_request.csv`, `positive_context_clips.md`, `pre_registered_protocol.md`, `completion_check.json`, `entry_confirmation.json`

## Global visual and statistical rules

- Use the same restrained palette as the approved architecture figure: deep blue, gold, green, and purple, with white backgrounds and light tints.
- Use consistent typography, axis sizes, units, and line weights across figures.
- Prefer paired plots for paired decision replays; show individual observations and exact sample counts.
- No fabricated repetitions, confidence intervals, significance markers, or success-rate estimates.
- Do not describe one decision per factorial cell as a replicated experiment.
- Do not label generic o200k_base estimates as actual Provider tokens or billing.
- Do not claim that a retrieved record caused a decision change unless a pre-read Plan or controlled counterfactual establishes that link.
- Show positive results prominently while keeping the accompanying evidence-coverage and measurement basis visible.
