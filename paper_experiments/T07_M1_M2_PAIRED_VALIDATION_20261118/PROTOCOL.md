# T07 matched structure–control audit

## Binding

The four original required conditions are M1_A (archived as `default` in the final aggregate), M1_B, M1_C and M5. Here **M1/M2 denote comparison semantics**; M1_A/B/C and M5 are **condition IDs**.

- `d0`: T07's 13 November history-informed initial elliptical-root design. The authoritative full ID in `summary.json` comes from `INITIAL_CANDIDATE.json`. The original M1_B condition alias and control seed are separate Store objects.
- `d1`: selected circular-root, original-tail, 14-mm routing design. Its shared root and per-condition aliases are linked by `FINAL_RESULT.json`.
- Both have two segments with 12 two-angle cells each, a common ordered four-tendon mapping, four one-to-one displacement channels and 8 N per tendon. The test input is **ideal direct tendon tension in N**, not a displacement command: the registered evaluator checks geometric stroke and speed as output constraints. Both arms share the same named initial coordinates and velocities, mount, gravity, external forces, timing, integration mode and frozen evaluator. Changed segment/route geometry remains part of the treatment, including any resulting Cartesian initial-position differences.
- Core `5a1865d1e07c1505f787fa767572ffa00bf8d19c`; MuJoCo 3.13.0; 1 ms physical steps, 20 ms zero-order-hold intervals, 0.6 s horizon. Exactly one shared structure per arm; open-loop schedules are condition-specific, as in the original T07 protocol.

## M1: fixed input

M1_B's original, saved 30-by-4 baseline sequence is available as the candidate-bound `HARD_CASE_SEED.json` Store trajectory. Its times, tension values and order exactly equal the immutable showcase M1_B schedule and its recorded baseline input. Replay the same numeric sequence unchanged on both arms; only the necessary design/model/task binding metadata is set. Reuse does **not** transfer acceptance from the showcase body or an earlier evaluation version. No matched `d0`-bound input was found for M1_A, M1_C or M5; do not upgrade different-model schedules or generate replacements.

## M2: symmetric finite reoptimization

Pair each archived `d1` numerical worker with one `d0` worker. Keep the original method, native objective, full horizon, constraints, optimizer tolerances, seed policy and **identical numerical warm start**. Only model/design bindings are changed. The frozen seeds are case-specific: transferred isotropic-root trial for M1_A, historical absolute schedules for M1_B/M5, and the archived A-derived warm start for M1_C. The M1_C number sequence is frozen for both arms rather than recomputed using each arm's A optimizer; this estimates a finite-budget result conditional on the shared archived seed, not design-neutral globally optimal capacity. The native settings in `optimizer_input.json` and the matched d1 archive include the safety margin, knots, step/radius and stop rules. The maximum was 2,600 evaluations/45 iterations on M1_A/M1_B/M5, 3,000/50 on M1_C.

An original local target reached plus a complete, valid registered independent evaluation is required for an observed M2 endpoint. Iteration-limit and numerical-failure outputs are retained as numerical diagnostics only; none is assigned a physical PASS/FAIL or used for a structure delta. No further change of basin, restart or solver is made to rescue a comparison.

## Scoring and provenance

For each frozen nonzero bound, signed excess is `-margin / abs(bound)`; `gmax` is the maximum across these constraints. `gap = max(0, gmax)` is also stored. Zero-bound and other validity gates are checked separately; comparable values require the unscaled gates to pass. PASS/FAIL is the frozen full-trajectory evaluation, not a diagnosis from the optimizer. Negative deltas indicate improvement:

- `ΔM1 = gmax(d1,U0) - gmax(d0,U0)`
- `ΔM2 = gmax(d1,U1*) - gmax(d0,U0*)`
- `Δd1,reopt = gmax(d1,U1*) - gmax(d1,U0)`

`source_sha256.csv` records archival and supplemental byte digests; `store_artifact_sha256.csv` records SQLite artifact-row payload digests. Historical Store/Trace bytes stay in the archive checkout. The new replay includes the actual compiled XML, samples, physical result and independent evaluator output; optimizer result gzip contains the complete numerical outputs.
