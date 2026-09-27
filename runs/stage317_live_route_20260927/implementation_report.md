# Stage 3.17: completed real-provider capability-use acceptance

Current result (2026-09-27): the real DeepSeek decision / public execution /
independent evaluation / evidence delivery chain completed successfully on
unchanged implementation `bb7ae76`. No source fix or new tests were needed.
The original reach passed; additional sampled settling failed; real-time
operation was not demonstrated. The provider's final interpretation passed
the manual evidence review below. No launch blocker remains.

## Fresh execution and acceptance

The existing prepared session `gvs-live-1d8a5832db1e` was resumed after read-only
inspection confirmed zero prior calls. The current attached request explicitly
authorized paid DeepSeek use and the necessary context transmission. Network
execution was permitted this turn. The earlier two denied launches and zero-call
checkpoint remain in `launch_review.json.historical_checkpoint` and Git history.

Four genuine `deepseek-flash` responses selected these public actions:
`control.profile_describe`, `route.advance build`, `route.advance run`, and
`route.advance finish`. The run invoked three child tools: `single-simulation`,
`single-evaluation`, and `single-profile-report`. All receipts are completed and
uncached. Total: **4/24 model calls, 7/60 tools, 1/1 authorized new backend
execution, 0 workers**. The unused second project backend allowance was not used.
Provider usage totals 51,135 tokens; no monetary price is inferred.

The child owner is `gvs-live-1d8a5832db1e-53bb5822a962609c`; new execution is
`c102aeb4a355401fab0a15af3c6d70b6`. The original straight-start task remains:
target `[0.29, 0.035, 0.19]` m, duration 0.35 s, tolerance 0.01 m, 12 cells per
segment, control period 0.01 s, physics step 0.0005 s, and ideal bounded tensions.
There was no controller tuning, historical trajectory replay, or private cache
injection. The fixed profile's existing numerical preparation remained intact.

| Evidence from this execution | Result |
| --- | --- |
| Original evaluator `evaluate.reach@1.0.0` | valid; task success true |
| Terminal position error | 8.473431 mm |
| Last 50 ms sampled position maximum | 8.694221 mm; limit 10 mm |
| Last 50 ms sampled speed maximum | 0.03156205 m/s; limit 0.02 m/s; settling failed |
| Terminal tip speed | 0.02094737 m/s |
| Accepted plans / converged / initialization selected | 35 / 0 / 7 |
| Optimization termination | 35 feasible early stops; raw `User_Requested_Stop` |
| Maximum accepted plan violation | 9.235746e-6 |
| Hold-last responses / solver errors | 0 / 0 |
| Tension range / force-bound violation | 0.566200–5.025997 N / 0 N |
| Mean delivered update / deadline misses | 24.977007 s / 35 of 35 |
| Mean preparation / numerical solve / validation | 9.578587 / 14.895135 / 0.256703 s |
| Graph / solver construction | 1.315432 / 3.973356 s |
| Simulation tool wall time | 878.735 s |
| Charged project/session wall time | 912.095 of 7200 s |
| First context through final event elapsed time | 923.510237 s |

The measured live interval is 03:27:13.995488–03:42:37.505725 UTC. Ledger wall
time is charged tool/model time and is distinct from the event interval.
The engine completed 700 physics steps. Backend solve time is 874.371469 s;
simulation tool time additionally includes preparation/export overhead.

## Manual review of the provider's actual final delivery

`model-3` received payload
`bee9c8db2a239962821bf7aafd32d73ef170843fb9a28decee8db20b84bcf6ba`, containing
the new evaluation and sealed report summary, before it returned its finish
action. Its raw service response is
`61e789a810ce4e86f5320c684c4fbf2c20e666c3255881236009a2ec855e49a4`.
`model_final.txt` is the verbatim finish reason extracted from that response;
it is not a developer-authored replacement or an extra provider message.

The final text correctly reports reach success, failed sampled settling due to
speed, all missed deadlines, zero converged updates, and seven initialization
selections. It uses this execution's timing, not the historical timing. It does
not claim improvement at every update, continuous settling, real-time control,
general target transfer, contact/hardware capability, or comparison of multiple
controllers. Its no-reset statement is consistent with completed execution and
the existing per-step numerical-failure detection; zero hold responses alone
would not establish that. Its statement about no further solve is understood
within the exhausted authorized session backend budget, not as a scientific
claim that future experiments cannot improve performance.

Thus call-chain acceptance and evidence-interpretation acceptance pass.
Control acceptance is specifically: original reach passes, sampled settling
fails, real-time delivery fails. The deterministic endpoint matches prior
evidence, but fresh service IDs, uncached execution receipt, timestamps, and
new sealed exports establish a new execution.

`behavior_audit.json` indexes service responses, delivered contexts, provider
decisions, all tool receipts and the review. `summary.json` and `report.md`
contain the measured control result. `platform.sqlite` retains content-addressed
raw responses, payloads, receipts, trajectory and backend exports, avoiding a
duplicate checked-in backend directory. The report belongs to the child owner:

- Report: `8b81aec5365f5dba252af789e7f7ad63f495fdbce7b84d019979ea26e6555cb1`.
- Evaluation: `1359c8df075550abefc4391694f03fd27c03352b8fa313c9c2e8214551eb2c9b`.
- Simulation: `52f067b938db0037c185fbb94d0b70f39cea4cd5defbb579a11645ea2854cbc7`.

Read-only `inspect` was run after completion. It regenerates automatic audit
fields; this report retains the manual review and chronology independently.
No full suite or additional simulation was run. Remaining limits are the fixed
free-space scope, ideal tension execution, failed sampled speed condition,
nonconverged accepted plans, and computation far slower than the control period.

## Earlier implementation and historical preparation checkpoint

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

## Historical prepared experiment and launch status (before this turn)

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
# This turn's authorized launch (already completed; do not start a new experiment):
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
