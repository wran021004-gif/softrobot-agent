# Reusable V1 surrogate exploration envelope

`capabilities/robot_families/tendon_driven_continuum/envelope.yaml` is the
Human-owned long-term authority, referenced by the family grammar. The user's
explicit correction sets length to [0.05, 0.80] m. It is simulation exploration
permission under legacy_v1_surrogate, not manufacturing or real-robot validation.

| Field | Representation | Permitted experimental use |
| --- | --- | --- |
| sections | 1 | Fixed; multi-section unsupported |
| total_length_m | 0.05–0.80 m | Design search |
| tendon_routing_radius_m | 0.002–0.018 m | Design search |
| tendon_count | Integers 3–8 | Discrete design search |
| body_radius_m | 0.01–0.05 m | Representable; optimization BLOCKED_BY_MECHANICS_COUPLING |
| segments | Integers 4–24 | NUMERICAL_SENSITIVITY_ONLY |

The relation `0 < tendon_routing_radius_m < body_radius_m` applies to every
envelope candidate, including fixed reference fields. Dimensions must be finite
and positive; counts are strict integers. No invented wall thickness or material
safety constraints are included. Direct numerical compatibility APIs retain their
historical executable support (including old test fixtures); they do not authorize
design exploration beyond this envelope.

ExperimentPolicy uses `authorization_mode: ENVELOPE_SUBSET` for a task-specific
choice under this authority. It can live under configs/experiments,
proposals/engineer or runs, with a reference DesignSpec, selected variables, subset
bounds, seed and finite budgets. The existing broad Human approval record supplies
`approval_source`; Engineer does not invent another scientific approval. The
validator checks the actual grammar-linked envelope, policy and approval hashes,
all fixed fields, relations, existing TaskContract, M0/M1 and C1-only capability.
Unknown physical inputs or unsupported routes are rejected. This is deterministic
repository authorization, not OS isolation for arbitrary untrusted code.

`purpose: NUMERICAL_SENSITIVITY` permits only segments as the varying field and
rejects design ranking through optimize_design. Every other field remains equal
to the reference. The study runner preserves the existing C1 commands, task,
environment, simulator settings and per-joint surrogate parameters. It reports
all segment results and never selects a physical-design segment optimum.

The old Round 3.1 policy and its file-specific narrower bounds remain executable.
Legacy per-field grammar metadata is retained for compatibility; new reusable
authorization comes from the linked envelope. Generic optimization selections now
accept the three approved fields. Merely copying an old policy no longer creates
a blocker when that policy already fits the broad approved envelope.

The staged runner reuses ExperimentSession, RunArtifacts, TraceWriter, the existing
candidate stream conventions, canonical evaluator and debug plotting. Completed
evaluations are reused only for identical design/fidelity and task/source hashes,
after checking the sealed child manifest. Reuse files preserve the original parent,
candidate and child identities; a reused child is not relabeled as newly executed.
Stage summaries distinguish new evaluation budgets from all evidence comparisons.

`analyze_actuation` uses the existing tendon mapping and nonsingular bending
coordinates b=(theta cos(phi), theta sin(phi)). Its Jacobian row is
[-r cos(alpha_i), -r sin(alpha_i)] m/rad. Stroke/SVD/rank/condition results are
GEOMETRIC_ACTUATION_ONLY. Uniform tendon layouts can have condition number one
for several counts/radii; that does not establish equivalent physical actuation.

`model_shape.json` contains MATLAB PCC samples at normalized arc length. The
normal MuJoCo ToolResult records final proximal segment origins plus distal tip
after the already-existing final forward call. `shape_comparison.json` compares
65 normalized arc-length correspondences, reporting tip/RMS/max discrepancies and
compact vector differences. It never reads debug/ files. No mismatch threshold is
introduced; failure_attribution remains UNKNOWN. Geometric model agreement, shape
disagreement and numerical segment sensitivity inform the final qualitative phase
decision without overriding canonical task status.
