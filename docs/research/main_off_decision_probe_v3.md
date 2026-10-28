# Main-Off schema-feedback and navigation probe v3

## Outcome

A new isolated, authorized provider-only probe used **7 Main and 0 Reporter requests**. The fixed navigation responses reached Main intact. The real native analysis call had malformed candidate and protocol types, and the repaired tool feedback correctly identified both fields. That feedback was produced after the seventh and final authorized Main request, so it was **not delivered to a subsequent model turn**. Whether Main would use it to correct its call is untested. No scientific worker or physical operation ran, and this probe does not establish readiness for a fresh autonomous Study.

The cap was 8 total, 7 Main and 1 Reporter; the unused Reporter allowance was not converted to a Main request. There were no automatic retries. This run uses its own ledger and `runs/research/main-off-saved-c3-v3-20261028`; the earlier v2 ledger remains untouched. The pending fresh Study was not prepared or launched. The existing v2 fixture preserves original C3 ownership, frozen evidence, content hashes and sealed execution manifests; probe-only hypothetical mathematical eligibility grants no scientific permission. The unchanged historical scientific guard still blocks genuine execution because dependency identities differ. See [the v2 report](main_off_decision_probe_v2.md) for source and ownership details.

## Live observations

The first Main request read the root working set and the current result summary. Across the run, six evidence reads were each delivered exactly and completely on the next actual Main wire:

| View and pointer | Delivered UTF-8 bytes | Observation |
|---|---:|---|
| `working_set`, root | 3,753 | Original derived working set was 86,059 bytes; navigational index delivered intact. |
| `summary`, root | 3,845 | Original summary was 66,086 bytes; navigational index delivered intact. |
| `mathematical_capabilities`, `/methods` | 4,005 | Index delivered intact. |
| `fields`, `/acceptance` | 1,036 | Returned original metrics, units and limits. |
| `mathematical_capabilities`, `/methods/short_input_response_v1` | 4,006 | Index delivered intact. |
| `mathematical_capabilities`, `/methods/braking` | 3,854 | Index delivered intact. |

The earlier v2 probe's 6,007- and 6,107-byte indexes had been offloaded to 2,122-byte previews. In this run all six were present exactly in the next provider wire, so the smaller presentation target solved the observed delivery problem for these queries. There were no exact repeated reads. The 4 KiB target is approximate: final metadata made two outputs a few bytes over 4,000. Original evidence and exact scalar access remain unchanged. No new Reporter call was made; the saved historical interpretation remained available in the compact decision context.

Main correctly identified the independent failure: holding speed 0.043009681835387996 m/s exceeded 0.02 m/s, while the 0.0040334275990930235 m position error met 0.01 m. It independently selected `short_input_response_v1` in a settled read-only diagnosis, then the next wire advertised its method-specific native schema. It proposed a test of input response against residual speed. However, its conclusion that the measured improvement was attributable to structure, or that an insufficient local response proves the need for structural change, exceeded the saved evidence: the compared executions changed structure and control, and a local diagnostic does not establish global infeasibility.

Instead of invoking the selected tool, Main submitted another diagnosis with an invented malformed candidate ID. The existing validation reported `string_pattern_mismatch` on `decision.selected_candidate.artifact_id`; Main corrected the candidate identity in the following diagnosis and selected `native_dynamics_v1`. That diagnosis settled and the following actual wire advertised only that method's `research_analysis` operation. The model then submitted a native JSON tool call with candidate as a hex string and protocol as the string `task-local-v2`, instead of the exact object constants. JSON Schema and Pydantic each found the two type errors. The actual production feedback was `SELECTED_ANALYSIS_SCHEMA_MISMATCH` and explicitly said both candidate and protocol must be JSON objects matching the selected constants. The rejected input was not rewritten and no worker was started.

The call also requested `fixed_input_equilibrium`. In an **offline diagnostic only**, substituting the two exact object constants into a copy of the rejected payload exposed the original Pydantic error `NATIVE_ANALYSIS_REQUIRES_EXACT_STATE_OR_FROZEN_INITIALIZATION`. This was not sent, is not a valid model-produced request, and is not scientific preflight. A schema-valid or typed valid live analysis request was not observed. No model turn followed the new schema feedback because the Main cap was reached. The saved response, feedback and exact request remain in the isolated Store.

