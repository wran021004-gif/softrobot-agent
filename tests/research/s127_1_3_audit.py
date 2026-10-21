"""Derived delivery statistics only; never serialize raw Provider conversations."""
from copy import deepcopy
import json
import subprocess
from unittest.mock import patch
from tools.research.agent import decision_packet, plan_schema
from tools.research.research_context import context, decision_brief
from tools.research.state import state
from tools.research.contracts import EvidenceQuery
from tools.state_io import read, atomic_json, digest
from tools.research.config import ROOT
from tests.research.test_s127_working_set import historical_host
from tests.research.test_s127_layered_context import size


def layered():
    h=historical_host();before=digest(state(h));ledger=h.store.remaining();events=h.store.events(h.run_id)
    frozen=read(ROOT/'runs/s127_1_baseline.json')
    assert frozen['state_identity']==before and frozen['ledger']==ledger
    c=context(h);brief=decision_brief(c);packet=decision_packet(h)
    with patch('tools.research.research_context.decision_brief',return_value=frozen['brief']):old=decision_packet(h)
    # Exact serialized default request envelopes, using the saved Provider's parameters/schema.
    event=next(e for e in reversed(events) if e['kind']=='r3_request')
    wire=h.store.artifact(h.store.artifact(event['outputs'][0])['request'])
    envelopes=[]
    for p in (old,packet):
        request=deepcopy(wire)
        request['messages']=[dict(role='system',content=state(h)['spec']['execution_instructions']+
            '\nCURRENT_RESEARCH_PACKET\n'+json.dumps(p,separators=(',',':'))),
            dict(role='user',content='Choose the next research decision using this frozen state.')]
        envelopes.append(request)
    for tool in envelopes[1]['tools']:
        if tool['function']['name']=='evidence_read':tool['function']['parameters']=EvidenceQuery.model_json_schema()
        if tool['function']['name']=='research_plan':
            actions=tool['function']['parameters']['properties']['action']['enum']
            tool['function']['parameters']=plan_schema(actions,decision_required=True)
    envelopes[0]['tools']=deepcopy(envelopes[1]['tools'])
    out=dict(baseline='bd31326296afb6daace6db5afb1205daa8e01841',source_study=h.run_id,
        source_state_identity=before,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        old_decision_brief_bytes=size(frozen['brief']),new_decision_brief_bytes=size(brief),
        old_working_set_bytes=size(frozen['context']['evidence_working_set']),
        new_default_working_set_bytes=size(brief['evidence_working_set']),detailed_working_set_bytes=size(c['evidence_working_set']),
        old_default_request_json_bytes=size(envelopes[0]),new_default_request_json_bytes=size(envelopes[1]),
        tool_schema_bytes=[size(e['tools']) for e in envelopes],
        request_scope='Serialized default envelope at identical frozen state, same saved tool set and provider parameters; excludes accumulated chat. No HTTP request sent.',
        sections={k:size(v) for k,v in brief.items()},all_fresh_results=brief['all_fresh_results'],
        complete_stop_index_retained=brief['all_fresh_results']==frozen['brief']['all_fresh_results'],
        detail_tests='tests.research.test_s127_layered_context',
        new_provider_requests=0,new_scientific_executions=0,actual_prompt_tokens=None,
        actual_completion_tokens=None,actual_cache_hit_tokens=None,actual_cache_miss_tokens=None,
        provider_comparison='blocked_independent_current_round_transfer_and_request_authorization_required')
    assert before==digest(state(h)) and ledger==h.store.remaining() and events==h.store.events(h.run_id)
    atomic_json(ROOT/'evidence/s127_layered_context/audit.json',out)
    return out


def probe_inventory():
    from tools.platform_host import Host
    manifest=read(ROOT/'evidence/s127_decision_probe/manifest.json');h=Host(manifest['store'],manifest['run_id']);rows=[]
    assert len(manifest['cases'])==12
    for i in range(0,12,2):
        pair=manifest['cases'][i:i+2];a,b=[h.store.artifact(r['request']) for r in pair]
        assert a['tools']==b['tools']
        pa,pb=[json.loads(w['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n',1)[1])['research'] for w in (a,b)]
        assert pa['all_fresh_results']==pb['all_fresh_results'] and pa['task']==pb['task'] and pa['actions']==pb['actions']
        assert all(pa['budget'][k]==pb['budget'][k] for k in pa['budget'])
        for row in pair:assert digest(h.store.artifact(row['request']))==row['identity']
        rows.append(dict(name=pair[0]['name'],same_task_actions_budget_science_index_and_tools=True,
            all_fresh_result_count=len(pa['all_fresh_results']),wire_identities=[r['identity'] for r in pair],
            full_scientific_admission='not_tested',actual_tokens=None))
    atomic_json(ROOT/'evidence/s127_decision_probe/offline_checks.json',dict(tests=rows,
        frozen_manifest_identity=manifest['frozen_manifest_identity'],live_status='blocked_independent_authorization_required',
        metrics='No actual prompt/completion/cache tokens, legal proposal rates, evidence delivery counts or decision degradation measurements exist. Bytes are not tokens.'))


