"""Route model visibility and explicit public GVS basis selection."""

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from uuid import uuid4

from examples.platform_route import prepare
from examples.platform_tendon_family import session
from extensions.tendon_family.contracts import (Discretization, GVSBasisSpecification,
    GVSModelParameters, Space)
from extensions.tendon_family.gvs_basis import resolve_basis
from extensions.tendon_family.model_applicability import assess_model_uses
from extensions.tendon_family.route import create, model_options, overview, view
from schemas.platform import Binding, Payload, SessionInput
from tools.platform_host import Host
from tools.platform_models import input_for
from tools.platform_registry import registry
from tools.spec_tools import ROOT
from tools.state_io import digest, read
from tests.test_gvs_basis import fixture


class RouteModelOptionsTests(unittest.TestCase):
    def test_overview_keeps_assessments_separate_from_executable_combinations(self):
        root = ROOT / 'runs/route_model_options_tests' / uuid4().hex
        prepare(root, True)
        inp = read(root / 'inputs/route.json')
        combinations = inp['policy']['route']['data']['combinations']
        inp['policy']['route']['data']['combinations'] = {
            'family_mujoco': combinations['family_mujoco']}
        host = Host(root, inp['run_id'])
        host.store.create(read(root / 'inputs/project.json'))
        create(root, inp)

        summary = overview(host)
        self.assertEqual(set(summary['model_options']['options']),
                         {'pcc', 'gvs', 'serial_bending'})
        self.assertEqual(set(summary['combinations']), {'family_mujoco'})
        self.assertEqual(summary['combinations']['family_mujoco']['dynamics_model'],
                         'model.serial_bending_cells')
        self.assertEqual(summary['combinations']['family_mujoco']['backend'],
                         'backend.family_mujoco')
        options = summary['model_options']['options']
        self.assertEqual(options['pcc']['uses']['reachability'], 'ALLOW')
        self.assertEqual(options['pcc']['uses']['contact_prediction'], 'REJECT')
        self.assertEqual(options['pcc']['backend_solves'], 0)
        self.assertEqual(options['serial_bending']['backend_solves'], 1)
        self.assertEqual(options['serial_bending']['execution_backends'],
                         ['backend.family_mujoco'])
        representations = options['gvs']['representations']
        self.assertEqual(set(representations), {'first_order', 'structural_linear'})
        self.assertNotEqual(representations['first_order']['representation']['identity'],
                            representations['structural_linear']['representation']['identity'])
        self.assertLess(representations['first_order']['representation']['state_dimension'],
                        representations['structural_linear']['representation']['state_dimension'])
        self.assertEqual(representations['first_order']['uses']['shape_prediction'], 'WARN')
        self.assertEqual(representations['structural_linear']['uses']['shape_prediction'], 'ALLOW')
        self.assertEqual(representations['structural_linear']['uses']['static_equilibrium'], 'WARN')
        self.assertEqual(representations['structural_linear']['uses']['contact_prediction'], 'REJECT')
        self.assertEqual(representations['structural_linear']['backend_solves'], 0)
        self.assertEqual(representations['structural_linear']['basis_argument'],
                         {'basis': {'strategy': 'structural_linear'}})
        self.assertEqual(representations['structural_linear']['optimization_assembler']['basis'],
                         {'strategy': 'structural_linear'})
        receipt = host.invoke(dict(request_id='structural-description',
            tool_id='dynamics.gvs_describe', tool_version='2.0.0',
            arguments={'basis': {'strategy': 'structural_linear'}},
            reason='Inspect the explicit structural GVS coordinates.'))
        self.assertEqual(receipt['execution_status'], 'completed', receipt)
        description = host.store.artifact(receipt['output'])
        self.assertEqual(len(description['coordinates']),
                         representations['structural_linear']['representation']['generalized_coordinate_dimension'])
        self.assertEqual(digest(description['resolved_basis']),
                         representations['structural_linear']['representation']['identity'])
        self.assertEqual(receipt['charged']['backend_solves'], 0)
        self.assertLess(len(json.dumps(summary['model_options'])), 12000)
        self.assertEqual(input_for(host).context['route']['model_options'], summary['model_options'])
        legacy = deepcopy(inp)
        legacy['policy']['tool_bindings']['dynamics.gvs_describe'] = '1.0.0'
        older_options = model_options(host, SessionInput.model_validate(legacy),
                                      view(host)['combinations'])['options']
        self.assertEqual(set(older_options['gvs']['representations']), {'first_order'})
        mixed = deepcopy(inp)
        mixed['policy']['tool_bindings']['dynamics.gvs_build_system'] = '2.0.0'
        mixed['policy']['tool_bindings']['statics.gvs_equilibrium'] = '1.0.0'
        mixed_options = model_options(host, SessionInput.model_validate(mixed),
                                      view(host)['combinations'])['options']['gvs']['representations']
        self.assertIn('dynamics.gvs_build_system', mixed_options['first_order']['tools'])
        self.assertNotIn('dynamics.gvs_build_system', mixed_options['structural_linear']['tools'])
        self.assertIn('statics.gvs_equilibrium', mixed_options['first_order']['tools'])
        self.assertNotIn('statics.gvs_equilibrium', mixed_options['structural_linear']['tools'])

    def test_structural_basis_reaches_describe_and_numeric_evaluate(self):
        design = fixture(2)
        inp = SessionInput.model_validate(session('family_mujoco', design, Space(),
            discretization=Discretization(cells={'section_a': 2, 'section_b': 2})))
        reg = registry()
        ctx = SimpleNamespace(input=inp, reg=reg)
        basis = GVSBasisSpecification(strategy='structural_linear')
        model = Binding(extension_id='model.gvs', parameters=Payload(
            contract='family.gvs_model',
            data=GVSModelParameters(basis=basis).model_dump(mode='json')))
        assessment = assess_model_uses(inp.robot, inp.task, model,
            ['shape_prediction', 'reduced_dynamics'], registry=reg)
        resolved = resolve_basis(design, basis)
        describe = reg.get('dynamics.gvs_describe', '2.0.0').resolve()
        description = describe(ctx, reg.get('dynamics.gvs_describe', '2.0.0').input_schema(basis=basis))
        self.assertEqual(description.resolved_basis, resolved)
        self.assertEqual([item.name for item in description.coordinates], resolved.coordinate_order)
        self.assertEqual(assessment.generalized_coordinate_dimension, len(description.coordinates))
        self.assertEqual(assessment.state_dimension, 2 * len(description.coordinates))

        evaluate = reg.get('dynamics.gvs_evaluate', '3.0.0').resolve()
        request = reg.get('dynamics.gvs_evaluate', '3.0.0').input_schema.model_validate(dict(
            state=dict(q=[0.] * resolved.dimension, qdot=[0.] * resolved.dimension),
            input=dict(tendon_tensions_n={tendon.id: 0. for tendon in design.tendons}),
            basis=basis.model_dump(mode='json'), samples_per_segment=2))
        result = evaluate(ctx, request)
        self.assertEqual(result.coordinate_order, resolved.coordinate_order)
        self.assertEqual(len(result.qdd), assessment.generalized_coordinate_dimension)
        with self.assertRaises(ValueError):
            reg.get('dynamics.gvs_describe', '2.0.0').input_schema.model_validate({})
        with self.assertRaises(ValueError):
            reg.get('statics.gvs_equilibrium', '2.0.0').input_schema.model_validate(dict(
                tendon_tensions_n={tendon.id: 0. for tendon in design.tendons},
                initial_q=[0.] * resolved.dimension))
        assembler = reg.get('optimization_assembler.gvs_inverse', '2.0.0')
        with self.assertRaises(ValueError):
            assembler.input_schema.model_validate({'template': 'inverse_tip_static'})
        self.assertEqual(assembler.input_schema(template='inverse_tip_static', basis=basis).basis,
                         basis)
        _, parameters = reg.bind(Binding(
            extension_id='optimization_assembler.gvs_inverse', version='2.0.0',
            parameters=Payload(contract='family.gvs_inverse_assembler_parameters',
                version='2.0.0', data={'template': 'inverse_tip_static',
                                       'basis': basis.model_dump(mode='json')})),
            'optimization_assembler')
        self.assertEqual(parameters.basis, basis)
        with self.assertRaises(ValueError):
            reg.get('dynamics.gvs_evaluate', '3.0.0').input_schema.model_validate(dict(
                state=dict(q=[0.] * resolved.dimension, qdot=[0.] * resolved.dimension),
                input=dict(tendon_tensions_n={tendon.id: 0. for tendon in design.tendons})))
        with self.assertRaises(ValueError):
            reg.get('dynamics.gvs_build_system', '3.0.0').input_schema.model_validate(dict(
                x0=[0.] * (2 * resolved.dimension), u0=[0.] * len(design.tendons)))
        self.assertNotIn('basis', reg.get('dynamics.gvs_evaluate', '2.0.0').input_schema.model_fields)


if __name__ == '__main__':
    unittest.main()
