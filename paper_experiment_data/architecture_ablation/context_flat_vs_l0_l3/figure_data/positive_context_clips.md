# PHS_C035: observed cost–quality tradeoff

No qualifying Clip A (quality tie), Clip B (quality improvement), or on-demand L1–L3 reading clip was observed. Do not present this pair as overall quality preservation. Both conditions made zero extra evidence reads; this does not test selective read effectiveness or repeated-read avoidance.

## Limited positive observation: evidence boundaries retained with a smaller delivered input

- Provider actual first accepted input: Flat 675,802; Hierarchical 78,785; reduction 88.3420%.
- Accepted cumulative input is the same in this one-inference-per-condition pair. These are not two independent findings.
- Blind mean: Flat 4.0; Hierarchical 3.8. Hierarchical minus Flat = -0.2.
- Evidence consistency, limitation recognition, actionability and reference accuracy are 4/4 for both. Research decision quality is 4 for Flat and 3 for Hierarchical. The retained boundary below illustrates only that narrower strength.

Hierarchical original (`sessions/fec86d8b-3f0d-4bb3-b255-cc50fc5ba8be/result.json`, `/decision/interpretation`):

> hard-equilibrium mathematics does not transfer to dynamic success, and no independent full ten-case acceptance exists.

Flat original (`sessions/2b730049-978d-4824-939e-d961c9bfa617/result.json`, `/decision/interpretation`):

> At 2e-4, drift and qvel improved further, but tip/monitor speeds did not and static balance regressed to 0.00371 N m.

The reviewer favored Flat because it uses the already observed non-monotone trend to propose an untested intermediate candidate. Hierarchical instead proposes a sound but partly redundant saved-response comparison. No proposed action was executed.

## Token accounting boundary

An initial Hierarchical HTTP400 rejected medium reasoning with function tools. Both successful conditions then used reasoning=none. This one failed send remains in the raw request count: Flat 1 send, Hierarchical 2 sends (1 accepted each). Its usage is absent, not zero.

Accepted inference usage reduction is 88.3420%. **Strict all-send actual cumulative reduction is unavailable.** Full-wire generic-proxy totals including the rejected send are Flat 696,894 and Hierarchical 161,772, reduction 76.7867%. The proxy is not verified for this model and is supplemental; it must not be merged with actual usage.

## Traceable references

- Main decisions: `context_replay_results.jsonl`, condition/session fields, original `/decision/interpretation`; session raw responses preserve exact function arguments.
- Blind scores: `blind_review/independent_model_review.json`, `/review/evaluations/0` (anonymous A) and `/review/evaluations/1` (anonymous B); map opened after review in `decision_scores.csv`.
- Shared corpus: `information_manifest.json` resolves C031/C032 (F3), C034/C035 (F4) and CURRENT_CANDIDATE to unchanged source files. C035 `/observation/qualification_diagnosis` contains loaded qualification and incomplete task scope; detailed F3/F4 metrics are in C032/C035 observations.
- Token sources: `token_request_accounting.json` links every exact wire and original response. No length/read-count/reference-count bonus was used.

This is one engineering-Core-origin checkpoint with two fresh Main decisions, not a recovered historical Main conversation. Later FULL acceptance is provenance only, never decision or reviewer input. No robot success-rate result or statistical significance is claimed.
