# Stage 3.37 bounded diagnostics and autonomous design

This stage contains exactly three local NMPC reconstructions, the evidence-driven decision to keep `controller.gvs_nmpc@6.0.0` unchanged, one offline provider-schema/linkage fixture, and one separately frozen paid DeepSeek design experiment.

The local solves use the saved pre-integration measurement, candidate configuration, timestamp, and previous applied input. Missing warm horizons are reconstructed as repeated saved state/input guesses and regenerated through the existing implicit controller preparation. They are labeled “reconstructed from saved state and configuration” and are not bitwise historical replays. Raw plans and traces remain local under `runs/stage337_bounded_nmpc_diagnostics_20261001`; compact findings are sealed here. No MuJoCo trajectory, provider request, sweep, retry, or worker was used for those diagnostics.

`control_decision.json` records outcome B. Reporting retention was improved, but no control policy changed. The paid experiment’s actual model choices, workflow completion, official reach result, sampled settling, complete-update timing, usage, and stopping reason will be added by the packaging step without rewriting earlier archives.
