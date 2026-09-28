# Stage 3.22: candidate-capable NMPC and prepared real design experiment

Implementation is complete and the bounded experiment is prepared. The real
provider launch was rejected before process creation by automatic approval
review. It treated the older IDE selection's prohibition on paid experiments as
controlling despite the attached request's explicit authorization. Direct user
confirmation is pending. No workaround or indirect launch was attempted.

There are **zero real model requests, zero executed tools and zero fresh backend
attempts**. No provider-selected design, fresh reach outcome or provider delivery
exists. Historical success and the numerical plan check are not substituted for
the requested real experiment. Acceptance is not achieved at this checkpoint.

## Changes and verification

Checkout started clean on `feat/gvs-dynamics` at the attachment's reviewed commit
`b783a31d3fe2993ebf0881c3e720385bfe280a89`. No historical artifact was changed.
One agent was used. The resolved interpreter is
`C:\Users\gugugaga\miniconda3\envs\softagent\python.exe`, Python 3.11.16.

- `extensions/tendon_family/gvs_profile.py`: explicit v4 length-candidate path;
  compatibility keeps topology, physical scene, materials, damping, tendon and
  actuator declarations fixed. Experiment length bounds remain in public input.
  Numerical dimensions, basis, projection, tendon order, force limits and nominal
  initial metadata come from the candidate. Only compatible historical tensions
  and initial applied input are reused. Historical states/equilibria are not.
  Candidate pretension supplies a cold guess when needed.
- `extensions/tendon_family/gvs_nmpc.py`, `candidate.py`, `manifest.py`: register
  and connect v4 to the existing preparation hook, public build and execution-local
  workspace. Existing measured-state regeneration, independent plan validation,
  tension bounds and recorded hold response remain in use. Versions 2/3 retain
  their fixed-robot contracts.
- `examples/gvs_nmpc_route_experiment.py`: honor an explicit Route input's tool
  grants, design policy and project/session budgets. Historical invocations keep
  their one-attempt default. Existing credential loading and provider audit reused.
- `examples/gvs_design_input.py`: reusable explicit experiment input with task,
  baseline design, two authorized length variables, fixed controller recipe,
  execution bindings, initialization policy, budgets and historical references.
- `tests/test_gvs_candidate_reach.py`: two focused checks for candidate physics,
  preparation, identities, frozen task/recipe, a second target/length input,
  solve-free public build and preserved budgets.
- `docs/gvs_candidate_reach.md`: scope, preparation semantics and commands.

Two new candidate tests pass. Six existing parameterized-reach and Route-report
tests also pass, including current child execution/evaluation/report propagation.
The initial new tests exposed a resolved tendon field mismatch (`entity`, not
`id`); it was corrected and those two tests then passed. No full suite was run.

Exactly one numerical plan check used near length 0.162 m, far length 0.12 m,
the original task and actual projected straight initial state. This is an
implementation fixture, **not the provider's design choice**. Candidate warm
states regenerated successfully; accepted plan, raw policy status
`feasible_early_stop`, independently evaluated scaled violation
`2.811878334341156e-13`, total 39.493 s. This does not establish a successful
backend reach. See `plan_check.py`, `plan_check.json` and `verification.json`.
No deterministic full baseline/candidate rollout was performed.

## Frozen experiment and budget

Session: `gvs-live-ce84ecb1bfcd`. Authority is `experiment_input.json`, with the
prepared normalized input in `input.json` and dependency snapshot in the Store.
`workflow.json` records the interpreter, model, thread settings and reservations.

| Quantity | Frozen value |
|---|---|
| Target | `[0.29, 0.035, 0.19]` m |
| Duration / original tolerance | 0.35 s / 0.01 m |
| Control / physics / sample period | 0.01 / 0.0005 / 0.01 s |
| Mesh | 12 cells in each section |
| Near baseline / allowed | 0.16 m / 0.15–0.17 m |
| Far baseline / allowed | 0.12 m / 0.11–0.13 m |
| Controller | v4 execution, bundled Stage 3.15/3.16/3.17 recipe; fixed |
| Prediction | 10 intervals, one implicit substep each |
| Settling, reported separately | final 0.05 s, position ≤0.01 m, speed ≤0.02 m/s |
| Provider | existing DeepSeek adapter, `deepseek-flash` |
| Ceilings | 24 model requests, 60 tools, 3 total backend attempts, 7200 s |
| Per-call reservation | 1800 s; evaluation/report headroom retained |

