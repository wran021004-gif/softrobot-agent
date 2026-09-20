"""Constant-curvature PCC kinematics for tendon-driven continuum robots.

This module contains only deterministic mathematical kinematics.

It does not:
- read platform sessions;
- start MATLAB or MuJoCo;
- model tendon forces;
- solve static equilibrium;
- perform control;
- define platform contracts.

Coordinate convention
---------------------
Each undeformed flexible segment extends along its local +x axis.

The constant curvature vector is represented by two components:

    curvature_y_rad_m : curvature about the local +y axis
    curvature_z_rad_m : curvature about the local +z axis

following the right-hand rule.

These inputs are the actual total geometric curvature.  They are not
increments relative to ``Segment.natural_curvature_rad_m``; natural curvature
belongs to constitutive mechanics and is intentionally not added here.

Therefore:

- positive curvature about +y bends the local +x tangent toward -z;
- positive curvature about +z bends the local +x tangent toward +y.

No torsion, shear, or axial extension is included in this PCC model.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
import numpy as np


_EPS_THETA = 1e-7


def _finite_scalar(name: str, value: float) -> float:
    """Convert one scalar to float and require it to be finite."""
    value = float(value)

    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")

    return value


def skew(vector: np.ndarray) -> np.ndarray:
    """Return the 3x3 skew-symmetric matrix of a 3-vector.

    For vector ``w``:

        skew(w) @ v == np.cross(w, v)
    """
    w = np.asarray(vector, dtype=float)

    if w.shape != (3,):
        raise ValueError("skew requires a vector with shape (3,)")

    if not np.all(np.isfinite(w)):
        raise ValueError("skew requires finite values")

    x, y, z = w

    return np.array(
        [
            [0.0, -z, y],
            [z, 0.0, -x],
            [-y, x, 0.0],
        ],
        dtype=float,
    )


def _se3_coefficients(curvature_norm: float, s_m: float) -> tuple[float, float, float]:
    """Return stable coefficients for the constant-strain SE(3) exponential.

    Let

        k = ||curvature||
        theta = k * s

    then

        R = I + A * Omega + B * Omega^2

    and

        p = (s I + B Omega + C Omega^2) e_x

    where Omega = skew(curvature_vector).

    Taylor expansions are used near the straight configuration to avoid
    division by very small curvature values.
    """
    k = curvature_norm
    s = s_m
    theta = k * s

    if abs(theta) < _EPS_THETA:
        k2 = k * k
        k4 = k2 * k2

        s2 = s * s
        s3 = s2 * s
        s4 = s2 * s2
        s5 = s4 * s
        s6 = s3 * s3
        s7 = s6 * s

        # sin(k s) / k
        a = s - k2 * s3 / 6.0 + k4 * s5 / 120.0

        # (1 - cos(k s)) / k^2
        b = s2 / 2.0 - k2 * s4 / 24.0 + k4 * s6 / 720.0

        # (k s - sin(k s)) / k^3
        c = s3 / 6.0 - k2 * s5 / 120.0 + k4 * s7 / 5040.0

        return a, b, c

    a = math.sin(theta) / k
    b = (1.0 - math.cos(theta)) / (k * k)
    c = (theta - math.sin(theta)) / (k * k * k)

    return a, b, c


def segment_pose_at(
    s_m: float,
    curvature_y_rad_m: float,
    curvature_z_rad_m: float,
) -> np.ndarray:
    """Compute the local PCC pose at arc length ``s_m``.

    Parameters
    ----------
    s_m:
        Arc length measured from the segment base, in metres.
        Must be non-negative.

    curvature_y_rad_m:
        Constant bending curvature about the segment-local +y axis,
        in rad/m.

    curvature_z_rad_m:
        Constant bending curvature about the segment-local +z axis,
        in rad/m.

    Returns
    -------
    numpy.ndarray
        Homogeneous transform with shape ``(4, 4)``:

            T = [R p]
                [0 1]

        mapping coordinates from the local frame at ``s_m`` into the
        segment base frame.

    Notes
    -----
    The underlying constant body strain is

        v = [1, 0, 0]
        w = [0, curvature_y, curvature_z]

    which means:

    - no axial extension;
    - no shear;
    - no torsion;
    - constant bending curvature.
    """
    s = _finite_scalar("s_m", s_m)
    ky = _finite_scalar("curvature_y_rad_m", curvature_y_rad_m)
    kz = _finite_scalar("curvature_z_rad_m", curvature_z_rad_m)

    if s < 0.0:
        raise ValueError("s_m must be non-negative")

    # Angular strain vector expressed in the segment-local frame.
    curvature = np.array([0.0, ky, kz], dtype=float)
    curvature_norm = float(np.linalg.norm(curvature))

    omega = skew(curvature)
    omega2 = omega @ omega

    a, b, c = _se3_coefficients(curvature_norm, s)

    identity = np.eye(3)

    rotation = identity + a * omega + b * omega2

    # The undeformed centerline tangent is local +x.
    tangent = np.array([1.0, 0.0, 0.0], dtype=float)

    translation = (
        s * identity
        + b * omega
        + c * omega2
    ) @ tangent

    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = translation

    return transform


def segment_transform(
    length_m: float,
    curvature_y_rad_m: float,
    curvature_z_rad_m: float,
) -> np.ndarray:
    """Compute the end pose of one constant-curvature PCC segment.

    This is equivalent to::

        segment_pose_at(
            s_m=length_m,
            curvature_y_rad_m=...,
            curvature_z_rad_m=...,
        )
    """
    length = _finite_scalar("length_m", length_m)

    if length <= 0.0:
        raise ValueError("length_m must be positive")

    return segment_pose_at(
        s_m=length,
        curvature_y_rad_m=curvature_y_rad_m,
        curvature_z_rad_m=curvature_z_rad_m,
    )


def sample_backbone(
    length_m: float,
    curvature_y_rad_m: float,
    curvature_z_rad_m: float,
    samples: int = 51,
) -> np.ndarray:
    """Sample centerline points along one PCC segment.

    Parameters
    ----------
    length_m:
        Segment arc length in metres.

    curvature_y_rad_m:
        Constant curvature about local +y, in rad/m.

    curvature_z_rad_m:
        Constant curvature about local +z, in rad/m.

    samples:
        Number of samples including both the base and tip.

    Returns
    -------
    numpy.ndarray
        Array with shape ``(samples, 3)``.

        Row 0 is exactly the segment base:

            [0, 0, 0]

        and the final row is the PCC tip position.
    """
    length = _finite_scalar("length_m", length_m)

    if length <= 0.0:
        raise ValueError("length_m must be positive")

    if isinstance(samples, bool) or not isinstance(samples, int):
        raise TypeError("samples must be an integer")

    if samples < 2:
        raise ValueError("samples must be at least 2")

    arc_lengths = np.linspace(0.0, length, samples)

    points = np.empty((samples, 3), dtype=float)

    for index, s_m in enumerate(arc_lengths):
        pose = segment_pose_at(
            s_m=float(s_m),
            curvature_y_rad_m=curvature_y_rad_m,
            curvature_z_rad_m=curvature_z_rad_m,
        )

        points[index] = pose[:3, 3]

    return points


def tip_position(
    length_m: float,
    curvature_y_rad_m: float,
    curvature_z_rad_m: float,
) -> np.ndarray:
    """Convenience function returning only the segment tip position."""
    return segment_transform(
        length_m=length_m,
        curvature_y_rad_m=curvature_y_rad_m,
        curvature_z_rad_m=curvature_z_rad_m,
    )[:3, 3].copy()


def quaternion_wxyz_to_rotation(
    quaternion_wxyz,
) -> np.ndarray:
    """Convert a unit quaternion in wxyz order to a 3x3 rotation matrix."""
    q = np.asarray(quaternion_wxyz, dtype=float)

    if q.shape != (4,):
        raise ValueError("quaternion_wxyz must have shape (4,)")

    if not np.all(np.isfinite(q)):
        raise ValueError("quaternion_wxyz must contain finite values")

    norm = float(np.linalg.norm(q))

    if norm <= 0.0:
        raise ValueError("quaternion_wxyz must have nonzero norm")

    if abs(norm - 1.0) > 1e-10:
        raise ValueError("quaternion_wxyz must be unit length")

    w, x, y, z = q

    return np.array(
        [
            [
                1.0 - 2.0 * (y * y + z * z),
                2.0 * (x * y - z * w),
                2.0 * (x * z + y * w),
            ],
            [
                2.0 * (x * y + z * w),
                1.0 - 2.0 * (x * x + z * z),
                2.0 * (y * z - x * w),
            ],
            [
                2.0 * (x * z - y * w),
                2.0 * (y * z + x * w),
                1.0 - 2.0 * (x * x + y * y),
            ],
        ],
        dtype=float,
    )


def rigid_transform(
    position_m,
    quaternion_wxyz=(1.0, 0.0, 0.0, 0.0),
) -> np.ndarray:
    """Construct a homogeneous rigid transform."""
    position = np.asarray(position_m, dtype=float)

    if position.shape != (3,):
        raise ValueError("position_m must have shape (3,)")

    if not np.all(np.isfinite(position)):
        raise ValueError("position_m must contain finite values")

    transform = np.eye(4)
    transform[:3, :3] = quaternion_wxyz_to_rotation(quaternion_wxyz)
    transform[:3, 3] = position

    return transform


def transform_points(
    transform: np.ndarray,
    points: np.ndarray,
) -> np.ndarray:
    """Transform row-wise 3D points by a homogeneous transform."""
    transform = np.asarray(transform, dtype=float)
    points = np.asarray(points, dtype=float)

    if transform.shape != (4, 4):
        raise ValueError("transform must have shape (4, 4)")

    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")

    rotation = transform[:3, :3]
    translation = transform[:3, 3]

    return points @ rotation.T + translation


def _parse_segment_curvature(
    segment_id: str,
    configuration: Mapping,
) -> tuple[float, float]:
    """Read one flexible segment's PCC curvature from a configuration mapping."""
    if segment_id not in configuration:
        raise ValueError(
            f"PCC configuration missing flexible segment: {segment_id}"
        )

    value = configuration[segment_id]

    if not isinstance(value, Mapping):
        raise TypeError(
            f"PCC configuration for {segment_id} must be a mapping"
        )

    allowed = {
        "curvature_y_rad_m",
        "curvature_z_rad_m",
    }

    unknown = set(value) - allowed

    if unknown:
        raise ValueError(
            f"Unknown PCC configuration fields for {segment_id}: "
            + ", ".join(sorted(unknown))
        )

    if set(value) != allowed:
        raise ValueError(
            f"PCC configuration for {segment_id} must define "
            "curvature_y_rad_m and curvature_z_rad_m"
        )

    ky = _finite_scalar(
        f"{segment_id}.curvature_y_rad_m",
        value["curvature_y_rad_m"],
    )

    kz = _finite_scalar(
        f"{segment_id}.curvature_z_rad_m",
        value["curvature_z_rad_m"],
    )

    return ky, kz


