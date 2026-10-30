"""Read-only snapshot; source wire remains in the original Store, no secrets/reasoning copied."""
import json,sqlite3
from pathlib import Path
from tools.research.config import ROOT
from tools.state_io import read,atomic_json
root=ROOT/'runs/research/p63g3-m3-action-handoff-sol-20261030'
db=sqlite3.connect((root/'platform.sqlite').as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
def art(ref):return json.loads(db.execute('SELECT body FROM artifacts WHERE id=?',(ref['artifact_id'],)).fetchone()[0])
s=json.loads(db.execute('SELECT state FROM sessions').fetchone()[0])
events=[json.loads(v[0]) for v in db.execute('SELECT body FROM events ORDER BY seq')]
reqevents=[e for e in events if e['kind']=='r3_request'];requests=[]
for number,event in enumerate(reqevents,1):
    v=art(event['outputs'][0]);wire=art(v['request'])
    responseevents=[e for e in events if e['kind']=='r3_response' and e.get('request_id')==event['request_id']]
    response=art(responseevents[-1]['outputs'][0]) if responseevents else {}
    schema=next((t['function']['parameters'] for t in wire.get('tools',[]) if t['function']['name']=='research_analysis'),None)
    row=dict(number=number,request_id=event['request_id'],purpose=v['purpose'],phase=v.get('request_phase'),input_bytes=v.get('input_bytes'),
        event_reference=event['outputs'][0],wire_reference=v['request'],response_reference=response.get('body'),
        model=wire.get('model'),reasoning_setting={k:wire[k] for k in ('reasoning','reasoning_effort','thinking') if k in wire},
        http_status=response.get('http_status'),usage=response.get('usage'),elapsed_s=response.get('elapsed_s'),money=response.get('money'),
        visible_tools=[t['function']['name'] for t in wire.get('tools',[])],analysis_schema_kind='ScientificQuestion' if schema and 'question_type' in schema.get('properties',{}) else 'precise_or_absent',tools=[])
    text=next((m['content'] for m in reversed(wire['messages']) if m['role']=='user' and isinstance(m.get('content'),str) and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')),None)
    if text:
        p=json.loads(text.split('\n',1)[1])['research']
        row.update(delivered_latest_math=(p.get('mathematical_research') or {}).get('latest_result'),
            delivered_handoff=p.get('tool_continuation'),actual_capabilities=p.get('capabilities'),
            post_result_decision=p.get('post_result_decision'),index_read_progress=(p.get('evidence_access',{}).get('stop_index') or {}).get('read_progress'),
            delivered_reporters=[dict(reference=r['report_reference'],status=r['status'],interpretation_kinds=[i['kind'] for i in r['interpretations']],result_references=r['result_references']) for r in p.get('reporter_findings',[])],
            delivered_budget=p.get('budget'))
    if response.get('body') and row['purpose']=='conversation':
        parsed=art(response['body']);row['main_visible_text']=[c.get('message',{}).get('content') for c in parsed.get('choices',[]) if c.get('message',{}).get('content')]
    next_seq=reqevents[number]['sequence'] if number<len(reqevents) else 10**12
    for e in events:
        if e['kind']!='model_original_tool_request' or not event['sequence']<e['sequence']<next_seq:continue
        use=art(e['outputs'][0])['tool_use']
        fe=next((f for f in events if f['kind']=='model_original_tool_feedback' and art(f['outputs'][0])['tool_use']['toolUseId']==use['toolUseId']),None)
        returned=art(fe['outputs'][0])['result'] if fe else None;content=None
        if returned:
            try:content=json.loads(''.join(b.get('text','') for b in returned.get('content',[])))
            except ValueError:pass
        output={k:content[k] for k in ('status','reason','error','message','scientific_execution_started','scientific_result_produced','choices','execution_feedback','scientific_result_status','scientific_result_reference','operation_outcome','interpretation_status','reference','this_read','notice','read_progress') if k in content} if isinstance(content,dict) else {}
        if use['name']=='evidence_read' and use['input'].get('pointer')=='/all_fresh_results':
            output['returned_result_references']=content.get('results') if isinstance(content,dict) else content
        if use['name']=='experience_retrieve':output=dict(knowledge_body_omitted=True,retained_in_original_store=True)
        row['tools'].append(dict(tool=use['name'],input=use['input'],tool_use_id=use['toolUseId'],input_reference=e['outputs'][0],
            feedback_reference=fe['outputs'][0] if fe else None,feedback_status=returned.get('status') if returned else None,feedback_summary=output))
    requests.append(row)
results=[]
for ref in s.get('analysis_results',[]):
    raw=art(ref);native=raw.get('nonlinear_capability') or {}
    results.append(dict(reference=ref,status=raw.get('status'),operation=raw.get('operation'),candidate=raw.get('candidate'),
        task_acceptance=raw.get('task_acceptance'),scoped_claim=raw.get('scoped_claim'),origin=raw.get('origin'),operation_key=raw.get('operation_key'),
        nonlinear_capability={k:native[k] for k in ('J','initial_J','improvement','initial_metrics','best_metrics','stop_reason','callbacks','rollouts','physics_steps','iterations_started','response_steps_completed','search_quality','settings','best_control','cost','limitations') if k in native},
        other_result_summary={k:raw[k] for k in ('nonlinear_response','native_analysis','conclusion') if k in raw and not native},
        charged_analysis_evaluations=raw.get('charged_analysis_evaluations'),charged_numerical_s=raw.get('charged_numerical_s'),native_cost=raw.get('native_dynamics',{}).get('cost')))
calls=[dict(request_id=r[0],receipt=json.loads(r[1]) if r[1] else None,charged=json.loads(r[2]) if r[2] else None,status=r[3]) for r in db.execute('SELECT request_id,receipt,charged,status FROM calls ORDER BY rowid')]
used={k:sum((c['charged'] or {}).get(k,0) for c in calls) for k in ('model_calls','tool_calls','backend_solves','worker_calls','wall_s')}
reports=[]
for e in events:
    if e['kind']=='reporter_completed':
        completion=art(e['outputs'][0]);saved=art(completion['report_reference'])
        reports.append(dict(completion_reference=e['outputs'][0],**completion,interpretation_status=saved['interpretation_status'],
            error=saved['error'],rejection_details=saved.get('rejection_details'),interpretations=saved['report']['interpretations']))
out=dict(study_id=s['spec']['study_id'],store=str(root),freeze=s.get('freeze'),resolved_identity=s['spec']['resolved_identity'],
    research_status=s['research_status'],mathematical_evaluations=s['mathematical_evaluations'],budgets=s['spec']['budgets'],pending=s.get('pending'),
    pilot_summary={k:s['pilot'].get(k) for k in ('live_model_requests','unconsumed_response')},requests=requests,
    results=results,reporter_completions=reports,calls=calls,shared_ledger_used=used,plans=[dict(reference=r,**art(r)) for r in s['plans']],
    numerical_s=s.get('numerical_s'),construction_numerical_s=s.get('construction_numerical_s'),
    scientific_state={k:s.get(k) for k in ('results','physical_replays','mechanics_results','rl_evaluations','rl_training_summaries','rl_runs','searches','search_results','local_solves','offline_nlp','bdf_replays','selected','evaluation_reads')},
    last_event_kinds=[e['kind'] for e in events[-8:]],unsealed_calls=sum(not c['receipt'] for c in calls),
    pauses=[dict(reference=e['outputs'][0],**art(e['outputs'][0])) for e in events if e['kind']=='supervisor_pause'])
out['closure']=dict(final_disposition=s.get('final_disposition'),
    disposition=art(s['final_disposition']) if s.get('final_disposition') else None,
    success_gate=s.get('success_gate'),closed_unix=s.get('closed_unix'))
out['independent_results']=[dict(reference=ref,kind=key,**{k:raw[k] for k in ('candidate','status','accepted','task_passed','task_acceptance','acceptance','termination','cost','metrics','numerical_s','source_reference','task_identity','implementation') if k in raw})
    for key in ('results','physical_replays','rl_evaluations') for ref in s.get(key,[]) for raw in [art(ref)]]
out['worker_boundaries']=[dict(folder=str(folder),boundary=read(folder/'boundary.json'),lifecycle=read(folder/'worker_lifecycle.json') if (folder/'worker_lifecycle.json').exists() else None)
    for folder in (root/'analyses').glob('*') if (folder/'boundary.json').exists()]
out['original_event_references']=[dict(sequence=e['sequence'],kind=e['kind'],status=e.get('status'),outputs=e['outputs']) for e in events if e['kind'] in
    ('analysis_request_binding','candidate_analysis','physical_replay','research_report','reporter_completed','original_research_plan','model_original_tool_feedback','supervisor_pause','formal_study_authorization','live_handoff_admission')]
out['preparation']=read(root/'g3_preparation.json') if (root/'g3_preparation.json').exists() else None
out['structure_bindings']=[dict(reference=e['outputs'][0],**art(e['outputs'][0])) for e in events if e['kind']=='structure_search_intent_binding']
out['search_results']=[dict(reference=r,**art(r)) for r in s.get('search_results',[])]
out['worker_records']=[dict(kind=kind,folder=str(folder.relative_to(root)),boundary=read(folder/'boundary.json') if (folder/'boundary.json').exists() else None,
    lifecycle=read(folder/'worker_lifecycle.json') if (folder/'worker_lifecycle.json').exists() else None,
    result={k:raw[k] for k in ('status','cost','candidate','physics_steps','model_identity','source_reference') if k in raw},
    native_cost=raw.get('native_dynamics',{}).get('cost'))
    for kind in ('analyses','physical_replay') for folder in (root/kind).glob('*') if (folder/'result.json').exists() for raw in [read(folder/'result.json')]]
out['search_schemas']=[dict(provider_request=r['number'],wire_reference=r['wire_reference'],schema=t['function']['parameters'])
    for r in requests for t in art(r['wire_reference']).get('tools',[]) if t['function']['name']=='research_plan' and t['function']['parameters']['properties']['action'].get('enum')==['search']]
atomic_json(ROOT/'runs/g3_readonly_audit.json',out)
from collections import Counter
p=out
schemas=[]
for r in p['requests']:
    wire=art(r['wire_reference'])
    for t in wire.get('tools',[]):
        item=next((s for s in schemas if s['function']==t['function']),None)
        if item is None:item=dict(function=t['function'],provider_requests=[]);schemas.append(item)
        item['provider_requests'].append(r['number'])
    for t in r['tools']:
        if not t.get('feedback_reference'):continue
        raw=art(t['feedback_reference'])['result']
        body=json.loads(''.join(b.get('text','') for b in raw.get('content',[])))
        if isinstance(body,dict):
            for k in ('field','expected','issues','contract','error_code','scientific_result_produced','choices'):
                if k in body:t['feedback_summary'][k]=body[k]
for r in p['results']:
    raw=art(r['reference'])
    r.update(boundary=raw.get('boundary'),error=raw.get('error'),reason=raw.get('reason'),
        recorded_native_cost=raw.get('native_dynamics',{}).get('cost'))
roles=Counter(r['purpose'] for r in p['requests']);usage=Counter()
for r in p['requests']:
    for k in ('prompt_tokens','completion_tokens','total_tokens'):usage[k]+=(r.get('usage') or {}).get(k,0)
    usage['reasoning_tokens']+=((r.get('usage') or {}).get('completion_tokens_details') or {}).get('reasoning_tokens',0)
prep=p.get('preparation') or {}
main_results=[r for r in p['results'] if r['reference']!=prep.get('math_result')]
search_results=[r for r in main_results if r['origin']=='model_search']
codesign_requests=[r for r in p['requests'] if any(t['tool']=='research_plan' and t['feedback_status']=='success' and t['input'].get('next_research_action')=='structure_control_codesign' for t in r['tools'])]
next_wire=[]
for r in codesign_requests:
    following=next((w for w in p['requests'] if w['number']>r['number'] and w['purpose']=='conversation'),None)
    next_wire.append(dict(diagnose_request=r['number'],next_request=following['number'] if following else None,
        wire_reference=following['wire_reference'] if following else None,
        search_schema_loaded=bool(following and any(t['function']['name']=='research_plan' and
            'ScientificStructureSearch' in json.dumps(t['function']['parameters']) for t in art(following['wire_reference']).get('tools',[])))))
cost=Counter()
for w in p['worker_records']:
    for k,v in (w['native_cost'] or w['result'].get('cost') or {}).items():
        if isinstance(v,(int,float)):cost[k]+=v
p.update(schema='p63g3_live_audit_v1',scope='One new Study only. Operator preparation and offline fixture science are excluded from Main execution. No original G2 Store or allowance is reused.',
    actual_tool_schemas=schemas,
    provider_totals=dict(roles=dict(roles),requests=len(p['requests']),ceiling=16,usage=dict(usage),
        elapsed_s=sum(r.get('elapsed_s') or 0 for r in p['requests']),max_input_bytes=max((r['input_bytes'] for r in p['requests']),default=0),
        monetary_cost='unknown: not supplied',all_http_200=all(r['http_status']==200 for r in p['requests'])),
    scientific_cost_totals=dict(cost),ownership=dict(operator_preparation_math=1,operator_preparation_physical=1,
        operator_preparation_reporter=prep.get('provider_after_reporter'),main_math=len(main_results),main_search_math=len(search_results),
        main_physical=max(0,len(p['independent_results'])-1),main_searches=len(p['search_results'])),
    next_codesign_wires=next_wire,
    acceptance=dict(explicit_codesign_selected=bool(codesign_requests),next_search_schema_loaded=any(r['search_schema_loaded'] for r in next_wire),
        search_plan_admitted=any(r['original_plan']['action']=='search' for r in p['plans']),
        original_search_worker_started=any((r['boundary'] or {}).get('worker_started') for r in search_results),
        original_search_worker_completed=any((r['boundary'] or {}).get('termination_confirmed') and (r['boundary'] or {}).get('returncode')==0 for r in search_results),
        search_mathematical_results=len(search_results),global_feasibility_or_task_acceptance_claimed=False))
p['main_search_outcomes']=dict(status_counts=dict(Counter(r['status'] for r in search_results)),
    charged_worker_wall_s=sum(r.get('charged_numerical_s') or 0 for r in search_results),
    detailed_native_cost_missing=sum(r['recorded_native_cost'] is None for r in search_results),
    cost_scope='Scientific cost counters sum reported native costs only. Missing detailed counters for incomplete Workers are unknown, not zero; all charged Worker wall time and formal evaluation charges are retained.',
    original_failure_reasons=dict(Counter(r['reason'] for r in search_results if r['reason'])))
p['publication']=dict(local_frozen_implementation='e082a4ae2525cc4d12806fdce11a53a265a997f3',
    published_implementation='e06603b1e1f3c2b186535ee2f7df9815cdf19afb',
    identical_implementation_tree='933b8b4c5a7a6c8e0d14e0947a5b1c6f2c05cfd7',
    method='GitHub connector Git-data publication because direct git transport was unavailable; commit metadata differs, exact source tree agrees. Original local commits are retained in the delivered incremental bundle.')
p['local_runner_boundaries']=dict(initial_preflight='No Main request sent until original frozen single-thread environment was set.',
    closeout='Original engineering_closeout after settled receipts. Subsequent SDK continuation blocked before r3_request by SEALED_STOP_OR_PENDING_WORK_BLOCKS_SEND; APIConnectionError wraps that local guard. No new actual Provider request, outstanding receipt or worker.')
g2=Path(r'C:/Users/gugugaga/Documents/Codex/2026-10-30/files-pasted-by-the-user-p6/work/softrobot-g2/runs/research/p63g2-m3-mixed-search-sol-20261030/platform.sqlite')
stamp=dict(size=g2.stat().st_size,mtime_ns=g2.stat().st_mtime_ns)
before=json.loads((ROOT/'runs/g3_g2_store_stamp_before.json').read_text())
assert before==stamp
p['g2_store_unchanged']=dict(before=before,after=stamp,unchanged=True)
dest=ROOT/'docs/research/p63g3_live_audit.json'
dest.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print(json.dumps(dict(requests=[dict(number=r['number'],purpose=r['purpose'],http=r['http_status'],tools=[dict(tool=t['tool'],status=t['feedback_status'],input=t['input']) for t in r['tools']],delivered_post_result=bool(r.get('post_result_decision'))) for r in requests],
    results=[dict(reference=r['reference'],status=r['status'],operation=r['operation'],J=r['nonlinear_capability'].get('J'),callbacks=r['nonlinear_capability'].get('callbacks')) for r in results],
    status=s['research_status'],used=used,pending=s.get('pending'),unsealed_calls=out['unsealed_calls']),ensure_ascii=False,indent=2))
