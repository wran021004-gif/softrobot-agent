# M3-C2 delivery — 2026-10-15

Status: **M3-C2 partially complete with listed technical boundaries**. Physical
generation covers 1–9 serial segments. Dynamics/control validation covers the
specific 1/2/3-segment cases below. High-segment dynamics/control compatibility
and the default-mesh Windows XML-loading limitation remain unresolved.

Branch: `feat/m3c2-variable-segments`. Starting SHA:
`bafad737824f7ff09741dbbc9273a2dba34bf882`. Real engineering implementation SHA:
`6b95df3e49b8e7f5f9af599fcbfd45d386989606`. A later optional-analysis metadata
correction freezes length scales for every declared segment from family domains,
instead of inheriting the bootstrap's one-segment normalization map. It was
tested without repeating control. Family-source deduplication then preserved the bound frozen definition exactly. Final production source SHA: `cc98b5c40d75d39af712996bc086a5b4d378fad1`. The final reply records the verified local/remote
delivery HEAD; the evidence retains its original implementation binding.

## Dense failure and repair

The exact recorded five-tendon dense request reproduced 22 coordinates and the
minimum mass eigenvalue `8.524523232987222e-13`. Mass rank was 22, symmetry residual
zero and condition estimate approximately `5.483e6`. Every force term and RHS was
finite; NumPy, CSparse and LAPACK solved the identical mass/RHS. Default CasADi QR
failed. A targeted raw-matrix probe failed at its documented absolute R-entry
cutoff `1e-12` and passed at `1e-13`, isolating that numerical rejection.

Production scales both sides by the mass Frobenius norm before the same default
QR solve. There is no diagonal regularization, changed physical parameter,
clipping, solver-accuracy reduction or lower-dimensional model. The repaired
dense solve has relative residual `7.54e-15`. The 12/14-coordinate controls pass
with residuals and NumPy agreement recorded. Their tendon/routing layouts differ;
this does not isolate dimension as the cause. No valid representation-only knot
override exists under current structural-station semantics.

See [diagnostic](../../evidence/m3c2_variable_segments/gvs_dense_diagnostic.json),
[original failed evaluation](../../evidence/m3c2_variable_segments/gvs_dense_original.json)
and [QR boundary probe](../../evidence/m3c2_variable_segments/qr_boundary.json).
No robot infeasibility claim follows from this numerical failure.

## Preparation, claims and evidence

Family-only composition uses `family_study_defaults.json` and the independent
task/control/runtime sources. Fresh preparation was tested with an isolated
fixture that has no robot.json and rejects every attempted robot.json read.
Reference-candidate configuration hash remains
`31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e`.
V2 shares the immutable prototype/domain source through a single-level
`base_space` composition over v1, owned by the same resolver. Both sources are
fingerprinted and the full resolved definition is frozen. Equality against the
bound engineering study proves this deduplication changes no family value.

The existing Host/compile_input contract needs concrete physical signals.
`config.family_bootstrap` constructs its deterministic compatibility input from
the frozen family and records the exact reason/request. It is absent from the
candidate pool, has no scientific candidate reference, and supplies no comparison
baseline or task acceptance. Generated candidates replace its structure, mesh and
builder and materialize their own named zero initializer. Canonical task identity
remains separate from effective initialization, physical configuration, basis and
evaluation profile. No thresholds, holding windows or sampling semantics changed.

`family_space_claims_v1` separates family generation, physical validation,
identified design pairs, evaluated structure/control search, selection, task
acceptance and confirmation. Reference-comparison fields are explicitly null.
Legacy claims retain their meanings. Synthetic selection fixtures are tests only.

The Agent sees exact compact bounds, conditional topology/routing rules, control
domains, operations and limitations. V2 summary size is 3,678 bytes versus 7,737
bytes for the full family. The full frozen artifact is available through
`study.family_space.full_specification`, using the existing evidence_read and
Store paging path. Exact artifact identity:
`120f23ddcf625a2fe4c0c0bfad3ad8d7a0fa25d42654e22261f2757ba539c987`.
Retrieval and ownership checks passed after recovery. No provider request was
needed. Authorized RL input preparation compares the canonical task rule while
retaining each candidate's physical initializer; input preparation was tested
without starting training.

## Serial construction and measured coverage

