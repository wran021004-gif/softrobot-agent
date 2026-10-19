# S5.10 reference validation and low-dimensional control correction

This distinct user-authorized study keeps the original Design B, zero physical
initial state, target [0.29,0.035,0.19] m, 35 held commands over .35 s, .0005 s
MuJoCo step, inclusive .30–.35 s holding samples, .010 m position and .020 m/s
speed limits, and four independently bounded [0,8] N tendons. A passing registered
evaluation stops further science immediately. No provider, RL or full NLP runs.

The finite ceiling is 192 full MuJoCo replays, 18 candidate-bound mathematical
integrations and 240 public operations (four protected). These are ceilings,
not required consumption. Historical S5.9 is read through the archive's existing
hash checks; its result and exact robot/task are preserved with explicit provenance.

The saved S5.9 sequence is independently integrated at four and 32 substeps.
The four-step replay checks saved sampled states; 32 steps is a refinement screen,
not a continuous-time error bound. Its standalone original-task MuJoCo execution
isolates reference performance from PPO correction.

Three knots at 0, .18 and .30 s and four tendon offsets give 12 coefficients.
Offsets interpolate linearly and hold after .30 s; each lies in [-2,2] N and final
physical tensions are explicitly clipped to [0,8] N. Twelve .02 N one-sided
four-step integrations build a local response, anchored to the 32-step reference.
A bounded +/- .1 N mathematical proposal is tested first. Subsequent trust-region
least squares uses actual MuJoCo residuals and .01 N simulator finite differences,
with at most 16 major function evaluations and the hard shared replay ceiling.
Every actual derivative probe is a charged original-task evaluation and participates
in incumbent ranking by (original pass, maximum normalized excess, sum of excesses).
The fitting residual aims at 80% of original limits; acceptance never changes.

For returned mathematical/simulator arrays on the same task samples, define
epsilon as the maximum of terminal position vector error/.010, maximum holding
position vector error/.010, and maximum holding velocity vector error/.020.
The reverse triangle inequality and the 1-Lipschitz max/positive-part operators
give |G_sim-G_math| <= epsilon (interpreting the arrays as real values).
For endpoints a,b, G_sim(a)-G_sim(b) >= G_math(a)-G_math(b)-epsilon_a-epsilon_b.
Positive right side proves improvement for those arrays. Evaluated endpoint
errors are a posteriori; they do not certify an unvisited candidate. Prospective
use needs independently valid discrepancy envelopes and integration/roundoff
bounds, which this implementation does not invent. Empirical maxima, finite-grid
agreement and local finite differences do not establish those regional bounds.

Implementation ownership:

- `tools/research/control_correction.py`: pure controls, task violations, fitting
  residual and scoped error inequalities. No numerical process or Store.
- `physical_replay.py`: additive explicit-schedule input under a new declared
  capability; existing binding, budget, worker and evaluator are reused. Missing
  model predictions produce unavailable comparison rather than fabricated outputs.
- `mechanics.py`: same explicit-schedule capability for the existing integration.
- `tests/research/sorosim_s510_correction.py`: thin finite experiment driver using
  the existing core/Store; writes rankings, guidance checks and exact-pair bounds.
- One sparse study JSON and focused fabricated-fixture tests complete the change.

After 44 completed physics evaluations, repeated full-history assembly in the
core response became the dominant cost (the owned worker itself took about 1.1 s).
At a verified boundary with no active numerical worker, the two owned driver
processes were stopped. Existing `core.recover` sealed the unfinished metadata
receipt without launching physics. The original source freeze, counters, calls
and artifacts are in `pre_serialization_repair/`; the boundary/recovery JSONs
retain exact counts. `core.resource_use` now owns the unchanged ledger projection,
shared by full packets, plan receipts, recovery and count-mode export. Numerical
kernels are unchanged. A committed explicit migration preserves cumulative costs;
the exact prior candidate/profile is retained through the existing imported-candidate
contract. A restarted optimizer initializes from the best observed incumbent and
reuses exact cached function evaluations; it does not claim continuation of an
in-memory optimizer checkpoint. The configured 16 major evaluations apply to
each invocation, while the shared 192-backend limit remains cumulative.

The first metadata interruption also exposed one settled evaluation absent from
the driver's local journal. A second boundary retained 52 completed evaluations;
the Store remains authoritative. One new outer plan had begun preflight between
the boundary check and process termination, with no worker reservation. Its
charged public operation is explicitly sealed failed as
`ENGINEERING_STOP_BEFORE_WORKER_RESERVATION`; the original recovery rejection is
retained. Recovery now reconciles every completed Store result into the journal
and ranks it, checks remaining shared backend capacity, and uses a distinct
request only for that known prelaunch failure. No completed numerical trajectory
is replayed. All boundaries, migrations and optimizer restarts are reported.

Launch through the existing research interpreter with MATLAB Engine on PYTHONPATH,
the pinned SOROSIM_ROOT and configured single-thread numerical environment:
`python -m tests.research.sorosim_s510_correction`.
This is an explicit scientific launch, never ordinary test discovery.
