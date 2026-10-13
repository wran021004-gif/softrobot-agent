"""One authorized frozen fc1012 tension replay; analysis never steps physics.

Run with the existing mainline5 Python and single-thread numerical environment:
  python -m tools.fc1012_open_loop_replay --check
  python -m tools.fc1012_open_loop_replay
  python -m tools.fc1012_open_loop_replay --analyse
The exclusive execution record prevents accidental repetition, including failures.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tarfile
import time
import traceback

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / 'evidence/fixed_task_20261012'
OUT = ROOT / 'evidence/fc1012_open_loop_20261013'
SOLVE = '7924efa56ab65e39431915aa8ffdc98ffcf71b0c9c8cd5d858465804f05b7ee7'
BDF = '115f97fe1d3fbdf165667ec8f319e985038825b69ae52f1ace0df49d608e72dc'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def artifact(aid, raw=False):
    """Read existing blobs without modifying the sealed Store or auditing hashes."""
    dbpath = ROOT / 'runs/fc1012/platform.sqlite'
    body = None
    if dbpath.exists():
        with closing(sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True)) as db:
            row = db.execute('SELECT body FROM artifacts WHERE id=?', (aid,)).fetchone()
            if row is not None:
                body = row[0]
    if body is None:
        # Existing reassembled archive, or the existing untracked full archive.
        paths = [ROOT / 'runs/fc1012/delivery_archive_reassembled.tar.gz', HISTORY / 'immutable_artifacts.tar.gz']
        archive = next((p for p in paths if p.exists()), None)
        if archive is None:
            raise FileNotFoundError('Required existing fc1012 blob/archive: ' + aid)
        with tarfile.open(archive, 'r:gz') as tar:
            member = next((m for m in tar if m.name in (f'artifacts/{aid}.json', f'artifacts/{aid}.bin')), None)
            if member is None:
                raise FileNotFoundError('Required fc1012 archive member: ' + aid)
            body = tar.extractfile(member).read()
    return body if raw else json.loads(body)


def inputs():
    state = read(HISTORY / 'state.json')
    accepted = artifact(state['accepted_offline']['artifact_id'])
    if accepted['offline_candidate']['artifact_id'] != SOLVE or accepted['independent_verification']['artifact_id'] != BDF:
        raise ValueError('Expected accepted new fc1012 candidate, not historical schedule')
    if not all(accepted[k] for k in ('numerical_feasibility', 'independent_original_sampled_task', 'all_node_consistency')):
        raise ValueError('All three saved acceptance gates required')
    solved = artifact(SOLVE)
    candidate = artifact(solved['trajectory_reference']['artifact_id'])
    verification = artifact(BDF)
    configuration = artifact(solved['checkpoint_reference']['artifact_id'])['configuration']
    summary = read(HISTORY / 'scientific_summary.json')
    physical = next(r for r in summary['physical'] if r['execution_id'] == '6380ef76518b4c24a6bf459942f72545')
    files = physical['source']['files']
    saved = {name: artifact(files[name]['artifact_id'], raw=True) for name in (
        'robot.xml', 'experiment_scene.json', 'compiled_physics.json', 'resolved_physics.json', 'robot_description.json')}
    scene = json.loads(saved['experiment_scene.json'])
    physics = json.loads(saved['resolved_physics.json'])
    if configuration['robot']['structure'] != json.loads(saved['robot_description.json']):
        raise ValueError('Offline structure and saved MuJoCo structure differ')
    if configuration['task']['initializer']['parameters']['data'] != scene['initial']:
        raise ValueError('Saved physical initializer differs')
    from extensions.experiment_dynamics.contracts import Assembly
    if Assembly.model_validate(configuration['task']['environment']['data']).model_dump(mode='json') != scene['assembly']:
        raise ValueError('Saved physical environment differs')
    task = configuration['task']
    if (configuration['seed'] != 17 or scene['target_world_m'] != [.29, .035, .19]
            or task['goal']['data']['target_m'] != scene['target_world_m'] or scene['forces']
            or scene['control']['tension_execution_mode'] != 'ideal_tension'
            or (scene['control_period_s'], scene['timestep_s'], scene['duration_s']) != (.01, .0005, .35)):
        raise ValueError('Frozen physical conditions required')
    tensions = np.asarray(candidate['tensions_n'])
    order = [t['entity'] for t in physics['tendons']]
    lengths = [c['length_m'] for c in configuration['robot']['structure']['data']['components'] if c['kind'] == 'flexible_segment']
    if candidate['tendon_order'] != order or lengths != candidate['lengths_m']:
        raise ValueError('Full precision lengths/tendon order mismatch')
    if tensions.shape != (35, 6) or not np.isfinite(tensions).all() or np.any((tensions < 0) | (tensions > 8)):
        raise ValueError('35 saved bounded six-tendon commands required')
    model = mujoco.MjModel.from_xml_string(saved['robot.xml'].decode('utf-8'))
    mapping = json.loads(saved['compiled_physics.json'])
    joints = [model.joint(j).id for j in physics['dofs']]
    qi, vi = model.jnt_qposadr[joints], model.jnt_dofadr[joints]
    aids = [model.actuator(t + '_direct_tension').id for t in order]
    tids = [model.tendon(t).id for t in order]
    if (qi.tolist() != mapping['qpos_indices'] or vi.tolist() != mapping['qvel_indices']
            or aids != mapping['direct_tension_ids'] or tids != mapping['tendon_ids']
            or model.opt.timestep != .0005 or model.nu != 6
            or not np.all(model.actuator_trntype[aids] == mujoco.mjtTrn.mjTRN_TENDON)
            or model.actuator_trnid[aids, 0].tolist() != tids
            or not np.all(model.actuator_gainprm[aids, 0] == -1)
            or not np.all(model.actuator_ctrlrange[aids] == [0, 8])
            or not np.all(model.actuator_forcerange[aids] == [-8, 0])):
        raise ValueError('Saved direct-tension mapping/limits mismatch')
    return configuration, candidate, verification, scene, model, qi, vi, aids


def reference_outputs(configuration, candidate):
    """Kinematics of stored optimizer states only; no rollout/dynamics/NLP."""
    import casadi as ca
    from extensions.tendon_family.contracts import GVSModelParameters
    from extensions.tendon_family.gvs import _topology, coordinate_order
    from extensions.tendon_family.gvs_basis import resolve_basis
    from extensions.tendon_family.gvs_casadi import _SymbolicKinematics
    from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
    design = configuration['robot']['structure']['data']
    parameters = GVSModelParameters(basis=configuration['policy']['controller']['parameters']['data']['recipe']['basis'])
    resolved = resolve_basis(design, parameters.basis)
    if coordinate_order(design, parameters.basis) != candidate['coordinate_order']:
        raise ValueError('Stored optimizer coordinate order mismatch')
    n = resolved.dimension
    q, v = ca.MX.sym('saved_q', n), ca.MX.sym('saved_v', n)
    kinematics = _SymbolicKinematics(_topology(design), q, parameters.integration_steps_per_segment, resolved)
    mount = configuration['task']['environment']['data']['mount']
    tip = ca.DM(quaternion_wxyz_to_rotation(mount['quaternion_wxyz'])) @ kinematics.attachment_pose(kinematics.design.tip)[:3, 3] + ca.DM(mount['position_m'])
    output = ca.Function('saved_node_motion', [q, v], [tip, ca.jtimes(tip, q, v)])
    motion = [output(x[:n], x[n:]) for x in candidate['states']]
    return np.array([np.asarray(p).ravel() for p, _ in motion]), np.array([np.asarray(v).ravel() for _, v in motion])


def run():
    if (OUT / 'execution.json').exists():
        raise RuntimeError('Existing authorized replay record: inspect/take over; never start again')
    wall = time.perf_counter()
    configuration, candidate, bdf, scene, model, qi, vi, aids = inputs()
    positions, velocities = reference_outputs(configuration, candidate)
    data, pose = mujoco.MjData(model), mujoco.MjData(model)
    data.qpos[qi] = scene['qpos_rad']
    data.qvel[vi] = scene['qvel_rad_s']
    mujoco.mj_forward(model, data)
    site = model.site('tip_site').id
    jac, rot = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    rows = []

    def observe(step, command_index):
        # Separate reconstruction buffer, preserving executed solver state.
        pose.qpos[:] = data.qpos
        pose.qvel[:] = data.qvel
        mujoco.mj_forward(model, pose)
        mujoco.mj_jacSite(model, pose, jac, rot, site)
        rows.append([step * .0005, float(data.time), command_index, *data.ctrl[aids],
                     *(-data.actuator_force[aids]), *pose.site_xpos[site], *(jac @ pose.qvel)])

    observe(0, -1)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / 'references.npz', offline_time_s=candidate['times_s'], offline_position_m=positions,
                        offline_velocity_m_s=velocities, bdf_time_s=bdf['trajectory']['times_s'],
                        bdf_position_m=bdf['trajectory']['tip_positions_m'], bdf_velocity_m_s=bdf['trajectory']['tip_velocities_m_s'],
                        saved_tensions_n=candidate['tensions_n'])
    record = dict(status='running', pid=os.getpid(), started_utc=datetime.now(timezone.utc).isoformat(),
                  source_solve=SOLVE, source_bdf=BDF, source_physical_execution='6380ef76518b4c24a6bf459942f72545',
                  seed=17, d=candidate['d'], lengths_m=candidate['lengths_m'], tendon_order=candidate['tendon_order'],
                  target_m=scene['target_world_m'], control_period_s=.01, timestep_s=.0005, duration_s=.35,
                  command_intervals=35, planned_physics_steps=700, completed_physics_steps=0,
                  initializer=scene['initial'], qpos_indices=qi.tolist(), qvel_indices=vi.tolist(), actuator_ids=aids,
                  velocity_definition='World translational mj_jacSite at stored post-step qpos times qvel',
                  tension_definition='Positive pull = -actuator_force; each recorded force describes the just-completed solver step',
                  preparation_wall_s=time.perf_counter() - wall, mujoco_version=mujoco.__version__,
                  thread_environment={k: os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS')})
    with (OUT / 'execution.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    started = time.perf_counter()
    steps = 0
    try:
        for k, tension in enumerate(candidate['tensions_n']):
            # Preserve the original backend's boundary forward/step ordering.
            mujoco.mj_forward(model, data)
            data.ctrl[aids] = tension
            mujoco.mj_forward(model, data)
            for _ in range(20):
                before = data.time
                mujoco.mj_step(model, data)
                steps += 1
                observe(steps, k)
                warnings = (mujoco.mjtWarning.mjWARN_BADQPOS, mujoco.mjtWarning.mjWARN_BADQVEL, mujoco.mjtWarning.mjWARN_BADQACC)
                if data.time <= before or any(data.warning[w].number for w in warnings) or not all(np.isfinite(x).all() for x in (data.qpos, data.qvel, data.qacc)):
                    raise RuntimeError('MuJoCo numerical failure; retained, no automatic retry')
            mujoco.mj_forward(model, data)
        record['status'] = 'completed'
    except BaseException:
        record.update(status='failed', exception=traceback.format_exc())
        raise
    finally:
        record.update(completed_physics_steps=steps, physics_and_recording_wall_s=time.perf_counter() - started,
                      total_execution_wall_s=time.perf_counter() - wall, ended_utc=datetime.now(timezone.utc).isoformat())
        header = ','.join(['time_s', 'engine_time_s', 'command_index'] + [f'ctrl_{i}_n' for i in range(6)] +
                          [f'applied_{i}_n' for i in range(6)] + [f'tip_{a}_m' for a in 'xyz'] + [f'velocity_{a}_m_s' for a in 'xyz'])
        np.savetxt(OUT / 'trajectory.csv', np.asarray(rows), delimiter=',', header=header, comments='', fmt='%.17g')
        write(OUT / 'execution.json', record)
    print(json.dumps({k: record[k] for k in ('status', 'completed_physics_steps', 'physics_and_recording_wall_s', 'total_execution_wall_s')}))


def analyse():
    record = read(OUT / 'execution.json')
    rows = np.loadtxt(OUT / 'trajectory.csv', delimiter=',', skiprows=1)
    with np.load(OUT / 'references.npz') as refs:
        metrics = {}
        for name in ('offline', 'bdf'):
            times = refs[name + '_time_s']
            # Existing times only; no interpolation or additional integration.
            pairs = [(i, int(np.argmin(abs(times - t)))) for i, t in enumerate(rows[:, 0]) if np.min(abs(times - t)) < 1e-10]
            ai, ri = np.array(pairs).T
            pos, vel = refs[name + '_position_m'][ri], refs[name + '_velocity_m_s'][ri]
            dp = np.linalg.norm(rows[ai, 15:18] - pos, axis=1)
            dv = np.linalg.norm(rows[ai, 18:21] - vel, axis=1)
            error = np.linalg.norm(pos - record['target_m'], axis=1)
            speed = np.linalg.norm(vel, axis=1)
            table = np.c_[rows[ai, 0], pos, vel, dp, dv]
            np.savetxt(OUT / (name + '_comparison.csv'), table, delimiter=',', fmt='%.17g', comments='',
                       header='time_s,reference_x_m,reference_y_m,reference_z_m,reference_vx_m_s,reference_vy_m_s,reference_vz_m_s,position_vector_gap_m,velocity_vector_gap_m_s')
            official = np.isclose(rows[ai, 0] / .01, np.round(rows[ai, 0] / .01), atol=1e-8)
            hold = official & (rows[ai, 0] >= .30 - 1e-10)
            metrics[name] = dict(common_samples=len(ai), maximum_position_gap_m=float(max(dp)), maximum_velocity_gap_m_s=float(max(dv)),
                                 maximum_position_gap_time_s=float(rows[ai[np.argmax(dp)], 0]), maximum_velocity_gap_time_s=float(rows[ai[np.argmax(dv)], 0]),
                                 terminal_position_error_m=float(error[-1]), holding_max_position_error_m=float(max(error[hold])),
                                 holding_max_speed_m_s=float(max(speed[hold])))
        cmd = rows[1:, 2].astype(int)
        expected = refs['saved_tensions_n'][cmd]
        command_gap = float(np.max(abs(rows[1:, 3:9] - expected)))
        applied_gap = float(np.max(abs(rows[1:, 9:15] - expected)))
        counts = np.bincount(cmd, minlength=35)
        schedule_correct = np.array_equal(cmd, np.repeat(np.arange(35), 20))
    error = np.linalg.norm(rows[:, 15:18] - record['target_m'], axis=1)
    speed = np.linalg.norm(rows[:, 18:21], axis=1)
    hi = [int(np.argmin(abs(rows[:, 0] - t))) for t in np.arange(30, 36) * .01]
    complete = record['status'] == 'completed' and record['completed_physics_steps'] == 700 and schedule_correct and all(abs(rows[i, 0] - t) < 1e-10 for i, t in zip(hi, np.arange(30, 36) * .01))
    result = dict(complete=complete, accepted=bool(complete and max(error[hi]) <= .01 and max(speed[hi]) <= .02),
                  terminal_position_error_m=float(error[-1]), holding_max_position_error_m=float(max(error[hi])),
                  holding_max_speed_m_s=float(max(speed[hi])), command_max_difference_n=command_gap, applied_max_difference_n=applied_gap,
                  maximum_engine_time_difference_s=float(max(abs(rows[:, 0] - rows[:, 1]))),
                  holding_samples=[dict(time_s=float(rows[i, 0]), position_error_m=float(error[i]), speed_m_s=float(speed[i])) for i in hi],
                  reference_metrics=metrics, comparison='Only matching stored timestamps, tolerance 1e-10 s; no interpolation',
                  offline_output='Original saved 657 optimizer states, existing symbolic tip kinematics and analytic Jacobian; no dynamics recomputation',
                  physical_launches=1, new_optimizations=0, new_bdf_integrations=0, provider_requests=0)
    result.update(command_schedule_correct=bool(schedule_correct), physics_steps_per_command=counts.tolist())
    bdf = np.loadtxt(OUT / 'bdf_comparison.csv', delimiter=',', skiprows=1)
    result['first_bdf_gap_threshold_crossings'] = {}
    for column, unit, limits in [(7, 'position_m', [.0001, .001, .005, .01]), (8, 'velocity_m_s', [.002, .01, .02, .05, .1])]:
        for limit in limits:
            ids = np.flatnonzero(bdf[:, column] > limit)
            result['first_bdf_gap_threshold_crossings'][f'{unit}>{limit}'] = float(bdf[ids[0], 0]) if len(ids) else None
    result['bdf_gap_phase_samples'] = [dict(time_s=float(t), position_gap_m=float(bdf[i, 7]), velocity_gap_m_s=float(bdf[i, 8]))
        for t in (0, .0005, .01, .05, .10, .20, .29, .30, .35) for i in [int(round(t / .0005))]]
    with np.load(OUT / 'references.npz') as refs:
        u = refs['saved_tensions_n']
        result['command_switch_neighborhoods'] = [dict(command_index=k, switch_time_s=k * .01,
            max_tension_change_n=float(abs(u[k] - u[k - 1]).max()), position_gap_at_switch_m=float(bdf[20 * k, 7]),
            velocity_gap_at_switch_m_s=float(bdf[20 * k, 8]), velocity_gap_after_0005_s_m_s=float(bdf[20 * k + 1, 8]),
            velocity_gap_first_step_change_m_s=float(bdf[20 * k + 1, 8] - bdf[20 * k, 8]),
            velocity_gap_interval_change_m_s=float(bdf[20 * k + 20, 8] - bdf[20 * k, 8])) for k in range(1, 35)]
    write(OUT / 'analysis.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--check', action='store_true', help='Input/mapping/kinematics only; no physics steps')
    modes.add_argument('--analyse', action='store_true', help='Analyse saved execution only; no physics steps')
    args = parser.parse_args()
    if args.analyse:
        analyse()
    elif args.check:
        config, candidate, _, _, _, _, _, _ = inputs()
        position, velocity = reference_outputs(config, candidate)
        print(json.dumps(dict(commands=len(candidate['tensions_n']), stored_nodes=len(position), initial_position_m=position[0].tolist(), initial_velocity_m_s=velocity[0].tolist(), physics_steps_executed=0)))
    else:
        run()


if __name__ == '__main__':
    main()
