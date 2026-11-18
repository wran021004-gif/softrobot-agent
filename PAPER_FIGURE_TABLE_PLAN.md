# Phase-2 Figure and Table Plan

## Narrative

The main paper should let the reader see the robot, understand how its structure or research route changed, and then inspect the physical evidence. Figure 1 remains frozen. Figures 2--4 use the actual MuJoCo renders and saved execution plots from the current task archive.

## Main figures

### Figure 1 — Framework
Keep the approved Overleaf figure unchanged. Do not import or substitute the older GitHub TikZ drawing during Overleaf synchronization.

### Figure 2 — Structural evolution
- PHS-2D: initial diagnostic, intermediate candidate, accepted final structure.
- T07: ellipse-root candidate and final round-root morphology.
- Use only candidates with original physical models; do not fabricate missing T07 candidate renders.
- Keep the same camera and scale within each task.
- Use no card backgrounds, arrows over the robot, or dense annotations.

### Figure 3 — Evidence-guided research trajectories
- T04: incomplete GVS route, native equilibrium-point bank, tension feedforward, complete 22-s tracking.
- T10: GVS/NMPC route, native tangent model/discrete LQR, bounded tension allocation, three required conditions.
- Display the robot states and the task-specific tracking/control plots.
- Keep frozen-input controls separate from the required T10 conditions.
- Treat these as selected archived research records, not additional task trials.

### Figure 4 — Contact execution
- T09: approach, maximum button travel, and joint depth/force holding states.
- Pair the native renders with the recorded depth and contact-force curves.
- Report the 0.5-s hold and task-specific maximum errors in the caption or nearby prose.

### Figure 5 — Local mathematical sensitivity
- Preserve the existing implicit-derivative versus finite-difference comparison.
- State that 18 pairs represent six loading branches by three metrics along one common material-parameter direction.
- Maximum relative discrepancy: 0.1191%.

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

Both tables use booktabs, no vertical rules, no cell shading, compact but readable spacing, and bold best results. Avoid explanatory paragraphs inside cells.

## Supplementary material
Retain the full condition-level metrics, complete A/B/FULL matrix, task-specific thresholds, all decision records, source indices, and detailed architecture/context protocols. Use PHS-2D as the reader-facing name while retaining exact study identifiers only in underlying source metadata.
