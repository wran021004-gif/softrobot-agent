"""Final-answer delivery and qualification feedback; synthetic fixtures only."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from jsonschema import Draft202012Validator

from tools.research.agent import answer_delivery_tools
from tools.research.config import resolve
from tools.research.reporter import qualification_feedback
from tools.research.scientific_intent import complete_execution_profile,question_schema
from tools.research.session_handoff import main_feedback_projection
from tools.state_io import digest

ROOT=Path(__file__).resolve().parents[2]


class AnswerDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=resolve(ROOT/'configs/research/study_p3_passive_progressive_stiffness_autonomous_v1_2.json')

    def test_delivery_retains_evidence_navigation_without_experiment_or_review_tools(self):
        names=('research_plan','evidence_read','research_recall','experience_retrieve',
            'retrieve_context','research_route','research_analysis','research_investigate','research_rl')
        tools={name:object() for name in names}
        agent=SimpleNamespace(tool_registry=SimpleNamespace(registry=dict(tools)))
        answer_delivery_tools(agent)
        self.assertEqual(set(agent.tool_registry.registry),
            {'evidence_read','research_recall','experience_retrieve','retrieve_context'})
        self.assertTrue(all(agent.tool_registry.registry[k] is tools[k] for k in agent.tool_registry.registry))

    def test_advertised_complete_profile_and_exploration_have_distinct_valid_scopes(self):
        schema=question_schema(self.spec)
        profile=schema['$defs']['PassiveExecutionProfile']
        validator=Draft202012Validator(dict(profile,**{'$defs':schema['$defs']}))
        complete=complete_execution_profile(self.spec)
        self.assertTrue(validator.is_valid(complete))
        self.assertEqual(complete,dict(purpose='final_acceptance',fidelity='final_evaluation'))
        self.assertFalse(validator.is_valid(dict(complete,sample_period_s=.01)))
        self.assertTrue(validator.is_valid(dict(purpose='exploration',fidelity='final_evaluation',sample_period_s=.01)))

    def test_coverage_guidance_survives_handoff_without_upgrading_or_mutating_result(self):
        ref=dict(artifact_id='a'*64,media_type='application/json')
        feedback=dict(artifact_id='b'*64,media_type='application/json')
        raw=dict(status='computed',structure_research=dict(records=[dict(
            observation=dict(qualification_diagnosis=dict(reason='COMPLETE_QUALIFICATION_GRID_REQUIRED')),
            mechanics=dict(dynamic_execution=dict(execution_profile=dict(purpose='exploration'))))]))
        before=deepcopy(raw)
        host=Mock()
        host.store.artifact.side_effect=lambda r:raw if r==ref else dict(result=dict(content=[dict(
            text=json.dumps(dict(scientific_result_reference=ref)))]))
        s=dict(spec=self.spec,analysis_results=[ref])
        delivery=dict(items=[dict(tool='research_analysis',status='success',feedback_reference=feedback,
            result=dict(status='computed'),facts='fixture')])
        with patch('tools.research.reporter.state',return_value=s),\
                patch('tools.research.session_handoff.state',return_value=s),\
                patch('tools.research.object_choices.main_projection',side_effect=lambda h,v:v):
            guidance=qualification_feedback(host,raw)
            projected=main_feedback_projection(host,delivery)
        self.assertTrue(guidance['computation_completed'])
        self.assertFalse(guidance['qualified_certificate'])
        self.assertEqual(projected['items'][0]['execution_guidance'],guidance)
        self.assertNotIn('result',projected['items'][0])
        self.assertEqual(raw,before)
        self.assertIn('result',delivery['items'][0])
        self.assertIsNone(qualification_feedback(host,dict(status='computed')))

    def test_registered_protocol_source_is_the_exact_frozen_source(self):
        source=json.loads((ROOT/'configs/research/p3_original_protocol_source_v1.json').read_text(encoding='utf-8'))
        self.assertEqual(digest(source),'7df0162f9b8d9e8213fb2ef6dbd8bb20628bcd4a411e3788c0532b8402b0e340')
        config=json.loads((ROOT/'configs/research/study_p3_passive_progressive_stiffness_autonomous_v1_2.json').read_text(encoding='utf-8'))
        self.assertIn('configs/research/p3_original_protocol_source_v1.json',config['supplied_evidence'])


if __name__=='__main__':unittest.main()
