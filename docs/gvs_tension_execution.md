# GVS tendon-tension execution

`controller.gvs_lqr` always computes a desired tendon-tension vector in the
frozen tendon order. `tension_execution_mode` selects only how a backend
realizes that vector:

- `ideal_tension` (MuJoCo): clips each command to `0 <= T_i <= force_limit_i`
  and applies it through a bounded direct tendon-force actuator. It bypasses
  transmission inversion, actuator velocity/travel limits, and the tendon
  length servo. Tendon length, change, and rate remain measured outputs; they
  are simulation evidence, not a universal tension-to-length law. No actuator
  command or target tendon length is emitted.
- `actuator_realistic`: preserves the existing tension-to-target-length,
  minimum-norm transmission, actuator rate/travel limiting, and MuJoCo/MATLAB
  tendon length-servo path.

MuJoCo declares both modes. MATLAB declares only `actuator_realistic` and
rejects an ideal-tension request explicitly.

Run the controlled comparison with the same robot, GVS equilibrium, LQR gain,
initial state, and horizon:

```powershell
conda activate softagent
python examples/gvs_lqr_ab.py runs/my_gvs_lqr_ab --base-input runs/my_previous/inputs/route.json
```

Prepare the bounded autonomous route from that comparison:

```powershell
python examples/gvs_lqr_route.py prepare runs/my_gvs_route `
  --base-input runs/my_previous/inputs/route.json `
  --comparison runs/my_gvs_lqr_ab/comparison.json
$env:DEEPSEEK_API_KEY = '<configured outside the repository>'
python examples/gvs_lqr_route.py start runs/my_gvs_route
```

The route exposes both GVS-LQR modes without prescribing their order, keeps the
frozen evaluator authoritative, and stops normally through `route.advance`
with either a successful or honest unmet-tolerance delivery.
