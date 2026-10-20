"""Killed-process SDK/Store audit. Synthetic HTTP and worker fixtures, no live science.

This deliberately tests the S12.6 prototype rather than enabling session rotation.
Store and filesystem interruption gaps remain production admission blockers.
"""
import asyncio
from copy import deepcopy
import json
import os
import subprocess
import sys
import unittest
import httpx
from tools.platform_host import Host
from tools.research.agent import build_harness, LiveBoundary, live_model_class
from tools.research.state import state, update
from tools.research.config import ROOT
from tools.state_io import atomic_json, digest, read
from tests.research.test_s126_checkpoint import cold_host, checkpoint, completed_boundary


def build(h,transport):
    from strands.tools.executors import SequentialToolExecutor
    return build_harness(h,transport=transport,api_key='synthetic-fixture',instructions='Offline protocol fixture',
        model_class=live_model_class(transport),tool_executor=SequentialToolExecutor(),research_tools=[],
        configuration_path=h.store.root/'s127_framework.json',session_directory=h.store.root/'s127_sessions')


def child(directory,run_id,mode):
    h=Host(directory,run_id,actor='unified-research');p=state(h)['pilot'];p['framework_session_id']='s127-old-'+digest(run_id)[:16];update(h,pilot=p)
    def response(request):
        return httpx.Response(200,json=dict(id='synthetic',object='chat.completion',created=1,model=p['provider']['model'],
            choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content='Offline boundary',reasoning_content='Immutable fixture reasoning'))],
            usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12)))
    async def exercise():
        transport=LiveBoundary(h,httpx.MockTransport(response));old=build(h,transport)
        await old.invoke_async('Complete fixture invocation')
        original=deepcopy(old.messages);boundary=completed_boundary(h,original)
        next_id='s126-'+digest(dict(previous=state(h)['pilot']['framework_session_id'],boundary=boundary))[:20]
        atomic_json(h.store.root/'s127_interruption.json',dict(mode=mode,boundary=boundary,original_messages=original,
            previous_session=state(h)['pilot']['framework_session_id'],next_session=next_id,ledger=h.store.remaining()))
        if mode=='prepare':os._exit(71)
        if mode=='snapshot_before_pointer':
            from strands_harness import create_harness
            new=create_harness(model=old.model,tools=[],builtin_tools=[],builtin_plugins=[],skills=False,memory=False,
                background_tasks=False,session=dict(id=next_id,dir=str(h.store.root/'s127_sessions')),callback_handler=None)
            await new._session_manager.save_snapshot(new,is_latest=True)
            os._exit(71)
        if mode in ('math_feedback_pending','physics_feedback_pending'):
            # Explicit worker-completion fixture; no mathematical or MuJoCo solve is claimed.
            atomic_json(h.store.root/'completed_fixture.json',dict(status='completed',fixture=True))
            update(h,pending=dict(kind='candidate_analysis' if mode.startswith('math') else 'physical_replay',fixture_completed=True))
            os._exit(71)
        if mode=='rl_running':update(h,rl_runs={'fixture':dict(status=dict(worker_alive=True))});os._exit(71)
        if mode=='pass_before_select':update(h,success_gate={'fixture':True});os._exit(71)
        if mode=='stopped':update(h,research_status='stopped');os._exit(71)
        checkpoint(h,boundary)
        if mode=='store_before_snapshot':os._exit(71)
        if mode=='committed':
            new=build(h,transport);await new._session_manager.save_snapshot(new,is_latest=True);os._exit(71)
        provider=state(h)['pilot']['provider']
        wire=dict(model=provider['model'],thinking=dict(type=provider['thinking']),reasoning_effort=provider['reasoning_effort'],
            max_tokens=provider['max_tokens'],stream=False,messages=[dict(role='user',content='Synthetic first new-session request')])
        atomic_json(h.store.root/'s127_first_wire.json',wire)
        def unknown(request):raise httpx.ReadError('Synthetic unknown outcome')
        boundary_transport=LiveBoundary(h,httpx.MockTransport(unknown if mode=='unknown_send' else response))
        try:await boundary_transport.handle_async_request(httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire))
        except httpx.ReadError:pass
        os._exit(71)
    asyncio.run(exercise())


