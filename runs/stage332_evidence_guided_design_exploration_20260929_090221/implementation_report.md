# Stage 3.32 assessed real experiment

**Evidence integration and fresh length exploration completed; no fresh covered
candidate passed, and provider-protocol failure prevented formal autonomous delivery.**
The model independently selected, built and evaluated four length-varying candidates
in one uninterrupted frozen replacement session. Every execution was valid and
complete, met the original multiparameter coverage rule, and failed the unchanged
0.01 m endpoint tolerance. The original provider output is preserved.

The best fresh candidate was `fresh_near0p168_far0p128_compliant_s1p05`, terminal
error **0.012611358712897407 m**. The supplied historical `rev_compliant_max`
remains better at **0.011787523596227019 m**; the fresh best is about 0.824 mm worse.
No historical case was rerun, charged, imported as an owner, or selected for delivery.

## Implementation and frozen conditions

Implementation commit: `d014e0f`; initial evidence/blocker commit: `c8f97a9`.
The starting tree was clean at `838a7d1`. Source hashes and both frozen input
identities remained unchanged through the genuine experiment. No dependencies
were upgraded. No scientific or model configuration changed after freeze.

The existing historical binding accepts the three explicitly selected Stage 3.31
cases, retaining source session/candidate/configuration/execution/evaluation/report
identities and comparing scientific conditions by value. Reporting-source hashes
need not equal historical implementation hashes. Small, attributed detail exports
permit ordinary evidence.read access without importing historical ownership.
Prior provider conclusions and the successful deterministic plumbing case were
not provided to the experimental LLM.

Normal route context now includes tested decision values and constants, historical
versus fresh samples, baseline deltas, comparisons to each prior case, explicit
build-parent changes where applicable, the best measured sample and remaining
resources. It distinguishes coverage from exploration. The three prior cases all
used near/far 0.170/0.130 m, scales 1.05/1.01/1.02, and compliant/stiff scenarios.

Motion feedback reports sampled minimum error/time, terminal error, signed world
position error, speed, final-window error change and earlier tolerance entry with
an outside endpoint. The late change is last sampled error minus first sampled
error in [0.30, 0.35] s. All are diagnostics, not new acceptance criteria or
continuous-time guarantees. New execution reports produce the same summary.

The brief makes analysis optional for free reach and ties it to a specific question;
tracking's existing prerequisite remains unchanged. It requires an LLM-chosen fresh
length change, evidence-based hypotheses, continuation while legal untested ideas
and resources remain, and explicit distinctions among success, budget limits,
blockers and voluntary stops. No numerical repair sequence was supplied by Codex.

The archived family experiment remains authority: target [0.29, 0.035, 0.19] m,
0.01 m reach tolerance, 0.35 s duration, 0.0005 s physics step, 0.01 s control/sample
period, 12 cells per segment, structural_linear basis, controller.gvs_nmpc@6.0.0
and its existing recipe. Scene, gravity, payload, routing, limits and initializer
rules are unchanged, with candidate-specific regeneration. Authorized bounds remain
near 0.15-0.17 m, far 0.11-0.13 m, scale 0.95-1.05 and baseline/compliant/stiff
numerical Young-modulus scenarios. Density and bending viscosity stay unchanged.

## Focused verification and actual context

Before freeze, `python -m unittest tests.test_stage332_exploration -v` passed the
combined saved-evidence check: original identities/facts, unchanged source state
and accounting, no owner import, zero preparation charges, exploration constants,
archived trajectory measurements, fresh report regeneration, scientific compatibility,
and the prepared high-effort DeepSeek request. One read-only replay also exercised
the new fresh-history and comparison paths. No full suite, plumbing simulation,
numerical sweep, controller benchmark or repeated physical-consistency campaign ran.
These checks were not repeated after the user's direct network authorization.

All 12 actual replacement request contexts contained the three prior cases.
Fresh feedback counts progressed from zero to four and included the saved motion
summaries. The fourth result was delivered in model-11's context before its malformed
response. Context and request references are retained in context_feedback_audit.json.

