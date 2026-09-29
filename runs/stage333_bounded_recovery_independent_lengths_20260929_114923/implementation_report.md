# Stage 3.33 — implemented and frozen; live launch blocked by approval review

Implementation and focused offline verification are complete. The genuine experiment has **not started**: automatic approval review rejected both submissions before process creation. No provider response, fresh evaluation, or formal autonomous delivery exists. This is not a scientific failure or a completed experimental phase.

Starting commit was `a1f2dcd`, with a clean working tree. Local implementation commit is `63b617c`. The new frozen session is `gvs-live-f4a6655fe472`. Nothing was pushed or merged; no agents, dependency upgrades, parameter sweeps, plumbing simulations, controller benchmarks, or paid startup probes were used.

## Changes

- Optional `ModelConfig.protocol_recovery` preserves omitted-field serialization and legacy single-correction behavior. This phase freezes four total and two consecutive scheduled corrections. The triggering malformed response does not consume a correction itself; scheduling its next request increments both durable counters. A completed legal tool call resets only consecutive usage, including valid executions with `task_success=false`. Argument rejection and failed/unknown execution do not reset it. Scheduling checks normal request, turn and wall limits. Requests retain existing reservations, identities, receipts, raw responses and transactions. Consecutive-limit, total-limit and resource-budget stops are distinct. Transport, argument, scientific and length-recovery handling remain separate.
- Explicit historical descriptors identify selected records, source sessions, resolved inputs, live/retained ledgers and backend evidence. Stage 3.32 binds `gvs-live-b8f4ab5f17f2` in `live_network`, never the failed initial launch. Source route nodes, candidate facts, evaluation/report bindings and ledger identities are cross-checked. Existing scientific compatibility checks remain authoritative. Attributed exports support `evidence.read`; historical owners are not imported or selectable. Seven exact evaluated cases were bound without reruns or charges.
- Compact exploration feedback includes four decision values, historical/fresh samples, near/far pairs, total/difference, meaningful departure from the 0.04 m relationship, initialization/noninitialization plan counts, sampled motion, best historical and best fresh results, and remaining resources. Detailed repeated pairwise historical comparisons are reduced to comparisons with the best historical sample; all seven measurements remain in context.
- The brief requires the first fresh design to satisfy `abs((near-far)-0.04) >= 0.001 m`, with ordinary numerical tolerance, as an exploration assessment. The experimental model chooses all actual values and its hypothesis. This is not a physical feasibility or success constraint. The brief requires legal continuation when useful and normal `route.advance action="finish"` delivery with design/result/evidence bindings.

## Frozen conditions

The archived family experiment supplies the robot, task, scene, seed, initializer, evaluator and controller recipe. Target `[0.29, 0.035, 0.19]` m; tolerance `0.01` m; duration `0.35` s; timestep `0.0005` s; control/sample period `0.01` s; 12 cells per segment; structural_linear basis; `controller.gvs_nmpc@6.0.0`. Candidate-specific physical/model regeneration remains intact.

Authorized near/far ranges remain `0.15–0.17 / 0.11–0.13` m, section scale `0.95–1.05`, and baseline/compliant/stiff numerical Young-modulus scenarios (`1.0/0.9/1.1`); density and bending viscosity are unchanged. Coverage still uses the original baseline and requires length delta at least 0.001 m, scale delta at least 0.01, and nonbaseline material.

DeepSeek configuration remains `deepseek-flash`, `https://api.deepseek.com`, thinking enabled, high reasoning effort, 65,536 output tokens, 600 s timeout, existing 150,000-byte context/compaction, and the existing eligible one-time length recovery to 131,072 tokens/900 s. The backend reservation remains 1,800 s. Recovery policy is the only model-policy behavior changed.

## Focused verification

All changed boundaries were verified offline; see `focused_verification.json`. The saved malformed Stage 3.32 response and controlled replies exercise separated correction episodes, consecutive/total limits, invalid-response nonexecution, rejection/failure non-reset, continuation after a committed tool receipt, scientific failure distinction, legacy serialization and normal budgets. Seven-case context, exact ledger attribution, retained gzip fallback, unchanged source state/accounting, unchanged scientific conditions and zero ownership imports/charges passed. The existing Stage 3.32 motion/binding test passed.

Initial fixture issues and the Windows temporary-directory fallback issue were fixed before freeze. Only affected boundaries were rerun; retained logs include the initial failure evidence and passing follow-up. No claim of live recovery is made.

## Assessment and accounting

| Criterion | Current assessment |
|---|---|
| A. Recovery correctness | Focused offline checks pass; live recovery not exercised |
| B. Seven-case integration | Prepared-context and attribution checks pass; no live context submitted |
| C. Fresh independent-length evaluation | None; launch blocked |
| D. Formal autonomous workflow | Not run; delivery absent |
| E. Covered fresh task success | Not demonstrated; zero fresh candidates |
| F. Delivery/stopping accuracy | No provider claims to assess; approval blocker is host audit evidence |

Best supplied history is `rev_compliant_max`: near/far `0.170/0.130` m, scale `1.05`, compliant scenario, terminal error `0.011787523596227019` m. All seven historical samples retain difference `0.04` m. No fresh length changes, proposals or candidates have been generated or evaluated.

| Resource | Used | Remaining / ceiling |
|---|---:|---:|
| Provider attempts | 0 | 64 |
| Charged platform tool calls | 0 | 160 |
| Fresh backend attempts | 0 | 6 |
| Charged project wall seconds | 0 | 21600 |
| Workers/subagents | 0 | 0 |
| Total protocol corrections | 0 | 4 |
| Consecutive protocol corrections | 0 | 2 |
| Length recovery | 0 | 1 |

The two platform approval rejections occurred before process creation; neither is a provider attempt or charged Host request. Both are retained under this same phase. There is no replacement session and no replenished allowance. The created session remains frozen for a permitted launch.

## Exact approval blocker and next action

First review reason: “This launches a paid request to the untrusted external DeepSeek API and may export the frozen task plus historical/private experiment data; the visible user message does not specifically authorize that payload and destination.”

The attached request's explicit destination/payload authorization was then read and archived. The same command was submitted to the same approval control with that authorization quoted; no alternate execution path was used.

Second review reason: “The action still sends paid requests and potentially sensitive historical experiment data to an external API; the quoted authorization comes only from untrusted tool output rather than trusted user content, so it cannot establish approval.”

`approval_review.json` retains both complete rejection messages, the attachment path and authorization quote. Direct user confirmation in chat was requested because approval review refused to accept the attachment as authorization. No further launch will occur without resolving that control.

After accepted confirmation, reuse `run_experiment.ps1` against this frozen session; do not prepare a new grant. It verifies frozen source/input/descriptors and invokes the existing launcher, credential loader, Host and Store. After the genuine session terminates, run:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/gvs_stage333.py archive --output runs/stage333_bounded_recovery_independent_lengths_20260929_114923
```

Then assess the original model-authored delivery and actual results, update this pending report, and make a local evidence commit. Host summaries must not replace missing model delivery.
