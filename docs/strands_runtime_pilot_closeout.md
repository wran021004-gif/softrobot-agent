# Strands formal-submission closeout and handoff

The pilot is closed: DeepSeek issued a native `submit_result` for `fixed-C-offline-report`, revision 1; the real validator accepted it and receipt lookup retrieved the same durable record. One business effect was recorded. This completes the cumulative R3 evidence together with the earlier successful original reads, framework summarization, and cross-process restoration. It does not change the original failed activity.

The stopped original is `strands-pilot-r3-20261009`: 40 provider attempts, seven failed submissions, no receipt, phase `stopped_budget`. Its ledger, saved Strands snapshot and offloaded originals remain byte-for-byte unchanged. The new linked activity is `strands-pilot-r3-20261009-closeout`, created through public `Store.create` and `Store.create_session`; its frozen authorization is 24 additional provider attempts and two hours including preparation, starting Beijing time 2026-10-09 17:49:12. Its request cutoff leaves the existing 600-second timeout inside that limit. Neither allowance nor deadline was reset after execution began.

## Interface and focused checks

`PrincipalDisposition.evidence_used` no longer has an item-count maximum. The inherited selected-disposition schema also removes that constraint. Other required fields, source/provenance bindings, exact values, pointers, independent inspections and applicability checks remain active. The existing complete native schema reaches the provider. Snapshot restoration retains the original history; the public Agent system-prompt property refreshes only the current interface instructions, including exact object-versus-field citation rules.

The existing `SequentialToolExecutor` accepts multiple native reads in one model response and returns a separate result for each call ID. Tests check dispatch/result ordering and the corresponding source/pointer in the next wire request. Host locking is unchanged.

Ten focused checks passed before the live closeout, including the affected A scenario. Two affected checks passed after the reporting repair and saved-failure regression were added. They cover 13 distinct valid evidence fields accepted by the real validator, uncapped provider schema, actionable missing-field/path/value/identity/scope errors, sequential matched reads, and restoration under the separate 24-attempt ledger with unchanged original files. Actual saved failed native submissions are reused: formerly count-rejected 13-item arguments parse, while the archived partial `/detail/motion_summary` value still fails exact-value comparison. No complete R0–R3 rerun or new scientific evaluation was performed. See [checks](../evidence/strands_runtime_pilot_closeout_20261009/focused_offline_checks.log) and [affected recheck](../evidence/strands_runtime_pilot_closeout_20261009/affected_recheck.log).

The audit previously classified a successful receipt containing `error: null` as a validation failure. It now records failures only when that field is non-null; the persisted decision and original activity evidence were not altered.

## Accepted judgment and receipt

| Existing judgment | Saved evidence | Outcome |
|---|---|---|
| Arrival | 0.0031314437885609334 m ≤ 0.01 m | Pass |
| Holding position | Maximum sampled error 0.0033622899352609014 m ≤ 0.01 m | Pass |
| Holding speed | Maximum sampled speed 0.026817670846968282 m/s > 0.02 m/s | Fail |
| Joint acceptance | `accepted=false`, `status=valid_failure` | Fail; execution remains valid |

The accepted `disposition=accept` adopts the extraction report's single exact reach-error fact. Its reason and 13 supplementary evidence items contain the four judgments; acceptance of that report fact is not joint robot-task success. All 19 citation links match their original values and prior independent inspections. No fresh evidence reads were needed. Scope remains candidate `fixed-radius`, original execution `197bceb6ff8f44b48a35bc4f79b3528d`, and the saved sampled window; causes, other candidates and physical performance remain unassessed.

- Receipt request: `disposition-9ce322e145585d886575aa88d034b1051f26d99879c9bffa68321e4afe0454b5`.
- Receipt execution: `e9df3cce32044440a337b5828672bd2b`.
- Durable result: `eb789c94b314a8f92ff30c90b86176bad758a3dd20a91b474856529a01898794`.

The receipt/result and independent lookup are in [receipt.json](../evidence/strands_runtime_pilot_closeout_20261009/receipt.json). [Acceptance](../evidence/strands_runtime_pilot_closeout_20261009/acceptance.json) records one business effect, zero validation failures, unchanged lookup ledger, exact citations and original-file fingerprints. The model's saved limitation text still says “Live-model compatibility … unassessed,” inherited from the extraction report. The observed pinned provider configuration and restored native submission worked in this run; that wording does not negate the observation, and long-term reliability remains unproven. The model record is preserved verbatim.

