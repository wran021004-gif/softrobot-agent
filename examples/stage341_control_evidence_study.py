"""Bounded Stage 3.41 recording replay. Each expensive action has a durable one-shot guard."""
from __future__ import annotations
import argparse
from copy import deepcopy
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.platform_store import Store,plain
from tools.platform_host import Host
from tools.state_io import atomic_json,read,digest
from tools.runtime_identity import require_softagent_runtime
from extensions.tendon_family.control_evidence import ControlEvidence,EvidenceQuery,ExecutionComparison,RECORD_UPDATE_IDS

OUTPUT=ROOT/'runs/stage341_control_evidence_20261001'
SOURCE=ROOT/'runs/stage340_bounded_autonomous_20261001'
EXECUTION='f9b8c232a576465ab5ef1ca92658faad'


def invoke(host,tool,args,request):
    receipt=host.invoke(dict(request_id=request,tool_id=tool,tool_version='1.0.0',arguments=args,
        reason='Authorized fixed-design evidence study; no provider.',cache='new'))
    if receipt['execution_status']!='completed':raise RuntimeError(receipt)
    return receipt


def replay():
    runtime=require_softagent_runtime();OUTPUT.mkdir(parents=True,exist_ok=True)
    guard=OUTPUT/'recording_attempt.json'
    if guard.exists():raise RuntimeError('RECORDING_REPLAY_ALREADY_ATTEMPTED')
    reader=ControlEvidence(Store(SOURCE));source=reader.resolve(EXECUTION)
    baseline=plain(reader.query(EvidenceQuery(execution_id=EXECUTION,operation='prediction',update_ids=[0,4,34])))
    atomic_json(OUTPUT/'historical_inspection.json',baseline)
    inp=deepcopy(source['configuration']);run='gvs-stage341-recording-'+os.urandom(6).hex();inp['run_id']=run
    # Reporting also reserves timeout_s; leave room after the single rollout.
    # This declaration does not change any already-created grant or snapshot.
    budget=dict(model_calls=0,tool_calls=8,backend_solves=1,worker_calls=0,wall_s=2400.)
    inp['policy'].update(route=None,budget=budget,timeout_s=900.,allowed_tools=[],
        tool_bindings={k:'1.0.0' for k in ('simulation.run','evaluation.run','control.profile_report','control.inspect_evidence','evidence.read')})
    store=Store(OUTPUT/'recording')
    if store.db.exists():
        with store.connect(True) as db:
            if db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]:raise RuntimeError('EXISTING_RECORDING_SESSION')
        run=store.config()['project_id'];inp['run_id']=run
    else:
        store.create(dict(project_id=run,grant_id=run,budget=budget,
            authorization_source='User authorized one fixed Stage 3.40 design recording replay, Stage 3.41.'))
    host=Host(store.root,run);host.create(inp)
    atomic_json(guard,dict(run_id=run,classification='new recording replay, not historical reproduction',
        source_execution=EXECUTION,source_manifest=source['manifest'],runtime=runtime,
        record_update_ids=[0,4,34],scientific_changes=[],instrumentation='bounded existing solver trace and post-selection snapshots',
        warning='Instrumentation and finite-time stopping can change numerical behavior; no bitwise equivalence claim.',
        offline_total_limit_s=10800,local_solve_limit=4,local_preparation_solve_limit_s=1200))
    start=time.perf_counter();token=RECORD_UPDATE_IDS.set((0,4,34))
    try:sim=invoke(host,'simulation.run',dict(candidate_id='stage340-recording',changes={}),'recording-simulation')
    finally:RECORD_UPDATE_IDS.reset(token)
    ev=invoke(host,'evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']),'recording-evaluation')
    report=invoke(host,'control.profile_report',dict(simulation_request_id='recording-simulation',evaluation_request_id='recording-evaluation'),'recording-profile')
    current=ControlEvidence(store)
    query=plain(current.query(EvidenceQuery(execution_id=sim['execution_id'],operation='prediction',update_ids=[0,4,34])))
    atomic_json(OUTPUT/'recording_inspection.json',query)
    comparison=reader.compare(ExecutionComparison(baseline_execution_id=EXECUTION,variant_execution_id=sim['execution_id'],changed_factor='recording'),current)
    atomic_json(OUTPUT/'recording_comparison.json',comparison)
    atomic_json(OUTPUT/'recording_result.json',dict(run_id=run,simulation=sim,evaluation=store.artifact(ev['output']),
        profile=store.artifact(report['output']),elapsed_s=time.perf_counter()-start,usage=store.remaining(run)['used']))
    print('RECORDING_COMPLETE',sim['execution_id'],flush=True)


