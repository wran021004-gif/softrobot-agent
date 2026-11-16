# Manuscript Figure and Table Plan — Architecture Ablation Integration

## Positioning

The primary contribution is **physics-grounded agentic scientific research for soft-robot co-design**. Structure–control decoupling, mechanism diagnosis, sensitivity analysis, optimization, and physical validation are the domain-specific scientific capabilities coordinated by the agent. Do not frame autonomous research and structure–control optimization as competing contributions.

## Publication precedents

1. **Gottweis et al., “Accelerating scientific discovery with Co-Scientist,” Nature 655, 487–496 (2026), DOI: 10.1038/s41586-026-10644-y.** Fig. 1 combines system overview, agent architecture, and end-to-end validation; Fig. 2 reports scaling and blinded expert assessment; component ablations appear in Supplementary Figs. 2–6. Follow this hierarchy: one central method figure, domain-level results, and compact component ablations with detailed protocols in an appendix/supplement.
2. **Chen et al., “ScienceAgentBench,” ICLR 2025.** Fig. 1 combines task taxonomy with representative scientific outputs; evaluation separates executable outcomes and computational cost. Follow this by showing task-family coverage and representative robot outputs together, while keeping physical outcomes, decision quality, and token cost as distinct measurements.
3. **AID-SR, Robotics: Science and Systems 2026.** Use as a robotics-specific precedent for presenting a physics-grounded design loop and multiple soft/continuum-robot task cases. Do not compare its task-success percentages directly with our frozen task contracts.

## Main figures

### Fig. 1 — Physics-grounded agentic research framework
- Import the user's latest approved, genuinely editable architecture SVG. Do not reconstruct it from a screenshot.
- Preserve the four panels, parallel M0–M3 semantics, independent mathematical/physical evidence paths, read-only Reporter, and optional direct physical-test path.
- Main-text anchor: Section 4.

### Fig. 2 — Eleven-task portfolio and physical coverage
- Task-family matrix: active/passive, family, segment/tendon morphology, required-condition count, representative physical output.
- Add small MuJoCo-native thumbnails by task family; do not use eleven oversized screenshots.
- T10's two frozen controls are separate from its three required conditions.
- Data: `ALL_TASK_RESULTS.csv`, `TASK_CASE_RESULTS.csv`, `SOURCE_DATA/MODEL_BINDINGS.json`.

### Fig. 3 — PHS-2D mechanism-guided passive design
- F0/F3/F6/F8 structural evolution at identical camera and scale.
- Pair with ten required load cases showing loaded-point displacement, projected tip displacement, and ratio.
- Keep the nine-segment Round-3 package separate from older seven-segment snapshots.
- Data: `PHS_CANDIDATE_INDEX.csv`, `FIGURE_DATA/PHS_CANDIDATE_PROGRESS.csv`, `TASK_CASE_RESULTS.csv`.

### Fig. 4 — Local implicit-gradient consistency
- Six loading branches × three task metrics = 18 paired derivatives.
- Panel A: implicit KKT derivative versus finite-difference re-equilibration scatter with identity line.
- Panel B: relative discrepancy by branch and metric.
- State that all pairs follow one common Young's-modulus perturbation direction across nine segments.
- Data: `PHS2D_9SEG_GRADIENT_FIGURE_DATA.csv`.

### Fig. 5 — Evidence-to-action research trajectories
- Four concise timelines: PHS-2D, T04, T07, T10.
- Each row follows observation → hypothesis → mathematical/physical investigation → structure/control action → independent physical result.
- Include informative rejected hypotheses and route changes; every transition must link to an existing decision/Trace/candidate ID.
- Data: `KEY_RESEARCH_NODES.csv`, `RESEARCH_PROCESS.md`, `CANDIDATE_EVOLUTION.csv`, `SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json`.

