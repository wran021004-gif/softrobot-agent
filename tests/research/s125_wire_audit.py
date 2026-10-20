"""Read-only S12 wire attribution and exact archived rejection reproduction."""
from collections import Counter
from copy import deepcopy
import json
from unittest.mock import patch
from tests.research.s8_audit import archive_host, payload, size
from tools.research.config import ROOT
from tools.research.state import state
from tools.state_io import atomic_json, digest


def audit():
    h,values=archive_host('evidence/s12_mirror/study')
    events=h.store.events(h.run_id);usage={};rows=[];errors=[];duplicates=Counter();subtrees=Counter()
    for e in events:
        if e['kind']=='r3_response':
            v=h.store.artifact(e['outputs'][0])
            if v.get('usage'):usage[e['request_id']]=v['usage']
    for e in events:
        if e['kind']=='r3_request':
            metadata=h.store.artifact(e['outputs'][0]);wire=h.store.artifact(metadata['request'])
            parts=payload(wire);counts=Counter();repeated=Counter()
            for m in wire['messages']:
                kind=m['role']
                for key in ('content','reasoning_content'):
                    if isinstance(m.get(key),str):
                        fingerprint=(kind,key,digest(m[key]))
                        if counts[fingerprint]:repeated[kind+'_'+key]+=size(m[key])-2
                        counts[fingerprint]+=1
            duplicates.update(repeated)
            seen=set();duplicate_nodes=Counter()
            def visit(value,path):
                if not isinstance(value,(dict,list)):return
                n=size(value);key=digest(value)
                if n>=128 and key in seen:
                    duplicate_nodes[path.rsplit('/',1)[-1]]+=n
                    return  # Do not count children again within this occurrence.
                seen.add(key)
                for k,v in (value.items() if isinstance(value,dict) else enumerate(value)):
                    visit(v,path+'/'+str(k))
            for m in wire['messages']:
                text=m.get('content')
                if not isinstance(text,str):continue
                if '\nCURRENT_RESEARCH_PACKET\n' in text:text=text.split('\nCURRENT_RESEARCH_PACKET\n',1)[1]
                try:parsed=json.loads(text)
                except ValueError:continue
                visit(parsed,m['role'])
            subtrees.update(duplicate_nodes)
            u=usage[e['request_id']]
            from tools.research.agent import plan_schema
            projected=deepcopy(wire)
            projected['tools']=[t for t in projected['tools'] if t['function']['name']!='experience_retrieve']
            for t in projected['tools']:
                if t['function']['name']=='research_plan':
                    actions=t['function']['parameters']['properties']['action']['enum']
                    t['function']['parameters']=plan_schema(actions,decision_required=True)
            rows.append(dict(order=len(rows)+1,request_id=e['request_id'],request=metadata['request'],
                **parts,message_count=len(wire['messages']),usage=u,
                prompt_cache_hit_tokens=u.get('prompt_cache_hit_tokens','unavailable'),
                prompt_cache_miss_tokens=u.get('prompt_cache_miss_tokens','unavailable'),
                reasoning_tokens=u.get('completion_tokens_details',{}).get('reasoning_tokens','unavailable'),
                repeated_exact_string_bytes=dict(repeated),repeated_parsed_subtree_bytes=dict(duplicate_nodes),
                projected_schema_bytes=size(projected['tools']),projected_request_bytes=size(projected),
                projection='Schema-only S12.5 projection, not a sent request; preserves all original messages and reasoning'))
        if e['kind']=='model_original_tool_feedback':
            v=h.store.artifact(e['outputs'][0])
            if v['result']['status']=='error':
                errors.append(dict(sequence=e['sequence'],reference=e['outputs'][0],
                    tool_use=v['tool_use'],feedback=json.loads(v['result']['content'][0]['text'])))
    totals=Counter()
    for row in rows:totals.update(row['serialized_bytes'])
    # Associate each send with subsequent feedback before the next send.
    for i,row in enumerate(rows):
        start=next(e['sequence'] for e in events if e['kind']=='r3_request' and e['request_id']==row['request_id'])
        end=next((e['sequence'] for e in events if e['kind']=='r3_request' and e['sequence']>start),float('inf'))
        row['tool_outcomes']=[dict(tool=(v:=h.store.artifact(e['outputs'][0]))['tool_use']['name'],
            action=v['tool_use']['input'].get('action'),status=v['result']['status'],reference=e['outputs'][0])
            for e in events if start<e['sequence']<end and e['kind']=='model_original_tool_feedback']
    assert len(rows)==22 and len(errors)==4
    assert sum(v['total_tokens'] for v in usage.values())==1610906
    return dict(source='evidence/s12_mirror/study',requests=rows,errors=errors,
        cumulative_bytes=dict(totals),ranked_components=totals.most_common(),
        repeated_exact_strings_ranked=duplicates.most_common(),
        repeated_parsed_subtrees_ranked=subtrees.most_common(),
        provider_totals={k:sum(v[k] for v in usage.values()) for k in ('prompt_tokens','completion_tokens','total_tokens')},
        new_provider_requests=0,new_scientific_executions=0,
        limitation='Canonical JSON bytes, not HTTP byte recording or token estimates. Repeated strings are exact within-request matches; semantic similarity is not measured. Reasoning is retained unchanged.')