The public candidate builder enforces the two numeric bounds. No controller,
model, discretization or template edits are authorized. Scientific tools that
still resolve the parent baseline are excluded. The provider receives the task,
space and historical scope and must choose its own millimeter-scale design
change and next actions. Historical validated skills are not imported as
validation for changed designs. The existing child execution owns its report,
which propagates into the Route incumbent and final delivery.

## Evidence and acceptance

`behavior_audit.json`, `design_audit.json` and `route_status.json` currently
confirm the prepared, unexecuted state. `launch_review.json` preserves the exact
blocker. `audit_design.py` links provider choices, effective candidate, compiled
physics, numerical preparation, backend exports, evaluation and report. A
separate review of actual provider interpretation is required before real
call-chain acceptance; receipt in context alone does not establish correct use.

| Acceptance | Current result |
|---|---|
| Genuine provider call chain and explicit delivery | Not run |
| Provider-selected changed design execution | Not run |
| Unchanged original reach task | Not evaluated |
| Backend settling, tension and solve/deadline metrics | Unavailable |

## Commands

Read-only inspection (no provider/backend calls):

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$out = 'runs/stage322_live_design_20260927'
& $py examples/gvs_nmpc_route_experiment.py inspect --output $out
& $py "$out/audit_design.py" --output $out
```

After resolving automatic approval review's authorization conflict, the existing
prepared session can be launched without increasing any budget:

```powershell
& $py examples/gvs_nmpc_route_experiment.py run --output $out --input "$out/experiment_input.json"
```

Focused implementation checks (no paid requests or full backend rollout):

```powershell
& $py -m unittest tests.test_gvs_candidate_reach tests.test_gvs_parameterized_reach tests.test_gvs_route_report
```

The next step is the authorized real launch, then read-only identity and provider
interpretation review. Remaining interface work is candidate selection for the
omitted scientific tools and NMPC control editing; neither is needed for this
fixed-controller design experiment. The narrow length envelope does not establish
robustness or transfer to other topology/material/contact/actuator models.


## 2026-09-28 continuation

The final-candidate audit was corrected and three synthetic association checks passed. The old frozen session remains unchanged. The exact 1 mm acceptance clarification required a new frozen input in `../stage322_live_design_20260928` (run `gvs-live-e593ca2b7c60`), with unchanged scientific settings and the same stage-wide budget. The old live ledger and dependency compatibility were checked before preparation. The current attached request explicitly superseded the older paid-experiment prohibition, but automatic approval review again rejected the direct launch before process creation, treating attachment authorization as untrusted. No credential was loaded, no real request or backend attempt occurred, and no workaround was attempted. See the continuation `implementation_report.md`, `launch_review.json`, `design_audit.json`, and `engineering_experience.json` for the actual outcome. The historical rejection above is retained as history; real-experiment completion remains blocked.


## Direct-chat authorized execution completed on 2026-09-28

After the user withdrew the paid-experiment prohibition directly in chat, the prepared continuation session ran successfully through DeepSeek and two MuJoCo attempts. The delivered changed design used near/far lengths 0.159/0.120 m and passed original reach at 9.438402 mm; sampled settling failed. The provider explicitly delivered the correct execution but incorrectly described near length as 0.150 m / a 10 mm change, so provider interpretation and overall final acceptance failed. Usage: 24 model requests, 30 tools, two backend attempts, 2372.451 charged seconds. Earlier rejection records remain historical. See `../stage322_live_design_20260928/implementation_report.md`, `provider_delivery_raw.json`, `provider_interpretation_review.json`, `design_audit.json` and `engineering_experience.json` for the actual outcome. No third attempt or correction call was made.
