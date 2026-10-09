"""Narrow Mainline4 integration checks; all backend outputs are substitutes."""
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import json
import uuid

from tools import research_mainline4 as m4
from tools.platform_models import payload_for
from tools.platform_search import validate_batch_plan,prepare_offline_batch,run_live_batch
from tools.working_state import project_working_state
from tools.candidate_parameters import planning_configuration,fixed_configuration,parameter_value
from tools.research_execution import construct_candidate
from tools.live_batch_execution import LiveBatchExecution
from tools.state_io import digest
from tools.platform_store import plain,zero


class Mainline4Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=m4.ROOT/'runs'/('mainline4-focused-'+uuid.uuid4().hex)
        cls.w=m4.prepare(cls.directory,offline=True)

    def test_native_configuration_tools_and_template_bounds(self):
        w=self.w
        row,_=w.store.reserve(w.host.run_id,'zero-count-engineering',digest('offline engineering'),w.host.actor,{**zero(),'wall_s':1.},kind='engineering')
        w.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=w.host.actor,tool_id='engineering.offline_fixture',tool_version='1.0.0',execution_status='completed',charged=zero()),elapsed=1.,kind='engineering')
        packet=m4.configure(w);adapter=m4.ResearchAdapter(w);payload=payload_for(w.host,adapter)
        self.assertEqual(payload['model'],'deepseek-flash');self.assertEqual(payload['max_tokens'],32768)
        self.assertEqual(payload['thinking'],{'type':'enabled'});self.assertEqual(payload['reasoning_effort'],'high')
        self.assertEqual(adapter.timeout_s,600.)
        self.assertEqual(set(adapter.advertised.values()),set(m4.NATIVE))
        wire=next(t['function']['parameters'] for t in payload['tools'] if adapter.advertised[t['function']['name']]=='research.decide')
        reference=wire['anyOf'][0]['properties']['selected_candidate']['anyOf'][1]
        self.assertFalse(reference['additionalProperties'])
        self.assertEqual(set(reference['required']),{'candidate_id','configuration','execution_id','owner_run_id'})
        cfg=planning_configuration(w.store,w.records[0]['facts']['candidate'],m4.configuration()['policy'])
        self.assertEqual(cfg['policy']['controller']['version'],'10.0.0')
        self.assertEqual(w.store.artifact(w.records[0]['facts']['configuration'])['effective']['policy']['controller']['version'],'9.0.0')
        for key in ('T0','T1','T2','T3'):
            source=plain(construct_candidate(m4.configuration(),{'template':key}))
            paths=['design/near_section_scale','control/recipe/holding_tip_speed_weight']
            changed=plain(construct_candidate(source,{paths[0]:1.01,paths[1]:.06}))
            self.assertEqual(fixed_configuration(source,paths),fixed_configuration(changed,paths))
            self.assertEqual(parameter_value(changed,paths[0]),1.01)
            unrelated=deepcopy(changed);unrelated['task']['timing']['duration_s']=.36
            self.assertNotEqual(fixed_configuration(source,paths),fixed_configuration(unrelated,paths))
            with self.assertRaises(ValueError):construct_candidate(source,{'components/far/length_m':.11 if key in ('T2','T3') else .055})
        self.assertLess(len(json.dumps(payload).encode()),4194304)

    def test_version8_correction_uses_native_business_fields(self):
        from tools.platform_models import _model_failure,delivery_instruction
        w=self.w;w.host.resume()
        self.assertIn('business fields directly',delivery_instruction(w.host))
        failure=m4.save(w.store,dict(error='Offline malformed native business fields',response=None,protocol_errors=[]))
        receipt=dict(request_id='offline-native-correction',execution_id='offline-native-correction',output=failure)
        self.assertIsNone(_model_failure(w.host,receipt))
        correction=w.store.session(w.host.run_id)['state']['protocol_correction']
        self.assertIn('no outer arguments/reason/tool_version wrapper',correction['requirement'])
        self.assertNotIn('with outer arguments (object)',correction['requirement'])
        self.assertEqual(w.store.remaining()['used']['model_calls'],0)

    def test_reused_outcomes_preserve_facts_and_weights(self):
        w=self.w;record=w.records[1]
        result=dict(candidates=[dict(candidate_id=record['facts']['candidate']['candidate_id'],
            reused=True,historical_source=record,feedback={'fixture':'offline'},retained_baseline_comparison={}),
            dict(candidate_id=record['facts']['candidate']['candidate_id'],reused=True,
                feedback={'fixture':'offline duplicate'},retained_baseline_comparison={})])
        outcomes=m4.batch_outcomes(w,result)
        self.assertEqual(len(outcomes),2)
        for outcome in outcomes:
            self.assertEqual(outcome['candidate'],record['facts']['candidate'])
            self.assertEqual(outcome['acceptance'],record['acceptance'])
            self.assertEqual(outcome['controller'],'10.0.0')
            self.assertEqual(outcome['applied_values']['holding_tip_speed_weight'],.05)
            self.assertTrue(outcome['reused'])
        self.assertEqual(w.store.remaining()['used']['model_calls'],0)

    def test_bounded_length_recovery_keeps_cumulative_counter(self):
        from tools.platform_models import _model_failure
        w=self.w;m4.configure(w)
        with w.store.transaction() as db:
            state=w.store.session(w.host.run_id,db)['state'];state['length_retries_used']=1
            w.store.update_state(db,w.host.run_id,state)
        failure=m4.save(w.store,dict(error='Offline length fixture',response=None,
            length_truncated=True,finish_reason='length',without_usable_action=True))
        self.assertIsNone(_model_failure(w.host,dict(request_id='offline-second-length',
            execution_id='offline-second-length',output=failure)))
        state=w.store.session(w.host.run_id)['state']
        self.assertEqual(state['length_retries_used'],2)
        self.assertEqual(state['protocol_correction']['type'],'length_truncation')
        self.assertEqual(w.store.remaining()['used']['model_calls'],0)

    def test_verified_reporting_recovery_does_not_repeat_execution(self):
        w=self.w;old=(w.status,w.rounds,w.verification)
        current=w.store.artifact(w.feedback)['result']
        final=dict(decision={'decision':{'action':'stop'},'evidence_selectors':[{'reference':current}]})
        def finish(obj,row):obj.status='model_stopped'
        try:
            w.verification=[{'mode':'offline sealed verification substitute'}]
            w.rounds=[dict(decision={'decision':{'action':'stop'},'evidence_selectors':[]})]
            with patch.object(m4,'decision',return_value=final) as decide,patch.object(m4,'execute',side_effect=finish),patch.object(m4,'verify_selection') as verify:
                m4.report_verified_selection(w);decide.assert_called_once();verify.assert_not_called()
                self.assertEqual(w.status,'model_stopped')
            w.rounds=[final]
            with patch.object(m4,'decision') as decide,patch.object(m4,'execute',side_effect=finish),patch.object(m4,'verify_selection') as verify:
                m4.report_verified_selection(w);decide.assert_not_called();verify.assert_not_called()
            self.assertEqual(w.store.remaining()['used']['model_calls'],0)
        finally:
            w.status,w.rounds,w.verification=old;m4.persist(w)

    def test_mixed_batch_feedback_and_receipt_recovery(self):
        w=self.w;m4.configure(w);source=w.records[1];current=w.store.artifact(w.feedback)['result']
        alias=next(iter(m4.aliases(w,current)))
        plan=dict(source_candidate=source['facts']['candidate'],predecessor_decision=None,
            hypothesis='Labeled offline fixture: exercise mixed reconstruction, not scientific evidence.',
            evidence=[alias],weakening_observations=['Backend substitute cannot test hypothesis'],
            variables={'design/near_section_scale':[.95,1.05],'control/recipe/holding_tip_speed_weight':[.025,.1]},
            fixed_conditions=['robot','task','acceptance','controller_implementation','other_numerical_settings'],
            fixed_controller='controller.gvs_nmpc@10.0.0',objectives=['joint_reach_holding_acceptance','terminal_error_m','holding_max_error_m','holding_max_speed_m_s'],
            constraints=['frozen_acceptance','force_bounds','finite_valid_execution'],method='search.family_coordinate@1.0.0',
            max_candidates=4,max_backend_attempts=2,target_changed_configurations=2,step=.1,candidates=None,
            planned_budget=dict(model_calls=8,tool_calls=30,backend_solves=2,worker_calls=0,wall_s=6000.),
            fidelity_limits=['offline_backend_substitute'],verification=['candidate.apply','simulation.run','evaluation.run','control.profile_report','bound_comparison','diagnostic_revision'],
            stopping_conditions=['initial plus one changed point complete'],scientific_promise='uncertain',rationale='Offline integration only',
            replication_reason='Offline check evaluates method initial point with a labeled substitute; no physical claims')
        validated=validate_batch_plan(w.store,project_working_state(w.store,w.host.run_id),plan)
        with w.store.transaction() as db:
            ref=plain(w.store.put(db,validated));w.store.event(db,w.host.run_id,'role_transition','search_batch_plan',outputs=[ref])
        m4.configure_role(w.host,'executor','Offline substitute only',phase_budget={});w.host.resume()
        prepare_offline_batch(w.host,ref,mode='live',starting_facts=source['facts'],retained_baseline=w.baseline,historical_results=w.records)
        simulations=[]
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
            sim=json.loads(child.store.lookup(child.run_id,'complete-simulation')['receipt'])
            f['configuration']=candidate['configuration'];f['execution_id']=sim['execution_id']
            f['candidate']=dict(candidate_id=candidate['candidate_id'],configuration=candidate['configuration'],owner_run_id=child.run_id,execution_id=sim['execution_id'])
            return dict(mode='labeled_offline_backend_substitute',factual_result=f,configuration=candidate['configuration'],
                acceptance=deepcopy(source['acceptance']),receipts={})
        with patch.object(LiveBatchExecution,'stage',stage),patch.object(LiveBatchExecution,'facts',facts):
            run_live_batch(w.host,stop_after_stage='simulation');before=len(simulations)
            result=run_live_batch(w.host)
            self.assertEqual(len(simulations),2);self.assertEqual(before,1)
            run_live_batch(w.host);self.assertEqual(len(simulations),2)
        self.assertEqual(result['status'],'completed')
        self.assertTrue(any(p['actual_changes'] for p in result['proposals']))
        m4.feedback(w,dict(status='labeled_offline_backend_substitute',batch_result=m4.save(w.store,result)),'offline-feedback')
        packet=m4.configure(w)
        self.assertTrue(packet['current_feedback']['aliases'])
        self.assertEqual(w.store.remaining()['used']['model_calls'],0)
