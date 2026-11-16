# Claim–Theory–Evidence map — manuscript v1.1

## Central research question

How can an LLM agent use task-conditioned mathematical and physical evidence to autonomously investigate and improve soft-robot structure and control?

## C1 — Mechanism-guided adaptive research

**Claim.** The agent formulates testable physical hypotheses, selects discriminating mathematical or physical investigations, and revises the research route as evidence changes the interpretation of the current design problem.

- Main process evidence: PHS-2D, T01, T02, T04, T07, T10.
- Theoretical framing: hypothesis formation, expected and weakening observations, empirical investigation, and sequential research-state updates.
- Representative cases: PHS-2D structural-route changes; T04 control-route selection; T07 structural rejection and control-initialization transfer; T10 feedback-control selection.

## C2 — Task-conditioned composable mathematical research

**Claim.** High-level research intent is compiled into a parameterized physical research problem and analyzed using complementary, task-conditioned mathematical semantics.

- PPRP: frozen task + current candidate + selected parameters + observables + inner physical problem + analysis semantics + budget.
- M0: mechanism sensitivity.
- M1: fixed-input physical response.
- M2: re-optimized task capability.
- M3: closed-loop performance.
- Mathematical basis: KKT and active-set analysis, implicit differentiation, envelope/dual sensitivity, analytic/automatic differentiation, finite differences, directional comparisons, and finite-scale interaction analysis.
- Main evidence: nine-segment PHS-2D gradient audit; T01/T02/T07 structure–control cases; T04/T10 control-method changes.
- The contribution is the task-conditioned composition, validity-aware routing, and integration into agent-directed research—not a new KKT, IFT, envelope, or finite-difference theorem.

## C3 — Evidence-grounded research continuity

**Claim.** Historical findings, methods, candidates, and physical evidence can inform later research decisions while current task validity remains tied to the active task contract.

- Main evidence: Knowledge reads and Skill-guided procedures in T04, T07, T09, and T10; control-initialization transfer in T07; method adaptation in T04/T10.
- Architecture: independent Knowledge and Skill resources, L0–L3 context, immutable Store/Trace, fixed evidence extraction, and read-only Reporter.
- Trace-based usage is reported as component-use evidence; isolated component effects are reported only when controlled ablation outcomes exist.

## Supporting system contribution

Executable soft-robot research harness and multi-task evaluation suite connecting frozen task contracts, parameter/observable registries, mathematical execution, active/passive physical backends, independent evaluation, and evidence storage.

## Completed evidence portfolio

- Eleven FULL task cases, T01–T10 and nine-segment PHS-2D.
- Thirty required conditions passed; two T10 frozen controls reported separately.
- Nine-segment PHS-2D: ten loading conditions, independent-process reproduction, half-step check, and initial-state perturbation check.
- PHS-2D local sensitivity audit: six loading branches × three task metrics = 18 derivative pairs along one common Young's-modulus direction; maximum relative discrepancy 0.1191223%.
- Representative A/B/C case comparison: T01, T04, and T07, with C identified as historical FULL.
- Real-world demonstrations are maintained as a separate physical-evidence layer.
