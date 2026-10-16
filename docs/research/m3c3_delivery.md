# M3-C3 delivery — 2026-10-16

M3-C3 is complete for the bounded offline mathematical-search milestone, with
the runtime and scientific limits below. It discovers concrete mathematical
candidates; it establishes no complete-task-feasible robot, global optimum,
real-time control, nine-segment dynamics coverage, or Agent efficiency advantage.

Branch: `feat/m3c3-mixed-family-search`; worktree:
`D:\softrobot-agent\.worktrees\m3c3-mixed-family-search`.
Starting commit: `4c4a491747ae0a674cbdc3a82c65b25de64a17f8`.
Implementation checkpoint: `7940e83b636152fa4ccdc5e3ac673c292e9d4388`.
Exact real-search binding: `e702fe9cd7eaeb0ee3db49e2b49bf9d48be9af77`.
Final production/test source: `72a9e60bdc488307892e4545e9083cb8e1dbb403`.
Later delivery changes contain documentation/evidence only. The final reply gives
the exact delivery HEAD and verified remote SHA. Other worktrees were untouched.

## Runtime diagnosis and admission

The retained failing XML from both C2 attempts has SHA256
`2f53a0dadae471cde5f2618a2a473275d19e16d55ebfccc826290ec0bc26c969`.
The [original XML](../../evidence/m3c3_mixed_family_search/original_six_segment_12_cell.xml)
contains 144 physical joints and three inputs. C2's original default-main-thread
failure remains `-1073741571` / `0xC00000FD` (stack overflow), with no physical
steps. No identical default-stack crash was repeated.

One discriminating contained child loaded those exact bytes on a **16 MiB thread
stack**, returning `nv=144, nu=3`, exit 0 in 0.283498 s. This supports a Windows
stack boundary; it validates only that loading method. The frozen final backend
continues using its original main-thread loader. No global thread setting,
geometry, contacts, discretization, dependency or acceptance rule was changed.
The alternate loader is not enabled for final execution or declared verified for
controller updates. See [diagnosis](../../evidence/m3c3_mixed_family_search/windows_loader_boundary.json).

Actual interpreter: Python 3.11.16, MuJoCo 3.13.0, CasADi 3.7.2. The platform API
reports `Windows-10-10.0.19044-SP0`, differing from the attachment's Windows 11
description; the evidence uses the observed value. Native library and interpreter
hashes, architecture, backend parameters and all three single-thread environment
variables are recorded. Original failure metadata did not contain native library
hashes: the new record explicitly identifies its current installation inspection
and imported historical observation, rather than claiming a new default-stack
measurement.

For new fidelity-policy studies, physical execution admission requires exact final
fidelity and an exact candidate/model/backend/environment capability record, or a
bounded contained preflight. Each native probe has durable launch intent, a
30-second engineering loading bound and a frozen count cap. Unknown termination
cannot relaunch automatically. Successful and failed exact records are reused;
other candidates do not inherit them. The imported C2 denial matches the exact
XML, backend and inspected environment and can only import the recorded failure,
never an unverified successful load. Its context is saved immutably in Store.

Capability evidence separates `design_valid`, `physics_compiled`,
`numerical_model_available`, `runtime_backend_loadable`,
`control_preparation_available`, `controller_update_verified`, and
`complete_task_evaluated`. Unknown numerical/control levels remain null. Native
failure returns `runtime_unavailable`, the failed boundary and original status;
uncertain or timed-out probes remain `runtime_unresolved`. Both retain
`task_success: null` and `physical_infeasibility_proven: false`. No mesh reduction
or redesign follows. Fixture tests bind the exact six-segment denial with zero
new probes, contain simulated native exits, distinguish other candidates, and
reuse exact successful capability records.

| Capability region | Evidence and limits |
|---|---|
| Physical generation, 1–9 segments | Existing C2 compiler evidence; no new complete topology grid |
| Four-cell XML, 1–9 / three tendons | Existing C2 loads; no dynamics/control inference |
| Twelve-cell default XML, 1–5 | Existing C2 loads for those exact examples |
| Twelve-cell default XML, 6 | Original exact native failure; conservative admission denial |
| Same six-segment XML, 16 MiB thread | One new successful load; alternate final runtime not enabled |
| Twelve-cell default XML, 7–9 | Unverified; no inferred failure |
| GVS/control, specific 1/2/3 cases | Existing C2 evidence; sealed short-control series not repeated |
| New bounded search | Actual one-/two-segment, three-/four-tendon GVS cases below |
| GVS/control, 4–9 | Still unverified; physical infeasibility is not established |
| 8–12 tendons | Still declarative, outside the executable grant |

