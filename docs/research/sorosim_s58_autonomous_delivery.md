# S5.8 autonomous morphology–control research delivery

The bounded real DeepSeek/Strands campaign produced four fresh, complete,
independently evaluated MuJoCo results. **None passed the original task.**
Both NMPC executions completed all 35 controller updates without unusable
plans. Residual PPO initially improved physical holding speed, then a genuine
continuation with a stronger holding-speed reward worsened it. No solution
was selected. The remaining violation in every fresh evaluation is holding
speed; both position requirements passed.

The Agent made the experiment choices through the existing sequential
Strands executor. Numerical controllers, PPO and MuJoCo performed the actual
computations. The engineering driver did not choose its next experiment.
The campaign ended by engineering provider-count closure after four rejected
model STOP submissions, **not an accepted native model STOP**. Their original
justifications, errors, references and charged requests remain archived.

Repository/branch: `wran021004-gif/softrobot-agent`,
`feat/sorosim-matlab-nmpc`. Starting local and remote SHA:
`1aa392ee192dbc24b796ec9428229625c255f477`.
Identity/preparation commit: `0fc401ae5a090d43b87a1d7b59be3907aa5a8867`.
The complete live scientific source freeze, committed and remotely verified
before the first send, is
`e8df3565231f1ad1807650a4ef45ea4ff1adcba7`.
Post-campaign software repairs are `f73a94994b2af49b571b482ec988b4365fae3a2b`
and `a1a9b8dae0bab0e36212ba614e6b8a5914d78176`.
No physical or model execution followed those repairs. The final delivery
SHA is the commit containing this report; exact local/remote equality is
returned at delivery, avoiding a self-referential document hash.

The original task evaluator and scientific kernel hashes remain unchanged.
The effective task identity is
`882b3493037dcc8f8da294b3473e1223f0465e92c35bc3064bfc42d467bf212e`;
the canonical family task identity is
`fe7b95c3c1ba12659b59c1983544b6454c9d90ac42c4dec528e9736d99fd3a6b`.
The frozen registered protocol retains the 0.35 s duration, 35 intervals,
0.01 s control period, 0.0005 s physical timestep, original world target,
zero named joint initial state, 0.010 m position limits, 0.020 m/s speed
limit and inclusive 0.30–0.35 s holding interval. Each actual candidate has
four independently bounded [0,8] N tendon channels in original order.
No hardware experiment, force-bound relaxation or extra confirmation ran.

The mandatory projection audit used the saved S5.7 source states at indices
19 and 29, original MuJoCo joint addresses, the existing GVS projector and
inverse discretization, and `mj_forward`/site Jacobians. It used zero time
steps, NLPs or provider requests. Original archived outputs and projected
coefficient round trips matched. No coordinate, unit, indexing or binding
defect was found.

| Control index | MuJoCo reconstruction position m | Reconstruction velocity m/s | Original cross-model position m | Original cross-model velocity m/s |
|---:|---:|---:|---:|---:|
| 19 | 0.000495835 | 0.001188044 | 0.005642278 | 0.005155644 |
| 29 | 0.000578002 | 0.000813589 | 0.005549454 | 0.002081320 |

Remaining mathematical-versus-reconstructed kinematic differences were
0.005445990/0.005305117 m and 0.004909021/0.001389386 m/s. These are signed
vector decompositions in the underlying evidence; their norms are not
additive error shares. The comparisons support ordinary reduction loss and
different model kinematics at these states, without establishing a unique
dynamic error mechanism. Research proceeded to physical task experiments.

One sparse formal study reuses `family_study_defaults.json`,
`family_space_v2.json` and `control_sorosim_s56_braking.json`. Its executable
scope is two segments and four tendons. Existing length, material, section,
routing and two speed-weight domains remain available; the compatible
0.02 s brake-lead profile is frozen. Direct and residual PPO are both exposed.
Eight sealed historical evaluations were explicitly registered with their
actual candidate/controller/action identities, including nested S5.6 physics
and RL archives. S5.5–S5.7 packets are historical read-only context. S5.7 adds
diagnostic evidence, not another physical evaluation. Two exact sealed S5.6
PPO continuation sources were imported without charging their old actions.
The known Design B and compatible mathematical tension reference were
engineering preparation, consuming no experimental backend slot.

