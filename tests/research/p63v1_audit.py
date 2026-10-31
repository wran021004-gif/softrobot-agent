"""Read-only compact V1 checkpoint/final audit; no science or model requests."""
import json,sqlite3
from contextlib import closing
from collections import Counter
from datetime import datetime
from pathlib import Path
from tools.research.config import ROOT
from tools.state_io import atomic_json,read

RUN='p63v1-m3-autonomous-feasibility-sol-20261030'
root=ROOT/'runs/research'/RUN
def rows(sql,parameters=()):
    # Full reports belong on offline snapshots or after the runner ends.
    # No connection spans Python JSON parsing, reporting or another query.
    with closing(sqlite3.connect((root/'platform.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        return db.execute(sql,parameters).fetchall()
def art(ref):
    return json.loads(rows('select body from artifacts where id=?',(ref['artifact_id'],))[0][0])
s=json.loads(rows('select state from sessions')[0][0])
events=[json.loads(row[0]) for row in rows('select body from events order by seq')]
def feedback_body(result):
    try:return json.loads(''.join(c.get('text','') for c in result.get('content',[])))
    except (ValueError,TypeError):return None
def compact_claim(raw):
    value=raw.get('scoped_claim')
    if not value:return None
    return {**{k:v for k,v in value.items() if k!='binding'},'binding':{
        k:v for k,v in value.get('binding',{}).items() if k in (
            'candidate','candidate_id','canonical_task_identity','effective_configuration_identity',
            'model_identity','evaluation_profile_identity','physical_design_identity')}}
feedback={}
for e in events:
    if e['kind']=='model_original_tool_feedback':
        v=art(e['outputs'][0]);feedback[v['tool_use']['toolUseId']]=(v,e['outputs'][0])
requests=[];uses=[];knowledge=[]
reqevents=[e for e in events if e['kind']=='r3_request']
for i,e in enumerate(reqevents):
    request=art(e['outputs'][0]);wire=art(request['request'])
    re=[v for v in events if v['kind']=='r3_response' and v.get('request_id')==e['request_id']]
    response=art(re[-1]['outputs'][0]) if re else {}
    row=dict(number=i+1,request_id=e['request_id'],purpose=request['purpose'],phase=request.get('request_phase'),
        wire_reference=request['request'],response_reference=response.get('body'),http_status=response.get('http_status'),
        model=wire.get('model'),reasoning_setting={k:wire[k] for k in ('reasoning','reasoning_effort','thinking') if k in wire},
        usage=response.get('usage'),elapsed_s=response.get('elapsed_s'),input_bytes=request.get('input_bytes'),tools=[])
    packet_text=next((m['content'] for m in reversed(wire.get('messages',[])) if m['role']=='user'
        and isinstance(m.get('content'),str) and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')),None)
    if packet_text:
        p=json.loads(packet_text.split('\n',1)[1])['research'];continuation=p.get('tool_continuation') or {}
        row['delivered']=dict(loaded=continuation.get('loaded'),action_handoff=continuation.get('scientific_action_handoff'),
            latest_math_reference=((p.get('mathematical_research') or {}).get('latest_result') or {}).get('reference'),
            post_result_decision=p.get('post_result_decision'),
            reporter_findings=[dict(reference=r['report_reference'],status=r['status'],results=r.get('result_references')) for r in p.get('reporter_findings',[])],
            knowledge_catalog=(p.get('knowledge') or {}).get('access'),
            knowledge_read_progress=(p.get('knowledge') or {}).get('read_progress'))
    end=reqevents[i+1]['sequence'] if i+1<len(reqevents) else float('inf')
    for te in events:
        if te['kind']!='model_original_tool_request' or not e['sequence']<te['sequence']<end:continue
        use=art(te['outputs'][0])['tool_use'];payload=use['input']
        fv,fref=feedback.get(use['toolUseId'],({},None));result=fv.get('result') or {};body=feedback_body(result)
        summary={k:payload[k] for k in ('action','next_research_action','question_type','effect_semantics','parameter_group','parameter_id','operation','tool','reference','pointer','view','key','entry_id','revision','failure_type','structure','task') if k in payload}
        if payload.get('decision'):summary['decision']={k:v for k,v in payload['decision'].items() if k!='selected_variables'}
        for field in ('search','generation','control_seed','physical_replay','control_scope','control_search_effort','selected_execution','supporting_evidence'):
            if field in payload:
                value=payload[field]
                if field=='control_seed' and isinstance(value,dict):value={k:v for k,v in value.items() if k!='tensions_n'}
                summary[field]=value
        detail={k:body[k] for k in ('status','reason','error_code','field','expected','scientific_execution_started','reference','scientific_result_reference','scientific_result_status','operation_outcome') if isinstance(body,dict) and k in body}
        item=dict(tool=use['name'],tool_use_id=use['toolUseId'],input_reference=te['outputs'][0],input_summary=summary,
            feedback_reference=fref,feedback_status=result.get('status'),feedback_summary=detail)
        row['tools'].append(item);uses.append(item)
        if use['name']=='experience_retrieve':
            knowledge.append(dict(request=i+1,operation=payload.get('operation','search'),query=payload,
                feedback_status=result.get('status'),input_reference=te['outputs'][0],feedback_reference=fref,
                role='actual_entry_read' if payload.get('operation')=='read' and result.get('status')=='success' else 'catalog_search_or_rejected_read'))
    requests.append(row)
catalog_exposures={}
for request in requests:
    access=(request.get('delivered') or {}).get('knowledge_catalog') or {}
    for kind in ('hints','study_private_entries'):
        for entry in access.get(kind,[]):
            key=(entry['entry_id'],entry['revision'],kind)
            row=catalog_exposures.setdefault(key,dict(entry=entry,exposure_kind=kind,requests=[],
                scope='Automatic catalog metadata/short hint only, not an entry-body read or current scientific evidence.'))
            row['requests'].append(request['number'])
results=[]
for ref in s.get('analysis_results',[]):
    raw=art(ref);native=raw.get('nonlinear_capability') or {}
    results.append(dict(reference=ref,candidate=raw.get('candidate'),operation=raw.get('operation'),origin=raw.get('origin'),
        status=raw.get('status'),error=raw.get('error'),reason=raw.get('reason'),boundary=raw.get('boundary'),
        charged_evaluations=raw.get('charged_analysis_evaluations'),charged_numerical_s=raw.get('charged_numerical_s'),
        native={k:native[k] for k in ('J','initial_J','best_metrics','initial_metrics','improvement','callbacks','iterations_started','stop_reason','settings','search_quality') if k in native},
        cost=raw.get('native_dynamics',{}).get('cost'),control_source=raw.get('control_schedule_reference'),
        conclusion={**{k:raw[k] for k in ('conclusion','task_acceptance','score_semantics') if k in raw},
            'scoped_claim':compact_claim(raw)}))
physical=[]
for ref in s.get('physical_replays',[]):
    raw=art(ref)
    playback=art(raw['raw_reference'])
    physical.append(dict(reference=ref,cost=playback.get('cost'),physics_steps=playback.get('physics_steps'),
        comparison={k:v for k,v in (raw.get('comparison') or {}).items() if k!='samples'},
        **{k:raw[k] for k in ('candidate','source_reference','status','owning_study','role','acceptance','raw_reference','evaluation_reference','profile_reference','boundary','charged_numerical_s') if k in raw}))
searches=[]
for ref in s.get('search_results',[]):
    saved=art(ref);r=saved['result'];best=r.get('best_native_candidate') or r.get('best_observed') or {}
    searches.append(dict(reference=ref,admission=saved.get('admission'),status=r.get('status'),termination=r.get('termination_reason'),
        resources=r.get('resource_use'),best_candidate=(best.get('evidence') or {}).get('candidate'),best_score=best.get('proxy_values'),
        evaluated=[dict(candidate=(x.get('evidence') or {}).get('candidate'),status=x.get('computation_status'),score=x.get('proxy_values'),
            changed_paths=(x.get('lineage') or {}).get('variables_or_topology_changed'),
            previous_candidate=(x.get('lineage') or {}).get('previous_candidate_ref'),cost=(x.get('lineage') or {}).get('cost')) for x in r.get('evaluated',[])]))
search_delivery=[]
for search in searches:
    ref=search['reference'];best=search.get('best_candidate')
    if not best:continue
    recorded=next((e for e in events if ref in e.get('outputs',[])),None)
    next_request=next((e for e in reqevents if recorded is not None and e['sequence']>recorded['sequence']
        and art(e['outputs'][0])['purpose']=='conversation'),None)
    if next_request is None:continue
    request=art(next_request['outputs'][0]);wire_text=json.dumps(art(request['request']),ensure_ascii=True)
    score=(search.get('best_score') or {}).get('task_violation')
    reporters=[e for e in events if e['kind']=='reporter_completed' and recorded['sequence']<e['sequence']<next_request['sequence']]
    elapsed=lambda a,b:(datetime.fromisoformat(b)-datetime.fromisoformat(a)).total_seconds()
    search_delivery.append(dict(search_reference=ref,best_candidate=best,request_id=next_request['request_id'],
        wire_reference=request['request'],search_reference_in_wire=ref['artifact_id'] in wire_text,
        best_candidate_reference_in_wire=best['artifact_id'] in wire_text,
        best_score_in_wire=score is not None and str(score) in wire_text,
        search_saved_timestamp=recorded['timestamp'],next_main_request_timestamp=next_request['timestamp'],
        search_to_next_main_s=elapsed(recorded['timestamp'],next_request['timestamp']),
        last_reporter_completion_before_main=reporters[-1]['timestamp'] if reporters else None,
        reporter_to_next_main_s=elapsed(reporters[-1]['timestamp'],next_request['timestamp']) if reporters else None,
        scope='Literal checks of the actual first Main wire after this saved search. Missing direct exposure does not mean the immutable result is unreadable through evidence_read.'))
plans=[]
for ref in s.get('plans',[]):
    saved=art(ref);p=saved['original_plan']
    plans.append(dict(reference=ref,request_id=saved.get('request_id'),origin=saved.get('origin'),action=p['action'],
        hypothesis=p['hypothesis'],expected=p.get('expected_observation'),weakening=p.get('weakening_observation'),
        interpretation=p.get('interpretation'),supporting_evidence=p.get('supporting_evidence'),decision=p.get('decision'),
        next_research_action=p.get('next_research_action'),search=p.get('search'),selected_execution=p.get('selected_execution'),
        experience_disposition=p.get('experience_disposition')))
usage=Counter()
for r in requests:
    for k in ('prompt_tokens','completion_tokens','total_tokens'):usage[k]+=(r.get('usage') or {}).get(k,0)
    usage['reasoning_tokens']+=((r.get('usage') or {}).get('completion_tokens_details') or {}).get('reasoning_tokens',0)
calls=[dict(request_id=row[0],status=row[1],charged=json.loads(row[2]) if row[2] else None,receipt=bool(row[3])) for row in rows('select request_id,status,charged,receipt from calls')]
generation_failures=[dict(reference=e['outputs'][0],reason=art(e['outputs'][0]).get('reason'),
    diagnostic={k:art(e['outputs'][0]).get('diagnostic',{}).get(k) for k in ('status','reason','check','error_code')})
    for e in events if e['kind']=='generation_failure']
knowledge_receipts=[]
for ref in s.get('retrievals',[]):
    receipt=art(ref)
    knowledge_receipts.append(dict(reference=ref,operation=receipt['query']['operation'],query=receipt['query'],
        matched_count=receipt.get('matched_count'),reader=receipt.get('reader'),
        entries=[{k:r.get(k) for k in ('entry_id','revision','title','kind','task','structure','status','content_role')} for r in receipt.get('results',[])],
        content_read=receipt['query']['operation']=='read' and len(receipt['results'])==1 and receipt['results'][0].get('status')!='source_unavailable',
        scientific_evidence=receipt.get('scientific_evidence')))
reported_cost=Counter()
for row in [*results,*physical]:
    for k,v in (row.get('cost') or {}).items():
        if isinstance(v,(int,float)) and not isinstance(v,bool):reported_cost[k]+=v
knowledge_delivered={}
for request in requests:
    progress=(request.get('delivered') or {}).get('knowledge_read_progress') or {}
    for row in progress.get('reads',[]):
        if row.get('body_delivered'):
            knowledge_delivered[(row['entry_id'],row['revision'])]=dict(**row,confirmed_request=request['number'])
def embedded_objects(value):
    if isinstance(value,str):
        try:parsed=json.loads(value)
        except ValueError:return
        if isinstance(parsed,(dict,list)):yield from embedded_objects(parsed)
    elif isinstance(value,dict):
        yield value
        for child in value.values():yield from embedded_objects(child)
    elif isinstance(value,list):
        for child in value:yield from embedded_objects(child)
for receipt in knowledge_receipts:
    if not receipt['content_read'] or receipt.get('reader','agent')!='agent':continue
    expected=dict(reference=receipt['reference'],**art(receipt['reference']))
    for request in requests:
        if request['purpose']!='conversation' or request.get('http_status')!=200:continue
        wire=art(request['wire_reference'])
        if receipt['reference']['artifact_id'] not in json.dumps(wire):continue
        if any(value==expected for value in embedded_objects(wire)):
            entry=receipt['entries'][0]
            knowledge_delivered[(entry['entry_id'],entry['revision'])]=dict(entry_id=entry['entry_id'],revision=entry['revision'],
                read_receipt=receipt['reference'],tool_read_completed=True,body_delivered=True,confirmed_request=request['number'],
                confirmation_method='Exact complete receipt in an actual HTTP200 Main request; delivery does not prove understanding or adoption.')
            break
out=dict(schema='p63v1_compact_live_audit_v1',study_id=RUN,store=str(root),freeze=s.get('freeze'),
    status=s['research_status'],pending=s.get('pending'),unconsumed_response=s['pilot'].get('unconsumed_response'),
    provider=dict(total=len(requests),ceiling=s['spec']['budgets']['provider_requests'],roles=dict(Counter(r['purpose'] for r in requests)),
        usage=dict(usage),elapsed_s=sum(r.get('elapsed_s') or 0 for r in requests),monetary_cost='unknown: not supplied',
        max_input_bytes=max((r['input_bytes'] for r in requests),default=0)),
    preparation=read(root/'v1_preparation.json'),requests=requests,plans=plans,generation_failures=generation_failures,
    implementation_repairs=s.get('core_repairs',[]),
    profile_history=[{k:p[k] for k in ('identity','version') if k in p} for p in s.get('profile_history',[])],
    analysis_results=results,physical_replays=physical,searches=searches,search_delivery_checks=search_delivery,
    candidates=[dict(reference=ref,parameters=art(ref)['parameters'],provenance=art(ref).get('provenance'),
        physical_design_identity=art(ref).get('physical_design_identity'),model_identity=art(ref).get('numerical_model_identity'),
        profile_identity=art(ref).get('profile_identity'),evaluation_version=art(ref).get('evaluation_version'),
        cells=art(ref)['configuration']['policy']['discretization']['data']['cells']) for ref in s['candidates'].values()],
    knowledge_access=knowledge,knowledge_catalog_exposures=list(catalog_exposures.values()),
    knowledge_actual_read_count=sum(x['role']=='actual_entry_read' for x in knowledge),
    knowledge_receipts=knowledge_receipts,knowledge_actual_source_read_count=sum(x['content_read'] for x in knowledge_receipts),
    knowledge_main_source_read_count=sum(x['content_read'] and x.get('reader','agent')=='agent' for x in knowledge_receipts),
    knowledge_reporter_source_read_count=sum(x['content_read'] and x.get('reader')=='reporter' for x in knowledge_receipts),
    knowledge_main_delivered_bodies=list(knowledge_delivered.values()),
    analysis_status_counts=dict(Counter(r['status'] for r in results)),analysis_failure_reasons=dict(Counter(r['reason'] for r in results if r['reason'])),
    counts={k:s.get(k) for k in ('mathematical_evaluations','physical_replay_launches','nmpc_launches','rl_runs','rl_evaluations','local_solves','offline_nlp','bdf_replays')},
    numerical_s=s.get('numerical_s'),construction_numerical_s=s.get('construction_numerical_s'),
    control_initialization_s=s.get('control_initialization_s'),control_source_registration_count=len(s.get('control_initializations',[])),
    known_native_cost_counters=dict(reported_cost),missing_detailed_analysis_costs=sum(r['cost'] is None for r in results),
    cost_scope='Only reported counters are summed; missing detailed cost is unknown, not zero. Worker wall and kernel wall scopes overlap and must not be added again.',
    selected=s.get('selected'),success_gate=s.get('success_gate'),
    final_disposition=art(s['final_disposition']) if s.get('final_disposition') else None,
    open_calls=[c for c in calls if not c['receipt']],shared_ledger={k:sum((c['charged'] or {}).get(k,0) for c in calls) for k in ('model_calls','tool_calls','backend_solves','worker_calls','wall_s')},
    worker_boundaries=[dict(kind=kind,folder=str(folder.relative_to(root)),boundary=read(folder/'boundary.json'),
        lifecycle=read(folder/'worker_lifecycle.json') if (folder/'worker_lifecycle.json').exists() else None)
        for kind in ('analyses','physical_replay') for folder in (root/kind).glob('*') if (folder/'boundary.json').exists()],
    last_events=[dict(kind=e['kind'],sequence=e['sequence'],outputs=e['outputs']) for e in events[-8:]])
atomic_json(ROOT/'runs/p63v1_latest_audit.json',out)
print(json.dumps(dict(status=out['status'],provider=out['provider'],candidates=len(s['candidates']),plans=[r['action'] for r in plans],
    analysis=out['analysis_status_counts'],physical=[r['acceptance']['status'] for r in physical],selected=out['selected'],
    pending_kind=(s.get('pending') or {}).get('kind'),open_calls=len(out['open_calls']),knowledge_actual_reads=out['knowledge_actual_read_count']),indent=2))
