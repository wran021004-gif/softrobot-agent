# SoRoSim S4.5–S5 research delivery

## Source and stage boundaries

Designated branch: `feat/sorosim-matlab-nmpc`. Starting SHA:
`0a4a692975c3c840a4a0bea612f07f3ae8dc0d4e`. The remote matched it before
work. The S4.5 numerical study began at source freeze `30c1b20c`; the failed
cross attempt remains under that freeze. Explicit migrations retained the same
ledger and all consumed counts. The signed-margin optimization used source freeze
`a26a8d13`. The pinned SoRoSim dependency and MATLAB configuration were reused.

The original 0.35 s task, 35 tension intervals, 36 sampled states, 0–8 N four
tendon bounds, and inclusive 0.30–0.35 s holding window were frozen. Every S4.5
result is a rod-model statement; physical task acceptance remains unmeasured in
this stage. Neither an optimizer exit nor a mathematical replay is a MuJoCo result.

## P0 owner inventory

| Owner | Existing function and role |
|---|---|
| MATLAB dynamics | `sr_dynamics` evaluates force balance; `sr_nmpc_callbacks` owns scaled multiple-shooting constraints and output derivatives. |
| MATLAB offline and online | `sr_codesign` owns full-task SQP/replay; `sr_nmpc` owns preparation, implicit root integration, and online SQP. |
| Candidate mathematics | `sorosim_codesign.calculate` binds identities and MATLAB Session; `sorosim_analysis.calculate_candidate_configuration` owns static/local analysis. |
| Research ledger | `mechanics.dispatch/recover` reserves and settles mathematical work; `core.dispatch` validates typed actions and `core.export` archives the Store. |
| Physical execution | `execution.execute/finish_execution`, `execution_worker.execute`, `MujocoBackend.solve`, and `research_tasks.assemble_acceptance` own the existing contained backend and task evidence. |
| RL and Agent | `rl.prepare_input/dispatch`, `TensionEnv.step`, `rl.checks.run_episode`, `feedback.facts`, and `agent.decision_packet` own candidate-bound PPO and research feedback. |

The S4 report and sealed archive were read without changes. The M3-D branch was
reviewed as read-only diagnosis; its GVS physical results were not transferred
to a SoRoSim identity. Implementation proceeds in stage order: S4.5 mathematical
feasibility, S5-A fixed open-loop MuJoCo, S5-B complete SoRoSim NMPC, S5-RL,
S5-T, then an integrated Agent pilot. Each stage uses its own evidence and caps.

## S4.5 measured results

The [historical margin audit](../../evidence/sorosim_s45/historical_margins.json)
uses the frozen task translator's radii and the immutable S4 replay excesses.
It reports all 13 sampled values and signed normalized margins. It is an
independent arithmetic audit of the saved replay output, not a new integration.

| Saved trajectory | Terminal error (m) | Holding max error (m) | Holding max speed (m/s) | Original sampled task |
|---|---:|---:|---:|---|
| A with U_A | 0.009614040 | 0.010003816 | 0.028184903 | Failed position and speed |
| B with U_B | 0.005724630 | 0.005954838 | 0.020373137 | Failed speed |

Both saved tension grids are complete and within the original force bounds.
Both historical optimizers stopped at 120 iterations without convergence; both
relaxed trajectories passed their original independent mathematical replays.
Those facts do not imply original-task feasibility.

The first new cross replay, A with U_B, integrated its 35 intervals but failed
in the new MATLAB replay checker because a nested variable had not been
initialized before that branch. The result, 23.586456 s cost, raw localized log,
source freeze, and sealed receipt are in the
[failed cross archive](../../evidence/sorosim_s45/failed_cross_attempt/archive_manifest.json).
Its integration output was not saved, so its task metrics are unavailable. The
checker was fixed and the same computation was not repeated. The two-cross
integration allowance was exhausted by this attempt and the next one.

The second cross replay, B with U_A, used only the historical A physical
tensions, started from B's declared mathematical initial state, and reintegrated
B's own model. It completed and passed scaled dynamics verification
(8.65e-13). Terminal error was 0.014463243 m, holding maximum error
0.014687188 m, and holding maximum speed 0.160030985 m/s. It failed all three
original task thresholds. Its exact identity, controls, states and margins are
in the [attempt archive](../../evidence/sorosim_s45/attempt01/archive_manifest.json).
The absent A with U_B cell prevents a four-cell morphology–control interaction
contrast; no causal or global-optimality interpretation is made from three cells.

