"""Synthetic transport verifies shared reservation and non-dispatch; no live calls."""
import asyncio
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from uuid import uuid4
import httpx
from tools.platform_store import Store,zero
from tools.research.decision_comparison import prepare_shared_probe,execute_shared_probe,nonthinking_wire
from tools.research.state import update
from tools.state_io import digest


class SharedProbeTests(unittest.TestCase):
    def setUp(self):
        folder=Path('runs')/('probe-fixture-'+uuid4().hex)
        self.addCleanup(shutil.rmtree,folder,ignore_errors=True)
        store=Store(folder/'store')
        budget=dict(tool_calls=28,model_calls=8,backend_solves=1,worker_calls=0,wall_s=None)
        store.create(dict(project_id='probe-'+uuid4().hex,grant_id='grant-'+uuid4().hex,purpose='development',
            authorization_source='synthetic fixture',budget=budget,exclusive_resources={'provider_request':1}))
        store.create_session(dict(input=dict(run_id='parent',policy=dict(budget=budget))))
        self.source=SimpleNamespace(store=store,run_id='parent')
        provider=dict(base_url='https://api.deepseek.com',model='deepseek-flash',thinking='enabled',reasoning_effort='high',
            max_tokens=100,adapter='deepseek',context_guard=dict(context_limit_tokens=100000,framing_headroom_tokens=10))
        update(self.source,spec={'budgets':{'protected_provider_requests':2}},pilot={'provider':provider,'live_model_requests':5},pending=None)
        for i in range(5):
            row,_=store.reserve('parent',str(i),'hash','fixture',{**zero(),'model_calls':1},resources=['provider_request'])
            store.complete(row,dict(request_id=str(i),execution_id=row['execution_id'],caller='fixture',tool_id='model.deepseek',tool_version='1.0.0',execution_status='completed',charged=zero()))
        wire=dict(model='deepseek-flash',thinking={'type':'enabled'},reasoning_effort='high',max_tokens=100,stream=False,messages=[{'role':'user','content':'fixture'}],tools=[])
        self.baseline=dict(wire=wire,request_id='baseline',original_request_identity=digest(wire),packet={},response={'choices':[{'finish_reason':'stop','message':{}}]})

    def test_one_success_is_charged_to_parent_and_project_without_science(self):
        child=prepare_shared_probe(self.source,self.baseline,'probe')
        sent=[]
        def answer(request):
            sent.append(request)
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'fixture'}}],'usage':{'prompt_tokens':3,'completion_tokens':2}})
        result=asyncio.run(execute_shared_probe(self.source,child,self.baseline,'fixture-secret',transport=httpx.MockTransport(answer)))
        self.assertEqual(len(sent),1)
        self.assertEqual(sent[0].read(),__import__('json').dumps(nonthinking_wire(self.baseline['wire']),ensure_ascii=False,separators=(',',':')).encode())
        self.assertEqual(result['validation']['status'],'complete')
        self.assertEqual(self.source.store.remaining()['remaining']['model_calls'],2)
        self.assertEqual(self.source.store.remaining('parent')['remaining']['model_calls'],2)
        self.assertEqual(self.source.store.remaining('probe')['used']['tool_calls'],0)
        with self.assertRaisesRegex(ValueError,'NO_RETRY'):
            asyncio.run(execute_shared_probe(self.source,child,self.baseline,'fixture-secret',transport=httpx.MockTransport(answer)))
        self.assertEqual(len(sent),1)

    def test_source_change_blocks_before_send_and_reservation(self):
        child=prepare_shared_probe(self.source,self.baseline,'probe')
        update(self.source,changed=True)
        def answer(request):raise AssertionError('must not send')
        with self.assertRaisesRegex(ValueError,'SOURCE_STATE_CHANGED_OR_BUSY'):
            asyncio.run(execute_shared_probe(self.source,child,self.baseline,'fixture-secret',transport=httpx.MockTransport(answer)))
        self.assertEqual(self.source.store.remaining()['used']['model_calls'],5)

    def test_unknown_transport_keeps_charge_and_blocks_retry(self):
        child=prepare_shared_probe(self.source,self.baseline,'probe')
        def fail(request):raise httpx.ConnectError('fixture')
        with self.assertRaises(httpx.ConnectError):
            asyncio.run(execute_shared_probe(self.source,child,self.baseline,'fixture-secret',transport=httpx.MockTransport(fail)))
        self.assertEqual(self.source.store.remaining()['remaining']['model_calls'],2)
        with self.assertRaisesRegex(ValueError,'NO_RETRY'):
            asyncio.run(execute_shared_probe(self.source,child,self.baseline,'fixture-secret',transport=httpx.MockTransport(fail)))
