"""Focused verification of CasADi GVS export, AD linearization, and LQR."""

import math
import unittest

import numpy as np

from examples.platform_tendon_family import example_design, design_space, session
from extensions.tendon_family.contracts import GVSModelParameters, LQRParameters
from extensions.tendon_family.gvs import GVSModel, evaluate_dynamics, tendon_kinematics
from extensions.tendon_family.gvs_casadi import (
    CasadiLinearizer,
    ContinuousLQRController,
    evaluate_system,
    expression_from_system,
    functions_for,
)
from schemas.platform import Payload, RobotDescription
from schemas.platform_math import SystemContext
from tools.platform_registry import registry


class GVSCasadiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = example_design()
        raw = session('family_mujoco', cls.design, design_space(cls.design))
        environment = raw['task']['environment']
        environment['data']['external_forces'] = []
        # The fixture equilibrium below uses gravity parallel to the straight arm.
        environment['data']['mount']['quaternion_wxyz'] = [
            math.sqrt(0.5), 0.0, math.sqrt(0.5), 0.0
        ]
        cls.robot = RobotDescription.model_validate(raw['robot'])
        cls.scene = Payload.model_validate(environment)
        cls.parameters = GVSModelParameters(
            integration_steps_per_segment=4,
            quadrature_points_per_segment=2,
            finite_difference_step=1e-6,
        )
        # Precomputed static root for this focused fixture; no equilibrium solver
        # is part of the production implementation.
        cls.equilibrium_q = [
            -0.00428001826600311,
            -0.00037966415427626395,
            -0.0020811732603514266,
            -0.00016802920958824597,
            -0.03066654799927823,
            -0.012506238812556515,
            -0.008499266522646117,
            -0.005605600658935161,
        ]
        cls.system = GVSModel(cls.parameters).build_system(
            cls.robot,
            cls.parameters,
            None,
            SystemContext(
                x0=cls.equilibrium_q + [0.0] * 8,
                u0=[0.0] * len(cls.design.tendons),
                scene=cls.scene,
            ),
        )
        cls.functions = functions_for(expression_from_system(cls.system))

    def test_casadi_terms_match_numpy_reference(self):
        q = np.array([0.2, 0.06, -0.1, 0.03, 0.12, -0.04, 0.18, 0.05])
        qdot = np.array([0.01, -0.02, 0.015, -0.005, 0.008, -0.01, 0.012, -0.006])
        tensions = np.linspace(0.2, 0.45, len(self.design.tendons))
        expression = expression_from_system(self.system)
        symbolic = self.functions.evaluate(np.r_[q, qdot], tensions)
        numeric = evaluate_dynamics(
            self.design,
            q,
            qdot,
            {tendon.id: tensions[index] for index, tendon in enumerate(self.design.tendons)},
            np.asarray(expression.gravity_robot_base_m_s2),
            self.parameters,
            samples_per_segment=3,
        )
        for name, atol, rtol in [
            ('mass_matrix', 2e-12, 2e-5),
            ('elastic_force', 1e-14, 1e-10),
            ('damping_force', 1e-14, 1e-10),
            ('gravity_force', 2e-10, 2e-5),
            ('tendon_generalized_force', 2e-10, 3e-5),
            ('tendon_lengths_m', 1e-13, 1e-12),
            ('qdd', 2e-2, 3e-6),
        ]:
            np.testing.assert_allclose(
                symbolic[name].reshape(np.asarray(numeric[name]).shape),
                numeric[name],
                atol=atol,
                rtol=rtol,
            )

    def test_tendon_jacobian_uses_ad_and_matches_reference(self):
        q = np.array([0.11, -0.03, 0.08, 0.02, -0.07, 0.04, 0.09, -0.01])
        _, _, numeric = tendon_kinematics(self.design, q, self.parameters)
        symbolic = self.functions.evaluate(np.r_[q, np.zeros(8)], np.zeros(6))
        np.testing.assert_allclose(
            symbolic['tendon_length_jacobian'], numeric, atol=8e-11, rtol=4e-5
        )

    def test_dynamic_system_order_context_and_xdot(self):
        expected = [
            'near.kappa_y_0', 'near.kappa_y_1',
            'near.kappa_z_0', 'near.kappa_z_1',
            'far.kappa_y_0', 'far.kappa_y_1',
            'far.kappa_z_0', 'far.kappa_z_1',
        ]
        self.assertEqual([item.name for item in self.system.state_definition[:8]], expected)
        self.assertEqual(
            [item.name for item in self.system.state_definition[8:]],
            [name + '.rate' for name in expected],
        )
        self.assertEqual(
            [item.entity for item in self.system.input_definition],
            [tendon.id for tendon in self.design.tendons],
        )
        self.assertEqual(self.system.x0, self.equilibrium_q + [0.0] * 8)
        self.assertEqual(self.system.u0, [0.0] * 6)
        self.assertEqual((self.system.time_domain, self.system.timestep), ('continuous', None))
        result = self.functions.evaluate(self.system.x0, self.system.u0)
        np.testing.assert_allclose(result['xdot'][:8, 0], self.system.x0[8:], atol=0, rtol=0)
        np.testing.assert_allclose(result['xdot'][8:, 0], result['qdd'][:, 0], atol=0, rtol=0)
        parsed = registry().parse(self.system.dynamics)
        self.assertEqual(parsed.symbolic_type, 'MX')

    def test_ad_linearization_matches_finite_difference(self):
        linear = CasadiLinearizer().linearize(self.system)
        x0 = np.asarray(self.system.x0)
        u0 = np.asarray(self.system.u0)
        h = 2e-6
        A_fd = np.column_stack([
            (evaluate_system(self.system, x0 + h * np.eye(len(x0))[i], u0)
             - evaluate_system(self.system, x0 - h * np.eye(len(x0))[i], u0)) / (2 * h)
            for i in range(len(x0))
        ])
        B_fd = np.column_stack([
            (evaluate_system(self.system, x0, u0 + h * np.eye(len(u0))[i])
             - evaluate_system(self.system, x0, u0 - h * np.eye(len(u0))[i])) / (2 * h)
            for i in range(len(u0))
        ])
        np.testing.assert_allclose(linear.A, A_fd, atol=0.08, rtol=3e-5)
        np.testing.assert_allclose(linear.B, B_fd, atol=0.02, rtol=3e-5)
        np.testing.assert_allclose(linear.drift, evaluate_system(self.system, x0, u0), atol=1e-12)

    def test_lqr_equilibrium_gain_and_bounded_tendon_command(self):
        linear = CasadiLinearizer().linearize(self.system)
        limits = [tendon.force_limit_n for tendon in self.design.tendons]
        controller = ContinuousLQRController(LQRParameters(
            Q=np.eye(16).tolist(),
            R=np.eye(6).tolist(),
            tendon_order=[tendon.id for tendon in self.design.tendons],
            force_limits_n=limits,
            equilibrium_tolerance=1e-8,
        ))
        K = controller.configure_model(linear)
        self.assertEqual(K.shape, (6, 16))
        eigenvalues = np.linalg.eigvals(np.asarray(linear.A) - np.asarray(linear.B) @ K)
        self.assertLess(float(np.max(eigenvalues.real)), 0.0)
        state = np.asarray(linear.x0) + 0.02 * K[0] / np.linalg.norm(K[0])
        command = controller.command(0.0, {'state': state.tolist()})
        self.assertEqual(command.tendon_order, [tendon.id for tendon in self.design.tendons])
        self.assertTrue(any(command.saturated))
        self.assertTrue(all(0 <= value <= limit for value, limit in zip(command.tendon_tensions_n, limits)))
        with self.assertRaisesRegex(ValueError, 'NOT_EQUILIBRIUM'):
            controller.configure_model(linear.model_copy(update={'drift': [0.01] + [0.0] * 15}))


if __name__ == '__main__':
    unittest.main()
