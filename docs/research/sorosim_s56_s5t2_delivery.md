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

Raw evidence and the exact candidate-bound physical handoff are in
[the P2 summary](../../evidence/sorosim_s56/codesign/summary.json). The handoff
states use 36 original samples, retain the 32-step integration identity and link
the full internal NLP trajectory and independent replay. It certifies complete
numerical integration, **not** original task success.
