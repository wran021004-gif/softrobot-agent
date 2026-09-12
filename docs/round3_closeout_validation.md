# Closeout validation record

This file records development and regression separately from the formal campaign.

- Initial sandbox attempt: temporary-directory ACL failures in software tests and
  MATLAB startup UnicodeDecodeError. No MuJoCo rollout or mechanics solve started.
  Original logs are retained; the normal-permission retry succeeded.
- Six focused tests passed: authority/plan, stage reservations/incumbent/key,
  cross-process interrupted reservation/resume with new retry ID, evidence corruption,
  independent visual failure, and LOG_REPLAY interface.
- Real validation parent: `20260912T080900_304322Z_a24c91ad`.
  Four development MuJoCo rollouts, fifteen top-level MATLAB mechanics solves.
  These are not formal candidates. The C1 exact baseline error was preserved with
  normal trajectory recording, and an independent world +z force pulse changed response.
- Real statics: zero load, known tip force, gravity and nonnegative tendon input passed
  interior equilibrium residual checks. Real dynamics: rest, unforced energy decay,
  tendon pulse and external force pulse completed with finite states.
- Fixed synthetic stiffness=1.4 was recovered as 1.3999999839206634; training residual
  MSE=5.15888e-22 (N m)², held-out validation MSE=7.25072e-21 (N m)².
  Invalid negative tension returned a structured failure before backend startup.

Full regression ran exactly once: 139 tests, zero skipped, 167.812 s, PASS, with real MATLAB enabled. Instrumentation counted 54 run_task invocations (the raw counter is named mujoco_rollouts; it includes rejection/error-path tests), plus 8 analyze_workspace, 15 plan_pcc_reach and 8 analyze_clearance calls. They are regression calls, not formal candidates or additional development experiments.

Formal campaign audit, final analysis counts and portable evidence references are appended after actual execution. Historical 133-test results are not counted as validation of this change.

Formal campaign: `20260912T081952_082199Z_ce91267e`, execution commit
`65b8d2acd05a4df72897362764fec0cabdbd9d1d`. 41 attempts = 25 screening + 16 MuJoCo
routes. Two verified current-revision model cache reads; zero retries. MATLAB
top-level calls: 41 workspace + 41 PCC planner + 41 centerline; compile/run_task
each 16. Historical raw evidence was verified but not used as a current-code cache.

One numerical reproduction compared all 1000 samples and final states: every maximum
absolute difference was zero (predeclared atol/rtol=1e-9). The single parent campaign
stopped after the two frozen improvement rounds.

Independent post-campaign analysis: `20260912T082624_505318Z_6c8bf663`. Six additional
mechanics solves bring the persistent total to **21 / 200**: 18 passed, 3 failed.
Three constant-final-tension statics found interior equilibria. All three observed-force
dynamic replays exceeded the one-mode domain and returned structured failures; no
valid trajectory/accuracy claim is made. These conditional force-input analyses are
not C1 length-servo predictions. Main trajectories contain nonzero sampled contacts;
the independent rod excludes contact. Boundary conditions therefore differ, and no
static-versus-transient accuracy or causal diagnosis is inferred.

Development total outside regression: **4 / 12** real MuJoCo rollouts. Exactly one
full regression was used. After the campaign, two narrowly targeted non-numerical
tests passed (4.636 s): automatic E-budget routing for interrupted MuJoCo and
cross-process recovery. No formal result was rerun or ranked under new source code.

Post-execution review changes affect the offline auditor and interrupted-attempt
recovery only. The initial auditor rejected three historical hello-example files
that plan discovery indexed but execution snapshots omitted. Their exact original
bytes matched all frozen hashes and are bundled under `plan_sources/`, explicitly
auxiliary rather than executed child sources. Numerical/controller/task sources
were present throughout. The auditor additionally checks TaskSpec target/tolerance
and each controller's incumbent. Sealed artifacts/manifests were not rewritten.
All formal results retain the single 65b8d2a execution revision; audit/recovery fixes
belong to the later delivery revision.

The [portable package](evidence/round3_closeout_evidence.tar.xz) is 9,141,564 bytes.
Solid xz compression preserves every original hashed byte while reducing repeated
snapshot overhead (the intermediate ZIP was 22,114,603 bytes). The final
[offline audit and corruption test](evidence/round3_closeout_audit.json) passed with
MATLAB and MuJoCo imports explicitly blocked. It verifies 41 formal children plus
5 development/analysis runs. Changing the best run's copied tip x by 0.01 m was
rejected with `Artifact hash mismatch: mujoco_result.json`; the original archive
hash was unchanged. Reproduce this non-numerical check with:

```powershell
python examples/audit_closeout_corruption.py docs/evidence/round3_closeout_evidence.tar.xz --output runs/closeout_corruption_check.json
```
