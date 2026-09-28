"""Read actual charged attempts, preflight rejections and provider usage from this round."""
import json
from collections import Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.platform_store import Store
from tools.state_io import atomic_json
out=Path(__file__).resolve().parent
result={}
for name in ('deterministic','live'):
    store=Store(out/name)
    if not store.db.exists():
        result[name]=dict(started=False,provider_request_attempts=0,backend_attempts=0,charged_tool_calls=0)
        continue
    with store.connect(True) as db:
        calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
        events=[json.loads(r[0]) for r in db.execute('SELECT body FROM events ORDER BY seq')]
    charges=[json.loads(r['charged']) for r in calls]
    rejected=[e for e in events if e['status']=='rejected']
    raw=[e for e in events if e['kind']=='model_raw_response']
    responses=[dict(request_id=e['request_id'],reference=e['outputs'][0],usage=store.artifact(e['outputs'][0]).get('raw',{}).get('usage')) for e in raw]
    correction=[e for e in events if 'correction' in e['kind'] or 'retry' in e['kind']]
    transport=[r for r in calls if r['caller']=='model-transport']
    receipts=[json.loads(r['receipt']) for r in calls if r['receipt']]
    updates=[]
    for path in (out/name).glob('sessions/*/executions/*/backend/controller_observations.json'):
        values=json.loads(path.read_text())
        updates.append(dict(path=path.relative_to(out).as_posix(),updates=len(values)))
    result[name]=dict(started=True,provider_request_attempts=sum(c['model_calls'] for c in charges),
        transport_submissions=sum(e['kind']=='context_delivery' for e in events),provider_transport_statuses=dict(Counter(r['status'] for r in transport)),
        backend_attempts=sum(c['backend_solves'] for c in charges),charged_tool_calls=sum(c['tool_calls'] for c in charges),
        tool_attempts=sum(r['caller']!='model-transport' for r in calls)+sum(e['kind'] in ('tool','request_validation') for e in rejected),
        preflight_rejection_count=sum(e['kind'] in ('tool','request_validation') for e in rejected),
        preflight_rejections=[dict(kind=e['kind'],request_id=e.get('request_id'),references=e['outputs']) for e in rejected],
        event_kind_counts=dict(Counter(e['kind'] for e in events)),
        tool_receipts=[dict(tool=r['tool_id'],request_id=r['request_id'],status=r['execution_status'],charged=r['charged']) for r in receipts if not r['tool_id'].startswith('model.')],
        corrections=correction,provider_responses=responses,controller_updates_by_rollout=updates,
        charged_usage=store.remaining()['used'],
        monetary_cost=None,monetary_cost_note='No monetary charge returned by the provider API; no price estimate substituted.')
atomic_json(out/'usage_audit.json',result)
print(json.dumps({k:{f:v[f] for f in ('started','provider_request_attempts','backend_attempts','charged_tool_calls')} for k,v in result.items()},indent=2))
