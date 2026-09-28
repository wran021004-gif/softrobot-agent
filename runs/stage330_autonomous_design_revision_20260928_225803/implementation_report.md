# Stage 3.30 outcome

The reporting/context implementation is complete and focused checks pass. The
genuine DeepSeek experiment ran, but **autonomous revision and fresh evaluation did
not complete**. No revised design was built or executed. Both provider responses
exhausted the frozen 16,384-token completion limit entirely on reasoning, with
empty message content and no tool call. The existing single length-correction
attempt also failed; the loop stopped with `MODEL_LENGTH_RETRY_FAILED`. This is a
provider protocol failure, not a measured physical-design failure or project
budget exhaustion. No controller change, new session, or extra retry was used to
manufacture a result.

## Implementation and verification

Implementation commit: `24a23c5`.

- `delivery_facts.py`: typed free-reach projection and task dispatcher; strict
  statement comparison. Existing tracking behavior is retained.
- `route.py`: task-specific result guidance; historical evidence reference;
  current evaluation/remaining-execution counts; automatic historical comparisons;
  reject identical historical design before execution; correction feedback on
  mismatched reach delivery. Candidate design-statement checks remain independent.
- Reporting, diagnosis, comparison and delivery use the same reach projection.
  World signed error is actual measured tip minus target. Settling, accepted
  initialization plans, convergence, tendon ranges, prediction alignment and
  computation are explicit. Reports retain detailed evidence references.
- `historical_failure.py`: small trusted binding for the original failed live
  case, without importing sessions or bypassing execution ownership. It compares
  scientific conditions by value and separates reporting-source hashes.
- `examples/gvs_revision_input.py` derives the new input from the old frozen
  baseline. `examples/gvs_nmpc_route_experiment.py --historical-failure` uses the
  existing launcher, credential loader, provider adapter, transport and loop.

Six unique focused checks passed: three Stage 3.30 tests, Stage 3.25 tracking
compatibility, Stage 3.23 evidence retention/context, and Stage 3.29 saved one-step
alignment. Initial local test failures exposed a Windows temporary-directory/
SQLite cleanup issue and missing fields in older pre-multiphysics reports; both
were fixed before freezing, and affected checks passed. No full suite, numerical
sweep, deterministic plumbing campaign, or optimization solve was run.

## Historical evidence and scientific compatibility

This was **autonomous design revision from supplied historical failure evidence**.
The developer supplied `build_covered_stiff_long`; DeepSeek did not independently
generate that historical failure in this session.

| Binding | Original identity |
|---|---|
| Session | `gvs-live-81630b95545d` |
| Execution owner | `gvs-live-81630b95545d-b77192b4ed2f3834` |
| Execution | `6d018c9f0e8a40989eb8e42a4ac4d941` |
| Configuration | `dd52a46de78edd4ac5ce620dd3677a27c1c1f2d88f8fe8c227e910bebffbcfeb` |
| Evaluation | `e54ce8f59fd86dde35e930aecad98fd4efb00baa7a5a418bfeacd831e1978c88` |
| Report | `7de778386ce7b7fa3aff4b3226a9a14df8fe013bd4dbc49407e500f7fb6913d2` |

The saved configuration confirms near/far lengths 0.170/0.130 m, section scale
1.05 and stiff material. The complete valid execution failed the original reach
task at 0.038874362971136237 m terminal error. Its measured terminal world tip is
`[0.3178831617269221, 0.03606142715008873, 0.16293306886758294]` m. Signed error is
`[+0.027883161726922123, +0.0010614271500887298, -0.027066931132417066]` m.
Terminal speed is 0.23423393816834698 m/s; sampled settling failed. It had 35
accepted, initialization-selected plans; zero accepted non-initialization plans;
zero converged updates; constant per-tendon tensions; zero force-bound violations;
and 35 aligned one-step comparisons. These facts do not establish static equilibrium
or failure of the whole authorized design space.

Compatibility checks pass for the complete frozen task/evaluator, controller
recipe, execution mode, initialization, discretization, basis, baseline physical
conditions and authorized design expansion. The original source commit was
`fe714ad0f2928452fa98b26970318976eaf5e685`; the reporting implementation differs.
Historical session state and final output remain unchanged. No successful plumbing
candidate, result, or parameter hint was included in the provider payload.

## Genuine experiment and acceptance

Fresh session: `gvs-live-48f6184309c0`. Model and destination remain
`deepseek-flash` through `https://api.deepseek.com`; thinking and the 16,384-token
completion limit remain as configured for Stage 3.29. The initial request was
55,615 serialized bytes. The source and scientific input remained unchanged during
the live run.

The automatic launch review initially did not recognize the authorization in the
user-supplied attachment. Read-only checks established the explicit paid-request,
destination and payload authorization. Review then approved the same launch; no
workaround was used, and that rejected launch sent no request.

| Acceptance item | Outcome |
|---|---|
| Reach tools/context/delivery integration | Pass in focused saved-evidence checks; live delivery unexercised |
| Autonomous revision and fresh evaluation | Not achieved: no tool call, build, or evaluation |
| Covered revised design passes unchanged reach task | Not achieved: no tested revised candidate |
| Structured delivery and provider explanation accurate | Not delivered; cannot accept |

Actual LLM revisions and measured revised results: **none**. Truncated internal
reasoning is not a declared candidate or provider delivery. There is no provider
final explanation to replace or audit as successful; the Host's terminal record is
explicitly incomplete. Empty revised-candidate/comparison exports preserve that
distinction.

## Resources and retained evidence

| Resource | Used | Ceiling |
|---|---:|---:|
| Genuine provider requests, including failed decoding | 2 | 32 |
| Platform tool calls | 0 | 80 |
| Fresh backend attempts | 0 | 3 |
| Workers/subagents | 0 | 0 |
| Charged project wall time | 156.735 s | 10,800 s |

Provider-reported token use: 29,936 prompt tokens, 32,768 completion tokens (all
reasoning), 62,704 total. The historical execution was not recharged. Monetary
cost was not reported and is not estimated. Thirty requests and three executions
remained, but the frozen loop's bounded length-correction policy had stopped; the
project ceilings are not usage targets.

`evidence_index.json` links the frozen input/source identity, compact prior case,
unmodified raw provider requests/responses, all receipts and usage, empty revised
candidate/comparison lists, and factual acceptance audit. The original fresh
database remains at `live/platform.sqlite`; no historical database or unrelated
tree was copied. No credentials are included in archived evidence.

The next justified development step is first-action response budgeting, using
these captured truncations, followed by a separately frozen protocol experiment
with the same scientific conditions. This run provides no basis for controller
tuning, new design variables, a numerical sweep, or claims about revised physical
performance. The Stage 3.30 repair objective remains incomplete.

Only local commits were made. Nothing was pushed or merged.
