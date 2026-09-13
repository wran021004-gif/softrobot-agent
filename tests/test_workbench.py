"""Focused executor checks. Fake workers only: zero MATLAB / MuJoCo solves."""
import contextlib
import io
import subprocess
import unittest
import uuid
from unittest.mock import patch
from tools.spec_tools import ROOT
from tools.closeout_state import atomic_json, read
from tools.workbench import Workbench, owner


def proposal(tool, arguments=None, evidence=None):
    return dict(action='continue', tool=tool, arguments=arguments or {}, evidence=evidence or ['request'], reason='test request')


class WorkbenchTests(unittest.TestCase):
    def book(self, launcher=None, **kwargs):
        def fake(root, folder, timeout):
            tool = read(folder / 'job.json')['tool']
            data = dict(canonical_task_status='FAIL', trajectory_available=True) if tool == 'evaluate_design' else {}
            atomic_json(folder / 'result.json', dict(tool=tool, status='completed', data=data))
        book = Workbench(ROOT / 'runs/round5_tests' / uuid.uuid4().hex, launcher=launcher or fake)
        book.create(**kwargs)
        return book

    def run_book(self, book, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return book.run(**kwargs)

    def test_pause_resume_feedback_stop_and_no_replay(self):
        book = self.book()
        self.assertEqual(self.run_book(book, steps=3)['status'], 'PAUSED')
        state = self.run_book(book)
        self.assertEqual(state['status'], 'STOPPED')
        self.assertEqual([a['tool'] for a in state['attempts']], ['inspect_task', 'analyze_design', 'evaluate_design', 'diagnose', 'observe'])
        self.assertIn('FAIL', state['stop_reason'])
        self.assertEqual(book.remaining()['simulations'], 0)
        with patch.object(book, 'launcher', side_effect=AssertionError('unexpected replay')):
            self.run_book(book)
        self.assertIn('失败证据', (book.root / 'index.html').read_text(encoding='utf-8'))

    def test_denies_unknown_tools_extra_arguments_paths_and_missing_preconditions(self):
        book = self.book()
        for p in [proposal('run_round4'), proposal('evaluate_design', {'controller': 'C2'}),
                  proposal('inspect_task', {'shell': 'echo'}), proposal('read_evidence', {'evidence_id': '../request.json'}),
                  proposal('evaluate_design'), proposal('inspect_task', evidence=['invented'])]:
            state = self.run_book(book, decision=p)
            self.assertEqual(state['decisions'][-1]['status'], 'rejected')
        self.assertEqual(len(state['attempts']), 0)
        self.assertEqual(book.remaining()['simulations'], 1)

    def test_same_inputs_reuse_sealed_result_without_worker(self):
        book = self.book()
        self.run_book(book, decision=proposal('inspect_task'))
        with patch.object(book, 'launcher', side_effect=AssertionError('unexpected replay')):
            state = self.run_book(book, decision=proposal('inspect_task'))
        self.assertEqual(len(state['attempts']), 1)
        self.assertEqual(state['decisions'][-1]['status'], 'reused')

    def test_modified_result_or_code_blocks_resume(self):
        book = self.book()
        self.run_book(book, steps=1)
        result = book.root / book.state['attempts'][0]['result_ref']
        original = result.read_bytes()
        result.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'EVIDENCE_CHANGED'):
            self.run_book(book)
        result.write_bytes(original)
        with patch('tools.workbench.source_hashes', return_value={}):
            with self.assertRaisesRegex(ValueError, 'SOURCE_OR_RUNTIME_CHANGED'):
                self.run_book(book)

    def test_budget_exhaustion_stops_without_backend_and_forced_request_rejected(self):
        book = self.book(simulations=0)
        self.run_book(book, steps=2)
        state = self.run_book(book, decision=proposal('evaluate_design', {'controller': 'C1'}))
        self.assertEqual(state['decisions'][-1]['failure_code'], 'BUDGET_EXHAUSTED')
        state = self.run_book(book)
        self.assertEqual(state['status'], 'STOPPED')
        self.assertFalse(any(a['tool'] == 'evaluate_design' for a in state['attempts']))

    def test_worker_timeout_is_charged_and_stops(self):
        def timeout(*args):
            raise subprocess.TimeoutExpired('fake worker', 180)
        book = self.book(launcher=timeout)
        state = self.run_book(book)
        self.assertEqual(state['status'], 'CAPABILITY_MISSING')
        self.assertEqual(state['attempts'][0]['result']['failure_code'], 'TIMEOUT')
        self.assertEqual(book.remaining()['tool_calls'], 9)

    def test_hard_interruption_recovers_sealed_output_or_marks_charged(self):
        for sealed in (False, True):
            book = self.book()
            self.run_book(book, steps=1)
            state = read(book.root / 'state.json')
            attempt = state['attempts'][0]
            result_ref = attempt.pop('result_ref')
            attempt.pop('result')
            attempt['status'] = 'reserved'
            state['evidence'] = {k: v for k, v in state['evidence'].items() if not k.startswith('attempts/')}
            if not sealed:
                (book.root / result_ref).unlink()
            atomic_json(book.root / 'state.json', state)
            with owner(book.root):
                book.load()
            self.assertEqual(book.remaining()['tool_calls'], 9)
            self.assertEqual(book.state['attempts'][0]['result']['status'], 'completed' if sealed else 'interrupted')

    def test_registered_history_is_context_and_never_current_score(self):
        book = self.book(history=[ROOT / 'docs/evidence/round4/length_summary.json'])
        state = self.run_book(book, steps=1)
        self.assertEqual(state['attempts'][0]['tool'], 'read_evidence')
        self.assertEqual(state['evidence']['history:0']['role'], 'historical_context_only')
        self.assertEqual(book.remaining()['simulations'], 1)

    def test_denies_outside_output_and_permission(self):
        with self.assertRaises(ValueError):
            Workbench(ROOT / 'tasks/output')
        book = self.book()
        book.state['request']['permissions'] = []
        # Exercise dispatcher with a trusted restrictive policy, not a modified file on resume.
        book.submit(proposal('inspect_task'))
        self.assertEqual(book.state['decisions'][-1]['failure_code'], 'PERMISSION_DENIED')
        self.assertEqual(book.state['attempts'], [])

    def test_decision_budget_bounds_repeated_invalid_model_output(self):
        book = self.book()
        state = self.run_book(book, policy=lambda context: proposal('nonexistent'))
        self.assertEqual(state['status'], 'STOPPED')
        self.assertEqual(state['stop_reason'], 'DECISION_BUDGET_EXHAUSTED')
        self.assertEqual(len(state['decisions']), 14)
        self.assertEqual(state['attempts'], [])

    def test_replay_rule_and_cost_do_not_request_new_simulation(self):
        from tools.workbench_policy import decide
        book = self.book()
        self.run_book(book, steps=2)
        book.state['request']['replay'] = {'path': 'inputs/replay'}
        book.state['request']['limits'].update(simulations=0, matlab_calls=0)
        book.state['evidence']['inputs/replay/run.json'] = book.state['evidence']['request']
        value = decide(book.context())
        self.assertEqual(value.tool, 'evaluate_design')
        book.submit(value)
        self.assertEqual(book.state['attempts'][-1]['cost'], {'tool_calls': 1})
        self.assertEqual(book.remaining()['simulations'], 0)

    def test_malformed_model_json_is_rejected_without_dashboard_crash(self):
        book = self.book()
        state = self.run_book(book, decision=['invalid decision'])
        self.assertEqual(state['decisions'][-1]['status'], 'rejected')
        self.assertEqual(state['attempts'], [])


if __name__ == '__main__':
    unittest.main()
