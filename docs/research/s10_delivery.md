# S10 delivery — real feedback decisions, no accepted mirror solution

**The real DeepSeek/Strands S10 Study completed and natively stopped without a
complete original-task pass.** It executed 20 fresh independent MuJoCo evaluations
and one SoRoSim target-equilibrium analysis. Best valid normalized task gap improved
from the historical 3.6020739579 to 2.4190924923. Position and holding speed still
violate the frozen task. No accepted label or SELECT is claimed.

Real failure-driven revisions occurred: a fresh failed replay led to a different
control-search experiment; that failed search led to a new mathematical calculation.
A subsequently revised larger-radius search was proposed but **never executed**.
Provider capacity entered protected closeout with 44 physical slots still unused.
This is incomplete bounded research, not evidence of structural/global infeasibility.

## Research starting point and frozen protocol

Only `feat/sorosim-matlab-nmpc` in
`D:/softrobot-agent/.worktrees/sorosim-matlab-nmpc` was modified. Initial worktree
was clean; local and fetched origin HEAD matched S9 baseline
`e7750c956e2ec8be9afd28e6d32c81d63a0b2a55`. The independent RL worktree, original
task/evaluator and sealed S7/S8/S9 evidence remain unchanged.

Authoritative task: `tasks/reach_hold_mirror_v1.json`, target `[0.29,-0.035,0.19]` m,
canonical identity `d24aeac7041052ce1d2ae60e825a802e7367107784f6fec192b0a65c4a5e76e7`.
Original duration 0.35 s, control interval 0.01 s, physics step 0.0005 s, hold
0.30–0.35 s, position 0.01 m and speed 0.02 m/s remain unchanged, as do initializer,
backend, evaluator and actuator limits. Effective task identity, including actual
joint names, is `bd9df2d930423f2b2a12152f076e2ae88b4d1a0af84d6126aa13b0b1fac9ec77`.

New formal Study `s10-mirror-live-20261020` owns an independent Store at
`runs/research/s10-mirror-live-20261020`. Its
[configuration](../../configs/research/study_s10_mirror.json) has resolved identity
`2dc839eccd78bc434a3088d7bc46c4809fca2ecd10ef49223a9971168d8929f4`.

| Resource | Frozen ceiling | Actual |
|---|---:|---:|
| Provider requests | 32, including 4 protected | 29 |
| Public operations | 160, including 12 protected | 73 |
| Shared backend starts | 64 | 20 |
| Registered mathematical analyses | 4 | 1 |
| Offline NLP / BDF reintegrations | 1 / 2 | 0 / 0 |
| NMPC executions | 2 | 0 |
| PPO stages / aggregate actions | 1 / 65,536 | 0 / 0 |
| Independent RL evaluations | 1 | 0 |

PPO rollout is 256; the action ceiling permits 256 complete updates. Smaller legal
allocations remain the Agent's choice. Scientific timers stay null; finite solver
counts and original timing remain enforced. No allowance increased, reset or
transferred after results. Original confirmation repetitions remain zero; a first
fresh complete pass would block exploration and require public reading/exact SELECT.

S7 mirror best failure `7f10b14a…` is imported through existing hash and task/physical
identity checks. S8 produced two static equilibria and zero fresh physics; these
retain original candidate/model/workpoint scope and are not current verified input
sensitivity. S6 supplies an optional adapted unmeasured control. S9's accepted
second-target result is not mirror acceptance. See
[historical inventory](../../evidence/s10_mirror/historical_inventory.json).

## Actual engineering capability and Agent use

Separate readiness/admission ledgers used zero Provider and scientific starts.
Pinned SoRoSim `24d573a3e864ffda87c42ee462a6ed620133cc7b` passed dependencies,
MATLAB startup, gateway, sqrt(4) and shutdown. No new runtime/encoding workaround.
[Readiness](../../evidence/s10_readiness/verified/report.json) and
[admission/domain checks](../../evidence/s10_mirror/preflight.json) distinguish
registration, actual readiness, candidate prerequisites and executed science.

