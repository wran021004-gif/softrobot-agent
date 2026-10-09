# First bounded Mainline 5 study

From `D:\softrobot-agent\.worktrees\strands-mainline5`, use the isolated interpreter
`D:\softrobot-agent\.mainline5-env\Scripts\python.exe`. Its exact packages are in
`requirements-strands-mainline5.lock`. Mainline 4 and the accepted pilot are merged
with both histories preserved; their closed activities are not reopened.

```powershell
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
& $studyPython -m tools.research_mainline5 prepare
# Commit implementation and focused checks before binding/dispatch.
& $studyPython -m tools.research_mainline5 bind
& $studyPython -m tools.research_mainline5 run
& $studyPython -m tools.research_mainline5 status
& $studyPython -m tools.research_mainline5 export
```

Preparation imports provenance-preserving evidence from the explicit historical
root `D:\softrobot-agent`. It creates one new cumulative grant, sixty sends,
1024 workflow operations, 48 mathematical/search operations, six development,
two verification, two identified technical replacement slots and ten backend
attempts overall. The actual user goal start is retained once, including all
implementation time; twelve hours include a final thirty-minute delivery window.
The original scientific task, family 2, controller 10 and solver recipe are fixed.
The principal selects one T2/T3 target and subsequent decisions; no other model
worker is authorized. Structural domains always bind to the selected template's
fixed semantic source, and actual constructed values are independently checked.

Exact `0.0375 / 0.1` testing is direct parameter transfer. Searching after historical
evidence is method/experience reuse. An untested direct transfer stays untested;
this entry does not add an experiment to fill a reporting category.

Recovery uses the same Store, Strands framework session and original grant:

```powershell
& $studyPython -m tools.research_mainline5 recover
```

Inspect `failure.json`, `study_state.json`, the cumulative Store reservations and
the framework checkpoint under `framework_sessions` before a scoped repair.
Accepted pending decisions are reconciled before another model send. Sealed
batch receipts and sealed verification are not re-executed after a lost return.
Unknown provider/backend outcomes retain their reservation and block automatic
resends. Confirmed unconsumed responses may be replayed only for the exact saved
request; do not replace the ledger, delete the checkpoint or replenish a budget.
A valid physical failure is a completed experiment. Completed STOP is preserved.

Credentials load only in live execution through the existing loader for
`$HOME\.codex\.env`; auth headers are not archived. DeepSeek Flash uses enabled
thinking, high effort, 32768 output tokens, 600-second timeout and tool choice
auto. Client, transport, framework overflow and SDK retries are disabled. Every
actual conversation or summary send shares the same Store reservation boundary.
SequentialToolExecutor supports multiple native calls with matched return IDs.
The public automatic context manager and persistent session are Strands-owned.

| Responsibility | Active owner / reused service |
|---|---|
| Conversation, reasoning, tools, context and restoration | Accepted `create_harness` and Strands session |
| Permissions, current domains, plan/fact validation | Host, research scheduler, candidate builder and current authority |
| Numerical proposals, robot execution and acceptance | Existing ask/tell and deterministic receipt executor |
| Durable business artifacts and cumulative resources | One new Store |
| Retired from this entry | `Host.run`, `platform_models.run_loop/input_for/payload_for`, `research_mainline4.live/decision`, legacy history/correction/recovery scheduler and context request/compression assembly |

Mainline 4 business assembly/execution functions were extracted to
`tools/research_mainline5_services.py`; this module does not invoke its former
conversation runtime. Shared evidence indexes, alias/value checks and business
state remain legitimate services. The unchanged atomic submission behavior and
framework context/restoration behavior retain their accepted pilot evidence.
Focused checks use clearly labeled model/backend substitutes; they do not count
as scientific evidence. The delivered nominal results do not establish robustness,
global optimality, real-time performance or completion of all Mainline 5.
