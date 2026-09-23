# Stage 3.5 Case A — DeepSeek behavior validation

## Execution

- Branch/commit: `feat/gvs-dynamics` / `20723e333abcc1b71af2efc62c5f765664dac27c`; run ID `stage35-case-a-live`.
- Task: frozen `reach_free` reach, target `[0.29, 0.035, 0.19]` m, tolerance `0.01` m. The environment has no active obstacle/contact requirement.
- Available choices: PCC, GVS `first_order` (8 q) and `structural_linear` (12 q), serial bending (10 q), and one executable `family_mujoco` combination. The bound GVS tools are `dynamics.gvs_describe@2.0.0`, `dynamics.gvs_evaluate@3.0.0`, `dynamics.gvs_build_system@3.0.0`, and `statics.gvs_equilibrium@2.0.0`. Initial verdicts, representation identities and all route-visible versions are in `behavior_validation.json`.
- Budget used: **18/18 model requests, 19/40 charged tool calls, 2/2 backend solves**. There were 21 tool requests including two rejected requests, and one length-truncated model response recovered on the next request.
- Final: explicit `finish-1` delivery of `build-2`, valid evaluation, position error **0.072451 m**, task success **false**. `run-1` measured 0.078380 m; `run-2` measured 0.072451 m.
- The source tree was clean at start and remains unchanged. Saved model requests, raw responses, decisions, receipts and route nodes are referenced by artifact ID in the JSON report.

## Actual decision sequence

| Decision | Question, choice and reason | Backend cost |
| --- | --- | ---: |
| `model-0-tool` | Starts with `kinematics.pcc_describe` to learn two segment curvature coordinates. The saved `model-0` reasoning explicitly cites `model_options`: PCC reachability **ALLOW**. | 0 |
| `model-1-tool` to `model-3-tool` | Reads optimizer templates and frozen design space. `model-3-tool` is rejected because it adds a forbidden nested `reason` to `evidence.read`. | 0 |
| `model-4-tool` (`build-1`) | Raises near length to 0.20 m, claiming 0.28 m of baseline flexible length cannot reach the target. Build constructs without evaluation. This bound omits rigid connector/tip offsets; no `pcc_forward` was called. | 0 |
| `model-5-tool` (`run-1`) | Uses serial-bending MuJoCo to measure task error after the saved build. It says execution is validation authority and plans to inspect the result. First charged solve: global tool event **58**. | 1 |
| `model-6-tool` to `model-13-tool` | Tries to inspect run-1 configuration, evaluation and simulation. `model-6-tool` fails on pointer `/`; `model-10-tool` is rejected for the extra nested `reason`; `model-7-tool` repeats cached PCC description; `model-9-tool` and `model-12-tool` reread the same scalar evaluation. | 0 |
| `model-14` | DeepSeek response truncates; the platform's existing length recovery requests one complete call, with no tool executed from the truncated response. | 0 |
| `model-15-tool` (`build-2`) | Rebuilds with near length 0.20 m and feedback gain 8.0 after run-1 error 0.078380 m. It cites saved result/evaluation refs but has not established the error direction or that gain is the cause. | 0 |
| `model-16-tool` (`run-2`) | Runs and evaluates build-2 on MuJoCo. Second charged solve: global tool event **157**. | 1 |
| `model-17-tool` (`finish-1`) | Stops and explicitly delivers the valid session incumbent, reporting the unmet 0.01 m tolerance. | 0 |

DeepSeek's saved `model-5` reasoning considers GVS equilibrium and rejects it as unnecessary for this actuator-command validation question. It calls **no** GVS equilibrium, DynamicSystem export, linearization or LQR tool. GVS basis consistency therefore has no executed call to inspect. The initial GVS `reachability` verdict is ALLOW for both bases; its static equilibrium verdicts are WARN and contact/high-fidelity validation verdicts are REJECT. No rejected use becomes an authority in the decision sequence.

## Behavior classifications

