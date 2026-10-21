"""Local live-evidence audit; publish only derived statistics and exact references."""
from collections import Counter,defaultdict
from copy import deepcopy
import json
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state
from tools.research.agent import pending,received,provider_outcome
from tools.research.evidence_policy import registered_references
from tools.state_io import read,atomic_json,digest
from tests.research.s126_decision_probe import frozen_s127


def audit_a(final=False):
    out=ROOT/'evidence/s127_6_decision'
    scope=read(out/'scope.json');manifest=read(out/'manifest.json')
    source=Host(manifest['store'],manifest['run_id'])
    h=Host(ROOT/'runs/s127-6a-decision-20261021','s127-6a-decision-20261021')
    s=state(h);es=h.store.events(h.run_id);rows=read(out/'results.json')['cases'] if (out/'results.json').exists() else []
    sends=[e for e in es if e['kind']=='r3_request'];totals=defaultdict(Counter);groups=defaultdict(list);calls=[];deliveries=[];delivered_ids=set()
    assert len(sends)<=18 and h.store.remaining()['limit']['model_calls']==18
    for row in rows:
        event=next(e for e in sends if e['request_id']==row['request_id'])
        wire=h.store.artifact(h.store.artifact(event['outputs'][0])['request'])
        reception=received(h,row['request_id']);body=json.loads(h.store.artifact(reception['body'],raw=True))
        assert digest(wire)==row['wire_identity'] and wire['max_tokens']==65536
        assert wire['model']=='deepseek-flash' and wire['thinking']==dict(type='enabled') and wire['reasoning_effort']=='high'
        assert reception['http_status']==200 and body['choices'][0]['finish_reason'] in ('stop','tool_calls')
        case=next(c for c in manifest['cases'] if c['name']==row['name'] and c['arm']==row['arm'])
        frozen=frozen_s127(source,case);known=registered_references(frozen)
        key=(row['name'],row['arm']);usage=row['usage'];groups[key].append(row)
        delivered_ids.update((row['name'],row['arm'],m['tool_call_id']) for m in wire['messages'] if m['role']=='tool')
        for field in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'):
            totals[row['arm']][field]+=usage.get(field,0)
        totals[row['arm']]['reasoning_tokens']+=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
        totals[row['arm']]['requests']+=1
        if row['turn']:
            previous=next(r for r in rows if r['name']==row['name'] and r['arm']==row['arm'] and r['turn']==row['turn']-1)
            feedback=h.store.artifact(previous['feedback_reference'])['feedback']
            actual=[m for m in wire['messages'] if m['role']=='tool']
            assert all(m in actual for m in feedback)
            previous_reception=received(h,previous['request_id'])
            previous_body=json.loads(h.store.artifact(previous_reception['body'],raw=True))
            original_message=previous_body['choices'][0]['message']
            assert original_message in wire['messages']
            deliveries.append(dict(name=row['name'],arm=row['arm'],turn=row['turn'],tool_feedback_count=len(feedback),
                unchanged_original_reasoning_and_tool_ids=True,feedback_delivered_exactly=True))
        feedback_messages=h.store.artifact(row['feedback_reference'])['feedback']
        for call,check,feedback_message in zip(body['choices'][0]['message'].get('tool_calls',[]),row['checks'],feedback_messages):
            q=json.loads(call['function']['arguments']);name=call['function']['name']
            entry=dict(name=row['name'],arm=row['arm'],turn=row['turn'],tool=name,action=q.get('action'),
                tool_use_id=call['id'],
                full_execution_admission=check['full_execution_admission'],status=check['status'],error_code=check['error_code'],
                request_id=row['request_id'],feedback_identity=check['feedback_identity'])
            if check['status']=='rejected':
                rejection=json.loads(feedback_message['content'])
                detail=rejection.get('feedback',rejection)
                entry['rejection']={k:detail[k] for k in ('error_code','field','expected','error') if k in detail}
            if name=='evidence_read':
                entry.update(reference=q['reference'],pointer=q.get('pointer',''),view=q.get('view','full'),
                    registered_for_citation=q['reference'] in known,query_identity=digest(q),actual_store_read=check['actual_store_read'])
            else:
                d=q.get('decision') or {};entry.update(selected_method=d.get('selected_method'),
                    selected_candidate=d.get('selected_candidate',q.get('candidate')),requested_budget=d.get('requested_budget'),
                    claimed_inference=d.get('claimed_inference'),supporting_evidence=q.get('supporting_evidence',[]))
                if q.get('mechanics'):entry['mechanics_initialization']=q['mechanics'].get('initialization')
                if q.get('control_seed'):entry['control_seed_method']=q['control_seed'].get('method')
                if q.get('control_search'):entry['control_search_method']=q['control_search']['settings']['method']
                if q.get('operation'):entry['operation']=q['operation']
            calls.append(entry)
    for c in calls:c['feedback_delivered_to_model']=(c['name'],c['arm'],c['tool_use_id']) in delivered_ids
    reads=[c for c in calls if c['tool']=='evidence_read'];repeated=[]
    counts=Counter((c['name'],c['arm'],c['query_identity']) for c in reads)
    for (name,arm,query),count in counts.items():
        if count>1:repeated.append(dict(name=name,arm=arm,query_identity=query,count=count))
    sequences=[dict(name=name,arm=arm,requests=len(rs),prompt_tokens_by_round=[r['usage']['prompt_tokens'] for r in rs],
        completion_tokens_by_round=[r['usage']['completion_tokens'] for r in rs],
        evidence_read_proposals=sum(c['tool']=='evidence_read' for c in calls if c['name']==name and c['arm']==arm),
        successful_store_reads=sum(c.get('actual_store_read',False) for c in calls if c['name']==name and c['arm']==arm),
        followup_requests_with_tool_feedback=sum(d['tool_feedback_count']>0 for d in deliveries if d['name']==name and d['arm']==arm))
        for (name,arm),rs in groups.items()]
    result=dict(stage='S12.7.6A',status='completed' if len(rows)==18 else 'partial',request_ceiling=18,
        actual_requests=len(sends),processed_responses=len(rows),actual_tokens_by_arm=dict(totals),
        provider_usage_is_actual=True,new_numerical_executions=0,new_physical_launches=0,
        sequences=sequences,feedback_deliveries=deliveries,tool_proposals=calls,
        citation_errors=sum(c.get('error_code')=='UNREGISTERED_RESEARCH_EVIDENCE' for c in calls),
        successful_evidence_reads=sum(c['actual_store_read'] for c in reads),
        registered_evidence_reads=sum(c['actual_store_read'] and c['registered_for_citation'] for c in reads),
        successful_evidence_reads_delivered_to_model=sum(c['actual_store_read'] and c['feedback_delivered_to_model'] for c in reads),
        registered_evidence_reads_delivered_to_model=sum(c['actual_store_read'] and c['registered_for_citation'] and c['feedback_delivered_to_model'] for c in reads),
        exact_repeated_reads=repeated,
        full_admission_passed=sum(c['full_execution_admission']=='passed' for c in calls),
        numerical_prelaunch_passed=sum(c['full_execution_admission']=='prelaunch_passed' for c in calls),
        rejected_proposals=sum(c['status']=='rejected' for c in calls),
        uncertainty='One sample per arm/state; no statistical superiority, global scientific efficacy, model understanding or absent-fact causality claim. Numerical prelaunch checks are not executed experiments. Repeated reads are counted exactly; value requires scientific interpretation.',
        pending_provider_count=len(pending(h)),saved_unconsumed_response=s['pilot'].get('unconsumed_response'),ledger=h.store.remaining(),
        authorization_scope_identity=digest(scope),raw_requests_responses_reasoning_local_only=True)
    if final:
        assert len(rows)==len(sends)==18 and not pending(h) and not s['pilot'].get('unconsumed_response')
        assert len({r['wire_identity'] for r in rows})==18
        with h.store.connect(True) as db:assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0
        a=totals['full'];b=totals['layered']
        result['paired_prompt_reduction_fraction']=1-b['prompt_tokens']/a['prompt_tokens']
        result['paired_total_token_reduction_fraction']=1-b['total_tokens']/a['total_tokens']
        atomic_json(out/'metrics.json',result)
    return result


