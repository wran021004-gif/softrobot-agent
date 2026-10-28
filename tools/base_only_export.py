"""Export selected historical receipts; at most ten single-pass capture replays.

Read-only source Store and original XML. No study dispatch, optimization or new
acceptance. A durable exclusive ledger prevents a crashed export being rerun.
"""
import argparse
import ast
from contextlib import closing
from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
from types import SimpleNamespace
import xml.etree.ElementTree as ET

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'

import mujoco
import numpy as np
from tools.platform_store import Store
from tools.state_io import read,atomic_json,digest
from tools.base_only_audit import audit
from tools.research.physical_replay import binding
from extensions.tendon_family import backends
from tools import base_only_export_docs as docs

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from package_io import sha,joint_map,observation,csv_write,compare,compare_timestep
from validate_package import physical_fingerprint

KEYS=('M1','M2','M3','M4','M5','M6')
BASE_COMMIT='314f75a4971e0a9e4521fe79ddf744ff71de61e2'


def physical_xml_identity(path):
    root=ET.parse(path).getroot()
    for parent in root.iter():
        for child in list(parent):
            if child.tag=='site' and child.get('name')=='task_target':parent.remove(child)
    import hashlib
    return hashlib.sha256(ET.tostring(root,encoding='utf8')).hexdigest()


def source_snapshot(owner):
    return {p.relative_to(owner).as_posix():sha(p) for key in KEYS for p in
        [owner/key/'private-store/platform.sqlite',owner/key/'index.json',owner/key/'review_manifest.json']}


def preflight(owner):
    """Use original audit without Host.prepare or manifest writes."""
    prepared=[];before=source_snapshot(owner)
    for key in KEYS:
        store=Store(owner/key/'private-store')
        with closing(store.connect(True)) as db:
            sessions=list(db.execute('SELECT run_id FROM sessions'))
        if len(sessions)!=1:raise ValueError('ONE_OWNING_STUDY_REQUIRED')
        host=SimpleNamespace(store=store,run_id=sessions[0][0]);manifest=read(owner/key/'review_manifest.json')
        report=audit(key,host=host,owner=owner,write_manifest=False)
        if report['private_review_manifest_identity']!=digest(manifest):raise ValueError('REVIEW_MANIFEST_CHANGED')
        for record in manifest['selected_records']:
            result=store.artifact(record['reference']);candidate=store.artifact(record['candidate'])
            cfg=candidate['configuration'];source=store.artifact(record['source'])
            raw=store.artifact(record['raw']);evaluation=store.artifact(record['evaluation']);profile=store.artifact(record['profile'])
            if not (result['acceptance']==record['acceptance'] and result['acceptance']['accepted']
                and raw['candidate']==result['candidate']==record['candidate']
                and raw['source_reference']==result['source_reference']==record['source']
                and result['raw_reference']==record['raw'] and evaluation['source']==record['raw']
                and result['evaluation_reference']==record['evaluation']==profile['evaluation']
                and result['profile_reference']==record['profile'] and profile['simulation']==record['raw']
                and profile['execution_id']==result['execution_id']==record['receipt']['execution_id']
                and profile['task']==cfg['task']):raise ValueError('ACCEPTED_EVIDENCE_BINDING_CHANGED')
            inp,physics,scene=binding(cfg,source['trajectory'])
            if raw['task_identity']!=digest(cfg['task']) or raw['model_identity']!=physics['identity'] or raw['scene_identity']!=scene['identity']:
                raise ValueError('RAW_CONFIGURATION_IDENTITY_MISMATCH')
            xml=store.root/'physical_replay'/result['execution_id']/'robot.xml'
            if sha(xml)!=raw['xml_sha256']:raise ValueError('ORIGINAL_ACCEPTED_XML_CHANGED')
            model=mujoco.MjModel.from_xml_path(str(xml));mapping=joint_map(model,physics['dofs'])
            if mapping['tendon_order']!=source['trajectory']['tendon_order']:raise ValueError('COMPILED_TENDON_ORDER')
            if raw['physics_steps']!=round(scene['duration_s']/model.opt.timestep):raise ValueError('INCOMPLETE_ORIGINAL')
            if len(raw['samples'])!=round(scene['duration_s']/scene['control_period_s'])+1:raise ValueError('ORIGINAL_GRID')
            prepared.append(dict(key=key,condition=record['condition'] or 'default',store=store,record=record,
                result=result,candidate=candidate,cfg=cfg,source=source,raw=raw,evaluation=evaluation,profile=profile,
                inp=inp,physics=physics,scene=scene,xml=xml,mapping=mapping,
                compiled_physical_identity=physical_fingerprint(model),
                source_model_dimensions=dict(nq=model.nq,nv=model.nv,nbody=model.nbody,ntendon=model.ntendon,nu=model.nu),
                original_xml_sha256=sha(xml)))
            prepared[-1]['physical_xml_identity']=physical_xml_identity(xml)
        entries=[v for v in prepared if v['key']==key]
        if len({v['compiled_physical_identity'] for v in entries})!=1:raise ValueError('CONDITIONS_DIFFER_PHYSICALLY')
        if len({v['physical_xml_identity'] for v in entries})!=1:raise ValueError('XML_DIFFERS_BEYOND_TARGET_MARKER')
    if len(prepared)!=10 or sum(v['raw']['physics_steps'] for v in prepared)!=6700:raise ValueError('EXPORT_GRANT_SCOPE')
    if source_snapshot(owner)!=before:raise ValueError('SOURCE_CHANGED_DURING_AUDIT')
    return prepared,before


