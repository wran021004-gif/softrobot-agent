"""Focused platform tests for the public GVS model and tools."""

import json
import sys
import unittest
from uuid import uuid4

from examples.platform_fixtures import project
from examples.platform_tendon_family import example_design, design_space, session
from extensions.tendon_family.contracts import (
    GVSDescription,
    GVSDynamicsRequest,
    GVSDynamicsResult,
)
from schemas.platform_math import DynamicSystem
from tools.platform_host import Host
from tools.platform_models import OfflineAdapter, input_for
from tools.platform_registry import registry
from tools.platform_store import Store
from tools.spec_tools import ROOT


class GVSPlatformTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex
        self.root = ROOT / 'runs/gvs_platform_tests' / suffix
        self.store = Store(self.root)
        self.store.create(project())
        self.reg = registry()
        design = example_design()
        self.input = session('family_mujoco', design, design_space(design))
        self.input['run_id'] = 'gvs-' + suffix
        self.input['task']['environment']['data']['external_forces'] = []
        self.input['policy']['budget']['backend_solves'] = 0
        self.input['policy']['budget']['tool_calls'] = 4
        self.input['policy']['timeout_s'] = 10.0
        self.input['policy']['model']['max_turns'] = 3
        self.input['policy']['tool_bindings'].update({
            'dynamics.gvs_describe': '1.0.0',
            'dynamics.gvs_evaluate': '1.0.0',
            'dynamics.gvs_build_system': '1.0.0',
            'linearization.linearize': '1.0.0',
            'control.lqr_describe': '1.0.0',
            'session.control': '1.0.0',
        })
        self.host = Host(self.root, self.input['run_id'], reg=self.reg)
        self.host.create(self.input)
        self.request = {
            'state': {
                'q': [0.15, 0.03, -0.1, 0.02, 0.08, -0.02, 0.12, 0.04],
                'qdot': [0.0] * 8,
            },
            'input': {
                'tendon_tensions_n': {
                    tendon['id']: 0.2
                    for tendon in self.input['robot']['structure']['data']['tendons']
                },
            },
            'samples_per_segment': 7,
        }

    def test_unique_registration_and_honest_capabilities(self):
        for extension_id in (
            'model.gvs',
            'dynamics.gvs_describe',
            'dynamics.gvs_evaluate',
            'dynamics.gvs_build_system',
            'linearization.linearize',
            'control.lqr_describe',
        ):
            matches = [
                definition
                for definition in self.reg.extensions.values()
                if definition.extension_id == extension_id
            ]
            expected = 2 if extension_id in {
                'dynamics.gvs_evaluate',
                'dynamics.gvs_build_system',
                'linearization.linearize',
                'control.lqr_describe',
            } else 1
            self.assertEqual(len(matches), expected)
        model = self.reg.get('model.gvs', '1.0.0', 'dynamics_model')
        self.assertEqual(
            model.capabilities['mathematical_model']['capabilities'],
            {
                'kinematics': True,
                'statics': True,
                'dynamics': True,
                'linearization': False,
                'gradients': True,
            },
        )
        self.assertEqual(
            model.capabilities['mathematical_model']['representations'],
            ['dynamic_system'],
        )
        self.reg.get('linearizer.casadi', '1.0.0', 'linearizer')
        self.reg.get('controller.lqr', '1.0.0', 'controller')
        self.assertIs(
            self.reg.get('dynamics.gvs_describe').output_schema,
            GVSDescription,
        )
        evaluate = self.reg.get('dynamics.gvs_evaluate')
        self.assertIs(evaluate.input_schema, GVSDynamicsRequest)
        self.assertIs(evaluate.output_schema, GVSDynamicsResult)

    def test_host_evaluation_and_llm_visibility_use_zero_backend_solves(self):
        tools = {tool['extension_id'] for tool in input_for(self.host).tools}
        self.assertIn('dynamics.gvs_describe', tools)
        self.assertIn('dynamics.gvs_evaluate', tools)
        self.assertIn('dynamics.gvs_build_system', tools)
        self.assertIn('linearization.linearize', tools)
        self.assertIn('control.lqr_describe', tools)

        receipt = self.host.invoke({
            'request_id': 'gvs-evaluate',
            'tool_id': 'dynamics.gvs_evaluate',
            'tool_version': '1.0.0',
            'arguments': self.request,
            'reason': 'Evaluate frozen-robot variable-strain dynamics.',
        })
        self.assertEqual(receipt['execution_status'], 'completed', receipt)
        self.assertEqual(receipt['charged']['backend_solves'], 0)
        result = self.store.artifact(receipt['output'])
        self.assertEqual(len(result['coordinate_order']), 8)
        self.assertEqual(len(result['qdd']), 8)
        self.assertEqual(
            result['dynamics_equation'],
            'M*qdd+c+elastic+damping=tendon+gravity',
        )
        self.assertEqual(
            self.store.remaining(self.host.run_id)['used']['backend_solves'], 0
        )
        self.assertNotIn('mujoco', sys.modules)
        self.assertNotIn('matlab.engine', sys.modules)

    def test_public_system_export_preserves_explicit_context(self):
        x0 = self.request['state']['q'] + self.request['state']['qdot']
        u0 = [0.2] * len(self.request['input']['tendon_tensions_n'])
        receipt = self.host.invoke({
            'request_id': 'gvs-build-system',
            'tool_id': 'dynamics.gvs_build_system',
            'tool_version': '1.0.0',
            'arguments': {'context': {
                'x0': x0,
                'u0': u0,
                'scene': self.input['task']['environment'],
            }},
            'reason': 'Export the explicit GVS continuous operating point.',
        })
        self.assertEqual(receipt['execution_status'], 'completed', receipt)
        system = DynamicSystem.model_validate(self.store.artifact(receipt['output']))
        self.assertEqual((system.x0, system.u0), (x0, u0))
        self.assertEqual((len(system.x0), len(system.u0)), (16, 6))
        self.assertEqual(system.dynamics.contract, 'family.gvs_continuous_dynamics')
        self.assertEqual(receipt['charged']['backend_solves'], 0)

    def test_offline_adapter_observes_gvs_description_then_stops(self):
        outcome = self.host.run(OfflineAdapter([
            {
                'tool_id': 'dynamics.gvs_describe',
                'arguments': {},
                'reason': 'Discover the frozen robot GVS coordinates.',
            },
            {
                'tool_id': 'session.control',
                'arguments': {
                    'status': 'stopped',
                    'reason': 'GVS coordinates received.',
                },
                'reason': 'Stop after observing the GVS description.',
            },
        ]))
        self.assertEqual(outcome['status'], 'stopped', outcome['state'])
        deliveries = [
            event
            for event in self.store.events(self.host.run_id)
            if event['kind'] == 'context_delivery'
        ]
        self.assertEqual(len(deliveries), 2)
        second_input = self.store.artifact(deliveries[1]['inputs'][0])
        context = json.loads(second_input['messages'][-1]['content'])
        observation = context['observation']
        self.assertEqual(
            observation['receipt']['tool_id'], 'dynamics.gvs_describe'
        )
        self.assertEqual(
            observation['content']['coordinates'][0]['name'],
            'near.kappa_y_0',
        )
        self.assertEqual(
            observation['receipt']['charged']['backend_solves'], 0
        )


if __name__ == '__main__':
    unittest.main()
