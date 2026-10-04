"""Focused verified-history, live scheduler and final research handoff checks."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
from tools.platform_store import Store,plain,zero
from tools.state_io import digest,atomic_json
from tools.live_batch_execution import LiveBatchExecution,verified_historical_result
from tools.platform_search import prepare_offline_batch,run_live_batch
from tests.test_stage357_live_batch import LiveIntegrationTests
from tests.test_stage356_batch import offline_directory
from examples import stage358_confirmation as confirmation


class ConfirmationTests(LiveIntegrationTests):
    def test_three_verified_records_duplicate_and_two_new_target(self):
        with offline_directory() as directory:
            host,ref=self.fixture(directory,wall_s=7200.,max_candidates=6,backend_attempts=3,model_calls=16)
            sources=[verified_historical_result(host,Store(path),eid,role,confirmation.reviewed_changes())
                for role,path,eid in confirmation.SOURCES]
            self.assertEqual([s['execution_id'] for s in sources],[s[2] for s in confirmation.SOURCES])
            self.assertEqual(host.store.remaining()['used']['backend_solves'],0)
            self.assertEqual(sources[1]['facts'],self.facts)
            record=host.store.artifact(ref);record['plan'].update(max_backend_attempts=3,target_changed_configurations=2,step=.25,
                variables={'control/recipe/holding_tip_speed_weight':[0.,1.],'control/recipe/terminal_tip_speed_weight':[0.,1.]})
            fixed=deepcopy(self.configuration['effective'])
            for p in record['plan']['variables']:fixed['policy']['controller']['parameters']['data']['recipe'][p.rsplit('/',1)[-1]]='<batch variable>'
            record['bindings'].update(fixed_configuration=fixed,fixed_configuration_identity=digest(fixed))
            with host.store.transaction() as db:
                ref=plain(host.store.put(db,record));host.store.event(db,host.run_id,'role_transition','search_batch_plan',outputs=[ref])
            prepare_offline_batch(host,ref,starting_facts=sources[1]['facts'],retained_baseline=sources[0]['facts'],mode='live',historical_results=sources)
            calls=[]
            def stage(obj,name,candidate):
                child=obj.candidate_host(candidate);request='complete-'+name;old=child.store.lookup(child.run_id,request)
                if old:return json.loads(old['receipt'])
                calls.append((name,dict(candidate['changes'])))
                row,_=child.store.reserve(child.run_id,request,digest(candidate),child.actor,
                    {**zero(),'tool_calls':1,'backend_solves':int(name=='simulation'),'wall_s':dict(simulation=900,evaluation=30,profile=60)[name]})
                return child.store.complete(row,dict(request_id=request,execution_id=row['execution_id'],caller=child.actor,
                    tool_id='offline.test.'+name,tool_version='1.0.0',execution_status='completed',charged=zero()),dict(mode='offline_test_fixture'),.01)
            def facts(obj,candidate):
                f=self.synthetic(.03,.08,2.,candidate['configuration']);f['candidate']['candidate_id']=candidate['candidate_id']
                return dict(factual_result=f,configuration=candidate['configuration'],mode='offline_test_fixture')
            with patch.object(LiveBatchExecution,'stage',stage),patch.object(LiveBatchExecution,'facts',facts):
                paused=run_live_batch(host,stop_after_stage='simulation')
                self.assertEqual(paused['accounting']['other_historical_reuse'],1)
                self.assertEqual(paused['accounting']['historical_start_reuse'],1)
                self.assertEqual(paused['accounting']['retained_baseline_reuse'],1)
                self.assertEqual(paused['fully_evaluated_distinct_changed_configurations'],0)
                result=run_live_batch(host)
            self.assertEqual(result['stop_reason'],'pilot_target_complete')
            self.assertEqual(result['accounting']['new_backend_attempts'],2)
            self.assertEqual(result['fully_evaluated_distinct_changed_configurations'],2)
            self.assertEqual(result['completed_evaluations'],2);self.assertEqual(result['completed_profiles'],2)
            self.assertEqual(sum(n=='simulation' for n,_ in calls),2)
            reused=next(c for c in result['candidates'] if c.get('execution_id')==confirmation.SOURCES[2][2])
            self.assertEqual(reused['feedback']['physical_metrics']['terminal_error_m'],.018690324120991027)
            self.assertEqual(reused['feedback']['comparison']['baseline']['source']['execution_id'],confirmation.SOURCES[1][2])
            self.assertEqual(reused['retained_baseline_comparison']['baseline']['source']['execution_id'],confirmation.SOURCES[0][2])
            with self.assertRaisesRegex(ValueError,'COMPLETE_CHAIN|OWNED_EXECUTION|SEALED_SIMULATION'):
                verified_historical_result(host,Store(confirmation.PILOT),'d06d23180c19424faf5ac6618c779173','historical_candidate',confirmation.reviewed_changes())
            # Exact pinning refuses an unreviewed physical/implementation change.
            review=confirmation.reviewed_changes();review['tools/platform_search.py']['current_hash']='0'*64
            with self.assertRaisesRegex(ValueError,'UNREVIEWED_IMPLEMENTATION'):
                verified_historical_result(host,Store(confirmation.PILOT),confirmation.SOURCES[2][2],'historical_candidate',review)

    def test_confirmation_plan_context_and_final_research_consumption(self):
        from tools.platform_models import payload_for
        from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
        from tools.diagnostic_revision import ensure_aliases
        from tools.diagnostic_workflow import save
        with offline_directory() as directory:
            root=Path(directory)
            with patch.object(confirmation,'RUN',root/'confirmation'),patch.object(confirmation,'EVIDENCE',root/'evidence'):
                atomic_json(confirmation.EVIDENCE/'compatibility_review.json',confirmation.reviewed_changes())
                workflow=confirmation.prepare()
            seen=[]
            def fixture(host):
                host.resume();adapter=EvidenceDrivenAdapter();payload=payload_for(host,adapter)
                seen.append(payload)
                state=host.store.session(host.run_id)['state'];role=state['role_context']
                if role['phase']=='improvement':
                    args=deepcopy(confirmation.read(confirmation.PILOT/'search_plan.json')['plan'])
                    aliases=ensure_aliases(state)['aliases'];feedback=workflow.store.artifact(workflow.chain['feedback'])['result']
                    args['evidence']=[next(a for a,h in aliases.items() if state['fact_catalog'][h]['selector']['reference']==feedback)]
                    name='design.submit_search_plan';version='1.0.0'
                else:
                    self.assertEqual(role['batch_result']['batch_id'],'actual-offline-fixture')
                    args=dict(disposition='defer',recommendation_id=None,reasoning='Offline handoff fixture; no live inference.',
                        next_action='finish',candidate_disposition='retain_baseline',selected_candidate='baseline',
                        next_research=dict(route='initialization_selection',unresolved_question='Why select initialization?',
                            evidence=['explicit synthetic fixture'],bounded_check='Inspect one retained selected plan.',fixed_conditions=['All science fixed'],
                            expected_observations=['Compare selected initialization with retained alternatives'],proposed_budget={**zero(),'tool_calls':1,'wall_s':60.},
                            stopping_conditions=['One read only'],limitations=['No causal conclusion']))
                    name='design.respond_diagnosis';version='3.0.0'
                resolved=adapter.resolve_business(name,args);resolved.update(workflow.fixed(role['phase']).get(name,{}))
                receipt=host.invoke(dict(request_id='offline-'+role['phase'],tool_id=name,tool_version=version,arguments=resolved,
                    reason='Engineer-authored offline handoff fixture',cache='new'))
                self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
            with patch('tools.diagnostic_workflow.run_loop',side_effect=fixture):
                workflow.phase('improvement','search_batch_plan','search_plan',factual_audit=workflow.store.artifact(workflow.freeze['current_factual_audit']))
                summary=dict(mode='offline_test_fixture',batch_id='actual-offline-fixture',candidates=[])
                ref=save(workflow.store,summary)
                workflow.phase('response_final','design_response','final_response',batch_result=summary,require_research_route=True,
                    improvement_feedback_content=dict(baseline_facts=workflow.historical_feedback['baseline_facts'],execution=None),check_feedback=[dict(reference=ref)])
            self.assertEqual(workflow.store.artifact(workflow.chain['final_response'])['next_research']['route'],'initialization_selection')
            self.assertTrue(all(p['max_tokens']==65536 for p in seen))
            self.assertTrue(all(len(json.dumps(p).encode())<400000 for p in seen))
            self.assertEqual(workflow.store.remaining()['used']['model_calls'],0)
            self.assertEqual(workflow.store.remaining()['used']['backend_solves'],0)
