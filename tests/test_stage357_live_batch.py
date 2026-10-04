"""Targeted retained facts and real batch integration risks."""
from pathlib import Path
from unittest import TestCase
from tools.platform_store import Store
from tools.state_io import read
from tools.diagnostic_summary import update_facts,read_coverage
from extensions.tendon_family.control_evidence import ControlEvidence
from copy import deepcopy
from unittest.mock import patch
from tools.platform_store import plain,zero
from tools.state_io import digest
from tools.platform_search import prepare_offline_batch,run_offline_batch,run_live_batch,offline_batch_result
from tools.live_batch_execution import LiveBatchExecution
from tests.test_stage356_batch import BatchTests,offline_directory

ROOT=Path(__file__).resolve().parents[1]


class FactualSummaryTests(TestCase):
    def test_archived_counts_bounds_and_merged_role_coverage(self):
        reader=ControlEvidence(Store(ROOT/'runs/stage354_milestone0_20261003/single_context'))
        source=reader.resolve('087adee8e8a24fe88e5c85fe89e638c8')
        facts=update_facts(reader,source,[24,26,27,28,29,31,32,33])
        self.assertEqual(facts['selected_iterations']['iteration_zero'],dict(count=4,update_ids=[24,26,27,28]))
        self.assertEqual(facts['controller_policy_stop']['relative_seed_improvement']['update_ids'],[29])
        self.assertEqual(facts['raw_optimizer_termination']['User_Requested_Stop']['count'],8)
        self.assertTrue(any(c['applied_input_backend_readback']['minimum_distance_to_upper_bound_n']<.01 for c in facts['tension_channels']))
        self.assertEqual(max(c['applied_input_backend_readback']['maximum_bound_violation_n'] for c in facts['tension_channels']),0.)
        states=read(ROOT/'evidence/stage356_milestone2_20261004/dual_context/evidence_contexts.json')
        coverage=read_coverage(states,35)
        self.assertEqual(coverage['shared_workflow']['queried_count'],8)
        self.assertEqual(len(coverage['shared_workflow']['unread_update_ids']),27)
        design=next(r for r in coverage['contexts'] if r['context']=='design')
        self.assertEqual(design['queried_count'],0)
        # Earlier reads must contribute when they exist; no review prose can
        # manufacture a receipt absent from the preserved workflow.
        earlier=dict(method='diagnosis.inspect_evidence',status='completed',role='diagnostic',view='plans',coverage=dict(update_ids=list(range(8))))
        states['diagnostic']['read_ledger'].append(earlier)
        merged=read_coverage(states,35)
        self.assertEqual(merged['shared_workflow']['queried_count'],16)
        self.assertEqual(len(merged['shared_workflow']['unread_update_ids']),19)