def reproduce(errors):
    from tools.research.core import read_evidence
    from tools.research.contracts import Plan
    from tools.research.evidence_policy import admit_decision
    h,_=archive_host('evidence/s12_mirror/study');s=state(h)
    outcomes=[]
    for row in errors:
        use=row['tool_use'];before=deepcopy(use)
        try:
            with patch('tools.research.core.protected',return_value=False):
                if use['name']=='evidence_read':read_evidence(h,use['input'])
                else:admit_decision(h,Plan.model_validate(use['input']))
        except (ValueError,KeyError,IndexError) as exc:
            outcomes.append(dict(sequence=row['sequence'],exception=type(exc).__name__,reason=str(exc),
                original_error=row['feedback']['error_code'],rejected=True))
        else:raise AssertionError('Archived invalid request accepted')
        assert use==before
    h.store.reserve.assert_not_called();h.store.transaction.assert_not_called()
    return outcomes


def live_audit(host):
    """Attribute actual cold-study requests and preserve rejected proposals."""
    events=host.store.events(host.run_id);requests=[e for e in events if e['kind']=='r3_request']
    usage={e['request_id']:host.store.artifact(e['outputs'][0]).get('usage') for e in events if e['kind']=='r3_response'}
    rows=[];outcomes=[];totals=Counter()
    for i,event in enumerate(requests):
        end=requests[i+1]['sequence'] if i+1<len(requests) else float('inf')
        metadata=host.store.artifact(event['outputs'][0]);wire=host.store.artifact(metadata['request'])
        row=dict(order=i+1,request_id=event['request_id'],request=metadata['request'],sequence=event['sequence'],
            **payload(wire),message_count=len(wire['messages']),usage=usage[event['request_id']],tool_outcomes=[])
        row.update({k:row['usage'].get(k,'unavailable') for k in ('prompt_cache_hit_tokens','prompt_cache_miss_tokens')})
        row['reasoning_tokens']=row['usage'].get('completion_tokens_details',{}).get('reasoning_tokens','unavailable')
        for e in events:
            if not (event['sequence']<e['sequence']<end and e['kind']=='model_original_tool_feedback'):continue
            v=host.store.artifact(e['outputs'][0]);use=v['tool_use'];result=v['result']
            text=''.join(c.get('text','') for c in result['content'])
            try:detail=json.loads(text)
            except ValueError:detail=dict(error_code=text)
            if not isinstance(detail,dict):detail=dict(value=detail)
            business=host.store.artifact(detail['wrapper_reference']).get('result',{}) if detail.get('wrapper_reference') else detail
            if not isinstance(business,dict):business={}
            item=dict(sequence=e['sequence'],provider_order=i+1,reference=e['outputs'][0],tool=use['name'],
                action=use['input'].get('action'),status=result['status'],business_status=business.get('status'),
                business_reference=business.get('reference'),
                reason=business.get('reason'),error_code=detail.get('error_code') if result['status']=='error' else None)
            row['tool_outcomes'].append(item);outcomes.append(item)
        totals.update(row['serialized_bytes']);rows.append(row)
    s=state(host)
    science_ids={r['artifact_id'] for k in ('results','mechanics_results','analysis_results','physical_replays','control_search_results','rl_evaluations') for r in s.get(k,[])}
    physical_ids={r['artifact_id'] for k in ('results','physical_replays','rl_evaluations') for r in s.get(k,[])}
    scientific=[o for o in outcomes if o['status']=='success' and
        (o['tool']=='research_analysis' or o['action'] in ('execute','mechanics','replay','refine','physical_replay','control_search')) and
        (o.get('business_reference') or {}).get('artifact_id') in science_ids]
    first=min((o['sequence'] for o in scientific if (o.get('business_reference') or {}).get('artifact_id') in physical_ids),default=float('inf'))
    changed=[o for o in outcomes if o['sequence']>first and o['action'] in
        ('generate','initialize_control','mechanics','control_search','physical_replay','execute','refine')]
    child_events=[e for ref in s['results'] for e in host.store.events(host.store.artifact(ref)['owner_run_id'])]
    physics=next((e for e in sorted(events+child_events,key=lambda e:e['sequence'])
        if e['status']=='reserved' and e['cost'].get('backend_solves',0)>0),None)
    from datetime import datetime
    first_physics=None if physics is None else dict(sequence=physics['sequence'],
        provider_requests=sum(e['sequence']<physics['sequence'] for e in requests),
        wall_s=(datetime.fromisoformat(physics['timestamp'])-datetime.fromisoformat(requests[0]['timestamp'])).total_seconds())
    return dict(study_id=host.run_id,requests=rows,cumulative_bytes=dict(totals),ranked_components=totals.most_common(),
        provider_totals={k:sum(v[k] for v in usage.values()) for k in ('prompt_tokens','completion_tokens','total_tokens')},
        cache_totals={k:sum(v[k] for v in usage.values()) for k in ('prompt_cache_hit_tokens','prompt_cache_miss_tokens')},
        tool_errors=[o for o in outcomes if o['status']=='error'],
        invalid_generation=[o for o in outcomes if o['action']=='generate' and o['business_status']=='invalid'],
        generated_candidates=len(s['candidates']),generation_proposals=sum(o['action']=='generate' for o in outcomes),
        successful_generation_calls=sum(o['business_status']=='generated' for o in outcomes),
        first_physics=first_physics,
        executed_scientific_decisions=scientific,feedback_revision_proposals=changed,
        executed_feedback_revisions=sum(o in scientific for o in changed),
        registered_scientific_results={k:s.get(k,[]) for k in ('results','mechanics_results','analysis_results','physical_replays','control_search_results','rl_evaluations')},
        admitted_ppo_stages=s.get('admitted_training_stages',0),
        new_provider_requests=0,new_scientific_executions=0,
        limitation='Canonical JSON bytes are not token savings. Scientific decisions require a registered result reference; optimizer internal iterations and admitted PPO stages are separate. Rejected feedback proposals, structural generation and baseline initialization are not executed feedback calculations.')


if __name__=='__main__':
    result=audit();result['reproduced']=reproduce(result['errors'])
    out=ROOT/'evidence/s125_wire_audit';out.mkdir(parents=True,exist_ok=True)
    atomic_json(out/'s12_requests.json',result)
    print(json.dumps({k:result[k] for k in ('provider_totals','ranked_components','repeated_exact_strings_ranked')}))
