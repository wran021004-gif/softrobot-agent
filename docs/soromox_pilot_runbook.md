# Bounded SoRoMoX model-admission pilot

This entry starts from mixed-design commit
`2d13dfcc6395e09b53f6241dac3cae24ee69abb8` on
`feat/soromox-codesign-pilot`. It has a fresh Store, grant and eight-hour clock.
The historical mixed-design study remains STOP. No historical execution is
reopened or treated as a successful two-segment baseline.

The admitted scope is two physical flexible segments, actual asymmetric 3+3
tendon routing, six independent 0–8 N ideal tensions, 24 physical cells, and the
existing structural-linear basis. A freezes lengths at 0.16/0.11 m; B declares
one independent proximal length in [0.1545, 0.1655] m with distal length
`0.27 - L_proximal`. The two full specifications in `examples/soromox` fix the
task, weights and controller 11 recipe. Their `physical_source` is an existing
generator/compiler contract; its historical search-method field is not the
new mathematical method. The pilot does not dispatch that search.

Use the accepted interpreter for Host/Store/Strands and the separate numerical
interpreter for SoRoMoX. The accepted environment must not be upgraded.

```powershell
Set-Location D:\softrobot-agent\.worktrees\soromox-codesign-pilot
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
$pilotPython = 'D:\softrobot-agent\.soromox-env\python.exe'
$pilotConda = 'C:\Users\gugugaga\miniconda3\Scripts\conda.exe'
# First-time setup only. Existing prefixes are reused, never rebuilt by run.
& $pilotConda create --prefix D:\softrobot-agent\.soromox-env --file examples/soromox/conda-win-64.lock --yes
& $pilotPython -m pip install -r requirements-soromox-pilot.lock
$env:PATH = 'D:\softrobot-agent\.soromox-env\Library\bin;' + $env:PATH
& $pilotPython -m pip check
& $studyPython -m unittest tests.test_soromox_pilot tests.test_mixed_design.MixedDesignTests.test_full_dispatch_and_numerical_initialization -v
& $studyPython -m tools.research_soromox prepare
# Commit implementation and frozen specs before scientific dispatch.
& $studyPython -m tools.research_soromox bind
& $studyPython -m tools.research_soromox check
& $studyPython -m tools.research_soromox smoke
& $studyPython -m tools.research_soromox status
& $studyPython -m tools.research_soromox stop
& $studyPython -m tools.research_soromox export
```

The [official cyipopt binary route](https://cyipopt.readthedocs.io/stable/install.html)
uses conda-forge on Windows. The recorded environment contains Python 3.11.17,
SoRoMoX 0.5.0, JAX/JAXlib 0.10.2, cyipopt 1.7.0 and IPOPT 3.14.20. The explicit
conda lock preserves native packages; the pip lock contains only the numerical
pip layer, without nonportable conda build paths. No rendering or RL extras are
installed. CPU float64 is enabled before numerical construction. The process
adapter exchanges `WorkerInput`/`WorkerOutput` through local JSON files and
prepends the native DLL directory only in its child environment.

`math.soromox_describe@1.0.0` resolves the physical source and runs admission once.
It stores the complete checks and returns a compact typed packet.
`math.soromox_solve@1.0.0` and `math.soromox_replay@1.0.0` return retained gate
rejections for this incompatible model. They do not contain a runnable NLP or
replay integrator. This is the bounded incompatibility outcome permitted by the
pilot stop rule, not completed joint optimization. The native GVS factory probe
is clearly separate from the exact JAX source-geometry diagnostic map.

The diagnostic map preserves the current nodal basis, offsets and discrete
guide geometry, and differentiates tip/tendon lengths with respect to runtime
length allocation. Compare zero and two nonzero states against the existing
CasADi kinematics and tendon Jacobian, check central length differences at three
steps, and check the virtual-work force sign. Tolerances are recorded before
comparison. Separately, probe the actual native factory and demonstrate that
interpolating nodal values with equal-size Legendre coordinates changes the
strain between knots. Inspect the rotated section tensors and retained package
source identities. The one-link native length-update check establishes only
that native kinematics can differentiate a length; it says nothing about full
candidate mechanics, material refresh, or optimal-design sensitivities.

The delivered evidence also records one justified native endpoint follow-up at
commit `1811aa6c`. Its subprocess command was
`& $pilotPython -m tools.soromox_native_followup <output-json>` under the same
Store reservation (`native-endpoint-followup`, 300 s ceiling). It compared the
endpoint-abscissa, interior-abscissa and dedicated tips APIs, with identity pose,
two states and three finite-difference steps. The dedicated tips API passed;
the endpoint-abscissa derivative failed. These results are retained without
rerunning the successful source-geometry checks. After the reporting repair,
the original result is linked through `original_admission_reference`.

The live smoke exhausted four provider requests during evidence inspection,
with native tool use demonstrated and the final model explanation incomplete.
No fifth request was sent. `smoke_outcome.json` retains this limitation and the
subsequent transport-cleanup repair. No additional provider request is available.

If mechanics admission fails, no trajectory objective/Jacobian, coherent state
guess, solve, replay or MuJoCo launch is eligible. The frozen prospective
objective is mean squared normalized effort plus 0.1 times mean squared tension
variation, with 35 constant-action intervals and implicit force balance. The
two prospective guesses are constant 0.2 N and a linear 0.2→0.4 N ramp shared
by A/B. Neither is physical initialization. A future mechanics implementation
would need independent state rollout, sparse Jacobian checks and replay before
dispatch; this stopped activity does not authorize that follow-on work.

One cumulative ledger caps actual provider sends at four, physical launches at
two and tools at 32. Activity time has an absolute eight-hour deadline with the
last 30 minutes protected. Numerical process time is separately reserved and
accumulated against 7,200 s. Worker timeout retains its pending identity and
blocks automatic repeat. Inspect the saved files, Store calls and provider
reservations after an interruption; never reset a grant or rerun an unknown
outcome. A scoped repair must be committed, retain the original failure, and
record the exact dependency migration before resuming. Completed STOP stays
sealed. Calling `prepare` again returns the same activity without replenishment.

Live smoke uses the existing credential loader with
`Path.home() / '.codex' / '.env'`, the current DeepSeek configuration,
`build_harness`, `LiveBoundary` and sequential native tools. No credentials or
auth headers enter the evidence. Every actual send, including summarization,
crosses the existing Store boundary; retries remain disabled. No model request
is used to plan or fabricate an experiment.

Read full artifacts through `evidence.read` in the active Host. After STOP,
use the committed archive and its manifest: each artifact filename is its
SHA-256 identity. The original local Store remains the recovery authority;
the export is evidence, not a replacement grant.
