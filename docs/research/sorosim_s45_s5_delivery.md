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

## S5-B complete SoRoSim feedback

The separately frozen `sorosim-s5b-nmpc-20261016` study generated the same
Design B physical geometry. Its one MuJoCo execution completed all 35 original
control updates. The controller ran actual MATLAB SQP against each projected
MuJoCo measurement; 34 noninitialization plans were accepted, and one update
used the declared fallback after a solver error. The
[Store archive](../../evidence/sorosim_s5b/study/archive_manifest.json)
retains the controller observations, solver outcomes, raw update inputs,
physical trajectory, independent evaluation, profile, and receipts. Its
[compact result](../../evidence/sorosim_s5b/summary.json) links the exact
candidate and evaluated execution.

| Same Design B physical task | Fixed S5-A open loop | S5-B SoRoSim feedback |
|---|---:|---:|
| Terminal error (m) | 0.024960134 | 0.006099499 |
| Holding maximum position error (m) | 0.024960134 | 0.006634832 |
| Holding maximum speed (m/s) | 0.895355122 | 0.042351326 |
| Original task acceptance | `valid_failure` | `valid_failure` |

Feedback reduced all three observed summary metrics on this one paired
candidate, but it did not satisfy the 0.020 m/s holding-speed requirement.
The registered acceptance also marked the solver-errors component failed:
there was one solver error and one unusable plan. All 35 updates missed the
0.01 s real-time deadline. Study numerical time was 1,768.212 s, with one
physical launch, six public operations, and zero provider requests.

The profile aligned 34 accepted one-step mathematical predictions with the
actual next MuJoCo outputs. The maximum world tip position innovation was
0.005938145 m; the maximum velocity-vector innovation was 0.168852444 m/s.
One prediction was unavailable for the fallback update at 0.34 s. These are
matched feedback-step discrepancies, unlike S5-A's accumulated open-loop
drift. The measured improvement does not isolate model mismatch, projection,
solver quality, or control weights as a single cause, and it is not evidence
of real-time NMPC.

## S5-RL direct and residual PPO

The `sorosim-s5rl-design-b-20261016` study regenerated the same four-tendon
Design B and admitted the exact complete S4.5 mathematical tension sequence
as a residual reference. Admission checked the model, task, candidate,
tendon order, 35-command grid and force bounds. Its reference source was the
sealed S5-A mathematical-source artifact, whose open-loop MuJoCo outcome was
a physical failure. Reference admission did not transfer a success claim.

Two real PPO workers each completed 32,768 attempted actions and 128 rollout
optimizations. The direct worker recorded 782 complete and 260 failed training
episodes; the residual worker recorded 936 complete and zero failed training
episodes. Both published checkpoints. Each checkpoint then received one fresh
35-action, 700-physics-step MuJoCo task evaluation.

| Independently evaluated route | Direct PPO | Residual PPO |
|---|---:|---:|
| Terminal error (m) | 0.189722862 | 0.041048734 |
| Holding maximum position error (m) | 0.198931568 | 0.047028312 |
| Holding maximum speed (m/s) | 0.355531167 | 0.292965029 |
| Complete evaluation | Yes | Yes |
| Original task passed | No | No |

The [S5-RL Store archive](../../evidence/sorosim_s5rl/study/archive_manifest.json)
retains the source bridge, frozen candidate and task, training summaries,
checkpoint identities, evaluation trajectories, and ledger. The
[stage summary](../../evidence/sorosim_s5rl/summary.json) links both routes.
Combined attempted training actions were exactly 65,536, with two admitted
training stages and two independent evaluations. The ledger charged four
physical launch slots (two starts and two evaluations), eight public
operations, zero provider requests, and 127.851 s numerical time. Training
reward and failed-episode fractions were not used as task acceptance.

