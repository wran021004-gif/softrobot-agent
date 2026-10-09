# Research Mainline 3 V2

**The authorized V2 capability release is complete.** T1, T2 and T3 each completed a valid physical failure through the real public scientific chain. The native model used the finite public entry and delivered an evidence-supported report. No new incumbent, optimization gain or real-time control is claimed. [Completion](../evidence/research_mainline3_v2_20261009/completion.json) retains the exact outcomes, limits and cumulative usage; no genuine V2 blocker remains.

The finite public entry uses `candidate.family@2.0.0` and `controller.gvs_nmpc@10.0.0`. Version 10 inherits the V7 controller algorithm and stopping behavior. Historical versions retain their old compatibility envelopes. Supported task family: `task.reach`, with the declared serial bending model, frozen environment/backend and template-owned meshes. This release adds four explicit structural choices; it does not synthesize arbitrary topology.

The [committed catalog](../extensions/tendon_family/profiles/finite_templates_v2.json) contains complete designs, physical connections, guide/tip IDs, routing points, actuator specifications, transmission matrices, meshes, semantic initialization and template differences. [Frozen evidence](../evidence/research_mainline3_v2_20261009/frozen_templates.json) records the pre-execution choices; the [construction record](../evidence/research_mainline3_v2_20261009/construction.json) explicitly records each template's coordinate, state, backend-joint, tendon and actuator orderings. T0 comes directly from executed configuration `77a1406779dbbf5c440e8077796eeb222446001587d1a9befea0c64bbc146925`; its already-applied routing scales are not applied again.

| Template | Flexible / total components; lengths (m) | Tendons / actuators | Reduced coordinates / state | Backend position / velocity | Cells | Compiled mass (kg) | Sum of independent force limits (N) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T0 | 2 / 5; near 0.16, far 0.11 | 6 / 6 | 12 / 24 | 48 / 48 | 12 + 12 | 0.06781158427 | 48 |
| T1 | 2 / 5; near 0.16, far 0.11 | 8 / 8 | 12 / 24 | 48 / 48 | 12 + 12 | 0.06781158427 | 64 |
| T2 | 3 / 7; near 0.16, middle 0.055, far 0.055 | 6 / 6 | 18 / 36 | 48 / 48 | 12 + 6 + 6 | 0.06981158427 | 48 |
| T3 | 3 / 7; near 0.16, middle 0.055, far 0.055 | 8 / 8 | 18 / 36 | 48 / 48 | 12 + 6 + 6 | 0.06981158427 | 64 |

T1 places four channels at quarter turns in each region, using the executed first near/far route as the prototype. T2 adds an actual middle flexible component and a 2 g split guide with declared inertia; it preserves total flexible length, taper, material assignments and the 24-cell distribution. Distal routing includes the new middle/split/far stations. T3 combines these two changes. The added mass, routing stations and channel capacity prevent treating these cases as perfectly isolated performance ablations. Tendons and actuators have an independent identity mapping; each tendon has an enforced 0–8 N bound. The aggregate numbers describe available independent tension bounds, not a net tip force or motor power.

Public selection uses a named categorical choice:

```text
research.capability_catalog({})
research.select_template({"template":"T3"})
research.prepare_candidate({"candidate_id":"example-T3","changes":{"template":"T3"}})
research.candidate_dimensions({"configuration":<prepared configuration EvidenceRef>})
```

Selection uses `search.family_explicit@1.0.0`. Continuous coordinate search rejects categorical interpolation. Grants are intersected with the selected template's physical domain. Each active flexible component owns length changes within ±5%, section scale 0.95–1.05, material choices baseline/compliant/stiff, and routing-radius scale 0.98–1.02. These scales are relative to that selected executed-radius template. Middle parameters apply only to T2/T3. Holding/terminal speed weights remain publicly available over 0.025–0.10. The scientific cases use no additional continuous changes.

Named near/distal integrated bends and rates use local y/z axes with right-hand signs. The split distal region assigns bend/rate in proportion to component length. The new basis produces named backend joints and projection, rather than copying historical vectors by index. All scientific initial states retain archived zero positions and velocities, with zero projection residual and initial tip `[0.298,0,0.15]` m in world coordinates. The [nonzero offline fixture](../evidence/research_mainline3_v2_20261009/nonzero_initialization_fixture.json) records the split integrals, base-frame tip and projection residuals. T1/T3 use dimension-correct 0.2 N pretension; T0/T2 may reuse explicitly identified compatible historical tensions as guesses. Candidate dynamics regenerate warm states in every case.

The scientific pipeline is the existing `fixed_pipeline` with separate `v2-T1`, `v2-T2`, `v2-T3` identities, followed by public task acceptance. Preparation, linearization, control metrics, bounded endpoint, simulation, evaluation, profile and acceptance preserve exact configuration and original execution ownership. Task, seed 17, mount/gravity, target `[0.29,0.035,0.19]`, 0.35 s duration, 0.01 s control/sample period, 0.0005 s physics step, 0.05 s holding window, 0.01 m position criteria and 0.02 m/s speed criterion are unchanged. Horizon 10, weights 0.05/0.10, tolerance 1e-6, 120 iterations, 30 CPU seconds and 5/15 s feasible-return settings are unchanged.