def portable_kernel():
    """Extract the ONE authoritative loop; strip only framework compilation imports.

    The exported module always receives the archived XML, so it never compiles.
    All integration, force, sample and contact logic is verbatim AST from backends.
    """
    names=('check_rigid_tool_definition','check_rigid_tool_model','_mujoco_state_failed',
        '_bind_mujoco_forces','_apply_mujoco_forces','MujocoFailureSnapshot','playback_tensions')
    nodes=[]
    for name in names:
        node=ast.parse(inspect.getsource(getattr(backends,name))).body[0]
        if name=='playback_tensions':
            node.body=[n for n in node.body if not (isinstance(n,ast.ImportFrom) and
                n.module in ('mjcf','tools.platform_registry'))]
            for n in node.body:
                if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='xml' for t in n.targets):
                    n.value=ast.parse('Path(xml_path)',mode='eval').body
        nodes.append(node)
    header='''"""Generated from the research backend: original fixed-tension replay semantics.
Only XML compilation/imports are removed; archived XML is mandatory.
"""
import hashlib
import time
from pathlib import Path
import numpy as np
from package_io import write as atomic_json
'''
    return header+'\n\n'.join(ast.unparse(ast.fix_missing_locations(n)) for n in nodes)+'\n'


def structure(v):
    p=v['physics'];cfg=v['cfg'];design=cfg['robot']['structure']['data']
    resolved=[]
    for tendon in p['tendons']:
        t=deepcopy(tendon)
        for point in t['points']:
            point['body_name']='fixed_base' if point['body']<0 else p['parts'][point['body']]['entity']
        resolved.append(t)
    tip=deepcopy(p['tip']);tip['body_name']='fixed_base' if tip['body']<0 else p['parts'][tip['body']]['entity']
    return dict(version='base_only_structure_v1',design=design,design_identity=digest(design),
        physical_design_identity=p['design_identity'],configuration_identity=digest(cfg),
        discretization=p['discretization'],discretization_identity=p['discretization_identity'],
        resolved_physics=p,resolved_tendons=resolved,tip_site=tip,
        base_world_pose=cfg['task']['environment']['data']['mount'],
        tool_axis_local=cfg['task']['goal']['data'].get('axis_local',[1.,0.,0.]),
        joint_order=p['dofs'],tendon_order=v['mapping']['tendon_order'],actuator_order=v['mapping']['actuator_order'],
        xml_sha256=v['original_xml_sha256'],compiled_physical_identity=v['compiled_physical_identity'],
        units='SI',interpretation=docs.LIMITATIONS)


