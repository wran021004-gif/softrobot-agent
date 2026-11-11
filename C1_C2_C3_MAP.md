# Contribution--Mechanism--Experiment Map (v0.3)

## C1 — Mechanism-Guided Autonomous Research
**Claim:** the system can formulate testable physical hypotheses, select discriminating investigations, and revise its research direction in response to evidence.

- Theoretical support: abductive reasoning; hypothesis testing; sequential research decisions; active diagnosis and identifiability.
- Primary comparison: P3 Full vs Fixed-Plan.
- Optional extension: One-shot LLM Plan, added only if Full vs Fixed-Plan indicates a meaningful difference.
- Supporting comparison: M1 Full vs No-Automated-Physical-Probe.
- Measures: valid hypotheses, expected/weakening observations, evidence-grounded pivots, effective research action ratio, task outcome, and cost.
- Do not claim calibrated mutual-information or numerical VOI optimization.

## C2 — Composable Mathematical Research
**Claim:** high-level research intent can be projected into parameterized physical problems and investigated through reusable mathematical operations with explicit semantics and validity.

Four layers:
1. Research Intent Projection.
2. Parameter / Observable Composition.
3. Composable Mathematical Operations: inspect, differentiate, optimize, compare, interact.
4. Solver Routing and Numerical Validity.

- Theoretical support: KKT and active-set analysis; parameterized optimization; implicit differentiation; envelope-theorem sensitivity; finite-scale interaction analysis.
- Primary comparisons: P3 Full vs No-Math; Full vs No-Intent-Projection; Full vs No-Pairwise-Interaction.
- Independent validation: equilibrium/KKT residuals, derivative checks against reference solutions, active-set qualification, finite-difference scale checks, and four-point interaction verification.
- Do not present KKT, sensitivity, or four-point interaction as newly invented mathematics.
- Do not claim global gradients or descent guarantees without regularity and error bounds.
- No-Intent-Projection must wait for an audit of `scientific_question_v4`; do not create a nominal feature flag if no independent projection process exists.
- No-Math and No-Pairwise-Interaction are nested, not independent factorial ablations.

## C3 — Evidence-Grounded Iterative Research
**Claim:** domain knowledge, structured evidence, traceability, and scientific interpretation improve research continuity and decision quality.

- Theoretical support: external memory, evidence provenance, context organization, evidence-based iteration.
- Primary comparisons: P3 Full vs No-Knowledge; Reporter ON/OFF on six paired historical snapshots; evidence-trace audit.
- Measures: evidence citation correctness, unsupported claims, repeated/ineffective actions, decision quality, context/token cost.
- No-Knowledge must retain task definitions, tool schemas, and essential interface information.
- Align historical Full knowledge assets (45 records / 17 entry IDs) with current Core knowledge (reported four general entries) before claiming a matched ablation.

## Cross-task and portability
- P3: passive structural design and progressive stiffness.
- M1: active multi-target control.
- PHS-2D: additional passive multi-condition stabilization case.
- Tracking: lightweight mathematical transfer, conditional on auditing the task compiler.
- Backbone comparison: DeepSeek Flash, GPT-5.6 Sol, GPT Astra under the same M1 Full configuration.
- One seed is a pilot; use at least three, preferably five, independent seeds for quantitative claims.

## Budget fairness
- Hard cap: 200 Provider requests per Study, shared by Main and Reporter.
- Additional ceilings: 100 mathematical evaluations and 150 physical launches.
- Public Operations ceiling must be derived from historical Full usage and frozen before execution.
- No automatic extension or 201st request.
- Budget exhaustion without a qualifying candidate is a within-budget failure, not proof of infeasibility.
- Reconstruct an equal-budget Full prefix if possible; otherwise treat historical Full as a high-budget reference.
