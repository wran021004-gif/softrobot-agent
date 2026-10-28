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
