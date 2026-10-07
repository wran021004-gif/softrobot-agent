"""Focused post-live repairs and Milestone 3 offline preparation; no execution."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from contextlib import ExitStack,closing,contextmanager
from uuid import uuid4
import shutil
import json
import gc

from tools.state_io import read,digest
from tools.platform_store import Store,plain,zero
from tools.platform_host import Host
from tools.platform_search import physical_feedback,prepare_offline_batch,run_offline_batch
from tools.working_state import project_working_state
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.platform_models import ToolProtocolError
from schemas.platform_handoff import SearchBatchPlan
from schemas.diagnostic_revision import CheckedRevision
from tools.diagnostic_revision import correct
from examples.stage356_milestone2 import ROOT,HISTORY

OFFLINE_EXAMPLES={}


@contextmanager
def offline_directory():
    directory=ROOT/'runs'/('batch-offline-'+uuid4().hex)
    directory.mkdir()
    try:yield str(directory)
    finally:
        gc.collect()
        if not directory.resolve().is_relative_to((ROOT/'runs').resolve()):raise ValueError('UNSAFE_OFFLINE_CLEANUP')
        shutil.rmtree(directory)


class BatchTests(TestCase):
    def setUp(self):
        self.guards=ExitStack();self.addCleanup(self.guards.close)
        for target in ('tools.model_transports.deepseek.request_completion',
                'extensions.tendon_family.backends.MujocoBackend.run',
                'extensions.tendon_family.gvs_trajectory.TrajectoryWorkspace.__init__'):
            self.guards.enter_context(patch(target,side_effect=AssertionError('OFFLINE_FORBIDS_EXECUTION: '+target)))
        self.plan=read(ROOT/'evidence/stage356_milestone2_20261004/dual_context/search_plan.json')
        old=Store(HISTORY)
        self.configuration=old.artifact(self.plan['bindings']['subject']['configuration'])
        self.facts=read(HISTORY/'feedback.json')['execution']['factual_result']

    def fixture(self,directory,*,wall_s=3570.,max_candidates=3,backend_attempts=0,model_calls=0):
        store=Store(directory);budget={**zero(),'tool_calls':4*max_candidates+4,'wall_s':wall_s,'backend_solves':backend_attempts,'model_calls':model_calls}
        store.create(dict(project_id='offline-batch',grant_id='offline-only-'+uuid4().hex,budget=budget,
            authorization_source='Engineer-authored synthetic offline fixtures; zero provider/backend/workers.'))
        host=Host(directory,'offline-batch');inp=deepcopy(self.configuration['effective']);inp['run_id']=host.run_id
        inp['policy'].update(budget=budget,tool_bindings={},allowed_tools=[],route=None)
        host.create(inp)
        # A separately labelled engineering plan derived from the accepted live
        # schema. This is not an amendment of an archived model product.
        record=deepcopy(self.plan);record['plan'].update(max_candidates=max_candidates,step=1.,
            variables={'control/recipe/holding_tip_speed_weight':[.05,1.]},planned_budget={**zero(),
                'tool_calls':4*max_candidates,'backend_solves':max_candidates,'wall_s':990.*max_candidates})
        fixed=deepcopy(self.configuration['effective'])
        fixed['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']='<batch variable>'
        record['bindings'].update(fixed_configuration=fixed,fixed_configuration_identity=digest(fixed))
        record['offline_engineering_fixture']=True
        SearchBatchPlan.model_validate(record['plan'])
        with store.transaction() as db:
            self.assertEqual(plain(store.put(db,self.configuration)),record['bindings']['subject']['configuration'])
            ref=plain(store.put(db,record))
            store.event(db,host.run_id,'role_transition','search_batch_plan',outputs=[ref])
        return host,ref

    def synthetic(self,terminal,position,speed,configuration=None):
        facts=deepcopy(self.facts);facts.update(terminal_error_m=terminal,task_accepted=terminal<=.01)
        facts['sampled_settling'].update(max_error_m=position,max_speed_m_s=speed,passed=position<=.01 and speed<=.02)
        if configuration:
            facts['configuration']=configuration;facts['candidate']['configuration']=configuration
            facts['execution_id']='offline-synthetic';facts['candidate']['execution_id']='offline-synthetic'
        return facts

    def test_physical_feedback_preserves_tradeoff_and_joint_acceptance(self):
        acceptance=self.plan['bindings']['acceptance']
        base=physical_feedback(self.facts,self.facts,acceptance)
        better=physical_feedback(self.facts,self.synthetic(.007,.05,.2),acceptance)
        trade=physical_feedback(self.facts,self.synthetic(.009,.05,.1),acceptance)
        joint=physical_feedback(self.facts,self.synthetic(.009,.009,.019),acceptance)
        self.assertEqual(better['comparison']['classification'],'physical_pareto_improvement')
        self.assertEqual(trade['comparison']['classification'],'physical_tradeoff')
        self.assertLess(trade['score'],base['score']);self.assertFalse(trade['candidate_promoted'])
        self.assertLess(joint['score'],better['score']);self.assertTrue(joint['physical_metrics']['joint_reach_holding_passed'])
        invalid=self.synthetic(.007,.009,.019);invalid['force_bound_violation_n']=.1
        self.assertIsNone(physical_feedback(self.facts,invalid,acceptance)['score'])
        changed=self.synthetic(.007,.009,.019);changed['sampled_settling']['speed_limit_m_s']=.1
        with self.assertRaisesRegex(ValueError,'ACCEPTANCE_CHANGED'):physical_feedback(self.facts,changed,acceptance)

    def test_proposals_duplicates_resume_and_plan_binding(self):
        with offline_directory() as directory:
            host,ref=self.fixture(directory);calls=[]
            prepare_offline_batch(host,ref,starting_facts=self.facts)
            def inject(stage,candidate,receipts):
                calls.append(stage)
                facts=self.synthetic(.02,.08,2.,candidate['configuration']);facts['candidate']['candidate_id']=candidate['candidate_id']
                return dict(factual_result=facts) if stage=='profile' else {'synthetic':True}
            paused=run_offline_batch(host,inject,stop_after_stage='evaluation')
            self.assertEqual(calls,['simulation','evaluation']);self.assertIsNotNone(paused['pending'])
            view=project_working_state(host.store,host.run_id);self.assertEqual(view.search_batch['pending'],paused['pending'])
            result=run_offline_batch(Host(directory,host.run_id),inject)
            self.assertEqual(calls,['simulation','evaluation','profile'])
            a=result['accounting'];self.assertEqual([a[k] for k in ('proposals','distinct_configurations','reused_evaluations','new_backend_attempts','completed_new_evaluations')],[3,2,2,0,1])
            self.assertEqual(a['usage']['tool_calls'],4);self.assertEqual(result['status'],'completed')
            self.assertFalse(result['candidate_promoted'])
            with host.store.transaction() as db:other=plain(host.store.put(db,{**self.plan,'different':True}))
            with self.assertRaises(ValueError):prepare_offline_batch(host,other)
            # Candidate generation must preserve every frozen physical/numerical
            # setting outside the single planned path, including terminal weight.
            changed=next(r for r in result['candidates'] if not r['reused'])
            effective=host.store.artifact(changed['configuration'])['effective']
            expected=deepcopy(self.configuration['effective'])
            expected['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=1.
            self.assertEqual(effective,expected)
            with closing(host.store.connect(True)) as db:
                state=host.store.session(host.run_id,db)['state']
                self.assertEqual(host.store.artifact(state['search_batch_result'],db=db),result)
            from tools.diagnostic_facts import handover
            with host.store.transaction() as db:
                state=host.store.session(host.run_id,db)['state'];state['fact_scope']={'offline_batch':ref}
                host.store.update_state(db,host.run_id,state)
            handover(host,state['search_batch_result'],result,origin={'mode':'offline_injected'},kind='batch_result')
            state=host.store.session(host.run_id)['state']
            self.assertTrue(any(r['field']=='accounting.completed_new_evaluations' for r in state['fact_catalog'].values()))
            OFFLINE_EXAMPLES['completed_batch']=result

    def test_reservations_and_unsealed_work_are_not_replayed(self):
        with offline_directory() as directory:
            host,ref=self.fixture(directory,wall_s=1800.)
            with self.assertRaisesRegex(ValueError,'RESERVATION_CAPACITY'):prepare_offline_batch(host,ref,starting_facts=self.facts)
        with offline_directory() as directory:
            host,ref=self.fixture(directory);prepare_offline_batch(host,ref,starting_facts=self.facts)
            def interrupt(stage,candidate,receipts):raise RuntimeError('Injected process interruption')
            with self.assertRaisesRegex(RuntimeError,'interruption'):run_offline_batch(host,interrupt)
            result=run_offline_batch(Host(directory,host.run_id),lambda *args:self.fail('Unsealed work was replayed'))
            self.assertEqual(result['status'],'pending');self.assertEqual(result['accounting']['usage']['wall_s'],900.)
            self.assertEqual(result['accounting']['new_backend_attempts'],0)
            self.assertEqual(result['accounting']['offline_execution_attempts'],1)
            self.assertEqual(result['accounting']['completed_new_evaluations'],0)
            view=project_working_state(host.store,host.run_id);self.assertTrue(view.operations['unresolved'])
            OFFLINE_EXAMPLES['unsealed_batch']=result

    def test_v6_alias_errors_address_submitted_fields(self):
        adapter=EvidenceDrivenAdapter();adapter.wire={'design.submit_search_plan':SearchBatchPlan,'diagnosis.revise_assessment':CheckedRevision}
        adapter.fact_state=dict(fact_scope={'fixture':True},fact_catalog={},reference_interface=dict(scope={'fixture':True},aliases={},alias_format='decimal'))
        adapter.retain=lambda *args:None
        args=deepcopy(self.plan['plan']);args['evidence']=['prose instead of an alias']
        with self.assertRaises(ToolProtocolError) as error:adapter.resolve_business('design.submit_search_plan',args)
        self.assertEqual(error.exception.issues[0]['path'],'evidence.0')
        revised=correct(args,{'corrections':[{'path':'/evidence/0','operation':'replace','value':'F1'}]})
        self.assertEqual(revised['evidence'],['F1']);self.assertEqual(revised['fixed_conditions'],args['fixed_conditions'])
        # Regression for the missing selected-result hint using the retained live
        # final-phase catalog, with no provider call or model-product mutation.
        from tools.platform_search import validate_batch_plan
        from types import SimpleNamespace
        saved=Store(ROOT/'runs/stage356_milestone2_20261004/dual_context');freeze=read(saved.root/'freeze.json')
        run_id=freeze['hosts']['design'];state=saved.session(run_id)['state']
        result=saved.artifact(state['role_context']['result_feedback'])['result']
        aliases=state['reference_interface']['aliases']
        args=deepcopy(self.plan['plan']);args['evidence']=[a for a,h in aliases.items() if state['fact_catalog'][h]['selector']['reference']!=result][:1]
        with self.assertRaisesRegex(ValueError,'exact result alias, e.g. F'):
            validate_batch_plan(saved,SimpleNamespace(run_id=run_id),args)
