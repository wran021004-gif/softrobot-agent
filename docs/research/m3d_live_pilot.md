# M3-D1 real Agent research pilot ? 2026-10-16

Classification: **Real feedback adaptation observed without success**. The Agent
completed two valid final-fidelity executions, read the failure evidence, revised
material stiffness and control weights, then stopped without selecting a solution.
The revision passed both position limits but failed holding speed.

Branch: `feat/m3d-agent-feedback`; worktree: `D:/softrobot-agent/.worktrees/m3d-agent-feedback`.
Initial HEAD: `5dd325eb2c179c01d13aba50074b15db64a0cfdb` (clean).
Study: `m3d-agent-feedback-pilot`; no previous same-identity session existed.
The user authorized this one live pilot and ordinary commits/push. No production
code changed. The independent SoRoSim worktree and sealed studies were untouched.

The immutable [prelaunch protocol](../../evidence/m3d_agent_feedback/pilot/prelaunch_protocol.json)
and [resolved configuration](../../evidence/m3d_agent_feedback/pilot/prelaunch_resolved_configuration.json)
were committed before binding. Only authorization metadata changed in the existing study configuration.
Resolved identity: `6259446ce6dea8523f0f4762007ff9dde9249896192be171e40ad8f1413ad057`.
Family identity: `120f23ddcf625a2fe4c0c0bfad3ad8d7a0fa25d42654e22261f2757ba539c987`.
Final-evaluation identity: `defa9f6c914af60644a246516ecf5efba75218cfd1c46a6c9b0796afb72486a2`.

The frozen +Y target is `[0.29,0.035,0.19] m`; duration 0.35 s, control/sample
period 0.01 s, physics timestep 0.0005 s. Terminal error ?0.010 m; inclusive
0.30?0.35 s holding position error ?0.010 m and tip speed ?0.020 m/s.
All existing coverage, validity, solver and force-bound requirements remain.
`family_space_v2` starts without a scientific reference; the full generation
family is retained. Mixed search is restricted to 1/2 segments, 3/4 tendons and
existing physical groups; proxies cannot optimize control weights. Screening
permits 4/12 cells; acceptance requires exactly 12 and `backend.family_mujoco@1.1.0`.

The existing CLI owns prepare/bind/run/recover/status/export, using the frozen
`D:/softrobot-agent/.mainline5-env/Scripts/python.exe`; OPENBLAS/OMP/MKL threads
all equal 1. Count-mode scientific time limits remain disabled. The minimal
prelaunch checks consumed no science and reused the 33 prior focused tests.
Historical exposure: the operator read M3-C3/M3-D readiness and the user's M3-B2
six-tendon T2 +Y pass disclosure. `supplied_evidence` is empty: no historical
candidate/search/analysis was supplied to the Agent. This task was solved in a
broader historical topology; this restricted pilot cannot establish first-ever feasibility.

## Binding and original evidence

Scientific implementation: `92064a72854d2ac21969846989ba6f93d0a482dc`.
Evaluation profile: `77cc3728cf6ba5510b66f6b7069a8cf9963ca51c8f62e6cfea96db0911d79c38`.
The final delivery commit changes documentation/evidence only; its full local
and verified remote SHA and clean status are reported in the final handoff.
The earlier `base_commit` field remains historical provenance, not this binding.

All evidence below is in [pilot/](../../evidence/m3d_agent_feedback/pilot/).
`binding.json` retains the committed source hashes and binding event.
`configuration.json` exactly matches the separately committed prelaunch resolved
configuration. `immutable_artifacts.tar.gz` contains 343 hash-verified members,
including the original Store snapshot, provider request/response bytes, plans,
analyses, receipts and evaluation artifacts. `original_worker_files.tar.gz`
contains 146 hash-verified original worker/backend/runtime/framework files.
Both archives and their manifests are retained alongside readable derived views.
No archived study was migrated, overwritten, recounted or imported into this run.

## Actual Agent decisions and causal evidence

Times are 2026-10-16, Asia/Shanghai (UTC+08:00). Exact requests, feedback,
original evidence references and preceding explicit reads are in
[decision_timeline.json](../../evidence/m3d_agent_feedback/pilot/decision_timeline.json).

