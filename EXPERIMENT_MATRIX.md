# Experimental matrix — manuscript v1.0

## Completed FULL portfolio

Eleven completed task cases: T01--T10 and PHS-2D. The archived summary contains 30 passed required conditions among 30 required records, plus two T10 frozen control records that did not pass the complete recovery criteria. This is a completed-case summary, not a multi-seed success-rate estimate.

## First matched comparison: eight new runs

| Task | A: LLM-only | B: Direct mathematical tools | C: Historical FULL |
|---|---:|---:|---|
| PHS-2D | 1 | 1 | Existing result |
| T01 | 1 | 1 | Existing result |
| T04 | 1 | 1 | Existing result |
| T07 | 1 | 1 | Existing result |

### Method permissions

- **A — LLM-only:** LLM proposes and modifies structures and controls; it can use the candidate generator, physical simulator, direct control-input interface, and independent evaluator. Optional mathematical diagnosis and automated mathematical optimization tools are unavailable.
- **B — Direct mathematical tools:** A plus direct access to supported bottom-level mathematical tools (e.g., Jacobian, KKT/equilibrium, finite difference, and supported optimization). The LLM constructs the mathematical question and requests itself. The high-level research-intent projection and mathematical research orchestration are unavailable.
- **C — Ours:** the existing FULL result and trace; no re-run.

### Fairness conditions

- A and B use the same base model, task contract, initial state, legal design space, structure generator, physical backend, evaluator, and within-task budget.
- A and B start from the original task state, not from a FULL intermediate candidate or decision trace.
- Topology and parameter groups are open within the task's complete legal design space.
- Knowledge/Skill access is aligned between A and B and documented against the historical C configuration.
- C remains a historical reference. Any mismatch in model, knowledge snapshot, task protocol, or resource configuration is reported rather than hidden.
- The same task-specific budget ceilings apply to A and B. Mathematical calls are separately recorded.

### Primary measurements

Required pass count; task-specific normalized violation; best violation versus cumulative physical-evaluation budget; cost to first feasible candidate; candidate count; physical evaluations; mathematical calls; LLM tokens; integration steps; wall-clock time; and evidence linking a mathematical finding to a subsequent design/control action.

One run per A/B condition is a matched case comparison and budget trace, not a statistical-significance study. No raw-error average is computed across heterogeneous tasks.

## Extensions not included in the first batch

Knowledge/Skill ON/OFF, Flat Context versus L0--L3, and additional task coverage may be considered after the first batch. They are not prerequisites for the initial manuscript framework. No Fixed-Plan experiment is included in the current plan.
