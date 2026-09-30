# Public GVS free-reach result

Program-generated factual result:

```json
{
  "accepted_noninitialization_plans": 12,
  "accepted_plans": 35,
  "applied_tension_ranges": [
    {
      "limit_n": 8.0,
      "maximum_n": 2.077194118027104,
      "minimum_n": 1.197347703597216,
      "tendon": "near_t0",
      "tendon_index": 0
    },
    {
      "limit_n": 8.0,
      "maximum_n": 4.755852667139922,
      "minimum_n": 3.8122215280499736,
      "tendon": "near_t1",
      "tendon_index": 1
    },
    {
      "limit_n": 8.0,
      "maximum_n": 4.804765797726525,
      "minimum_n": 3.1031566686630025,
      "tendon": "near_t2",
      "tendon_index": 2
    },
    {
      "limit_n": 8.0,
      "maximum_n": 4.920791140393819,
      "minimum_n": 3.218253612486097,
      "tendon": "far_t0",
      "tendon_index": 3
    },
    {
      "limit_n": 8.0,
      "maximum_n": 3.8198211140651894,
      "minimum_n": 0.7859357597552847,
      "tendon": "far_t1",
      "tendon_index": 4
    },
    {
      "limit_n": 8.0,
      "maximum_n": 2.0545855359439265,
      "minimum_n": 8.145818446189429e-05,
      "tendon": "far_t2",
      "tendon_index": 5
    }
  ],
  "candidate": {
    "candidate_id": "b2_near0p169_far0p129_compliant_s1p05",
    "configuration": {
      "artifact_id": "a9e2ba04110b8417b9ef6282b0385f3f79d532810d6c43e338a5dc8d55eaf5d5",
      "media_type": "application/json"
    },
    "execution_id": "7575e2c798fa4b66a388f7e277ba51c9",
    "owner_run_id": "gvs-live-f4a6655fe472-2ca2bdf3ffc6811e"
  },
  "complete": true,
  "configuration": {
    "artifact_id": "a9e2ba04110b8417b9ef6282b0385f3f79d532810d6c43e338a5dc8d55eaf5d5",
    "media_type": "application/json"
  },
  "control_period_s": 0.01,
  "control_updates": 35,
  "converged_updates": 0,
  "coordinate_frame": "world",
  "deadline_misses": 35,
  "error_convention": "actual_tip minus target",
  "evaluation": {
    "artifact_id": "b4e7bc1240f43c8a27a87909b5955462079f4a46222ec053c613256a6de93fce",
    "media_type": "application/json"
  },
  "evaluation_validity": "valid",
  "execution_id": "7575e2c798fa4b66a388f7e277ba51c9",
  "force_bound_violation_n": 0.0,
  "hold_last_responses": 0,
  "initialization_selected": 23,
  "mean_complete_update_s": 15.340472751430102,
  "measured_computation_s": 540.280999999959,
  "one_step_prediction_evidence": {
    "artifact_id": "2d431cc6383b75f759d59196cfad602c36d3545183a395c5f5022e9061a35a0b",
    "media_type": "application/json"
  },
  "one_step_prediction_summary": {
    "aligned_count": 35,
    "frame": "world",
    "maximum_tip_difference_m": 0.007535415657909328,
    "mean_tip_difference_m": 0.004059976742465859,
    "missing": [],
    "scope": "Only accepted first-step predictions matched to next execution timestamp; no future-plan replay comparison"
  },
  "real_time_demonstrated": false,
  "report": {
    "execution_id": "7575e2c798fa4b66a388f7e277ba51c9",
    "owner_run_id": "gvs-live-f4a6655fe472-2ca2bdf3ffc6811e",
    "reference": {
      "artifact_id": "0b46bbc5b1511b61e6879162a5b6fa359c37ed52246f4b193e406ad997862330",
      "media_type": "application/json"
    },
    "request_id": "single-profile-report"
  },
  "result_type": "free_reach",
  "sampled_settling": {
    "available": true,
    "continuous_time_guarantee": false,
    "max_error_m": 0.010781152479219073,
    "max_speed_m_s": 0.4080379021769773,
    "passed": false,
    "position_limit_m": 0.01,
    "speed_limit_m_s": 0.02,
    "window_s": 0.05
  },
  "signed_position_error_m": [
    -0.007155638897093364,
    0.0023117928912372576,
    0.0017767463844345355
  ],
  "simulated_duration_s": 0.35000000000000003,
  "simulation": {
    "artifact_id": "85497e413a426c7cdef2045949fbdc67f55bc17ff13131229b5f7dadfc1d2d92",
    "media_type": "application/json"
  },
  "solver_error_count": 0,
  "target_position_m": [
    0.29,
    0.035,
    0.19
  ],
  "task_accepted": true,
  "terminal_error_m": 0.0077268610775768345,
  "terminal_position_m": [
    0.2828443611029066,
    0.03731179289123726,
    0.19177674638443454
  ],
  "terminal_tip_speed_m_s": 0.1422878074819384,
  "valid_complete_execution": true
}
```

Reach acceptance, sampled settling, convergence and computation are separate. Provider prose requires independent review.
