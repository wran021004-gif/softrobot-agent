# Base-only historical accepted package export

This tool exports existing selected witnesses. It does not search, dispatch a
study action, reinterpret acceptance, or write to an original Store. Full
packages, XML, controls, exact candidate identities and artifacts stay local and
private. Only tooling, fabricated tests and scalar audit summaries belong in Git.

Run from the separate export checkout, using the original research Python:

```powershell
python -m tools.base_only_export --source <owner-run-directory> --output <directory-outside-all-checkouts> --audit-only
python -m unittest tests.research.test_base_only_export -v
python -m tools.base_only_export --source <owner-run-directory> --output <directory-outside-all-checkouts>
python <output>/scripts/validate_package.py --package <output>
python <output>/scripts/view_trajectory.py --benchmark M1 --condition central_high --loop
```

The source directory contains M1–M6 `review_manifest.json`, `index.json` and
`private-store/platform.sqlite`. The source must be the historical selected
run, not an example configuration. `base_only_audit.audit` supports an injected
read-only Store host and `write_manifest=False`, avoiding `Host.prepare` and
updates to review manifests. Store artifacts retain their original hash checks.
The exporter additionally checks candidate/source/raw/evaluation/profile/task/
receipt bindings and copies the actual accepted execution XML by its SHA-256.

A fixed ignored `runs/base-only-export-20261028/ledger.json` and exclusive lock
reserve ten single-pass export replays, with a combined 6,700-step ceiling.
Changing `--output` cannot create a second grant. Started or failed captures are
never automatically retried. Static preflight occurs before reservation and
before any integration. A crashed operation retains its full reserved cost;
confirmed completed steps and diagnostics are separate from that upper bound.
Do not delete the ledger to retry scientific execution.

`playback_tensions` has optional `xml_path` and `step_observer` arguments.
Existing callers and evaluator semantics are unchanged. The default path still
compiles exactly as before. Capture uses archived XML. At t=0 and after every
actual `mj_step`, an observer receives a detached `mj_copyData` copy. All extra
forward calculations use that copy. The shared `MjModel` is read-only to the
observer. No intermediate forward operation touches live warmstarts or changes
the control-boundary operations of the historical loop.

The portable `scripts/playback_kernel.py` is generated from the authoritative
backend functions via Python AST. Only framework compiler imports and the XML
compilation expression are removed. Force binding, integer tick windows,
initialization, interval forward calls, integration, samples, contact tracking
and failure diagnostics remain the same code. Portable replay requires MuJoCo
and NumPy only; it never reads the original Store. Running `simulate_controls`
is a new explicit integration requested by that command, and was not performed
as an additional check during this bounded export.

Each benchmark shares one exact archived XML. M1/M2 conditions must match both
compiled dynamic/routing fingerprints and the complete XML after removing only
the optional `task_target` visualization marker. The actual original XML hashes
remain in condition provenance. The viewer hides the representative marker and
draws the selected condition's reference.

Each condition contains:

- `trajectory_timestep.csv`: t=0 and every post-step state, without interpolation.
- `control_schedule.csv`: exact ZOH intervals and six ideal tensions in N.
- `reference.csv`: visualization references with separate evaluator/window flags.
- `task.json` / `task_zh.md`: frozen goal, initializer, clocks, evaluator, limits,
  historical acceptance and unrounded numerical margins. M3 is a development draft.
- `replay_spec.json`, `configuration.json`: original physics, scene and initial state.
- `original_samples.json`, original evaluation/profile/receipt, exact referenced
  artifacts and provenance. Hash-addressed original artifacts remain unchanged.
- `validation.json`: export consistency, complete differences, environment and costs.

`joint_map.json` maps every CSV joint column to exact MuJoCo addresses and lists
tendon/actuator order. `structure.json` retains the original design, material and
section stations, cell physics, guide holes, payload tensors, body-local routing,
mount and tip frame. It is an ideal discrete model, not manufacturing CAD or a
validated hardware drive specification. Archived displacement actuator metadata
does not change the executed ideal tension channel semantics.

The validator makes no `mj_step` calls. It checks hashes, ten conditions, names,
dimensions, all clocks/finite values, controls, initial states, detached FK,
Jacobians, tool axes, COM force windows, original sample differences, Base starts,
shared physical structure and M6's rigid mass/COM/full inertia and contacts.
It reports integrity and reproduction separately from historical acceptance.
The 1e-9 diagnostic comparison tolerance never changes scientific task thresholds.
The manifest is a file-integrity inventory, not a cryptographic signature.

Windows Python 3.11 / MuJoCo 3.13 were used. Linux instructions are included in
the package but have not been verified. The standard MuJoCo viewer needs a desktop
and OpenGL; `--check-states` validates all saved poses without rendering or stepping.
