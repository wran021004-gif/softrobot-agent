# S5.6 and S5-T2 research delivery

Source start: `963b86c242ba4226c716fedd53c6b26ffe627deb`, verified local and
remote on `feat/sorosim-matlab-nmpc`. Target worktree was clean. Upstream
SoRoSim is `24d573a3e864ffda87c42ee462a6ed620133cc7b` and remains untouched.

The authorized sequence is P1 numerical refinement, P2 fixed-design control
optimization, P3 independent physics, P4 separate direct/residual PPO, and P5
KKT/structural sensitivity. Each owns a new frozen Store grant. Historical
studies, failures and budgets remain sealed. No provider requests are authorized.

| Stage | Prospective ceiling | Evidence destination |
|---|---|---|
| P1 | 16/32, conditional 64: three integrations | `evidence/sorosim_s56/refinement/` |
| P2 | Three NLP attempts, three independent high-resolution checks | `evidence/sorosim_s56/codesign/` |
| P3 | Two complete physics evaluations, three local probes | `evidence/sorosim_s56/physics/` |
| P4 | Four stages, 262144 actions, four independent evaluations | `evidence/sorosim_s56/rl/` |
| P5 | Two base NLPs, two conditional perturbation NLPs | `evidence/sorosim_s5t2/` |

The frozen task/compiler/evaluator, physical model, 35 held physical commands,
36 original task samples, force bounds and acceptance thresholds remain the
authority. Integration substeps do not add physical control decisions.

## P1: completed numerical refinement

Execution source: `36d35a35`. MATLAB R2024a / Optimization Toolbox 24.1 and
the pinned source/MEX identities are preserved in the immutable Store export.
Initial preparation without MATLAB's existing Engine PYTHONPATH failed before
any scientific reservation; the installed Engine build path resolved it. MATLAB
and SSH require execution outside the Windows filesystem sandbox. Remote read
then verified the exact authorized starting SHA.

| Internal steps per held command | Complete roots | Terminal error (m) | Holding position (m) | Holding speed (m/s) | Worker time (s) |
|---|---:|---:|---:|---:|---:|
| 16 | 560 | .010718 | .024705 | .791913 | 111.466 |
| 32 | 1120 | .011242 | .025697 | .827020 | 140.116 |
| 64, conditional | 2240 | .011510 | .026199 | .844771 | 235.409 |

All three integrations complete the same 35 commands and 36 output samples;
all fail the unchanged sampled mathematical task. The maximum full implicit
residual is below 3.30e-12. Maximum absolute represented state rises from 631.0
to 634.4; rates are represented curvature rates, not Cartesian speed. Position
and full velocity-vector differences at every original sample and the five
specified time windows are in [the P1 summary](../../evidence/sorosim_s56/refinement/summary.json).
Three integrations used 486.991 worker seconds, zero physical steps, PPO
actions or provider calls. Eight focused refinement/equivalence checks passed.

The decreasing differences support numerical refinement of this fixed sequence,
but do not establish a rigorous continuous-time bound. The 16-to-32 velocity gap
exceeded .020 m/s and prospectively triggered the one authorized 64-step check.
Further refinement is stopped at this ceiling. Use 32 steps as an exploratory
independent validation grid with its measured 32/64 uncertainty; use four steps
only as a cost-controlled intermediate optimization transcription. A task pass
on that intermediate grid alone cannot establish higher-fidelity feasibility.

The successive maximum position differences are 2.136, 1.101 and .559 mm;
velocity-vector differences are .070636, .036349 and .018424 m/s, each largest
at the critical .30 s braking sample for velocity. Both decrease pointwise at
every original sample (1e-10 comparison allowance). The final observed velocity
gap is still 92% of the task speed tolerance. Small root residuals and consistent
roughly first-order refinement support discretization sensitivity rather than a
failed root solve; nonunique roots and continuous-time error remain unbounded.

## P2: one actual control solve and independent validation

