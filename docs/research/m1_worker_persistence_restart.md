# M1 persistence repair and independent restart

Baseline: `134673c57f4e24383115f5410834563abfc87ebf` on
`codex/m1-final-interface-audit`. The predecessor remains engineering-paused, with
eight Provider requests, seven public operations and one failed mathematical
evaluation retained. It is not migrated, reset, reopened or supplied as evidence
to the new Main.

## Narrow repairs

`tools/state_io.py::io_path` supplies an absolute Windows extended path at the
filesystem boundary, including UNC conversion; other platforms retain their
ordinary paths. Existing `read` and `atomic_json` use it, preserving UTF-8/LF JSON
bytes, the sibling `.tmp` write and atomic replace. Logical paths in scientific
requests and Store identities are unchanged. SDK storage reuses that same helper.
Worker checkpoint existence checks and analysis/Replay file enumeration, logs and
receipt recovery use it too. The helper itself is included in original core
source freezing. Checkpoints still reject overwrite; real errors still propagate.
No registry setting, Store location, numerical algorithm or control was changed.

Reporter can consume the last request of a supervised segment inside the
before-model hook. That hook now rechecks the same cap after Reporter completion.
The original LiveBoundary reservation guard remains authoritative, with its cap
exception classified as the existing SupervisorReviewPause. The existing unwind
path saves a paired settled SDK snapshot, records the pause and returns normally.
No new retry controller, session state machine or budget owner was introduced.

## Focused offline verification

Six new fixture tests cover deep-path atomic read/write and exact content,
temporary-file completion, Windows absolute/UNC/extended path handling and a
non-Windows projection; checkpoint overwrite protection and complete Worker
result reading; incomplete calculation charging, idempotent settled reuse and
unknown-termination no-relaunch; deep result/progress recovery into the original
Store receipt; and actual SDK Mock HTTP with seven Main calls plus Reporter as
request eight. Restoration sends no request, and the next separately allowed
call receives the preserved Reporter feedback without another Reporter charge.
Two existing Provider-budget/request-feedback boundary regressions also pass.
All eight checks use fixtures only: no real Provider, numerical Worker or physics.
An initial extra-test command named a nonexistent test class; the corrected
existing test ran successfully. No production change was needed for that typo.

## Independent resource scope

The fresh configuration starts with an empty candidate pool and preserves the
original 1--9 segment / 1--7 tendon FamilySpace, all three tasks, physics, grids,
actuator bounds, acceptance thresholds and Knowledge whitelist. Its instructions
make task feasibility first and fewer tendons an important secondary preference
among comparably promising directions, without a weighted task/complexity score,
forced count order, inherited design or post-success optimization phase.

New limits: Provider 72 (12 protected), public operations 233 (16 protected),
mathematical evaluations 15, independent Replay 18; Native per request remains
800 callbacks / 100 iterations / 4 knots. All tasks retain 600 integration steps.
New conservative bound: `15 * 801 * 600 + 18 * 600 = 7,219,800` steps. Including
one conservative predecessor mathematical slot retains the original 7,700,400
window bound. Original failed fees are not refunded. Earlier independent history
and engineering probes remain separately identified, never recast as new results.

The user's current instruction explicitly authorizes this repair-and-restart
scope. Only after committed implementation, resolved configuration and scope
verification may the original formal authorization event be recorded. The frozen
PENDING text is retained; no gate is weakened. The first real segment is at most
eight requests including Reporter; further authorized continuation stays in this
one new Study and leaves all scientific choices to Main.

## Actual independent run and sealed outcome

Study: `m1-open-topology-restart-20261101-fefefd8c`. Frozen implementation:
`c4de879c552de66b2bf9e95baeb68f8eeb4517e5`. Resolved identity:
`9d8eb242a4d6168bd6def4b1e4ca354333848eeabf5562e2eb8ef725ac613212`.
Approval scope: `16282ecbc25a3dfb93855a5acfc7b85fe90cd4d515d00c5e5c27ccdf601472ad`.
Scientific scope: `34dc6e0990ae1ee01a47007b18f47e8ec9631ebaac48421bd891455266d938ea`.
The original formal authorization event binds the user's repair/restart approval
to these verified identities. Original authorization and dependency guards pass.
The frozen interpreter and existing Gateway model, proxy and tools were retained;
health/catalog checks returned 200 without extra inference probes.

The first segment used exactly eight sends (seven Main, one Reporter), paused
normally with CLI exit 0, and restore-only used no extra request. Continuations
in this same Study reached 24 and then 40 total sends, both with exit 0. Main
submitted its own legal STOP as send 40; all ten new results were cited after
public evidence reads. It was not an Operator STOP or automatic exhaustion of
Provider/public protection reserves. All 40 sends returned HTTP 200, with zero
rejected sends or unknown outcomes. There are no pending Workers or unsealed
receipts. The accepted STOP seals further execution despite unused resources.

