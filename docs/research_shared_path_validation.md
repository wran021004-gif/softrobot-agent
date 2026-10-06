# Final shared-path development validation, 2026-10-06

The independently authorized single execution completed the final shared
catalog-bound preparation and receipt pipeline. The robot's joint physical task
failed holding speed. Integration completion and physical acceptance are separate
outcomes; no missing signal or incomplete execution was treated as a physical
failure.

The executed implementation is commit
`c80d331691b1a0f9d683049f1b09480c8bd62319`, with
`fixed_coordinate_reach_hold@1.1.0`, `shared.parameter_search@1.1.0`,
`candidate.family@1.1.0`, stable `controller.gvs_nmpc@7.0.0` and
`backend.family_mujoco@1.1.0`. No implementation repair or code edit occurred
before or after this attempt. The [pre-execution freeze](../evidence/research_shared_path_v11_approval_20261006/pre_execution.json)
records the commit, source hashes, dependency fingerprints, empty code diff,
reviewed input identity and authorization attachment hash. The runtime snapshot
is marked dirty because the new pre-execution evidence files were created before
Host creation; executed source hashes and dependency fingerprints match the
clean code freeze. Publication of this documentation does not rebind the real
result to a later code revision.

The ordinary documented `examples/fixed_research_baseline.py --mode smoke` entry
point projected the retained source into the current authorized builder, resolved
the shared parameter catalog, prepared a finite ask/tell proposal, constructed
the candidate and applied the frozen initializer. The common Host executed
`simulation.run`, `evaluation.run` and `control.profile_report`, all fresh with
`cache=new`. Final acceptance was assembled from the unchanged terminal evaluator
and sealed profile/motion evidence. No handcrafted backend call bypassed that
path. The authority index and target directories were inspected before launch;
neither contained this authorized attempt. The new Store is
`runs/research_shared_path_v11_approval_20261006`; it is now stopped, with zero
backend/tool slots remaining, and must not be reset or replayed.

Only near-segment section scale changed, 0.95 to 0.96. Near/far lengths remain
0.16/0.11 m, Young moduli 7.2/5.4 MPa, far section scale 0.95, and terminal/holding
tip-speed weights 0.05/0.05. The near elliptical section resolves to semi-axes
0.0096/0.00768 m. The case is the already exposed development case `near_z_plus`,
seed label 17, with total bend +0.01 rad and rate +0.02 rad/s mapped across the
twelve near z joints. The actual backend initializer exactly matches the reviewed
named position and velocity mapping. The effective execution input equals both
the owned snapshot and the [previously reviewed full input](../evidence/research_pre_study_revision_20261006/next_execution_input.json).

Simulated duration is 0.35 s, control/sample period 0.01 s and physical timestep
0.0005 s. Source-bound v7 initialization, warm-state regeneration and solver
stopping rules remain unchanged. Acceptance is still terminal/holding position
at most 0.01 m, holding speed at most 0.02 m/s in the inclusive final 0.05 s window,
six nonnegative tendon inputs bounded by 8 N, valid complete execution and zero
solver errors. Wall-clock real-time deployment is outside this offline protocol.

| Outcome | Observed value | Result |
| --- | ---: | --- |
| Execution and evaluation | Complete, valid; 35 control updates | Complete |
| Terminal position error | 0.0028029393033160714 m | Pass |
| Holding maximum position error | 0.004094678029888374 m | Pass |
| Holding maximum speed | 0.06758272073425946 m/s | Fail |
| Applied tendon tension range | 0.18790190600338286 to 6.162152221653249 N | Pass |
| Force-bound violation | 0 N | Pass |
| Solver errors | 0 | Pass |
| Joint physical acceptance | `valid_failure`, accepted=false | Fail |

All six holding samples at 0.30, 0.31, 0.32, 0.33, 0.34 and 0.35 s are available.
The last two speed samples fall below 0.02 m/s, but earlier samples in that same
required window exceed it. Terminal tip speed alone, 0.012106980829123433 m/s,
cannot establish holding acceptance. There are no missing signals or acceptance
issues. The execution selected 17 noninitialization plans and 18 initialization
plans. All 35 deadline misses remain reported, with mean complete update
16.802659108571657 s; they do not alter this offline physical classification.

