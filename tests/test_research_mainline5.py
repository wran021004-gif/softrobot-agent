"""Focused integration checks. All model/backend outputs here are substitutes."""
from copy import deepcopy
import json
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
import httpx
from tools import research_mainline5 as m5
from tools import research_mainline5_services as s
from tools.platform_store import Store,plain,zero
from tools.state_io import digest
from tools.live_batch_execution import LiveBatchExecution
from tools.research_execution import construct_candidate
from tools.candidate_parameters import parameter_value,fixed_configuration
from tools.strands_pilot import completion


class Mainline5Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w=m5.prepare(s.ROOT/'runs'/('mainline5-focused-'+uuid4().hex),offline=True)

    def test_template_fixed_source_chained_changes_and_actual_bounds(self):
        cfg=s.configuration()
        paths=['design/near_section_scale','design/middle_routing_radius_scale','components/far/length_m']
        for key in ('T2','T3'):
            base=plain(construct_candidate(cfg,{'template':key}))
            a=plain(construct_candidate(base,{paths[0]:1.04,paths[1]:1.01,paths[2]:.056}))
            b=plain(construct_candidate(a,{paths[0]:1.05,paths[1]:1.02,paths[2]:.05775}))
            direct=plain(construct_candidate(base,{paths[0]:1.05,paths[1]:1.02,paths[2]:.05775}))
            self.assertEqual(b,direct)
            self.assertEqual(fixed_configuration(base,paths),fixed_configuration(b,paths))
            self.assertAlmostEqual(parameter_value(b,paths[0]),1.05)
            with self.assertRaises(ValueError):construct_candidate(b,{paths[2]:.06})
            bad=deepcopy(b);near=next(c for c in bad['robot']['structure']['data']['components'] if c['id']=='near')
            for section in near['sections']:
                section['section']['parameters']={k:v*1.02 for k,v in section['section']['parameters'].items()}
            with self.assertRaises(ValueError):construct_candidate(bad,{'control/recipe/holding_tip_speed_weight':.04})
        with self.assertRaises(ValueError):construct_candidate(plain(construct_candidate(cfg,{'template':'T0'})),{'design/middle_section_scale':1.01})

    def test_atomic_store_receipt_rolls_back_with_business_state(self):
        w=self.w
        row,_=w.store.reserve(w.host.run_id,'offline-atomic-receipt',digest('atomic'),w.host.actor,{**zero(),'tool_calls':1})
        receipt=dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=w.host.actor,
            tool_id='offline.atomic',tool_version='1.0.0',execution_status='completed',charged=zero())
        with self.assertRaisesRegex(RuntimeError,'rollback'):
            with w.store.transaction() as db:
                state=w.store.session(w.host.run_id,db)['state'];state['offline_atomic']='uncommitted'
                w.store.update_state(db,w.host.run_id,state)
                w.store.complete(row,receipt,{'mode':'offline'},db=db)
                raise RuntimeError('rollback')
        self.assertNotIn('offline_atomic',w.store.session(w.host.run_id)['state'])
        self.assertIsNone(w.store.lookup(w.host.run_id,row['request_id'])['receipt'])
        w.store.complete(row,receipt,{'mode':'offline'})
        self.assertEqual(w.store.complete(row,receipt,{'mode':'offline'}),json.loads(w.store.lookup(w.host.run_id,row['request_id'])['receipt']))

    def test_native_batch_feedback_restore_and_matched_multiple_calls(self):
        w=self.w;w.status='running';s.persist(w)
        source=w.records[2];calls=[];simulations=[];wires=[]
        def plan():
            packet=s.configure(w);alias=next(iter(packet['current_feedback']['aliases']))
            return dict(action='control_search',evidence=[alias],reasoning='Offline native wiring substitute, no scientific conclusion',
                observations=[dict(evidence=alias,value=packet['current_feedback']['aliases'][alias]['value'])],
                plan=dict(source_candidate=source['facts']['candidate'],predecessor_decision=None,
                    hypothesis='Labeled offline test',evidence=[alias],weakening_observations=['Substitute is not physical evidence'],
                    variables={'control/recipe/holding_tip_speed_weight':[.025,.1]},
                    fixed_conditions=['robot','task','acceptance','controller_implementation','other_numerical_settings'],
                    fixed_controller='controller.gvs_nmpc@10.0.0',objectives=['joint_reach_holding_acceptance','terminal_error_m','holding_max_error_m','holding_max_speed_m_s'],
                    constraints=['frozen_acceptance','force_bounds','finite_valid_execution'],method='search.family_explicit@1.0.0',
                    max_candidates=2,max_backend_attempts=2,target_changed_configurations=2,step=None,
                    candidates=[{'control/recipe/holding_tip_speed_weight':.0375},{'control/recipe/holding_tip_speed_weight':.04}],
                    planned_budget=dict(model_calls=8,tool_calls=30,backend_solves=2,worker_calls=0,wall_s=6000.),
                    fidelity_limits=['offline substitutes'],verification=['candidate.apply','simulation.run','evaluation.run','control.profile_report','bound_comparison','diagnostic_revision'],
                    stopping_conditions=['two substituted outcomes'],scientific_promise='uncertain',rationale='Offline wiring only'))
        decision=plan()
        def wire(request):
            body=json.loads(request.content);wires.append(body)
            if len(wires)==1:
                result=completion('research_capability_catalog',{},call_id='offline-read-a')
                result['choices'][0]['message']['tool_calls'].append(completion('research_capability_catalog',{},call_id='offline-read-b')['choices'][0]['message']['tool_calls'][0])
            elif len(wires)==2:result=completion('research_decide',decision,call_id='offline-batch')
            else:
                packet=s.configure(w);aliases=packet['current_feedback']['aliases']
                alias=next(a for a,v in aliases.items() if isinstance(v['value'],str))
                result=completion('research_decide',dict(action='stop',evidence=[alias],reasoning='Offline feedback consumed',
                    observations=[dict(evidence=alias,value=aliases[alias]['value'])],stop_reason='Offline fixture done'),call_id='offline-stop')
            result['usage']=dict(prompt_tokens=5,completion_tokens=5,total_tokens=10)
            return httpx.Response(200,json=result)
        def stage(obj,name,candidate):
            child=obj.candidate_host(candidate);request='complete-'+name
            old=child.store.lookup(child.run_id,request)
            if old:return json.loads(old['receipt'])
            if name=='simulation':simulations.append(candidate['candidate_id'])
            row,_=child.store.reserve(child.run_id,request,digest(candidate),child.actor,
                {**zero(),'tool_calls':1,'backend_solves':int(name=='simulation'),'wall_s':1.})
            return child.store.complete(row,dict(request_id=request,execution_id=row['execution_id'],caller=child.actor,
                tool_id='offline.backend_substitute.'+name,tool_version='1.0.0',execution_status='completed',charged=zero()),
                dict(mode='labeled_offline_backend_substitute'),.01)
        def facts(obj,candidate):
            f=deepcopy(source['facts']);child=obj.candidate_host(candidate)
            receipt=json.loads(child.store.lookup(child.run_id,'complete-simulation')['receipt'])
            f.update(configuration=candidate['configuration'],execution_id=receipt['execution_id'])
            f['candidate']=dict(candidate_id=candidate['candidate_id'],configuration=candidate['configuration'],owner_run_id=child.run_id,execution_id=receipt['execution_id'])
            return dict(mode='labeled_offline_backend_substitute',factual_result=f,configuration=candidate['configuration'],
                acceptance=deepcopy(source['acceptance']),receipts={})
        with patch.object(LiveBatchExecution,'stage',stage),patch.object(LiveBatchExecution,'facts',facts):
            agent=m5.build_live(w,transport=httpx.MockTransport(wire),key='offline-no-secret')
            try:agent('Offline integration only')
            except Exception:
                if w.status!='model_stopped':raise
        self.assertEqual(w.status,'model_stopped');self.assertEqual(len(simulations),2)
        returned=w.store.artifact(w.rounds[0]['feedback_result'])['outcomes']
        self.assertEqual([o['applied_values']['holding_tip_speed_weight'] for o in returned],[.0375,.04])
        self.assertTrue(all(o['candidate']['owner_run_id'].startswith('batch-') for o in returned))
        self.assertEqual(w.spec['selected_template'],'T2')
        self.assertEqual(w.store.remaining()['used']['model_calls'],3)
        wire2=wires[1]
        ids=[m['tool_call_id'] for m in wire2['messages'] if m['role']=='tool']
        self.assertEqual(ids[:2],['offline-read-a','offline-read-b'])
        names={t['function']['name'] for t in wires[0]['tools']}
        self.assertTrue({n.replace('.','_') for n in s.NATIVE}<=names)
        research=next(t['function']['parameters'] for t in wires[0]['tools'] if t['function']['name']=='research_decide')
        self.assertEqual(set(research['properties']['selected_candidate']['anyOf'][1]['required']),
            {'candidate_id','configuration','execution_id','owner_run_id'})
        restored=s.restore(w.directory);before=restored.store.remaining()
        m5.recover_business(restored)
        self.assertEqual(restored.store.remaining(),before);self.assertEqual(len(simulations),2)
        restored_agent=m5.build_live(restored,transport=httpx.MockTransport(wire),key='offline-no-secret')
        self.assertEqual(restored_agent.messages,agent.messages)
        self.assertEqual(restored.store.remaining(),before)

    def test_reused_outcomes_and_sealed_verification_preserve_ownership(self):
        w=self.w;record=w.records[2]
        result=dict(candidates=[dict(candidate_id=record['facts']['candidate']['candidate_id'],reused=True,
            historical_source=record,feedback={'mode':'offline'},retained_baseline_comparison={})])
        self.assertEqual(s.batch_outcomes(w,result)[0]['candidate'],record['facts']['candidate'])
        old=(w.status,w.verification,w.rounds,w.feedback)
        try:
            w.verification=[dict(mode='offline sealed verification substitute')]
            ref=w.store.artifact(w.feedback)['result']
            row=dict(decision=dict(decision=dict(action='stop',selected_candidate=None,stop_reason='offline sealed stop'),
                evidence_selectors=[dict(reference=ref)]))
            with patch.object(s,'verify_selection',side_effect=AssertionError('must not replay')):
                m5.apply_decision(w,row)
                self.assertEqual(w.status,'model_stopped');self.assertTrue(row['verification_feedback_consumed'])
                m5.apply_decision(w,row)
        finally:w.status,w.verification,w.rounds,w.feedback=old;s.persist(w)

    def test_confirmed_response_replay_uses_same_ledger(self):
        import asyncio
        w=self.w;sent=[]
        wire=dict(model='deepseek-flash',thinking={'type':'enabled'},reasoning_effort='high',
            max_tokens=32768,stream=False,messages=[dict(role='user',content='Offline auxiliary summary')])
        def transport(request):
            sent.append(True);return httpx.Response(200,json=completion(text='Offline response'))
        boundary=m5.ResearchBoundary(w.host,httpx.MockTransport(transport))
        request=httpx.Request('POST','https://api.deepseek.com/chat/completions',json=wire)
        before=w.store.remaining()['used']['model_calls']
        first=asyncio.run(boundary.handle_async_request(request));charged=w.store.remaining()
        second=asyncio.run(boundary.handle_async_request(request))
        self.assertEqual(first.content,second.content);self.assertEqual(len(sent),1)
        self.assertEqual(w.store.remaining(),charged);self.assertEqual(charged['used']['model_calls'],before+1)
        different={**wire,'messages':[dict(role='user',content='changed offline request')]}
        with self.assertRaisesRegex(ValueError,'SAVED_RESPONSE_MUST_BE_PROCESSED_FIRST'):
            asyncio.run(boundary.handle_async_request(httpx.Request('POST','https://api.deepseek.com/chat/completions',json=different)))
        boundary.consumed()

    def test_length_response_is_saved_and_consumed_by_strands(self):
        w=self.w;w.status='running';s.persist(w)
        count=[]
        def fixture(request):
            count.append(True);body=completion(text='')
            body['choices'][0]['finish_reason']='length'
            body['choices'][0]['message']['reasoning_content']='Offline truncated reasoning substitute.'
            body['usage']=dict(prompt_tokens=3,completion_tokens=4,total_tokens=7,
                completion_tokens_details=dict(reasoning_tokens=4))
            return httpx.Response(200,json=body)
        before=w.store.remaining()['used']['model_calls']
        agent=m5.build_live(w,transport=httpx.MockTransport(fixture),key='offline-no-secret')
        from strands.types.exceptions import MaxTokensReachedException
        with self.assertRaises(MaxTokensReachedException):agent('Offline length-conversion check only')
        self.assertEqual(len(count),1)
        self.assertEqual(w.store.remaining()['used']['model_calls'],before+1)
        self.assertNotIn('unconsumed_response',m5.pilot(w.host))
        self.assertTrue(any('reasoningContent' in block for message in agent.messages for block in message['content']))