T0's V1 execution remains historical evidence under controller version 9; its exact construction was checked through V2 without another simulation. T1–T3 each completed one valid 0.35 s backend execution and all eight public scientific stages. Every new case is a `valid_failure`, satisfying the finite interface-validation objective while failing physical acceptance. No tuning, additional seed, fresh T0 run or technical backend retry was needed.

| Case | Terminal error (m) | Holding max error (m) | Holding max speed (m/s) | Reach / holding position / holding speed | Mean update (s) |
| --- | --- | --- | --- | --- | --- |
| T0, historical | 0.003131444 | 0.003362290 | 0.026817671 | pass / pass / fail | 12.331832 |
| T1 | 0.066458183 | 0.194541251 | 4.390147373 | fail / fail / fail | 16.835042 |
| T2 | 0.011093378 | 0.023420466 | 1.121019770 | fail / fail / fail | 22.670960 |
| T3 | 0.103233020 | 0.202267189 | 3.772649367 | fail / fail / fail | 22.680832 |

Each new run has 35 updates, zero solver errors, zero solver-failure flags, zero hold-last responses and zero force violations. All have 35/35 deadline misses against the 0.01 s period; real time is not demonstrated. Fully converged / feasible-early-stop updates are 4/31 (T1), 0/35 (T2), 3/32 (T3). Initialization plans were selected 30, 33 and 31 times; accepted later plans numbered 5, 2 and 4. Feasible early stopping preserves the inherited V7 behavior and does not mean full optimizer convergence. Maximum motion projection residuals were 3.684061, 0.616291 and 3.111524 rad/m, distinct from the exactly representable zero initialization. These observations do not establish a unique physical cause.

| Case | Exact configuration | Original backend execution | Full summary / original receipts |
| --- | --- | --- | --- |
| T1 | `721f374f3703d5d08c8bd182788c11b32fc127dbec8249ef7295300e55e810b7` | `7099708881f242b1836e982bdf3374e1` | [T1](../evidence/research_mainline3_v2_20261009/T1_summary.json) / [receipts](../evidence/research_mainline3_v2_20261009/T1_receipts.json) |
| T2 | `6a6d863c8632871ef62b355acadcb58ec4cddf13c32d6d64e0e081b074a1718e` | `2b79f26a8efe487b8d5c7cb07c1cfe9e` | [T2](../evidence/research_mainline3_v2_20261009/T2_summary.json) / [receipts](../evidence/research_mainline3_v2_20261009/T2_receipts.json) |
| T3 | `073dc830fdaa5befca702642c80aefa8d275bea53e6f972d4c2ea1e643431d6b` | `0396ce298c2b4fdcbfee37766909af83` | [T3](../evidence/research_mainline3_v2_20261009/T3_summary.json) / [receipts](../evidence/research_mainline3_v2_20261009/T3_receipts.json) |

All nine public mathematical operations completed. Each case has available standardized-initial, controller-start and target-equilibrium local models; halfway-waypoint construction is unavailable. Position-only endpoint witnesses are feasible in the local affine models. Initial position-plus-braking is undetermined for every case; controller-start braking is feasible locally for T2 and undetermined for T1/T3. Target-equilibrium braking is feasible locally for all three. These statements preserve the diagnostics' local scope and do not establish physical task feasibility, settling or real-time control.

One real DeepSeek native session received the actual registered catalog and original execution evidence, selected/prepared T2, inspected dimensions, then ultimately selected/prepared and reported T1. It stopped after [the actual report](../evidence/research_mainline3_v2_20261009/native_result.json), preserving original execution `7099708881f242b1836e982bdf3374e1` and its owner. A first report used a preparation-wrapper reference and failed; all intermediate selections, three preparations, reads, failed/public final receipts and 14 complete responses remain saved. The coding-agent [material review](../evidence/research_mainline3_v2_20261009/native_material_review.json) checks the final dimensions, configuration scope, failure criteria and timing. Its stop-condition-list clause refers to configured allowed termination conditions; no observed numerical-failure cause is adopted. The acceptance report's zero new solves describes composition/reuse, while the original T1 run used one backend execution. This is an engineered capability-use test, with no duplicate simulation or extra paid reviewer.

