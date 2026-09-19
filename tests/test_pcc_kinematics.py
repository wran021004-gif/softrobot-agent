"""Focused mathematical tests for PCC kinematics."""

import math
import unittest

import numpy as np

from extensions.tendon_family.pcc import (
    forward_kinematics,
    sample_backbone,
    segment_transform,
    tip_position,
)


class PCCSegmentKinematicsTests(unittest.TestCase):

    def test_zero_curvature_is_straight_segment(self):
        transform = segment_transform(
            length_m=0.3,
            curvature_y_rad_m=0.0,
            curvature_z_rad_m=0.0,
        )

        expected = np.eye(4)
        expected[0, 3] = 0.3

        np.testing.assert_allclose(
            transform,
            expected,
            rtol=0.0,
            atol=1e-12,
        )

    def test_positive_z_curvature_is_planar_circle(self):
        length = 0.3
        curvature = 2.0
        theta = curvature * length

        transform = segment_transform(
            length_m=length,
            curvature_y_rad_m=0.0,
            curvature_z_rad_m=curvature,
        )

        expected_position = np.array(
            [
                math.sin(theta) / curvature,
                (1.0 - math.cos(theta)) / curvature,
                0.0,
            ]
        )

        np.testing.assert_allclose(
            transform[:3, 3],
            expected_position,
            rtol=0.0,
            atol=1e-12,
        )

    def test_positive_y_curvature_bends_toward_negative_z(self):
        length = 0.3
        curvature = 2.0
        theta = curvature * length

        transform = segment_transform(
            length_m=length,
            curvature_y_rad_m=curvature,
            curvature_z_rad_m=0.0,
        )

        expected_position = np.array(
            [
                math.sin(theta) / curvature,
                0.0,
                -(1.0 - math.cos(theta)) / curvature,
            ]
        )

        np.testing.assert_allclose(
            transform[:3, 3],
            expected_position,
            rtol=0.0,
            atol=1e-12,
        )

    def test_rotation_remains_valid_for_spatial_bending(self):
        transform = segment_transform(
            length_m=0.27,
            curvature_y_rad_m=1.3,
            curvature_z_rad_m=-0.8,
        )

        rotation = transform[:3, :3]

        np.testing.assert_allclose(
            rotation.T @ rotation,
            np.eye(3),
            rtol=0.0,
            atol=1e-12,
        )

        self.assertAlmostEqual(
            np.linalg.det(rotation),
            1.0,
            places=12,
        )

    def test_near_zero_curvature_is_continuous(self):
        straight = tip_position(
            length_m=0.3,
            curvature_y_rad_m=0.0,
            curvature_z_rad_m=0.0,
        )

        almost_straight = tip_position(
            length_m=0.3,
            curvature_y_rad_m=1e-10,
            curvature_z_rad_m=-2e-10,
        )

        np.testing.assert_allclose(
            almost_straight,
            straight,
            rtol=0.0,
            atol=1e-9,
        )

    def test_backbone_contains_base_and_tip(self):
        points = sample_backbone(
            length_m=0.3,
            curvature_y_rad_m=0.7,
            curvature_z_rad_m=-0.4,
            samples=31,
        )

        self.assertEqual(points.shape, (31, 3))

        np.testing.assert_allclose(
            points[0],
            np.zeros(3),
            rtol=0.0,
            atol=1e-12,
        )

        np.testing.assert_allclose(
            points[-1],
            tip_position(0.3, 0.7, -0.4),
            rtol=0.0,
            atol=1e-12,
        )

class PCCRobotKinematicsTests(unittest.TestCase):

    def test_current_two_segment_design_straight_configuration(self):
        from examples.platform_tendon_family import example_design

        design = example_design()

        result = forward_kinematics(
            design=design,
            configuration={
                "near": {
                    "curvature_y_rad_m": 0.0,
                    "curvature_z_rad_m": 0.0,
                },
                "far": {
                    "curvature_y_rad_m": 0.0,
                    "curvature_z_rad_m": 0.0,
                },
            },
            samples_per_segment=21,
        )

        self.assertEqual(
            result["chain"],
            (
                "near",
                "mid_guide",
                "connector",
                "far",
                "payload",
            ),
        )

        # Current example geometry:
        #
        # near                 0.160 m
        # connector offset    0.002 m
        # far-base offset     0.012 m
        # far                  0.120 m
        # payload->tip offset 0.014 m
        #
        # total straight tip x = 0.308 m
        np.testing.assert_allclose(
            result["tip_position_m"],
            np.array([0.308, 0.0, 0.0]),
            rtol=0.0,
            atol=1e-12,
        )

        np.testing.assert_allclose(
            result["segment_transforms"]["near"]["base"][:3, 3],
            np.array([0.0, 0.0, 0.0]),
            rtol=0.0,
            atol=1e-12,
        )

        np.testing.assert_allclose(
            result["segment_transforms"]["near"]["tip"][:3, 3],
            np.array([0.160, 0.0, 0.0]),
            rtol=0.0,
            atol=1e-12,
        )

        np.testing.assert_allclose(
            result["segment_transforms"]["far"]["base"][:3, 3],
            np.array([0.174, 0.0, 0.0]),
            rtol=0.0,
            atol=1e-12,
        )

        np.testing.assert_allclose(
            result["segment_transforms"]["far"]["tip"][:3, 3],
            np.array([0.294, 0.0, 0.0]),
            rtol=0.0,
            atol=1e-12,
        )

    def test_two_segment_spatial_configuration_is_finite(self):
        from examples.platform_tendon_family import example_design

        result = forward_kinematics(
            design=example_design(),
            configuration={
                "near": {
                    "curvature_y_rad_m": 1.2,
                    "curvature_z_rad_m": 0.5,
                },
                "far": {
                    "curvature_y_rad_m": -0.7,
                    "curvature_z_rad_m": 1.0,
                },
            },
            samples_per_segment=31,
        )

        self.assertTrue(
            np.all(np.isfinite(result["tip_transform"]))
        )

        rotation = result["tip_transform"][:3, :3]

        np.testing.assert_allclose(
            rotation.T @ rotation,
            np.eye(3),
            rtol=0.0,
            atol=1e-11,
        )

        self.assertAlmostEqual(
            np.linalg.det(rotation),
            1.0,
            places=11,
        )

        self.assertEqual(
            result["segment_backbones_m"]["near"].shape,
            (31, 3),
        )

        self.assertEqual(
            result["segment_backbones_m"]["far"].shape,
            (31, 3),
        )

    def test_configuration_must_cover_every_flexible_segment(self):
        from examples.platform_tendon_family import example_design

        with self.assertRaisesRegex(
            ValueError,
            "missing flexible segments",
        ):
            forward_kinematics(
                design=example_design(),
                configuration={
                    "near": {
                        "curvature_y_rad_m": 0.0,
                        "curvature_z_rad_m": 0.0,
                    },
                },
            )
if __name__ == "__main__":
    unittest.main()