# S5.5 model fidelity and S5-T mathematical sensitivity

Starting branch `feat/sorosim-matlab-nmpc`, commit
`7000e900568a5b5778265968dd8f8861d32cb130`.

## P0: prospective scientific identity and saved PPO failures

The new preflight compares the resolved robot, compiled physical scene identity,
task and seed, controller/model, runtime identity, and either the complete ordered
fixed-tension grid or RL mode, binding, residual reference and checkpoint policy
hash. Store artifact IDs, study names and paths are excluded from the scientific
signature. For NMPC the numerical environment is included. Missing effective
fields produce an unresolved comparison and a possible repeat is withheld from
execution. The preflight runs before the public plan or backend reservation;
an explicit confirmation remains admitted under the existing confirmation grant.
The saved preflight returns the proposed identity, exact equal categories and
differing paths, prior identities and outcomes, and repeat admission status.

The [read-only equivalence audit](../../evidence/sorosim_s55/p0_equivalence.json)
finds the S5-Agent NMPC launch equivalent to S5-B and its fixed-tension replay
equivalent to S5-A. It also recognizes the original direct and residual PPO
evaluations independently. All four comparisons retain the prior `valid_failure`
or task-failure outcome. Changing a physical tension, robot, seed, RL mode or
checkpoint hash changes the appropriate signature. This is a configuration
comparison, not a claim that physical executions are deterministic.

The [PPO classification](../../evidence/sorosim_s55/p0_ppo_diagnosis.json) reads
all 260 original direct failure JSON, JSONL and NPZ captures. Saved interval
start states were reconstructed with `mj_setState` and `mj_forward`, with zero
physics steps; reconstructed tip-speed norms match the snapshots exactly. No
checkpoint or training record was modified.

| Recorded training fact | Direct | Residual |
|---|---:|---:|
| Attempted actions | 32,768 | 32,768 |
| Complete episodes | 782 | 936 |
| Numerical-failure episodes | 260 | 0 |
| Engine time reset captures | 260 | 0 |
| `mjWARN_BADQVEL` | 207 | 0 |
| `mjWARN_BADQACC` | 52 | 0 |
| `mjWARN_BADQPOS` | 1 | 0 |
| Explicit nonfinite-state/observation captures | 0 | 0 |

The 260 direct failures occurred at episode actions 18–27; 249 occurred at
actions 18–22. They occurred across all four consecutive 8,192-action training
quarters: 104, 88, 29 and 39. The failing physics substeps span 1–20. No
capture records action clipping or tension saturation. At failure interval
starts the per-channel tension extrema were approximately 3.23–4.90 N and the
median tip speed was 1.155 m/s. One saved state has an extreme finite speed of
about 3.42e10 m/s; it is reported as an instability outlier, not treated as a
normal task sample. The saved last-valid-action reward median is about -429;
reward magnitude is a training signal, not an independent acceptance metric.

`TensionEnv.fail()` increments `failed_episodes` for an invalid MuJoCo
transition, restores the interval's last valid boundary, and returns a terminal
surrogate observation with the frozen failure penalty of -10,000 and
`valid_physical_transition=false`. A normal complete episode that misses reach
or holding thresholds increments `complete_episodes`, not `failed_episodes`.
The independent `checks.run_episode()` excludes the terminal surrogate from
physical trajectory evidence. Direct and residual remain separate available
controller routes. The saved correlation with the middle episode phase does
not establish whether state, action, physical stiffness, or their interaction
caused the warnings. A next RL investigation should first inspect pre-failure
joint states and force/acceleration growth against stable direct episodes;
further training is not supported by this audit alone.

P0 incurred zero new model requests, mathematical integrations, physical
rollouts, and PPO actions. The only numerical work was read-only identity
construction and saved-state kinematic reconstruction.

## P1: fixed-sequence integration refinement

The candidate-bound `refine` action now reserves one mathematical replay slot
per resolution in the original research ledger. Its typed request accepts the
archived verified Design B trajectory and a declared substep count. The worker
checks model, design, task, coordinate, channel, initial-state, force-bound and
35-command/36-time identities before constructing SoRoSim. `sr_diagnose` uses
the existing implicit-Euler residual and root Jacobian for each substep, records
every root outcome, and samples outputs only on the original task clock. A root
failure preserves the last completed sample, failing state and residual, and
cannot be reported as task success. A complete result includes every sampled
state and world tip output, original-constraint violations, root count, force
residual, wall time, and exact trajectory/control hashes. The sparse study grant
allocates at most four refinements and zero physical, PPO, full-NLP or provider
work.

**Execution status:** no P1 mathematical integration has been launched. The
configured `SOROSIM_ROOT` environment variable is absent and the pinned
`GVSRobotics/SoRoSim@24d573a3e864ffda87c42ee462a6ed620133cc7b`
checkout has not been located. The MATLAB Engine Python source is present in
the installed R2024a tree and can be imported through its existing `build/lib`
path, but a standalone `matlab -batch` syntax check failed at startup with
`failed to load settings errors_warnings plugin`. This is an environment
obstruction, not a numerical result. The historical one-substep S4.5 discrete
feasible witness remains intact; integration robustness is unresolved.
