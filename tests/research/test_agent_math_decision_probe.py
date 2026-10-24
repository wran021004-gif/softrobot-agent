"""Three offline checks. Mock Provider decisions/usage are fixtures, not evidence."""
import asyncio
import gc
import json
import os
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from tests.research import agent_math_decision_probe as probe
from tools.state_io import read


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.out = probe.ROOT / 'runs' / ('probe-fixture-' + uuid4().hex)
        self.summary = self.out.parent / (self.out.name + '-summary.json')
        self.summary_patch = patch.object(probe, 'SUMMARY', self.summary)
        self.summary_patch.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.summary_patch.stop()
        gc.collect()
        assert self.out.resolve().parent == (probe.ROOT / 'runs').resolve()
        if self.out.exists():
            shutil.rmtree(self.out)
        self.summary.unlink(missing_ok=True)

    def test_pairs_have_only_evidence_difference_and_no_future_or_rubric(self):
        frozen = probe.freeze(self.out)
        data = frozen['cases']
        for case in data['cases']:
            for turn in (1, 2):
                b = probe.wire(frozen['provider'], data, case, 'baseline', turn)
                e = probe.wire(frozen['provider'], data, case, 'evidence', turn)
                bp = json.loads(b['messages'][-1]['content'])
                ep = json.loads(e['messages'][-1]['content'])
                self.assertEqual(ep.pop('diagnostic_evidence'), data['cases'][case]['evidence'])
                self.assertEqual(bp.pop('diagnostic_evidence'), [])
                self.assertEqual(bp, ep)
                b['messages'][-1] = e['messages'][-1] = {'content': 'compared above'}
                self.assertEqual(b, e)
                text = json.dumps(probe.wire(frozen['provider'], data, case, 'evidence', turn))
                self.assertNotIn('rubric_offline_only', text)
                self.assertNotIn('sources_offline_only', text)
                self.assertNotIn('.md', text)
                if turn == 1:
                    self.assertNotIn('new_observations', bp)
                    for future in data['cases'][case]['round2']:
                        self.assertNotIn('"' + future['id'] + '"', text)
                    self.assertNotIn('-0.050734', text)
                    self.assertNotIn('0.022752409', text)
        actual = read(probe.ROOT / 'evidence/mujoco_reoptimized_structure/summary.json')['results']
        rows = list(actual.values())
        st = data['cases']['structure']
        self.assertEqual(st['common'][0]['values']['J'], [r['fixed']['signed_maximum_excess'] for r in rows])
        self.assertEqual(st['round2'][0]['raw_values']['J'], [r['warm']['best']['signed_maximum_excess'] for r in rows])

    def test_eight_single_decisions_exact_usage_and_isolated_history_no_dispatch(self):
        probe.freeze(self.out)
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            plan = dict(action='diagnose', hypothesis='Fixture competing mechanisms A and B',
                expected_observation='Fixture metric', weakening_observation='Fixture falsifier',
                fixed_conditions='Fixture fixed inputs', stopping_condition='Fixture budget',
                interpretation='Fixture conditional decision', decision=dict(hypothesis_id=f'fixture-{len(requests)}',
                    research_intent='DIAGNOSE', selected_method='native_dynamics_v1', requested_budget=1))
            return httpx.Response(200, json=dict(choices=[dict(finish_reason='tool_calls', message=dict(
                role='assistant', content=None, tool_calls=[dict(id=f'call-{len(requests)}', type='function',
                function=dict(name='research_plan', arguments=json.dumps(plan)))]))],
                usage=dict(prompt_tokens=10, completion_tokens=5, total_tokens=15,
                           prompt_cache_hit_tokens=2, prompt_cache_miss_tokens=8,
                           completion_tokens_details=dict(reasoning_tokens=3))))

        with patch.dict(os.environ, DEEPSEEK_API_KEY='offline-fixture'), \
             patch('tools.research.core.dispatch', side_effect=AssertionError('NO_SCIENCE')) as dispatch:
            result = asyncio.run(probe.live(self.out, test_transport=httpx.MockTransport(respond)))
        self.assertEqual(len(requests), 8)
        self.assertEqual(result['usage']['total_tokens'], 120)
        self.assertEqual(result['usage']['reasoning_tokens'], 24)
        self.assertEqual(result['provider_ledger']['used']['model_calls'], 8)
        self.assertEqual(result['provider_ledger']['used']['backend_solves'], 0)
        self.assertEqual(result['provider_ledger']['used']['worker_calls'], 0)
        self.assertTrue(all(r['schema_check'] == 'passed' for r in result['results']))
        dispatch.assert_not_called()
        for second, own_first, other_first in ((2, 1, 2), (3, 2, 1), (6, 5, 6), (7, 6, 5)):
            messages = json.dumps(requests[second]['messages'])
            self.assertIn(f'fixture-{own_first}', messages)
            self.assertNotIn(f'fixture-{other_first}', messages)
        with self.assertRaises(ValueError):
            probe.parse(dict(content='unstructured fixture without a tool call'))
        self.assertIsNone(result['money'])

    def test_unknown_outcome_stops_and_existing_attempt_cannot_resend(self):
        probe.freeze(self.out)
        attempts = []

        def fail(request):
            attempts.append(request)
            raise httpx.ReadError('offline fixture unknown outcome')

        with patch.dict(os.environ, DEEPSEEK_API_KEY='offline-fixture'):
            with self.assertRaises(httpx.ReadError):
                asyncio.run(probe.live(self.out, test_transport=httpx.MockTransport(fail)))
            with self.assertRaisesRegex(ValueError, 'NO_AUTOMATIC_RESEND'):
                asyncio.run(probe.live(self.out, test_transport=httpx.MockTransport(fail)))
        result = read(self.summary)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(result['actual_requests'], 1)
        self.assertEqual(result['confirmed_responses'], 0)
        self.assertEqual(result['provider_ledger']['occupied']['provider_request'], 1)
        self.assertIsNone(result['usage']['total_tokens'])


if __name__ == '__main__':
    unittest.main()