def forward_kinematics(
    design,
    configuration: Mapping,
    samples_per_segment: int = 51,
) -> dict:
    """Compute PCC forward kinematics for a serial tendon-family design.

    Parameters
    ----------
    design:
        ``family.Design`` or data accepted by that contract.

    configuration:
        Mapping from flexible-segment ID to constant curvature, for example::

            {
                "near": {
                    "curvature_y_rad_m": 1.0,
                    "curvature_z_rad_m": 0.0,
                },
                "far": {
                    "curvature_y_rad_m": 0.5,
                    "curvature_z_rad_m": -0.2,
                },
            }

    samples_per_segment:
        Number of centerline points sampled for every flexible segment.

    Returns
    -------
    dict
        Deterministic kinematic result in the robot base frame.

        Important entries are:

        ``tip_transform``
            4x4 end-effector transform.

        ``tip_position_m``
            3D tip position.

        ``component_transforms``
            Base-frame transform of every component on the serial chain.

        ``segment_transforms``
            Base and tip transforms of each flexible segment.

        ``segment_backbones_m``
            Sampled centerline of every flexible segment.

    Notes
    -----
    This function models geometry only.

    It does not infer curvature from tendon commands, forces, stiffness,
    gravity, contact, or static equilibrium.
    """
    from extensions.tendon_family.contracts import (
        Design,
        Reserved,
        Rigid,
        Segment,
    )

    parsed = (
        design
        if isinstance(design, Design)
        else Design.model_validate(design)
    )

    if not isinstance(configuration, Mapping):
        raise TypeError("configuration must be a mapping")

    if isinstance(samples_per_segment, bool) or not isinstance(
        samples_per_segment,
        int,
    ):
        raise TypeError("samples_per_segment must be an integer")

    if samples_per_segment < 2:
        raise ValueError("samples_per_segment must be at least 2")

    components = {component.id: component for component in parsed.components}

    if len(components) != len(parsed.components):
        raise ValueError("PCC design contains duplicate component IDs")

    flexible_segments = {
        component.id
        for component in parsed.components
        if isinstance(component, Segment)
    }

    unknown_configuration = set(configuration) - flexible_segments

    if unknown_configuration:
        raise ValueError(
            "PCC configuration contains unknown or non-flexible components: "
            + ", ".join(sorted(unknown_configuration))
        )

    missing_configuration = flexible_segments - set(configuration)

    if missing_configuration:
        raise ValueError(
            "PCC configuration missing flexible segments: "
            + ", ".join(sorted(missing_configuration))
        )

    # Walk from the physical tip back to the fixed base.
    #
    # PCC v1 intentionally supports one serial chain only. Branching and
    # closed-chain models must be implemented explicitly rather than being
    # silently projected onto this representation.
    chain_reverse = []
    current = parsed.tip.part
    visited = set()

    while current != "fixed_base":
        if current in visited:
            raise ValueError("PCC component graph contains a cycle")

        visited.add(current)

        component = components.get(current)

        if component is None:
            raise ValueError(
                f"PCC tip chain references unknown component: {current}"
            )

        if isinstance(component, Reserved):
            raise ValueError(
                f"PCC does not implement reserved topology: {component.kind}"
            )

        chain_reverse.append(current)
        current = component.connection.part

    chain = list(reversed(chain_reverse))

    if set(chain) != set(components):
        unused = set(components) - set(chain)

        raise ValueError(
            "PCC currently requires one serial component chain; "
            "components outside the tip ancestry: "
            + ", ".join(sorted(unused))
        )

    curvature = {
        segment_id: _parse_segment_curvature(
            segment_id,
            configuration,
        )
        for segment_id in flexible_segments
    }

    component_base_cache: dict[str, np.ndarray] = {}

    def point_pose(part_id: str, s: float) -> np.ndarray:
        """Pose of an attachment point on one component."""
        if part_id == "fixed_base":
            if abs(float(s)) > 1e-12:
                raise ValueError(
                    "fixed_base has no nonzero along-component coordinate"
                )

            return np.eye(4)

        component = components.get(part_id)

        if component is None:
            raise ValueError(
                f"Unknown attachment component: {part_id}"
            )

        base = component_base_pose(part_id)

        if isinstance(component, Segment):
            if not 0.0 <= s <= 1.0:
                raise ValueError(
                    f"Flexible-segment attachment s outside [0, 1]: {part_id}"
                )

            ky, kz = curvature[part_id]

            local = segment_pose_at(
                s_m=component.length_m * float(s),
                curvature_y_rad_m=ky,
                curvature_z_rad_m=kz,
            )

            return base @ local

        if isinstance(component, Rigid):
            if abs(float(s)) > 1e-12:
                raise ValueError(
                    f"Rigid component does not support nonzero s: {part_id}"
                )

            return base

        raise TypeError(
            f"Unsupported PCC component type: {type(component).__name__}"
        )

    def component_base_pose(component_id: str) -> np.ndarray:
        """Resolve one component frame in the robot base frame."""
        cached = component_base_cache.get(component_id)

        if cached is not None:
            return cached

        component = components[component_id]

        parent_pose = point_pose(
            component.connection.part,
            component.connection.s,
        )

        connection_pose = rigid_transform(
            component.connection.position_m,
            component.connection.quaternion_wxyz,
        )

        result = parent_pose @ connection_pose

        component_base_cache[component_id] = result

        return result

    component_transforms = {}
    segment_transforms = {}
    segment_backbones = {}

    for component_id in chain:
        component = components[component_id]

        base = component_base_pose(component_id).copy()
        component_transforms[component_id] = base

        if isinstance(component, Segment):
            ky, kz = curvature[component_id]

            local_backbone = sample_backbone(
                length_m=component.length_m,
                curvature_y_rad_m=ky,
                curvature_z_rad_m=kz,
                samples=samples_per_segment,
            )

            backbone = transform_points(
                base,
                local_backbone,
            )

            tip = point_pose(
                component_id,
                1.0,
            ).copy()

            segment_transforms[component_id] = {
                "base": base,
                "tip": tip,
            }

            segment_backbones[component_id] = backbone

    tip_parent_pose = point_pose(
        parsed.tip.part,
        parsed.tip.s,
    )

    tip_attachment = rigid_transform(
        parsed.tip.position_m,
        parsed.tip.quaternion_wxyz,
    )

    tip_transform = tip_parent_pose @ tip_attachment

    return {
        "frame": "robot_base",
        "chain": tuple(chain),
        "tip_transform": tip_transform,
        "tip_position_m": tip_transform[:3, 3].copy(),
        "component_transforms": component_transforms,
        "segment_transforms": segment_transforms,
        "segment_backbones_m": segment_backbones,
    }


