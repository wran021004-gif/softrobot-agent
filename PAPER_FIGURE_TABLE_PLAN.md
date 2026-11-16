# Authoritative Figure and Table Plan

This is the single authoritative manuscript figure/table plan. Figure numbering follows the current eight-chapter manuscript. Figure 1 is frozen and must not be redrawn.

## Scientific narrative

1. **Coverage:** eleven FULL task cases demonstrate breadth across active/passive soft-robot research.
2. **Mechanism:** the independent PHS-2D-9S study provides the detailed passive-design case.
3. **Mathematical evidence:** local implicit derivatives are checked against finite differences.
4. **Research decisions:** selected trajectories show how evidence changes hypotheses, structures, and control routes.
5. **Method comparison:** the 11-by-3 A/B/C matrix compares research modes.
6. **Research architecture:** Reporter, Knowledge/Skill, and hierarchical context are evaluated at the decision level.

## Figures

| Figure | Title | Primary claim | Source / current status |
|---|---|---|---|
| 1 | Physics-Grounded Agentic Research Framework | Main Agent decision authority, PPRP, complementary M0--M3, independent mathematical/physical evidence, read-only Reporter | Existing editable source; frozen |
| 2 | Task Portfolio and Physical Coverage | Eleven FULL cases span active/passive task families and task-specific physical requirements | figures/fig02_task_portfolio.tex; 30/30 required conditions |
| 3 | Mechanism-Guided Passive Design | PHS-2D-9S uses physical guide plates and tendon routing to retain loaded-point compliance while limiting tip motion | figures/fig03_phs2d_results.tex plus figures/fig03_phs2d_mechanism.svg; ten signed-load cases |
| 4 | Local Mathematical Sensitivity Validation | Implicit task-metric derivatives agree with finite differences along the tested common modulus direction | figures/fig04_gradient_validation.tex; 18 pairs, max relative discrepancy 0.1191% |
| 5 | Evidence-Guided Research Trajectories | Physical and mathematical evidence motivates research-route, morphology, and control changes | figures/fig05_research_trajectories.tex; PHS-2D-9S, T04, T07, T10 |
| 6 | Research-Mode Comparison | FULL research mode has broader task completion than the recorded A/B modes | figures/fig06_abc_matrix.tex; 33 task--method records |
| 7 | Reporter and Knowledge/Skill Decision Studies | Reporter improves two sampled decisions; Knowledge/Skill changes historical-experience use and decision profiles | figures/fig07_reporter_ks.tex; six Reporter pairs, 24 K/S sessions (23 valid) |
| 8 | Hierarchical Context and Evidence Utilization | Context organization changes request-text volume while decision quality and evidence recall remain separate outcomes | figures/fig08_context.tex; two historical Provider-usage pairs and six cross-task pairs |

## Tables

**Table I** is the only main-text data table. It contains canonical task ID/name, segment/tendon/actuator counts, and required-condition count. Do not duplicate the full condition metrics in another main-text table.

The complete A/B/C matrix, per-condition metrics, architecture scores, resource details, and all task-specific thresholds belong in the appendices/supplementary data.

## Panel-level instructions

### Figure 2
Use a compact task atlas with task family, morphology/actuation profile, required-condition count, and status. T10's two frozen controls are separate from its three required conditions. PHS-2D-7S is the PHS case in the eleven-task portfolio. PHS-2D-9S is not included in the FULL denominator.

### Figure 3
Panel (a) uses the actual final PHS-2D-9S mechanism illustration. Panels (b)--(c) use ten signed-load records at five material positions. Keep loaded-point displacement, tip displacement, and their ratio on separate axes. Do not merge PHS-2D-7S measurements into this figure.

### Figure 4
Show three parity plots (loaded-point displacement, projected tip displacement, and ratio) and one relative-error panel. State the tested derivative units and common modulus perturbation direction. Do not present the 18 pairs as 18 independent design-parameter directions. A matched M1/M2 physical comparison is not included until its fixed-input replays have actually been completed.

### Figure 5
Use four horizontal research trajectories: PHS-2D-9S, T04, T07, and T10. T07's intermediate signed-excess values are finite-budget native capability diagnostics, not matched fixed-input effects or independent physical acceptance.

### Figure 6
Show the complete 11-by-3 A/B/C status matrix. Preserve incomplete, qualification-failed, valid-failure, and qualified-pass states. C is the historical FULL record. Do not convert the matrix into a single pooled success-rate claim.

### Figure 7
Panel (a): six Reporter paired scores, including all four ties. Panel (b): original E1 historical-experience utilization under the K/S 2-by-2 design. Panel (c): common five-dimensional reassessment across six frozen checkpoint groups; retain the budget-exhausted K+S+ decision. Report the sixteen-session supplemental K/S text-volume total separately.

### Figure 8
Panel (a): Provider-reported input for historical E2 and E2-R2. Panel (b): serialized request-text volume for six cross-task pairs, including the failed T08 Flat session. Panel (c): blind decision quality. Panel (d): key-evidence recall. Do not merge the two historical Provider-usage pairs with the new serialized-text counts.

## Global visual system

White background; straight panel boundaries; no shadows, rounded cards, dashboard tiles, or gradients. Use a consistent, restrained palette:

- Main Agent: #26384B
- Mathematical evidence: #527F7B
- Physical evidence: #70849A
- Structural modification: #B08A59
- Verified pass: #557663
- Failure/violation: #A35D55
- Baseline: #929BA4
- Auxiliary lines: #D9DEE2

Use color and line/marker shape together. Use Helvetica/Arial-like figure labels at 8--9 pt at final size. Prefer vector PDF/SVG output. Keep robot structures at matched camera, scale, orientation, and lighting when rendered from MuJoCo. Figure 1 remains unchanged.

## Numerical conventions

Keep full precision in source CSV. Display lengths in mm with three decimals, angles in rad with four decimals, ratios with four decimals, scores with one decimal, and counts/tokens as integers. State units on each panel. Never plot UNKNOWN as zero.

For the 28 supplemental K/S and context sessions, serialized request-text tokens are reconstructed from recorded payload text using o200k_base; they are not Provider billing or hidden-reasoning usage. Historical E2/E2-R2 input counts are Provider-reported and must remain a separate measurement category.
