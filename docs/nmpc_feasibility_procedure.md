# Draft procedure: inspect and test NMPC feasibility recovery

Recommendation only, supported by one bounded investigation. The
[case](../memory/nmpc_feasibility_case_draft.json) and
[summary](../evidence/nmpc_feasibility_20261011/scientific_summary.json) record
restored discretized feasibility and improved sampled closed-loop motion with
continued holding-speed acceptance failure. Do not infer always-enable recovery,
robustness, unique cause, optimizer convergence or LLM superiority.

1. Freeze physics, task, timing, objective, scaling and acceptance. Import owned,
   hash-verified source archives and the latest paired numerical evidence.
   Supply case/procedure facts explicitly; distinguish this from model retrieval.
2. Select rejected tensions from the immutable nested returned/retained plan,
   not top-level selected initialization. Preserve exact references/pointers and
   variable order; deduplicate identical vectors and tension schedules.
3. Reconstruct measured state, previous input, effective horizon, absolute
   timing and holding flags. Deserialize/evaluate the CasADi objective and all
   original constraints without running an NLP to populate a cache.
4. Decode actual row order: kinematic rows first, then generalized force rows.
   Record named coordinate, zero-based interval, absolute times, signed/absolute
   scaled and physical residual, denominator/unit, ranked violations and count
   above unchanged1e-5. Verify force decomposition against the exact implicit
   expression. Small physical residuals do not bound trajectory errors.
5. Require a model hypothesis, evidence, source plan, fixed conditions, expected
   and weakening observations, budget and stop rule. Regenerate under unchanged
   tensions using the existing implicit root finder. Saved states are guesses;
   evaluate each returned step. Preserve verified partial evidence on failure.
6. Verify the regenerated candidate against the original objective, all
   constraints, bounds and measured initial state. Compare independently with
   both the feasible selected initialization and rejected raw plan. Label each
   metric's comparator. Preserve raw solver status/iterations; regeneration is
   neither IPOPT convergence nor an extra IPOPT iteration. A diagnostic executes
   no simulator command. Save complete numerical artifacts before packaging.
7. Return one result before another scientific decision. Allow only one bounded
   next step: distinct additional regeneration, explicit warm/cold comparison,
   recovery flag revision, or STOP. Keep post-solve recovery disabled for the
   warm/cold comparison; count every new cold/warm attempt and preparation.
8. Before testing a15s controller, prefer its saved15s returned schedule rather
   than extrapolating from30s. Materialize the full configuration and verify only
   the recovery flag changes. Live recovery uses current simulator measurement
   each update, attempts the raw returned schedule once, and delivers only a
   feasible lower-objective result. Preserve the verified incumbent on failure
   or no improvement; do not inject diagnostic future states.
9. Compare complete sampled terminal/holding metrics, aligned prediction errors,
   initialization selections, recovered/other feasible deliveries, failures and
   actual costs. Record original IPOPT iteration counts when available; explicitly
   mark missing ordinary-observation counts. Snapshot update selection controls
   evidence capture, not when recovery is active. Earlier changed commands alone
   do not establish acceptance; keep .30s diagnostic and .35s task metrics distinct.
10. STOP seals provider sends. Preserve the original model disposition and
    separate factual corrections. Repeated references in packets are evidence
    reuse, not repeated experiments. Inspect sealed outputs after reporting
    failures; do not repeat numerical work or reset clocks/counters. Preserve
    negative results and maintain reference-backed drafts under the known legacy
    admission mismatch; do not fabricate validation or approval.

Confirmed observations in this round: update20's15s schedule regenerated with
10 root solves, scaled residual8.78e-13 and objective22.2605 versus selected1697.0857.
Endpoint speed slightly worsened versus the rejected plan. The single full
35-update flag revision recovered6 deliveries, achieved terminal3.016mm and
holding maximum3.464mm, but exceeded .02m/s holding speed at .30s and .31s.
Projection/prediction disagreement remains. No real-time or continuous-time
guarantee, hardware transfer or unconditional remedy follows.
