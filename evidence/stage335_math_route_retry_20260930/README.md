# Stage 3.35 math-led Route retry

This directory separates the completed offline integration proof from the one authorized live DeepSeek retry.

The offline provider-format fixture passed the production DeepSeek function decoder and Host boundary. It advertised `route.record_analysis@1.0.0`, invoked metrics and endpoint tools with the returned candidate-linearization envelope, retained the original optimizer result, built an exact returned proposal, attached candidate-bound evidence, and passed the real execution gate without starting a backend. It used 8 cumulative mathematical evaluations, 0 provider requests, 0 backend attempts, 0 NMPC solves, and 0 workers. The scripted proposal choice is not evidence of LLM reasoning.

The first offline report call intentionally remains visible in `provider_fixture_trace.json`: the fixture supplied the outer Route result wrapper where the Route requires the build node result. The same store was resumed with that returned node reference. No optimizer evaluation was repeated and no counter was reset.

Run focused verification with the required interpreter:

```powershell
& 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' -m unittest tests.test_task_analysis tests.test_math_analysis tests.test_stage335_math_route
```

Do not reproduce the paid live action during ordinary review. `offline_manifest.json` identifies committed files. `local_only_artifacts.json` identifies the raw local SQLite/artifact store by absolute path, size, and SHA-256 and explicitly does not claim remote availability.

The retained five-case MATLAB/SciPy acceptance evidence remains under `evidence/stage334_math_led_design_20260930/`; it was not recomputed for these narrow integration repairs.
