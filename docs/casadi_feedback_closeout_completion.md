# CasADi feedback closeout, 2026-10-10

The candidate-feedback research loop **completed**. Real returned numerical results survived checkpoint saving and candidate export, and independent BDF replay evidence reached the sole research LLM. Its typed native STOP plan was accepted.

The fetched source remained `d9ce124244697f30df3a609942cb7591c3cf3f15`. The isolated branch is `fix/casadi-feedback-closeout`; the first dispatch was bound to `b63bb6b591293dd82e8c2977406ec73a9ecc9ec3`. The new grant is `casadi-feedback-closeout-20261010`. The prior activity stays sealed STOP with 24 sends exhausted. Its two refined NLPs really ran (18/21 iterations, about 221/260 seconds of IPOPT time), but their unsaved vectors remain unrecoverable. Their original-task and replay outcomes remain unknown.

Codex prescribed and implemented checkpoint/recovery, engineering-error pause, fresh activity accounting, compatibility and protected-closeout repairs. The research LLM chose the scientific experiments. Its initial choice froze `d=0`, used the two-step state grid, equal position/speed weights, and the historical tension schedule as initialization. After seeing the first replay failure, it chose one revision at the same design and grid, adding the allowed effort/variation coefficient `0.001`, initialized from the first new schedule. It hypothesized that smoother tensions could improve speed margin and replay consistency. Both model plans, original statements, actual feedback and separately labeled engineering corrections are retained.

The [runbook](casadi_feedback_closeout_runbook.md) and [frozen specification](../examples/casadi_feedback/specification.json) define the task, execution and ceilings. The existing Windows Python 3.11.16 environment was reused with CasADi 3.7.2, SciPy 1.17.1, MuJoCo 3.13.0, Strands Agents 1.59.0 and Harness 0.2.0. Historical diagnosis, speed and mechanics evidence was imported without rerunning it. Local step AD remained reverse and outer derivatives exact automatic AD.

| Candidate | Solver termination | Solver iterations | Selected iteration | Solve time, s | Worker time, s | Checkpoint/export |
|---|---|---:|---:|---:|---:|---|
| initial | Solve_Succeeded | 22 | 22 | 466.911033 | 552.939405 | exported |
| revision | Maximum_CpuTime_Exceeded | 34 | 3 | 572.061858 | 661.468988 | exported |

Both selected candidates pass the `1e-5` hard normalized-residual tolerance
(initial `9.99e-9`, revision `5.52849e-6`) and relaxed-NLP feasibility checks.
The revision termination does not establish convergence. Both replay inputs
pass the finite design and six-channel force bounds.

Checkpoints contain the exact configuration, original input/execution identity, grid, initialization, ordered returned variables, selected solver result, retained vectors, diagnostics and timings. The real preservation checks compare each file checkpoint with its stored artifact and verify that the exported states and tensions decode exactly from the selected retained vector. The focused injected extraction failure recovered through the actual packaging function with only one mocked solver invocation. No new real NLP was used for recovery testing.

| Candidate and evaluation | Terminal error, mm | Holding position error, mm | Holding speed, m/s | Position limits | Speed limit |
|---|---:|---:|---:|---|---|
| initial, NLP state nodes | 5.514971 | 5.514971 | 0.01974186 | pass | pass |
| initial, dense BDF | 5.422547 | 5.422547 | 0.04312197 | pass | fail |
| revision, NLP state nodes | 5.406667 | 5.406667 | 0.01915398 | pass | pass |
| revision, dense BDF | 5.434130 | 5.434130 | 0.04218082 | pass | fail |

Acceptance uses the original unsoftened 0.01 m position and 0.02 m/s holding-speed limits. Reported slacks near `-1e-8` are numerical bound relaxation, not negative physical gaps. Independent BDF starts from the prescribed zero physical state, uses actual lengths and all 35 six-channel tension commands, and preserves continuous state across switches. Dense metrics use 0.0005 s samples with the established tolerances.

| Candidate | Original 36-node position disagreement, mm | Original 36-node velocity disagreement, m/s | Dense position disagreement, mm | Dense velocity disagreement, m/s |
|---|---:|---:|---:|---:|
| initial | 2.447584 | 0.03046345 | 2.459632 | 0.04661231 |
| revision | 2.451771 | 0.03037313 | 2.463434 | 0.04642945 |

