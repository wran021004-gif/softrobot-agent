"""Three archived states, six MuJoCo continuations, three fixed-geometry BDF solves."""
import argparse
from contextlib import closing
import csv
import gzip
import json
import os
from pathlib import Path
import sqlite3
import sys
import tarfile
import time

import casadi as ca
import mujoco
import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from extensions.tendon_family.contracts import ResolvedGVSBasis
from extensions.tendon_family.gvs_codesign import expression
from extensions.tendon_family.gvs_casadi import GVSCasadiFunctions
from extensions.tendon_family.gvs_projection import project, discretize

EXECUTION = '6380ef76518b4c24a6bf459942f72545'
DEFAULT_SOURCE = Path('D:/softrobot-agent/.worktrees/mechanics-control-mainline')
OUT = Path(__file__).resolve().parent
THREADS = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS')


def artifact(root, aid):
    """Small read-only loader following fc1012_open_loop_replay.artifact."""
    dbpath = root / 'runs/fc1012/platform.sqlite'
    if dbpath.exists():
        with closing(sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True)) as db:
            row = db.execute('SELECT body FROM artifacts WHERE id=?', (aid,)).fetchone()
            if row is not None:
                return row[0]
    for path in (root / 'runs/fc1012/delivery_archive_reassembled.tar.gz',
                 root / 'evidence/fixed_task_20261012/immutable_artifacts.tar.gz'):
        if path.exists():
            with tarfile.open(path, 'r:gz') as archive:
                for member in archive:
                    if member.name in (f'artifacts/{aid}.json', f'artifacts/{aid}.bin'):
                        return archive.extractfile(member).read()
    raise FileNotFoundError('Missing existing artifact: ' + aid)


def at_time(rows, wanted):
    # Match saved timestamps, never interpolate. Tolerance only handles float spelling.
    matches = [row for row in rows if abs(row['time_s'] - wanted) < 1e-12]
    if len(matches) != 1:
        raise ValueError(f'Expected one archived sample at {wanted}: {len(matches)}')
    return matches[0]


def load_cases(root):
    summary = json.loads((root / 'evidence/fixed_task_20261012/scientific_summary.json').read_text(encoding='utf8'))
    source = next(row['source'] for row in summary['physical'] if row['execution_id'] == EXECUTION)
    names = ('robot.xml', 'resolved_physics.json', 'compiled_physics.json', 'experiment_scene.json',
             'trajectory.json.gz', 'controller_observations.json', 'solver_configuration.json')
    saved = {}
    for name in names:
        raw = artifact(root, source['files'][name]['artifact_id'])
        saved[name] = raw.decode('utf8') if name.endswith('.xml') else json.loads(
            gzip.decompress(raw) if name.endswith('.gz') else raw)
    scene, physics = saved['experiment_scene.json'], saved['resolved_physics.json']
    model = mujoco.MjModel.from_xml_string(saved['robot.xml'])
    joints = [model.joint(name).id for name in physics['dofs']]
    qi, vi = model.jnt_qposadr[joints], model.jnt_dofadr[joints]
    order = [tendon['entity'] for tendon in physics['tendons']]
    aids = [model.actuator(name + '_direct_tension').id for name in order]
    mapping = saved['compiled_physics.json']
    assert qi.tolist() == mapping['qpos_indices'] and vi.tolist() == mapping['qvel_indices']
    assert aids == mapping['direct_tension_ids'] and len(qi) == model.nq == model.nv
    assert scene['control']['tension_execution_mode'] == 'ideal_tension' and not scene['forces']
    assert scene['control_period_s'] == .01 and scene['timestep_s'] == model.opt.timestep == .0005
    assert np.all(model.actuator_gainprm[aids, 0] == -1) and np.all(model.actuator_ctrlrange[aids] == [0, 8])
    cases = []
    for wanted in (0., .20, .29):
        obs = at_time(saved['controller_observations.json'], wanted)
        state = scene if wanted == 0 else at_time(saved['trajectory.json.gz'], wanted)
        following = at_time(saved['trajectory.json.gz'], wanted + .01)
        record = obs['complete_update_record']
        q, v, u = [np.asarray(value, dtype=float) for value in
                   (state['qpos_rad'], state['qvel_rad_s'], obs['actual_tension_n'])]
        assert q.shape == v.shape == (len(qi),) and u.shape == (len(aids),)
        assert np.isfinite(np.r_[q, v, u]).all() and np.all((u >= 0) & (u <= 8))
        assert record['tendon_order'] == order
        assert np.array_equal(u, record['actual_applied_action_n'])
        assert np.array_equal(u, following['tension_n'])
        cases.append(dict(time_s=obs['time_s'], state_time_s=0. if wanted == 0 else state['time_s'],
                          state_source='saved scene initializer' if wanted == 0 else 'post-step trajectory',
                          q=q, v=v, u=u, observation=obs, following=following))
    return source, saved, model, qi, vi, aids, cases


