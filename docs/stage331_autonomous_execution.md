# Stage 3.31: effective configuration and autonomous revision execution

Explicit experiment `policy.model` fields take precedence over matching fields in
`configs/deepseek.yaml`; schema defaults fill the remainder. The explicit offline
preparation override is saved in the resolved input. Existing launch paths without
an input use global defaults. `reasoning_effort` optionally accepts low/high/max;
omitting it retains the old wire format.

`examples/gvs_revision_input.py` loads the complete Stage 3.29 frozen scientific
input. It configures deepseek-flash at https://api.deepseek.com, thinking enabled,
high effort, 65536 completion tokens and a 600-second timeout. The first length
exhaustion without usable content or a complete tool action permits one frozen
retry with 131072 tokens and 900 seconds; model/effort stay the same. Subsequent normal requests return to
the initial settings. All requests consume the existing project ledger. Partial
outputs never become actions. Ordinary protocol correction and unknown-outcome
handling are retained. Each context-delivery/model-request event references both
the exact provider payload and effective model configuration (including transport
timeout). Endpoint rejection bodies are saved with credentials redacted.

The provider sees only the applicable reach or tracking result definition. The
shared runtime union and strict delivery validators are unchanged. The shorter
revision brief retains the historical evidence, candidate-analysis prerequisite,
coverage, resource ceilings and factual delivery requirements without choosing a
design or introducing a new success criterion.

Official parameter reference:
https://api-docs.deepseek.com/api/create-chat-completion/

Focused offline checks:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$py='C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
& $py -m unittest tests.test_stage331_execution tests.test_route_model_protocol.RouteModelProtocol.test_length_truncation_has_one_dedicated_retry_and_executes_no_partial_call tests.test_stage325_efficiency.OfflineRecoveryTests.test_shared_facts_and_original_negative_prose
```

Freeze implementation before launching; keep the same output directory through
preparation, execution and inspection. No paid startup probes are required.

```powershell
$old='runs/stage329_multiphysics_design_20260928_202221'
$new='runs/stage331_autonomous_revision_execution_'+(Get-Date -Format yyyyMMdd_HHmmss)
& $py examples/gvs_revision_input.py --source $old --output "$new/frozen_input.json"
& $py examples/gvs_nmpc_route_experiment.py prepare --output "$new/live" --input "$new/frozen_input.json" --historical-failure $old
& $py examples/gvs_nmpc_route_experiment.py run --output "$new/live" --input "$new/frozen_input.json" --historical-failure $old
& $py examples/gvs_nmpc_route_experiment.py inspect --output "$new/live"
```

Phase ceilings: 64 requests, 160 platform calls, 6 fresh backend attempts, 21600
charged seconds, zero workers, available in one continuous session. A replacement
attempt requires a concrete implementation defect; subtract all prior ledger use
from its grants and disable length_recovery.enabled if the recovery was already
used. Preserve interrupted attempts. Historical evidence is never charged again.
Assess configuration, autonomous workflow, covered reach success and delivery
accuracy separately in the phase evidence report.