def task_data(v):
    d=v['cfg']['task'];a=v['record']['acceptance'];period=d['timing']['sample_period_s'];duration=d['timing']['duration_s']
    window=v['profile'].get('sampled_settling',{}).get('window_s')
    margins={k:dict(value=c['value'],limit=c['limit'],unit=c['unit'],margin=c['limit']-c['value'])
        for k,c in a['components'].items() if type(c['value']) in (int,float) and type(c['limit']) in (int,float)}
    return dict(version='base_only_task_export_v1',benchmark=v['key'],condition=v['condition'],
        definition=d,task_identity=digest(d),historical_acceptance=a,acceptance_margins=margins,
        holding_window_s=None if window is None else [duration-window,duration],
        evaluator_sample_times_s=[i*period for i in range(1,round(duration/period)+1)],
        task_sampling_window_s=d['sampling']['window_s'],
        tool_axis_local=d['goal']['data'].get('axis_local',[1.,0.,0.]),
        simulation_limits=docs.LIMITATIONS,
        development_draft=v['key']=='M3')


def reference_rows(task):
    from extensions.reference.contracts import TrackingGoal,OrientedTrackingGoal
    d=task['definition'];goal=d['goal']['data'];timing=d['timing'];rows=[]
    tracking=(OrientedTrackingGoal.model_validate(goal) if d['family']=='task.oriented_tracking' else
        TrackingGoal.model_validate(goal) if d['family']=='task.tracking' else None)
    for i in range(round(timing['duration_s']/timing['timestep_s'])+1):
        t=i*timing['timestep_s'];p=tracking.at_time(t)[0] if tracking else goal['target_m']
        axis=(tracking.axis_at_time(t) if d['family']=='task.oriented_tracking' else goal.get('target_axis_world',[0.,0.,0.]))
        on_grid=i%round(timing['sample_period_s']/timing['timestep_s'])==0
        row=dict(time_s=t,evaluator_input_sample=int(i>0 and on_grid),
            task_window_sample=int(i>0 and on_grid and d['sampling']['window_s'][0]-1e-12<=t<=d['sampling']['window_s'][1]+1e-12),
            holding_window_sample=int(on_grid and task['holding_window_s'] is not None and t>=task['holding_window_s'][0]-1e-12),
            tool_axis_reference_defined=int('axis_local' in goal))
        for prefix,values in [('reference_position_m',p),('reference_tool_axis_world',axis)]:
            row.update({prefix+'_'+a:float(x) for a,x in zip('xyz',values)})
        rows.append(row)
    return rows


