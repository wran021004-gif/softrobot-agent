"""Focused task identity, truth consistency and contract-driven execution tests."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
import yaml

from metrics.reach import evaluate_reach
from schemas.task_contract import TaskContract
from tests.test_trace import FixtureMatlab
from tests.test_gate_semantics import NegativeClearanceMatlab
from tools.artifact_tools import file_hash
from tools.harness import run_reach
from tools.spec_tools import ROOT, load_yaml
from tools.task_contract_tools import resolve_task_contract
from tools.trace_tools import read_trace

DEV = ROOT / 'tests/fixtures/reach_window_dev'
PROPOSAL = ROOT / 'proposals/benchmark/reach_window_v1'


def evaluate_development_probe(tip, task, window=None):
    """Explicit software test evaluator: preserve evaluation and record dispatch."""
    return {**evaluate_reach(tip, task, window), 'contract_evaluator_probe': True}


evaluate_development_probe.supported_task_types = ('reach_window',)


class TaskContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'runs')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def copy_development(self):
        package = self.root / 'package'
        shutil.copytree(DEV, package)
        return package

    def test_frozen_resolves_authoritative_sources_without_values_in_index(self):
        resolved = resolve_task_contract(ROOT / 'tasks/reach_free')
        self.assertEqual(resolved.contract.status, 'FROZEN')
        self.assertEqual(resolved.contract.benchmark_id, 'tendon_v1')
        self.assertEqual(resolved.task.environment_id, resolved.environment.environment_id)
        self.assertEqual(resolved.task.target_m, [.25, 0., .15])
        self.assertEqual(resolved.grammar['family_name'], 'tendon_driven_continuum')
        self.assertIs(resolved.evaluator, evaluate_reach)
        self.assertEqual(resolved.run_settings.steps, 1000)
        for key, path in resolved.source_paths.items():
            self.assertEqual(resolved.source_hashes[key], file_hash(path))
        self.assertFalse({'target_m', 'position_error_max_m', 'gravity', 'design', 'optimization_bounds'} & TaskContract.model_fields.keys())
        self.assertNotIn('task', resolved.reference_view())

    def test_proposal_resolves_read_only_and_cannot_execute(self):
        resolved = resolve_task_contract(PROPOSAL)
        self.assertEqual(resolved.contract.status, 'PROPOSED_NOT_APPROVED')
        self.assertIsNone(resolved.contract.benchmark_id)
        self.assertIsNone(resolved.environment)
        self.assertIsNone(resolved.evaluator)
        self.assertTrue(resolved.unresolved)
        run = run_reach(task_package=PROPOSAL, run_root=self.root, matlab_factory=lambda: self.fail('Proposal started MATLAB'))
        self.assertEqual(run.record.task_contract_status, 'PROPOSED_NOT_APPROVED')
        self.assertNotEqual(run.record.final_status, 'PASS')
        self.assertFalse((run.path / 'mujoco_result.json').exists())

    def test_development_cannot_claim_frozen(self):
        self.assertEqual(resolve_task_contract(DEV).contract.status, 'DEVELOPMENT_ONLY')
        package = self.copy_development()
        value = load_yaml(package / 'contract.yaml')
        value['status'] = 'FROZEN'
        (package / 'contract.yaml').write_text(yaml.safe_dump(value))
        with self.assertRaisesRegex(ValueError, 'FROZEN.*development'):
            resolve_task_contract(package)

    def test_environment_identity_and_evaluator_consistency(self):
        package = self.copy_development()
        path = package / 'environment.yaml'
        original = path.read_text()
        env = load_yaml(path)
        env['environment_id'] = 'different_task'
        path.write_text(yaml.safe_dump(env))
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            resolve_task_contract(package)
        path.write_text(original)
        contract = load_yaml(package / 'contract.yaml')
        contract['evaluator'] = 'tools.spec_tools.load_task'
        (package / 'contract.yaml').write_text(yaml.safe_dump(contract))
        with self.assertRaisesRegex(ValueError, 'evaluator.*task_type'):
            resolve_task_contract(package)

    def test_harness_contract_artifact_trace_and_baseline(self):
        run = run_reach(run_root=self.root, matlab_factory=FixtureMatlab)
        self.assertEqual(run.record.final_status, 'TASK_FAILED')
        self.assertEqual(run.record.task_contract_id, 'reach_free_v1')
        self.assertEqual(run.record.task_contract_status, 'FROZEN')
        self.assertEqual(run.record.task_contract_hash, file_hash(run.path / 'task_contract.yaml'))
        resolved = json.loads((run.path / 'task_contract_resolved.json').read_text())
        with zipfile.ZipFile(run.path / 'source_snapshot.zip') as archive:
            for key, path in resolved['source_paths'].items():
                self.assertEqual(hashlib.sha256(archive.read(path)).hexdigest(), resolved['source_hashes'][key])
        result = json.loads((run.path / 'mujoco_result.json').read_text())
        self.assertEqual(result['metrics']['position_error_m'], 0.17116166894090315)
        events = read_trace(run.path / 'trace.jsonl')
        operations = [event.operation for event in events]
        self.assertLess(operations.index('task_contract_resolved'), operations.index('task_loaded'))
        self.assertLess(operations.index('task_contract_resolved'), operations.index('environment_validated'))

    def test_referenced_protocol_and_evaluator_are_executed(self):
        package = self.copy_development()
        settings = load_yaml(ROOT / 'configs/run.yaml')
        settings['steps'] = 2
        (package / 'short_run.yaml').write_text(yaml.safe_dump(settings))
        contract = load_yaml(package / 'contract.yaml')
        contract['run_settings_source'] = './short_run.yaml'
        contract['evaluator'] = 'tests.test_task_contracts.evaluate_development_probe'
        (package / 'contract.yaml').write_text(yaml.safe_dump(contract))
        run = run_reach(task_package=package, run_root=self.root, matlab_factory=NegativeClearanceMatlab)
        result = json.loads((run.path / 'mujoco_result.json').read_text())
        self.assertEqual(result['metrics']['steps'], 2)
        self.assertTrue(result['metrics']['contract_evaluator_probe'])
        self.assertEqual(run.record.task_contract_status, 'DEVELOPMENT_ONLY')
        resolved = json.loads((run.path / 'task_contract_resolved.json').read_text())
        self.assertEqual(resolved['source_hashes']['run_settings_source'], file_hash(package / 'short_run.yaml'))
