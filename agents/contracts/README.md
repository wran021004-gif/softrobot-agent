# Authority boundary

Human defines scientific semantics and approves immutable truth. Engineer proposes
routes/designs, Coding implements approved rules, Diagnosis attributes failures
from evidence. Numerical tools compute; canonical gates decide outcomes.

Human-owned: tasks/, benchmarks/, physics_contracts/, schemas/, capabilities/,
metrics/, official configs/, legacy environments, and authorization contracts.
Agents read these and submit separate proposals. Runs are written by the trusted
Harness artifact service; agents cannot rewrite evidence. The current migration
establishes these files under the user's explicit architecture request without
changing baseline scientific values. This is not ongoing authority to edit them.

permissions.py supplies deny-by-default checks with resolved path containment and
protected-prefix rules. Unknown roles/paths and traversal outside the repository
are denied. Output schemas forbid extra fields; Diagnosis has no task-success
override. No LLM, mock physics tools or autonomous executor is present. This policy
is an application contract, not OS isolation: a future executor must enforce it
before every write and use filesystem isolation/Human code review for arbitrary code.
Permitted software files can still contain harmful semantic changes, so path checks
alone cannot validate physics or prevent a malicious implementation.

## Optimization boundary

The existing family grammar owns per-field optimization metadata and the objective
source reference. All current fields are optimizable=false with null bounds and
scientific_status=human_approval_required. Examples are not approved bounds.
agents/contracts/optimization.py checks names, approval, units, finite bounds and
supported constraints. EngineerOutput validates selections at construction; a
future executor must recheck selections before execution and every candidate with
validate_optimization_candidate. Candidate validation reloads policy, rejects
out-of-bound values and unselected field changes, then applies DesignSpec and the
existing resolver. No caller-supplied bounds or objective is accepted.

Human defines the allowed set, bounds, units, constraints, provenance and objective
authority. Engineer selects from that set; an optimizer may only produce values
inside it. Coding cannot edit grammar/policy, objective, metrics, tolerance,
benchmark or run evidence. This contract is not an optimizer; optimize_design
remains PLANNED. Simulator settings and frozen task/environment/metric fields
cannot enter this design-variable mechanism.

## Isolation activation point

Application-level authorization is implemented; OS/process isolation is not.
Before autonomous Coding LLM write access, require an isolated worktree, a
permission-enforcing executor, post-run git diff allowlist and Human review.
Optional stronger isolation uses a separate OS user, WSL2, container or VM with
Human-owned sources read-only. No autonomous executor is introduced here.

Path checks reject traversal, resolved escapes, Windows device/UNC/drive-relative
paths, alternate data streams, reserved names and trailing-dot/space aliases.
Windows case/separators are normalized; existing links are resolved. These checks
are not OS isolation. A future executor must also prevent link/race changes and
arbitrary code effects; a software allowlist alone cannot enforce scientific truth.

## Trace and Skill integration contracts

Round 1.5 adds schemas.trace.DecisionRecord: actor, structured decision, a short
public rationale, requested tools, evidence links, selected versioned skills and
next action. It has no private chain-of-thought fields. Current traces contain
actual Harness/tool/gate actors only, not fictional agent activity.

Future Engineer can retrieve DESIGN/MODEL_SELECTION/CONTROL strategies; Diagnosis
can inspect the trace and retrieve DIAGNOSIS strategies; Coding can retrieve
CODING_SIMULATION strategies. All recommendations still pass through existing
role permission checks before execution. Skill Curator is a role contract only
(../skill_curator/ROLE.md) and receives no write scope. Human remains the final
Skill approval authority. No existing agent permissions are expanded.

## Gate scientific authority (Round 2.5)

Human alone defines benchmark truth, Gate scientific authority and Physics Contract
approval. schemas/gate.py encodes the three meanings and their fixed actions:
HARD FAIL stops the current candidate, SCREENING FAIL continues physical validation,
CANONICAL FAIL remains TASK_FAILED. Diagnostic work may continue after a final failure
but never changes it. Tool execution status is distinct from a Gate decision.

Spec legality and grammar/capability support are HARD input/execution conditions.
The workspace HARD rule is norm(target-base) <= L + task tolerance, because the
fixed-base, inextensible V1 endpoint norm cannot exceed L (triangle inequality).
This is necessary, not sufficient; a target just beyond L can still satisfy tolerance.
M0's unchanged exact-target observation norm(target)<=L alone is not the task gate.
Only that length-bound rejection implies geometric infeasibility under this specific
representation; missing software or invalid input is not proof about real robots.

Valid model outputs/commands, compilation and finite-state execution are HARD
execution conditions. Physics sanity proves executable finite evidence only, not
task success, convergence or physical fidelity. PCC task and full-shape clearance
predictions are SCREENING irrespective of their MATLAB backend. Tool runtime failure
is an execution HARD failure, not a negative scientific prediction.

The actual TaskSpec evaluator is CANONICAL: target tolerance for reach_free;
target AND approved initial side AND final aperture AND no forbidden contact for
reach_window. CANONICAL labels the final evaluation role, not benchmark membership.
A NON_CANONICAL development fixture remains development-only even when that
evaluator passes. Only an explicit Human-approved frozen package/registry entry is
a formal benchmark. Historical traces missing gate_type remain untyped; no type
or authority is inferred from a tool name.

Engineer can propose next routes, Diagnosis can explain observations, and Coding
can implement approved rules. None can change the type/threshold, waive a HARD
condition or override CANONICAL. A future Engineer route policy may choose among
screened candidates only under separate Human-owned policy; none is introduced here.
