# Paper claim map — research-oriented manuscript v1.0

The manuscript is organized around one scientific question: how can an LLM agent use mathematical and physical evidence to autonomously investigate and improve soft-robot structure and control?

## C1 — Mechanism-guided adaptive research

**Claim.** The agent can formulate testable physical hypotheses, choose a discriminating mathematical or physical investigation, and revise the research route when the evidence changes the interpretation of the current design problem.

- Main process evidence: PHS-2D, T04, T07, T10.
- Supporting evidence: T02, T05, and T06.
- Theoretical framing: abductive hypothesis formation, deduction of expected/weakening observations, empirical investigation, and sequential research-state updates.
- Main comparison: complete research architecture (C) against LLM-only (A) and direct bottom-level mathematical-tool use (B).
- Do not claim that the agent is a globally optimal experiment selector or that it computes calibrated mutual information/value of information.

## C2 — Task-conditioned composable mathematical research

**Claim.** High-level research intent can be mapped to a parameterized physical research problem, which is analyzed using task-conditioned mathematical semantics and applicable differentiation/optimization methods.

- Core interface: frozen task contract + candidate + registered parameter group + physical observables + inner physical problem + sensitivity semantics + budget.
- Mathematical semantics: M0 mechanism sensitivity; M1 fixed-input physical sensitivity; M2 re-optimized task-capability sensitivity; M3 closed-loop sensitivity.
- Reusable operations: inspect, differentiate, optimize, compare, and interact.
- Mathematical basis: KKT and active-set analysis, implicit differentiation, parametric optimization/envelope sensitivity, finite differences, and finite-scale interaction analysis.
- Main evidence: PHS-2D gradient audit; T01/T02/T07 active structure--control cases; T04/T10 control-method changes.
- Main comparison: B (direct bottom-level math tools) against C (complete research-intent and mathematical-research organization).
- KKT, implicit differentiation, envelope sensitivity, and finite differences are established mathematics; the contribution is their task-conditioned composition, validity-aware execution, and integration into agent-directed research.

## C3 — Cross-task evidence-grounded research continuity

**Claim.** Historical methods, intermediate solutions, and numerical evidence can be retained and adapted to later tasks or conditions while preserving task-specific physical validity.

- Main evidence: T04 reuse and adaptation of prior tracking experience; T07 transfer of a control initialization between conditions; T10 use of prior feedback-control experience; shared task and evidence interfaces across T01--T10 and PHS-2D.
- Supporting architecture: Knowledge/Skill, immutable Store/Trace, fixed evidence extraction, Reporter summaries, and L0--L3 hierarchical context.
- Knowledge/Skill and context ablations are extensions, not part of the first A/B/C batch.

## Supporting system contribution

**Executable soft-robot research harness and multi-task evaluation suite.** The harness connects task contracts, design/parameter registries, mathematical analysis, physical backends, independent evaluators, and evidence storage. The eleven completed cases span active and passive tendon-driven design, multi-condition tasks, tracking, orientation, loading, contact, and impact recovery.

## First controlled-comparison batch

| Task | A: LLM-only | B: Direct mathematical tools | C: Historical FULL |
|---|---:|---:|---|
| PHS-2D | 1 new run | 1 new run | Existing FULL |
| T01 | 1 new run | 1 new run | Existing FULL |
| T04 | 1 new run | 1 new run | Existing FULL |
| T07 | 1 new run | 1 new run | Existing FULL |

Eight new runs in total. No Fixed-Plan condition is included in this batch. A and B start from the original task initial state and the complete legal design space. C is not re-run; its historical configuration and comparability are reported as recorded.

## Claim boundaries

- M0--M3 are different sensitivity semantics, not four mandatory sequential stages or four independent optimizers.
- A local sensitivity is scoped to its model, candidate, operating point, parameterization, and input treatment.
- The PHS-2D 18-pair audit concerns three task metrics along one common Young's-modulus direction; it is not 18 independent parameter gradients or a global error bound.
- The 30/30 required-condition count is a completed-case snapshot, not a multi-seed success rate. T10's two frozen controls are separate.
- A/B/C outcome claims are added only after the eight new runs are complete.
- Physical-robot validation is a separate evidence layer and must use the already archived hardware records.