| Category | Rating | Saved evidence |
| --- | --- | --- |
| Model applicability use | **GOOD** | `model-0` raw response names `model_options` and PCC `reachability: ALLOW`; `model-4` reasoning treats PCC shape prediction WARN as coarse. |
| Model hierarchy understanding | **GOOD** | `model-0-tool` chooses cheap PCC description; `model-5-tool` reserves MuJoCo for validation; GVS/LQR is skipped. |
| PCC use | **QUESTIONABLE** | `model-0-tool` and cached repeat `model-7-tool` describe PCC, but no `pcc_forward`; `model-4-tool` uses an incomplete flexible-length bound. |
| GVS use | **GOOD** | No GVS call was needed for simple reach; `model-5` explains why equilibrium would not directly validate commanded actuation. |
| GVS basis consistency | **NOT_OBSERVED** | No basis-aware GVS call. |
| Backend solve timing | **QUESTIONABLE** | First solve after a zero-solve build (`model-5-tool`), but the build premise is incomplete; second solve follows a gain choice unsupported by directional error evidence (`model-15-tool`). |
| Budget discipline | **QUESTIONABLE** | Repeated PCC description (`model-7-tool`), duplicate evaluation reads (`model-9-tool`, `model-12-tool`), all 18 model requests consumed. |
| Evidence use | **QUESTIONABLE** | Route transitions cite refs, but `model-3-tool`/`model-10-tool` reject on schema, `model-6-tool` fails on `/`, and the gain decision lacks causal evidence. |
| Stopping behavior | **GOOD** | `model-17-tool` explicitly delivers the valid failed-tolerance result; no further tools follow. |

## Direct answers

1. **Used `model_options`?** Yes. `model-0` raw reasoning explicitly cites PCC reachability ALLOW; later reasoning cites WARN and avoids treating it as validation.
2. **Recognized PCC for initial reasoning?** Yes in choice and explanation, but only called `pcc_describe`, never `pcc_forward`; its geometric reach claim was incomplete.
3. **Invoked GVS?** No. No GVS use, verdict or basis was executed; the saved reasoning judged it unnecessary for this task.
4. **Unnecessary equilibrium/DynamicSystem/linearization/LQR?** None.
5. **First backend solve?** `run-1`, global event 58 after `model-5-tool`, with PCC description, space/template reads and `build-1` as prior evidence. It sought the first actual tip-error measurement, although its reachability premise was incomplete.
6. **Applicability confused with physical validation?** No visible confusion: DeepSeek says simulation provides validation and treats PCC WARN as a coarse prediction.
7. **REJECT respected?** No relevant REJECT use was attempted. Contact and control-design questions were absent, so strict REJECT handling remains untested in this case.
8. **Stopped appropriately?** Yes after two valid evaluations and exhausted solve budget, with explicit honest delivery. Earlier repeat reads show room to stop or decide sooner.
9. **Cause of weaknesses?** The flexible-length claim, gain inference and repeated reads are LLM reasoning issues; nested `reason` rejections are tool-schema misuse; pointer `/` gives weak interface feedback; the first sealed launch failed from sandbox network access. MuJoCo worked in the live run.

## Problems and next step

- **LLM behavior:** Incomplete geometric bound, no PCC forward test, repeated evidence reads, and a gain trial without established error direction.
- **Interface / Stage 3:** `evidence.read` pointer `/` failed with an empty error string. This did not block the completed run; no planner, guidance, assessment or tool description was changed.
- **Environment:** A separate sealed first launch in `runs/stage35_case_a_20260922` stopped at `DEEPSEEK_NETWORK_ERROR` before a decision. Network-enabled execution completed; MuJoCo had no environment blocker.
- **Deferred capability:** `CANDIDATE_SPECIFIC_REASSESSMENT_NOT_AVAILABLE`. `model_options` assesses the frozen near length 0.16 m; both candidates changed it to 0.20 m.

**Conclusion:** DeepSeek behaved as a model-aware planner, not as an undifferentiated tool caller, but its concrete PCC and evidence use was inefficient and partly unsound. **Recommendation 2:** inspect prompt/model reasoning before changing architecture. Do not start Case B yet.