The exported S5-RL summary has a legacy `aggregate_action_limit: null` display
field despite its frozen `authorized_limits.training_actions: 65536` and the
enforced 32,768-action per-stage grant. The feedback display was corrected
after this sealed result; the original summary and actual action counts remain
unchanged. None of the direct/residual results outperformed the S5-B feedback
controller on the original terminal or holding position metrics, and all
three still failed the task. This single fixed-budget comparison does not
establish general controller superiority.

## S5-T task capability and sensitivity reliability

The optional `task_capability` mode now expresses the maximum of the frozen
sampled squared-normalized task excesses through an unrestricted signed
epigraph. It preserves full dynamics and physical input bounds. Future full
`fmincon` solves retain raw task, dynamics and bound multipliers, and calculate
stationarity, primal, dual and complementarity residuals on the raw iterate
before any projection or tension recovery. An envelope derivative would still
need the explicit design dependence of dynamics, initialization and structural
constraints; no partial task-only derivative is reported as that result.

The dedicated [S5-T study](../../evidence/sorosim_s5t/study/archive_manifest.json)
ran one 1,006-variable, 864-equality, 13-inequality check-only directional
derivative preflight for Design B. Relative objective and constraint errors
were 2.238e-8 and 1.727e-10. It made **zero** new full reoptimization
attempts and zero physical launches, recording 49.257 s numerical time.
The [structured classification](../../evidence/sorosim_s5t/summary.json)
is `solver_unresolved`: the sealed S4.5 base solve stopped at its iteration
limit, and that historical run did not retain full-NLP multipliers. The new
multiplier extraction branch was not exercised by a full solve in this stage.
Consequently the reoptimized optimal-value gradient, gradient error bound,
Lipschitz bound, and certified descent condition are unavailable. No global
optimality or physical sensitivity is claimed.

The study also joined the historical A with U_A replay and the completed B
with the **same U_A** cross replay. Across the 0.005 m proximal-length change,
the fixed-command mathematical terminal-error difference was +0.004849203 m,
holding-position difference +0.004683372 m, and holding-speed difference
+0.131846081 m/s in B minus A order. This is a two-design secant with exact
common physical commands and separate initial states, not a local derivative
of reoptimized task capability. The missing A with U_B cell still prevents a
complete morphology-control interaction contrast.

## Integrated Agent feedback pilot

The local S5-Agent preflight froze the `formal_research` study, materialized
the exact Design B candidate, imported the verified mathematical tension
reference, and exposed five P1–P5 summaries with original artifact pointers
in the same research Store. Its [decision packet](../../evidence/sorosim_s5_agent/preflight.json)
shows one candidate, a valid compatible residual reference, 12 remaining
provider requests, 39 remaining public operations and two backend launch
slots. The [preflight Store archive](../../evidence/sorosim_s5_agent/preflight_study/archive_manifest.json)
preserves source ownership. That preparation was an engineering action.

Automatic approval review initially rejected the outbound live call to
`https://api.deepseek.com/chat/completions` because the destination was not
explicit in the authorization. The [egress review](../../evidence/sorosim_s5_agent/egress_review.json)
records that earlier boundary. The user then explicitly approved one bounded
send to this endpoint, including repository-derived task, candidate and P1–P5
evidence and subsequent tool outputs, with at most 12 provider requests. The
live pilot used the existing credential loader and [frozen study](../../configs/research/study_sorosim_s5_agent_feedback.json).

The model made 10 provider requests and 16 original tool requests. It first
read the imported P1–P5 evidence, then chose one 35-update SoRoSim NMPC
execution and one fixed-tension physical replay. One initial evidence read
failed on a bad reference; the model corrected the read. Its first replay
proposal failed plan validation; a corrected proposal launched. After both
physical failures, the model read the exact new result artifacts. The STOP
gate rejected three incomplete proposals until the model supplied the exact
reads and cited both fresh results. The accepted disposition stopped with no
selected solution. Original requests, feedback, rejected calls, evaluations
and final disposition are in the [live Store archive](../../evidence/sorosim_s5_agent/study/archive_manifest.json)
and [pilot summary](../../evidence/sorosim_s5_agent/summary.json).

