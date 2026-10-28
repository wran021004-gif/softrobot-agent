"""Synthetic cap-17 authorization and corrected-feedback pair; no real science."""
import asyncio,json,unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from tests.research.test_p2_feedback_pair2 import Pair2Tests
from tests.research import p2_feedback_pair2 as second,p2_feedback_pair3 as third
from tests.research.p2_feedback_pair3_execute import admit_calls
from tools.platform_store import zero
from tools.research.agent import record
from tools.research.research_context import mathematics_authorization
from tools.research.state import state,update


class Pair3Tests(unittest.TestCase):
    def setUp(self):
        Pair2Tests.setUp(self);second.authorize(self.h)
        for i in range(8,10):
            row,_=self.h.store.reserve('p2-fixture',str(i),'hash','fixture',{**zero(),'model_calls':1},resources=['provider_request'])
            self.h.store.complete(row,dict(request_id=str(i),execution_id=row['execution_id'],caller='fixture',
                tool_id='model.deepseek',tool_version='1.0.0',execution_status='completed',charged=zero()))
        second.record_math_authorization(self.h)
        with self.h.store.transaction() as db:
            raw=self.h.store.put(db,dict(error='fixture',reason='fixture',numerical_failure={'integration_state':[.1]})).model_dump(mode='json')
            replay=self.h.store.put(db,dict(raw_reference=raw,status='execution_incomplete',acceptance={'accepted':None})).model_dump(mode='json')
        update(self.h,physical_replays=[replay])
        pause=record(self.h,'paired_feedback_round2_supervisor_pause',{'fixture':True})
        wire=dict(model='deepseek-flash',thinking={'type':'enabled'},reasoning_effort='high',max_tokens=100,stream=False,
            messages=[{'role':'system','content':'fixture'},{'role':'user','content':'old'}],
            tools=[{'type':'function','function':{'name':'research_plan','parameters':{}}}])
        prior_tools=[{'tool_use':{'name':'evidence_read'},'actual_tool_response':{'status':'success'}},
            {'tool_use':{'name':'evidence_read'},'actual_tool_response':{'status':'error'}}]
        context=record(self.h,'fixture_context2',dict(wire=wire,packet={'shared_prior_tool_feedback':{'shared_t1':{'fixture':'T1'},'results':prior_tools}}))
        previous={'on':'prior-second-on','off':'prior-second-off'}
        for arm,name in previous.items():
            self.h.store.create_session(dict(input=dict(run_id=name,policy=dict(budget=dict(model_calls=1,tool_calls=0,backend_solves=0,worker_calls=0,wall_s=None))),parent_run_id='p2-fixture'))
            child=SimpleNamespace(store=self.h.store,run_id=name);update(child,paired_context=context)
            record(child,'paired_tool_feedback',dict(result={'toolUseId':arm,'status':'success','content':[{'text':'same-result-index'}]}))
        for name,value in [('RUN','p2-fixture'),('PRIOR_ID',state(self.h)['spec']['resolved_identity']),('PAUSE',pause['artifact_id']),
                           ('PRIOR_CHILDREN',previous),('CHILDREN',{'on':'third-on','off':'third-off'}),
                           ('clean_commit',lambda:'fixture-commit'),('science_hashes',lambda:{}),
                           ('execution_environment',lambda spec:{'status':'ready'}),('guard',lambda *args:None),
                           ('decision_packet',lambda host:{'research':{'actions':['stop'],'mathematics_authorization':{'registered_study_scope_authorized':True}}}),
                           ('plan_schema',lambda *a,**k:{})]:
            p=patch.object(third,name,value);p.start();self.addCleanup(p.stop)

    def test_approved_scope_survives_cap_change_and_pair_is_identical(self):
        before=self.h.store.remaining()['used'];third.authorize(self.h)
        self.assertEqual(self.h.store.remaining()['limit']['model_calls'],17)
        self.assertEqual(self.h.store.remaining()['used'],before)
        self.assertTrue(mathematics_authorization(self.h,state(self.h))['registered_study_scope_authorized'])
        self.assertEqual(state(self.h)['spec']['budgets']['protected_provider_requests'],4)
        bundle=third.freeze_pair(self.h)
        self.assertEqual(bundle['packet']['shared_corrected_feedback']['exact_common_results_index'][0]['text'],'same-result-index')
        third.prepare(self.h,bundle);sent=[]
        def respond(req):
            sent.append(json.loads(req.content));return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'fixture'}}]})
        for arm in ('on','off'):
            r=asyncio.run(third.send_arm(self.h,bundle,arm,'fixture-secret',transport=httpx.MockTransport(respond)))
            self.assertEqual(r['validation']['status'],'complete')
        a,b=deepcopy(sent[0]),deepcopy(sent[1]);a.pop('thinking');a.pop('reasoning_effort');b.pop('thinking')
        self.assertEqual(a,b);self.assertEqual(self.h.store.remaining()['remaining']['model_calls'],5)
        self.assertEqual(state(self.h)['mathematical_evaluations'],1);self.assertEqual(state(self.h)['physical_replay_launches'],1)
        with self.assertRaisesRegex(ValueError,'NO_RETRY'):
            asyncio.run(third.send_arm(self.h,bundle,'on','fixture-secret',transport=httpx.MockTransport(respond)))

    def test_only_noncomputational_exact_choices_are_admitted(self):
        def call(name,data):return {'function':{'name':name,'arguments':json.dumps(data)}}
        admit_calls('on',[call('research_plan',{'action':'diagnose'})])
        admit_calls('off',[call('evidence_read',{}),call('evidence_read',{})])
        for calls in ([call('research_plan',{'action':'diagnose','diagnostic':{'foo':'bar'}})],
                      [call('research_plan',{'action':'physical_replay'})],
                      [call('research_analysis',{})]):
            with self.assertRaisesRegex(ValueError,'READ_ONLY'):admit_calls('on',calls)
