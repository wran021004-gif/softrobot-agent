# Task-aware mathematical evidence (M1)

M1 adds deterministic descriptions and evidence scope to `research_analysis`.
It does not implement a trajectory feasibility solver or a tracking controller.
The independent evaluator and reach/hold acceptance assembly are unchanged.

## Data flow and ownership

`dispatch` verifies the owned candidate against study state, then reads its frozen
effective configuration. It does not resolve mutable research JSON sources.
`ResearchTaskAdapter.analysis_requirements(binding)` owns reach translation;
`describe_analysis_requirements` exposes it to analysis callers. The common
`TaskAnalysisRequirement` also accepts explicitly declared, validated fixtures.
`model_assessment` reuses the existing registry and `assess_model_uses` for the
actual GVS binding used by candidate mathematics. `check_analysis_applicability`
checks the operation, outputs, input bounds, sampling and available horizon.
`calculate` retains the original numerical algorithms and raw result, attaching
`task_analysis`, `analysis_applicability`, and a versioned `scoped_claim`.
The existing Store saves these fields in the same candidate analysis artifact.
The tool response exposes applicability and claim; `evidence_read` exposes full
requirements, model and raw verification data. No prompt or Agent change is needed.

## Contract and sampling

`task-analysis-v1` uses SignalSpec identity, dimension, units, frame and phase.
Each constraint has ordered unique nonnegative sample indices, one reference
vector per index, and frozen-configuration JSON-pointer provenance.
`norm_bound` means `||signal[index] - reference[index]||_2 <= radius`.
`component_interval` means `lower <= signal[index] - reference[index] <= upper`.
The inclusive absolute task grid must match duration and sample period within
1e-12 seconds; invalid indices and nonfinite values are rejected.
Physical inputs retain nonnegative total tendon tensions, limits, channel order,
newtons, tendon-path frame, pre-step phase and the task control period.
The current task yields terminal index 35 and holding indices 30 through 35,
with separate terminal-position, holding-position and holding-speed requirements.
Values come from the frozen evaluator tolerance and controller settling contract.
Task/candidate/configuration/source/evaluation-profile identities are retained.
Time-varying references use the same schema; their tests are synthetic fixtures.
They do not register or establish an executable tracking task.

## Applicability and evidence

Schema expressibility, mathematical applicability and executable compatibility
are separate. Execution support is explicitly `not_assessed` here; existing
task/controller/backend compatibility checks retain ownership of that question.
Endpoint analysis checks terminal position only. Braking also checks the final
speed sample; the rest of the holding window remains unanalyzed. Coverage lists
exact analyzed indices. `full_task_supported` is false for current operations.
Linearization/controllability and equilibrium provide diagnostics, not sampled
constraint certificates. Actual model outputs and input semantics are rechecked
after construction. Nominal operating points retain a nominal horizon; saved
states retain their actual origin and remaining task time.
External applied forces, declared omitted physics and unknown required physics
prevent applicability before numerical model construction. Nonconvex/contact
requirements retain their original payload with `kind=unsupported`; unknown
signals or mismatched units/frames/phases are not silently replaced. Intervals
are expressible but have no constraint solver in this interface yet.

- `feasible_witness`: existing bounded_endpoint independent finite/bounds/output
  checks passed; only the reported local affine endpoint problem is covered.
- `model_infeasibility_certificate`: the existing separating-direction lower
  bound has a positive margin including its numerical allowance, within that
  exact model and input box. Solver failure alone is never a certificate.
- `diagnostic`: computed Gramian authority or available static construction.
- `inconclusive`: failed, unavailable, or insufficiently verified computation.
- `not_applicable`: no compatible operation/model scope; reasons are explicit.

Claims retain model/protocol hashes, assumptions, operating point, horizon,
physical inputs, coverage, computation/verification status and a JSON Pointer
into the same result's numerical evidence. No claim establishes backend task
acceptance, whole-window holding, global nonlinear behavior or hardware results.
`reach-local-v1`, `task-local-v2` and historical AnalysisResult payloads remain
valid. Old receipts are reused unchanged. New failed workers use scope frozen in
their request; attempts and elapsed costs retain existing accounting semantics,
including admitted requests found not applicable. Recovery never relaunches work.

## Verification and M2 extension point

Run `python -m unittest discover -s tests/research -p test_task_analysis_contract.py -v`
and the directly affected `test_mainline.py`. Create the untracked `runs/`
directory first when running the older regression module in a fresh worktree.
Tests cover frozen translation, moving references, invalid grids/signals,
unsupported physics, real kernel witnesses/certificates on labeled fixtures,
one light GVS initial linearization, acceptance, old contracts and Store recovery.
No provider request, full NMPC rollout or RL training is involved.
Verified on 2026-10-15 using the existing `.mainline5-env`: M1 11/11 passed;
mainline 12/12 passed; `git diff --check` passed. The first mainline attempt
failed during fixture setup because `runs/` was absent; creating it resolved this.
M2 can reuse normalized references, physical bounds, exact grids, provenance and
claim semantics, adding explicit multi-sample coverage and a verified solver.
It must retain independent task acceptance and introduce its own versioned scope.
