"""Public mathematical boundaries only; no algorithms, integration or network."""
from dataclasses import replace
from typing import get_args
import unittest

from schemas.common import Contract
from schemas.platform import BackendResult, Binding, EvidenceRef, Objective, Payload, SessionInput, Signal, SignalSpec
from schemas.platform_math import (DynamicSystem, LinearizedModel, MathematicalModel,
    ModelCapabilities, ModelRequirement, OptimizationConstraint, OptimizationProblem, OptimizationResult)
from schemas.platform_protocols import Solver
from tools.platform_registry import Extension, ExtensionKind, registry
from tools.platform_store import encode
from tools.platform_tools import _candidate
from extensions.tendon_family.contracts import DynamicsModel, Space
from extensions.tendon_family.execution import model_definition
from extensions.tendon_family.route import Combination


class Expression(Contract):
    """Serialization fixture, deliberately no expression evaluator."""
    symbol: str


class ModelParameters(DynamicsModel):
    """Candidate parameter transport fixture, no physics implementation."""
    regularization: float = .1


class SolverStub:
    """Only exercises registration/dispatch; does not solve anything."""
    def __init__(self, parameters):
        self.parameters = parameters

    def solve(self, problem: OptimizationProblem) -> OptimizationResult:
        self.problem = problem
        return OptimizationResult(status='unknown', iterations=0)


def coordinate(name, units='m'):
    return SignalSpec(name=name, entity='fixture', dimension=1, units=units, frame='local', phase='sampled_state')