The causal evidence chain is retained in the Store and portable immutable export:

| Artifact | Identity |
| --- | --- |
| Simulation execution | `8b8ce2691fc24b3392ff5e7fa4905ba4` |
| Effective candidate configuration | `a5bad0274360cb103c6e7056a88b5b539b12e9a6b38445bff3885f36e4c7ba72` |
| Official terminal evaluation | `d6896c85db290ca5bb7b343508546abba78e780ec73e470c13c0794840194456` |
| Execution-owned profile | `310cb1690b13def63b6c932e669eeaeec84db14288bcdcc4f9fedf13eaa64fcc` |

The [delivery](../evidence/research_shared_path_v11_approval_20261006/delivery.json),
[artifact manifest](../evidence/research_shared_path_v11_approval_20261006/artifact_manifest.json)
and [validation summary](../evidence/research_shared_path_v11_approval_20261006/validation_summary.json)
retain receipts, configuration, official evaluation, profile, raw backend exports,
six holding observations and component outcomes. Focused offline evidence checks
confirmed all three ledger calls completed fresh, binding consistency, exact
initialization, unchanged scientific settings, agreement with authoritative
acceptance, and all 35 exported artifact hashes against the Store. No new unit
suite, model request or backend attempt was needed for that audit. API credentials
were neither loaded nor published. Publication attributes preserve this export's
raw bytes: one staged raw artifact initially underwent automatic newline
conversion, which was corrected before commit with a rule limited to this new
evidence directory. A focused index check then compared all 35 staged artifact
hashes against the sealed manifest. This packaging correction changes no executed
code or scientific result and requires no additional backend attempt.

| Charged operation | Actual seconds | Authorized limit |
| --- | ---: | ---: |
| Simulation | 591.8589999999967 | 900 |
| Evaluation | 1.2969999999913853 | 30 |
| Profile | 1.1410000000032596 | 60 |
| Total | 594.2969999999914 | 990 |

Actual allocation use is one backend attempt, three charged operations, zero
model requests and zero experimental workers. There was no timeout, overrun,
cancellation, tuning, controller/code repair, runtime intervention or retry. Unused wall time remains
unused; exhausted attempt/tool slots prevent further work under this allocation.
Formal study allocations and historical unused slots were not consumed or
transferred. Earlier milestone protected files and prior study/smoke evidence
remain byte-identical.

The earlier execution `ef0a8703dff7494f8053e34067b33f7a` remains sealed as a direct
fixed-runner development smoke before the later shared planner/catalog bridge.
The intervening bridge checks were offline. This new execution verifies the
final shared preparation path with real closed-loop execution. Descriptively:

| Metric | Earlier direct smoke | Final shared path |
| --- | ---: | ---: |
| Terminal error (m) | 0.0028974459148354828 | 0.0028029393033160714 |
| Holding maximum error (m) | 0.0028974459148354828 | 0.004094678029888374 |
| Holding maximum speed (m/s) | 0.06773111912652348 | 0.06758272073425946 |
| Charged seconds | 336.3589999999822 | 594.2969999999914 |

Both fail holding speed. These differences establish no physical improvement,
robustness advantage or isolated cause: implementation fingerprints differ and
time-limited solver behavior matters. This is an exposed development observation,
not an unseen test, formal robustness repetition or candidate promotion.

Live LLM planning/context quality, native planner role/alias-ledger execution,
complete multi-candidate search, full matched robustness validation and the formal
three-group comparison remain unverified. This single run does not validate
those broader claims, and joint physical acceptance for this development candidate
remains unmet.

The next bounded research step proposed for separate approval is the frozen v1.1
fixed mathematical group only: at most 28 backend attempts, 100 workflow calls and
30000 charged seconds, with zero provider/worker calls. Preserve the split of
eight search/adaptation attempts, ten unchanged-incumbent validations and ten
validations for one eligible selected candidate over the same five cases and two
fresh repetitions. No eligible candidate leaves its ten slots unused. No LLM
campaign, three-group comparison or additional integration execution is included
in this proposal. Nothing further was launched.
