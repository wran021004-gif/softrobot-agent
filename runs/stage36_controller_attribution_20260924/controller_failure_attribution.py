"""Reproduce Case B's saved LQR and compare three offline dynamics levels.

No model service or MuJoCo backend is called by this file.
"""
import gzip
import json
from pathlib import Path
import sys

import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from extensions.tendon_family.contracts import GVSModelParameters, ResolvedGVSBasis  # noqa: E402
from extensions.tendon_family.gvs import GVSModel, forward_kinematics  # noqa: E402
from extensions.tendon_family.gvs_casadi import CasadiLinearizer, expression_from_system, functions_for  # noqa: E402
from extensions.tendon_family.gvs_projection import project  # noqa: E402
from schemas.platform import Payload, RobotDescription  # noqa: E402
from schemas.platform_math import SystemContext  # noqa: E402
from tools.state_io import digest  # noqa: E402

HERE = Path(__file__).resolve().parent
CASE = ROOT / 'runs/stage35_case_b_retry_softagent_20260924/sessions'
GVS = CASE / 'stage35-case-b-retry-softagent-44efe3ecec6b6acb/executions/5e0f73882b1846edbefb893a84c34d10/backend'
TIP = CASE / 'stage35-case-b-retry-softagent-34039c197777faab/executions/44caf52d4455474db18a877a52cfe149/backend'


def read(folder, name):
    path = folder / name
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding='utf-8'))


def norm(value):
    return float(np.linalg.norm(value))


def direction(raw, limits):
    return ['lower' if a < 0 else 'upper' if a > b else 'none' for a, b in zip(raw, limits)]


