# Public GVS free-reach result

Program-generated factual result:

```json
{
  "accepted_noninitialization_plans": 28,
  "accepted_plans": 35,
  "applied_tension_ranges": [
    {
      "limit_n": 8.0,
      "maximum_n": 2.5551652199396235,
      "minimum_n": 1.422389603111227,
      "tendon": "near_t0",
      "tendon_index": 0
    },
    {
      "limit_n": 8.0,
      "maximum_n": 4.755852667139922,
      "minimum_n": 3.9442650938768438,
      "tendon": "near_t1",
      "tendon_index": 1
    },
    {
      "limit_n": 8.0,
      "maximum_n": 5.141690020625788,
      "minimum_n": 3.1031566686630025,
      "tendon": "near_t2",
      "tendon_index": 2
    },
    {
      "limit_n": 8.0,
      "maximum_n": 5.8112037757196315,
      "minimum_n": 3.218253612486097,
      "tendon": "far_t0",
      "tendon_index": 3
    },
    {
      "limit_n": 8.0,
      "maximum_n": 3.2223613359595125,
      "minimum_n": 0.7859357597552847,
      "tendon": "far_t1",
      "tendon_index": 4
    },
    {
      "limit_n": 8.0,
      "maximum_n": 2.4170764019086053,
      "minimum_n": 0.45573349501265825,
      "tendon": "far_t2",
      "tendon_index": 5
    }
  ],
  "candidate": {
    "candidate_id": "rev_compliant_max",
    "configuration": {
      "artifact_id": "9d159d6fb19bb276b46cbfbe71ed23119070ce45e5ae2aa0f67348c9b83360d8",
      "media_type": "application/json"
    },
    "execution_id": "b1bc6758f2d54f4791f14e6a19827264",
    "owner_run_id": "gvs-live-c0f08900d76e-a7a46a25d0958b8b"
  },
  "complete": true,
  "configuration": {
    "artifact_id": "9d159d6fb19bb276b46cbfbe71ed23119070ce45e5ae2aa0f67348c9b83360d8",
    "media_type": "application/json"
  },
  "control_period_s": 0.01,
  "control_updates": 35,
  "converged_updates": 0,
  "coordinate_frame": "world",
  "deadline_misses": 35,
  "error_convention": "actual_tip minus target",
  "evaluation": {
    "artifact_id": "42fe1bd816229fb855c4ca316ef5955f3a54d3a69d7e4dc24f83a8047c67d411",
    "media_type": "application/json"
  },
  "evaluation_validity": "valid",
  "execution_id": "b1bc6758f2d54f4791f14e6a19827264",
  "force_bound_violation_n": 0.0,
  "hold_last_responses": 0,
  "initialization_selected": 7,
  "mean_complete_update_s": 11.819069280029673,
  "measured_computation_s": 417.625,
  "one_step_prediction_evidence": {
    "artifact_id": "1f3c60e134baf070868c7ff9875e15353ba9a6b3056382822582a14d6c4369f5",
    "media_type": "application/json"
  },
  "one_step_prediction_summary": {
    "aligned_count": 35,
    "frame": "world",
    "maximum_tip_difference_m": 0.007763725050668922,
    "mean_tip_difference_m": 0.005990814789575285,
    "missing": [],
    "scope": "Only accepted first-step predictions matched to next execution timestamp; no future-plan replay comparison"
  },
  "real_time_demonstrated": false,
  "report": {
    "execution_id": "b1bc6758f2d54f4791f14e6a19827264",
    "owner_run_id": "gvs-live-c0f08900d76e-a7a46a25d0958b8b",
    "reference": {
      "artifact_id": "999d0431346f49134de4a80bfe3e8180f53798ff67f0c0d6fe687c2d19ea2ba3",
      "media_type": "application/json"
    },
    "request_id": "single-profile-report"
  },
  "result_type": "free_reach",
  "sampled_settling": {
    "available": true,
    "continuous_time_guarantee": false,
    "max_error_m": 0.011787523596227019,
    "max_speed_m_s": 0.039850392544551944,
    "passed": false,
    "position_limit_m": 0.01,
    "speed_limit_m_s": 0.02,
    "window_s": 0.05
  },
  "signed_position_error_m": [
    -0.010610914600433285,
    0.0037558004036140416,
    0.003499738161939131
  ],
  "simulated_duration_s": 0.35000000000000003,
  "simulation": {
    "artifact_id": "ee9ed264e6900b12a653ea1f0f88cadc1e2edb6d2770254e83f79e9e49b4dd90",
    "media_type": "application/json"
  },
  "solver_error_count": 0,
  "target_position_m": [
    0.29,
    0.035,
    0.19
  ],
  "task_accepted": false,
  "terminal_error_m": 0.011787523596227019,
  "terminal_position_m": [
    0.2793890853995667,
    0.038755800403614045,
    0.19349973816193913
  ],
  "terminal_tip_speed_m_s": 0.03504922546562082,
  "valid_complete_execution": true
}
```

Reach acceptance, sampled settling, convergence and computation are separate. Provider prose requires independent review.
