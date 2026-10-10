# CasADi joint length and trajectory pilot, 2026-10-10

The current-model CasADi path now constructs and actually executes fixed-design
and joint-design trajectory NLPs. Four actual bounded IPOPT solves returned
finite iterates without finding mathematical feasibility within their deadlines.
Independent replay tested both primary and corrected returned schedules.
These outcomes do not establish that joint optimization is ineffective.
SoRoMoX adoption remains deferred and both historical activities stay STOP.

Branch: `feat/casadi-codesign-pilot`, based on
`34307384307158dba899ad2499a8b3e582f8356e`. One successful fetch found no
intervening changes to the three supplied branch tips. The work is isolated
under `.worktrees/casadi-codesign-pilot`; unrelated local environments and
the original working branch are preserved.

The accepted Python 3.11.16 interpreter, CasADi 3.7.2, SciPy 1.17.1, MuJoCo
3.13.0, Strands Agents 1.59.0 and Harness 0.2.0 are recorded in
[environment evidence](../evidence/casadi_codesign_pilot_20261010/environment.json).
No dependency was installed or upgraded. Commands and reconstruction details
are in the [runbook](casadi_codesign_runbook.md).

The optional length map propagates through normalized segment integration,
poses, tip/tendon geometry, distributed mass and complete rotated inertia
tensors, gravity, velocity bias, elastic/viscous forces, tendon Jacobians and
virtual-work forces, nested inertial-wrench functions, and implicit constraints.
Rigid masses/inertias remain fixed while their poses and moment arms change.
Numeric serializable configurations and the structural-linear strain field
remain intact. Every dependent nested function explicitly takes design input.
The original fixed-design API and analysis tuple are preserved.

The current interfaces resolve 12 curvature coordinates, 24 reduced states,
48 physical positions and velocities, and six one-to-one tension channels.
The primary NLP has 1075 decisions and 853 constraints: one shared `d`, 36
state nodes, 35 control intervals, initial state fixed zero, tension/design
bounds, force balance, and smooth squared-norm position/speed inequalities
at every holding node from 0.30 through 0.35 s. Geometry is fixed in time.
The common objective is mean squared normalized effort plus 0.1 times mean
squared normalized successive tension changes; task limits are hard constraints.

Implementation and specifications were committed at `056a5cf8` before dispatch.
The focused check passed all 92 comparisons at zero and nonzero states, using
three numeric reference graphs reused at baseline and a central length pair.
Baseline output agreement was exact. Maximum length-partial errors per
normalized design unit were 1.64e-12 for tip geometry, 1.49e-13 for tendon
lengths, 2.40e-16 for mass, 9.44e-14 for gravity, 9.10e-14 for force residual,
and 8.33e-4 for acceleration against a derivative scale of 8.71e4. Tolerances
were fixed by quantity before evaluation. The full constraint directional
check passed with maximum absolute discrepancy 7.54e-7; coherent guess defects
were at most 5.05e-11 normalized. Full tolerances, states and checks are in
[focused numerical evidence](../evidence/casadi_codesign_pilot_20261010/00_check_check.json).

Both primary initializations used constant 0.2 N guesses and Newton implicit
rollouts from prescribed zero state. These are numerical guesses, not physical
initial pretension. Both used exact first derivatives, sparse reverse-mode
constraint Jacobians, limited-memory Hessians, and 1000 iteration ceilings.
Neither used the controller's feasible-return policy.

| Primary case | Lengths, m | Iterations | Objective | Largest normalized violation | Solve seconds |
|---|---|---:|---:|---:|---:|
| A | 0.160000 / 0.110000 | 33 | 0.0264920 | 11.0488, speed at 0.35 s | 608.711 |
| B | 0.157499 / 0.112501 | 28 | 0.0351257 | 18.3746, speed at 0.34 s | 580.952 |

Both terminated `Maximum_CpuTime_Exceeded`, with no retained feasible iterate.
A's effort/weighted variation were 0.026443994/0.0000480111; B's were
0.035083879/0.0000418418. Raw terminal errors were 7.949/6.242 mm, but maximum
holding speeds were 0.06942/0.08803 m/s against 0.02 m/s. Dynamics violations
also remained. Position tolerance alone does not establish task feasibility.
The actual design change in B establishes that length entered the optimized
decision vector; these infeasible outcomes do not establish a design advantage.