Main independently explored three segments/four tendons and then three
segments/five tendons with different routing, initialized fresh positive_high
controls for each, and tried Native T1 and Direct control formulations. All six
control computations encountered MuJoCo FatalError:
`FactorizeHessian: rank-deficient sparse Hessian` at 0.168 s. Each recorded 168
completed steps and an unsuccessful 169th attempt; zero rollouts completed.
Results, partial progress, logs, runtime and receipts were successfully persisted
through the formerly failing path boundary. These are incomplete numerical
computations, not completed optimizer failures, physical task rejections or
infeasibility certificates. Their common underlying numerical cause remains
unlocated; production physics/solver settings were not changed in this run.

Three real frozen-initial-state mechanism inspections completed. Instantaneous
drive singular values on the five-tendon candidate were approximately
`[211.785, 1.154e-8, 7.868e-25] m/s^2/N`. Directional acceleration bounds were
`[-821.493, 821.493] m/s^2` in world y and `[-881.843, 862.223] m/s^2` in world z.
A phase derivative returned not-applicable because guide-hole clearance blocked
the perturbation; it supplies no improvement direction. It retained five charged
evaluations under the existing request accounting, with three actual mechanism
probe attempts. The three inspections charged one each; six incomplete control
requests charged one each: 14 charged mathematical evaluations across ten results.

Main explicitly used these results: it proposed a local conditioning explanation
from the singular values, then weakened a lateral-authority explanation after
the directional bounds and returned to task-level trajectory questions. The
four-to-five-tendon revision followed incomplete control feedback, before these
completed mechanism results. No subsequent structure revision or completed
control reoptimization was produced from completed mathematical evidence.
Knowledge `research-bounded-continuation@2` was actually read once and marked
adopted in eleven Plans; its demonstrated use was procedural treatment of bounded
failure and fresh controls, not a supplied successful structure.

There were two corrected Schema errors, one corrected initial-state/source
prerequisite choice and one rejected derivative budget request requiring ten
evaluations. None of these invalid requests launched a scientific Worker.
Valid tools / Provider = 31/40 (77.5%), including reads, routes, diagnosis and
admitted incomplete mathematics. Completed generation + initialization + computed
mathematics / Provider = (2+2+3)/40 (17.5%); completed mathematics alone = 3/40.
These definitions do not count incomplete research as completed science.

No independent Replay, complete acceptance certificate or SELECT occurred for
any condition. Negative_low and central_high were not executed. Both structures
remain unmeasured under independent task acceptance; no fewer-tendon winner or
global minimum is established. Main chose STOP with one mathematical evaluation
left, judging further joint feasibility research unpromising within that allowance.
This judgement is not a deterministic proof that all possible use of remaining
controls/Replay resources must fail. Remaining Provider/public allowances were
32/198, above protected reserves 12/16.

New consumption: 40 Provider (35 Main/5 Reporter), 35 public operations, 14 math,
zero Replay; remaining 32/198/1/18. Recorded numerical work totals 11 model builds,
133 forwards, five mechanics evaluations and 1,008 completed integration steps
(1,014 attempts); charged numerical wall time is 11.6711529 s. The six recorded
rollouts were started but incomplete. Adding the predecessor yields 48 Provider,
42 public, 15 math and zero Replay for this 80/240/16/18 resource window. Earlier
separate history (43 formal Provider, one math, 19,200 steps, plus eight engineering
probes) stays separate and charged. Nothing is reset or refunded.

The predecessor's 23-file manifest still matches. Both older STOP Stores retain
all 13/218 manifest files and matching hashes; the earlier zero-run Study remains
zero-run. The new complete private archive has 133 files, including 37 SDK files,
and an extended-path SHA-256 manifest. Only derived identities, costs and findings
are published in `evidence/m1_worker_persistence_restart/summary.json`. Raw Stores,
full Provider wires, approval source text, controls and credentials remain local.
No other Study, M2/M5 run or main-branch merge was performed.

## Read-only clarification of repeated numerical failure

All six saved failures name `native.sequence -> mj_step` under MuJoCo 3.13.0,
implicitfast, Newton, auto Jacobian selection and 0.001 s steps. Each occurred in
the initial uniform-pretension baseline, with zero completed optimization
evaluations; T1 and Direct share `native_control.calculate` and
`NativeModel.rollout_sequence`. Changing the question/objective/window therefore
did not avoid the failed baseline. Before each failing call, saved positions and
velocities were finite, warnings were zero and ncon/nefc were both zero. The
exact internal failure state and solver factorization are unavailable. This does
not establish that a contact appeared, inertia was singular, or actuation rank
caused the error.

The [MuJoCo 3.13.0 source](https://github.com/google-deepmind/mujoco/blob/3.13.0/src/engine/engine_solver.c)
raises this error when its sparse Newton Hessian factorization returns deficient
rank; it is distinct from the Agent's tendon-to-tip singular-value diagnostic.
An [upstream numerical fix](https://github.com/google-deepmind/mujoco/commit/35c0631de)
documents lost pivots for ill-conditioned single-precision inertia. It supplies
a relevant lead, not proof of the cause or an applicable remedy for this frozen
binary. No engine was upgraded or scientific computation rerun for this check.
The later repeated baseline attempts added no complete trajectory evidence;
engineering supervision should have isolated that common failure earlier.
