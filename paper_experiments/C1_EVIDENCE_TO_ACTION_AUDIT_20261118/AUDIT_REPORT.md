# C1 Evidence-to-Action audit

## Result

| Recorded initiator | Evidence-linked proposals | Selected | Dispatched | Executed | Independently validated |
| --- | ---: | ---: | ---: | ---: | ---: |
| Main Agent | 88 | 88 | 73 | 46 | 1 |
| External Codex | 132 | 132 | 132 | 114 | 9 |
| All verified links | 220 | 220 | 205 | 160 | 10 |

Execution conversion is **160/220 (72.73%)**; validation conversion is **10/160 (6.25%)**. Proposal-to-validation is **10/220 (4.55%)**. Fifteen identified proposals are in intentionally decision-only replays; the operational archive alone is **160/205 (78.05%)** for execution. The observed Main Agent alone is **46/88 (52.27%)** executed and **1/46 (2.17%)** independently validated. The optional Main-role aggregation includes outside work performed in that role; it is **not** evidence that the Main Agent itself made or executed 160 actions.

The audit reads 25,662 historical event/receipt rows across 283 source-index entries and creates 1,314 candidate action rows; 1,094 do not enter the denominator. Counts are for this archive and its identifiable edges, not an autonomy rate across all FULL studies. Zero verified actions for a task is not evidence of zero activity. No new tool execution, inference or simulation was required for C1.

## Admission and join rules

- Count one action once per stable run, action identifier and actor, not one per supporting reference. Group evidence as mathematical, physical or both. Require a structured action and at least one explicit reference that resolves to a recorded scientific artifact or an explicitly derived schedule. Free text and D3's declared-only links are not execution evidence. No adjacency-only join is used.
- **Proposed** is the cumulative base of the funnel; **Selected** requires a structured choice. Every admitted proposal in this corpus is already a recorded choice; free-text suggestions are outside the population. **Dispatched** requires an original invocation record; a model emitting a tool-shaped decision in a replay is not dispatch.
- **Executed** requires a successful scientific operation plus an inspectable result: join Main original request and feedback on exact tool-use ID and payload; join external FULL decisions and actual operations on logged request ID, selector and actor with the Store output; join PHS-2D external CLI calls to explicit input files and SHA256-verified stdout. Registered mathematical output does not establish physical feasibility. A complete physical evaluation may legitimately return FAIL and still be an executed action.
- **Validated** requires a later passed independent evaluator result linked to the exact produced schedule and candidate. The sequence test ensures the receipt is later *after* identity is established; it is not the evidence of a causal relationship. This conservative join does not count same-call evaluation or candidate identity alone. No general claim about the absence of further mathematical or physical corroboration is supported.
- Separate the Main Agent that issued a scientific action, external Codex operators, human/operator repairs, sub-agents, the Reporter role and the fixed kernel/host. The event ledger preserves original labels and normalized roles. A Core worker on behalf of an initiator is not an autonomous Agent. Reporter-derived suggestions and deterministic summaries do not become execution credit.
- Retain failed attempts, missing receipt joins and unrecognized aliases separately. In A/B traces, textual evidence and fixed-driver output are retained without treating similar command ordering as a join. Reporter, E1 and E2 decisions may be selected without native scientific dispatch. Two direct-math archives have artifact-only Stores without event/receipt tables; their linked JSONL is indexed, but no fabricated execution edge is added. Coverage is lower than the underlying activity wherever exports, bindings or executable receipts are missing.

## Files and reproduction

- `trace_event_ledger.csv` indexes every parsed event/receipt in the explicitly enumerated Trace and Store sources, including duplicated archival representations, non-scientific events and failures. `source_manifest.csv` distinguishes raw-file SHA256, index-only sources, logical SQLite event/receipt SHA256 and excluded-store gaps. It is not a digest of every byte in a SQLite container.
- `evidence_to_action.csv` contains the identity, evidence, status, locator, actor and exclusion fields; `denominator=yes` is the inferential boundary. `by_task_id.csv`, `by_action_type.csv`, `by_evidence_type.csv`, `by_actor.csv` and joint tables reconcile to `summary.json`. The figure uses `funnel.csv`, `by_actor.csv` and `by_task_actor.csv`.
- The raw local archive is not republished with the derived ledger; source locators and SHA256 allow an independent audit against the same local archive. Source files remain read-only; the publication master and P0/D3 are indexes rather than sources of accepted actions.

```sh
python audit.py <archive-root> --output <check-dir>
python plot.py --directory <check-dir>
```

Use Python 3.11+ for analysis and Matplotlib 3.11.2 to reproduce both vector formats. The shipped CSVs alone suffice to redraw the figure.
