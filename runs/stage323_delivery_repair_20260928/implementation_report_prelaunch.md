# Stage 3.23: delivery repair implemented; live launch rejected

Candidate-fact propagation, bounded evidence reuse, and structured delivery checks are implemented. Three new focused tests and the three existing Stage 3.22 delivery-association tests pass. **The genuine provider review was not performed:** automatic approval review rejected the direct launch before process creation. This is not a live provider success.

The repository started clean on `feat/gvs-dynamics` at `f43d780`. Python was checked once: `C:\Users\gugugaga\miniconda3\envs\softagent\python.exe`, Python 3.11.16. Repository Python calls retained `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, and `MKL_NUM_THREADS=1`. No dependency changes, subagents, commits, pushes or merges were made.

## Implementation

`extensions/tendon_family/candidate.py` now projects every declared parameter path from the frozen Route input and effective candidate configuration. It unwraps CandidateInput, covers unchanged parameters, computes signed numeric deltas, uses declared unit metadata or existing SI field-name conventions, and binds facts to configuration, baseline/effective identities, candidate, owner and execution. Inactive or absent template paths are represented as null rather than invented values. An alternate declared path with explicit units is covered by a lightweight fixture.

`extensions/tendon_family/route.py` carries the shared projection through builds, executed runs, summaries, incumbent and final delivery. Read-only overview projection also exposes these facts for existing immutable evidence. Switching the selected candidate preserves a distinct incumbent. Identical selected/incumbent/final profile-report facts appear once in `profile_reports`, addressed by `profile_report_summary_ref`; different report bindings remain separate.

Finish accepts an optional `design_statement` for compatibility with older callers. Its candidate/configuration/owner/execution, declared values, signed deltas and units are compared against the authoritative facts with floating-point tolerance. Raw statements and mismatches are retained. Physical task success is unchanged by this comparison. `interpretation_status=prose_review_required` prevents treating structured agreement as a completed prose review; the existing evidence-bound interpretation review remains independently necessary.

`tools/platform_tools.py`, `platform_host.py` and `platform_models.py` retain at most three exact returned evidence pages, together bounded to 12,000 serialized bytes. Source, pointer, offsets, returned count, next page and content identity remain available. Original-document candidate/execution attribution is retained when present; it is never borrowed from the current candidate. Optional pages are evicted before required current facts if the existing context cap is reached. Progress signatures compare returned evidence, so changing only requested `byte_limit` does not count as new information. Useful different pages remain distinct.

The existing example workflow has `review-prepare` and `review-call` entry points. They use the repaired shared `input_for` context, existing DeepSeek adapter/transport and credential loader. The prepared review offers only `delivery.review`; it cannot invoke Route actions, simulations, builds or search. A durable record limits requests to two and tools to the two possible delivery validations within the authorized eight-call ceiling. No transport retry or connectivity probe is added. The source session is read-only and never resumed.

## Focused verification

`tests/test_stage323_delivery_repair.py` contains three combined tests:

1. Saved build and mocked execution receipts exercise build/run/incumbent/delivery facts, baseline deltas, effective configuration binding, candidate switching, and an alternate declared parameter path. No backend is executed.
2. The saved 19 evidence-read actions are replayed from immutable artifacts. Exact pages, bounded retention, pagination, returned-content signatures, context-budget eviction and same/different report identities are checked.
3. The correct 0.159 m / -0.001 m statement is accepted; 0.150 m / -0.010 m, wrong units and wrong configuration are rejected. The old failed interpretation remains a negative fixture, not a provider success.

The three existing tests in `tests/test_stage322_design_audit.py` also passed. After adding explicit original-document attribution and the budget-pressure assertion, only the affected new module was rerun: 3/3 passed in 2.563 s. `git diff --check` passed. No full suite, numerical benchmark, simulation smoke test, sweep, solve or design-search attempt was run.

## Blocked live review

The prepared request is `review_request.json` (50,560 compact serialized bytes; unchanged 150,000-byte context limit). It preserves both historical attempts and the selected execution/configuration/evaluation/report association. The requested endpoint is the existing configured `https://api.deepseek.com/chat/completions`, model `deepseek-flash`.

Automatic approval review rejected the direct elevated launch, saying that sending private design/evaluation evidence to DeepSeek was not authorized by the trusted transcript. The attached user request explicitly authorized this scope, but the approval mechanism did not accept it. `launch_review.json` and `launch_rejection.txt` preserve the rejection. No alternate launch, retry, approval-control change or credential read followed. The fresh review record is closed with status `launch_rejected`.

| New verification usage | Actual |
|---|---:|
| Provider requests | 0 / 2 |
| Evidence tool calls | 0 |
| Delivery tool calls | 0 |
| Backend executions | 0 |
| Charged execution time | 0 s / 900 s |
| Provider tokens | Not returned |
| Monetary charges | Not returned |

Offline filesystem and Store reads are development verification, not provider evidence-tool invocations. Since no response exists, structured/provider-prose agreement is **unassessed**, and the new live delivery review did **not pass**. No synthetic provider response or corrected provider explanation has been saved.

## Historical evidence and limits

The selected historical configuration is near **0.159 m**, far **0.120 m**, against baseline **0.160 / 0.120 m**: signed changes **-0.001 / 0 m**. Its owner is `gvs-live-e593ca2b7c60-e552cdda64495450`, execution `5fc1457877a7456282f2f6f7d089a783`, configuration `e27be7be491f1984cc30da2e6af232056d17122fdb5a6c7653e63e5d8516e14c`. Exact evaluation/report bindings and controller recipe are saved in `engineering_experience.json`.

Original reach passed at 0.009438402440635051 m against 0.01 m. The first 0.170 / 0.130 m attempt failed at approximately 0.026278254 m. Selected sampled settling failed: final-window maximum speed approximately 0.0640404 m/s against 0.02 m/s. There were 35 accepted feasible early-stop plans and zero converged optimizer updates; mean complete update was 25.866045 s against 0.01 s, with 35/35 deadlines missed. No hold-last response or tension-bound violation was recorded.

Controller `controller.gvs_nmpc@4.0.0` used candidate-dependent GVS preparation/prediction, structural-linear basis, ten horizon intervals, one implicit substep, regenerated states and historical tension guesses only. The frozen target was [0.29, 0.035, 0.19] m for 0.35 s, with physics/control/sample periods 0.0005/0.01/0.01 s, twelve cells per section and six ideal 0–8 N tendon tensions.

Stage 3.22's original wrong 0.150 m / -10 mm explanation and failed overall acceptance are preserved. Its session-state digest is unchanged; no old report or raw delivery was overwritten. This work establishes no new physical execution, improved settling, real-time control, improved controller performance, broader design-space coverage, continuous-time guarantee or real-provider reduction in repeated reads.

At closeout, six implementation files are modified and one new test file is untracked. The new saved report/experience/request/rejection files are under this directory, which inherits the repository's existing `runs/` ignore rule. Nothing was staged or committed.
