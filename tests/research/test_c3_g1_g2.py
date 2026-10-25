"""Offline protocol checks; no Provider or scientific execution."""
import json
import unittest

from tests.research import agent_math_decision_probe as probe
from tests.research.c3_f1_f2_validation import continuity_instructions
from tools.state_io import read


class G1ProtocolTests(unittest.TestCase):
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
