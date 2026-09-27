# Bounded physical design with GVS NMPC

`controller.gvs_nmpc@4.0.0` supports length changes to the bundled two-section
robot while retaining its topology, sections, materials, damping, attachments,
tendon/actuator arrangement and serial-cell execution. Experiment bounds belong
to `SessionInput.policy.candidate_builder` and `editable`. Versions 2 and 3
retain their historical fixed-robot behavior.

`candidate_reach_input()` creates the versioned controller input. The task owns
the target, evaluator, initialization, environment and timing; the control payload
owns the recipe and separately reported sampled-settling thresholds. Build is
solve-free. Numerical preparation derives dimensions, basis, projection, tendon
order, force limits and initial metadata from the candidate. Compatible historical
tensions and the historical initial applied input can seed execution, but historical
states and equilibria are not transferred. Without a compatible input guess,
candidate pretension is used. Each execution owns its mutable workspace; the
existing solver regenerates states from measurement using candidate dynamics,
independently checks plans and records every bounded hold response.

The example below freezes a 350 ms reach to `[0.29, 0.035, 0.19]` m with 10 mm
original evaluator tolerance, 10 ms control, 0.5 ms physics, twelve cells per
section, and the bundled Stage 3.15 recipe. Only near length 0.15–0.17 m and far
length 0.11–0.13 m are editable. The provider must choose a millimeter-scale
change. Controller tuning and baseline-bound scientific analysis tools are absent.

```powershell
Set-Location 'D:\softrobot-agent'
$py = 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$out = 'runs/gvs_design_reproduction' # fresh folder; launches paid requests
& $py examples/gvs_design_input.py --output "$out/experiment_input.json"
& $py examples/gvs_nmpc_route_experiment.py prepare --output $out --input "$out/experiment_input.json"
& $py examples/gvs_nmpc_route_experiment.py run --output $out --input "$out/experiment_input.json"
& $py examples/gvs_nmpc_route_experiment.py inspect --output $out
```

The existing launcher preserves explicit Route policies and budgets; its legacy
fixed-profile invocation still defaults to one backend execution. This example's
project ceiling is 24 model requests, 60 tools, three backend attempts including
infrastructure failures and 7200 charged seconds. The 1800-second per-call
reservation leaves evaluation/report headroom at historical execution costs.
The credential loader reads `~/.codex/.env` as data without printing or saving
the key. Keep dependency-tracked implementation unchanged during execution.

Fresh reports propagate through the owning child execution, Route result,
incumbent and provider's delivery. Historical profile success does not validate
a new design. Reach, sampled settling, plan feasibility, optimizer convergence
and real-time feasibility remain separate. No actuator, contact, robustness,
global-stability or optimal-design claim follows from this one experiment.
