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
