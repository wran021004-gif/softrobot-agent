# Public GVS tracking result

{
  "valid_complete_execution": true,
  "official_task_success": true,
  "tracking": {
    "acceptance": {
      "contract": "family.tracking_evaluation",
      "data": {
        "max_position_error_m": 0.01,
        "tension_limits_n": {
          "far_t0": 8.0,
          "far_t1": 8.0,
          "far_t2": 8.0,
          "near_t0": 8.0,
          "near_t1": 8.0,
          "near_t2": 8.0
        }
      },
      "version": "1.0.0"
    },
    "continuous_time_guarantee": false,
    "metrics": [
      {
        "name": "max_position_error",
        "units": "m",
        "value": 0.005772548837294318
      },
      {
        "name": "rms_position_error",
        "units": "m",
        "value": 0.004412616885360754
      },
      {
        "name": "terminal_position_error",
        "units": "m",
        "value": 0.003872882630204964
      }
    ],
    "reference": {
      "end_m": [
        0.30599999999999994,
        0.024,
        0.142
      ],
      "end_s": 0.4,
      "frame": "world",
      "interpolation": "quintic",
      "outside": "clamp_position_zero_velocity",
      "provenance": "Baseline MuJoCo mj_forward at task initializer; no integration. robot sha256 ba16d1977581e01edd9b36839eedc9c8e29b4255fb7f94576264cc4ef353899a; frozen for every candidate.",
      "start_m": [
        0.30799999999999994,
        0.0,
        0.15
      ],
      "start_s": 0.0,
      "units": "SI"
    },
    "rule": "All inclusive uniform samples in scoring interval; arithmetic RMS; max <= declared limit. Complete grid required. Terminal error is at execution endpoint.",
    "scoring_interval_s": [
      0.01,
      0.4
    ],
    "velocity_error_max_m_s": 0.13704289525701807
  },
  "accepted_plans": 40,
  "converged_updates": 0,
  "mean_update_s": 30.390883490006672,
  "backend_timings_s": {
    "backend_call": 1216.3148956999648,
    "engine_compile": 0.023313899990171194,
    "prepare_compile": 0.03919460019096732,
    "solve": 1216.013571599964
  }
}
