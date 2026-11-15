"""Add exactly two missing K+S+ Main sessions, reusing frozen E1 inputs verbatim."""
import argparse
import datetime
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

RUN=Path(__file__).resolve().parent
ROOT=RUN.parent
sys.path.insert(0,str(ROOT))
from e1_replay import DATA,HISTORY,TASKS,read,write,messages_for,credential,httpx,Plan,ExperienceQuery,EvidenceQuery,jsonschema


def prepare():
    if (RUN/'execution_schedule.json').exists():raise RuntimeError('Supplement already frozen; do not create extra sessions.')
    existing=[json.loads(s) for s in (DATA/'decision_results.jsonl').read_text('utf-8').splitlines()]
    assert len(existing)==6 and all(r['condition']!='K+S+' and r['status']=='completed' for r in existing)
    shutil.copytree(DATA,RUN/'prior_figure_data')
    for name in ['scores_unblinded.csv','execution_accounting.json','matching_and_leakage_notes.json','replay_configuration.json','independent_review_configuration.json']:
        if (ROOT/name).exists():shutil.copy2(ROOT/name,RUN/('prior_'+name))
    probe=[];schedule=[]
    for task,rel in TASKS.items():
        source=HISTORY/rel;final=read(source/'FINAL_RESULT.json');delivery=read(source/'DELIVERY_VERIFICATION.json')
        trace=[json.loads(s) for s in (source/'STUDY_TRACE.jsonl').read_text('utf-8').splitlines()]
        assert final['provider_calls']==0 and final['formal_main_executed'] is False and delivery['formal_main_executed'] is False
        actual=read(source/'ACTUAL_KNOWLEDGE_READS.json')
        reads=[dict(line_1_based=i+1,event_id=e['event_id'],actor=e.get('actor'),tool=e.get('tool_name')) for i,e in enumerate(trace) if e.get('tool_name')=='experience_retrieve']
        assert reads and all(r['actor']=='codex_surrogate_main' for r in reads)
        probe.append(dict(task_id=task,source_directory=source.as_posix(),provider_calls=0,formal_main_executed=False,
            result_source=(source/'FINAL_RESULT.json').as_posix(),result_pointers=['/provider_calls','/formal_main_executed'],
            delivery_source=(source/'DELIVERY_VERIFICATION.json').as_posix(),actual_KS_reads=actual,read_trace_source=(source/'STUDY_TRACE.jsonl').as_posix(),read_events=reads,
            classification='Codex surrogate engineering Core/public-tool executions; not Main LLM requests/responses or Main SDK delivery.',
            main_replay_input_scope='MAIN_REPLAY_INPUT contains authored intent projections and future replay templates, not evidence of a completed historical Main Provider session.',
            matching_historical_Main_KplusSplus_found=False,selected_action='One new K+S+ decision-only replay.'))
        historical=read(ROOT/'historical_reference'/f'{task}.json')
        write(RUN/'engineering_reference'/f'{task}.json',historical)
        snapshot=read(ROOT/'snapshots'/f'{task}.json')
        messages,available=messages_for(snapshot,'K+S+')
        assert [a['key'] for a in available]==actual
        item=dict(task_id=task,condition='K+S+',session_id=str(uuid.uuid4()),ordinal=len(existing)+len(schedule)+1,phase='ks_completion')
        schedule.append(item);folder=ROOT/'sessions'/item['session_id']
        write(folder/'initial_messages.json',messages)
        write(folder/'delivery_manifest.json',dict(task_id=task,condition='K+S+',delivered_entry_keys=[e['key'] for e in available],
            delivery='Exact same E1 messages_for with both factors enabled; archived read results preloaded.',reporter=False,
            current_candidate=None,current_scientific_evidence=[],old_messages_restored=False,new_experience_generated=False,
            read_claim='Provider request proves delivery of entry content; optional experience_retrieve calls are recorded separately and not invented.'))
    write(RUN/'history_search_result.json',probe)
    write(RUN/'execution_schedule.json',schedule)
    cfg=read(ROOT/'replay_configuration.json')
    write(RUN/'replay_configuration.json',dict(original_configuration=cfg,matching='Same model, transport, unexposed default reasoning, snapshots, prompts, schema, optional reads, Reporter OFF and max four requests.',
        native_reasoning_parameter_sent=False,native_tools_parameter_sent=False,new_main_sessions=2,old_other_cells_rerun=False,prior_materials_archive=(RUN/'prior_figure_data').as_posix()))
    (RUN/'protocol.md').write_text('''# E1 K+S+ completion

Two original FULLs explicitly record zero Provider calls, formal_main_executed=false and codex_surrogate_main experience reads. Their Core Plans remain separate engineering references and are excluded from the completed four-LLM comparison.

Exactly one missing K+S+ replay per T04/T07. Reuse immutable E1 snapshots, messages_for, full original system prompt, exact schemas, gpt-5.6-sol, account3 text-only Gateway, unexposed Gateway-default reasoning and max four Provider sends. All original other-cell decisions are reused without rerunning. The model/stream/messages-only wire is retained; no medium or none parameter is added. No workers, math, physics, Reporter or Knowledge/Skill changes.

All four Main LLM decisions per task will receive one fresh anonymous joint review with the existing gpt-6-astra/rubric. Old reviews and authored-reference comparisons are archived, not mixed into updated scores. Preserve human review forms. Same factual reference library, no future outcomes, no costs/condition labels; reviewer library does not prove every Main received it.

For each scored metric y00,y10,y01,y11 (Knowledge first), report K main effect=((y10-y00)+(y11-y01))/2; S main effect=((y01-y00)+(y11-y10))/2; interaction contrast=y11-y10-y01+y00. Also report the corresponding +/-1 regression coefficient interaction/4, never confuse it with the contrast. Single observation/cell: descriptive contrasts, no significance or population-causal synergy claim. Invalid-action count effects use lower-is-better direction. Knowledge/Skill entries overlap semantically and references can cross categories, so effects concern delivered bundles rather than pure separable facts/procedures.

K+S+ is acquired later than the six original sessions; provider default reasoning and backend revision are not exposed, so within-task inputs/settings are matched but temporal/backend identity is unverified. Token usage is actual when supplied; absent Gateway usage stays unknown, with separately labeled full-wire generic proxy estimates over every send. Preserve legacy visible-text estimates separately.
''',encoding='utf-8')
    print(json.dumps(dict(prepared=True,missing_historical_Main=2,new_sessions=2,old_six_reused=True)),flush=True)