### Fig. 6 — Research-mode comparison (A/B/C)
- A compact 3-task × 3-method matrix for T01, T04, T07.
- Show status and normalized constraint-violation fraction; mark T04-B as a pre-execution qualification failure.
- C is historical FULL, not a newly randomized run.
- Data: `FINAL_ABC_DATASET_P0_20261114/D1_ABC_STATUS_MATRIX.csv`, `RESOURCE_COSTS.csv`.

### Fig. 7 — Architecture decision studies: Reporter and Knowledge/Skill
- Panel A: six Reporter OFF/ON paired mean scores (M1-A/B/C, P3-A/B/C), paired connectors, means 3.433→3.733, median paired delta 0, win/tie/loss 2/4/0.
- Panel B: T04 and T07 side-by-side 2×2 heatmaps; horizontal Skill OFF/ON, vertical Knowledge OFF/ON. Historical-experience utilization 0/3/3/3; decision quality, evidence consistency, and actionability remain 4 in every cell.
- Annotate descriptive K and S main effects (+1.5 each), interaction contrast (−3), joint-minus-best-single (0).
- No significance stars, confidence intervals, population synergy, or robot-success labels.
- Data: `architecture_ablation/reporter_on_off/pairwise_results.csv`, `knowledge_skill/figure_data/factorial_results.csv`, `factorial_effects.csv`, `interaction_effects.csv`.

### Fig. 8 — Hierarchical context: efficiency, decision quality, evidence coverage
- Panel A: E2 C035 and E2-R2 C037 actual Provider input. E2 accepted inference only (675,802 vs 78,785; −88.34%); E2-R2 cumulative accepted requests (877,197 vs 174,298; −80.13%). Never merge cost bases.
- Panel B: paired blind mean and key-evidence coverage. E2: 4.0 vs 3.8, no extra reads. E2-R2: 3.4 vs 3.6, coverage 5/5 vs 3/5.
- Panel C: E2-R2 L0 → three parallel L3 records (C031 qualifications, C034 qualifications, C036 route geometry) → final scoped diagnostic Plan. Show no L1/L2 reads.
- Mark C042 as excluded before inference by the preregistered capacity gate. Separate actual Provider usage from generic tokenizer proxies.
- Data: `context_flat_vs_l0_l3/figure_data/context_comparison_table.csv`, `context_flat_vs_l0_l3_v2/figure_data/pairwise_results.csv`, `retrieval_path.csv`, `positive_context_clips.md`.

### Fig. 9 — Real-world validation
- Only include existing hardware platform and measured demonstrations.
- Use synchronized physical frames and measured trajectories/metrics from original hardware records.
- Keep simulation and hardware metrics/trial counts separate.

## Main tables

1. Table I — Task portfolio: eleven tasks, family, morphology, required conditions.
2. Table II — FULL outcomes: task-specific final metrics and pass counts; no cross-task raw-error average.
3. Table III — A/B/C comparison: T01/T04/T07 status and normalized violation; historical C explicit.
4. Table IV — Architecture decision studies: Reporter, Knowledge/Skill, E2, E2-R2 with sample unit, score, cost basis, evidence coverage, and interpretation scope.
5. Table V — PHS-2D and gradient audit: ten-condition metrics and 18-pair sensitivity consistency, with common-modulus direction stated.

## Appendix and visual language

- Appendix D retains full replay protocols, rubrics, sample units, model/backend identity, transport corrections, actual-versus-proxy token accounting, and interpretation boundaries.
- Supplementary tables should hold full six-pair Reporter scores, all T04/T07 2×2 cells, per-request context accounting, and detailed decision clips.
- Preserve raw sessions, request/response logs, candidate histories, and provenance in the experiment repository; do not paste raw traces into the main text.
- White background, compact IEEE/TRO typography, restrained palette consistent with Figure 1.
- Use consistent colors for Agent, mathematical evidence, physical evidence, and context resources.
- Robot geometry must come from MuJoCo-native renders.
- Prefer paired dots/lines, heatmaps, timelines, and task matrices over decorative dashboards.
- Never invent error bars, confidence intervals, repeated-run means, token counts, trial counts, or physical outcomes.
