# PHS-2D round-three isolated evidence

This package contains a ten-condition passive Base-only numerical witness, independent replay, half-timestep and initial-perturbation checks. It uses the unchanged development PHS evaluator, not a registered SELECT or hardware certificate.

- `solution/design.json`: complete candidate configuration, compiled physical parameters, fixed payouts, baseline, ten cases, KKT screen, modal diagnostics and normalized sensitivities.
- `solution/model.xml`: actual zero-actuator MuJoCo XML.
- `study_v1.json`, `study_v2.json`: all structures, screens, dynamic sets, failure records and audited costs.
- `store_v1`, `store_v2`: original core Store exports, receipts, immutable content-addressed artifacts and reconstruction manifests. Raw Store databases remain private under the isolated worktree's ignored runs directories.
- `experiment_journal.json`: hypotheses, variables, mathematical predictions, observations and cumulative budgets.
- `environment.json`: actual scientific Python/platform/package versions; `visualization_environment.json` records the separately installed plotting environment. No environment secrets.
- `curvature_evidence.json`, `numerical_comparison.json`, PNG/SVG figures: derived checks and visualizations.

## Verify without executing physics

From the research branch root using the recorded environment:

```powershell
python -m tools.phs2d_round3_export --verify
python -m tools.phs2d_round3_reproduce
```

The first command verifies part hashes, reconstructs each archive under `runs/phs3_archive_verify/`, and verifies every member hash. The second checks the delivered XML identity. These commands do not reopen sealed studies or consume integration steps.

## Inspect per-timestep data

Each independent loaded case in `solution/design.json` has `every_timestep_trajectory.archive_member`, identifying a `.bin` member of the v2 archive. It is a normal lossless NumPy NPZ container. Read it with `tarfile.extractfile` into `io.BytesIO`, then `numpy.load(..., allow_pickle=False)`. Arrays are `columns` and `trajectory`. There are 32000 rows per 4 s trajectory, 442 float64 columns: time, world-x force, 144 qpos (rad), 144 qvel (rad/s), 144 qacc (rad/s²), four lengths (m), four tensions (N). The unloaded trace is referenced from the baseline artifact in the same archive.

Rows are recorded after mj_step and the following mj_forward. qacc is the actual native recomputation using the generalized material-point force applied immediately before that step; regular 10 ms snapshots additionally remap the force at the refreshed geometry. This force-sampling phase is preserved explicitly. The independent evaluator retains its original 10 ms saved measurement phase. All per-step state/length/tension arrays are preserved; no float32 conversion or lossy compression is used.

## Execute a fresh reproduction

The user-invoked command below, from a clean committed checkout, creates the separately configured private reproduction Study, uses the existing candidate builder, Store reservations, native passive model and original evaluator, solves the unloaded state again and runs one baseline plus ten independent loads. Its hard cap is 500000 steps, 20 mathematical requests and one design; cumulative prior-study allowance is checked. This prepared recipe was not executed as extra search after finding the witness.

```powershell
python -m tools.phs2d_round3_reproduce --execute
```

It writes `runs/phs2d-isolated-reproduction/result.json` and seals its own Store. Repeating that command reads the sealed result; it never resets that ledger or reopens either research Store. A further execution requires a separately authorized, newly identified Study. The original in-study independent/convergence harness is `tools.phs2d_round3_validate`; its completed requests are archived, and its sealed Study is intentionally not runnable again.

The actual frozen mesh is owned by `generation` and compiled `physics.discretization`: eight cells per segment, 144 coordinates. The inherited protocol cells-per-segment default is not used to reconstruct a candidate.

No active motor/control input, extra world anchor or Tip spring is present. Mass, density, payload and physical installation assumptions are explicit in the design. Limitations include bending-cell idealization, frictionless cables, no axial/shear/torsion/self-collision model and sampled cable-solid checks rather than a continuous collision engine.
