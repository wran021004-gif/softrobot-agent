# Round 3 experiment decisions

Status: BLOCKED_FOR_HUMAN_APPROVAL applies to real experiments only. No approved
optimization/control experiment policy existed in the audited baseline 928547d.
The machine-readable proposal next to this document deliberately contains no
numerical search values. Production grammar remains deny-by-default.

Human decisions required before any real reach_free optimization or feedback run:

1. Select each permitted numerical DesignSpec field; approve its units, finite
   lower/upper bounds, positive/integer constraints and scientific justification.
   Update Human-owned grammar approval metadata and approve an experiment subset.
   Sections beyond one remain unsupported. Segmentation changes retain the fixed
   surrogate joint constants and do not imply continuum stiffness equivalence.
2. Approve objective references: model.predicted_position_error_m for ranking and
   mujoco.position_error_m for physical comparison. Canonical acceptance always
   follows the existing task evaluator. No tolerance value belongs in policy.
3. Approve allowed M0/M1 and C1/C2 routes, the seed, total evaluation budget
   (including rejected attempts), and the separate MuJoCo validation sub-budget.
   At least baseline and another candidate must complete canonical evaluation
   before a comparative physical improvement claim is supported.
4. For C2, approve the Jacobian-transpose experiment and all fixed parameters:
   gain_rad2_per_m2, update_every_steps, max_bend_update_rad,
   max_command_update_m, min_tendon_length_m, max_tendon_length_m.
   Their exact source is policy.feedback_parameters, separate from DesignSpec.
   These are outer-loop parameters; kp and force limits in approved Physics
   Contracts are unchanged. Automatic controller tuning is not implemented.
5. Approve sensitivity variables/ranges and fidelity. Observed trends are evidence
   only; no automatic causal diagnosis or universal tracking/mismatch threshold.
6. Approve repair_iteration_budget, ordered repair_actions, and stop_conditions
   (budget_exhausted and actions_exhausted required; canonical_success optional).
   Each repair shares the same total experiment evaluation/MuJoCo budget.
7. Place a reviewed HUMAN_APPROVED policy and its approval-source record under
   configs/experiments/, binding the existing TaskContract and baseline candidate.
   A status string is repository authority metadata, not cryptographic proof of
   a person's approval. Future agents cannot write this Human-owned directory.

Separate deferred scientific decisions, not prerequisites for the implemented
geometric algorithms: material/EI, damping, tendon slack/friction/elasticity,
actuator identification, multi-section coupling and causal diagnostic criteria.
reach_window_v1 remains PROPOSED_NOT_APPROVED; its benchmark/initializer decisions
remain listed in proposals/benchmark/reach_window_v1/README.md. No promotion occurs.

Synthetic numbers under tests/fixtures/round3 are software fixtures only and
cannot execute frozen reach_free or supply formal benchmark results.
