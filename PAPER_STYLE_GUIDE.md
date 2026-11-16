# Manuscript style and notation guide

This file is the single manuscript-wide reference for task naming, mathematical notation, and visual semantics. Figure 1 is frozen and must not be edited. All subsequent figures should follow its conceptual hierarchy while using the publication palette below.

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

PHS-2D-7S is the passive case inside the eleven-case FULL portfolio. PHS-2D-9S is a separate independent mechanism study. Never combine their candidate histories, morphology, or measurements.

## Canonical terms

Use Physics-Grounded Agentic Research, Main Agent, Reporter, Research Intent, Parameterized Physical Research Problem (PPRP), Analysis Semantics, Mathematical Evidence, Physical Evidence, Research Decision, Design Candidate, Independent Physical Evaluation, and Structure--Control Co-design.

Use Physics-Grounded, not Physics-Guided, for the proposed framework. M0--M3 are complementary analysis semantics, not a mandatory sequence. The Main Agent owns scientific decisions. The Reporter is read-only.

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
| \(w_{\mathcal A}\) | Passive-equilibrium primal/dual state \((q,\mu_{\mathcal A})\) |

Evidence is written as \(\mathcal E_k=(\mathcal E_k^{\mathrm{math}},\mathcal E_k^{\mathrm{phys}})\). Use \(\mu_{\mathcal A}\) for passive-equilibrium multipliers and \(\lambda_i\) for M2 task-constraint multipliers. Do not reuse \(z\) for both the M3 design/controller vector and passive-equilibrium state.

## M0--M3

- M0: mechanism sensitivity, \(\partial m(d)/\partial d_j\).
- M1: fixed-input response, \(\partial g_{\tau,i}(d,U_0)/\partial d_j\).
- M2: re-optimized task capability, \(\partial V_\tau(d)/\partial d_j\), under stated optimality/regularity conditions.
- M3: closed-loop performance, \(\nabla_{z_{\mathrm{cl}}}J_{\tau,H}(d,\theta)\).

Passive-equilibrium response sensitivity is calculated through the equilibrium/KKT system and is not mislabeled as M2 active-control capability.

## Publication palette

| Color | Hex | Fixed meaning |
|---|---|---|
| Deep Navy | #26384B | Main Agent / primary method |
| Muted Teal | #527F7B | Mathematical Evidence |
| Slate Blue | #70849A | Physical Evidence |
| Muted Ochre | #B08A59 | Structure Modification |
| Forest Green | #557663 | Verified Pass |
| Muted Brick | #A35D55 | Failure / Constraint Violation |
| Neutral Gray | #929BA4 | Baseline / Historical |
| Light Gray | #D9DEE2 | Grid / Auxiliary |

## Figure styling

- White background; straight edges; no shadows, gradients, rounded cards, or dashboard tiles.
- Helvetica/Arial-style labels, 8--9 pt at final size; consistent line weights and axis styles.
- Use panel labels (a), (b), (c) and concise legends.
- Export vector PDF and SVG.
- Keep Figure 1 unchanged. Use its conceptual colors and hierarchy for all other figures.
- Show UNKNOWN as missing/hatched, never as zero.
- Do not average raw errors across different task families.
- Do not add unobserved confidence intervals, repetitions, significance markers, or physical outcomes.
