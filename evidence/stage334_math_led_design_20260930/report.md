# Stage 3.34 math-led design validation

## Outcome

The mathematical layer, bounded optimizer, Route evidence linkage, and MATLAB/SciPy checks were implemented and verified. The one authorized live DeepSeek experiment ran to its frozen provider cap but did not execute a changed candidate. It is therefore a failed live design-and-validation experiment, not a reach result.

The live run used 24 provider requests, 19 charged tool calls, 0 backend attempts, 0 workers, and 1285.4435367996339 charged seconds. It stopped with `MODEL_PROTOCOL_CORRECTION_BUDGET_EXHAUSTED: normal request/turn/wall budget`. The unchanged seed was built only for mathematics and was never executed.

## Mathematical use and live failure

DeepSeek invoked the optimizer for all 16 authorized live evaluations and read its two proposals. Both proposed near=0.15 m, far=0.11 m, scale=0.95; the compliant and stiff local residual-upper-bound ratios were both 0.2. The model never selected and built either proposal, so mathematics did not influence an executed design.

The blocking defect was a public-interface mismatch: `analysis.linearize_candidate` returned an envelope containing model references, while `analysis.control_metrics` and `analysis.bounded_endpoint` accepted only bare model references. Commit `465e051c7ffd0f8ce8341a877418886cd0832114` repairs that post-run and adds a regression test. No second live experiment was run.

## Acceptance dimensions

- Mathematical correctness/reproducibility: focused tests pass; sound witnesses and separating-direction certificates are retained.
- MATLAB/SciPy: five representative cases passed in one MATLAB R2024a Engine session; Control System Toolbox and Optimization Toolbox were present and licensed.
- Deterministic Route/optimizer linkage: passed with eight evaluations and zero provider/backend/worker use.
- Genuine LLM use: optimizer invocation and proposal reading occurred, but selection/execution provenance did not; this item is incomplete.
- Reach, sampled settling, real time, and factual candidate delivery: unavailable because no changed candidate was executed.
- Environment conformance: failed for the live run because unqualified `python` resolved to base Conda Python 3.14 instead of `softagent` Python 3.11. Final verification used the required interpreter.

## Reproduction

From the repository root in PowerShell:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest tests.test_task_analysis tests.test_math_analysis
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/stage334_math_route_validation.py --output runs/stage334_math_route_reproduction
```

The paid live experiment must not be reproduced as part of ordinary review. See `manifest.json` for committed versus local-only evidence.