| Pilot action | Terminal error (m) | Holding position (m) | Holding speed (m/s) | Solver errors | Original acceptance |
|---|---:|---:|---:|---:|---|
| Model-selected SoRoSim NMPC, 35 updates | 0.006099499 | 0.006634832 | 0.042351326 | 1 | valid failure |
| Model-selected fixed mathematical tensions, 35 commands | 0.024960134 | 0.024960134 | 0.895355122 | 0 | valid failure |

The pilot's NMPC metrics exactly reproduce S5-B; its fixed-tension metrics
exactly reproduce S5-A. The candidate artifact IDs differ across studies,
but the [identity audit](../../evidence/sorosim_s5_agent/decision_audit.json)
finds equal candidate parameters, compiled robot, task, seed, backend and
controller. S5-A and the pilot replay also use the same source
tension artifact (`45815dc9...`). These are new execution IDs of the same
physical configurations, not new morphologies or a discriminating controller
comparison. The model's stated reason that S5-A/S5-B used different physical
candidates is false at this level. Repeated metrics support reproducibility
of these two outcomes; they do not establish deterministic behavior in
general. The measured prediction discrepancies make model mismatch a plausible
contributor, but neither these runs nor the pilot isolate it from controller
settings, solver behavior or other causes. The model's categorical causal and
no-remaining-route claims are hypotheses, not established findings. The
original task thresholds remain frozen.

The pilot consumed two of two backend launch slots, 20 of 40 public
operations, and 10 of 12 provider requests; no fresh NLP, BDF replay, PPO
training or RL evaluation ran. The shared ledger reports 2,047.227 s charged
wall time, 1,826.329 s numerical time, and 2,576.858 s study elapsed time.
There is no accepted physical solution or demonstrated Agent performance
advantage. The observable Agent milestone is an evidence-conditioned STOP
after actual feedback, with the duplicate-experiment reasoning flaw above.

## Implementation, source freezes and costs

The development branch is `feat/sorosim-matlab-nmpc`; the verified starting
remote SHA was `0a4a692975c3c840a4a0bea612f07f3ae8dc0d4e`. Stage evidence
bound to committed implementations: S4.5 through `4931904a`, S5-A through
`933d47c6`, S5-B through `1bfbadde`, S5-RL through `ada51d26`, S5-T through
`a3c5b046`, and local Agent preflight through `bbed3a91`. Every stage used a
separate sparse study configuration and immutable Store export. The final
delivery commit and verified remote SHA are reported with the final handoff.

| Frozen study | Resolved configuration identity |
|---|---|
| S4.5 final | `194da2a7b5c653834922b7a7e438c31f4f72a8181f0467a27f4244f7d0b6e6f3` |
| S5-A | `8cbb7c2f0f33365c9f0734b2ea241fb73428f1c52ed70d44480b7e3a2154d362` |
| S5-B | `0ea922a8dede13ce7027a3f6ab9033e71043c7c5fdb5e38f902dbd2cd1eec4ac` |
| S5-RL | `7b1b29a48ef31511d3729f282673ae70e160f711420d14435f7b97c66d81586d` |
| S5-T | `4f2a9ad5dc1f131f132bacd8a09ee7e0a88c11c9676962ce02d904de8ed8afc8` |
| S5-Agent preflight and live pilot | `545b63f7382db8023f6fb83aaf912aa26cdb9b36860144557bb9546362dcf886` |

| Production owner | Change and reason | Approx. lines changed |
|---|---|---:|
| `sr_codesign.m`, SoRoSim Python bridge | Original-task feasibility, cross replay, signed epigraph, raw multiplier/KKT diagnostics | 160 |
| `sr_trajectory_outputs.m`, gateway, manifest | Saved-state world tip outputs with source identity, no dynamics reintegration | 23 |
| family `backends.py` | Candidate-compiled fixed SI MuJoCo tension playback with 36 samples and actual force checks | 67 |
| `physical_replay.py`, execution worker | Typed one-launch reservation, contained execution, registered acceptance and comparison | 199 |
| research contracts/core/state/feedback | Typed actions, recovery, packet and imported evidence visibility | 81 |
| research config/RL | Explicit action counts and exact mathematical residual-reference admission | 53 |

