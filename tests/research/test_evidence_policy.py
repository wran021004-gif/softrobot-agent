"""Synthetic evidence only. No model, physics or provider launch."""
from copy import deepcopy
import unittest
from tools.research.evidence_policy import (summarize_evidence,check_inference,hypothesis_catalog,
    paired_evidence,statistical_evidence)
from tools.research.contracts import EvidenceSummary
from tools.research import analysis
from tests.research import test_task_analysis_contract as task_fixtures

REF=dict(artifact_id='a'*64,media_type='application/json')


def model(conclusion='diagnostic',verification='fixed_state_box_minimum'):
    return dict(status='computed',candidate=REF,raw={'fixture':True},
        analysis_applicability=dict(status='applicable',full_task_supported=False),
        scoped_claim=dict(conclusion=conclusion,verification_status=verification,
            binding=dict(candidate=REF,task_identity='task',physical_design_identity='design'),
            model_identity='model',operating_point=dict(time_s=.3),horizon=dict(duration_s=.01),
            constraint_coverage=[dict(constraint_id='speed',analyzed_indices=[30])],
            numerical_result_pointer='/raw'))


def physical(valid=True,passed=True):
    components={k:dict(passed=valid) for k in ('evaluation_validity','execution_complete','holding_coverage','solver_errors','force_bounds')}
    components.update({k:dict(passed=passed,value=.001,limit=.01,unit='m') for k in ('evaluator:task_bound','holding_position','holding_speed')})
    return dict(candidate=REF,model_identity='model',design_identity='design',status='evaluated',
        execution_id='fixture-execution',acceptance=dict(accepted=passed,task_identity='task',components=components,timing={'duration_s':.35}))


