# Bounded recovery-enabled holding-speed follow-up

The one-weight development passed, but its exact scientific-configuration confirmation failed holding speed. A repeatable improvement has not been demonstrated.

The archived failure occurs with active holding cost and predicted speed already above actual speed. The new study used the existing DeepSeek model and frozen task; the model chose the actual weight and experiments.

| Execution | Terminal error mm | Holding max error mm | Holding max speed m/s | Overspeed samples s | Joint acceptance |
|---|---:|---:|---:|---|---|
| Inherited recovery baseline | 3.016 | 3.464 | 0.024642722 | [0.3, 0.31] | valid_failure |
| development | 2.912 | 2.918 | 0.008583287 | [] | accepted |
| exact_confirmation | 3.349 | 4.355 | 0.058648447 | [0.32, 0.33, 0.34, 0.35] | valid_failure |

The development changes only holding_tip_speed_weight from .05 to .10; terminal speed weight remains .10 and recovery True. Complete generated physics/task/initial state/seed/timing/solver/evaluation identity is checked. No baseline or historical optimization was rerun.

The .29s update predicted .30s speed .026699464m/s versus measured .020493825; the .30s update predicted .31s speed .031330296 versus .024642722. Both first-node hold flags are active. Late inputs are interior; .29/.30s early-stop reasons are relative_seed_improvement, selected iteration4. At .32s verified_settled_seed selected iteration0 carries changed prior inputs. No exception fallback is implied.

The identical-configuration executions share the same numerical guess and independent zero physical initial state. Their first applied command divergence is update8/.08s: measured state, previous input and prediction timing are identical and no holding node is active. Both stop by budget_best_feasible, but raw recovery parents are iterations16/19 and delivery selections differ. Earlier complete warm plans are unrecorded, so this identifies optimizer/selection path variability without isolating its unique source.

The saved first-node holding cost is .000891077/.001226984 at updates29/30. Running terms include h=.01; terminal speed does not. Position and velocity normalization matter. These supported partial terms cannot establish the dominant complete horizon cost. The archived full snapshot is only update20; missing late vectors, intermediate nodes and full iteration/cost decompositions remain unknown.

Actual counts: 3 provider sends, 9 public calls, 0 standalone local NLP attempts, 2 MuJoCo launches, 70 internal NMPC attempts, 16 internal recoveries / 152 roots. No codesign/BDF/hardware/extra research model.

Scientific time charged 894.610s of3600s; remaining 2705.390s. Actual project ledger and six-hour activity/delivery reserve are in the machine summary. All updates and wall-clock real-time performance are separate below. Repeated artifact references are not repeated executions.

Confirmation performed: True; exact scientific identity matches: True.

Original model decisions, hypotheses and STOP are preserved in plan files and immutable events/archive. Codex supplied implementation, arithmetic and task context, not autonomous model memory or its scientific decisions. The original model causal hypothesis remains a hypothesis: the historical complete dominant cost and unique cause are unknown. One tested value cannot establish all weights ineffective; a repeated configuration cannot establish robustness or continuous-time/hardware performance.

Validation: nine focused new checks passed; no full suite, broad benchmark or repeated old mechanics validation. The initial policy compile failure was repaired without a provider send or numerical experiment, and its cost/time were retained. Existing Python/dependencies were reused without upgrades.

Implementation freeze: `f452ba27efd3d7f0ede7ff96200352097f42c511`. Source: `f31a926ee741fcc859853d851ab255b2bf4e1409`. Delivery: `feat/nmpc-settling-followup`.

[Machine-readable summary](../evidence/nmpc_settling_20261011/scientific_summary.json), [diagnostic timeline](../evidence/nmpc_settling_20261011/diagnostic_timeline.json), [commands](../evidence/nmpc_settling_20261011/execution_commands.json), [runbook](nmpc_settling_runbook.md), [case draft](../memory/nmpc_feasibility_case_draft.json), [procedure draft](nmpc_feasibility_procedure.md).