class LiveIntegrationTests(BatchTests):
    def test_pilot_launcher_preserves_provider_and_model_plan_path(self):
        from examples import stage357_live_pilot as pilot
        from tools.platform_models import payload_for
        from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
        from tools.diagnostic_revision import ensure_aliases
        from tools.platform_search import validate_batch_plan
        from tools.working_state import project_working_state
        from tools.state_io import read
        with offline_directory() as directory:
            with patch.object(pilot,'RUN',Path(directory)/'pilot'),patch.object(pilot,'EVIDENCE',Path(directory)/'evidence'):
                workflow=pilot.prepare()
            def submit_fixture(host):
                host.resume()
                payload=payload_for(host,EvidenceDrivenAdapter())
                self.assertLess(len(__import__('json').dumps(payload).encode()),400000)
                self.assertEqual(payload['max_tokens'],65536)
                state=host.store.session(host.run_id)['state'];aliases=ensure_aliases(state)['aliases']
                result=host.store.artifact(workflow.chain['feedback'])['result']
                alias=next(a for a,h in aliases.items() if state['fact_catalog'][h]['selector']['reference']==result)
                args=read(pilot.CONFIRM/'search_plan.json')['plan']
                args.update(evidence=[alias],max_candidates=6,max_backend_attempts=3,target_changed_configurations=2,
                    planned_budget=dict(model_calls=16,tool_calls=24,backend_solves=3,worker_calls=0,wall_s=7200.))
                validated=validate_batch_plan(host.store,project_working_state(host.store,host.run_id),args)
                self.assertTrue(validated['structurally_operationally_valid'])
                receipt=host.invoke(dict(request_id='offline-plan-fixture',tool_id='design.submit_search_plan',tool_version='1.0.0',arguments=args,
                    reason='Explicit engineer-authored offline launcher fixture',cache='new'))
                self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
            with patch('tools.diagnostic_workflow.run_loop',side_effect=submit_fixture):
                workflow.phase('improvement','search_batch_plan','search_plan')
            result=dict(mode='offline_test_fixture',candidates=[])
            from tools.diagnostic_workflow import save
            ref=save(workflow.store,result)
            baseline=read(ROOT/'runs/stage354_milestone0_20261003/single_context/feedback.json')['baseline_facts']
            def final_fixture(host):
                host.resume();adapter=EvidenceDrivenAdapter();payload_for(host,adapter)
                args=dict(disposition='defer',recommendation_id=None,reasoning='Offline fixture preserves baseline; further diagnostics require another grant.',
                    next_action='finish',candidate_disposition='retain_baseline',selected_candidate='baseline')
                resolved=adapter.resolve_business('design.respond_diagnosis',args)
                resolved.update(workflow.fixed('response_final')['design.respond_diagnosis'])
                receipt=host.invoke(dict(request_id='offline-final-fixture',tool_id='design.respond_diagnosis',tool_version='3.0.0',arguments=resolved,
                    reason='Engineer-authored offline final-path fixture',cache='new'))
                self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
            with patch('tools.diagnostic_workflow.run_loop',side_effect=final_fixture):
                workflow.phase('response_final','design_response','final_response',batch_result=result,
                    improvement_feedback_content=dict(baseline_facts=baseline,execution=None),check_feedback=[dict(reference=ref)])
            model=workflow.store.session(workflow.host('design').run_id)['snapshot']['input']['policy']['model']
            self.assertEqual(model,read(pilot.CONFIRM/'freeze.json')['host_provider_configurations']['shared'])
            self.assertEqual(workflow.store.remaining()['used']['model_calls'],0)
            self.assertEqual(workflow.store.remaining()['used']['backend_solves'],0)

    def live_fixture(self,directory,*,holding_lower=.05):
        host,old=self.fixture(directory,wall_s=7200.,max_candidates=6,backend_attempts=3,model_calls=16)
        record=host.store.artifact(old);record['plan'].update(max_backend_attempts=3,target_changed_configurations=2,step=.2,
            variables={'control/recipe/holding_tip_speed_weight':[holding_lower,1.],'control/recipe/terminal_tip_speed_weight':[0.,1.]},
            planned_budget=dict(model_calls=16,tool_calls=24,backend_solves=3,worker_calls=0,wall_s=7200.))
        fixed=deepcopy(self.configuration['effective'])
        for p in record['plan']['variables']:fixed['policy']['controller']['parameters']['data']['recipe'][p.rsplit('/',1)[-1]]='<batch variable>'
        record['bindings'].update(fixed_configuration=fixed,fixed_configuration_identity=digest(fixed))
        with host.store.transaction() as db:
            ref=plain(host.store.put(db,record));host.store.event(db,host.run_id,'role_transition','search_batch_plan',outputs=[ref])
        # Historical references are fixed; fixture facts retain both identities.
        retained=read(ROOT/'runs/stage354_milestone0_20261003/single_context/feedback.json')['baseline_facts']
        baseline_store=Store(ROOT/'runs/stage351_settling_20261003/baseline')
        with host.store.transaction() as db:
            self.assertEqual(plain(host.store.put(db,baseline_store.artifact(retained['configuration']))),retained['configuration'])
        prepare_offline_batch(host,ref,starting_facts=self.facts,retained_baseline=retained,mode='live')
        return host

    def test_retained_baseline_and_float_roundtrip_never_spend_backend_budget(self):
        for improves in (False,True):
            with self.subTest(improves=improves),offline_directory() as directory:
                host=self.live_fixture(directory,holding_lower=0.);calls=[]
                def stage(obj,name,candidate):
                    child=obj.candidate_host(candidate);request='complete-'+name
                    old=child.store.lookup(child.run_id,request)
                    if old:return __import__('json').loads(old['receipt'])
                    if name=='simulation':calls.append(dict(candidate['changes']))
                    row,_=child.store.reserve(child.run_id,request,digest(candidate),child.actor,
                        {**zero(),'tool_calls':1,'backend_solves':int(name=='simulation'),'wall_s':dict(simulation=900,evaluation=30,profile=60)[name]})
                    return child.store.complete(row,dict(request_id=request,execution_id=row['execution_id'],caller=child.actor,
                        tool_id='offline.test.'+name,tool_version='1.0.0',execution_status='completed',charged=zero()),dict(mode='offline_test_fixture'),.01)
                def facts(obj,candidate):
                    f=self.synthetic(.009,.05,.2,candidate['configuration']) if improves else self.synthetic(.03,.08,2.,candidate['configuration'])
                    f['candidate']['candidate_id']=candidate['candidate_id']
                    return dict(factual_result=f,configuration=candidate['configuration'],mode='offline_test_fixture')
                with patch.object(LiveBatchExecution,'stage',stage),patch.object(LiveBatchExecution,'facts',facts):result=run_live_batch(host)
                self.assertEqual(result['stop_reason'],'pilot_target_complete')
                self.assertEqual(result['accounting']['new_backend_attempts'],2)
                self.assertEqual(result['fully_evaluated_distinct_changed_configurations'],2)
                self.assertEqual(len(calls),2)
                self.assertTrue(all(not (c['control/recipe/holding_tip_speed_weight']==0. and c['control/recipe/terminal_tip_speed_weight']==0.) for c in calls))
                self.assertEqual(result['accounting']['retained_baseline_reuse'],0 if improves else 1)
                if improves:
                    self.assertTrue(any(p['roundoff_canonicalized'] for p in result['proposals']))
                    self.assertGreaterEqual(result['accounting']['duplicate_result_reuse'],1)

    def test_shared_scheduler_two_comparisons_caps_and_continuation(self):
        with offline_directory() as directory:
            host=self.live_fixture(directory);adapter=LiveBatchExecution(host);calls=[]
            def stage(obj,name,candidate):
                child=obj.candidate_host(candidate);request='complete-'+name
                old=child.store.lookup(child.run_id,request)
                if old:return __import__('json').loads(old['receipt'])
                row,_=child.store.reserve(child.run_id,request,digest(candidate),child.actor,
                    {**zero(),'tool_calls':1,'backend_solves':int(name=='simulation'),'wall_s':dict(simulation=900,evaluation=30,profile=60)[name]})
                calls.append((candidate['candidate_id'],name))
                return child.store.complete(row,dict(request_id=request,execution_id=row['execution_id'],caller=child.actor,
                    tool_id='offline.test.'+name,tool_version='1.0.0',execution_status='completed',charged=zero()),
                    dict(mode='offline_test_fixture',configuration=candidate['configuration']),.01)
            def facts(obj,candidate):
                f=self.synthetic(.009,.05,.2,candidate['configuration']);f['candidate']['candidate_id']=candidate['candidate_id']
                return dict(factual_result=f,configuration=candidate['configuration'],mode='offline_test_fixture')
            with patch.object(LiveBatchExecution,'stage',stage),patch.object(LiveBatchExecution,'facts',facts):
                paused=run_live_batch(host,stop_after_stage='simulation')
                self.assertEqual(paused['accounting']['new_backend_attempts'],1)
                self.assertEqual(paused['fully_evaluated_distinct_changed_configurations'],0)
                result=run_live_batch(host)
            self.assertEqual(result['stop_reason'],'pilot_target_complete')
            self.assertEqual(result['fully_evaluated_distinct_changed_configurations'],2)
            self.assertEqual(result['accounting']['new_backend_attempts'],2)
            self.assertEqual(sum(n=='simulation' for _,n in calls),2)
            self.assertEqual(result['accounting']['historical_start_reuse'],1)
            self.assertLessEqual(result['accounting']['proposals'],6)
            for c in result['candidates']:
                if not c['reused']:
                    self.assertEqual(c['feedback']['comparison']['baseline']['source']['execution_id'],self.facts['execution_id'])
                    self.assertEqual(c['retained_baseline_comparison']['baseline']['source']['execution_id'],self.plan['bindings']['baseline']['execution_id'])
            with self.assertRaisesRegex(ValueError,'SYNTHETIC_OUTPUTS'):run_offline_batch(host,lambda *a: {})

    def test_live_adapter_refuses_wrong_result_configuration(self):
        with offline_directory() as directory:
            host=self.live_fixture(directory)
            # Obtain an actual optimizer-generated pending changed configuration.
            with patch.object(LiveBatchExecution,'stage',return_value=dict(execution_status='unknown',output=None)):
                run_live_batch(host)
            pending=host.store.session(host.run_id)['state']['search_batch']['pending']
            adapter=LiveBatchExecution(host)
            wrong=dict(status='evaluated',configuration=self.facts['configuration'])
            with patch('tools.live_batch_execution.complete_execution',return_value=wrong):
                with self.assertRaisesRegex(ValueError,'CONFIGURATION_MISMATCH'):adapter.facts(pending)