def static_export(output,prepared,environment):
    (output/'scripts').mkdir();(output/'evidence/artifacts').mkdir(parents=True)
    for path in (ROOT/'scripts').glob('*.py'):shutil.copy2(path,output/'scripts'/path.name)
    (output/'scripts/playback_kernel.py').write_text(portable_kernel(),encoding='utf8')
    (output/'requirements.txt').write_text(f"mujoco=={environment['mujoco']}\nnumpy=={environment['numpy']}\n",encoding='utf8')
    for key in KEYS:
        values=[v for v in prepared if v['key']==key];v=values[0];base=output/key;base.mkdir()
        shutil.copyfile(v['xml'],base/'robot.xml');s=structure(v)
        atomic_json(base/'structure.json',s);atomic_json(base/'joint_map.json',v['mapping'])
        (base/'structure.md').write_text(docs.structure_md(key,s),encoding='utf8')
        (base/'README.md').write_text(docs.benchmark_readme(key,[v['condition'] for v in values]),encoding='utf8')
        for v in values:
            folder=base/v['condition'];folder.mkdir();v['folder']=folder
            task=task_data(v);atomic_json(folder/'task.json',task)
            (folder/'task_zh.md').write_text(docs.task_zh(key,v['condition'],task),encoding='utf8')
            atomic_json(folder/'configuration.json',v['cfg'])
            atomic_json(folder/'replay_spec.json',dict(physics=v['physics'],scene=v['scene']))
            atomic_json(folder/'original_samples.json',v['raw']['samples'])
            for name in ('evaluation','profile'):
                atomic_json(folder/('original_'+name+'.json'),v[name])
            atomic_json(folder/'original_receipt.json',v['record']['receipt'])
            provenance=dict(benchmark=key,condition=v['condition'],research_commit=BASE_COMMIT,
                frozen_implementation=v['raw']['implementation'],references={k:v['record'][k] for k in
                ('reference','candidate','source','raw','evaluation','profile')},
                design_identity=digest(v['cfg']['robot']['structure']['data']),configuration_identity=digest(v['cfg']),
                task_identity=digest(v['cfg']['task']),source_trajectory_identity=digest(v['source']['trajectory']),
                mathematical_model_identity=v['source']['trajectory']['model_identity'],
                physics_identity=v['physics']['identity'],scene_identity=v['scene']['identity'],
                original_xml_sha256=v['original_xml_sha256'],package_xml_sha256=sha(base/'robot.xml'),
                compiled_physical_identity=v['compiled_physical_identity'],model_dimensions=v['source_model_dimensions'],
                physical_xml_identity=v['physical_xml_identity'],
                xml_sharing='Physical fingerprints match all original condition models; task_target visualization marker may differ.')
            atomic_json(folder/'provenance.json',provenance)
            for name in ('reference','candidate','source','raw','evaluation','profile'):
                ref=v['record'][name];body=v['store'].artifact(ref,raw=True)
                (output/'evidence/artifacts'/(ref['artifact_id']+'.json')).write_bytes(body)
            tr=v['source']['trajectory'];rows=[]
            for i,u in enumerate(tr['tensions_n']):
                row=dict(control_interval_index=i,start_s=tr['times_s'][i],end_s=tr['times_s'][i+1])
                row.update(dict(zip(v['mapping']['requested_tension_columns'],u)));rows.append(row)
            csv_write(folder/'control_schedule.csv',rows);csv_write(folder/'reference.csv',reference_rows(task))