def restore(model, qi, vi, q, v, case, aids):
    data = mujoco.MjData(model)  # Same default non-joint state and empty caches for A/B.
    data.qpos[qi], data.qvel[vi] = q, v
    data.time, data.ctrl[aids] = case['time_s'], case['u']
    mujoco.mj_forward(model, data)
    return data


def observe(model, data):
    # Refresh only a separate buffer, preserving the executed integration cache.
    pose = mujoco.MjData(model)
    pose.qpos[:], pose.qvel[:] = data.qpos, data.qvel
    mujoco.mj_forward(model, pose)
    jac, rot = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    site = model.site('tip_site').id
    mujoco.mj_jacSite(model, pose, jac, rot, site)
    return np.r_[pose.site_xpos[site], jac @ pose.qvel]


def errors(delta):
    return dict(max_abs=float(np.max(np.abs(delta))), rms=float(np.sqrt(np.mean(delta**2))))


def project_and_reconstruct(physics, projector, case):
    basis = ResolvedGVSBasis.model_validate(projector['resolved_basis'])
    projected = project(physics, basis, case['q'], case['v'], convention=projector['id'])
    x = np.r_[projected['q_gvs'], projected['qdot_gvs']]
    record = case['observation']['complete_update_record']
    assert projected['coordinate_order'] == record['coordinate_order']
    alignment = float(np.max(np.abs(x - record['measured_state'])))
    if alignment > 1e-9:
        raise ValueError(f'Projection alignment unresolved: {alignment}')
    q, v = discretize(physics, basis, projected['q_gvs'], projected['qdot_gvs'], convention=projector['id'])
    return x, q, v, alignment


def static_comparison(model, a, b, qi, vi, bodies):
    shape = a.xpos[bodies] - b.xpos[bodies]
    motion = observe(model, a) - observe(model, b)
    distances = np.linalg.norm(shape, axis=1)
    return dict(joint_angle_rad=errors(a.qpos[qi] - b.qpos[qi]),
                joint_velocity_rad_s=errors(a.qvel[vi] - b.qvel[vi]),
                shape_difference_mm=shape * 1000, shape_max_mm=float(max(distances) * 1000),
                shape_rms_mm=float(np.sqrt(np.mean(distances**2)) * 1000),
                tip_position_difference_mm=motion[:3] * 1000, tip_velocity_difference_m_s=motion[3:])


def fixed_functions(configuration, scene):
    expr = expression(configuration)
    f = GVSCasadiFunctions(expr)  # Fixed geometry: no Workspace, parameterized graph, or NLP.
    assert f.resolved.model_dump(mode='json') == scene['control']['projector']['resolved_basis']
    x, u, rhs = f._linearization_symbols
    rhs_fn = ca.Function('gap_rhs', [x, u], [rhs], {'cse': True})
    jac_fn = ca.Function('gap_jac', [x, u], [ca.jacobian(rhs, x)], {'ad_weight': 1., 'cse': True})
    n = len(expr.coordinate_order)
    q, v = f.q_symbol, ca.MX.sym('v', n)
    tip = ca.DM(scene['mount_rotation']) @ f.tip_position_expression + ca.DM(scene['mount_position'])
    motion = ca.Function('gap_motion', [q, v], [ca.vertcat(tip, ca.jtimes(tip, q, v))])
    return f, rhs_fn, jac_fn, motion, n


