# Bounded CasADi joint length and trajectory pilot

The branch starts at `34307384307158dba899ad2499a8b3e582f8356e`.
Historical mixed-design and SoRoMoX activities remain sealed STOP. The frozen
specifications in `examples/casadi_codesign` retain the source physical task,
generator, controller 11 recipe, and independent ideal tension channels.
SoRoMoX adoption remains deferred.

The accepted interpreter is Python 3.11.16 with CasADi 3.7.2, SciPy 1.17.1,
MuJoCo 3.13.0, Strands Agents 1.59.0 and Strands Harness 0.2.0. No new
optimization stack or environment upgrade is required.

```powershell
Set-Location D:\softrobot-agent\.worktrees\casadi-codesign-pilot
$studyPython = 'D:\softrobot-agent\.mainline5-env\Scripts\python.exe'
& $studyPython -m tools.research_casadi_codesign prepare
# Commit implementation and frozen specifications before binding/dispatch.
& $studyPython -m tools.research_casadi_codesign bind
& $studyPython -m tools.research_casadi_codesign check
& $studyPython -m tools.research_casadi_codesign solve --case A
& $studyPython -m tools.research_casadi_codesign solve --case B
# Persist the least-violating retained noninitial schedule when infeasible.
& $studyPython -m tools.research_casadi_codesign select --case A
& $studyPython -m tools.research_casadi_codesign select --case B
# Pass the selected reference (or feasible solve/trajectory reference).
& $studyPython -m tools.research_casadi_codesign replay --candidate '<EvidenceRef JSON>' --request-id replay-A
& $studyPython -m tools.research_casadi_codesign status
& $studyPython -m tools.research_casadi_codesign export
& $studyPython -m tools.research_casadi_codesign stop
& $studyPython -m tools.research_casadi_codesign export
```

Direct numerical entry points are `correctness`, `solve`, and `replay` in
`tools.casadi_codesign_worker`; the typed Host tools call exactly these in an
isolated subprocess. Direct scientific dispatch must carry the same reservation
and ledger; the CLI is the recommended accountable entry point. Native Strands
can wrap registry input/output schemas through the existing `PythonAgentTool`
pattern. Live provider requests are optional and credentials are loaded only
at actual send time through the existing loader/boundary.

`GVSCasadiFunctions` accepts an optional explicit length map and design input;
fixed-design signatures remain unchanged. Distributed descriptors retain their
complete normalized section tensors and acquire symbolic integration-length
ratios. Rigid mass and local inertia stay fixed, with symbolic poses and moment
arms. Every design-dependent nested mass-wrench call takes the design input.
Tip speed differentiates position with respect to curvature at constant design.

The decision vector has a single shared `d`, 36 reduced states and 35 six-channel
tensions on the primary grid. A fixes `d=0`; B permits `[-1,1]`. Flexible lengths
are `0.16+0.0055*d` and `0.11-0.0055*d`. Initial positions and rates are fixed
zero. Coherent guesses are Newton implicit rollouts from that state with either
constant 0.2 N or the paired 0.2 to 0.4 N ramp. They are numerical guesses.

The objective is mean squared tension divided by 8 N plus 0.1 times mean squared
successive tension changes divided by 8 N. Hard normalized squared-norm
position/speed inequalities cover every node from 0.30 through 0.35 s; terminal
position is separately named. Curvature decisions scale by 10 rad/m, rate by
1000 rad/(m s), kinematic defects by 10 rad/m and force balance by 0.001
N m²/rad, matching the existing implicit transcription. Solver diagnostics
retain normalized violations; task metrics retain metres and metres/second.

Offline IPOPT uses exact first derivatives, sparse reverse-mode constraint
Jacobians, limited-memory Hessians, retained feasible iterates, 1000 iterations
and a 600 s solve ceiling. The original primary A used 600 s CPU/wall options
and returned after 608.7 s because IPOPT checks between iterations. Its evidence
is retained. Following that known overrun, 570 s CPU/wall options reserve a
30 s stopping margin; comparisons identify the differing effective limits.
The controller's feasible-return policy is
absent. Graph construction is timed separately. A numerical invocation is
counted before dispatch, with actual solver entry established by diagnostics
and logs. Unknown outcomes retain their pending identity and forbid automatic
repeat. Known failures may receive a scoped committed repair with the original
receipt preserved and explicit dependency migration, within the same grant.

One cumulative activity caps primary/paired/correction solves at two each,
six total; physical launches at two (1800 s each); provider sends at four; and
numerical process time at 7200 s. Process reservations include construction,
checks, guess generation, solves and replay. Eight hours includes engineering,
with the last 30 minutes protected. Re-running prepare does not reset capacity.

The first Radau replay exceeded its 900 s reservation without a returned
trajectory. Its original unknown event was reconciled to a known failed
numerical worker after checking process absence and the installed Python
timeout/kill behavior. The failed attempt remains charged and archived.
Replacement replay uses adaptive SciPy BDF with exact direct-graph state Jacobians,
relative tolerance 1e-8, curvature/rate absolute tolerances 1e-9/1e-7, and
continuous state across each 0.01 s input switch. Dense output every 0.0005 s
checks the task and compares optimizer tip outputs using documented linear
interpolation, while node discrepancies are retained separately. Sampled
0.01 s position and instantaneous Jacobian speed metrics remain separate.
Physical eligibility requires mathematical feasibility, replay discrepancy
limits of 1 mm/0.002 m/s, and the original reach/hold limits. Controller 11
validation tests geometry/controller behavior, separately from optimized
open-loop schedule execution.

The recorded corrections use the existing exact automatic AD execution mode
after a single equivalence check, with unchanged equations and fresh primary
guesses:

```powershell
& $studyPython -m tools.research_casadi_codesign check --scope jacobian_execution --request-id full-constraint-jacobian-execution-check
& $studyPython -m tools.research_casadi_codesign solve --case A --category correction --jacobian-mode automatic --request-id correction-A-exact-auto
& $studyPython -m tools.research_casadi_codesign solve --case B --category correction --jacobian-mode automatic --request-id correction-B-exact-auto
```

These commands document the executed study. Its stopped grant is not reopened
to repeat them. `select` does not optimize; it preserves solver-selected feasible
candidates or selects the smallest independently recomputed normalized violation
among retained noninitial checkpoints. Every selection names its source artifact.
For reproducible inspection, `evidence.read` takes an `EvidenceRef` and JSON
pointer such as `/costs_s`; the archived Store artifacts retain the complete
dependency snapshot, solver trace, variables, inputs and replay trajectories.
The generic receipt's `solver_status=not_run` is a backend-result envelope field;
the mathematical tool's typed Feedback carries the actual IPOPT status and
termination. Physical status is reported separately.
