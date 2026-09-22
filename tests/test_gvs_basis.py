"""Focused RobotIR feature, resolved basis, and state mapping checks."""

from copy import deepcopy
import unittest

import casadi as ca
import numpy as np

from examples.platform_tendon_family import example_design, design_space, session
from extensions.tendon_family.contracts import (Design, GVSBasisSpecification,
    GVSContinuousDynamicsExpression, GVSModelParameters)
from extensions.tendon_family.gvs import GVSModel, coordinate_order, evaluate_dynamics, forward_kinematics
from extensions.tendon_family.gvs_basis import resolve_basis
from extensions.tendon_family.gvs_casadi import CasadiLinearizer, GVSStaticCasadiExpressions, functions_for
from extensions.tendon_family.gvs_projection import discretize, project
from schemas.platform import Payload, RobotDescription
from schemas.platform_math import SystemContext


STRUCTURAL = GVSBasisSpecification(strategy='structural_linear')


def fixture(segment_count):
    def station(s, width=.01):
        return dict(s=s, section=dict(kind='ellipse',
            parameters=dict(semi_y_m=width, semi_z_m=.008), angle_rad=.2))

    def segment(name, parent, length):
        return dict(id=name, kind='flexible_segment',
            connection=dict(part=parent, s=0.0 if parent == 'fixed_base' else 1.0),
            length_m=length, sections=[station(0.0)], interpolation='step',
            physics=dict(mode='material', density_kg_m3=1000., young_pa=5e6,
                         bending_viscosity_nm2_s=(.0005, .0007)))

    first = segment('section_a', 'fixed_base', .16)
    components = [first]
    if segment_count >= 2:
        first['sections'].append(station(.72, .008))
        second = segment('section_b', first['id'], .12)
        components.append(second)
    if segment_count == 3:
        connector = dict(id='coupler', kind='rigid_connector',
            connection=dict(part=first['id'], s=1.0), mass_kg=.002,
            inertia_com_local_kg_m2=[[1e-7, 0., 0.], [0., 1e-7, 0.], [0., 0., 1e-7]],
            envelope_halfsize_m=(.005, .005, .005))
        second['connection']['part'] = connector['id']
        second['connection']['s'] = 0.0
        third = segment('section_c', second['id'], .1)
        components = [first, connector, second, third]

    points = [dict(attachment=dict(part='fixed_base', s=0.,
                                   position_m=(0., .015, 0.)), role='start')]
    if segment_count == 2:
        guides = [('section_a', .37)]
    elif segment_count == 3:
        guides = [('section_a', .29), ('section_b', .61), ('section_c', .42)]
    else:
        guides = []
    for part, position in guides:
        points.append(dict(attachment=dict(part=part, s=position,
                                           position_m=(0., .015, 0.)), role='guide'))
    points.append(dict(attachment=dict(part=components[-1]['id'], s=1.0,
                                       position_m=(0., .015, 0.)), role='anchor'))
    return Design(id='basis_fixture', components=components,
        tendons=[dict(id='cable_a', points=points, diameter_m=.001,
                      length_servo_gain_n_m=900., force_limit_n=5.)],
        actuators=[dict(id='motor_a', transmission=[dict(tendon='cable_a', ratio=1.)],
                        limits=(-.01, .01), velocity_limit=.02)],
        tip=dict(part=components[-1]['id'], s=1.0))


def cell_physics(design, count=10):
    parts = []
    entity_map = {}
    dofs = []
    for component in design.components:
        if component.kind != 'flexible_segment':
            continue
        bodies = []
        for index in range(count):
            indices = [len(dofs), len(dofs) + 1]
            dofs.extend(indices)
            bodies.append(len(parts))
            parts.append(dict(entity=f'{component.id}_{index}',
                              length_m=component.length_m / count,
                              dofs=indices, section_axis_rad=.2))
        entity_map[component.id] = dict(bodies=bodies)
    return dict(parts=parts, entity_map=entity_map, dofs=dofs)