- Mathematics: engine/gateway ready; one current-candidate target equilibrium
  actually computed. Other registered analysis/trajectory methods retain original
  model, operating-point, paired-candidate and numerical-verification conditions;
  they were not executed in S10.
- Physical control: original exact binding, initialization, independent replay,
  response/pattern methods, active coefficients and multistart remain available.
  S10 used one replay and one single-start response batch. Every actual applied
  sequence was reconstructed without rerunning physics.
- NMPC: dependency/gateway ready; full candidate-specific admission and real
  numerical execution still required. The Agent did not execute NMPC.
- Direct PPO: actual environment construction passed in the configured
  `.rl-pilot-env`: four ideal-tension channels, 48 DOFs, 107 observation components,
  35 intervals and original 0–8 N limits. Initial preflight used the research
  interpreter lacking gymnasium; it was corrected to the existing RL interpreter,
  without installation. No training or policy evaluation was performed.
- Residual PPO: no published complete compatible reference at preparation. Exact
  mathematical/NMPC trajectory, candidate/task/order/grid and checkpoint-lineage
  conditions remain required. Missing prerequisites do not disable Direct PPO or
  justify changing actuator semantics.
- Structure: complete `family_space_s7` domains remain available, including legal
  segment/tendon counts, geometry, material, routing, density/viscosity and other
  declared variables subject to construction. No manually reduced space or fixed
  method order. The Agent generated no new structural design in formal S10.

## Original autonomous decisions and feedback

The [decision chain](../../evidence/s10_mirror/feedback_decision_chain.json) links
each action to its preceding actual research packet, original request, feedback
and evidence reads. [Raw decisions](../../evidence/s10_mirror/decisions.json) and
the archive preserve originals. Missing hypothesis/budget fields on the existing
`research_analysis` contract remain null; they are not invented retrospectively.

| Decision | Actual evidence and Agent choice | Actual result |
|---|---|---|
| 1, `H_FRESH_BASELINE_9CA1` | Test whether transferred unmeasured source `9ca1…` passes; request one full replay | Fresh valid failure `6c00a527…`: error 0.0725687332 m, holding speed 0.0199778632 m/s; gap 6.2568733172 |
| 2, `H_LOCAL_RESPONSE_897_8COEFF` | Cite fresh failure and better-position historical source `897b…`; change from validation to eight-coefficient local response optimization | 28 callbacks: 19 new physics, 9 cache reuses; best `49c76e42…`, gap 2.4190924923; no pass |
| 3, `research_analysis` | After failed-search/trace inspection, request current-candidate `equilibrium` at `target_equilibrium` | New result `3573c3b2…`: computed local static target equilibrium; dynamic holding unverified |
| 4, `H_LARGER_RADIUS_62DD` | Cite search boundary offsets and equilibrium tensions; propose radius 0.8 N, coefficient cap 2 N, another 28-callback search from best source `62dd…` | Rejected before science: unregistered wrapper/search references in supporting evidence |
| 5, same revised hypothesis | Correct citations and resubmit | Protected closeout rejects exploration; no new physics |
| 6, `H_NO_FRESH_PASS_PROTECTED_CLOSEOUT` | Cite all 20 fresh physics results plus analysis and explain no acceptance exists | Native model STOP seals Study; no substitute engineering STOP or SELECT |

Exact request references for decisions 1–3 begin `41f8d87a…`, `b4be8b94…`,
`7e586dbf…`; expanded-radius requests `88d3f106…`, `8520956f…`; native STOP
`c952776d…`. Full hashes and responses are in the decision-chain file.

