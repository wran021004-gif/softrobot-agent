# Main-Off v5: independent live test of the v2 binding interface

## Outcome: C overall; real binding and feedback path verified

The independently authorized probe used **8 Main requests, 0 Reporter requests, 0 scientific or physical workers, and no retries**. Main autonomously selected an owned candidate and `equilibrium`, submitted only its scientific variables, and reached a valid original `AnalysisRequest`. The program bound the frozen identities/protocol and intercepted execution. The final Main request received that real feedback and correctly acknowledged both non-execution and the method's inability to check holding speed.

This is a genuine technical advance over [v4](main_off_decision_probe_v4.md), not full scientific-decision acceptance. Main initially asked static equilibrium to discriminate a dynamic speed failure, inverted parts of its expected/weakening observations, and finally submitted a STOP missing its required `hypothesis`. **Classification remains C, rather than A or an interface-defect B.** No mathematical result was computed. Do not launch the formal two-condition cold-start Study on this evidence.

## Authorization, version and isolation

The user explicitly authorized sending the required saved C3 evidence to DeepSeek API for one new independent probe: at most eight Main requests, no Reporter, no scientific/physical workers, no automatic retries, with a decision after analysis feedback. The destination was `https://api.deepseek.com/chat/completions`; model `deepseek-flash`, thinking disabled, reasoning effort none, `max_tokens` absent. Every response was HTTP 200 and finished with `tool_calls`; none was truncated.

Tested commit: `3a52eb503b45e91fcde3d088ee68e696f7bdd266`, branch `codex/english-native-decision-brief`. Its worktree was clean before sending. The new ID, Store and grant ledger are `main-off-saved-c3-v5-20261028`, `runs/research/main-off-saved-c3-v5-20261028`, and that ID's `-provider-only` grant. Preparation explicitly froze **`bound_scientific_variables_v2`**. No v4 allowance, Store, response or selected decision was carried forward; its residual allowance remains unused. The original C3 archive and execution Store were read-only.

`main_off_live_probe.py` gained explicit `--probe-id` and `--analysis-interface` arguments, freezing the interface at creation and rejecting an existing destination. Continuation must match the original authorization and interface; it cannot upgrade a frozen Store. Existing default v1 callers remain unchanged. The only pre-run engineering change was this preparation interface and its regression test. Actual command options were `--live --probe-id main-off-saved-c3-v5-20261028 --analysis-interface bound_scientific_variables_v2`, plus the independently granted authorization text stored in the scope record. No correct method or tool variables were supplied to Main.

The source boundary remains sequence 425 of `b3-r1-history-assisted-050`, saved state `8a96cdd0c29c211346a2e5c33694908335ef8812109998c8088772e02c7de835`. Candidate `e85fc8e3eb57e05bfef71db74885db619ce316f90cb9e9b88dc3e971e01f7543` and canonical task `062de8ca2fd2acaebdbf856ba8fc3420d88c8d3943cfa789c5c9e6f06e486c6b` retain their original identities. Frozen scientific dependency differences were preserved, not migrated. No formal Study was prepared or executed.

## Actual decisions and scientific limits

1. Requests 1–3 read acceptance, candidate/control links and existing mathematical descriptions, including braking and short input response. Main was free to choose among them. Requests 4–5 attempted and then corrected two control-link reads: `task_acceptance` was absent from those specific rows. Accurate field feedback reached request 5, whose revised queries succeeded. There were ten evidence-read calls in total, including those two failures; no Reporter investigation or procedural search was launched.
2. On request 6, Main correctly identified the failed holding speed: **0.043009681835387996 m/s versus 0.02 m/s**, while position error **0.0040334275990930235 m** met 0.01 m. It recognized that the earlier 0.1114 m/s case changed both structure and control, so improvement cannot be causally assigned to either alone. Its numerical-failure-tag concern remained an uncertainty, not a proved execution defect.
3. It independently selected `equilibrium` and explicitly supplied the exact owned candidate in a native diagnose Plan. That diagnosis settled read-only. Its `claimed_inference=mathematical_prediction`, without supporting evidence, was recorded as an unsupported hypothesis under the original admission; no prediction or certificate was created. The v2 candidate requirement appeared on actual request Schemas 1–7. Main supplied the candidate on its first diagnosis, so this run did not test correction of a missing-candidate rejection or isolate the rule's causal effect.
4. The science rationale was inadequate for the stated question. Main said the residual speed might be structural/static and suggested equilibrium could predict terminal velocity or distinguish structural from transient control effects. Its expected near-balanced static outcome would weaken its stated structural hypothesis, while its nominal weakening outcome would instead support it. Solver non-convergence was also proposed as structural evidence, contrary to the method's limited numerical meaning.
5. The registered `target_equilibrium` construction jointly attempts a configuration and bounded static tensions; it is not a replay of the stored final command or measured terminal state. The existing implementation's `_candidate_points()` in `extensions/tendon_family/math_analysis.py` records `computed_tensions_n` and `execution_data_used=False`. No such solve ran here. Static target construction can answer a limited static question, but cannot discriminate the proposed holding-speed mechanism, establish dynamic feasibility or identify a structure/control cause. This is a scientific method/scope problem, not an invalid parameter object.

