# Stage 3.16: reusable public GVS NMPC capability

Implemented and committed as `ae2824d`, based on clean `feat/gvs-dynamics` at
`7faffeb`. The attached Stage 3.16 request supersedes the older Stage 3.12–NMPC
IDE context. Historical experiments and sealed reports are unchanged.

## Delivered capability

- `controller.gvs_nmpc@2.0.0` selects the versioned declarative
  `gvs_nmpc_free_reach_v1` profile. The original controller identity remains
  available at 1.0.0. Predictor and execution-model bindings remain distinct.
- `gvs_profile.py` checks exact physical/task/execution scope, coordinate and
  tendon order, units, dimensions, bounds and numerical content identity.
  Bundled historical numerical data are explicitly imported into the project
  Store. No production import of experiment scripts or private cache injection
  is needed. Current measurements, nominal metadata and numerical guesses stay
  separate; each execution has its own mutable workspace.
- `control.profile_describe`, `control.profile_declare_strategy` and
  `control.profile_report` expose preparation provenance, compact discovery and
  evidence-derived reporting through the registry/Host. Route overview points
  to the capability; build remains solve-free.
- `examples/gvs_nmpc_profile.py` orchestrates ordinary public requests. The
  predeclared strategy is validated through trusted new-run evidence and the
  existing skill lifecycle. One skill covers six selection/diagnosis topics;
  two memory notes provide inspection guidance. There is no human approval.
- Optional structured execution scope distinguishes matching validation,
  changed unvalidated starting points and incompatible configurations. Old
  unscoped skill hashes remain unchanged.

Production changes are in `extensions/tendon_family/{gvs_profile,gvs_reporting,
gvs_nmpc,candidate,manifest,route}.py`, the profile JSON, `schemas/skill.py`,
`skills/schema/skill.schema.json`, and `tools/{platform_skills,platform_tools,
skill_policy}.py`. The example, focused tests and `docs/gvs_nmpc_profile.md`
complete the public workflow.

## Fresh acceptance

Producer: `gvs-profile-d38694fc8e72`; execution:
`71ced9f839a045749eed8d2af8edca36`. One backend solve; no paid model calls.
The original 350 ms task, robot/materials, straight start, target, 10 mm
tolerance, ideal tension, 12 cells/segment, 10 ms controller period and 0.5 ms
physics step are unchanged. No code dependencies changed during execution;
`source_compatibility.json` confirms compatibility afterward.

| Result dimension | New measured result |
|---|---:|
| Complete / evaluator validity / official success | true / valid / true |
| Endpoint error | 8.473431 mm |
| Endpoint tip speed | 0.0209474 m/s |
| Final 50 ms sampled maximum error / speed | 8.694221 mm / 0.0315621 m/s |
| Additional sampled settling | **false** |
| Accepted plans / converged plans | 35 / 0 |
| Feasible early stops / raw `User_Requested_Stop` | 35 / 35 |
| Updates selecting regenerated initialization | 7 |
| Hold-last responses / solver-error flags | 0 / 0 |
| Maximum independently checked plan violation | 9.235746e-6 |
| Applied tensions / bound violation | 0.566200–5.025997 N / 0 N |
| Mean full update delivery | 24.446914 s |
| Mean preparation / numerical solve / validation | 9.305309 / 14.645962 / 0.254247 s |
| Workspace graph / solver construction | 1.288419 / 3.933086 s |
| Public simulation wall time | 859.906 s |
| Missed control deadlines | 35 / 35 |
| Sampled contacts | 0 |

The minimum recorded position error was 4.194189 mm before rising to the final
8.473431 mm. Maximum position/rate projection residuals were 2.472206 rad/m and
12.563365 rad/(m*s); the backend trajectory does not remain exactly in the GVS
subspace. `summary.json` retains every update's delivery time; the sealed exports
retain every observation, actual command and valid trajectory sample.

The unchanged ordinary `evaluation.run` succeeded within the planned budget;
no saved-evaluation continuation was needed. `evaluation.json` and
`evaluate_receipt.json` expose its result. `report.md` was generated from actual
data, without hard-coded success statements.

## Discovery and focused verification

The candidate strategy was defined and its hash declared before this execution.
The trusted reporting tool emitted new strategy-bound validation evidence;
`skills.validate` produced a **validated development** record, with
`human_approval=null`. `validated_skill.json` and the append-only
`development_skills/candidates` revisions retain this lifecycle.

A separate fresh Python process created discovery session
`gvs-profile-discovery-bc8da2407822`. Both public `skills.search` and Host context
retrieved the matching validated skill under `allow_development_skills=true`;
two memory notes were also available. See `fresh_session_discovery.json`.

Focused checks passed: fresh-process solve-free preparation and candidate
preflight; explicit numerical Store import; new-session skill retrieval;
changed-scope and corrupted-artifact rejection; saved reach/settling/incomplete
reporting; existing platform skill lifecycle regression. Small fixture and
candidate-normalization corrections were made before acceptance. No full suite,
gain search, historical LQR investigation or GVS/BDF rollout was run.

## Reproduce

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$out = 'runs/gvs_profile_reproduction'
& $py examples/gvs_nmpc_profile.py prepare --output $out
& $py examples/gvs_nmpc_profile.py run --output $out
& $py examples/gvs_nmpc_profile.py inspect --output $out
```

Use a new output directory for a new acceptance. To inspect this saved Store
without another solve, run only `inspect --output
runs/stage316_public_profile_20260927`. The resolved environment was Python
3.11.16, MuJoCo 3.13.0, CasADi 3.7.2 and SciPy 1.17.1.

## Remaining limits

No implementation blocker remains for this fixed public capability. It is an
offline ideal-tension simulation result for one task and initial condition.
MuJoCo low-speed settling failed; all real-time deadlines were missed. It does
not establish actuator realism, neighboring-task transfer, robustness, global
stability or contact prediction. The combined configuration evidence does not
isolate causal effects of individual settings. Copied Store files retain the
existing local authorization binding; fresh projects import the declared data
through the profile instead of copying authority or inventing historical receipts.