## Accounted live requests

All requests used the configured `deepseek-flash`, thinking disabled, reasoning effort none, with `max_tokens` absent. Finish reasons were `tool_calls` throughout, with no length truncation. References below identify the original request wire and raw response artifacts in the probe Store.

| # | Request ID | Wire ref | Response ref | Bytes | Prompt | Completion | Cache hit / miss | Seconds |
|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | `r3-request-a3f58a1782d54a1394f37695b895c671` | `10dc182cfda4b3d06277805a7f12328db9e8fdbbab36f30ffb5717f69c6241a3` | `c99e5faf02021323dad2ccc4f680c99a67430c3274e7760504971ee793a54de5` | 40,463 | 11,324 | 237 | 7,808 / 3,516 | 1.281 |
| 2 | `r3-request-e34f65a4238046eb9076b0ddced638d3` | `5b466894b223f279d8525da793194b17f87a93759fee6f85c4d325cc8cbfa999` | `4b83d1531c086a9ce3baaadd111eb9c8972e1f4d7fb80c550db6510cc170c759` | 49,867 | 13,870 | 260 | 7,808 / 6,062 | 1.297 |
| 3 | `r3-request-ac96709629894704851599ff432198a1` | `18c6e78b9a3cc272b8f2efb9fd2581756c57b6d69e1538ace09b442f49aa8d73` | `85cd9818390e95ddc187ac00e406bdf57eca8e721077da5b1b38bcc72aeae499` | 56,412 | 15,602 | 248 | 10,240 / 5,362 | 1.219 |
| 4 | `r3-request-7e96a2af20c64eec89996c787173f10a` | `5c4f2456eed3021d3e8c747d21482ea5b1beb036073e59f0288cda17bc74578f` | `d286eea9154514cad98f65e51d32ffd19d6d5e934219b406d3bb114387554e80` | 65,971 | 18,338 | 1,122 | 12,032 / 6,306 | 6.047 |
| 5 | `r3-request-828c52b0ffd1401cae21d6350f948021` | `5f4179dd905bd877bf8e4d850e5602daf8a2ffd26411e4ed710ba329affd7720` | `fe5b098f50687e56d5247e93f5c6a2dfa61fbb897d0d63c67db2594ad9bf015c` | 79,131 | 22,063 | 929 | 7,808 / 14,255 | 5.172 |
| 6 | `r3-request-e8a0fce793a549759effeb4ae456a95b` | `0201189ab943160de766f89207eba410b3954a177cfb3eef02e1d24163576073` | `709726373c5d8f1d807c7e0e3978d220ffe49a15a40708f40e92cd792555eded` | 84,338 | 23,356 | 997 | 18,432 / 4,924 | 4.953 |
| 7 | `r3-request-df2fc0682b154ad0a3671161ecddc8a3` | `c78ade7531bcebbc12095dc368e945b46aa233be3b40b4e98f16e68402950852` | `c3d13d6b8889c1c68497d3d08451efc819d590a3f190295650db5fc2368b40a1` | 92,715 | 25,429 | 219 | 8,192 / 17,237 | 1.390 |

Total actual usage: 129,982 prompt tokens, 4,012 completion tokens, 133,994 total; cache hit 72,320, cache miss 57,662; sum of request elapsed intervals 21.359 s. Currency cost was not reported. These figures are not a controlled comparison with the prior run, whose request sequence included a Reporter and different decisions.

## Judgment

The navigation delivery fix is verified for the six live reads in this case, and the field-specific schema feedback is verified as a correctly generated live tool result. Its effectiveness in helping the model correct an analysis request is inconclusive because the feedback never reached another Main request. Main's unsupported causal claims and malformed request also remain meaningful decision limitations. A future separately authorized test should reserve a Main turn after any rejection and assess whether the model supplies the exact objects and a scientifically appropriate operating point; a live success cannot be inferred from the present run.
