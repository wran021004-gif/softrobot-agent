"""Real SDK/Store process crashes; synthetic HTTP is explicitly not live science."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from uuid import uuid4
import httpx
from schemas.platform import ProjectConfig
from tools.platform_host import Host
from tools.research.agent import build_harness, LiveBoundary, live_model_class, record
from tools.research.session_handoff import handoff, reconcile, recover_feedback, unmatched
from tools.research.state import state, update
from tools.research.config import ROOT
from tools.state_io import atomic_json, read, digest
from tests.research.test_s126_checkpoint import cold_host
from tests.research.test_s127_working_set import historical_host


def response(request):
    wire=json.loads(request.content)
    return httpx.Response(200,json=dict(id='offline-fixture',object='chat.completion',created=1,model=wire['model'],
        choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content='Completed offline boundary',reasoning_content='Retained fixture reasoning'))],
        usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12)))


def factory(h,transport):
    from strands.tools.executors import SequentialToolExecutor
    def build(session_id=None):
        return build_harness(h,transport=transport,api_key='offline-fixture',instructions='Offline protocol, no scientific executor',
            model_class=live_model_class(transport),tool_executor=SequentialToolExecutor(),research_tools=[],
            configuration_path=h.store.root/'framework.json',session_directory=h.store.root/'sdk',session_id=session_id)
    return build


def child(directory,run_id,mode):
    h=Host(directory,run_id,actor='unified-research')
    async def exercise():
        transport=LiveBoundary(h,httpx.MockTransport(response));build=factory(h,transport);old=build()
        await old.invoke_async('Complete the offline fixture')
        atomic_json(h.store.root/'crash.json',dict(previous=state(h)['pilot']['framework_session_id'],
            messages=old.messages,ledger=h.store.remaining(),mode=mode))
        if mode in ('math_pending','physics_pending'):update(h,pending=dict(kind=mode,fixture=True))
        if mode=='rl_running':update(h,rl_runs={'fixture':dict(status=dict(worker_alive=True))})
        if mode=='pass_before_select':update(h,success_gate=dict(fixture=True))
        if mode=='stopped':update(h,research_status='stopped')
        if mode in ('math_pending','physics_pending','rl_running','pass_before_select','stopped'):os._exit(71)
        if mode=='writing_snapshot':
            from strands.storage import LocalFileStorage
            original=LocalFileStorage.write
            async def interrupted(storage,key,data):
                if 'rh-' in key:
                    await original(storage,key,b'{"partial":');os._exit(71)
                return await original(storage,key,data)
            LocalFileStorage.write=interrupted
        def stage(name):
            if name==mode and mode!='writing_snapshot':os._exit(71)
        ref,new=await handoff(h,old,build,h.store.root/'sdk',stage=stage)
        if mode=='repeat':
            await handoff(h,new,build,h.store.root/'sdk')
            repeated,_=await handoff(h,old,build,h.store.root/'sdk')
            assert repeated==ref
            os._exit(71)
        provider=state(h)['pilot']['provider']
        wire=dict(model=provider['model'],thinking=dict(type=provider['thinking']),reasoning_effort=provider['reasoning_effort'],
            max_tokens=provider['max_tokens'],stream=False,messages=[dict(role='user',content='Offline new-session fixture')])
        atomic_json(h.store.root/'wire.json',wire)
        def unknown(request):raise httpx.ReadError('Offline unknown send')
        boundary=LiveBoundary(h,httpx.MockTransport(unknown if mode=='unknown_send' else response))
        try:await boundary.handle_async_request(httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire))
        except httpx.ReadError:pass
        os._exit(71)
    asyncio.run(exercise())


def replica():
    """Independent protocol grant; copy exact saved science/receipts, execute none."""
    old=historical_host();name='s127-recovery-replica-'+uuid4().hex
    h=Host(ROOT/'runs'/name,old.run_id,actor='unified-research');config=old.store.config()
    config.update(project_id=name,grant_id=name,authorization_source='Current task: offline isolated recovery replay of actual saved science, no new scientific execution or external transmission')
    h.store.create(ProjectConfig.model_validate(config))
    with old.store.connect(True) as source,h.store.transaction() as target:
        for table in ('artifacts','sessions','calls','events'):
            rows=source.execute('SELECT * FROM '+table).fetchall()
            if rows:target.executemany('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in rows[0])+')',[tuple(r) for r in rows])
    update(h,research_status='ready')  # Explicit protocol fixture reopens no scientific work.
    return h


def feedback_child(directory,run_id):
    h=Host(directory,run_id,actor='unified-research')
    async def recover():
        def forbidden(request):raise AssertionError('Saved feedback recovery must not send HTTP')
        transport=LiveBoundary(h,httpx.MockTransport(forbidden));agent=factory(h,transport)()
        count=await recover_feedback(h,agent)
        atomic_json(h.store.root/'recovered_feedback.json',dict(count=count,ledger=h.store.remaining()))
        os._exit(71)
    asyncio.run(recover())


class SessionRecoveryTests(unittest.TestCase):
    def test_optional_checkpoint_failure_keeps_original_safe_conversation(self):
        from unittest.mock import patch
        from tools.research.agent import converse
        h=cold_host();p=deepcopy(state(h)['pilot']);p['session_handoff_live_admitted']=True;update(h,pilot=p)
        previous=p['framework_session_id'];sent=[]
        def respond(request):
            sent.append(request)
            if len(sent)==2:update(h,research_status='stopped')
            return response(request)
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline-fixture'}),\
             patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
             patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)),\
             patch('tools.research.session_handoff.handoff',side_effect=ValueError('Offline checkpoint failure')):
            asyncio.run(converse(h,session_handoff=True))
        self.assertEqual(len(sent),2);self.assertEqual(state(h)['pilot']['framework_session_id'],previous)
        self.assertTrue(any(e['kind']=='session_handoff_not_committed' for e in h.store.events(h.run_id)))
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_live_handoff_is_closed_before_credentials_or_send(self):
        from tools.research.agent import converse
        from unittest.mock import patch
        h=cold_host()
        with patch('tools.research.agent.load_credential',side_effect=AssertionError('No credential access')):
            with self.assertRaisesRegex(ValueError,'LIVE_PROVIDER_CONTINUATION_UNVERIFIED'):
                asyncio.run(converse(h,session_handoff=True))

    def test_killed_process_matrix(self):
        modes=('before_prepare','prepared','writing_snapshot','snapshot_saved','verified','committed',
            'unknown_send','unconsumed_response','math_pending','physics_pending','rl_running','pass_before_select','stopped','repeat')
        rows=[]
        for mode in modes:
            with self.subTest(mode=mode):
                h=cold_host()
                process=subprocess.run([sys.executable,'-m','tests.research.test_s127_session_recovery','--child',str(h.store.root),h.run_id,mode],
                    cwd=ROOT,capture_output=True,text=True,timeout=55,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.assertEqual(process.returncode,71,process.stderr[-3000:])
                h=Host(h.store.root,h.run_id,actor='unified-research');info=read(h.store.root/'crash.json');s=state(h)
                def forbidden(request):raise AssertionError('No new HTTP send permitted')
                transport=LiveBoundary(h,httpx.MockTransport(forbidden));build=factory(h,transport)
                self.assertEqual(build(info['previous']).messages,info['messages'])
                async def check():
                    current=await reconcile(h,build,h.store.root/'sdk')
                    if mode in ('committed','unknown_send','unconsumed_response','repeat'):
                        self.assertIsNotNone(current)
                        self.assertNotEqual(s['pilot']['framework_session_id'],info['previous'])
                        if mode in ('committed','repeat'):
                            ref,_=await handoff(h,current,build,h.store.root/'sdk');self.assertEqual(ref,s['pilot']['handoff'])
                    else:
                        self.assertIsNone(current);self.assertEqual(s['pilot']['framework_session_id'],info['previous'])
                        if mode in ('prepared','snapshot_saved','verified'):
                            await handoff(h,build(info['previous']),build,h.store.root/'sdk')
                            self.assertIsNotNone(await reconcile(h,build,h.store.root/'sdk'))
                        elif mode=='writing_snapshot':
                            with self.assertRaises(Exception):await handoff(h,build(info['previous']),build,h.store.root/'sdk')
                        elif mode!='before_prepare':
                            with self.assertRaises(ValueError):await handoff(h,build(info['previous']),build,h.store.root/'sdk')
                    if mode in ('unknown_send','unconsumed_response'):
                        wire=read(h.store.root/'wire.json');provider=s['pilot']['provider'];ledger=h.store.remaining()
                        for _ in range(2):
                            request=httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire)
                            if mode=='unknown_send':
                                with self.assertRaisesRegex(ValueError,'UNCONFIRMED'):await transport.handle_async_request(request)
                            else:self.assertEqual((await transport.handle_async_request(request)).status_code,200)
                        self.assertEqual(h.store.remaining(),ledger)
                        ref,_=await handoff(h,build(info['previous']),build,h.store.root/'sdk')
                        self.assertEqual(ref,s['pilot']['handoff']);self.assertEqual(h.store.remaining(),ledger)
                    await transport.aclose()
                asyncio.run(check())
                self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
                if mode not in ('unknown_send','unconsumed_response'):self.assertEqual(h.store.remaining(),info['ledger'])
                rows.append(dict(mode=mode,killed_process=True,reopened_sdk_and_store=True,new_science=0,external_requests=0,
                    max_sdk_path_chars=max(len(str(p)) for p in (h.store.root/'sdk').rglob('*.json'))))
        self.assertEqual(len(rows),len(modes))
        atomic_json(ROOT/'runs/s127_4_recovery/crash_matrix.json',dict(tests=rows,
            offline_protocol_passed=True,production_recovery_validated=False,live_provider_continuation_unverified=True,
            scope='Real SDK and process termination. HTTP usage and pending-worker markers are fixtures; no scientific execution is claimed.'))

    def test_committed_snapshot_loss_and_changed_preparation_fail_closed(self):
        h=cold_host();transport=LiveBoundary(h,httpx.MockTransport(response));build=factory(h,transport)
        async def exercise():
            old=build();await old.invoke_async('Complete fixture')
            def changed(stage):
                if stage=='verified':update(h,numerical_s=state(h)['numerical_s']+1.)
            with self.assertRaisesRegex(ValueError,'CHANGED'):await handoff(h,old,build,h.store.root/'sdk',stage=changed)
            self.assertEqual(state(h)['pilot']['framework_session_id'],old._session_manager.session_id)
            await transport.aclose()
        asyncio.run(exercise())
        h=cold_host();transport=LiveBoundary(h,httpx.MockTransport(response));build=factory(h,transport)
        async def missing():
            old=build();await old.invoke_async('Complete fixture');ref,new=await handoff(h,old,build,h.store.root/'sdk')
            ledger=h.store.remaining()
            await new.invoke_async('Complete a second offline invocation')
            second,new=await handoff(h,new,build,h.store.root/'sdk')
            self.assertNotEqual(second,ref)
            self.assertEqual(h.store.remaining()['used']['model_calls'],ledger['used']['model_calls']+1)
            from types import SimpleNamespace
            def wrong_schema(session_id):
                restored=build(session_id)
                restored.tool_registry.registry['fixture_unexpected']=SimpleNamespace(tool_spec=dict(name='fixture_unexpected',description='Schema mismatch fixture',inputSchema={'json':dict(type='object',properties={})}))
                return restored
            with self.assertRaisesRegex(ValueError,'SCHEMA'):await reconcile(h,wrong_schema,h.store.root/'sdk')
            latest=next((h.store.root/'sdk'/'session'/state(h)['pilot']['framework_session_id']).rglob('snapshot_latest.json'))
            latest.write_text('{"corrupted":',encoding='utf8')
            with self.assertRaises(Exception):await reconcile(h,build,h.store.root/'sdk')
            self.assertEqual(state(h)['pilot']['framework_session_id'],new._session_manager.session_id)
            latest.unlink()
            with self.assertRaisesRegex(ValueError,'MISSING'):await reconcile(h,build,h.store.root/'sdk')
            await transport.aclose()
        asyncio.run(missing())

    def test_real_saved_math_and_physics_feedback_recover_without_worker(self):
        rows=[]
        for kind in ('mathematics','physics'):
            h=replica();events=h.store.events(h.run_id)
            uses=[h.store.artifact(e['outputs'][0])['tool_use'] for e in events if e['kind']=='model_original_tool_request']
            use=next(u for u in uses if u['name']=='research_analysis' and h.store.lookup(h.run_id,'native-'+u['toolUseId']+'-analysis')) if kind=='mathematics' else next(u for u in uses if u['name']=='research_plan' and u['input'].get('action')=='physical_replay')
            # Simulate crash after real worker settlement but before original tool feedback save.
            with h.store.transaction() as db:
                for e in events:
                    if e['kind']=='model_original_tool_feedback' and h.store.artifact(e['outputs'][0])['tool_use']==use:
                        db.execute('DELETE FROM events WHERE seq=?',(e['sequence'],))
            ledger=h.store.remaining();transport=LiveBoundary(h,httpx.MockTransport(response));build=factory(h,transport)
            async def exercise():
                old=build();old.messages=[dict(role='user',content=[dict(text='Offline original invocation prefix')]),
                    dict(role='assistant',content=[dict(reasoningContent=dict(reasoningText=dict(text='Fixture prefix; actual tool ID and receipt'))),dict(toolUse=use)])]
                await old._session_manager.save_snapshot(old,is_latest=True)
                process=subprocess.run([sys.executable,'-m','tests.research.test_s127_session_recovery','--recover-feedback',str(h.store.root),h.run_id],
                    cwd=ROOT,capture_output=True,text=True,timeout=55,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.assertEqual(process.returncode,71,process.stderr[-3000:])
                self.assertEqual(read(h.store.root/'recovered_feedback.json')['count'],1)
                old=build();self.assertFalse(unmatched(old.messages))
                self.assertEqual(await recover_feedback(h,build()),0)
                self.assertEqual(h.store.remaining(),ledger)
                with self.assertRaisesRegex(ValueError,'CONSUMED'):await handoff(h,old,build,h.store.root/'sdk')
                # Consume in original SDK with synthetic HTTP, then start independent SDK context.
                restored=build();await restored.invoke_async('Consume the recovered original tool feedback')
                ref,new=await handoff(h,restored,build,h.store.root/'sdk')
                self.assertEqual(len(new.messages),1);saved=h.store.artifact(ref)
                self.assertEqual(saved['scientific_results'],state(h)['results']+state(h)['mechanics_results']+state(h)['physical_replays']+state(h).get('matched_state_results',[])+state(h).get('rl_evaluations',[])+state(h)['analysis_results'])
                for result in saved['scientific_results']:h.store.artifact(result)
                self.assertEqual(h.store.remaining()['used']['backend_solves'],ledger['used']['backend_solves'])
                self.assertEqual(h.store.remaining()['used']['model_calls'],ledger['used']['model_calls']+1)
                await transport.aclose()
                return saved['scientific_results']
            refs=asyncio.run(exercise());rows.append(dict(kind=kind,original_tool_id=use['toolUseId'],scientific_results=refs,
                exact_saved_scientific_receipts=True,new_scientific_executions=0,external_requests=0,synthetic_consumption_requests=1))
        atomic_json(ROOT/'runs/s127_4_recovery/saved_worker_recovery.json',dict(tests=rows,
            scope='Actual saved S12.6 scientific receipts in independent protocol grants. Invocation prefixes and HTTP are fixtures; no live Provider continuation or repeated worker computation.'))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':child(*sys.argv[2:])
    elif len(sys.argv)>1 and sys.argv[1]=='--recover-feedback':feedback_child(*sys.argv[2:])
    else:unittest.main()