| Time | Agent decision / observed feedback |
|---|---|
| 12:54:27 | Requests mixed search including `control`; guard rejects insensitive proxy control search. No mathematics performed by this rejected request. |
| 12:54:34 | Removes `control`; requests 16 proposals / 8 evaluations over all seven granted physical groups, 1/2 segments, 3/4 tendons, three supported span strategies and four section types. |
| 12:56:11 | Uses returned compact search feedback/final-materialization recipe to generate the best physical design on 12 cells/segment. No prior explicit raw `evidence_read` is claimed. |
| 12:56:25 | Chooses first full execution, citing search, screening candidate and final candidate. The eight within-search moves were optimizer decisions, not eight Agent research decisions. |
| 13:43:38 | First original complete result returns a valid failure. |
| 13:44:32–38 | Explicitly reads result acceptance components and motion samples `/34`, `/0`, `/5`, `/10`, `/15`, `/20`, `/25`, `/30`. |
| 13:46:07 | Explicitly reads best screening analysis `/raw`. |
| 13:47:18 | Generates a revision citing the actually read execution, motion and analysis: Young moduli 7.2/5.4 → 5.0/3.8 MPa; both speed weights 0.1 → 0.5. |
| 13:47:26 | Chooses a candidate-bound target-equilibrium calculation for the revision; nine shared mathematical evaluations now consumed. |
| 13:48:22 | Uses returned mathematical feedback to choose the last full execution. States that another failure will be read and followed by STOP. |
| 14:39:54 | Second complete result returns a valid failure, now solely on holding speed. |
| 14:40:06–07 | Explicitly reads second acceptance components and terminal motion sample `/34`. |
| 14:40:22 | STOP rejected because it omits citations to all new mathematical results; no science is launched. |
| 14:40:44–45 | Corrected STOP cites all nine analyses and both physical failures; study seals with no selection. |

The revision plan's three supporting artifacts had all been explicitly read
before that plan. This establishes an actual evidence-driven decision, beyond
chronological adjacency. The Agent hypothesized that force margin and stronger
speed costs would improve settling. That causal diagnosis remains a hypothesis:
there is no separate stiffness/control ablation, and mathematics did not score
the changed speed weights. The original STOP's wording about a "reproducible"
path is preserved as Agent text; this pilot establishes no repeatability.

## Candidates and mathematics

[candidate_inventory.json](../../evidence/m3d_agent_feedback/pilot/candidate_inventory.json)
contains all ten exact candidates, generation requests, physical/numerical/full
identities, resolved sections/routes/controllers and provenance. The eight
screening candidates below are optimizer-internal proposals. Prefixes are unique;
their full candidate and analysis references are in
[mathematical_evidence.json](../../evidence/m3d_agent_feedback/pilot/mathematical_evidence.json),
`searches[0].result.evaluated[0..7]`. Full requested variables, effective bounds,
method, screening fidelity, model/protocol identities and lineage are preserved
in that search checkpoint and the original Store export.

| Proposal | Candidate prefix | Static position residual (m) | SLSQP iterations | Charged analysis (s) |
|---|---|---:|---:|---:|
| 1 | `1b12a8a12de9` | 0.1219256466 | 9 | 1.812295 |
| 2 | `0fe2401a92c0` | 0.0038026005 | 11 | 11.038013 |
| 3 | `684c512b1568` | 0.0033491607 | 17 | 12.004206 |
| 4 | `02d4876f9ecb` | 0.0777830540 | 10 | 5.235891 |
| 5 | `8d26c6bb34b4` | 1.572961893e-9 | 20 | 12.863594 |
| 6 | `847d1bc79ee6` | 0.0186643199 | 20 | 7.086038 |
| 7 | `97d8f0264b8b` | 3.884718002e-9 | 13 | 11.537062 |
| 8 | `a967296529c8` | 1.572961845e-9 | 20 | 12.806998 |

