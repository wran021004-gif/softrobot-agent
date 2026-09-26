"""Focused deterministic model-use decisions; no backend execution."""

import unittest
from copy import deepcopy

from examples.platform_tendon_family import example_design, example_discretization, design_space, session
from extensions.tendon_family.contracts import Design, GVSBasisSpecification, GVSModelParameters
from extensions.tendon_family.gvs_basis import resolve_basis
from extensions.tendon_family.model_applicability import assess_model_uses
from schemas.platform import Binding, Payload, SessionInput
from tools.platform_registry import registry
from tests.test_gvs_basis import fixture


def binding(model_id, contract, data=None):
    return Binding(extension_id=model_id, parameters=Payload(contract=contract, data=data or {}))


def context(design):
    raw = session('family_mujoco', design, design_space(example_design()))
    return SessionInput.model_validate(raw)


class ModelApplicabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = registry()

    def test_local_evidence_requires_actual_task_environment(self):
        from schemas.platform import EvidenceRef
        from schemas.platform_math import ModelAgreementEvidence
        from tools.state_io import digest

        inp = context(example_design())
        model = binding('model.gvs', 'family.gvs_model')
        basis = resolve_basis(inp.robot.structure.data)
        item = ModelAgreementEvidence(
            design_identity=digest(Design.model_validate(inp.robot.structure.data).model_dump(mode='json')),
            model_bindings=[model],
            representation_ids={'model.gvs': digest(basis.model_dump(mode='json'))},
            numerical_settings={'gvs': GVSModelParameters().model_dump(mode='json')},
            mapping_convention='backend_discrete_to_gvs_integrated_v2',
            reference_state_input={'q': [0.] * basis.dimension},
            environment=inp.task.environment.data,
            measured_uses=['shape_prediction'],
            metrics={'tip': dict(absolute_error=0., relative_error=None, units='m', norm='Euclidean')},
            sources=[], source_locations=[], limitations=['Synthetic single-state test fixture.'])
        ref = EvidenceRef(artifact_id=digest(item.model_dump(mode='json')))
        scope = {key: getattr(item, key) for key in
                 ('numerical_settings', 'mapping_convention', 'reference_state_input', 'environment')}

        def assess(task):
            return assess_model_uses(inp.robot, task, model,
                ['shape_prediction', 'local_model_control'], evidence=[ref],
                evidence_loader=lambda _: item, evidence_context=scope, registry=self.reg)

        matched = assess(inp.task)
        self.assertEqual(matched.uses['shape_prediction'].validation, 'measured_local')
        self.assertEqual(matched.uses['local_model_control'].validation, 'unavailable')
        changed = deepcopy(inp.task.environment.data)
        changed['mount']['position_m'][2] += .1
        task = inp.task.model_copy(update={'environment': inp.task.environment.model_copy(update={'data': changed})})
        # Reusing the historical query context cannot validate a changed mount.
        self.assertEqual(assess(task).uses['shape_prediction'].validation, 'unavailable')

    def test_pcc_keeps_capability_and_use_verdicts_separate(self):
        inp = context(example_design())
        model = binding('model.pcc', 'family.pcc_model')
        declaration = self.reg.mathematical_model(model)
        self.assertTrue(declaration.capabilities.kinematics)
        self.assertFalse(declaration.capabilities.dynamics)
        result = assess_model_uses(inp.robot, inp.task, model,
            ['reachability', 'shape_prediction', 'reduced_dynamics', 'contact_prediction'], registry=self.reg)
        self.assertEqual([result.uses[use].status for use in result.uses],
                         ['ALLOW', 'WARN', 'REJECT', 'REJECT'])
        self.assertIn('dynamics', result.unsupported_requested_physics)
        self.assertIn('contact_response', result.unsupported_requested_physics)
        self.assertEqual(self.reg.parse(Payload(contract='platform.model_use_assessment',
                         data=result.model_dump(mode='json'))), result)

    def test_gvs_resolved_basis_changes_representation_reasons_not_static_validation(self):
        design = fixture(3)  # Different component structure from the development robot.
        inp = context(design)
        use = ['reachability', 'shape_prediction', 'reduced_dynamics',
               'static_equilibrium', 'linearization', 'local_model_control', 'contact_prediction']
        results = {}
        for strategy in ('first_order', 'structural_linear'):
            params = GVSModelParameters(basis=GVSBasisSpecification(strategy=strategy))
            model = binding('model.gvs', 'family.gvs_model', params.model_dump(mode='json'))
            basis = resolve_basis(design, params.basis)
            result = assess_model_uses(inp.robot, inp.task, model, use,
                resolved_basis=basis, registry=self.reg)
            self.assertTrue(self.reg.mathematical_model(model).capabilities.dynamics)
            self.assertEqual(result.generalized_coordinate_dimension, basis.dimension)
            self.assertEqual(result.state_dimension, 2 * basis.dimension)
            self.assertEqual(result.representation_kind, basis.representation_id)
            self.assertEqual(result.representation_strategy, strategy)
            self.assertEqual(result.uses['static_equilibrium'].status, 'WARN')
            self.assertEqual(result.uses['linearization'].status, 'WARN')
            self.assertEqual(result.uses['local_model_control'].status, 'WARN')
            self.assertEqual(result.uses['contact_prediction'].status, 'REJECT')
            self.assertEqual(result.uses['reachability'].status, 'ALLOW')
            results[strategy] = result
        with self.assertRaisesRegex(ValueError, 'GVS_RESOLVED_BASIS_MISMATCH'):
            assess_model_uses(inp.robot, inp.task,
                binding('model.gvs', 'family.gvs_model',
                        GVSModelParameters(basis=GVSBasisSpecification(strategy='structural_linear')).model_dump(mode='json')),
                ['shape_prediction'], resolved_basis=resolve_basis(design), registry=self.reg)
        self.assertNotEqual(results['first_order'].representation_id,
                            results['structural_linear'].representation_id)
        self.assertEqual(results['first_order'].uses['shape_prediction'].status, 'WARN')
        self.assertEqual(results['first_order'].uses['reduced_dynamics'].status, 'WARN')
        self.assertEqual(results['structural_linear'].uses['shape_prediction'].status, 'ALLOW')
        self.assertEqual(results['structural_linear'].uses['reduced_dynamics'].status, 'ALLOW')
        self.assertIn('validation evidence is unavailable',
                      results['structural_linear'].uses['static_equilibrium'].reasons[0])

    def test_task_force_and_explicit_omitted_physics(self):
        design = fixture(1)
        raw = session('family_mujoco', design, design_space(example_design()))
        raw['task']['environment']['data']['external_forces'] = [dict(
            entity='section_a', force_n=[0., 0., 1.], start_s=0., end_s=.1)]
        inp = SessionInput.model_validate(raw)
        result = assess_model_uses(inp.robot, inp.task,
            binding('model.gvs', 'family.gvs_model'),
            ['reachability', 'static_equilibrium', 'reduced_dynamics'], registry=self.reg)
        self.assertEqual(result.uses['reachability'].status, 'ALLOW')
        self.assertEqual(result.uses['static_equilibrium'].status, 'REJECT')
        self.assertEqual(result.uses['reduced_dynamics'].status, 'REJECT')
        self.assertIn('external_applied_forces', result.unsupported_requested_physics)

    def test_serial_cells_are_higher_dimensional_reference_with_known_omissions(self):
        design = example_design()
        inp = context(design)
        cells = example_discretization()
        result = assess_model_uses(inp.robot, inp.task,
            binding('model.serial_bending_cells', 'family.dynamics_model'),
            ['reduced_dynamics', 'high_fidelity_validation', 'contact_prediction'],
            discretization=cells,
            required_physics={'contact_prediction': ['self_collision']}, registry=self.reg)
        self.assertEqual(result.generalized_coordinate_dimension, 2 * sum(cells.cells.values()))
        self.assertEqual(result.state_dimension, 4 * sum(cells.cells.values()))
        self.assertEqual(result.uses['reduced_dynamics'].status, 'WARN')
        self.assertEqual(result.uses['high_fidelity_validation'].status, 'WARN')
        self.assertEqual(result.uses['contact_prediction'].status, 'REJECT')
        self.assertEqual(result.unsupported_requested_physics, ['self_collision'])
        self.assertTrue(self.reg.mathematical_model(
            binding('model.serial_bending_cells', 'family.dynamics_model')).capabilities.dynamics)

    def test_off_tip_flexible_branch_is_a_structural_rejection(self):
        raw = fixture(3).model_dump(mode='json')
        branch = deepcopy(next(component for component in raw['components']
                               if component['id'] == 'section_c'))
        branch['id'] = 'side_branch'
        branch['connection']['part'] = 'section_a'
        raw['components'].append(branch)
        inp = context(Design.model_validate(raw))
        for model_id, contract in [('model.gvs', 'family.gvs_model'),
                                   ('model.serial_bending_cells', 'family.dynamics_model')]:
            result = assess_model_uses(inp.robot, inp.task, binding(model_id, contract),
                ['reachability'],
                discretization={'cells': {'section_a': 2, 'section_b': 2,
                                          'section_c': 2, 'side_branch': 2}}
                    if model_id == 'model.serial_bending_cells' else None,
                registry=self.reg)
            self.assertEqual(result.uses['reachability'].status, 'REJECT')


if __name__ == '__main__':
    unittest.main()