def s1274_decision():
    """Summarize actual provider usage; never write historical S12.7 evidence."""
    from tools.platform_host import Host
    from tools.research.agent import received
    folder=ROOT/'evidence/s127_4_decision';result=read(folder/'results.json')
    h=Host(ROOT/'runs/s127-4a-decision-20261021','s127-4a-decision-20261021')
    manifest=read(ROOT/'evidence/s127_decision_probe/manifest.json')
    fields=('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens')
    records=[]
    for row in result['cases']:
        reception=received(h,row['request_id']);body=json.loads(h.store.artifact(reception['body'],raw=True))
        assert body['usage']==row['usage']
        wire=next(c for c in manifest['cases'] if c['name']==row['name'] and c['arm']==row['arm'])
        choices=[]
        for call,check in zip(body['choices'][0]['message'].get('tool_calls',[]),row['checks']):
            q=json.loads(call['function']['arguments']);kind=call['function']['name']
            prerequisites=(
                'Actual local pointer/view read was checked; subsequent delivery and model use are outside this single-request arm.'
                if kind=='evidence_read' else
                'Formal execute still needs candidate/control/profile binding, full capability/novelty/guard preflight, NMPC/shared-backend/public-operation capacity and an owned settled worker receipt. Only original independent acceptance can establish physical success.'
                if q.get('action')=='execute' else
                'Control initialization still needs a registered candidate and exact source/parent, compatible measured task/model/grid/tendon order and force bounds, formal admission and a settled native operation receipt.'
                if q.get('action')=='initialize_control' else
                'STOP still needs all fresh scientific results explicitly cited, settled work and formal lifecycle admission; it is not a new scientific experiment.'
                if q.get('action')=='stop' else 'Full formal capability, ownership, budget and operation-specific admission remain untested.')
            choices.append(dict(tool=kind,action=q.get('action'),analysis=q.get('operation'),
                rl_mode=q.get('mode'),evidence_view=q.get('view') if kind=='evidence_read' else None,
                pointer=q.get('pointer') if kind=='evidence_read' else None,
                partial_checks=check['contract_and_reference_checks'],rejection=check.get('error'),
                full_scientific_admission='not_tested',remaining_preconditions=prerequisites))
        records.append(dict(name=row['name'],arm=row['arm'],request_id=row['request_id'],provider_response_id=row['provider_response_id'],
            actual_model=row['actual_model'],raw_body_reference=reception['body'],wire_identity=wire['identity'],
            schema_identity=row['tool_schema_identity'],usage=row['usage'],tools=choices,
            reasoning_tokens=row['usage'].get('completion_tokens_details',{}).get('reasoning_tokens'),
            finish_reason=body['choices'][0].get('finish_reason'),truncated=body['choices'][0].get('finish_reason')=='length',
            effective_new_evidence_deliveries=0,
            legal_scientific_proposal='not_tested',remaining_preconditions='Only contract/reference/budget subset checked. Actual construction, scientific ownership/admission and worker-specific prerequisites remain untested unless a read was actually performed locally.'))
    def totals(rows):
        return {arm:dict(requests=len(chosen),**{key:sum(r['usage'][key] for r in chosen)
            if chosen and all(r['usage'].get(key) is not None for r in chosen) else None for key in fields},
            reasoning_tokens=sum(r['reasoning_tokens'] for r in chosen) if chosen and all(r['reasoning_tokens'] is not None for r in chosen) else None,
            truncated_requests=sum(r['truncated'] for r in chosen),
            evidence_read_requests=sum(c['tool']=='evidence_read' for r in chosen for c in r['tools']),
            working_set_read_requests=sum(c['tool']=='evidence_read' and c['evidence_view']=='working_set' for r in chosen for c in r['tools']),
            partial_check_rejections=sum(c['partial_checks']=='rejected' for r in chosen for c in r['tools']),
            partially_checked_plan_proposals=sum(c['tool']=='research_plan' and c['partial_checks']=='passed' for r in chosen for c in r['tools']),
            full_scientific_admission='not_tested',effective_new_evidence_deliveries=0,
            unnecessary_detail_reads=None,critical_scientific_fact_omissions=None)
            for arm in ('s127_full','layered') for chosen in [[r for r in rows if r['arm']==arm]]}
    main=totals([r for r in records if r['name']!='independent_session_boundary'])
    pairs=[]
    for name in dict.fromkeys(r['name'] for r in records):
        pair=[r for r in records if r['name']==name]
        if len(pair)!=2:continue
        a,b=pair
        pairs.append(dict(name=name,experiment='separate_session_condition' if name=='independent_session_boundary' else 'layered_context_pair',
            tokens={r['arm']:r['usage'] for r in pair},
            prompt_token_reduction=a['usage']['prompt_tokens']-b['usage']['prompt_tokens'],
            total_token_reduction=a['usage']['total_tokens']-b['usage']['total_tokens']))
    report=dict(status=result['status'],actual_requests=len(records),request_ceiling=12,cases=records,pairs=pairs,
        compression_only=main,all_six_pairs_descriptive=totals(records),
        separate_session_condition=totals([r for r in records if r['name']=='independent_session_boundary']),
        sixth_pair_wire_identical_to_fifth={arm:manifest['cases'][8+i]['identity']==manifest['cases'][10+i]['identity']
            for i,arm in enumerate(('s127_full','layered'))},
        sixth_pair_limitation='Both arms repeat the exact fifth-pair request body with no old assistant/tool history. This is a separately sampled stateless condition with strongly warmed provider cache, not an actual different-history comparison or SDK recovery.',
        ledger=result['ledger'],new_scientific_executions=0,
        limitation='Six fixed states, one request per arm, no follow-up evidence feedback. Only first-request token cost and partial admission observed. No adaptive retrieval net-cost, complete scientific legality rate, factual non-degradation or study success-rate conclusion.',
        money_usd=None,source='Actual DeepSeek usage fields; no byte-to-token substitution or synthetic usage.')
    atomic_json(folder/'metrics.json',report)
    return report