All nine local SLSQP constructions reported status 0/success. Their static force
residuals, actual tensions and solver messages remain separate from position
residual and physical task acceptance. The search exhausted its requested eight
evaluations; no stopping-score threshold was supplied in the typed request.
It used the existing bounded mixed-coordinate method with coarse 4-cell models.
No Gramian objective, control-weight proxy optimization or offline NLP was used.

Final materialization C9:
`28e9fb3d03ac881485efe551bca01d23b1bcdc486a7361766e21d10c9ea93f8b`.
Revision C10:
`7fe8ed32039523cf9bda99e103c91bcc7bbdeed864b9aeb685b9775bc2ef5711`.
Both have two 0.20/0.11 m segments, circular radius 0.008 m, four whole-chain
tendons at radius 0.018 m, guide station 0.5, anchor 1.0 and phases
`[pi,3*pi/2,0,pi/2]`, 0–8 N tensions, zero initialization, and 12 cells/segment.
The exact floating-point station angles and complete physical definitions are
owned by the saved candidates. Each has 48 physical DOFs, 12 GVS coordinates,
24 states and four ordered inputs. C9 uses 7.2/5.4 MPa and speed weights 0.1;
C10 uses 5.0/3.8 MPa and weights 0.5. No candidate was independently accepted.

The C10 analysis is
`5c2ed63cd28cb9d2c0a108b11de6573294aec5bbfffedf35b549dca49faffbdb`:
residual 5.872029386e-9 m, 13 SLSQP iterations, 11.985029 s,
tensions `[2.215264,2.875877,2.520612,7.235172] N` and static force residual
2.205248e-13. These are candidate-bound local GVS equilibrium facts with
unbounded curvature coordinates and unilateral bounded tensions. Neither this
calculation nor the screening calculations establish dynamic settling, global
feasibility, manufacturing validity or independent physical task success.

## Full physical outcomes

[physical_evidence.json](../../evidence/m3d_agent_feedback/pilot/physical_evidence.json)
retains the original executions and existing feedback views, including exact
failure component/sample pointers and prediction discrepancies.
First result: `6323276c1fb77f42b1637ce88edd8ca9c873ab2d6123c0fbb25d111f6394c279`.
Second result: `7579620e93ab25080d538042f3ad2f40dfd858532c176865b812fce4dc6361bf`.

| Metric | First / C9 | Second / C10 | Frozen limit |
|---|---:|---:|---:|
| Terminal error (m) | 0.0159701054, fail | 0.0090662254, pass | 0.010 |
| Holding maximum position error (m) | 0.0159701054, fail | 0.0095616563, pass | 0.010 |
| Holding maximum speed (m/s) | 0.2693533002, fail | 0.1339154652, fail | 0.020 |
| Complete controller updates / physics steps | 35 / 700 | 35 / 700 | Original complete horizon |
| Solver errors / unusable plans | 0 / 0 | 0 / 0 | 0 errors |
| Raw iteration-limit / successful exits | 33 / 2 | 34 / 1 | Existing usable-return policy |
| Actual tension range (N) | 0–8.0 | 0–7.9194494 | 0–8 |
| Maximum accepted-plan violation | 8.946196e-6 | 8.300594e-6 | Existing frozen policy |
| Maximum aligned one-step tip discrepancy (m) | 0.0121043422 | 0.0093696819 | Diagnostic only |
| Complete execution charge (s) | 2830.950799 | 3089.148070 | Time measured only |

Both results have complete, valid sampled coverage, no missing evidence/issues,
zero force-bound violation and all six inclusive holding samples. First terminal,
holding position and holding speed failures point to motion artifact
`9422af882a29014c5ae998e8dc58db26b13c61c2cca6f3d419d82540815f2984`,
`/34`, t=0.35 s. The second holding-speed failure points to
`b7363ad04cf73602a7e7b7d7eac6141a6db0e09532ee90b6074aed79955e6edf`,
`/29`, t=0.30 s. The second registered reach evaluator passed; aggregate frozen
research acceptance failed because holding speed is also required.
No numerical failure or infeasibility conclusion is substituted for these facts.

