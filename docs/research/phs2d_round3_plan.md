# PHS-2D round 3: inverse passive design

Base: f33648d0bf5fcebbe3d5f5a5878c3198eb32a69c. Remote verified unchanged before creation. Round-two STOP and Store are read-only. New branch research/phs2d-inverse-passive-design, new private Store runs/phs2d-round3/store, study phs2d-inverse-passive-design-20261028-v1. The main workspace had unrelated untracked files and was left intact.

Frozen acceptance is inherited verbatim from phs2d_protocol_v3: 0.28 m flexible material, gravity [0,0,-9.81], 10 g eccentric payload, +/-0.1 N, search 0.3/0.5/0.7, holdout 0.4/0.6, 5 mm tip / 10 mm force point / 0.30 ratio / 2 mm out of plane, 4 s windows and original residual/stability/contact limits. Primary timestep 0.125 ms, independently halve for a final design. No active actuator, controller or world anchor. Every assembly freezes one payout vector before any force condition.

Hard budget: 20,000,000 integration attempts; 1,200 top-level mathematical requests; 300 structures/assemblies; at most 60 dynamic assemblies. P0 <=500,000, development <=15,500,000, protects 4,000,000 final steps. Provider / Research Agent / NMPC / PPO zero. Request admission/reservations and receipts reuse the existing Store; unknown requests must be recovered before another launch.

## Domain audit and minimal changes

Schema FamilySpaceV2 permits declared segment bounds, with no literal 9-segment solver maximum. The example grants 1-9 segments and 1-12 tendons, execution 1-7 in its inherited base; round-two Study further narrows this to 2 and 1-6, while phs2d.candidate additionally narrowed counts to 1/2/4/6. MuJoCo construction, Jacobian sparse-row decoding and KKT dimensions are generic. This round freezes a separate space; numeric bounds alone are not validation. Each exercised topology must compile and pass derivative, equilibrium and dynamic checks. No need to add tendons without a missing-mode hypothesis.

New space permits 15-280 mm segments, 3.5-200 mm radial routing and guide stations 0.001-0.999. Material modulus, density, damping, sectional dimension bounds and rigid masses/inertias remain inherited. A new optional `terminal_payload_anchor` flag (absent from serialized old spaces) permits an actual terminal payload anchor inside its existing solid envelope. Old spaces still reject it. Base sites are on the same fixed base. This enables P1 without fictitious anchors at unsupported free-space tip points. Outboard base mounting is an external base support arrangement, not evidence for a guided tendon robot.

## Mechanism and staged decision

For a cable between base radius b and distal radius r at an axial station L, linear length variation has a bending gradient combining distal translation and rotation. Its effective lever depends on the actual straight segment direction; use the actual MuJoCo Jacobian to match it to the measured tip (including payload offset). A paired cable should switch positive multipliers between force signs. First test one soft continuous segment with real payload anchors to avoid crossing intersegment guide solids. Then test guided gradients and three to five segment compensation, adapting stiffness only after row-space improvement is measured.

Kinematic zero-tip directions (A), one-sided feasible directions (B), and actual force-excited response (C) are distinct outputs. Use nonlinear six-case ideal-hard-cable screening and then independent soft-constraint dynamics. Validity precedes minimax ranking. The optimization ratio surrogate is tip_xy-0.30*point_dx, while final evaluation uses the unchanged ratio evaluator. Holdouts remain unused until six search passes. First ten-case witness triggers final half-step, perturbation and independent reproduction, then STOP.

Cable paths are checked against compiled convex solid extrusions with cable radius and actual owned guide-hole exceptions at sampled shapes. Friction, cable/cable contact, continuous swept collision and fabrication of massless offset guides remain limitations; never silently claim hardware feasibility.
