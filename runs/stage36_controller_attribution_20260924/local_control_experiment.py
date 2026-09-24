"""Six deterministic local MuJoCo runs using saved Case B physics and controllers."""
import gzip
import json
from pathlib import Path
import sys
import time

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from extensions.tendon_family.backends import MujocoBackend  # noqa: E402
from extensions.tendon_family.contracts import Control, GVSLQRControl, MujocoParameters, ResolvedGVSBasis  # noqa: E402
from extensions.tendon_family.control import Controller  # noqa: E402
from extensions.tendon_family.gvs_lqr import GVSLQRController  # noqa: E402
from extensions.tendon_family.gvs_projection import discretize, project  # noqa: E402
from tools.state_io import atomic_json  # noqa: E402

HERE = Path(__file__).resolve().parent
CASE = ROOT / 'runs/stage35_case_b_retry_softagent_20260924/sessions'
GVS = CASE / 'stage35-case-b-retry-softagent-44efe3ecec6b6acb/executions/5e0f73882b1846edbefb893a84c34d10/backend'
TIP = CASE / 'stage35-case-b-retry-softagent-34039c197777faab/executions/44caf52d4455474db18a877a52cfe149/backend'


def read(folder, name):
    return json.loads((folder / (name+'.json')).read_text(encoding='utf-8'))


def norm(value):
    return float(np.linalg.norm(value))


def run_case(level, fraction, mode, q0, physics, basis, tip_target):
    source = GVS if mode == 'gvs_lqr' else TIP
    scene = read(source, 'experiment_scene')
    control = read(source, 'control_spec')
    q_initial = q0 * (1. - fraction)
    qpos, qvel = discretize(physics, basis, q_initial, np.zeros_like(q0))
    scene['qpos_rad'] = qpos.tolist()
    scene['qvel_rad_s'] = qvel.tolist()
    scene['initial'] = dict(qpos_rad=dict(zip(physics['dofs'], qpos.tolist())),
                            qvel_rad_s={}, unspecified='zero')
    # The GVS gain and task target are precisely the saved Case B control plan.
    backend = MujocoBackend()
    backend.physics = physics
    backend.scene = scene
    backend.config = MujocoParameters.model_validate(read(source, 'solver_configuration'))
    backend.timings = {}
    controller = (GVSLQRController(GVSLQRControl.model_validate(control['effective_parameters']), scene['control_period_s'])
                  if mode == 'gvs_lqr' else
                  Controller(Control.model_validate(control['effective_parameters']), scene['control_period_s']))
    controller.configure(physics, control)
    backend.controller = controller
    folder = HERE / 'local_runs' / level / mode
    folder.mkdir(parents=True, exist_ok=True)
    backend.folder = folder
    start = time.perf_counter()
    rows, observations, complete, reason, steps = backend.solve(120.)
    elapsed = time.perf_counter()-start
    with gzip.open(folder/'trajectory.json.gz','wt',encoding='utf-8') as stream:
        json.dump(rows,stream,allow_nan=False)
    with gzip.open(folder/'controller_observations.json.gz','wt',encoding='utf-8') as stream:
        json.dump(observations,stream,allow_nan=False)
    projected_initial = project(physics,basis,qpos,qvel)
    projected = [project(physics,basis,r['qpos_rad'],r['qvel_rad_s']) for r in rows]
    state_distance = [norm(np.r_[p['q_gvs'],p['qdot_gvs']] - np.r_[q0,np.zeros_like(q0)])
                      for p in [projected_initial]+projected]
    tip_initial = np.asarray(observations[0]['tip_position_m']) if observations else np.full(3,np.nan)
    tip_errors = [norm(tip_initial-tip_target)] + [norm(np.asarray(r['tip_m'])-tip_target) for r in rows]
    limits = np.asarray([t['force_limit_n'] for t in physics['tendons']])
    tension = np.asarray([r['tension_n'] for r in rows]) if rows else np.zeros((0,len(limits)))
    if mode == 'gvs_lqr':
        requests = np.asarray([o['raw_desired_tension_n'] for o in observations])
        lower = (requests < 0).sum(axis=0).tolist()
        upper = (requests > limits).sum(axis=0).tolist()
        max_request = float(np.max(requests))
        max_abs_request = float(np.max(np.abs(requests)))
        any_saturated = int(np.sum(np.any((requests < 0) | (requests > limits),axis=1)))
    else:
        lower = upper = None
        max_request = max_abs_request = None
        any_saturated = None
    summary = dict(level=level, perturbation_fraction_of_q0=fraction, controller=mode,
        perturbation_definition='q_initial=(1-fraction)*q0; qdot_initial=0; exact resolved-basis discretization',
        q_initial=q_initial.tolist(), projected_initial_q=projected_initial['q_gvs'],
        projection_residual_max_rad_m=projected_initial['projection_residual_max_rad_m'],
        initial_state_distance=state_distance[0], final_state_distance=state_distance[-1] if rows else None,
        state_distance=state_distance, tip_deviation_m=tip_errors,
        initial_tip_deviation_m=tip_errors[0], final_tip_deviation_m=tip_errors[-1],
        disturbance_reduced=bool(state_distance[-1] < state_distance[0]) if rows else False,
        final_to_initial_distance_ratio=state_distance[-1]/state_distance[0] if state_distance[0] else None,
        steps_with_any_force_request_saturation=any_saturated,
        lower_request_saturation_by_tendon=lower, upper_request_saturation_by_tendon=upper,
        maximum_requested_tension_n=max_request, maximum_absolute_requested_tension_n=max_abs_request,
        actual_tendon_near_limit_channel_samples=int(np.sum(tension >= .95*limits)),
        actual_tendon_at_limit_channel_samples=int(np.sum(tension >= limits-1e-6)),
        maximum_actual_tension_n=float(np.max(tension)) if len(tension) else None,
        numerical_valid=bool(complete and all(np.isfinite(r['qpos_rad']).all() and
                                              np.isfinite(r['qvel_rad_s']).all() for r in rows)),
        complete=complete, reason=reason, steps=steps, wall_time_s=elapsed)
    if mode == 'tip_feedback':
        commands=np.asarray([o['actuator_command'] for o in observations])
        prior=np.vstack([np.zeros(commands.shape[1]),commands[:-1]])
        speed=np.asarray([a['velocity_limit'] for a in physics['actuators']])
        travel=np.asarray([a['limits'] for a in physics['actuators']])
        summary['actuator_rate_hits']=int(np.sum(np.abs(commands-prior)>=speed*scene['control_period_s']-1e-10))
        summary['actuator_travel_hits']=int(np.sum((np.abs(commands-travel[:,0])<1e-10)|
                                               (np.abs(commands-travel[:,1])<1e-10)))
    atomic_json(folder/'summary.json',summary)
    print(json.dumps({k:summary[k] for k in ('level','controller','initial_state_distance','final_state_distance',
        'initial_tip_deviation_m','final_tip_deviation_m','steps_with_any_force_request_saturation',
        'actual_tendon_at_limit_channel_samples','numerical_valid','wall_time_s')}),flush=True)
    return summary