The original A used 600 s CPU/wall settings and overshot the declared ceiling
by 8.711 s because IPOPT checks time between iterations. This is a retained
budget violation, not hidden construction time. Repair `e3ffcf82` introduced
570 s settings to reserve a stopping margin, restored the shared analysis tuple,
and corrected sampled replay speeds to the existing instantaneous Jacobian
definition. B stayed under the ceiling. Its differing effective stopping limit
is explicit; no strict equal-work primary A/B comparison is claimed. The same
grant, counters, original A outcome and correctness evidence were retained.
The [migration record](../evidence/casadi_codesign_pilot_20261010/repair_migration.json)
identifies exact dependency changes without repeating the mechanics checks.

Replay selects the least-violating independently checked retained noninitial
iterate for each case: A iteration 32 (violation 6.09272, objective 0.0336946),
and B iteration 12 (violation 16.4501, objective 0.0886202, lengths
0.158106/0.111894 m). Original raw and selected variables, objective components,
residual names/times, options, traces and solver logs remain immutable.
These schedules receive diagnostic replay because mathematical feasibility
has not been established.

The dominant primary solve cost was exact constraint Jacobian evaluation:
603.668 s across 35 calls in A, and 575.584 s across 30 calls in B. Both graph
builds took approximately 2–3 s for mechanics, 20 s for assembly/guess rollout,
and 8 s for the IPOPT adapter. This measured derivative cost limits progress
under the solve ceiling. No global optimality, physical impossibility, real-time capability,
motor validation or LLM-organizational advantage is inferred.

The first adaptive Radau replay reached its 900 s process limit without a
trajectory artifact. Its original unknown event was retained, process absence
was verified, and the installed Python timeout handler's kill/wait behavior
was inspected before settling a known failure at 900.023 s. There was no
automatic repeat of an unresolved outcome. A committed repair used adaptive
SciPy BDF on the direct dynamics/state-Jacobian graph. An analytic switching
test verified zero initialization and continuity. Both replacements completed
the full horizon with finite bounded inputs and no integration failure.

| Primary diagnostic replay | Terminal error, mm | Holding position maximum, mm | Holding speed maximum, m/s | Dense tip disagreement, mm | Dense speed disagreement, m/s | Process seconds |
|---|---:|---:|---:|---:|---:|---:|
| A, retained iteration 32 | 4.651 | 4.651 | 0.08382 | 8.648 | 0.10490 | 191.150 |
| B, retained iteration 12 | 7.617 | 7.617 | 0.12401 | 8.236 | 0.09416 | 160.415 |

The sampled instantaneous holding speed maxima were 0.08207/0.12401 m/s.
Dense replay used 0.0005 s samples, `rtol=1e-8`, and curvature/rate absolute
tolerances `1e-9/1e-7`. Disagreement uses linear interpolation of the optimizer's
tip outputs; node discrepancies are retained separately. No optimizer state
was used to initialize or reset integration. Neither primary passes the
1 mm/0.002 m/s replay gates or the holding speed limit. Their replay trajectories
are diagnostics of infeasible NLP iterates, not validated task solutions.

A single additional derivative-execution check compared exact automatic and
forced reverse AD on the same assembled transport graph. Its 18,931 Jacobian
nonzeros agreed within 7.28e-12; the global design column touches 433 rows.
One point evaluation took 8.932 s automatically versus 30.214 s in forced
reverse mode. These transport-graph timings are not general solver performance
claims. This concrete bottleneck justified the two allowed correction solves,
with identical fresh 0.2 N guesses, original equations/weights, 570 s stopping
settings and automatic exact AD. No second ramp initialization or random seed
was introduced.

| Corrected case | Lengths, m | Iterations | Objective | Largest normalized violation | Solve seconds |
|---|---|---:|---:|---:|---:|
| A | 0.160000 / 0.110000 | 59 | 0.0140111 | 0.218720, speed at 0.30 s | 573.529 |
| B | 0.155782 / 0.114218 | 57 | 0.0128458 | 0.736259, speed at 0.34 s | 570.453 |

Corrected A remains infeasible: terminal error 9.812 mm, holding position
maximum 9.818 mm, holding speed maximum 0.022079 m/s and force-balance residual
up to 2.50e-7 N m²/rad. Its effort/weighted variation are
0.013974686/0.0000363993. Exact Jacobians consumed 550.976 s across 61 calls,
so changing AD execution improved progress without changing the physics.

Corrected B also terminated `Maximum_CpuTime_Exceeded`, with no feasible iterate.
Its terminal/holding position error is 10.017 mm and holding speed is
0.026353 m/s. Effort/weighted variation are 0.012813304/0.0000324813.
The smaller objective is attached to an infeasible trajectory and does not
establish an advantage over A. Both corrected replay selections are their last
retained iterations, 59 and 57. All four solves actually entered IPOPT; neither
the two optional ramp solves nor another grid solve was dispatched.

