# CasADi joint length and trajectory pilot, 2026-10-10

The current-model CasADi path now constructs and actually executes fixed-design
and joint-design trajectory NLPs. Both primary solves returned finite iterates
without finding mathematical feasibility within their deadlines. Independent
replay and final delivery are in progress; this file is finalized at closeout.
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
under the solve ceiling. Subsequent bounded numerical work, replay outcomes,
physical eligibility, final cumulative costs and push status are added below
at closeout. No global optimality, physical impossibility, real-time capability,
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

Corrected A remains infeasible: terminal error 9.812 mm, holding position
maximum 9.818 mm, holding speed maximum 0.022079 m/s and force-balance residual
up to 2.50e-7 N m²/rad. Its effort/weighted variation are
0.013974686/0.0000363993. Exact Jacobians consumed 550.976 s across 61 calls,
so changing AD execution improved progress without changing the physics.
