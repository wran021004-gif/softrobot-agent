# Native restart source guidance

The authorized M1 continuation exposed an initialization request with a completed
Native analysis result in `control_seed.source`. A Native result contains
`control_schedule_reference`; it is not itself the executable schedule. The
original implementation reported only `KeyError('trajectory')`.

Initialization now rejects a source without a trajectory or measured execution
with `CONTROL_INITIALIZATION_REQUIRES_EXECUTABLE_SOURCE`. The actual Main Schema,
compact context and SDK error feedback explain how to read
`/control_schedule_reference` and explicitly choose the saved schedule. This does
not resolve or substitute a source automatically. The existing candidate, task,
channel, time-grid and tension-bound checks remain authoritative; copied controls
retain `task_acceptance=unmeasured`.

Only required source metadata is projected, avoiding unrelated Native rollout
arrays when a result is supplied by mistake. Measured NMPC conversion retains its
original exact-candidate ownership checks.

Three targeted offline regressions passed: actionable Native-result rejection
through actual SDK feedback followed by exact schedule copying without acceptance
transfer; missing-schedule rejection; and existing malformed/foreign NMPC source
rejection. Synthetic fixtures establish interface behavior only. They launch no
Provider request, solver, physical Replay or formal Study Worker.

The formal candidate_1534 Direct result remains separate scientific evidence. Its
4096-rollout attempt failed all three positive_high limits; this is a finite
optimizer result, not a proof of structural infeasibility. Main independently
selected a candidate_1210 restart. The repair does not choose its method, effort,
control values or subsequent research route.
