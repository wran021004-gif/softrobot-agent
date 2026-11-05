# PHS-2D isolated admission: pre-execution freeze (2026-11-05)

Branch base: d7d9ecbb1df4739ad390e0a74bae369531175661, verified against origin. Original medium Store is read-only. No Provider, Reporter, autonomous Main, account/model changes, or original Study changes are authorized by these engineering specifications.

A new opt-in structure domain admits nine segments, four fixed passive payouts, eight bending cells per segment, physical plate holes and payload-envelope terminal anchors. Legacy serialization and grants remain unchanged. The new domain is distinct from the one-segment, one-tendon original Study. Historical reference requests, payouts, states and trajectories remain under ignored runs only and must never enter a discovery Study.

The executable tasks explicitly define a NEW continuous-state bridge, using the historical frozen protocol extracted from 9d6d160e, rather than claiming strict original-protocol identity. The source artifact retains the original protocol and lists differences. Every episode has a fresh zero named state, four seconds of unloaded dynamics and four seconds of independently loaded dynamics, interval-start smooth ramp, original 10 ms score grid, original displacement/ratio thresholds, full raw step traces and separately qualified 250 ms tails. All 21 monitored material points and Tip have plane-displacement checks. Original 1 nm fixture threshold is excluded.

Preflight step costs are determined by the existing Worker formula, `load_cases * duration / timestep`. Every load owns its unloaded prefix; no baseline reuse or hidden separate evaluator integration:

| Test | Cases | dt / s | Steps upper bound | Models | Episodes | Provider |
|---|---:|---:|---:|---:|---:|---:|
| A ordinary representative | 2 | 0.000125 | 128000 | 1 | 2 | 0 |
| B private reference representative | 2 | 0.000125 | 128000 | 1 | 2 | 0 |
| B private reference complete | 10 | 0.000125 | 640000 | 1 | 10 | 0 |
| Primary total | 14 | | 896000 | 3 | 14 | 0 |

Each Store uses the original reservations, finite backend episode counts, durable request IDs, termination receipts and recovery. Failures are charged and preserved. Model builds, attempted steps and completed steps are reported separately. Existing independent evaluation is read-only and adds zero integrations. No mathematical optimizer is authorized in these three execution specifications. Do not retry unknown execution. Full ten-case reference execution depends on inspecting the representative result; expensive numerical confirmation is conditional on a complete pass and a documented protocol-equivalence decision. Half-step ten cases would add 1280000 steps, initial-state perturbation ten cases 640000; these are not launched by the primary specifications.

Engineering pass, original-protocol reproduction, formal acceptance and autonomous discovery are separate claims. No formal autonomous Study is launch-ready solely because this bridge is executable.

## Accounted diagnostic addendum, before further physics

The first ordinary design actually executed 32000 steps and failed unloaded qualification; its generic route also intersected guide_1 outside the owned hole. It is retained as invalid, including the unused reserved second episode. A separately frozen ordinary-constant Study tests a new, constant guide line and higher physical material viscosity (within the same new domain), with an additional two episodes / 128000-step upper bound. This is a new design and identity, not re-execution or reclassification of the failed design. Its actual generated request remains private alongside the original. No success is assumed.

Two separately identified lightweight numerical control Stores reproduce the original best candidate at 1 ms (500 steps) and 0.5 ms (1000 steps), keeping the original 1 nm bound; they have no Provider and exactly one episode each. A further isolated registered mechanism request has a cap of two mathematical evaluations and zero physical episodes; it executes the existing hard-KKT/Jacobian kernel, not an alternate robot or solver. Primary plus these predeclared engineering bounds total 1025500 physical steps, 16 PHS episodes plus two lightweight episodes and at most two static mathematical evaluations. Historical costs remain separate and unchanged.

## Old-implementation paired reproduction freeze

To resolve the state-semantics comparison with fresh evidence, an independent historical checkout at `9d6d160e` is prepared under `phs2d-legacy-reproduction-20261105`. Its existing `tools.phs2d_round3_reproduce` runner is reused, with only a new Study identity/authorization and representative-first independent case ordering. It is explicitly OLD_IMPLEMENTATION_REPRODUCTION, not the unified Harness. The pre-existing recipe permits at most 500000 attempted integration steps, 20 mathematical requests, one candidate and 11 dynamic episodes; the complete planned fresh baseline plus ten loads is exactly 352000 steps at 0.125 ms. It uses the existing legacy Store reservations and the original independent evaluator. Fresh unloaded hard-KKT preparation, model builds and each dynamic request are retained. The reference-only checkout and its Study are not published to Main or merged. The maximum additional legacy allowance is 500000 (planned 352000), making the total authorized bounded engineering allowance 1525500 steps (planned primary ceiling 1377500), before any conditional convergence execution. No Provider call is sent.

## Full-dimensional registered mathematics

One additional isolated REFERENCE_REPRODUCTION_ONLY engineering Store is authorized for one registered `mechanism_structure_v1` evaluation of the actual 144-coordinate reference assembly, loaded at s=0.5 with +0.1 N. It uses the existing Worker, hard-unilateral equilibrium kernel and projected Tip row diagnostic. Its cap is one mathematical evaluation, zero physical episodes and zero integrations. Numerical qualification is measured, never assumed. This supplements the four-coordinate light diagnostic without exporting the reference parameters to Main.

## Conditional smaller numerical check

Only after the first complete unified ten-case run is independently accepted, the separately frozen reference-halfstep Store may execute s=0.5 ±0.1 N again at 0.0625 ms. Its exact cap is two episodes / 256000 attempted steps / one model / zero Provider. It has a distinct task/protocol/Study identity. This is a limited fresh representative timestep check, not the requested full ten-case and initial-perturbation/per-step-geometry robustness certificate. The primary and legacy finite allowance plus this conditional check is at most 1781500 attempted steps; planned total is at most 1633500 before accounting the original ordinary early stop. No unknown attempt is retried. Remaining full convergence and perturbation work is itemized separately.
