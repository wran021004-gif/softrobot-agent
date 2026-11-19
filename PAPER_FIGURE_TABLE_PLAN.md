# Phase-5 Figure and Table Plan

## Narrative

The main results follow one visual argument:

**Agent decisions → mathematical and physical evidence → integrated structural outcomes.**

Figure 1 remains the approved editable architecture figure already imported into Overleaf and is not modified by this phase. Figure 2 establishes benchmark breadth. Figures 3--5 then separate the Agent research process, evidence validation, and resulting physical designs. Figures 6--7 retain the method comparison and research-continuity studies.

## Main figures

### Figure 1 — Framework
Preserve the approved Overleaf architecture SVG and its inclusion environment. Do not replace, redraw, or re-import it during the manuscript sync.

### Figure 2 — Eleven-task benchmark suite
Organize all eleven FULL task cases into four functional families:
- Reach and dynamic motion: T01--T04.
- Pose and contact interaction: T05, T06, T09.
- Shared morphology and control: T07, T10.
- Passive mechanics: T08, PHS-2D.

List every task, required-condition completion, and its principal task-specific physical metric. Retain task-native units.

### Figure 3 — Agent-Directed Research Process
Show the common research-decision path and three representative cases:
- T04: initialization diagnosis, equilibrium-consistent restart, boundary-tension adjustment, and equilibrium-bank construction.
- T07: shared-morphology research question, fixed-input M1 investigation, re-optimized M2 control capability, and evidence returned to the Main Agent.
- T10: GVS/NMPC recovery conflict, controller-formulation change, native tangent model, discrete LQR, and bounded tension allocation.

The figure explains why the Agent selects an investigation and how it changes the research route. Do not repeat detailed structural renderings or quantitative structure-performance plots here.

### Figure 4 — Mathematical and Physical Evidence Validation
Panel A: eighteen implicit equilibrium derivative/central finite-difference pairs, shown as three parity facets for loaded-point displacement, projected tip displacement, and tip-to-point ratio. Show 18/18 sign agreement, 0.0260% median discrepancy, and 0.1191% maximum discrepancy.

Panel B: compact 10-by-3 physical validation matrix for the ten signed-loading conditions and the three checks: independent-process reproduction, half timestep, and initial-state perturbation. Use equal visual weight for all ten conditions.

### Figure 5 — Agent-Guided Structural Research and Physical Outcomes
Use a two-column structure-to-outcome layout.

**PHS-2D**
- Left: initial, intermediate, and final native structure renders; label the actual structural changes (one segment/two tendons → one segment/four tendons with denser guide routing → nine segments/four tendons/eight guide plates).
- Add a final guide-plate inset with four tendon holes and a side-view routing sketch.
- Right: signed-load response and the three physical metrics: loaded-point displacement, projected tip displacement, and tip-to-point ratio. Show the 10 mm loaded-point target and 0.3 ratio threshold.

**T07**
- Left: ellipse and circle root cross-sections at the same scale, with four tendon positions from the candidate design; add the side-view distinction between the two near-segment tendons and the two tendons routed through the intermediate guide.
- Right upper: M1 fixed-input comparison for maximum geometric tendon speed and maximum position error.
- Right lower: M2 four-condition result on one shared modified morphology, with four task-specific control solutions and 4/4 completion.

### Figure 6 — Research-mode comparison
Show the 11-by-3 A/B/FULL matrix with status, evaluated/required coverage, and known normalized violation. Retain the original task-specific reporting semantics.

### Figure 7 — Research continuity
Combine Reporter matched-pair results, original Knowledge/Skill utilization, and the historical context comparisons. Show context input reduction alongside decision scores and evidence coverage.

## Main tables
- Table I: four-family benchmark coverage and required-condition completion.
- Table II: A/B/FULL task-wise outcomes, grouped by the same four task families as Figure 2.
- Detailed task-native metrics remain in the task-portfolio appendix.

## Visual style
White background; restrained Navy/Teal/Slate palette; native MuJoCo renders; consistent camera and lighting. Use concise labels and print-scale typography. Prefer editable SVG vector shapes and text for all diagrammatic content. Avoid dashboard tiles, shadows, gradients, and decorative fills.
