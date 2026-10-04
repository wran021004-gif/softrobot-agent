# Current development status - Milestones 4 and 5, 2026-10-04

Milestones 2, 3, and 4 are closed. Milestone 5 remains open. The accepted
Milestone 4 deliverable is execution `91c3ba1b01d6499fb26df8f95409401b`,
candidate `batch-ebbeadbdaca10732-0`: near/far 0.16/0.11 m, section scale 0.95,
compliant scenario, holding/terminal weights 0.05/0.05, controller 7. Joint
sampled acceptance passed; mean update was 8.518 s with 35/35 deadline misses.
The passing 0/0.05 recipe remains a research reference; the adaptation is a
tradeoff, not dominance. Selected deliverable and latest execution are distinct.

The original Milestone 5 pilot remains sealed and inconclusive. The later bounded
prediction-validation stage is now completed in the same ledger. The model chose
weights 0.075 and 0.15; both received full evaluation. Weight 0.075 lost holding
speed acceptance (0.023286 m/s), while 0.15 preserved joint sampled acceptance
(0.012939 m/s). The incumbent remains retained; the latest tested result is distinct.

Four prospectively sealed local intervals had correct speed-change directions
but all missed the 1e-4 m/s endpoint tolerance. These are separate from the six
historical development intervals (6/6 directions, 0/6 numerical passes). All four
full-task direction forecasts abstained; conditional accuracy is undefined.
The implemented secondary speed-order rule abstained on tied cold previews;
actual full-task speed order resolved, so ordering usefulness was not demonstrated.

The accepted research-model role is local diagnostic evidence only. Its next
action is finish/stop with zero future budget. Milestone 5 remains open: numerical
accuracy, useful prospective discrimination, repeatability and real-time operation
remain gaps. Both new runs missed all 35 deadlines. No further experiment is
launched or authorized by the future-research proposal.

Stage usage was 9 provider attempts, 18 workflow calls, 2 backend attempts and
971.706 charged seconds; cumulative usage was 28/55/6 and 3201.913 seconds.
Two protocol and two semantic corrections and a charged transport failure are
preserved. Additional solves/rollouts were 6/6; embedded controller updates 70.
The explicit transmission authorization and earlier automatic rejection remain
alongside the versioned handoffs. No historical replay, worker, subagent or push.

See [current delivery](../evidence/milestone5_validation_20261004/delivery.json),
[stage report](milestone5_prediction_validation.md), [Milestone 4](milestone4.md),
and [original pilot](milestone5.md).

## Historical Stage 3.42 status, 2026-10-01

The optional sequential design/diagnostic interfaces, explicit evidence binding,
matched endpoint-velocity analysis and bounded mathematical tools are implemented.
The one live attempt stopped at the protocol-correction limit before diagnostic
report submission. The requested diagnosis–improvement–verification cycle remains
incomplete. No controller modification was adopted and no new backend run occurred.

The latest successful reach execution is still Stage 3.41,
`5991de53e82747439e87ba8569667e1b`: 7.643 mm terminal error against 10 mm tolerance.
Its sampled settling and real-time criteria failed. Historical blocked statuses
and earlier failed robot results describe their own archived stages; they do not
replace that baseline or the newer Stage 3.42 workflow failure.

Stage 3.42 used 17/24 provider attempts and exhausted the separate four-correction
protocol allowance. It also exposed a diagnostic subgrant enforcement defect,
now fixed offline. The failed live execution is retained without rewriting its
budget or provenance. A new live attempt requires a separately authorized stage;
unused project attempts do not reset its exhausted correction allowance.

Details: [implementation and outcome](stage342_diagnostic_cycle.md),
[compact evidence](../evidence/stage342_diagnostic_cycle_20261001/outcome.json).

The next physical parameter group is tendon routing and guide lever arms, only
after a valid diagnostic handoff, matched controller comparison, and braking
assessment across trajectory operating points. No routing bounds or design-space
expansion were opened here. Screening priorities and exclusions are unchanged.