Executed response settings: knots `[0.24,0.34]` s, correction window `[0.20,0.35]` s,
all eight knot-major coefficients across four tendons, coefficient cap 1 N,
difference step 0.02 N, initial radius 0.4 N, minimum radius 0.001 N, three
iterations, 28 callbacks, zero local safety-margin fraction. The existing SciPy
SLSQP epigraph step, trust-radius update, cache, ranking and evaluator are unchanged. Stopping
reason is `iteration_limit`. Sixteen unique fresh response probes were informative;
input-direction and observed-response ranks were eight, with resolved-subspace
condition about 11,132 then 10,819. Eight callbacks repeated applied sequences and
were cached; the remaining reuse is the historical baseline. Ineffective attempts
were zero. All trial inputs and unchanged window-exterior inputs are verified.

There are **three executed high-level scientific decisions**, and two executed
transitions after failure: replay→control search, then failed search→equilibrium.
Nineteen internal search evaluations are not nineteen Agent decisions. The later
radius revision is a real proposal with no executed result; its retry and STOP add
no new experiment. No controlled comparison establishes general policy reliability
or method superiority from this single Study.

The first replay weakens immediate-acceptance expectations. Response search
supports local improvement but fails complete-pass aspirations. Static equilibrium
supports only a scoped diagnostic. The trust-radius explanation remains untested
because its proposed discriminating experiment never ran.

## Mathematical value and limitations

SoRoSim equilibrium uses the same candidate, 12 generalized coordinates / 24 states,
`structural_linear` bending basis, frozen task and bounded tensions. Assumptions
include inextensibility, no shear/torsion and straight frictionless tendon spans.
MATLAB SQP used 17 iterations / 48 function evaluations. Position residual was
`1.2417996448e-8` m, static residual infinity norm `1.8604909280e-16`; tensions were
`[4.1301529785,1.8139051284,2.1014899944,3.2404328924]` N.

Tool status is `computed`, scoped conclusion `diagnostic`. Holding-speed coverage
is explicitly not applicable and original-task acceptance remains unmeasured. This
is not verified current input sensitivity, an independent dynamic replay or a
full-task witness. Raw numerical results, binding and verification status remain
in the original artifact.

The Agent explicitly cited these tensions in enlarged-radius proposals to justify
investigating larger tendon-0 input. Mathematics therefore informed a subsequent
research proposal. It generated no new mathematical control seed and improved no
subsequent physical result, because that experiment never executed. It identified
no proven dynamic failure cause. The earlier measured control improvement came
from MuJoCo finite differences and the existing constrained numerical optimizer.

## Best valid failure and original acceptance

[Complete design/control/task package](../../evidence/s10_mirror/study/design_package.json)
contains robot configuration, design parameters, exact 35×4 ZOH controls, task,
evaluator, original acceptance, raw reference and implementation. Its status is
`best_valid_candidate`, `accepted=false`.
[Best control/acceptance](../../evidence/s10_mirror/best_control.json) and the
summary/archive retain all 20 fresh results.

Unchanged structure: two flexible segments, lengths 0.195 / 0.11 m, moduli
10.45 / 5.40 MPa, angled elliptical first and rectangular second sections,
12 cells each, four consecutive-span tendons. Full section, routing,
density/viscosity, material and coordinate data are in the package. Candidate:
`8a2ee4f9c69ccf5e2ffa031fb4530a4706b8ed43a6e24cd3c7747bd17d716366`.
Best fresh evaluation:
`49c76e42767e0ab9870e7a18322bebc916215f721c955a7bbbba472ac72ab0ed`.
Control source:
`62ddc2387077c5b49440d16208cd83d07d9108187e3e94df00043e4bfdb9557d`.

| Original check | Best result | Frozen requirement | Outcome |
|---|---:|---:|---|
| Terminal position error | 0.034190924922823 m | ≤0.01 m | Fail |
| Holding maximum position error | 0.034190924922823 m | ≤0.01 m | Fail |
| Holding maximum speed | 0.068014941313063 m/s | ≤0.02 m/s | Fail |
| Maximum normalized task gap | 2.419092492282298 | 0 | Fail |
| Force-bound violation | 0 N | ≤1e-8 N | Pass |
| Solver errors | 0 | 0 | Pass |
| Execution / evaluation | Complete / valid | Complete / valid | Pass |
| Holding coverage | All 6 inclusive samples | 0.30–0.35 s | Pass |
| Independent task evaluator | false | true | Fail |

