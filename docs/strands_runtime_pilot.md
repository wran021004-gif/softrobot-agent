# Strands runtime pilot: R0–R2 offline acceptance

R3 now has an executable live entry point. Its bounded run verified real request accounting, original reads, framework summarization/offloading and new-process retrieval, but exhausted 40 attempts before a valid formal submission. **R3 is not accepted.** See the [Chinese R3 stop report and commands](strands_runtime_pilot_r3.md). The R0–R2 evidence below remains the offline baseline.

The offline integration passes A–G using `strands-harness==0.2.0`, `strands-agents==1.59.0`, Python 3.11.16, controlled HTTP model fixtures, and the existing evidence, submission, and accounting services. [Results](../evidence/strands_runtime_pilot_20261009/results.json), [configuration](../evidence/strands_runtime_pilot_20261009/configuration.json), and [manifest](../evidence/strands_runtime_pilot_20261009/manifest.json) record the checks. **Live model requests: 0; mathematical solves: 0; robot backend executions: 0.** This establishes offline integration and recovery, not live DeepSeek compatibility, autonomous research quality, or physical improvement.

The pilot branch starts at frozen commit `ca56f7c0870d3071d13568c7686cb9160b76f485`. The isolated worktree is `D:\softrobot-agent\.worktrees\strands-pilot`; the separate dependency environment is `D:\softrobot-agent\.pilot-env`. The original `softagent` environment and `feat/gvs-dynamics` branch are unchanged. Local Git excludes hide these two workspace directories; they are not committed.

## Selected workflow and boundary

One principal reviews the saved fixed-C evaluation, holding profile, and joint-acceptance record. `initialize()` imports those exact content-addressed artifacts from the V1 handoff bundle into a new `strands-pilot-*` activity. It creates an explicitly labeled extraction-only fixture report and a new disposition target, `fixed-C-offline-report`. The fixture report and new decision are not new robot experiments. The existing `Store.create_session()` imports a frozen robot input as data; dependency checks cover the active business services. The pilot does not recompile, initialize, or check the robot backend.

Original references remain `6314170…66892` (evaluation), `400226…6ab13` (holding profile), and `558256…88627` (joint result). Exact hashes are in the manifest. The original source execution is `197bceb6ff8f44b48a35bc4f79b3528d`. Assertions retain reach error 0.0031314437885609334 m and holding-position error 0.0033622899352609014 m below 0.01 m, holding speed 0.026817670846968282 m/s above 0.02 m/s, and joint `valid_failure`. Valid execution does not imply joint task success.

Only two business categories are exposed: evidence (`discover_evidence`, `read_original`) and formal decisions/receipts (`submit_result`, `get_receipt`). `retrieve_context` is the framework's additional retrieval tool. `read_original` calls the real `Host.invoke()` → `research.investigation_read` → `platform_tools.read_evidence()` chain, retaining public version checks, JSON-pointer paging, immutable identities, exact units, and independent source-inspection records. Discovery pages read a directory artifact through that same interface.

`submit_result` calls `InvestigationDispatcher.submit_disposition()` and the unchanged `disposition(validate_only=True)` validator. Native arguments contain business fields directly; assistant text is never interpreted as a submission. The adapter does not alter scientific judgments. A source-value mismatch is returned as existing structured feedback and corrected by a subsequent controlled model response.

The opt-in submission service uses `(investigation_id, revision)` as its business key, independent of transport call IDs. Equal delivery returns the original receipt; different payloads conflict. Explicit consecutive revisions append to the existing `disposition_versions` list. Decision state, immutable output, receipt, and ledger settlement commit in one existing SQLite transaction. `Store.complete(db=...)` allows this shared transaction; its default behavior is unchanged for other callers. An interruption before sealing rolls back the decision and retains the reservation. An interruption after commit recovers the original receipt without repeating the business effect. There is no second business-state machine.

## Framework and provider configuration

