# Checkout verification and evidence applicability correction

The checkout was clean on `feat/gvs-dynamics` at `2da9d89`, already containing the four-phase implementation and its completed experiments. The reviewed baseline `3451719ac22cc33e566f29e79240ed5f6a173549` was not restored. A comparison against that baseline confirms that the Stage 3.6 and Stage 3.11 source/evidence artifacts remain unchanged.

The existing [implementation report](implementation_report.md) remains the main error/cost, control, optimization and backend report. Its measurements are reused, not presented as new runs.

## Focused correction

`extensions/tendon_family/model_applicability.py` now requires the stored evidence environment to equal the actual normalized task assembly, in addition to the existing design, representation, model version/parameters and explicit local-scope match. Previously, supplying the old query context could still produce `measured_local` after changing the task mount or gravity. A changed environment now leaves validation unavailable. Capability verdicts and old evidence records retain their existing contracts.

`tests/test_model_applicability.py::ModelApplicabilityTests.test_local_evidence_requires_actual_task_environment` passes. It checks a matched local shape measurement, exclusion of unmeasured dynamic control, and rejection of the same evidence after a 0.1 m mount translation while the old query context is reused.

A read-only smoke using the original Store and the archived 12-cell EvidenceRef returns `shape_prediction=measured_local`, `local_model_control=unavailable`, and `contact_prediction=unavailable` with the corrected implementation. No store grants, receipts or historical measurement records were changed.

## Saved-matrix reproduction

The new `verify_saved.py` reads the Stage 3.6 matrices and uses the production augmented-exponential ZOH and discrete Riccati path. It performs no symbolic model build, trajectory optimization or backend simulation. [checkout_verification.json](checkout_verification.json) records the result and resolved software environment:

| Quantity | Reproduced value |
|---|---:|
| Continuous maximum real eigenvalue, 1/s | -3.1756078048006255 |
| Saved gain held for 10 ms, spectral radius | 24.46305321361195 |
| Discrete LQR at 10 ms, spectral radius | 0.9683849337500653 |
| Maximum difference from archived discrete gain | 0 |

This homogeneous linear perturbation calculation does not establish a new nonlinear equilibrium. The public synthesis path retains its separately documented continuous-drift check. Physics stepping is 0.5 ms; feedback updates are 10 ms.

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
& $py runs/stage312_to_nmpc_20260926/verify_saved.py
& $py -m unittest tests.test_model_applicability.ModelApplicabilityTests.test_local_evidence_requires_actual_task_environment -v
```

The full experiment reproduction commands remain in the implementation report. Use a fresh output directory for those commands; existing public run IDs and accounting are immutable.

## Completion boundary

Implemented capabilities are scoped agreement/cost evidence with integrated mapping, sampled LQR, a cached implicit multiple-shooting OCP, and a registered backend-executable projected-state NMPC controller. Existing commits are `d190d3f` (agreement/mapping), `f6859e6` (sampled LQR and trajectory/NMPC), `96f6210` (derivatives and resumable experiments), `360e039`/`ec27e6a` (explicit feasible-suboptimal execution and warm starts), `c950f1b` (MuJoCo numerical-reset guard), and `2da9d89` (final experimental evidence).

Successful full-task NMPC has **not** been demonstrated. The 12-cell local LQR nominal/perturbed endpoints pass at 9.345/8.950 mm, but the comparable straight-start LQR endpoint fails at 33.942 mm. The offline five-interval plan is independently feasible (scaled violation 3.55707e-7) and iteration-limited, not converged. Its full 0.35 s continuation fails in MuJoCo at 235.154 mm. NMPC reaches a numerical reset at 0.236 s; its last valid sampled error is 256.632 mm at 0.23 s. The reviewed authoritative evaluation is incomplete with no task-success value.

The archived public evaluation receipt rejects changed dependencies because the numerical-reset guard was fixed during the original long run. The separately derived failed result is evaluated by the unchanged registered reach evaluator; it is not a completed public evaluation receipt. The new regression and saved-matrix reproduction do not remove that limitation.

NMPC mean optimization time is 125.194 s per 10 ms control period, with 34 nonconverged solves among 35 diagnostic updates, 31 hold-last uses, and a 4409.625 s total execution. Only the prefix before the reset is valid physical evidence. The current backend stops at numerical resets. Neither a valid full-duration NMPC trace nor real-time feasibility is claimed.

No full suite, resolution/gain sweep, repeated long simulation, paid LLM call, push or merge was performed in this follow-up. Remaining work is successful full-task optimization/replanning and backend numerical stability; it cannot be inferred from local agreement, Riccati stability or NLP feasibility.