def audit_b():
    out=ROOT/'evidence/s127_6_handoff';result=read(out/'live.json')
    h=Host(ROOT/'runs/research/s127-6b-sdk-20261021','s127-6b-sdk-20261021')
    s=state(h);events=h.store.events(h.run_id);scope=read(out/'scope.json')
    preparation=h.store.artifact(s['pilot']['handoff'])
    before=h.store.artifact(preparation['source_state']);ledger=h.store.remaining()
    assert read(out/'offline.json')['offline_protocol_passed']
    assert result['mode']=='live' and result['new_provider_requests']<=12
    assert result['live_old_tool_round_passed'] and result['live_sdk_continuation_passed'] and result['live_scientific_action_passed']
    assert preparation['next_session']==s['pilot']['framework_session_id']
    assert not pending(h) and not s['pilot'].get('unconsumed_response') and not s['pending']
    assert not before['research_history'] and not before['research_mathematics']
    assert not s['spec']['research_decisions']['history'] and not s['spec']['research_decisions']['mathematics'] and not s['spec']['research_decisions']['control_seeds']
    assert all(s['candidates'].get(k)==v for k,v in before['candidates'].items())
    assert all(ledger['used'][k]>=preparation['budget']['used'][k] for k in ledger['used'])
    assert not s['pilot'].get('session_handoff_live_admitted')
    assert s['spec']['runtime']['provider']['max_tokens']==65536
    with h.store.connect(True) as db:assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0
    from tools.research.session_handoff import unmatched
    old_messages=h.store.artifact(preparation['completed_boundary'])['messages']
    assert not unmatched(old_messages) and digest(old_messages)==preparation['completed_boundary_identity']
    assert all(m['role']=='user' and all(set(b)=={'text'} for b in m['content']) for m in preparation['initial_messages'])
    totals=Counter();requests=[];raw_calls={};deliveries={}
    for event in events:
        if event['kind']!='r3_request':continue
        wire=h.store.artifact(h.store.artifact(event['outputs'][0])['request'])
        reception=received(h,event['request_id']);body=json.loads(h.store.artifact(reception['body'],raw=True))
        assert reception['http_status']==200 and wire['max_tokens']==65536 and wire['model']==scope['model']
        assert body['choices'][0]['finish_reason'] in ('stop','tool_calls')
        usage=body['usage']
        for k in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'):totals[k]+=usage.get(k,0)
        totals['reasoning_tokens']+=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
        for call in body['choices'][0]['message'].get('tool_calls',[]):
            assert call['id'] not in raw_calls
            raw_calls[call['id']]=dict(name=call['function']['name'],input=json.loads(call['function']['arguments']))
        for message in wire['messages']:
            if message['role']=='tool':deliveries[message['tool_call_id']]=message['content']
        requests.append(dict(request_id=event['request_id'],wire_identity=digest(wire),body=reception['body'],actual_model=body.get('model'),
            finish_reason=body['choices'][0]['finish_reason'],usage=usage,
            input_tool_feedback_count=sum(m['role']=='tool' for m in wire['messages'])))
    assert len({r['wire_identity'] for r in requests})==len(requests)
    feedback={};errors=[]
    for event in events:
        if event['kind']=='model_original_tool_request':
            use=h.store.artifact(event['outputs'][0])['tool_use']
            assert raw_calls[use['toolUseId']]==dict(name=use['name'],input=use['input'])
        if event['kind']=='model_original_tool_feedback':
            value=h.store.artifact(event['outputs'][0]);use=value['tool_use'];response=value['result']
            if response['status']=='success':feedback[use['toolUseId']]=''.join(b.get('text','') for b in response['content'])
            else:
                text=''.join(b.get('text','') for b in response['content'])
                try:detail=json.loads(text)
                except ValueError:detail=dict(error_code='SDK_TOOL_VALIDATION_ERROR',feedback_format='sdk_text')
                errors.append(dict(tool_use_id=use['toolUseId'],tool=use['name'],
                    **{k:detail[k] for k in ('error_code','field','expected') if k in detail}))
    actual_actions=[]
    for row in result['real_tool_actions']:
        if row['name']!='research_plan':continue
        key='native-'+row['id'];receipt=json.loads(h.store.lookup(h.run_id,key)['receipt'])
        assert receipt['execution_status']=='completed' and row['id'] in raw_calls
        original_feedback=feedback[row['id']];delivered=deliveries.get(row['id'])
        if delivered==original_feedback:feedback_mode='full'
        else:
            from strands._context_manager.methods.truncate import _build_preview
            expected=_build_preview(original_feedback,1,dict(preview_tokens=500))+'\n\n[Stashed] [ref: '+row['id']+'_0]'
            assert delivered==expected
            feedback_mode='exact_configured_offload_preview'
        value=h.store.artifact(row['value'])['result']
        identity=value.get('source') or value.get('candidate')
        if identity:assert identity['artifact_id'] in delivered
        actual_actions.append(dict(phase=row['phase'],action=row['action'],tool_use_id=row['id'],
            result_reference=row['value'],candidate=value.get('candidate'),source=value.get('source'),
            receipt_execution_id=receipt['execution_id'],feedback_delivered_to_model=True,raw_provider_tool_call_matches=True,
            feedback_delivery_mode=feedback_mode,complete_tool_feedback_characters=len(original_feedback),
            delivered_tool_feedback_characters=len(delivered),complete_original_feedback_preserved=True))
    assert any(r['phase']=='old' for r in actual_actions) and any(r['phase']=='new' for r in actual_actions)
    assert len({r['tool_use_id'] for r in actual_actions})==len(actual_actions)
    new_actions=[r for r in actual_actions if r['phase']=='new']
    for action in new_actions:
        if action['action']=='initialize_control':assert action['source'] not in [c['source'] for c in before.get('control_initializations',[])]
        if action['action']=='generate':assert action['candidate'] not in list(before['candidates'].values())
    value=dict(stage='S12.7.6B',status='live_clean_handoff_and_scientific_action_verified',
        offline_protocol_passed=True,live_old_tool_round_passed=True,live_sdk_continuation_passed=True,
        live_scientific_action_passed=True,production_recovery_validated=False,production_handoff_admitted=False,
        production_scope='Clean live handoff and two actual tool rounds verified. Original crash/recovery tests are offline; no production admission flag or mechanism is changed by this isolated test.',
        requests=requests,actual_usage=dict(totals),actual_provider_requests=len(requests),request_ceiling=12,
        old_session_requests=preparation['budget']['used']['model_calls'],
        new_session_requests=len(requests)-preparation['budget']['used']['model_calls'],
        new_physical_launches=0,task_pass_demonstrated=False,historical_scientific_evidence_imported=False,
        production_flags_modified=False,
        actions=actual_actions,tool_errors=errors,candidate_identities_preserved=True,cumulative_ledger=ledger,
        old_tools_and_feedback_paired=True,old_reasoning_preserved=True,new_initial_context_has_no_old_chat=True,
        new_sdk_snapshot_independently_reopened=result['snapshot_independently_reopened'],
        old_framework_session=preparation['previous_session'],new_framework_session=preparation['next_session'],
        source_state_identity=preparation['source_state_identity'],handoff_reference=s['pilot']['handoff'],
        no_unsettled_receipts=True,no_unknown_provider_outcomes=True,no_duplicate_old_actions=True,
        independent_authorization_scope_identity=digest(scope),raw_data_local_only=True)
    atomic_json(out/'live_audit.json',value)
    return value


