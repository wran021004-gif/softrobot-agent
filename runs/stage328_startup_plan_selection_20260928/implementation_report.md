# Stage 3.28: startup plan selection — withdrawn

The one bounded selection direction failed its predeclared local gate: it delivered the same startup plan while adding 4.235 seconds. The implementation is withdrawn; production files match `a4c695f`. No full deterministic confirmation, backend attempt, credential loading, or provider request occurred. The unchanged Stage 3.27 deterministic failure remains the latest full-task outcome. Live tracking, structured delivery, and prose delivery were each **not run**, not passed or failed.

## Saved-data diagnosis

The initial tree was clean on `feat/gvs-dynamics`, at `a4c695f` (exact identity in environment.json). Historical Stage 3.25 withdrawn SX work and all failed deliveries remain unchanged. Inputs were located from the Stage 3.26/3.27 indices and their input/summary execution bindings, without searching old run trees or copying databases. baseline_identities.json records source and numerical-preparation bindings.

Saved checks confirm equal robot, policy, initialization, environment, measured startup state, and absolute first-horizon reference nodes. The 0.10-second startup horizon cannot see the segment beginning at 0.40 seconds. Stage 3.27's first command, first predicted state, and recovered objective exactly match Stage 3.26 modified.json's t=0 case. The maximum first-command difference from Stage 3.26 full confirmation is 0.451083 N.

Stage 3.27 completed 70 samples, with maximum/RMS/terminal errors 11.264183/3.035140/1.541298 mm. Violations occurred at 0.05 and 0.06 seconds (11.264183 and 11.070651 mm). Segment 2 peaked at 1.541298 mm. All 70 plans were feasible, zero converged, all 70 missed deadlines; mean complete update was 8.684704 seconds and charged simulation wall time 612.672 seconds. No live session or provider request occurred in Stage 3.27.

The aligned predictions for those two endpoints were 9.729577 and 9.522583 mm, with prediction/execution differences 1.535584 and 1.548745 mm. At 0.60 seconds, the larger 1.835160 mm discrepancy coexisted with only 1.425523 mm actual error. The largest discrepancy therefore does not identify the startup failure's cause.

saved_diagnosis.json retains the complete measured states, previous applied tensions, absolute reference nodes, command changes, stop reasons, sources, available objectives, predictions, and timings for exactly t=0 and t=0.04 seconds. At t=0 the nominal applied pretensions are 0.2 N; the command change is 4.809031 N. The startup numerical seed exactly matches the indexed numerical-preparation artifact. At t=0.04 the previous command comes from the t=0.03 observation; the delivered command change is 0.402566 N. The historical controller shifted the previous accepted plan and regenerated its states, but that full warm plan was not exported.

Historical t=0 retained the feasible initialization (objective 173.118435), stopped for `budget_best_feasible`, and recovered the final unfinished iterate. Stage 3.26/3.27 recovery parent counts were 16/17, recovered objectives 1.060172/1.162427, recovery times 2.737814/2.652151 seconds, and complete updates 31.504374/31.908277 seconds. The t=0.04 Stage 3.27 update stopped with reported count 17 and selected feasible callback 4, objective 0.0907924124 versus warm-seed objective 0.0969342831; it performed no recovery and cost 18.377677 seconds. Its raw returned objective and complete horizon are unavailable. The saved 0.05-second prediction is one node, not a fabricated full plan.

## One bounded diagnostic solve

The missing full iteration-16 plan justified exactly one startup NLP solve, with the same initial state, pretensions, public numerical seed, references, model and discretization. Only for this diagnostic, wall-time return was disabled and max_iterations set to 20; the existing 30-second CPU safety remained. Callback vectors were retained only at indices 15–17. The initial callback was 0, final callback 20, and IPOPT reported 20 iterations: 21 callback invocations. Recovered controls and objectives at 16 and 17 exactly reproduce their historical counterparts, establishing the numbering correspondence for these observations.

| Callback | Raw objective | Recovered objective | Predicted horizon peak, mm | Terminal, mm | First command change, N |
|---:|---:|---:|---:|---:|---:|
| 15 | 3.669075 | 3.669704 | 18.736383 | 4.912482 | 4.207820 |
| 16 | 0.443973 | 1.060172 | 6.158384 | 1.517791 | 4.727754 |
| 17 | 0.478337 | 1.162427 | 9.508566 | 2.125971 | 4.809031 |

All three recovered plans independently meet the unchanged 1e-5 scaled feasibility rule. Recovery uses the existing implicit integrator and original objective. This diagnostic cost 33.231821 seconds before candidate recoveries, including cold setup and warm preparation; candidate integration times total 7.569041 seconds. It is not a production benchmark. It isolates substantial adjacent-iterate plan-quality differences, not their closed-loop causal effect or a repeatability distribution.

## Declared direction and gate

local_rule.json was written before either revised measurement. One optional controller field enabled a rolling shortlist of at most three finite callback iterates. Extra recovery activated only for tracking when the independently selected feasible incumbent was the initialization (callback -1 or 0). The original returned-iterate recovery ran first. At most two distinct recent candidates were then recovered against the original incumbent. An alternative had to be feasible, lower the delivered original objective, and not increase the original recovery output's predicted peak. There were no additional NLP solves. All production stopping settings, CSE, equations, integration, bounds, weights, reference and 10 mm task rule stayed unchanged. The extra effort was disabled when an optimized feasible incumbent existed. The opt-in field would have been frozen against length-only LLM edits; no live input was created.