class MathematicalContracts(unittest.TestCase):
    def setUp(self):
        self.reg = registry()
        self.model = Binding(extension_id='model.serial_bending_cells',
            parameters=Payload(contract='family.dynamics_model', data={}))
        self.expression = Payload(contract='test.expression', data={'symbol': 'f'})
        self.reg.add_contract('test.expression', '1.0.0', Expression)

    def test_model_compatibility_and_explicit_capabilities(self):
        old = DynamicsModel()
        self.assertEqual(model_definition(old).data, old.model_dump(mode='json'))
        self.assertNotIn('mathematical_model', old.model_dump())
        contract = self.reg.mathematical_model(self.model)
        self.assertEqual(contract, old.mathematical_model)
        self.assertTrue(contract.capabilities.supports(['kinematics', 'dynamics']))
        self.assertFalse(contract.capabilities.supports(['gradients']))
        payload = Payload(contract='platform.mathematical_model', data=contract.model_dump(mode='json'))
        self.assertEqual(self.reg.parse(payload), contract)
        self.assertEqual(set(Combination.model_fields), {'dynamics_model', 'backend', 'controller'})

    def test_controller_dependency_matching_uses_declarations(self):
        controller = self.reg.get('controller.family')
        binding = Binding(extension_id=controller.extension_id, parameters=Payload(contract='family.control', data={}))
        self.reg.check_controller_model(binding, None)  # Old controllers remain usable.
        for kind, capability in [('mathematical_model', 'kinematics'), ('dynamic_system', 'dynamics'),
                                 ('linearized_model', 'linearization')]:
            required = ModelRequirement(input=kind, capabilities=[capability])
            name = 'controller.test_' + kind
            self.reg.add(replace(controller, extension_id=name,
                capabilities={**controller.capabilities, 'model_requirement': required.model_dump(mode='json')}))
            selected = binding.model_copy(update={'extension_id': name})
            if kind == 'mathematical_model':
                self.reg.check_controller_model(selected, self.model)
            else:
                with self.assertRaisesRegex(ValueError, 'MODEL_REQUIREMENT_UNSUPPORTED'):
                    self.reg.check_controller_model(selected, self.model)
            with self.assertRaisesRegex(ValueError, 'MODEL_REQUIREMENT_UNSUPPORTED'):
                self.reg.check_controller_model(selected, None)
        # A declaration-only provider fixture: names have no capability meaning.
        descriptor = self.reg.mathematical_model(self.model).model_copy(update={
            'capabilities': ModelCapabilities(dynamics=True, linearization=True),
            'representations': ['dynamic_system', 'linearized_model']})
        extension = self.reg.get(self.model.extension_id)
        self.reg.add(replace(extension, extension_id='model.unrelated_fixture',
            capabilities={'mathematical_model': descriptor.model_dump(mode='json')}))
        offered = self.model.model_copy(update={'extension_id': 'model.unrelated_fixture'})
        self.reg.check_controller_model(binding.model_copy(update={'extension_id': 'controller.test_linearized_model'}), offered)
        self.reg.check_controller_model(binding.model_copy(update={'extension_id': 'controller.test_dynamic_system'}), offered)
        from examples.platform_tendon_family import example_design, design_space, session
        from tools.platform_tasks import compile_input
        design = example_design()
        value = session('family_mujoco', design, design_space(design))
        value['policy']['controller']['extension_id'] = 'controller.test_linearized_model'
        with self.assertRaisesRegex(ValueError, 'MODEL_REQUIREMENT_UNSUPPORTED'):
            compile_input(value, self.reg)  # Reject before any backend check/start.

    def test_standard_ir_serialization_time_and_dimensions(self):
        fields = dict(state_definition=[coordinate('position')], input_definition=[coordinate('velocity', 'm/s')],
            output_definition=[coordinate('position')], x0=[0.], u0=[0.])
        for domain, timestep in [('continuous', None), ('discrete', .01)]:
            system = DynamicSystem(**fields, dynamics=self.expression, time_domain=domain, timestep=timestep)
            linear = LinearizedModel(**fields, A=[[1.]], B=[[.01]], time_domain=domain, timestep=timestep)
            for name, value in [('dynamic_system', system), ('linearized_model', linear)]:
                payload = Payload(contract='platform.' + name, data=value.model_dump(mode='json'))
                self.assertEqual(self.reg.parse(payload), value)
                self.assertEqual(type(value).model_validate_json(encode(value)), value)
            self.assertEqual(self.reg.parse(system.dynamics), Expression(symbol='f'))
        with self.assertRaisesRegex(ValueError, 'DISCRETE_SYSTEM_REQUIRES_TIMESTEP'):
            DynamicSystem(**fields, dynamics=self.expression, time_domain='discrete')
        with self.assertRaisesRegex(ValueError, 'MATRIX_DIMENSION_MISMATCH'):
            LinearizedModel(**fields, A=[[1., 0.]], B=[[1.]], time_domain='continuous')

    def test_problem_and_solver_are_independent_from_task_and_search(self):
        space = Space(model_parameters={'model/regularization': {'type': 'number', 'bounds': [0., 1.]}})
        objective = Objective(metric='error', direction='minimize', units='m')
        problem = OptimizationProblem(variables=space.model_parameters, objective=objective,
            objective_function=self.expression, constraints=[OptimizationConstraint(name='limit',
                expression=self.expression, units='m', upper=1.)], model_reference=self.model,
            horizon=5, initial_guess={'model/regularization': .1})
        parsed = self.reg.parse(Payload(contract='platform.optimization_problem', data=problem.model_dump(mode='json')))
        self.assertEqual(parsed, problem)
        self.assertEqual(parsed.objective, objective)
        self.assertNotIn('solver', problem.model_dump())
        self.assertIn('solver', get_args(ExtensionKind))
        self.reg.add(Extension('solver.test', 'solver', '1.0.0', Expression, OptimizationResult,
            'tests.test_platform_math:SolverStub', 'Protocol-only fixture'))
        binding = Binding(extension_id='solver.test', parameters=self.expression)
        definition, parameters = self.reg.bind(binding, 'solver')
        solver: Solver = definition.resolve()(parameters)
        result = solver.solve(parsed)
        self.assertIs(solver.problem, parsed)
        self.assertEqual(self.reg.parse(Payload(contract='platform.optimization_result', data=result.model_dump(mode='json'))), result)
        with self.assertRaisesRegex(ValueError, 'EXTENSION_KIND_MISMATCH'):
            self.reg.bind(binding, 'search')
        with self.assertRaisesRegex(ValueError, 'EXTENSION_KIND_MISMATCH'):
            self.reg.get('search.family_coordinate', kind='solver')

    def test_space_model_parameters_reach_only_model_payload(self):
        from examples.platform_tendon_family import example_design, design_space, session
        design = example_design()
        value = session('family_mujoco', design, design_space(design))
        space = value['policy']['candidate_builder']['parameters']['data']
        self.assertEqual(Space.model_validate(space).model_parameters, {})
        space['model_parameters'] = {'model/regularization': {'type': 'number', 'bounds': [0., 1.]}}
        self.reg.add_contract('test.model_parameters', '1.0.0', ModelParameters)
        self.reg.add(replace(self.reg.get(self.model.extension_id), extension_id='model.test_parameters', input_schema=ModelParameters))
        value['policy']['dynamics_model'] = dict(extension_id='model.test_parameters',
            parameters=dict(contract='test.model_parameters', data=ModelParameters().model_dump(mode='json')))
        original = SessionInput.model_validate(value)
        updated = _candidate(original, {'model/regularization': .2}, self.reg)
        self.assertEqual(updated.policy.dynamics_model.parameters.data['regularization'], .2)
        self.assertEqual(original.policy.dynamics_model.parameters.data['regularization'], .1)
        self.assertEqual(updated.task, original.task)
        self.assertEqual(updated.robot, original.robot)
        self.assertEqual(self.reg.bind(updated.policy.controller, 'controller')[1],
                         self.reg.bind(original.policy.controller, 'controller')[1])
        self.assertEqual(updated.policy.discretization, original.policy.discretization)
        with self.assertRaisesRegex(ValueError, 'OUT_OF_BOUNDS'):
            _candidate(original, {'model/regularization': 2.}, self.reg)
        with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
            _candidate(original, {'model/undeclared': .2}, self.reg)
        from unittest.mock import patch
        def changed_binding(inp, parameters, changes):
            return inp.model_copy(update={'policy': inp.policy.model_copy(update={
                'dynamics_model': inp.policy.dynamics_model.model_copy(update={'extension_id': 'model.other'})})})
        with patch.object(Extension, 'resolve', return_value=changed_binding):
            with self.assertRaisesRegex(ValueError, 'CANDIDATE_CHANGED_FROZEN'):
                _candidate(original, {}, self.reg)
        # Existing serial model has no regularization knob; do not accept one.
        with self.assertRaisesRegex(ValueError, 'Extra inputs'):
            self.reg.bind(self.model.model_copy(update={'parameters': Payload(
                contract='family.dynamics_model', data={'regularization': .2})}), 'dynamics_model')

    def test_backend_signal_exit_and_existing_reference_format(self):
        specs = [coordinate(name, units) for name, units in [
            ('tip_position', 'm'), ('tendon_length', 'm'), ('tendon_tension', 'N'),
            ('joint_position', 'rad'), ('joint_velocity', 'rad/s'), ('contact_force', 'N')]]
        signals = [Signal(spec=spec, times_s=[.1, .25], values=[[0.], [1.]]) for spec in specs]
        result = BackendResult(solver_status='completed', backend_id='backend.test', model_id='test',
            signals=signals, data=self.expression, initial_state=self.expression,
            limitations=['Serialization fixture only'], seed=0)
        self.assertEqual(BackendResult.model_validate_json(encode(result)), result)
        ref = EvidenceRef(artifact_id='a' * 64)
        problem = OptimizationProblem(variables={}, objective=Objective(metric='x', direction='minimize', units='1'),
            objective_function=ref, model_reference=ref)
        self.assertEqual(OptimizationProblem.model_validate_json(encode(problem)), problem)


if __name__ == '__main__':
    unittest.main()
