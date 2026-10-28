"""Paired cap-15 authorization and identical-feedback transport fixtures."""
import asyncio,json,unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from tests.research.test_p2_feedback_paired import PairedAuthorizationTests
from tests.research import p2_feedback_paired as first,p2_feedback_pair2 as second
from tools.platform_store import zero
from tools.research.agent import record
from tools.research.state import state,update


class Pair2Tests(unittest.TestCase):
    def setUp(self):
        PairedAuthorizationTests.setUp(self);first.authorize(self.h)
        for i in range(6,8):
            row,_=self.h.store.reserve('p2-fixture',str(i),'hash','fixture',{**zero(),'model_calls':1},resources=['provider_request'])
            self.h.store.complete(row,dict(request_id=str(i),execution_id=row['execution_id'],caller='fixture',
                tool_id='model.deepseek',tool_version='1.0.0',execution_status='completed',charged=zero()))
        with self.h.store.transaction() as db:
            t1=self.h.store.put(db,{'synthetic':'t1'}).model_dump(mode='json')
            replay=self.h.store.put(db,{'synthetic':'replay'}).model_dump(mode='json')
        current=state(self.h);spec=deepcopy(current['spec']);spec.update(resolved_identity='round1',physical_replay_limit=1,
            numerical_execution_guard={'limit_s':300},family_space={'version':'serial_family_space_v3'})
        spec['budgets']['mathematical_evaluations']=2
        provider=dict(base_url='https://api.deepseek.com',model='deepseek-flash',thinking='enabled',reasoning_effort='high',
            max_tokens=100,adapter='deepseek',context_guard=dict(context_limit_tokens=100000,framing_headroom_tokens=10))
        update(self.h,spec=spec,validation_extension_pending_binding=False,analysis_results=[t1],physical_replays=[replay],
            mathematical_evaluations=1,physical_replay_launches=1,pilot={'provider':provider,'live_model_requests':8})
        pause=record(self.h,'paired_feedback_supervisor_pause',{'fixture':True})
        wire=dict(model='deepseek-flash',thinking={'type':'enabled'},reasoning_effort='high',max_tokens=100,stream=False,
            messages=[{'role':'system','content':'fixture'},{'role':'user','content':'old'}],
            tools=[{'type':'function','function':{'name':'research_plan','parameters':{}}}])
        common=record(self.h,'fixture_context',{'wire':wire,'packet':{'shared_t1_feedback':{'status':'incomplete'}}})
        first_children={'on':'first-on','off':'first-off'}
        for arm,name in first_children.items():
            self.h.store.create_session(dict(input=dict(run_id=name,policy=dict(budget=dict(model_calls=1,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=None))),parent_run_id='p2-fixture'))
            child=SimpleNamespace(store=self.h.store,run_id=name);update(child,paired_context=common)
            for n in range(2 if arm=='off' else 1):
                record(child,'paired_tool_feedback',dict(tool_use={'name':'fixture','toolUseId':arm+str(n),'input':{}},
                    result={'status':'success','content':[{'text':'real tool feedback fixture'}]}))
        for name,value in [('RUN','p2-fixture'),('PRIOR_ID','round1'),('T1_ID',t1['artifact_id']),('REPLAY_ID',replay['artifact_id']),
                           ('PAUSE_ID',pause['artifact_id']),('FIRST_CHILDREN',first_children),('CHILDREN',{'on':'second-on','off':'second-off'}),
                           ('clean_commit',lambda:'fixture-commit'),('science_hashes',lambda:{}),
                           ('execution_environment',lambda spec:{'status':'ready'}),('guard',lambda *args:None),
                           ('decision_packet',lambda host:{'research':{'actions':['stop']}}),('plan_schema',lambda *a,**k:{})]:
            p=patch.object(second,name,value);p.start();self.addCleanup(p.stop)

    def test_extension_and_equal_paired_feedback_without_science(self):
        before=self.h.store.remaining()['used'];second.authorize(self.h)
        self.assertEqual(self.h.store.remaining()['limit']['model_calls'],15)
        self.assertEqual(self.h.store.remaining()['used'],before)
        self.assertEqual(state(self.h)['spec']['budgets']['protected_provider_requests'],4)
        self.assertEqual(state(self.h)['spec']['budgets']['mathematical_evaluations'],2)
        bundle=second.freeze_pair(self.h)
        self.assertEqual(len(bundle['packet']['shared_prior_tool_feedback']['results']),3)
        second.prepare(self.h,bundle);sent=[]
        def respond(req):
            sent.append(json.loads(req.content));return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'fixture'}}]})
        for arm in ('on','off'):
            result=asyncio.run(second.send_arm(self.h,bundle,arm,'fixture-secret',transport=httpx.MockTransport(respond)))
            self.assertEqual(result['validation']['status'],'complete')
        a,b=deepcopy(sent[0]),deepcopy(sent[1]);a.pop('thinking');a.pop('reasoning_effort');b.pop('thinking')
        self.assertEqual(a,b);self.assertEqual(self.h.store.remaining()['remaining']['model_calls'],5)
        self.assertEqual(state(self.h)['mathematical_evaluations'],1);self.assertEqual(state(self.h)['physical_replay_launches'],1)
        with self.assertRaisesRegex(ValueError,'NO_RETRY'):
            asyncio.run(second.send_arm(self.h,bundle,'on','fixture-secret',transport=httpx.MockTransport(respond)))