Execution source: `08b823d2`. The new `saved_candidate_controls` initialization
checks candidate/model/task/order/input/initial-state identities, imports only
35 physical commands and regenerates all 141 state nodes through the existing
implicit root preparation. The stricter saved-full-trajectory path remains.
Legal constant/ramp starts remain supported without a feasible historical task.
The check-only request uses the same mechanics reservation/receipt lifecycle
and charges a mathematical evaluation, never a full NLP attempt.

The measured four-step problem has 3,526 variables, 3,384 equalities, 72,264
nonzero dynamics Jacobian entries and 12 distinct task inequalities. All 13
original predicates remain in reports. Dense SQP Hessian storage alone is about
99.5 MB; actual observed MATLAB process memory reached about 4.8 GB, including
runtime and solver workspaces. A full callback took 2.836 s. Objective and
constraint directional relative errors were 8.30e-7 and 9.07e-11; rematerialized
initial dynamics violation was 1.00e-12.

One genuine feasibility-first SQP solve (`maximum_original_violation`, rho>=0)
used a 60-iteration ceiling and returned flag 1 after 21 iterations / 43 function
evaluations in 135.672 solver seconds. Raw scaled primal violation was 5.50e-13.
Its exact strict predicate flag remains **false**: a holding speed exceeds .020
by approximately 4.36e-15 m/s after bounded export. This is a numerical boundary
point, not an exact original-task pass; no threshold was relaxed. Recovery and
the multiplier-bearing raw optimizer checkpoint are preserved separately.

| Independent 32-step replay | Old commands | New commands |
|---|---:|---:|
| Terminal error (m) | .011242 | .010069 |
| Maximum holding error (m) | .025697 | .015030 |
| Maximum holding speed (m/s) | .827020 | .202355 |

The new sequence is numerically complete and improves these measured metrics,
but fails original higher-fidelity task acceptance. One solve, one derivative
preflight and one independent replay consumed 395.260 recorded numerical seconds
including initialization. No physical launch occurred in P2. The remaining P2
ceiling is two NLPs and two validations; no additional attempt is represented as
performed. A separate `task_feasible_effort` objective is implemented with zero
slacks and explicit original task constraints; it is not substituted for the
feasibility value function or its sensitivity. The near-flat feasibility value
motivates testing this secondary objective in the separately budgeted P5 study.

Raw evidence and the original candidate-bound handoff are in
[the P2 summary](../../evidence/sorosim_s56/codesign/summary.json). An append-only
erratum and the canonical versioned control source are in
[the annotations](../../evidence/sorosim_s56/annotations/summary.json). The
original handoff label overstated verification and copied a coarse epigraph;
the canonical source separates complete integration from task acceptance and
removes those coarse optimization fields. Details appear below.

## P3: new physical control and a controlled NMPC intervention

Execution source `288a8d66`; source commands differ from the historical grid by
5.14351 N in full-sequence Euclidean norm. The existing scientific-equivalence
preflight admitted the changed complete grid before reservation. One new
open-loop evaluation completed all 35 commands, 700 original MuJoCo steps and
36 samples, with zero force-bound violation and valid original task evaluation.

| MuJoCo open loop | Historical S5-A | New P2 sequence |
|---|---:|---:|
| Terminal error (m) | .024960 | .016857 |
| Holding maximum error (m) | .024960 | .016857 |
| Holding maximum speed (m/s) | .895355 | .498798 |
| Original acceptance | Valid failure | Valid failure |

Thus mathematical improvement transferred partially to physical measurements,
but did not establish physical task success. The new independent 32-step model
predicts holding speed .202355 m/s versus measured .498798 m/s; complete aligned
position/velocity differences are retained with the physical result. Worker
execution cost was 1.294 s. No local physical probes were needed or launched.

The single changed NMPC factor is `holding_brake_lead_s: 0 -> .02`. The earlier
cost window addresses the observed sharp late brake; all other controller
weights, horizon, solver settings, physical parameters and task criteria remain
fixed. Its one-substep predictor remains explicitly numerically limited. The
archived/current prefix through .17 s has identical requested commands and
physical tip positions. The first command change occurs at .18 s, when the
changed cost window enters the horizon, and grows to .433 N in vector norm at
.19 s. This verifies a real controlled intervention rather than a new artifact
label for the old experiment.

