Shared deterministic local analysis
===================================

Run from D:\softrobot-agent in PowerShell::

  & 'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe' examples/offline_math_analysis.py

This creates a timestamped runs/offline_math_analysis_* directory. It reads the
seven explicitly inherited Stage 3.31/3.32 executions and the two completed live
Stage 3.33 Route executions, copying SQLite ledgers into the new directory before
access. It preserves historical evidence and the failure-only historical binder.
There are no provider requests, workers, backend executions, trajectory generation,
or NMPC solves. A single MATLAB Engine session serves the matrix comparison batch.
The existing installation needs Engine 24.1 and licensed Control System Toolbox.
If Windows sandbox access prevents MATLAB startup, --matlab-only --output PATH
retries just saved matrices in an environment where MATLAB can launch.
--report-only --output PATH verifies/renders retained results without Engine work.

Public tools, all version 1.0.0:

* analysis.linearize_saved_case: case and protocol EvidenceRefs -> model EvidenceRefs.
* analysis.control_metrics: models and protocol EvidenceRefs, implementation
  scipy or matlab -> the same AnalysisResult contract. Selection names trusted code.
* analysis.saved_case: case and protocol EvidenceRefs -> saved measurements/facts.
* analysis.compare_case_metrics: result EvidenceRefs and protocol -> case statistics.

The offline study demonstrates both design-facing and diagnostic-facing callers
through Host.invoke, with identical results and no agents. For example, using its
existing analysis session (whose tool budget must still have capacity)::

  import json
  from pathlib import Path
  from tools.platform_host import Host
  root = Path('runs/offline_math_analysis_20260930_final')
  saved = json.loads((root / 'cases/b2_near0p169_far0p129_compliant_s1p05/metrics.json').read_text())
  host = Host(root / 'analysis', 'offline-math', actor='diagnostic-facing')
  receipt = host.invoke(dict(
      request_id='example-control-metrics', tool_id='analysis.control_metrics',
      tool_version='1.0.0', reason='Inspect the shared saved model contract',
      arguments=dict(models=[saved['records'][0]['model_reference']],
                     protocol=saved['protocol'], implementation='scipy')))
  result = host.store.artifact(receipt['output'])

Implementation
--------------

schemas/platform_analysis.py adds a versioned output-aware model without changing
LinearizedModel or DynamicSystem interpretation. The tendon adapter differentiates
the explicit symbolic world tip expression R*tip(q)+translation. The resolved basis
supplies dimensions and coefficient ordering (the study is q=12, x=24, u=6, y=3).
Saved pre-step observations carry the previous applied input and the actual input
for the following held interval as separate fields. Missing observations stay missing.

extensions/math_analysis/kernels.py holds family-independent matrix kernels;
extensions/tendon_family/math_analysis.py binds robot data. Public tools reuse the
existing registry, Host, immutable artifacts, receipts, budgets, dependency hashes,
and MATLAB resource reservation. The linearization tool caches the existing CasADi
graph and reuses the existing bounded damped-Newton static solver once per case.
The frozen limit is 20 iterations, at most 262 residual evaluations, no recovery.

Fixed protocol
--------------

Nodal curvature scales use baseline section lengths (near 0.16 m, far 0.12 m),
not candidate lengths. Velocity scales divide by 0.35 s; tension uses 8 N and world
tip uses 0.01 m. Positive scale vectors and their derivation accompany each model.
The 65-point log frequency grid spans 0.1 to 1000 rad/s. Nominal Gramian windows
are 0.05, 0.10 and 0.35 s; saved samples are 0, 0.10, 0.20, 0.30 and 0.34 s.
Nominal windows are explicitly distinct from remaining task time.

Continuous Gramians use short-interval Van Loan exponentials and doubling, avoiding
overflow from stiff negative modes. Held-input Gramians sum Ad^j Bd Bd' (Ad')^j / dt
for the cost sum(dt*||delta_u||^2). MATLAB uses gram/gramOptions on stable A and
the explicit exponential method on unstable/marginal A; A is never modified.
MATLAB also uses ss, pole, damp, freqresp, sigma, and c2d(...,'zoh').

The endpoint for minimum energy is y0 + C*integral(exp(A*t)*drift dt), holding
physical u=u0 (zero perturbation input). Thus energy includes affine drift.
Unreachable components remain explicit and make full correction energy unavailable.
Nonzero D makes this endpoint correction unavailable because instantaneous direct
feedthrough requires a different endpoint/cost definition.

Rank cutoff: 1e-12 + 1e-9*largest Gramian eigenvalue. Numerical comparison:
elementwise abs(error) <= 1e-8 + 2e-6*abs(reference). Pole sets use optimal matching;
eigenvector signs/order are not compared. Directional AD checks use step 1e-5,
normalized atol 2e-5 and rtol 2e-4. Dynamic equilibrium requires normalized drift
infinity norm <= 1e-5/s, independently of the 1e-10 static-force solver criterion.
No tolerances are fitted to terminal results.

Interpretation
--------------

These are local unconstrained quantities. Input bounds, unilateral tensions,
nonlinear trajectories and closed-loop stability require separate interpretation.
Transient Jacobian frequency curves are not measured steady-state responses.
Usable bandwidth is undefined without an independently justified MIMO threshold;
if supplied in a future frozen protocol, the rule retains the connected grid band
from the lowest frequency with minimum singular value at least that threshold.

The retained report separates MATLAB/SciPy numerical verification from retrospective
explanatory usefulness. Nine cases and one pass establish neither causality nor a
universal design threshold. All source hashes, matrices, facts, sample locations,
counterexamples, plots, usage receipts and unavailable reasons are under the run.

Focused verification
--------------------

tests/test_math_analysis.py covers analytic finite Gramians (including marginal,
unstable and stiff systems), normalization/ZOH and held energy, unreachable targets,
sampling phases, and public Host evidence/serialization/zero execution accounting.
The study additionally checks nine CasADi directional derivatives, seven real
MATLAB/SciPy representative models, and repeats lightweight saved-matrix calculations.