class EvidencePolicyTests(unittest.TestCase):
    def test_instantaneous_braking_never_whole_task(self):
        r=summarize_evidence(model(),REF)
        self.assertEqual(r['claim_kind'],'NUMERICAL_DIAGNOSTIC')
        self.assertFalse(check_inference(r,'whole_horizon_from_instantaneous_braking')['allowed'])
        self.assertFalse(check_inference(r,'observed_task_pass')['allowed'])

    def test_static_sensitivity_cannot_predict_readapted_dynamics(self):
        r=summarize_evidence(model(verification='perturbed_equilibria_checked'),REF)
        self.assertFalse(check_inference(r,'adapted_dynamic_improvement_from_static_sensitivity')['allowed'])

    def test_unreliable_kkt_or_failed_solver_is_not_exclusion(self):
        for value in [dict(status='failed',solver_status='failed'),dict(kkt={'reliability':'solver_unresolved'})]:
            r=summarize_evidence(value,REF)
            self.assertEqual(r['claim_kind'],'NUMERICAL_DIAGNOSTIC')
            self.assertFalse(check_inference(r,'structural_infeasibility')['allowed'])

    def test_refinement_failure_downgrades_coarse_witness(self):
        value=model('feasible_witness','independent_discrete_replay_passed');original=deepcopy(value)
        for refined in [dict(complete=True,original_task_satisfied=False),dict(complete=False),{}]:
            r=summarize_evidence(value,REF,refinement=refined)
            self.assertEqual(r['claim_kind'],'NUMERICAL_DIAGNOSTIC')
            self.assertFalse(check_inference(r,'model_sampled_feasibility')['allowed'])
        self.assertEqual(original,value)

    def test_no_unknown_candidate_descent_guarantee(self):
        value=model('feasible_witness','independent_discrete_replay_passed');value['prospective_guarantee']=True
        r=summarize_evidence(value,REF)
        self.assertFalse(r['prospective_guarantee'])
        self.assertFalse(check_inference(r,'unvisited_simulation_descent_guarantee')['allowed'])
        with self.assertRaises(ValueError):EvidenceSummary.model_validate({**r,'prospective_guarantee':True})

    def test_missing_model_certificate_does_not_block_legal_search(self):
        r=summarize_evidence({},None)
        self.assertTrue(check_inference(r,'empirical_search',legal_candidate=True)['allowed'])
        self.assertFalse(check_inference(r,'empirical_search',legal_candidate=False)['allowed'])

    def test_physical_success_cannot_transfer_between_tasks_designs_models(self):
        r=summarize_evidence(physical(),REF)
        keys=('task_identity','candidate_identity','model_identity','design_identity','operating_point','covered_samples')
        target={k:r[k] for k in keys}
        self.assertTrue(check_inference(r,'observed_task_pass',target=target)['allowed'])
        for k in keys:
            with self.subTest(field=k):
                self.assertFalse(check_inference(r,'observed_task_pass',target={**target,k:'changed'})['allowed'])

    def test_invalid_physical_observation_does_not_pass(self):
        r=summarize_evidence(physical(valid=False),REF)
        self.assertEqual(r['claim_kind'],'NUMERICAL_DIAGNOSTIC')
        self.assertFalse(check_inference(r,'observed_task_pass')['allowed'])

    def test_scoped_model_witness_and_exclusion_remain_scoped(self):
        for conclusion,status,kind,inference in [
                ('feasible_witness','kernel_independent_checks_passed','MODEL_WITNESS','model_sampled_feasibility'),
                ('model_infeasibility_certificate','kernel_separating_lower_bound_verified','MODEL_EXCLUSION','model_input_box_exclusion')]:
            r=summarize_evidence(model(conclusion,status),REF)
            self.assertEqual(r['claim_kind'],kind);self.assertTrue(check_inference(r,inference)['allowed'])
            self.assertFalse(check_inference(r,'global_nonlinear_infeasibility')['allowed'])

    def test_missing_reference_pointer_or_identity_never_certifies(self):
        value=model('feasible_witness','kernel_independent_checks_passed')
        self.assertEqual(summarize_evidence(value,None)['claim_kind'],'UNVERIFIED_HYPOTHESIS')
        del value['raw']
        self.assertEqual(summarize_evidence(value,REF)['claim_kind'],'NUMERICAL_DIAGNOSTIC')
        value=model('feasible_witness','kernel_independent_checks_passed');value['scoped_claim']['model_identity']=None
        self.assertEqual(summarize_evidence(value,REF)['claim_kind'],'NUMERICAL_DIAGNOSTIC')

    def test_catalog_describes_hypotheses_not_causes(self):
        catalog=hypothesis_catalog();self.assertEqual(len(catalog),5)
        for entry in catalog.values():
            self.assertEqual(entry['claim_kind'],'UNVERIFIED_HYPOTHESIS');self.assertIsNone(entry['probability'])
            self.assertTrue(entry['discriminating_experiments']);self.assertIn('identified_root_cause',entry['forbidden_inferences'])

    def test_paired_comparison_requires_same_metrics_and_task(self):
        a=summarize_evidence(physical(),REF)
        b=summarize_evidence(physical(passed=False),dict(artifact_id='b'*64))
        self.assertTrue(check_inference(paired_evidence(a,b,REF),'paired_observed_difference')['allowed'])
        b['covered_samples']['components']['holding_speed']['limit']=2.
        self.assertFalse(check_inference(paired_evidence(a,b,REF),'paired_observed_difference')['allowed'])
        b['task_identity']='other'
        self.assertFalse(check_inference(paired_evidence(a,b,REF),'paired_observed_difference')['allowed'])

    def test_statistics_record_method_samples_uncertainty_without_population_claim(self):
        r=statistical_evidence([REF],'synthetic_method',{'standard_error':.1},REF)
        self.assertEqual(r['claim_kind'],'STATISTICAL_EVIDENCE');self.assertEqual(r['covered_samples']['count'],1)
        self.assertFalse(check_inference(r,'population_superiority')['allowed'])
        self.assertFalse(check_inference(statistical_evidence([],None,{},REF),'reported_sample_statistic')['allowed'])

    def test_existing_math_results_are_unmodified_with_additive_views(self):
        task_fixtures.TaskAnalysisTests.setUpClass();fixture=task_fixtures.TaskAnalysisTests();fixture.setUp()
        value=fixture.compute_fixture();original=deepcopy(value)
        compact=analysis.compact_result(value,REF);decision=analysis.decision_result(value,REF)
        self.assertEqual(value,original);self.assertEqual(compact['scoped_claim'],original['scoped_claim'])
        # F2 keeps inference strength in the decision view and retrieves repeated
        # operating-point/configuration/coverage from the original scope pointer.
        self.assertEqual({k:v for k,v in compact['evidence_summary'].items() if k not in
            ('operating_point','covered_samples','assumptions')},decision['evidence_summary'])
        self.assertEqual(compact['evidence_summary']['claim_kind'],'MODEL_WITNESS')


if __name__=='__main__':unittest.main()