| Complete offline feedback | Historical S5-B | Earlier braking |
|---|---:|---:|
| Terminal error (m) | .006099 | .006121 |
| Holding maximum error (m) | .006635 | .006927 |
| Holding maximum speed (m/s) | .042351 | .041814 |
| Unusable controller updates | 1 | 1 |
| Original acceptance | Valid failure | Valid failure |

Both position criteria pass; speed and the original zero-controller-error
criterion fail. Earlier braking alone yields little improvement and is not a
validated controller solution. All 35 measured/projected states, projection
residuals, requested/applied controls, recovery/fallback decisions, optimization
statuses and timings are preserved. Thirty-four accepted predictions align to
the next actual output; their maximum position and full velocity-vector errors
are .005947 m and .168852 m/s. Maximum reconstruction residual is 6.975 rad/m.
Nineteen SQP calls reach their iteration limit, fifteen converge, and the final
update fails during setup before any SQP call.

The final .34 s error is exactly `CONTROL_TIME_GRID_REQUIRED`: binary floating
arithmetic makes `(.35-.34)/.01` slightly less than one, so the old raw
`remaining>=1` check rejects a valid last interval. It is a separate interface
boundary defect, not evidence of task infeasibility or SQP stagnation. Its fix
and zero-dynamics boundary verification are recorded with the final repairs;
the two full physical results and their original failures remain immutable, and
no third full launch is admitted.

The stage uses two complete physical executions and zero local physical probes.
Actual stage numerical time is 1838.603 s; the feedback simulation worker uses
1835.390 s. Mean update computation is 52.154 s (range .024--69.236 s), with 35
deadline misses. The .01 s period is not a real-time achievement. Parallel PPO
and later mathematical diagnostics make these observed costs, not a timing
benchmark against the historical machine run.

The [matched-fidelity alignment audit](../../evidence/sorosim_s56/physics/alignment_audit.json)
compares both physical open loops with their own 32-step mathematical sequence.
Whole-trajectory maximum position/velocity-vector differences change from
.067150 m / 1.206194 m/s to .066005 m / 1.110139 m/s. Holding velocity mismatch
increases from .306384 to .330439 m/s. Thus better task metrics do not establish
global model calibration. Different state/input histories prevent unique causal
decomposition; the optimized sequence has no separate 64-step convergence check.

[P3 evidence](../../evidence/sorosim_s56/physics/summary.json) and the
[complete NMPC comparison](../../evidence/sorosim_s56/physics/nmpc_comparison.json)
retain the original evaluator and per-update evidence bindings.

## P4: actual direct and residual PPO studies

Implementation `5003578e` preserves cross-study parent/checkpoint references
outside the new-stage allocation table. Weights, Adam moments/steps, observation,
action and reference semantics remain identical for continuation. The direct
intervention uses the existing .2 N initial-mean option and a new seed-17 policy
lineage; variance, architecture, reward, timestep and evaluator remain fixed.
It is not a continuation of the old direct weights. Both modes remain callable.

The read-only audit reconstructs all 260 old direct failures with zero new
physics steps. Median maximum joint rate grows from 1.15 rad/s at interval start
to 2.09e10 rad/s immediately before the recorded engine warning. Adjacent-cell
rate differences also become extreme. Original stable episodes lack archived
joint states; the independent stable evaluation supplies only output/tension
phase comparisons. These observations establish recorded numerical blow-up,
not its unique cause. Three new complete episodes preserve joint integration
states at actions 18--22 (15 states) for a scoped observational comparison.

| Measured fact | New direct | Residual continuation |
|---|---:|---:|
| New training actions | 65,536 | 65,536 |
| Lifetime policy actions | 65,536 | 98,304 |
| Complete training episodes | 1,872 | 1,872 |
| Numerical-failure episodes / captured warnings | 0 / 0 | 0 / 0 |
| New complete PPO rollout optimizations | 256 | 256 |
| Terminal position error (m) | .133172 | .021602 |
| Holding maximum position error (m) | .135179 | .025761 |
| Holding maximum speed (m/s) | .052935 | .312143 |
| Independent original task | Complete failure | Complete failure |

