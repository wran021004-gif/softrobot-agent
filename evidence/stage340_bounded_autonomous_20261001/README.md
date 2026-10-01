# Stage 3.40: prepared; live launch blocked

Delivery/context, scoped coverage, archive fixes, and the bounded solver diagnosis are complete. The implementation was frozen at `a882854c097424eb65a5a24302ea35661416a025` for session `gvs-stage340-46894a55d13d`. Automatic approval review rejected the live launch before process creation. No provider request, new mathematical design evaluation, backend attempt, or worker ran in this session. The model has not selected a design or authored a delivery; there are no new robot outcomes or supported performance improvements. See `launch_block.json` and `completion_report.json`.

The rejection states that sending repository/project context using credentials to `https://api.deepseek.com` lacks explicit trusted-transcript authorization for the specific payload and destination. The action was not retried or bypassed. The next action is explicit approval for that frozen payload and destination. The original session remains `created`; no manual finish, replacement experiment, resumed frozen session, or budget reset occurred.

## Changes and verification

The new experiment requires an effective near/far length change of at least 0.001 m from 0.16/0.12 m, common section change of at least 0.01 from 1.0, and compliant/stiff material. This is checked from candidate facts before backend reservation, displayed in context, and scoped by an opt-in Route policy. The unchanged baseline remains a solve-free seed. Direct parent simulation and alternate execution paths cannot bypass the experiment's proposal-build/run path.

The existing bounded coordinate search projects its **starting point before evaluation** into the covered domain, evaluates exact configurations, and returns only covered, historically distinct evaluated proposals. It does not alter returned proposal values after evaluation. Legacy search behavior remains available without the policy. The straight-start world-x degeneracy and advisory ranking limitations remain visible. A valid run selecting initialization throughout with constant tensions blocks further backend retries while leaving normal model-authored finish available.

The disposable saved-fact fixture serialized a 155,444-byte post-backend request against the frozen 200,000-byte limit, leaving 44,556 bytes of headroom. The registered finish operation preserved exact candidate/result facts, execution ownership and analysis references. This is explicitly an offline scripted fixture, not a live model-authored finish. Two focused coverage tests passed, and the existing bundle test also passed. Targeted compilation passed. A test run overlapping implementation edits correctly rejected changed dependencies; the final coverage tests ran after stabilization and passed.

Stage 3.39 `actual_manifest.json` remains its original local-byte record. Its added `git_blob_sha256_manifest.json` records exact committed Git bytes with the existing verifier. Relevant Stage 3.39/3.40 evidence has LF attributes, and the shared JSON evidence writer explicitly writes LF. Historical scientific records were not regenerated.

## Solver diagnosis and controller decision

The representative Stage 3.37 reconstructed late failure at 0.23 s already retained sufficient vectors and traces. Five retained vectors were independently re-evaluated against the fixed expression: their objectives and residuals matched. No new local NMPC solve was needed; no variant was tested or adopted. The controller remains `controller.gvs_nmpc@6.0.0`.

The lower objective is accompanied by dynamics violations. The dominant equations are generalized-force balances for `near.kappa_y_node_1`: `dynamics_8_13` at the least-infeasible checkpoint and `dynamics_0_13` at return. Initial-state and variable-bound residuals remain zero. Residuals are nonmonotonic: iteration 5 reaches 0.000321598, later residuals rise, and the final four iterations improve to 0.00293500, still 293.5 times the 1e-5 acceptance limit. That returned scaled force residual means a physical defect of 2.935e-6 N*m^2/rad against 1e-8. Decision scaling, residual scaling, discretization, solver tolerance, and selection policy are separate in `diagnosis.json`.

Exact reverse-AD Jacobians consume about 93% of numerical solve time. The saved local update takes about 29.24 s including workspace construction: warm preparation 8.99 s, solver construction 4.32 s, numerical solve 15.70 s, plus checks and validation. The feasible-return timer excludes preparation/construction/validation; it is not a complete-update budget. This locates cost without isolating a derivative, scaling, or warm-start remedy. A feasible start does not imply easy useful improvement. Full historical warm horizons were not retained, so these remain reconstructed cases, not historical reproductions.

## Freeze and evidence

`scientific_inheritance_check.json` verifies equality with Stage 3.39 for robot, task, controller, backend, model, discretization, initialization-related fields, candidate builder, editable inputs and seed. Only `context_bytes` changes in provider configuration. Existing output/timeout/recovery limits are preserved. Limits are 24 provider attempts, 60 tool calls, 16 mathematical design evaluations, 3 backend attempts, zero workers and 3600 charged seconds.

Before freezing, preparation found one missing historical `detail_export`. The same entirely unlaunched session was repaired with a recorded event; all counters remained zero. `preparation_repair.json` records this. No frozen session was migrated. Prelaunch verification subsequently passed all checks.

`actual_*` files describe the prepared session honestly. In particular, its Host stop reason is null because the external approval reviewer blocked process creation; `launch_block.json` records that external stop reason. `actual_local_only_artifacts.json` inventories absolute local paths, sizes and hashes for the ledger, frozen inputs, payloads, fixture and retained diagnostic data. None is claimed remotely available. The Git-byte manifest covers the committed compact evidence separately from local raw-byte hashes.

Reproduction uses `C:\Users\gugugaga\miniconda3\envs\softagent\python.exe` with `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`:

```powershell
& $python -m unittest tests.test_stage340_coverage.Stage340CoverageTests
& $python examples/stage340_offline_finish_fixture.py
& $python examples/stage340_saved_solver_diagnosis.py
& $python examples/verify_git_blob_manifest.py verify --root evidence/stage339_candidate_analysis_autonomous_20261001 --output evidence/stage339_candidate_analysis_autonomous_20261001/git_blob_sha256_manifest.json
& $python examples/verify_git_blob_manifest.py verify --root evidence/stage340_bounded_autonomous_20261001 --output evidence/stage340_bounded_autonomous_20261001/git_blob_sha256_manifest.json
```

The first three commands create new offline verification outputs; use a separate checkout when preserving this sealed export. The blocked live command is retained in `launch_block.json` for review, not as an instruction to retry without approval. Credentials use the existing loader and are not included in evidence.
