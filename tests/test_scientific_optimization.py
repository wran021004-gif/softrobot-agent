"""Focused real-mathematics checks for trusted assembly and IPOPT."""
import json
import math
import unittest
from uuid import uuid4

import casadi as ca
import numpy as np
from pydantic import ValidationError

from examples.platform_fixtures import project
from examples.platform_tendon_family import example_design, design_space, session
from extensions.optimization.ipopt import IpoptSolver, expression_payload
from extensions.tendon_family.contracts import (
    GVSInverseAssemblerParameters,
    PCCReachAssemblerParameters,
)
from extensions.tendon_family.gvs import coordinate_order, forward_kinematics as gvs_forward
from extensions.tendon_family.pcc import forward_kinematics as pcc_forward, quaternion_wxyz_to_rotation
from extensions.tendon_family.scientific_optimization import gvs_authorization
from schemas.platform import Binding, Objective, Payload, SessionInput
from schemas.platform_math import (
    ConstraintSelection,
    ObjectiveSelection,
    OptimizationProblem,
    OptimizationSpecification,
    SystemContext,
)
from tools.platform_host import Host
from tools.platform_optimization import assemble_optimization
from tools.platform_registry import registry
from tools.platform_store import Store
from tools.spec_tools import ROOT


Q_TARGET = np.array([
    -0.153457508048493, -0.01367631448345668,
    0.03605236058506734, 0.0006143717266751143,
    -1.6588143086238407, -0.42381052787062873,
    -0.8182492520990569, -0.2623998390844626,
])
KNOWN_TENSIONS = np.array([1.2, 0.4, 0.8, 0.7, 1.1, 0.3])


def mathematical_session(target_from_q=False):
    design = example_design()
    value = session('family_mujoco', design, design_space(design))
    value['task']['environment']['data']['external_forces'] = []
    value['task']['environment']['data']['mount']['quaternion_wxyz'] = [
        math.sqrt(0.5), 0.0, math.sqrt(0.5), 0.0,
    ]
    if target_from_q:
        mount = value['task']['environment']['data']['mount']
        rotation = quaternion_wxyz_to_rotation(mount['quaternion_wxyz'])
        local = gvs_forward(design, Q_TARGET, samples_per_segment=2)['tip_position_m']
        value['task']['goal']['data']['target_m'] = (
            rotation @ local + np.asarray(mount['position_m'])
        ).tolist()
    return design, SessionInput.model_validate(value)


class ScientificOptimizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = registry()

    def test_public_gvs_trajectory_initial_context(self):
        """Real Host assembly with explicit measured values; no solve or backend."""
        from extensions.tendon_family.gvs_trajectory import trajectory_authorization
        from tools.state_io import atomic_json

        root = ROOT / 'runs/public_gvs_trajectory_assembly' / uuid4().hex
        grant = project()
        grant['authorization_source'] = 'User-authorized public GVS trajectory assembly repair; no solve or simulation'
        Store(root).create(grant)
        value = json.loads((ROOT / 'runs/stage35_case_b_retry_softagent_20260924/inputs/route.json').read_text(encoding='utf8'))
        value['run_id'] = 'public-gvs-assembly'
        value['policy'].update(route=None, allowed_tools=['optimization.assemble'],
            tool_bindings={'optimization.assemble': '1.0.0'}, timeout_s=30.)
        value['policy']['budget'].update(tool_calls=3, backend_solves=0, model_calls=0)
        # Authorize a fixed existing length for the static compatibility probe;
        # the robot, task and physical value are unchanged.
        length = next(c['length_m'] for c in value['robot']['structure']['data']['components'] if c['id']=='near')
        value['policy']['candidate_builder']['parameters']['data']['parameters']['components/near/length_m'] = dict(
            type='number', bounds=[length, length])
        host = Host(root, value['run_id'], reg=self.reg)
        host.create(value)
        inp = SessionInput.model_validate(value)
        parameters = dict(horizon=2, curvature_scale_rad_m=20., rate_scale_rad_m_s=200.)
        coordinates = coordinate_order(inp.robot.structure.data, {'strategy': 'structural_linear'})
        n = len(coordinates)
        tendons = [t['id'] for t in inp.robot.structure.data['tendons']]
        # Distinct nonzero entries detect reordering, zero/equilibrium substitution,
        # and confusion between physical values and scaled decision variables.
        x0 = [0.2*(j+1) for j in range(n)] + [-2.*(j+1) for j in range(n)]
        u0 = [0.5+0.25*j for j in range(len(tendons))]
        arguments = dict(assembler=dict(extension_id='optimization_assembler.gvs_trajectory',
            parameters=dict(contract='family.gvs_trajectory_parameters', data=parameters)),
            specification=dict(variables=list(trajectory_authorization(inp.robot, {}, parameters)),
                horizon=2, objectives=[dict(template_id='dynamic_tip_tracking')],
                constraints=[dict(template_id=k) for k in ('initial_state', 'implicit_dynamics', 'tendon_force_bounds')]),
            context=dict(x0=x0, u0=u0))
        request = dict(request_id='assemble-gvs', tool_id='optimization.assemble', tool_version='1.0.0',
            arguments=arguments, reason='Verify supplied dynamic initial conditions through the public Host.')
        receipt = host.invoke(request)
        self.assertEqual(receipt['execution_status'], 'completed', receipt)
        summary = host.store.artifact(receipt['output'])
        problem = OptimizationProblem.model_validate(host.store.artifact(summary['problem']))
        names = coordinates + [name+'.rate' for name in coordinates]
        for j, (name, physical) in enumerate(zip(names, x0)):
            spec = problem.variables[f'x/0/{j}']
            scale = 20. if j < n else 200.
            self.assertEqual(spec['physical_coordinate'], name)
            self.assertEqual(spec['units'], '1')
            self.assertEqual(spec['physical_units'], 'rad/m' if j < n else 'rad/(m*s)')
            self.assertEqual(spec['physical_scale'], scale)
            self.assertEqual(spec['bounds'], [physical/scale]*2)
            self.assertEqual(problem.initial_guess[f'x/0/{j}'], physical/scale)
        # Artifact JSON canonicalizes dictionary keys; vector order is explicit
        # in the serialized expression rather than the variables dictionary.
        order = problem.objective_function.data['variable_order']
        self.assertEqual([k.removeprefix('previous_u/') for k in order if k.startswith('previous_u/')], tendons)
        self.assertEqual([k for k in order if k.startswith('x/0/')], [f'x/0/{j}' for j in range(2*n)])
        for tendon, tension in zip(tendons, u0):
            self.assertEqual(problem.variables['previous_u/'+tendon]['bounds'], [tension]*2)
            self.assertEqual(problem.variables['previous_u/'+tendon]['units'], 'N')
            self.assertEqual(problem.initial_guess['previous_u/'+tendon], tension)
            self.assertEqual(problem.initial_guess['u/0/'+tendon], tension)
        self.assertEqual(len(problem.constraints), 2*2*n)

        missing = host.invoke({**request, 'request_id': 'missing-context',
            'arguments': {k:v for k,v in arguments.items() if k!='context'}})
        self.assertEqual(missing['execution_status'], 'failed', missing)
        self.assertIn('GVS_TRAJECTORY_INITIAL_STATE_AND_PREVIOUS_TENSION_REQUIRED', missing['error'])

        # Static callers still omit context. Assemble only; never invoke solve.
        static_arguments = dict(assembler=dict(extension_id='optimization_assembler.pcc_reach',
            parameters=dict(contract='family.pcc_reach_assembler_parameters', data=dict(configuration=dict(segments={
                s:dict(curvature_y_rad_m=0.,curvature_z_rad_m=0.) for s in ('near','far')})))),
            specification=dict(variables=['components/near/length_m'],
                objectives=[dict(template_id='tip_position_error_squared')],
                constraints=[dict(template_id='authorized_design_bounds')]))
        static = host.invoke({**request, 'request_id': 'static-no-context', 'arguments': static_arguments})
        self.assertEqual(static['execution_status'], 'completed', static)
        self.assertEqual(host.store.remaining(host.run_id)['used']['backend_solves'], 0)
        atomic_json(root/'verification.json', dict(request=request, receipt=receipt,
            problem=summary['problem'], initial_variables={k:v for k,v in problem.variables.items()
                if k.startswith(('x/0/','previous_u/'))},
            missing_context_receipt=missing, static_without_context_receipt=static,
            backend_solves=0, optimizer_invoked=False))
        print('\nPublic GVS assembly verified:', root/'verification.json')

    def test_legacy_versions_and_semantic_lqr_description(self):
        legacy_ids = (
            'kinematics.pcc_forward', 'dynamics.gvs_evaluate',
            'dynamics.gvs_build_system', 'linearization.linearize',
            'control.lqr_describe',
        )
        for name in legacy_ids:
            legacy = self.reg.get(name, '1.0.0', 'tool')
            self.assertTrue(legacy.capabilities['legacy'])
            self.assertFalse(legacy.capabilities['route_visible'])
            self.assertFalse(legacy.capabilities['recommended'])
        for name, version in (
            ('kinematics.pcc_forward', '2.0.0'),
            ('dynamics.gvs_evaluate', '2.0.0'),
            ('dynamics.gvs_build_system', '2.0.0'),
            ('linearization.linearize', '2.0.0'),
            ('control.lqr_describe', '2.0.0'),
        ):
            self.assertTrue(self.reg.get(name, version, 'tool').capabilities['route_visible'])
        description = self.reg.get('control.lqr_describe', '2.0.0', 'tool').output_schema()
        self.assertIn('semantic weights', description.workflow)
        self.assertEqual(description.tendon_order_source, 'frozen_robot.family.design')
        self.assertFalse(description.backend_executable)

    def test_generic_ipopt_solver(self):
        public_schema = str(
            self.reg.get('optimization.solve', '1.0.0', 'tool').input_schema.model_json_schema()
        )
        self.assertNotIn('OptimizationProblem', public_schema)
        self.assertNotIn('serialized_function', public_schema)
        x = ca.MX.sym('x')
        expression, _ = expression_payload(
            ['x'], {'variables': {'x': x}, 'expression': (x - 3) ** 2}, {}
        )
        problem = OptimizationProblem(
            variables={'x': {'type': 'number', 'bounds': [-5, 5]}},
            objective=Objective(metric='quadratic_fixture', direction='minimize', units='1'),
            objective_function=expression,
            initial_guess={'x': 0},
        )
        solver=IpoptSolver()
        result = solver.solve(problem)
        self.assertEqual(result.status, 'converged')
        self.assertAlmostEqual(result.optimum['x'], 3.0, places=7)
        self.assertLess(result.objective_value, 1e-14)
        # NMPC updates measured-state equalities through bounds on a cached graph.
        problem.variables['x']['bounds']=[4.,4.]
        updated=solver.solve(problem)
        self.assertTrue(solver.last_diagnostics['cached_solver'])
        self.assertAlmostEqual(updated.optimum['x'],4.,places=7)
        self.assertLess(updated.constraint_violation,1e-7)

    def test_limited_solve_retains_independently_feasible_iterate(self):
        x,y=ca.MX.sym('x'),ca.MX.sym('y')
        expression,selectors=expression_payload(['x','y'],
            dict(variables={'x':x,'y':y},expression=(x-2)**2+y**2),{'parabola':y-x*x})
        from schemas.platform_math import OptimizationConstraint
        problem=OptimizationProblem(variables={k:dict(type='number',bounds=[-5.,5.]) for k in ('x','y')},
            objective=Objective(metric='distance',direction='minimize',units='1'),objective_function=expression,
            constraints=[OptimizationConstraint(name='parabola',expression=selectors[0],units='1',lower=0.,upper=0.)],
            initial_guess={'x':0.,'y':0.})
        solver=IpoptSolver(dict(max_iterations=1,retain_feasible_iterate=True))
        result=solver.solve(problem)
        self.assertEqual(result.status,'iteration_limit')
        self.assertGreater(solver.last_diagnostics['returned_iterate_constraint_violation'],1e-5)
        self.assertLessEqual(result.constraint_violation,1e-5)
        self.assertAlmostEqual(result.optimum['y'],result.optimum['x']**2,places=8)
        self.assertEqual(solver.last_diagnostics['selected_feasible_iteration'],0)
        first=solver.last_diagnostics['first_feasible_candidate']
        self.assertTrue(first['iteration_zero'])
        self.assertTrue(first['independently_feasible'])
        self.assertGreaterEqual(first['elapsed_s'],0.)
        self.assertLessEqual(first['elapsed_s'],solver.last_diagnostics['solve_s'])
        self.assertEqual(first,solver.last_diagnostics['selected_feasible_candidate'])
        # A cached solve with incompatible new bounds cannot inherit a feasible
        # candidate or timestamp from the preceding solve.
        problem.variables['x']['bounds']=[1.,5.]
        problem.variables['y']['bounds']=[-5.,.5]
        updated=solver.solve(problem)
        self.assertTrue(solver.last_diagnostics['cached_solver'])
        self.assertGreater(updated.constraint_violation,1e-5)
        self.assertIsNone(solver.last_diagnostics['first_feasible_candidate'])
        self.assertIsNone(solver.last_diagnostics['selected_feasible_candidate'])

    def test_optional_feasible_stop_preserves_raw_status_and_current_bounds(self):
        x=ca.MX.sym('x')
        expression,_=expression_payload(['x'],dict(variables={'x':x},expression=(x-2)**2),{})
        problem=OptimizationProblem(variables={'x':dict(type='number',bounds=[-5.,5.])},
            objective=Objective(metric='distance',direction='minimize',units='1'),
            objective_function=expression,initial_guess={'x':0.})
        solver=IpoptSolver(dict(feasible_return=dict(minimum_s=0.,budget_s=10.,relative_improvement=.1)))
        result=solver.solve(problem)
        self.assertEqual(result.status,'feasible_early_stop')
        self.assertEqual(solver.last_diagnostics['return_status'],'User_Requested_Stop')
        self.assertFalse(solver.last_diagnostics['success'])
        self.assertLessEqual(result.objective_value,.9*4.)
        self.assertLessEqual(result.constraint_violation,1e-5)
        # Explicit settling may accept a good initialization without artificial
        # improvement; it does not make an optimizer convergence claim.
        problem.variables['x']['bounds']=[3.,4.];problem.initial_guess['x']=3.
        result=solver.solve(problem,seed_settled=True)
        self.assertEqual(result.status,'feasible_early_stop')
        self.assertGreaterEqual(result.optimum['x'],3.)
        self.assertEqual(solver.last_diagnostics['policy_stop_reason'],'verified_settled_seed')

    def test_pcc_public_evidence_chain_and_mathematical_verification(self):
        suffix = uuid4().hex
        root = ROOT / 'runs/scientific_optimization_tests' / suffix
        Store(root).create(project())
        design = example_design()
        value = session('family_mujoco', design, design_space(design))
        value['run_id'] = 'optimization-' + suffix
        value['task']['environment']['data']['external_forces'] = []
        value['policy']['budget'].update(tool_calls=3, backend_solves=0)
        value['policy']['timeout_s'] = 30.0
        value['policy']['tool_bindings'].update({
            'optimization.assemble': '1.0.0',
            'optimization.solve': '1.0.0',
        })
        host = Host(root, value['run_id'], reg=self.reg)
        host.create(value)
        configuration = {'segments': {
            'near': {'curvature_y_rad_m': 0.0, 'curvature_z_rad_m': 0.0},
            'far': {'curvature_y_rad_m': 0.0, 'curvature_z_rad_m': 0.0},
        }}
        assemble = host.invoke({
            'request_id': 'assemble-pcc', 'tool_id': 'optimization.assemble',
            'tool_version': '1.0.0', 'reason': 'Assemble trusted PCC reach mathematics.',
            'arguments': {
                'assembler': {
                    'extension_id': 'optimization_assembler.pcc_reach', 'version': '1.0.0',
                    'parameters': {'contract': 'family.pcc_reach_assembler_parameters',
                                   'version': '1.0.0', 'data': {'configuration': configuration}},
                },
                'specification': {
                    'variables': ['components/near/length_m'],
                    'objectives': [{'template_id': 'tip_position_error_squared'}],
                    'constraints': [{'template_id': 'authorized_design_bounds'}],
                },
            },
        })
        self.assertEqual(assemble['execution_status'], 'completed', assemble)
        summary = host.store.artifact(assemble['output'])
        solve = host.invoke({
            'request_id': 'solve-pcc', 'tool_id': 'optimization.solve',
            'tool_version': '1.0.0', 'reason': 'Solve trusted PCC reach mathematics.',
            'arguments': {'problem': summary['problem']},
        })
        self.assertEqual(solve['execution_status'], 'completed', solve)
        result = host.store.artifact(solve['output'])
        self.assertEqual(result['problem_reference'], summary['problem'])
        self.assertIsNotNone(result['solver_evidence'])
        length = result['optimum']['components/near/length_m']
        changed = design.model_dump(mode='json')
        next(item for item in changed['components'] if item['id'] == 'near')['length_m'] = length
        local_tip = pcc_forward(changed, configuration['segments'], samples_per_segment=2)['tip_position_m']
        assembly = value['task']['environment']['data']
        rotation = quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
        world_tip = rotation @ local_tip + np.asarray(assembly['mount']['position_m'])
        target = np.asarray(value['task']['goal']['data']['target_m'])
        verified = float(np.sum((world_tip - target) ** 2))
        initial = pcc_forward(design, configuration['segments'], samples_per_segment=2)['tip_position_m']
        initial_world = rotation @ initial + np.asarray(assembly['mount']['position_m'])
        self.assertAlmostEqual(result['objective_value'], verified, places=11)
        self.assertLessEqual(verified, float(np.sum((initial_world - target) ** 2)))
        self.assertEqual(host.store.remaining(host.run_id)['used']['backend_solves'], 0)
        with self.assertRaises(ValidationError):
            PCCReachAssemblerParameters.model_validate({
                'configuration': configuration, 'target_m': [0, 0, 0],
            })

    def test_gvs_inverse_shape_and_inverse_tip_static(self):
        design, shape_session = mathematical_session()
        model_binding = Binding(
            extension_id='model.gvs',
            parameters=Payload(contract='family.gvs_model', data={}),
        )
        model = self.reg.mathematical_model(model_binding)
        context = SystemContext(x0=[], u0=[], scene=shape_session.task.environment)
        tendon_paths = ['tendon_tensions_n/' + tendon.id for tendon in design.tendons]
        shape_binding = Binding(
            extension_id='optimization_assembler.gvs_inverse',
            parameters=Payload(
                contract='family.gvs_inverse_assembler_parameters',
                data={'template': 'inverse_shape', 'q_target': Q_TARGET.tolist()},
            ),
        )
        shape_parameters = self.reg.bind(shape_binding, 'optimization_assembler')[1]
        shape_space = gvs_authorization(
            shape_session.robot, design_space(design).parameters, shape_parameters
        )
        shape_problem = assemble_optimization(
            self.reg, shape_binding, task=shape_session.task, robot=shape_session.robot,
            space=shape_space, mathematical_model=model,
            specification=OptimizationSpecification(
                variables=tendon_paths,
                objectives=[ObjectiveSelection(template_id='inverse_shape_static')],
                constraints=[ConstraintSelection(template_id='tendon_force_bounds')],
                initial_guess={name: 0.5 for name in tendon_paths},
            ), context=context,
        )
        shape_result = IpoptSolver({'tolerance': 1e-10}).solve(shape_problem)
        self.assertEqual(shape_result.status, 'converged')
        self.assertLess(math.sqrt(shape_result.objective_value), 1e-5)
        for tendon in design.tendons:
            value = shape_result.optimum['tendon_tensions_n/' + tendon.id]
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, tendon.force_limit_n)
            self.assertEqual(
                shape_problem.variables['tendon_tensions_n/' + tendon.id]['bounds'],
                [0.0, tendon.force_limit_n],
            )

        _, tip_session = mathematical_session(target_from_q=True)
        coordinates = coordinate_order(design)
        q_paths = ['q/' + name for name in coordinates]
        tip_binding = Binding(
            extension_id='optimization_assembler.gvs_inverse',
            parameters=Payload(
                contract='family.gvs_inverse_assembler_parameters',
                data={'template': 'inverse_tip_static'},
            ),
        )
        tip_parameters = self.reg.bind(tip_binding, 'optimization_assembler')[1]
        tip_space = gvs_authorization(tip_session.robot, design_space(design).parameters, tip_parameters)
        initial_guess = {name: 0.0 for name in q_paths}
        initial_guess.update(dict(zip(tendon_paths, KNOWN_TENSIONS.tolist())))
        tip_problem = assemble_optimization(
            self.reg, tip_binding, task=tip_session.task, robot=tip_session.robot,
            space=tip_space, mathematical_model=model,
            specification=OptimizationSpecification(
                variables=q_paths + tendon_paths,
                objectives=[ObjectiveSelection(template_id='tip_position_error_squared')],
                constraints=[
                    ConstraintSelection(template_id='static_equilibrium'),
                    ConstraintSelection(template_id='tendon_force_bounds'),
                ],
                initial_guess=initial_guess,
            ), context=SystemContext(x0=[], u0=[], scene=tip_session.task.environment),
        )
        tip_result = IpoptSolver({'max_iterations': 500, 'tolerance': 1e-9}).solve(tip_problem)
        self.assertEqual(tip_result.status, 'converged')
        self.assertLess(tip_result.constraint_violation, 1e-8)
        q_solution = [tip_result.optimum[name] for name in q_paths]
        local_tip = gvs_forward(design, q_solution, samples_per_segment=2)['tip_position_m']
        assembly = tip_session.task.environment.data
        rotation = quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
        final_tip = rotation @ local_tip + np.asarray(assembly['mount']['position_m'])
        target = np.asarray(tip_session.task.goal.data['target_m'])
        straight = gvs_forward(design, np.zeros(len(q_paths)), samples_per_segment=2)['tip_position_m']
        initial_tip = rotation @ straight + np.asarray(assembly['mount']['position_m'])
        self.assertLess(np.linalg.norm(final_tip - target), 1e-6)
        self.assertLess(np.linalg.norm(final_tip - target), np.linalg.norm(initial_tip - target))
        with self.assertRaises(ValidationError):
            GVSInverseAssemblerParameters(
                template='inverse_tip_static', q_target=[0.0] * len(q_paths)
            )


if __name__ == '__main__':
    unittest.main()
