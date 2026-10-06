# First offline research study, version 1.0.0

The [machine-readable freeze](../configs/research/reach_hold_v1.json) prepares
Research Mainline 1, offline state recovery from Mainline 2, and the minimum
shared interfaces needed from Mainline 3. The finalized six-mainline roadmap is
unchanged. The adaptive campaign and formal three-group comparison have not run.

The question is whether design and control adaptation improve joint reach and
hold robustness under small, predefined initial-state variation around an
already successful configuration. The common source is the retained M4 incumbent
`batch-ebbeadbdaca10732-0`, execution `91c3ba1b01d6499fb26df8f95409401b`, configuration
`285236abf99bf36894fa08410ac82fefa177a80179c4ceba15d95f8d1bc8d978`. Its complete saved
configuration is embedded and hash-verified. It has near/far lengths 0.16/0.11 m,
original-source section scale 0.95, compliant Young moduli 7.2/5.4 MPa and speed
weights 0.05/0.05. The sealed nominal result has terminal error
0.0026978288583256148 m, holding maximum error 0.0027300544346297905 m and speed
0.012750255515948416 m/s. A later joint pass exchanges higher position error for
lower speed; it is retained as context and does not replace this starting point.
Original holding-speed failures and measured matching repetition are linked in
the freeze. Their causes and general repeatability remain unresolved.

The cases are frozen in this order:

| Case | Segment principal total bend (rad) | Total bend rate (rad/s) |
| --- | ---: | ---: |
| nominal | 0 | 0 |
| near_z_plus | near z +0.01 | near z +0.02 |
| near_z_minus | near z −0.01 | near z −0.02 |
| far_y_plus | far y +0.01 | far y +0.02 |
| far_y_minus | far y −0.01 | far y −0.02 |

Each case has two fresh repetitions, seed 17 then 18, before the next case.
Seed labels do not create randomized initial conditions. For each participating
segment, named cell angles and rates equal the total value divided by its cell
count; all other named coordinates have explicitly zero values. This preserves
the integrated principal bend and its rate versus normalized arc. The fixed
section orientations, station layout, topology, routing and 12+12 mesh make that
mapping comparable. With length changes, curvature per metre, tip displacement
and velocity, mass and energy necessarily change. Equal initial tip offset or
energy is not asserted. A 0.01 rad total bend is about 0.57 degree; the per-cell
0.000833 rad and 0.001667 rad/s remain far below the installed initialization
limits. Nonzero velocity is applied once, without relaxation or repeated resets
until passing. These values and case order were written before new outcomes.

World target `[0.29,0.035,0.19]` m, gravity, scene and mount stay source-bound.
Control/sample spacing is 0.01 s, physical timestep 0.0005 s and duration 0.35 s.
Joint acceptance uses the unchanged terminal reach evaluator (0.01 m tolerance),
final inclusive `[0.30,0.35]` s holding window with six samples (maximum error
0.01 m, speed 0.02 m/s), applied nonnegative tendon tensions with six 8 N bounds,
complete valid execution and zero recorded solver errors. The shared
`research.task_acceptance@1.0.0` implementation and component outcomes are the
authority for evaluation, ranking, stopping and delivery. Its zero-error
requirement is part of the frozen adapter implementation. Position, physical
speed and force evidence are retained separately; missing signals or incomplete
execution cannot become a physical infeasibility claim.

The new protocol excludes the 10 ms wall-clock deployment requirement. Its
simulated control period and holding standards remain fixed. Stable controller
`gvs_nmpc@7.0.0`, MuJoCo backend `family_mujoco@1.1.0`, serial-bending model and
structural-linear basis remain bound to the source. Solver maximum CPU 30 s,
120 iterations, and feasible-return 5 s minimum/15 s budget are unchanged.
Historical deadline failures keep their original protocol labels. Experimental
v8 is outside this study.

The [catalog](research_parameter_catalog.md) grants eight variables: two lengths,
two per-segment scales, two per-segment Young-modulus scenarios and two controller
speed objective weights. Task initial conditions, thresholds and solver/model
settings are outside the candidate vector. Any variable subset is available to
all future groups within the same granted domains, with no new per-batch user
permission. Unsupported topology, routing, shape, material and omitted-physics
work has explicit engineering reasons in the generated backlog.

