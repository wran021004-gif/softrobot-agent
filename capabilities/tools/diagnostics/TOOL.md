# Deterministic diagnostic tools — Round 1

The four callables in tools/diagnostic_tools.py consume ToolResults and return
the existing ToolResult. status=pass means evidence processing succeeded, even
when the task failed or an anomaly occurred. Missing, malformed or contradictory
required evidence returns status=fail, failure_code=UNKNOWN and
evidence_status=unavailable. It never becomes zero discrepancy or non-saturation.

| Callable | Inputs | Evidence |
| --- | --- | --- |
| compare_model_sim | model_result, simulation_result, TaskSpec | predicted/actual tips and errors, Euclidean tip discrepancy, predicted tolerance failure |
| check_actuator_limits | simulation_result | force limits/extrema, lower/upper limit counts, active-sample fractions and sampled lower-limit duration |
| check_tendon_tracking | simulation_result | final commanded/actual lengths, signed/absolute/relative errors in tendon order |
| inspect_numerics | simulation_result | finite flags, state peaks, warnings, step completion, time advance anomalies and termination code |

All accept optional evidence_paths. References come from the caller; the tools
do not invent filenames or read/write arbitrary files. Harness persists each
ToolResult and diagnostic_summary.json through RunArtifacts/save_tool_result,
then hashes them. Verify run.json artifact_hashes before reading saved evidence.
Hashes detect corruption, not a writer replacing the entire run. A historical
run lacking new observations is insufficient evidence; never retrofit its truth.

Comparison requires matching Harness run_id, task/environment/RobotIR hashes and
coordinate frame, matching target/command, and consistent canonical errors.
Instrumented executions must have held the model command in every observed step.
The Harness binds context from executed inputs. Unbound standalone results cannot
establish a same-run comparison.

Force and tendon length sampled after mj_step are solver-stage values for that
step; qpos/qvel have already been integrated. Final tracking uses the unchanged
final mj_forward. No extra forward call enters the loop. Initial tip kinematics
use a separate MjData. Storage scales with model size, without long time-series
arrays or raw stdout. Fractions count active-command samples. Duration=count*dt
is sampled exposure, not a continuous-time measurement.

For V1 [-limit,0] N forces, lower-bound hits establish observed maximum-pull
saturation. Upper hits record the no-push bound; they do not prove active clipping, maximum-pull
saturation or cable slack. Passive C0 has no target/active samples, so these two
checks return unavailable. Contradictory counters/extrema are rejected.

Numerics reports warning counters even when MuJoCo returns finite state after
recovery. State peaks use rad/rad/s for V1 hinges. No large-qvel threshold is
approved; magnitudes are reported without an invented alarm. Finite states and
absent warnings establish neither convergence, stability nor physical validity.

No approved mismatch criterion exists. PCC failure plus MuJoCo failure, or any
nonzero discrepancy, leaves causal failure_attribution=UNKNOWN. ACTUATOR_LIMIT
may be an observed evidence category, without claiming it caused the task failure.
Diagnostics cannot override the canonical actual-tip gate; their own processing
failure is recorded separately.

run_parameter_sensitivity remains PLANNED: no diagnostic variable/bounds policy
is approved. check_tendon_slack awaits physical semantics; check_collision awaits
an implemented contact evidence contract. No optimizer, retuner or Diagnosis LLM
exists. Manifest specifies input fields, limitations and costs.
