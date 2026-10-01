# Sequential diagnostic handoff and bounded control verification

The authorized live attempt did **not** complete the cycle. The design role made
a real diagnosis request; the diagnostic role made real evidence queries, but
five responses contained multiple tool calls. The fifth exhausted the four
cumulative protocol corrections. No diagnostic report, design adoption,
numerical comparison, backend variant or model-authored final review followed.
Project use was 17/24 provider attempts, 14/60 tool calls, 0/3 backend attempts,
0/6 local solves, 0/24 short prediction/braking evaluations, 0 workers, and
117.62000000034459/3600 charged seconds. One of the tool calls was a later
read-only comparison of existing saved cases in the same ledger.

The live implementation also failed to enforce the model-requested diagnostic
subgrant: its request allowed four provider attempts and eight tools, while that
role used fifteen attempts and ten tools. The larger user-authorized project
limits were respected. This is an implementation defect, not a compliant
diagnostic subgrant outcome. Post-live fixes now enforce the narrower grant,
reject query artifacts passed as execution bindings with a clear error, and
reduce the default prediction view from 8978 to 6961 content bytes so it fits the
Host envelope. These fixes passed focused offline checks; they have not been
validated by another live model attempt. Original live source bytes and receipts
are retained separately from the repaired implementation.

The physical incumbent remains Stage 3.41: terminal error 0.007642608585867386 m
(reach passes), terminal speed 0.6351726092425104 m/s, final-window maximum error
0.05813810428573256 m and speed 1.5810152739742807 m/s (sampled settling fails),
mean update 17.075238151415917 s versus 0.01 s, and 35/35 deadline misses. There is
no newly validated physical improvement. See the compact `outcome.json` and
`focused_checks.json` for exact references and the limits of validation.

Stage 3.42 adds an optional diagnostic branch after saved-result inspection.
The historical design route and its deterministic `route.advance(action="diagnose")`
remain compatible. The additional `diagnosis.request` tool is route-visible when
granted, and yields to the fixed sequential coordinator. Diagnosis is not automatic.

The public contracts are in `schemas/platform_handoff.py` and registered in
`extensions/platform/manifest.py`:

| Entrypoint | Responsibility |
| --- | --- |
| `diagnosis.request@1.0.0` | Question, subject identities, exact imported manifest, scope, permitted tools, budget, stopping conditions |
| `diagnosis.check_request@1.0.0` | Advisory discriminating check with exact state/input selectors, fixed conditions, changed factor, numerical protocol and criteria |
| `diagnosis.submit@1.0.0` | `DiagnosticReport`, checked fact selectors, attribution, gaps, results and configuration-scoped recommendations |
| `design.respond_diagnosis@1.0.0` | Explicit adoption, deferral or rejection linked to a report and selected recommendation |
| `design.review_verification@1.0.0` | Model-authored final review linked to actual verification and its predeclared gate |

`tools/platform_diagnosis_coordinator.py` uses separate sessions in one project
store and the existing provider loop. Sessions run sequentially; no worker is
started. Provider requests, raw responses, corrections, tool decisions and role
transitions are retained. Recovery counters are transferred between roles;
provider/tool/backend reservations remain subject to the same project budget.
The final implementation also applies the diagnosis request's narrower tool
allowlist and budget as a subgrant before diagnostic work begins.

The tendon adapter `import_execution` in
`extensions/tendon_family/diagnostic_evidence.py` imports exact source bytes and
binds their original owner, configuration and export manifest. It does not add a
historical execution to the new session's `result_executions`. `BoundReader`
checks those bindings before serving evidence. `diagnosis.inspect_evidence`
provides summary, late motion, plans, prediction and saved-case comparison views.
Unavailable plans remain unavailable. Inspection never calls an optimizer or
advances the backend.

One-step velocity comparison uses the same alignment checks as position:
update, next timestamp, world frame and actual interval input. The prediction is
the recorded accepted first-step vector. Measured velocity is reconstructed as
`J_site(q_backend) @ qdot_backend` using the sealed MuJoCo XML, recorded joint
ordering and saved state. The vector discrepancy and both speed magnitudes are
reported separately. This does not equate projected GVS states to the full backend
state.

`diagnosis.saved_state_check@1.0.0` in
`extensions/tendon_family/diagnostic_math.py` performs explicitly charged new
numerical work. `prediction_braking` evaluates the recorded input and the
instantaneous decelerating input obtained from a linear objective over the
recorded unilateral tension box. Endpoint acceleration includes
`J qdd + Jdot qdot`. Near-zero velocity has no defined deceleration direction.
Short held-input nonlinear rollouts report speed, error, drift, force margin,
integration residuals and computation time. These are model predictions, not
verified physical braking.

`local_comparison` changes one existing tip-speed cost parameter and keeps the
robot, task, recorded projected state, previous input, effective horizon, bounds,
integration and solver budgets matched. Both solves use a declared fresh seed:
constant previous applied input with states regenerated by candidate dynamics.
This is not a reconstruction of historical warm starts. Plans are independently
checked for feasibility and compared in physical units at common timestamps;
different scalar objectives are not ranked against each other.

The experiment entrypoint is:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/stage342_diagnostic_cycle.py prepare
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/stage342_diagnostic_cycle.py run
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/stage342_diagnostic_cycle.py export
```

The one-shot live guard prevents a second experiment. `refreeze-prelaunch` is an
explicit migration available only before any paid or numerical work; it preserves
the previous freeze and sessions and does not create a new grant. The ledger is
local under `runs/stage342_diagnostic_cycle_20261001`; compact evidence is under
`evidence/stage342_diagnostic_cycle_20261001`. Exact limits and improvement/tradeoff
criteria are frozen before launch. Reach acceptance, sampled settling and timing
are reported separately. Rejected variants cannot replace the successful baseline.

Advisory braking descriptors remain separate from affine design scoring and
official backend evaluation. Saved-case controller/design mismatches are explicit;
candidate ranking and exclusion remain unchanged. The next physical design group
requires new authorization and evidence at multiple trajectory operating points.
