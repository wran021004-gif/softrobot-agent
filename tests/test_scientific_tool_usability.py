"""Focused checks for compact, evidence-oriented scientific tools."""

import math
import subprocess
import sys
import unittest
from uuid import uuid4

from examples.platform_fixtures import project
from examples.platform_tendon_family import example_design, design_space, session
from extensions.tendon_family.route import create as create_route
from schemas.platform import EvidenceRef
from schemas.platform_math import DynamicSystem, LinearizedModel
from tools.platform_host import Host
from tools.platform_models import input_for
from tools.platform_registry import registry
from tools.platform_store import Store
from tools.platform_tasks import compile_input
from tools.spec_tools import ROOT


def scientific_input(suffix):
    design = example_design()
    value = session('family_mujoco', design, design_space(design))
    value['run_id'] = 'scientific-' + suffix
    value['task']['environment']['data']['external_forces'] = []
    value['task']['environment']['data']['mount']['quaternion_wxyz'] = [
        math.sqrt(0.5), 0.0, math.sqrt(0.5), 0.0,
    ]
    value['policy']['budget'].update(tool_calls=20, backend_solves=0)
    value['policy']['timeout_s'] = 30.0
    value['policy']['tool_bindings'].update({
        'kinematics.pcc_forward': '2.0.0',
        'dynamics.gvs_evaluate': '2.0.0',
        'dynamics.gvs_build_system': '2.0.0',
        'linearization.linearize': '2.0.0',
        'statics.gvs_equilibrium': '1.0.0',
        'control.lqr_synthesize': '1.0.0',
    })
    return value


class ScientificToolUsabilityTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid4().hex
        self.root = ROOT / 'runs/scientific_tool_tests' / suffix
        self.store = Store(self.root)
        self.store.create(project())
        self.reg = registry()
        self.input = scientific_input(suffix)
        self.host = Host(self.root, self.input['run_id'], reg=self.reg)
        self.host.create(self.input)
        self.configuration = {
            'segments': {
                'near': {'curvature_y_rad_m': 0.0, 'curvature_z_rad_m': 0.0},
                'far': {'curvature_y_rad_m': 0.0, 'curvature_z_rad_m': 0.0},
            },
        }
        self.state = {'q': [0.0] * 8, 'qdot': [0.0] * 8}
        self.tensions = {
            tendon['id']: 0.0
            for tendon in self.input['robot']['structure']['data']['tendons']
        }

    def invoke(self, request_id, tool_id, version, arguments):
        receipt = self.host.invoke({
            'request_id': request_id,
            'tool_id': tool_id,
            'tool_version': version,
            'arguments': arguments,
            'reason': 'Focused scientific tool verification.',
        })
        self.assertEqual(receipt['execution_status'], 'completed', receipt)
        return self.store.artifact(receipt['output'])

    def test_pcc_compact_default_and_backbone_opt_in(self):
        compact = self.invoke('pcc-compact', 'kinematics.pcc_forward', '2.0.0', {
            'configuration': self.configuration,
        })
        self.assertIsNone(compact['backbone_points_m'])
        self.assertEqual(set(compact['segment_end_poses']), {'near', 'far'})
        self.assertAlmostEqual(compact['tip']['position_m'][0], 0.308, places=12)

        detailed = self.invoke('pcc-backbone', 'kinematics.pcc_forward', '2.0.0', {
            'configuration': self.configuration,
            'include_backbone': True,
            'samples_per_segment': 5,
        })
        self.assertEqual(len(detailed['backbone_points_m']['near']), 5)

    def test_gvs_output_layers(self):
        base = {'state': self.state, 'input': {'tendon_tensions_n': self.tensions},
                'samples_per_segment': 3}
        summary = self.invoke('gvs-summary', 'dynamics.gvs_evaluate', '2.0.0', base)
        self.assertEqual(summary['detail'], 'summary')
        self.assertIsNone(summary['mass_matrix'])
        self.assertIsNone(summary['gravity_force'])
        self.assertIsNone(summary['backbone_points_m'])

        forces = self.invoke('gvs-forces', 'dynamics.gvs_evaluate', '2.0.0', {
            **base, 'detail': 'forces',
        })
        self.assertEqual(len(forces['gravity_force']), 8)
        self.assertIsNone(forces['mass_matrix'])

        full = self.invoke('gvs-full', 'dynamics.gvs_evaluate', '2.0.0', {
            **base, 'detail': 'full', 'include_backbone': True,
        })
        self.assertEqual((len(full['mass_matrix']), len(full['tendon_length_jacobian'])), (8, 6))
        self.assertEqual(len(full['backbone_points_m']['near']), 3)

    def test_equilibrium_evidence_chain_and_lqr(self):
        equilibrium = self.invoke('gvs-equilibrium', 'statics.gvs_equilibrium', '1.0.0', {
            'tendon_tensions_n': self.tensions,
            'initial_q': [0.0] * 8,
            'tolerance': 1e-12,
        })
        self.assertTrue(equilibrium['converged'], equilibrium)
        self.assertLessEqual(equilibrium['residual_norm'], 1e-12)

        system_summary = self.invoke('gvs-system', 'dynamics.gvs_build_system', '2.0.0', {
            'x0': equilibrium['q_equilibrium'] + [0.0] * 8,
            'u0': [0.0] * 6,
        })
        system_ref = EvidenceRef.model_validate(system_summary['system'])
        system = DynamicSystem.model_validate(self.store.artifact(system_ref))
        self.assertEqual(system_summary['environment_source'], 'frozen_task_environment')

        linear_summary = self.invoke('linearize', 'linearization.linearize', '2.0.0', {
            'system': system_ref.model_dump(mode='json'),
        })
        self.assertEqual(linear_summary['source_system'], system_ref.model_dump(mode='json'))
        model_ref = EvidenceRef.model_validate(linear_summary['model'])
        LinearizedModel.model_validate(self.store.artifact(model_ref))

        synthesis = self.invoke('lqr', 'control.lqr_synthesize', '1.0.0', {
            'model': model_ref.model_dump(mode='json'),
            'curvature_weight': 2.0,
            'state_rate_weight': 0.2,
            'tendon_tension_weight': 1.0,
        })
        self.assertEqual(synthesis['gain_shape'], [6, 16])
        self.assertTrue(synthesis['closed_loop_stable'], synthesis)
        self.assertFalse(synthesis['backend_executable'])
        gain = self.store.artifact(EvidenceRef.model_validate(synthesis['gain']))
        self.assertEqual(len(gain['K']), 6)
        self.assertEqual(gain['tendon_order'], list(self.tensions))
        self.assertEqual(gain['force_limits_n'], [8.0] * 6)

    def test_public_build_rejects_scene_override(self):
        receipt = self.host.invoke({
            'request_id': 'scene-override',
            'tool_id': 'dynamics.gvs_build_system',
            'tool_version': '2.0.0',
            'arguments': {'x0': [0.0] * 16, 'u0': [0.0] * 6,
                          'scene': self.input['task']['environment']},
            'reason': 'Confirm that public callers cannot replace frozen physics.',
        })
        self.assertEqual(receipt['execution_status'], 'rejected')
        self.assertIn('scene', receipt['error'])

    def test_route_visibility_is_capability_driven(self):
        suffix = uuid4().hex
        root = ROOT / 'runs/scientific_route_tests' / suffix
        store = Store(root)
        store.create(project())
        value = scientific_input(suffix)
        value['run_id'] = 'scientific-route-' + suffix
        value['policy']['tool_bindings'].update({
            'route.advance': '1.0.0',
            'route.inspect': '1.0.0',
            'evidence.read': '1.0.0',
            'session.control': '1.0.0',
            'design.family_build': '1.0.0',
        })
        value['policy']['route'] = {
            'contract': 'family.route_policy', 'version': '1.0.0', 'data': {
                'source': 'Focused route visibility fixture.',
                'combinations': {'baseline': {
                    'dynamics_model': value['policy']['dynamics_model'],
                    'backend': value['policy']['backend'],
                    'controller': value['policy']['controller'],
                }},
            },
        }
        create_route(root, value)
        host = Host(root, value['run_id'], reg=self.reg)
        visible = {item['extension_id'] for item in input_for(host).tools}
        self.assertIn('route.advance', visible)
        self.assertIn('kinematics.pcc_forward', visible)
        self.assertIn('statics.gvs_equilibrium', visible)
        self.assertIn('control.lqr_synthesize', visible)
        self.assertNotIn('design.family_build', visible)

    def test_casadi_import_does_not_import_scipy(self):
        command = (
            'import sys; import extensions.tendon_family.gvs_casadi; '
            'assert not any(name == "scipy" or name.startswith("scipy.") for name in sys.modules)'
        )
        subprocess.run([sys.executable, '-c', command], cwd=ROOT, check=True)

    def test_model_space_lqr_is_rejected_as_backend_controller(self):
        value = scientific_input(uuid4().hex)
        value['policy']['controller'] = {
            'extension_id': 'controller.lqr',
            'version': '1.0.0',
            'parameters': {
                'contract': 'family.lqr_parameters',
                'version': '1.0.0',
                'data': {
                    'Q': [[1.0 if row == column else 0.0 for column in range(16)]
                          for row in range(16)],
                    'R': [[1.0 if row == column else 0.0 for column in range(6)]
                          for row in range(6)],
                    'tendon_order': list(self.tensions),
                    'force_limits_n': [8.0] * 6,
                },
            },
        }
        with self.assertRaisesRegex(ValueError, 'CONTROL_BACKEND_ADAPTER_REQUIRED'):
            compile_input(value, self.reg)


if __name__ == '__main__':
    unittest.main()
