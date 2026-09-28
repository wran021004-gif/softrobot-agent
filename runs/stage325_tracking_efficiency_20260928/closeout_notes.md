# Stage 3.25 closeout

The retained maintenance changes were reviewed against the existing focused checks. No relevant repair code was changed in this closeout, so the ten tests were not rerun. Original test logs and the verification summary are retained. The public-render check has a recorded outcome (0.151 s), but no separate original console log was retained.

Historical reproduction commands (the exact original shell wrapper was not retained):

```powershell
$softPython = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& $softPython -m unittest tests.test_stage325_efficiency tests.test_stage324_tracking tests.test_stage323_delivery_repair -v
& $softPython -m unittest tests.test_stage325_efficiency.OfflineRecoveryTests.test_original_rejections_and_bounded_corrected_transition tests.test_stage325_efficiency.OfflineRecoveryTests.test_shared_facts_and_original_negative_prose -v
& $softPython -m unittest tests.test_stage325_efficiency.OfflineRecoveryTests.test_public_deterministic_render_uses_sealed_binding_without_execution -v
```

The first recorded combined run predates addition of the public-render test and contained nine tests. The two shared-path checks were repeated after their changes; the public-render test brought the unique total to ten. These are offline regressions, not a live provider session or proof of arbitrary prose accuracy.

`offline_replay_evidence.json` extracts the five actual requests, historical error outputs, raw-response references, and retained replay events/artifacts. Original references resolve in the Stage 3.24 committed Store; no whole database is duplicated. This extraction is new archival work, not a newly observed replay.

Stage 3.24's original index describes recovered CRLF report bytes (15,746 bytes; SHA-256 b4c7da8077cccaceba063afe9cb02115eda015127223acbf7ba70bbb0544be4a). Git's LF blob has 15627 bytes; SHA-256 df5e277e0afd10cdb35868d373d15d0d2455c3948f21528d87218e7dbbabbd04. Newline-normalized contents agree. The historical index and report remain unchanged.

Stage 3.22 failed delivery, Stage 3.23 successful delivery-only review, Stage 3.24 tracking success with failed prose, and Stage 3.25 numerical withdrawal remain distinct. The final numerical implementation matches the established baseline; the timing-boundary correction includes prediction/observation work.