The real provider-free preflight recorded zero provider requests and zero
backend launches; it prepared the controller without MATLAB execution,
verified the pinned clean SoRoSim checkout
`24d573a3e864ffda87c42ee462a6ed620133cc7b`, and blocked the old NMPC science.
The provider endpoint/model were the configured DeepSeek chat-completions
endpoint and `deepseek-flash`. The existing credential loader and accounted
transport were used, with zero client/transport retries. Credentials were
never included in research payloads or evidence.

The Agent read actual historical packets, the experiment index and candidate
parameters. Its executed decisions were:

1. Increase tendon route radius from 0.018 to 0.023 m and declared servo gain
   from 900 to 1500 N/m, retaining speed weights 0.1. It hypothesized improved
   actuation authority and earlier braking, then requested full NMPC.
2. After the measured speed worsened to 0.104977 m/s, return to the original
   meaningful Design B geometry and set both speed weights to 1.0. Its Plan
   explicitly cites the first fresh result and rejects its prior hypothesis.
3. After the second physical failure, start a new residual PPO policy on the
   first candidate using that execution's exact actual tension reference.
   It chose 65,536 actions, `gamma=0.995`, rollout 512, batch 64, 10 epochs,
   position reward 1 and holding-speed reward 2.
4. Read the first independent PPO evaluation, then continue from its exact
   checkpoint for another 65,536 actions. The attempted gamma change was
   rejected. The admitted continuation retained gamma 0.995 and changed only
   holding-speed reward from 2 to 10; learning rate remained 0.0003 and
   `target_kl` remained null. Weights, Adam moments and optimizer counters were
   preserved; lifetime actions reached 131,072 with no optimizer reset.

This demonstrates actual feedback-conditioned changes of morphology, control
weights and learning objective. It does not establish Agent superiority.
The first residual policy was newly initialized because its new reference
differs from the historical policy's reference. The second stage is a genuine
continuation of that new lineage. Direct PPO remained available but was not
selected; the recorded rationale favored the already-reaching NMPC reference
and physical-state residual correction over the poor historical direct route.

Engineering supplied P0 results and the explicit ideal-tension interface
semantics during the first execution, before its result. It also exposed the
already-imported historical continuation-source references. These supplements
are identified as engineering evidence, not Agent discoveries or choices.
The actual first intervention remains new because routing changed. Its
servo-slew explanation is unsupported: ideal-tension execution bypasses
motor displacement/rate limits and length-servo gain.

The independent physical outcomes are below. All four new evaluations are
complete and numerically valid; NMPC solver errors/unusable plans are 0/0
for both runs, and both RL episodes have zero numerical failures. Original
NMPC force-bound violations are zero. Both RL trajectories contain 36 states
and 35 actions; recorded applied tensions range from 0 to 8 N.

| Fresh result | Effective intervention / route | Terminal error m | Holding error m | Holding speed m/s | Original task | Valid normalized gap G | Charged evaluation s |
|---|---|---:|---:|---:|---|---:|---:|
| `15cce2112131…` | Radius 0.023 m; NMPC weights 0.1/0.1 | 0.005726665 | 0.006938187 | 0.104976667 | Fail: speed | 4.248833 | 1718.838370 |
| `ad716d412cb2…` | Design B; NMPC weights 1/1 | 0.005483582 | 0.007462181 | 0.336118609 | Fail: speed | 15.805930 | 2041.117837 |
| `a323c9375b46…` | Residual PPO stage 1, new reference/lineage | 0.005917144 | 0.006618028 | 0.069612810 | Fail: speed | 2.480640 | 1.028259 |
| `88a9368baf27…` | Residual continuation, holding reward 10 | 0.006589360 | 0.007297400 | 0.109578213 | Fail: speed | 4.478911 | 1.028575 |

G is derived from original component limits for research comparison only.
It never changes acceptance. The best fresh valid result is stage-one PPO,
candidate `85b9126ceac7625f5b727729ee3d0eb36a27487e43e871e0430c441c2f3277d3`,
exact design SHA
`e370e9aebc93060ad08e1f91e548c49fd0768dc8e329645eb0f5f04409c65bd3`.
Its holding speed improved 33.7% from its own fresh NMPC reference, and its
normalized gap fell about 41.6%, while terminal error slightly increased.
The later continuation worsened both position metrics and speed.

