"""Focused mathematical verification for variable-strain GVS dynamics."""

import unittest

import numpy as np

from examples.platform_tendon_family import example_design
from extensions.tendon_family.contracts import Design, GVSModelParameters
from extensions.tendon_family.gvs import (
    constitutive_forces,
    coordinate_order,
    evaluate_dynamics,
    forward_kinematics as gvs_forward_kinematics,
    mass_matrix,
    tendon_kinematics,
    tendon_lengths,
)
from extensions.tendon_family.pcc import forward_kinematics as pcc_forward_kinematics


class GVSDynamicsTests(unittest.TestCase):
    def setUp(self):
        self.design = example_design()
        self.parameters = GVSModelParameters(
            integration_steps_per_segment=16,
            quadrature_points_per_segment=4,
            finite_difference_step=1e-6,
        )

    def test_coordinate_order_is_four_modes_per_flexible_segment(self):
        self.assertEqual(
            coordinate_order(self.design),
            [
                'near.kappa_y_0',
                'near.kappa_y_1',
                'near.kappa_z_0',
                'near.kappa_z_1',
                'far.kappa_y_0',
                'far.kappa_y_1',
                'far.kappa_z_0',
                'far.kappa_z_1',
            ],
        )

    def test_constant_gvs_mode_matches_spatial_pcc(self):
        q = np.array([0.8, 0.0, -0.5, 0.0, -0.35, 0.0, 0.6, 0.0])
        gvs = gvs_forward_kinematics(
            self.design,
            q,
            samples_per_segment=11,
            integration_steps_per_segment=16,
        )
        pcc = pcc_forward_kinematics(
            self.design,
            {
                'near': {
                    'curvature_y_rad_m': 0.8,
                    'curvature_z_rad_m': -0.5,
                },
                'far': {
                    'curvature_y_rad_m': -0.35,
                    'curvature_z_rad_m': 0.6,
                },
            },
            samples_per_segment=11,
        )
        np.testing.assert_allclose(
            gvs['tip_transform'],
            pcc['tip_transform'],
            rtol=0.0,
            atol=2e-12,
        )

    def test_natural_curvature_is_zero_elastic_force_reference(self):
        value = self.design.model_dump(mode='json')
        natural = {
            'near': (0.4, -0.25),
            'far': (-0.15, 0.3),
        }
        for component in value['components']:
            if component['id'] in natural:
                component['natural_curvature_rad_m'] = natural[component['id']]
        design = Design.model_validate(value)
        q = np.array([
            0.4, 0.0, -0.25, 0.0,
            -0.15, 0.0, 0.3, 0.0,
        ])
        elastic, _ = constitutive_forces(design, q, np.zeros(8), 4)
        np.testing.assert_allclose(elastic, np.zeros(8), rtol=0.0, atol=1e-14)

    def test_mass_matrix_is_finite_symmetric_positive_definite(self):
        q = np.array([0.3, 0.1, -0.2, 0.05, 0.15, -0.08, 0.25, 0.04])
        mass = mass_matrix(self.design, q, self.parameters)
        self.assertTrue(np.all(np.isfinite(mass)))
        np.testing.assert_allclose(mass, mass.T, rtol=0.0, atol=1e-14)
        self.assertGreater(float(np.min(np.linalg.eigvalsh(mass))), 0.0)

    def test_tendon_force_has_virtual_work_sign(self):
        q = np.array([0.25, 0.08, -0.18, 0.04, 0.12, -0.05, 0.2, 0.03])
        names, _, jacobian = tendon_kinematics(self.design, q, self.parameters)
        tensions = np.linspace(0.2, 0.7, len(names))
        direction = np.array([0.3, -0.2, 0.1, 0.25, -0.15, 0.2, 0.05, -0.1])
        epsilon = 2e-6
        directional_length_change = (
            tendon_lengths(self.design, q + epsilon * direction, self.parameters)
            - tendon_lengths(self.design, q - epsilon * direction, self.parameters)
        ) / (2.0 * epsilon)
        generalized_tendon_force = -jacobian.T @ tensions
        self.assertAlmostEqual(
            float(generalized_tendon_force @ direction),
            float(-tensions @ directional_length_change),
            places=9,
        )

    def test_dynamics_solve_has_zero_stationary_bias_and_small_residual(self):
        q = np.array([0.2, 0.06, -0.1, 0.03, 0.12, -0.04, 0.18, 0.05])
        qdot = np.zeros(8)
        tensions = {tendon.id: 0.25 for tendon in self.design.tendons}
        result = evaluate_dynamics(
            self.design,
            q,
            qdot,
            tensions,
            gravity_robot_base_m_s2=np.array([0.0, 0.0, -9.81]),
            parameters=self.parameters,
            samples_per_segment=7,
        )
        np.testing.assert_allclose(
            result['velocity_bias'], np.zeros(8), rtol=0.0, atol=0.0
        )
        self.assertTrue(np.all(np.isfinite(result['qdd'])))
        residual = (
            result['mass_matrix'] @ result['qdd']
            + result['velocity_bias']
            + result['elastic_force']
            + result['damping_force']
            - result['tendon_generalized_force']
            - result['gravity_force']
        )
        self.assertLess(float(np.linalg.norm(residual)), 1e-10)


if __name__ == '__main__':
    unittest.main()
