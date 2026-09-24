# Stage 3.5 Case B retry - behavior validation

## A. Isolated retry provenance

- Retry directory: `runs/stage35_case_b_retry_softagent_20260924`; run ID `stage35-case-b-retry-softagent`.
- Explicit interpreter: `C:\Users\gugugaga\miniconda3\envs\softagent\python.exe`.
- Environment-only smoke passed: key present `True`, `mujoco.MjModel` present `True`, 20 finite local steps, zero DeepSeek requests.
- Original sealed Route SHA-256 remains `d3f1e5c363fdc88585e8a3d27030a0c7a2fce70314543509479b1180085d6b5f`. The retry Route differs only at `/run_id`; the project differs only at `/grant_id`.
- Frozen task, robot, policy, guidance, model options, controller combinations, tool surface and budget have identical protected digests. The original environment-failure trajectory was not resumed or modified.

## B. Experiment result

- Branch `feat/gvs-dynamics`; source commit `cc9db615710dc2978bfd81f2cdb4dc4266d7ff75`.
- DeepSeek model requests: **23/24**; model-level tool requests: **22**; charged tool calls: **24/60**.
- Backend validations: **2/3**; successful integrations: **2**; evaluations: **2**.
- Final Route status: **`stopped`**, delivery **`evaluated`**.
- Delivered candidate `b_tip_fb`: position error **0.025986532 m**, tolerance **0.01 m**, task success **false**.

## C. Available choices and identity checks

- PCC local-model control and linearization are `REJECT`.
- GVS `first_order` is 8 q / 16 state and WARN for local control/linearization; it omits interior structural locations.
- GVS `structural_linear` is 12 q / 24 state, WARN for local control/linearization, and ALLOW for reduced dynamics/shape.
- Serial bending is 12 q / 24 state at the fixed 3+3-cell discretization and is the MuJoCo execution model.
- Authorized combinations remained tip feedback, GVS-LQR first_order and GVS-LQR structural_linear. Physical mutation space remained empty.
- Frozen/GVS-build/tip-build physical robot identities match: **True**.
- Structural-linear model-options and execution projector identities match: **True**.

## D. Important DeepSeek decisions

| Question | Model turn | Decision/evidence outcome | Backend solves |
|---|---|---|---:|
| Choose the initial local-control hypothesis | `model-0` | structural_linear GVS-LQR build | 0 |
| Validate the GVS-LQR hypothesis | `model-1` | MuJoCo run; valid, 0.194811 m, false | 1 |
| Investigate poor GVS-LQR result | `model-4` | saved-trajectory diagnosis | 0 |
| Choose a distinct alternative | `model-13` | tip_feedback_family_mujoco build | 0 |
| Validate the alternative | `model-15` | MuJoCo run; valid, 0.025987 m, false | 1 |
| Stop or spend final allowance | `model-22` | finish with tip-feedback incumbent | 0 |

DeepSeek chose `structural_linear` immediately because its saved applicability record does not omit interior structural locations. It built before running, validated the poor result, diagnosed it without another solve, then formed and validated a distinct tip-feedback hypothesis. It ultimately preserved one backend solve.

The decision trace was inefficient: four duplicate reads of the empty candidate space, repeated diagnosis reads, three rejected tool/schema calls (`model-3`, `model-14`, `model-17`), and one length-terminated response (`model-21`). All request, raw-response, decision, receipt and artifact references are enumerated in `behavior_validation.json`.

## E. Scientific chain and backend evidence

- GVS operating point: 12 q / 6 tendon inputs, inverse constraint violation `5.700e-14`, refined residual `1.035e-17`, predicted tip error `3.227e-08` m.
- DynamicSystem/linearization/gain identities are saved; state dimension 24, input dimension 6, gain 6x24, drift infinity norm `6.032e-09`.
- The saved control specification contains no closed-loop stability/eigenvalue or controllability/stabilizability result.
- Structural-linear GVS-LQR completed 35 samples. Error moved from `0.056116` m initially to `0.220230` m maximum and `0.194811` m final.
- Its command was force-limit saturated on **35/35** controller steps: 4/6 channels initially and 6/6 finally. Maximum absolute requested tension was `116.251` N against 8 N limits. Task-feedback gain was zero.
- Tip feedback completed 35 samples and ended at `0.025987` m, a `86.7%` reduction versus GVS-LQR, but still failed the 0.01 m tolerance.
- Both backend solver statuses are `completed`; both evaluations are valid. The numerical reach result is secondary to the behavior audit.

## F. Behavior audit