Historical S5.6 still has the lower raw holding speed 0.041814094 m/s,
terminal error 0.006120972 m and holding error 0.006926834 m, but retains its
one unusable controller update and task failure. Its raw metric gap 1.090705
is not a fresh valid development result. The new campaign did not improve
that historical raw speed, and no historical failure was promoted to success.
Larger routing did not produce a passing result; higher NMPC speed weights
worsened physical speed. There is no fresh unchanged baseline or controlled
PPO morphology ablation, so these observations do not isolate a general
morphology benefit. Both new NMPC runs exercised the repaired final clock
boundary successfully; the unchanged historical controller was not re-run.

The checkpoint supplement preserves all 256 policy files, metadata, configs,
references, logs and evaluation trajectories. The two evaluated checkpoints are:

| Stage | Run ID | Checkpoint | Policy file SHA-256 |
|---|---|---|---|
| 1 | `sorosim-s58-agent-20261018-01da69f1` | `step-00065536-c803423f` | `c6fd77f1f9670600f2e19e8b4f7becaa161d056531f033a679abfa39c915764a` |
| 2 | `sorosim-s58-agent-20261018-fc761a15` | `step-00065536-49839429` | `92cc1ea3600e78e8a1a3e91944774024bdf74572d15ea4a2328bfd12f028cbed` |

The model also generated zero-speed-weight candidate `324f3a0d…`; it was not
physically executed. Its request to re-run the historical baseline was blocked
as equivalent/unresolved science without a replication grant. Zero-weight
execution was blocked by exhausted NMPC admission. Neither is a new outcome.
There were eight native-tool rejections: one extra Plan field, that historical
repeat, exhausted NMPC capacity, unsupported continuation changes, and four
STOP contract failures. The STOP failures concerned actual evidence reading,
training-summary read/citation, RL evaluation read, then omission of the two
NMPC result references. The Agent supplied real STOP justifications, but none
was admitted. The final disposition is the existing engineering count-budget
closure `07cf1eb663a27f72f8baf22fb593cd0bc528c9962013dfa376129d06e1e82670`.
It has `model_stop=false`, `selected=null` and no observed pass.

The model's consolidated narrative is retained as untrusted interpretation.
Its claims that the fresh NMPC runs were old repetitions, that historical
S5.6 was fully valid, and that servo gain supplies damping are incorrect.
No 15 rad/s mode, unique sway mechanism, fixed static pose, global
impossibility or continuous-time error bound was established. Increasing a
reward and adding training together do not isolate reward causality.

The finite accounting is preserved without reset:

| Resource | Actual | Frozen maximum |
|---|---:|---:|
| Outbound provider requests, including requests yielding rejected tools | 26 | 26 |
| Public operations, including engineering preparation/internal work | 39 | 90 |
| Shared backend starts | 6 | 8 |
| Complete NMPC executions | 2 | 2 |
| Fixed-tension physical replays | 0 | 2, within shared 8 |
| PPO training stages / new actions | 2 / 131,072 | 2 / 131,072 |
| Independent RL evaluation episodes | 2 | 2 |
| Full offline mathematical NLP / independent mathematical replay / analysis | 0 / 0 / 0 | 2 / 3 / 8 |

All 26 HTTP outcomes were received and archived; no provider outcome remains
unknown. The 32 original live tool requests comprise 11 `evidence_read`,
2 `retrieve_context`, 12 `research_plan` and 7 `research_rl` calls. The Plan
counts are generate 4, execute 4 and stop 4; RL counts are start 1, continue 2,
status 2 and evaluate 2. Attempt counts include the rejected calls above.
The protected 4 provider requests and 10 operations are within total limits.
Two backend slots and mathematical allowances remained, but provider capacity
was exhausted and NMPC/training/evaluation route limits were consumed.

The provider reported 4,952,134 prompt tokens (1,389,696 cache hits and
3,562,438 misses), 79,783 completion tokens and 5,031,917 total tokens.
Provider response time summed to 463.860 s. Recorded numerical work was
3991.172 s, including 3759.956 s for the two NMPC executions and 223.883 s
of actual PPO activity. The study elapsed 4529.014 s. These are distinct
measured quantities; the raw ledger also retains its original wall-time
semantics. The receipts provide no billed currency amount; money is unknown.
No real-time, repeatability, robustness or hardware result is claimed.

