# Source and claim boundaries — manuscript v1.0

## Authoritative evidence

- Eleven completed FULL task cases: T01--T10 and PHS-2D.
- Archived task summary: 30 passed required conditions among 30 required records; two T10 frozen controls are reported separately and did not pass the full recovery criteria. This is a completed-case snapshot, not a multi-seed success rate.
- Principal passive mechanism-design case: the nine-segment, four-tendon PHS-2D Round-3 evidence package. Its ten-condition results, independent-process reproduction, half-time-step check, and initial-state perturbation check must remain attached to that package.
- PHS-2D local sensitivity audit: six loading branches by three task metrics (18 derivative pairs), along one common Young's-modulus direction on a fixed nine-segment topology. Maximum relative discrepancy is 0.1191223% for those task-metric pairs.
- First A/B/C comparison: eight new A/B runs on PHS-2D, T01, T04, and T07; C is the corresponding historical FULL result. No A/B outcomes are available until those runs complete.
- Real-world validation: separate hardware records already organized by the user; import the original measured results and selected demonstrations without inferring hardware performance from simulation.

## Required distinctions

- M0--M3 are different mathematical research semantics, not four independent optimizers and not a mandatory sequence.
- A mechanism indicator is not a task-success certificate.
- M1 fixed-input response is not M2 task capability after control re-optimization.
- M2 envelope sensitivity requires appropriate optimality, differentiability, and regularity conditions.
- M3 closed-loop behavior may be non-smooth due to controller iteration limits, saturation, contact, or mode changes.
- A failed numerical search does not prove infeasibility; a best-found local value is not a certified global optimum.
- The 0.1191223% PHS-2D discrepancy applies to 18 saved task-metric derivative pairs, not all internal generalized-coordinate derivatives, not 18 independent parameters, and not a global error bound.
- The PHS-2D local sensitivity audit and the final ten-condition physical validation are reported with their own source scope; do not merge metrics from different design snapshots.
- Historical C and new A/B runs are not described as perfectly matched if the recorded configuration differs.
- No calibrated Bayesian mutual-information/VOI policy, universal descent guarantee, or global structural gradient is claimed.
- Real-world robot results are a separate evidence layer and must be sourced from the archived hardware records.