def validate():
    require_softagent_runtime()
    local=next((ROOT/'runs/control_comparisons').glob('*/result.json'))
    result=read(local)
    if not result['local_gate_passed']:raise ValueError('LOCAL_GATE_NOT_PASSED')
    guard=OUTPUT/'validation_attempt.json'
    if guard.exists():raise RuntimeError('FIXED_DESIGN_VALIDATION_ALREADY_ATTEMPTED')
    reader=ControlEvidence(Store(SOURCE));source=reader.resolve(EXECUTION)
    inp=deepcopy(source['configuration']);run='gvs-stage341-validation-'+os.urandom(6).hex();inp['run_id']=run
    inp['policy']['controller']['version']='7.0.0'
    budget=dict(model_calls=0,tool_calls=8,backend_solves=1,worker_calls=0,wall_s=2400.)
    inp['policy'].update(route=None,budget=budget,timeout_s=900.,allowed_tools=[],
        tool_bindings={k:'1.0.0' for k in ('simulation.run','evaluation.run','control.profile_report','control.inspect_evidence','evidence.read')})
    store=Store(OUTPUT/'validation');store.create(dict(project_id=run,grant_id=run,budget=budget,
        authorization_source='User authorized at most one fixed-design validation after the local gate, Stage 3.41.'))
    host=Host(store.root,run);host.create(inp)
    atomic_json(guard,dict(run_id=run,source_execution=EXECUTION,source_manifest=source['manifest'],
        local_gate_source=str(local.relative_to(ROOT)),changed_factor='controller horizon truncates at deadline, version 7.0.0',
        frozen_input=inp,acceptance=dict(valid_complete=True,terminal_error_improvement_m=.0005,
            force_violation_n=0.,solver_errors=0,settling_and_speed_reported_separately=True,
            unchanged_solve_budgets=True),instrumented_update_ids=[],elapsed_offline_before_s=420.25+read(ROOT/'runs/control_comparisons/usage.json')['wall_s']))
    start=time.perf_counter();sim=invoke(host,'simulation.run',dict(candidate_id='stage340-deadline-validation',changes={}),'validation-simulation')
    ev=invoke(host,'evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']),'validation-evaluation')
    report=invoke(host,'control.profile_report',dict(simulation_request_id='validation-simulation',evaluation_request_id='validation-evaluation'),'validation-profile')
    profile=store.artifact(report['output'])['detail']
    gate=bool(profile['valid_complete_execution'] and profile['force_bound_violation_n']==0 and profile['solver_error_count']==0
        and .018349652058180982-profile['terminal_error_m']>=.0005)
    atomic_json(OUTPUT/'validation_result.json',dict(run_id=run,simulation=sim,evaluation=store.artifact(ev['output']),
        profile=profile,adoption_gate_passed=gate,elapsed_s=time.perf_counter()-start,usage=store.remaining(run)['used']))
    comparison=reader.compare(ExecutionComparison(baseline_execution_id=EXECUTION,variant_execution_id=sim['execution_id'],changed_factor='controller'),ControlEvidence(store))
    atomic_json(OUTPUT/'validation_comparison.json',comparison)
    print('VALIDATION_COMPLETE',sim['execution_id'],'adoption_gate',gate,'error_m',profile['terminal_error_m'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['replay','validate']);args=parser.parse_args()
    replay() if args.action=='replay' else validate()