```json
{
  "role": "development",
  "execution_id": "04c93bc37a834ae7b3fd7667ce8e4285",
  "control": {
    "candidate": {
      "artifact_id": "0e16077e9183ebcd64729eb982aa5a73e5eb03e111d5d7ed402552ca16db345b",
      "media_type": "application/json"
    },
    "feasible_return_budget_s": 15.0,
    "holding_tip_speed_weight": 0.1,
    "preceding_execution": {
      "artifact_id": "a370a238d80c88a23e0a1272d9d288c2d1bea9e073cd231404e594724e280bb5",
      "media_type": "application/json"
    },
    "record_update_ids": [
      29,
      30
    ],
    "recover_returned_tensions": true,
    "substeps": 1,
    "terminal_tip_speed_weight": 0.1
  },
  "applied_updates": 35,
  "plan_selection": {
    "initialization": 15,
    "recovered": 6,
    "other_feasible": 29,
    "accepted_noninitialization": 20
  },
  "recovery": {
    "attempts": 6,
    "selected": 6,
    "failed": 0,
    "root_solves": 60
  },
  "stops": {
    "budget_best_feasible": 12,
    "relative_seed_improvement": 17,
    "verified_settled_seed": 6
  },
  "raw_stops": {
    "User_Requested_Stop": 35
  },
  "input_range_n": [
    0.2593507808283583,
    5.8507457133535805
  ],
  "prediction_summary": {
    "aligned_count": 35,
    "frame": "world",
    "maximum_speed_magnitude_difference_m_s": 0.0886547501538345,
    "maximum_tip_difference_m": 0.003955689120204966,
    "maximum_velocity_vector_difference_m_s": 0.08946397004175773,
    "mean_tip_difference_m": 0.0028092522058620704,
    "missing": [],
    "scope": "Only accepted first-step predictions matched to next execution timestamp; no future-plan replay comparison",
    "velocity_matched_count": 35,
    "velocity_missing": []
  },
  "real_time": false,
  "deadline_misses": 35,
  "costs_s": {
    "construction": 0.21594259998528287,
    "evaluation": 1.062999999965541,
    "profile": 2.312999999965541,
    "settling_analysis": 0.04135710000991821,
    "simulation": 459.2029999999795,
    "total": 462.8362996999058
  }
}
```

```json
{
  "role": "exact_confirmation",
  "execution_id": "1523bfc7c97647ed85b1e85da6774d79",
  "control": {
    "candidate": {
      "artifact_id": "0e16077e9183ebcd64729eb982aa5a73e5eb03e111d5d7ed402552ca16db345b",
      "media_type": "application/json"
    },
    "feasible_return_budget_s": 15.0,
    "holding_tip_speed_weight": 0.1,
    "preceding_execution": {
      "artifact_id": "21a10d08e03e5cb4d3831f0671daecc0b8acedd31c4de78c2e55eb2e9bd5bdaf",
      "media_type": "application/json"
    },
    "record_update_ids": [
      29,
      30
    ],
    "recover_returned_tensions": true,
    "substeps": 1,
    "terminal_tip_speed_weight": 0.1
  },
  "applied_updates": 35,
  "plan_selection": {
    "initialization": 6,
    "recovered": 10,
    "other_feasible": 25,
    "accepted_noninitialization": 29
  },
  "recovery": {
    "attempts": 10,
    "selected": 10,
    "failed": 0,
    "root_solves": 92
  },
  "stops": {
    "budget_best_feasible": 5,
    "relative_seed_improvement": 25,
    "verified_settled_seed": 5
  },
  "raw_stops": {
    "User_Requested_Stop": 35
  },
  "input_range_n": [
    0.2786360842598081,
    8.0
  ],
  "prediction_summary": {
    "aligned_count": 35,
    "frame": "world",
    "maximum_speed_magnitude_difference_m_s": 0.0886547501538345,
    "maximum_tip_difference_m": 0.003955689120204966,
    "maximum_velocity_vector_difference_m_s": 0.08946397004175773,
    "mean_tip_difference_m": 0.0029344146183641084,
    "missing": [],
    "scope": "Only accepted first-step predictions matched to next execution timestamp; no future-plan replay comparison",
    "velocity_matched_count": 35,
    "velocity_missing": []
  },
  "real_time": false,
  "deadline_misses": 35,
  "costs_s": {
    "construction": 0.269897399994079,
    "evaluation": 1.0459999999729916,
    "profile": 1.2190000000409782,
    "settling_analysis": 0.03288250003242865,
    "simulation": 389.06300000002375,
    "total": 391.6307799000642
  }
}
```

