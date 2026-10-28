"""Real SDK/Mock HTTP checks; scripted replies are fixtures, not model decisions."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
import httpx
from jsonschema import Draft202012Validator
from tools.research import agent
from tools.research.config import validate_conversation_policy
from tools.research.research_context import research_action_trace, research_recall, bounded_action_trace, read_coverage
from tools.research.session_handoff import rotation_ready
from tools.research.state import state, update, save
from tests.research import test_request_boundary_handoff as boundary_tests

POLICY=dict(version='recent_round_trace_v1',trace_limit=8)
TOOLS=dict(version='on_demand_tools_v1')


def provision(*,tools=True):
    h=boundary_tests.RequestBoundaryHandoffTests().provision();s=state(h);spec=deepcopy(s['spec'])
    spec['research_decisions'].update(architecture='english_decision_v1',conversation_policy=deepcopy(POLICY))
    if tools:spec['research_decisions']['tool_schema_policy']=deepcopy(TOOLS)
    update(h,spec=spec)
    return h


def run_fixture(h, responses, *, limit=None):
    sent=[]
    def respond(request):
        wire=json.loads(request.content);sent.append(wire);n=len(sent)-1
        if n>=len(responses):raise AssertionError('Unexpected extra model request')
        use=responses[n]
        message=dict(role='assistant',content='Offline fixture feedback consumed.')
        if use:
            name,payload=use
            message.update(content=None,tool_calls=[dict(id='offline-use-'+str(n),type='function',
                function=dict(name=name,arguments=json.dumps(payload)))])
        return httpx.Response(200,json=dict(id='offline-response-'+str(n),object='chat.completion',created=1,
            model=wire['model'],choices=[dict(index=0,finish_reason='tool_calls' if use else 'stop',message=message)],
            usage=dict(prompt_tokens=10,completion_tokens=4,total_tokens=14)))
    with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
            patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
            patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)):
        asyncio.run(agent.converse(h,max_new_provider_requests=limit,pause_after_completed_invocations=1))
    return sent


class RecentRoundToolTests(unittest.TestCase):
    def test_directory_only_then_one_selected_tool_and_reuse(self):
        h=provision();ref=state(h)['public_prior_manifest']
        read=dict(reference=ref,view='summary')
        wires=run_fixture(h,[('research_route',dict(tool='evidence_read')),
            ('evidence_read',read),('evidence_read',read),
            ('research_route',dict(tool='research_plan',action='diagnose')),None])
        names=lambda w:{t['function']['name'] for t in w['tools']}
        self.assertEqual(names(wires[0]),{'research_route'})
        for w in wires[1:4]:self.assertEqual(names(w),{'research_route','evidence_read'})
        self.assertEqual(names(wires[4]),{'research_route','research_plan'})
        schema=next(t['function']['parameters'] for t in wires[4]['tools'] if t['function']['name']=='research_plan')
        self.assertEqual(schema['properties']['action']['enum'],['diagnose'])
        self.assertNotIn('generation',schema['properties']);self.assertNotIn('search',schema['properties'])
        self.assertNotIn('ControlSearchRequest',schema['$defs'])
        self.assertIn('hypothesis',schema['required'])
        packets=[json.loads(w['messages'][-1]['content'].split('\n',1)[1])['research'] for w in wires]
        self.assertTrue(packets[0]['tool_directory']);self.assertIn('history_trace',packets[-1])
        self.assertTrue(packets[2]['recent_round'])
        # The original native calls stay in Store, not subsequent SDK messages.
        for w in wires[1:]:self.assertFalse(any(m.get('tool_calls') or m['role']=='tool' for m in w['messages']))
        self.assertEqual(h.store.remaining()['used']['model_calls'],5)
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        events=h.store.events(h.run_id)
        self.assertEqual(sum(e['kind']=='research_tool_route' for e in events),2)
        self.assertEqual(sum(e['kind']=='session_handoff' and e['status']=='committed' for e in events),4)
        # Exact registry and snapshot recovery needs no additional request.
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'):
            asyncio.run(agent.converse(h,restore_only=True))
        self.assertEqual(h.store.remaining()['used']['model_calls'],5)

    def test_recall_is_stable_bounded_and_never_awards_full_read(self):
        h=provision(tools=False)
        invalid=dict(action='stop')
        run_fixture(h,[('research_plan',invalid),None])
        trace=research_action_trace(h,limit=None);self.assertEqual(trace['total'],1)
        step=trace['recent'][0]['step'];before=read_coverage(h)
        summary=research_recall(h,dict(step=step));detail=research_recall(h,dict(step=step,view='details'))
        self.assertFalse(summary['scientific_result']);self.assertEqual(summary['execution_status'],'rejected')
        self.assertFalse(detail['formal_read_credit']);self.assertEqual(before,read_coverage(h))
        self.assertEqual(research_action_trace(h,limit=None)['recent'][0]['step'],step)
        self.assertEqual(summary['source']['reference'],trace['recent'][0]['feedback_source']['reference'])
        many={**trace,'total':200,'recent':[{**trace['recent'][0],'step':i+1} for i in range(200)]}
        compact=bounded_action_trace(many,8)
        self.assertEqual(len(compact['recent']),8);self.assertLessEqual(len(compact['unresolved']),2)
        self.assertEqual(research_recall(h,dict(limit=1))['items'][0]['step'],step)

    def test_automatic_rotation_defers_worker_and_rejects_unpaired_history(self):
        h=provision();s=state(h)
        update(h,rl_runs={'fixture':dict(active_reservation=True,status=dict(worker_alive=True))})
        self.assertFalse(rotation_ready(h,[]))
        update(h,rl_runs=s.get('rl_runs',{}))
        with self.assertRaisesRegex(ValueError,'MISSING_TOOL_RESULT'):
            rotation_ready(h,[dict(role='assistant',content=[dict(toolUse=dict(toolUseId='unpaired',name='evidence_read',input={}))])])
        pilot=deepcopy(state(h)['pilot']);pilot['unconsumed_response']='unknown-fixture';update(h,pilot=pilot)
        self.assertFalse(rotation_ready(h,[]))

    def test_versioning_and_focused_stop_keep_required_science(self):
        validate_conversation_policy({})
        for policy in (dict(version='wrong',trace_limit=8),dict(version=POLICY['version'],trace_limit=100)):
            with self.assertRaises(ValueError):validate_conversation_policy(dict(architecture='english_decision_v1',conversation_policy=policy))
        with self.assertRaises(ValueError):validate_conversation_policy(dict(architecture='english_decision_v1',tool_schema_policy=TOOLS))
        schema=agent.plan_schema(['stop'],decision_required=True,focused=True)
        self.assertIn('hypothesis',schema['required']);self.assertNotIn('generation',schema['properties'])
        with self.assertRaises(Exception):Draft202012Validator(schema).validate(dict(action='stop',decision={}))

    def test_explicit_full_result_reaches_main_through_rotation(self):
        h=provision(tools=False)
        ref=save(h,dict(status='offline_fixture',values=list(range(1500))),'large_exact_read_fixture')
        wires=run_fixture(h,[('evidence_read',dict(reference=ref,view='full')),None])
        # Explicit original full reads bypass compact-feedback size limits.
        packet=json.loads(wires[1]['messages'][-1]['content'].split('\n',1)[1])['research']
        self.assertEqual(packet['research_state']['pending_feedback']['items'][0]['delivery'],'exact_feedback')
        row=next(r for r in read_coverage(h) if r['tool_call_id']=='offline-use-0')
        self.assertTrue(row['successfully_provided']);self.assertTrue(row['full_artifact'])

    def test_protected_directory_rejects_scientific_route(self):
        h=provision();update(h,count_closeout=True)
        wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='diagnose')),None])
        self.assertEqual([t['function']['name'] for t in wires[1]['tools']],['research_route'])
        self.assertNotIn('tool_route',state(h)['pilot'])
        self.assertFalse(any(e['kind']=='original_research_plan' for e in h.store.events(h.run_id)))

    def test_saved_route_response_replays_with_original_schema_without_charge(self):
        h=provision()
        def interrupted(boundary):
            if boundary.last_request:raise RuntimeError('offline after durable response')
        with patch.object(agent.LiveBoundary,'require_complete',new=interrupted):
            with self.assertRaisesRegex(Exception,'offline after durable response'):
                run_fixture(h,[('research_route',dict(tool='evidence_read'))])
        self.assertTrue(state(h)['pilot'].get('unconsumed_response'))
        self.assertNotIn('tool_route',state(h)['pilot'])
        wires=run_fixture(h,[None])
        self.assertEqual(len(wires),1)
        self.assertEqual({t['function']['name'] for t in wires[0]['tools']},{'research_route','evidence_read'})
        self.assertEqual(h.store.remaining()['used']['model_calls'],2)
        self.assertEqual(sum(e['kind']=='r3_request' for e in h.store.events(h.run_id)),2)

    def test_route_receipt_recovers_missing_feedback_without_reexecution(self):
        h=provision();record=agent.record
        def interrupted(host,kind,value,*args,**kwargs):
            if kind=='model_original_tool_feedback':raise RuntimeError('offline after route receipt')
            return record(host,kind,value,*args,**kwargs)
        with patch('tools.research.agent.record',side_effect=interrupted):
            with self.assertRaisesRegex(Exception,'offline after route receipt'):
                run_fixture(h,[('research_route',dict(tool='evidence_read'))])
        self.assertIn('tool_route',state(h)['pilot'])
        wires=run_fixture(h,[None])
        self.assertEqual(len(wires),1)
        self.assertEqual(sum(e['kind']=='research_tool_route' for e in h.store.events(h.run_id)),1)
        self.assertTrue(any(e['kind']=='model_original_tool_feedback' and h.store.artifact(e['outputs'][0]).get('recovered_from_receipt') for e in h.store.events(h.run_id)))


if __name__=='__main__':unittest.main()