def main():
    physics=read(GVS,'resolved_physics')
    control=read(GVS,'control_spec')
    q0=np.asarray(control['reference']['equilibrium_q'])
    basis=ResolvedGVSBasis.model_validate(control['algorithm']['projector']['resolved_basis'])
    target=np.asarray(control['predicted_equilibrium_tip_world_m'])
    # Same direction for all levels; percentages have a physical interpretation as
    # a fixed fraction of the equilibrium curvature profile toward the straight arm.
    levels={'small':.01,'medium':.05,'large':.20}
    if '--summarize' in sys.argv:
        summaries=[read(HERE/'local_runs'/level/mode,'summary') for level in levels
                   for mode in ('gvs_lqr','tip_feedback')]
    else:
        summaries=[]
        for level,fraction in levels.items():
            for mode in ('gvs_lqr','tip_feedback'):
                summaries.append(run_case(level,fraction,mode,q0,physics,basis,target))
    model=mujoco.MjModel.from_xml_path(str((HERE/'local_runs/small/gvs_lqr/robot.xml').resolve()))
    data=mujoco.MjData(model)
    qi=np.asarray([model.jnt_qposadr[model.joint(j).id] for j in physics['dofs']])
    vi=np.asarray([model.jnt_dofadr[model.joint(j).id] for j in physics['dofs']])
    aids=np.asarray([model.actuator(t['entity']+'_direct_tension').id for t in physics['tendons']])
    data.qpos[qi]=discretize(physics,basis,q0,np.zeros_like(q0))[0]
    data.ctrl[aids]=control['algorithm']['u0']
    mujoco.mj_forward(model,data)
    equilibrium_probe=dict(backend_tip_world_m=data.site_xpos[model.site('tip_site').id].tolist(),
        gvs_tip_world_m=target.tolist(),tip_discrepancy_m=norm(data.site_xpos[model.site('tip_site').id]-target),
        backend_qacc_norm_rad_s2=norm(data.qacc[vi]),
        backend_qacc_max_abs_rad_s2=float(np.max(np.abs(data.qacc[vi]))),
        actual_tension_n=(-data.actuator_force[aids]).tolist())
    for summary in summaries:
        folder=HERE/'local_runs'/summary['level']/summary['controller']
        with gzip.open(folder/'trajectory.json.gz','rt',encoding='utf-8') as stream:
            rows=json.load(stream)
        q_initial=np.asarray(summary['projected_initial_q'])
        states=[q_initial]+[np.asarray(project(physics,basis,r['qpos_rad'],r['qvel_rad_s'])['q_gvs']) for r in rows]
        q_distances=[norm(q-q0) for q in states]
        summary['initial_q_distance']=q_distances[0]
        summary['final_q_distance']=q_distances[-1]
        summary['q_distance']=q_distances
        atomic_json(folder/'summary.json',summary)
    atomic_json(HERE/'local_control_results.json',dict(
        source_gvs=str(GVS.relative_to(ROOT)),source_tip_feedback=str(TIP.relative_to(ROOT)),
        frozen_physics_identity=physics['identity'],
        target_equilibrium_tip_world_m=target.tolist(),perturbation_fractions=levels,
        backend_equilibrium_probe=equilibrium_probe,
        results=summaries))
    print(json.dumps(equilibrium_probe),flush=True)


if __name__=='__main__':
    main()
