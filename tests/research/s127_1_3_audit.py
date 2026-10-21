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


if __name__=='__main__':
    result=layered();probe_inventory();print(json.dumps({k:v for k,v in result.items() if k.endswith('_bytes')}))
