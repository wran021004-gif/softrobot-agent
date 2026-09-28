# Stage 3.22 continuation: audit fixed; real launch rejected

The final-candidate audit fix is complete. The genuine paid DeepSeek launch was
attempted directly and rejected by automatic approval review before process
creation. Stage 3.22's real-experiment objective remains blocked. No replacement
offline experiment, connectivity test, numerical plan check, or backend rollout
was performed. No credential was loaded or external request sent.

## Audit changes

`../stage322_live_design_20260927/audit_design.py` now resolves delivery by owning
run and simulation execution, then checks configuration, simulation output,
evaluation and report references. Candidate labels are display information.
Repeated references to one sealed execution are deduplicated by identity;
inconsistent evidence is reported rather than resolved by first matching label.
Build decisions must originate in recorded real provider responses. The audit
checks built configuration against the executed candidate, authorized length
bounds, and report ownership in addition to the existing physics/preparation
checks.

The audit independently reports aggregate changed-design execution, delivered
original reach, delivered changed-design reach, call-chain completion and
interpretation. Final acceptance requires all criteria on the delivered changed
execution. A changed failure followed by an unchanged success cannot pass.

Interpretation review must bind the run, execution, configuration, evaluation,
report, finish request, raw provider response and conclusion digest. Receipt of
the matching report in the finish request's context is checked separately from
correct interpretation. A stale review or a bare boolean cannot certify it.
The reviewer is this assistant after reading the actual evidence; no new human
sign-off gate was introduced. Here no response exists, so no review was invented.

Three synthetic tests in `tests/test_stage322_design_audit.py` passed: repeated
labels/mixed references; changed failure then unchanged success; and current
bound review versus stale or unqualified review. The empty-session audit also
ran successfully. No historical numerical checks were repeated.

## Frozen session and authorization

Checkout: clean `feat/gvs-dynamics`, HEAD
`9c6ae8953bfeba8fc391b919b44eeb698be7bec3`. One agent. No push, merge or commit.
Interpreter: `C:\Users\gugugaga\miniconda3\envs\softagent\python.exe`.

The original `gvs-live-ce84ecb1bfcd` session was compatible and its live ledger
showed zero usage and no occupied reservations. Its frozen input did not state
the exact 1 mm threshold. The fresh `gvs-live-e593ca2b7c60` session adds only that
clarification and the same-delivery acceptance requirement to recorded guidance.
The old frozen input and dependency snapshot remain unchanged. The new snapshot
also passes compatibility. `continuation.json` links both sessions and budgets;
`prelaunch_verification.json` records checks. An audit-only code change was not
the reason for creating a new session.

The task remains target `[0.29, 0.035, 0.19]` m, duration 0.35 s, tolerance 0.01 m,
control/sample period 0.01 s, physics step 0.0005 s, twelve cells per section.
Near/far baseline lengths remain 0.16/0.12 m, allowed ranges 0.15–0.17/0.11–0.13 m.
Controller v4 and the bundled Stage 3.15/3.16/3.17 recipe are unchanged.

The previous rejection is preserved in the old `launch_review.json`. The new
`launch_review.json` preserves this continuation's exact rejection. Review cited
the older IDE prohibition and classified the attached superseding authorization
as untrusted. No retry or indirect launch was attempted after rejection.

## Outcomes

| Outcome | Actual result |
|---|---|
| Real provider/backend execution | Neither occurred |
| Provider-selected final lengths/rationale | Unavailable; no decision exists |
| Call-chain completion | Not achieved |
| Changed-design execution | Not achieved |
| Delivered original / changed-design reach | Not evaluated / not achieved |
| Explicit provider delivery / interpretation | Absent / not reviewable |
| Final acceptance | Not achieved |
| Reach error / sampled settling | Unavailable / not evaluated |
| Tension, solver and timing metrics | Unavailable |
| Model / tool / fresh backend counts, both sessions | 0 / 0 / 0 |
| Charged experiment time / provider cost incurred | 0 s / no provider request cost |
| Remaining stage budget | 24 models, 60 tools, 3 backends, 7200 charged seconds |

`design_audit.json` and `behavior_audit.json` record the actual empty ledger.
`engineering_experience.json` is an evidence-linked blocked engineering record,
not a validated robot/controller skill. There is no `model_final.txt`, provider
response or numerical report to cite; this report must not substitute for one.

## Commands

Read-only inspection and focused verification:

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$out = 'runs/stage322_live_design_20260928'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& $py -m unittest tests.test_stage322_design_audit
& $py examples/gvs_nmpc_route_experiment.py inspect --output $out
& $py runs/stage322_live_design_20260927/audit_design.py --output $out
```

The rejected launch command, recorded for use only after resolving approval:

```powershell
& $py examples/gvs_nmpc_route_experiment.py run --output $out --input "$out/experiment_input.json" --credential-file "$HOME\.codex\.env"
```

The smallest next step is resolving the reviewer's trusted-instruction conflict
and launching this prepared session. No additional control work or numerical
preparation is needed first. Then review the actual provider conclusion against
its execution and save the resulting tested configuration and costs. Nothing
here validates the allowed length rectangle or any new physical configuration.