Each independent evaluation contains 35 valid actions, 700 physics steps and
all 36 samples. Direct evaluation has 23 saturated channel samples out of 140
(zero clipping); residual has 15 clipped/saturated samples. Applied tension
ranges are [0,1.525] N and [0,8] N. Failure-only diagnostics cannot establish
whole-training clipping/saturation rates. No failure terminal surrogate enters
the physical evaluation trajectory. Residual continuation has an immutable proof
of preserved weights/Adam state, a fresh stage schedule and 384 lifetime PPO
rollout optimizations. Its original compatible, physically failing reference is
retained to isolate continuation; changing reference would change lineage.

Direct improves the previously measured position/speed but has a changed
initialization and training length. Residual improves position over its old
checkpoint while holding speed worsens (.292965 to .312143 m/s). These single
seed/fixed-initial-state observations establish neither formal route superiority
nor robustness, and do not establish that PPO is ineffective.

A Windows atomic state-file read briefly returned `PermissionError` while the
residual worker continued. Driver repair `8c6408d5` adds only three bounded
read retries. Reusing the same operation IDs recovered the completed 65,536-action
worker, performed its still-unrun independent evaluation, and sealed evidence;
no training grant was reset or repeated. The original monitoring exception is
retained in the delivery history. MATLAB static checking found no diagnostics
in `sr_optimality.m`; existing optimizer warnings concern shared loop variables,
growing small task arrays and an unused derivative-check temporary, with no
syntax errors.

[P4 evidence](../../evidence/sorosim_s56/rl/summary.json) preserves final policy
ZIPs, checkpoint metadata, evaluation CSVs and stable-state NPZs as immutable
Store blobs. The stage used 131,072 new actions, 2,621,440 training physics steps,
1,400 evaluation physics steps, two training stages and two independent episodes.
Actual active training time was 226.786 s; stage numerical time including
evaluation/postprocessing was 234.552 s, plus 2.761 s for the separately recorded
pre-training read-only audit. Two stages, two evaluation episodes and 131,072
actions remain unused under the original ceiling; they are not new authorization.

The [binding/reward audit](../../evidence/sorosim_s56/rl/binding_and_reward_audit.json)
confirms byte-identical compiled physical XML, task, action and observation
definitions for each old/new route; residual reference metadata is identical.
Mean logged training rewards improve from -14015 to -4973 (direct) and -2819 to
-2140 (residual). Decomposing the already saved independent trajectories gives
position/holding-speed/smoothness reward totals of -4451.527/-37.357/-0.000014
and -1384.531/-541.792/-0.001744; their sums match the original recorded episode
rewards within 7e-13. This is saved-sample arithmetic, not another evaluation.
Latest residual approximate KL .252 and PPO likelihood-ratio clip fraction .641
suggest testing a smaller continuation learning rate or declared KL limit before
simply increasing training. PPO likelihood clipping and physical tension
clipping are different metrics; neither establishes convergence or superiority.

## P5: actual KKT diagnostics, secondary solve and structural sensitivity

The two preserved multiplier-bearing SQP points are evaluated at their exact
raw normalized vectors, before projection/recovery. After removing the fixed
auxiliary variable, the equality matrices have 864 rows / 1005 columns, numerical
rank 864 at relative cutoff 1e-9 and row-scaled condition estimates 506.0. Active
constraint matrices also have full measured row rank at activity thresholds
1e-5, 1e-7 and 1e-9 (scaled conditions about 674--2096). These are finite-tolerance
gradient-rank observations at approximately feasible points, not rigorous LICQ
proofs at an exact optimum. Fixed lower/upper bound pairs do not identify unique
individual multipliers; only their difference is meaningful.

