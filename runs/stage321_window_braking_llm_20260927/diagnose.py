"""Three sealed B states: aligned reconstruction, local prediction and braking."""
import argparse
import gzip
import json
import sys
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.platform_store import Store
from tools.state_io import atomic_json, digest
from schemas.platform import SessionInput
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace

HERE = Path(__file__).resolve().parent
OLD = ROOT / 'runs/stage320_reach_brake_20260927/B'


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def workspace(parameters=None):
    inp = SessionInput.model_validate(read(OLD / 'input.json'))
    frozen = read(HERE / 'fixed_inputs.json')
    recipe = parameters or inp.policy.controller.parameters.data['recipe']
    nominal = frozen['nominal']
    return TrajectoryWorkspace(inp.task, inp.robot, recipe,
        nominal['q0'] + [0.] * len(nominal['q0']), nominal['u0'],
        settling=inp.policy.controller.parameters.data['settling'])


def freeze():
    import mujoco
    store = Store(OLD)
    summary = read(OLD / 'summary.json')
    run = read(OLD / 'workflow.json')['run_id']
    refs = next(e['outputs'] for e in store.events(run) if e['kind'] == 'simulation'
        and e['execution_id'] == summary['execution_id'] and e['status'] == 'completed')
    bundle = next(v for r in refs if r['media_type'] == 'application/json'
        for v in [store.artifact(r)] if isinstance(v, dict) and 'files' in v)
    references = {f['filename']: f['reference'] for f in bundle['files']}
    files = {name: store.artifact(ref, raw=True) for name, ref in references.items()}
    obs = json.loads(files['controller_observations.json'])
    rows = json.loads(gzip.decompress(files['trajectory.json.gz']))
    material = store.artifact(summary['numerical_preparation']['source'])
    physics = json.loads(files['resolved_physics.json'])
    model = mujoco.MjModel.from_xml_string(files['robot.xml'].decode('utf8'))
    data = mujoco.MjData(model)
    ids = [model.joint(j).id for j in physics['dofs']]
    qi, vi = model.jnt_qposadr[ids], model.jnt_dofadr[ids]
    def motion(row):
        data.qpos[qi] = row['qpos_rad']; data.qvel[vi] = row['qvel_rad_s']
        mujoco.mj_forward(model, data)
        jac = np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, jac, np.zeros_like(jac), model.site('tip_site').id)
        return dict(position_m=list(row['tip_m']), velocity_m_s=(jac @ data.qvel).tolist())
    cases = []
    N = len(material['warm_guess']['tensions'])
    for index, label in ((24, 'approach'), (28, 'late'), (29, 'entry')):
        o = obs[index]; x = o['measured_initial_state']; t = o['time_s']
        # The export contains post-step samples only. Reconstruct the declared
        # straight, stationary initial state; its tip is independently observed.
        row = dict(qpos_rad=[0.]*len(qi), qvel_rad_s=[0.]*len(vi),
            tip_m=o['tip_position_m']) if index == 0 else next(r for r in rows if abs(r['time_s'] - t) < 1e-8)
        following = next(r for r in rows if abs(r['time_s'] - t - .01) < 1e-8)
        cases.append(dict(label=label, time_s=t, measured_x=x,
            previous_u=material['nominal']['u0'] if index == 0 else obs[index-1]['desired_tension_n'],
            applied_u=o['desired_tension_n'], actual=motion(row), next_actual=motion(following),
            recorded_observation=o, next_projected_x=obs[index+1]['measured_initial_state'],
            warm=material['warm_guess'] if index == 0 else dict(
                states=[x]*(N+1), tensions=[o['desired_tension_n']]*N)))
    atomic_json(HERE / 'fixed_inputs.json', dict(cases=cases, nominal=material['nominal'],
        source=dict(folder=str(OLD.relative_to(ROOT)), execution_id=summary['execution_id'],
            observations=references['controller_observations.json'], trajectory=references['trajectory.json.gz'],
            numerical=summary['numerical_preparation']['source']),
        provenance='Sealed measured states and actual applied tensions. World velocity reconstructed with MuJoCo site Jacobian, no stepping. Diagnostic guesses repeat measured state and current applied tension, then fully regenerate dynamics. These are not saved historical complete plans.'))
    w = workspace(); results = []
    for case in cases:
        x = np.asarray(case['measured_x']); started = time.perf_counter()
        y, timing = w._extend_tail(x, case['applied_u'])
        p, v = w._motion(x[:w.n], x[w.n:]); pn, vn = w._motion(y[:w.n], y[w.n:])
        nx = np.asarray(case['next_projected_x'])
        rp, rv = w._motion(nx[:w.n], nx[w.n:])
        def comparison(p, v, actual):
            p = np.asarray(p).ravel(); v = np.asarray(v).ravel()
            return dict(predicted_position_m=p.tolist(), predicted_velocity_m_s=v.tolist(),
                position_difference_m=float(np.linalg.norm(p-actual['position_m'])),
                velocity_difference_m_s=float(np.linalg.norm(v-actual['velocity_m_s'])),
                predicted_speed_m_s=float(np.linalg.norm(v)),
                actual_speed_m_s=float(np.linalg.norm(actual['velocity_m_s'])))
        results.append(dict(label=case['label'], time_s=case['time_s'],
            reconstruction=comparison(p, v, case['actual']),
            one_period_prediction=comparison(pn, vn, case['next_actual']),
            next_reconstruction=comparison(rp, rv, case['next_actual']),
            prediction_to_next_projected_q_norm=float(np.linalg.norm(y[:w.n]-nx[:w.n])),
            prediction_to_next_projected_rate_norm=float(np.linalg.norm(y[w.n:]-nx[w.n:])),
            prediction_timing=timing, wall_s=time.perf_counter()-started))
        print(json.dumps(results[-1]), flush=True)
    atomic_json(HERE / 'prediction_checks.json', dict(input_identity=digest(read(HERE/'fixed_inputs.json')),
        rows=results, period_s=.01, integration='Production implicit Euler, reconstructed only for these three intervals',
        frames='World position m and velocity m/s; same interval-start state and actual held tension',
        timing='Stage 3.20 rolling endpoints are t+0.10 s; absolute holding start 0.30 s is already anticipated from 0.20 s. These aligned one-period checks use actual applied tensions. No original full plans were saved; local solves below reconstruct plans with explicitly regenerated constant-tension guesses.'))