def series_summary(t, x, request, q0, tip_error=None):
    distance = np.linalg.norm(x - q0, axis=1)
    return dict(times_s=t.tolist(), state_distance=distance.tolist(), initial_distance=float(distance[0]),
                final_distance=float(distance[-1]), minimum_distance=float(min(distance)),
                maximum_distance=float(max(distance)),
                q_distance=np.linalg.norm(x[:,:len(q0)//2]-q0[:len(q0)//2],axis=1).tolist(),
                qdot_distance=np.linalg.norm(x[:,len(q0)//2:]-q0[len(q0)//2:],axis=1).tolist(),
                maximum_absolute_request_n=float(np.max(np.abs(request))),
                tip_error_m=None if tip_error is None else tip_error)


def main():
    control = read(GVS, 'control_spec.json')
    physics = read(GVS, 'resolved_physics.json')
    scene = read(GVS, 'experiment_scene.json')
    robot = RobotDescription.model_validate(read(ROOT / 'runs/stage35_case_b_retry_softagent_20260924/inputs', 'route.json')['robot'])
    observations = read(GVS, 'controller_observations.json')
    rows = read(GVS, 'trajectory.json.gz')
    tip_observations = read(TIP, 'controller_observations.json')
    tip_rows = read(TIP, 'trajectory.json.gz')
    algorithm = control['algorithm']
    x0, u0, K = (np.asarray(algorithm[key], dtype=float) for key in ('x0', 'u0', 'K'))
    n = len(x0) // 2
    limits = np.asarray([t['force_limit_n'] for t in physics['tendons']])
    basis = ResolvedGVSBasis.model_validate(algorithm['projector']['resolved_basis'])
    projected = project(physics, basis, scene['qpos_rad'], scene['qvel_rad_s'])
    xi = np.r_[projected['q_gvs'], projected['qdot_gvs']]
    parameters = GVSModelParameters.model_validate({'basis': basis.specification})
    environment = Payload(contract='experiment.assembly', data=scene['assembly'])
    system = GVSModel(parameters).build_system(robot, parameters, None, SystemContext(
        x0=x0.tolist(), u0=u0.tolist(), scene=environment))
    linear = CasadiLinearizer().linearize(system)
    print('Reconstructed saved linearization', flush=True)
    A, B = np.asarray(linear.A), np.asarray(linear.B)
    assert digest(system.model_dump(mode='json')) == algorithm['dynamic_system_identity']
    assert digest(linear.model_dump(mode='json')) == algorithm['linearization_identity']
    assert np.allclose(x0, linear.x0) and np.allclose(u0, linear.u0)
    closed = np.linalg.eigvals(A - B @ K)
    ctrb = np.hstack([np.linalg.matrix_power(A, i) @ B for i in range(len(x0))])
    # Raw powers span many orders of magnitude; a full-rank prefix is checked
    # with column normalization before later powers lose floating-point rank.
    scaled_rank=0
    rank_prefix_powers=0
    for powers in range(1,len(x0)+1):
        prefix=ctrb[:,:powers*B.shape[1]]
        scaled=prefix/np.maximum(np.linalg.norm(prefix,axis=0),1e-300)
        scaled_rank=int(np.linalg.matrix_rank(scaled))
        if scaled_rank==len(x0):
            rank_prefix_powers=powers
            break
    unstable = [v for v in np.linalg.eigvals(A) if v.real >= -1e-10]
    stabilizable = all(np.linalg.matrix_rank(np.hstack([v*np.eye(len(x0))-A, B])) == len(x0)
                       for v in unstable)

    raw = np.asarray([o['raw_desired_tension_n'] for o in observations])
    directions = [direction(r, limits) for r in raw]
    counts = {name: dict(lower=sum(d[j] == 'lower' for d in directions),
                         upper=sum(d[j] == 'upper' for d in directions))
              for j, name in enumerate(control['reference']['tendon_order'])}
    actual_first = u0 - K @ (xi - x0)
    assert np.allclose(actual_first, raw[0], atol=1e-8)
    t = np.r_[0., np.asarray([r['time_s'] for r in rows])]
    dt = scene['control_period_s']

    # L0 is the exact continuous-time matrix exponential at saved sample times.
    l0 = np.stack([x0 + expm((A - B @ K) * ti) @ (xi - x0) for ti in t])

    def integrate(rhs):
        result = solve_ivp(rhs, (0., float(t[-1])), xi, t_eval=t, method='RK45',
                           max_step=dt/4, rtol=1e-7, atol=1e-9)
        return result.y.T, result.success, result.message

    l1, l1_ok, l1_message = integrate(lambda _, x: A @ (x-x0) + B @ (
        np.clip(u0-K@(x-x0), 0., limits)-u0))
    print('Integrated L1', flush=True)
    nonlinear = functions_for(expression_from_system(system))
    def bounded(x):
        request=u0-K@(x-x0)
        return request,np.clip(request,0.,limits)
    evaluations=[0]
    def nonlinear_rhs(time_s,x):
        evaluations[0]+=1
        if evaluations[0]%200==0:
            print('L2 evaluations '+str(evaluations[0])+' at '+format(time_s,'.5f')+' s',flush=True)
        return nonlinear.evaluate(x,bounded(x)[1])['xdot'].reshape(-1)
    def nonlinear_jac(_,x):
        request,command=bounded(x)
        local_A,local_B,_=nonlinear.linearize(x,command)
        active=(request>0)&(request<limits)
        return local_A-local_B@(active[:,None]*K)
    def escape(_,x):
        return 1e4-norm(x-x0)
    escape.terminal=True
    escape.direction=-1
    l2_times=np.unique(np.r_[np.linspace(0.,.01,11),t])
    try:
        integrated=solve_ivp(nonlinear_rhs,(0.,float(t[-1])),xi,method='BDF',
                             jac=nonlinear_jac,t_eval=l2_times,max_step=dt,
                             rtol=1e-4,atol=1e-6,events=escape)
        l2=integrated.y.T
        l2_times=integrated.t
        l2_ok=integrated.success and not len(integrated.t_events[0])
        l2_message=integrated.message
        l2_stop=float(integrated.t_events[0][0]) if len(integrated.t_events[0]) else float(integrated.t[-1])
    except (ValueError,FloatingPointError,np.linalg.LinAlgError) as exc:
        l2=np.asarray([xi]);l2_times=np.asarray([0.]);l2_ok=False
        l2_message=type(exc).__name__+': '+str(exc);l2_stop=0.
    print('Integrated L2 through '+str(l2_stop)+' s', flush=True)

    target = np.asarray(control['predicted_equilibrium_tip_world_m'])
    rotation = np.asarray(scene['mount_rotation'])
    mount = np.asarray(scene['mount_position'])
    design = robot.structure.data
    def tip_errors(states):
        return [norm(mount + rotation @ forward_kinematics(design, x[:n].tolist(),
                samples_per_segment=2, basis=basis.specification)['tip_position_m']-target) for x in states]

    def offline(x, times):
        request = np.asarray([u0-K@(row-x0) for row in x])
        out = series_summary(times, x, request, x0, tip_errors(x))
        out['clipped_channel_samples'] = int(np.sum((request < 0) | (request > limits)))
        return out

    final_projection = project(physics, basis, rows[-1]['qpos_rad'], rows[-1]['qvel_rad_s'])
    backend_x = np.stack([np.r_[o['gvs_q'], o['gvs_qdot']] for o in observations] +
                         [np.r_[final_projection['q_gvs'], final_projection['qdot_gvs']]])
    backend_tip = [norm(np.asarray(o['tip_position_m'])-target) for o in observations]
    backend_tip.append(norm(np.asarray(rows[-1]['tip_m'])-target))
    l3 = series_summary(t, backend_x, raw, x0, backend_tip)

    tip_control = read(TIP, 'control_spec.json')
    tip_physics = read(TIP, 'resolved_physics.json')
    tip_limits = np.asarray([a['limits'] for a in tip_physics['actuators']])
    tip_rates = np.asarray([a['velocity_limit'] for a in tip_physics['actuators']])
    commands = np.asarray([o['actuator_command'] for o in tip_observations])
    prior = np.vstack([np.zeros(commands.shape[1]), commands[:-1]])
    rate_hit = np.abs(commands-prior) >= tip_rates*dt-1e-10
    travel_hit = (np.abs(commands-tip_limits[:,0]) < 1e-10) | (np.abs(commands-tip_limits[:,1]) < 1e-10)
    tension = np.asarray([r['tension_n'] for r in tip_rows])
    force_limits = np.asarray([x['force_limit_n'] for x in tip_physics['tendons']])
    tip_target = np.asarray(tip_control['reference']['target_world_m'])
    tip_errors_saved = [norm(np.asarray(o['tip_position_m'])-tip_target) for o in tip_observations]
    tip_errors_saved.append(norm(np.asarray(tip_rows[-1]['tip_m'])-tip_target))

    result = dict(source=dict(gvs=str(GVS.relative_to(ROOT)), tip=str(TIP.relative_to(ROOT))),
        identities=dict(dynamic_system=algorithm['dynamic_system_identity'],
                        linearization=algorithm['linearization_identity'],
                        gain=algorithm['gain_identity'], basis=algorithm['projector']['resolved_basis']),
        chain=dict(q0=x0[:n].tolist(), u0=u0.tolist(), x0=x0.tolist(), A=A.tolist(), B=B.tolist(),
                   K=K.tolist(), Q_diagonal=algorithm['Q_diagonal'], R_diagonal=algorithm['R_diagonal'],
                   tendon_order=control['reference']['tendon_order'], force_limits_n=limits.tolist(),
                   projected_initial_state=xi.tolist(), initial_delta_x=(xi-x0).tolist(),
                   initial_delta_q_norm=norm(xi[:n]-x0[:n]), initial_delta_qdot_norm=norm(xi[n:]-x0[n:]),
                   initial_projection_residual=projected['projection_residual_max_rad_m'],
                   maximum_saved_projection_residual_rad_m=max(o['gvs_projection_residual_max_rad_m'] for o in observations),
                   maximum_saved_rate_projection_residual_rad_m_s=max(o['gvs_rate_projection_residual_max_rad_m_s'] for o in observations),
                   first_unconstrained_n=actual_first.tolist(), first_clipped_n=np.clip(actual_first,0,limits).tolist(),
                   first_clipping_direction=directions[0], lower_margin_n=u0.tolist(),
                   upper_margin_n=(limits-u0).tolist()),
        quality=dict(closed_loop_eigenvalues=[[float(v.real),float(v.imag)] for v in closed],
                     maximum_real_eigenvalue=float(max(closed.real)), controllability_rank=scaled_rank,
                     controllability_full_rank_prefix_powers=rank_prefix_powers,
                     public_unscaled_controllability_rank=int(np.linalg.matrix_rank(ctrb)),
                     stabilizable=stabilizable, unstable_open_loop_eigenvalues=[[float(v.real),float(v.imag)] for v in unstable]),
        saturation=dict(total_steps=len(raw), steps_with_any=int(sum(any(d != 'none' for d in row) for row in directions)),
                        channel_samples=int(raw.size), clipped_channel_samples=int(sum(d != 'none' for row in directions for d in row)),
                        per_tendon=counts, maximum_unconstrained_requested_tension_n=float(np.max(raw)),
                        minimum_unconstrained_requested_tension_n=float(np.min(raw))),
        levels=dict(L0=offline(l0,t), L1=offline(l1,t), L2=offline(l2,l2_times), L3=l3),
        integration=dict(L1=dict(success=l1_ok,message=l1_message), L2=dict(success=l2_ok,message=l2_message,stop_time_s=l2_stop)),
        tip_feedback=dict(error_m=tip_errors_saved, actuator_travel_hits_by_channel=travel_hit.sum(axis=0).tolist(),
                          actuator_rate_hits_by_channel=rate_hit.sum(axis=0).tolist(),
                          tendon_near_limit_hits_by_channel=(tension >= .95*force_limits).sum(axis=0).tolist(),
                          tendon_at_limit_hits_by_channel=(tension >= force_limits-1e-6).sum(axis=0).tolist(),
                          maximum_tension_n=float(np.max(tension)),
                          steps_with_any_near_limit=int(np.sum(np.any(tension >= .95*force_limits,axis=1))),
                          steps_with_any_travel_hit=int(np.sum(np.any(travel_hit,axis=1))),
                          steps_with_any_rate_hit=int(np.sum(np.any(rate_hit,axis=1)))))
    (HERE/'controller_failure_attribution.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('quality','saturation','integration','tip_feedback')},indent=2))
    print(json.dumps({k:{m:v for m,v in result['levels'][k].items() if m in ('initial_distance','final_distance','maximum_distance','maximum_absolute_request_n','clipped_channel_samples')} for k in result['levels']},indent=2))


if __name__ == '__main__':
    main()