The first B feasibility solve minimized the nonnegative maximum squared
normalized sampled violation. It converged in 3 SQP iterations and 7 function
evaluations. Independent replay regenerated the saved states exactly and passed
the dynamics check. Two speed samples were above 0.020000000 m/s by at most
5.207e-13 m/s, so the strict sign check marked original feasibility unresolved.
The [compact index](../../evidence/sorosim_s45/summary.json) links this result
to the full immutable artifact.

The second and final B solve minimized the **signed** maximum sampled excess,
with an epigraph lower bound of −1 implied by nonnegative squared norms. It
retained all original hard dynamics and input limits. It stopped at the 120
iteration cap (501 function evaluations) without convergence; its returned
objective was −0.999967516 and scaled constraint violation 6.436e-13.
Its fresh implicit reintegration returned identical states, and separately
recomputed force residual was 6.436e-16 N·m². Every original sampled task
constraint had a positive signed margin; minimum holding speed clearance was
0.019886011 m/s. Tensions ranged from approximately 0 to 7.768123 N.

The sealed replay's `passed=false` flag arose because its legacy check required
the signed epigraph to be nonnegative. The
[post-hoc audit](../../evidence/sorosim_s45/posthoc_verification.json) preserves
that flag and verifies the corrected bound from the sealed, identical states,
commands, time grid, original task values, independent state regeneration, and
force-balance residual. Its corrected scaled violation is at most 6.436e-13,
below the existing 1e-5 replay tolerance. This supports a **mathematical feasible
witness after a post-hoc verifier correction**; it is not a converged optimum,
and the original replay flag remains false in the
[final Store archive](../../evidence/sorosim_s45/final_study/archive_manifest.json).
No extra integration was performed for the correction.

The shared S4.5 ledger records two complete NLP attempts, four new replay slots
(one failed cross, one completed cross, two same-candidate replays), twelve public
operations, 440.051 s recorded numerical time, zero physical launches, zero PPO
actions, and zero provider requests. The study is closed; counts were not reset.

## S5-A open-loop physical playback

The committed S5-A study `sorosim-s5a-open-loop-20261016` generated the same
Design B physical geometry and bound it to the sealed S4.5 mathematical
trajectory. The saved mathematical states were converted to world tip outputs
without a new mathematical integration. One fixed 35-command, four-tendon
sequence was then applied directly to the independent MuJoCo candidate. The
physical backend completed all 700 physics steps and saved 36 inclusive samples.
The observed actuator tension equaled every requested physical input to the
recorded precision; the force-bound component passed.

| S5-A metric | Mathematical saved-state output | MuJoCo physical result |
|---|---:|---:|
| Terminal position error | 0.000056381 m | 0.024960134 m |
| Holding maximum position error | 0.000056429 m | 0.024960134 m |
| Holding maximum speed | 0.000113989 m/s | 0.895355122 m/s |
| Original task acceptance | Mathematical post-hoc feasible witness | `valid_failure` |

The independent registered reach evaluator found a terminal error above the
0.010 m bound. The inclusive holding samples also exceeded both the position
and 0.020 m/s speed limits. The complete acceptance, candidate, source and
receipt are in the [S5-A Store archive](../../evidence/sorosim_s5a/study/archive_manifest.json),
with a compact [summary](../../evidence/sorosim_s5a/summary.json). The
[per-sample join](../../evidence/sorosim_s5a/comparison_detail.json) includes
world position and velocity vectors, speed magnitudes, expected and actual
tensions, and both models' original holding margins. Maximum accumulated
position and velocity discrepancies were 0.056479582 m and 1.299509910 m/s.
The initial tip position offset was 1.67e-16 m. This demonstrates substantial
trajectory mismatch under the same open-loop inputs; it does not establish a
unique physical cause.

A matched-initial-state one-step discrepancy is unavailable in this S5-A study:
it did not perform a declared MuJoCo-to-SoRoSim state projection and fresh
one-step mathematical integrations. The joined interval increments begin from
divergent states and are labeled accordingly. No incompatible state vectors
were subtracted. The S5-A ledger charged one physical launch, three public
operations, zero provider requests, and 1.417 s recorded numerical time.

S5-B complete NMPC, S5-RL, S5-T sensitivity, and the integrated Agent pilot
remain unexecuted at this boundary. They must retain distinct source,
candidate, task, backend and budget identities.
