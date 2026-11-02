# Explicit diagnose route handoff

The authorized Conic-to-Native continuation exposed a focused-Schema mismatch.
The active diagnosis still selected structure/mechanism research while Main
requested control feasibility. The compiler correctly refused scientific
execution, but directed Main to submit `research_plan(action=diagnose)` without
first selecting its Schema. The actual delivered Plan Schema still allowed only
`initialize_control`, so the attempted diagnosis was rejected before admission.

`DIAGNOSE_DOMAIN_MISMATCH` now returns an explicit sequence: first call
`research_route` with `{tool: research_plan, action: diagnose}`, then submit a
complete candidate-bound diagnosis with Main's hypothesis and chosen research
action. The existing domain gate remains unchanged. Route selection alone never
records that scientific diagnosis or starts a Worker. SDK action-enum feedback
also explains this route switch when the requested action is available in the
original tool directory.

Three targeted offline tests passed: actual SDK Schema loading for both domain
directions with complete Plan validation; real JSON Schema enum rejection through
SDK feedback; and the existing explicit Conic-entry regression. Fixture diagnoses
retain their normal public-operation accounting. Refusal and Schema selection do
not add mathematical or Provider charges. No live Provider or scientific Worker
was used by these tests.

The original Study's Main decisions, Conic diagnostic sequence, failed requests,
receipts, costs, task identity and acceptance requirements remain preserved. This
repair does not choose a method, source, control value or research route for Main.