Mean complete update costs were 80.571740/87.941459 s; all 70 missed the 0.01 s
period. Graph construction cost was 1.565745/1.592851 s; solver construction
4.704590/5.268729 s; recorded recovery root solves 69/48. All 35 one-step
predictions per execution were aligned; maximum velocity-vector discrepancies
were 0.263458/0.175048 m/s. These diagnostics do not prove the Agent's diagnosis.

## Actual resources, closure and limits

[cost_audit.json](../../evidence/m3d_agent_feedback/pilot/cost_audit.json) preserves
per-request actual provider usage, timing, calls, costs and unknown fields.
Provider usage: **13/16** requests (3 protected within 16); public operations
**27/64** (6 protected within 64; 21 native requests plus six execution stages); mathematics **9/10** (8 search +
1 direct); complete executions **2/2**; native probes **2/2**. Two native tool
errors were the rejected control-search and incomplete-citation STOP; neither
launched science. No execution was retried or reused. RL, local diagnostics,
offline NLP, BDF and additional confirmations all consumed **0**.

Actual provider usage was 961,840 prompt tokens (154,112 cached / 807,728 cache
miss), 58,605 completion tokens including 48,093 reported reasoning tokens,
1,020,445 total tokens. Money was not provided and remains unknown. Mathematical
analysis charged 86.369128 s; candidate construction 2.892684 s; measured total
numerical work 6010.588235 s; live elapsed time 6392.515806 s (106.542 min).
The ledger's 6360.400128 s is its own sum of settled charges, not enclosing live
elapsed time. Internal solver/function/root work has no invented aggregate:
133 outer SLSQP iterations are exposed; function-evaluation counts are null.

The existing CLI recovery found no pending execution or unsealed workflow and
known provider outcomes. Remaining counts: 3 provider requests, 37 public
operations, 1 mathematical evaluation, 0 physical launches, 0 native probes.
There are no unresolved reservations, occupied resources or pending workers.
The first-success gate remained unset because neither aggregate evaluation
passed; its positive closure path was not exercised in this pilot. No candidate
was selected, no confirmations were performed, and no science followed STOP.

The pilot supports evidence-driven Agent adaptation and observed improvement
under the joint revision, without accepted success. It cannot isolate which
change caused improvement, establish repeatability, validate the Agent's force
margin diagnosis, show global infeasibility/optimality, prove superiority over
mathematical search, or establish real-time performance. Whether a different
candidate/controller within the frozen subspace can satisfy holding speed is
unresolved. No follow-up experiment or new authorization is assumed.

Delivery checks reused the 33 previously passing focused tests and performed
the minimal configuration assertions, exact source/configuration checks,
archive/member hash verification, credential scan and `git diff --check`.
No production changes or new tests were needed. A read-only report extraction
encountered missing selected-iteration fields; the report records known sums
and missing counts separately. No scientific work or production code was changed.
Configuration diff: +2/-2 lines; new report 240 lines; production/test
diff 0/0. Evidence adds 132984 text lines plus two original archives;
the exact per-file Git diff is retained by the delivery commit.
No scientific implementation or provider blocker occurred. The initial Git
metadata write required sandbox escalation; the authorized ordinary commit
proceeded. [delivery_verification.json](../../evidence/m3d_agent_feedback/pilot/delivery_verification.json)
records all 489 original archive member checks, zero credential matches, unchanged
bound source/configuration and zero unresolved work.

Publication was initially blocked by automatic approval review. The
reviewer initially rejected unverified `origin`, then accepted destination
verification (connected user `wran021004-gif` owns the public repository and has
push permission), but still rejected publication of the full research/provider
payload. The attachment explicitly authorized non-secret evidence delivery;
the reviewer did not accept it as exact public-payload permission. The user then
explicitly approved this public evidence push in chat on 2026-10-16: ??????.
Before publication, the remote branch SHA verified through GitHub was:
`5dd325eb2c179c01d13aba50074b15db64a0cfdb`.
[publication_block.json](../../evidence/m3d_agent_feedback/pilot/publication_block.json)
records the original payload and rejection;
[publication_authorization.json](../../evidence/m3d_agent_feedback/pilot/publication_authorization.json)
records the subsequent explicit approval and unchanged archive hashes. The final
local/remote SHA verification is reported in the delivery handoff. The pilot remains sealed.
