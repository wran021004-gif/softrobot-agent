"""Deterministic gate plus a separately bound independent material review."""
import hashlib
from tools.state_io import read,atomic_json,digest
from tools.platform_store import encode,zero
from tools.research_v1_finish import OUT,ROOT


def generate(mode):
    m=read(OUT/'validation_manifest.json');p=m['phases'][mode];b=read(OUT/(mode+'_bundle.json'))
    arts=b['artifacts'];events=b['events'];nodes=b['state'].get('investigations',{})
    result=read(OUT/(mode+'_result.json'))
    used=zero();unknown=[]
    for c in b['calls']:
        for k,v in (c.get('charged') or {}).items():used[k]+=v
        if c['status'] in ('running','unknown'):unknown.append(c['request_id'])
    attempts=[e for e in events if e['kind']=='investigation_provider_attempt'];responses=[e for e in events if e['kind']=='investigation_provider_response']
    artifacts_ok=all(hashlib.sha256(encode(v).encode()).hexdigest()==k for k,v in arts.items())
    accounting=not unknown and all(used[k]<=p['project_budget'][k] for k in used) and used['model_calls']==len(attempts)
    settings=all((a:=arts[e['outputs'][0]['artifact_id']]['payload']).get('model')=='deepseek-flash' and a.get('thinking')=={'type':'enabled'} and a.get('reasoning_effort')=='high' and a.get('tool_choice')=='auto' and a.get('max_tokens')==32768 for e in attempts)
    capacity=all(arts[e['outputs'][0]['artifact_id']]['measurement']['passed'] for e in attempts)
    review=result.get('material_review',{})
    gates=dict(immutable_archive='pass' if artifacts_ok else 'fail',bounded_accounting='pass' if accounting and b['session_status']=='stopped' else 'fail',
        actual_provider='pass' if b['transport']=='real_configured_deepseek' and attempts and len(responses)==len(attempts) else 'fail',
        approved_settings_and_wire_capacity='pass' if settings and capacity else 'fail',
        formal_dispositions='pass' if result['status']=='formal_dispositions_recorded' and len(result['receipts'])==2 and all(r['execution_status']=='completed' for r in result['receipts']) else 'fail',
        material_correctness='pass' if review.get('report')==result.get('report') and review.get('material_correctness')=='pass' else 'fail')
    key='principal-historical-v2' if mode=='reuse' else 'principal-coordinated-v2';principal=nodes[key]
    targets=result['targets'];necessary=[]
    for target in targets:
        matching=[e for e in events if e['kind']=='investigator_read' and e['status']=='completed' and e.get('request_id','').startswith('investigation-'+key)
            and arts[e['outputs'][0]['artifact_id']]['reference']==target['report'] and arts[e['outputs'][0]['artifact_id']]['pointer']=='']
        linked=[]
        for event in matching:
            record=arts[event['outputs'][0]['artifact_id']]
            for send in attempts:
                if send['sequence']<=event['sequence']:continue
                packet=__import__('json').loads(arts[send['outputs'][0]['artifact_id']]['payload']['messages'][1]['content'])
                if any(x['result']==record['page'] for x in packet.get('confirmed_followup_evidence',[])):linked.append(send['sequence'])
        necessary.append(dict(target=target,read_sequences=[e['sequence'] for e in matching],followup_send_sequences=linked))
    gates['necessary_read_followup']='pass' if all(x['read_sequences'] and x['followup_send_sequences'] for x in necessary) else 'fail'
    external=sum(e['kind']=='principal_inspection' and arts[e['outputs'][0]['artifact_id']].get('inspection_origin')!='principal_node_evidence_read' for e in events)
    caps=all(n['usage']['model_calls']<=n['order']['budget']['model_calls'] and n['usage']['tool_calls']<=n['order']['budget']['tool_calls'] for n in nodes.values())
    caps &= principal['usage']['tool_calls']+external<=24 if mode=='reuse' else principal['usage']['tool_calls']+external<=16
    gates['node_bounds']='pass' if caps else 'fail'
    if mode=='reuse':
        gates['historical_handoff']='pass' if len(b['state'].get('historical_investigations',{}))==2 and len(nodes)==1 else 'fail'
    else:
        from tools.research_validation_gate import generate as shared
        checked=shared(b,dict(bundle_identity=digest(b),reports=[t['report']['artifact_id'] for t in targets],material_correctness=review['material_correctness']),
            limits=dict(node_models=12,node_evidence=16,node_elapsed_s=2400,node_count=5,phase_models=36))
        atomic_json(OUT/'coordinated_shared_gate.json',checked)
        gates['new_investigator_queries_and_reports']='pass' if checked['gates']['investigator_selected_followup']=='pass' and checked['gates']['completed_reports']=='pass' and checked['gates']['source_scope_and_provenance']=='pass' else 'fail'
        gates['coordinator_synthesis']='pass' if result.get('coordinator_synthesis')==nodes['coordinator-summary']['result'] and nodes['coordinator-summary']['status']=='completed' else 'fail'
    return dict(version='mainline3.finish_gate@1.0.0',frozen_manifest_identity=digest(m),bundle_identity=digest(b),gates=gates,
        passed=all(v=='pass' for v in gates.values()),necessary_report_read_closures=necessary,usage=used,unknown_reservations=unknown,
        material_review=review,no_scientific_conclusion_required=True)


if __name__=='__main__':
    import sys
    mode=sys.argv[1];v=generate(mode);atomic_json(OUT/(mode+'_gate.json'),v);print(encode(dict(passed=v['passed'],gates=v['gates'],usage=v['usage'])))
