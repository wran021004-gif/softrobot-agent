"""Focused engineering fixtures for the actual producer/consumer tool path."""
from copy import deepcopy
from contextlib import closing
import hashlib
import gc
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from tools.platform_store import Store,plain,encode
from tools.platform_diagnosis_coordinator import configure_role
from tools.diagnostic_facts import handover,record_read
from tools.diagnostic_revision import ensure_aliases
from tools.diagnostic_handoff import engineering_fixture,consume_handoff,numerical_eligibility
from tools.working_state import project_working_state
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.platform_search import validate_batch_plan
from examples.stage356_milestone2 import prepare,ROOT


class Milestone2Tests(TestCase):
    def test_actual_check_revision_plan_and_host_lineage(self):
        with TemporaryDirectory(dir=ROOT/'runs') as directory:
            workflow=prepare('single_context',Path(directory)/'fixture');host=workflow.host('diagnostic');store=workflow.store
            def phase(name,role='diagnostic',**extra):
                context=dict(phase=name,binding=workflow.binding,identities=workflow.identities,
                    inventory=workflow.inventory,request=workflow.chain['request'],source_record=workflow.source_record,
                    source_report=workflow.common['source_report'],historical_feedback=workflow.common['feedback'],
                    improvement_feedback_content=workflow.historical_feedback,memory_identity=host.run_id,native_store_root=str(host.store.root),
                    protocol=dict(saved_state_check=workflow.scope),phase_tools=list(workflow.tools),native_fixed=workflow.fixed(name))
                configure_role(host,role,workflow.instructions[name],**{**context,**extra});host.resume()
            def invoke(tool,args):
                receipt=host.invoke(dict(request_id='fixture-'+str(len(store.events(host.run_id))),tool_id=tool,tool_version=workflow.tools[tool],
                    arguments=args,reason='Engineer-authored offline fixture',cache='new'))
                self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
                return store.artifact(receipt['output'])['reference']
            phase('initial')
            handover(host,workflow.summary,store.artifact(workflow.summary),origin={'fixture':True},kind='common_summary')
            handover(host,workflow.common['feedback'],workflow.historical_feedback,origin={'fixture':True},kind='campaign_comparison')
            state=store.session(host.run_id)['state'];rows=list(state['fact_catalog'].values())
            speed=next(r['selector'] for r in rows if r['selector']['pointer']=='/detail/summary/late_max_speed_m_s')
            reach=next(r['selector'] for r in rows if r['selector']['pointer']=='/detail/summary/reach_passed')
            report=dict(previous_report=None,request=workflow.chain['request'],check_results=[],missing_evidence=[],recommendations=[dict(
                recommendation_id='wait',action='defer',rationale='Inspect prediction detail first.',configuration_scope=workflow.identities['configuration'])],
                fact_selectors={'speed':[speed],'reach':[reach]},report=dict(subject='control',source=workflow.binding,
                facts=[dict(fact_id='speed',statement='Holding speed failed.',evidence=[speed['reference']]),dict(fact_id='reach',statement='Reach passed.',evidence=[reach['reference']])],
                attribution=[dict(cause='prediction_disagreement',status='possible',fact_ids=['speed'],reason='Need aligned velocity errors to assess local disagreement.')]))
            initial=invoke('diagnosis.submit',report);workflow.chain['initial_report']=initial
            phase('response_initial','design',report=initial)
            workflow.chain['initial_response']=invoke('design.assess_diagnosis',dict(report=initial,disposition='defer',reasoning='Inspect archived detail.',next_action='request_check'))
            phase('check',previous_report=initial,previous_report_content=store.artifact(initial),max_checks=1,check_feedback=[])
            state=store.session(host.run_id)['state'];table=ensure_aliases(state)['aliases']
            alias=next(a for a,h in table.items() if state['fact_catalog'][h]['selector']==speed)
            proposal=dict(question='Do accepted first-step velocities disagree with measured next endpoints at update 34?',assessment_ids=['prediction_disagreement'],
                relationships=[dict(assessment_id='prediction_disagreement',relationship='supporting',references=[alias],relevance='Failed holding speed motivates a prediction consistency check; it does not establish mismatch.')],
                missing_information=['Selected aligned velocity difference not in initial summary.'],operation='evidence_query',view='prediction',update_ids=[34],units=['m/s','s'],
                expected=[dict(assessment_id='prediction_disagreement',observation='Large endpoint velocity difference',effect='retain'),
                    dict(assessment_id='prediction_disagreement',observation='Small endpoint difference',effect='weaken')],
                distinguishes='Quantifies local disagreement at a selected late update; cannot explain the entire trajectory.',limitations=['Selected endpoint only.'],
                work_limits={'wall_s':180.,'tool_calls':1.},stopping_conditions=['One query; then revision.'])
            payload=payload_for(host,EvidenceDrivenAdapter());self.assertLess(len(encode(payload).encode()),400000)
            self.assertEqual({t['function']['name'] for t in payload['tools']},{'diagnosis_propose_check','diagnosis_inspect_evidence','diagnosis_submit','diagnosis_request','diagnosis_check_request','evidence_read','design_respond_diagnosis','design_assess_diagnosis','diagnosis_revise_assessment','design_submit_search_plan'})
            checked=invoke('diagnosis.propose_check',proposal);value=store.artifact(checked)
            view=project_working_state(store,host.run_id)
            self.assertEqual(consume_handoff(store,view,value['handoff']).scope['source_report'],workflow.common['source_report'])
            for field in ('task','model','controller','source_report','previous_assessment','feedback','grant','baseline'):
                invalid=deepcopy(value['handoff']);invalid['scope'][field]={'forged':True}
                with self.subTest(field=field),self.assertRaises((ValueError,KeyError)):consume_handoff(store,view,invalid)
            eligibility=numerical_eligibility(store,workflow.binding);self.assertEqual(eligibility['local_comparison'],[34])
            invalid=deepcopy(proposal);invalid.update(operation='local_comparison',view=None,update_ids=[33],changed_parameter='holding_tip_speed_weight',changed_value=.1)
            phase('check',previous_report=initial,previous_report_content=store.artifact(initial),max_checks=1,check_feedback=[],adopted_parameter={'parameter':'holding_tip_speed_weight','value':.1})
            from tools.diagnostic_handoff import propose_check
            from schemas.platform_handoff import CheckProposal
            class Context:
                run_id=host.run_id
            ctx=Context();ctx.store=store
            with self.assertRaisesRegex(ValueError,'INELIGIBLE'):propose_check(ctx,CheckProposal.model_validate(invalid))
            invocation=dict(request_id='fixture-query',tool_id='diagnosis.inspect_evidence',tool_version='1.0.0',arguments=dict(binding=workflow.binding,view='prediction',update_ids=[34]),reason='Recorded proposal selected this query',cache='new')
            receipt=host.invoke(invocation);self.assertEqual(receipt['execution_status'],'completed')
            coverage=store.session(host.run_id)['state']['read_ledger'][-1]['coverage']
            from tools.diagnostic_workflow import save
            feedback=save(store,dict(proposal=checked,previous_assessment=initial,receipt=receipt,result=receipt['output'],kind='newly_read_historical_evidence',coverage=coverage,execution_id=workflow.execution,binding=workflow.binding))
            workflow.chain['feedback']=feedback
            state=store.session(host.run_id)['state'];table=ensure_aliases(state)['aliases']
            result_alias=next(a for a,h in table.items() if state['fact_catalog'][h]['selector']['reference']==receipt['output'] and
                state['fact_catalog'][h]['selector']['pointer'].endswith('/velocity/vector_difference_norm_m_s'))
            revision=dict(changes=[dict(kind='hypothesis',identifier='prediction_disagreement',disposition='unresolved',supporting_fact_ids=['aligned_error'],reason='New selected endpoint evidence bounds disagreement; it does not identify causality.')],
                new_facts=[dict(fact_id='aligned_error',statement='An aligned endpoint velocity difference is recorded.',references=[result_alias])],
                recommendation='Bound a future speed-weight batch.',rationale='Preserve physical acceptance and test holding.',result_interpretation='Selected prediction and measured motion are distinct.',
                expected_observations_interpretation='This single endpoint cannot resolve the complete trajectory question.',remaining_uncertainty=['Dominant cause.'],resolving_evidence=['Future bounded physical comparison.'])
            phase('revision',previous_report=initial,previous_report_content=store.artifact(initial),proposal=checked,result_feedback=feedback,
                check_feedback=[dict(reference=feedback,receipt=receipt,result=receipt['output'])])
            revised=invoke('diagnosis.revise_assessment',revision);workflow.chain['revised_report']=revised
            self.assertEqual(store.artifact(revised)['check_results'],[feedback])
            phase('improvement','design',previous_report=revised,result_feedback=feedback,delivery_tool='design.submit_search_plan')
            plan=dict(hypothesis='Increasing speed costs may improve holding.',evidence=[result_alias],weakening_observations=['No physical improvement or reach loss.'],
                variables={'control/recipe/holding_tip_speed_weight':[.01,.1]},fixed_conditions=['robot','task','acceptance','controller_implementation','other_numerical_settings'],
                fixed_controller='controller.gvs_nmpc@7.0.0',objectives=['joint_reach_holding_acceptance','terminal_error_m','holding_max_error_m','holding_max_speed_m_s'],
                constraints=['frozen_acceptance','force_bounds','finite_valid_execution'],method='search.family_coordinate@1.0.0',max_candidates=3,step=.2,
                planned_budget=dict(model_calls=0,tool_calls=12,wall_s=2970.,backend_solves=3,worker_calls=0),fidelity_limits=['Projected predictions cannot certify physical outcomes.'],
                verification=['candidate.apply','simulation.run','evaluation.run','control.profile_report','bound_comparison','diagnostic_revision'],
                stopping_conditions=['Candidate count, grant exhaustion, or achieved joint acceptance.'],scientific_promise='uncertain',rationale='One endpoint cannot establish a cause.')
            accepted=invoke('design.submit_search_plan',plan);self.assertFalse(store.artifact(accepted)['execution_authorized'])
            from tools.diagnostic_handoff import bind_handoff
            role={**store.session(host.run_id)['state']['role_context'],'previous_report':revised}
            updated=bind_handoff(store,project_working_state(store,host.run_id),role,value['handoff']['assessments'],value['handoff']['check'],check_result=feedback)
            self.assertEqual(consume_handoff(store,project_working_state(store,host.run_id),updated).scope['check_result'],feedback)
            workflow.chain.update(check=checked,feedback=feedback,revised_handoff=save(store,updated),search_plan=accepted)
            self.assertEqual(project_working_state(store,host.run_id).experiment_plan['reference'],accepted)
            for change in (dict(fixed_controller='controller.gvs_nmpc@6.0.0'),dict(method='not_installed@1.0.0'),
                    dict(variables={'design/section_scale':[.95,1.1]}),dict(planned_budget=dict(model_calls=0,tool_calls=1,wall_s=1.,backend_solves=0,worker_calls=0))):
                with self.subTest(change=change),self.assertRaises(ValueError):validate_batch_plan(store,project_working_state(store,host.run_id),{**plan,**change})
            before=store.remaining()
            with closing(store.connect(True)) as db:fp=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
            project_working_state(store,host.run_id);payload_for(host,EvidenceDrivenAdapter())
            with closing(store.connect(True)) as db:self.assertEqual(fp,hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest())
            self.assertEqual(before,store.remaining());self.assertEqual(before['used']['backend_solves'],0)
            phase('response_final','design',report=revised,previous_report=revised,result_feedback=feedback,
                experiment_plan=accepted,check_feedback=[dict(reference=workflow.common['feedback'])],final_response=True)
            workflow.chain['final_response']=invoke('design.respond_diagnosis',dict(report=revised,disposition='defer',reasoning='Unresolved interpretation; future grant required.',
                next_action='finish',candidate_disposition='defer_selection',selected_candidate=None,feedback=workflow.common['feedback']))
            from examples.stage356_milestone2 import acceptance
            from unittest.mock import patch
            with closing(store.connect(True)) as db:numerical=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
            fixture_export=Path(directory)/'gate';(fixture_export/workflow.mode).mkdir(parents=True)
            with patch('examples.stage356_milestone2.EXPORT',fixture_export):
                gate=acceptance(workflow,dict(chain=workflow.chain,status='completed',usage=store.remaining(),numerical_work=numerical))
            self.assertTrue(gate['passed'],gate)
            gc.collect()

    def test_fixture_relationship_amendment_and_scope(self):
        store=Store(ROOT/'runs/stage354_milestone0_20261003/dual_context')
        with closing(store.connect(True)) as db:identity=next(r[0] for r in db.execute('SELECT run_id FROM sessions') if r[0].endswith('design'))
        view=project_working_state(store,identity);fixture=engineering_fixture(store,view)
        self.assertTrue(all(not row.contradicting for row in fixture.assessments))
        bad=fixture.model_copy(update={'provenance':'accepted_diagnostic_product'})
        with self.assertRaisesRegex(ValueError,'ACCEPTED_PRODUCT_REQUIRED'):consume_handoff(store,view,bad)

    def test_dual_context_fresh_input_payload_and_role_isolation(self):
        with TemporaryDirectory(dir=ROOT/'runs') as directory:
            w=prepare('dual_context',Path(directory)/'dual')
            diagnostic=w.host('diagnostic');design=w.host('design')
            for host,role in ((diagnostic,'diagnostic'),(design,'design')):
                configure_role(host,role,w.instructions['initial'],phase='initial',binding=w.binding,identities=w.identities,
                    source_record=w.source_record,source_report=w.common['source_report'],historical_feedback=w.common['feedback'],
                    source_report_content=w.store.artifact(w.common['source_report']),improvement_feedback_content=w.historical_feedback,
                    common_scientific_input=w.common,inventory=w.inventory,memory_identity=host.run_id,native_store_root=str(w.directory),
                    native_fixed=w.fixed('initial'),phase_tools=['diagnosis.submit'],evidence_turn_limit=0)
                handover(host,w.summary,w.store.artifact(w.summary),origin={'fixture':True},kind='common_summary')
                handover(host,w.common['feedback'],w.historical_feedback,origin={'fixture':True},kind='campaign_comparison')
                payload=payload_for(host,EvidenceDrivenAdapter());self.assertLess(len(encode(payload).encode()),400000)
                self.assertEqual(payload['model'],'deepseek-flash');self.assertEqual(payload['max_tokens'],65536)
                self.assertEqual(payload['reasoning_effort'],'high');self.assertEqual(payload['thinking'],{'type':'enabled'})
                self.assertEqual(w.store.session(host.run_id)['snapshot']['input']['policy']['model']['protocol_recovery'],dict(max_total=4,max_consecutive=2))
            ds=w.store.session(diagnostic.run_id)['state'];ss=w.store.session(design.run_id)['state']
            self.assertNotEqual(project_working_state(w.store,diagnostic.run_id).evidence['context_id'],
                project_working_state(w.store,design.run_id).evidence['context_id'])
            from tools.diagnostic_workflow import save
            private=save(w.store,dict(fixture_private_value=123.))
            handover(diagnostic,private,w.store.artifact(private),origin={'context':diagnostic.run_id},kind='fixture_private_read')
            self.assertNotIn(private,project_working_state(w.store,design.run_id).evidence['permitted_references'])
            self.assertFalse(ds.get('workflow_memory'));self.assertFalse(ss.get('workflow_memory'))
            self.assertEqual(w.store.remaining()['limit'],w.limits)
            from tools.diagnostic_handoff import source_record
            self.assertEqual(source_record(w.store,w.source_record)['verified_source_bundle'],__import__('tools.state_io',fromlist=['digest']).digest(w.common))
            gc.collect()
