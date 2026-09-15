"""Three focused host scenarios; counted synthetic backend, zero physical/API calls."""
import json
import unittest
from dataclasses import replace
from typing import Literal
from unittest.mock import patch
from uuid import uuid4

from examples.platform_fixtures import project, reference_input
from extensions.reference.implementation import ReferenceBackend
from schemas.common import Contract
from schemas.platform import EvaluationResult, ToolReceipt
from tools.platform_host import Host
from tools.platform_registry import registry
from tools.platform_store import Store, plain
from tools.spec_tools import ROOT


class MathematicalResult(Contract):
    contract_version: Literal['3.0.0'] = '3.0.0'
    validity: str
    solver_status: str
    norm_m: float


class PublicFixTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'runs/platform_public_fixes' / uuid4().hex
        self.store = Store(self.root)
        config = project()
        config['budget']['backend_solves'] = 10
        self.store.create(config)
        self.reg = registry()
        backend = self.reg.get('backend.reference')
        # Charge synthetic runs as solves to exercise the real common ledger.
        self.reg.extensions[(backend.extension_id, backend.version)] = replace(backend,
            capabilities={**backend.capabilities, 'reference': False}, resources=('reference_device',))
        self.runs = 0
        original = ReferenceBackend.run

        def counted(backend, **kwargs):
            self.runs += 1
            result = original(backend, **kwargs)
            folder = kwargs['folder']
            folder.mkdir(parents=True)
            (folder / 'trajectory.json').write_text(json.dumps(plain(result)), encoding='utf8')
            return result

        self.counter = patch.object(ReferenceBackend, 'run', counted)
        self.counter.start()
        self.addCleanup(self.counter.stop)

    def host(self):
        host = Host(self.root, 'fixture', reg=self.reg)
        inp = reference_input('fixture')
        inp['policy']['budget']['backend_solves'] = 10
        host.create(inp)
        return host

    def call(self, host, tool, args=None, request=None, cache='reuse'):
        result = host.invoke(dict(tool_id=tool, request_id=request or uuid4().hex,
            arguments=args or {}, reason='公共接口两项修复：离线验收', cache=cache))
        self.assertEqual(result['execution_status'], 'completed', result)
        return result

    def evaluation(self, host, simulation, expected):
        receipt = self.call(host, 'evaluation.run', dict(result=simulation['output'], execution_id=simulation['execution_id']))
        outcome = self.store.artifact(receipt['output'])
        self.assertEqual(receipt['analysis_status'], 'valid')
        self.assertIs(receipt['task_success'], expected)
        self.assertEqual(outcome['source_execution_id'], simulation['execution_id'])
        self.assertEqual(outcome['original_execution_id'], simulation['original_execution_id'])
        self.assertEqual(outcome['candidate_id'], 'baseline')
        return receipt

    def test_01_result_contract(self):
        math = self.reg.get('analysis.vector_norm')
        self.reg.extensions[(math.extension_id, math.version)] = replace(math, output_schema=MathematicalResult)
        evaluation = self.reg.get('evaluation.run')
        # Optional caching also must preserve EvaluationResult's own version.
        self.reg.extensions[(evaluation.extension_id, evaluation.version)] = replace(evaluation, cache=True)
        host = self.host()
        with patch('extensions.reference.implementation.vector_norm', return_value=dict(
                validity='valid', solver_status='matrix_converged', norm_m=5.0)) as calculate:
            first = self.call(host, 'analysis.vector_norm', dict(values_m=[3., 4.]))
            cached = self.call(host, 'analysis.vector_norm', dict(values_m=[3., 4.]))
            self.assertEqual(calculate.call_count, 1)
        self.assertFalse(first['cache_hit'])
        self.assertTrue(cached['cache_hit'])
        self.assertEqual(first['output'], cached['output'])
        for receipt in (first, cached):
            self.assertEqual(receipt['result_contract'], 'MathematicalResult')
            self.assertEqual(receipt['result_version'], '3.0.0')
            self.assertEqual(receipt['solver_status'], 'not_run')
            self.assertEqual(receipt['analysis_status'], 'not_assessed')
            self.assertIsNone(receipt['task_success'])
            self.assertEqual(host.observation(receipt)['content']['norm_m'], 5.)
        for command, success in ((0.30, True), (0.35, False)):
            sim = self.call(host, 'simulation.run', dict(changes={'controller.command_m': command}))
            assessed = self.evaluation(host, sim, success)
            reused = self.evaluation(host, sim, success)
            self.assertFalse(assessed['cache_hit'])
            self.assertTrue(reused['cache_hit'])
            self.assertEqual(assessed['output'], reused['output'])
            self.assertEqual(assessed['result_version'], '1.2.0')
            self.assertEqual(reused['result_version'], '1.2.0')
        old_receipt = {k: v for k, v in assessed.items() if k != 'original_execution_id'}
        old_receipt['contract_version'] = '1.1.0'
        self.assertIsNone(ToolReceipt.model_validate(old_receipt).original_execution_id)
        old_result = self.store.artifact(assessed['output'])
        old_result.pop('original_execution_id')
        old_result['contract_version'] = '1.1.0'
        self.assertIsNone(EvaluationResult.model_validate(old_result).original_execution_id)
        self.assertEqual(self.runs, 2)

    def test_02_reuse_provenance_evaluation_accounting_and_reopen(self):
        host = self.host()
        reserved = []
        reserve = host.store.reserve

        def observe_reservation(*args, **kwargs):
            result = reserve(*args, **kwargs)
            reserved.append((json.loads(result[0]['resources']), host.store.remaining()['occupied']))
            return result

        with patch.object(host.store, 'reserve', side_effect=observe_reservation):
            simulations = [self.call(host, 'simulation.run', dict(changes={'controller.command_m': 0.35}),
                request='simulation-' + str(i)) for i in range(3)]
        first = simulations[0]
        self.assertEqual(self.runs, 1)
        self.assertEqual(reserved, [(['reference_device'], {'reference_device': 1}), ([], {}), ([], {})])
        self.assertEqual(len({s['execution_id'] for s in simulations}), 3)
        self.assertEqual(len({s['request_id'] for s in simulations}), 3)
        for i, sim in enumerate(simulations):
            self.assertEqual(sim['cache_hit'], i > 0)
            self.assertEqual(sim['output'], first['output'])
            self.assertEqual(sim['original_execution_id'], first['execution_id'])
            self.assertEqual(sim['solver_status'], 'completed')
            self.assertEqual(sim['charged']['backend_solves'], int(i == 0))
            self.assertEqual(sim['charged']['tool_calls'], 1)
            self.assertGreater(sim['charged']['wall_s'], 0)
            metadata = self.store.session('fixture')['state']['result_executions'][sim['execution_id']]
            self.assertEqual(metadata['request_id'], sim['request_id'])
            self.assertEqual(metadata['original_execution_id'], first['execution_id'])
            effective = self.store.artifact(metadata['candidate_input'])['effective']
            self.assertEqual(effective['policy']['controller']['parameters']['data']['command_m'], 0.35)
            self.evaluation(host, sim, False)
        saved = self.store.session('fixture')['state']['result_executions']
        host = Host(self.root, 'fixture', reg=registry())
        # Restore the same trusted test declaration when opening a new Host.
        host.reg.extensions[('backend.reference', '1.0.0')] = self.reg.get('backend.reference')
        self.assertTrue(host.compatibility()['compatible'])
        self.assertEqual(saved, host.store.session('fixture')['state']['result_executions'])
        for sim in simulations:
            self.evaluation(host, sim, False)
        events = self.store.events('fixture')
        self.assertEqual(len([e for e in events if e['kind'] == 'simulation' and e['status'] == 'started']), 1)
        links = [e for e in events if e['kind'] == 'result_provenance']
        self.assertEqual([e['status'] for e in links], ['produced', 'reused', 'reused'])
        self.assertTrue(all(self.store.artifact(e['outputs'][0])['original_execution_id'] == first['execution_id'] for e in links))
        self.assertEqual(len(list((host.folder / 'executions').glob('*/backend/trajectory.json'))), 1)
        self.assertEqual(self.store.remaining()['used']['backend_solves'], 1)
        self.assertEqual(self.store.remaining()['used']['model_calls'], 0)
        self.assertEqual(self.runs, 1)

    def test_03_explicit_recompute_changed_input_and_idempotency(self):
        host = self.host()
        initial = self.call(host, 'simulation.run', request='initial')
        fresh = self.call(host, 'simulation.run', request='new', cache='new')
        changed = self.call(host, 'simulation.run', dict(changes={'controller.command_m': 0.31}), request='changed')
        self.assertEqual(self.runs, 3)
        self.assertEqual(initial['output'], fresh['output'])
        self.assertNotEqual(changed['output'], fresh['output'])
        for sim in (initial, fresh, changed):
            self.assertFalse(sim['cache_hit'])
            self.assertEqual(sim['original_execution_id'], sim['execution_id'])
            self.assertEqual(sim['charged']['backend_solves'], 1)
        usage, events = self.store.remaining(), self.store.events('fixture')
        self.assertEqual(fresh, self.call(host, 'simulation.run', request='new', cache='new'))
        self.assertEqual(changed, self.call(host, 'simulation.run', dict(changes={'controller.command_m': 0.31}), request='changed'))
        self.assertEqual(usage, self.store.remaining())
        self.assertEqual(events, self.store.events('fixture'))
        self.assertEqual(self.runs, 3)


if __name__ == '__main__':
    unittest.main()
