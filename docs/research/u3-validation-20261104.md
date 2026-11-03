# U3 bounded engineering validation

No new autonomous PHS/P3 research was started. External Provider requests,
RL, NMPC and M1 scientific executions were zero. The engineering Stores are
separate from the sealed original M1 Store. Its final SHA-256 remains
`e8cec2b77000b622617c1ac0e9eb213685fbcc5dd8b9b52e3741485454b8c9d4`.

Implementation: `03b626e`, certificate integration `e2337e6`, full-tail metric /
partial recovery integration `36cf0d9`. Saved-state tests use `8b83ff7`;
Reporter aggregate-cost and interrupted lower-bound delivery use `88c6e3b`.
Protocol integration observations below retain actual execution identity
`e2337e6`; later numerical reanalysis is explicitly zero-integration evidence,
not a new physical Replay or a rewritten historical acceptance result.

## Shared execution and scientific scope

Both task translations use the same registered goal/evaluator `2.0.0`, existing
`task.passive_response`, `passive_execution.execute`, contained Worker,
reservation, Store, TaskAdapter and acceptance path. There is no production
task-name dispatch or benchmark-specific physical runner. Test harness branches
translate frozen protocol fields and call those original interfaces only.

The ordinary generated structure uses two default prototype segments of 0.14 m,
two tendons, and each geometric rest length plus 0.1 mm payout. It is neither a
historical winning design nor M1's accepted structure. All thresholds below
come from original protocol files and source evaluators. No target was relaxed
to make this structure pass.

Original read-only sources include:

- `phs2d_protocol_inverse_v2.json`, `passive.py` and `phs2d_evaluation.py` in the
  PHS inverse-design worktree; relevant source history reaches `f42e863`.
- `passive_progressive_stiffness_dev_v1.json`, `passive_response.py`,
  `route_validation.py` and `passive_evaluation.py` in the P3 worktree; relevant
  source history reaches `f66bcce`.

Exact source byte hashes, effective task identities, candidate/result references,
Store locations, costs and test status are in
[the compact evidence record](evidence/u3-validation-20261104.json). Full local
delivery includes original-source manifest, actual schemas, protocol/effective
task JSON, raw reference links, SDK wire and measured comparisons.

## PHS representative cases

Two signs of 0.1 N at material coordinate 0.5, gravity [0,0,-9.81], original
mount, 21 material monitors plus separate physical tip, 12 cells per segment,
dt=0.000125 s. Each episode has 4 s unloaded preparation followed by 4 s loaded
execution; actual original source uses a 0.5 s **smoothstep**, sampled at interval
start. Observation interval is 0.01 s and tail is 0.25 s.

The final corrected task completed 128,000 physical steps, 515,208 native forward
calls and one model build (51.36 s end-to-end). Both unloaded and loaded tails
qualified under original speed, drift, balance, length and initial lateral
limits. It was a **valid task failure**: point dx about 4.3645 mm versus minimum
10 mm; tip XY about 9.251 mm versus maximum 5 mm; ratio about 2.12 versus 0.3.
Out-of-plane response stayed under 2 mm, including the separate physical tip.

Original-source comparison used 96,000 further integration steps and two model
compilations, with costs recorded in the same engineering Store. Force differences
were at most 1.53e-16 N; full position differences about 2.18e-7 m and final
position differences at most 1.18e-10 m. Original and U3 acceptance predicates
both fail on this ordinary assembly.

This is not a PHS equivalence certificate: the original loaded run resets
velocity, warm start and clock from baseline qpos; U3 continues the complete
qualified state. A source-backed cross-implementation trajectory tolerance was
not located. Compiled physical mass/stiffness inputs agree, but strict equality
of every compiled array is false: quaternion rounding and derived inverse-weight
arrays differ. Both facts remain explicit prerequisites for a formal task freeze.

An initial engineering translation omitted the separate tip-plane predicate.
That attempt and its original-source comparison remain retained and charged;
the corrected task was executed afresh. Its extra 128,000 + 96,000 steps are
included in the observed total, not erased.

## P3 five-stage and paired cases

Both signs at s=0.7 use 4 s each of unloaded, 0.05 N, 0.1 N, 0.2 N, recovery;
0.5 s endpoint-held smoothstep transitions, dt=0.000125 s and 0.01 s score grid.
Qualification uses every physical step in each 0.25 s tail. Limit solver settings,
strict thresholds and original registered stiffness/activation definitions are
retained. Stage scoring reductions use those frozen full-tail grids.

| Model | Actual steps | Forward calls | Native models | End-to-end | Acceptance |
|---|---:|---:|---:|---:|---|
| Two cells/segment, two arms × two signs | 640,000 | 2,655,016 | 2 | 436.24 s | INVALID |
| Four cells/segment, two arms × two signs | 640,000 | 2,655,016 | 2 | 469.11 s | INVALID |