The primary metric is joint accepted fresh executions divided by ten scheduled
case/repetition executions for each finalist. All scheduled failures, unavailable
and incomplete slots remain in the denominator. Component maxima and total
computation costs remain visible. No weighted score hides tradeoffs. Equal
acceptance counts use componentwise dominance; incomparable ties retain earlier
proposal order and explicitly retain tradeoffs. A cached result or repeated
receipt is not a repetition. Small deterministic-case acceptance is descriptive,
not a population probability.

The fixed baseline uses existing `ParameterSpace` and bounded coordinate kernels.
It starts the exact incumbent and visits up to four structures, using ±0.25 of
granted numeric widths in catalog order; discrete material options are enumerated
in declared order without interpolation. Each structure receives two nominal
control allocations starting at the incumbent weights. Numerical controller
adaptation runs within each execution. The extra control pair is an existing
bounded coordinate proposal. Joint acceptance and then componentwise dominance
can update the search centre; unknown results cannot displace valid results.
Actual control pairs, embedded updates and cost are recorded per structure.
Insufficient adaptation does not prove structural infeasibility. Up to two
nondominated nominal candidates receive the full frozen ten-execution schedule;
nominal adaptation does not count as independent validation. Unvisited dimensions
are untested, rather than implicitly optimized. Additional mathematical analysis
is disabled here; a future use must declare a decision question and outcomes that
change or retain selection.

Future equal group ceilings are 28 backend attempts, 100 workflow calls, eight
model requests, zero workers and 30000 charged seconds each. This covers eight
adaptation attempts and twenty finalist validation attempts. The fixed method
uses zero model calls. One-shot planning must freeze its entire plan, including
executable branches, before new outcomes; later LLM rewriting or branch addition
is forbidden. Optimizer-internal feedback remains allowed. Feedback planning uses
the same pool and cumulative ceilings. Budget is an upper bound. Stop legality
and evidence support are assessed separately from unproven optimal stopping.

Integration validation has a separate predeclared cap: 12 workflow calls, two
backend attempts, zero provider/worker calls and 2100 seconds. The historical
source execution cost 300.265 seconds; each simulation reserves 900 seconds,
evaluation 30 seconds and profiling 60 seconds. Normally only one attempt is
used; the second is reserved for a material versioned repair with preserved failed
evidence. The single scheduled smoke changes near section scale to 0.96 and uses
`near_z_plus`, seed 17. It runs candidate generation, resolved preparation,
closed-loop adaptation, simulation, evaluation, comparison and delivery. The
different initial conditions prevent treating the historical nominal result as a
matched robustness baseline. Smoke results do not establish study superiority or
robustness on the full case set.

Invocation in PowerShell:

```powershell
& 'C:/Users/gugugaga/miniconda3/envs/softagent/python.exe' examples/fixed_research_baseline.py --mode plan
& 'C:/Users/gugugaga/miniconda3/envs/softagent/python.exe' examples/fixed_research_baseline.py --mode smoke --output runs/research_first_study_smoke_20261006 --export evidence/research_preparation_20261006/smoke
```

The delivered smoke directory already contains a completed scheduled attempt;
the runner refuses to execute it again or reset its budget. Future authorized
full fixed-baseline execution is `--mode study --output runs/<new-run>`. That
invocation is prepared and has not been executed in this assignment. Saved Store
receipts and immutable exports are the evidence, and process-local live backend
resume is unsupported. The [shared recovery work](research_state_recovery.md)
preserves bound claims, counterexamples, budgets and STOP across a new process.
Live context-quality/input-cost validation remains pending.

See [validation and actual integration result](../evidence/research_preparation_20261006/validation.json)
and the [portable artifact manifest](../evidence/research_preparation_20261006/smoke/artifact_manifest.json).
All old milestone reports and seals remain unchanged: M4 qualified closed, old M5
open with its sealed negative outcome and six protected slots. The next bounded
step is independent specification review and a newly authorized small prospective
comparison using these frozen interfaces, before any formal Mainlines 4/5 study.