class CrossProcessCheckpointTests(unittest.TestCase):
    def test_interruption_matrix_and_fail_closed_recovery(self):
        rows=[]
        modes=('prepare','store_before_snapshot','snapshot_before_pointer','committed','unknown_send','unconsumed_response',
            'math_feedback_pending','physics_feedback_pending','rl_running','pass_before_select','stopped')
        for mode in modes:
            with self.subTest(mode=mode):
                h=cold_host()
                process=subprocess.run([sys.executable,'-m','tests.research.test_s127_checkpoint','--child',str(h.store.root),h.run_id,mode],
                    cwd=ROOT,capture_output=True,text=True,timeout=45,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.assertEqual(process.returncode,71,process.stderr[-3000:])
                h=Host(h.store.root,h.run_id,actor='unified-research');info=read(h.store.root/'s127_interruption.json');s=state(h)
                # A separate process must restore exact old SDK messages and reasoning.
                original_id=s['pilot']['framework_session_id'];p=deepcopy(s['pilot']);p['framework_session_id']=info['previous_session'];update(h,pilot=p)
                new_files=[f for f in (h.store.root/'s127_sessions').rglob('*') if f.is_file() and info['next_session'] in str(f)]
                if mode=='store_before_snapshot':self.assertFalse(new_files)
                if mode in ('snapshot_before_pointer','committed'):self.assertTrue(new_files)
                transport=LiveBoundary(h,httpx.MockTransport(lambda r:(_ for _ in ()).throw(AssertionError('No HTTP send permitted'))))
                old=build(h,transport);self.assertEqual(old.messages,info['original_messages'])
                p=deepcopy(state(h)['pilot']);p['framework_session_id']=original_id;update(h,pilot=p)
                if mode in ('prepare','snapshot_before_pointer'):
                    self.assertEqual(original_id,info['previous_session'])
                elif mode in ('store_before_snapshot','committed'):
                    self.assertEqual(original_id,info['next_session'])
                    self.assertEqual(checkpoint(h,info['boundary']),s['pilot']['handoff'])
                    self.assertFalse(build(h,transport).messages)
                elif mode=='unconsumed_response':
                    wire=read(h.store.root/'s127_first_wire.json');ledger=h.store.remaining();provider=s['pilot']['provider']
                    async def replay():
                        for _ in range(2):
                            answer=await transport.handle_async_request(httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire))
                            self.assertEqual(answer.status_code,200)
                        await transport.aclose()
                    asyncio.run(replay());self.assertEqual(h.store.remaining(),ledger)
                    with self.assertRaisesRegex(ValueError,'PENDING'):checkpoint(h,completed_boundary(h,[]))
                else:
                    with self.assertRaises(ValueError):checkpoint(h,completed_boundary(h,[]))
                    if mode=='unknown_send':
                        async def blocked_send():
                            wire=read(h.store.root/'s127_first_wire.json');provider=s['pilot']['provider']
                            with self.assertRaisesRegex(ValueError,'UNCONFIRMED'):
                                await transport.handle_async_request(httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire))
                            await transport.aclose()
                        asyncio.run(blocked_send())
                self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
                rows.append(dict(mode=mode,killed_process=True,original_history_restored=True,external_provider_requests=0,
                    synthetic_provider_charges=h.store.remaining()['used']['model_calls'],new_scientific_executions=0))
        destination=ROOT/'evidence/s127_checkpoint';destination.mkdir(parents=True,exist_ok=True)
        atomic_json(destination/'admission.json',dict(status='not_admitted',production_rotation=False,tests=rows,
            blockers=['Prototype commits Store pointer before validating a new SDK snapshot; killed-process test confirms this gap.',
                'Pending completed-worker fixtures fail closed, but real scientific recovery and feedback replay across a new SDK conversation are not validated.',
                'No independently authorized real-provider continuation or executable new-session scientific decision test.'],
            scope='Actual Strands SDK snapshots and Store reopened across processes; HTTP/usage and completion markers are synthetic, not scientific evidence or measured token savings.'))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':child(*sys.argv[2:])
    else:unittest.main()