async def reopen_b():
    """Run in a fresh process; restore both actual SDK sessions without sending."""
    import httpx
    from strands.tools.executors import SequentialToolExecutor
    from strands.tools.tools import PythonAgentTool
    from tools.research.agent import build_harness,live_model_class,plan_schema,LiveBoundary
    from tools.research.contracts import EvidenceQuery
    from tools.research.session_handoff import validate_snapshot,unmatched
    out=ROOT/'evidence/s127_6_handoff';h=Host(ROOT/'runs/research/s127-6b-sdk-20261021','s127-6b-sdk-20261021')
    before=deepcopy(state(h));ledger=h.store.remaining();events=h.store.events(h.run_id)
    value=h.store.artifact(before['pilot']['handoff']);directory=h.store.root/'sdk'
    def forbidden(*args,**kwargs):raise AssertionError('READ_ONLY_REOPEN_FORBIDS_PROVIDER_AND_TOOLS')
    boundary=LiveBoundary(h,httpx.MockTransport(forbidden))
    tools=[PythonAgentTool(name,dict(name=name,description=description,inputSchema={'json':schema}),forbidden)
        for name,description,schema in [('research_plan','Execute one legal bounded scientific Plan or STOP',
            plan_schema(before['spec']['allowed_plan_actions'],decision_required=True)),
            ('evidence_read','Read own exact immutable evidence',EvidenceQuery.model_json_schema())]]
    def build(session_id):
        agent=build_harness(h,transport=boundary,api_key='no-send-read-only-reopen',
            instructions=before['spec']['execution_instructions'],model_class=live_model_class(boundary),
            tool_executor=SequentialToolExecutor(),research_tools=tools,configuration_path=h.store.root/'framework_configuration.json',
            session_directory=directory,session_id=session_id)
        agent.tool_registry.registry.pop('retrieve_context',None)
        return agent
    old=build(value['previous_session'])
    assert digest(old.messages)==value['completed_boundary_identity'] and not unmatched(old.messages)
    new=await validate_snapshot(h,before['pilot']['handoff'],build,directory)
    turns=[h.store.artifact(e['outputs'][0]) for e in events if e['kind']=='model_original_turn']
    last=next(t for t in reversed(turns) if t['session_id']==value['next_session'])
    assert digest(new.messages)==last['sdk_message_identity'] and not unmatched(new.messages)
    sdk_reasoning=[''.join(b['reasoningContent'].get('reasoningText',{}).get('text','')
        for b in m['content'] if 'reasoningContent' in b) for m in old.messages if m['role']=='assistant']
    old_sends=[e for e in events if e['kind']=='r3_request'][:value['budget']['used']['model_calls']]
    reasoning_count=0
    for event in old_sends:
        reception=received(h,event['request_id']);body=json.loads(h.store.artifact(reception['body'],raw=True))
        reasoning=body['choices'][0]['message'].get('reasoning_content')
        if reasoning:assert reasoning in sdk_reasoning;reasoning_count+=1
    new_reasoning=[''.join(b['reasoningContent'].get('reasoningText',{}).get('text','')
        for b in m['content'] if 'reasoningContent' in b) for m in new.messages if m['role']=='assistant']
    new_reasoning_count=0
    for event in [e for e in events if e['kind']=='r3_request'][len(old_sends):]:
        reception=received(h,event['request_id']);body=json.loads(h.store.artifact(reception['body'],raw=True))
        reasoning=body['choices'][0]['message'].get('reasoning_content')
        if reasoning:assert reasoning in new_reasoning;new_reasoning_count+=1
    assert state(h)==before and h.store.remaining()==ledger and h.store.events(h.run_id)==events
    result=dict(independent_fresh_process_reopen=True,old_sdk_message_identity=digest(old.messages),
        new_sdk_message_identity=digest(new.messages),old_reasoning_messages_verified=reasoning_count,
        new_reasoning_messages_verified=new_reasoning_count,
        old_tool_ids_and_results_paired=True,new_tool_ids_and_results_paired=True,
        same_store_session_pointer=True,store_state_ledger_and_events_unchanged=True,
        new_provider_requests=0,new_tool_executions=0,credentials_not_loaded=True)
    atomic_json(out/'live_reopen.json',result)
    await boundary.aclose()
    return result


