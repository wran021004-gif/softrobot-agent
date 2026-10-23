"""Explicit S135 two-execution development check, never run by test discovery.

prepare checks definitions/routes without stepping physics. Each named run can
create its Store only once. collect exports sealed evidence without rerunning.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import zipfile

from tools.research.config import ROOT, resolve
from tools.platform_tasks import compile_input
from tools.platform_host import Host
from tools.platform_store import plain
from tools.state_io import atomic_json, read
from tools.execution_completion import complete_execution
from tools.research_tasks import assemble_acceptance

OUT=ROOT/'evidence/s135_development'
RUNS=ROOT/'runs/s135_development'


def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    base=resolve(ROOT/'configs/research/study.json')['configuration']
    checks={}
    for kind in ('reach','tracking'):
        cfg=deepcopy(base);cfg['run_id']='s135-development-'+kind
        if kind=='tracking':
            initial=cfg['task']['initializer']
            cfg['task']=read(ROOT/'tasks/tracking_linear_development.json')['task']
            cfg['task'].update(status='development_valid',initializer=initial,
                source='S135 user-authorized development review of S132 path, SI world coordinates, evaluator and acquisition grid; no formal approval')
            cfg['seed']=cfg['task']['sampling']['seeds'][0]
            cfg['policy']['backend']['version']='1.2.0'
            cfg['policy']['controller']['version']='12.0.0'
            control=cfg['policy']['controller']['parameters']['data']
            control['settling']=None
            control['recipe'].update(reference_mode='free_progress',velocity_weight=0.,
                terminal_velocity_weight=0.,terminal_tip_speed_weight=0.,holding_tip_speed_weight=0.,
                path_lookahead_m=.003,path_capture_m=.001,progress_weight=.1,regression_weight=1.)
        bindings={name:'1.0.0' for name in ('simulation.run','evaluation.run','control.profile_report')}
        cfg['policy'].update(allowed_tools=[],tool_bindings=bindings,
            operation_allowances={name:dict(timeout_s=None,reserve_s=None) for name in bindings},
            budget=dict(model_calls=0,tool_calls=3,backend_solves=1,worker_calls=0,wall_s=None),timeout_s=None)
        path=OUT/(kind+'_input.json')
        if path.exists():
            if read(path)!=cfg:raise ValueError('Preserve original S135 development input')
        else:atomic_json(path,cfg)
        checks[kind]=compile_input(cfg)['approval']
    atomic_json(OUT/'review.json',dict(authorization='S135 user attachment: at most one Reach and one Tracking development execution',
        task_review='Original S132 draft retained. Copy has named zero initial state for this existing candidate; geometry, tolerances, reference ordering and time-free semantics unchanged.',
        approval=checks,provider_calls=0,ppo_training=False,formal_study=False))
    print(json.dumps(checks))


def run(kind):
    cfg=read(OUT/(kind+'_input.json'))
    folder=RUNS/kind
    if folder.exists():raise ValueError('S135 run already attempted; collect/inspect it, never automatically replay')
    from schemas.platform import ProjectConfig
    host=Host(folder,cfg['run_id'])
    host.store.create(ProjectConfig(project_id=cfg['run_id'],grant_id=cfg['run_id'],
        authorization_source='S135 explicit user authorization: one development execution per task; zero provider calls',
        budget=cfg['policy']['budget']))
    host.create(cfg)
    outcome=complete_execution(host,cfg,'s135-'+kind)
    atomic_json(folder/'outcome.json',outcome)
    collect(kind)


def collect(kind):
    cfg=read(OUT/(kind+'_input.json'));folder=RUNS/kind
    host=Host(folder,cfg['run_id'])
    outcome=read(folder/'outcome.json')
    summary=dict(kind=kind,status=outcome['status'],store=str(folder),provider_calls=0,
        receipts=outcome.get('receipts'),usage=host.store.remaining(cfg['run_id']))
    if outcome['status']=='evaluated':
        evaluation=outcome['evaluation_data']
        profile=host.store.artifact(outcome['receipts']['profile']['output'])['detail']
        acceptance=assemble_acceptance(cfg,evaluation,profile,
            evaluation_reference=outcome['receipts']['evaluation']['output'],
            profile_reference=outcome['receipts']['profile']['output'])
        summary.update(acceptance=acceptance,control_updates=profile['updates'],accepted_plans=profile['accepted_plans'],
            raw_solver_statuses=profile['raw_termination_counts'],complete=profile['complete'],
            solver_errors=profile['solver_error_count'],tension_range_n=profile['tension_range_n'],
            force_bound_violation_n=profile['force_bound_violation_n'],simulation_wall_s=profile['simulation_wall_s'])
        from extensions.tendon_family.control_evidence import ControlEvidence
        source=ControlEvidence(host.store).resolve(outcome['execution_id'])
        with zipfile.ZipFile(OUT/(kind+'_evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
            for name,ref in source['files'].items():archive.writestr(name,host.store.artifact(ref,raw=True))
            for name,value in dict(configuration=cfg,outcome=outcome,profile=profile,evaluation=evaluation,acceptance=acceptance,
                manifest=host.store.artifact(source['manifest'])).items():
                archive.writestr(name+'.json',json.dumps(plain(value),ensure_ascii=False,indent=2))
    atomic_json(OUT/(kind+'_summary.json'),summary)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','reach','tracking','collect'])
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='collect':
        for kind in ('reach','tracking'):collect(kind)
    else:run(args.action)
