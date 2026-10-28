"""Synthetic ledger tests; no real Provider, physics, T1, or study mutation."""
import asyncio,json
from copy import deepcopy
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4
from tools.platform_store import Store,zero
from tools.research.state import update
from tests.research import p2_feedback_paired as paired
from tests.research import p2_feedback_modes as modes
from tools.state_io import digest
import httpx


class PairedAuthorizationTests(unittest.TestCase):
    def setUp(self):
        folder=Path('runs')/('p2-paired-fixture-'+uuid4().hex);self.addCleanup(shutil.rmtree,folder,ignore_errors=True)
        store=Store(folder/'store');budget=dict(model_calls=8,tool_calls=28,backend_solves=1,worker_calls=0,wall_s=None)
        run='p2-fixture';store.create(dict(project_id=run,grant_id=uuid4().hex,purpose='development',
            authorization_source='synthetic',budget=budget,exclusive_resources={'provider_request':1}))
        store.create_session(dict(input=dict(run_id=run,policy=dict(budget=budget))))
        self.h=SimpleNamespace(store=store,run_id=run,actor='fixture')
        self.candidate={'artifact_id':'a'*64,'media_type':'application/json'};self.source={'artifact_id':'b'*64,'media_type':'application/json'}
        spec=dict(resolved_identity='fixture',budgets=dict(provider_requests=8,protected_provider_requests=2),
            configuration=dict(policy=dict(budget=budget)),runtime={})
        update(self.h,spec=spec,profile={'science_hashes':{}},freeze='fixture-old-commit',research_status='ready',pending=None,
            pilot={'provider':{},'live_model_requests':6},control_initializations=[dict(candidate=self.candidate,source=self.source,task_acceptance='unmeasured')])
        for i in range(6):
            row,_=store.reserve(run,str(i),'hash','fixture',{**zero(),'model_calls':1},resources=['provider_request'])
            store.complete(row,dict(request_id=str(i),execution_id=row['execution_id'],caller='fixture',tool_id='model.deepseek',tool_version='1.0.0',execution_status='completed',charged=zero()))
        for name,value in [('RUN',run),('BASELINE_ID','fixture'),('CANDIDATE',self.candidate),('SOURCE',self.source)]:
            p=patch.object(paired,name,value);p.start();self.addCleanup(p.stop)
        for name,value in [('clean_commit',lambda:'fixture-commit'),('science_hashes',lambda:{}),
                           ('execution_environment',lambda spec:{'status':'ready'}),('guard',lambda h:None)]:
            p=patch.object(paired,name,value);p.start();self.addCleanup(p.stop)
        p=patch.object(paired.core,'bind');p.start();self.addCleanup(p.stop)

    def test_authorization_extends_existing_grant_and_preserves_history(self):
        before=self.h.store.remaining()['used']
        result=paired.authorize(self.h)
        self.assertEqual(self.h.store.remaining()['limit']['model_calls'],13)
        self.assertEqual(self.h.store.remaining('p2-fixture')['limit']['model_calls'],13)
        self.assertEqual(self.h.store.remaining()['used'],before)
        current=self.h.store.session('p2-fixture')['state']
        self.assertEqual(current['spec']['budgets']['protected_provider_requests'],4)
        self.assertEqual(self.h.store.artifact(result['addendum'])['original_protected'],2)
        self.assertEqual(self.h.store.artifact(result['addendum'])['previous_ledger']['used'],before)
        with self.assertRaisesRegex(ValueError,'NO_REPEAT'):paired.authorize(self.h)

    def test_pending_source_refuses_before_extension(self):
        update(self.h,pending={'fixture':'uncertain'})
        with self.assertRaisesRegex(ValueError,'SETTLED_SOURCE'):paired.authorize(self.h)
        self.assertEqual(self.h.store.remaining()['limit']['model_calls'],8)

    def test_supervised_t1_outer_public_charge_is_append_only_and_once(self):
        row,_=self.h.store.reserve('p2-fixture',paired.T1_KEY+'-analysis','fixture','fixture',zero())
        self.h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller='fixture',
            tool_id='research.candidate_analysis',tool_version='1.0.0',execution_status='completed',charged=zero()))
        original=self.h.store.lookup('p2-fixture',paired.T1_KEY+'-analysis')['receipt']
        paired.account_t1_public(self.h)
        self.assertEqual(self.h.store.remaining()['used']['tool_calls'],1)
        self.assertEqual(self.h.store.lookup('p2-fixture',paired.T1_KEY+'-analysis')['receipt'],original)
        with self.assertRaisesRegex(ValueError,'ALREADY_RECORDED'):paired.account_t1_public(self.h)
        self.assertEqual(self.h.store.remaining()['used']['tool_calls'],1)

    def test_matched_arms_share_feedback_and_preserve_both_closeout_pools(self):
        paired.authorize(self.h)
        provider=dict(base_url='https://api.deepseek.com',model='deepseek-flash',thinking='enabled',reasoning_effort='high',
            max_tokens=100,adapter='deepseek',context_guard=dict(context_limit_tokens=100000,framing_headroom_tokens=10))
        update(self.h,pilot={'provider':provider,'live_model_requests':6})
        wire=dict(model='deepseek-flash',thinking={'type':'enabled'},reasoning_effort='high',max_tokens=100,stream=False,
            messages=[{'role':'user','content':'identical real feedback fixture'}],tools=[])
        bundle=dict(wire=wire,packet={'research':{'actions':[]}},t1={'artifact_id':'c'*64,'media_type':'application/json'},
            parent_state_identity=digest(self.h.store.session('p2-fixture')['state']))
        arms={'on':'fixture-on','off':'fixture-off'};sent=[]
        def reply(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'fixture'}}],'usage':{'prompt_tokens':3,'completion_tokens':2}})
        with patch.object(modes,'RUN','p2-fixture'),patch.object(modes,'CHILDREN',arms):
            modes.prepare(self.h,bundle)
            for arm in ('on','off'):
                result=asyncio.run(modes.send_arm(self.h,bundle,arm,'fixture-secret',transport=httpx.MockTransport(reply)))
                self.assertEqual(result['validation']['status'],'complete')
            with self.assertRaisesRegex(ValueError,'NO_RETRY'):
                asyncio.run(modes.send_arm(self.h,bundle,'on','fixture-secret',transport=httpx.MockTransport(reply)))
        a,b=deepcopy(sent[0]),deepcopy(sent[1]);a.pop('thinking');b.pop('thinking');a.pop('reasoning_effort')
        self.assertEqual(a,b);self.assertEqual(len(sent),2)
        self.assertEqual(self.h.store.remaining()['remaining']['model_calls'],5)
        self.assertEqual(self.h.store.remaining('p2-fixture')['remaining']['model_calls'],5)
        self.assertEqual(self.h.store.remaining()['used']['tool_calls'],0)