def _vec3(value):
    return tuple(float(x) for x in value)


def _matrix3(value):
    return tuple(
        tuple(float(x) for x in row)
        for row in value
    )


def _pose(transform):
    from extensions.tendon_family.contracts import PCCPose

    return PCCPose(
        position_m=_vec3(transform[:3, 3]),
        rotation_matrix=_matrix3(transform[:3, :3]),
    )


class PCCModel:
    """Registered PCC kinematics provider.

    The numerical PCC implementation remains in the pure functions above.
    This class only adapts platform contracts to that mathematical kernel.
    """

    def __init__(self, parameters):
        from extensions.tendon_family.contracts import PCCModelParameters

        self.parameters = PCCModelParameters.model_validate(parameters)

    def forward(self, robot, request, registry):
        from schemas.platform import Payload
        from extensions.tendon_family.contracts import (
            Design,
            PCCForwardRequest,
            PCCKinematicsResult,
            PCCSegmentKinematics,
        )

        if robot.structure.contract != 'family.design':
            raise ValueError(
                'PCC_REQUIRES_FAMILY_DESIGN: '
                + robot.structure.contract
            )

        design = registry.parse(robot.structure)

        if not isinstance(design, Design):
            raise ValueError('PCC_REQUIRES_FAMILY_DESIGN')

        query = registry.parse(request)

        if not isinstance(query, PCCForwardRequest):
            raise ValueError('PCC_FORWARD_REQUEST_REQUIRED')

        configuration = {
            name: value.model_dump(mode='json')
            for name, value in query.configuration.segments.items()
        }

        raw = forward_kinematics(
            design=design,
            configuration=configuration,
            samples_per_segment=query.samples_per_segment,
        )

        segments = {}

        for name, transforms in raw['segment_transforms'].items():
            segments[name] = PCCSegmentKinematics(
                base=_pose(transforms['base']),
                tip=_pose(transforms['tip']),
                backbone_points_m=[
                    _vec3(point)
                    for point in raw['segment_backbones_m'][name]
                ],
            )

        result = PCCKinematicsResult(
            configuration=query.configuration,
            chain=list(raw['chain']),
            segments=segments,
            tip=_pose(raw['tip_transform']),
        )

        return Payload(
            contract='family.pcc_kinematics_result',
            data=result.model_dump(mode='json'),
        )