| Capability | Represented | Publicly integrated | Mathematical preparation | Closed-loop evidence |
| --- | --- | --- | --- | --- |
| Exact T0 baseline | yes | V2 construction/selection checked | historical V1 preparation | historical controller 9 execution; no new controller 10 run |
| T1 eight-channel layout | yes | catalog, explicit selection, grant, preparation, dimensions | actual candidate-owned local models and endpoint analyses | one complete valid failure, 35 updates |
| T2 three flexible segments / 36-state model | yes | same public entry, owned mesh and initializer | actual changed basis/dynamics/projection and local analyses | one complete valid failure, 35 updates |
| T3 representative combination | yes | same public entry | actual changed state/input dimensions and analyses | one complete valid failure, 35 updates |
| Nonzero named bend/rate mapping | offline helper | scientific template entry grants zero initial state only | independent fixture and projection checks | no nonzero scientific run |
| Continuous design/control domains | explicit per-template domains | existing mutations, owner-specific applicability and grant intersections | focused selected checks; no exhaustive sweep | exact frozen template points only; no whole-domain validation |
| Independent actuator declarations | one-to-one mapping | actual candidate channel/force-bound preparation | ordered tension dynamics and force mapping | bounded ideal tension only; motor specifications not executed |

The controller executes `ideal_tension`: bounded forces directly actuate tendons. Declared actuator travel ±0.015 m, velocity 0.025 m/s, transmission and length servo are bypassed. Coupled/shared drives, motor-realistic execution, arbitrary topology, shear, stretch, torsion and friction are unsupported. Local Jacobians and bounded affine endpoint witnesses do not establish nonlinear or physical feasibility; unavailable or undetermined diagnostics are not infeasibility proofs. No incumbent is promoted and no optimization gain is claimed.

The [focused checks](../evidence/research_mainline3_v2_20261009/focused_checks.json) cover preservation/old-version rejection, public discovery and selection, input ordering/bounds, changed dimensions, nonzero named initialization, independent finite-difference routing/virtual-work consistency, ownership, receipt recovery, a public chain with an explicitly labeled static backend substitute, and the actual native request/schema capacity path. Only affected checks were rerun after fixture repairs. No full suite, stress campaign, parameter sweep, paid connectivity probe or extra model reviewer was run.

The native report allowance is 1 MiB, with no 3,000-character prose limit. Actual outgoing requests used the existing 950,000 conservative input-estimate ceiling, 1,000,000 total context, 4 MiB serialized allowance, 32,768 output/8,192 interaction reservations and 600 s provider timeout. [Request measurements and actual provider usage](../evidence/research_mainline3_v2_20261009/provider_usage.json) keep these quantities separate: maximum serialized request 205,517 bytes and maximum conservative estimate 213,709; estimates are not provider-reported tokens. After the session stopped, reference descriptions and handler feedback were corrected to identify `PreparedCandidate.configuration`; the [affected saved-failure check](../evidence/research_mainline3_v2_20261009/native_saved_failure_check.json) passed with zero new provider/public/backend calls.

Use was **14/40 provider requests**, **811,538 prompt + 78,030 completion = 889,568 reported tokens**, **39/1,024 public operations**, **9/32 public mathematical operations**, **3 backend attempts**, and **105 internal NMPC updates**. There were zero backend retries and no fresh T0 execution. All 14 complete responses have usage records; monetary cost remains unknown. One original grant and the original 12-hour clock cover the whole activity, with the final 30 minutes protected. Recorded initial engineering is 1,257.612 s. Final elapsed time, charged wall time and remaining review/delivery overhead are separately recorded in [completion](../evidence/research_mainline3_v2_20261009/completion.json) and the [cumulative ledger](../evidence/research_mainline3_v2_20261009/cumulative_ledger.json). Interventions cover candidate-owned initialization, pre-dispatch snapshot serialization, Windows fixture ownership/cleanup, catalog provenance and native reference feedback; none reset usage, replaced the grant or changed scientific conditions.

Scientific dependencies were frozen at `9534443dfbf86393b18703340bf6290a125757d8`; the native session used `b08b0f6a92648250f52da1318659daf9b675e3b2`. The [manifest](../evidence/research_mainline3_v2_20261009/validation_manifest.json) records current implementation hashes and original dependency snapshots. The [lossless Store export](../evidence/research_mainline3_v2_20261009/store_manifest.json) preserves original JSON/binary bytes and owners. [History verification](../evidence/research_mainline3_v2_20261009/preservation_review.json) confirms the protected V1 records unchanged. The installed environment remains Python 3.11.16, NumPy 2.4.6, SciPy 1.17.1, CasADi 3.7.2, MuJoCo 3.13.0 and Pydantic 2.13.5.

Mainline 4 can start from the saved [T1 configuration and finite pool](../evidence/research_mainline3_v2_20261009/mainline4_start.json), with no incumbent claim:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m tools.research_v2_entry --prepare --template T1 --output runs/mainline4_finite_entry.json
```

This preparation is solve-free. Future scientific execution uses the same public catalog, selector and scientific pipeline through `--run-with-grant <new ProjectConfig JSON> --directory <new store>`, under separately supplied Mainline 4 authority. V1/V2 activities and unused capacity are not reopened or transferred. The historical [handoff](research_mainline3_v2_handoff.md) remains preserved beneath its new current-status entry; this completion document supplies the new capability map.
