# Stage 3.17: Route profile reporting and prepared live capability use

Implementation commit: `00583ce`, based on clean `923dd51` on
`feat/gvs-dynamics`. The attached request identifies this later Route integration
as the current task. The older Stage 3.12 through NMPC implementation and
historical evidence were preserved.

## Implementation

- Controller capability declares the applicable reporting tool and scope hook.
  Route grants it to the owning child only when the parent authorizes it.
- `single-profile-report` runs in the session owning `single-simulation` and
  `single-evaluation`, with `route-executor` attribution. It requires no new
  strategy declaration or skill validation.
- Report reference, owner/execution identity and compact result survive Route
  inspection, incumbent selection and final delivery. Sealed calls reuse their
  original receipts; building stays solve-free. Ordinary Route behavior passes
  focused regression checks.
- Profile presentation uses the declared combination, checked scope and tool
  authorization. GVS prediction and MuJoCo serial-cell execution remain distinct.
- Trusted preparation imports original skill revisions and source artifacts
  into a new project. Historical snapshots/events are preserved as evidence,
  not executable sessions or new receipts. Grants and call ledgers are not
  imported. The validated development skill is retrieved with matching scope
  and no human approval.
- The dedicated example uses the existing DeepSeek adapter and Host loop,
  existing configured model `deepseek-flash`, 16,384 output tokens, at most
  24 model calls, 60 tool calls and one primary backend execution. Project
  ceiling two is reserved for a separately justified infrastructure retry.

Changes: `extensions/tendon_family/{manifest,route}.py`,
`tools/platform_skills.py`, `examples/gvs_nmpc_route_experiment.py`,
`tests/test_gvs_route_report.py`, and `docs/gvs_nmpc_route_experiment.md`.
Focused checks and the one corrected test-fixture error are recorded in
`verification.json`. No full suite, controller tuning, historical dynamics
rerun, paid smoke request or subagent was used.

## Prepared experiment and launch status

Prepared run: `gvs-live-1d8a5832db1e`. New project grant, fixed original physical
scope, straight start, 350 ms task, target `[0.29, 0.035, 0.19]` m, 10 mm
endpoint tolerance, 12 cells/segment, 10 ms control period, 0.5 ms physics step
and ideal tendon tensions are unchanged. Preparation context contains the
matching validated skill `gvs_nmpc_free_reach@1`. It has not yet been delivered
to a real provider.

At this checkpoint, automatic approval review rejected process creation twice.
It treated the older IDE selection's prohibition on paid model experiments as
controlling and did not accept the attached request's explicit authorization.
Direct user confirmation is pending. See `launch_review.json`. There are zero
real model requests, zero executed tools and zero fresh backend executions.
No fresh reach, settling or model-behavior outcome exists. Historical success
is not substituted for a new result. Implementation is complete; live acceptance
remains blocked at this checkpoint.

`workflow.json` records budgets, interpreter, model configuration, thread settings
and reservation analysis. `prepared_context.json` records scoped capability and
skill availability. `platform.sqlite` preserves the new grant and imported
evidence. `behavior_audit.json` and `route_status.json` record current state.

## Reproduction

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$out = 'runs/stage317_live_route_20260927'
# Once direct live-provider authorization is confirmed:
& $py examples/gvs_nmpc_route_experiment.py run --output $out
# Read-only evidence inspection; no provider or backend execution:
& $py examples/gvs_nmpc_route_experiment.py inspect --output $out
```

For a separately authorized new experiment, choose a fresh output directory and
run `prepare` then `run`. Credentials are parsed as data into the process and
are not printed or persisted. The real-provider loop must run against stable
dependency-tracked source. Skill import establishes availability for this exact
scope; it does not establish empty-Store discovery without explicit preparation
or transfer to another task.
