"""Public frozen-input preparation/execution/report, one backend attempt per folder."""
import argparse
import json
import os
import sys
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ.setdefault(key,'1')
from extensions.tendon_family.gvs_profile import reach_input
from extensions.tendon_family.gvs_reporting import markdown
from tools.platform_store import Store
from tools.platform_host import Host
from tools.state_io import atomic_json


def call(host,tool,args,request):
    receipt=host.invoke(dict(request_id=request,tool_id=tool,arguments=args,cache='new',
        reason='Authorized deterministic task-parameterized free reach; no model calls'))
    atomic_json(host.store.root/(request+'_receipt.json'),receipt)
    if receipt['execution_status']!='completed':raise RuntimeError(json.dumps(receipt))
    return receipt,host.store.artifact(receipt['output'])


def prepare(root,input_path=None):
    if (root/'workflow.json').exists():
        state=json.loads((root/'workflow.json').read_text(encoding='utf8'))
        if input_path is not None:
            if json.loads(input_path.read_text(encoding='utf8'))!=json.loads((root/'input.json').read_text(encoding='utf8')):
                raise ValueError('FROZEN_SESSION_INPUT_CHANGED: use a fresh output folder')
        return Host(root,state['run_id'])
    inp=json.loads(input_path.read_text(encoding='utf8')) if input_path else reach_input('gvs-reach-'+uuid4().hex[:12])
    store=Store(root)
    store.create(dict(project_id=inp['run_id'],grant_id=inp['run_id'],
        authorization_source='User authorized one fixed-input free-space local execution in this project; no paid calls',
        budget=dict(tool_calls=12,model_calls=0,backend_solves=1,worker_calls=0,wall_s=5400.)))
    host=Host(root,inp['run_id']);host.create(inp)
    _,description=call(host,'control.profile_describe',{},'describe')
    atomic_json(root/'input.json',inp)
    atomic_json(root/'assessment.json',description['detail'])
    atomic_json(root/'workflow.json',dict(run_id=inp['run_id'],interpreter=sys.executable,
        numerical_preparation='simulation.run budgeted prepare_execution hook; solve-free session setup',
        threads={k:os.environ[k] for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}))
    print('Prepared frozen session '+host.run_id+'; zero backend solves',flush=True)
    return host


def run(root,input_path=None):
    host=prepare(root,input_path)
    print('Starting the one authorized full-duration backend execution',flush=True)
    sim,_=call(host,'simulation.run',dict(candidate_id='parameterized-reach',changes={}),'simulate')
    ev,_=call(host,'evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']),'evaluate')
    _,report=call(host,'control.profile_report',dict(simulation_request_id='simulate',evaluation_request_id='evaluate'),'report')
    summary=report['detail'];atomic_json(root/'summary.json',summary)
    (root/'report.md').write_text(markdown(summary),encoding='utf8')
    print(json.dumps({k:summary[k] for k in ('complete','official_task_success','terminal_error_m','sampled_settling',
        'accepted_plans','updates','mean_update_s','deadline_misses')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['make-input','prepare','run'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--target',nargs=3,type=float)
    args=parser.parse_args()
    if args.action=='make-input':
        atomic_json(args.output,reach_input('gvs-reach-'+uuid4().hex[:12],target_m=args.target))
    else:
        if args.target is not None:parser.error('--target belongs to make-input; run consumes frozen --input')
        (prepare if args.action=='prepare' else run)(args.output.resolve(),args.input)