The final reporting commit adds meaningful physical task-residual units and
compact trajectory metrics, plus a deterministic CLI for persisting returned
schedule selections. It changes neither equations nor integration. Dependency
migrations carry the original correctness proof on the same activity and grant;
budgets and failed executions are preserved.

The focused replay test initially required an unnecessarily tight global
1e-8 analytic position tolerance across 35 adaptive BDF restarts. Its measured
error was 5.94e-8. The corrected 1e-7 global tolerance (0.1 micrometre, 10,000
times tighter than the replay gate) passed without changing integration
tolerances. Both the failure and repair are retained in the verification ledger;
no NLP was run as a test. A separate regression preserves the fixed-design
analysis tuple and linearization API.

The native `evidence.read` call retrieved corrected B's `/costs_s` from its
immutable solver artifact through the actual Host. No live model request was
needed. The mathematical tools' compact Feedback and referenced artifacts
carry the actual solver/replay outcomes separately from physical status.

| Corrected diagnostic replay | Terminal error, mm | Holding position maximum, mm | Dense holding speed, m/s | Dense tip disagreement, mm | Dense speed disagreement, m/s | Process seconds |
|---|---:|---:|---:|---:|---:|---:|
| A, iteration 59 | 5.483 | 6.876 | 0.09800 | 8.111 | 0.09969 | 174.828 |
| B, iteration 57 | 5.484 | 6.804 | 0.09370 | 7.629 | 0.09376 | 164.184 |

The corrected sampled holding speeds were 0.09777/0.09355 m/s. Both completed
with no integration failure and compliant inputs. They fail the discrepancy
and holding speed gates. Zero MuJoCo/controller-11 evaluations were launched
because no mathematically feasible, replay-qualified candidate exists in this
study. No claim about physical impossibility follows.

| Cost, seconds | Primary A | Primary B | Corrected A | Corrected B |
|---|---:|---:|---:|---:|
| Mechanics construction | 2.163 | 2.770 | 1.740 | 1.592 |
| Assembly and coherent guess | 19.650 | 19.995 | 29.925 | 30.815 |
| Solver construction | 8.243 | 8.375 | 27.745 | 27.443 |
| Numerical solve | 608.711 | 580.952 | 573.529 | 570.453 |
| Full numerical process | 641.607 | 614.923 | 637.262 | 635.261 |

Full process costs include construction and result extraction; inner timers
are components, not additional charges. The mechanics/reference check cost
33.097 s and the AD execution check 109.436 s. Four completed replay processes
cost 690.577 s combined, and the known Radau failure cost 900.023 s. Focused
verification/interface inspection and candidate-selection checks are charged
conservatively at 34.069 s; inner selection/postprocessing costs are retained
separately. Cumulative numerical work is **4296.348 s of 7200 s**, leaving
2903.652 s unused. Backend and provider costs are zero. Twelve Host tool calls
include the eleven scientific invocations and one evidence read. No capacity
was replenished. Scientific STOP occurred after 6134.104 s of activity time;
engineering delivery continues under the original eight-hour clock.

The [compact result summary](../evidence/casadi_codesign_pilot_20261010/result_summary.json)
and [immutable archive manifest](../evidence/casadi_codesign_pilot_20261010/archive_manifest.json)
provide exact costs, identities and source artifact hashes. Implementation
commits are `056a5cf8199b4cf4b654f6944926dfb2a572f81b`,
`e3ffcf8216a9ec2cf7071c8ad828632ce284a3aa`,
`39c71a1f5d56f0eb36237e91f49e27748a7ed5db`, and
`9af70b160ca8589f5e3cb0cabf73fb6a498bfba2`; documentation/evidence closeout
is a subsequent scoped commit. Ordinary push targets only
`feat/casadi-codesign-pilot`.

The existing-model joint optimization path works through differentiation,
actual NLP execution, typed evidence and independent integration. Its bounded
results establish neither feasibility nor a joint-design benefit. Exact
constraint Jacobians still consumed 550.976/548.686 s in the corrected pair.
The next justified study should first reduce that measured derivative cost,
then compare a finer state grid with the same 35 control intervals and task
constraints under a fresh bounded authorization. The substantial replay
discrepancy motivates grid refinement; the present infeasible dynamics defects
mean it cannot yet be attributed solely to the grid. No further solves are
authorized by this stopped activity.