def delivery():
    """Combine existing checks; do not authorize or start an S12.8 Study."""
    import subprocess
    from tools.research.state import science_hashes
    from tools.research.agent import provider_outcome
    a=audit_a(True);b=audit_b();out=ROOT/'evidence/s127_6_handoff'
    reopened=read(out/'live_reopen.json');assert reopened['independent_fresh_process_reopen']
    original=Host(ROOT/'runs/research/s126-cold-live-20261020','s126-cold-live-20261020')
    assert digest(state(original))=='d366a9a2791a6d35d881ca5c11bf82c182e03c38b912536ce8b900dfb071b5f3'
    assert state(original)['profile']['science_hashes']==science_hashes()
    old=Host(ROOT/'runs/research/s127-4b-sdk-20261021','s127-4b-sdk-20261021')
    old_diagnosis=read(ROOT/'evidence/s127_5_provider/classification.json')
    assert digest(state(old))==old_diagnosis['source_state_identity']
    assert old.store.remaining()==old_diagnosis['source_ledger']
    assert provider_outcome(old,state(old)['pilot']['unconsumed_response'])==old_diagnosis['provider']
    unchanged=subprocess.check_output(['git','diff','--name-only','f351104d','--','tasks','extensions','schemas',
        'configs/research/runtime.json','evidence/s126_cold','evidence/s127_4_decision','evidence/s127_4_handoff',
        'evidence/s127_session_recovery'],cwd=ROOT,text=True)
    assert not unchanged.strip(),unchanged
    previous=read(out/'verification.json');tests=set(previous['unique_test_ids'])
    tests.add('tests.research.test_s127_6_validation.NewValidationTests.test_read_only_resume_rejects_unresolved_or_scientifically_changed_prefix')
    raw=(ROOT/'runs/s127_6_read_only_resume_tests.log').read_bytes()
    log=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    assert 'Ran 5 tests' in log and '\nOK' in log and 'FAILED (' not in log
    total=Counter(b['actual_usage'])
    for values in a['actual_tokens_by_arm'].values():
        total.update({k:v for k,v in values.items() if k!='requests'})
    token_rows=[r['usage'] for r in read(ROOT/'evidence/s127_6_decision/results.json')['cases']]
    token_rows += [r['usage'] for r in b['requests']]
    assert a['actual_requests']==18 and b['actual_provider_requests']==11 and total['total_tokens']==1106209
    result=dict(status='live_decisions_and_clean_sdk_scientific_continuation_verified',
        unique_passing_test_count=len(tests),unique_test_ids=sorted(tests),killed_process_subscenarios=14,
        actual_provider_requests=29,authorized_provider_ceiling=30,actual_provider_usage=dict(total),
        max_observed_completion_tokens=max(r['completion_tokens'] for r in token_rows),
        max_observed_prompt_tokens=max(r['prompt_tokens'] for r in token_rows),
        largest_observed_prompt_plus_reserved_output_and_framing=max(r['prompt_tokens'] for r in token_rows)+65536+8192,
        frozen_context_limit_tokens=1000000,length_truncations=0,new_physical_launches=0,new_numerical_worker_launches=0,
        duplicate_provider_sends=0,unknown_provider_outcomes=0,unsettled_provider_receipts=0,
        original_s126_state_and_budgets_unchanged=True,old_s127_4b_confirmed_incomplete_state_unchanged=True,
        original_task_evaluator_scientific_dependencies_and_production_runtime_unchanged=True,
        offline_protocol_passed=True,live_old_tool_round_passed=True,live_sdk_continuation_passed=True,
        live_scientific_action_passed=True,independent_new_process_sdk_restore_passed=True,
        production_recovery_validated=False,production_handoff_admitted=False,production_flags_modified=False,
        handoff_scope='Isolated clean boundary, generation/control initialization and actual persisted SDK restore. Full production entry remains gated; no manual flag is set.',
        s128_started=False,raw_provider_sdk_store_data_uploaded=False,
        driver_resume_test_log='runs/s127_6_read_only_resume_tests.log',
        base_offline_verification_identity=digest(previous))
    atomic_json(out/'live_verification.json',result)
    preflight=read(ROOT/'evidence/s127_8_preflight/preflight.json')
    admission=dict(status='ready_for_separate_bounded_cold_start_authorization_using_continuous_strands',
        engineering_basis='Confirmed truncation is blocked accurately, live feedback is consumed, formal admission guards work, and the original continuous SDK path remains available.',
        science_success_proven=False,decision_quality_non_degradation_proven=False,
        session_strategy='Use the existing continuous Strands session with layered evidence and 65536 output in a NEW frozen configuration. Production session handoff stays off.',
        clean_live_handoff_demonstrated=True,production_handoff_admitted=False,
        residual_conditions=['A scientific proposal can still fail Schema or point at the wrong artifact; preserve deterministic rejection and repair feedback.',
            'The three-round comparison does not include a fourth correction after last-round errors. No claim that all three layered states produced a legal action.',
            'No new independent physical success, PPO selection, complete method superiority or structural infeasibility was demonstrated.',
            '96 future calls are not guaranteed to fit one context; keep per-send output reservation, actual usage audit and honest bounded closeout.'],
        proposed_budget=preflight['s128_proposal'],
        original_task='tasks/reach_hold_mirror_v1.json',initial_scientific_history='empty',
        historical_candidates_controls_math_results_or_successes_may_be_imported=False,
        independent_provider_and_scientific_budget_authorization_required=True,new_study_started=False)
    atomic_json(ROOT/'evidence/s127_8_preflight/admission.json',admission)
    return result


if __name__=='__main__':
    import sys
    if '--delivery' in sys.argv:
        result=delivery();print(json.dumps({k:result[k] for k in ('status','unique_passing_test_count','actual_provider_requests','actual_provider_usage','s128_started')}))
    elif '--reopen-b' in sys.argv:
        import asyncio
        print(json.dumps(asyncio.run(reopen_b())))
    elif '--b' in sys.argv:
        result=audit_b();print(json.dumps({k:result[k] for k in ('status','actual_provider_requests','actual_usage','actions')}))
    else:
        result=audit_a('--final' in sys.argv)
        print(json.dumps({k:result[k] for k in ('status','actual_requests','processed_responses','actual_tokens_by_arm','citation_errors','successful_evidence_reads','full_admission_passed','numerical_prelaunch_passed','rejected_proposals')}))
