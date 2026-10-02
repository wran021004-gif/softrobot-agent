# Shared diagnostic workflow (Stage 3.46)

`tools/diagnostic_workflow.py` runs the same sequential phases in
`single_context` and `dual_context` modes. The former keeps one Host session
as working memory across design and diagnostic phases; the latter keeps one
per role. Experiment identity, memory identity, phase, and project budget
ownership are recorded separately. There is no LLM coordinator or parallel
execution. `examples/stage346_shared_diagnosis.py` exposes `minimal`, `pilot`,
and `compare`; the comparison is gated on actual successful pilot execution,
feedback consumption, revision, and final response.

The `deepseek@3.0.0` adapter exposes business fields directly. It supplies
fixed top-level bindings, request/version metadata, saved-state model and
integration protocol. It records native provider responses and resolved
internal invocations through the existing event/receipt ledger. Invalid
native calls and unknown fields receive bounded corrections. Ordinary prose
is never an executable decision. Legacy adapter versions remain available.

The development pilot exposed a remaining burden in version 3: copying a
24-value measured state through evidence pages. After a subsequent read batch
evicted its first 20 values, the model submitted the remaining four values,
then a predicted state, then four measured values again. All three were
correctly rejected by the unchanged executor; the six-attempt check phase and
bounded repair limit ended the pilot before any numerical execution.

The runner now defaults to `deepseek@4.0.0`. The model still chooses the
operation and update ID. The host resolves the exact measured state and
current applied input (prediction/braking) or previous applied input (local
comparison) from immutable evidence. The model cannot supply replacement
selectors or vectors. The full internal invocation is recorded, and the
existing scope/adoption/horizon/value validators still run. Version 4 is an
offline-validated repair; the preserved paid runs used version 3. No fresh
pilot or comparison was launched after the original pilot exhausted its
check-phase allowance.

`design.respond_diagnosis@2.0.0` separates disposition (`adopt`, `defer`,
`reject`) from action (`request_check`, `verify_adopted_change`, `finish`).
Finish ends the workflow before checking. Adoption alone executes nothing.
A local comparison still requires the exact adopted parameter/value and
matching saved horizon. Prediction/braking checks require no modification
adoption. No production controller or physical design is changed.

The host generates an inventory from actual immutable source files. It lists
retained counts, coverage, signal units, source references and access paths.
Full trajectories stay in evidence storage. Models must distinguish a view
that does not display data from absent data and unsupported calculations.
Exact selector validation checks values and linkage, not scientific prose.

Working memory reconstructs instructions plus a structured state snapshot,
without chronological chat replay. Each context keeps up to eight own handoff
products, 12,000 bytes per inline product, 48,000 bytes total, with FIFO
eviction and immutable references for retrieval. Existing evidence retention
keeps at most three pages/12,000 bytes and four recent actions. Explicit
current handoffs accompany phase changes in both modes. The payload cap is
200,000 bytes; optional evidence yields first, and required-state overflow
stops rather than silently dropping required facts. Comparison runs use
fresh stores with no cross-run experience updates.

Each full run permits 24 provider attempts, 60 tool calls, 3,600 charged
seconds, one check, at most six local solves and 24 short predictions, and
zero backend simulations/workers. Protected capacity belongs to phases, not
roles. Both modes use the same phase permissions and project ledger. Four
cumulative and two consecutive protocol corrections are allowed; a valid
accepted call resets only the consecutive counter. Transport and length
recovery retain the frozen provider rules and consume original budgets.

The source provider settings are preserved: `deepseek-flash`, thinking
enabled, high reasoning effort, 65,536 output tokens, with the existing
131,072-token length recovery. Endpoint: `https://api.deepseek.com`.
The source is Stage 3.41 execution `5991de53e82747439e87ba8569667e1b`.
Historical source files and failed Stage 3.45 evidence remain unchanged.

Run focused checks using the `softagent` Python 3.11 interpreter. New tests
are in `tests/test_shared_diagnosis.py`; numerical/provider fixtures in those
tests establish implementation behavior, not physical or diagnostic results.
Live evidence and the final evaluation belong under
`evidence/stage346_shared_diagnosis_20261002`.

The minimal native validation succeeded with a model-selected `reject +
finish` response. It used two attempts, including a preserved network failure
and one explicit continuation within the same ledger; transport retry policy
was unchanged. The full dual-context pilot completed the request, initial
report and design response, but no check, revision or final response. Formal
paired runs were therefore blocked by the required feedback-capability gate.
There is no live single-context result or comparative diagnostic conclusion.

| Workload | Result | Provider attempts | Tool calls | Charged seconds |
| --- | --- | ---: | ---: | ---: |
| Minimal native validation, v3 | Accepted `reject + finish`; cross-run protocol unit | 2 | 2 | 94.155 |
| Dual-context development pilot, v3 | Stopped in check selection; no executed check or revision | 11 | 18 | 436.313 |
| Single-context formal runs | Not started; prerequisite failed | 0 | 0 | 0 |
| Dual-context formal runs | Not started; prerequisite failed | 0 | 0 | 0 |

Total: 13/123 provider attempts, 20/303 tool calls, and 530.468/18,300 charged
seconds. No numerical checks, short prediction evaluations, local solves,
backend simulations, or workers executed. Monetary cost was not returned and
remains unknown. Reported usage totals are 153,710 input tokens, 109,879
completion tokens including 89,597 reasoning tokens, and 14,720 cache-hit
tokens; the failed network attempt returned no token usage. Runtime was
`C:/Users/gugugaga/miniconda3/envs/softagent/python.exe`, Python 3.11.16.
Wall elapsed to the last execution event was 313.114 seconds for the minimal
run, including its stopped troubleshooting interval, and 462.081 seconds for
the pilot. The overall live-workload window was 800.623 seconds.

Seven focused checks passed before live work. Two affected repair checks
passed afterward, including both modes with feedback/finish fixture paths.
No full historical suite was run. Neither offline fixtures nor an accepted
native design response establishes live feedback capability.

The initial pilot report's numeric selectors passed validation, but its
recommendation to instrument full q/qdot data conflates a query limitation
with missing recording. Thirty-five sampled trajectory records are retained.
Its deadline-to-solver-stop explanation remains a hypothesis; retained stop
reasons distinguish budget-best-feasible returns and relative improvement.
No executed check exists to assess diagnostic-check usefulness. The masked
development report and common rubric are preserved, with the limitation that
the implementer knows the run identity. No paid reviewer was used.

Implementation commits: `0fe602a` (shared runner and v3 interface), `234104e`
(minimal live validation and preserved network continuation), and `ffd3ebf`
(offline-validated v4 repair). Entry points are the shared runner, native
adapter, inventory builder, stage driver, versioned handoff contract and
focused tests named above. Raw requests/responses, resolved calls, receipts,
frozen runtime/provider settings, exact live source bytes and report review
are under `evidence/stage346_shared_diagnosis_20261002`.

All four formal runs remain unexecuted, and no formal paired freeze was
created because the required live feedback gate failed. The single next step
is a separately authorized fresh bounded pilot with adapter v4, to establish
actual check execution and report revision before any paired comparison.