New contracts: `serial_family_space_v2`, `serial_family_generation_v2`,
`family.serial_space_build_v2@1`; registered builder `candidate.family@6.0.0`.
One loop expands explicit root/repeated segment, guide, connector and payload
prototypes. Per-index scalar/section domains, cells, consecutive spans, angular
offsets and typed route overrides determine the actual candidate. Existing
compiler, route-clearance, independent actuator and initializer checks are reused.
V3/v4 remain source-relative; exact v5 C1 physical identities matched for the
recorded one-, mixed-five- and seven-tendon cases.

The [1–9 table](family_space.md) and
[physical evidence](../../evidence/m3c2_variable_segments/physical_generation.json)
establish actual materialization and MuJoCo XML loading for explicit **four-cell,
three-tendon** candidates. Physical DOFs are 8N; this routing produces 6N GVS
coordinates and 12N states. Those proportions describe these examples only.
GVS recipe/basis construction passed for all nine counts in the bound study;
zero-state dynamics were evaluated only for 1/2/3 segments.

The default 12-cell mesh hit a native Windows stack overflow in
`MjModel.from_xml_path` at six segments / 144 DOFs. Counts 1–5 loaded before the
failure; 7–9 at that mesh were not attempted. The
[failure evidence](../../evidence/m3c2_variable_segments/windows_xml_limitation.json)
is preserved. Four-cell requests were explicit; the generator never silently
changes the requested mesh. No native stack workaround was introduced.

## Three real short controller cases

These cases used 12 cells per segment, three tendons, the registered NMPC
controller and the actual MuJoCo backend. Each performed one update and exactly
20 steps at dt=0.0005, totaling 0.01 seconds per case.

| Segments | Physical DOFs | GVS coordinates / state / inputs | Plan | Fallback | Elapsed seconds | Applied tensions N |
|---|---:|---|---|---|---:|---|
| 1 | 24 | 6 / 12 / 3 | Feasible, iteration-limited | No | 35.737 | 5.4420, 2.2197, 3.5003 |
| 2 | 48 | 12 / 24 / 3 | Feasible, iteration-limited | No | 112.395 | 8.0000, 5.2294, 0.000000514 |
| 3 | 72 | 18 / 36 / 3 | Feasible, iteration-limited | No | 285.994 | 8, 8, 0 |

Raw status was `Maximum_Iterations_Exceeded` in all three cases; feasibility
acceptance is distinct from convergence. Mass rank/SVD, term finiteness, Jacobian
and force-map shapes, coordinate/tendon order, warm input/state arrays, measured
physical states, complete update inputs and all costs are retained through exact
Store references in [short_control.json](../../evidence/m3c2_variable_segments/short_control.json).
Large original records are stored once in the
[immutable archive](../../evidence/m3c2_variable_segments/control/immutable_artifacts.tar.gz).
Its manifest hashes verify. Case elapsed sum is 434.125 seconds; total fixture
wall time was 443.604 seconds. This is no evidence of real-time control.

The original Store charged three backend attempts and twelve public operations.
The study is stopped with zero unsealed calls, pending work or occupied resources.
No owned worker remains. No repeat of these single-use cases is required.

## Validation, changes and remaining work

The consolidated focused regression passed **27 tests in 23.973 seconds**. Four
affected checks passed after the normalization correction; five passed after
family-source deduplication, including exact frozen-definition equality. The
opt-in bound numerical/control test also passed. Earlier real C1 model/XML regressions
passed for the recorded 12/14-coordinate controls. Development failures and the
unrecoverable intermediate diagnostic wall-time detail are disclosed in
[verification.json](../../evidence/m3c2_variable_segments/verification.json).

[Per-file before/after LOC, diff totals and responsibilities](../../evidence/m3c2_variable_segments/module_inventory.json)
cover production, tests, configuration, documentation and the one-time diagnostic.
No GVS engine rewrite, parallel Host/Store/registry, alternate evaluator, solver
installation or future search framework was introduced. Historical evidence and
the real historical robot.json are unchanged.

Provider calls **0**; credential files read **0**; RL training stages **0**;
complete task evaluations **0**; physical steps **60**; short real cases **3**.
Compilation, finite dynamics and one accepted control interval do not establish
the frozen complete task, robust control, universal nine-segment numerical
compatibility, structural improvement or Agent efficiency superiority.

Remaining technical boundaries: the native Windows default-mesh stack failure;
untested dynamics/control for 4–9 segments; declared but unmaterialized 8–12
tendons; branches, closed chains and the already excluded physics. M3-C3 still
owns mixed discrete/continuous count/routing selection, conditional continuous
search and a traditional non-Agent baseline. M3-D mathematical decision utility
and M4 multi-task benchmarking remain outside this delivery.