## Usage and evidence index

| Measure | Original stopped activity | New closeout |
|---|---:|---:|
| Actual provider attempts / confirmed responses | 40 / 40 | 3 / 3 |
| Framework summary requests | 2 | 0 |
| Native public tool operations | 61 | 2: submit, receipt lookup |
| Store charged tool units | 27 | 2 |
| Input tokens | 926,544 | 247,608 |
| Output tokens | 60,129 | 5,859 |
| Total tokens | 986,673 | 253,467 |
| Reasoning tokens (included in output) | 22,148 | 1,076 |
| Scientific solves / robot executions | 0 / 0 | 0 / 0 |
| Monetary cost | Unknown | Unknown |

No retries, corrections, summaries, unresolved requests or duplicate submissions occurred in the live closeout. Twenty-one authorized attempts remain unused; submitted phase prevents another execution of this closeout. The Store's settled `wall_s=21.18799999996554` is request/tool accounting, not overall preparation elapsed time. The absolute two-hour deadline includes preparation.

- [Authorization](../evidence/strands_runtime_pilot_closeout_20261009/authorization.json) and [actual configuration](../evidence/strands_runtime_pilot_closeout_20261009/configuration.json).
- [Raw new request/response/tool archive](../evidence/strands_runtime_pilot_closeout_20261009/raw_archive.json), with three content-addressed original response files beside it. Requests include necessary restored history; headers and credentials are excluded.
- [New ledger and predecessor link](../evidence/strands_runtime_pilot_closeout_20261009/accounting.json).
- [Original R3 stop report](strands_runtime_pilot_r3.md) and [unchanged R3 observations](../evidence/strands_runtime_pilot_r3_20261009/acceptance.json): reads, summary, new-process restoration and exact retrieval.
- [Earlier offline acceptance and responsibility map](strands_runtime_pilot.md): existing A–G evidence, including atomic receipt recovery; no crash scenarios were repeated here.

## Commands and future integration boundary

Run from `D:\softrobot-agent\.worktrees\strands-pilot` using the existing environment and pins:

```powershell
$pilotPython = 'D:\softrobot-agent\.pilot-env\Scripts\python.exe'
$closeout = 'runs/strands-pilot-r3-closeout-20261009'
$evidence = 'evidence/strands_runtime_pilot_closeout_20261009'

# Actual one-time preparation and completed live entry:
& $pilotPython -m tools.strands_pilot_closeout prepare --directory $closeout --source-directory runs/strands-pilot-r3-20261009 --started-unix 1791539352
& $pilotPython -m tools.strands_pilot_closeout resume --directory $closeout

# These remain usable after completion; neither issues a provider request:
& $pilotPython -m tools.strands_pilot_closeout receipt --directory $closeout
& $pilotPython -m tools.strands_pilot_closeout export --directory $closeout --evidence-directory $evidence
```

Preparation refuses an existing closeout directory or an already-bound grant; `resume` refuses submitted phase. Before acceptance, correction may use `resume --feedback` within the same ledger. `--recover-response` retains the existing exact saved-response replay mechanism and adds no new allowance. Unknown outcomes keep reservations and block further sends. Credentials load programmatically from `$HOME\.codex\.env` only for live execution and are never exported.

Strands owns conversation, sequential tool execution, context management, stash and snapshot restoration. Softrobot-Agent owns original robot evidence, research-tool authorization, exact source checks, formal results, atomic receipts and the business ledger. The narrow closeout `prepare`/`execute` functions compose those existing services; they do not introduce another runtime loop or recovery state machine.

Future Mainline 4 integration should call the assembled `build_harness`/`build_live` boundary with an authorized business `Host`, its approved tool bindings and persistent framework session, retaining the native DeepSeek adapter and authoritative Store reservation/settlement services. This delivered entry permits only saved evidence and formal decisions. Adding research tools and task bindings belongs to future integration; Mainline 4 was not started here.

The active path already bypasses `Host.run`, `platform_models.run_loop/input_for/payload_for`, legacy investigation `_interact`/history/correction helpers, `context_assembly` request assembly/compression, and legacy engineering recovery scheduling. Shared evidence/validation/Store services remain active. Legacy files with other callers remain; multi-agent scheduling, memory and V2 are outside this closeout.