Existing sourced Reporter conclusions were available and mentioned by Main. Their contribution is not isolated, and no new Reporter-Low request or result was generated.

## Real analysis input, deterministic binding and validation

Request 7 actually advertised the selected `research_analysis` Schema. Its required fields were `operating_point` and `model_source`; no top-level `candidate`, `protocol` or `operation` was exposed. The point enum contained only `target_equilibrium`. Main explicitly submitted:

```json
{"model_source":"controller","operating_point":"target_equilibrium"}
```

The program did not change either value or choose a state for Main. The original contract permits this static point without a saved state. Reduced model source is a genuine choice, so it remained explicit rather than being auto-bound. The frozen controller resolves to `model.gvs` for this candidate.

| Full-request field | Value / trusted source |
|---|---|
| `candidate` | Exact `e85fc8…7543` EvidenceRef from the settled diagnose Plan `b26abb9763525bab0b563eab4af88c9529143c3a5990388125353bccab24785d`, `/original_plan/decision/selected_candidate` |
| `protocol` | Complete original `analysis_protocol` from the frozen source Study; retained without expansion or alteration in the binding audit |
| `operation` | `equilibrium`, from the existing selected registration `/methods/equilibrium` |
| `model_source` | `controller`, submitted by Main |
| `operating_point` | `target_equilibrium`, submitted by Main |

The binding audit is `6d96b3aee6903054509618e3666bf77bc2437f6651f126e6b59572bb8beda29f`. Its full raw request, complete protocol, exact Provider Schema and provenance for every submitted/bound top-level field are preserved in [the live evidence export](../../evidence/main_off_binding_v5/live_validation.json). Original Pydantic serialization may omit the default `model_source=controller`; the raw bound request still retains Main's explicit choice.

The live binder passed selected JSON Schema, full original JSON Schema and Pydantic validation. The interceptor independently checked candidate ownership, exact protocol/operation and deterministic model applicability. A post-run read-only audit reproduced these validations against the saved objects, matched candidate to the settled Plan and Store, and verified the next actual wire contained analysis feedback. It did not repair a request, send anything, construct a numerical model or run a solver.

Applicability was **`applicable` for the limited static diagnostic**, with `full_task_supported=false`. Position constraints were diagnostic, no sample indices were verified, and `holding_max_speed_m_s` was explicitly **`not_applicable`**. The GVS static use was `WARN`: design/representation agreement had no validation evidence. That warning is not itself a hard unsupported-method rejection.

The original scientific guard returned **`DEPENDENCIES_CHANGED_COMMIT_AND_MIGRATE_WITHOUT_RESETTING_COSTS`** for the same eight historical scientific dependencies. Full original scientific execution admission was **not run or passed**. Parameter validity and deterministic applicability do not override this guard, source/profile identity, resource admission or independent task acceptance. The result was `probe_only_not_executed`, with both worker and scientific-execution flags false. Interception artifact: `1d0432ee8675e005f200621e1836f8e28e83dd3767217bb673a99cf8b69e73ec`.

## Actual feedback decision and final state

The reserved request 8 contained the real interception feedback. Main explicitly stated that nothing had executed and recognized that static equilibrium could not address the failing speed constraint. It withdrew its proposed structural/transient discrimination, retained the confound, and did not invent a mathematical result or claim global structural infeasibility. This is genuine evidence of feedback use, rather than the scripted correction used in earlier offline tests. There was no erroneous analysis request to correct; its first analysis variables were valid.

Main also noticed protected closeout and correctly stated that remaining mathematical balance is not execution authorization. Its stronger phrase that the method was unavailable “in principle” should be limited to the speed question: the deterministic result still permits a static diagnostic, and a validation warning is distinct from a hard failure. Protected closeout, scientific dependency rejection and scope limitations are separate facts.

Its final native STOP omitted required top-level `hypothesis`, despite supplying interpretation and stopping conditions. The original Pydantic Plan contract returned `Field required`; further STOP citation/inference admission was not reached. No fields were supplied on Main's behalf, and no accepted STOP or SELECT is claimed. After the eighth request the orchestrator paused at the verified feedback boundary with no pending work, no unconsumed response and no occupied resource. `research_status` remains `ready` because the STOP was rejected; request allowance is exhausted, so it will not continue automatically.

## Accounting and comparisons

Every row is an actual Main send. The linked evidence export records each full request ID, wire and raw response reference, tool arguments, usage and completion status. Cache columns are hit/miss tokens. All response finishes were `tool_calls`.