Each arm has independent observations and native receipts under one aggregate
Worker reservation. Base compiled signatures, complete initial states, qualified
boundary states, solver settings and payout lengths agree between arms. The
intervention changes only selected tendon limit flags after common qualification.
Four complete trace CSVs total 328.7 MB for the coarse model and 561.0 MB for the
finer model; immutable byte artifacts and per-arm links remain in the Store.

All stages physically completed, but original static-balance requirements failed
in loaded/recovery tails; coarse high/recovery speed conditions failed too.
Unloaded qualification passed. Thus descriptive stiffness is not mechanism proof:
coarse ratios are approximately 1.0225/1.0220, finer 1.0167/1.0162, versus minimum
1.5, and the registered same-tendon slack-to-taut predicate is false. No stable
paired mechanism conclusion or new P3 success is claimed.

Original-source schedule comparisons performed and charged another 640,000 steps
per mesh. All four trajectories per mesh were complete, with point differences
at most 5.24e-16 m and force differences at most 1.20e-15 N. The original CSV
kinematic consistency check is 1e-10 m. The separate 1 mm half-step confirmation
bound is not promoted into a generic equivalence tolerance.

Original full-tail CSV reanalysis also returns INVALID. It exposed an initial
score-grid-only metric reduction error; the generic evaluator was corrected to
the declared qualification grid. Subsequent zero-integration comparisons show
mean displacement differences <=7.64e-17 m and stiffness-ratio differences
<=5.33e-15. Earlier comparisons, failed NumPy-scalar serialization and costs
remain retained. Forward/time counts lost on that failed direct audit are marked
unknown; they are never represented as measured zero work.

Geometry was legal at 2,001 score poses per episode. This is exploration scope,
not the original every-step final-witness geometry check. The historical coarse
success / finer INVALID limitation is not generalized; these ordinary designs
are INVALID at both tested meshes, for the recorded conditions only.

## Main, Reporter, recovery and regressions

Real SDK formatter + Mock HTTP used five scripted requests to route a candidate
and named intervention through the original Worker, deliver the certificate,
select the exact result and stop. This validates interfaces, not autonomous
scientific decision quality or real Provider token savings. Main never supplied
engine state vectors/matrices. Wire bodies were about 37–45 kB. Reporter received
source-bound phase/qualification facts; large traces and full states stayed in L2.
Control feasibility, Native active optimization and RL remained unavailable.
Reporter resources take the parent result's aggregate actual cost, avoiding
reporting the primary arm's 320,000 steps as a 640,000-step pair's total.
Interrupted resources are explicitly named lower bounds and retain uncertainty.

Saved-state result/episode references also reached the original Worker, restored
the exact recorded engine clock/full state, and rejected unowned source refs.
A hard-interruption fixture completed a 500-step baseline and six unpersisted
secondary steps. Recovery retained the 500-step durable lower bound, incomplete
CSV bytes and both budget slots; uncertainty remained explicit. Repeating the
same request launched no additional physics. Pending state was cleared only
after confirmed termination. No new state machine or evidence database was added.

Thirty-two targeted tests have passing outcomes: nine v2, nine existing passive
v1 and fourteen M1 admission/cache tests. An older unregistered-passive fixture
initially retained active actuators/controller and hit the correct mixed-physics
guard; its setup was corrected, with no production guard relaxation, and rerun.
The first failure log remains in delivery. No exhaustive repository suite is
claimed. V1 frozen tasks and original M1 evidence were not modified.

## Readiness boundary

The schema supports all ten PHS internal cases and P3's complete five-stage
paired evaluation. This is technical capability, not completed autonomous
benchmark validation. Before a formal Study:

1. Freeze PHS complete-state initialization versus original qpos-only reset and
   a source-backed numerical comparison criterion.
2. Freeze full domain, task versions, generation/initialization rules, Provider,
   mathematical and physical budgets, repetition policy and stop criteria.
3. Verify P3 half-step, 0.001 rad perturbation and every-step final geometry on
   qualified assemblies; never infer fidelity from the coarse historical result.
4. Keep `allow_benchmark_answers=false`, procedure-only curated Knowledge and
   explicit include IDs. Safe candidates include passive-force-response-research@2,
   model-physics-comparison@1, research-stable-start@2, skill-matched-comparison@1,
   and skill-witness-replay@1. They are methods, not current evidence. Exclude
   PHS/P3 success traces, winning parameters, optimization iterates and controls;
   do not expose raw provenance transitively as default Main context.

Nominal per-candidate physical scope: ten PHS 8 s episodes cost 640,000 primary
steps / ten episode slots; a P3 two-sign pair costs 640,000 steps / four slots.
All-arm half-step P3 confirmation would cost another 1,280,000 steps; the exact
confirmation scope still needs freezing. These are preparation estimates, not
new grants. No formal PHS/P3 configuration was activated or Study launched.
