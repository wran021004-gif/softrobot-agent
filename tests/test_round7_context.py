"""Four focused checks; saved round6 evidence, zero live model/numerical calls."""
import copy
import json
import os
import unittest
import uuid
from unittest.mock import patch
from tools.workbench import Workbench, owner, source_hashes, runtime
from tools.design_continuation import continue_design, compatible
from tools.design_evidence import read_slice
from tools.design_session import preconditions
from tools.deepseek_adapter import payload_for, encoded_size, run_model
from tools.state_io import read, atomic_json
from tools.spec_tools import ROOT
from schemas.workbench import Decision, EvidenceArguments, DeepSeekConfig


class BoundedContextTests(unittest.TestCase):
    def book(self):
        book = Workbench(ROOT / 'runs/round7_tests' / uuid.uuid4().hex)
        continue_design(book, ROOT / 'runs/round6_ready', ROOT / 'configs/deepseek.yaml')
        return book

    def test_bounded_reads_and_candidate_citations(self):
        b = self.book()
        ev = b.state['evidence']['eval:c001']
        raw = next(k for k, v in b.state['evidence'].items() if v.get('evaluation_id') == 'eval:c001' and k.endswith('mujoco_result.json'))
        args = EvidenceArguments(evidence_id=raw, pointer='/metrics', max_bytes=256).model_dump()
        part = read_slice(b.root, b.state, args)
        self.assertEqual(part['cite_as'], 'eval:c001')
        self.assertLessEqual(part['content_bytes'], 256)
        self.assertIsNotNone(part['next_byte_offset'])
        reconstructed = part['content']
        while part['next_byte_offset'] is not None:
            args['byte_offset'] = part['next_byte_offset']
            part = read_slice(b.root, b.state, args)
            reconstructed += part['content']
        self.assertIsInstance(json.loads(reconstructed), dict)
        target = dict(parent_id='c001', changes={'total_length_m': .29})
        for ref in ('eval:c001', raw, ev['path']):
            d = Decision(action='continue', tool='create_candidate', arguments=target, evidence=[ref], reason='test only')
            preconditions(b, d, dict(target))
        with self.assertRaisesRegex(ValueError, 'FEEDBACK_REQUIRED'):
            preconditions(b, d.model_copy(update={'evidence': ['eval:c000']}), dict(target))
        catalog = read_slice(b.root, b.state, EvidenceArguments(evidence_id='catalog:c001', pointer='/entries', limit=2).model_dump())
        self.assertEqual(catalog['next_offset'], 2)
        self.assertTrue(all(e['candidate_id'] == 'c001' for e in catalog['content']))

    def test_thinking_pause_replay_and_compaction(self):
        b = self.book()
        b.state['request']['design_session']['thinking'] = 'enabled'
        atomic_json(b.root / 'request.json', b.state['request'])
        b.register(b.root / 'request.json', 'request')
        b.save()
        captured = []
        def worker(root, folder, timeout):
            from tools.workbench_actions import execute
            job = read(folder / 'job.json')
            result = execute(job['tool'], job['arguments'], root, folder, read(root / 'state.json'))
            atomic_json(folder / 'result.json', result.model_dump(mode='json'))
        b.launcher = worker
        def model(config, payload, key):
            captured.append(payload)
            i = len(captured)
            return dict(choices=[dict(finish_reason='tool_calls', message=dict(role='assistant', content=None,
                reasoning_content='protocol fixture 思考字段 ' + str(i),
                tool_calls=[dict(id='fixture_' + str(i), type='function', function=dict(name='read_evidence',
                    arguments=json.dumps(dict(evidence_id='eval:c001', pointer='/data/actual_tip_m', reason='protocol fixture', evidence=['eval:c001']))))]))])
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'fixture-key'}), owner(b.root):
            run_model(b, steps=1, transport=model)
            b.load()
            saved = b.state['model_calls'][-1]['message']
            run_model(b, steps=1, transport=model)
            self.assertIn(saved, captured[1]['messages'])
            self.assertNotIn('temperature', captured[1])
            self.assertTrue(any(m.get('tool_call_id') == 'fixture_1' for m in captured[1]['messages']))
            compacted = payload_for(b)
            self.assertFalse(any(m['role'] == 'assistant' for m in compacted['messages']))
            self.assertLess(encoded_size(compacted), 25000)
            self.assertIn('protocol fixture', read(b.root / b.state['model_calls'][-1]['folder'] / 'response.json')['message']['reasoning_content'])
        self.assertEqual(DeepSeekConfig.model_validate(b.state['request']['design_session']).thinking, 'enabled')

    def test_continuation_preserves_costs_cache_and_compatibility(self):
        b = self.book()
        self.assertEqual(b.remaining()['simulations'], 1)
        self.assertEqual(b.remaining()['candidates'], 1)
        self.assertEqual(b.remaining()['model_calls'], 11)
        old = read(ROOT / 'runs/round6_ready/state.json')
        self.assertEqual(b.state['attempts'], old['attempts'])
        self.assertEqual(read(b.root / b.state['request']['continuation']['archive'] / 'state.json'), old)
        b.launcher = lambda *args: self.fail('Inherited evaluation was recomputed')
        b.submit(Decision(action='continue', tool='evaluate_candidate', arguments={'candidate_id': 'c001'}, reason='cache test', evidence=['eval:c001']))
        self.assertEqual(b.state['decisions'][-1]['status'], 'reused')
        self.assertEqual(b.remaining()['simulations'], 1)
        changed = source_hashes()
        changed['metrics/reach.py'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'INCOMPATIBLE_COMPUTATION'):
            compatible(old['request'], changed, runtime())

    def test_input_growth_and_dashboard_states(self):
        b = self.book()
        from tools.workbench_view import render
        for count in (0, 10, 30):
            b.state['model_calls'] += copy.deepcopy(b.state['model_calls'][:1]) * count
            self.assertLess(encoded_size(payload_for(b, fresh=True)), 25000)
        # Original seven requests and inherited trajectory truth remain visible.
        b.state['model_calls'] = b.state['model_calls'][:7]
        page = render(b.root, b.state)
        for label in ('计算完成但任务未达标', '轨迹已保存，尚未生成动画', '完整回复', '拒绝原因', '历史工具反馈'):
            self.assertIn(label, page)
        with patch.dict(os.environ, {}, clear=True):
            run_model(b, transport=lambda *a: self.fail('No key'))
        self.assertEqual(b.state['status'], 'WAITING_FOR_KEY')
        self.assertEqual(b.remaining()['model_calls'], 11)


if __name__ == '__main__':
    unittest.main()