The disagreement limits remain 1 mm and 0.002 m/s. The replay artifact’s existing `node_max` fields compare all 71 refined state nodes. The separate saved-output check above uses only the original 36 control-boundary nodes; it launches no integration and does not spend a replay slot. Dense comparisons use interpolated NLP tip outputs, as in the existing implementation.

The accepted final disposition is the original native `action=stop` plan, with an accepted receipt in `result_summary.json`. Its supporting references are preserved. The requested revision was executed and its returned evidence was available in the final model packet. No further provider send followed acceptance. The final model interpretation remains distinct from the numerical facts; the full original decision is linked below.

The model stopped because its requested effort/variation revision still failed both replay disagreement criteria and the independent holding-speed limit, and both authorized NLP attempts were consumed. It requested no third diagnostic replay. BDF holding speed improved by 2.18 percent, but remained more than twice the limit. The accepted STOP supports this bounded workflow decision; it does not endorse the model prose claiming that warm-start effects, other weights or objective degeneracy were excluded, that a dominant cause was established, or that the historical comparison proved a refinement gain. The CPU-limited revision exported an early retained iterate. The [post-STOP correction](../evidence/casadi_feedback_closeout_20261010/post_stop_correction.json) preserves the original decision and corrects these overclaims and numerical percentages. It was recorded after acceptance and was not sent to the model, preserving the no-more-sends rule.

Ten focused fixture tests passed initially. Only the provider/closeout fixture was rerun for the two concrete native-context repairs; the matching SDK direct-schema fixture passed. The first attempt to edit that fixture had a syntax error before any test ran. In the live activity, compatibility cancelled continuation before an eighth send until committed migration. Send 8 successfully retrieved the new revision feedback, then a local native-schema conversion error blocked send 9. A second committed migration preserved the same grant, task, costs and clock. Send 9 exercised protected closeout with a STOP-only plan schema and native retrieval restricted to new execution feedback. The old successful retrieval on send 6 has a generic accounting receipt incorrectly marked failed; its original successful tool feedback is preserved and the labeled correction explains that receipt. Future native-context receipts match their actual outcome.

| Consumed resource | Actual | Authorized ceiling |
|---|---:|---:|
| NLP attempts / solver entered / solver returned | 2 / 2 / 2 | 2 attempts |
| New BDF attempts / completed replays | 2 / 2 | 3 |
| Numerical seconds, including focused checks and saved-output evaluation | 1638.699485 | 3600 |
| Actual provider sends, including auxiliary requests | 9 | 12, including final 4 protected |
| Public workflow calls | 14 | 48 |
| Physical launches / additional research LLMs | 0 / 0 | 0 / 0 |
| Sealed elapsed activity, including engineering/reporting | 3004.332225 s | 14400 s, final 1800 s reserved |
| Provider elapsed time | 106.765000 s | Included above |
| Provider prompt / completion / total tokens | 172511 / 21989 / 194500 | Actual reported usage |
| Provider cache hit / miss tokens | 36096 / 136415 | Actual reported usage |

No monetary charge was reported by the provider; monetary cost remains unknown. The generic receipt’s `solver_status=not_run` does not cover extension-owned NLP execution. `backend_solves=0` counts physical launches, not the two NLPs. The final elapsed snapshot precedes ordinary Git delivery; numerical and provider allowance is never reset. No unknown worker/provider outcomes remain.

The first candidate-feedback loop and its model-selected revision establish a completed bounded research workflow. They do not establish physical validation, global optimality, joint-design benefit, LLM superiority, a unique source of discretization error, or convergence of the 0.005 s grid. Both new candidates use fixed design `d=0`; the comparison does not test joint design optimization. Historical and new schedules differ, so their discrepancy differences are not a controlled grid-convergence experiment.

Evidence: [summary](../evidence/casadi_feedback_closeout_20261010/result_summary.json), [decision trace](../evidence/casadi_feedback_closeout_20261010/decision_trace.json), [original final decision](../evidence/casadi_feedback_closeout_20261010/model_original_final_disposition.json), [preservation checks](../evidence/casadi_feedback_closeout_20261010/numeric_preservation_checks.json), [original-node comparisons](../evidence/casadi_feedback_closeout_20261010/original_node_comparisons.json), [artifact manifest](../evidence/casadi_feedback_closeout_20261010/archive_manifest.json). The directory includes candidate schedules, numeric checkpoints, complete replay trajectories, original plans, actual feedback, exact worker inputs/outputs, wire artifacts, receipts and counters. `final_packet.json` is an exported state snapshot after STOP; the exact before-send packets actually supplied are linked through the decision trace and archived wire requests.
