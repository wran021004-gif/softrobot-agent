# Stage I: unified mathematical diagnostics

Scope: unified result interfaces and partial mathematical facts only. Stop after
Stage I review. Candidate identity, Plan lifecycle, Store relations, STOP, SELECT,
budgets, physics, solver settings and original task acceptance are unchanged.

The supplied workspace was on `feat/gvs-dynamics` at `d629a80d`. The requested
baseline was absent locally but available from the existing origin. Development
uses a separate worktree and branch `codex/stage1-unified-math-diagnostics-20261106`
starting at `0528cda9a7fd7f44864d07a7f16f638f15517d65`; the original workspace was
not switched, reset or cleaned.

## Implementation

| File / functions | Change |
| --- | --- |
| `tools/research/analysis.py`: `diagnostic_layers`, `diagnostic_overview`, `scoped_result`, `recover`, `compact_result`, `decision_result` | One read-only four-layer projection over existing results, persisted on new mathematical results and shared by existing views. Recover published active checkpoints on failed workers. |
| `tools/research/evidence_views.py`: `quantitative_facts` | Reporter uses the same projection. |
| `tools/research/research_context.py`: `mathematical_decision_view` | Main receives independent layer statuses, principal obstruction, up to four recorded quantitative facts, and a detail query. |
| `tools/research/structure_research.py`: `initial_geometry` | Reuse position pipeline; retain contact world positions and geometric active/slack observations. No full forward retry. |
| `extensions/tendon_family/passive_equilibrium.py`: `StaticProblem.qualify`, `solve`, `qualification_diagnosis` | Expose separate checks using unchanged thresholds. Record actual start, initial forward, optimizer entry/return/status, and interrupted current trial, retaining earlier completed trials. |
| `extensions/tendon_family/math_analysis.py`, `sorosim_analysis.py`: `calculate_candidate_configuration` | Publish process milestones through the existing checkpoint callback. Active construction, derivatives, inputs and qualification remain owned by their existing kernels. |
| `tests/research/test_constrained_mechanics.py`: shared Worker fixture | Replace a hidden legacy tip-row question with registered output-row coverage and the identical explicit world X/Y projection. No production registry change. |

No new Worker, Agent, state machine, physics kernel, registry, hash identity or
scientific evidence type was introduced. Existing candidate references remain on
raw results and tool responses. Projection neither launches computation nor
changes resource accounting.

## Interface semantics

`diagnostic_layers` has `geometry`, `numerical_solve`, `static_qualification`, and
`dynamic_validation`. Each contains `status`, `facts`, `missing_checks`,
`failure_reasons`, and `scope`. States are `passed`, `unqualified`,
`not_evaluated`, and `not_applicable`.

These are independent information layers, never a sequential execution pipeline.
`passed` covers only the declared scope: successful position observations can
include contacts; this does not claim an admissible equilibrium. A short native
integration can be recorded while full task validation and Replay remain missing.
An independently recorded dynamic result is not suppressed by missing static
facts. Affine-model replay never becomes physical execution.

Raw arrays, per-start results, qualifications, counters, and original failures
remain available. Existing immutable evidence is projected without being rewritten.
Unrecorded worker progress stays unknown. Passive second-order positivity at an
unqualified point does not grant stability or a trusted mechanism gradient.
Active non-equilibrium linearizations retain their valid local scope, with static
minimum qualification marked not applicable. No passive KKT/payout fields are
added to active diagnostics.

## Real passive failure checks

Both samples use the original successor task scene, floor/contact rules,
`unloaded_static_solver`, and original two starts. They are bounded engineering
tests, not formal Studies or independent task evidence. Sample A uses the legal
family default; sample B sets all nine registered segment lengths to 0.04 m.
No frozen physical or numerical configuration was changed to assist convergence.

