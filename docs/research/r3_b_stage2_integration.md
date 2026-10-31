# Stage II: shared constrained mechanics

Base: `codex/r3-b-stage1-integration@fe8043a7c965138f07f38c6ed7d76f098e359e4e`.
Selective numerical source: `research/phs2d-inverse-passive-design@9d6d160e050c836b87d0563a497fc0ec1c3761a8`.
Branch: `codex/r3-b-stage2-constrained-mechanics`. Neither source branch nor main is modified.

## Implemented integration

One original Study, Main, Reporter, mathematical interface, Store and allowance remain authoritative. New passive problems use the original `mechanism_structure_v1` worker and `inspect / differentiate / optimize / compare` operations. No passive SDK tool, second optimizer, budget, cache, hash service or planner was added.

The original Design/compiler/MJCF path now supports explicitly granted `fixed_payout_lengths_m`. Passive designs have no actuators. XML contains genuine unilateral tendon upper limits and `nu=0`, rather than zero active tension. Active ideal-tension and realistic-actuator compilation retain their previous meanings and channel order.

New frozen FamilySpace V2 payout domains authorize assembly parameters. Existing spaces do not acquire payout permissions. Original structure, routing, material, mesh and topology checks remain in force. Passive Study bootstrapping and formal generate use the same family materialization as mathematical perturbations. Payout stays identical across load cases of one assembly.

`TaskDefinition.physical_problem` binds the explicit contact-free unilateral mode, mounting, gravity, named constant world loads, material stations, unloaded baseline and mathematical observations. Empty robot/task active channels are legal only for a validated passive assembly. The legacy Reach task/controller fields are composition scaffolding for this mathematics-only opt-in; they do not become a passive physical evaluator or controller. Dynamic backend compilation and Reach acceptance explicitly reject this mode.

`PassiveModel`, `StaticProblem`, equilibrium qualification, tangent QPs, row matching and KKT design sensitivity were selectively extracted. PHS campaigns, search scripts, Store/budget code, large-stack study loader, dynamic campaign runner, duplicate compliance implementation and task-specific modal prototypes were not copied. The source branch retains them for reproduction.

## Physical modes and mathematical strength

| Mode | Status |
|---|---|
| Active contact-free ideal-tension mechanisms and two-scale structural FD | Real worker validated; existing M1/M2/control/Replay interfaces retained |
| Active realistic-actuator compilation | Real XML/model compilation checked; no control optimization rerun |
| Passive unilateral hard equilibrium | Real native geometry, world forces, potential, NNLS multipliers, KKT and reduced-stiffness checks |
| Passive re-equilibrated sensitivity | Rebuilt legal models, checked local KKT system, paired re-equilibrium and two-scale target comparison; both unloaded and loaded states change |
| Zero-multiplier unilateral boundary | Feasible cone retained; signed local QPs exposed as `directional_material_response`; no bilateral-nullspace or ordinary-gradient substitution |
| Passive local parameter optimization | Original bounded Powell/direction path reused; numerical acceptance here validates FD/KKT proposals and generation, not a new optimization campaign |
| Finite-time passive MuJoCo response/independent acceptance | Not registered in this Stage; zero integration steps |
| Hybrid active/passive or contact sensitivity | Explicitly unsupported |

The constraint convention is `g=length-payout<=0`, with nonnegative tensions. Positive multiplier rows impose local equalities; active zero-multiplier rows remain inequalities; slack rows impose no local motion equality. Smooth tangent matrices require a qualified equilibrium, LICQ and strict complementarity. Cone QPs preserve one-sided response. Active geometric tendon rows never imply fixed length.

Qualification preserves the source distinction between SLSQP termination and independent physical KKT/stability checks. A line-search failure remains visible even if its final point independently passes the unchanged numerical qualification tests. No strict convergence or derivative certificate is inferred. Very small baseline derivatives use a mixed absolute/relative comparison with an explicitly labelled, observed-residual/stiffness noise estimate, not a rigorous bound.

Actual active-set changes, unqualified states, material-point binding switches, incompatible DOFs/topology and inconsistent scales withhold a gradient/direction. Failed probes, solver flags, residuals and costs remain saved. A fully constrained zero-dimensional tangent is represented as empty; its extrema are not invented.

## Real numerical example

The small passive case has one 0.16 m flexible segment, two cells/four bending DOFs, elliptical semi-axes 0.0095/0.0076 m, section angle 0.35 rad, density 1100 kg/m^3, Young modulus 7.2 MPa, one tendon and fixed payout 0.1598 m. Mounting and loads are frozen; gravity is explicitly zero in this example. A 0.01 N world-y load acts at material station 0.5. This is a real MuJoCo numerical model, not a hardware claim.