The local gate required a startup predicted-peak reduction of at least 0.5 mm; independent feasibility; no objective increase above 1%; no critical-case peak increase above 0.1 mm; no startup first-command-change increase above 0.1 N; and no more than 7 seconds or 40% added complete update time per case. These are local experimental criteria, not new task acceptance or certified uncertainty margins.

Four focused tests initially passed, but their mocked recovery record omitted the production `source` key. The first revised startup attempt then failed while recording its first additional recovery: a duplicate `source` keyword raised TypeError. The actual failed log and patch are retained. One permitted correction changed the diagnostic dictionary merge and added the actual source key to the test fixture. All four focused tests passed again. Only the affected revised startup measurement was repeated; the critical revised case had not yet been attempted. There was one direction, one correction, and no heuristic search.

## Paired production measurements and withdrawal

Each variant ran in a fresh process, with identical saved states, previous command, warm input, absolute references, model and solver options. One implicit step and solver construction warmed the caches without an NLP solve. The complete update timer covers serial-state projection, warm preparation, solver, recovery, validation, command conversion, predictions and observation construction. Archive serialization and independent value checks are outside that timer. Cache setup was 12.582983 seconds baseline and 12.244683 seconds revised. No simultaneous numerical runs occurred.

The t=0 warm input is exact public preparation. At t=0.04 both variants use the same explicitly reconstructed constant-previous-tension input and repeated measured-state placeholders. Its initial objective is 22.276009, versus historical warm objective 0.096934; this is not a replay of the unsaved historical warm plan. Initial decision vectors and numerical solver options match exactly pairwise.

| Case | Baseline / revised objective | Peak, mm B / R | Terminal, mm B / R | Complete seconds B / R | Recovery seconds B / R |
|---|---:|---:|---:|---:|---:|
| Startup | 1.060172 / 1.060172 | 6.158384 / 6.158384 | 1.517791 / 1.517791 | 21.718099 / 25.952629 | 2.869564 / 7.307903 |
| Saved t=0.04 | 0.0620743 / 0.0620743 | 9.266184 / 9.266184 | 0.238470 / 0.238470 | 12.239050 / 11.980442 | 0 / 0.000013 |

Both startup solves stopped at reported count 16, returned raw objective 0.443973, retained initialization objective 173.118435 before recovery, and selected recovered callback 16. First-command change remained 4.727754 N. The revised path recovered three candidates versus one baseline. Both critical-case solves stopped at count 8 for relative seed improvement, selected independently feasible callback 8 with raw/delivered objective 0.0620743, and did no recovery; command change remained 0.534860 N. Startup/critical scaled violations were 1.7348e-11/2.5992e-8 in both variants.

The revised startup also recovered callbacks 15 and 14. Callback 14's raw objective 0.488450 was worse than 16's raw 0.443973, yet its recovered objective 0.488593 was lower than 16's recovered 1.060172. Its predicted peak was worse, 9.523437 mm, so the declared guard rejected it. This confirms that raw-objective ranking can reverse after reintegration and that a lower recovered objective alone does not establish better peak tracking. In candidate records, `iteration` is the candidate callback index; the embedded legacy `parent_iteration` retains the final solver count and must not be used to identify an alternate candidate. Top-level recovery parent identifies the selected candidate.

The startup peak reduction was exactly zero, below the required 0.5 mm; complete cost increased by 4.234530 seconds (19.50%). All other local checks passed. The critical case's 0.258608-second timing reduction carries no quality claim. The full local update sum increased from 33.957150 to 37.933071 seconds. local_decision.json closes the full-confirmation gate. The corrected implementation and focused tests are retained only as a withdrawn patch and archived test source. Four value-only evaluations after withdrawal confirm the saved objectives and feasibility against the restored production graph, with zero additional solves/integrations.

## Usage, limitations, and handoff

Actual NLP calls: **1 diagnostic + 5 local production calls**, consisting of two baselines, one invalid revised startup, and two completed revised cases. Four controller updates completed and one aborted. There were zero backend attempts, full confirmations, Route trials, platform tool calls, provider attempts, provider tokens/charges, workers, or credential loads. Eight focused test invocations and four restored-graph value checks ran. Coding/shell tools are not provider-session tool usage.

Known implicit-step integrations total 133: diagnostic warm/recovery 10/30; baseline warm/recovery 20/10; completed revised warm/recovery 20/30; invalid revised warm 10; and three setup priming steps. The invalid attempt reached two recovery-method invocations but failed before its measurement checkpoint. Its actual recovery integration count is unavailable, bounded between 0 and 20; the honest total is **133–153**, not an invented exact count. Seven completed full recovery sequences are recorded, plus up to two in that invalid attempt. The invalid attempt's wall duration and stopping count are also unavailable. usage_audit.json separates measured timings and these accounting limits.

No fresh deterministic acceptance exists. The latest full task remains the Stage 3.27 failure; this round neither repairs it nor repeats it. Live tracking, structured-delivery and prose-delivery outcomes are individually not performed. No successful candidate or provider explanation was manufactured.

The evidence supports finite-stop plan sensitivity and objective/peak tradeoffs. It does not show a dependable benefit from the tested bounded rule or isolate why predicted and executed trajectories differ. State projection, integration approximation, and dynamics mismatch remain separate hypotheses; none was isolated as dominant. No physical-model change or task expansion is recommended from this round. Reproduction commands, bindings and repository-byte hashes are indexed alongside this report. Local commits only; no push.
