"""Isolated handoff prototype. Never imported by the production Agent.

SDK snapshot completion and scientific Store settlement are distinct boundaries.
Real-provider admission remains separate from these synthetic protocol tests.
"""
import asyncio
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import httpx
from tools.platform_store import plain, zero
from tools.state_io import digest, atomic_json
from tools.research.agent import record, build_harness, LiveBoundary, live_model_class, DeepSeekModel
from tools.research.state import state, update
from tools.research.evidence_policy import registered_references
from tools.research.config import ROOT
from tests.research.test_s125_contract import cold_host as prepare_fixture


def cold_host():
    host=prepare_fixture()
    update(host,freeze='isolated_s126_protocol_fixture')
    return host


def checkpoint(host,boundary,*,interrupt=None):
    """Test-only atomic pointer switch; reject all unresolved work before writing."""
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state']
        prior=s['pilot'].get('handoff')
        if prior and host.store.artifact(prior)['completed_boundary']==boundary:return prior
        if s['research_status']=='stopped':raise ValueError('STOPPED')
        if s.get('success_gate'):raise ValueError('SELECT_REQUIRED')
        if s.get('pending') or s['pilot'].get('unconsumed_response'):raise ValueError('PENDING')
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:raise ValueError('UNSETTLED')
        if any(e.get('status',{}).get('worker_alive',True) for e in s.get('rl_runs',{}).values()):raise ValueError('WORKER')
        completed=host.store.artifact(boundary)
        if completed['session_id']!=s['pilot']['framework_session_id']:raise ValueError('STALE_BOUNDARY')
        if completed['source_state_identity']!=digest(s):raise ValueError('STATE_CHANGED')
        outstanding=set();seen=set()
        for message in completed['messages']:
            for block in message['content']:
                if 'toolUse' in block:
                    key=block['toolUse']['toolUseId']
                    if key in seen:raise ValueError('DUPLICATE_TOOL_ID')
                    outstanding.add(key);seen.add(key)
                if 'toolResult' in block:
                    key=block['toolResult']['toolUseId']
                    if key not in outstanding:raise ValueError('UNPAIRED_RESULT')
                    outstanding.remove(key)
        if outstanding:raise ValueError('MISSING_TOOL_RESULT')
        from tools.research.agent import decision_packet
        previous=s['pilot']['framework_session_id'];next_id='s126-'+digest(dict(previous=previous,boundary=boundary))[:20]
        hypotheses=[dict(reference=r,pointer='/original_plan',plan=host.store.artifact(r)['original_plan']) for r in s['plans']]
        value=dict(version='research_session_handoff_v1',study_id=host.run_id,implementation=s.get('freeze'),
            previous_session=previous,next_session=next_id,completed_boundary=boundary,
            source_state_identity=digest(s),source_state=plain(host.store.put(db,s)),
            candidate_index=list(s['candidates'].values()),registered_scientific_evidence=registered_references(host),
            open_hypotheses=hypotheses,packet=decision_packet(host),budget=host.store.remaining(db=db),pending_work=None)
        ref=host.store.put(db,value)
        if interrupt=='metadata':raise RuntimeError('INTERRUPT')
        s['pilot'].update(framework_session_id=next_id,handoff=plain(ref))
        host.store.update_state(db,host.run_id,s)
        host.store.event(db,host.run_id,'experimental_session_handoff','committed',outputs=[ref])
        return plain(ref)


def completed_boundary(host,messages):
    return record(host,'experimental_completed_invocation',dict(session_id=state(host)['pilot']['framework_session_id'],
        source_state_identity=digest(state(host)),messages=deepcopy(messages)))


