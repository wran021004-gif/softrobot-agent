# Stage 3.40 first live execution

Session `gvs-stage340-46894a55d13d` completed its autonomous workflow and its own normal, provider-authored final delivery. The eligible candidate executed validly but failed reach and sampled settling. Real-time feasibility was not demonstrated. The controller remains `controller.gvs_nmpc@6.0.0`; no implementation, scientific input, grant, or budget was changed for execution.

The user explicitly authorized the payload, DeepSeek destination, existing authentication credentials, subsequent result context, and paid requests. The exact requested entrypoint performed one prelaunch verification, which passed, then ran the previously unlaunched session. No completed tests or offline diagnostics were repeated. The original prelaunch export and approval-rejection record in `../stage340_bounded_autonomous_20261001` remain unchanged. This is a separate execution export. The live SQLite ledger naturally advanced from its previously recorded prelaunch bytes; old raw-file hashes remain historical records, while this export inventories its final bytes.

## Model decisions and provenance

The provider read the saved diagnosis, built `seed_baseline_cfg` without a solve, requested 12 bounded mathematical evaluations, read the proposals, and selected `proposal_compliant_cfg`: near length 0.15 m, far length 0.11 m, common section scale 0.99, compliant material. Effective facts pass length, section, and nonbaseline material coverage. The selected proposal is an evaluated, historically distinct configuration.

`design.build_proposal` preserved the exact evaluated proposal. `analysis.prepare_candidate` completed its candidate-bound bundle, and `route.record_analysis@2.0.0` registered it with matching optimizer provenance before Route executed the backend. See `candidate_provenance.json` for the selected evaluated row, exact references, coverage and novelty checks, bundle, and registration trace.

The provider received the exact official result in its final request and authored `route.advance` action `finish`. Both typed design and result statements passed exact checks. This was not a scripted or Host-generated delivery. Eleven real requests completed, with no protocol correction events. `provider_execution_trace.json` preserves normalized decisions, receipts, response references, exact advertised tool names, payload sizes and the final response/decision references. The largest request, also the post-backend finish request, was 158,145 serialized bytes against the 200,000-byte cap.

## Official outcomes

| Item | Result |
|---|---|
| Execution | `f9b8c232a576465ab5ef1ca92658faad`, valid and complete |
| Model-authored workflow / multi-category coverage | Passed / passed |
| Target | [0.29, 0.035, 0.19] m |
| Terminal position | [0.27435863249513154, 0.03866455444038071, 0.1988672653048974] m |
| Terminal error / tolerance | 0.018349652058180982 m / 0.01 m; reach failed |
| Sampled settling | Failed: maximum error 0.02416703546281375 m and speed 0.15568023512281687 m/s over 0.05 s |
| Initialization / noninitialization accepted plans | 9 / 26; all 35 plans accepted, zero converged updates |
| Applied tensions | Varied; zero force-bound violation |
| Solver errors | 0 |
| Mean complete update / control period | 11.927797351424982 s / 0.01 s |
| Deadline misses | 35/35; real-time feasibility not demonstrated |
| Measured simulation computation | 419.81199999991804 s |

The all-initialization/constant-tension stop condition did not trigger. The model voluntarily finished after reviewing this valid failed execution; no second backend attempt occurred. Typed results and the original delivery prose are retained without rewriting them.

The delivery prose describes the 0.002 m affine residual bound as “contradicted” by the nonlinear result. That bound applies only within the frozen local model. The discrepancy demonstrates a limitation of using it to predict this execution; it neither invalidates that local bound nor proves further model-led search impossible. World-x degeneracy remains visible. No global optimum, nonlinear performance guarantee, or causal diagnosis follows.

## Comparison and limits

Stage 3.39 terminal error was 0.0321765714687057 m; this run observed 0.018349652058180982 m, a 42.97% reduction. Mean complete-update time changed from 18.404486402862574 s to 11.927797351424982 s. The non-robot execution scope matches by value, including task, controller, backend, model, discretization and seed; the common section scale changed from 1.0 to 0.99. Evaluation comparison identities differ, so this is an observed cross-run comparison, not a formal cross-session ranking or isolated causal effect. No repeated matched experiment was performed. See `historical_observation_comparison.json`.

Actual usage: **11/24 provider attempts, 14/60 tool calls, 12/16 mathematical evaluations, 1/3 backend attempts, 0 workers, and 845.3110000002198/3600 charged seconds**. All frozen limits were respected. Controller behavior was not patched during or after the run.

The next justified action is a separately authorized fixed-design solver study retaining complete warm-start horizons and comparing initialization-selected versus improved feasible updates. This execution shows useful feasible optimizer progress, while reach and braking/settling remain unresolved. No additional study was launched.

## Archive and reproduction

`actual_stage340_audit.json`, `outcome_summary.json`, and `execution_verification.json` separate workflow completion, coverage, execution validity, reach, settling and timing. `actual_local_only_artifacts.json` records final local raw-artifact paths, sizes and SHA-256 hashes. The credential file was used only through the existing authentication loader and is not part of the export or project payload. `actual_manifest.json` records local bytes; `git_blob_sha256_manifest.json` records exact committed Git bytes with the existing verifier. Relevant text uses LF.

The authorized command was:

```powershell
& 'C:/Users/gugugaga/miniconda3/envs/softagent/python.exe' examples/stage340_bounded_autonomous_experiment.py run --output runs/stage340_bounded_autonomous_20261001
```

It is retained for provenance, not for replaying this now-completed session. The entrypoint rejects a second live attempt. Verify the committed export without spending experiment resources:

```powershell
& 'C:/Users/gugugaga/miniconda3/envs/softagent/python.exe' examples/verify_git_blob_manifest.py verify --root evidence/stage340_live_execution_20261001 --output evidence/stage340_live_execution_20261001/git_blob_sha256_manifest.json
```
