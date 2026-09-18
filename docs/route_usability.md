# Real-LLM route usability pass

Implementation and targeted verification are complete on `feat/independent-spatial-dynamics`, reviewed baseline `3efd9ca`. The seven-layer architecture, Host/Registry/Store, backend implementations, task and 10 mm tolerance remain in place. Real-LLM acceptance is **unverified**: this process has no `DEEPSEEK_API_KEY`. No live model request was attempted; no historical run was replayed, resumed or rewritten. No commit, push or merge was made.

## Diagnosed failure

Read-only inspection of `runs/route_protocol_20260918_105917` confirms 10 model requests: five inspections, four evidence reads and one build, with zero solves/evaluations. Its saved build decision explicitly expected `position_error` and a tip trajectory. The registered description did not distinguish construction from execution; there was no single-run action, and downstream actions required an optimization trial. The model repeatedly received a large route snapshot, with no compact record of recent inspections. Root paging could not subdivide a one-key `detail` wrapper, and content-only byte accounting allowed the response envelope to exceed Host's inline observation budget. The terminal summary did not explicitly label missing evaluation as incomplete.

## Interface and identity

The actual provider tool declarations now contain English action descriptions and field explanations, sourced from the registered manifests and Pydantic schemas. Derived catalogs are regenerated with `python examples/export_platform_contracts.py`.

| Action | Source and behavior | Charged backend attempts |
| --- | --- | --- |
| build | Authorized combination plus declared `changes`; saves a normalized immutable configuration. No score or trajectory. | 0 |
| run | Completed build `source_node`; preserves its candidate label and entire configuration; calls simulation then evaluation with stable request IDs. No search variables. | 1, or 0 when sealed work is reused |
| optimize | Optional build/run/optimize source; otherwise original baseline. `variables[path]=[lower,upper]` supplies numerical bounds, not samples. An explicit combination with a source must match its bindings. | Up to the bounded proposal count; duplicate candidates reuse evidence |
| diagnose / video | Valid run or optimization source; read saved trajectory/export evidence. | 0 |
| crosscheck | Valid run or optimization source plus an authorized alternative backend; preserves physical/control configuration. | 1, or 0 for sealed reuse |
| finish | Valid run or optimization source, even when its task tolerance is missed. Explicit evaluated delivery. | 0 |

`source_node` is a completed route node label, not an artifact ID. `candidate_id` selects an optimization trial (default: best valid), or must match the single built/run candidate. Changes come only from the authorized candidate space on build/optimize, including complete templates, physical parameters, discretization and controller parameters. Later actions cite a prior node's result in their nested `evidence` field. These references already appear in the overview; reading them again is optional.

The build's saved SessionInput becomes the run child snapshot. `simulation.run` prepares that same effective configuration with empty changes and binds the candidate to the saved result execution. Evaluation cites that execution, and diagnosis/delivery resolve its CandidateInput reference. Single runs have no fabricated search state. Existing immutable session comparison, parent/project budgets, sealed receipts and unknown-execution recovery remain authoritative.

The shared compact overview reports current selection, existing solves/evaluations, result references, legal combinations/bounds, budget and prerequisites. Frozen snapshot pointers expose detailed templates and configurations on demand. The model also sees four recent actions and the existing paging history. Evidence pages distinguish original content, navigation overviews and English projections, with offsets/counts and escaped JSON Pointers. Full evidence stays in Store. Page sizing includes the serialized page envelope and reserves space for Host's observation/receipt envelope; context limits were not raised.

Legacy task title/source and development provenance receive equivalent English projections without changing frozen records, identifiers, parameters or numbers. Known translations live in `tools/platform_language.py`. Unrecognized Chinese prose is reported as `ENGLISH_PROJECTION_REQUIRED` at its field path, rather than silently deleting information or sending mixed-language instructions; additional custom prose requires a local equivalent translation. No translation-model calls were added.

## Verification and judgments

