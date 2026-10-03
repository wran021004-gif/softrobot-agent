"""Bounded Milestone 0: saved-data continuation and exactly two fresh workflows."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from tools.state_io import read,atomic_json
from tools.platform_store import Store,encode
from tools.platform_host import Host
from tools.improvement_workflow import execution_host,archive_store
from tools.execution_completion import complete_execution,import_completed_simulation
from tools.settling_campaign import SettlingWorkflow
from tools.runtime_identity import require_softagent_runtime
from extensions.tendon_family.control_evidence import ControlEvidence
from examples.stage352_settling_campaign import verify_baseline
from examples.stage351_settling_campaign import frozen_implementation,capability_gate
from examples.stage350_delivery_audit import audit_run,export_closure

CONFIG=ROOT/'examples/stage353_experiment.json'
EXTRA=['schemas/platform.py','tools/execution_completion.py','tools/platform_tools.py',
       'extensions/tendon_family/gvs_reporting.py','examples/stage353_milestone0.py',
       'examples/stage353_experiment.json','tests/test_stage353_completion.py']
POSTHOC_LIMITS=dict(model_calls=0,tool_calls=4,wall_s=120.,backend_solves=0,worker_calls=0)


def implementation():
    value=frozen_implementation()
    value['files'].update({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in EXTRA})
    return value


def posthoc(config):
    directory=Path(config['run_directory'])/'posthoc';export=Path(config['evidence_directory'])/'posthoc'
    original=Store(config['historical_store']);source=ControlEvidence(original).resolve(config['historical_execution'])
    store=Store(directory);run_id='gvs-stage353-posthoc'
    if not store.db.exists():
        store.create(dict(project_id=run_id,grant_id=run_id,budget=POSTHOC_LIMITS,authorization_source=config['authorization_source']))
        host=execution_host(store,run_id,source['configuration'],POSTHOC_LIMITS,operation_allowances=config['operation_allowances'])
    else:host=Host(directory,run_id,actor='improvement-executor')
    imported=import_completed_simulation(host,original,source['execution_id'])
    result=complete_execution(host,source['configuration'],source['metadata']['candidate'])
    outcome=dict(status=result['status'],classification='Post-hoc evaluation of a previously completed Stage 3.52 simulation.',
        historical_scheduled_evaluation_completed=False,stage352_matched_comparison_completed=False,
        source_store=str(original.root),source_manifest=source['manifest'],provenance=imported,result=result,usage=store.remaining())
    atomic_json(directory/'outcome.json',outcome)
    export_closure(directory,export,[original.root,Path(config['source_store'])])
    print('POSTHOC',json.dumps(result.get('structured_feedback',result)),flush=True)
    return outcome


def verify(config):
    command=[sys.executable,'-m','unittest','tests.test_stage350_improvement','tests.test_stage351_settling',
             'tests.test_stage352_context','tests.test_stage353_completion']
    started=time.monotonic();result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    record=dict(status='passed' if result.returncode==0 else 'failed',command=command,elapsed_s=time.monotonic()-started,
        output=result.stdout+result.stderr,implementation_files=implementation()['files'])
    atomic_json(Path(config['evidence_directory'])/'focused_check.json',record)
    print(record['output'],flush=True)
    if result.returncode:raise ValueError('FOCUSED_CHECK_FAILED')


def live(config,mode,credential):
    export=Path(config['evidence_directory']);current=implementation()
    marker=read(export/'focused_check.json')
    if marker['status']!='passed' or marker['implementation_files']!=current['files']:raise ValueError('FOCUSED_CHECK_REQUIRED')
    frozen=export/'live_freeze.json'
    if frozen.exists():
        if read(frozen)['implementation']!=current:raise ValueError('FROZEN_IMPLEMENTATION_CHANGED')
    else:
        dirty=subprocess.check_output(['git','diff','HEAD','--',*current['files']],cwd=ROOT,text=True)
        if dirty:raise ValueError('COMMIT_IMPLEMENTATION_BEFORE_LIVE')
        atomic_json(frozen,dict(implementation=current,configuration=config,runtime=require_softagent_runtime()))
    verified=verify_baseline(config)
    if not (export/'baseline_verification.json').exists():
        atomic_json(export/'baseline_verification.json',dict(execution_id=config['execution_id'],hashes=verified['artifact_hashes'],
            historical_usage=verified['historical_usage'],new_backend_executions=0))
    directory=Path(config['run_directory'])/mode
    resume_preparation=directory.exists()
    if resume_preparation:
        with Store(directory).connect(True) as db:
            if db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]:raise ValueError('PRESERVE_EXISTING_RUN: use its saved work; no replacement launch')
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(credential)
    experiment={**config,'source_manifest':verified['source']['manifest'],'baseline_facts':verified['result']['factual_result']}
    workflow=SettlingWorkflow(directory,mode,experiment=experiment)
    workflow.prepare(require_softagent_runtime(),resume_preparation=resume_preparation);outcome=workflow.run()
    export_closure(directory,export/mode,[Path(config['source_store'])])
    audit=audit_run(directory);audit['acceptance']=capability_gate(directory)
    audit['request_sizes']=[]
    with workflow.store.connect(True) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')]
    for run in ids:
        for e in workflow.store.events(run):
            if e['kind']=='model_request':
                payload=workflow.store.artifact(e['inputs'][0]);size=len(encode(payload).encode('utf8'))
                audit['request_sizes'].append(dict(request_id=e['request_id'],run_id=run,bytes=size,
                    estimated_input_tokens_upper=size+8192,output_headroom=payload['max_tokens']))
    atomic_json(export/(mode+'_audit.json'),audit)
    print('LIVE_ACCEPTANCE',mode,audit['acceptance'],flush=True)
    return outcome


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['posthoc','verify','single_context','dual_context'])
    parser.add_argument('--credential',type=Path,default=Path.home()/'.codex/.env')
    args=parser.parse_args();require_softagent_runtime();config=read(CONFIG)
    if args.action=='posthoc':posthoc(config)
    elif args.action=='verify':verify(config)
    else:live(config,args.action,args.credential)


if __name__=='__main__':main()