## Fidelity and authoritative task acceptance

`numerical_fidelity_v1` is resolved and frozen in the existing study configuration.
The development policy authorizes `coarse=4` and `standard=12` cells per segment;
final evaluation requires exactly 12 cells and `backend.family_mujoco@1.1.0`.
Alternative final runtimes are empty. The frozen final-evaluation identity is
`defa9f6c914af60644a246516ecf5efba75218cfd1c46a6c9b0796afb72486a2`.

These cell counts identify the effective MuJoCo discretization. GVS analysis uses
the existing frozen controller basis and analysis protocol, not the number of
MuJoCo cells. Its actual model identity, coordinate/input order, construction
point and coverage remain in each mathematical result. No GVS cost reduction or
mesh-convergence claim follows from selecting `coarse`.

An additive physical-design identity hashes actual resolved physical structure,
excluding numerical mesh, task results and controller weights. The effective
numerical identity binds that design, mesh, dynamics model, backend and basis.
The original full scientific candidate hash algorithm is unchanged. Four- and
twelve-cell materializations share physical identity and have distinct full and
numerical identities. Request spelling remains provenance, as in C1/C2.

Execution admission rejects a screening model with `final_fidelity_required` and
no task outcome. `budget.observe_pass` independently checks final fidelity.
`feedback.result_view` also prevents selection of a provisional pass and requires
the exact candidate science/profile for new-policy results. Synthetic fixtures
show that an otherwise passing coarse result neither triggers success nor can be
selected; the matching final fixture triggers the existing gate and blocks
further expensive work. These fixtures are interface checks, not experiments.
Legacy studies without this policy retain their original acceptance semantics.

## Request and existing lifecycle

The Agent-visible `research_plan.search` union accepts the old `Search` and
`family_mixed_search_v1`. The new request supplies exact family identity, selected
groups, segment/tendon choices, permitted span strategies, optional section types
and smaller physical bounds, screening fidelity, scoped objective, proposal and
evaluation caps, stopping score/step, and optional parent/evidence references.
No full starting robot or nominal scientific reference is required.

Example `search` value, with the identity read from the frozen decision packet:

```json
{
  "version": "family_mixed_search_v1",
  "family_space_identity": "120f23ddcf625a2fe4c0c0bfad3ad8d7a0fa25d42654e22261f2757ba539c987",
  "variable_groups": ["segment_count", "tendon_count", "spans", "lengths", "materials", "sections", "routing"],
  "segment_counts": [1, 2, 3], "tendon_counts": [3, 4],
  "span_strategies": ["whole_chain", "distributed_consecutive", "distal"],
  "screening_fidelity": "coarse",
  "objective": "target_equilibrium_residual", "operating_point": "target_equilibrium",
  "max_proposals": 16, "max_evaluations": 8
}
```

`bounded_mixed_coordinate_v1` initializes from family-domain defaults, evaluates,
then makes deterministic discrete/continuous moves from the best observed proxy.
It rebuilds active segment/tendon coordinates after topology moves. Supported
section choices are circle, tube, ellipse and rectangle when granted; polar
routes have individual tendon angular offsets/radii and declared guide/anchor
stations. Bounds use `length_m`, `young_pa`, `section.<kind>.<dimension>` and
`routing.<domain>`. Cells are absent from physical search coordinates.

The supported objectives are target equilibrium residual and normalized held-input
position-output Gramian minimum eigenvalue. The latter has no invented task-pass
threshold. Both use existing scoped analysis applicability. Neither depends on
speed-cost weights, so selecting the `control` group explicitly requires a later
control-dependent evaluator and is rejected here. Generated controllers remain
fully defined by the granted defaults, including both weights 0.1. This milestone
does not claim control-weight optimization from insensitive proxies.