Original final disposition (preserved, not rewritten):

STOP. Inherited evidence (prior round, not new work): baseline recovery-enabled execution cda6509a699545d7b59b9be854c60d08 with holding_tip_speed_weight 0.05, result artifact a370a238d80c88a23e0a1272d9d288c2d1bea9e073cd231404e594724e280bb5, is a valid_failure whose only failing component is sampled holding_speed = 0.024643 m/s at t=0.31 s (0.020494 at t=0.30 s) with holding position 0.003464 m and terminal error 0.003016 m passing; the archived diagnosis (6829111c627768fcf8800054c676c4070b0989e0cfa908143c1e61c846ccf7c8) shows the holding penalty already active and correctly computed at updates 29/30 (first-node holding cost 0.000891/0.001227) and its first-step prediction already above the measured overspeed (0.0267 vs 0.0205; 0.0313 vs 0.0246), so persistence is not an absent or underestimated holding penalty. New work this round, one development plus one exact confirmation: (1) development execution 04c93bc37a834ae7b3fd7667ce8e4285, feedback artifact 21a10d08e03e5cb4d3831f0671daecc0b8acedd31c4de78c2e55eb2e9bd5bdaf, holding_tip_speed_weight raised 0.05 to 0.10 with recover_returned_tensions true, feasible_return_budget 15 s, substeps 1, terminal_tip_speed_weight 0.10 and everything else frozen, preceding_execution a370a238; accepted, sampled holding max speed 0.008583 m/s, holding position 0.002918 m, terminal error 0.002912 m, 0 solver errors, 6 recovery selections. (2) Confirmation execution 1523bfc7c97647ed85b1e85da6774d79, feedback artifact 12db137c5de38a024cbeb346dd1664bb9d3be161d1b3c023a15bd0e77ed7ab0e, identical candidate, weights, seed 17, named zero initial state, recovery and acceptance with preceding_execution 21a10d08; valid_failure, sampled holding max speed 0.058648 m/s (about 3x the limit and worse than the 0.05 baseline), per-sample .30-.35 s = 0.005653/0.009979/0.027209/0.058648/0.036177/0.027491 m/s, holding position 0.004355 m, terminal error 0.003349 m, near_t1 tension at the 8 N bound, 10 recovery selections. Sampled joint acceptance: development accepted (all components pass); confirmation not accepted (holding_speed fails, position/terminal/solver-errors/coverage pass). Confirmation status: performed once and did not repeat; this is a same-configuration, same-seed repetition result only, explicitly not a robustness, continuous-time, real-time, hardware or model-superiority claim, and no unique cause is attributed. Model contribution and limits are distinct: the GVS projected model places and computes the soft holding-speed penalty at the correct absolute node times and already predicts more overspeed than measured, but its projected first-step tip velocity differs from the full serial backend (mean tip difference 0.0028 m, max speed difference 0.088 m/s), the penalty is soft rather than a hard speed constraint, every solve early-stopped (converged_updates 0, 35/35 deadline misses, stops by relative_seed_improvement/budget_best_feasible/verified_settled_seed inside the 15 s feasible-return budget), and the ideal-tension model omits shear, stretch, torsion, tendon friction and actuator dynamics. Answer to the research question: with recovery enabled the two overspeed holding samples are not caused by an absent or mis-scaled holding penalty; and one in-range speed-weight change (holding_tip_speed_weight 0.05 to 0.10) produced one accepted closed loop but the same-configuration independent repetition did not reproduce it, so no repeatable improvement of the frozen task is demonstrated. No local NLP attempts, full NLP solves or independent replays were used (all 0). Accounting basis is the packet's pre-send template with its stated before-send timestamp; used and remaining budget are reported in final_accounting below.

- No unique causal attribution; structure and control remain jointly reported.
- Same-configuration same-seed repetition did not hold, so no robustness, real-time or continuous-time claim is made.
- Sampled 6-point inclusive holding window is not a continuous-time guarantee.
- Projected GVS predictions differ from the full serial backend, and ideal tensions omit shear, stretch, torsion, tendon friction and actuator dynamics.
- All solves early-stopped without convergence, so wall-clock and initialization state influence the delivered iterates.