The actual assembled entry point is `create_harness()`, not a separately rebuilt loop. Installed wheel source and behavior were inspected for the pinned versions, alongside the official [configuration reference](https://strandsagents.com/docs/user-guide/harness/reference/configuration/), [context guide](https://strandsagents.com/docs/user-guide/harness/configure/context-and-caching/), and [session guide](https://strandsagents.com/docs/user-guide/harness/configure/sessions/). Dependencies, including transitive packages, are frozen in [requirements-strands-pilot.lock](../requirements-strands-pilot.lock); `pip check` passes.

Explicit public configuration disables all built-in shell/file/web/code/subagent tools, background work, memory, skill scanning, and built-in environment/todo plugins. Context management is `auto`, with persistent sessions and durable framework storage. The E scenario uses public `Offload.truncate()` and `Offload.summarize()` strategies with inexpensive thresholds. No adapter compressor or capacity estimator is introduced. Actual registered tools and disabled features are recorded in configuration evidence.

The model configuration is preserved from the saved V1 snapshot: endpoint `https://api.deepseek.com`, model `deepseek-flash`, thinking enabled, reasoning effort high, generation limit 32768, timeout 600 s, and a 1,000,000-token context-window declaration. Temperature remains absent in thinking mode. Credentials are unnecessary and are not loaded. The literal offline API-key placeholder never leaves `httpx.MockTransport`.

Stock `OpenAIModel` 1.59.0 accepts incoming reasoning but excludes reasoning blocks when formatting subsequent chat-completion messages. `DeepSeekPilotModel` is a small public model-provider subclass: the base formatter retains content/tool-call conversion, while the subclass restores DeepSeek `reasoning_content` from Strands' own message blocks. There is no parallel conversation history. Fixtures and one actual archived V1 response verify the subsequent wire request; C verifies session restoration, and E verifies preservation through tool-result offloading. The saved-response protocol replay deliberately encounters its unavailable historical tool name and returns framework feedback; it is not counted as a formal submission.

`FixtureBoundary` owns offline request-boundary accounting through existing `Store.reserve/complete/mark_unknown`, for ordinary calls, correction, and summarization. Strands retry configuration is `None` (one attempt), and the injected OpenAI client has `max_retries=0`. Every sent fixture request and confirmed raw response are archived as immutable Store artifacts. Simulated token usage, historical usage replay, real provider usage, and real costs are explicitly distinguished. Missing responses retain charged reservation/unknown status across a new process. Activity identity and the original overall deadline persist; a restart cannot create another allowance. HTTP accounting is currently fixture-only; enabling live transport requires a separate scoped implementation and authorization.

## Focused validation

| Scenario | Observed result |
|---|---|
| A | Actual Harness discovery/paging, original metric/holding/joint reads, native validated submission, and receipt lookup pass. Existing exact-fact validation is instrumented. |
| B | Existing source-value error reaches the model fixture; a native correction commits one result. Both attempts share the common budget. |
| C | `os._exit(73)` after persisted evidence results; a new interpreter restores the same session, IDs, references, deadline, and cumulative budget, then submits. |
| D | `os._exit(74)` after decision/receipt commit and before tool return; a new interpreter recovers the identical receipt. Replay has one business effect; changed payload conflicts. Revisions and rollback before sealing pass. |
| E | Framework tool offloading and actual summarizer invocation occur. A new interpreter calls native `retrieve_context`; the retrieved original page equals its stored public evidence result, with exact identity, values, units, and pagination. |
| F | `os._exit(75)` after sent request with no response. Reopening marks the existing reservation unknown. Exhaustion blocks both real framework summarization attempts and ordinary fixture dispatch; no fresh allowance or deadline is minted. |
| G | Old-runtime, scientific, and real HTTP boundaries fail if called; every observed counter is zero. Legacy turn/history remain inactive, and historical handoff hashes are unchanged. |

The initial seven-scenario run passed six cases; E's assertion assumed a JSON result block, while the framework stored a text result block containing JSON. Only E was rerun after correcting that assertion. D was separately rerun after adding atomic rollback verification. The saved-response protocol check was then added and passed. CLI selection and E's exact original-page equality were checked with affected E runs. A and saved-response conversion were rerun after using only public formatter delegation and declaring both business tool bindings. The final accepted scenario records contain 56 simulated request attempts. No unrelated full suite, scientific setup, fuzzing, or live request ran. Raw sessions and SQLite data stay in ignored `runs/`; the committed evidence includes compact results, receipts, source bindings, accounting, and scope assertions.

## Responsibility retirement map

| Actual old file/function | Pilot owner / still called? | Remaining non-pilot callers | Deletion eligibility |
|---|---|---|---|
| `platform_host.Host.run`; `platform_models.run_loop` | Strands assembled tool loop / no | `Host.run`, diagnostic workflow and diagnosis coordinator | Retain until other workflows migrate. |
| `platform_models.input_for/payload_for`; `InvestigationDispatcher._interact/_assistant_history/_append_evidence_turn/_append_correction` | Strands active messages and session continuation / no | Legacy host and investigation execution | Retain for those workflows. |
| `context_assembly.assemble_request/compact_investigation_request/assemble_working_request` | Strands context manager/stash / no | Investigation execution, diagnostic reference adapter | Retain; evidence archive utilities are separate services. |
| `platform_models._model_failure`; legacy correction/retry branches in `_interact` | Single observed request boundary; framework retries disabled / no | Legacy host/investigator paths | Retain outside pilot. |
| `InvestigationDispatcher.engineering_recovery/_checkpoint/_handle_failure`; `context_assembly.restore_working_state` | Strands snapshot continuation, existing business receipt lookup / no | V1 continuation, legacy investigation/research recovery | Retain outside pilot. |
| `platform_tools.bounded_evidence_page/read_evidence`; `research_investigations.read_source/_validate_fact/_visible` | Existing evidence and business validation services / yes | Both runtimes | Shared services; not retirement targets. |
| `InvestigationDispatcher.disposition/submit_disposition/disposition_receipt`; `Store.complete/lookup` | Existing submission and receipt authority / yes | Old disposition callers and pilot opt-in service | Shared services. |
| `Store.reserve/remaining/spendable/mark_unknown`; `Store.put/artifact/event` | Existing common budget and immutable raw archive / yes | Both runtimes | Shared services; no competing balances. |

The pilot removes five responsibility groups from its active path: legacy loop, mutable conversation management, context assembly/compression, correction/retry control, and engineering recovery scheduling. [Measurement](../evidence/strands_runtime_pilot_20261009/simplification.json) counts retained provider/adapter wiring separately from fixtures, tests, documentation, and third-party source. No global line-removal or deletion claim is made. Exact evidence-inspection state in the business Store is intentionally retained; it does not schedule a conversation.

## Reproduction and R3 boundary

From the pilot worktree, install into a fresh environment without upgrading `softagent`:

```powershell
C:\Users\gugugaga\miniconda3\envs\softagent\python.exe -m venv D:\softrobot-agent\.pilot-env-repro
D:\softrobot-agent\.pilot-env-repro\Scripts\python.exe -m pip install -r requirements-strands-pilot.lock
$pilotPython = 'D:\softrobot-agent\.pilot-env-repro\Scripts\python.exe'
& $pilotPython -m tools.strands_pilot scenarios --directory runs/strands-pilot-repro
& $pilotPython -m tools.strands_pilot scenarios --directory runs/strands-pilot-repro-E --scenario E
& $pilotPython -m tools.strands_pilot start --directory runs/strands-pilot-user --activity strands-pilot-user
& $pilotPython -m tools.strands_pilot resume --directory runs/strands-pilot-user --activity strands-pilot-user
```

Use fresh directories/activity IDs for independent offline scenarios; use the same pair to resume. `start --fault read`, `start --fault submit`, and `start --fault unresolved` reproduce process-death points. The last exhausts the activity's one-request fixture allowance. Expected exit codes are 73, 74, and 75. `python -m unittest tests.test_strands_pilot` is the repository's focused test entry. Live R3 now uses `tools.strands_pilot_r3`.

The separately authorized R3 check ran with the user's shared ceiling of 40 provider attempts, 512 public operations and six hours including preparation. It reached an evidence-backed stop: live compatibility/continuation observations passed, while formal submission remained invalid at exhaustion. The original 12-request/1800-second R3 command was only an earlier proposal and is superseded by the [implemented commands](strands_runtime_pilot_r3.md). Do not create a new activity to replenish the spent grant, or expand to robot V2/scientific experimentation. Monetary cost remains unknown without verified billing evidence.
