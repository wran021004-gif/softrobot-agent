"""Eight bounded offline acceptance groups; no real model or physics requests."""
import copy
import json
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from examples.platform_fixtures import reference_input, project, binding, payload, budget
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.platform_registry import registry, dependency_identity
from tools.platform_tasks import compile_input, report
from tools.spec_tools import ROOT
from schemas.platform import WorkOrder, MemoryEntry

ROOTS = []


def development(run='fixture', terminal=False):
    inp = reference_input(run)
    inp['policy']['tool_bindings'] = {n: '1.0.0' for n in inp['policy'].pop('allowed_tools')}
    inp['policy']['candidate_builder'] = binding('candidate.synthetic', 'convergence.empty')
    inp['policy']['editable']['structure.response_fraction'] = [0.1, 1.]
    inp['policy']['model'] = dict(adapter='model.observing', strategy='strategy.evidence', parameters=dict(values_m=[3., 4.]), max_turns=8)
    if terminal:
        inp['task'].update(family='task.terminal', task_id='terminal-dev', name='Synthetic final signal error',
            goal=payload('convergence.terminal_goal', dict(target_m=0.3)),
            evaluator=binding('evaluate.terminal', 'convergence.terminal_evaluation', dict(tolerance_m=0.01)),
            objectives=[dict(metric='terminal_error', direction='minimize', units='m')])
    return inp


class ConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'runs/platform_convergence' / uuid4().hex
        ROOTS.append(self.root)
        self.store = Store(self.root)
        self.store.create(project())

    def host(self, inp=None, reg=None):
        inp = inp or development()
        host = Host(self.root, inp['run_id'], reg=reg)
        host.create(inp)
        return host

    def call(self, host, tool, args=None, request=None, version='1.0.0'):
        return host.invoke(dict(request_id=request or uuid4().hex, tool_id=tool, tool_version=version,
            arguments=args or {}, reason='offline convergence acceptance'))

    def done(self, receipt):
        self.assertEqual(receipt['execution_status'], 'completed', receipt)
        return self.store.artifact(receipt['output'])

    def test_01_delivered_results_change_actions_and_raw_failures(self):
        changes = []
        for name, values in [('low', [3., 4.]), ('high', [6., 8.])]:
            inp = development(name)
            inp['policy']['model']['parameters']['values_m'] = values
            host = self.host(inp)
            outcome = host.run()
            self.assertEqual(outcome['status'], 'stopped', outcome['state'])
            delivered = [e for e in self.store.events(name) if e['kind'] == 'context_delivery']
            contexts = [json.loads(self.store.artifact(e['inputs'][0])['messages'][-1]['content']) for e in delivered]
            self.assertEqual(contexts[2]['observation']['content']['content'], 5. if name == 'low' else 10.)
            self.assertFalse(contexts[2]['observation']['truncated'])
            changes.append(contexts[3]['last_receipt']['execution_id'])
            candidate = next(e for e in self.store.events(name) if e['kind'] == 'candidate')
            changes[-1] = self.store.artifact(candidate['outputs'][0])['changes']
            self.assertEqual(len(delivered), 5)
        self.assertNotEqual(changes[0], changes[1])
        from extensions.convergence.implementation import ObservingAdapter
        from extensions.convergence.contracts import AdapterParameters
        host = self.host(development('bad-response'))
        adapter = ObservingAdapter(AdapterParameters())
        with patch.object(adapter, 'decode', side_effect=ValueError('INJECTED_PARSE_ERROR')):
            outcome = host.run(adapter)
        self.assertEqual(outcome['status'], 'failed')
        raw = next(e for e in self.store.events('bad-response') if e['kind'] == 'model_raw_response')
        self.assertIn('tool_id', self.store.artifact(raw['outputs'][0])['raw'])
        failed = self.store.lookup('bad-response', 'model-0')
        self.assertEqual(self.store.artifact(json.loads(failed['receipt'])['output'])['response'], raw['outputs'][0])

    def test_02_candidate_effective_input_and_noncontrol_parameter(self):
        from extensions.convergence.implementation import LimitedBackend
        inp = development()
        inp['policy']['backend'] = binding('backend.limited_synthetic', 'convergence.empty')
        host = self.host(inp)
        LimitedBackend.executions.clear()
        bad = self.call(host, 'simulation.run', dict(candidate_id='bad', changes={'controller.command_m': 0.31}))
        self.assertEqual(bad['execution_status'], 'rejected', bad)
        self.assertIn('0.305', bad['error'])
        self.assertEqual(LimitedBackend.executions, [])
        good = self.call(host, 'simulation.run', dict(candidate_id='good', changes={'controller.command_m': 0.30, 'structure.response_fraction': 0.8}))
        self.done(good)
        self.assertEqual(LimitedBackend.checks[-1], LimitedBackend.executions[-1])
        self.assertEqual(LimitedBackend.executions[-1]['robot']['structure']['data']['response_fraction'], 0.8)
        self.done(self.call(host, 'evaluation.run', dict(result=good['output'], execution_id=good['execution_id'])))

    def test_03_stateful_search_resume_pending_and_sealed_calls(self):
        from tools.platform_search import run_search, _save
        def make(name):
            inp = development(name)
            inp['policy']['search'] = binding('search.stateful', 'convergence.search', dict(candidates=[0.30, 0.304]))
            return self.host(inp)
        normal = run_search(make('normal'))
        host = make('interrupted')
        def interrupt_after_last_proposal(h, saved):
            _save(h, saved)
            if saved['pending'] and saved['pending']['index'] == 1:
                raise InterruptedError('after proposal committed')
        with patch('tools.platform_search._save', side_effect=interrupt_after_last_proposal):
            with self.assertRaises(InterruptedError):
                run_search(host)
        original = host.invoke
        def interrupt_after_evaluation(value, **kw):
            result = original(value, **kw)
            if value['request_id'] == 'search-1-evaluation':
                raise InterruptedError('after sealed evaluation')
            return result
        with patch.object(host, 'invoke', side_effect=interrupt_after_evaluation):
            with self.assertRaises(InterruptedError):
                run_search(host)
        used = self.store.remaining('interrupted')['used']
        resumed = run_search(host)
        self.assertEqual(normal['algorithm'], resumed['algorithm'])
        self.assertEqual([(t['candidate'], t['score']) for t in normal['trials']],
                         [(t['candidate'], t['score']) for t in resumed['trials']])
        self.assertEqual(used, self.store.remaining('interrupted')['used'])

    def test_04_precise_tool_versions_and_legacy_normalization(self):
        for version, expected in [('1.0.0', 3.), ('2.0.0', 6.)]:
            inp = development('version-' + version)
            inp['policy']['tool_bindings']['analysis.versioned_value'] = version
            host = self.host(inp)
            good = self.call(host, 'analysis.versioned_value', dict(value=3.), version=version)
            self.assertEqual(self.done(good)['value'], expected)
            other = '2.0.0' if version == '1.0.0' else '1.0.0'
            bad = self.call(host, 'analysis.versioned_value', dict(value=3.), version=other)
            self.assertIn('VERSION_NOT_GRANTED', bad['error'])
            visible = [r for r in host.discover() if r['extension_id'] == 'analysis.versioned_value' and r['executable']]
            self.assertEqual([r['version'] for r in visible], [version])
        old = reference_input('old')
        self.assertIn('analysis.vector_norm', compile_input(old)['normalization']['legacy_tools'])
        old['policy']['allowed_tools'].append('analysis.versioned_value')
        self.assertIn('policy.tool_bindings.analysis.versioned_value', str(report(old)['errors']))

    def test_05_plugin_dependencies_semantic_compatibility(self):
        host = self.host(development(terminal=True))
        host.reg.add(replace(host.reg.get('analysis.vector_norm'), extension_id='analysis.unused'))
        self.assertTrue(host.compatibility()['compatible'])
        paths = [ROOT / 'extensions/convergence/unrelated.txt', ROOT / 'docs/convergence_unrelated.tmp']
        try:
            for path in paths:
                path.write_text('irrelevant', encoding='utf8')
            self.assertTrue(host.compatibility()['compatible'])
        finally:
            for path in paths:
                path.unlink()
        original = __import__('tools.platform_registry', fromlist=['file_hash']).file_hash
        def changed(path):
            return 'changed' if str(path).endswith('convergence/implementation.py') or str(path).endswith('convergence\\implementation.py') else original(path)
        with patch('tools.platform_registry.file_hash', side_effect=changed):
            self.assertFalse(host.compatibility()['compatible'])
        # Same channel, new controller identity, no backend name allow-list edit.
        reg = registry()
        reg.add(replace(reg.get('controller.length_reference'), extension_id='controller.same_contract'))
        inp = development('semantic', terminal=True)
        inp['policy']['controller']['extension_id'] = 'controller.same_contract'
        self.assertTrue(report(inp, reg)['executable'])
        inp['task']['observations'][0]['frame'] = 'world'
        self.assertFalse(report(inp, reg)['executable'])

    def test_06_workers_parallel_common_host_accounting_and_cancel(self):
        from tools.platform_workers import Coordinator
        host = self.host()
        receipt = self.call(host, 'simulation.run')
        self.done(receipt)
        coordinator = Coordinator(host)
        def order(name, worker, tools, delay=0.8):
            return WorkOrder(work_id=name, goal='fixed saved evidence', worker=binding(worker, 'convergence.worker', dict(delay_s=delay)),
                input_snapshot=receipt['output'], base_candidate='baseline', allowed_tools=tools,
                budget=budget(tool_calls=len(tools), worker_calls=0, wall_s=15.), timeout_s=10., output_contract='WorkerOutput@2.0.0')
        before = self.store.remaining()['used']
        for args in [('math', 'worker.math', ['evidence.read', 'analysis.vector_norm']), ('inventory', 'worker.inventory', ['evidence.read'])]:
            self.assertEqual(coordinator.submit(order(*args)).status, 'running')
        end = time.monotonic() + 20
        while time.monotonic() < end:
            rows = [coordinator.collect(n) for n in ('math', 'inventory')]
            if all(r.status in ('completed', 'failed') for r in rows):
                break
            time.sleep(0.05)
        self.assertEqual([r.status for r in rows], ['completed', 'completed'], rows)
        outputs = [self.store.artifact(r.result) for r in rows]
        self.assertLess(max(o['started_at'] for o in outputs), min(o['ended_at'] for o in outputs))
        self.assertNotEqual(outputs[0]['result']['contract'], outputs[1]['result']['contract'])
        for name in ('math', 'inventory'):
            self.assertEqual(coordinator.accept(name).status, 'accepted')
        used = self.store.remaining()['used']
        self.assertEqual(used['tool_calls'] - before['tool_calls'], 3)
        self.assertEqual(used['worker_calls'] - before['worker_calls'], 2)
        self.assertEqual(self.store.remaining(host.run_id)['used']['tool_calls'], used['tool_calls'])
        child = Host(self.root, 'fixture-work-math', actor='worker:math')
        denied = self.call(child, 'analysis.vector_norm', dict(values_m=[3., 4.]))
        self.assertIn('BUDGET_EXHAUSTED', denied['error'])
        self.assertTrue(any(e['request_id'] == 'norm' for e in self.store.events('fixture-work-math')))
        self.assertEqual(coordinator.submit(order('cancel', 'worker.inventory', ['evidence.read'], 5.)).status, 'running')
        self.assertEqual(coordinator.cancel('cancel').status, 'cancelled')

    def test_07_identical_content_multiple_executions_and_memory_scope(self):
        host = self.host()
        a = self.call(host, 'simulation.run', dict(candidate_id='a'))
        b = self.call(host, 'simulation.run', dict(candidate_id='b'))
        self.done(a); self.done(b)
        self.assertEqual(a['output'], b['output'])
        self.assertNotEqual(a['execution_id'], b['execution_id'])
        bad = self.call(host, 'evaluation.run', dict(result=a['output']))
        self.assertIn('SELECTION_REQUIRED', bad['error'])
        for receipt in (a, b):
            self.done(self.call(host, 'evaluation.run', dict(result=receipt['output'], execution_id=receipt['execution_id'])))
        for name, model in [('matching', host.model_identity()), ('wrong', 'other-physics-model')]:
            entry = MemoryEntry(memory_id=name, summary=name, kind='direct_observation', task_family='task.signal_hold',
                task_version='1.0.0', backend='backend.reference', model_id=model, sources=[a['output']])
            self.store.save_memory(host.run_id, entry)
        self.assertEqual([m['memory_id'] for m in host.context()['memory']], ['matching'])
        events = [e for e in self.store.events(host.run_id) if e['kind'] == 'evaluation']
        self.assertEqual([e['candidate_id'] for e in events], ['a', 'b'])

    def test_08_complete_tasks_debug_and_legacy_configuration(self):
        from tools.platform_config import load
        from tools.platform_models import payload_for
        for name in ('hold', 'terminal'):
            inp = load(ROOT / ('configs/platform/convergence/' + name + '.yaml'))
            host = self.host(inp)
            self.assertEqual(host.run()['status'], 'stopped')
            self.assertTrue(any(e['kind'] == 'evaluation' for e in self.store.events(host.run_id)))
            before = self.store.db.read_bytes()
            host.context(); host.discover(); host.compatibility(); self.store.events(host.run_id); payload_for(host)
            self.assertEqual(before, self.store.db.read_bytes())
        self.assertTrue(report(load(ROOT / 'configs/platform/signal_hold/session.yaml'))['executable'])
        self.assertEqual(self.store.remaining()['used']['backend_solves'], 0)
        self.assertEqual(self.store.remaining()['used']['model_calls'], 0)


if __name__ == '__main__':
    unittest.main()
