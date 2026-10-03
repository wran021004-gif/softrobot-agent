# Stage 3.54 Milestone 0 delivery

Milestone 0 passed: both supplementary suffixes and both fresh end-to-end
workflows produced accepted evidence-backed revisions and model-authored final
decisions. Each fresh workflow selected a legal nonempty change, verified its
effective configuration, and completed simulation, evaluation and profiling.
Stage 3.53 remains unchanged and incomplete; its suffixes are new validation grants.

The implementation adds host-scoped exact aliases, compact report deltas,
aggregate field feedback, retained unaccepted drafts and constrained field
corrections. Native invocation instructions use the advertised name mapping.
Capability/authorization gaps are distinct from missing or unread data. Existing
selectors, validators, role separation, scientific criteria and budget ceilings
remain in use. Final recommendation disposition and candidate selection are
separate structured fields.

| Validation | Accepted revision/final | Provider attempts | Tool calls | New backends | Charged seconds | Workflow elapsed seconds | Reported tokens |
|---|---|---:|---:|---:|---:|---:|---:|
| Single-context suffix | yes / yes | 3 | 3 | 0 | 75.219 | 82.844 | 178,917 |
| Dual-context suffix | yes / yes | 5 | 5 | 0 | 217.484 | 232.859 | 333,088 |
| Fresh single-context | yes / yes | 9 | 12 | 1 | 852.311 | 877.547 | 363,013 |
| Fresh dual-context | yes / yes | 7 | 12 | 1 | 961.261 | 983.781 | 311,169 |
| Total | all passed | 24 | 32 | 2 | 2,106.275 | 2,177.031 | 1,186,187 |

Extra numerical checks, workers and provider preflights: zero. Reported tokens
comprise 996,891 prompt and 189,296 completion tokens. Monetary cost is unknown.
Charged time follows sealed operation receipts. Workflow elapsed excludes setup,
export and the engineer's repair interval; the evidence also records elapsed
wall spans, including pauses (dual suffix: 1,047.213 seconds).

The single suffix needed one protocol correction. Its four invalid references
were fixed with a 241-character patch. The dual suffix initially stopped after
four revision attempts. Its last paid response used the advertised draft-root
pointer form, which the host incorrectly interpreted. After a focused repair,
that exact saved response passed the ordinary pending-tool validation with zero
new revision provider attempts. The existing revision limit stayed at four;
the final design decision used one further provider attempt. All original
failure receipts, pre-repair outcome/audit, counters and implementation migration
are archived. Total protocol corrections were 1 / 2 / 2 / 1 respectively, within
the unchanged four-total/two-consecutive policy.

Implementation commits: `541f426` (initial interface) and `e925723` (focused
repair). Both fresh workflows used the same frozen `e925723` implementation,
common baseline, task/scientific configuration, permissions, provider settings,
400,000-byte context limit, 900/30/60-second operation allowances and recovery
rules. Eleven affected reference/revision/recovery tests and twelve existing
completion/settling/context tests passed. The tests cover duplicate-execution
and duplicate-charge prevention; no full repository suite was run.

## Physical outcome, separate from workflow reliability

Both fresh models independently selected `holding_tip_speed_weight: 0 → 0.05`,
leaving `terminal_tip_speed_weight` and all other scientific settings unchanged.
They used separate new backend executions. Their physical measurements matched.

| Metric | Common baseline | Each fresh candidate | Threshold / result |
|---|---:|---:|---|
| Terminal error | 0.007642609 m | 0.008698904 m | 0.01 m; both pass |
| Holding maximum position error | 0.058138104 m | 0.056504560 m | 0.01 m; both fail |
| Holding maximum speed | 1.581015274 m/s | 1.175005267 m/s | 0.02 m/s; both fail |
| Mean complete update | 17.263319 s | 17.778773 / 17.714295 s | 0.01 s period; real-time not demonstrated |
| Deadline misses | 35/35 | 35/35 in each | no improvement |

Each fresh execution had zero solver errors and zero force-bound violation.
Holding metrics improved, while terminal error and computation worsened: the
frozen classification is `physical_tradeoff`, with joint reach/holding acceptance
still false. The single-context final decision retained the baseline; the
dual-context final decision deferred selection with `selected_candidate=null`.
Neither adopted the changed candidate. Both suffix decisions used their actual
historical worsening and retained the baseline.

Exact citations do not validate every scientific sentence. The archived dual
revision contains one mistyped candidate name in recommendation prose; structured
feedback binding and its explicit final no-selection decision are correct. This
was retained and documented, not silently edited. Sampled holding is not a
continuous-time guarantee, and these single runs do not establish causality or
organizational superiority.

Detailed evidence: [delivery summary](../evidence/stage354_milestone0_20261003/delivery_summary.json),
[scientific review](../evidence/stage354_milestone0_20261003/scientific_review.json),
and [exact-byte manifest](../evidence/stage354_milestone0_20261003/sha256_manifest.json).
The offline assembly is reproducible with `python examples/stage354_delivery.py`
in the established `softagent` runtime and saved local stores.

The [Milestone 1 interface inventory](stage354_milestone_interfaces.md) maps
contracts, producers, consumers and gaps. The next target is a read-only view
joining existing task, candidate, accepted decision, completion, evidence-scope
and budget references, with demonstrated rebuild dependencies for the two
controller weights. Milestone 1 itself is not implemented.