def short_mujoco(model, data, deadline, steps=20):
    rows = [observe(model, data)]
    for step in range(steps):
        if time.perf_counter() >= deadline:
            raise TimeoutError('900-second numerical allowance exhausted')
        before = data.time
        mujoco.mj_step(model, data)
        assert data.time > before and np.isfinite(np.r_[data.qpos, data.qvel, data.qacc]).all()
        assert not any(data.warning[w].number for w in (mujoco.mjtWarning.mjWARN_BADQPOS,
                      mujoco.mjtWarning.mjWARN_BADQVEL, mujoco.mjtWarning.mjWARN_BADQACC))
        if (step + 1) % (steps // 20) == 0:
            rows.append(observe(model, data))
    return np.asarray(rows)


def short_gvs(functions, x, u, deadline):
    _, rhs_fn, jac_fn, motion, n = functions

    def rhs(t, state):
        if time.perf_counter() >= deadline:
            raise TimeoutError('900-second numerical allowance exhausted')
        return np.asarray(rhs_fn(state, u)).ravel()

    solution = solve_ivp(rhs, (0., .01), x, method='BDF',
                         jac=lambda t, state: np.asarray(jac_fn(state, u)), rtol=1e-10,
                         atol=np.r_[np.full(n, 1e-11), np.full(n, 1e-9)], dense_output=True)
    if not solution.success:
        raise RuntimeError(solution.message)
    states = solution.sol(np.arange(21) * .0005).T
    rows = np.asarray([np.asarray(motion(y[:n], y[n:])).ravel() for y in states])
    assert np.isfinite(states).all() and np.isfinite(rows).all()
    return rows, dict(nfev=solution.nfev, njev=solution.njev, nlu=solution.nlu)


def differences(a, b):
    result = {}
    for name, sl, scale in (('position_mm', slice(0, 3), 1000), ('velocity_m_s', slice(3, 6), 1)):
        delta = (a[:, sl] - b[:, sl]) * scale
        increment = delta[-1] - delta[0]
        result[name] = dict(start_vector=delta[0], end_vector=delta[-1], increment_vector=increment,
                            start_norm=float(np.linalg.norm(delta[0])), end_norm=float(np.linalg.norm(delta[-1])),
                            max_norm=float(np.linalg.norm(delta, axis=1).max()), increment_norm=float(np.linalg.norm(increment)))
    return result


def summarize(result):
    (OUT / 'results.json').write_text(json.dumps(result, indent=2, allow_nan=False,
         default=lambda value: value.tolist()) + '\n', encoding='utf8')
    rows = []
    for case in result['cases']:
        row = dict(time_s=case['time_s'], shape_max_mm=case['static']['shape_max_mm'],
                   shape_rms_mm=case['static']['shape_rms_mm'])
        for field in ('joint_angle_rad', 'joint_velocity_rad_s'):
            row.update({field + '_' + key: value for key, value in case['static'][field].items()})
        for pair, metrics in case.get('comparisons', {}).items():
            for quantity, values in metrics.items():
                row.update({f'{pair}_{quantity}_{key}': values[key] for key in
                            ('start_norm', 'end_norm', 'max_norm', 'increment_norm')})
        rows.append(row)
    if rows:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        with (OUT / 'results.csv').open('w', newline='', encoding='utf8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def refine_mujoco(model, qi, vi, aids, saved, cases):
    """One explicitly invoked half-step check; retain C and the original allowance."""
    result = json.loads((OUT / 'results.json').read_text(encoding='utf8'))
    assert result['status'] == 'completed' and 'refinement' not in result
    case = at_time(cases, .29)
    original = at_time(result['cases'], .29)
    assert np.array_equal(case['u'], original['command_n'])
    refinement = dict(time_s=case['time_s'], timestep_s=.00025, status='running',
        question='Sensitivity of the 0.29 s B-C velocity increment difference to MuJoCo timestep',
        fixed='Saved C trajectory, initial states, command, integrator and restoration policy', sampled_motion={})
    result['refinement'] = refinement
    started = time.perf_counter()
    deadline = started + max(0., 900 - result['numerical_elapsed_s'])
    operation, op_start = None, started
    try:
        assert time.perf_counter() < deadline, 'Original numerical allowance exhausted'
        projector = saved['experiment_scene.json']['control']['projector']
        basis = ResolvedGVSBasis.model_validate(projector['resolved_basis'])
        x = np.asarray(original['projected_state'])
        q, v = discretize(saved['resolved_physics.json'], basis, x[:basis.dimension], x[basis.dimension:],
                          convention=projector['id'])
        model.opt.timestep = .00025  # Only numerical setting changed.
        for label, pos, vel in (('A', case['q'], case['v']), ('B', q, v)):
            op_start = time.perf_counter()
            operation = dict(name=label, phase='refinement', time_s=case['time_s'], status='running')
            result['operations'].append(operation)
            data = restore(model, qi, vi, pos, vel, case, aids)
            refinement['sampled_motion'][label] = short_mujoco(model, data, deadline, steps=40)
            operation.update(status='completed', physics_steps=40, elapsed_s=time.perf_counter() - op_start)
        motion = refinement['sampled_motion']
        refinement['refined_minus_original'] = {label: differences(motion[label], np.asarray(original['sampled_motion'][label]))
                                                for label in ('A', 'B')}
        motion['C'] = np.asarray(original['sampled_motion']['C'])
        refinement['comparisons'] = {left + right: differences(motion[left], motion[right])
                                    for left, right in (('A', 'B'), ('B', 'C'), ('A', 'C'))}
        refinement['status'] = 'completed'
    except Exception as exc:
        refinement.update(status='failed', error=repr(exc))
        if operation is not None:
            operation.update(status='failed', error=repr(exc), elapsed_s=time.perf_counter() - op_start)
        raise
    finally:
        refinement['numerical_elapsed_s'] = time.perf_counter() - started
        result['numerical_elapsed_s'] += refinement['numerical_elapsed_s']
        summarize(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--check', action='store_true', help='Read and validate inputs only; no dynamics or stepping')
    parser.add_argument('--refine-mujoco', action='store_true', help='Once only: half MuJoCo timestep at 0.29 s, using existing results and fixed C')
    args = parser.parse_args()
    assert all(os.environ.get(key) == '1' for key in THREADS), 'Set numerical threads before starting Python'
    source, saved, model, qi, vi, aids, cases = load_cases(args.source_root.resolve())
    if args.check:
        print(f'Inputs aligned: {len(cases)} cases, {len(qi)} named joints, no capture required')
        return
    if args.refine_mujoco:
        refine_mujoco(model, qi, vi, aids, saved, cases)
        return
    if (OUT / 'results.json').exists():
        raise FileExistsError('Existing results: inspect them; do not silently repeat the bounded analysis')
    scene, physics = saved['experiment_scene.json'], saved['resolved_physics.json']
    projector = scene['control']['projector']
    body_names = [part['entity'] for part in physics['parts'] if part['dofs']]
    bodies = [model.body(name).id for name in body_names]
    result = dict(status='running', execution_id=EXECUTION, source_root=str(args.source_root.resolve()),
                  source_files={name: source['files'][name] for name in saved}, capture_needed=False,
                  projector=projector, joint_order=physics['dofs'], qpos_indices=qi, qvel_indices=vi,
                  tendon_order=[t['entity'] for t in physics['tendons']], actuator_ids=aids,
                  dimensions=dict(mujoco_qpos=model.nq, mujoco_qvel=model.nv, gvs=projector['resolved_basis']['dimension']),
                  shape_locations=dict(definition='World body-frame origins of the same flexible cells', names=body_names),
                  restoration=dict(policy='Fresh MjData per A/B; named q/v, saved time and following command; mj_forward once before steps; separate observation buffer',
                     missing=['qacc_warmstart', 'solver/cache history', 'historical applied-force buffers', 'activation snapshot'],
                     activation_dimension=model.na, applied_forces='zero; saved scene has no external forces',
                     other_state='Model defaults for non-joint state; no exact historical engine snapshot claimed'),
                  settings=dict(mujoco_version=mujoco.__version__, solver=saved['solver_configuration.json'],
                     timestep_s=.0005, interval_s=.01, samples=21, bdf_rtol=1e-10, bdf_atol_q=1e-11,
                     bdf_atol_v=1e-9, mount_rotation=scene['mount_rotation'], mount_position=scene['mount_position'],
                     threads={key: os.environ[key] for key in THREADS}), cases=[], operations=[])
    started = time.perf_counter()
    deadline = started + 900
    operation = dict(name='fixed_geometry_functions', status='running')
    result['operations'].append(operation)
    op_start = started
    try:
        functions = fixed_functions(source['configuration'], scene)
        assert functions[0].parameters.model_dump(mode='json') == cases[0]['observation']['complete_update_record']['model_binding']['parameters']['data']
        operation.update(status='completed', elapsed_s=time.perf_counter() - op_start)
        result['settings']['gvs_parameters'] = functions[0].parameters.model_dump(mode='json')
        print('Fixed-geometry functions built', flush=True)
        for case in cases:
            x, q, v, alignment = project_and_reconstruct(physics, projector, case)
            a = restore(model, qi, vi, case['q'], case['v'], case, aids)
            b = restore(model, qi, vi, q, v, case, aids)
            entry = dict(time_s=case['time_s'], state_time_s=case['state_time_s'], state_source=case['state_source'],
                         command_n=case['u'], command_source='controller_observations at interval start',
                         projected_state=x, recorded_projection_max_abs_difference=alignment,
                         static=static_comparison(model, a, b, qi, vi, bodies), sampled_motion={},
                         times_s=case['time_s'] + np.arange(21) * .0005,
                         motion_columns=['x_m', 'y_m', 'z_m', 'vx_m_s', 'vy_m_s', 'vz_m_s'])
            result['cases'].append(entry)
            for label, data in (('A', a), ('B', b), ('C', None)):
                op_start = time.perf_counter()
                if op_start >= deadline:
                    raise TimeoutError('900-second numerical allowance exhausted')
                operation = dict(name=label, time_s=case['time_s'], status='running')
                result['operations'].append(operation)
                if data is None:
                    rows, stats = short_gvs(functions, x, case['u'], deadline)
                    operation.update(stats)
                else:
                    rows = short_mujoco(model, data, deadline)
                    operation['physics_steps'] = 20
                entry['sampled_motion'][label] = rows
                operation.update(status='completed', elapsed_s=time.perf_counter() - op_start)
            motion = entry['sampled_motion']
            entry['comparisons'] = {left + right: differences(motion[left], motion[right])
                                    for left, right in (('A', 'B'), ('B', 'C'), ('A', 'C'))}
            nxt = case['following']
            archived = restore(model, qi, vi, nxt['qpos_rad'], nxt['qvel_rad_s'], case, aids)
            entry['archive_alignment'] = dict(next_time_s=nxt['time_s'],
                initial_tip_max_abs_m=float(np.max(np.abs(motion['A'][0, :3] - case['observation']['tip_position_m']))),
                endpoint_motion_difference=motion['A'][-1] - observe(model, archived),
                endpoint_qpos_max_abs_rad=float(np.max(np.abs(a.qpos[qi] - nxt['qpos_rad']))),
                endpoint_qvel_max_abs_rad_s=float(np.max(np.abs(a.qvel[vi] - nxt['qvel_rad_s']))))
            print(f"Completed case {case['time_s']:.2f} s", flush=True)
        result['status'] = 'completed'
    except Exception as exc:
        operation.update(status='failed', elapsed_s=time.perf_counter() - op_start, error=repr(exc))
        result.update(status='failed', error=repr(exc))
        raise
    finally:
        result['numerical_elapsed_s'] = time.perf_counter() - started
        summarize(result)


if __name__ == '__main__':
    main()
