"""Changed finite generation, source binding, stopping and payload checks only."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
from tests.test_stage359_continuation import ContinuationTests
from tests.test_stage356_batch import offline_directory
from tools.platform_store import plain,zero
from tools.state_io import digest
from tools.live_batch_execution import LiveBatchExecution
from tools.platform_search import prepare_offline_batch,run_live_batch,validate_batch_plan
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.diagnostic_revision import ensure_aliases
from tools.working_state import project_working_state
from extensions.tendon_family.optimization import ExplicitSearch,ExplicitSearchParameters


class ExplicitTests(ContinuationTests):
    def test_finite_feedback_persistence_and_invalid_values(self):
        params=ExplicitSearchParameters(initial={'x':.05},bounds={'x':(.05,.2)},candidates=[{'x':.1},{'x':.15}])
        a=ExplicitSearch(params);self.assertEqual(a.propose(),{'x':.1});a.feedback(0.)
        b=ExplicitSearch(params);b.restore(a.save().data)
        self.assertEqual(b.propose(),{'x':.15});b.feedback(1.)
        self.assertTrue(b.stopped());self.assertEqual(b.state.best_score,0.)
        with self.assertRaisesRegex(ValueError,'PATHS_MISMATCH'):
            ExplicitSearch(params.model_copy(update={'candidates':[{'other':.1}]}))
        with self.assertRaisesRegex(ValueError,'OUT_OF_BOUNDS'):
            ExplicitSearch(params.model_copy(update={'candidates':[{'x':.25}]}))

    def test_first_changed_point_is_not_reused_and_stops_after_one(self):
        with offline_directory() as directory:
            host,old,history=self.terminal_fixture(directory)
            record=host.store.artifact(old);path='control/recipe/terminal_tip_speed_weight'
            record['plan'].update(method='search.family_explicit@1.0.0',variables={path:[.05,.2]},
                candidates=[{path:.1}],step=None,max_candidates=1,max_backend_attempts=1,target_changed_configurations=1,
                planned_budget=dict(model_calls=8,tool_calls=20,backend_solves=1,worker_calls=0,wall_s=4200.))
            with host.store.transaction() as db:
                ref=plain(host.store.put(db,record));host.store.event(db,host.run_id,'role_transition','search_batch_plan',outputs=[ref])
            prepare_offline_batch(host,ref,mode='live',starting_facts=self.facts,retained_baseline=history[0]['facts'],historical_results=history)
            calls=[]
            def stage(obj,name,candidate):
                child=obj.candidate_host(candidate);request='complete-'+name;old_call=child.store.lookup(child.run_id,request)
                if old_call:return json.loads(old_call['receipt'])
                calls.append(name);reservation,_=child.store.reserve(child.run_id,request,digest(candidate),child.actor,
                    {**zero(),'tool_calls':1,'backend_solves':int(name=='simulation'),'wall_s':dict(simulation=900,evaluation=30,profile=60)[name]})
                return child.store.complete(reservation,dict(request_id=request,execution_id=reservation['execution_id'],caller=child.actor,
                    tool_id='offline.test.'+name,tool_version='1.0.0',execution_status='completed',charged=zero()),dict(mode='offline_fixture'),.01)
            def facts(obj,candidate):
                f=self.synthetic(.007,.008,.03,candidate['configuration']);f['candidate']['candidate_id']=candidate['candidate_id']
                return dict(factual_result=f,configuration=candidate['configuration'],mode='offline_fixture')
            with patch.object(LiveBatchExecution,'stage',stage),patch.object(LiveBatchExecution,'facts',facts):
                paused=run_live_batch(host,stop_after_stage='simulation');self.assertFalse(paused['proposals'][0]['reused'])
                result=run_live_batch(host)
            self.assertEqual(calls,['simulation','evaluation','profile'])
            self.assertEqual(result['accounting']['proposals'],1);self.assertEqual(result['accounting']['new_backend_attempts'],1)
            self.assertEqual(result['fully_evaluated_distinct_changed_configurations'],1)
            self.assertEqual(result['stop_reason'],'pilot_target_complete')
            row=result['candidates'][0]
            self.assertEqual(row['changes'],{path:.1})
            self.assertEqual(row['feedback']['comparison']['baseline']['source']['execution_id'],history[-1]['execution_id'])
            self.assertEqual(row['retained_baseline_comparison']['baseline']['source']['execution_id'],history[0]['execution_id'])

    def test_live_preparation_bindings_plan_validation_and_payload(self):
        from examples import stage359_live_continuation as live
        from tools.diagnostic_workflow import save
        from tools.platform_diagnosis_coordinator import configure_role
        with offline_directory() as directory:
            w,planning=live.prepare(Path(directory)/'live',Path(directory)/'evidence')
            self.assertEqual(w.identities['execution_id'],live.preparation.SOURCES[-1][2])
            self.assertEqual(w.store.remaining()['used']['model_calls'],0)
            self.assertEqual(w.store.remaining()['used']['backend_solves'],0)
            def plan_fixture(host):
                payload=payload_for(host,EvidenceDrivenAdapter());context=json.loads(payload['messages'][1]['content'])['role_context']
                self.assertEqual(context['planning_packet'],planning)
                self.assertIn('1200 s allocation is insufficient',context['instructions'])
                state=host.store.session(host.run_id)['state'];aliases=ensure_aliases(state)['aliases']
                feedback=host.store.artifact(w.chain['feedback'])['result']
                alias=next(a for a,h in aliases.items() if state['fact_catalog'][h]['selector']['reference']==feedback)
                args=live.read(live.previous.RUN/'search_plan.json')['plan']
                args.update(evidence=[alias],method='search.family_explicit@1.0.0',step=None,
                    candidates=[{'control/recipe/terminal_tip_speed_weight':.1}],variables={'control/recipe/terminal_tip_speed_weight':[.05,.2]},
                    max_candidates=1,max_backend_attempts=1,target_changed_configurations=1,
                    planned_budget=dict(model_calls=8,tool_calls=20,backend_solves=1,worker_calls=0,wall_s=4200.))
                validated=validate_batch_plan(host.store,project_working_state(host.store,host.run_id),args)
                self.assertEqual(validated['bindings']['subject'],w.historical_results[-1]['facts']['candidate'])
                host.resume();receipt=host.invoke(dict(request_id='offline-explicit-plan',tool_id='design.submit_search_plan',tool_version='1.0.0',arguments=args,reason='Offline fixture',cache='new'))
                self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
            with patch('tools.diagnostic_workflow.run_loop',side_effect=plan_fixture):
                w.phase('improvement','search_batch_plan','search_plan',planning_packet=planning)
            packet=dict(complete_results=[],facts_are_program_generated=True)
            def final_fixture(host):
                payload=payload_for(host,EvidenceDrivenAdapter());context=json.loads(payload['messages'][1]['content'])['role_context']
                self.assertEqual(context['decision_packet'],packet);self.assertNotIn('reference_view',context)
            with patch('tools.diagnostic_workflow.run_loop',side_effect=final_fixture):
                with self.assertRaisesRegex(RuntimeError,'PHASE_INCOMPLETE'):
                    w.phase('response_final','design_response','final_response',decision_packet=packet,
                        decision_packet_reference=save(w.store,packet),improvement_feedback_content=w.historical_feedback,check_feedback=[dict(reference=w.chain['feedback'])])
