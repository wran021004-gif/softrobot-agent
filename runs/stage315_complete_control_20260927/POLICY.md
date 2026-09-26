# Declared experiment and return policy

The original task remains 0.35 s, 10 mm endpoint tolerance, straight start,
10 ms held commands and the original robot, gravity, mount and force limits.
The milestone uses one agent and the existing production workspace/IPOPT path.

Warm starts shift controls by one executed interval, preserve the actual previous
input, and regenerate **every** state from the measured state with the shooting
residual and cached Newton root solver. Old shifted nodes are only Newton guesses.
The generic optimizer independently evaluates the entire initial constraint vector.

The optional return policy is declared before the final rollouts:

- Keep the maximum scaled constraint/bound violation at 1e-5.
- Compare signed objective against this solve's independently feasible seed.
- After 5 s of numerical optimization, return a feasible candidate with at least
  10% objective improvement over that seed.
- At 15 s, return the best feasible candidate no worse than the seed. If there was
  no feasible seed, return the best feasible current-solve candidate at that budget.
- A verified feasible seed whose entire predicted trajectory has tip error at
  most 5 mm and tip speed at most 0.02 m/s can return without artificial improvement.
- Genuine optimizer convergence remains accepted normally. Callback budgets are
  checked at iterations, not hard wall-clock interrupts; the CPU cap stays 30 s.
- Preserve raw `User_Requested_Stop`, report `feasible_early_stop`, and independently
  validate the selected vector before using it. This is not convergence.
- The policy is disabled by default in the generic solver and controller contract.

Preparation, graph/solver construction, callback candidate times, policy stop,
validation and delivered-plan wall time are reported separately. A feasible
initialization is not evidence of optimization or successful control.

The fixed Stage 3.14 problems are used only for preparation/return comparisons.
For control performance, the initial formulation uses a 100 ms horizon (10 held
10 ms intervals), tracking weight 1, terminal position weight 5, curvature-rate
stage and terminal weights 1e-4, tension weight 1e-4 and variation weight 1e-3.
Implicit Euler prediction is unchanged; actual GVS observations come from BDF
with exact AD Jacobian, rtol 1e-7 and atol 1e-8. No physical damping is changed.

The preparation rollout covers 0.12 s to observe approach/deceleration. Its actual
integrated states, inputs and accepted plans are checkpointed and reused as the
prefix of the original 0.35 s run, provided the formulation is identical.
Settling is reported separately: every sampled endpoint in the final 50 ms must
have error <=10 mm and tip speed <=0.02 m/s. The official endpoint criterion is
unchanged. No continuation substitutes for the deadline.

Budget before rollout: 35*(30 s solve + 12 s integration + 6 s preparation), about
28 minutes, with a 1800 s wall guard per execution. The initial 10-second delivery
objective is not a gate. One bounded formulation correction is allowed if the
approach check exposes a specific deficiency. Three consecutive unusable NMPC
updates stop backend execution; the only interim response is bounded hold-last.
