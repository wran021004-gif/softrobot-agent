"""Focused local platform acceptance. No model APIs or real simulator solves."""
import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4
from examples.platform_fixtures import reference_input, project, binding, budget
from schemas.platform import WorkOrder, EvidenceRef, MemoryEntry, BackendResult
from tools.platform_host import Host
from tools.platform_store import Store, zero, plain, encode
from tools.platform_registry import registry
from tools.platform_tasks import report
from tools.spec_tools import ROOT

TEST_ROOTS = []


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'runs/platform_tests' / uuid4().hex
        self.store = Store(self.root)
        self.store.create(project())
        self.host = Host(self.root, 'fixture')
        self.input = reference_input('fixture')
        self.host.create(self.input)
        TEST_ROOTS.append(self.root)

    def call(self, tool, arguments=None, identity=None, **extra):
        return self.host.invoke(dict(request_id=identity or uuid4().hex, tool_id=tool,
            arguments=arguments or {}, reason='开发契约验收', **extra))

    def simulate(self):
        result = self.call('simulation.run')
        self.assertEqual(result['execution_status'], 'completed', result)
        return result['output']

    def test_definition_units_missing_implementation_and_independent_sampling(self):
        self.assertTrue(report(self.input)['executable'])
        bad = copy.deepcopy(self.input)
        del bad['task']['goal']['data']['length_m']
        self.assertIn('length_m', str(report(bad)['errors']))
        bad = copy.deepcopy(self.input)
        bad['task']['observations'][0]['units'] = 'rad'
        self.assertIn('REQUIRED_SIGNAL', str(report(bad)['errors']))
        bad = copy.deepcopy(self.input)
        bad['task']['evaluator']['extension_id'] = 'evaluate.gentle_catch'
        self.assertIn('IMPLEMENTATION_REQUIRED', str(report(bad)['errors']))
        bad = copy.deepcopy(self.input)
        bad['task']['sampling']['split'] = 'evaluation'
        self.assertIn('DISJOINT_SEED', str(report(bad)['errors']))
        bad = copy.deepcopy(self.input)
        bad['policy']['editable'] = {'task.goal.length_m': [0., 1.]}
        self.assertIn('PARAMETER_NOT_EDITABLE', str(report(bad)['errors']))

    def test_catalog_lazy_dependency_and_duplicate_detection(self):
        code = "from tools.platform_registry import registry; import sys; r=registry(); r.catalog(); assert 'mujoco' not in sys.modules; assert 'matlab.engine' not in sys.modules; assert 'numpy' not in sys.modules"
        subprocess.run([sys.executable, '-c', code], cwd=ROOT, check=True)
        reg = registry()
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_EXTENSION'):
            reg.add(reg.get('analysis.vector_norm'))
        row = next(r for r in reg.catalog() if r['extension_id'] == 'backend.genesis')
        self.assertFalse(row['implementation_exists'])
        self.assertFalse(row['executable'])

    def test_math_extension_loop_discovery_delivery_and_pagination(self):
        from tools.platform_models import OfflineAdapter
        result = self.host.run(OfflineAdapter([
            dict(tool_id='analysis.vector_norm', arguments=dict(values_m=[3., 4.]), reason='数学接口'),
            dict(tool_id='evidence.read', arguments=dict(reference='$last_output', pointer='/norm_m'), reason='读计算结果'),
            dict(tool_id='session.control', arguments=dict(status='stopped', reason='完成'), reason='停止')]))
        self.assertEqual(result['status'], 'stopped', result['state'])
        events = self.store.events('fixture')
        delivered = [e for e in events if e['kind'] == 'context_delivery']
        self.assertEqual(len(delivered), 3)
        payload = self.store.artifact(delivered[2]['inputs'][0])
        context = json.loads(payload['messages'][-1]['content'])
        self.assertEqual(context['observation']['content']['content'], 5.0)
        self.assertTrue(context['pagination'])
        self.assertEqual(context['visual_delivery']['images_submitted'], [])
        self.assertEqual(self.store.remaining()['used']['model_calls'], 0)
        children = self.store.events('fixture', delivered[0]['parent_id'])
        self.assertTrue(any(e['kind'] == 'tool' for e in children))

    def test_request_dedup_cache_new_and_caller_identity(self):
        a = self.call('analysis.vector_norm', dict(values_m=[3., 4.]), 'same')
        self.assertEqual(a['execution_status'], 'completed', a)
        used = self.store.remaining()['used']
        self.assertEqual(a, self.call('analysis.vector_norm', dict(values_m=[3., 4.]), 'same'))
        self.assertEqual(used, self.store.remaining()['used'])
        collision = self.call('analysis.vector_norm', dict(values_m=[1.]), 'same')
        self.assertIn('COLLISION', collision['error'])
        cached = self.call('analysis.vector_norm', dict(values_m=[3., 4.]), 'cache')
        self.assertTrue(cached['cache_hit'])
        fresh = self.call('analysis.vector_norm', dict(values_m=[3., 4.]), 'new', cache='new')
        self.assertFalse(fresh['cache_hit'])
        forged = self.call('analysis.vector_norm', dict(values_m=[1.]), caller='admin')
        self.assertEqual(forged['execution_status'], 'rejected')
        self.assertIn('caller', forged['error'])
        event = next(e for e in self.store.events('fixture') if e['request_id'] == 'same' and e['status'] == 'reserved')
        original = self.store.artifact(event['inputs'][0])
        self.assertEqual(original['arguments'], dict(values_m=[3., 4.]))
        self.assertEqual(original['reason'], '开发契约验收')

    def test_task_snapshot_and_nonreach_evaluation(self):
        self.input['task']['goal']['data']['length_m'] = 999.
        reference = self.simulate()
        result = self.call('evaluation.run', dict(result=reference))
        self.assertEqual(result['execution_status'], 'completed', result)
        evaluation = self.store.artifact(result['output'])
        self.assertEqual(evaluation['validity'], 'valid')
        self.assertEqual({m['name'] for m in evaluation['metrics']}, {'rms_deviation', 'max_deviation'})
        self.assertNotIn('position_error_m', encode(evaluation))
        self.assertEqual(self.store.remaining()['used']['backend_solves'], 0)
        failed_task = self.call('simulation.run', dict(changes={'controller.command_m': 0.34}))
        failed_eval = self.call('evaluation.run', dict(result=failed_task['output']))
        self.assertFalse(failed_eval['task_success'])
        from tools.platform_search import score
        self.assertIsNotNone(score(self.store.artifact(failed_eval['output']), reference_input()['task']['objectives']))

    def test_backend_incompatibility_before_any_solve(self):
        bad = copy.deepcopy(self.input)
        bad['policy']['backend'] = binding('backend.mujoco')
        self.assertIn('BACKEND_INCOMPATIBLE', str(report(bad)['errors']))
        before = self.store.remaining()['used']
        result = self.call('simulation.run', dict(changes={'task.goal': 1.}))
        self.assertEqual(result['execution_status'], 'rejected')
        self.assertEqual(before, self.store.remaining()['used'])

    def test_interruption_unknown_no_replay_and_retained_reservation(self):
        from extensions.reference.implementation import ReferenceBackend
        with patch.object(ReferenceBackend, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.call('simulation.run', identity='interrupted')
        used = self.store.remaining()['used']
        with patch.object(ReferenceBackend, 'run', side_effect=AssertionError('must not replay')):
            result = self.call('simulation.run', identity='interrupted')
        self.assertEqual(result['execution_status'], 'unknown')
        self.assertEqual(used, self.store.remaining()['used'])
        self.assertEqual(used['wall_s'], 10.)

    def test_atomic_shared_resources_and_copied_grant_rejection(self):
        def reserve(index):
            try:
                return self.store.reserve('fixture', 'race-' + str(index), str(index), 'worker',
                    {**zero(), 'worker_calls': 1, 'wall_s': 10.}, ['reference_device'])
            except ValueError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(reserve, range(2)))
        self.assertEqual(sum(isinstance(r, tuple) for r in rows), 1)
        self.assertTrue(any('RESOURCE_BUSY' in r for r in rows if isinstance(r, str)))
        with self.assertRaisesRegex(ValueError, 'GRANT_ALREADY_BOUND'):
            Store(self.root / 'copied').create(self.store.config())
        copied = self.root / 'copied_readonly'
        copied.mkdir()
        with self.store.connect(True) as source, sqlite3.connect(copied / 'platform.sqlite') as destination:
            source.backup(destination)
        self.assertEqual(Store(copied).config(), self.store.config())
        with self.assertRaisesRegex(ValueError, 'MOVED_OR_COPIED'):
            with Store(copied).transaction():
                pass

    def test_search_lifecycle_restore_and_ranking_identity(self):
        from tools.platform_search import run_search, rank
        result = run_search(self.host)
        self.assertEqual(result['status'], 'completed', result)
        self.assertEqual(len(result['trials']), 2)
        used = self.store.remaining()['used']
        self.assertEqual(run_search(self.host)['trials'], result['trials'])
        self.assertEqual(used, self.store.remaining()['used'])
        evaluations = [self.store.artifact(t['evaluation']) for t in result['trials']]
        self.assertEqual(len(rank(evaluations, self.input['task']['objectives'])), 2)
        evaluations[1]['comparison_identity'] = 'different_backend'
        with self.assertRaisesRegex(ValueError, 'INCOMPARABLE'):
            rank(evaluations, self.input['task']['objectives'])
        from extensions.reference.implementation import LengthController
        from extensions.reference.contracts import LengthControl
        a = LengthController(LengthControl(command_m=0.3), 0.01)
        a.reset(); a.command(0., {})
        b = LengthController(LengthControl(command_m=0.3), 0.01)
        b.restore(a.checkpoint().data)
        self.assertEqual(a.command(0.01, {}), b.command(0.01, {}))
        b.reset()
        self.assertEqual(b.state.steps, 0)

    def test_diagnostic_missing_and_fact_evidence(self):
        ref = self.simulate()
        for signal, threshold, units, expected in [('contact_count', 0., 'count', 'no_event'), ('absent', 0., 'N', 'missing_data'),
            ('tendon_length', 0.2, 'm', 'events_found'), ('tendon_length', 0.2, 'N', 'not_applicable')]:
            result = self.call('diagnostics.sample_exceeds', dict(result=ref, signal=signal, threshold=threshold, units=units))
            self.assertEqual(result['execution_status'], 'completed', result)
            detail = self.store.artifact(result['output'])
            self.assertEqual(detail['status'], expected)
            self.assertIsNone(detail['causal_hypothesis'])

    def test_memory_retrieval_actual_context_and_invalidated_sources(self):
        from tools.platform_models import OfflineAdapter
        ref = self.simulate()
        entry = dict(memory_id='experience', summary='参考长度轨迹可读取；不能推断真实物理能力', kind='direct_observation', task_family='task.signal_hold',
            task_version='1.0.0', backend='backend.reference', model_id='discrete_length_response_fixture', tags=['development'], sources=[ref])
        saved = self.call('memory.save', dict(entry=entry))
        self.assertEqual(saved['execution_status'], 'completed', saved)
        model_host = Host(self.root, 'fixture', actor='model')
        denied = model_host.invoke(dict(request_id='model-fact', tool_id='memory.save', arguments=dict(entry=entry), reason='注入伪造已验证事实'))
        self.assertEqual(denied['execution_status'], 'failed')
        other = Host(self.root, 'later')
        other.create(reference_input('later'))
        other.run(OfflineAdapter([]))
        delivery = next(e for e in self.store.events('later') if e['kind'] == 'context_delivery')
        context = json.loads(self.store.artifact(delivery['inputs'][0])['messages'][-1]['content'])
        self.assertEqual(context['memory'][0]['memory_id'], 'experience')
        with self.store.transaction() as db:
            db.execute('UPDATE artifacts SET body=? WHERE id=?', (b'{}', ref['artifact_id']))
        self.assertEqual(self.store.memories(dict(task_family='task.signal_hold')), [])

    def order(self, work_id, signal, ref, inject='none', delay=1.2):
        return WorkOrder(work_id=work_id, goal='读取固定证据中的信号', worker={**binding('worker.signal', 'reference.worker', dict(signal=signal, delay_s=delay, inject=inject)), 'version': '2.0.0'},
            input_snapshot=ref, base_candidate='baseline', allowed_tools=['evidence.read'],
            budget=budget(tool_calls=1, worker_calls=1, wall_s=10.), timeout_s=10., output_contract='WorkerOutput@2.0.0')

    def collect_workers(self, coordinator, names):
        end = time.monotonic() + 20
        while time.monotonic() < end:
            results = [coordinator.collect(name) for name in names]
            if all(r.status not in ('running', 'output_ready', 'failure_ready', 'reserved') for r in results):
                return results
            time.sleep(0.05)
        self.fail('worker deadline')

    def test_actual_concurrent_workers_evidence_and_idempotent_merge(self):
        from tools.platform_workers import Coordinator
        ref = self.simulate()
        coordinator = Coordinator(self.host)
        for name, signal in [('tendon', 'tendon_length'), ('contact', 'contact_count')]:
            result = self.call('workers.submit', dict(order=plain(self.order(name, signal, ref))))
            self.assertEqual(result['execution_status'], 'completed', result)
        results = self.collect_workers(coordinator, ['tendon', 'contact'])
        self.assertEqual([r.status for r in results], ['completed', 'completed'])
        outputs = [self.store.artifact(r.result) for r in results]
        self.assertLess(max(o['started_at'] for o in outputs), min(o['ended_at'] for o in outputs))
        for name in ('tendon', 'contact'):
            self.assertEqual(coordinator.accept(name).status, 'accepted')
            self.assertEqual(coordinator.accept(name).status, 'accepted')
        self.assertNotEqual(outputs[0]['result']['data']['signal'], outputs[1]['result']['data']['signal'])
        self.assertEqual(self.store.remaining()['used']['worker_calls'], 2)
        before = self.store.remaining()['used']
        coordinator.submit(self.order('tendon', 'tendon_length', ref))
        self.assertEqual(self.store.remaining()['used'], before)

    def test_worker_failure_cancel_and_conflict(self):
        from tools.platform_workers import Coordinator
        ref = self.simulate(); coordinator = Coordinator(self.host)
        coordinator.submit(self.order('failure', 'contact_count', ref, 'failure'))
        coordinator.submit(self.order('cancel', 'contact_count', ref, delay=5.))
        self.assertEqual(coordinator.cancel('cancel').status, 'cancelled')
        self.assertEqual(self.collect_workers(coordinator, ['failure'])[0].status, 'failed')
        for name, signal in [('conflict1', 'tendon_length'), ('conflict2', 'contact_count')]:
            coordinator.submit(self.order(name, signal, ref, 'conflict'))
        self.collect_workers(coordinator, ['conflict1', 'conflict2'])
        self.assertEqual(coordinator.accept('conflict1').status, 'accepted')
        self.assertEqual(coordinator.accept('conflict2').status, 'conflict')

    def test_readonly_queries_leave_database_identical(self):
        from tools.platform_models import payload_for
        from tools.platform_view import result_view
        before = self.store.db.read_bytes()
        self.store.events('fixture'); self.store.remaining(); self.host.discover(); self.host.context(); self.host.compatibility()
        result_view(self.host); payload_for(self.host)
        self.assertEqual(before, self.store.db.read_bytes())

    def test_dependency_identity_changes_and_no_document_invalidation(self):
        from tools.platform_registry import dependency_identity
        definition = self.host.reg.get('analysis.vector_norm')
        identity = dependency_identity(definition)
        self.assertFalse(any(p.startswith('docs/') for p in identity['sources']))
        self.assertNotEqual(identity, dependency_identity(replace(definition, version='2.0.0')))
        bad = copy.deepcopy(self.input)
        bad['policy']['search']['parameters']['data']['candidates'] = [0.3]
        bad['task']['objectives'].append(dict(metric='max_deviation', direction='minimize', units='m'))
        self.assertIn('MULTIOBJECTIVE', str(report(bad)['errors']))

    def test_existing_service_executor_adapted_without_double_charge(self):
        inp = reference_input('service')
        inp['policy']['allowed_tools'].append('analysis.pcc_condition')
        host = Host(self.root, 'service')
        host.create(inp)
        result = host.invoke(dict(request_id='condition', tool_id='analysis.pcc_condition', tool_version='1.1.0',
            arguments=dict(length_m=1., bend_rad=[0., 0.]), reason='复用真实数学进程执行器'))
        self.assertEqual(result['execution_status'], 'completed', result)
        self.assertEqual(host.store.artifact(result['output'])['singular_values_m_per_rad'], [0.5, 0.5])
        self.assertEqual(host.store.remaining('service')['used']['tool_calls'], 1)
        self.assertEqual(host.store.remaining('service')['used']['backend_solves'], 0)

    def test_skill_existing_lifecycle_and_next_context(self):
        from datetime import datetime, timezone, timedelta
        from tools.skill_policy import REQUIRED_CONSTRAINTS, strategy_hash
        from schemas.skill import SkillValidationEvidence
        ref = self.simulate()
        artifact = dict(run_id='fixture', path='objects/' + ref['artifact_id'] + '.json', sha256=ref['artifact_id'])
        timestamp = datetime.now(timezone.utc)
        skill = dict(skill_id='saved_signal_inspection', name='保存信号检查开发策略', version=1, status='candidate', category='DIAGNOSIS',
            description='引用已保存信号；只证明接口经验，不证明物理因果。', trigger_signature=dict(failure_categories=[], metrics=[]),
            when_to_apply=['同类参考信号任务'], when_not_to_apply=['真实接触物理分析'],
            applicability=dict(robot_families=['reference_signal_robot'], task_types=['task.signal_hold'], model_levels=['M0'], control_levels=['C1']),
            required_tools=['evidence.read'], strategy=[dict(action='inspect_evidence', evidence_refs=[artifact], instruction='读取已保存参考信号并报告缺失项。')],
            negative_constraints=sorted(REQUIRED_CONSTRAINTS), evidence=[artifact],
            provenance=dict(source_runs=['fixture'], supporting_evidence=[artifact], created_by='harness', created_at=timestamp.isoformat()))
        result = self.call('skills.propose', dict(skill=skill))
        self.assertEqual(result['execution_status'], 'completed', result)
        validation = SkillValidationEvidence(skill_ref='saved_signal_inspection@1', strategy_sha256=strategy_hash(skill), run_id='fixture',
            worked=True, summary='确定性检查：保存证据具有 tendon_length 信号；不声称自然语言因果已验证。')
        with self.store.transaction() as db:
            validation_ref = self.store.put(db, validation)
            self.store.event(db, 'fixture', 'skill_validation_experiment', 'completed', inputs=[ref], outputs=[validation_ref])
        record = dict(validation_id='check1', skill_ref='saved_signal_inspection@1', strategy_sha256=strategy_hash(skill), method='deterministic',
            outcome='passed', validated_runs=['fixture'], failed_validation_runs=[], task_coverage=['task.signal_hold'],
            robot_coverage=['reference_signal_robot'], seed_coverage=[17], validated_by='harness', validated_at=(timestamp + timedelta(seconds=1)).isoformat(),
            summary='确定性保存信号检查', evidence_refs=[dict(run_id='fixture', path='objects/' + validation_ref.artifact_id + '.json', sha256=validation_ref.artifact_id)])
        result = self.call('skills.validate', dict(reference='saved_signal_inspection@1', record=record))
        self.assertEqual(result['execution_status'], 'completed', result)
        self.assertEqual(self.store.artifact(result['output'])['skills'][0]['status'], 'validated')
        other = Host(self.root, 'with-skill'); other.create(reference_input('with-skill'))
        from tools.platform_models import OfflineAdapter
        other.run(OfflineAdapter([]))
        event = next(e for e in self.store.events('with-skill') if e['kind'] == 'context_delivery')
        context = json.loads(self.store.artifact(event['inputs'][0])['messages'][-1]['content'])
        self.assertEqual(context['skills'][0]['skill_id'], 'saved_signal_inspection')
        self.assertIsNone(context['skills'][0]['human_approval'])

    def test_bounded_repair_pause_and_visual_claim_rejected(self):
        from tools.platform_models import OfflineAdapter
        malformed = [dict(tool_id='unregistered.tool', arguments={}, reason='故障注入')] * 5
        outcome = self.host.run(OfflineAdapter(malformed))
        self.assertEqual(outcome['status'], 'failed')
        self.assertEqual(outcome['state']['turn'], 3)
        inp = reference_input('visual')
        inp['policy']['model']['supports_images'] = True
        visual = Host(self.root, 'visual'); visual.create(inp)
        outcome = visual.run(OfflineAdapter([]))
        self.assertEqual(outcome['status'], 'needs_input')
        self.assertFalse(any(e['kind'] == 'context_delivery' for e in self.store.events('visual')))

    def test_worker_stale_base_and_unknown_resource_retention(self):
        from tools.platform_workers import Coordinator
        ref = self.simulate(); coordinator = Coordinator(self.host)
        coordinator.submit(self.order('stale', 'contact_count', ref, delay=0.1))
        self.collect_workers(coordinator, ['stale'])
        with self.store.transaction() as db:
            state = self.store.session('fixture', db)['state']; state['active_candidate'] = 'new-candidate'
            self.store.update_state(db, 'fixture', state)
        self.assertEqual(coordinator.accept('stale').status, 'stale')
        row, _ = self.store.reserve('fixture', 'unknown-resource', 'identity', 'worker',
            {**zero(), 'worker_calls': 1, 'wall_s': 3.}, ['reference_device'])
        self.store.mark_unknown('fixture', 'unknown-resource')
        self.assertEqual(self.store.remaining()['occupied']['reference_device'], 1)

    def test_historical_readonly_no_new_solves(self):
        from tools.platform_history import inspect_history
        path = ROOT / 'runs/round9_reach'
        if not path.exists():
            self.skipTest('历史运行未在当前工作区安装')
        before = (path / 'state.json').read_bytes()
        report = inspect_history(path)
        self.assertTrue(report['references'])
        self.assertFalse(report['errors'], report['errors'][:2])
        self.assertEqual(before, (path / 'state.json').read_bytes())

    def test_common_physics_provider_without_engine_and_unavailable_quantity(self):
        from examples.platform_fixtures import reach_input
        from tools.platform_physics import RobotIRProvider
        inp = reach_input()
        provider = RobotIRProvider(inp['robot']['structure']['data'])
        query = dict(quantity='force_limit', model_identity=provider.identity, units='N', frame=provider.ir.coordinate_frame)
        self.assertEqual(provider.get(query).values, [20.])
        with self.assertRaisesRegex(ValueError, 'UNIT_MISMATCH'):
            provider.get({**query, 'units': 'Pa'})
        with self.assertRaisesRegex(ValueError, 'MODEL_QUANTITY_UNAVAILABLE'):
            provider.get({**query, 'quantity': 'mass_matrix'})

    def test_invalid_results_and_resource_budget_exhaustion(self):
        from tools.platform_search import score
        source = self.simulate()
        incomplete = dict(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
                          evaluator='evaluate.hold', comparison_identity='same', reason='injected')
        self.assertIsNone(score(incomplete, self.input['task']['objectives']))
        incomplete['metrics'] = [dict(name='rms_deviation', value=1., units='m')]
        with self.assertRaises(ValueError):
            score(incomplete, self.input['task']['objectives'])
        inp = reference_input('zero')
        inp['policy']['budget']['tool_calls'] = 0
        host = Host(self.root, 'zero'); host.create(inp)
        result = host.invoke(dict(request_id='no-budget', tool_id='analysis.vector_norm', arguments=dict(values_m=[1.]), reason='零额度'))
        self.assertEqual(result['execution_status'], 'rejected')
        self.assertIn('BUDGET_EXHAUSTED', result['error'])
        from tools.platform_models import OfflineAdapter
        outcome = host.run(OfflineAdapter([]))
        self.assertEqual(outcome['status'], 'budget_exhausted')

    def test_blank_template_and_bundle_export_readonly(self):
        from tools.platform_config import load
        with self.assertRaisesRegex(ValueError, 'environment_file'):
            load(ROOT / 'docs/templates/platform/task.blank.yaml')
        from schemas.platform import ExportBundle
        from tools.platform_view import export_bundle
        with self.store.transaction() as db:
            raw = self.store.put(db, b'saved original bytes', 'application/octet-stream')
            result = self.store.put(db, dict(saved=True))
            bundle = self.store.put(db, ExportBundle(result=result, source='synthetic_export_fixture', files=[dict(filename='source.dat', reference=raw)]))
        before = self.store.db.read_bytes()
        destination = self.root / 'exported'
        export_bundle(self.store, bundle.artifact_id, destination)
        self.assertEqual((destination / 'source.dat').read_bytes(), b'saved original bytes')
        self.assertEqual(before, self.store.db.read_bytes())

    def test_late_sealed_worker_output_reconciles_unknown_without_relaunch(self):
        from tools.platform_workers import Coordinator, PROCESSES
        ref = self.simulate(); coordinator = Coordinator(self.host)
        coordinator.submit(self.order('late', 'contact_count', ref, delay=0.1))
        key = (str(self.root.resolve()), 'fixture', 'late')
        process, _ = PROCESSES.pop(key)
        process.wait(timeout=20)
        self.store.mark_unknown('fixture', 'worker-late')
        with self.store.transaction() as db:
            db.execute("UPDATE workers SET status='unknown' WHERE run_id='fixture' AND work_id='late'")
        before = self.store.remaining()['used']['worker_calls']
        self.assertEqual(coordinator.collect('late').status, 'completed')
        self.assertEqual(self.store.remaining()['used']['worker_calls'], before)
        self.assertEqual(coordinator.accept('late').status, 'accepted')


if __name__ == '__main__':
    unittest.main()
