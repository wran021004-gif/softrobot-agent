"""Portable package data and detached MuJoCo observations (SI, no integration)."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write(path, value):
    path=Path(path)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode('utf8')).hexdigest()


def csv_write(path, rows):
    with Path(path).open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def csv_read(path):
    with Path(path).open(newline='',encoding='utf8') as stream:
        reader=csv.DictReader(stream)
        if len(reader.fieldnames)!=len(set(reader.fieldnames)):raise ValueError('DUPLICATE_CSV_COLUMNS')
        return [{k:float(v) for k,v in row.items()} for row in reader]


def parser(description):
    p=argparse.ArgumentParser(description=description)
    p.add_argument('--package',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--benchmark',choices=['M1','M2','M3','M4','M5','M6'],required=True)
    p.add_argument('--condition',default='default')
    return p


def locate(args):
    root=args.package.resolve();manifest=read(root/'manifest.json')
    entries=[e for e in manifest['trajectories'] if
        e['benchmark']==args.benchmark and e['condition']==args.condition]
    if len(entries)!=1:raise ValueError('Choose a condition from manifest.json for this benchmark')
    entry=entries[0];folder=root/entry['directory']
    task=read(folder/'task.json');mapping=read(root/args.benchmark/'joint_map.json')
    model=mujoco.MjModel.from_xml_path(str(root/args.benchmark/'robot.xml'))
    return root,folder,entry,task,mapping,model


def joint_map(model, order):
    joints=[]
    for name in order:
        j=model.joint(name).id
        if model.jnt_type[j]!=mujoco.mjtJoint.mjJNT_HINGE:
            raise ValueError('THIS_EXPORT_REQUIRES_SCALAR_HINGE_JOINTS')
        joints.append(dict(name=name,joint_id=int(j),qpos_address=int(model.jnt_qposadr[j]),
            qvel_address=int(model.jnt_dofadr[j]),qpos_column='qpos_rad__'+name,qvel_column='qvel_rad_s__'+name))
    if len(joints)!=model.nq or len(joints)!=model.nv:raise ValueError('INCOMPLETE_JOINT_MAP')
    tendons=[model.tendon(i).name for i in range(model.ntendon)]
    actuators=[model.actuator(i).name for i in range(model.nu)]
    return dict(version='base_only_joint_map_v1',nq=model.nq,nv=model.nv,joints=joints,
        tendon_order=tendons,actuator_order=actuators,
        requested_tension_columns=['requested_tension_n__'+t for t in tendons],
        actual_tension_columns=['actual_tension_n__'+t for t in tendons])


def observation(model, data, step, interval, mapping, axis_local, force_bodies):
    """data MUST be detached. Forward refreshes post-step pose/force caches."""
    integration_contacts=int(data.ncon)
    applied=data.xfrc_applied.copy()
    mujoco.mj_forward(model,data)
    tip=model.site('tip_site').id;jac=np.zeros((3,model.nv))
    mujoco.mj_jacSite(model,data,jac,None,tip)
    rotation=data.site_xmat[tip].reshape(3,3);velocity=jac@data.qvel
    row=dict(step_index=step,time_s=float(data.time),control_interval_index=interval)
    for j in mapping['joints']:
        row[j['qpos_column']]=float(data.qpos[j['qpos_address']])
        row[j['qvel_column']]=float(data.qvel[j['qvel_address']])
    for prefix,values in [('tip_position_m',data.site_xpos[tip]),('tip_velocity_m_s',velocity),
        ('tool_axis_world',rotation@np.asarray(axis_local))]:
        row.update({prefix+'_'+axis:float(v) for axis,v in zip('xyz',values)})
    row.update({f'tip_rotation_r{i}{j}':float(rotation[i,j]) for i in range(3) for j in range(3)})
    for t,a in zip(mapping['tendon_order'],mapping['actuator_order']):
        aid=model.actuator(a).id
        row['requested_tension_n__'+t]=float(data.ctrl[aid])
        row['actual_tension_n__'+t]=float(-data.actuator_force[aid])
    for axis,v in zip('xyz',applied[:,:3].sum(axis=0)):row['external_force_n_'+axis]=float(v)
    for body in force_bodies:
        for axis,v in zip('xyz',applied[model.body(body).id,:3]):
            row['external_force_n__'+body+'_'+axis]=float(v)
    row.update(integration_cache_contact_count=integration_contacts,post_state_contact_count=int(data.ncon))
    return row


def restore(model, data, row, mapping):
    for j in mapping['joints']:
        data.qpos[j['qpos_address']]=row[j['qpos_column']]
        data.qvel[j['qvel_address']]=row[j['qvel_column']]
    data.time=row['time_s'];mujoco.mj_forward(model,data)


def namespace(task, design):
    definition=task['definition']
    return SimpleNamespace(task=SimpleNamespace(family=definition['family'],
        goal=SimpleNamespace(data=definition['goal']['data']),
        environment=SimpleNamespace(data=definition['environment']['data'])),
        robot=SimpleNamespace(structure=SimpleNamespace(data=design)))


def compare(original, fresh):
    fields=('qpos_rad','qvel_rad_s','tip_m','tip_velocity_m_s','actual_tension_n','tip_tool_axis_world')
    errors={}
    if len(original)!=len(fresh):raise ValueError('CONTROL_SAMPLE_COUNT_MISMATCH')
    for key in fields:
        pairs=[(a[key],b[key]) for a,b in zip(original,fresh) if key in a and key in b]
        if pairs:errors[key]=float(max(np.max(np.abs(np.asarray(a)-b)) for a,b in pairs))
    errors['time_s']=max(abs(a['engine_time_s']-b['engine_time_s']) for a,b in zip(original,fresh))
    return errors


def compare_timestep(original, rows, mapping, period, timestep):
    results=[]
    for sample in original:
        row=rows[round(sample['time_s']/timestep)]
        pairs=dict(qpos_rad=[row[j['qpos_column']] for j in mapping['joints']],
            qvel_rad_s=[row[j['qvel_column']] for j in mapping['joints']],
            tip_m=[row['tip_position_m_'+a] for a in 'xyz'],
            tip_velocity_m_s=[row['tip_velocity_m_s_'+a] for a in 'xyz'],
            actual_tension_n=[row[c] for c in mapping['actual_tension_columns']],
            tip_tool_axis_world=[row['tool_axis_world_'+a] for a in 'xyz'],
            engine_time_s=row['time_s'])
        results.append(pairs)
    return compare(original,results)
