91c3ba1b01d6499fb26df8f95409401b / joint_reach_holding_passed: True 1 (exact True)
91c3ba1b01d6499fb26df8f95409401b / terminal_error_m: 0.00269783 m (exact 0.0026978288583256148)
91c3ba1b01d6499fb26df8f95409401b / holding_max_error_m: 0.00273005 m (exact 0.0027300544346297905)
91c3ba1b01d6499fb26df8f95409401b / holding_max_speed_m_s: 0.0127503 m/s (exact 0.012750255515948416)
91c3ba1b01d6499fb26df8f95409401b / mean_complete_update_s: 8.51806 s (exact 8.518060568580404); less than a8382f8a4c6e4ebe921fb72f821b2188: 17.258959311459744 s
91c3ba1b01d6499fb26df8f95409401b / deadline_misses: 35 1 (exact 35)
91c3ba1b01d6499fb26df8f95409401b / real_time_demonstrated: False 1 (exact False)
91c3ba1b01d6499fb26df8f95409401b / solver_error_count: 0 1 (exact 0)
91c3ba1b01d6499fb26df8f95409401b / force_bound_violation_n: 0 N (exact 0.0)
a8382f8a4c6e4ebe921fb72f821b2188 / joint_reach_holding_passed: True 1 (exact True)
a8382f8a4c6e4ebe921fb72f821b2188 / holding_max_speed_m_s: 0.0183345 m/s (exact 0.0183345147769523); greater than 91c3ba1b01d6499fb26df8f95409401b: 0.012750255515948416 m/s
a8382f8a4c6e4ebe921fb72f821b2188 / mean_complete_update_s: 17.259 s (exact 17.258959311459744)
bebcfd47274940fb88a55ce5a2457c4c / joint_reach_holding_passed: True 1 (exact True)
bebcfd47274940fb88a55ce5a2457c4c / holding_max_speed_m_s: 0.0127357 m/s (exact 0.01273567785134029); less than 91c3ba1b01d6499fb26df8f95409401b: 0.012750255515948416 m/s
bebcfd47274940fb88a55ce5a2457c4c / terminal_error_m: 0.002705 m (exact 0.002705004945938772); greater than 91c3ba1b01d6499fb26df8f95409401b: 0.0026978288583256148 m
bebcfd47274940fb88a55ce5a2457c4c / mean_complete_update_s: 8.34285 s (exact 8.342849928579692)
148a2a290daa440f9b966f4d5cee4b5f / joint_reach_holding_passed: True 1 (exact True)
148a2a290daa440f9b966f4d5cee4b5f / holding_max_speed_m_s: 0.0102012 m/s (exact 0.010201160469407439); less than 91c3ba1b01d6499fb26df8f95409401b: 0.012750255515948416 m/s
148a2a290daa440f9b966f4d5cee4b5f / terminal_error_m: 0.00331301 m (exact 0.0033130137577230853); greater than 91c3ba1b01d6499fb26df8f95409401b: 0.0026978288583256148 m
148a2a290daa440f9b966f4d5cee4b5f / holding_max_error_m: 0.00337023 m (exact 0.003370231014572803); greater than 91c3ba1b01d6499fb26df8f95409401b: 0.0027300544346297905 m
148a2a290daa440f9b966f4d5cee4b5f / mean_complete_update_s: 8.74062 s (exact 8.740616519999666)
9af9c7a3d6d84751ab0c1ebacd73d0f8 / terminal_error_m: 0.00277117 m (exact 0.002771173824806968); equal than 1ffdcbc4f93f4dc4bb16a807c7b4056b: 0.002771173824806968 m
9af9c7a3d6d84751ab0c1ebacd73d0f8 / holding_max_error_m: 0.00282021 m (exact 0.0028202094361386796); equal than 1ffdcbc4f93f4dc4bb16a807c7b4056b: 0.0028202094361386796 m
9af9c7a3d6d84751ab0c1ebacd73d0f8 / holding_max_speed_m_s: 0.0226046 m/s (exact 0.02260458517372844); equal than 1ffdcbc4f93f4dc4bb16a807c7b4056b: 0.02260458517372844 m/s
9af9c7a3d6d84751ab0c1ebacd73d0f8 / mean_complete_update_s: 8.85894 s (exact 8.85894021142823); greater than 1ffdcbc4f93f4dc4bb16a807c7b4056b: 8.644476228571408 s
3389776a7ca449bb90388e2501194400 / joint_reach_holding_passed: False 1 (exact False)
3389776a7ca449bb90388e2501194400 / holding_speed_passed: False 1 (exact False)
3389776a7ca449bb90388e2501194400 / holding_max_speed_m_s: 0.0284833 m/s (exact 0.02848333276847738); greater than 91c3ba1b01d6499fb26df8f95409401b: 0.012750255515948416 m/s

