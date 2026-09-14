# Framework construction at 1a0081b

Baseline: `feat/round9-matlab-dynamics-design-loop`, HEAD
`1a0081b6822ccf802cfd08ce8d1ecb9c5049a69b`; initial workspace clean.

Execution order (continue without stage approvals):

1. Regress incomplete feedback, contact-only queries, declared duration.
2. Bind service declarations to implementations; reusable execution requirements,
   reservation, source identity, cache, sealing and recovery.
3. Model quantity and saved signal adapters; independent versioned diagnostic rules.
4. Explicit task execution context, controller lifecycle and evaluator/search adapters.
5. Local extension acceptance, small real MuJoCo runs, migration and catalog export.

Constraints: historical artifacts and frozen task/physics/score/grants stay intact.
New source identity means a new validation run, not relaxed continuation checks.
No model API call, full campaign replay, large search, or multi-agent orchestration.
Offline native function responses are transport fixtures, not live model decisions.

## Stage 1

Feedback now gates task/model conclusions on solver completeness. A partial
MuJoCo rollout emits null task success. Contact events do not need tendon/joint
summaries. Diagnostic time windows use saved samples; remaining duration uses
declared shared input duration, or null when historical duration is absent.
Direct regression coverage is in `tests/test_framework.py`.

## Stages 2–3

Service definitions now own binding, schema, execution needs, source dependencies,
cache and feedback scope. Default extensions use a killable process; existing
inline adapters explicitly retain their own bounds. Dynamic dispatch uses named
bindings with a declaration/binding consistency check. PCC/compiled parameter
providers and saved signal queries separate model authority from rule judgments.
The independent contact rule requires only a saved contact-count signal.

## Stage 4

TaskContext carries the task, environment, duration, initializer and evaluator.
Independent development configurations preserve physics and tolerance. C1/C2
generators and lifecycle contracts are registered; actual execution saves reset,
observations, period and updates. Existing optimization delegates parameter-space,
proposal and evaluator functions. The independent evaluator owns its frozen
configuration, per-call/per-solve ledger, source identity and sealed recovery.
Search checkpoints bind both proposal source and evaluator identity.

## Stage 5 — complete

Final native math, saved MATLAB signal reuse and three short real MuJoCo
evaluations are sealed at
`runs/framework_acceptance/8f8d2b7043dc4b569618ba24db8cbe2c`.
36 distinct targeted cases passed across the recorded groups. Three legacy
controller tests first hit Windows temporary-directory permissions; replacing
only their directory fixture allowed unchanged assertions/backend to pass.
No historical source compatibility allowlist or frozen scientific definition
was relaxed. Source hashes matched the final workspace at evidence packaging.

Review starts at `docs/framework_extensions.md` and `docs/framework_validation.md`.
Remaining limitations: PCC/public saved parameters only (no general dynamics
quantity service), uncalibrated model assumptions, length actuation, original
MATLAB task restrictions, and no live model API/multi-agent/hardware validation.
Next work can add local math/rule/search/controller implementations and contracts;
new physical channels or task semantics require an explicit backend/task adapter.