| Layer | A: initial full forward failure | B: forward completes, optimizer unqualified |
| --- | --- | --- |
| Geometry | `passed` for position facts: 228 contacts, four lengths/payouts/residuals and example contact positions | `passed`: zero initial contacts |
| Numerical solve | `unqualified`: first forward fails, optimizer not entered, second start skipped | `unqualified`: both starts returned; status 4 / 4 iterations and status 9 / 400 iterations |
| Static qualification | `not_evaluated`: no fabricated KKT, capacity or stability result | `unqualified`: length, stationarity, complementarity, capacity, KKT and second-order checks fail independently |
| Dynamic validation | `not_evaluated` | `not_evaluated` |

A retains one position call, one attempted full forward, zero completed forwards,
one attempted mathematical evaluation and zero integration steps. It never retries
the known failing full forward to collect geometry.

B retains 2,208 static forward calls and 404 optimizer iterations. Its selected
trial has primal violation `7.789113647377333e-05 m`, stationarity residual
`0.13590602708669494 Nm`, and complementarity `0.0030883164910895603 Nm`.
Nonnegative duals, LICQ and strict complementarity pass separately; capacity, KKT
and second-order eligibility fail. Tangent stiffness/compliance remain unavailable,
no structural direction is produced, and no loading integration is performed.
These local failures do not prove structural infeasibility.

Full engineering outputs are in local ignored
`runs/stage1_diagnostics/initial_forward_failure.json` and
`runs/stage1_diagnostics/unqualified_multistart.json`.

## Validation

Ten focused new tests cover real A/B failures, interrupted second-start
qualification, saved real active SoRoSim compatibility, partial active derivative
progress, native geometry rejection, independent dynamic-layer projection, and
identical Main/Reporter/tool facts without mutation. Synthetic process/dynamic
fixtures are explicitly labeled and are not scientific observations.

The original targeted active/passive suites are run after committing, because
their existing `core.bind` requires a clean committed implementation. Initial
module-wide unittest discovery also collected imported `ReportingTests`; seven
errors there come from its old `offline_host` Mock not supporting the existing
`artifact(..., paths=...)` API. Both incompatible lines exist at `0528cda9`. This
unrelated fixture is not repaired in Stage I; final runs name the intended test
classes explicitly.

The first committed run completed 39 intended tests in 72.645 s with one failure:
the shared passive SDK fixture requested `constraint_tip_row_residual`, already
hidden from Main at the supplied baseline. Its first request was rejected before
execution (`INVALID_SCIENTIFIC_V4_INPUT`), yielding six rather than seven charged
evaluations. The fixture now requests the existing registered
`constraint_output_row_residual` with explicit identical world X/Y rows; original
numerical checks and seven-evaluation assertion are retained.
Its old rejection assertion was also updated to accept the existing
`needs_choice` response for invalid advertised input, alongside `unsupported`.
Both are pre-execution rejection; the original unchanged-budget assertion remains.
The unified view reads both GVS per-derivative check flags and SoRoSim aggregate
flags, without changing either kernel's calculation or qualification.

An independent exact baseline comparison completed in 10.154 s: real GVS,
saved real SoRoSim initial and target-equilibrium results, and the real PHS
two-start failure all preserve every original result field after removing only
new diagnostic fields. The passive comparison includes original qualification
and numerical counters and compares serialized JSON consistently (tuples become
lists). Local comparison script and result:
`runs/stage1_diagnostics/compare_baseline.py` and `baseline_comparison.json`.

Final targeted counts, timings, exact baseline comparisons and publication
identity are appended after verification. No Provider, formal Study, full ten-case
physical experiment, or MATLAB session is launched.

## Remaining scientific questions

The tested PHS points remain unqualified. Geometry, unilateral branch changes,
and numerical search limitations remain competing explanations; contact counts
alone do not identify the factorization failure's cause. No new feasibility,
dynamic stability, task success, Replay, SELECT, or regional gradient certificate
is claimed. Candidate–Plan workflow repair belongs to Stage II and was not begun.
