# P6.3-F1: result feedback and frozen F2 design

Baseline: published C3 commit `f49014880525bfb510499050c4cb829a2dbb0567`, independent branch `codex/p6-3c4-result-feedback-validation`. The preceding [F0 audit](p63f0_feedback_audit.md) was written from original read-only C3 evidence before production edits.

## Minimal change

`research_context.py` projects result-index progress from existing confirmed `read_coverage` records. It distinguishes unread, confirmed unchanged and new-result content; the last confirmed classification distinguishes exact repeats. Full result body reads remain separate, with no inferred comprehension or independent SELECT qualification. A returned tool response awaiting the next actual Provider wire remains pending confirmation.

`core.read_tool_evidence` wraps only the Main working-set `/all_fresh_results` response with the original result list and descriptive progress. A confirmed repeat explicitly says the unchanged index adds no new scientific information; reading a concrete result or making an independent judgment remains optional. Repeats are permitted. Internal `read_evidence` still returns the exact original list. Coverage hashes the list rather than its changing descriptive metadata. No second read ledger, blacklist or automatic action was introduced.

The existing compact `information_flow_brief` switches to `post_result_decision` only when the recorded latest mathematical result belongs to the current Main Plan in the original action trace. A later Plan therefore retains its own execution-preparation handoff. Completed requests no longer show the stale instruction to submit the previous scientific question. The view references the Main hypothesis/Plan, one numeric fact owner, original limits, non-authoritative saved Reporter interpretations, index/body progress, legal action directory and shared remaining resources. It assesses no hypothesis and chooses no next action. The current method progress uses original ScientificQuestion compilation receipts instead of leaving a legacy optional intent label looking unexecuted; compilation is identified as the selection source.

The Native method detail already explains `S baselines + sum(D_i probes + 1 proposal)` within the callback cap. Its latest result now exposes actual active dimension, requested callback budget, the nominal one-baseline `D+2` first complete response cost, and original completed response count. Clipping, inactive probes, failures and additional starts/updates qualify this estimate. This is information only; the optimizer, Worker and physical behavior are unchanged.

`reporter.py`, `agent.py`, `scientific_intent.py`, mathematical kernels, evaluator and Store are unchanged. Existing STOP complete-result citation and independent SELECT/full-read gates remain in force. One existing protected-read test now checks the original list inside the public wrapper while still checking the unchanged internal list.

## Offline acceptance

`test_p63f_result_feedback.py` uses the actual SDK with Mock HTTP, fabricated native outputs and guards against real Provider/Worker/physics. It verifies available/unavailable/missing Reporter interpretations, fixed-fact delivery, post-result phase, freely retained scientific tools, first/repeat/new index delivery, canonical coverage classification, and separate full mathematical body reading without independent evaluation credit.

Directed regression also covers the C0 catalog, C1 state-aware discovery, C2 compilation/C3 three-node handoff, original action interface, evidence-policy gates and exact independently passing SELECT admission. Logs remain in ignored `runs/f1_directed_tests.log`; no historical nine-trace science was rerun (the catalog test only checks its saved audit).

Result: all 35 directed tests passed in 226.058 s. `git diff --check` passed. The F1 wire tests were additionally rerun after the final descriptive metadata and later-Plan phase regression were added.

## F2 authorization and resources

The user explicitly authorized real models, continuous execution and no further approval request. Exactly one new Study uses the same original M3 0.50 s Reach/Hold task, final 0.05 s hold, 0.01 m position and 0.02 m/s speed thresholds, original 0.0005 s integration step and Operator initial structure/full baseline schedule. Original task, family, control and protocol equality is checked at configuration; effective robot/physics equality is checked at preparation. No C3 scientific result is imported.

`study_p63f2_m3_result_feedback_sol.json` retains `gpt-5.6-sol / none` for Main and Reporter. Provider ceiling is 20 total, including Reporter, failed sends and protected closeout (one reserved request). Required public/math/backend/local/NLP/BDF counts are 1,000,000, with no scientific time ceilings. Optional independent replay and training-action caps are absent. Native limits are the original contract maxima: 1000 callbacks, 100 iterations, four knots. All four versioned special mathematical grants and existing analysis, GVS/mechanics, structure/control search, NMPC, replay and PPO capabilities are authorized, subject to their original environment, applicability and evidence admission. No PHS/P3 execution is invented.

Original unavoidable technical limits remain: count mode requires finite integers, RL training stages have a schema maximum of 10, mixed-family search requires per-request grants at most 128 proposals/evaluations, and Native contracts retain their maxima. The mixed-search grant uses these maxima, existing screening/final fidelity and the same frozen two-segment/six-tendon M3 family; continuous structure/control/routing research is available. The unchanged C2 ScientificQuestion adapter supports its existing adapted semantics; authorization does not fabricate an adapter for other semantics. Other original Plan tools retain their own contracts.

F2 may pause for read-only supervision near 12 requests and continue automatically in the same Store up to the same total 20. No result-based prompt/code change, model switch, forced next action or second Study is permitted. A1/A2/A3 will be judged independently from actual receipts and wire, with the Provider/scientific-budget confound reported.
