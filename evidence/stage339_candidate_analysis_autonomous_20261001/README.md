# Candidate-specific analysis bundle and autonomous experiment

Implementation commit `f9b01c052aff423f9c7c5308e64b5867f458e3e4` added `analysis.prepare_candidate@1.0.0`, candidate-specific Route overview status, and `route.record_analysis@2.0.0`. The legacy individual analysis tools, explicit-reference registration, historical binding, readable `deepseek@2.0.0` transport, and `controller.gvs_nmpc@6.0.0` remain available and unchanged.

Focused verification used the real mathematical implementations and no provider, backend, or worker calls. A complete bundle registered successfully and opened the existing run gate; repeating the request reused the exact component artifacts without recomputation. A second build could not register the first build's bundle. The directly affected Stage 3.35/3.36 linkage tests and model-context/protocol checks also passed.

The one paid session was `gvs-stage339-464517014f72`. It used 12 provider attempts, 14 tool calls, 12 new mathematical evaluations, one backend attempt, zero workers, and `1099.0339999997523 s` charged wall time. One bounded protocol correction was consumed. All limits were respected.

The model used the unchanged baseline only as a solve-free mathematical seed, ran the bounded optimizer, and selected `math-compliant-a09627a8a276`, built as `build_compliant_a09627a8a276`: near `0.15 m`, far `0.11 m`, section scale `1.0`, compliant material scenario. Compliant and stiff tied on the primary controller-start local residual (`0.0019999999999999463 m`, `0.2` of tolerance); compliant had lower secondary normalized witness energy (`9.820930992617149e-05` versus `0.00019534778694341192`). The world-x control row was zero, so this remained an advisory local proxy.

The selected build's bundle `ddaa0f450792afa9f54e274f4ad5b23b7f0209a6957abd0c2f0eab2d26e1906a` completed all four components and registered successfully as report `f6c02af80038e7f54a8608b168508e4c2c52e1120874508604910085c50fb45e`. The existing run prerequisite check passed.

Backend execution, official evaluation, and the control profile all completed. The execution was valid and complete, with zero solver errors and zero force-bound violation, but official reach failed: terminal error `0.0321765714687057 m` against the `0.01 m` tolerance (`task_accepted=false`). Terminal position was `[0.26333332090927003, 0.032014264798555285, 0.20775683989508284] m`, and terminal tip speed was `0.1442085121981818 m/s`. Sampled settling failed (`0.032776618854796144 m` maximum error and `0.17072241795880597 m/s` maximum speed over `0.05 s`). Complete-update real-time feasibility was not demonstrated: 35/35 deadline misses and `18.404486402862574 s` mean complete update versus a `0.01 s` control period.

The model-selected design did not meet the declared multi-category coverage condition because section scale remained `1.0`; `candidate_facts.multi_category_coverage` is false. The model's statement that it was a covered design was therefore incorrect, although it was fresh relative to the supplied historical configurations.

The session did not author a finish. After the backend result, required model context measured `158164` bytes before optional compaction and remained above the frozen `150000`-byte limit, so the Host stopped exactly with `CONTEXT_LIMIT_REQUIRED_STATE_TOO_LARGE: narrow tools or raise explicit byte limit`. No manual finish, resume under changed dependencies, replacement session, budget reset, or unrecorded retry was performed. A follow-up compact-status change reduced the same post-run payload to `148843` bytes; it was not used to alter or resume this sealed experiment.

Exact hashes for compact evidence are in `actual_manifest.json`. The large SQLite ledger, provider payload, trajectory, controller observations, and NMPC updates remain local; their absolute paths, sizes, and SHA-256 hashes are in `actual_local_only_artifacts.json`.

Recommended next action: before any separately authorized future experiment, make the multi-category coverage requirement a deterministic pre-run check, then use the compacted Route status so the model retains enough context to author its own finish.
