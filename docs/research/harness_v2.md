# Research Harness V2

Development branch: `mainline/research-harness-v2`, based exactly on
`5fdea5660cc12aea23d4ff6f2744c0b132a230ba`. The public entry remains
`python -m tools.research`. No historical Store is migrated by importing code.

## Runtime ownership

```text
tools/research/
  __main__.py                     existing CLI
  provider.py, provider_context.py model formatting, accounted transport, capacity
  agent.py                        Main SDK lifecycle and typed tool routing
  research_context.py             L0 decision brief and L1 retrieval projections
  session_handoff.py              exact Store/SDK feedback and snapshot recovery
  config.py, state.py, budget.py   frozen composition, state guards and allowances
  reporter.py, evidence_policy.py  fixed facts, read-only interpretation, claim scope
  analysis.py, native_analysis.py  admitted mathematical methods
  mechanics.py, optimal_capability.py, nonlinear_capability.py
  design.py, search.py             candidate construction and bounded search
  execution.py, physical_replay.py, rl.py  existing owned execution paths
  feedback.py, diagnostic_relations.py    task outcomes and scoped comparisons
tools/platform_store.py, platform_host.py, platform_registry.py
extensions/tendon_family/          structure compiler, GVS and MuJoCo physics
extensions/math_analysis/          numerical kernels without workflow ownership
tools/research_tasks.py            task adapters and acceptance meaning
```

L0 is a bounded decision projection, L1 is an on-demand working set, and original
L2/L3 evidence remains in the existing content-addressed Store. Dynamic packets
stay at the request tail; stable instructions stay in the system prompt.
Registered evaluation alone determines task acceptance. A route selects a tool;
it does not submit a Plan or grant scientific permission.

## P0 changes and boundary

Extracted the existing transport and response recovery from agent.py into one
provider.py owner. Reporter and session verification import that owner directly.
Agent imports the transport it actually uses; there are no forwarding functions.
Renamed the still-used sorosim_s55_feedback module to diagnostic_relations;
removed build_sorosim_s55_packet, a historical standalone preparation script with
no production or test callers. Numerical methods, Store and evaluator are retained.
Existing one-off research scripts are not deleted without a caller review.

Historical studies and private experience remain in their original worktrees.
Tests use isolated engineering fixtures and mock transport. No live Provider,
scientific Worker, mathematical solve or rollout is authorized for this change.

P0 verification: CLI help and configuration checks passed. The initial 28-test
selection exposed three pre-existing fixture failures, reproduced unchanged at
5fdea566: missing-cap reserve expectation, historical C3 evaluation identity,
and a synthetic execution fixture missing calibrated environment admission.
These are tracked for P3; no production guard or historical hash was weakened.

## P1 decision continuity

New on_demand_tools_v2 keeps the selected Plan available while reading evidence
or experience. Initial generation and closeout STOP are exposed as tools, never
submitted automatically. Legacy v1 registries retain their original behavior.
Navigation projection preserves exact usable entries before summary metadata.
The L0 tool_continuation view rebuilds route selections and four recent feedback
items from existing events, separately from scientific Plan intent and trace.
No second memory, planner, execution queue or digest was added.

The R2 fixture is extracted read-only from original events 35/68/105/122/427;
it excludes private cards. Four new real-SDK MockTransport checks pass, including
one legal generation, feedback, precise restore, and zero scientific execution.
Nine existing recent-round routing/recovery checks also pass. Scripted model
outputs establish protocol operation, not autonomous research improvement.

## P2 Provider and language boundary

provider.request_settings owns Main/Reporter wire construction. research_roles_v3
allows independent explicit models and none/medium reasoning. None is the new
configuration default for both roles. DeepSeek medium maps explicitly to its
Thinking enabled/high wire profile; Gateway medium maps to Responses reasoning
medium. Legacy role versions and serialized snapshots retain their old values.
Credentials, model discovery and context capacities stay out of scientific facts.
Gateway model capabilities bind the exact configured model and catalog source;
offline-only fixtures are refused by the live transport. No model/price ranking is
inferred. `python -m tools.research models --runtime <file>` is a separate explicit
network operation; preparation/config resolution never discovers models.

The gateway owns only its HTTP layer and Responses conversion. Its pinned external
DevKit remains ignored, with license/notices and one explicit authenticated
inference callback patch. OAuth, protected storage, consent and quota errors stay
in the existing DevKit. Function IDs, structured text, results and completed opaque
reasoning survive replay. Partial streams never admit tool execution; unknown
usage remains unknown. Actual account/model/tool/reasoning support is NOT verified.

english_decision_v2 requires english_sources_v1 with authored_language=en. Stable
instructions and generated Plan/Reporter prose originate in English. The Provider
checks the actual decoded packet, including JSON-escaped text. The Unicode script
check is a bypass detector, not a language classifier. Source ownership matters:
experience reads need declared English origin, and reviewed translations need an
original reference and reviewer. Historical Chinese bytes remain unchanged; they
are refused until an explicitly reviewed English view is supplied. Scientific
observations and historical translated guidance never share evidence status.

`study_harness_v2.json` is a parsed pending configuration, not a prepared Study or
execution grant. It preserves the M5 task/evaluator, exposes the new routing and
English-source policy, and limits a future request to eight Provider calls.
`runtime_chatgpt_gateway.example.json` is deliberately incomplete: the owner must
supply a real account model, verified capabilities and context capacity. No slug,
price or real account capability was invented.

P2 verification: 15 combined Provider/F1/recent-round checks passed; five Provider
checks also cover uncertain sends, no retry and incomplete responses. The Gateway
suite exercised 106 cases: two missing-script packaging failures were fixed by
including the owned dpapi.ps1 and both passed targeted reruns (alongside the
unavailable-storage guard). Forty request/HTTP/conversion tests passed independently.
A fresh ignored dependency preparation was also checked against the pinned source.
Full final-suite results are recorded below at P3. No actual account, model catalog,
OAuth consent, inference or scientific execution occurred.