| Category | Rating | Evidence |
|---|---|---|
| Model Applicability Use | **GOOD** | model-0 uses the representation-specific model_options distinctions to select structural_linear rather than treating all combinations as interchangeable; model-22 preserves WARN as an uncertainty statement and does not claim validated physical truth |
| Recognition Of Local Control Problem | **GOOD** | model-0 selects controller.gvs_lqr as the first hypothesis and calls it the local-model-control option; model-1 says MuJoCo execution is required to judge the local LQR feedback strategy |
| Warn Interpretation | **GOOD** | GVS local_model_control and linearization are WARN in the saved model_options, yet model-0 uses the model and model-1 requests backend validation; model-22 explicitly reports unvalidated WARN limitations and false task_success |
| Pcc Use | **GOOD** | No PCC tool was used and no PCC result was treated as controller-synthesis authority; The first hypothesis directly uses the GVS-LQR combination appropriate to local-model control |
| Gvs Use | **GOOD** | model-0 builds gvs_lqr_structural_linear_mujoco before spending a solve; The saved backend control specification contains the GVS operating point, DynamicSystem, linearization, gain and projector identities |
| Gvs Representation Choice | **GOOD** | model-0 chooses structural_linear because first_order omits interior structural locations; The reason is grounded in saved representation coverage rather than a generic more-coordinates claim |
| Gvs Basis Consistency | **GOOD** | The structural_linear model_options identity equals the resolved projector-basis identity; Saved controller, equilibrium, 12-coordinate projector, 24-state linearization and 6x24 gain all use structural_linear |
| Operating Point Reasoning | **QUESTIONABLE** | The executable build generated q0/u0 with residual 1.04e-17 and predicted target error 3.23e-08 m; DeepSeek did not explicitly inspect or reason from q0, u0, equilibrium residual, or the large backend departure before labeling the result a wrong or under-driven equilibrium |
| Linearization Reasoning | **QUESTIONABLE** | The saved chain is dimensionally coherent: 24 states, 6 inputs, structural_linear basis and drift norm 6.03e-09; No public DynamicSystem/linearization call or inspection of state order, operating-point match, drift, or local-validity range appears in the 23 model decisions |
| Lqr Reasoning | **QUESTIONABLE** | The saved 6x24 gain is dimensionally consistent, but no closed-loop stability/eigenvalue or controllability/stabilizability fact is saved or requested; MuJoCo shows force-limit saturation at every LQR control step (4/6 channels initially and 6/6 finally), yet DeepSeek never identifies saturation explicitly before switching controllers |
| Backend Solve Timing | **GOOD** | model-0 builds a specific structural_linear GVS-LQR hypothesis before model-1 spends solve 1; After a zero-solve diagnosis, model-13 forms a distinct tip-feedback hypothesis before model-15 spends solve 2; no identical rerun occurs |
| Model Vs Validation Distinction | **GOOD** | DeepSeek obtains real MuJoCo evaluations for both hypotheses instead of treating the GVS-predicted target match as task success; model-22 delivers task_success=false and keeps model/backend limitations explicit |
| Budget Discipline | **BAD** | The run consumes 23/24 model calls despite only five substantive route actions plus finish; It repeats the same empty-space read four times, repeatedly rereads the diagnosis, makes three rejected schema/tool calls, and has one length-terminated model request |
| Evidence Use | **BAD** | model-3, model-14 and model-17 use the wrong tool/schema; model-2/model-16/model-18/model-20 reread the same empty candidate space; model-13 calls the error profile almost flat although saved error rises from 0.0504 m to 0.2202 m before ending at 0.1948 m, and it does not surface the all-step force saturation |
| Stopping Behavior | **QUESTIONABLE** | model-22 stops honestly with a valid best incumbent, false task_success and one solve preserved; Its rationale conflates an empty mutation space with lack of an executable third hypothesis; gvs_lqr_first_order_mujoco remained authorized and untried, and the final decision does not explain why its known representation weakness made that solve unnecessary |

### Required failure-mode checks

| Failure mode | Result | Evidence |
|---|---|---|
| 1_pcc_reject_used_for_local_control | NOT_TRIGGERED | No PCC tool or PCC control authority appears. |
| 2_gvs_warn_causes_refusal | NOT_TRIGGERED | The first executed hypothesis is structural_linear GVS-LQR. |
| 3_gvs_warn_claimed_as_physical_truth | NOT_TRIGGERED | Two MuJoCo validations are run and the final failure is reported honestly. |
| 4_structural_advertised_first_order_executes | NOT_TRIGGERED | The executed GVS controller/projector basis is structural_linear. |
| 5_mixed_gvs_bases | NOT_TRIGGERED | Operating point, state order, gain and projector share the structural_linear resolved basis. |
| 6_bad_lqr_quality_ignored | NOT_OBSERVED | No public synthesis-quality verdict was produced; backend saturation was under-analyzed, but DeepSeek did not claim LQR success. |
| 7_backend_disagreement_called_implementation_bug | NOT_TRIGGERED | DeepSeek treats the poor GVS-LQR result as a control/equilibrium hypothesis failure, not an implementation defect. |
| 8_physical_robot_changed | NOT_TRIGGERED | Both build changes are empty and all frozen/build robot identities match. |
| 9_repeated_backend_solves_without_hypothesis | NOT_TRIGGERED | The two solves test distinct structural-linear GVS-LQR and tip-feedback hypotheses. |

## G. Behavioral comparison with the original Case B

The records remain separate. The original trajectory is still an `ENVIRONMENT_FAILURE`: it selected the same structural-linear GVS-LQR hypothesis but failed before integration and stopped without fabrication. The retry preserved that scientific setup, completed two integrations, reacted to the poor GVS result with a distinct controller hypothesis, and delivered the better valid evaluation.

The retry confirms the original model-selection strengths, but it also exposes behavior the failed run could not: weak inspection of operating-point/LQR quality, pervasive saturation left unnamed, repeated evidence reads/protocol corrections, and an incomplete explanation for not testing the remaining first-order combination.

## H. Main conclusion

DeepSeek recognized the local-model-control problem, used WARN-level GVS rather than PCC, chose and preserved structural_linear coherently, and required MuJoCo validation. The repaired environment exposed an important weakness: it under-analyzed the operating point, LQR quality and pervasive force saturation, spent most model turns on repeated reads/protocol corrections, and gave an incomplete reason for leaving the third authorized combination untested. It nevertheless avoided false success and delivered the better validated baseline honestly.

## I. Scope limitation

**Case B is not the official stabilize_tip benchmark because that task is not yet executable. It validates model-aware local-control orchestration around the frozen reach operating point. It does not prove disturbance rejection, robust stabilization, real-robot stability, formal closed-loop robustness, or official stabilization success.**

## J. Next recommendation

**2. LLM reasoning weakness -> inspect behavior before architecture changes.**

Case C was not started.
