# Task-parameterized GVS free reach

`controller.gvs_nmpc@3.0.0` extends the public preparation, simulation,
evaluation, report and Route hooks. `gvs_nmpc_free_reach_v1` and controller v2
retain their strict original scope and unchanged asset.

Use `extensions.tendon_family.gvs_profile.reach_input`. Its JSON result is an
ordinary `SessionInput`: the task owns world target, initialization and timing;
`family.gvs_reach_control` owns `recipe`, `settling` and `numerical_source`.
Modify and freeze this public input before creating the session. No process
cache injection or target-specific controller code is needed.

Supported changes are target position, named joint initial positions/rates
(absolute limits 0.05 rad and 0.5 rad/s), task timing, control weights/horizon,
solver/plan-acceptance settings and sampled final-window acceptance. Robot,
materials, mount, gravity, free-space scene, backend/discretization, GVS basis,
and original reach evaluator remain fixed. This is not trajectory tracking or
contact/hardware control. Technical support does not promise target reachability.
Task/settling durations must lie on the control/sample grid; physics steps divide
the control period. Every warm state must be regenerated from measured state.

`recipe.seed_position_tolerance_fraction` (default 0.5 times original reach
tolerance) and `recipe.seed_speed_limit_m_s` (default 0.02 m/s) describe internal
early acceptance of an already feasible seed. They are separate from
`settling.window_s`, `position_limit_m`, `speed_limit_m_s`. Reports freeze and
display these actual settings; the original authoritative endpoint evaluator
remains independent.

`control.profile_describe` returns technical compatibility/model-use assessment,
historical evidence coverage, preparation state and separate authorization and
budget information. New v3 configurations do not inherit v2 validation, including
when their task happens to match. Model suitability and skill validation are
not execution permission. Route uses the same compatibility/report hooks.

Numerical preparation runs inside the budgeted `simulation.run` hook:

- `bundled_guess` checks the fixed numerical asset identity, order, dimensions,
  units and bounds, then imports its target-independent numerical values as a
  guess. The old equilibrium retains its original target/source; it is never
  asserted to solve the current target. Changed horizons/timing resample the
  guess only; dynamics-consistent states are regenerated in every update.
- `initial_state_pretension` generates a guess from the projected task initial
  state and bounded design pretensions. It requires no prior process or solve.
  It is not an equilibrium and has no closed-loop success evidence this round.

Preparation artifacts carry full execution scope, source, reuse, units/orders,
validity and time. Each execution builds its own graph/solver workspace for the
current target. Session creation and description are solve-free. Import/generation,
graph/solver construction, warm regeneration, solving and independent validation
remain charged execution costs, with separate timings. Sealed tool receipts can
be recovered by resuming the same folder; a new input requires a new folder.

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& $py examples/gvs_parameterized_reach.py make-input --target 0.29 0.05 0.19 --output runs/new_reach_input.json
# Optional: edit recipe, settling, task initializer/timing in this JSON.
& $py examples/gvs_parameterized_reach.py prepare --input runs/new_reach_input.json --output runs/new_reach
# Separate process; consumes the authorized one-backend budget:
& $py examples/gvs_parameterized_reach.py run --output runs/new_reach
```

The example uses the normal Host/registry path and no model service. It saves
input, assessment, public receipts, summary and report. `platform.sqlite` holds
the sealed evidence and exports; working backend folders need not be duplicated
in Git. The Stage 3.18 implementation report records the two actual outcomes and
the rejected fixed-state performance candidate. Ten seconds/update is a
development cost goal, not the ten-millisecond control deadline.
