# Stage 3.36 proposal-bound continuation

This directory records the zero-provider, zero-backend offline replay and the separately frozen Stage 3.36 continuation. The live command was rejected by the platform approval layer before the Python process started. It was not retried, so there was no provider/model decision and no robot execution.

The production DeepSeek decoder and Host boundary rejected the actual Stage 3.35 mistake, `mathsel_c1_n0p15_f0p11_s0p95_compliant`, as an `optimizer_candidate_id`. The error records that submitted value and both valid proposal IDs. The same path then built `math-compliant-4795c8184616` directly from optimizer artifact `9e408e81...`, verified equality of the complete scientific configuration, imported the retained named mathematical evidence with explicit historical lineage, inherited proposal provenance into the report, and passed the real Route run gate without executing it.

The replay used 0 paid provider requests, 0 new mathematical evaluations, 0 backend executions, 0 NMPC solves, and 0 workers. It made seven local Host tool calls to cover the original failure, success path, conflicting-ID rejection, and altered-configuration rejection. The imported source traversal found all 173 referenced artifacts across the preserved Stage 3.35 store and its three historical source stores; no mathematical artifact was recomputed.

The live freeze is run `gvs-stage336-dc706ed007f2` at implementation commit `72f0512a9c85deebb341ddbd96f8d0624f20b440`. It retained the inherited DeepSeek model/reasoning/token/timeout and correction settings, reduced only the request limit to 16, exposed nine scoped tools, enforced 60 tool calls, zero mathematical evaluations, one backend attempt, zero workers and 3600 charged seconds, and verified all frozen hashes before the attempted launch. The platform rejected launch before process creation, so new-stage use is 0 provider requests, 0 tool calls, 0 mathematical evaluations, 0 backend attempts, 0 workers and 0 charged seconds. Reach, sampled settling and complete-update real-time results are unavailable. This does not complete or alter Stage 3.35.

The platform separately rejected `git push` before its process started. Local commit `72f0512` exists on `feat/gvs-dynamics`, but neither it nor this final live evidence is remotely available. The exact platform messages are retained in `live_launch_rejection.json` and `push_rejection.json`.

Run the focused verification with the required interpreter:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest tests.test_stage335_math_route tests.test_stage336_proposal_bound
```

Reproduce the offline provider-format replay in a fresh output directory:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples\stage336_proposal_bound_continuation.py offline --output runs\stage336_proposal_bound_offline_replay --evidence evidence\stage336_proposal_bound_continuation_20260930
```

Prepare and launch the separately named live continuation only once:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples\stage336_proposal_bound_continuation.py prepare --output runs\stage336_proposal_bound_continuation_20260930_live
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples\stage336_proposal_bound_continuation.py run --output runs\stage336_proposal_bound_continuation_20260930_live --credential-file "$HOME\.codex\.env"
```

`offline_replay.json` is the compact acceptance record, `historical_import_manifest.json` captures original stores, hashes, tool versions, source bindings and named references, `offline_provider_tools.json` is the actual advertised provider inventory, and `sha256_manifest.json` covers the compact files. Raw SQLite databases remain local-only and are identified by absolute path, size and SHA-256 in the import manifest.
