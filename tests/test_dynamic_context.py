"""One focused >40 KB evidence regression; no backend, network or campaign writes."""
import copy
import json
import time
import unittest
import uuid
from unittest.mock import patch

from schemas.dynamic_workbench import Read
from tools.dynamic_campaign import DynamicCampaign, LEDGER
from tools.dynamic_context import encoded_size, evidence_page, resolve_pointer
from tools.spec_tools import ROOT
from tools.state_io import atomic_json, read


class DynamicContextRegression(unittest.TestCase):
    def test_nested_feedback_pagination_and_request_boundary(self):
        # Workspace fixture retained for inspection (Windows temp ACLs differ).
        root = ROOT / 'runs/round9_context_tests' / uuid.uuid4().hex
        (root / 'inputs').mkdir(parents=True)
        original = ROOT / 'runs/round9_reach'
        (root / 'inputs/system_prompt.md').write_bytes((original / 'inputs/system_prompt.md').read_bytes())
        book = DynamicCampaign.__new__(DynamicCampaign)
        book.root = root
        book.state = read(original / 'state.json')
        book.ledger = read(LEDGER)
        book.tick = time.monotonic()
        queries = [dict(entity_name=f'tendon_{i}' if i % 2 else f'joint_{i}_y',
                        t_start_s=.002 * i, t_end_s=1.5 + .002 * i,
                        values={'force_n': -0.123456789012345 * (i+1)}) for i in range(12)]
        samples = [-0.123456789012345 * (i+1) for i in range(5000)]
        queries[7]['nested'] = {'samples': samples}
        document = {'queries': queries, 'a/b~c': {'text': '绳索"\n' * 4000}}
        ref = 'diagnostics/large.json'
        atomic_json(root / ref, document)
        book.register(root / ref)
        old_result = dict(tool='read_evidence', status='completed', data={'content': document, 'cite_as': ref},
                          other_nested={'also_large': samples})
        self.assertGreater(encoded_size(old_result), 40000)
        attempt_ref = 'attempts/context_fixture/result.json'
        atomic_json(root / attempt_ref, old_result)
        book.register(root / attempt_ref)
        book.state['attempts'] = [dict(tool='read_evidence', arguments={'evidence_ref': ref}, result_ref=attempt_ref)]
        state_before = copy.deepcopy(book.state)
        payload, metrics = book.build_model_request()
        self.assertEqual(book.state, state_before)  # Legacy migration is read-only.
        legacy_page = json.loads(payload['messages'][1]['content'])['latest_tool_result']['data']
        self.assertEqual(legacy_page['next_read']['pointer'], '/queries')
        self.assertLessEqual(encoded_size(legacy_page), 4000)
        self.assertLessEqual(encoded_size(payload), 60000)

        # Other arbitrarily nested tool fields are bounded as well.
        book.state['attempts'][-1]['tool'] = 'compare_candidates'
        old_result['tool'] = 'compare_candidates'
        atomic_json(root / attempt_ref, old_result)
        self.assertLessEqual(encoded_size(book.latest_preview()), 4600)
        book.state['attempts'][-1]['tool'] = 'read_evidence'

        def page(**args):
            parsed = Read.model_validate({'evidence_ref': ref, **args}).model_dump()
            result = book.dispatch('read_evidence', parsed, [ref], 'fixture read')
            self.assertLessEqual(encoded_size(result), parsed['max_bytes'])
            return result

        first = page(pointer='/queries', offset=5, limit=5)
        self.assertEqual(first['content'], queries[5:7])
        self.assertEqual(first['returned_range'], {'start': 5, 'end_exclusive': 7})
        self.assertEqual(first['next_offset'], 7)  # Actual count, not requested limit.
        directory = page(**first['next_read'])
        self.assertEqual(directory['mode'], 'directory')
        self.assertEqual(directory['returned_count'], 0)
        self.assertEqual(directory['next_offset'], 7)
        self.assertEqual(directory['next_read']['pointer'], '/queries/7')
        self.assertEqual(directory['resume_container']['offset'], 8)
        self.assertIn('/queries/7/nested', [d['pointer'] for d in directory['directory']])
        record = page(**directory['next_read'])
        self.assertEqual(record['content']['entity_name'], queries[7]['entity_name'])
        self.assertEqual(record['content']['values'], queries[7]['values'])
        nested = page(**record['next_read'])
        nested = page(**nested['next_read'])
        sample_directory = page(**nested['next_read'])
        self.assertEqual(sample_directory['pointer'], '/queries/7/nested/samples')
        self.assertTrue(sample_directory['has_more'])
        received = sample_directory['content'][:]
        current = sample_directory
        while current['has_more']:
            current = page(**current['next_read'])
            self.assertEqual(current['offset'], len(received))
            received.extend(current['content'])
        self.assertEqual(received, samples)

        # A >40 KB legacy result is replaced by exactly the requested valid page
        # in the next model request, including original names/times/numbers.
        atomic_json(root / attempt_ref, dict(tool='read_evidence', status='completed', data=first))
        payload, metrics = book.build_model_request()
        self.assertEqual(json.loads(payload['messages'][1]['content'])['latest_tool_result']['data'], first)
        self.assertEqual(encoded_size(payload), metrics['total_bytes'])
        self.assertLessEqual(metrics['total_bytes'], 60000)
        r = first['content'][1]
        claim = dict(evidence_ref=ref, record_type='queries', record_index=first['offset']+1,
                     entity_name=r['entity_name'], t_start_s=r['t_start_s'], t_end_s=r['t_end_s'],
                     field='force_n', value=r['values']['force_n'], statement='Exact saved fixture observation')
        verified = book.dispatch('record_verified_diagnosis', claim, [ref], 'fixture verification')
        self.assertEqual(verified['verification'], 'NUMERIC_ENTITY_TIME_MATCH')
        self.assertEqual(read(root / ref), document)
        self.assertEqual(resolve_pointer(document, '/a~1b~0c'), document['a/b~c'])
        text = page(pointer='/a~1b~0c/text', max_bytes=1000)
        self.assertTrue(text['has_more'])
        self.assertEqual(text['content'], document['a/b~c']['text'][:text['next_offset']])
        self.assertEqual(page(pointer='/queries', offset=12)['content'], [])
        self.assertEqual(page(pointer='/queries/6/values/force_n')['content'], queries[6]['values']['force_n'])
        self.assertEqual(Read(evidence_ref=ref).max_bytes, 4000)
        with self.assertRaises(ValueError):Read(evidence_ref=ref, max_bytes=8001)

        # Oversized necessary memory must pause before any model reservation.
        # Historical Round 9 may now be closed. Test context limits independently
        # of that external experiment's terminal flag and correction receipts.
        book.state.pop('experiment', None)
        book.state.pop('tool_call_corrections', None)
        book.state['working_memory'] = {'findings': ['x' * 70000], 'next_action': 'Preserve the current page'}
        charged_before = book.ledger['used']['model_calls']
        calls_before = len(book.state['model_calls'])
        with patch('tools.dynamic_campaign.LEDGER', root / 'ledger.json'), \
             patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'fixture-not-a-real-key'}), \
             patch.object(book, 'reserve', side_effect=AssertionError('Must not reserve before size check')), \
             patch.object(book, 'render'), \
             patch('tools.deepseek_adapter.request_completion', side_effect=AssertionError('No API')):
            book.run_model(steps=1)
        self.assertEqual(book.state['status'], 'PAUSED')
        self.assertEqual(book.ledger['used']['model_calls'], charged_before)
        self.assertEqual(len(book.state['model_calls']), calls_before)
        self.assertEqual(read(root / 'state.json')['status'], 'PAUSED')
        pause = read(root / 'context_pause.json')
        self.assertGreater(pause['total_bytes'], 60000)
        self.assertEqual(pause['compactions'], ['history_and_decisions', 'candidate_details'])
        self.assertIn('working memory', pause['reason'])
        print(f'Nested fixture: {encoded_size(old_result)} bytes; next request: {metrics["total_bytes"]} bytes; '
              f'original samples verified: {len(samples)}; API/solver calls: 0/0; fixture: {root}')


if __name__ == '__main__':
    unittest.main()
