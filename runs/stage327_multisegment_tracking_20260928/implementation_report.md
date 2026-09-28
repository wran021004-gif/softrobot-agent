# Stage 3.27: two-segment sampled tracking

Baseline: `2b2fb6da3e941f3c939fe79e3fb1dbf5b9096aef`, initially clean on `feat/gvs-dynamics`. Implementation: `3fa014c` (full identity and repository-byte source hashes in `code_identity.json`). The Stage 3.26 accepted CSE optimization remains unchanged. The Stage 3.25 withdrawn SX experiment remains a negative result at `1b4c00f`; `baseline_record.json` links both historical archives without copying their databases or repeating their runs.

The frozen input is copied from the committed Stage 3.26 input, retaining robot, policy, physical settings, objective, tolerances, initializer, implicit integration, horizon, and stopping policy exactly. Only run identity and declared task/reference metadata, duration and scoring interval change. Knots use baseline p0/p1 at their original stored precision, and p2=p0+[-0.003,0.012,-0.014] m, at 0, 0.40, 0.70 seconds. The two separate quintic laws impose zero reference velocity and acceleration at the internal knot, with no dwell. They do not require actual robot settling. The path remains in world coordinates for all length candidates. Evaluation includes all 70 samples from 0.01 to 0.70 seconds under the unchanged 10 mm maximum-error and tendon-bound rules.

`family.cartesian_reference@2.0.0` adds ordered piecewise-quintic knots. Version 1.0.0 constant and single-quintic contracts remain intact. `reference_at` supplies the shared mathematical semantics to controller, evaluator and report. Existing absolute prediction-node scheduling remains unchanged: one persistent controller/clock/graph/warm state spans both segments, and nodes beyond the last knot clamp to zero reference velocity. No numerical solver or CSE changes were made. The public report adds per-segment peak times and internal-knot motion diagnostics; these do not alter global scoring or duplicate the knot in global RMS. New deterministic candidate labels and live guidance describe tracking and actual task/sample counts. Live guidance requires candidate-bound analysis, both authoritative structured statements, signed length changes and evidence-consistent prose.

Six focused offline checks passed: four new checks and two relevant existing shared-reference/evaluation checks (commands and measured durations in `verification_results.json`). They cover endpoint/clamp and derivative behavior, knot continuity, legacy compatibility, absolute nodes across both boundaries, preserved schedule workspace, full-grid scoring, startup/intermediate violations with a correct endpoint, and one-count knot RMS. The existing graph-path test verifies expression identity under schedule updates. No backend rollout or provider call is used by those tests; no historical maintenance campaign or performance benchmark was repeated.

Environment is recorded in `environment.json`: existing softagent Python 3.11 interpreter and packages, all numerical thread settings at 1. No dependencies upgraded, subagents used, MATLAB/GPU/compiler setup, or solver migration.

**Outcome: the implementation checks pass, but the single deterministic task fails its frozen scientific acceptance rule.** No live session was prepared or run; no credentials were loaded. There is no live tracking, structured-delivery or prose-delivery outcome. `live_gate_decision.json` and `provider_delivery_review.json` record this explicitly. The conditional live input is retained for review, not executed. No second deterministic rollout was justified because no implementation defect was identified.

The public simulation -> evaluation -> profile-report chain completed all 70 expected samples with valid evaluation. Maximum/RMS/terminal position error was **11.264183 / 3.035140 / 1.541298 mm**. The two violations were 11.264183 mm at 0.05 s and 11.070651 mm at 0.06 s. The global 10 mm rule fails despite the acceptable endpoint. Segment 1 peaks at 0.05 s; segment 2 peaks at its endpoint with 1.541298 mm. Around the middle knot, errors at 0.39/0.40/0.41 s were 1.470840/1.504645/1.514315 mm; actual tip speeds were 5.879356/3.632552/2.272104 mm/s. Reference speed is zero at 0.40 s, but the actual robot is moving. Tendon tensions span 1.859347-5.042567 N with zero bound violation.

