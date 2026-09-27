# Optional spatial braking for parameterized GVS reach

`controller.gvs_nmpc@3.0.0` accepts the following optional recipe fields:

- `position_error_scale_m`: position-cost scale; defaults to the task's reach
  tolerance. This does not change the evaluator's tolerance.
- `tip_speed_scale_m_s`: positive spatial speed scale, default 0.02 m/s.
- `terminal_tip_speed_weight`: dimensionless squared normalized world tip-speed
  cost at the rolling horizon endpoint, default zero.
- `holding_tip_speed_weight`: stage weight per second on the same squared speed,
  default zero. Active at prediction nodes at/after task duration minus the
  configured `settling.window_s`. The prediction continues holding beyond the
  task endpoint; physical execution still ends at the original task duration.

World tip velocity is the fixed-mount tip-position Jacobian times GVS generalized
velocity. A rolling endpoint is not the absolute task endpoint. Holding activation
uses the controller's actual interval-start time and prediction-node times.
Scheduling inputs have equal lower/upper bounds and are refreshed with the measured
state and previous tension; the graph and IPOPT instance are reused. Generic
workspace callers must supply explicit settling settings and current execution
time when enabling holding cost.

The original v2 asset is unchanged. Default zero speed weights retain its cost.
The existing curvature-rate penalties remain separate. Independent plan feasibility
still uses 1e-5, recovery remains opt-in, and neither a low predicted speed nor a
feasible plan establishes backend settling or optimization convergence.

The bounded Stage 3.20 experiment and physical acceptance results are recorded in
`runs/stage320_reach_brake_20260927/implementation_report.md`. The configuration
is an experimental recipe, not a newly validated general control profile.

Stage 3.20's one fresh B reached 6.176 mm endpoint error, but failed sampled
settling: maximum final-window speed 0.025266 m/s exceeded 0.02 m/s. All 35
plans were independently feasible, none optimization-converged. Mean complete
update took 27.411 s. Conditional A and LLM acceptance were not run.