def compare(variant):
    frozen = read(HERE/'fixed_inputs.json')
    recipe = dict(read(OLD/'input.json')['policy']['controller']['parameters']['data']['recipe'])
    if variant == 'lead':recipe.update(holding_brake_lead_s=.05)
    started = time.perf_counter(); w = workspace(recipe)
    result = dict(variant=variant, parameters=recipe, input_identity=digest(frozen),
        graph_s=w.graph_s, rows=[])
    for case in frozen['cases']:
        plan = w.solve(case['measured_x'], case['previous_u'], warm=case['warm'],elapsed_s=case['time_s'])
        motion = [w._motion(x[:w.n], x[w.n:]) for x in plan['states']]
        errors = [float(np.linalg.norm(np.asarray(p).ravel()-w.target)) for p,v in motion]
        speeds = [float(np.linalg.norm(np.asarray(v))) for p,v in motion]
        quality = dict(error_m=errors, tip_speed_m_s=speeds, terminal_error_m=errors[-1],
            terminal_speed_m_s=speeds[-1], minimum_error_m=min(errors), peak_speed_m_s=max(speeds),
            tensions_min_n=float(np.min(plan['tensions'])), tensions_max_n=float(np.max(plan['tensions'])))
        result['rows'].append(dict(label=case['label'], time_s=case['time_s'], plan=plan, quality=quality))
        atomic_json(HERE/(variant+'.json'), result)
        print(json.dumps(dict(label=case['label'], accepted=plan['accepted'], quality=quality,
            violation=plan['result']['constraint_violation'], feedback=plan.get('feedback'),
            delivery_s=plan['update_wall_s'], recovery=plan['recovery'])), flush=True)
    result['experiment_wall_s'] = time.perf_counter()-started
    atomic_json(HERE/(variant+'.json'), result)


def freeze_candidate():
    from extensions.tendon_family.gvs_profile import reach_input
    recipe=read(HERE/'lead.json')['parameters']
    import subprocess
    candidate=dict(recipe=recipe,source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        rationale='50 ms empirical braking lead: current trajectory has short-term velocity prediction discrepancy at entry, and is still moving 52 mm/s at 0.28 s. Demand low speed earlier to leave recovery time, without a constant vector correction or changed feasibility/budget.',
        limitation='Empirical temporal margin motivated by three local states; no certified error bound or settling guarantee.',
        fixed_inputs_identity=digest(read(HERE/'fixed_inputs.json')),
        full_backend_budget=4,conditional_A='B reach and all sampled settling checks pass',
        conditional_LLM='B and A both pass reach and sampled settling; one fresh backend execution')
    atomic_json(HERE/'candidate.json',candidate)
    for label,target in (('B',[.29,.05,.19]),('A',[.29,.035,.19])):
        atomic_json(HERE/(label+'_input.json'),reach_input('stage321-'+label+'-window-brake',target_m=target,recipe=recipe))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['freeze','baseline','lead','freeze-candidate'])
    args = parser.parse_args()
    if args.action=='freeze':freeze()
    elif args.action=='freeze-candidate':freeze_candidate()
    else:compare(args.action)