def run():
    cfg=read(ROOT/'replay_configuration.json');provider=cfg['provider'];key=credential(provider,cfg['credentials_reference'])
    output=DATA/'decision_results.jsonl'
    done={json.loads(s)['session_id'] for s in output.read_text('utf-8').splitlines()}
    with httpx.Client(timeout=provider['timeout_s'],trust_env=False,follow_redirects=False) as client:
        for item in read(RUN/'execution_schedule.json'):
            if item['session_id'] in done:continue
            folder=ROOT/'sessions'/item['session_id']
            if list(folder.glob('request_*.json')):raise RuntimeError('Unresolved send exists; do not create a replacement session.')
            snapshot=read(ROOT/'snapshots'/f"{item['task_id']}.json")
            messages=read(folder/'initial_messages.json');expected,available=messages_for(snapshot,'K+S+');assert messages==expected
            allowed={e['key']:e for e in available}
            rec=dict(**item,status='no_valid_decision',decision=None,requests=[],experience_reads=[],errors=[],delivered_entry_keys=list(allowed),
                transport='text_serialized_existing_Core_Plan',effective_reasoning=cfg['effective_reasoning'],new_studies=0,new_reporter_requests=0,new_mathematical_solves=0,new_physics_runs=0,new_candidates=0)
            begun=time.perf_counter();print(json.dumps(dict(event='KplusSplus_started',**item)),flush=True)
            for turn in range(1,5):
                wire=dict(model=provider['model'],stream=False,messages=messages)
                # httpx json=wire is the same original transport. Save its exact
                # encoding as well as the semantic request for whole-wire accounting.
                payload=httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire).content
                assert len(payload)<=provider['model_capabilities']['max_request_bytes']
                (folder/f'request_{turn}.json').write_bytes(payload)
                req=dict(turn=turn,sent_at=datetime.datetime.now(datetime.timezone.utc).isoformat());rec['requests'].append(req);write(folder/'result.json',rec)
                sent=time.perf_counter()
                try:response=client.post(provider['base_url'].rstrip('/')+'/chat/completions',json=wire,headers={'Authorization':'Bearer '+key})
                except Exception as exc:
                    req['transport_error']=type(exc).__name__+': '+str(exc);rec['status']='transport_error_stop_all';write(folder/'result.json',rec);raise
                (folder/f'response_{turn}.txt').write_text(response.text,encoding='utf-8');req.update(http_status=response.status_code,wall_s=time.perf_counter()-sent)
                if response.status_code!=200:
                    rec['status']='gateway_rejected_stop_all';write(folder/'result.json',rec);raise RuntimeError('Gateway rejection: stop sends and inspect actual incompatibility.')
                body=response.json();req.update(usage=body.get('usage'),response_id=body.get('id'),model=body.get('model'))
                message=body['choices'][0]['message'];messages.append(message)
                try:
                    text=message['content'].strip()
                    if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1])
                    call=json.loads(text)
                    if 'action' in call:call={'tool':'research_plan','arguments':call}
                    name,args=call['tool'],call['arguments']
                    if name=='research_plan':
                        jsonschema.Draft202012Validator(snapshot['tools'][0]['function']['parameters']).validate(args);Plan.model_validate(args);assert args.get('decision') is not None
                        rec.update(status='completed',decision=args,original_decision_text=message['content']);break
                    if name=='experience_retrieve':
                        query=ExperienceQuery.model_validate(args)
                        if query.operation=='read':
                            entry_key=query.entry_id or query.key or ''
                            if '@' not in entry_key:entry_key+='@'+str(query.revision or '1')
                            value=dict(status='available',results=[allowed[entry_key]['archived_result']]) if entry_key in allowed else dict(status='unavailable',reason='Entry is not permitted in this isolated session.')
                        else:value=dict(status='available',results=[e['archived_result'] for e in available])
                        rec['experience_reads'].append(dict(request=args,response=value))
                    elif name=='evidence_read':
                        EvidenceQuery.model_validate(args)
                        value=dict(status='unavailable',reason='No scientific candidate or raw execution artifact exists at this pre-candidate checkpoint. Task and family facts are already supplied; no experience or future artifact can be accessed through this reader.')
                    else:value=dict(status='unavailable',reason='This session only records a research_plan; scientific execution is disabled.')
                    messages.append(dict(role='user',content=name+' result: '+json.dumps(value,separators=(',',':'))))
                except (json.JSONDecodeError,jsonschema.ValidationError,ValueError,KeyError) as exc:
                    rec['errors'].append(type(exc).__name__+': '+str(exc)[:1500])
                    messages.append(dict(role='user',content='Invalid tool/Plan arguments: '+str(exc)[:1500]+'. Correct the existing Core Plan schema and submit research_plan; no research action is executed.'))
                write(folder/'result.json',rec)
                print(json.dumps(dict(event='request_complete',task_id=item['task_id'],turn=turn,repairs=len(rec['errors']),usage=req['usage'])),flush=True)
            rec.update(wall_s=time.perf_counter()-begun,provider_requests=len(rec['requests']));write(folder/'result.json',rec)
            if rec['status']!='completed':raise RuntimeError('Four-request cap reached; no extra replay permitted.')
            with output.open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n')
            with (RUN/'new_decisions.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False)+'\n')
            print(json.dumps(dict(event='KplusSplus_completed',task_id=item['task_id'],requests=rec['provider_requests'],repairs=len(rec['errors']))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);a=p.parse_args();{'prepare':prepare,'run':run}[a.mode]()
