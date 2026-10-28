# PHS-2D round 2 frozen implementation plan

Base 519a798003f841ea44f3521b9cb99b74349abf2d, fetched and confirmed.
Independent branch/worktree research/phs2d-passive-equilibrium-search.
Original STOP Store and evidence are read-only; new Study phs2d-equilibrium-search-20261028-v1.

1. Store-admitted read-only tail analysis. Old traces have q/qvel but no qacc,
   per-joint residual or warmstart, so identify missing facts explicitly.
2. Native potential/KKT solver (SciPy SLSQP, nonnegative multipliers, reduced
   Hessian), gradient/virtual-work regression and loaded geometric Hessian.
3. P0-A validates semantics; P0-B requires one legal KKT equilibrium supported
   by unloaded dynamics. Loaded failure does not block other legal structures.
4. Math-directed bounded A/B/C/D comparisons, fixed per-rope payouts; six search
   conditions only. Dynamics starts from qualified unloaded q, never loaded q.
5. Ten-condition witness requires held-out four conditions only after six pass.
   Reserve final numerical/independent verification; archive all failures.

Budgets: 8M steps, P0 <=400k, P1 <=6.8M, reserve >=800k for final; math requests
<=400, legal generated candidates <=80. Internal forwards, SQP iterations,
finite differences and QP calls will be explicitly counted. No Provider/Agent,
NMPC/PPO/active optimization, task SELECT or automatic merge.

Original performance and static acceptance tolerances unchanged in protocol v3.
Initial payout domain: each reference length +/-0.2 mm, independently frozen.
Original timestep and solver parameters initially retained. Any numerical
protocol comparison gets explicit source identity; no retrospective relabeling.

Completed 2026-10-28: steps 1–4 and final numerical verification. P0-A/B passed.
23 assemblies / 17 unique structures, 94 math requests, 1,744,000 integration
attempts. No six-condition performance pass; holdout loads intentionally unused.
Best valid fine-step CD assembly remains too stiff at the force point and has
ratio >1. Study stopped through the existing stop action; old Store unchanged.
See phs2d_round2_results_20261028.md and the independent round-2 evidence archive.
