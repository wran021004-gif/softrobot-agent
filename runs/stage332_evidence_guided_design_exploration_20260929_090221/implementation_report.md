# Stage 3.32 implementation and blocked launch

Implementation and saved-evidence verification are complete. The genuine design
experiment is blocked on external-provider transfer approval. No fresh candidate
has been selected, built, simulated, evaluated or delivered. This is not a design
failure, voluntary model stop, or evidence of infeasibility.

## Implementation

Local implementation commit: `d014e0f`. Starting tree was clean at `838a7d1`.
The existing historical binding now accepts the three explicitly selected Stage
3.31 evaluated cases. Scientific compatibility remains value-based; reporting
source hashes need not match historical source hashes. Original session,
configuration, candidate, execution, report and evaluation identities are retained.
Only attributed detail exports are added to the new store. No historical owner is
imported and no historical execution is rerun or charged. Original provider
conclusions and the deterministic plumbing candidate are not included.

Normal route context now shows tested values and constants separately for prior
and fresh samples, baseline deltas, comparisons against each historical case,
explicit build-parent changes when applicable, best measured error and remaining
resources. Both lengths were constant at 0.170/0.130 m; scales were 1.05, 1.01 and
1.02; scenarios were compliant and stiff. Coverage is not exploration coverage.

Reports and compact context include sampled minimum error/time, terminal error,
signed world position error and speed, and final-0.05-second error change. This is
last sampled error minus first sampled error over [0.30, 0.35] s. Earlier entry into
tolerance remains diagnostic and does not change endpoint acceptance or settling.

The brief makes free-reach analysis optional and purposeful, requires a meaningful
fresh length change chosen by the LLM, prioritizes a covered passing design, and
distinguishes a pass, insufficient budget, concrete blocker, or voluntary stop.
Tracking's existing analysis prerequisite remains intact. No controller, evaluator,
physical condition, authorized design decision or model request setting was tuned.

## Focused verification

`python -m unittest tests.test_stage332_exploration -v` passed. The combined check
validated all three original bindings and facts, unchanged source state/accounting,
no ownership import, zero preparation charges, unchanged lengths, saved trajectory
measurements, fresh report regeneration, task/space/controller compatibility,
and the prepared high-effort DeepSeek payload. One read-only Stage 3.31 replay
also exercised the new fresh-sample history and historical-comparison paths.
No full suite, simulation, plumbing campaign, sweep or controller benchmark ran.

During verification, a temporary-directory cleanup permission issue was avoided
by opening the existing live source without a temporary directory. The test's
settling argument and diagnostic nominal-duration alignment were corrected before
freeze. No defect was found after an actual design action; no live repair occurred.

| Prior candidate | Minimum error (m) | Time (s) | Terminal error (m) | Terminal speed (m/s) | Late error change (m) |
|---|---:|---:|---:|---:|---:|
| rev_compliant_max | 0.00591307134337357 | 0.160 | 0.011787523596227 | 0.0350492254656208 | 0.000714863639718791 |
| c2_stiff_scale1p01 | 0.0270394344880664 | 0.350 | 0.0270394344880664 | 0.240157198101351 | -0.00650626574987603 |
| c3_compliant_scale1p02 | 0.00534830142219851 | 0.170 | 0.012342134134044 | 0.0416443683896788 | 0.00135196183825557 |

The two compliant samples entered tolerance earlier but finished outside it. All
three historical runs failed the original 0.01 m endpoint criterion.

## Launch, accounting and blocker

Initial session `gvs-live-06029f79f8b5` failed with `DEEPSEEK_NETWORK_ERROR` before
receiving a provider response or executing a tool. Its sealed ledger conservatively
charges one model request and 2.078 seconds. Raw request/failure evidence is retained.
The Host sealed an incomplete terminal result, so it cannot be reopened.

Replacement `gvs-live-b8f4ab5f17f2` is prepared and frozen, with the failed charge
subtracted: 63 model requests, 160 tools, 6 backend attempts, 21597.922 seconds,
zero workers. Source and scientific settings are unchanged. It has no calls.
Normal requests remain deepseek-flash at https://api.deepseek.com, thinking enabled,
high effort, 65536 max tokens, 600-second timeout. The unused one-time recovery
remains 131072 tokens / 900 seconds. The 1800-second backend reservation remains.

Automatic approval review rejected the network-enabled launch twice. The second
review did not accept the authorization in the attached request/tool-generated
excerpts as trusted user-message authorization for transmitting repository-derived
task/configuration/history to DeepSeek. A direct authorization question is pending.
No workaround or substitute provider was used. No rejection itself sent a request.

| Resource | Used | Remaining |
|---|---:|---:|
| Charged provider attempts | 1 | 63 |
| Platform tool calls | 0 | 160 |
| Fresh backend attempts | 0 | 6 |
| Charged project seconds | 2.078 | 21597.922 |
| Workers/subagents | 0 | 0 |

No provider token receipt or currency charge is available. No new candidates or
terminal errors exist. Evidence integration passed; fresh exploration, autonomous
workflow and fresh covered task success are unassessed because execution is blocked.
There is no provider-authored delivery or stopping explanation to audit.

## Retained evidence and continuation

`evidence_index.json` maps inputs, source identity, original bindings, compact
summaries, raw records, both compressed ledgers, accounting and the approval blocker.
`resume_experiment.ps1` launches the already-prepared replacement; it must be run
only after the external-transfer approval is resolved. Do not generate a new grant
or discard the initial failed charge. No push or merge was performed.
