"""Assembly/operating-point fixtures only; no numerical solvers or backends."""
from typing import Literal, get_args, get_type_hints
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from examples.platform_tendon_family import example_design, session
from extensions.platform.manifest import Empty
from extensions.tendon_family.contracts import Space
from schemas.common import Contract
from schemas.platform import Binding, Payload, SessionInput
from schemas.platform_math import (ConstraintSelection, DynamicSystem, LinearizedModel,
    ObjectiveSelection, OptimizationConstraint, OptimizationProblem, OptimizationResult,
    OptimizationSpecification, SystemContext)
from schemas.platform_protocols import DynamicSystemProvider, Linearizer, Solver
from tests.test_platform_math import coordinate
from tools.platform_optimization import assemble_optimization
from tools.platform_registry import Extension, ExtensionKind, registry


class FixtureExpression(Contract):
    """Fixed test semantics: weighted squared distance or scalar identity.

    This is a serialized expression fixture, not a robot objective or evaluator.
    """
    template_id: Literal['objective.test', 'constraint.test']
    variable: str
    target: float = 0.
    weight: float = 1.


class AssemblerFixture:
    def __init__(self, parameters):
        self.parameters = parameters

    def assemble(self, task, robot, space, mathematical_model, specification, context):
        if not mathematical_model.capabilities.kinematics:
            raise ValueError('FIXTURE_REQUIRES_KINEMATICS')
        path = specification.variables[0]
        # Trusted, fixed fixture templates read existing task/robot semantics.
        expression = FixtureExpression(template_id='objective.test', variable=path,
            target=task.goal.data['target_m'][0], weight=specification.objectives[0].weight)
        constraints = [OptimizationConstraint(name='constraint.test', units='m',
            expression=Payload(contract='test.assembly_expression', data=FixtureExpression(
                template_id='constraint.test', variable=path).model_dump(mode='json')),
            upper=robot.structure.data['components'][0]['length_m'])
            for selection in specification.constraints]
        return OptimizationProblem(variables={p: space[p] for p in specification.variables},
            objective=task.objectives[0], objective_function=Payload(
                contract='test.assembly_expression', data=expression.model_dump(mode='json')),
            constraints=constraints, horizon=specification.horizon, initial_guess=specification.initial_guess)


class SystemFixture:
    """One-coordinate export/linearization fixtures, no integration or algorithms."""
    def build_system(self, robot, parameters, discretization, context):
        return DynamicSystem(state_definition=[coordinate('position')],
            input_definition=[coordinate('velocity', 'm/s')], output_definition=[],
            dynamics=Payload(contract='test.assembly_expression', data=FixtureExpression(
                template_id='constraint.test', variable='velocity').model_dump(mode='json')),
            x0=context.x0, u0=context.u0, time_domain='continuous')

    def linearize(self, system):
        return LinearizedModel(state_definition=system.state_definition,
            input_definition=system.input_definition, output_definition=system.output_definition,
            x0=system.x0, u0=system.u0, A=[[0.]], B=[[1.]], drift=system.u0,
            time_domain=system.time_domain)


class OptimizationAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.reg = registry()
        self.reg.add_contract('test.assembly_expression', '1.0.0', FixtureExpression)
        self.reg.add(Extension('assembler.test', 'optimization_assembler', '1.0.0', Empty,
            OptimizationProblem, 'tests.test_platform_optimization:AssemblerFixture',
            'Fixed test templates only', capabilities={
                'supported_objectives': ['objective.test'], 'supported_constraints': ['constraint.test']}))
        self.binding = Binding(extension_id='assembler.test', parameters=Payload(contract='platform.empty', data={}))
        self.space = Space(parameters={'components/near/length_m': {'type': 'number', 'bounds': [.14, .2]}},
            control_parameters={'control/feedback_gain': {'type': 'number', 'bounds': [1., 8.]}},
            model_parameters={'model/regularization': {'type': 'number', 'bounds': [0., 1.]}},
            discretization_parameters={'discretization/cells/near': {'type': 'integer', 'bounds': [2, 6]}})
        self.inp = SessionInput.model_validate(session('family_mujoco', example_design(), self.space))
        # Trusted projection of the existing Space; there are no renamed variables.
        self.paths = {**self.space.parameters, **self.space.control_parameters,
            **self.space.model_parameters, **self.space.discretization_parameters}
        self.spec = OptimizationSpecification(variables=list(self.paths),
            objectives=[ObjectiveSelection(template_id='objective.test', weight=2.)],
            constraints=[ConstraintSelection(template_id='constraint.test')],
            initial_guess={'components/near/length_m': .16})
        self.context = SystemContext(x0=[.3], u0=[.7], scene=self.inp.task.environment)

    def assemble(self, specification=None):
        return assemble_optimization(self.reg, self.binding, task=self.inp.task, robot=self.inp.robot,
            space=self.paths, mathematical_model=self.reg.mathematical_model(self.inp.policy.dynamics_model),
            specification=specification or self.spec, context=self.context)

    def test_specification_serializes_and_rejects_expression_inputs(self):
        self.assertEqual(self.reg.parse(Payload(contract='platform.optimization_specification',
            data=self.spec.model_dump(mode='json'))), self.spec)
        self.assertEqual(OptimizationSpecification.model_validate_json(self.spec.model_dump_json()), self.spec)
        self.assertNotIn('MathematicalExpression', str(OptimizationSpecification.model_json_schema()))
        for extra in ('objective_function', 'expression', 'code'):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                OptimizationSpecification.model_validate({**self.spec.model_dump(), extra: 'lambda x: x'})
        for value in (Payload(contract='test.expression', data={}), lambda x: x, 'lambda x: x'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ObjectiveSelection(template_id='objective.test', weight=value)
        for selection in (ObjectiveSelection, ConstraintSelection):
            with self.assertRaises(ValidationError):
                selection(template_id='lambda x: x')
            with self.assertRaises(ValidationError):
                selection(template_id='objective.test', parameters={'expression': 'x*x'})

    def test_registered_assembly_to_solver_and_separate_kinds(self):
        problem = self.assemble()
        self.assertEqual(problem.variables, self.paths)
        self.assertEqual(problem.objective, self.inp.task.objectives[0])
        expression = self.reg.parse(problem.objective_function)
        self.assertEqual(expression.target, self.inp.task.goal.data['target_m'][0])
        self.assertEqual(expression.weight, 2.)
        self.assertEqual(problem.constraints[0].upper, self.inp.robot.structure.data['components'][0]['length_m'])
        self.assertEqual(self.reg.parse(problem.constraints[0].expression).template_id, 'constraint.test')
        self.assertEqual(self.reg.parse(Payload(contract='platform.optimization_problem',
            data=problem.model_dump(mode='json'))), problem)
        self.reg.add(Extension('solver.assembly_test', 'solver', '1.0.0', Empty, OptimizationResult,
            'tests.test_platform_math:SolverStub', 'Dispatch fixture'))
        definition, parameters = self.reg.bind(self.binding.model_copy(update={
            'extension_id': 'solver.assembly_test'}), 'solver')
        solver: Solver = definition.resolve()(parameters)
        self.assertEqual(solver.solve(problem).status, 'unknown')
        self.assertIs(solver.problem, problem)
        self.assertIs(get_type_hints(Solver.solve)['problem'], OptimizationProblem)
        kinds = {'optimization_assembler', 'solver', 'search'}
        self.assertTrue(kinds.issubset(get_args(ExtensionKind)))
        for extension, actual in [('assembler.test', 'optimization_assembler'),
                                  ('solver.assembly_test', 'solver'), ('search.family_coordinate', 'search')]:
            for wrong in kinds - {actual}:
                with self.assertRaisesRegex(ValueError, 'EXTENSION_KIND_MISMATCH'):
                    self.reg.get(extension, kind=wrong)

    def test_unsupported_choices_fail_before_assembler_execution(self):
        cases = [('objectives', [ObjectiveSelection(template_id='unknown')], 'UNSUPPORTED_OBJECTIVES'),
                 ('constraints', [ConstraintSelection(template_id='unknown')], 'UNSUPPORTED_CONSTRAINTS'),
                 ('variables', ['components/arm/unauthorized'], 'VARIABLE_NOT_AUTHORIZED')]
        with patch.object(Extension, 'resolve') as resolve:
            for field, value, error in cases:
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, error):
                    self.assemble(self.spec.model_copy(update={field: value}))
            resolve.assert_not_called()

    def test_explicit_context_reaches_system_and_linearization(self):
        parsed = self.reg.parse(Payload(contract='platform.system_context', data=self.context.model_dump(mode='json')))
        self.assertEqual(parsed, self.context)
        self.assertEqual(self.reg.parse(parsed.scene), self.reg.parse(self.inp.task.environment))
        provider: DynamicSystemProvider = SystemFixture()
        linearizer: Linearizer = provider
        for x0, u0 in [([.3], [.7]), ([1.2], [-.2])]:
            context = SystemContext(x0=x0, u0=u0, scene=parsed.scene)
            system = provider.build_system(self.inp.robot, self.inp.policy.dynamics_model.parameters,
                self.inp.policy.discretization, context)
            linear = linearizer.linearize(system)
            self.assertEqual((system.x0, system.u0, linear.x0, linear.u0), (x0, u0, x0, u0))
        with self.assertRaises(ValidationError):
            SystemContext(scene=parsed.scene)
        with self.assertRaises(TypeError):
            provider.build_system(self.inp.robot, self.inp.policy.dynamics_model.parameters, None)

    def test_constraint_bounds_and_initial_guess_contract(self):
        expression = Payload(contract='test.assembly_expression', data=FixtureExpression(
            template_id='constraint.test', variable=self.spec.variables[0]).model_dump(mode='json'))
        for bounds in ({'lower': 0.}, {'upper': 1.}, {'lower': 1., 'upper': 1.}, {'lower': 0., 'upper': 1.}):
            OptimizationConstraint(name='test', expression=expression, units='m', **bounds)
        for bounds in ({}, {'lower': 2., 'upper': 1.}):
            with self.assertRaisesRegex(ValueError, 'OPTIMIZATION_CONSTRAINT_BOUND'):
                OptimizationConstraint(name='test', expression=expression, units='m', **bounds)
        with self.assertRaisesRegex(ValueError, 'INITIAL_GUESS_VARIABLE_NOT_DECLARED'):
            self.assemble(self.spec.model_copy(update={'initial_guess': {'missing/path': .1}}))


if __name__ == '__main__':
    unittest.main()
