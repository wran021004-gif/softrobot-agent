# Public GVS tracking result

Program-generated factual result:

```json
{
  "candidate": {
    "candidate_id": "cand_near165",
    "configuration": {
      "artifact_id": "ad97dadde9a7422ea64f447428ad87bb8a48ae5c33e93576c4a7ac1e4a54e1d7",
      "media_type": "application/json"
    },
    "frozen_baseline_identity": "2b34ed0fa887d28068486e26d82d9404b128d4666f7bc9796fe9e92c7cd2a392",
    "effective_identity": "9a2d28258575201ea2fa4887fcc258614c100b7a887fb3a94c81bb066a88a6d8",
    "owner_run_id": "gvs-live-6971718592bc-0e6ec10af4ba158f",
    "execution_id": "842ae454986e4a41b9dbaca5a57fb40a",
    "parameters": [
      {
        "path": "components/far/length_m",
        "baseline_value": 0.12,
        "effective_value": 0.12,
        "baseline_delta": 0.0,
        "unit": "m"
      },
      {
        "path": "components/near/length_m",
        "baseline_value": 0.16,
        "effective_value": 0.165,
        "baseline_delta": 0.0050000000000000044,
        "unit": "m"
      }
    ]
  },
  "configuration": {
    "artifact_id": "ad97dadde9a7422ea64f447428ad87bb8a48ae5c33e93576c4a7ac1e4a54e1d7",
    "media_type": "application/json"
  },
  "execution_id": "842ae454986e4a41b9dbaca5a57fb40a",
  "simulation": {
    "artifact_id": "2358194bdf0a073f789b3234d84e9015700669042737a5b24c8832a0edc56062",
    "media_type": "application/json"
  },
  "evaluation": {
    "artifact_id": "60db46fb085bbeb99f8c3763873bc2062a00fd42281e819284a91abe71c43286",
    "media_type": "application/json"
  },
  "report": {
    "execution_id": "842ae454986e4a41b9dbaca5a57fb40a",
    "owner_run_id": "gvs-live-6971718592bc-0e6ec10af4ba158f",
    "reference": {
      "artifact_id": "8bc193ac382b0333744bd678ef7112cfd97e80dfb3182afd190ca3331a03487a",
      "media_type": "application/json"
    },
    "request_id": "single-profile-report"
  },
  "task_accepted": true,
  "valid_complete_execution": true,
  "maximum_tracking_error_m": 0.00719823810484788,
  "rms_tracking_error_m": 0.006001923582692169,
  "declared_limit_m": 0.01,
  "control_updates": 40,
  "accepted_feasible_plans": 40,
  "converged_updates": 0,
  "deadline_misses": 40,
  "control_period_s": 0.01,
  "simulated_duration_s": 0.4,
  "measured_computation_s": 1122.344000000041,
  "mean_complete_update_s": 27.929852807486895,
  "real_time_demonstrated": false
}
```

Sampled simulation acceptance; provider reasoning and its review are separate.
