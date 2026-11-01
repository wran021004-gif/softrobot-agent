# M1 final interface audit and open-topology preparation

Baseline: local and remote `codex/scientific-intent-interface-repair` both resolved to
`e129ff958645ae6ea34440f5abe3cd6c24eea91f`. The existing zero-run Study is bound to
production commit `7229c1a922545e0577f9685397b76a031650e55f`.

## Confirmed changes

- Validate raw V4 input against the selected Provider Schema before deep request
  compilation. Previously a Schema-invalid inspect request could reach binding
  and its validated event before final rejection. Keep the original full
  AnalysisRequest, Pydantic, binding audit, authorization and execution admission.
- Keep the original `prepare_context` cost calculation and rejection. Its
  ValueError now carries the actual minimum and parameter stencil cost basis;
  active mechanism request feedback reports that information, Main's unchanged
  cap, remaining shared budget and a Main-owned correction choice. Discovery
  already exposes operation minima, remaining budget and cost rules. No fixed
  ten-evaluation rule or automatic budget increase was added.
- Extend the original M1 condition fixture to check candidate, source, settled
  scientific choice and frozen protocol isolation, including cross-condition
  source rejection. No additional state manager.

## Topology and objectives

The new configuration removes the Study-only two-segment/six-tendon restriction.
It uses the existing Base-only v2 FamilySpace: 1--9 segments and 1--7 tendons,
with original continuous domains and Base-only routing legality. The 8--12 tendon
declarative range remains unsupported for execution. These boundaries originate
in the registered FamilySpace, not the new Study; no physics boundary was widened.
Candidate-specific mathematical and execution admission remains mandatory.

Existing Schema projection already reads these executable ranges. The added
offline fixture checks all 63 topology pairs in the generation Schema and real
generation, method discovery, control initialization, T1 compilation and Replay
source binding for (1,1), (3,4), and (9,7). These checks establish interface
admission only, not numerical stability or task feasibility across the domain.

The frozen instructions prioritize complete three-condition task acceptance,
then fewer tendons among already accepted structures. No scalar complexity
penalty, forced enumeration, prescribed method order or global optimality claim.
Original immediate joint SELECT/termination and all thresholds remain unchanged.

## Resource envelope

Provider 80 (12 protected), public operations 240 (16 protected), mathematical
evaluations 16, independent Replay episodes 18; Native per request remains
800 callbacks / 100 iterations / 4 knots. Each frozen task is 0.6 s at 0.001 s:
600 physics steps per full trajectory. Conservative bound remains
`16 * (800 + 1) * 600 + 18 * 600 = 7,700,400` physics steps. Changing topology or
mesh changes per-step computational cost, not the frozen number of time steps;
this is not a wall-time bound. No budget or scientific threshold was increased.

## Gateway evidence

Read-only original Provider Store evidence identifies two unique 502 requests:
`r3-request-366da3a584c84b588ed965fc7b6471d2` at 08:42:12 UTC and
`r3-request-e86adab47a68498296bfad79413652ac` at 08:52:44 UTC on 2026-11-01.
Both returned `empty_response` with one completed output item, after 5.703 s
and 6.125 s. Repeated events referencing the same response are not extra sends.
The Gateway raises this code after its completion/conversion path returns no
text or function calls. A local HTTP response was received; this was not a
client-side missing-response timeout. Available stdout is empty and stderr has
an uncorrelated generic internal error. No upstream response ID or retained raw
upstream item supports distinguishing upstream content from extraction behavior.
Root cause remains unlocated. Proxy, model and retries were not changed.

## Preserved evidence and launch gate

The two historical M1 Stores are STOP, with no pending/unsealed reservation.
Their SQLite hashes match the prior manifest exactly; all manifest-listed files
outside `framework_sessions` still match. However, 2 and 164 old SDK session/context
files listed in that manifest are absent at the start of this audit. Full auxiliary
SDK archive completeness therefore cannot be certified. No old Store was opened
for writing, reset, refunded or reconstructed. Historical actual expenditure
remains 43 Provider requests, one mathematical evaluation and 19,200 Native steps.

The old zero-run Study has two binding events, zero Provider/math/Replay use,
zero candidates and zero formal scientific authorization events. Its configuration
and bindings remain in its original Store. The expanded scientific scope gets a
new Study ID; it must be prepared/bound to committed code and reviewed for exact
identity-bound authorization before the first eight-request formal checkpoint.
Engineering probe authorization is not formal M1 scientific authorization.

Only derived identities, counts, code and fixture tests belong in public evidence.
Raw Stores, Provider wires, credentials and private trajectories remain local.
