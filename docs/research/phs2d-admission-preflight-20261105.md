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