The loaded equilibrium has one positive constraint multiplier, approximately 0.1111205 N, stationarity infinity residual approximately 2.55e-10 N*m, and length violation approximately 5.55e-17 m. Material-point displacement relative to the separately solved unloaded state is approximately 7.51285e-5 m.

Two physical Young-modulus scales give approximately -1.04380e-11 and -1.04355e-11 m/Pa. The normalized target KKT/FD discrepancy is approximately 9.60e-5. The proposal reduces the registered modulus to 7.135 MPa. Its local mechanism improvement does not establish dynamic task improvement. The actual SDK/Mock loop subsequently chooses the existing generate Plan, binds its evidence and records adoption/generation separately.

The sensitivity request uses five compiled models, ten equilibrium solves and two KKT linear solves, with zero integration. Exact forward/Jacobian/Hessian/optimizer counts and timings are in `r3_b_stage2_costs.json` and the raw numerical projections. A native soft-limit reaction sampled at the hard equilibrium is recorded separately; it is not a settled soft dynamic equilibrium.

## Main interface and fixed feedback

Only V4 extends physical semantics. Historical B V2 continues to reject passive no-control fields. Diagnose still owns candidate/hypothesis and loads `research_analysis`. The selected Schema advertises the diagnosed physical mode, frozen load names and applicable quantities; Main never fills solver matrices or difference steps.

```json
{
  "version": "scientific_question_v4",
  "domain": "structure",
  "structure": {
    "operation": "differentiate",
    "physical_problem": "passive_unilateral_equilibrium",
    "effect_semantics": "re_equilibrated_passive_response",
    "operating_point": "re_equilibrated",
    "control_treatment": "no_active_control",
    "load_condition": "lateral",
    "target": {"quantity": "re_equilibrated_position_response", "reduction": "norm", "goal": "increase", "material_s": 0.5},
    "parameter_paths": ["segments.0.young_pa"],
    "requested_budget": 5
  }
}
```

`r3_b_stage2_main_example.json` contains the actual final Schema/L0 excerpt; `r3_b_stage2_wire_example.json` preserves the complete actual SDK/Mock wire. Main gets short original aliases, scalar constraint qualification/costs, compact sensitivities and a source-bound generate query. Large matrices, raw tension arrays and private mappings stay in L2. The target displacement has one L0 owner; the equivalent frozen-task observation points to it. Passive handoff/catalog details use existing evidence queries rather than copied parameter/method inventories.

Reporter failure is explicitly exercised while numerical workers remain real. Fixed results reach Main independently. Reporter itself is unchanged. No actual Provider request, autonomous Study or formal robot rollout is run.

## Validation and cleanup

See `r3_b_stage2_validation.json` for individual completed test IDs, batch outcomes and resolved development failures. The final combined regression passes nine tests; the cumulative directed set contains 41 unique passing tests, including B semantics, short Replay binding and independent certificate/SELECT/STOP closure. This is not a claim that the entire repository suite ran.

The real checks cover native active FD, realistic actuator compilation, passive limits/Jacobian/reaction, unloaded/loaded equilibrium, implicit/FD sensitivity, constrained motion versus compliance, boundary QPs, active-set switches, force capacity failure, incompatible topology, invalid payout/contact, V4 source/physics admission, Reporter absence, actual Main wire and evidence-bound generation. One small synthetic dimension/format fixture covers an empty tangent and global-observation binding; it supplies no physical conclusion.

`r3_b_stage2_files.json` lists every actual file action and reason. No old numerical kernel was deleted. Unneeded PHS wrappers/functions/imports were excluded instead of retained as compatibility scaffolding; the original source evidence remains on its branch. The public Stage I selection audit now uses a relative source description. Its original database and scientific records were not changed.

## Stage III requirements

Passive mathematical research is usable in a newly authorized frozen V4 Study. Full passive independent Replay/SELECT is not usable yet: `registered_acceptance=not_registered` is intentional.

The remaining interfaces are:

1. Register the passive task goal/evaluator and complete frozen load-case, material-point, tolerance, reset, sampling, transient/settling and safety protocol. The current mathematical norm/displacement/ratio/tension/length observations do not constitute this evaluator.
2. Add the no-controller physical execution adapter within the existing backend/Replay path. Reuse fixed-payout XML and material-point force mapping; refresh forces per `mj_step`, record full traces/costs, and validate native soft-constraint response against the declared protocol. Do not substitute an active zero-tension schedule.
3. Bind a passive assembly/load-protocol source to candidate, payout, task, initialization, all cases and exact trace. Feed the registered evaluator's complete result into the original acceptance certificate and SELECT eligibility checks. Retain original complete-read, identity and STOP requirements.
4. Run a minimal authorized cross-task autonomous validation only after those execution/evaluation interfaces are registered. A restricted mathematical decision pilot is possible earlier, but must not claim complete passive Study success.

Stage III is not started and main is not merged.
