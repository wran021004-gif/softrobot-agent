"""Fresh bounded activity; direct CLI and typed Host operations share service."""
from pathlib import Path
import argparse
import json
import subprocess
import time
from schemas.platform import ProjectConfig
from tools.platform_host import Host
from tools.platform_store import plain, zero
from tools.research_execution import invoke
from tools.state_io import atomic_json, read, digest
from tools.spec_tools import ROOT

ACTIVITY='casadi-codesign-pilot-20261010'
RUN=ROOT/'runs'/ACTIVITY
OUT=ROOT/'evidence/casadi_codesign_pilot_20261010'
LIMITS=dict(model_calls=4,tool_calls=32,backend_solves=2,worker_calls=0,wall_s=28800.)
TOOLS={name:'1.0.0' for name in ('math.casadi_codesign_check','math.casadi_codesign_solve','math.casadi_codesign_replay','evidence.read','simulation.run')}


def configuration():
    from tools.research_v2 import native_configuration
    from tools.design_optimization import resolved_input
    from schemas.design_optimization import DesignOptimizationProblem
    spec=read(ROOT/'examples/casadi_codesign/case_A.json')
    source=DesignOptimizationProblem.model_validate(spec['physical_source'])
    base=native_configuration(ACTIVITY)
    base['policy'].update(budget=LIMITS,allowed_tools=[],tool_bindings=TOOLS,
        operation_allowances={name:dict(timeout_s=1900.,reserve_s=30.) for name in TOOLS})
    base['policy']['model'].update(max_turns=4)
    values=dict(segment_count=2,proximal_tendons=3,distal_tendons=3,lengths_m=[.16,.11],
        material='baseline',section_scale=1.,routing_scale=1.,pretension_n=.2,
        holding_tip_speed_weight=.05,terminal_tip_speed_weight=.1)
    return resolved_input(source,values,ACTIVITY,base['policy'])


def host():return Host(RUN,ACTIVITY,actor='casadi-codesign-pilot')


def prepare():
    h=host()
    if h.store.db.exists():return h
    started=time.time()
    h.store.create(ProjectConfig(project_id=ACTIVITY,grant_id=ACTIVITY+'-authorized',
        authorization_source='User /goal attachment d6a7ef09-42d6-417e-aef8-818a2524f472/pasted-text-1.txt',
        budget=LIMITS,exclusive_resources={'provider_request':1,'backend.family_mujoco':1}))
    h.create(configuration());h.resume()
    with h.store.transaction() as db:
        state=h.store.session(ACTIVITY,db)['state']
        state.update(casadi_started_unix=started,casadi_cutoff_unix=started+27000.,casadi_numerical_s=0.,
            casadi_python='D:/softrobot-agent/.mainline5-env/Scripts/python.exe',casadi_solves=0,
            casadi_solve_categories=dict(primary=0,paired_second=0,correction=0))
        h.store.update_state(db,ACTIVITY,state)
    atomic_json(RUN/'activity.json',dict(activity_id=ACTIVITY,started_unix=started,limits=LIMITS,
        numerical_limit_s=7200.,delivery_reserve_s=1800.,primary_solves=2,paired_second_solves=2,correction_solves=2,
        max_nlp_total=6,nlp_solve_limit_s=600.,physical_launch_limit=2,physical_launch_limit_s=1800.,
        base_commit='34307384307158dba899ad2499a8b3e582f8356e',historical_activities='sealed STOP; grants never reopened'))
    return h


def bind(h):
    from tools.platform_tasks import compile_input
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('COMMIT_BEFORE_BIND')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]:raise ValueError('BIND_REQUIRES_ZERO_CALLS')
    old=h.store.session(ACTIVITY)['snapshot'];snapshot=compile_input(old['input'],h.reg)
    if snapshot['instance_identity']!=old['instance_identity']:raise ValueError('BIND_CHANGED_SCIENCE')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    snapshot.update(project_commit=commit,worktree_dirty=False)
    with h.store.transaction() as db:
        ref=h.store.put(db,snapshot);db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(ref.artifact_id,ACTIVITY))
        state=h.store.session(ACTIVITY,db)['state'];state['casadi_freeze']=commit
        h.store.update_state(db,ACTIVITY,state);h.store.event(db,ACTIVITY,'implementation_freeze','committed',outputs=[ref])
    atomic_json(RUN/'implementation_freeze.json',dict(commit=commit,dependencies=snapshot['dependencies']))


