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
