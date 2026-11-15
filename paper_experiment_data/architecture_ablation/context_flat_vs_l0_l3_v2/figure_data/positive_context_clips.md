# E2-R2: one observed paired case

Checkpoint: PHS after C037, not prior E2/C035. Original engineering Core evidence, two new decision-only Main sessions. C042 was prepared but omitted before inference by the capacity rule; no replacement or outcome-driven rerun.

## Cost and decision quality: one finding

Provider actual initial input: Flat 877,197; Hierarchical 86,425, reduction 90.1476%.

Provider actual cumulative input across ALL requests: Flat 877,197; Hierarchical 174,298, reduction 80.1301%. Requests: 1 versus 2. Output tokens: 1,092 versus 1,012. No rejection, transmission error or missing Main usage occurred.

Blind five-metric mean: Flat 3.4/4; Hierarchical 3.6/4. The 0.2-point advantage reflects narrower causal attribution and candidate lineage, not fuller evidence coverage. Coverage is Flat 5/5 versus Hierarchical 3/5. Hierarchical omitted the detailed non-monotone trend and near/distal contrast and its matched reroute needs explicit legality/payout/preload admission. Preserve those limitations beside the positive result. Human review is pending.

## Exact decision clips

Hierarchical original (`D:/softrobot-agent/paper_experiment_data/architecture_ablation/context_flat_vs_l0_l3_v2/sessions/da9b126e-f4f8-4051-8ceb-665b9ee8d7d5/result.json`, `/decision/hypothesis`):

> Existing evidence discriminates only partly: it directly establishes illegal installed geometry for the studied F3 route, while viscosity variants still failed loaded qualification, but no matched legal-route comparison exists, so the causal performance hypothesis remains unresolved.

Flat original (`D:/softrobot-agent/paper_experiment_data/architecture_ablation/context_flat_vs_l0_l3_v2/sessions/997b390e-061a-426c-9b78-518d098342d5/result.json`, `/decision/weakening_observation`):

> H2 is refuted by the observed non-monotonic/static-balance response to viscosity

The blind reviewer judged the Flat refutation too broad: a non-monotone scalar response does not refute every possible viscosity redistribution. The raw C036 route record independently reports a cable-solid intersection at pose/time zero; original C031/C034 qualification records show continued loaded failures. These exact records are linked to Hierarchical's final Plan. No pre-read Plan exists, so a particular read's causal effect on decision change is not established. Flat did not miss those evidence groups; do not claim context overload caused its wording.

## Actual reading path: L0 → L3

Three parallel calls were requested in Provider turn 1 and their exact original content was delivered before the final Plan in turn 2. No L1 or L2 reads occurred, no repeat reads, and no four-level chain is claimed.

| Read | Exact record | Level | Feedback tokens, generic proxy estimate |
| --- | --- | --- | ---: |
| 1 | C031_EP0_qualifications | L3 | 438 |
| 2 | C034_EP0_qualifications | L3 | 440 |
| 3 | C036_EP0_route_geometry | L3 | 312 |

The read batch's next-request actual prompt increase was 1448 tokens, including tool-call history, raw returns, packet read progress and framing. This is not isolated actual per-read usage. The FULL 87873-token next request, including re-sent context, is included in the cumulative metric.

Flat received all 106 raw corpus records directly. Hierarchical requested three complete raw records through tools; 103 others were not fetched that way, though L0 already contained previews/metadata. This describes delivery, not model attention or a validated count of irrelevant facts.

## Sources and measurement boundary

- Decisions: `decision_replay_results.jsonl`; exact raw Provider requests/responses in the linked session files.
- Raw source pointers and return/delivery checks: `retrieval_path.csv`; original candidate/load binding retained in `information_manifest.json` and the frozen corpus.
- Scores/coverage/weaknesses: `blind_review/PHS_C037_A/independent_model_review.json`; anonymous originals and a human template are preserved.
- Actual cost: `token_accounting_per_request.csv` and `pairwise_results.csv`. Feedback/components/repetition proxies use full-wire o200k_base allocation and are NOT a verified model tokenizer or actual billing.
- Offline corpus/context construction is separate: `context_construction_costs.csv` plus `figure_data.json`. Observed preparation process wall time including a repaired local entry-binding check is 13.695 s; zero construction Provider calls. It includes unused C042 preparation and is not a production amortized latency benchmark.
- Later diagnostic/execution locators are in `retrospective_reference.json`, excluded from both Main and primary blind scoring; not a claim of isolated causal validation.

One paired sample, one judge, no statistical significance, no physical task-success improvement, no repeated packaging of initial/cumulative/path aspects as independent discoveries.