The same `search.py` loop owns persistence, budgets, pending work, evidence and
recovery for both contracts. `mixed_moves.py` is a pure conditional-move helper;
separating its arithmetic prevents Host/Store/provider concerns from entering
the numerical algorithm. `runtime_capability.py` owns one exact loader check and
uses the existing contained-process utility. Neither introduces a new scheduler,
research loop, Store, candidate registry, Agent, evaluator or optimization package.
The decision packet exposes allowed groups/fidelities, compact best-score feedback
and exact Store pointers. No live Agent/provider was invoked in this study.

## Actual bounded mathematical verification

New study: `m3c3-mixed-family-search-dev`. It has no scientific reference candidate,
the unchanged declarative 1–9 family, a 1–3 numerical search grant, zero provider,
RL, physical execution and complete-task allowances, and eight mathematical
evaluations. Each row below is a genuine existing GVS/analysis invocation.

| Proposal | Segments / tendons | Changed coordinate | Target static residual, m |
|---:|---|---|---:|
| 1 | 1 / 3 | Family defaults and authorized ranges | 0.12191467191886908 |
| 2 | 2 / 3 | Segment count | 0.015419372788427635 |
| 3 | 2 / 4 | Tendon count | 0.013872252322748684 |
| 4 | 2 / 4 | Distributed consecutive span allocation | 0.027801262160339582 |
| 5 | 2 / 4 | Root length | 5.324179660626445e-9 |
| 6 | 2 / 4 | Root Young modulus | 1.6212848724112968e-9 |
| 7 | 2 / 4 | Root ellipse semi-axis | 1.1834841497178348e-9 |
| 8 | 2 / 4 | Routing phase | 1.183484041825397e-9 |

Feedback is causal: proposal 3 uses proposal 2's candidate and analysis
`cb1475400fccb311c7e332ff8ce6c6e6c7a39b67a55e997bcd3e1fce9c3e376e`.
Proposal 4 performs worse; proposal 5 starts from proposal 3, using analysis
`792e6f15444531d402d7e65372b82053405d08148ef8cb6545e5ff10e87ac472`,
rather than adopting the chronological predecessor. A separate deterministic
fixture reverses the feedback and demonstrates a different subsequent proposal.
The final approximately 1.08e-16 m score difference is not evidence of a meaningful
physical improvement or numerical robustness.

The best observed candidate has two segments of 0.20 and 0.11 m; Young moduli
10.45 and 5.4 MPa; root ellipse semi-axes 0.01175/0.0076 m at angle 0.35 rad;
distal rectangular dimensions 0.0133/0.0095 m with its frozen station angles.
Four independent tendons each span segments 0–1, radius 0.018 m, guide station
0.5, anchor station 1.0, phases `[pi, 3pi/2, 0, pi/2]` and zero individual angular
offsets. Both control speed weights are 0.1. The effective screening model has
16 physical DOFs, 12 GVS coordinates, 24 states and four inputs.

Exact Store artifact identities:

- Original engineering research plan: `bf838883fbdf19f36e3557fed44c07722a41bda71b317de7320f66fcb8118ef3`.
- Search result: `5d59e00b1d8d5e15e0a9ccd390d0d5de2a5ce4ef86946143d007835e66791c31`.
- Checkpoint: `1ffbc5a31830d3e8574df5b11698cac412de9c0e422903fa47de2ec5063388c4`.
- Best candidate: `9cfc4af6424adce239b10ef62a07e4de75f414805d00e82980de7b50647dd96f`.
- Best analysis: `2d198c115f0bf5926eacdec6a4ce9189c70e967ebd9033638983400a3bdb472c`.

The [verification record](../../evidence/m3c3_mixed_family_search/search_verification.json)
contains every exact candidate, analysis, full request, resolved parameters,
physical/numerical identity and lineage. Original artifacts are stored once in
the [immutable export](../../evidence/m3c3_mixed_family_search/search/immutable_artifacts.tar.gz)
with its [manifest](../../evidence/m3c3_mixed_family_search/search/archive_manifest.json).
The first proposal has no parent and no fabricated evidence. Later decisions
name their actual incumbent, evidence used, changed coordinates, optimizer
origin, proposal identity, requesting plan, new candidate, score and cost.
Historical context or chronological adjacency alone never establishes improvement.

