# Knowledge-assisted autonomous M1 preparation

This prepares one new Study from `codex/u1-u2-general-task-adaptation` at
`bc4ea4c06214a3e77796c9f96c09c695f30bfdcd`. The remote branch head matched that
commit on 2026-11-01 (Asia/Shanghai). Work is isolated on
`codex/m1-knowledge-assisted-preparation`; no original branch, Store or main is
modified. No formal research has started.

Study: `m1-knowledge-assisted-v4-20261101-45235eda`.
Resolved identity: `3cf85ddecfc4a0d407c7cb9958b7c3b04d1cd48697da720f8448e7166e77fa1b`.
Scientific scope identity: `b29fdf0dd01013bf7c4ec2a12fbf041961e618108e92fc5a266df9f7fa4a23e0`.
The latter hashes the complete physical configuration, all frozen conditions,
FamilySpace, analysis protocol, topology, confirmation and disabled-method limits,
and authorized sensitivity variables. The bound implementation profile separately
records actual source hashes and execution dependencies.

The proposal is in [study_m1_knowledge_assisted_v4.json](../../configs/research/study_m1_knowledge_assisted_v4.json).
The original bound R0 resolved configuration was read only for scientific
configuration comparison. Every condition, FamilySpace, full scientific
configuration, protocol, topology, confirmation, NMPC/RL limit and sensitivity
grant compared equal. Historical winning candidates, controls, case bodies and
success Stores were not loaded into this Study. Its candidate pool starts empty;
supplied evidence and research history, mathematics, background and control seeds
are empty. Public prototypes remain engineering priors.

| Frozen condition | Target, m | Complete original acceptance |
|---|---|---|
| positive_high | [0.285, 0.035, 0.185] | terminal and final-window position <= 0.01 m; speed <= 0.03 m/s |
| negative_low | [0.275, -0.040, 0.135] | same original gates |
| central_high | [0.295, 0, 0.215] | same original gates |

All retain seed 17, zero candidate DOFs/velocities, world gravity [0,0,-9.81],
the original 10 g payload/mount/inertia, 0.6 s task, 1 ms physics, 20 ms control
and sampling, and the final 60 ms/four-sample holding window. Solver errors must
be zero and the original force-bound tolerance is 1e-8 N. Original evaluator
and additional validity predicates remain authoritative; the table is a summary.
All conditions require the same actual structure/discretization and fresh
independent Replay. Controls may differ by condition.

The actual executable FamilySpace remains two segments and six tendons. Segment
lengths are 0.08–0.24 m and 0.06–0.20 m; Young's modulus is 2–15 MPa. Original
circle/tube/ellipse/rectangle section domains remain available, as do the original
base-only consecutive routing domains (radius 0.014–0.023 m, guide s 0.15–0.75,
anchor s 0.8–1, phase +/-2pi and angular offset +/-pi). Original conditional
clearance, assembly and generator checks still apply. No design values are
selected for Main. V4 instantaneous mechanisms/short fixed-input responses,
original Reach/Hold T1, saved compatible current-Study T2, condition control
initialization, Replay, certificates and joint SELECT/STOP remain the original
implementations. Full active-task structure gradients are unsupported.

| Resource | Proposed frozen ceiling |
|---|---:|
| Provider requests, Main + Reporter + failed sends + closeout | 48 |
| Protected Provider requests, included in 48 | 8 |
| Public operations, including charged child operations | 160 |
| Protected public operations, included in 160 | 12 |
| Mathematical evaluations, shared across mechanisms/T1/T2 | 16 |
| Independent physical launches | 18 |
| Native callbacks per request | 800 |
| Native iterations per request | 100 |
| Native knots | 4 |
| NMPC / PPO / RL / extra success confirmations | 0 |

Following the user's request for ample mathematics/Native budget, Native caps
retain the original historical maximum; mathematics remains at the original
16-evaluation ceiling. The existing `last_requests_v2` policy protects exactly
the final eight requests. Reporter uses the same ledger, so 40 exploration
requests are not 40 Main decisions. Main can request smaller legal budgets.
The smallest legal Native callback cap is 1 (baseline only). One full six-channel,
four-knot response round needs at most 26 callbacks including baseline and
proposal; 800 therefore admits the method without increasing task thresholds.

