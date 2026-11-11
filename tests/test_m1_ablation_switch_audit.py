"""Offline audit of frozen M1 control gates; fixtures are not scientific evidence.

Requires M1_AUDIT_CORE pointing to the unchanged 7f034a60 Core checkout and
M1_AUDIT_FULL_CONFIG pointing to the existing original M1 leaf configuration.
No Host/Store/Study is created. Network, subprocesses and MuJoCo imports fail.
"""
import builtins
from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


if not all(os.environ.get(k) for k in ('M1_AUDIT_CORE', 'M1_AUDIT_FULL_CONFIG')):
    raise unittest.SkipTest('Set the two explicit frozen M1 audit source paths')
CORE = Path(os.environ['M1_AUDIT_CORE']).resolve()
FULL = Path(os.environ['M1_AUDIT_FULL_CONFIG']).resolve()
sys.path.insert(0, str(CORE))
sys.dont_write_bytecode = True


original_import = builtins.__import__


def no_mujoco(name, *args, **kwargs):
    if name == 'mujoco' or name.startswith('mujoco.'):
        raise AssertionError('MuJoCo import forbidden in offline audit')
    return original_import(name, *args, **kwargs)


from tools.research import analysis, config, conditions, feedback, physical_replay
from tools.research.contracts import AnalysisRequest, ControlSeedRequest, PhysicalReplayRequest
from tools.research.nonlinear_capability import T1, T1_OPERATION
from tools.platform_registry import registry


DIRECT = 'mujoco_direct_control_v1'
REF = dict(artifact_id='0' * 64, media_type='application/json')


def setUpModule():
    global offline_patches
    offline_patches = ExitStack()
    offline_patches.enter_context(patch('subprocess.Popen', side_effect=AssertionError('No subprocess')))
    offline_patches.enter_context(patch('socket.socket.connect', side_effect=AssertionError('No network')))
    offline_patches.enter_context(patch('builtins.__import__', side_effect=no_mujoco))


def tearDownModule():
    offline_patches.close()


class AdmissionReached(Exception):
    """Stop at the first candidate check, before scientific preparation."""