The post-campaign repairs reuse the existing owners. Historical evaluation
identities are cached in Store metadata, including nested archives; physical
replay can freeze an exact fresh passing robot/ordered sequence with its
original success gate. Inactive ideal-tension servo/motor fields and controller
costs are excluded from physical fingerprints. `effective_experiment_v3`
canonicalizes source numbers to 12 significant decimal digits for novelty
fingerprints, compiling those canonical numbers only for comparison. Exact
candidate bytes, solver inputs, policy files, ordered actions and acceptance
remain unchanged. Mixed identity versions are unresolved until explicitly
imported, preserving old semantics. Actual post-hoc comparisons confirm that
the routing case changes the robot and the weight case changes control only;
the 0.15 versus 0.15000000000000002 angle representation is not new science.
STOP errors now name exact missing references without auto-citing them or
accepting a fabricated model decision. Continuation sources are visible in
the native packet, P0/input semantics are included during preparation, and
sealed export recovers existing evidence without rewriting its archive.

Approximate source LOC relative to the verified start:

| Existing owner / new file | Added / removed | Purpose |
|---|---:|---|
| `tools/research/feedback.py` | +104 / -15 | Historical registration, effective identity, gap and strict selection |
| `tools/research/core.py` | +6 / -4 | Replay read/selection feedback and exact missing STOP citations |
| `tools/research/config.py` | +8 / -0 | Frozen executable scope and shared replay ceiling |
| `tools/research/budget.py` | +3 / -1 | Replay capacity and existing success gate |
| `tools/research/physical_replay.py` | +5 / -1 | Ownership/provenance and passing-result observation |
| `tools/research/rl.py` | +1 / -1 | Existing continuation-source visibility |
| `tests/research/sorosim_s58_agent_pilot.py` | +209 | Explicit existing-runtime driver and sealed recovery |
| `tests/research/test_s58_agent.py` | +115 | Seven focused fixture/real-history regressions |
| `study_sorosim_s58_agent.json` / shared defaults | +24 / +1 | Sparse study and optional shared replay cap |

Production growth is 105 net LOC; numerical kernels and the original evaluator
have zero changes. Two `.gitattributes` entries retain exact evidence bytes and
LF report text across checkouts. The final focused regression ran 70 tests: 69 passed and
one existing opt-in real-run test was skipped. An earlier sandbox run hit the
existing Windows TemporaryDirectory/SQLite access issue; the authorized
elevated run passed. No ordinary unit test launched a live experiment.

The most useful supported next controlled trial would fork the best stage-one
checkpoint, retain holding reward 2 and the exact reference, and test a
conservative optimizer change such as a lower learning rate with target KL.
This is an engineering proposal, not an executed or Agent-selected outcome;
it tests whether the observed continuation degradation can be avoided before
asserting a mechanical cause. The Agent's softer-structure suggestion is also
an untested hypothesis requiring candidate-specific feasibility and physical
evaluation. Its compliant-servo suggestion cannot work through this study's
ideal-tension input interface. No further trial is authorized by unused slots
after this study's provider/action budgets have closed.

Evidence is under `evidence/sorosim_s58/`. `summary.json` gives the compact
outcome; `decision_audit.json` links every original model request to the actual
decision packet, successful prior reads, feedback and costs. The unchanged
original views are `scientific_summary.json` and `raw_decision_audit.json`.
`projection_preflight.json`, `initial_research_packet.json`, `preflight.json`
and `identity_repair.json` separate engineering preparation and later repairs
from actual science. `checkpoints/summary.json` maps every raw RL file to its
Store artifact. No secret matches were found in either archive, including
checkpoint ZIP contents, and every manifest member hash was verified.
`environment_inventory.json` adds a read-only post-campaign executable/native
hash and package inventory: MuJoCo 3.13.0, SB3 2.9.0, CPU PyTorch 2.14.1,
Strands 1.59.0 and Harness 0.2.0. MATLAB Engine uses the existing R2024a
external `build/lib` path. This inventory is a later observation; original
source/dependency receipts remain the authority for the actual executions.

| Immutable archive | Bytes / members | SHA-256 |
|---|---:|---|
| `study/immutable_artifacts.tar.gz` | 6,523,256 / 434 | `fa6d14c5c97eae02a99b68fe8adde61e8fe970d1ed2b016731a72a900d48c3ae` |
| `checkpoints/study/immutable_artifacts.tar.gz` | 75,122,164 / 978 | `3aecd45d5eda3ad2b25026ff03a50f377ead416b1da5e7cd8a17beb2a15cc80a` |

The second archive is a post-closeout raw-checkpoint supplement, not a second
study or new scientific execution. The original scientific archive was never
overwritten. The delivery manifest hashes the report and compact files.
The exact original task remains unsolved; no passing robot/controller/policy
identity exists to select.