class CheckpointTests(unittest.TestCase):
    def test_atomic_interrupt_idempotency_and_cumulative_state(self):
        h=cold_host();before=deepcopy(state(h));ledger=h.store.remaining()
        boundary=completed_boundary(h,[])
        with self.assertRaisesRegex(RuntimeError,'INTERRUPT'):checkpoint(h,boundary,interrupt='metadata')
        self.assertEqual(state(h),before)
        ref=checkpoint(h,boundary);self.assertEqual(checkpoint(h,boundary),ref)
        handoff=h.store.artifact(ref)
        self.assertEqual(handoff['source_state_identity'],digest(before))
        self.assertEqual(h.store.artifact(handoff['source_state']),before)
        self.assertEqual(h.store.remaining(),ledger)
        # Restart before first request recovers committed identity without another switch.
        self.assertEqual(state(h)['pilot']['framework_session_id'],handoff['next_session'])
        next_ref=checkpoint(h,completed_boundary(h,[]))
        self.assertNotEqual(next_ref,ref);self.assertEqual(h.store.remaining(),ledger)

    def test_unsafe_boundaries_fail_closed(self):
        cases=[dict(pending={'worker':'running'}),dict(research_status='stopped'),dict(success_gate={'selected':False}),
            dict(rl_runs={'job':{'status':{'worker_alive':True}}})]
        for changes in cases:
            h=cold_host();update(h,**changes);b=completed_boundary(h,[])
            with self.assertRaises(ValueError):checkpoint(h,b)
        h=cold_host();p=deepcopy(state(h)['pilot']);p['unconsumed_response']='saved';update(h,pilot=p)
        with self.assertRaisesRegex(ValueError,'PENDING'):checkpoint(h,completed_boundary(h,[]))
        h=cold_host();b=completed_boundary(h,[]);update(h,numerical_s=1.)
        with self.assertRaisesRegex(ValueError,'STATE_CHANGED'):checkpoint(h,b)
        h=cold_host();h.store.reserve(h.run_id,'unfinished',digest({}),h.actor,zero())
        with self.assertRaisesRegex(ValueError,'UNSETTLED'):checkpoint(h,completed_boundary(h,[]))
        h=cold_host();messages=[dict(role='assistant',content=[dict(toolUse=dict(toolUseId='orphan',name='x',input={}))])]
        with self.assertRaisesRegex(ValueError,'MISSING_TOOL_RESULT'):checkpoint(h,completed_boundary(h,messages))

    def test_sdk_complete_tool_round_restore_and_new_independent_session(self):
        from strands.tools.tools import PythonAgentTool
        from strands.tools.executors import SequentialToolExecutor
        h=cold_host();wires=[];responses=[]
        def respond(request):
            wires.append(json.loads(request.content))
            message=dict(role='assistant',content='Synthetic completed boundary',reasoning_content='Preserved fixture reasoning')
            if len(wires)==1:
                message.update(content=None,tool_calls=[dict(id='fixture-old-tool',type='function',
                    function=dict(name='fixture_echo',arguments='{}'))])
            body=dict(id='synthetic-'+str(len(wires)),object='chat.completion',created=1,model=state(h)['pilot']['provider']['model'],
                choices=[dict(index=0,message=message,finish_reason='tool_calls' if len(wires)==1 else 'stop')],
                usage=dict(prompt_tokens=11,completion_tokens=3,total_tokens=14))
            responses.append(body);return httpx.Response(200,json=body)
        async def exercise():
            transport=LiveBoundary(h,httpx.MockTransport(respond))
            tool=PythonAgentTool('fixture_echo',dict(name='fixture_echo',description='Synthetic protocol fixture',inputSchema={'json':dict(type='object',properties={})}),
                lambda use,**kw:dict(toolUseId=use['toolUseId'],status='success',content=[dict(text='Fixture only; no scientific observation')]))
            def build():return build_harness(h,transport=transport,api_key='synthetic',instructions='Synthetic protocol test',
                model_class=live_model_class(transport),tool_executor=SequentialToolExecutor(),research_tools=[tool],
                configuration_path=h.store.root/'fixture_configuration.json',session_directory=h.store.root/'fixture_sessions')
            old=build();await old.invoke_async('Run fixture tool and finish interaction')
            original=deepcopy(old.messages);self.assertEqual(len(wires),2)
            self.assertIn('reasoning_content',wires[1]['messages'][2])
            restored=build();self.assertEqual(restored.messages,original)
            ref=checkpoint(h,completed_boundary(h,original));handoff=h.store.artifact(ref)
            new=build();self.assertFalse(new.messages)
            await new.invoke_async('New independent conversation with authoritative state: '+json.dumps(handoff['packet']))
            self.assertEqual(old.messages,original)
            self.assertFalse(any(m.get('tool_call_id')=='fixture-old-tool' for m in wires[-1]['messages']))
            self.assertFalse(any(m.get('reasoning_content') for m in wires[-1]['messages']))
            self.assertEqual(h.store.remaining()['used']['model_calls'],3)
            self.assertFalse(state(h)['pilot'].get('unconsumed_response'))
            from tools.research.core import export
            export(h,h.store.root/'checkpoint_validation/study')
            atomic_json(h.store.root/'checkpoint_validation/offline.json',dict(status='offline_protocol_passed',
                formal_admission='not_admitted',reason='Real-provider continuation, actual usage and complete crash recovery admission remain untested',
                sdk='1.59.0',harness='0.2.0',session_manager='SnapshotSessionManager',
                original_message_identity=digest(original),handoff=ref,study_id=h.run_id,
                simulated_model_calls=3,new_provider_requests=0,new_scientific_executions=0,
                actual_token_savings=None,synthetic_usage_is_not_measurement=True))
            await transport.aclose()
        asyncio.run(exercise())

    def test_unknown_send_in_new_session_never_resends_or_rotates(self):
        h=cold_host();checkpoint(h,completed_boundary(h,[]));identity=state(h)['pilot']['framework_session_id']
        provider=state(h)['pilot']['provider'];sent=[]
        def fail(request):sent.append(request);raise httpx.ReadError('Synthetic unknown outcome')
        wire=dict(model=provider['model'],thinking=dict(type=provider['thinking']),reasoning_effort=provider['reasoning_effort'],
            max_tokens=provider['max_tokens'],stream=False,messages=[dict(role='user',content='Synthetic new session')])
        async def exercise():
            boundary=LiveBoundary(h,httpx.MockTransport(fail))
            request=lambda:httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire)
            with self.assertRaises(httpx.ReadError):await boundary.handle_async_request(request())
            with self.assertRaisesRegex(ValueError,'UNCONFIRMED'):await boundary.handle_async_request(request())
            with self.assertRaisesRegex(ValueError,'UNSETTLED'):checkpoint(h,completed_boundary(h,[]))
            self.assertEqual(len(sent),1);self.assertEqual(h.store.remaining()['used']['model_calls'],1)
            self.assertEqual(state(h)['pilot']['framework_session_id'],identity)
            await boundary.aclose()
        asyncio.run(exercise())


if __name__=='__main__':unittest.main()