class M1SwitchAudit(unittest.TestCase):
    @classmethod
    def resolve_variant(cls, **edits):
        leaf = json.loads(FULL.read_text(encoding='utf-8'))
        # Normalize only the two explicitly authorized final Full grants and
        # implementation identity; retain every scientific source reference.
        leaf['base_commit'] = '7f034a60f1ea0be5ac3174c5b6c8908a8f56dd40'
        leaf['budgets']['provider_requests'] = 73
        leaf['native_control_limits']['knots_s'] = 30
        leaf.update(edits)
        original_read = config.read

        def read(path):
            return deepcopy(leaf) if Path(path).resolve() == FULL else original_read(path)

        with patch.object(config, 'read', side_effect=read):
            return config.resolve(FULL)

    @classmethod
    def setUpClass(cls):
        cls.full = cls.resolve_variant()

    def request(self, operation):
        return AnalysisRequest.model_validate(dict(
            candidate=REF, operation=operation, model_source='mujoco',
            operating_point='standardized_initial_pretension',
            protocol=self.full['analysis_protocol'],
            control_optimization=dict(source=REF, settings=dict(
                version='local_control_search_v2', method='response',
                correction_window_s=[0, .6], knots_s=[0, .3, .6],
                coefficient_limit_n=8, difference_step_n=.08,
                initial_radius_n=2, minimum_radius_n=.0008,
                iterations=100, evaluation_requests=180))))

    def call_analysis(self, spec, operation):
        host = SimpleNamespace(run_id='offline-fixture', store=Mock())
        host.store.lookup.return_value = None
        with patch.object(analysis, 'state', return_value=dict(spec=spec)), \
                patch.object(analysis, 'verify_candidate', side_effect=AdmissionReached), \
                patch.object(analysis, 'calculate', side_effect=AssertionError('No calculation')):
            return analysis.dispatch(host, self.request(operation), 'offline', guard=Mock())

    def test_full_sources_resolve_without_execution(self):
        self.assertEqual([c['condition_id'] for c in self.full['task_conditions']],
                         ['positive_high', 'negative_low', 'central_high'])
        self.assertEqual(self.full['budgets']['provider_requests'], 73)
        self.assertEqual(self.full['native_control_limits']['knots_s'], 30)
        self.assertEqual(self.full['configuration']['task']['timing']['duration_s'], .6)
        self.assertNotIn('mujoco', sys.modules)

    def test_t1_grant_removal_does_not_disable_direct(self):
        methods = deepcopy(self.full['mathematical_methods'])
        del methods[T1]
        spec = self.resolve_variant(mathematical_methods=methods)
        result = self.call_analysis(spec, T1_OPERATION)
        self.assertEqual(result['reason'], 'EXPLICIT_FROZEN_MATHEMATICAL_METHOD_AUTHORIZATION_REQUIRED')
        with self.assertRaises(AdmissionReached):
            self.call_analysis(spec, DIRECT)

    def test_direct_is_not_a_recognized_method_grant(self):
        methods = {**self.full['mathematical_methods'], DIRECT: 'offline fixture'}
        with self.assertRaisesRegex(ValueError, 'EXPLICIT_VERSIONED_MATHEMATICAL_METHOD_AUTHORIZATION_REQUIRED'):
            self.resolve_variant(mathematical_methods=methods)

    def test_coarse_analysis_gate_blocks_both_before_candidate_or_worker(self):
        capabilities = [c for c in self.full['capabilities'] if c != 'analysis']
        spec = self.resolve_variant(capabilities=capabilities)
        self.assertEqual(spec['capabilities'], ['control_correction', 'physical_replay'])
        result = self.call_analysis(spec, T1_OPERATION)
        self.assertEqual(result['status'], 'not_applicable')
        with self.assertRaisesRegex(ValueError, 'ANALYSIS_CAPABILITY_REQUIRED'):
            self.call_analysis(spec, DIRECT)
        for key in ('task_conditions', 'family_space', 'configuration', 'knowledge',
                    'runtime', 'budgets', 'confirmation', 'allowed_plan_actions'):
            self.assertEqual(spec[key], self.full[key], key)
        self.assertIn('physical_replay', spec['allowed_plan_actions'])
        self.assertIn('select', spec['allowed_plan_actions'])
        evaluator = spec['configuration']['task']['evaluator']
        registry().get(evaluator['extension_id'], evaluator['version'], 'evaluator').resolve()

    def test_baseline_and_probe_share_method_dispatch_without_gate(self):
        # Mock the immediate delegates: execute no initialization or probe.
        host = SimpleNamespace()
        for method, delegate in [('baseline', '_seed_control'), ('physical_response', 'guided_seed')]:
            with self.subTest(method=method), \
                    patch.object(physical_replay, 'state', return_value=dict(numerical_s=0)), \
                    patch.object(physical_replay, 'update'), \
                    patch.object(physical_replay, delegate, return_value='delegate-reached') as target:
                request = ControlSeedRequest(candidate=REF, method=method)
                self.assertEqual(physical_replay.seed_control(host, request, 'offline', plan=Mock()),
                                 'delegate-reached')
                target.assert_called_once()

    def test_invented_probe_method_switch_is_rejected(self):
        # Negative parser test only: no JSON with this unsupported field is saved.
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_CONFIGURATION_FIELD'):
            self.resolve_variant(control_initialization_methods=['baseline'])

    def test_replay_admits_explicit_baseline_without_analysis(self):
        spec = deepcopy(self.full)
        spec['capabilities'].remove('analysis')
        host = SimpleNamespace(run_id='offline-fixture', store=Mock())
        host.store.artifact.return_value = dict(source_kind='explicit_control_schedule_v1',
            task_acceptance='unmeasured', provenance=dict(fixture=True), trajectory={})
        with patch.object(physical_replay, 'guard'), \
                patch.object(physical_replay, 'state', return_value=dict(spec=spec)), \
                patch.object(physical_replay, 'verify_candidate',
                             return_value=dict(configuration=spec['configuration'])), \
                patch.object(physical_replay, 'binding') as binding, \
                patch('tools.research.budget.capacity', return_value=dict(admitted=1)), \
                patch.object(feedback, 'experiment_preflight', side_effect=AdmissionReached):
            with self.assertRaises(AdmissionReached):
                physical_replay.dispatch(host, PhysicalReplayRequest(candidate=REF, source=REF), 'offline')
            binding.assert_called_once()

    def test_joint_select_eligibility_uses_receipts_not_analysis_grant(self):
        for capabilities in [self.full['capabilities'], ['control_correction', 'physical_replay']]:
            spec = {**self.full, 'capabilities': capabilities}
            with self.subTest(capabilities=capabilities), \
                    patch('tools.research.state.state', return_value=dict(spec=spec)), \
                    patch.object(conditions, 'joint_assessment', return_value=dict(fixture=True)) as assess:
                # The mocked receipt assessment is not a physical success result.
                result = feedback.eligibility(SimpleNamespace(), [REF, REF, REF], selection=True)
                self.assertTrue(result['eligible'])
                assess.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