def export(h):
    import tarfile,io,hashlib
    OUT.mkdir(parents=True,exist_ok=True);manifest=[]
    with h.store.connect(True) as db,tarfile.open(OUT/'immutable_artifacts.tar.gz','w:gz') as tar:
        for row in db.execute('SELECT id,media,body FROM artifacts ORDER BY id'):
            name='artifacts/'+row['id']+('.json' if row['media']=='application/json' else '.bin')
            info=tarfile.TarInfo(name);info.size=len(row['body'])
            tar.addfile(info,io.BytesIO(row['body']));manifest.append(dict(name=name,sha256=row['id'],bytes=info.size,media=row['media']))
        calls=[dict(row) for row in db.execute('SELECT * FROM calls ORDER BY rowid')]
    for filename,value in [('activity.json',read(RUN/'activity.json')),('implementation_freeze.json',read(RUN/'implementation_freeze.json')),
        ('state.json',h.store.session(ACTIVITY)['state']),('events.json',h.store.events(ACTIVITY)),('ledger.json',h.store.remaining()),('calls.json',calls)]:
        atomic_json(OUT/filename,value)
    state=h.store.session(ACTIVITY)['state']
    for i,row in enumerate(state.get('casadi_results',[])):
        value=h.store.artifact(row['reference']);atomic_json(OUT/f'{i:02d}_{row["operation"]}_{row["case"] or "check"}.json',value)
    atomic_json(OUT/'archive_manifest.json',dict(members=manifest,archive_sha256=hashlib.sha256((OUT/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()))
    return dict(artifacts=len(manifest),numerical_s=state['casadi_numerical_s'],solves=state['casadi_solves'],ledger=h.store.remaining())


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','bind','check','solve','replay','status','export','stop'])
    p.add_argument('--case',choices=['A','B'],default='A');p.add_argument('--initialization',default='pretension_0_2',choices=['pretension_0_2','ramp_0_2_to_0_4'])
    p.add_argument('--category',default='primary',choices=['primary','paired_second','correction']);p.add_argument('--substeps',type=int,default=1)
    p.add_argument('--candidate');p.add_argument('--request-id');args=p.parse_args()
    h=prepare() if args.command=='prepare' else host()
    if args.command=='bind':bind(h)
    if args.command in ('check','solve','replay'):
        arguments={} if args.command=='check' else dict(case=args.case,initialization=args.initialization,category=args.category,substeps=args.substeps) if args.command=='solve' else dict(candidate=json.loads(args.candidate))
        receipt=invoke(h,'math.casadi_codesign_'+args.command,arguments,request_id=args.request_id or f'{args.command}-{args.case}-{args.initialization}-{args.category}-{args.substeps}')
        print(json.dumps(dict(receipt=receipt,feedback=h.store.artifact(receipt['output']) if receipt.get('output') else None)));return
    if args.command=='export':print(json.dumps(export(h)));return
    if args.command=='stop':
        state=h.store.session(ACTIVITY)['state'];elapsed=time.time()-state['casadi_started_unix']
        engineering=max(0.,elapsed-h.store.remaining()['used']['wall_s'])
        row,fresh=h.store.reserve(ACTIVITY,'engineering-closeout',digest({'started':state['casadi_started_unix']}),h.actor,{**zero(),'wall_s':engineering},kind='engineering')
        if fresh:h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=h.actor,
            tool_id='engineering.casadi_codesign',tool_version='1.0.0',execution_status='completed',charged=zero()),dict(elapsed_activity_s=elapsed),elapsed=engineering)
        with h.store.transaction() as db:
            state=h.store.session(ACTIVITY,db)['state'];state['casadi_completed_unix']=time.time()
            h.store.update_state(db,ACTIVITY,state,'stopped');h.store.event(db,ACTIVITY,'casadi_pilot_completion','STOP')
    print(json.dumps(dict(status=h.store.session(ACTIVITY)['status'],ledger=h.store.remaining(),state=h.store.session(ACTIVITY)['state'])))


if __name__=='__main__':main()