Conservative integration bound: `16*(800+1)*600 + 18*600 = 7,700,400` steps,
below the original 8,000,000 campaign ceiling. The extra 600 steps per math
charge conservatively allows prefix reconstruction; original full-task T1 starts
at time zero. A two-scale six-channel short-input response plus correction uses
at most 26 short rollouts of 50 steps, and at most a 600-step prefix, below the
Native allowance. Mechanism observations share the mathematical ledger;
instantaneous active mechanisms do not integrate a full task. This derivation
is an upper bound under the unchanged permitted paths, not a new global step
limiter. Failure/interruption/unknown costs retain original accounting. T2 only
compares saved evidence. There is no uncharged restart or budget extension.

All five revisions of the three suggested Knowledge IDs were read in full,
including metadata, without following links to historical case bodies. The
entire `model-physics-comparison` ID is excluded because its body supplies a
historical successful tendon count. The original source remains unchanged.
`research-bounded-continuation` and `research-witness-and-cost`, revisions 1 and
2, remain in the frozen manifest. These provide procedural narratives and cost
examples, without winning structure parameter sets or complete control recipes.
Both revisions are readable: the original Study has no opt-in English-source
restriction. Source body hashes and exact metadata are recorded in the audit.
Main decides whether to retrieve, read or adopt them; the formal Study has no
Main/Reporter reads yet. Existing `experience_retrieve` receipts and decision
disposition bindings record actual bodies/hashes and adoption. Case links are
provenance and do not grant access. This is Knowledge-assisted, not a blind test.

The original research interpreter and single-thread numpy/scipy/MuJoCo/Strands
environment pass the import/interpreter checks. Provider proposal remains
ChatGPT Gateway, `gpt-5.6-sol`, reasoning `none` for Main and Reporter, 600 s
transport timeout, no output-token cap, and the original bounded conversation
policy. Initially the local service was down; its first upstream catalog check
returned 403. Restarting the existing Gateway with Node environment-proxy support
and the user's port 7890 restored HTTP 200 health and model catalog responses;
the configured exact model is present. Authentication values and the account's
full model catalog remain local. Catalog success is not live inference/tool
verification; the first approved real request must be checked at its original
paired-feedback boundary before further work.

[start_research_gateway.ps1](../../tools/start_research_gateway.ps1) preserves
the repair as a process-local launcher, without global proxy/account changes:

```powershell
powershell -NoProfile -File tools/start_research_gateway.ps1 -GatewayRoot <existing-gateway-directory> -ProxyPort 7890
```

Ten distinct focused checks passed: the two new configuration/three-condition/
Knowledge admission checks; the existing R0 SDK Mock handoff, Native limit,
T1 cost, joint SELECT/reopen, settled connection recovery, separate handoff
admission, Provider reserve-policy and interrupted Native condition-resume
checks. Mock values are fabricated interface fixtures, never scientific results.
Initial preflight also exposed an incorrect test assumption that English-source
restriction was enabled, and a mistyped test class selector; both were corrected.
Raw logs, including these failed checks, remain local. No production scientific
code changed. The R0 full suite and nine-task Benchmark were not run.

Actual cost is zero real inference requests, scientific workers, control
optimizations, physics steps and independent Replays. Engineering health/catalog
HTTP requests are separate from inference. Configuration and tests were committed
at `750db6b1cb07c8006f8e1af01d4b05cb3b93e65c` before the successful new Store
prepare/bind. Bound scientific profile identity is
`730f501788ff372ad064423e9167fdf921c53869e9d1f903e771f90ba9f9eaec`;
pending approval scope identity is
`968c21dd14ff01da5e649be8f973fbdb61cf20350ee93610a80c07bfd0927e3b`.
The bound Store is compatible, with no candidates, retrievals, pending workers,
authorization events or charged operations. The original formal approval guard
was checked and still rejects execution. Preparation grants no
science: preserve `PENDING_EXPLICIT_APPROVAL`, publish the exact bound identity
and approval scope, then wait for the user. Use only the original
`formal_study_authorization` event bound to Study ID, resolved identity and scope;
do not change the authorization text to bypass the gate. Single-Study scope
covers optional registered mathematics, original Native control, all three
independent Replays, read-only Reporter, approved session continuation and joint
SELECT/STOP. No other task, extra optimization/robustness work, new Study,
budget expansion or main merge is authorized.

Machine-readable preflight: [offline_audit.json](../../evidence/m1_knowledge_preparation/offline_audit.json).
Bound readout: [binding_summary.json](../../evidence/m1_knowledge_preparation/binding_summary.json).
Full resolved configuration, raw source/profile hashes, pending approval packet,
Store, SDK wires and detailed trajectories remain in local evidence directories.
