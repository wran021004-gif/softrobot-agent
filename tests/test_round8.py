"""Focused round8 contracts using saved evaluations; no live API or simulation."""
import json
import os
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from tools.spec_tools import ROOT
from tools.state_io import read, atomic_json
from tools.workbench import Workbench, owner
from tools.design_continuation import start_round
from tools.deepseek_adapter import run_model, payload_for, encoded_size
from tools.design_evidence import read_slice
from schemas.workbench import EvidenceArguments


class Round8Tests(unittest.TestCase):
    def setUp(self):
        self.folder = ROOT / 'runs/round8_tests' / uuid.uuid4().hex
        self.folder.mkdir(parents=True)
        self.ledger_patch = patch('tools.design_continuation.ROUND_LEDGER', self.folder / 'budget.json')
        self.ledger_patch.start()
        self.addCleanup(self.ledger_patch.stop)

    def book(self):
        book = Workbench(self.folder / 'book')
        start_round(book, ROOT / 'runs/round7_ready', ROOT / 'configs/deepseek.yaml')
        def worker(root, folder, timeout):
            from tools.workbench_actions import execute
            job = read(folder / 'job.json')
            self.assertNotEqual(job['tool'], 'evaluate_candidate', 'Test must never run a simulation')
            result = execute(job['tool'], job['arguments'], root, folder, read(root / 'state.json'))
            atomic_json(folder / 'result.json', result.model_dump(mode='json'))
        book.launcher = worker
        return book

    def test_evidence_overview_complete_entries_and_read_memory(self):
        b = self.book()
        basic = read_slice(b.root, b.state, EvidenceArguments(evidence_id='eval:c001', pointer='/data').model_dump())
        self.assertIsNone(basic['next_offset'])
        self.assertIsNone(basic['next_byte_offset'])
        self.assertIn('compare_model_sim', basic['content']['diagnostic_entries'])
        args = EvidenceArguments(evidence_id='catalog:c001', pointer='/entries', limit=50, max_bytes=1000).model_dump()
        page = read_slice(b.root, b.state, args)
        self.assertIsInstance(page['content'], list)
        self.assertGreater(len(page['content']), 0)
        self.assertLess(page['next_offset'], 50)
        args['offset'] = page['next_offset']
        next_page = read_slice(b.root, b.state, args)
        self.assertNotEqual(page['content'][0], next_page['content'][0])
        self.assertTrue(any(len(r['sequences']) > 1 for r in b.state['working_memory']['reads'].values()))

    def test_thinking_roundtrips_memory_and_size_compaction(self):
        b = self.book()
        captured = []
        def model(config, payload, key):
            captured.append(payload)
            i = len(captured)
            name = 'read_evidence' if i <= 2 else 'create_candidate' if i == 3 else 'stop_design'
            args = ({'evidence_id': 'eval:c001', 'pointer': '/data/diagnostics/compare_model_sim'} if i <= 2 else
                    {'parent_id': 'c001', 'changes': {'total_length_m': .29}} if i == 3 else {})
            args.update(reason='protocol fixture, not a live design', evidence=['eval:c001'],
                        working_memory=dict(findings=['c001 actual error is 0.1218785 m'], unresolved=['cause is unproven'],
                                            next_action='test candidate change' if i < 3 else 'test stop', evidence=['eval:c001']))
            return dict(model='fixture-deepseek', usage={'prompt_tokens': 10, 'completion_tokens': 20}, choices=[dict(finish_reason='tool_calls',
                message=dict(role='assistant', content=None, reasoning_content='reasoning-protocol-fixture-' + str(i),
                             tool_calls=[dict(id='call_fixture_' + str(i), type='function', function=dict(name=name, arguments=json.dumps(args)))]))])
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'fixture-only'}), owner(b.root):
            for i in range(3):
                b.load()
                run_model(b, steps=1, transport=model)
            self.assertNotIn('tool_choice', captured[0])
            self.assertNotIn('temperature', captured[0])
            self.assertEqual(captured[0]['thinking'], {'type': 'enabled'})
            self.assertEqual(len([m for m in captured[2]['messages'] if m['role'] == 'assistant']), 2)
            self.assertIn('reasoning-protocol-fixture-1', json.dumps(captured[2]))
            self.assertEqual(b.state['model_calls'][-2]['feedback']['read_notice']['code'], 'REPEATED_READ')
            self.assertEqual(len(b.state['candidates']), 3)
            b.load()
            full_size = encoded_size(payload_for(b))
            # Force the real size-triggered path, without changing the byte cap.
            b.state['model_calls'][-1]['message']['reasoning_content'] += 'x' * 60000
            run_model(b, transport=model)
            self.assertEqual(b.state['context_compactions'][-1]['reason'], 'input_size')
            self.assertFalse(any(m['role'] == 'assistant' for m in captured[-1]['messages']))
            self.assertIn('c001 actual error', json.dumps(captured[-1]))
            self.assertEqual(b.remaining()['model_calls'], 8)
            self.assertEqual(b.remaining()['simulations'], 1)

    def test_new_grant_and_no_reimport_reset(self):
        b = self.book()
        b.load()
        old = read(ROOT / 'runs/round7_ready/state.json')
        self.assertEqual(len(b.state['model_calls']), 18)
        self.assertEqual(b.state['attempts'], old['attempts'])
        self.assertEqual(b.remaining()['model_calls'], 12)
        self.assertEqual(b.remaining()['simulations'], 1)
        self.assertEqual(b.remaining()['matlab_calls'], 3)
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'fixture-only'}):
            def failure(*args):
                raise RuntimeError('fixture network failure')
            run_model(b, transport=failure)
        b.load()
        self.assertEqual(b.remaining()['model_calls'], 11)
        with self.assertRaisesRegex(ValueError, 'ROUND_BUDGET_ALREADY_ASSIGNED'):
            start_round(Workbench(self.folder / 'duplicate'), ROOT / 'runs/round7_ready', ROOT / 'configs/deepseek.yaml')

    def test_native_saved_state_geometry_and_render(self):
        from tools.native_replay import NativeReplay, resolve_run
        source = resolve_run(ROOT / 'runs/round7_ready', 'c001')
        import mujoco
        with patch.object(mujoco, 'mj_step', side_effect=AssertionError('No integration')), patch.object(mujoco, 'mj_forward', side_effect=AssertionError('No forward solve')):
            player = NativeReplay(source)
            player.seek(player.times[-1])
            self.assertEqual(player.data.qpos.tolist(), player.samples[-1]['state'])
            self.assertAlmostEqual(player.data.time, player.times[-1])
            player.key(32)
            self.assertTrue(player.paused)
            player.key(263)
            self.assertEqual(player.cursor, player.times[-2])
            artifacts = player.export(self.folder / 'native', fps=5, width=320, height=240)
            self.assertTrue(all(p.is_file() for p in artifacts))
            manifest = read(artifacts[-1])
            self.assertFalse(manifest['rescoring'])
            self.assertEqual(manifest['backend_solves'], 0)


if __name__ == '__main__':
    unittest.main()