def pcc_forward_tool(ctx, args):
    from schemas.platform import Binding, Payload
    from extensions.tendon_family.contracts import PCCModelParameters

    binding = Binding(
        extension_id='model.pcc',
        parameters=Payload(
            contract='family.pcc_model',
            data=PCCModelParameters().model_dump(mode='json'),
        ),
    )

    definition, parameters = ctx.reg.bind(
        binding,
        'dynamics_model',
    )

    model = definition.resolve()(parameters)

    request = Payload(
        contract='family.pcc_forward_request',
        data=args.model_dump(mode='json'),
    )

    result = model.forward(
        ctx.input.robot,
        request,
        ctx.reg,
    )

    return ctx.reg.parse(result)


def pcc_describe_tool(ctx, args):
    from extensions.tendon_family.contracts import (
        Design,
        PCCDescription,
        PCCSegmentDescription,
        Segment,
    )

    if ctx.input.robot.structure.contract != 'family.design':
        raise ValueError('PCC_REQUIRES_FAMILY_DESIGN')
    design = ctx.reg.parse(ctx.input.robot.structure)
    if not isinstance(design, Design):
        raise ValueError('PCC_REQUIRES_FAMILY_DESIGN')
    return PCCDescription(
        segments=[
            PCCSegmentDescription(segment=component.id)
            for component in design.components
            if isinstance(component, Segment)
        ]
    )