## Genuine experiment and actual designs

Frozen replacement: `gvs-live-b8f4ab5f17f2`, launched using the existing
resume_experiment.ps1 after the user's explicit DeepSeek transfer authorization.
There were no workers/subagents, human candidate guidance, manual argument
replacements, code edits or changes to frozen policy during this attempt.
Analysis was not called; it was optional for this controller. Each actual revision
was chosen by the provider, built through the normal route, and freshly evaluated.

All four used **section scale 1.05 and compliant numerical material scenario**.
Both previously constant lengths changed in every evaluated revision, by at least
0.001 m relative to the supplied cases. They changed together with near-minus-far
fixed at 0.04 m, so this phase did not isolate either segment's independent effect.
Fresh scale/material alternatives were not explored.

| Actual order | Near / far (m) | Terminal error (m) | Terminal speed (m/s) | Initialization / noninitialization accepted plans | Minimum sampled error | Late error change (m) |
|---|---|---:|---:|---:|---|---:|
| 1 | 0.1650 / 0.1250 | 0.019948497256371 | 0.228688243 | 35/0 | 0.019948497 at 0.35 s | -0.007672620 |
| 2 | 0.1680 / 0.1280 | 0.012611358712897 | 0.054835476 | 25/10 | 0.008876972 at 0.27 s | -0.000661106 |
| 3 | 0.1666 / 0.1266 | 0.024572848476715 | 0.233235682 | 35/0 | 0.024572848 at 0.35 s | -0.007624161 |
| 4 | 0.1675 / 0.1275 | 0.027270077243515 | 0.234807792 | 35/0 | 0.027270077 at 0.35 s | -0.007554490 |

Actual candidate IDs, in that order:

1. `fresh_near0p165_far0p125_compliant_s1p05`
2. `fresh_near0p168_far0p128_compliant_s1p05`
3. `b4_n1666_f1266_compliant_s1p05`
4. `b6_n1675_f1275_compliant_s1p05`

All had 35 accepted plans, zero converged updates, zero solver errors, zero force
bound violations and failed sampled settling. The second candidate entered the
0.01 m region at a sampled point (minimum 0.008876971545770093 m at 0.27 s), but
ended outside it. Its signed terminal error was
[-0.009164068142830828, 0.0013684988269518222, 0.008555316161285798] m.
Its final speed was 0.05483547565373871 m/s. These observations establish neither
settling nor real-time operation. All 35 control deadlines were missed in every
execution. Measured backend computation times were 648.906, 576.078, 646.750 and
648.328 seconds for 0.35 seconds of simulated motion.

## Protocol history, stopping and explanation audit

The first restricted-network launch (`gvs-live-06029f79f8b5`) failed before any
provider response or design action with DEEPSEEK_NETWORK_ERROR. Its one-request,
2.078-second charge remains in phase totals. The sealed original session was never
reopened. Automatic review then rejected the network launch; the user explicitly
authorized the payload and destination, resolving that approval blocker. The
replacement was already frozen with the initial charge deducted; no budget was
regenerated. blocked_launch_report.md retains the earlier checkpoint.

The replacement then made 12 actual requests. Significant protocol events:

- model-4 proposed the exact historical compliant 0.170/0.130 scale-1.05 design,
  contrary to the no-rerun brief. It failed for missing nested evidence before
  construction or execution. No historical rerun occurred.
- model-5 returned malformed JSON with trailing characters. The existing one-time
  protocol correction was scheduled and model-6 supplied a usable fresh build.
- model-8 added forbidden `reason_en`; schema preflight rejected it without a
  charge. The next response selected another legal fresh candidate.
- model-11 returned another malformed route.advance envelope, beginning
  `{"json">{"node_id"::`. It hinted at a different, independently varied length
  proposal, but no action from that response was executed. It was not a delivery.