def capture(v,ledger,ledger_path,environment):
    name=v['key']+'/'+v['condition'];entry=ledger['trajectories'][name]
    if entry['status']!='not_started':raise ValueError('NO_RELAUNCH_OF_RESERVED_OR_COMPLETED_TRAJECTORY')
    entry.update(status='reserved',reserved_steps=v['raw']['physics_steps']);atomic_json(ledger_path,ledger)
    folder=v['folder'];rows=[];bodies=sorted({f['entity'] for f in v['scene']['forces']})
    axis=v['cfg']['task']['goal']['data'].get('axis_local',[1.,0.,0.]);started=time.perf_counter()
    def observer(model,data,step,interval):
        if step>entry['reserved_steps']:raise ValueError('EXPORT_STEP_CAP')
        entry['confirmed_completed_steps']=step
        rows.append(observation(model,data,step,interval,v['mapping'],axis,bodies))
    try:
        raw=backends.playback_tensions(v['inp'],v['physics'],v['scene'],v['source']['trajectory']['tensions_n'],
            folder/'capture_diagnostics',step_observer=observer,xml_path=v['xml'])
    except BaseException as exc:
        entry.update(status='failed_no_retry',error=str(exc),elapsed_s=time.perf_counter()-started)
        atomic_json(ledger_path,ledger)
        if rows:csv_write(folder/'trajectory_timestep.csv',rows)
        raise
    csv_write(folder/'trajectory_timestep.csv',rows)
    atomic_json(folder/'export_control_samples.json',raw['samples'])
    periodic_errors=compare(v['raw']['samples'],raw['samples'])
    errors=compare_timestep(v['raw']['samples'],rows,v['mapping'],v['scene']['control_period_s'],v['scene']['timestep_s'])
    consistent=raw['status']=='completed' and max([*errors.values(),*periodic_errors.values()])<=1e-9
    entry.update(status='completed',actual_mj_step_calls=raw['physics_step_attempts'],
        elapsed_s=time.perf_counter()-started,original_sample_max_abs=periodic_errors,timestep_max_abs=errors)
    atomic_json(ledger_path,ledger)
    validation=dict(historical_acceptance=v['record']['acceptance'],
        historical_receipt_binding_verified=True,export_reproduction='consistent' if consistent else 'reproduction_unverified',
        tolerance=1e-9,control_sample_comparison_max_abs=periodic_errors,timestep_comparison_max_abs=errors,
        physics_steps=raw['physics_steps'],actual_mj_step_calls=raw['physics_step_attempts'],
        detached_forward_evaluations=len(rows),
        cost=raw['cost'],export_elapsed_s=entry['elapsed_s'],environment=environment,
        environment_contact=raw.get('environment_contact'),rigid_tool_binding=raw.get('rigid_tool_binding'),
        original_sample_count=len(v['raw']['samples']),timestep_rows=len(rows),
        explanation='No discrepancies.' if consistent else 'Keep historical acceptance; inspect raw diagnostics and environment, do not replay automatically.')
    atomic_json(folder/'validation.json',validation)
    return dict(benchmark=v['key'],condition=v['condition'],directory=folder.relative_to(folder.parents[1]).as_posix(),
        rows=len(rows),timestep_s=v['scene']['timestep_s'],duration_s=v['scene']['duration_s'],
        compiled_physical_identity=v['compiled_physical_identity'],reproduction=validation['export_reproduction'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--audit-only',action='store_true')
    args=p.parse_args();owner=args.source.resolve();output=args.output.resolve()
    if any((a/'.git').exists() for a in (output,*output.parents)):
        raise ValueError('OUTPUT_MUST_BE_OUTSIDE_ALL_GIT_CHECKOUTS')
    prepared,before=preflight(owner)
    if args.audit_only:
        print(json.dumps(dict(selected_trajectories=len(prepared),authorized_steps=6700,receipt_audit='passed',source_unchanged=True)));return
    # Fixed local ledger, independent of --output: a second destination cannot mint a new replay grant.
    ledger_path=ROOT/'runs/base-only-export-20261028/ledger.json';ledger_path.parent.mkdir(parents=True,exist_ok=True)
    lock=ledger_path.with_suffix('.lock')
    with lock.open('x',encoding='utf8') as stream:stream.write('One export grant; never delete to authorize a retry.\n')
    if ledger_path.exists():raise ValueError('EXISTING_EXPORT_LEDGER_NO_RELAUNCH')
    output.mkdir(parents=True,exist_ok=False)
    environment=dict(python=platform.python_version(),mujoco=mujoco.__version__,numpy=np.__version__,
        platform=platform.platform(),threads={n:os.environ[n] for n in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')})
    ledger=dict(version='base_only_export_grant_v1',step_cap=6700,output=str(output),
        trajectories={v['key']+'/'+v['condition']:dict(status='not_started') for v in prepared})
    atomic_json(ledger_path,ledger);static_export(output,prepared,environment)
    entries=[]
    for v in prepared:
        entries.append(capture(v,ledger,ledger_path,environment))
        print(json.dumps(dict(benchmark=v['key'],condition=v['condition'],status=entries[-1]['reproduction'],rows=entries[-1]['rows'])),flush=True)
    if source_snapshot(owner)!=before:raise ValueError('SOURCE_STORE_OR_MANIFEST_CHANGED')
    total=sum(e['actual_mj_step_calls'] for e in ledger['trajectories'].values())
    if total!=6700:raise ValueError('ACTUAL_EXPORT_STEP_COUNT')
    atomic_json(output/'export_audit.json',dict(environment=environment,research_commit=BASE_COMMIT,
        actual_mj_step_calls=total,trajectory_replays=10,optimization_calls=0,source_files_unchanged=True,
        detached_forward_evaluations=sum(e['rows'] for e in entries),
        source_file_sha256=before,trajectories=ledger['trajectories']))
    (output/'README.md').write_text(docs.root_readme(environment,entries),encoding='utf8')
    manifest=dict(version='base_only_package_v1',research_commit=BASE_COMMIT,environment=environment,
        actual_mj_step_calls=total,trajectories=entries,files={q.relative_to(output).as_posix():sha(q)
            for q in sorted(output.rglob('*')) if q.is_file() and '__pycache__' not in q.parts})
    atomic_json(output/'manifest.json',manifest)
    print(json.dumps(dict(output=str(output),actual_mj_step_calls=total,complete=True)))


if __name__=='__main__':main()