class GVSBasisTests(unittest.TestCase):
    def test_robotir_features_resolve_one_two_and_three_segments(self):
        expected = [
            [('section_a', (0.0, 1.0))],
            [('section_a', (0.0, .37, .72, 1.0)), ('section_b', (0.0, 1.0))],
            [('section_a', (0.0, .29, .72, 1.0)),
             ('section_b', (0.0, .61, 1.0)),
             ('section_c', (0.0, .42, 1.0))],
        ]
        for count, locations in enumerate(expected, 1):
            with self.subTest(segments=count):
                design = fixture(count)
                resolved = resolve_basis(design, STRUCTURAL)
                self.assertEqual([(segment.segment, segment.knots)
                                  for segment in resolved.segments], locations)
                self.assertEqual(resolved.dimension, 2 * sum(len(knots) for _, knots in locations))
                self.assertEqual(coordinate_order(design, STRUCTURAL), resolved.coordinate_order)
                self.assertEqual(resolve_basis(design, STRUCTURAL).model_dump(mode='json'),
                                 resolved.model_dump(mode='json'))
        kinds = resolve_basis(fixture(3), STRUCTURAL).segments[0].locations[-1].kinds
        self.assertIn('rigid_attachment', kinds)

    def test_discretize_and_project_use_identical_basis(self):
        for count in (1, 2, 3):
            with self.subTest(segments=count):
                design = fixture(count)
                physics = cell_physics(design)
                n = resolve_basis(design, STRUCTURAL).dimension
                q = np.linspace(-.2, .3, n)
                qdot = np.linspace(.03, -.04, n)
                cells, rates = discretize(physics, design, q, qdot, STRUCTURAL)
                result = project(physics, design, cells, rates, STRUCTURAL)
                np.testing.assert_allclose(result['q_gvs'], q, atol=1e-12)
                np.testing.assert_allclose(result['qdot_gvs'], qdot, atol=1e-12)
                self.assertLess(result['projection_residual_max_rad_m'], 1e-12)

    def test_casadi_and_numpy_share_structural_order_and_kinematics(self):
        design = fixture(2)
        parameters = GVSModelParameters(basis=STRUCTURAL, integration_steps_per_segment=4,
                                        quadrature_points_per_segment=3)
        resolved = resolve_basis(design, STRUCTURAL)
        expression = GVSContinuousDynamicsExpression(
            design=design, parameters=parameters, gravity_robot_base_m_s2=(0., 0., 0.),
            coordinate_order=resolved.coordinate_order, tendon_order=['cable_a'],
            tendon_force_limits_n=[design.tendons[0].force_limit_n])
        parsed = GVSContinuousDynamicsExpression.model_validate_json(expression.model_dump_json())
        self.assertEqual(parsed.resolved_basis, resolved)
        symbolic = GVSStaticCasadiExpressions(parsed)
        tip = ca.Function('tip', [symbolic.q_symbol], [symbolic.tip_position_expression])
        q = np.linspace(-.1, .2, resolved.dimension)
        numeric = forward_kinematics(design, q, samples_per_segment=2,
                                     integration_steps_per_segment=4, basis=STRUCTURAL)
        np.testing.assert_allclose(np.asarray(tip(q)).reshape(3), numeric['tip_position_m'],
                                   atol=1e-11)

    def test_structural_dynamic_terms_match_numpy_and_casadi(self):
        value = fixture(1).model_dump(mode='json')
        transition = deepcopy(value['components'][0]['sections'][0])
        transition['s'] = .37
        transition['section']['parameters']['semi_y_m'] *= .8
        value['components'][0]['sections'].append(transition)
        design = Design.model_validate(value)
        parameters = GVSModelParameters(basis=STRUCTURAL,
                                        integration_steps_per_segment=4,
                                        quadrature_points_per_segment=5)
        order = coordinate_order(design, STRUCTURAL)
        self.assertEqual(len(order), 6)
        expression = GVSContinuousDynamicsExpression(
            design=design, parameters=parameters, gravity_robot_base_m_s2=(0., 0., 0.),
            coordinate_order=order, tendon_order=['cable_a'],
            tendon_force_limits_n=[design.tendons[0].force_limit_n])
        q = np.linspace(-.1, .2, len(order))
        symbolic = functions_for(expression).evaluate(np.r_[q, np.zeros(len(q))], [0.])
        numeric = evaluate_dynamics(design, q, np.zeros(len(q)), {'cable_a': 0.},
                                    [0., 0., 0.], parameters, samples_per_segment=2)
        np.testing.assert_allclose(symbolic['mass_matrix'], numeric['mass_matrix'], atol=2e-12)
        np.testing.assert_allclose(symbolic['elastic_force'].reshape(-1),
                                   numeric['elastic_force'], atol=1e-14)

        example = example_design()
        raw = session('family_mujoco', example, design_space(example))
        raw['robot']['structure']['data'] = design.model_dump(mode='json')
        raw['task']['environment']['data']['external_forces'] = []
        raw['task']['environment']['data']['environment']['gravity_m_s2'] = [0., 0., 0.]
        system = GVSModel(parameters).build_system(
            RobotDescription.model_validate(raw['robot']), parameters, None,
            SystemContext(x0=np.r_[q, np.zeros(len(q))].tolist(), u0=[0.],
                          scene=Payload.model_validate(raw['task']['environment'])))
        self.assertEqual([item.name for item in system.state_definition],
                         order + [name + '.rate' for name in order])
        self.assertEqual(system.dynamics.data['resolved_basis']['dimension'], len(order))
        linear = CasadiLinearizer().linearize(system)
        self.assertEqual(np.shape(linear.A), (2 * len(order), 2 * len(order)))
        self.assertEqual(np.shape(linear.B), (2 * len(order), 1))


if __name__ == '__main__':
    unittest.main()
