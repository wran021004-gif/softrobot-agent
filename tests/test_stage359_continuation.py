"""Focused offline checks; synthetic receipts are never live evidence."""
from copy import deepcopy
import json
from unittest.mock import patch
from examples import stage359_continuation as continuation
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.gvs_profile import execution_scope
from tests.test_stage357_live_batch import LiveIntegrationTests
from tests.test_stage356_batch import offline_directory
from tools.live_batch_execution import LiveBatchExecution
from tools.platform_store import Store, plain, zero
from tools.platform_search import prepare_offline_batch, run_live_batch
from tools.state_io import digest


class ContinuationTests(LiveIntegrationTests):
    def terminal_fixture(self, directory):
        old = Store(continuation.prior.RUN)
        source = ControlEvidence(old).resolve(continuation.SOURCES[-1][2])
        self.configuration = old.artifact(source['metadata']['candidate_input'])
        batch = continuation.read(continuation.prior.RUN / 'batch_result.json')
        self.facts = next(c['execution']['factual_result'] for c in batch['candidates']
                          if c.get('execution_id') == continuation.SOURCES[-1][2])
        self.plan['bindings']['subject'] = self.facts['candidate']
        host, original = self.fixture(directory, wall_s=4200., max_candidates=4,
                                      backend_attempts=2, model_calls=8)
        history, _ = continuation.import_references(host)
        record = host.store.artifact(original)
        record['plan'].update(variables={'control/recipe/terminal_tip_speed_weight': [0., 1.]},
                              step=.05, max_backend_attempts=2,
                              target_changed_configurations=2,
                              planned_budget=dict(model_calls=8, tool_calls=20,
                                                  backend_solves=2, worker_calls=0, wall_s=4200.))
        fixed = deepcopy(self.configuration['effective'])
        fixed['policy']['controller']['parameters']['data']['recipe']['terminal_tip_speed_weight'] = '<batch variable>'
        record['bindings'].update(fixed_configuration=fixed, fixed_configuration_identity=digest(fixed))
        record['offline_predecessor_plan'] = continuation.read(continuation.prior.RUN / 'chain.json')['search_plan']
        with host.store.transaction() as db:
            ref = plain(host.store.put(db, record))
            host.store.event(db, host.run_id, 'role_transition', 'search_batch_plan', outputs=[ref])
        return host, ref, history

    def test_one_variable_five_records_generation_and_continuation(self):
        with offline_directory() as directory:
            host, ref, history = self.terminal_fixture(directory)
            batch = prepare_offline_batch(host, ref, mode='live', starting_facts=self.facts,
                                          retained_baseline=history[0]['facts'], historical_results=history)
            self.assertEqual(len(batch['historical_results']), 5)
            self.assertEqual([r['reusable_under_plan'] for r in batch['historical_results']],
                             [True, False, False, False, True])
            self.assertEqual(batch['parameters']['initial'], {'control/recipe/terminal_tip_speed_weight': .05})
            self.assertEqual(batch['base_configuration'], history[-1]['facts']['configuration'])
            self.assertEqual(batch['retained_baseline']['execution_id'], continuation.SOURCES[0][2])
            calls = []

            def stage(obj, name, candidate):
                child = obj.candidate_host(candidate)
                request = 'complete-' + name
                old = child.store.lookup(child.run_id, request)
                if old:
                    return json.loads(old['receipt'])
                calls.append((name, candidate['changes']))
                row, _ = child.store.reserve(child.run_id, request, digest(candidate), child.actor,
                    {**zero(), 'tool_calls': 1, 'backend_solves': int(name == 'simulation'),
                     'wall_s': dict(simulation=900, evaluation=30, profile=60)[name]})
                return child.store.complete(row, dict(request_id=request, execution_id=row['execution_id'],
                    caller=child.actor, tool_id='offline.test.'+name, tool_version='1.0.0',
                    execution_status='completed', charged=zero()), dict(mode='offline_test_fixture'), .01)

            def facts(obj, candidate):
                f = self.synthetic(.007, .008, .03, candidate['configuration'])
                f['candidate']['candidate_id'] = candidate['candidate_id']
                return dict(factual_result=f, configuration=candidate['configuration'], mode='offline_test_fixture')

            with patch.object(LiveBatchExecution, 'stage', stage), patch.object(LiveBatchExecution, 'facts', facts):
                paused = run_live_batch(host, stop_after_stage='simulation')
                self.assertEqual(paused['completed_profiles'], 0)
                self.assertEqual(paused['accounting']['historical_start_reuse'], 1)
                result = run_live_batch(host)
            # Coordinate proposals depend on feedback. This synthetic fixture
            # improves at .10, so it revisits .05 then proposes .15, not .25.
            self.assertEqual([round(p['changes']['control/recipe/terminal_tip_speed_weight'], 8)
                              for p in result['proposals']], [.05, .10, .05, .15])
            self.assertEqual(result['accounting']['historical_start_reuse'], 1)
            self.assertEqual(result['accounting']['duplicate_result_reuse'], 1)
            self.assertEqual(result['accounting']['distinct_configurations'], 3)
            self.assertEqual(result['accounting']['new_backend_attempts'], 2)
            self.assertEqual(result['completed_evaluations'], 2)
            self.assertEqual(result['completed_profiles'], 2)
            self.assertEqual(sum(name == 'simulation' for name, _ in calls), 2)
            self.assertEqual(result['stop_reason'], 'pilot_target_complete')
            for row in result['candidates']:
                if row['reused']:
                    continue
                actual = host.store.artifact(row['configuration'])['effective']
                expected = deepcopy(self.configuration['effective'])
                expected['policy']['controller']['parameters']['data']['recipe']['terminal_tip_speed_weight'] = row['changes']['control/recipe/terminal_tip_speed_weight']
                self.assertEqual(actual, expected)
                self.assertEqual(row['feedback']['comparison']['baseline']['source']['execution_id'], continuation.SOURCES[-1][2])
                self.assertEqual(row['retained_baseline_comparison']['baseline']['source']['execution_id'], continuation.SOURCES[0][2])

    def test_changed_structure_is_reference_only_and_gate_blocks_launch(self):
        with patch.object(continuation,'read',return_value=dict(passed=False,criteria=dict(accurate_model_interpretation_and_final_decision=False))):
            with self.assertRaisesRegex(ValueError, 'REQUIRES_ACCEPTED_STAGE358'):
                continuation.require_interpretation_gate()
        with offline_directory() as directory:
            host, ref, history = self.terminal_fixture(directory)
            bad = deepcopy(history[-1])
            cfg = host.store.artifact(bad['facts']['configuration'])
            cfg['effective']['robot']['structure']['data']['components'][0]['length_m'] += .001
            with host.store.transaction() as db:
                new_ref = plain(host.store.put(db, cfg))
            bad['facts']['configuration'] = new_ref
            bad['facts']['candidate']['configuration'] = new_ref
            bad['execution_scope'] = execution_scope(cfg['effective'])
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_FIXED_SCIENCE_MISMATCH'):
                prepare_offline_batch(host, ref, mode='live', starting_facts=self.facts,
                                      retained_baseline=history[0]['facts'], historical_results=[bad])

    def test_offline_reference_roles_and_zero_live_usage(self):
        with offline_directory() as directory:
            host, refs = continuation.prepare_references(directory)
            self.assertEqual(len(refs['complete_historical_records']), 5)
            self.assertNotEqual(refs['search_start'], refs['retained_baseline'])
            self.assertEqual(refs['search_start'], refs['immediate_predecessor'])
            self.assertFalse(refs['predecessor_decision_accepted'])
            self.assertIsNone(refs['accepted_executable_plan'])
            self.assertEqual(host.store.remaining()['used'], zero())

    def test_full_correction_content_reaches_provider_payload_offline(self):
        from tools.platform_host import Host
        from tools.platform_models import payload_for
        from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
        store = Store(continuation.prior.RUN)
        with store.connect(True) as db:
            run_id = next(r['run_id'] for r in db.execute('SELECT run_id,state FROM sessions')
                          if json.loads(r['state']).get('role_context', {}).get('require_research_route'))
        host = Host(continuation.prior.RUN, run_id)
        request = continuation.read(continuation.prior.EVIDENCE / 'factual_correction_request.json')
        supplement = continuation.read(continuation.prior.EVIDENCE / 'factual_correction_supplement.json')
        original_session = host.store.session

        def session(*args, **kwargs):
            value = deepcopy(original_session(*args, **kwargs))
            if value['run_id'] == run_id:
                role = value['state']['role_context']
                role['factual_correction_content'] = request
                role['factual_correction_supplement_content'] = supplement
            return value

        before = host.store.remaining()['used']
        with patch.object(host.store, 'session', side_effect=session):
            payload = payload_for(host, EvidenceDrivenAdapter())
        content = json.loads(payload['messages'][1]['content'])['role_context']
        expected = deepcopy(request)
        # Existing model-facing tool spelling is normalized by the adapter;
        # the sealed original request retains internal names.
        for context in expected['contradictions'][5]['facts']['dual_read_coverage']['contexts']:
            for view in context['views']:
                view['method'] = view['method'].replace('diagnosis.inspect_evidence', 'diagnosis_inspect_evidence')
        self.assertEqual(content['factual_correction_content'], expected)
        self.assertEqual(content['factual_correction_supplement_content'], supplement)
        self.assertEqual(payload['max_tokens'], 65536)
        self.assertLess(len(json.dumps(payload).encode()), 400000)
        self.assertEqual(host.store.remaining()['used'], before)
