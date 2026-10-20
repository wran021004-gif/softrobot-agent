"""Read-only S9 accounting supplement; reuses S8 export/independent verification."""
import argparse,json
from collections import Counter
from datetime import datetime
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state
from tools.state_io import atomic_json,digest
from tests.research.s8_audit import live,verify_searches


def accounting(host):
    s=state(host);events=host.store.events(host.run_id);requests=[];feedback=[];usage={}
    decisions=[];first_physics=None
    for e in events:
        if e['status']=='reserved' and e['cost'].get('backend_solves',0)>0 and first_physics is None:first_physics=e
        if e['kind']=='r3_request':requests.append(e)
        if e['kind']=='r3_response':
            v=host.store.artifact(e['outputs'][0])
            if v.get('usage'):usage[e['request_id']]=v['usage']
        if e['kind']=='model_original_tool_feedback':feedback.append(host.store.artifact(e['outputs'][0]))
        if e['kind']=='model_original_tool_request':
            v=host.store.artifact(e['outputs'][0]);payload=v.get('input',{})
            if payload.get('decision'):decisions.append(dict(reference=e['outputs'][0],action=payload.get('action'),decision=payload['decision']))
    errors=Counter()
    for item in feedback:
        if item['result']['status']!='error':continue
        try:code=json.loads(''.join(c.get('text','') for c in item['result']['content'])).get('error_code','unknown')
        except ValueError:code='non_json_error'
        errors[code]+=1
    physical=[]
    for ref in s.get('physical_replays',[]):
        r=host.store.artifact(ref);source=host.store.artifact(r['source_reference'])['trajectory']
        physical.append(digest({k:source[k] for k in ('model_identity','design_identity','task_identity','tendon_order','times_s','tensions_n')}))
    searches=[host.store.artifact(r) for r in s.get('control_search_results',[])]
    plans=[host.store.artifact(r)['original_plan'] for r in s.get('plans',[])]
    signatures=[digest({k:d['decision'].get(k) for k in ('selected_method','selected_variables','selected_candidate')}) for d in decisions]
    first=next(iter(requests),None)
    return dict(study_id=host.run_id,freeze=s.get('freeze'),provider_requests=len(requests),
        total_tokens=sum(v.get('total_tokens',0) for v in usage.values()),provider_usage=usage,
        missing_usage_requests=[e['request_id'] for e in requests if e['request_id'] not in usage],
        tool_calls=len(feedback),tool_errors=sum(errors.values()),tool_errors_by_code=dict(errors),
        evidence_reads=sum(v['tool_use']['name']=='evidence_read' for v in feedback),
        time_to_first_physics=dict(provider_requests=sum(e['sequence']<first_physics['sequence'] for e in requests),
            wall_s=(datetime.fromisoformat(first_physics['timestamp'])-datetime.fromisoformat(first['timestamp'])).total_seconds()) if first and first_physics else None,
        new_physical_evaluations=sum(len(s.get(k,[])) for k in ('results','physical_replays','rl_evaluations')),
        backend_starts=host.store.remaining()['used']['backend_solves'],unique_physical_input_sequences=len(set(physical)),
        unique_response_probes=sum(r.get('cost_feedback',{}).get('unique_response_probes',0) for r in searches),
        cache_reuses=sum(sum(v.get('cache_hit',False) for v in r['candidates']) for r in searches),
        search_feedback=[r.get('cost_feedback') for r in searches],
        math_to_control_handoff=[p['control_seed']['response_evidence'] for p in plans if (p.get('control_seed') or {}).get('method')=='mathematical_response'],
        research_decision_changes=sum(a!=b for a,b in zip(signatures,signatures[1:])),decisions=decisions,
        task_passed=bool(s.get('selected')),ledger=host.store.remaining(),numerical_s=s.get('numerical_s'),
        limitation='Decision signature changes need interpretation from raw feedback. Distinct sequences are not a proof of independent response directions. Cached observations may supply valid information. Currency unknown.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run_id');p.add_argument('destination');p.add_argument('--export',action='store_true');args=p.parse_args()
    host=Host(ROOT/'runs/research'/args.run_id,args.run_id,actor='unified-research');out=ROOT/args.destination
    if args.export:
        live(host,out)
        atomic_json(out/'search_reconstruction.json',verify_searches(host))
    atomic_json(out/'accounting.json',accounting(host))
