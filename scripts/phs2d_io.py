"""Standalone PHS saved-state IO and moving material points; SI, float64."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import threading

import mujoco
import numpy as np
from portable_xml import load_xml

TASK_DIR = 'PHS2D_passive_head_stabilization'
RESEARCH_SHA = '9d6d160e050c836b87d0563a497fc0ec1c3761a8'
STACK_BYTES = 32 * 1024 * 1024


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(4*1024*1024):
            h.update(block)
    return h.hexdigest()


def array_sha(array):
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def forbid_integration():
    """Fail immediately if a read-only path accidentally starts integration."""
    def forbidden(*args, **kwargs):
        raise RuntimeError('PHYSICS_INTEGRATION_FORBIDDEN_IN_SAVED_STATE_TOOLS')
    for name in ('mj_step', 'mj_step1', 'mj_step2'):
        setattr(mujoco, name, forbidden)


def load_model(path):
    results, errors = [], []
    def compile_model():
        try:
            results.append(load_xml(path))
        except BaseException as exc:
            errors.append(exc)
    previous = threading.stack_size()
    try:
        threading.stack_size(max(previous, STACK_BYTES))
        worker = threading.Thread(target=compile_model)
        worker.start()
    finally:
        threading.stack_size(previous)
    worker.join()
    if errors:
        raise errors[0]
    model = results[0]
    # Exact runtime overrides in the frozen PassiveModel constructor.
    model.opt.iterations = 100
    model.opt.tolerance = 1e-10
    return model


def base_path(package):
    package = Path(package).resolve()
    return package if package.name == TASK_DIR else package / TASK_DIR


def parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument('--package', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--condition', help='equilibrium or s030_positive ... s070_negative')
    p.add_argument('--s', type=float, choices=[.3, .4, .5, .6, .7], default=.5)
    p.add_argument('--direction', choices=['positive', 'negative'], default='positive')
    return p


def locate(args):
    base = base_path(args.package)
    name = args.condition or f's{round(args.s*100):03d}_{args.direction}'
    entries = [e for e in read(base/'dataset.json')['trajectories'] if e['condition'] == name]
    require(len(entries) == 1, 'UNKNOWN_PHS_CONDITION')
    entry = entries[0]
    return base, base/entry['directory'], entry


def joint_mapping(model, physics):
    joints = []
    for name in physics['dofs']:
        index = model.joint(name).id
        require(model.jnt_type[index] == mujoco.mjtJoint.mjJNT_HINGE, 'SCALAR_HINGE_REQUIRED')
        joints.append(dict(name=name, joint_id=int(index), qpos_address=int(model.jnt_qposadr[index]),
                           qvel_address=int(model.jnt_dofadr[index]),
                           qpos_column='qpos_rad__'+name, qvel_column='qvel_rad_s__'+name))
    return dict(version='phs2d_passive_joint_map_v1', nq=model.nq, nv=model.nv,
                joints=joints, tendon_order=[model.tendon(i).name for i in range(model.ntendon)],
                actuator_order=[])


def material_point(physics, s):
    """Frozen passive.material_point convention, excluding rigid spacers."""
    require(0 <= s <= 1, 'MATERIAL_S_OUT_OF_RANGE')
    cells = [(i, p) for i, p in enumerate(physics['parts']) if p['dofs']]
    target = s * sum(p['length_m'] for _, p in cells)
    for k, (index, part) in enumerate(cells):
        if target < part['length_m']-1e-14 or k == len(cells)-1:
            return dict(body=index, position_m=[float(np.clip(target, 0, part['length_m'])), 0., 0.])
        target -= part['length_m']


def point(model, data, physics, binding):
    name = 'fixed_base' if binding['body'] < 0 else physics['parts'][binding['body']]['entity']
    bid = model.body(name).id
    return data.xpos[bid] + data.xmat[bid].reshape(3, 3) @ binding['position_m'], bid


def apply_force(model, data, physics, binding, force):
    data.qfrc_applied[:] = 0.
    data.xfrc_applied[:] = 0.
    position, bid = point(model, data, physics, binding)
    mujoco.mj_applyFT(model, data, np.array([force, 0., 0.]), np.zeros(3), position, bid, data.qfrc_applied)


def ramp_force(step_before, timestep, magnitude, ramp_s):
    a = min(step_before*timestep/ramp_s, 1.)
    return magnitude*a*a*(3-2*a)


def restore(model, data, row):
    n = model.nq
    data.time = row[0]
    data.qpos[:] = row[2:2+n]
    data.qvel[:] = row[2+n:2+2*n]
    data.qfrc_applied[:] = 0.
    data.xfrc_applied[:] = 0.
    mujoco.mj_forward(model, data)


def initial_row(snapshot):
    return np.asarray([snapshot['time_s'], snapshot['force_n'], *snapshot['qpos'],
                       *snapshot['qvel'], *snapshot['qacc'], *snapshot['tendon_lengths'],
                       *snapshot['tensions_n']], dtype=np.float64)


def state_columns(n=144, nt=4):
    return ['time_s', 'force_n', *[f'qpos_{i}' for i in range(n)],
            *[f'qvel_{i}' for i in range(n)], *[f'qacc_{i}' for i in range(n)],
            *[f'length_{i}' for i in range(nt)], *[f'tension_{i}' for i in range(nt)]]


def csv_columns(mapping):
    return ['step_index', 'time_s', *[j['qpos_column'] for j in mapping['joints']],
            *[j['qvel_column'] for j in mapping['joints']],
            *['tip_position_m_'+a for a in 'xyz'],
            *[f'tip_rotation_r{i}{j}' for i in range(3) for j in range(3)],
            *['force_point_m_'+a for a in 'xyz'], *['external_force_n_'+a for a in 'xyz'],
            *['tendon_length_m__'+t for t in mapping['tendon_order']],
            *['tendon_length_excess_m__'+t for t in mapping['tendon_order']],
            *['original_tension_n__'+t for t in mapping['tendon_order']],
            'original_qacc_inf_rad_s2', 'reconstructed_contact_count']


def csv_values(index, row, tip, rotation, force_point, payout, contacts):
    n, nt = 144, 4
    lengths = row[2+3*n:2+3*n+nt]
    return [index, row[0], *row[2:2+2*n], *tip, *rotation.ravel(), *force_point,
            row[1], 0., 0., *lengths, *(lengths-payout), *row[-nt:],
            np.max(np.abs(row[2+2*n:2+3*n])), int(contacts)]


def states(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def centerline(model, data, physics):
    start = data.xpos[model.body('fixed_base').id].copy()
    ends = [point(model, data, physics, dict(body=i, position_m=[part['length_m'], 0., 0.]))[0]
            for i, part in enumerate(physics['parts']) if part['dofs']]
    return np.asarray([start, *ends, point(model, data, physics, physics['tip'])[0]])


def write_png(path, rgb):
    import struct
    import zlib
    def chunk(kind, body):
        return struct.pack('!I', len(body))+kind+body+struct.pack('!I', zlib.crc32(kind+body)&0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!2I5B', rgb.shape[1], rgb.shape[0], 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(b''.join(b'\0'+row.tobytes() for row in rgb)))+chunk(b'IEND', b'')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(png)