Raw stationarity maxima .008296 and .011707 remain in internal state variables,
while control components are only 2.39e-5 / 1.58e-5. Unrestricted least-squares
multiplier refits still have nonzero residuals and sometimes negative active
inequality weights. This neither proves multiplier nonexistence nor supplies
valid KKT multipliers. Removing a duplicate or declaring rank failure cannot
explain the complete obstruction. Primal and stationarity gates fail; MFCQ,
constant-rank qualifications and second-order sufficiency remain unestablished.

One new full four-step `task_feasible_effort` solve starts from P2's rematerialized
controls. Its distinct objective is mean((U/limits)^2) + .1*mean(diff(U/limits)^2)
over 35 commands and 34 differences, subject to all original task constraints,
complete dynamics and unchanged physical bounds. It reaches its 60-iteration
ceiling, 592 function evaluations, in 1957.010 solver seconds. The raw point has
scaled violation .000454 and reported first-order optimality .345331, so its
multipliers do not describe a validated local optimum.

Root recovery selects a different trajectory: objective .317735 initially to
.266580, scaled violation 8.38e-13 and all original sampled four-step predicates
satisfied. A separate Engine/model replay verifies this selected trajectory.
This is a useful feasible secondary-control result for the declared discrete
model, not optimizer convergence, high-resolution feasibility, or a gradient.
Raw multipliers remain explicitly separate from the recovered trajectory.

The attempted large sparse-QR diagnostic exposes a JSON boundary error: MATLAB
cannot encode its sparse diagonal vector. That failed attempt remains charged
and archived. A bounded read-only serialization recovery is delivered separately;
no full NLP is repeated. The large problem uses sparse QR estimates rather than
silently claiming an SVD spectrum or certified LICQ.

With no regular local optimum branch, zero design-perturbation NLPs are admitted.
The useful lower-level calculation rebuilds Design B at proximal length
.195 +/- .00002 m with fixed [.2,.2,.2,.2] N. Its static implicit position
sensitivity is `[.746435, .178244, -.879912] m/m`; independently re-solved
perturbed equilibria agree to relative 1.90e-9. Both perturbed static residuals
are below 8e-17. This is a fixed-input local equilibrium sensitivity, not a
dynamic optimal-value, physical closed-loop or topology derivative.

The complete-Lagrangian implementation retains objective, initial-state,
every dynamics equality, task and physical-bound terms at fixed normalized
variables/multipliers while rebuilding perturbed models. Its numerical envelope
derivative is gated on a verified regular branch; no such derivative is reported.
For a differentiable local value branch, valid gradient-error bound delta_s and
regional gradient Lipschitz bound L along the proposed segment,
`W(d+Delta)-W(d) <= s_hat^T Delta + delta_s*||Delta|| + (L/2)*||Delta||^2`.
A strictly negative right side implies descent for that local mathematical
branch. Neither bound is established here; finite differences do not supply
rigorous regional bounds. Status remains `solver_unresolved` for the optimal
value and `locally_checked_not_certified` for the verified static sensitivity.

[Original P5 evidence](../../evidence/sorosim_s5t2/summary.json) uses one full base
NLP, one independent selected-trajectory replay and four diagnostic/analysis
evaluations (including the sparse serialization failure), 2171.210 recorded
numerical seconds, zero physical/PPO/provider work. The static operation includes
rebuilt base/minus/plus candidate models and independently solved equilibria;
these are not hidden full-horizon NLP attempts.

The [serialization recovery](../../evidence/sorosim_s5t2/diagnostic_recovery/summary.json)
uses repair `56483d6d`, converts only the sparse QR diagonal to a full JSON
vector, and re-evaluates the exact preserved raw point. It adds one diagnostic
and 42.390 numerical seconds, zero full NLPs or physical/PPO/provider work.
Combined original/recovery diagnostic-analysis use is five of the original
eight slots; the new session exposes only that one unused slot. The failed
attempt is retained, charged and linked. The recovered diagnostic still fails
primal, stationarity, complementarity and raw/selected replay correspondence
gates; activity-dependent QR rank estimates do not certify LICQ. No multiplier
or optimal-value sensitivity claim is upgraded by this engineering repair.

