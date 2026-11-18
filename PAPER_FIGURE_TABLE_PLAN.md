# Phase-2 Figure and Table Plan

## Narrative

The main paper should let the reader see the robot, understand how its structure or research route changed, and then inspect the physical evidence. Figure 1 remains frozen. Figures 2--4 use the actual MuJoCo renders and saved execution plots from the current task archive.

## Main figures

### Figure 1 — Framework
Keep the approved Overleaf figure unchanged. Do not import or substitute the older GitHub TikZ drawing during Overleaf synchronization.

### Figure 2 — Structural evolution and Agent decisions
- PHS-2D: actual MuJoCo F0 initial diagnostic, F3 intermediate and F8 accepted final morphology with native lighting, floor and shadows.
- T07: actual elliptical-root and round-root candidates.
- Each task couples native design changes with a compact, evidence-grounded Agent hypothesis / action / outcome line; no cards or decorative speech bubbles.
- Text is a concise editorial paraphrase of archived decision records, not a verbatim hidden internal thought trace.
- Reader-facing label is PHS-2D. Detailed Study identity remains in source data; do not pool two distinct studies.

### Figure 3 — Agent research traces and quantitative execution
- Two full-width study rows, T04 and T10.
- T04: earlier native state, final native state, measured 22-s figure-eight tracking curve. Include original Agent observation of an inadmissible all-4 N initialization, the 0.20 to 0.21 N bound-interior adjustment, the 89-point equilibrium bank and the final 0.688-mm RMSE.
- T10: preimpact, pulse and postimpact MuJoCo states plus the actual route-comparison graph. Explain Agent decision to replace GVS/NMPC with native tangent-model LQR and bounded tension allocation; keep the same morphology throughout.
- Use native visuals + agent output + executed action + physical evidence as one coherent trace. No colored cards, excessive explanatory footnotes or fabricated chain-of-thought passages.
- Do not portray incomplete initial T04 work as a fully evaluated physical baseline.
- C1 companion quantitative panel: [verified Evidence-to-Action audit](paper_experiments/C1_EVIDENCE_TO_ACTION_AUDIT_20261118/AUDIT_REPORT.md). Use the actor-stratified funnel and executed counts by task; do not relabel external Codex work as Main Agent observations.

### Figure 4 — Contact execution and task evidence
- T09: native MuJoCo approach, maximum button displacement and held-contact states, plus recorded displacement/force curves.
- A brief Agent observation/action line links unintended contacts and corrected contact setup; do not imply the guiding hardware was removed.
- Report only final measured 0.5-s depth/force hold and native outcome metrics; leave full timing and evaluator details to supplement.

### Figure 5 — Local mathematical sensitivity
- Preserve the existing implicit-derivative versus finite-difference comparison.
- State that 18 pairs represent six loading branches by three metrics along one common material-parameter direction.
- Maximum relative discrepancy: 0.1191%.
- C2 companion audit: [T07 M1/M2 results](paper_experiments/T07_M1_M2_PAIRED_VALIDATION_20261118/RESULTS.md). Show the measured M1_B fixed-input contrast and unpaired d1 M2 endpoints. No M2 structure-effect line or claims from nonconverged controls.

### Figure 6 — Architecture decision studies
- Reporter six-pair OFF/ON comparison.
- Original Knowledge/Skill utilization and supplemental four-checkpoint replay.
- Keep decision-only results distinct from physical task success.

### Figure 7 — Hierarchical context
- Historical actual Provider-usage pairs and six cross-task decision/evidence pairs.
- Keep unavailable Provider usage distinct from local text-token estimates.

## Main tables

### Table I — Physical task portfolio
Eleven rows grouped by active control, shared-morphology design, and passive mechanics. Each row reports the task's native metric and unit. Do not pool unlike errors or repeat all evaluator fields.

### Table II — A/B/FULL task comparison
Use the same 11 task rows, grouped by task family. Columns are A, B, and FULL. Report Pass, valid failure with evaluated-constraint violation fraction, incomplete evaluation, or qualification failure. Bold passing results; mark the T03-B protocol variant with a dagger and one concise note.

Both tables use traditional IEEE booktabs grouping: no vertical rules, cell shading, dashboard boxes, or explanatory paragraphs inside cells. Keep category grouping with fine horizontal rules and bold fully passed method results. Avoid explanatory paragraphs inside cells.

## Supplementary material
Retain the full condition-level metrics, complete A/B/FULL matrix, task-specific thresholds, all decision records, source indices, and detailed architecture/context protocols. Use PHS-2D as the reader-facing name while retaining exact study identifiers only in underlying source metadata.
