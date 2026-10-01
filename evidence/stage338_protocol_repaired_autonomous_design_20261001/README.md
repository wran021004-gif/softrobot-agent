# Repaired tool protocol and one autonomous design experiment

Implementation commit `81ebc8aabefdf36c5375066f8ca4d8944cd60ae1` adds the versioned `deepseek@2.0.0` transport. New sessions use deterministic readable names from registered public tool IDs; the frozen `readable_v1` mapping identity is `0846de5651b0b24dd9a04831a3d1e0e6aacb6cc65b098d4a870661508423b274`. The prior `deepseek@1.0.0` adapter retains hashed names. Declaration and production decoding use the same map, and decoding is restricted to names advertised in that request.

Focused local checks passed without network, mathematics, simulation, backend work, or workers. They covered readable and legacy declaration/decode round trips, deterministic collision handling, unknown-name rejection, mismatched evidence/endpoint arguments rejected before tool execution, compact correction feedback, and an existing decoder-to-Host fixture.

The one paid session was `gvs-stage337-97162901bdcb`. All 23 provider responses used exact advertised readable function names; one response returned two otherwise valid calls and was corrected within the configured protocol allowance. The model completed 22 public calls, including evidence reads, a fresh starting build, the full starting-build local analysis chain, 12 bounded mathematical evaluations, and exact proposal construction.

The model selected optimizer proposal `math-compliant-e63d9960aa49`: near length `0.1585 m`, far length `0.1185 m`, common section scale `1.05`, compliant material. The compliant and stiff proposals tied at a local controller-start residual upper bound of `0.015 m` (`1.5` times the official tolerance); the world-x position-control row was zero. The model chose compliant using the supplied historical closed-loop evidence. This local proxy is advisory and does not predict nonlinear reach, settling, real-time feasibility, or global optimality.

The exact proposal was built as `bp1_math_compliant`, but no backend execution occurred. Two analysis-record attempts omitted required linkage (first prior Route evidence, then endpoint and screen references), and the attempted run was rejected because candidate-bound shared analysis was incomplete. The Host then stopped at `BOUNDED_REPAIR_LIMIT`. Therefore official reach, sampled settling, and complete-update timing are unavailable, and autonomous finish is false.

Usage: 23 provider attempts, 22 tool calls, 12 new mathematical evaluations, 0 backend attempts, 0 workers, and `905.4660000009462 s` charged wall time. Raw provider responses and the SQLite ledger remain local; their paths, sizes, and SHA-256 hashes are in `actual_local_only_artifacts.json`.

Recommended next action: improve Route feedback/context so `route.record_analysis` explicitly enumerates the candidate-bound endpoint and screen references before a run is attempted; do not alter the controller or rerun this sealed experiment.