The Host stopped with **MODEL_PROTOCOL_CORRECTION_FAILED** because the existing
protocol correction opportunity had already been used. This was not output
truncation, voluntary early stopping, budget exhaustion or a demonstrated code
defect. The frozen 131072-token/900-second length recovery was ineligible and unused:
all provider responses had finish_reason=tool_calls. No extra repair allowance,
manual JSON reconstruction or replacement experiment was introduced.

The Host automatically summarized the best fresh evaluated candidate. Its facts
match the sealed candidate/configuration/execution/evaluation/report exactly.
However, explicit_delivery is false, design_statement and result_statement are
absent, and their checks fail. **This Host summary is not provider delivery.**
There is no original final provider explanation to accept or rewrite.

The direct prose audit also records unsupported intermediate monotonic-length
claims (model-2/model-4/model-8), the attempted historical repeat, and an unproven
noise characterization in model-9. The original text is preserved. Interpolation
was mostly labeled as a hypothesis; actual failures remain failures. Independent
length changes and other legal combinations remain untested, and no global
infeasibility or optimality claim is supported.

## Separate assessments

| Criterion | Result |
|---|---|
| A. Prior evidence, exploration and motion feedback | Pass; verified and present in all actual contexts |
| B. Meaningful fresh exploration of unchanged lengths | Pass; both lengths changed in four complete evaluations |
| C. Complete autonomous workflow including delivery | Not achieved; autonomous selection/build/evaluation/feedback occurred, then protocol stop |
| D. Covered fresh original-task success | Not achieved; 0 of 4 passed |
| E. Fully supported provider delivery and stopping | Not achieved; no provider delivery or stopping explanation; Host stop is factually identified |

## Configuration and resources

All 12 real requests, plus the initial failed transport reservation, used
**deepseek-flash**, **https://api.deepseek.com**, thinking enabled, high effort,
max_tokens=65536 and timeout_s=600. The existing 1800-second backend reservation
policy was retained. No model, reasoning-mode or token-budget comparison ran.

| Resource | Used, entire phase | Remaining |
|---|---:|---:|
| Charged provider attempts | 13 (12 responses + 1 initial network failure) | 51 |
| Charged platform tool calls | 21 | 139 |
| Additional uncharged preflight rejections | 1 | n/a |
| Fresh backend attempts | 4 | 2 |
| Charged project wall seconds | 3059.688 | 18540.312 |
| Workers/subagents | 0 | 0 |

The 21 tool charges comprise 9 route calls (8 successful build/run actions and
1 failed evidence check), plus 4 simulations, 4 evaluations and 4 reports. There
were 22 platform invocations including the preflight rejection. Provider receipts
sum to 339439 prompt tokens, 105829 completion tokens (97935 reasoning), and
445268 total tokens. Currency cost is unavailable. Historical accounting is
separate and incurred no new backend charge.

## Evidence and reusable commands

The evidence index maps both frozen inputs, implementation identity, prior bindings,
initial/final exploration and motion summaries, all raw provider exchanges/configs
and receipts, actual candidates, evaluations, comparisons, the original malformed
response, Host summary, factual/prose audits, compressed ledgers and backend exports.
The live stores remain available. Credential values are absent from these artifacts.
Only local implementation and evidence commits were made; nothing was pushed or merged.

The exact launch was the existing phase script:

```powershell
& 'D:\softrobot-agent\runs\stage332_evidence_guided_design_exploration_20260929_090221\resume_experiment.ps1'
```

The replacement is now terminal and must not be restarted to discard this outcome.
For read-only assessment through the existing inspection entry point:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$taskInterpreter='C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
& $taskInterpreter examples/gvs_nmpc_route_experiment.py inspect --output runs/stage332_evidence_guided_design_exploration_20260929_090221/live_network
```

The concrete remaining blocker is provider tool-envelope reliability under the
already exhausted frozen protocol correction policy. Remaining resources are not
permission to reopen a terminal session or silently change that policy. This phase
ends with its real, assessed unsuccessful/incomplete outcome preserved.
