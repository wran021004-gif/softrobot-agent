"""Focused contracts, injected model transport and evaluator: no live API or simulation."""
import json
import os
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch
import yaml
from schemas.workbench import WorkbenchResult
from tools.spec_tools import ROOT, load_yaml
from tools.state_io import atomic_json, read
from tools.workbench import Workbench, owner
from tools.deepseek_adapter import run_model
from tools.design_actions import execute


KEY = 'test-key-not-a-secret'


def response(name, args, index):
    return dict(model='deepseek-flash', usage=dict(total_tokens=100, completion_tokens=20, prompt_tokens=80),
                choices=[dict(finish_reason='tool_calls', message=dict(role='assistant', content=KEY,
                    tool_calls=[dict(id=f'call_{index}', type='function', function=dict(name=name, arguments=json.dumps(args)))]))])


class DesignLoopTests(unittest.TestCase):
    def create_book(self, **limits):
        folder = ROOT / 'runs/round6_tests' / uuid.uuid4().hex
        folder.mkdir(parents=True)
        cfg = {**load_yaml(ROOT / 'configs/deepseek.yaml'), **limits}
        (folder / 'config.yaml').write_text(yaml.safe_dump(cfg), encoding='utf-8')
        def worker(root, attempt, timeout):
            job = read(attempt / 'job.json')
            state = read(root / 'state.json')
            if job['tool'] == 'evaluate_candidate':
                cid = job['arguments']['candidate_id']
                c = next(c for c in state['candidates'] if c['candidate_id'] == cid)
                result = WorkbenchResult(tool=job['tool'], status='completed', failure_code='TASK_FAILED',
                    data=dict(candidate_id=cid, design_hash=c['design_hash'], canonical_task_status='FAIL',
                              position_error_m=c['design']['total_length_m']/2, evidence_role='TEST_ONLY'))
            else:
                result = execute(job['tool'], job['arguments'], root, attempt, state)
            atomic_json(attempt / 'result.json', result.model_dump(mode='json'))
        book = Workbench(folder / 'book', launcher=worker)
        book.create(deepseek_config=folder / 'config.yaml')
        return book

    def test_model_feedback_candidate_isolation_rejections_cache_and_stop(self):
        book = self.create_book(candidates=2, simulations=2)
        phases = set()
        def model(config, payload, key):
            self.assertEqual(key, KEY)
            self.assertEqual(payload['thinking'], {'type': 'disabled'})
            self.assertEqual(payload['tool_choice'], 'required')
            context = json.loads(payload['messages'][-1]['content'].split('\n', 1)[1])
            self.assertEqual(context['task']['task']['target_m'], [0.25, 0., 0.15])
            c = context['candidates'][-1]
            cid = c['candidate_id']
            reason = 'unit protocol test; not a real model design result'
            args = dict(reason=reason, evidence=['request'])
            if cid == 'c001' and 'bad_check' not in phases:
                phases.add('bad_check')
                return response('evaluate_candidate', {**args, 'candidate_id': cid}, len(book.state['model_calls']))
            if 'check_candidate_ref' not in c:
                tool, params = 'check_candidate', dict(candidate_id=cid)
            elif c['evaluation']['status'] == 'NOT_RUN':
                tool, params = 'evaluate_candidate', dict(candidate_id=cid)
            elif cid == 'c000':
                # Read this response's evaluation to derive the test modification;
                # no precomputed candidate sequence and no live-model acceptance claim.
                error = c['evaluation']['data']['position_error_m']
                tool = 'create_candidate'
                params = dict(parent_id=cid, changes={'total_length_m': c['design']['total_length_m'] - error / 4})
                args['evidence'] = [c['evaluate_candidate_ref']]
            elif 'cache' not in phases:
                phases.add('cache')
                tool, params = 'evaluate_candidate', dict(candidate_id=cid)
            elif 'over_budget' not in phases:
                phases.add('over_budget')
                tool, params = 'create_candidate', dict(parent_id=cid, changes={'total_length_m': .33})
                args['evidence'] = [c['evaluate_candidate_ref']]
            elif 'compared' not in phases:
                phases.add('compared')
                tool, params = 'compare_candidates', dict(candidate_ids=['c000', 'c001'])
            else:
                tool, params = 'stop_design', {}
            return response(tool, {**args, **params}, len(book.state['model_calls']))
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': KEY}), owner(book.root):
            book.load()
            state = run_model(book, transport=model)
        self.assertEqual(state['status'], 'STOPPED')
        self.assertEqual(len(state['candidates']), 2)
        self.assertEqual(book.remaining()['simulations'], 0)
        self.assertEqual(book.remaining()['candidates'], 0)
        evaluations = [a for a in state['attempts'] if a['tool'] == 'evaluate_candidate']
        self.assertEqual(len(evaluations), 2)
        self.assertNotEqual(evaluations[0]['result']['data']['design_hash'], evaluations[1]['result']['data']['design_hash'])
        self.assertEqual(len(state['reuse']), 1)
        created = next(a for a in state['attempts'] if a['tool'] == 'create_candidate')
        self.assertEqual(created['result'], read(book.root / created['result_ref']))
        reasons = [d.get('failure_code', '') for d in state['decisions']]
        self.assertIn('PRECONDITION_FAILED', reasons)
        self.assertIn('BUDGET_EXHAUSTED', reasons)
        tool_messages = [m for row in state['model_calls'] for m in read(book.root / row['folder'] / 'request.json')['messages'] if m['role'] == 'tool']
        self.assertTrue(any('PRECONDITION_FAILED' in m['content'] for m in tool_messages))
        self.assertFalse(read(book.root / 'design_report.json')['live_model_feedback_loop_verified'])
        self.assertFalse(any(KEY in p.read_text(encoding='utf-8') for p in book.root.rglob('*.json')))

    def test_missing_key_and_explicit_api_retry_keep_budget(self):
        book = self.create_book()
        with patch.dict(os.environ, {}, clear=True), owner(book.root):
            book.load()
            run_model(book, transport=lambda *a: self.fail('network call without key'))
        self.assertEqual(book.state['status'], 'WAITING_FOR_KEY')
        self.assertEqual(book.remaining()['model_calls'], 18)
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': KEY}), owner(book.root):
            book.load()
            def failure(*args):
                raise RuntimeError('network failure ' + KEY)
            run_model(book, transport=failure)
            self.assertEqual(book.state['status'], 'WAITING_MODEL_RETRY')
            book.load()
            run_model(book, transport=failure)
        self.assertEqual(book.state['status'], 'STOPPED')
        self.assertEqual(book.remaining()['model_calls'], 16)
        self.assertNotIn(KEY, (book.root / 'state.json').read_text(encoding='utf-8'))

    def test_interrupted_tool_response_resumes_without_reexecuting_decision(self):
        book = self.create_book(model_calls=1)
        def interrupt(*args):
            raise KeyboardInterrupt()
        book.launcher = interrupt
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': KEY}), owner(book.root):
            book.load()
            with self.assertRaises(KeyboardInterrupt):
                run_model(book, transport=lambda *a: response('check_candidate', dict(candidate_id='c000', evidence=['request'], reason='check'), 0))
            self.assertEqual(book.remaining()['tool_calls'], 23)
            book.load()
            run_model(book, transport=lambda *a: self.fail('API request replayed'))
        self.assertEqual(len(book.state['attempts']), 1)
        self.assertEqual(len(book.state['decisions']), 1)
        self.assertEqual(book.state['status'], 'STOPPED')


if __name__ == '__main__':
    unittest.main()
