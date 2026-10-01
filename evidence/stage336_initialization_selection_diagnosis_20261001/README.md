# Stage 3.36 initialization-selection diagnosis

The manual execution evidence is sealed and complete. Run `gvs-stage336-b3097f85c72a` built the exact Stage 3.35 proposal `math-compliant-4795c8184616`, bound the frozen mathematics, executed one backend validation as `494deb38d6374deb8f741e96f2430826`, evaluated it, produced a profile report, and explicitly finished. The terminal session status `stopped` is normal completion here because every route node, including `finish-delivery`, completed.

## Outcome

The execution was valid and complete but failed the reach task: terminal error `0.06672099201814737` m versus `0.01` m. Sampled settling failed; all 35 complete updates missed the 0.01 s deadline. This is the validation of a design selected earlier by Stage 3.35 mathematics, not a new optimization search and not one uninterrupted experiment.

## Why initialization was applied 35 times

The saved selected iterations are 0 on 34 updates and -1 at 0.14 s. Both are initialization selections by the reporting contract. The implementation seeds selection with an independently feasible initialization and retains only finite callback iterates with scaled violation <= `1e-5`; after callback iteration 0, a later candidate must have a strictly smaller objective to replace it. All 35 retained candidates were feasible (maximum selected violation `1.4797950191602904e-10`), while every raw returned iterate was infeasible (minimum returned violation `5.752145461205074e-05`). Each callback stopped at the 15 s feasible-return budget with `budget_best_feasible`, producing raw `User_Requested_Stop` and mapped `feasible_early_stop`; none converged. Recovery was disabled. The selected first command therefore remained the initialization tension vector on every update, and the ideal-tension backend applied those same six values.

This establishes the selection mechanism, not the deeper numerical reason that no useful lower-objective feasible iterate appeared. Full horizons, objective values, callback traces, and stopping iteration counts were not saved.

## Historical success

Provenance resolves the sole passing comparator to `b2_near0p169_far0p129_compliant_s1p05`, execution `7575e2c798fa4b66a388f7e277ba51c9`. It used the same declared controller settings and byte-identical core selection implementation. At 0.23 s it selected callback iteration 19 and first changed tension by `[-0.5539287822436905, -0.11155634365492872, 1.1460436309968314, 1.431040287305601, 3.0338853543099047, -0.6314487797947322]` N; the next update selected iteration 3. Its terminal error was `0.0077268610775768345` m.

The executions are not a controlled causal experiment. The successful robot used near/far lengths 0.169/0.129 m and scale 1.05, whereas the current proposal used 0.15/0.11 m and scale 0.95; physics, basis, projected states, and ensuing trajectories differ. The selection switch is an association, not proof of why the historical robot passed.

## Evidence boundaries

Direct observations, offline recomputations, implementation-established facts, unresolved hypotheses, and unsupported claims are separated in `findings.json`. In particular, the approximately 2 mm Stage 3.35 local-model residual is conditional on a local affine witness. It is not a prediction of closed-loop terminal error, and the saved artifacts do not support dividing 66.721 mm by 2 mm as a model-error ratio.

The one evidence-supported next diagnostic is the minimal retention described in `missing_evidence.json`: for a future expressly authorized evidence run, retain initial/selected/returned vectors with objective, violation, iteration, and first command at predeclared timestamps. No controller policy change is recommended from this evidence alone.

## Files

- `per_update_selection.csv/json`: compact 35-update current and historical tables.
- `selected_update_details.json`: current 0.00/0.22/0.23/0.24 s and historical 0.22/0.23/0.24 s records.
- `selection_rule.json` and `implementation_excerpts.md`: actual selection path and source evidence.
- `historical_success_comparison.json`: configuration, preparation, outcome, and mechanism comparison.
- `provenance_chain.json` and `tool_receipts.json`: proposal/build/analysis/run/delivery chain and nested receipts.
- `missing_evidence.json`, `findings.json`, `verification.json`, and `input_immutability.json`: limits and checks.
- `focused_checks.json`: the two narrow reader/alignment tests and package-integrity contract.
- `local_only_artifacts.json`: hashes and sizes for databases, raw traces, and full trajectories omitted from git.

## Reproduction

Use the explicit Python 3.11 environment and the arguments recorded in `protocol.json`. The generator is `examples/offline_nmpc_selection_diagnosis.py`; it performs saved-evidence reads and GVS tip-kinematics evaluation only. It launched zero provider requests, backend executions, NMPC solves, optimizer evaluations, workers, or MATLAB sessions.
