# Numerical repair nr1012

Use the existing worktree `D:\softrobot-agent\.worktrees\mechanics-control-mainline` and interpreter `D:\softrobot-agent\.mainline5-env\Scripts\python.exe`. Do not load provider credentials or call an application model. Historical studies stay sealed. The specification records the actual goal start and includes engineering and delivery activity in the 12 hour ceiling.

All examples below use that interpreter as `python` from the worktree. The active ledger is `runs/nr1012`; never create a second ledger to reset costs. Existing operation keys return their original receipt when the request identity still matches. Use `research_core recover` for pending outcomes before migration or another dispatch.

```powershell
python -m tools.numerical_repair prepare
# Commit scoped implementation, then:
python -m tools.research_core bind --spec examples/numerical_repair/specification.json
python -m tools.numerical_repair import
python -m tools.numerical_repair midpoint --substeps 4 --key midpoint4
python -m tools.numerical_repair midpoint --substeps 8 --key midpoint8
python -m tools.numerical_repair continuation --kind original --update 34 --key projection-A34-xml
python -m tools.numerical_repair continuation --kind representable --update 34 --key projection-B34
python -m tools.numerical_repair policy --update 10 --iterations 12 --key policy-div10-12
```

The original `projection-A34` failed before engine stepping because of temporary-directory permissions; its attempt and measured time remain charged. The corrected XML operation has its own key. A restores available named q/v, time and the applied command, and checks its initial and final tip against the archived physical interval. B reconstructs the state represented by the same reduced coefficients. C reuses the hash-verified matched tight BDF result from nd1011, after matching reduced state, structure, command and timing. These comparisons distinguish projection loss from representable-state differences without claiming an exact additive error decomposition or an exact restoration of unarchived engine fields.

Research stopping is `research_work_v1`: numerical convergence or the declared iteration ceiling; CPU, wall and feasible-return timers are disabled in effective solver options. Feasible selection and returned-tension regeneration remain enabled. Complete execution retains an external watchdog and classifies interruption as incomplete. `historical_timed_v1` is the separate default. Saved-input agreement does not establish closed-loop repetition.

Use `select_recipe` in `tools.numerical_repair` to record an evidence-based recipe choice. This updates the immutable evaluation profile and constructs a fresh candidate. Commit implementation changes and use `research_core migrate --reason ...` without resetting counters or clocks. The selected midpoint method drives offline constraints/initial rollout and NMPC constraints/warm regeneration/tail/recovery. Internal nodes share the original 35 zero-order-held tension commands. BDF node comparisons evaluate adaptive dense-output states at exact optimizer node times; sampled original-task and dense observations remain separate.

```powershell
python -m tools.numerical_repair solve --key fixed1-midpoint8
# Use the returned solve EvidenceRef as --source, preserving its exact tensions:
python -m tools.numerical_repair verify --source RETURNED_64_HEX_ARTIFACT_ID --key verify-fixed1
python -m tools.numerical_repair gate
python -m tools.numerical_repair execute --key fixed-reference
# Repeat the returned passing execution EvidenceRef (fresh controller/process):
python -m tools.numerical_repair repeat --source PASSING_64_HEX_EXECUTION_ARTIFACT_ID --key fixed-selected-repeat
```

A retained candidate must meet hard numerical feasibility and original task metrics. Its exact returned schedule is independently integrated from the original zero state and checked against both the unchanged original sampled task and all optimizer nodes (1 mm tip / 2 mm/s velocity-vector limits). One concrete evidence-based revision is permitted. Two future verification jobs/time and two passing complete executions are protected before preliminary work; each solve additionally reserves its own verification until consumed. Short fixed-input MuJoCo continuations count as independent integration configurations, not complete controller launches. Technical failures consume attempts and measured cost. Internal closed-loop NMPC work is charged within its complete execution only.

Only a new fixed offline candidate passing all three gates plus two fresh passing executions of one selected complete configuration admit the conditional length-design solve. Diagnostic runs and historical passing trajectories do not open this gate. The engineering requirement is initial execution plus one independent repetition, without relabeling them as the historical promotion protocol. Keep all failures, complete actions, node predictions, delivered commands and trajectories. The optional solve may reopen only d, and needs its own independent integration and complete repetition.

Actual fixed attempts and retained evidence:

- `fixed1-midpoint8`: solve `4bf50bd8202bf6edfd81525fbe60972bfcc87f165199181a87bf7076460c697e`; verification `43ff6a43e3efe72290191213f556f932c1d7e17ef7783135aae2429d9d89e684`. Numerical and independent original sampled task pass; exact-node velocity-vector disagreement 0.006495728 m/s fails.
- `fixed2-midpoint16`: solve `3ce63b3d84490c4468c895d579340b3e0f667789a4472f6be7012b159137812c`; verification `1d0798a28ee77e00fd5f4155559c68797eb26715d5c5ccfcfd268292fdcc5209`. Numerical and independent original sampled task pass; exact-node velocity-vector disagreement 0.003526347 m/s at 0.290625 s fails. Preserve both failures; a third fixed solve is outside this milestone.

The final numerical controller recipe before complete comparisons is midpoint16, three IPOPT iterations with numerical convergence enabled, automatic exact whole-NLP AD, reverse local residual AD, and scaled warm/tail/recovery root tolerance 1e-8. Full plan feasibility remains independently checked against the unchanged 1e-5 limit. Actual-root residual checks remain; the unused deliberately repeated-state diagnostic is omitted during research full regeneration. The historical timed path retains that diagnostic and the 1e-10 root default.

Two current-path checks with forced whole-NLP reverse AD hit their 300 s watchdogs and remain charged incomplete outcomes. Automatic AD with six iterations at saved holding update30 completed in166.558 s. The final three-iteration saved divergence update10 check completed in233.651 s and returned a feasible lower-cost command. These local cases support the declared work policy, not complete feedback repeatability. Standalone total remains capped at1500 s; the per-check outer watchdog is600 s. Complete simulation watchdog is6000 s; its interruption is incomplete. Total numerical/activity ceilings remain21600 s /12 hours.

The reused update34 C record's stored d differs from the declared scalar by -3.886e-16, while both actual resolved binary-float segment lengths are identical. Reduced state, tension, time, scene and physical lengths match; scalar bitwise equality is not claimed. Restored A's initial and final native world velocities match the archived interval exactly, as do its positions.

```powershell
python -m tools.numerical_repair solve --source 4bf50bd8202bf6edfd81525fbe60972bfcc87f165199181a87bf7076460c697e --key fixed2-midpoint16
python -m tools.numerical_repair verify --source 3ce63b3d84490c4468c895d579340b3e0f667789a4472f6be7012b159137812c --key verify-fixed2
python -m tools.numerical_repair gate
```

Existing keys are historical receipts only when their original implementation/request identity matches; after migration, inspect those immutable references rather than re-dispatching an old key under new inputs. Recipe selection is recorded through `select_recipe` and profile history before each new comparison. Since neither fixed candidate passes node consistency, complete feedback observations cannot admit optional length design.

Focused checks: `python -m unittest tests.test_numerical_repair tests.test_research_core_numerics`. Do not run the repository suite or provider probes. Export through the existing `research_core export` mechanism after an engineering STOP citing every new numerical/physical result. Deliver a machine summary, this runbook, completion report, immutable archive/manifest and ordinary HTTPS push with remote SHA verification.
