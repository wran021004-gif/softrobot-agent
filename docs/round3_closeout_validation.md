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
