# Stage 3.37 bounded diagnostics and autonomous design

## Archive repair

The Stage 3.36 archive now records the exact diagnosis invocation, interpreter, arguments, inputs, execution IDs, and output path. Its original Windows working-tree `sha256_manifest.json` is unchanged. New text evidence is UTF-8/LF in Git, and `git_blob_sha256_manifest.json` was verified against 21 exact blobs at commit `ac713d7`. `CURRENT_STATUS.md` separates implementation, LLM behavior, manual execution, and robot performance.

## Three reconstructed diagnostics

Exactly three local NMPC updates were run: current failed design at 0.00 s and 0.23 s, and historical passing design at 0.23 s. Each used the saved pre-integration measurement, configuration, timestamp, previous applied input, original recipe, and existing implicit warm-state regeneration. They are reconstructed from saved state and configuration, not bitwise historical replays because full warm horizons were not retained.

All three feasible initializations had zero initial-state and variable-bound residual and dynamics residual below `1e-5`. Lower objectives appeared only on dynamics-infeasible iterates. At current 0.23 s, objective fell from `173.34685198170365` to `4.2515980605350725`, but returned dynamics violation was `0.002935000121501684`; the least-infeasible noninitialization checkpoint was `0.0003215983575130185`. Exact reverse-mode Jacobian work dominated the approximately 15 s numerical solves. See `diagnostic_summary.json`; full plans and traces remain local and hashed in `local_only_diagnostic_artifacts.json`.

## Control decision

Outcome B was selected: keep `controller.gvs_nmpc@6.0.0` unchanged. No initialization, weight, integration, tolerance, recovery, or stopping policy changed, and no paired solves were authorized or needed. The evidence isolates delivery rejection to dynamics equality residuals but does not isolate warm-start quality, nonlinear conditioning, scaling interactions, or finite-budget effects, and does not prove design infeasibility.

## Autonomous DeepSeek experiment

The provider-format fixture passed automatic proposal binding and the real execution gate with zero provider/backend calls; its scripted proposal was not a live-model choice. A fresh paid session `gvs-stage337-be4419cee8fd` was then frozen at commit `cd8860b07fbd36d7ecbe7ebe65591fe7aaf5d19b` and passed every prelaunch check.

The model read the diagnostic evidence, inspected the Route, and read prior evidence. It stated an intent to start near the historical best region without duplicating a historical case, but it never supplied actual parameter values, built a candidate, ran mathematics, or spent a backend attempt. Three successive provider responses used unregistered function names during construction/recovery. The Host stopped at the configured consecutive protocol-correction limit. The session was not relaunched or manually completed.

| Candidate | Near / far (m) | Scale | Material | Official reach | Settling | Complete-update timing |
|---|---:|---:|---|---|---|---|
| None built | -- | -- | -- | Unavailable | Unavailable | Unavailable |

Autonomous workflow completion is false: there is no Route node, design statement, evaluation, profile report, or provider-authored finish. Usage was 8 provider attempts, 3 tool calls, 0 mathematical evaluations, 0 backend attempts, 0 workers, and `330.01399999973364` charged seconds. The exact stop reason was `MODEL_PROTOCOL_CORRECTION_CONSECUTIVE_LIMIT` following `INVALID_TOOL_CALL_ENVELOPE`. Remaining resources were not a stopping cause.

Recommended next action: in a separately authorized future session, correct the provider's hashed tool-name reliability (or expose stable registered names) and resume with a fresh grant; do not infer a design or robot result from this pre-build protocol failure.