## P6: source semantics, feedback, accounting and delivery checks

The append-only [annotation export](../../evidence/sorosim_s56/annotations/summary.json)
preserves historical control-source artifact `c5abd818...` unchanged and supplies
canonical `e9e7aff8...` with `source_kind=independently_integrated_control_v1`.
Its 35 commands, initial state, 36 independently integrated samples and model
identities are identical to the actual P2 outputs. It carries complete-root
verification and separate **false** original-task acceptance. Coarse NLP
slacks/objective fields are absent. The original exported source used
`verified_mathematical_trajectory` and copied coarse epigraph fields into a
high-resolution sampled source; that label/field error is explicitly corrected,
not silently rewritten. P3 and P5 imported only commands/initial state and
regenerated their own nodes, so neither computation depended on the copied
epigraph. No experiment was repeated for the metadata correction.

The common source-admission predicate retains legacy semantics, refuses a
legacy source with explicit failed posthoc task verification, and accepts the
new completeness-only schema under its explicit meaning. Both physical and
residual-reference imports use that same predicate. Scientific identity checks
treat canonical/legacy equal commands as equivalent rather than new science.
Runtime/profile-only edits with identical task, robot, controls and controller
remain unresolved/withheld; changing runtime metadata cannot bypass novelty.
Both direct and residual PPO remain supported, and reference compatibility
requires exact task/candidate/observation/action bindings. A reference that
fails the task may guide residual learning; its failure remains visible.

The saved MATLAB interface fixture tests all 35 valid clock positions, the
four-step final interval and full horizon, and invalid fractional/exhausted
intervals. The corrected integer-grid check passes before any dynamics root,
SQP or physical step. The original final NMPC setup failure stays in P3;
this interface test does not establish the outcome of a repaired full rollout.

The [versioned Agent packet](../../evidence/sorosim_s56/agent_feedback_packet.json)
is readable through the existing scoped-feedback mechanism alongside S5.5.
It binds experiment novelty, raw outcomes, task acceptance, numerical-model
limits, KKT/static sensitivity, direct/residual outcomes and remaining ceilings.
The append-only scoped-context artifact is `97a71f72...`; existing
`python -m tools.research status --run-id sorosim-s56-codesign-20261017` returns
the new feedback without launching an Agent/provider request. The final
postprocessor's exact file hashes and source are preserved in the annotation
folder: feedback assembly was pending commit during metadata append, while
all numerical study launches used their separately clean committed sources.
Counters and closed-stage status were asserted unchanged by postprocessing.
The original residual-reference NPZ is also preserved as a blob with its
frozen contract hash; continuation therefore remains auditable after delivery.

| Actual stage | Full NLP | Mathematical integrations/replays | Diagnostic/analysis calls | Recorded numerical worker seconds |
|---|---:|---:|---:|---:|
| P1 refinement | 0 | 3 | 0 | 487.289 |
| P2 control | 1 | 1 | 1 | 395.260 |
| P3 independent physics/NMPC | 0 | 0 | 0 | 1838.603 |
| P4 direct/residual PPO | 0 | 0 | 0 | 234.552 |
| P5 base/sensitivity | 1 | 1 | 4, including failed serialization | 2171.210 |
| P5 read-only recovery | 0 | 0 | 1 | 42.390 |
| Total | 2 | 5 | 6 | 5169.303 |

These are sums of measured worker durations across partially concurrent stages,
**not** elapsed session wall time. P1's Store `numerical_s` includes overhead;
its three integration workers alone total 486.991 s. The separately recorded
old-RL read-only audit is 2.761 s and metadata append .521 s, outside that
5169.303 s sum. Full-NLP solver time is 135.672 + 1957.010 s, a subset of the
stage totals. Physical work is two P3 episodes / 1400 steps, plus two independent
RL evaluations / 1400 steps and 2,621,440 training steps. New PPO actions total
131,072. Live provider requests and hardware executions are zero.

