# PHS-2D initialization repair and successor

Branch: `codex/phs2d-initialization-successor-20261105`, based on the requested
`bf67b178c1438d2706a2e628b1c5131c334e1771`. The stopped parent and its Store,
failures and charges remain untouched. No merge into main.

## Diagnostic conclusion

Only two saved failed designs were examined. The contact sample failed its first
forward under both single-start and original dual-start execution; the original
abort behavior never reached the second start. The failed-call diagnostic observed
228 contacts; that partially mutated state is not a valid completed forward.

The other sample had a saved formal dual-start result, which was reused. Its first
start terminated after five iterations with a 0.154 m primal violation. The second
hit 400 iterations, with stationarity 1.7495922075 N m and primal violation
2.49571134e-6 m; KKT, capacity and sufficient stiffness checks failed. Neither
start qualified. Positive stiffness at the first unqualified point does not prove
stability. The legacy scene's dual-start calculation also failed.

Three differences were confirmed: omitted multistart, a legacy static floor at
-100 m instead of the frozen native task scene, and warm-started structural probes
instead of the formal baseline starts. No sampled false negative was established;
the causal role in the parent's failure remains unproved. The repaired mathematical
path reproduced both saved formal trials exactly on the physical qualification
fields and state. See `phs2d-initialization-diagnostic-20261105.json`.

## Local changes and checks

- `passive_equilibrium.mechanics` accepts backward-compatible
  `unloaded_multistart=False` and an optional qualification-only inspection.
  `solve` keeps its acceptance and abort rules, adding per-start initial
  contact/length facts, cost and partial progress on exceptions.
- `structure_research.calculate` uses the original PHS scene, static solver and
  declared starts. Existing `inspect` with `constraint_active_set` on the frozen
  baseline exposes unloaded qualification. No new action, solver or Worker
  reservation state machine was added. Complete dynamics independently requalify.
- The existing result summary and Reporter projections carry initial-forward,
  unilateral length, numerical termination, KKT, capacity and conditional
  stability facts. Failed-point gradients do not establish a mechanism conclusion.
- Cross-candidate initialization review lists requested methods, unresolved
  explanations and optional research directions with costs/prerequisites. The
  existing STOP opportunity review asks why alternatives are declined, without
  requiring an experiment or forbidding justified STOP.
- `phs2d-research-process@1` is a real `case`, admitted only by its explicit
  whitelist. It contains seven English decisions: unloaded qualification;
  numerical versus physical failure; finite deformation; constraint geometry;
  actual guide holes; material relaxation/settling; complete independent checks.
  The first request receives six linked process summaries and seven transferable
  lessons. Detailed reading is optional. Repeated failures and STOP receive
  bounded reminders. Attribution remains Codex/operator organization, not proven
  autonomous discovery. No winning parameters, labels or reconstruction references
  were added to the case; benchmark-answer access remains disabled.

Four directed tests passed in 23.973 s, including a real SDK/Mock Provider wire,
on-demand detailed reading, cross-candidate reminders and the original Knowledge
SELECT/STOP isolation. The accounting regression reused the saved real kernel
output: one mathematical charge, retained kernel cost, zero backend episode
reservations and unmeasured task acceptance. The real kernel checks themselves
used two models, zero integration steps and no Provider. Including initial
diagnosis, this task built five static models, with no loaded episodes or search.
These engineering checks are not current-Study scientific evidence.

## Independent formal successor

`phs2d-mechanism-successor-20261105` is prepared with the original ten conditions,
nine-segment/four-tendon domain, physical model, qualification and Replay/SELECT
rules. The model remains Gateway `gpt-5.6-sol`, Main `medium`, Reporter `none`.
The new Store starts independently; it does not reset parent costs.

The concrete approval request is `phs2d-successor-authorization-20261105.json`:
64 shared Provider requests (6 protected), 80 backend episodes, 320 public
operations (10 protected), no cumulative mathematical count quota, and finite
unchanged Worker watchdogs. Provider extensions remain limited to at most eight
per exact addendum, with a total policy ceiling of 128; that policy does not grant
an increment in advance.

Status: explicitly approved and genuinely running in the same formal Study.
The existing request-feedback live admission was registered separately; no Provider
was sent before both admission and current-identity authorization passed.

At the first settled eight-request boundary: seven Main requests and one Reporter
request, one legal design, one real unloaded qualification check, zero loading
episodes/integration steps/backend episode charges, no independent Replay or SELECT.
The check reported initial-forward failure and partial failed-call contact facts;
no qualified unloaded point exists yet. Main proactively read the detailed expert
case, and its body delivery is confirmed by saved Provider requests. Main then
chose the low-cost check, explicitly distinguishing numerical, unilateral-branch
and geometric explanations and declining premature differentiation/full dynamics.
That is observable method use consistent with the experience; it proves neither
causal benefit nor a feasible mechanism. One invalid Plan field was rejected
without a scientific launch, then Main corrected it.

The user also authorized timely public-interface repairs and conditional Provider
increments. Existing settled transactions, batches of at most eight, the 128-total
policy ceiling, exact identity rebinding and actual cost preservation still apply.
Scientific failures alone are not interface defects. Source and sanitized reports
were explicitly authorized for push to the existing origin branch; private Stores,
full wires and credentials remain local.

## Live checkpoint after 44 shared requests

The same formal Study has two candidates and seven mathematical attempts. No
qualified unloaded point, loading integration, independent Replay or SELECT exists.
The one full-task attempt failed its hard-initialization forward and retained its
ten-episode reservation charge; 70 physical episodes remain. New native
position-only geometry now succeeds before the failing full forward, supplying
initial contact and tendon-length/payout facts as separate observations. Main
requested that geometry-first question and used the updated optional check.

Three small live feedback repairs are committed: shared hard-initialization
dependency/model binding; actual Knowledge receipt/summary aliases; and initial
position facts in existing unloaded inspect. Physics, solver settings, scientific
profile, original qualifiers and old records remain unchanged. Tests were limited
to existing-record projections, the affected SDK/gate checks and one position-only
engineering call. No Provider rehearsal or broad physical regression was run.

The latest user instruction authorized conditional small Provider increments.
One existing exact addendum raises the limit from 64 to 72, in an eight-request
batch, based on the new discriminating geometry evidence. All 44 prior requests
and costs remain. Physics stays at 80 total episodes and mathematical count has
no cumulative quota. The policy ceiling remains 128; this does not pre-grant all
remaining increments. See `phs2d-successor-live-status-20261105.json` for measured
counters, token usage and the distinction between experience delivery, reading
and observable method use. No causal benefit or research success is claimed.
