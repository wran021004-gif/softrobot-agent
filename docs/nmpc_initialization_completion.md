# NMPC initialization diagnosis: implementation ready, live investigation pending

The implementation supports a declared feasible-return change from15s to30s and
reports the **actual** stopping reason. CPU30s, iteration120, minimum5s, relative
improvement .1, tolerances and other settings are preserved. An iteration/CPU/
improvement/convergence stop is explicitly reported as a different condition;
it cannot establish that extending the feasible-return budget is ineffective.
Baseline defaults and historical runs stay intact.

The source ref was fetched once and matched
`97aced4e75a6c3c6fecd851ae5bb0dc6be112f18`. The isolated delivery branch is
`feat/nmpc-initialization-diagnosis`. Implementation was first committed as
`aae1ce5b5bb08df54e4a87b5d337d21d103b954a` and bound with compatible dependencies.
The existing Python environment and lock were reused without upgrade. The
[runbook](nmpc_initialization_runbook.md) gives exact lifecycle commands and limits.

The [35-update factual timeline](../evidence/nmpc_initialization_20261010/saved_timeline.json)
preserves original execution `21b607607bf442a6b6d9494dda897ea8` and owner
`casadi-nmpc-research-20261010-cl-afc46a23b0c9`. `ControlEvidence`, `import_execution`
and `BoundReader` import immutable evidence with original identities. Independent
archive fallback matched ownership, manifest and configuration without rerunning
the simulation.

| Established timing | Simulated time |
|---|---:|
| First holding-cost node visible in prediction | .20s |
| First shortened prediction horizon | .26s |
| First changed applied command | .30s |

All35 old plans were numerically accepted, 30 selected initialization and five
selected noninitialization plans. Old terminal error was95.5mm, holding maximum
error193.2mm, holding maximum speed3.25m/s. These are failed sampled task results,
not evidence of exception fallback or skipped synchronous virtual-time actions.
Historical full warm plans, objective vectors, rejected iterates and iteration
counts were not recorded. Their absence prevents a unique historical explanation.

The native interface now exposes inspection, one declared saved-state pair,
one targeted control revision and STOP. A pair uses the recorded state, preceding
applied tension, absolute time and effective horizon, separate mutable workspaces
and a new common seed. Update zero is excluded explicitly. Same-time projected
kinematics/velocity and next-step prediction disagreement remain separate.
Numerical results are preserved before downstream presentation, with bounded
initial/raw/selected/rejected snapshots and named residuals. A revision records
diagnosed updates in the actual controller scope and compares measured behavior
against the imported execution; earlier command changes alone are not improvement.

[Focused checks](../evidence/nmpc_initialization_20261010/focused_checks.json) cover
nine concrete contracts/fixtures, using7.091s of unittest timers including failed
fixture attempts. No full suite, new physical campaign or real NLP was run.
The first missing time-zero trajectory row was repaired using the recorded tip
and named zero initial velocities; a conservative15s preparation-recovery charge
is retained. The original clock and all counters persist across these repairs.

| New scientific/provider work | Actual | Ceiling |
|---|---:|---:|
| Paired comparisons / local NLP attempts | 0 / 0 | 2 / 4 |
| Representative numerical states | 0 | 2 |
| MuJoCo launches / internal NMPC solves | 0 / 0 | 1 launch |
| Actual provider sends / public calls | 0 / 0 | 16 / 64 |
| Full-horizon codesign / BDF / hardware / other models | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

**The live model-directed investigation and remote push have not executed.** Automatic approval
review rejected the live DeepSeek action twice. Its final stated reason was that
the attached authorization is untrusted and requires explicit authorization in
the chat for sending non-secret task/source/diagnostic feedback to
`https://api.deepseek.com/chat/completions`. An explicit approval question is
pending. The [authorization checkpoint](../evidence/nmpc_initialization_20261010/authorization_checkpoint.json)
records zero sends/solves/launches; no model decision, accepted native STOP or
revision result is fabricated. Automatic review also rejected the ordinary push
to `wran021004-gif/softrobot-agent` branch `feat/nmpc-initialization-diagnosis`,
requiring explicit chat authorization for the destination and non-secret payload.
Separate approval questions are pending. Delivery currently consists of local
commits; no remote branch SHA is asserted. Budget availability is not scientific evidence.

The [factual case draft](../memory/nmpc_initialization_case_draft.json) and
[diagnostic procedure draft](nmpc_initialization_procedure.md) retain the required
lessons and scope limits. [Actual legacy schema errors](../evidence/nmpc_initialization_20261010/legacy_admission_check.json)
show the provenance mismatch: legacy `ArtifactReference` requires run-relative
paths and finalized `run.json` artifact hashes, while platform `EvidenceRef` uses
immutable hashes/export bundles and SQLite sessions. No validation or human
approval is fabricated, and no memory database or provenance migration is built.

What remains unknown is whether the model would select a longer-budget comparison,
whether another stop would occur first, whether useful feasible progress would
appear, and whether a selected revision would improve measured closed-loop
acceptance. The current finding is a timing distinction and corrected reporting
semantics, not a causal optimizer/weight/model/structure diagnosis.
