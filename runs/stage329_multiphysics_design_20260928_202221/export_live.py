"""Read-only archival projection after the autonomous provider loop has stopped."""
import os
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from tools.platform_host import Host
from tools.state_io import read,atomic_json
from extensions.tendon_family.candidate_comparison import feedback
from extensions.tendon_family.route import trial_facts
from tools.platform_store import plain
folder=Path(__file__).resolve().parent
host=Host(folder/'live',read(folder/'live/workflow.json')['run_id'])
session=host.store.session(host.run_id)
state=session['state']; route=state['route']
trials=[]
for node in route['nodes']:
    if node['action']=='run' and node['status']=='completed':
        trial=host.store.artifact(node['result'])
        trial['candidate_facts']=trial_facts(host.store,session['snapshot']['input'],trial)
        trials.append(dict(node_id=node['node_id'],result=node['result'],**feedback(trial)))
atomic_json(folder/'candidate_comparisons.json',trials)
atomic_json(folder/'live_nodes.json',route['nodes'])
atomic_json(folder/'provider_delivery.json',route.get('final'))
records=[]; tokens={}
for event in host.store.events(host.run_id):
    if event['kind'] not in ('model_request','model_raw_response','model_response','model_decision'):continue
    record=dict(event=event)
    record['inputs']=[dict(reference=r,content=host.store.artifact(r)) for r in event['inputs']]
    record['outputs']=[dict(reference=r,content=host.store.artifact(r)) for r in event['outputs']]
    if event['kind']=='model_raw_response':
        for row in record['outputs']:
            raw=row['content'].get('raw',row['content'])
            for key,value in raw.get('usage',{}).items():
                if isinstance(value,(int,float)):tokens[key]=tokens.get(key,0)+value
    records.append(record)
atomic_json(folder/'raw_provider_records.json',records)
with host.store.connect(True) as db:
    receipts=[json.loads(row['receipt']) for row in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
atomic_json(folder/'live_call_receipts.json',receipts)
atomic_json(folder/'usage_audit.json',dict(live=host.store.remaining(),provider_tokens=tokens,
    deterministic=read(folder/'plumbing_confirmation.json'),
    monetary_cost='Not supplied by provider usage; no fabricated currency estimate',workers=0,
    development_checks='8 distinct focused tests, 11 test executions including two fixture fixes; no full suite or numerical sweep',
    preflight_failure='Incorrect saved diagnosis binding 1.0.0 fixed to registered 2.0.0 before any backend attempt'))
print('Archived',len(trials),'evaluated candidates; usage',host.store.remaining()['used'],flush=True)