## Costs, recovery and tests

Eight proposals constructed eight distinct physical candidates and performed
eight mathematical evaluations. The eight GVS graph builds and equilibrium solve
attempts used 116 reported SLSQP iterations; low-level function-evaluation totals
are not exposed by this existing solver path and are not inferred. Proposal 4
hit its 20-iteration limit and retained its actual residual/failed construction
scope; it is not an infeasibility certificate. Proposals 1–4 have inconclusive
scoped claims. Proposals 5–8 have local static diagnostic claims, not task passes.

Mathematical worker time: **73.5400974002 s**. Construction: **2.1754866000 s**.
Cumulative numerical charge: **75.7155840002 s**; search elapsed time including
orchestration: **79.958263 s**. The separate loader diagnostic cost is 0.283498 s.
The shared ledger charged two public operations, search and STOP; internal
analysis attempts are additionally charged by the existing mathematical counter,
not misreported as public operations or physical launches. Limits were 16
proposals, eight mathematical attempts and 40 public operations. Termination was
`evaluation_budget_exhausted`, with no accepted task solution.

Provider requests **0**; RL training stages **0**; NMPC/controller updates **0**;
physical backend executions **0**; complete task evaluations **0**; physics steps
**0**. There was **one** new contained XML loading diagnostic. Mocked native
exits and synthetic mathematical/acceptance fixtures are not included as science.
No credentials were read, packages installed, or providers reconfigured.

The study is stopped, with null pending work and success gate, zero unsealed
calls and no occupied ledger resources. Checkpoint identity includes the typed
method/request, exact task/family configuration, bounds, protocol, fidelity and
profile. Proposal state is persisted before construction and evaluation. Exact
candidate results reuse immutable analysis evidence without new solves. Failed
construction retains actual elapsed charge and spends no unperformed math count;
failed workers retain their admitted count. Recovery fixtures interrupt after a
sealed score and reuse it, preserving parent/evidence links without recomputation.
Original plan recovery packages existing evidence; a new requested search can
resume the same exact checkpoint. An uncertain native/analysis launch cannot be
blindly repeated. The sealed real study was never reset, migrated or rerun.
Final source also separates original-search evaluation attribution from zero
additional cost on recovery, so an interrupted completed score still consumes
the original request's cap. A two-evaluation request was verified to stop at two
total evaluations despite interruption. Per-proposal construction cost is explicit
in final source; the real study retains its original aggregate construction cost.

**35 distinct selected test cases passed across focused batches**: 12 mixed-search
cases, 12 mainline cases, four count/search/success cases, one family-claim case,
three serial-family compatibility/preparation cases, two source-relative topology
cases and one legacy analysis/acceptance case. The historical configuration hash
remains `31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e`;
recorded v5 physical hashes and v3/v4 source semantics passed. Registered NMPC
and RL preparation interfaces passed without control or training. The sealed
M3-B/C1/C2 scientific evidence and study counters were not rewritten.

Development test failures were limited to four old test-module import errors
(corrected by including `tests/research` in the invocation path) and two new
synthetic fixture errors (missing compact-request length and wrong fixture metric
names). Affected tests passed after correction. Final tests retain the expected
simulated numerical/native failures as interface checks. No scientific worker
crashed in the new bounded study. Archive hashes and all member hashes were
independently checked. See [verification and per-file sizes](../../evidence/m3c3_mixed_family_search/verification.json)
and [module inventory](../../evidence/m3c3_mixed_family_search/module_inventory.json).

## Remaining work before M3-D

M3-D can use the mixed-search action and exact feedback pointers. Its next work is
to freeze a new authorized Agent study, select a meaningful comparison/budget
protocol, and evaluate how Agent decisions use mathematical feedback. It must
preserve this study's evidence and costs. Optimizing control weights requires a
control-dependent evaluator and new execution authorization. Integrating the
verified enlarged-stack loader into a declared final runtime requires explicit
runtime configuration and candidate-specific controller validation. High-segment
GVS/control support and 8–12 tendon execution remain separate technical work.
Final task feasibility still requires a newly authorized exact-final-fidelity
complete execution under the unchanged independent acceptance protocol.
