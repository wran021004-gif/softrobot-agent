"""Focused public-platform tests for PCC kinematics; no simulator solves."""

import json
import sys
import unittest
from uuid import uuid4

from examples.platform_fixtures import project
from examples.platform_tendon_family import example_design, design_space, session
from extensions.tendon_family.contracts import (
    PCCForwardRequest,
    PCCKinematicsResult,
)
from schemas.platform import Binding, Payload, RobotDescription
from tools.platform_host import Host
from tools.platform_models import OfflineAdapter, input_for
from tools.platform_registry import registry
from tools.platform_store import Store
from tools.spec_tools import ROOT


STRAIGHT_REQUEST = {
    'configuration': {
        'segments': {
            'near': {
                'curvature_y_rad_m': 0.0,
                'curvature_z_rad_m': 0.0,
            },
            'far': {
                'curvature_y_rad_m': 0.0,
                'curvature_z_rad_m': 0.0,
            },
        },
    },
    'samples_per_segment': 21,
}


class PCCPlatformTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex
        self.root = ROOT / 'runs/pcc_platform_tests' / suffix
        self.store = Store(self.root)
        self.store.create(project())
        self.reg = registry()

        design = example_design()
        self.input = session(
            'family_mujoco',
            design,
            design_space(design),
        )
        self.input['run_id'] = 'pcc-' + suffix
        self.input['policy']['budget']['backend_solves'] = 0
        self.input['policy']['budget']['tool_calls'] = 3
        self.input['policy']['timeout_s'] = 10.0
        self.input['policy']['model']['max_turns'] = 3
        self.input['policy']['tool_bindings'].update({
            'kinematics.pcc_describe': '1.0.0',
            'kinematics.pcc_forward': '1.0.0',
            'session.control': '1.0.0',
        })

        self.host = Host(
            self.root,
            self.input['run_id'],
            reg=self.reg,
        )
        self.host.create(self.input)

    def test_registry_has_unique_model_and_public_tools(self):
        for extension_id in (
            'model.pcc',
            'kinematics.pcc_describe',
            'kinematics.pcc_forward',
        ):
            matches = [
                definition
                for definition in self.reg.extensions.values()
                if definition.extension_id == extension_id
            ]
            expected = 2 if extension_id == 'kinematics.pcc_forward' else 1
            self.assertEqual(len(matches), expected)

        model = self.reg.get('model.pcc', '1.0.0', 'dynamics_model')
        tool = self.reg.get('kinematics.pcc_forward', '1.0.0', 'tool')

        self.assertEqual(model.binding, 'extensions.tendon_family.pcc:PCCModel')
        self.assertEqual(model.capabilities['physical_input'], 'family.design')
        self.assertEqual(
            model.capabilities['mathematical_model']['capabilities'],
            {
                'kinematics': True,
                'statics': False,
                'dynamics': False,
                'linearization': False,
                'gradients': False,
            },
        )
        self.assertIs(tool.input_schema, PCCForwardRequest)
        self.assertIs(tool.output_schema, PCCKinematicsResult)
        self.assertEqual(
            tool.extension_dependencies,
            (('model.pcc', '1.0.0'),),
        )

    def test_model_pcc_runs_directly(self):
        definition, parameters = self.reg.bind(
            Binding(
                extension_id='model.pcc',
                parameters=Payload(contract='family.pcc_model', data={}),
            ),
            'dynamics_model',
        )
        model = definition.resolve()(parameters)
        request = Payload(
            contract='family.pcc_forward_request',
            data=STRAIGHT_REQUEST,
        )

        payload = model.forward(
            RobotDescription.model_validate(self.input['robot']),
            request,
            self.reg,
        )
        result = self.reg.parse(payload)

        self.assertIsInstance(result, PCCKinematicsResult)
        self.assertAlmostEqual(result.tip.position_m[0], 0.308, places=12)
        self.assertEqual(result.tip.position_m[1:], (0.0, 0.0))

    def test_host_invokes_public_tool_without_backend_solve(self):
        receipt = self.host.invoke({
            'request_id': 'pcc-host-forward',
            'tool_id': 'kinematics.pcc_forward',
            'tool_version': '1.0.0',
            'arguments': STRAIGHT_REQUEST,
            'reason': 'Compute deterministic PCC forward kinematics.',
        })

        self.assertEqual(receipt['execution_status'], 'completed', receipt)
        self.assertEqual(receipt['charged']['backend_solves'], 0)
        result = self.store.artifact(receipt['output'])
        self.assertAlmostEqual(result['tip']['position_m'][0], 0.308, places=12)
        self.assertEqual(result['tip']['position_m'][1:], [0.0, 0.0])
        self.assertEqual(
            self.store.remaining(self.host.run_id)['used']['backend_solves'],
            0,
        )
        self.assertNotIn('mujoco', sys.modules)
        self.assertNotIn('matlab.engine', sys.modules)

    def test_input_for_exposes_public_pcc_tool(self):
        model_input = input_for(self.host)
        tool_ids = {tool['extension_id'] for tool in model_input.tools}

        self.assertIn('kinematics.pcc_describe', tool_ids)
        self.assertIn('kinematics.pcc_forward', tool_ids)

        receipt = self.host.invoke({
            'request_id': 'pcc-describe',
            'tool_id': 'kinematics.pcc_describe',
            'tool_version': '1.0.0',
            'arguments': {},
            'reason': 'Discover the frozen robot PCC coordinates.',
        })
        self.assertEqual(receipt['execution_status'], 'completed', receipt)
        description = self.store.artifact(receipt['output'])
        self.assertEqual(
            [item['segment'] for item in description['segments']],
            ['near', 'far'],
        )
        self.assertEqual(
            description['curvature_semantics'],
            'actual_total_curvature',
        )

    def test_offline_adapter_completes_two_turn_pcc_loop(self):
        outcome = self.host.run(OfflineAdapter([
            {
                'tool_id': 'kinematics.pcc_forward',
                'arguments': STRAIGHT_REQUEST,
                'reason': 'Compute the straight PCC configuration.',
            },
            {
                'tool_id': 'session.control',
                'arguments': {
                    'status': 'stopped',
                    'reason': 'PCC result received.',
                },
                'reason': 'Stop after observing the PCC result.',
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
        second_context = json.loads(second_input['messages'][-1]['content'])
        observation = second_context['observation']

        self.assertEqual(
            observation['receipt']['tool_id'],
            'kinematics.pcc_forward',
        )
        self.assertEqual(
            observation['receipt']['charged']['backend_solves'],
            0,
        )
        position = observation['content']['tip']['position_m']
        self.assertAlmostEqual(position[0], 0.308, places=12)
        self.assertEqual(position[1:], [0.0, 0.0])
        self.assertEqual(
            self.store.remaining(self.host.run_id)['used']['backend_solves'],
            0,
        )


if __name__ == '__main__':
    unittest.main()