This is a standalone interpretation and closure note for the stopped autonomous supplement, written under the versioned post-run repair. It explains what the ledger supports; it does not retroactively correct any earlier text, and earlier statements remain as written. Closure of this version requires exactly this versioned repair artifact.

The run stopped because the reservation for one further complete search was exhausted. The ledger shows the backend solve budget fully consumed with none remaining, so no additional complete search could be reserved. The stop is therefore a capacity-exhaustion outcome, not a reporting-cost decision.

Passing behavior is described at three levels. Within the original geometry structure there is a matching-weight pass that shares the retained incumbent's holding and terminal weighting yet sits in the original geometry; its terminal, holding-position and holding-speed conditions all hold together. Within the shortened geometry there are distinct historical passes whose joint reach-and-holding condition is satisfied, and the retained incumbent is itself one of them. A newer updated-campaign observation adds a further joint pass on the shortened geometry.

The new passing point trades against the retained incumbent rather than dominating it: it achieves a smaller holding maximum speed, i.e. a tighter speed margin, while carrying larger terminal and holding position errors. It is a tradeoff candidate, not a strict improvement.

The replication is a repeat of an earlier frozen configuration by an updated-campaign execution on the shortened geometry. Only the retained aggregate metrics repeat exactly — terminal error, holding maximum error and holding maximum speed are identical between source and repeat. Timing does not repeat, and no claim of repeated trajectories, general repeatability or variance is made.

Timing partitions with geometry: shortened-geometry executions complete updates in a faster cluster and original-geometry executions in a slower cluster, with the retained incumbent in the faster cluster. Control period, control update count and deadline misses are constant across the ledger, real-time demonstration is not achieved in any execution, and solver errors and force-bound violations are absent.

Four historical failure causes are recorded and are distinct from one another: a prior connection refusal; an incompatible required tool choice under thinking; an original-geometry pass attributed to the shortened geometry; and a terminal metric attributed across execution identifiers although the correct source was retained in the ledger. The latter two are evidence-projection defects — faults in how evidence was labeled and carried — and they are possible contributors to the run's difficulties, not proven internal mechanisms.

No scientific work is requested or performed here; all scientific STOPs are preserved. Retaining the selected execution as incumbent and treating the latest as a later configuration that does not achieve the joint condition are the correct reading of this evidence. Limitations stand: a single matching repeat does not establish general repeatability, variance, identical trajectories or identical timing, and sampled acceptance does not establish a continuous-time guarantee, realtime, superiority or a unique physical cause.
Retain the selected execution as the incumbent. Treat the newer joint pass on the shortened geometry as a tradeoff candidate rather than a replacement, since it improves the speed margin but worsens position and terminal errors, and treat the latest updated-campaign execution as a later configuration that does not achieve the joint condition. Accept the repeated configuration as partial confirmation of the retained aggregate metrics only, and do not extend it to trajectories, timing, variance or general repeatability. Keep the four historical failure-cause distinctions separate when describing this run. Record this versioned post-run repair as the closure artifact for this version without rewriting earlier text. Do not request scientific work; any further complete search would require a fresh reserved backend capacity reservation rather than a reporting change.
Whether the newer joint-pass tradeoff is preferable to the retained incumbent under the intended objective is unresolved.
Whether the evidence-projection defects are causal contributors or incidental labeling faults is unresolved; they remain only possible contributors.
General repeatability, variance, trajectory identity and timing identity remain unresolved beyond the single aggregate-metric repeat.
Continuous-time, realtime and uniqueness guarantees remain outside what the sampled acceptance evidence can establish.
The original geometry structure carries an empty component definition in this ledger, so its exact geometry parameters are unresolved here.