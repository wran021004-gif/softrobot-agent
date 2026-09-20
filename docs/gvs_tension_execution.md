# GVS tendon-tension execution

`controller.gvs_lqr` computes a desired tendon-tension vector in the frozen
tendon order. In normal Route execution, backend realization is not a model
choice. `backend.family_mujoco` always clips it to each frozen force limit and
applies it through bounded direct tendon-force actuators.

This bypasses transmission inversion, actuator velocity/travel limits, and the
tendon length servo. Tendon length, change, and rate remain measured outputs;
they are simulation evidence, not a universal tension-to-length law. No
actuator command or target tendon length is emitted.

The historical length-servo comparison remains available only through the
explicit development script below. It is rejected in Route combinations.
MATLAB continues to expose only combinations it implements and does not claim
direct GVS-LQR execution.

Run the controlled comparison with the same robot, GVS equilibrium, LQR gain,
initial state, and horizon:

```powershell
conda activate softagent
python examples/gvs_lqr_ab.py runs/my_gvs_lqr_ab --base-input runs/my_previous/inputs/route.json
```

Prepare the bounded autonomous route:

```powershell
python examples/gvs_lqr_route.py prepare runs/my_gvs_route `
  --base-input runs/my_previous/inputs/route.json
$env:DEEPSEEK_API_KEY = '<configured outside the repository>'
python examples/gvs_lqr_route.py start runs/my_gvs_route
```

The route exposes one MuJoCo GVS-LQR combination. Each physical candidate gets
its own inverse/static equilibrium, DynamicSystem, linearization and LQR gain.
The frozen evaluator remains authoritative.
