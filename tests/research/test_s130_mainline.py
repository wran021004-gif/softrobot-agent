"""T3 contract fixtures. Saved scientific arrays; no scientific worker or Provider."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.platform_store import plain
from tools.state_io import digest, atomic_json
from tools.research import analysis, reporter, optimal_capability as opt
from tools.research.contracts import AnalysisRequest
from tools.research.state import state,update,save
from tools.research.evidence_views import result_card
from tools.research.research_context import mathematical_decision_view,agent_decision_brief
from tools.research.evidence_policy import mathematical_physical_relation,summarize_evidence
from tests.research import test_s129_agent_reporting as fixtures


def saved():
    root=Path('evidence')
    return (json.loads((root/'s129_math_capability/gvs_pair.json').read_text()),
        json.loads((root/'s130_optimal_capability/comparison.json').read_text()),
        json.loads((root/'s130_optimal_capability/t2_final_comparison.json').read_text()))


class MainlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.AgentReportingTests.setUpClass()
        cls.pair,cls.t1,cls.t2=saved()

    def setUp(self):
        self.f=fixtures.AgentReportingTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.h=self.f.h
        for value in self.pair['supporting_artifacts'].values():save(self.h,value,'T3_saved_fixture')
        spec=deepcopy(state(self.h)['spec'])
        spec['mathematical_methods']={opt.CONIC:'T3 offline fixture authorization',opt.SENSITIVITY:'T3 offline fixture authorization'}
        spec['budgets']['mathematical_evaluations']=30
        update(self.h,spec=spec,candidates={},mathematical_evaluations=0)
        self.base=deepcopy(self.pair['baseline'])
        self.query=AnalysisRequest.model_validate(dict(self.base['requested_operation'],capability_method=opt.CONIC))

    def conic(self):
        raw=deepcopy(self.base)
        raw['trajectory']=deepcopy(self.t1['cases']['baseline']['conic'])
        raw['charged_analysis_evaluations']=2  # Synthetic new-method accounting fixture.
        return analysis.scoped_result(raw,
            __import__('schemas.platform_analysis',fromlist=['TaskAnalysisRequirement']).TaskAnalysisRequirement.model_validate(raw['task_analysis']),
            raw['analysis_applicability'],self.query)

    def sensitivity(self,index=0):
        raw=deepcopy(self.base);raw.pop('trajectory');raw['optimal_sensitivity']=deepcopy(self.t2['analyses'][index])
        raw['charged_analysis_evaluations']=9  # Synthetic new-method accounting fixture.
        from schemas.platform_analysis import TaskAnalysisRequirement
        return analysis.scoped_result(raw,TaskAnalysisRequirement.model_validate(raw['task_analysis']),raw['analysis_applicability'],self.query)

    def register(self,raw):
        ref=save(self.h,raw,'T3_offline_decision_fixture')
        update(self.h,analysis_results=state(self.h).get('analysis_results',[])+[ref])
        return ref

    def test_legacy_serialization_and_explicit_authorization(self):
        old=self.base['requested_operation']
        self.assertEqual(plain(AnalysisRequest.model_validate(old)),old)
        self.assertEqual(digest(plain(AnalysisRequest.model_validate(old))),digest(old))
        spec=deepcopy(state(self.h)['spec']);spec.pop('mathematical_methods')
        with patch.object(opt,'dependencies',return_value={'available':True}):
            fit=opt.method_admission(spec,self.query)
        self.assertEqual(fit['status'],'not_applicable')
        self.assertIn('AUTHORIZATION',fit['reasons'][0])

    def test_identical_information_decision_fixture_arms(self):
        case=json.loads(Path('tests/research/fixtures/s130_decision_cases.json').read_text())
        before=self.h.store.remaining()
        legacy=self.register(self.base);new=self.register(self.conic())
        arms=[dict(shared=deepcopy(case['shared_information']),mathematics=mathematical_decision_view(plain(result_card(self.h,r)))) for r in (legacy,new)]
        self.assertEqual(arms[0]['shared'],arms[1]['shared'])
        self.assertIn('best_found_violation',arms[0]['mathematics']['capability'])
        self.assertIn('support_lower_estimate',arms[1]['mathematics']['capability'])
        self.assertEqual(self.h.store.remaining(),before)
        self.assertEqual({c['id'] for c in case['cases']},set('ABCDEF'))

    def test_conic_selected_only_when_explicit_with_same_model_builder(self):
        candidate=self.h.store.artifact(self.base['candidate'])
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration',return_value=self.base['raw']) as builder,patch(
                'extensions.math_analysis.conic_capability.conic_capability',return_value=deepcopy(self.t1['cases']['baseline']['conic'])) as conic,patch(
                'extensions.math_analysis.task_capability.task_capability',side_effect=AssertionError('SLSQP not selected')):
            result=analysis.calculate(candidate['configuration'],self.base['binding'],plain(self.query))
        self.assertEqual(builder.call_count,1);self.assertEqual(conic.call_count,1)
        self.assertEqual(result['trajectory']['method_version'],opt.CONIC)
        old=AnalysisRequest.model_validate(self.base['requested_operation'])
        with patch('extensions.tendon_family.math_analysis.calculate_candidate_configuration',return_value=self.base['raw']),patch(
                'extensions.math_analysis.task_capability.task_capability',return_value=self.base['trajectory']) as slsqp,patch(
                'extensions.math_analysis.conic_capability.conic_capability',side_effect=AssertionError('Legacy cannot select conic')):
            result=analysis.calculate(candidate['configuration'],self.base['binding'],plain(old))
        self.assertEqual(slsqp.call_count,1);self.assertEqual(result['trajectory'],self.base['trajectory'])

    def test_conic_l2_l1_l0_exact_sources_and_no_physical_pass(self):
        from tools.research.core import read_evidence
        raw=self.conic();ref=self.register(raw)
        card=plain(result_card(self.h,ref));view=mathematical_decision_view(card)
        self.assertAlmostEqual(view['capability']['replayed_violation'],-.2,places=8)
        self.assertEqual(view['capability']['optimality_status'],'numerically_checked')
        self.assertEqual(view['capability']['strict_optimality'],'unavailable')
        self.assertEqual(view['cost']['evaluations'],2)
        self.assertNotIn('observed_task_pass',card['evidence_summary']['supported_inferences'])
        self.assertNotEqual(card['mathematics']['claim']['conclusion'],'model_infeasibility_certificate')
        for row in card['mathematics']['quantities']:
            if row['source']:self.assertEqual(read_evidence(self.h,row['source'],record_read=False),row['value'])
        reporter.scientific_feedback(self.h,dict(reference=ref),{})
        packet=agent_decision_brief(self.h)
        self.assertEqual(packet['latest_reports'][-1]['findings'][0]['mathematics']['capability']['replayed_violation'],raw['trajectory']['replayed_violation'])
        self.assertNotIn('"soc_vector"',json.dumps(packet))
        self.assertNotIn('"discrete_dynamics"',json.dumps(packet))

    def test_sensitivity_length_flat_and_unresolved_views(self):
        from tools.research.core import read_evidence
        for i,status in enumerate(('stable_reoptimized_direction_envelope_unresolved','numerically_flat_fd_envelope_unresolved')):
            raw=self.sensitivity(i);ref=self.register(raw);card=plain(result_card(self.h,ref))
            decision=mathematical_decision_view(card)
            self.assertEqual(decision['cost']['evaluations'],9)
            view=decision['optimal_sensitivity']
            self.assertEqual(view['direction_status'],status)
            self.assertEqual(view['strict_gradient'],'unavailable')
            self.assertEqual(view['physical_failure_relation']['status'],'not_assessed')
            self.assertEqual(view['local_output_limitation']['world_x_first_order_state_and_input_coefficients'],'zero')
            if i==1:self.assertEqual(view['preferred_parameter_direction'],'unresolved')
            for row in card['mathematics']['quantities']:
                self.assertEqual(read_evidence(self.h,row['source'],record_read=False),row['value'])
            reporter.scientific_feedback(self.h,dict(reference=ref),{})
        packet=agent_decision_brief(self.h)
        self.assertEqual(len(packet['latest_reports']),2)
        self.assertNotIn('"constraint_contributions"',json.dumps(packet))

    def test_mathematical_position_and_physical_speed_mismatch_is_not_causal(self):
        raw=self.sensitivity()
        # Explicit synthetic physical observation to test alignment, not new science.
        physical=dict(status='evaluated',candidate=raw['candidate'],task_identity=raw['binding']['task_identity'],
            acceptance=dict(accepted=False,components={k:dict(passed=True) for k in
                ('evaluation_validity','execution_complete','holding_coverage','solver_errors','force_bounds')}))
        physical['acceptance']['components']['holding_speed']=dict(passed=False,value=.03,limit=.02,unit='m/s')
        ref=save(self.h,physical,'synthetic_T3_contract_observation')
        relation=mathematical_physical_relation(raw,[(ref,physical)])
        self.assertEqual(relation['status'],'constraint_mismatch')
        self.assertEqual(relation['causal_explanation'],'not_established')
        update(self.h,physical_replays=[ref])
        mathref=self.register(raw)
        reporter.scientific_feedback(self.h,dict(reference=mathref),{})
        reportref,report=reporter.current_reports(self.h)[-1]
        handoff=reporter.reporter_handoff_summary(self.h,reportref,report)
        projected=handoff['findings'][0]['mathematics']['optimal_sensitivity']['physical_failure_relation']
        self.assertEqual(projected['status'],'constraint_mismatch')
        from tools.research.core import read_evidence
        for source in projected['sources']:
            self.assertEqual(read_evidence(self.h,dict(reference=source['reference'],pointer=source['pointer']),record_read=False),physical['acceptance']['components'])
        changed=deepcopy(physical);changed['task_identity']='another task'
        self.assertEqual(mathematical_physical_relation(raw,[(ref,changed)])['status'],'not_assessed')
        changed=deepcopy(physical);changed['acceptance']['components']['execution_complete']['passed']=False
        self.assertEqual(mathematical_physical_relation(raw,[(ref,changed)])['status'],'not_assessed')

    def registered_model_fixture(self):
        """Rebind copied saved matrices into an explicitly synthetic offline Study."""
        from tools.research.design import full_science
        from tools.research.task_constraints import describe_analysis_requirements
        models=json.loads(Path('evidence/s130_optimal_capability/t2_models.json').read_text())['models'][:5]
        refs=[];candidates={};imported=[]
        for index,row in enumerate(models):
            c=deepcopy(self.h.store.artifact(self.base['candidate']))
            c.update(configuration=row['configuration'],parameters=row['parameters'],resolved_parameters=row['parameters'])
            c.update(scientific_configuration=full_science(c['configuration']),identity=digest(dict(fixture=index,configuration=c['configuration'])),profile_identity='fixture')
            c['candidate_id']='T3-fixture-'+c['identity'];c['configuration_reference']=save(self.h,c['configuration'],'T3_configuration_fixture')
            ref=save(self.h,c,'T3_candidate_fixture');candidates[c['identity']]=ref;imported.append(ref)
            result=deepcopy(self.base);binding=result['binding']
            binding.update(candidate=ref,candidate_id=c['candidate_id'],configuration=c['configuration_reference'],effective_configuration_identity=digest(c['configuration']))
            result.update(candidate=ref,model=deepcopy(row['model']),implementation=state(self.h)['freeze'])
            result['model']['binding'].update({k:binding[k] for k in ('candidate','candidate_id','configuration','effective_configuration_identity')})
            result['task_analysis']=plain(describe_analysis_requirements(c['configuration'],binding))
            result['requested_operation']['candidate']=ref
            refs.append(save(self.h,result,'T3_registered_model_fixture'))
        update(self.h,candidates=candidates,imported_candidates=imported,imported_candidate_profile={'identity':'fixture'},analysis_results=refs)
        q=AnalysisRequest.model_validate(dict(plain(self.query),candidate=imported[0],optimal_sensitivity=dict(
            variable='segments.near.length_m',steps=[.0005,.00025],model_results=refs)))
        return q

    def test_actual_candidate_model_validation_and_saved_kernel_adapter(self):
        q=self.registered_model_fixture()
        context=opt.sensitivity_context(self.h,q)
        self.assertEqual(len(context['points']),5)
        self.assertEqual(context['parameter']['units'],'m')
        with patch('extensions.math_analysis.capability_sensitivity.capability_sensitivity',return_value=deepcopy(self.t2['analyses'][0])) as kernel:
            result=analysis.calculate({}, {}, plain(q),design_context=context)
        self.assertEqual(kernel.call_count,1)
        self.assertEqual(result['scoped_claim']['conclusion'],'diagnostic')
        self.assertEqual(result['model_reuse']['new_model_builds'],0)
        bad=q.model_copy(update={'optimal_sensitivity':q.optimal_sensitivity.model_copy(update={'steps':[.0006,.00025]})})
        with self.assertRaisesRegex(ValueError,'STENCIL'):opt.sensitivity_context(self.h,bad)
        bad=q.model_copy(update={'optimal_sensitivity':q.optimal_sensitivity.model_copy(update={'variable':'segments.near.unknown'})})
        with self.assertRaisesRegex(ValueError,'AUTHORIZED'):opt.sensitivity_context(self.h,bad)

    def test_partial_coverage_and_positive_optimum_never_exclusion(self):
        raw=self.conic();raw['analysis_applicability']['full_task_supported']=False
        raw['trajectory']['full_requested_coverage']=False
        raw['trajectory'].update(status='inconclusive',replayed_violation=.1,numerical_feasibility='positive_optimum_numerical_evidence')
        raw['trajectory']['replay']['passed']=False
        from schemas.platform_analysis import TaskAnalysisRequirement
        raw=analysis.scoped_result(raw,TaskAnalysisRequirement.model_validate(raw['task_analysis']),raw['analysis_applicability'],self.query)
        ref=self.register(raw);view=mathematical_decision_view(plain(result_card(self.h,ref)))
        self.assertEqual(raw['scoped_claim']['conclusion'],'inconclusive')
        self.assertFalse(view['capability']['full_requested_coverage'])

    def test_missing_dependency_budget_and_models_reject_before_worker(self):
        for environment in ({'available':False},{'available':True}):
            spec=deepcopy(state(self.h)['spec']);spec['budgets']['mathematical_evaluations']=0
            update(self.h,spec=spec);before=deepcopy(state(self.h))
            with patch.object(opt,'dependencies',return_value=environment),patch('tools.service_execution._run_contained',side_effect=AssertionError('worker forbidden')):
                result=analysis.dispatch(self.h,plain(self.query),'deny',guard=lambda *a:None)
            self.assertEqual(result['status'],'not_applicable')
            self.assertTrue(result['admission']['alternatives'])
            self.assertEqual(state(self.h)['mathematical_evaluations'],before['mathematical_evaluations'])
        spec['budgets']['mathematical_evaluations']=30;update(self.h,spec=spec)
        q=AnalysisRequest.model_validate(dict(plain(self.query),optimal_sensitivity=dict(variable='segments.near.length_m',steps=[.001],model_results=[self.base['candidate']]*3)))
        with patch.object(opt,'dependencies',return_value={'available':True}),patch('tools.research.analysis.verify_candidate',return_value={}):
            result=analysis.dispatch(self.h,plain(q),'missing',guard=lambda *a:None)
        self.assertEqual(result['status'],'not_applicable');self.assertIn('REGISTERED',result['reason'])

    def test_multisolve_reservation_failure_recovery_and_receipt_reuse(self):
        q=AnalysisRequest.model_validate(dict(plain(self.query),optimal_sensitivity=dict(variable='segments.near.length_m',steps=[.0005,.00025],model_results=[self.base['candidate']]*5)))
        candidate=self.h.store.artifact(self.base['candidate'])
        calls=[]
        def failed_worker(command,log,timeout):
            calls.append(command)
            self.assertEqual(state(self.h)['mathematical_evaluations'],9)
            atomic_json(Path(command[-1]).with_name('result.json'),dict(status='execution_incomplete',error='offline injected failure'))
            return SimpleNamespace(returncode=1)
        with patch.object(opt,'dependencies',return_value={'available':True}),patch.object(opt,'sensitivity_context',return_value={'kind':opt.SENSITIVITY,'baseline':self.base}),patch('tools.research.analysis.verify_candidate',return_value=candidate),patch('tools.service_execution._run_contained',side_effect=failed_worker):
            result=analysis.dispatch(self.h,plain(q),'multi',guard=lambda *a:None)
            self.assertEqual(state(self.h)['mathematical_evaluations'],9)
            again=analysis.dispatch(self.h,plain(q),'multi',guard=lambda *a:None)
        self.assertEqual(len(calls),1)
        self.assertEqual(again['operation_reuse']['additional_analysis_evaluations'],0)
        raw=self.h.store.artifact(result['reference'])
        self.assertEqual(raw['charged_analysis_evaluations'],9)
        self.assertEqual(raw['method_admission']['dual_face_solves'],4)
        self.assertIsNone(state(self.h)['pending'])

    def test_unknown_termination_retains_charge_and_prevents_relaunch(self):
        candidate=self.h.store.artifact(self.base['candidate'])
        with patch.object(opt,'dependencies',return_value={'available':True}),patch('tools.research.analysis.verify_candidate',return_value=candidate),patch('tools.service_execution._run_contained',side_effect=RuntimeError('unknown')):
            with self.assertRaisesRegex(ValueError,'UNKNOWN_ANALYSIS_TERMINATION'):
                analysis.dispatch(self.h,plain(self.query),'unknown',guard=lambda *a:None)
            self.assertEqual(state(self.h)['mathematical_evaluations'],2)
            with self.assertRaisesRegex(ValueError,'PENDING_ANALYSIS'):
                analysis.dispatch(self.h,plain(self.query),'unknown',guard=lambda *a:None)
        pending=state(self.h)['pending'];folder=Path(pending['folder'])
        atomic_json(folder/'boundary.json',dict(termination_confirmed=True,elapsed_s=.01,returncode=1))
        atomic_json(folder/'numerical_optimal_model_attempt.json',dict(kind='model_build',stage='attempt'))
        result=analysis.recover(self.h)
        raw=self.h.store.artifact(result['reference'])
        self.assertEqual(raw['recorded_attempt_boundaries']['model_build'],1)
        self.assertEqual(raw['recorded_return_boundaries']['model_build'],0)
        self.assertIsNone(raw['actual_mathematical_calls']['capability_kernel_calls'])
        self.assertEqual(state(self.h)['mathematical_evaluations'],2)


if __name__=='__main__':unittest.main()