def s1274_handoff():
    from tools.platform_host import Host
    from tools.research.agent import received,pending
    folder=ROOT/'evidence/s127_4_handoff';h=Host(ROOT/'runs/research/s127-4b-sdk-20261021','s127-4b-sdk-20261021')
    s=state(h);rows=[]
    for event in h.store.events(h.run_id):
        if event['kind']!='r3_request':continue
        reception=received(h,event['request_id'])
        body=json.loads(h.store.artifact(reception['body'],raw=True)) if reception else {}
        rows.append(dict(request_id=event['request_id'],http_status=reception['http_status'] if reception else None,
            body_reference=reception.get('body') if reception else None,usage=body.get('usage'),actual_model=body.get('model'),
            finish_reasons=reception.get('finish_reasons') if reception else None,
            raw_reasoning_preserved=bool((body.get('choices') or [{}])[0].get('message',{}).get('reasoning_content'))))
    value=read(folder/'live.json')
    truncated=any('length' in (r['finish_reasons'] or []) for r in rows)
    value.update(status='blocked' if truncated else 'observed',requests=rows,source_freeze=s['freeze'],
        block_reason='Old first SDK response exhausted the frozen 8192-token output cap with reasoning only; no tool call/complete round. Native submission was rejected. SDK wrapped the local truncation rejection as APIConnectionError despite HTTP 200.' if truncated else None,
        old_complete_tool_round=bool(value.get('old_complete_tool_round')),old_scientific_actions=len(s['candidates']),
        new_snapshot_persisted_and_reopened=bool(value.get('snapshot_independently_reopened')),
        framework_session_id=s['pilot']['framework_session_id'],handoff_committed=bool(s['pilot'].get('handoff')),
        unknown_provider_outcomes=len(pending(h)),known_saved_response_unconsumed=bool(s['pilot'].get('unconsumed_response')),
        budget_unchanged_ceiling=h.store.remaining()['limit'],production_flags_modified=False,
        further_requests_not_sent='Remaining five requests deliberately not sent across an incomplete old tool boundary. No retries, new grant, rewritten response, raised token cap or manual admission flag.',
        interpretation='Live scientific continuation not validated. Offline SDK clean-path and crash fixtures do not substitute for it.')
    atomic_json(folder/'live.json',value)
    return value


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--s1274-decision',action='store_true');parser.add_argument('--s1274-handoff',action='store_true');args=parser.parse_args()
    if args.s1274_handoff:
        result=s1274_handoff();print(json.dumps(dict(status=result['status'],reason=result['block_reason'],requests=result['requests'])))
    elif args.s1274_decision:
        result=s1274_decision();print(json.dumps(dict(status=result['status'],actual_requests=result['actual_requests'],totals=result['compression_only'])))
    else:
        result=layered();probe_inventory();print(json.dumps({k:v for k,v in result.items() if k.endswith('_bytes')}))
