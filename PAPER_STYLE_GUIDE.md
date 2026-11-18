# Manuscript style and notation guide

This is the manuscript-wide reference for terminology, mathematical notation, and visual style. Figure 1 is frozen and must not be edited.

## Canonical task names

| ID | Canonical name |
|---|---|
| T01 | Multi-target Reach-and-Hold |
| T02 | Load-Conditioned Hold |
| T03 | Fast Target Reaching |
| T04 | Figure-Eight Trajectory Tracking |
| T05 | End-Effector Position and Tool-Axis Alignment |
| T06 | Loaded Time-Indexed Pose Scanning |
| T07 | Shared-Morphology Multi-Task Design |
| T08 | Passive Progressive-Stiffness Response |
| T09 | Guided Spring-Button Contact Manipulation |
| T10 | Impact-Recovery Control |
| PHS-2D | Passive Tendon-Constrained Compliance and Tip Suppression |

Use **PHS-2D** in all reader-facing text, tables, legends, and captions. Preserve exact study/candidate identifiers only in source metadata and supplementary provenance; do not expose segment-count suffixes in the manuscript.

## Canonical terms

Use Physics-Grounded Agentic Research, Main Agent, Reporter, Research Intent, Parameterized Physical Research Problem (PPRP), Analysis Semantics, Mathematical Evidence, Physical Evidence, Research Decision, Design Candidate, Independent Physical Evaluation, and Structure--Control Co-design.

Use Physics-Grounded, not Physics-Guided. M0--M3 are complementary analysis semantics, not a mandatory pipeline. The Main Agent owns scientific decisions. The Reporter is read-only.

## Mathematical notation

| Symbol | Meaning |
|---|---|
| \(\tau\) | Frozen task contract |
| \(d\) | Robot design/morphology |
| \(\mathcal D\) | Admissible design space |
| \(\theta\) | Controller parameters |
| \(U\) | Actuation/control sequence |
| \(q\) | Generalized coordinates |
| \(g_{\tau,i}\) | Normalized task-constraint violation |
| \(V_\tau(d)\) | Best achievable task violation after control re-optimization |
| \(s_k\) | Research state |
| \(\mathcal H_k\) | Working physical hypotheses |
| \(\mathcal E_k\) | Accumulated evidence |
| \(a_k\) | Research action |
| \(y_k\) | Observation returned by an action |
| \(\mathcal P_k\) | PPRP |
| \(\mathcal I_k\) | Selected parameter group |
| \(\mathcal O_k\) | Selected observables |
| \(\mathcal F_k\) | Inner physical problem/model |
| \(\sigma_k\) | Selected analysis semantics |
| \(\mathcal B_k\) | Research budget |
| \(z_{\mathrm{cl}}\) | Combined structure/controller vector \((d,\theta)\) for M3 |
| \(\mathcal M_{\mathrm{hi}}\) | High-fidelity physical execution model in M3 |
| \(N\) | Final sampled trajectory index |
| \(J_{\tau}^{\mathrm{cl}}\) | Closed-loop performance functional in M3 |
| \(w_{\mathcal A}\) | Passive-equilibrium primal/dual state \((q,\mu_{\mathcal A})\) |

Evidence is written as \(\mathcal E_k=(\mathcal E_k^{\mathrm{math}},\mathcal E_k^{\mathrm{phys}})\). Use \(\mu_{\mathcal A}\) for passive-equilibrium multipliers and \(\lambda_i\) for M2 task-constraint multipliers. Do not reuse \(z\) for both the M3 design/controller vector and passive-equilibrium state.

## M0--M3

- M0: mechanism sensitivity, \(\partial m(d)/\partial d_j\).
- M1: fixed-input response, \(\partial g_{\tau,i}(d,U_0)/\partial d_j\).
- M2: re-optimized task capability, \(\partial V_\tau(d)/\partial d_j\), under stated optimality/regularity conditions.
- M3: closed-loop performance, \(\nabla_{z_{\mathrm{cl}}}J_{\tau}^{\mathrm{cl}}(d,\theta;\mathcal M_{\mathrm{hi}})\).

Passive-equilibrium response sensitivity is calculated through the equilibrium/KKT system and is not mislabeled as M2 active-control capability.

## Publication palette

| Color | Hex | Fixed meaning |
|---|---|---|
| Deep Navy | #26384B | Primary method / labels |
| Muted Teal | #527F7B | Mathematical evidence |
| Slate Blue | #70849A | Physical evidence |
| Muted Ochre | #B08A59 | Structure modification |
| Forest Green | #557663 | Verified pass |
| Muted Brick | #A35D55 | Failure / constraint violation |
| Neutral Gray | #929BA4 | Baseline / historical |
| Light Gray | #D9DEE2 | Grid / auxiliary |

## Figure and table styling

- White background; no rounded cards, drop shadows, gradients, dashboard tiles, or decorative color fills.
- Use native MuJoCo renders for robot structure and state images.
- Use restrained, consistent lighting and a fixed camera for candidate comparisons.
- Use Helvetica/Arial-style labels, normally 8--9 pt at final print size.
- Use booktabs for tables: no vertical rules, no colored cells, clear group separators, and boldface for the best result within each row.
- Use concise captions; put protocol detail and source information in the supplement.
- Show UNKNOWN as unavailable, never as zero.
- Do not average raw errors across different task families.
- Do not add unobserved confidence intervals, repetitions, significance markers, or physical outcomes.
