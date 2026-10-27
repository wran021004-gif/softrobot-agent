"""C3.2 error reproductions only; no Provider, Store writes or scientific workers."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tools.research.agent import error_feedback,plan_schema
from tools.research.contracts import Plan,LocalControlSearchSettings,NativeControlOptimization
from tests.research.test_research_reporting import offline_host


class ExecutionFeedbackTests(unittest.TestCase):
    def test_schema_exposes_intent_only_routing_and_nonzero_native_cost(self):
        schema=plan_schema(['diagnose','control_search'],decision_required=True)
        fields=schema['$defs']['ResearchDecision']['properties']
        self.assertIn('Intent label only',fields['selected_method']['description'])
        self.assertIn('research_analysis',fields['selected_method']['description'])
        self.assertIn('not actual cost or authorization',fields['requested_budget']['description'])
        self.assertIn('unknown costs remain unresolved',fields['requested_budget']['description'])
        self.assertIn('physical replay',schema['$defs']['LocalControlSearchSettings']['properties']['evaluation_requests']['description'])

    def test_rejected_regularization_has_precise_shared_settings_correction(self):
        reference=dict(artifact_id='a'*64,media_type='application/json')
        value=dict(action='control_search',hypothesis='Fixture only',expected_observation='Fixture',
            weakening_observation='Fixture',fixed_conditions='Fixture',stopping_condition='Fixture',
            interpretation='Fixture',control_search=dict(candidate=reference,source=reference,
                settings=dict(regularization=1.)))
        native=dict(source=reference,settings=dict(version='local_control_search_v2',
            correction_window_s=[0.,.35],regularization=1.))
        for contract,payload,tool,path in ((Plan,value,'research_plan','control_search.settings.regularization'),
                (NativeControlOptimization,native,'research_analysis','settings.regularization')):
            host,current=offline_host({});before=deepcopy(current)
            with self.assertRaises(ValueError) as caught:contract.model_validate(payload)
            with patch('tools.research.agent.record',return_value=reference):
                feedback=error_feedback(host,dict(name=tool,input=payload),caught.exception,before)
            self.assertEqual(feedback['field'],path)
            self.assertEqual(feedback['status'],'rejected')
            self.assertFalse(feedback['scientific_execution_started'])
            self.assertIn('regularization is not supported',feedback['expected'])
            fields=feedback['expected'].split('fields: ',1)[1].split('. Plan ',1)[0].split(', ')
            self.assertEqual(set(fields),set(LocalControlSearchSettings.model_fields))
            self.assertNotIn('regularization',fields)
            self.assertIn('normal authorization and cost admission',feedback['expected'])
            self.assertEqual(current,before)
            host.store.reserve.assert_not_called();host.store.transaction.assert_not_called()

    def test_family_search_validation_reports_matching_union_branch(self):
        host,current=offline_host({});reference=dict(artifact_id='c'*64,media_type='application/json')
        search=dict(version='family_mixed_search_v1',family_space_identity='a'*64,variable_groups=['lengths'],
            segment_counts=[2],tendon_counts=[4],screening_fidelity='standard',objective='task_violation',
            operating_point='standardized_initial_pretension',max_proposals=1,max_evaluations=1,
            evaluation_mode='mujoco_control',initial_tension_n=.2,control_settings=None)
        value=dict(action='search',search=search,hypothesis='Fixture',expected_observation='Fixture',
            weakening_observation='Fixture',fixed_conditions='Fixture',stopping_condition='Fixture',interpretation='Fixture')
        with self.assertRaises(ValueError) as caught:Plan.model_validate(value)
        with patch('tools.research.agent.record',return_value=reference):
            feedback=error_feedback(host,dict(name='research_plan',input=value),caught.exception,current)
        self.assertIn('FamilyMixedSearch',feedback['field'])
        self.assertIn('NATIVE_SEARCH_REQUIRES',feedback['expected'])
        self.assertFalse(feedback['scientific_execution_started'])

    def test_v2_generation_error_does_not_recommend_v1(self):
        host,current=offline_host({});reference=dict(artifact_id='d'*64,media_type='application/json')
        value=dict(action='generate',hypothesis='Fixture',expected_observation='Fixture',weakening_observation='Fixture',
            fixed_conditions='Fixture',stopping_condition='Fixture',interpretation='Fixture',
            generation=dict(version='serial_family_generation_v2',family_space_identity='fixture',segment_count=1,
                tendon_count=3,segments={'segment_0':dict(length_m=.1)}))
        with self.assertRaises(ValueError) as caught:Plan.model_validate(value)
        with patch('tools.research.agent.record',return_value=reference):
            feedback=error_feedback(host,dict(name='research_plan',input=value),caught.exception,current)
        self.assertIn('GenerationRequestV2',feedback['field'])
        self.assertNotIn('serial_family_generation_v1',feedback['expected'])
        self.assertIn('integer',feedback['expected'])

    def test_unrelated_unknown_parameter_keeps_its_original_error(self):
        host,current=offline_host({});reference=dict(artifact_id='b'*64,media_type='application/json')
        with self.assertRaises(ValueError) as caught:LocalControlSearchSettings.model_validate(dict(other_field=1))
        with patch('tools.research.agent.record',return_value=reference):
            feedback=error_feedback(host,dict(name='research_plan',input={}),caught.exception,current)
        self.assertEqual(feedback['field'],'other_field')
        self.assertNotIn('regularization',feedback['expected'])
        self.assertFalse(feedback['scientific_execution_started'])


if __name__=='__main__':unittest.main()