Unused ceilings remain two P2 NLPs/two high-resolution checks, three P3 local
probes, two RL stages/131,072 actions/two evaluations, one P5 base NLP and two
conditional perturbation NLPs. P3's complete-episode ceiling is exhausted.
No regular base branch exists to admit perturbation NLPs. Completed sessions
are stopped/sealed; these unused ceilings do not reset grants or imply another
experiment has run. Fixed-input lower-level sensitivity is not charged as a
hidden design-perturbation full-horizon optimization.

| Numerical study | Exact frozen implementation |
|---|---|
| P1 | `36d35a359fd655f15ec1e99373d61192f1d0aa8f` |
| P2 | `08b823d2ad720e7d84ec3796f45058077562c6a3` |
| P3 | `288a8d66a5b6b64c94afb7dd990a9fae310a02ac` |
| P4 and original P5 | `ab03e8a3f57fd4c4f70731cceb421d6f8aa27692` |
| Read-only recovery/interface repairs | `56483d6dddef355d9b8adf323eb6d1e44d548a38` |
| Final versioned feedback/append-only annotations | `7b2d55eb6c5658d72d8d88bf33e9511c75508b5c` |

P4 monitor repair `8c6408d5` changes only bounded state-file read retries;
its reused operation IDs do not restart training. Final feedback/report commits
follow the numerical freezes and do not relabel earlier source identities.

The [delivery audit](../../evidence/sorosim_s56/delivery_audit.json) verifies all
seven archive hashes and all 315 member hashes, stopped sessions with no pending
or unsealed calls, zero provider calls, policy ZIP and reference-blob hashes,
the unchanged historical evidence tree and clean pinned upstream checkout.
Its source is retained beside the JSON. Twenty focused Python checks passed,
covering source admission, identity/novelty, sealed continuation accounting,
raw-versus-recovered KKT qualification and both feedback schemas. A separately
gated actual MATLAB time-grid interface test passed. Changed Python files
compile, MATLAB static checks report no syntax errors, and `git diff --check`
passes. Ordinary discovery does not launch expensive experiments. Archive JSON
secret scanning found no key patterns; staged source/config/documentation is
checked separately before commit.

The [production source change inventory](../../evidence/sorosim_s56/source_changes.json)
has 15 Python/MATLAB files, 471 added / 35 removed lines, net 436. Tests, explicit
experiment drivers, configurations, docs and evidence are separate. Existing
Host/Store/CLI, optimizer callbacks, implicit dynamics, physical backend, task
evaluator, PPO algorithm and ledger retain their responsibilities. The only new
focused production module is `sr_optimality.m`; there is no second candidate
generator, integration framework, SQP/PPO algorithm, evaluator or Agent system.
Shared source admission removes duplicated interpretation rather than adding
an alternate path. A constant/ramp legal initialization still does not require
a previously successful trajectory.

## Scientific boundary and next research decision

The implementation supports this tendon family and frozen norm-bound terminal/
holding task with original sampled acceptance. It returns explicit unsupported
results outside the implemented mathematical task family; it supplies no broad
STL/contact/collision proof, hardware claim or topology gradient. No physical
route passes the task. No continuous-time error bound, verified regular optimum,
regional sensitivity bound, numerical descent certificate, global optimality,
real-time achievement, RL convergence/generalization or unique model-mismatch
decomposition is established. The conditional local-branch descent statement
above remains a theorem with unverified numerical prerequisites here.

The most useful next experiment is a bounded **one-interval mathematical**
comparison: reintegrate the archived initial NMPC projected state and exact
first applied tension at declared finer grids, then compare full tip vectors
with the already archived .01 s physical output. It needs zero new physics and
no full NLP. Decreasing vector prediction error with refinement supports a
discretization contribution; agreement between consecutive fine grids with a
remaining physical discrepancy points toward projection/model identification.
Qualify this prediction before another expensive full feedback rollout or
morphology change. Separate later PPO work may test a smaller continuation
learning rate/KL limit with unchanged reference and independent evaluation;
current single-seed results cannot choose a generally superior controller.