Five focused route scenarios and the updated search-accounting helper check passed; the historical suite was not run. Checks used the `softagent` interpreter. Synthetic model/backend outputs are protocol evidence, not physical validation. The final synthetic provider payload was 27,018 bytes under the unchanged 60,000-byte limit, and its final observation was not truncated. The valid physical delivery returned CLI exit code 0 with unchanged accounting; a terminal route without evaluation returned 2.

| Scenario | Model network requests | Charged backend attempts | Evaluations | Evidence |
| --- | ---: | ---: | ---: | --- |
| Non-default build → run → repeated run → diagnosis → finish | 0 | 1 real MuJoCo attempt / 1 completed integration | 1 | Exact saved/effective configuration equality; repeated run reused both receipts; one diagnosis |
| Compact payload, oversized nested evidence, English projection, incomplete CLI result | 0 | 0 | 0 | Valid escaped pointers, pagination, no Host re-truncation, unchanged original task/evidence |
| Sourced optimization and failure before trial append | 0 | 1 synthetic | 0 | Source design/model/control preserved; charged attempt remains in ledger with empty trials |
| Provider correction, sealed receipt recovery, evidence read, crosscheck and finish | 0 | 2 synthetic | 2 synthetic | Seven synthetic provider responses including one two-call correction; no duplicate work on recovery |
| Existing optimization/deduplication and sealed-resume regression | 0 | 2 synthetic | 2 synthetic | No-source optimization remains usable; three proposals / two distinct candidates |

The physical check saved evidence in `runs/route_usability_checks/0435c91473e64d729f84cda487f4ea43`. Candidate `selected-tube` used `tube_distal`, near length 0.19 m, near discretization 4 cells, and feedback gain 5. Its evaluated position error was **0.05366764626319044 m (53.67 mm)**, so **task_success=false** against the unchanged 10 mm tolerance. This is a valid evaluated delivery, not a successful robot task. No alternative backend physical review or video was performed.

The synthetic provider scenario's final checked store is `runs/route_usability_checks/85d776fa1a2e4745a6e7666532e881f6`. Its ledger records seven model calls because it exercises the real adapter's budget path with a synthetic responder; these are **zero actual API requests**. Its two backend completions are also synthetic. Earlier iterations of the targeted tests remain separate and are not physical evidence.

Architecture/interface completion: verified within this pass's scope. Real-LLM autonomous evaluated delivery: **not verified**. Robot task success in the one physical check: **false**. Credential absence is the specific live-acceptance blocker; MATLAB runtime startup and independent physical review remain unverified here.

## PowerShell commands

Read the saved physical check without executing anything:

```powershell
Set-Location D:\softrobot-agent
conda activate softagent
$checkedRoute = 'runs/route_usability_checks/0435c91473e64d729f84cda487f4ea43'
python examples/workbench.py platform route status $checkedRoute
python examples/workbench.py platform route result $checkedRoute
```

For **one** fresh live acceptance, use the existing credential-enabled environment and existing runtimes. Do not edit the task or tolerance. Preparation retains the 10-model-request / 4-charged-backend-attempt project and session limits; corrections and failed attempts consume those budgets. The real model chooses the actions; no offline decisions are supplied.

```powershell
Set-Location D:\softrobot-agent
conda activate softagent
if (-not $env:DEEPSEEK_API_KEY) { throw 'DEEPSEEK_API_KEY is required in this process.' }
$freshRoute = "runs/route_acceptance_$(Get-Date -Format yyyyMMdd_HHmmss)"
python examples/workbench.py platform route prepare $freshRoute
if ($LASTEXITCODE -eq 0) { python examples/workbench.py platform route start $freshRoute }
$routeExit = $LASTEXITCODE
python examples/workbench.py platform route status $freshRoute
python examples/workbench.py platform route result $freshRoute
Write-Output "Acceptance exit code: $routeExit"
```

Operational failures return nonzero; stopping without an evaluated candidate returns 2. A valid explicit delivery that misses tolerance returns 0. Inspect `final.explicit_delivery`, `delivery_status`, `task_success`, counts and evidence separately. Old terminal records are not reset or migrated; dependency changes may require a new directory for further execution.