| # / request ID | Bytes | Prompt | Completion | Cache hit / miss | Seconds |
|---|---:|---:|---:|---:|---:|
| 1 `r3-request-c96bc53779684f079a2e177da335c3b0` | 41,240 | 11,558 | 276 | 5,248 / 6,310 | 1.250 |
| 2 `r3-request-8efaec77374549dcbc9f411441d949f2` | 47,325 | 13,374 | 277 | 7,936 / 5,438 | 1.141 |
| 3 `r3-request-15dcf5e08e3e45b49250a724b4290507` | 54,171 | 15,140 | 330 | 9,856 / 5,284 | 1.672 |
| 4 `r3-request-97429a1bca554645b260894d3a97a542` | 57,487 | 16,036 | 350 | 11,520 / 4,516 | 1.500 |
| 5 `r3-request-288943d70b97425096025bc0d00754b7` | 63,898 | 17,924 | 329 | 12,416 / 5,508 | 1.782 |
| 6 `r3-request-18047b14679647928ff71a98804fe42f` | 73,799 | 21,040 | 1,452 | 14,336 / 6,704 | 7.640 |
| 7 `r3-request-f4506d6a9d404da79cfc2dea2c72b592` | 88,428 | 24,707 | 125 | 7,936 / 16,771 | 0.922 |
| 8 `r3-request-cba6deec9eef4eddb8e40b921ad8d269` | 75,739 | 21,814 | 1,115 | 4,736 / 17,078 | 6.407 |

Totals: **141,593 prompt + 4,254 completion = 145,847 tokens**, cache hit 73,984 and miss 67,609; Provider elapsed sum **22.314 s**. Currency cost was not reported and remains unknown. The independent ledger used eight model calls and thirteen public tools, zero backend solves and zero worker calls; no provider allowance remains. Three tool errors were the two invalid field reads and missing STOP hypothesis. There were **zero analysis type or binding errors**. No physical rollout, NMPC, PPO, mathematical numerical work or formal Study ran.

The actual equilibrium Schema was **3,641 bytes**, versus **3,016 bytes** for an offline legacy selected-method projection of the same frozen candidate/method. The +625 bytes include source/coverage guidance and conditional state rules; fewer identity fields do not imply fewer serialized bytes. This is not a second live baseline request. V4 used seven requests without analysis; v5 used eight with one valid analysis call and an actual feedback decision. Their methods, retrievals and decisions differ. Neither the token-total difference nor a single smaller wire establishes reduced whole-research cost or proves the version caused the improved behavior.

## Verification and readiness

Three pre-send targeted tests passed: `test_new_probe_freezes_v2_without_inheriting_provider_allowances`, `test_missing_math_diagnosis_candidate_has_versioned_schema_and_feedback`, and `test_budget_preserves_feedback_and_rejects_reporter` in `tests.research.test_bound_analysis.BoundAnalysisTests`, using the installed `.f3-prestudy-env/Scripts/python.exe -m unittest`. They checked independent zero-use preparation, frozen v2, no destination reset, preserved v1 semantics, conditional candidate admission and the feedback reserve before ledger charging. The post-run saved-contract/wire audit above also passed. No broad suite or scientific Worker was run; prior unrelated baseline test expectations were not changed or retested. `git diff --check` passed.

| Required layer | This real probe |
|---|---|
| Understand failure | Yes: speed fails, position passes; confounded comparison acknowledged |
| Falsifiable supported hypothesis | Inadequate: expected/weakening labels conflict and static/dynamic mechanism is not identified |
| Autonomous method selection | Yes, `equilibrium`; insufficient for the claimed speed discriminator |
| Meaningful legal point | `target_equilibrium` is legal and explicit, but does not represent the observed terminal state |
| Scientific variables | Valid, original Main input preserved |
| Frozen-field binding | Passed, with settled candidate and frozen-protocol provenance |
| Full original request contract | JSON Schema and Pydantic passed |
| Original scientific admission | Dependency guard rejects; full execution admission not established |
| Feedback adaptation | Yes: non-execution and speed-coverage limitation understood; final STOP remained invalid |
| Mathematical computation | **No** |

The actual tool interface no longer requires Main to regenerate frozen objects in this observed case, and it delivered actionable scientific limitations to the next decision. Remaining blockers to autonomous formal research are the quality/consistency of method-to-hypothesis reasoning, reliable completion of the original Plan/STOP contract, and the separate scientific dependency/admission boundary. Do not mask these by weakening scope checks, supplying Main's missing fields or choosing a preferred diagnostic on its behalf. This probe is complete; another live test would require a new independently authorized ID and ledger.

The delivery commit and push status are provided with this report. The unrelated main worktree, old probe allowances and historical scientific Stores remain untouched.
