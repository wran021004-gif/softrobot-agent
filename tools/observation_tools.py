"""Saved-data adapters; kinematics only, no forward dynamics or numerical solve."""
import gzip
import math
from pathlib import Path
import numpy as np
from tools.closeout_state import read
from tools.artifact_tools import file_hash
from tools.spec_tools import load_yaml

FRAME = 'world_base_x_forward_yz_cross_section'


def _check(samples):
    previous = -math.inf
    for s in samples:
        if not math.isfinite(s['time_s']) or s['time_s'] <= previous:
            raise ValueError('Saved timestamps must be finite and strictly increasing')
        previous = s['time_s']
        if not np.isfinite(s['centerline_m']).all():
            raise ValueError('Nonfinite saved geometry')


def load_observation(source):
    """Accept a run directory or a saved {input,result} mechanics JSON."""
    source = Path(source).resolve()
    if source.is_file():
        value = read(source)
        if value.get('format') == 'observation_v1':
            _check(value['samples'])
            return value
        p, r = value['input'], value['result']
        meta = dict(format='observation_v1', backend='MATLAB', source=str(source), source_sha256=file_hash(source),
            frame=r.get('coordinate_frame', FRAME), model=r.get('model','one_mode_discrete_rod_v1'),
            status=r['status'], reason=r.get('reason'), diagnostics=r.get('diagnostics'), design=dict(total_length_m=p['length_m'], segments=p['n']),
            control='prescribed forces / reduced analysis', target_m=None, events=[],
            semantics={'state':'accepted MATLAB output time', 'shape':'reconstructed from saved equal-bend state',
                'force':'prescribed input, not measured', 'tendon_actual':'unavailable', 'contacts':'not modeled'}, samples=[])
        if r['status'] != 'pass' or p['operation'] != 'dynamic':
            meta['reason'] = r.get('reason','') + '; no completed dynamic trajectory'
            return meta
        for t,q,v,tip in zip(r['time_s'],r['q_rad'],r['velocity_rad_s'],r['tip_m']):
            angles = np.arange(1,p['n']+1)*q/p['n']
            line = np.vstack((np.zeros(3), np.cumsum(np.column_stack((np.cos(angles),np.zeros(p['n']),np.sin(angles)))*p['length_m']/p['n'],axis=0)))
            meta['samples'].append(dict(time_s=t, state=[q,v], centerline_m=line.tolist(), tip_m=tip,
                error_m=None, input_time_s=t, tendon_target_m=None, tendon_actual_m=None, force_n=None, contact_count=None))
        _check(meta['samples'])
        return meta
    trajectory = source / 'trajectory.json.gz'
    legacy = not trajectory.exists()
    if legacy:
        trajectory = source / 'debug/trajectory.json'
        rows = read(trajectory)['samples']
    else:
        rows = __import__('json').loads(gzip.decompress(trajectory.read_bytes()))
    task = load_yaml(source / 'task.yaml')
    design = load_yaml(source / 'design_input.yaml')
    result = read(source / 'mujoco_result.json') if (source / 'mujoco_result.json').exists() else {}
    import mujoco
    from tools.shape_tools import final_centerline
    model = mujoco.MjModel.from_xml_path(str(source / 'robot.xml'))
    data = mujoco.MjData(model)
    samples = []
    for row in rows:
        data.qpos[:] = row['qpos' if legacy else 'qpos_rad']
        mujoco.mj_kinematics(model, data)
        tip = row['tip_position_m' if legacy else 'tip_m']
        samples.append(dict(time_s=row['time_s'], state=data.qpos.tolist(), centerline_m=final_centerline(model,data),
            tip_m=tip, error_m=math.dist(tip,task['target_m']),
            input_time_s=row.get('solver_time_s'),
            tendon_target_m=row.get('tendon_target_lengths_m' if legacy else 'command_m'),
            tendon_actual_m=row.get('tendon_actual_lengths_m' if legacy else 'solver_tendon_length_m'),
            force_n=row.get('actuator_force_n' if legacy else 'solver_actuator_force_n'),
            contact_count=row.get('solver_contact_count')))
    _check(samples)
    controller = 'C2' if (source/'feedback_controller.json').exists() else 'C1'
    if (source/'observation_metadata.json').exists():
        controller = read(source/'observation_metadata.json').get('controller',controller)
    return dict(format='observation_v1', backend='MuJoCo', model='segmented_legacy_v1_surrogate', frame=FRAME,
        source=str(source), source_sha256=file_hash(trajectory), xml_sha256=file_hash(source/'robot.xml'),
        status=result.get('failure_code') or result.get('status','unknown'), design=design, control=controller,
        target_m=task['target_m'], events=result.get('artifacts',{}).get('disturbances',[]),
        semantics=dict(state='post integration', shape='kinematics reconstructed from saved qpos; no mj_step/mj_forward',
            error='derived Euclidean distance from recorded tip',
            force='last dynamics evaluation; signed actuator force, negative = pull',
            tendon_actual='last dynamics evaluation; not post-integration geometry',
            input_time='solver_time_s when recorded; unavailable for old debug data',
            contacts='count only; contact positions and forces unavailable', evidence='DEBUG_ONLY' if legacy else 'normal saved numerical artifact'),
        samples=samples)


def comparison_eligibility(a,b):
    """Cross-backend numerical comparison requires an explicit shared validation contract."""
    if a['frame'] != b['frame']:
        return dict(eligible=False, reason='coordinate frames differ')
    contract = a.get('comparison_contract')
    if not contract or contract != b.get('comparison_contract'):
        return dict(eligible=False, reason='input/initial-state/DOF/parameter/time mapping not established')
    if a['status'] != 'pass' or b['status'] != 'pass':
        return dict(eligible=False, reason='incomplete dynamic result')
    ta = [s['time_s'] for s in a['samples']]; tb = [s['time_s'] for s in b['samples']]
    if not ta or len(ta) != len(tb) or not np.allclose(ta,tb,rtol=0,atol=1e-10):
        return dict(eligible=False, reason='accepted output times differ')
    delta = np.array([s['tip_m'] for s in a['samples']])-np.array([s['tip_m'] for s in b['samples']])
    return dict(eligible=True, reason='explicit saved comparison contract', tip_rms_m=float(np.sqrt(np.mean(np.sum(delta**2,axis=1)))),
        tip_max_m=float(np.max(np.linalg.norm(delta,axis=1))))
