"""Offline protocol checks; no Provider or scientific execution."""
import json
import asyncio
import os
import unittest
from unittest.mock import patch
import httpx
from jsonschema import Draft202012Validator

from tests.research import agent_math_decision_probe as probe
from tests.research.c3_f1_f2_validation import continuity_instructions
from tools.state_io import read


class G1ProtocolTests(unittest.TestCase):
    def test_normal_exploration_handoff_keeps_original_query_and_study_read(self):
        from tests.research.test_request_boundary_handoff import RequestBoundaryHandoffTests
        from tools.research.agent import converse
        from tools.research.state import state, update, save, protected
        from tools.research.core import read_evidence
        from tools.research.research_context import read_coverage
        from tests.research.test_c3_f1_f2 import archive, ROOT
        historical = archive('b'); self.addCleanup(historical.archive.close)
        _, previous = historical.host()
        source = previous['results'][-1]; original = historical.artifact(source)
        h = RequestBoundaryHandoffTests().provision()
        excerpt = dict(kind='historical_scoped_evidence', owning_study=original['owning_study'],
            original_reference=source, candidate=original['candidate'], acceptance=original['acceptance']['components'],
            scope='Historical B execution only; no candidate or science executed in this independent test')
        reference = save(h, excerpt, 'explicit_offline_historical_excerpt')
        query = dict(reference=reference, view='full', pointer='')
        self.assertEqual(query, read(ROOT / 'evidence/c3_f1_f2/continuity_summary.json')['tool_queries'][0]['input'])
        update(h, scoped_context=[reference])
        self.assertEqual(read_evidence(h, query, record_read=False), excerpt)
        sent = []

        def respond(request):
            wire = json.loads(request.content); sent.append(wire)
            message = dict(role='assistant', content='Offline fixture consumes completed Study read.')
            if len(sent) == 1:
                message['tool_calls'] = [dict(id='fixture-original-read', type='function',
                    function=dict(name='evidence_read', arguments=json.dumps(query)))]
            return httpx.Response(200, json=dict(id='offline', object='chat.completion', created=1,
                model=wire['model'], usage=dict(prompt_tokens=10, completion_tokens=4, total_tokens=14),
                choices=[dict(index=0, finish_reason='tool_calls' if len(sent)==1 else 'stop', message=message)]))

        with patch('tools.research.provider.load_credential'), patch.dict(os.environ, {'DEEPSEEK_API_KEY':'offline'}), \
                patch('tools.research.core.guard'), patch('tools.research.agent.guard'), \
                patch('httpx.AsyncHTTPTransport', return_value=httpx.MockTransport(respond)):
            asyncio.run(converse(h, session_handoff=True, handoff_before_next_request=True,
                                 pause_after_completed_invocations=1))
        self.assertEqual(len(sent), 2)
        self.assertFalse(protected(h))
        second = json.loads(sent[1]['messages'][-1]['content'].split('\n', 1)[1])['research']
        self.assertFalse(second['budget']['closeout']['next_request_will_protect'])
        schema = next(t['function']['parameters'] for t in sent[1]['tools']
                      if t['function']['name']=='evidence_read')
        Draft202012Validator(schema).validate(query)
        self.assertEqual(second['evidence_working_set']['read_state']['completed_reads'], 1)
        self.assertEqual(second['evidence_working_set']['read_state']['recent'][0]['query']['reference'], reference)
        item = second['pending_feedback_delivery']['items'][0]
        self.assertEqual(item['query'], query)
        self.assertEqual(json.loads(item['result']['content'][0]['text']), excerpt)
        self.assertTrue(read_coverage(h)[0]['complete_data'])
        self.assertIn('ONCE to this entire Study', continuity_instructions(query))

    def test_l1_comparability_time_scope_and_rules_stay_out_of_l0(self):
        from tests.research.test_c3_f1_f2 import archive
        from tools.research.evidence_views import diagnostic_relations, result_card
        from tools.research.research_context import agent_decision_brief
        from tools.research.task_constraints import SCIENTIFIC_INTERPRETATION, mathematical_method_view
        a = archive('b'); self.addCleanup(a.archive.close)
        h, s = a.host()
        reference = s['results'][-1]
        relations = diagnostic_relations(h, reference)
        for row in relations['relations']:
            if 'prediction_error_comparability' not in row: continue
            comparable = all(row['alignment'].values())
            self.assertEqual(row['prediction_error_comparability']['status'], 'comparable' if comparable
                             else 'not_comparable_as_model_prediction_error')
            self.assertEqual(row['prediction_error_comparability']['reasons'], row['missing_conditions'])
            if not comparable: self.assertIsNone(row['sample_differences'])
            self.assertEqual(row['temporal_support']['kind'], 'discrete_samples')
        diagnosis = relations['task_diagnosis']
        self.assertEqual(diagnosis['temporal_support']['times_s'],
                         [r['time_s'] for r in diagnosis['critical_samples']])
        self.assertEqual(result_card(h, reference).deterministic_summary['scientific_interpretation'],
                         SCIENTIFIC_INTERPRETATION)
        candidate = h.store.artifact(reference)['candidate']
        self.assertEqual(mathematical_method_view(h, candidate)['scientific_interpretation'],
                         SCIENTIFIC_INTERPRETATION)
        l0 = json.dumps(agent_decision_brief(h))
        self.assertNotIn('scientific_interpretation_v1', l0)

    def test_startup_obligation_is_study_scoped_and_allows_scientific_recheck(self):
        query = dict(reference=dict(artifact_id='fixture'), view='full', pointer='')
        text = continuity_instructions(query)
        self.assertIn('ONCE to this entire Study', text)
        self.assertIn('read_state and pending_feedback_delivery', text)
        self.assertIn('scientifically motivated recheck remains legal', text)
        self.assertIn(json.dumps(query), text)
        self.assertNotIn('First call', text)

    def test_turn_two_keeps_prior_plan_and_requires_new_submission_in_both_arms(self):
        data = read(probe.CASES)
        provider = read(probe.ROOT / 'configs/research/runtime_c3_ab.json')['provider']
        history = [dict(role='assistant', tool_calls=[dict(id='fixture-prior-plan',
            type='function', function=dict(name='research_plan', arguments='{}'))])]
        for arm in probe.ARMS:
            wire = probe.wire(provider, data, 'reach_hold', arm, 2, history)
            packet = json.loads(wire['messages'][-1]['content'])
            self.assertEqual(wire['messages'][1], history[0])
            self.assertEqual(packet['evaluation_turn']['previous_plan_tool_ids'], ['fixture-prior-plan'])
            self.assertIn('NEW research_plan', packet['evaluation_turn']['submission'])
            self.assertTrue(packet['new_observations'])
            self.assertEqual(wire['tool_choice'], 'auto')


if __name__ == '__main__':
    unittest.main()
