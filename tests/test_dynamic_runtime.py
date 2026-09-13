"""Three offline groups only. Provider and numerical workers are fixture doubles."""
import copy
import json
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from tools.dynamic_campaign import DynamicCampaign
from tools.dynamic_context import encoded_size, PROMPT_VERSION
from tools.spec_tools import ROOT
from tools.state_io import atomic_json, read


class DynamicRuntimeChecks(unittest.TestCase):
    def book(self):
        source = ROOT / 'runs/round9_reach'
        root = ROOT / 'runs/round9_runtime_tests' / uuid.uuid4().hex
        (root / 'inputs').mkdir(parents=True)
        (root / 'inputs/system_prompt.md').write_bytes((source / 'inputs/system_prompt.md').read_bytes())
        b = DynamicCampaign.__new__(DynamicCampaign)
        b.root, b.tick = root, time.monotonic()
        b.state = read(source / 'state.json')
        b.state.update(status='PAUSED', stop_reason=None, model_calls=[], decisions=[], attempts=[],
                       verified_diagnoses=[], evidence={}, working_memory=dict(findings=[], unresolved=[], next_action='Review fixture evidence'))
        b.state.pop('experiment', None); b.state.pop('tool_call_corrections', None)
        b.ledger = read(ROOT / 'runs/round9_budget.json')
        b.ledger.update(active_root=str(root), entries=[], used={k: 0 for k in b.ledger['limits']})
        b.backends = Mock()
        # Candidate identities and c032 baseline evidence remain genuine saved
        # inputs; all new test numerical outputs are explicitly synthetic.
        for c in b.state['candidates']:
            path = root / c['path']; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((source / c['path']).read_bytes()); b.register(path)
        for r in b.candidate('c032')['results'].values():
            path = root / r['result_ref']; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((source / r['result_ref']).read_bytes()); b.register(path)
        atomic_json(root / 'fixture.json', {'events': [dict(entity_name=f'tendon_{i}', value=-i*.123456789) for i in range(20)],
                                          'large': {'nested': {'values': [i*.123456789 for i in range(5000)]}}})
        b.register(root / 'fixture.json')
        return b

    def reload(self, b):
        new = DynamicCampaign.__new__(DynamicCampaign)
        new.root, new.tick = b.root, time.monotonic()
        new.state, new.ledger = read(b.root / 'state.json'), read(b.root / 'budget.json')
        new.backends = b.backends
        return new

    def response(self, names=('read_evidence',), arguments=None):
        args = dict(evidence_ref='fixture.json', pointer='/events', offset=0, limit=2, max_bytes=4000)
        if arguments is not None:args = arguments
        args = {**args, 'reason': 'Which entity values answer the current fixture question?', 'evidence': ['fixture.json'],
                'working_memory': dict(findings=['The fixture values answer the stated question.'], unresolved=[], next_action='Use the observed evidence')}
        return {'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None,
                 'tool_calls': [dict(id=f'call_{i}', type='function', function=dict(name=n, arguments=json.dumps(args))) for i, n in enumerate(names)]}}]}

    def run_mock(self, b, responses, steps):
        with patch('tools.dynamic_campaign.LEDGER', b.root / 'ledger.json'), \
             patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'offline-fixture-only'}), \
             patch('tools.deepseek_adapter.request_completion', side_effect=responses) as send, \
             patch.object(b, 'render'), patch.object(b, 'render_experiment'):
            b.run_model(steps)
        return send

    def legacy_failure(self, b):
        b.state['model_calls'] = [dict(index=i, status='completed', decision_sequence=0) for i in range(46)]
        row = dict(index=46, status='failed', decision_sequence=0, request_ref='model_calls/046/request.json',
                   error='One tool call per decision required')
        b.state['model_calls'].append(row); b.ledger['used']['model_calls'] = 47
        atomic_json(b.root / 'model_calls/046/response.json', self.response(('read_evidence', 'diagnose_trajectory')))
        return copy.deepcopy(row)

    def test_1_one_correction_dispatch_and_saved_recovery(self):
        for names in ((), ('read_evidence', 'diagnose_trajectory')):
            with self.subTest(count=len(names)):
                b = self.book(); bad = self.response(names)
                with patch.object(b, 'submit', wraps=b.submit) as dispatch:
                    send = self.run_mock(b, [bad], 1)
                    self.assertEqual(dispatch.call_count, 0)
                self.assertEqual(send.call_count, 1)
                self.assertEqual(b.ledger['used']['model_calls'], 1)
                self.assertEqual(read(b.root / 'model_calls/000/response.json'), bad)
                b = self.reload(b)
                def check_saved_then_dispatch(*args, **kwargs):
                    self.assertTrue((b.root / 'model_calls/001/response.json').exists())
                    return DynamicCampaign.submit(b, *args, **kwargs)
                with patch.object(b, 'submit', side_effect=check_saved_then_dispatch) as dispatch:
                    send = self.run_mock(b, [self.response()], 1)
                    self.assertEqual(dispatch.call_count, 1)
                self.assertEqual(b.ledger['used']['model_calls'], 2)
                self.assertEqual(b.ledger['used']['tool_calls'], 1)
                correction = b.count_corrections()['0']
                self.assertEqual(correction['correction_request_index'], 1)
                self.assertEqual(correction['outcome'], 'completed')
                self.assertEqual(b.state['model_calls'][1]['correction_for'], 0)
                payload = send.call_args.args[1]
                self.assertLessEqual(encoded_size(payload), 60000)
                context = json.loads(payload['messages'][1]['content'])
                self.assertIn(f'contained {len(names)} tool calls', context['tool_call_correction']['instruction'])
                self.assertEqual(context['tool_call_correction']['original_response_ref'], 'model_calls/000/response.json')
        b = self.book()
        send = self.run_mock(b, [self.response(()), self.response(('read_evidence', 'read_evidence'))], 3)
        self.assertEqual(send.call_count, 2); self.assertEqual(len(b.state['decisions']), 0)
        self.assertEqual(b.state['status'], 'PAUSED')
        self.assertEqual(b.count_corrections()['0']['correction_observed_count'], 2)
        b = self.reload(b)
        self.assertEqual(self.run_mock(b, [], 3).call_count, 0)
        self.assertEqual(b.ledger['used']['model_calls'], 2)

        # Recover the 046 pattern, charge the correction to the experiment,
        # then interrupt after response persistence and before dispatch.
        b = self.book(); original = self.legacy_failure(b)
        with patch('tools.dynamic_campaign.LEDGER', b.root / 'ledger.json'):
            b.start_experiment('llm_reach_v1')
        with patch.object(b, 'apply_model_response', side_effect=KeyboardInterrupt('fixture crash')):
            with self.assertRaises(KeyboardInterrupt):self.run_mock(b, [self.response()], 1)
        self.assertEqual(b.ledger['used']['model_calls'], 48)
        self.assertEqual(b.experiment()['used']['model_calls'], 1)
        b = self.reload(b)
        self.assertEqual(self.run_mock(b, [], 0).call_count, 0)
        self.assertEqual(len(b.state['decisions']), 1)
        self.assertEqual(b.count_corrections()['46']['correction_request_index'], 47)
        self.assertEqual(b.count_corrections()['46']['outcome'], 'completed')
        self.assertEqual(b.state['model_calls'][46], original)
        self.assertEqual(b.experiment()['used']['model_calls'], 1)
        b = self.reload(b)
        self.assertEqual(self.run_mock(b, [], 0).call_count, 0)
        self.assertEqual(len(b.state['decisions']), 1)

        # A missing response retains its unknown activity reservation on resume.
        b = self.book(); self.legacy_failure(b)
        with patch('tools.dynamic_campaign.LEDGER', b.root / 'ledger.json'):
            b.start_experiment('llm_reach_v1')
        with self.assertRaises(KeyboardInterrupt):
            self.run_mock(b, [KeyboardInterrupt('fixture transport interruption')], 1)
        b = self.reload(b)
        self.assertEqual(self.run_mock(b, [], 0).call_count, 0)
        receipt = next(r for r in b.ledger['entries'] if r['resource'] == 'model_calls')
        self.assertGreater(receipt['unsettled_wall_s'], 0)
        self.assertLessEqual(b.experiment_remaining()['active_wall_s'], 1710)
        self.assertEqual(b.experiment()['used']['model_calls'], 1)

        # No budget means pending, no fake request or enlarged correction limit.
        b = self.book(); self.legacy_failure(b)
        b.ledger['used']['model_calls'] = b.ledger['limits']['model_calls']
        self.assertEqual(self.run_mock(b, [], 2).call_count, 0)
        self.assertEqual(b.count_corrections()['46']['outcome'], 'pending')
        self.assertIsNone(b.count_corrections()['46']['correction_request_index'])

    def test_2_question_progress_pagination_english_and_bytes(self):
        b = self.book(); original_prompt = (b.root / 'inputs/system_prompt.md').read_bytes()
        old_version = b.root / 'inputs/prompt_versions/old_fixture.json'
        atomic_json(old_version, {'version': 'dynamic_evidence_reading_v1'})
        for offset in (0, 2, 2):
            send = self.run_mock(b, [self.response(arguments=dict(evidence_ref='fixture.json', pointer='/events', offset=offset, limit=2, max_bytes=4000))], 1)
            self.assertEqual(send.call_count, 1)
            b = self.reload(b)
        payload, metrics = b.build_model_request()
        context = json.loads(payload['messages'][1]['content'])
        positions = context['progress']['recent_reads']
        self.assertEqual([p['offset'] for p in positions], [0, 2, 2])
        self.assertEqual(positions[-1]['returned_range'], dict(start=2, end_exclusive=4))
        self.assertEqual(positions[-1]['next_read']['offset'], 4)
        self.assertIsNotNone(context['progress']['repeated_read_notice'])
        self.assertEqual(context['latest_tool_result']['data']['content'], read(b.root / 'fixture.json')['events'][2:4])
        effective = payload['messages'][0]['content']
        self.assertIn('Write ALL newly generated natural language in English', effective)
        self.assertIn('it does NOT require reading every page', effective)
        self.assertNotIn('statement 中文', effective)
        self.assertNotIn('先读 history/c002_diagnosis.json', effective)
        self.assertEqual((b.root / 'inputs/system_prompt.md').read_bytes(), original_prompt)
        self.assertEqual(read(old_version)['version'], 'dynamic_evidence_reading_v1')
        self.assertEqual(metrics['prompt_version']['version'], PROMPT_VERSION)
        self.assertEqual(encoded_size(payload), metrics['total_bytes'])
        self.assertLessEqual(metrics['total_bytes'], 60000)
        self.assertTrue((b.root / b.state['model_calls'][-1]['prompt_version_ref']).exists())
        page = b.dispatch('read_evidence', dict(evidence_ref='fixture.json', pointer='/large'), [], '')
        self.assertEqual(page['mode'], 'directory')
        first_child = page['next_read']['pointer']
        self.assertEqual(first_child, '/large/nested')
        next_page = b.dispatch('read_evidence', page['next_read'], [], '')
        self.assertEqual(next_page['next_read']['pointer'], '/large/nested/values')
        self.assertLessEqual(encoded_size(next_page), 4000)
        print('Progress/English complete request bytes:', metrics['total_bytes'])

    def test_3_experiment_provenance_freshness_and_ceilings(self):
        b = self.book()
        with patch('tools.dynamic_campaign.LEDGER', b.root / 'ledger.json'):
            b.start_experiment('llm_reach_v1')
        old_ids = b.experiment()['existing_candidate_ids'][:]
        old_candidates = copy.deepcopy(b.state['candidates'])
        self.assertFalse(b.experiment_summary()['mujoco_task_success'])
        with self.assertRaisesRegex(ValueError, 'Historical success'):
            b.guard_experiment_action('stop_design', {})
        with self.assertRaisesRegex(ValueError, 'runtime DeepSeek'):
            b.guard_experiment_action('optimize_matlab', {'parent_id': 'c032'})
        b.decision_origin = 'deepseek_api'
        with self.assertRaisesRegex(ValueError, 'descendants'):
            b.guard_experiment_action('simulate_candidate', {'candidate_id': 'c066'})
        with self.assertRaisesRegex(ValueError, 'fixed 20 N'):
            b.guard_experiment_action('optimize_matlab', {'parent_id': 'c032', 'variables': ['tendon_force_limit_n']})
        b.decision_origin = 'codex_development'
        engine = b.backends.engine.return_value
        engine.tdcr_search_step.side_effect = lambda text, **kw: json.dumps({'x': [json.loads(text)['best'][0]+.001]})

        def synthetic_simulate(cid, backend, purpose='validation', model_id=None):
            c = b.candidate(cid)
            if c['results'].get(backend):return {**c['results'][backend], 'cache_hit': True}
            resource = 'matlab_dynamic' if backend == 'matlab' else 'mujoco'
            receipt, new = b.reserve(resource, f'fixture:{cid}:{backend}', purpose)
            self.assertTrue(new)
            ref = f'candidates/{cid}/{backend}/offline_fixture/result.json'
            diag_ref = f'candidates/{cid}/{backend}/offline_fixture/diagnosis.json'
            result = dict(complete=True, computation_status='completed', backend=backend, candidate_id=cid,
                          position_error_m=(.008 if c['control']['mode']=='C2' else .009) if backend == 'mujoco' else .012, canonical_task_success=backend == 'mujoco',
                          result_ref=ref, diagnosis_ref=diag_ref, fixture_only=True)
            atomic_json(b.root / ref, result); b.register(b.root / ref)
            atomic_json(b.root / diag_ref, {'queries': [dict(candidate_id=cid, entity_name='tendon_0',
                        t_start_s=0., t_end_s=1.998, values={'tension_max_n': 3.125})]})
            b.register(b.root / diag_ref); c['results'][backend] = result
            b.finish(receipt, candidate_id=cid, backend=backend, result_ref=ref)
            return result

        search_args = dict(parent_id='c032', variables=['bend_z_rad'], max_evaluations=1,
                           search_id='llm_reach_v1_offline_fixture', initial_step=.01)
        with patch.object(b, 'simulate', side_effect=synthetic_simulate):
            self.assertEqual(self.run_mock(b, [self.response(('optimize_matlab',), search_args)], 1).call_count, 1)
            summary = b.experiment_summary(); ids = summary['candidate_ids']
            self.assertEqual(len(ids), 1); cid = ids[0]
            self.assertNotIn(cid, old_ids)
            self.assertEqual(summary['fresh_matlab_ids'], [cid])
            self.assertFalse(summary['numerical_experiment_complete'])
            candidate = b.candidate(cid)
            self.assertEqual(candidate['provenance']['model_request_index'], 0)
            self.assertEqual(candidate['provenance']['generator']['search_id'], search_args['search_id'])
            search = read(b.root / f"searches/{search_args['search_id']}.json")
            self.assertEqual(search['provenance']['origin'], 'deepseek_api')
            self.assertEqual(search['trials'][0]['actual_rollouts'], 0)  # Historical baseline cache.
            self.assertEqual(b.experiment()['used']['matlab_dynamic'], 1)
            self.assertEqual(b.state['candidates'][:len(old_candidates)], old_candidates)
            self.run_mock(b, [self.response(('simulate_candidate',), dict(candidate_id=cid, backend='mujoco'))], 1)
            self.assertTrue(b.experiment_summary()['numerical_experiment_complete'])
            self.assertTrue(b.experiment_summary()['mujoco_task_success'])
            receipt = next(r for r in b.ledger['entries'] if r['resource'] == 'mujoco')
            receipt['status'] = 'cached'
            self.assertFalse(b.experiment_summary()['numerical_experiment_complete'])
            receipt['status'] = 'completed'
            # A feedback-driven control child of a fresh trial can be the new
            # best even when it does not need another MATLAB optimization.
            self.run_mock(b, [self.response(('create_candidate',), dict(parent_id=cid, changes={'mode': 'C2'}))], 1)
            cid = b.experiment_candidates()[-1]['candidate_id']; candidate = b.candidate(cid)
            self.run_mock(b, [self.response(('simulate_candidate',), dict(candidate_id=cid, backend='mujoco'))], 1)
            self.assertEqual(b.experiment_summary()['best_id'], cid)
            self.assertNotIn('matlab', candidate['results'])
            with self.assertRaisesRegex(ValueError, 'checked diagnosis'):
                b.guard_experiment_action('stop_design', {})
            diagnosis_args = dict(evidence_ref=candidate['results']['mujoco']['diagnosis_ref'], record_type='queries',
                                  record_index=0, entity_name='tendon_0', t_start_s=0., t_end_s=1.998,
                                  field='tension_max_n', value=3.125, statement='Synthetic offline fixture tension is 3.125 N.')
            self.run_mock(b, [self.response(('record_verified_diagnosis',), diagnosis_args)], 1)
            self.run_mock(b, [self.response(('stop_design',), {})], 1)
        self.assertTrue(b.experiment_summary()['workflow_complete'])
        used = copy.deepcopy(b.experiment()['used'])
        b = self.reload(b)
        with patch('tools.dynamic_campaign.LEDGER', b.root / 'ledger.json'):
            b.start_experiment('llm_reach_v1')
        self.assertEqual(b.experiment()['used'], used)
        self.assertEqual(b.experiment()['existing_candidate_ids'], old_ids)
        self.assertEqual(b.experiment()['limits'], dict(model_calls=24, matlab_dynamic=40, mujoco=3, active_wall_s=1800))
        for resource in ('model_calls', 'matlab_dynamic', 'mujoco', 'active_wall_s'):
            with self.subTest(resource=resource):
                previous = b.experiment()['used'][resource]
                b.experiment()['used'][resource] = b.experiment()['limits'][resource]
                before = copy.deepcopy(b.ledger['used'])
                with self.assertRaisesRegex(ValueError, 'EXPERIMENT_BUDGET_EXHAUSTED'):
                    b.reserve(resource if resource != 'active_wall_s' else 'model_calls', 'must-not-charge')
                self.assertEqual(b.ledger['used'], before)
                b.experiment()['used'][resource] = previous


if __name__ == '__main__':
    unittest.main()
