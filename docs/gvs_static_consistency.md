# Free-reach GVS/MuJoCo static consistency (E0–E2)

The current development `reach_free` assembly keeps gravity and floor but has
no timed payload force. Its existing target `[0.25, 0, 0.15]` m, evaluator,
and 0.01 m position tolerance are unchanged. Route now records a session-wide
valid comparable incumbent and delivers it by default; an explicit
`source_node` plus `candidate_id` can select another valid result. Direct-force
diagnosis uses tendon and projected-state evidence instead of requiring a
nonexistent actuator-displacement command.

`examples/gvs_static_consistency.py` uses the baseline design only. E1 obtains
`q0,u0` through the existing inverse-tip IPOPT and GVS equilibrium refinement,
uses the existing cell-centre GVS discretization Jacobian to initialize MuJoCo
with zero velocity, then applies constant bounded direct tendon tension `u0`
for 0.35 s with no LQR or external disturbance. The inverse mapping and
projector agree to `1.1e-14` rad/m. The static pass criterion budgets the
unchanged 0.01 m reach tolerance for both initial geometry gap and maximum tip
drift; a joint-angle drift threshold of `0.01 / 0.28 = 0.0357` rad uses the
total flexible-arm length as a lever. This is an engineering sufficiency test
for subsequent local control, not an exact-continuum claim.

Saved result: `runs/gvs_static_consistency_20260921/`. GVS predicts the target
with static residual `2.43e-17`. MuJoCo starts at
`[0.223887, -0.026956, 0.165956]` m, already 0.04078 m from the GVS tip.
Under exact constant tension tracking it ends at
`[0.192738, 0.066649, -0.003962]` m, a 0.19648 m displacement from its
initial tip. All states are finite. **E1_STATIC_CONSISTENCY = FAIL.** The
saved `equilibrium.json`, `input.json`, backend exports, and `e1_report.json`
contain the complete state and force evidence. The initial geometry gap means
the reduced and discrete coordinates do not represent exactly the same spatial
shape at this large-curvature operating point, despite an exact coordinate
round trip.

E2 evaluates only the saved E1 initial state, with no additional integration.
The exact cell-angle Jacobian gives `delta_q_backend = J_map delta_q_gvs` and
`tau_gvs = J_map.T tau_backend`. At zero velocity, GVS net force is
`tendon + gravity - elastic`; MuJoCo counterparts are `qfrc_actuator`,
`-qfrc_bias`, and `-qfrc_passive`, respectively. There is no contact or
constraint force at this state. In common GVS coordinates, the difference
norms are tendon `0.007247`, gravity `0.001410`, elastic `0.000798`; GVS net
residual is about `1e-9`, whereas projected MuJoCo net is nonzero.
**Tendon generalized force is the dominant measured force discrepancy.**
The 40.8 mm initial geometry gap limits a stronger causal claim: the tendon
discrepancy may arise from the coarse cell representation of the tendon path,
not merely a force-sign or magnitude bug. The full per-coordinate vectors and
mapping are in `e2_force_report.json`.

The next correction should be confined to geometric/tendon-path equivalence
at `q0`, particularly the common-coordinate tendon-length Jacobian. No
continuation controller, trajectory optimization, or NMPC was added because
E1 failed. To reproduce from a clean source, run E1 once, then E2 only if E1
fails; E2 does not step the simulator:

```powershell
conda run -n softagent python examples/gvs_static_consistency.py e1 runs/new_static_check
conda run -n softagent python examples/gvs_static_consistency.py e2 runs/new_static_check
```