All 70 controller plans passed the existing feasibility checks (largest scaled residual 8.140396e-6). Optimizer convergence: 0; holds: 0; solver errors/failure flags: 0; recovered plans: 3. All raw terminations were `User_Requested_Stop`, classified as feasible early stops. Deadline misses: **70/70**. Mean complete update was **8.684704 s**, range 7.627960-31.908277 s, sum 607.929311 s. Simulated duration was 0.70 s; charged simulation wall time **612.672 s**, backend call 609.073843 s, and complete charged public-chain wall time 616.359 s (including description/evaluation/report). Graph construction was 1.486328 s; solver construction plus later cache lookups 4.519122 s. Solver lookups near the internal knot were about 5 microseconds; the unchanged scheduler retained the same solver. These scopes overlap and must not be summed as independent costs.

All 70 predictions align with measured interval endpoints and applied tensions; maximum command discrepancy is exactly zero. Maximum/RMS one-step position discrepancy is **1.835160 / 1.250334 mm**, with the maximum over 0.59-0.60 s. Discrepancy is above the descriptive 1 mm level during 0.03-0.07 s and continuously across the aligned intervals from 0.22 to 0.70 s; this level was not an acceptance threshold. The full interval list is in `deterministic_audit.json` and `failure_diagnostics.json`. Sustained prediction/execution disagreement is observable, but it does not identify a physical cause or establish that it caused the startup failure.

Saved-data diagnosis confirms that the first segment matches baseline reference position and velocity exactly at every 0.01 s node through 0.40 s. Accepted commands already differ from the historical run at t=0 (maximum tendon difference 0.451083 N), before any prediction node can see the new segment. The robot/policy are unchanged and the wall-time stopping policy can produce different feasible returned plans; no causal isolation or repeatability distribution was measured. This is not evidence that crossing the waypoint caused the early violation. The fixed numerical test is reproducible as a procedure, not a claim of bitwise repeatability under wall-time stopping.

Actual usage: **1 deterministic backend attempt, 70 controller optimization updates, 4 tool attempts/charged tool calls, 0 preflight rejections, 0 live backend attempts, 0 provider request attempts, 0 protocol corrections and 0 worker calls**. There are no provider tokens or provider monetary charges in this round. `usage_audit.json` retains exact ledger accounting. There are no live candidate builds/analyses or provider-authored requests/responses to archive because that conditional stage was never started. The deterministic chain has no Route-owned candidate-analysis prerequisite; its current numerical preparation and configuration bindings are retained.

This round establishes the reusable reference implementation and a complete failed task result, not accepted multi-segment tracking or successful live LLM delivery. No continuous-time accuracy, actual stopping, optimizer convergence, robustness or real-time operation is claimed. Next work should examine the saved startup command/early-stop differences and the identified sustained one-step discrepancy before choosing any model change or expanding the task. No new physical model is justified from this evidence alone, and that investigation is not started here.

## PowerShell reproduction

The actual one-rollout deterministic command, from `D:\softrobot-agent`, was:

```powershell
$softPython = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$out = 'runs/stage327_multisegment_tracking_20260928'
& $softPython -m unittest tests.test_stage327_multisegment -v
& $softPython -m unittest tests.test_stage324_tracking.TrackingTests.test_same_graph_path_constant_and_absolute_moving_reference tests.test_stage324_tracking.TrackingTests.test_interval_evaluation_rejects_terminal_only_and_missing -v
& $softPython "$out/freeze.py"
& $softPython examples/gvs_tracking.py run --input "$out/frozen_input.json" --output "$out/deterministic"
& $softPython "$out/audit_deterministic.py"
& $softPython "$out/failure_diagnostics.py"
& $softPython "$out/audit_usage.py"
```

The completed evidence locations must not be overwritten or resumed. `freeze.py` refuses to overwrite its frozen input. Any future numerical reproduction requires a fresh output folder, run_id and grant. Reading the audit against the saved evidence is offline and does not authorize another rollout.