Inputs preserve original tendon order/grid and 0–8 N limits (actual extrema about
`1.10e-14` and `7.999999999999996` N). Independent recomputation confirms every
physical outcome and task gap. There is no pass, confirmation or SELECT to audit.
No experiment was appended after native STOP.

The Agent held structure fixed while testing controls/static reachability. It
provided no complete comparison of structural changes versus NMPC/RL, so neither
control-only optimality nor structural infeasibility follows.

## Costs, errors and stopping

Provider usage: **1,706,805 prompt + 47,544 completion = 1,754,349 tokens**.
Reasoning tokens 34,044 are included in completion; prompt cache hits 147,200.
Currency cost is unknown. All 29 requests have original response usage.
There were 54 native tool calls: 48 evidence reads and six research requests,
including rejected/corrected proposals and STOP. Six errors comprise four invalid
evidence-field/pointer reads, one unregistered supporting-evidence citation and one
protected-closeout rejection. Empty successful reads remain counted. The 73 public
operations include inner playback calls; they are not 73 outer research decisions
or duplicate physics billing.

First physics followed six Provider requests / 54.051624 s. Charged physical time
was 23.2683362 s; mathematics 11.5852062 s. Total numerical time 35.8066222 s also
includes preparation. Ledger wall time 309.4135424 s is cumulative charged elapsed
time, not CPU time or an enforced scientific deadline.

Invalid supporting citations consumed a remaining research request before the
corrected expanded-radius request met the four-request closeout reserve. At STOP,
3 Provider, 87 public-operation and 44 physical slots plus unused method allowances
remained, but exploration was no longer legal under that frozen reserve. This is
a sufficient operational stop, not scientific exhaustion of promising hypotheses.
Frequent reads and citation mistakes constrained efficiency; budgets were not
expanded to compensate.

All new physics/analysis retain S10 ownership. Native STOP cites all 21 fresh
results. Every receipt is settled, occupied resources empty, pending and unconsumed
response null. The Study is sealed. Artifacts permit reconstruction; further
science requires a separately authorized new Study, not reopening this ledger or
silently retrying the unexecuted hypothesis.

## Changes, validation and reproducibility

Production changes: **+0/-0 lines**. Requested production owners `agent`,
`research_context`, `core`, `analysis`, `physical_replay`, `local_control_search`,
`rl`, `feedback`, `budget`, `evidence_policy`, `contracts` and `__main__` were
reviewed/reused. No new Agent, optimizer, Store, evaluator, planning contract or
formal runner was introduced.

| New file | Purpose / function owner | Added/deleted lines |
|---|---|---:|
| `study_s10_mirror.json` | Formal identity, counts, full capabilities and neutral feedback instructions | +106/-0 configuration |
| `study_s10_readiness.json` | Independent zero-science startup ledger | +70/-0 configuration |
| `study_s10_admission.json` | Independent history/config/environment admission ledger | +105/-0 configuration |
| `test_s10_configuration.py` | Original task identity, finite methods/counts and historical scope | +38/-0 test |
| `s10_audit.py` | `decision_chain`, `verify`: original chronology and provenance beyond S9 accounting | +94/-0 read-only audit |
| S10 evidence and this report | Generated preparation, payload, real results/costs, recoverable package | Evidence/docs, not production |

S10 audit reuses S8 independent task/control/package verification and S9 accounting;
it adds no numerical evaluator, optimizer or budget logic. Ignored transient
helpers under `runs/` prepare/monitor/audit; they never select scientific actions
or replace the formal CLI.

Engineering regression: **75 tests, 74 pass / 1 opt-in real RL skip**; all three
S10 configuration tests pass. Logs are under `evidence/s10_mirror`. Post-study:

```powershell
python -m tests.research.s9_audit s10-mirror-live-20261020 evidence/s10_mirror --export
python -m tests.research.s10_audit
```

Offline regression commands (no Provider or scientific starts):

```powershell
python -m unittest tests.research.test_s9_evidence tests.research.test_s9_handoff tests.research.test_s9_probes tests.research.test_s8_agent_interface tests.research.test_s8_tool_readiness tests.research.test_evidence_policy tests.research.test_count_continuation tests.research.test_sorosim_contract tests.research.test_rl_integration
python -m unittest tests.research.test_s10_configuration
```

Runtime is existing `.mainline5-env`; `PYTHONPATH` includes repository,
`tests/research` and existing MATLAB Engine path; pinned `SOROSIM_ROOT` is retained,
OMP/OPENBLAS/MKL threads each one. Dependency versions are in preflight/readiness
and immutable configuration. Formal model is configured `deepseek-flash` through
Strands; original requests/responses and usage are archived.

[Independent audit](../../evidence/s10_mirror/independent_audit.json),
[input reconstruction](../../evidence/s10_mirror/search_reconstruction.json),
[accounting](../../evidence/s10_mirror/accounting.json) and
[artifact checks](../../evidence/s10_mirror/final_artifact_checks.json) verify
**607 archive members**, 29 request histories, all 54 native request/feedback
pairs, original response byte hashes, complete STOP citations, unchanged scientific
sources/task/history and zero configured-key matches.

Automatic review rejected the initial launch before execution over exact
payload/destination approval. The user then explicitly approved **“授权上述 S10
数据范围与地址，继续研究”**. Real research subsequently completed at
`https://api.deepseek.com/chat/completions`; that historical rejection is resolved.
[Authorization](../../evidence/s10_mirror/provider_authorization.json) and
[payload review](../../evidence/s10_mirror/provider_payload_review.json) retain
scope. Keys, authentication headers and unrelated worktrees are excluded.

| Stage | Commit | Ordinary push |
|---|---|---|
| Preparation | `8c2eb88ee5e076c873edc5fe9e4fb22966b93d64` | Remote SHA verified |
| Formal protocol/binding | `7bac54ad311fab798d806ccd29504740a5cf07c4` | Remote SHA verified before science |
| Pre-send archive | `927b1b04802cbc8b36972d6ebb96b683ddb49210` | Remote SHA verified |
| Explicit Provider authorization | `1d0eb679e24bd44eefaf650b17b54e31abeb050a` | Remote SHA verified |
| Actual S10 delivery | Final delivery commit | SHA in delivery message/local Git receipt |

The initial preparation binding was explicitly migrated to `7bac54ad…` before
Provider/science, preserving configuration and zero counters. Scientific
implementation stayed unchanged throughout the real run. No force push,
historical rewrite, foreign-worktree change or private environment file is included.

## Five requested conclusions

1. **Autonomous calculations:** one transferred-control replay, one eight-coefficient
   response batch (three iterations / 28 callbacks), one current-candidate target
   equilibrium. Expanded-radius 28-callback search was proposed but rejected.
2. **Failure-driven revision:** yes, replay failure→new control search, then search
   failure→new mathematics. Originals establish both transitions. Later radius
   revision was proposed only; STOP/internal probes are not additional revisions.
3. **Mathematical value:** MuJoCo response mathematics produced measured local
   improvement. Later SoRoSim mathematics informed a revised proposal, but generated
   no control seed or subsequent measured physical improvement and proved no
   dynamic failure cause or feasibility.
4. **Joint structure/control variation:** no new structure; Agent retained an
   existing design and investigated control/static reachability. No conclusion
   of structural infeasibility or control-only optimality follows.
5. **Feasible solution:** no. Original independent acceptance is false. Best valid
   failure, all new observations/violations, native STOP, unexecuted hypothesis,
   exact inputs and recoverable evidence are delivered.
