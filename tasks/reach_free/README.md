# Frozen reach task

Human owns task.yaml (target [0.25,0,0.15] m; final position tolerance 0.01 m)
and environment.yaml (sole environment semantic source). These reproduce
main@245a785 exactly. mujoco.xml is a checked deterministic representation of
environment.yaml without simulator timestep. Loading rejects any mismatch and
never rewrites either file. tools/spec_tools.environment_xml generates the
representation in memory; future Human-reviewed changes must update and refreeze
the representation explicitly. The compiler composes timestep from simulator.yaml.

benchmarks/tendon_v1.yaml declares membership and metrics.reach.evaluate_reach.
The canonical evaluator reads the frozen TaskSpec, never the XML target marker.
MATLAB checks shared environment frame/identity and uses only the kinematic inputs
its present equations need. Gravity/objects do not enter M0/M1 predictions.

configs/task_reach.yaml remains a deprecated checked compatibility copy;
load_task on that path rejects drift. mujoco/environments/reach_free.xml is a
legacy reference, no longer an executable source; tests compare its geometry and
gravity to EnvironmentSpec and timestep to SimulatorSpec.

## TaskContract entry

`contract.yaml` is the FROZEN reference index for this existing benchmark task.
Target/tolerance remain in task.yaml, geometry in environment.yaml, and the allowed
design envelope in the referenced family grammar. The baseline DesignSpec is an
independent candidate; it is not frozen task truth. See ../../docs/task_contract.md.
