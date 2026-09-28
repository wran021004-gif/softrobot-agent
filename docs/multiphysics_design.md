The Stage 3.29 entry point is `examples/gvs_design_input.py --multiphysics --output <fresh-input.json>`.
It derives the robot, task and controller recipe from the unchanged bundled reach asset and verifies the frozen task values.
`extensions/tendon_family/profiles/multiphysics_reach_experiment_v1.json` centralizes task checks, decisions, budgets and provider guidance.
Use the existing `gvs_nmpc_route_experiment.py prepare/run/inspect --input <fresh-input.json> --output <fresh-folder>` launcher.

The four decisions are near length [0.15,0.17] m, far length [0.11,0.13] m, common section scale [0.95,1.05], and material scenario baseline/compliant/stiff.
Scenarios multiply original Young moduli by 1/0.9/1.1, retaining density and bending viscosity. These are numerical scenarios, not validated materials.
Typed `Space.semantic_decisions` selects implemented expansion operations and component groups. `semantic_source` is the frozen physical source; repeated builds never compound scaling.
Adding future per-section choices can reuse component groups. New actuator/structural operations require implemented typed operations, not request-supplied code or another registry.
Effective robot fields, resolved groups, provenance, high-level selections, expanded physical changes, physical summaries and existing identities are retained.

`controller.gvs_nmpc@6.0.0` supports the declared physical envelope through the existing preparation hook, candidate model, projector and execution-local workspace. Technical support is separate from experiment authorization, model suitability and executed validation.
The controller algorithm, horizons, stopping criteria, initialization rule and task evaluator are unchanged. Historical tensions are bounded guesses; candidate states are regenerated, with no new equilibrium solve.
The geometry boundary retains analytic section validation, positive mass/inertia, guide-hole/tendon-diameter checks and reference-route nonzero-span checks. Scale endpoints pass these checks; no bound adjustment is needed. Self collision remains an existing model omission, not a newly validated clearance guarantee.

`analysis.gvs_candidate_evaluate` requires an owned build node and includes its physical summary and GVS dynamics/kinematics. `analysis.compare_candidates` compares up to four owned evaluated runs without executing or rescoring. Route diagnosis adds compact candidate and report observations, distinct from causal hypotheses.
Free reach records the first step of each accepted plan in world coordinates and compares only a matching next execution timestamp with the same applied tension and no intervening update. Detailed pairs are stored as evidence; missing data is explicit. No additional optimizer solve is introduced.
Delivery checks verify semantic selections and expanded physical changes. Multi-category coverage is reported separately from unchanged reach success; the provider's final prose still requires an independent factual audit.