Stage scripts and sparse grants are under `tests/research/sorosim_s45_pilot.py`,
`sorosim_s5a_pilot.py`, `sorosim_s5b_pilot.py`, `sorosim_s5rl_pilot.py`,
`sorosim_s5t_pilot.py`, `sorosim_s5_agent_pilot.py`, and matching
`configs/research/study_sorosim_*.json`. They call the original research
Store, controller, backend, RL and evaluator owners. The stage-specific
evidence archives preserve counts and full source identities; compact tables
above are navigation aids, not replacements for their raw results.

| Stage | Fresh full NLP | Mathematical replay slots | Backend launch slots | PPO actions | Provider sends |
|---|---:|---:|---:|---:|---:|
| S4.5 | 2 | 4, including one failed cross | 0 | 0 | 0 |
| S5-A | 0 | 0 | 1 | 0 | 0 |
| S5-B | 0 | 0 | 1 | 0 | 0 |
| S5-RL | 0 | 0 | 4, two starts/two evaluations | 65,536 | 0 |
| S5-T | 0 | 0; one derivative preflight | 0 | 0 | 0 |
| S5-Agent local preflight | 0 | 0 | 0 | 0 | 0 |
| S5-Agent live pilot | 0 | 0 | 2, NMPC and fixed replay | 0 | 10 |

The scope of P1 is limited by the missing A with U_B cross outcome; the S4.5
feasible witness is nonconverged and its sealed replay retained the original
false flag alongside the post-hoc verifier audit. S5-A, S5-B, and both PPO
checkpoint evaluations are complete original-task physical failures. The
observed NMPC speed improvement does not establish a unique causal mechanism
or a real-time controller. S5-T has no validated KKT point or certified
gradient. The live Agent made a genuine feedback-conditioned STOP decision,
but repeated two earlier physical configurations and found no accepted result.

For read-only reproduction, set `PYTHONPATH` to the worktree and
`tests/research`, use the configured research interpreter and the three
single-thread variables from `configs/research/runtime.json`, then run
`python -m unittest test_sorosim_contract test_agent_feedback
test_count_continuation -q` from the `tests/research` module path. Recompute
source and artifact SHA-256 values from each stage's `archive_manifest.json`
and compact index. The stage scripts above show the original contained
experiment calls and frozen grants; sealed scientific executions must not be
repeated under their existing study identities. Local Agent packet preparation
used `python tests/research/sorosim_s5_agent_pilot.py
runs/research/sorosim-s5-agent-feedback-20261016 --prepare-only` and the
approved live run used the same command without `--prepare-only`. Both are
sealed; neither should be rerun under this study identity. The Store archive
contains all provider requests and tool outcomes.

The final focused Python regression ran 45 selected tests successfully,
including SoRoSim contracts, cross-replay binding, Agent feedback, count
continuation and task-analysis contracts. A broader 48-test selection had one
unrelated Windows sandbox setup error when a topology fixture could not open
its temporary SQLite database under `runs/`; the focused rerun excluded that
fixture and passed. The real S5-A/S5-B/PPO/S5-T outcomes above are separate
from fixture tests. `git diff --check` passed before stage commits.

Follow-up work for S6 includes a justified matched-state physical/model
diagnostic, converged KKT base point before envelope-gradient testing, a
controller or morphology candidate that actually passes independent physical
acceptance, real-time performance work, and multi-seed/cross-task controller
and Agent comparisons. Add a prelaunch duplicate-science check using physical
and controller identities, since a changed candidate artifact ID alone did
not distinguish the pilot's two choices. None of these outcomes follows from
the single pilot here.
