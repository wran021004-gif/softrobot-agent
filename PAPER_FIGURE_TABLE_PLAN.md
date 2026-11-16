# Authoritative Figure and Table Plan — Phase 1

## Manuscript narrative

The paper is organized around one scientific claim: physics-grounded agentic research makes the selection and revision of soft-robot co-design questions an explicit, evidence-driven process.

The visual narrative is:
1. Framework (Fig. 1).
2. Breadth of physical task evidence (Fig. 2).
3. A deep passive mechanism-design case (Fig. 3).
4. Local mathematical consistency (Fig. 4).
5. Evidence-guided research trajectories (Fig. 5).
6. Full task-wise research-mode comparison (Fig. 6).
7. Decision-level Reporter and Knowledge/Skill studies (Fig. 7).
8. Context efficiency and evidence coverage (Fig. 8).

Figure 1 is frozen. Do not redraw, recolor, relabel, or replace its editable source. Other figures follow its semantic hierarchy and the palette in PAPER_STYLE_GUIDE.md.

## Main figures

### Figure 1 — Physics-Grounded Agentic Research Framework
Keep the currently approved editable source and vector PDF unchanged.

### Figure 2 — Task Portfolio and Physical Coverage
- One row for each of the eleven FULL cases: T01--T10 and PHS-2D-7S.
- Show task family, active/passive regime, segment/tendon/actuator morphology, required-condition count, and one to three named task-specific physical outputs.
- Show the 30 required conditions and keep T10's two frozen controls separate.
- Never use a pooled raw-error axis across different task families.
- Use exact model thumbnails only when the corresponding native render exists. The task matrix remains legible without thumbnails.

### Figure 3 — Mechanism-Guided PHS-2D-9S Design
- This is an independent nine-segment study, not the seven-segment FULL PHS-2D case.
- Panel (a): four actual Journal stages: diagonal stay, dense tendon guidance, physical guide plates, final nine-segment structure.
- Render actual XML/models at a common camera, scale, orientation, lighting, and material.
- Panel (b): ten signed-load cases, loaded-point and projected-tip displacement.
- Panel (c): tip-to-point ratio and matched tendon tension/taut-state evidence.
- Report 10/10 conditions, 11.155 mm minimum loaded-point displacement, 3.068 mm maximum projected tip displacement, and 0.1093 maximum ratio.
- Do not substitute seven-segment candidate images or use conceptual drawings as if they were simulation renders.

### Figure 4 — Local Mathematical Sensitivity Consistency
- Panel (a): implicit derivative versus finite-difference derivative, faceted by the three metrics and their units.
- Panel (b): relative discrepancy for six signed-loading branches and three metrics.
- State that all 18 pairs follow one common normalized Young's-modulus direction across nine segments.
- Maximum relative discrepancy: 0.1191%.
- Do not include an empirical M1/M2 panel until the matched physical replay is executed. The current 12 rows are NOT_EXECUTED/UNKNOWN and belong in the supplementary protocol only.

### Figure 5 — Evidence-Guided Research Trajectories
- Four rows: PHS-2D-9S, T04, T07, T10.
- Each row follows observation → hypothesis → investigation → mathematical/physical evidence → structure/control action → recorded outcome.
- Retain rejected candidates and changes in research route.
- Label native finite-budget diagnostics separately from independent physical acceptance.
- Use 2--4 evidence-backed nodes per row; complete node data remain supplementary.

### Figure 6 — Eleven-Task Research-Mode Comparison
- Panel (a): 11×3 status matrix for A (LLM-only), B (Direct Mathematical Tools), and C (historical FULL).
- Panel (b): task-wise normalized violation among evaluated cases; UNKNOWN and incomplete cases remain missing.
- C passes all eleven FULL task cases.
- Preserve A/B valid failures, incomplete evaluations, and qualification failures as different states.
- Mark T03-B and T05-B as protocol-deviant direct-mathematical-only variants.
- Do not describe the matrix as a randomized causal comparison or pool raw task errors.

### Figure 7 — Research Architecture Decision Studies
- Panel (a): six paired Reporter OFF/ON mean scores with connectors; annotate 3.433→3.733, +0.300, median paired difference 0, and 2/4/0 win--tie--loss.
- Highlight M1-C (budget-boundary/unsupported initialization) and P3-A (missing directional tendon-ablation experiment) as two cases within the six pairs.
- Panel (b): original T04/T07 K/S 2×2 utilization results (0/3/3/3), with the three saturated original quality dimensions shown separately.
- Panel (c): four-checkpoint supplemental K/S results using the common five-dimensional review; retain the T07-074 K+S+ budget-exhausted cell.
- Do not claim synergy, significance, or physical-success improvement.

### Figure 8 — Hierarchical Context and Evidence Utilization
- Panel (a): two historical actual-usage pairs, grouped by accounting scope: E2/C035 accepted-inference usage (675,802→78,785; 88.34%) and E2-R2/C037 cumulative accepted-request usage (877,197→174,298; 80.13%).
- Panel (b): six new cross-task pairs showing blind decision quality and key-evidence recall on separate axes; preserve the failed Flat T08 session.
- Panel (c): actual L0→L3 retrieval path for E2-R2/C037.
- New Gateway Provider usage is UNKNOWN; do not plot local estimates as actual usage or claim measured cross-task token savings.
- Local serialized-text estimates are supplementary only and must be labeled as estimates.

### Figure 9 — Physical Robot Validation
Not included in the current compiled manuscript. Add only when a complete hardware platform, protocol, trial count, and measured outcome package is available.

## Main tables

Table I — Task Portfolio. Canonical task names, regime, morphology, and required-condition count. It is the only main-text data table in Phase 1.

Do not retain separate main-text tables that repeat the FULL outcomes, A/B/C matrix, or architecture summary. Their information is represented by Figs. 2, 6, 7, and 8. Full condition-level data and protocols belong in the appendix/supplement.

## Supplementary material

- Full task-specific thresholds, metrics, and condition-level values.
- Complete A/B/C matrix and resource-scope records.
- PHS-2D-7S and PHS-2D-9S data kept separate.
- All 18 gradient pairs and their common perturbation direction.
- Full 32-node research set and annotation records.
- Six Reporter pairs and the two positive-case decision excerpts.
- Original E1 four-dimensional scores, common five-dimensional reassessment, and all supplemental K/S cells.
- E2/E2-R2 per-request usage, six cross-task Context decisions, key-evidence checklist, and retrieval path.
- Local text-token estimates, clearly distinguished from Provider usage.
- Prepared but unexecuted T07 M1/M2 protocol.

## Figure build order

1. Fig. 6 and Fig. 7: data-backed matrix and paired decision plots.
2. Fig. 4 and Fig. 8: mathematical consistency and context trade-off.
3. Fig. 2 and Fig. 5: task portfolio and research trajectories.
4. Fig. 3: render the four actual PHS-2D-9S model stages and matched load cases.
5. Compile the complete IEEEtran manuscript and adjust float placement/legibility.
