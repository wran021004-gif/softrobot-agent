"""Single baseline replay and two bounded, fresh improvement organizations."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.state_io import read,atomic_json
from tools.platform_store import Store
from tools.diagnostic_workflow import implementation
from tools.improvement_workflow import ImprovementWorkflow, execution_host, archive_store, BASELINE_LIMITS, MODE_LIMITS
from tools.diagnostic_improvement import complete_execution
from extensions.tendon_family.control_evidence import ControlEvidence

CONFIG=ROOT/'examples/stage350_experiment.json'
BASE=ROOT/'runs/stage350_physical_pilot_20261003'
EXPORT=ROOT/'evidence/stage350_physical_pilot_20261003'
EXTRA_FILES=['tools/improvement_workflow.py','examples/stage350_physical_pilot.py','tests/test_stage350_improvement.py','examples/stage350_experiment.json']


def physical_implementation():
    value=implementation()
    value['files'].update({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in EXTRA_FILES})
    return value


def usage(config):
    historical=read(Path(config['evidence_directory'])/'workload_usage.json')['used']
    rows=[]
    for path in sorted(BASE.glob('*/platform.sqlite')):
        s=Store(path.parent);rows.append(dict(label=path.parent.name,**s.remaining()))
    used={k:historical[k]+sum(r['used'][k] for r in rows) for k in historical}
    assert all(used[k]<=config['overall_stage_limits'][k] for k in used)
    physical={k:sum(r['used'][k] for r in rows) for k in used}
    assert all(physical[k]<=config['physical_campaign_limits'][k] for k in physical)
    result=dict(diagnostic_used=historical,physical_runs=rows,physical_used=physical,used=used,
        limits=config['overall_stage_limits'],remaining={k:config['overall_stage_limits'][k]-used[k] for k in used},monetary_cost=None)
    atomic_json(EXPORT/'cumulative_usage.json',result)
    return result


def baseline(config,runtime,freeze):
    directory=BASE/'baseline';outpath=directory/'outcome.json'
    if outpath.exists():return read(outpath)
    if (directory/'live_attempt.json').exists() or (directory/'platform.sqlite').exists():
        raise ValueError('BASELINE_ALREADY_STARTED_WITHOUT_TERMINAL_OUTCOME: inspect sealed receipts; no repeated execution')
    source=ControlEvidence(Store(config['source_store'])).resolve(config['execution_id'])
    if source['manifest']!=config['source_manifest']:raise ValueError('SOURCE_MANIFEST_CHANGED')
    s=Store(directory);s.create(dict(project_id='gvs-stage350-baseline',grant_id='gvs-stage350-baseline',
        budget=BASELINE_LIMITS,authorization_source=config['authorization_source']))
    host=execution_host(s,'gvs-stage350-baseline-executor',source['configuration'],BASELINE_LIMITS)
    atomic_json(directory/'freeze.json',dict(campaign=freeze,runtime=runtime,source_manifest=source['manifest'],
        effective_input=s.session(host.run_id)['snapshot']['input']))
    atomic_json(directory/'live_attempt.json',dict(started=datetime.now(timezone.utc).isoformat()))
    try:
        result=complete_execution(host,source['configuration'],'baseline-replay')
        gate=result['status']=='evaluated' and result['evaluation_data']['validity']=='valid' and bool(result['factual_result']) and result['factual_result']['valid_complete_execution']
        reason='Consistent valid complete baseline and fixed evaluation/profile; task acceptance is not a launch requirement.' if gate else 'Baseline lacks a consistent valid complete execution/evaluation.'
    except Exception as exc:
        result=dict(status='incomplete',error=str(exc));gate=False;reason=str(exc)
    outcome=dict(status='completed' if gate else 'incomplete',gate_passed=gate,gate_reason=reason,
        result=result,usage=s.remaining(),provider_usage=[],runtime=runtime)
    atomic_json(outpath,outcome)
    destination=EXPORT/'baseline'
    for path in directory.glob('*.json'):atomic_json(destination/path.name,read(path))
    archive_store(s,destination);usage(config)
    print('BASELINE',outcome['status'],'USAGE',outcome['usage']['used'],flush=True)
    return outcome


def main(action,credential):
    config=read(CONFIG)
    if read(Path(config['evidence_directory'])/'diagnostic_comparison_delivery.json')['status']!='delivered':raise ValueError('DIAGNOSTIC_COMPARISON_DELIVERY_REQUIRED')
    from tools.runtime_identity import require_softagent_runtime
    runtime=require_softagent_runtime()
    marker=read(EXPORT/'focused_check.json')
    if marker['status']!='passed' or marker['implementation_files']!=physical_implementation()['files']:raise ValueError('FOCUSED_INTEGRATION_CHECK_REQUIRED')
    freeze_path=EXPORT/'campaign_freeze.json'
    if freeze_path.exists():
        freeze=read(freeze_path)
        if freeze['implementation']['files']!=physical_implementation()['files']:raise ValueError('PHYSICAL_IMPLEMENTATION_CHANGED')
    else:
        freeze=dict(implementation=physical_implementation(),runtime=runtime,source_store=config['source_store'],source_execution=config['execution_id'],
            source_manifest=config['source_manifest'],provider=read(config['provider_freeze'])['provider_configuration'],
            order=['baseline','single_context','dual_context'],limits=dict(baseline=BASELINE_LIMITS,organization=MODE_LIMITS),
            stage_limits=config['overall_stage_limits'],physical_limits=config['physical_campaign_limits'],
            baseline_gate='Valid complete execution, valid evaluation, consistent source/execution/profile identities. Task success is not required.',
            instructions=ImprovementWorkflow.instructions,phases=ImprovementWorkflow.phases,permissions=ImprovementWorkflow.permissions,
            tool_bindings=ImprovementWorkflow.tools,scope='Original three geometry variables only, zero control parameters, one candidate per organization.',
            comparison='Fresh independent memories; identical replayed baseline. No cross-mode conclusions. Integration pilot, not organizational superiority.',
            focused_check=marker,diagnostic_freeze=read(Path(config['evidence_directory'])/'paired_freeze.json')['implementation'])
        atomic_json(freeze_path,freeze)
    usage(config)
    original=baseline(config,runtime,freeze)
    if action=='baseline' or not original['gate_passed']:return original
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(credential)
    replay=ControlEvidence(Store(BASE/'baseline')).resolve(original['result']['execution_id'])
    experiment={**config,'project_prefix':'gvs-stage350-physical','source_store':str(BASE/'baseline'),
        'execution_id':original['result']['execution_id'],'source_manifest':replay['manifest'],'evidence_directory':str(EXPORT),
        'baseline_facts':original['result']['factual_result']}
    outcomes=[]
    for mode in ('single_context','dual_context'):
        directory=BASE/mode
        if (directory/'outcome.json').exists():outcomes.append(read(directory/'outcome.json'));continue
        if directory.exists():raise ValueError('EXISTING_MODE_REQUIRES_RECEIPT_INSPECTION: '+mode)
        if physical_implementation()['files']!=freeze['implementation']['files']:raise ValueError('PHYSICAL_IMPLEMENTATION_CHANGED')
        capacity=usage(config)['remaining']
        if any(capacity[k]<v for k,v in MODE_LIMITS.items()):raise ValueError('STAGE_CAPACITY_INSUFFICIENT')
        workflow=ImprovementWorkflow(directory,mode,experiment=experiment);workflow.prepare(runtime)
        outcomes.append(workflow.run());usage(config)
    atomic_json(EXPORT/'pilot_outcomes.json',outcomes)
    return outcomes


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['baseline','campaign'])
    parser.add_argument('--credential',type=Path,required=True);args=parser.parse_args()
    main(args.action,args.credential)
