"""RobotIR-driven variable-strain continuum bending dynamics.

The resolved GVS basis determines the coordinate order and curvature field.
The strain is the actual
geometric curvature.  Natural curvature is used only as the zero-energy
reference in the constitutive bending force.

The continuum pose is integrated on SE(3) with midpoint, piecewise-constant
strain exponentials.  Mechanics use distributed section mass/inertia,
physical bending stiffness and viscosity, rigid attachment inertia, gravity,
and straight-frictionless tendon geometry.  This bounded model omits torsion,
shear, axial extension, contact, friction, rope elasticity and motor dynamics.
"""

from __future__ import annotations

import math

import numpy as np

from extensions.experiment_dynamics.contracts import Assembly, Scene
from extensions.tendon_family.contracts import Design, Reserved, Rigid, Segment
from extensions.tendon_family.pcc import (
    quaternion_wxyz_to_rotation,
    rigid_transform,
    segment_pose_at,
)
from extensions.tendon_family.sections import at as section_at
from extensions.tendon_family.sections import properties as section_properties
from extensions.tendon_family.gvs_basis import (basis_matrix, basis_quadrature,
    integration_intervals, resolve_basis, segment_basis, segment_slice)


MODEL_ID = 'gvs_variable_strain_bending_v1'


def _topology(design):
    parsed = design if isinstance(design, Design) else Design.model_validate(design)
    components = {component.id: component for component in parsed.components}
    if len(components) != len(parsed.components):
        raise ValueError('GVS design contains duplicate component IDs')

    reverse = []
    current = parsed.tip.part
    visited = set()
    while current != 'fixed_base':
        if current in visited:
            raise ValueError('GVS component graph contains a cycle')
        visited.add(current)
        component = components.get(current)
        if component is None:
            raise ValueError('GVS tip chain references unknown component: ' + current)
        if isinstance(component, Reserved):
            raise ValueError('GVS does not implement reserved topology: ' + component.kind)
        reverse.append(current)
        current = component.connection.part

    chain = tuple(reversed(reverse))
    if set(chain) != set(components):
        unused = set(components) - set(chain)
        raise ValueError(
            'GVS requires one serial component chain; components outside tip ancestry: '
            + ', '.join(sorted(unused))
        )
    segments = tuple(
        components[name] for name in chain if isinstance(components[name], Segment)
    )
    if not segments:
        raise ValueError('GVS requires at least one flexible segment')
    return parsed, components, chain, segments


def coordinate_order(design, basis=None) -> list[str]:
    return resolve_basis(design, basis).coordinate_order


def describe(design, basis=None) -> dict:
    parsed, _, _, _ = _topology(design)
    resolved = resolve_basis(parsed, basis)
    coordinates = []
    for local in resolved.segments:
        for axis_index, axis in enumerate(resolved.axes):
            for index in range(len(local.knots)):
                name = resolved.coordinate_order[local.start + axis_index * len(local.knots) + index]
                mode = ('constant' if index == 0 else 'linear') if resolved.specification.strategy == 'first_order' else 'nodal_linear'
                coordinates.append(dict(name=name, segment=local.segment, mode=mode,
                                        axis=axis, units='rad/m'))
    return dict(
        model_id=MODEL_ID,
        frame='robot_base',
        basis=(('phi0(s)=1', 'phi1(s)=2*s/L-1') if resolved.specification.strategy == 'first_order' else ('piecewise_linear_nodal',)),
        resolved_basis=resolved.model_dump(mode='json'),
        curvature_semantics='actual_total_curvature',
        natural_curvature_role='zero_elastic_energy_reference',
        coordinates=coordinates,
        tendon_inputs=[
            dict(
                tendon=tendon.id,
                units='N',
                constraint='nonnegative',
                force_limit_n=tendon.force_limit_n,
                design_pretension_n=tendon.pretension_n,
            )
            for tendon in parsed.tendons
        ],
    )


def _configuration(topology, q, basis=None):
    resolved = resolve_basis(topology[0], basis)
    values = np.asarray(q, dtype=float)
    expected = resolved.dimension
    if values.shape != (expected,) or not np.all(np.isfinite(values)):
        raise ValueError(f'GVS q must contain {expected} finite coordinates')
    return values, {
        segment.segment: values[segment_slice(segment)]
        for segment in resolved.segments
    }


def _segment_local_pose(segment, coefficients, u, integration_steps, resolved, local_basis):
    u = float(u)
    if not 0.0 <= u <= 1.0:
        raise ValueError('GVS segment coordinate must be within [0, 1]')
    if u == 0.0:
        return np.eye(4)
    transform = np.eye(4)
    for normalized_midpoint, normalized_width in integration_intervals(local_basis, u, integration_steps):
        ky, kz = basis_matrix(resolved, local_basis, normalized_midpoint) @ coefficients
        transform = transform @ segment_pose_at(segment.length_m * normalized_width, ky, kz)
    return transform


class _Kinematics:
    def __init__(self, topology, q, integration_steps, basis=None):
        self.design, self.components, self.chain, self.segments = topology
        self.resolved = resolve_basis(self.design, basis)
        self.q, self.coefficients = _configuration(topology, q, basis)
        self.integration_steps = integration_steps
        self._base_cache = {}
        self._point_cache = {}

    def point_pose(self, part, s):
        key = (part, float(s))
        cached = self._point_cache.get(key)
        if cached is not None:
            return cached
        if part == 'fixed_base':
            if abs(float(s)) > 1e-12:
                raise ValueError('fixed_base has no along-component coordinate')
            result = np.eye(4)
        else:
            component = self.components.get(part)
            if component is None:
                raise ValueError('Unknown GVS attachment component: ' + part)
            base = self.base_pose(part)
            if isinstance(component, Segment):
                result = base @ _segment_local_pose(
                    component,
                    self.coefficients[part],
                    s,
                    self.integration_steps,
                    self.resolved,
                    segment_basis(self.resolved, part),
                )
            elif isinstance(component, Rigid):
                if abs(float(s)) > 1e-12:
                    raise ValueError('Rigid GVS component does not support nonzero s')
                result = base
            else:
                raise TypeError('Unsupported GVS component type')
        self._point_cache[key] = result
        return result

    def base_pose(self, component_id):
        cached = self._base_cache.get(component_id)
        if cached is not None:
            return cached
        component = self.components[component_id]
        parent = self.point_pose(component.connection.part, component.connection.s)
        connection = rigid_transform(
            component.connection.position_m,
            component.connection.quaternion_wxyz,
        )
        result = parent @ connection
        self._base_cache[component_id] = result
        return result

    def attachment_pose(self, attachment, position_override=None):
        position = attachment.position_m if position_override is None else position_override
        return self.point_pose(attachment.part, attachment.s) @ rigid_transform(
            position,
            attachment.quaternion_wxyz,
        )

    def output(self, samples_per_segment):
        component_poses = {
            name: self.base_pose(name).copy()
            for name in self.chain
        }
        segment_transforms = {}
        backbones = {}
        for segment in self.segments:
            base = self.base_pose(segment.id).copy()
            points = []
            for u in np.linspace(0.0, 1.0, samples_per_segment):
                points.append(self.point_pose(segment.id, float(u))[:3, 3].copy())
            segment_transforms[segment.id] = dict(
                base=base,
                tip=self.point_pose(segment.id, 1.0).copy(),
            )
            backbones[segment.id] = np.asarray(points)
        tip = self.attachment_pose(self.design.tip)
        return dict(
            frame='robot_base',
            chain=self.chain,
            component_transforms=component_poses,
            segment_transforms=segment_transforms,
            segment_backbones_m=backbones,
            tip_transform=tip,
            tip_position_m=tip[:3, 3].copy(),
        )


def forward_kinematics(design, q, samples_per_segment=21, integration_steps_per_segment=24, basis=None):
    """Integrate the variable-curvature continuum pose in the robot base frame."""
    topology = _topology(design)
    return _Kinematics(topology, q, integration_steps_per_segment, basis).output(
        samples_per_segment
    )


def _principal_matrix(segment, normalized_s, values):
    section = section_at(segment, normalized_s)
    bending = np.asarray(section_properties(section)['bending_area_m4'], dtype=float)
    eigenvalues, axes = np.linalg.eigh(bending)
    if abs(eigenvalues[1] - eigenvalues[0]) <= 1e-12 * max(eigenvalues):
        angle = section.angle_rad
        axes = np.array([
            [math.cos(angle), -math.sin(angle)],
            [math.sin(angle), math.cos(angle)],
        ])
    return axes @ np.diag(np.asarray(values, dtype=float)) @ axes.T


def _stiffness_and_damping(segment, normalized_s):
    section = section_at(segment, normalized_s)
    prop = section_properties(section)
    physics = segment.physics
    if physics.mode == 'material':
        stiffness = physics.young_pa * np.asarray(prop['bending_area_m4'], dtype=float)
    else:
        stiffness = _principal_matrix(
            segment,
            normalized_s,
            physics.bending_ei_nm2,
        )
    damping = _principal_matrix(
        segment,
        normalized_s,
        physics.bending_viscosity_nm2_s,
    )
    return stiffness, damping


def constitutive_forces(design, q, qdot, quadrature_points_per_segment=5, basis=None):
    """Return positive-LHS elastic and viscous generalized forces."""
    topology = _topology(design)
    resolved = resolve_basis(topology[0], basis)
    values, coefficients = _configuration(topology, q, basis)
    rates = np.asarray(qdot, dtype=float)
    if rates.shape != values.shape or not np.all(np.isfinite(rates)):
        raise ValueError('GVS qdot must match q and contain finite values')
    elastic = np.zeros_like(values)
    damping = np.zeros_like(values)
    for segment in topology[3]:
        local = segment_basis(resolved, segment.id)
        sl = segment_slice(local)
        local_q = coefficients[segment.id]
        local_qdot = rates[sl]
        local_elastic = np.zeros(len(local_q))
        local_damping = np.zeros(len(local_q))
        natural = np.asarray(segment.natural_curvature_rad_m, dtype=float)
        for u, weight in basis_quadrature(local, quadrature_points_per_segment):
            matrix = basis_matrix(resolved, local, u)
            stiffness, viscosity = _stiffness_and_damping(segment, float(u))
            scale = segment.length_m * weight
            local_elastic += scale * matrix.T @ stiffness @ (matrix @ local_q - natural)
            local_damping += scale * matrix.T @ viscosity @ (matrix @ local_qdot)
        elastic[sl] = local_elastic
        damping[sl] = local_damping
    return elastic, damping


def _mass_descriptors(topology, quadrature_points, basis=None):
    resolved = resolve_basis(topology[0], basis)
    descriptors = []
    for segment in topology[3]:
        local = segment_basis(resolved, segment.id)
        for u, weight in basis_quadrature(local, quadrature_points):
            section = section_at(segment, float(u))
            prop = section_properties(section)
            area = prop['area_m2']
            physics = segment.physics
            line_density = (
                physics.density_kg_m3 * area
                if physics.mode == 'material'
                else physics.line_density_kg_m
            )
            density = line_density / area
            inertia_per_length = np.zeros((3, 3))
            inertia_per_length[0, 0] = density * prop['polar_area_m4']
            inertia_per_length[1:, 1:] = density * np.asarray(
                prop['bending_area_m4'], dtype=float
            )
            scale = segment.length_m * weight
            descriptors.append(dict(
                kind='segment',
                component=segment.id,
                s=float(u),
                offset=np.array([0.0, *prop['centroid_yz_m']], dtype=float),
                mass=float(scale * line_density),
                inertia=scale * inertia_per_length,
            ))
    for name in topology[2]:
        component = topology[1][name]
        if isinstance(component, Rigid):
            descriptors.append(dict(
                kind='rigid',
                component=name,
                offset=np.asarray(component.com_local_m, dtype=float),
                mass=float(component.mass_kg),
                inertia=np.asarray(component.inertia_com_local_kg_m2, dtype=float),
            ))
    return descriptors


def _observe_mass(topology, q, integration_steps, descriptors, basis):
    state = _Kinematics(topology, q, integration_steps, basis)
    observations = []
    for descriptor in descriptors:
        if descriptor['kind'] == 'segment':
            pose = state.point_pose(descriptor['component'], descriptor['s'])
        else:
            pose = state.base_pose(descriptor['component'])
        rotation = pose[:3, :3]
        position = pose[:3, 3] + rotation @ descriptor['offset']
        observations.append((position, rotation))
    return observations


def _mass_and_gravity(topology, q, gravity, parameters, descriptors=None):
    q, _ = _configuration(topology, q, parameters.basis)
    descriptors = descriptors or _mass_descriptors(
        topology, parameters.quadrature_points_per_segment, parameters.basis
    )
    base = _observe_mass(
        topology, q, parameters.integration_steps_per_segment, descriptors, parameters.basis
    )
    n = len(q)
    jacobian_v = [np.zeros((3, n)) for _ in descriptors]
    jacobian_w = [np.zeros((3, n)) for _ in descriptors]
    h = parameters.finite_difference_step
    for coordinate in range(n):
        delta = np.zeros(n)
        delta[coordinate] = h
        plus = _observe_mass(
            topology, q + delta, parameters.integration_steps_per_segment, descriptors, parameters.basis
        )
        minus = _observe_mass(
            topology, q - delta, parameters.integration_steps_per_segment, descriptors, parameters.basis
        )
        for item, ((_, rotation), (p_plus, r_plus), (p_minus, r_minus)) in enumerate(
            zip(base, plus, minus)
        ):
            jacobian_v[item][:, coordinate] = (p_plus - p_minus) / (2.0 * h)
            derivative = (r_plus - r_minus) / (2.0 * h)
            angular = derivative @ rotation.T
            angular = 0.5 * (angular - angular.T)
            jacobian_w[item][:, coordinate] = np.array([
                angular[2, 1], angular[0, 2], angular[1, 0]
            ])
    mass = np.zeros((n, n))
    gravity_force = np.zeros(n)
    gravity = np.asarray(gravity, dtype=float)
    for descriptor, (_, rotation), jv, jw in zip(
        descriptors, base, jacobian_v, jacobian_w
    ):
        inertia_world = rotation @ descriptor['inertia'] @ rotation.T
        mass += descriptor['mass'] * (jv.T @ jv) + jw.T @ inertia_world @ jw
        gravity_force += descriptor['mass'] * jv.T @ gravity
    return 0.5 * (mass + mass.T), gravity_force


def mass_matrix(design, q, parameters):
    topology = _topology(design)
    return _mass_and_gravity(topology, q, np.zeros(3), parameters)[0]


def gravity_force(design, q, gravity_robot_base_m_s2, parameters):
    topology = _topology(design)
    return _mass_and_gravity(
        topology, q, gravity_robot_base_m_s2, parameters
    )[1]


def _tendon_lengths(topology, q, integration_steps, basis=None):
    state = _Kinematics(topology, q, integration_steps, basis)
    lengths = []
    for tendon in topology[0].tendons:
        positions = []
        for route_point in tendon.points:
            attachment = route_point.attachment
            override = None
            if route_point.hole:
                guide = topology[1].get(attachment.part)
                if not isinstance(guide, Rigid) or route_point.hole not in guide.guide_holes:
                    raise ValueError('UNKNOWN_GUIDE_HOLE')
                override = guide.guide_holes[route_point.hole]
            positions.append(state.attachment_pose(attachment, override)[:3, 3])
        lengths.append(sum(
            np.linalg.norm(b - a)
            for a, b in zip(positions, positions[1:])
        ))
    return np.asarray(lengths, dtype=float)


def tendon_kinematics(design, q, parameters):
    """Return tendon order, lengths and dl/dq for straight frictionless spans."""
    topology = _topology(design)
    values, _ = _configuration(topology, q, parameters.basis)
    lengths = _tendon_lengths(
        topology, values, parameters.integration_steps_per_segment, parameters.basis
    )
    jacobian = np.zeros((len(lengths), len(values)))
    h = parameters.finite_difference_step
    for coordinate in range(len(values)):
        delta = np.zeros(len(values))
        delta[coordinate] = h
        plus = _tendon_lengths(
            topology, values + delta, parameters.integration_steps_per_segment, parameters.basis
        )
        minus = _tendon_lengths(
            topology, values - delta, parameters.integration_steps_per_segment, parameters.basis
        )
        jacobian[:, coordinate] = (plus - minus) / (2.0 * h)
    return [tendon.id for tendon in topology[0].tendons], lengths, jacobian


def tendon_lengths(design, q, parameters):
    """Return straight-frictionless tendon lengths without differentiating."""
    topology = _topology(design)
    values, _ = _configuration(topology, q, parameters.basis)
    return _tendon_lengths(
        topology, values, parameters.integration_steps_per_segment, parameters.basis
    )


def _velocity_bias(topology, q, qdot, parameters, descriptors):
    if not np.any(qdot):
        return np.zeros_like(q)
    n = len(q)
    h = parameters.finite_difference_step
    derivatives = np.zeros((n, n, n))
    for coordinate in range(n):
        delta = np.zeros(n)
        delta[coordinate] = h
        plus = _mass_and_gravity(
            topology, q + delta, np.zeros(3), parameters, descriptors
        )[0]
        minus = _mass_and_gravity(
            topology, q - delta, np.zeros(3), parameters, descriptors
        )[0]
        derivatives[coordinate] = (plus - minus) / (2.0 * h)
    bias = np.zeros(n)
    for i in range(n):
        for j in range(n):
            for k in range(n):
                gamma = 0.5 * (
                    derivatives[k, i, j]
                    + derivatives[j, i, k]
                    - derivatives[i, j, k]
                )
                bias[i] += gamma * qdot[j] * qdot[k]
    return bias


def evaluate_dynamics(
    design,
    q,
    qdot,
    tendon_tensions_n,
    gravity_robot_base_m_s2,
    parameters,
    samples_per_segment=21,
):
    """Assemble and solve M*qdd+c+elastic+damping=tendon+gravity."""
    topology = _topology(design)
    q, _ = _configuration(topology, q, parameters.basis)
    qdot = np.asarray(qdot, dtype=float)
    if qdot.shape != q.shape or not np.all(np.isfinite(qdot)):
        raise ValueError('GVS qdot must match q and contain finite values')
    tendon_order = [tendon.id for tendon in topology[0].tendons]
    if set(tendon_tensions_n) != set(tendon_order):
        raise ValueError('GVS tendon tensions must cover exactly: ' + ', '.join(tendon_order))
    tensions = np.asarray([tendon_tensions_n[name] for name in tendon_order], dtype=float)
    if np.any(tensions < 0.0) or not np.all(np.isfinite(tensions)):
        raise ValueError('GVS tendon tensions must be finite and nonnegative')
    limits = np.asarray(
        [tendon.force_limit_n for tendon in topology[0].tendons], dtype=float
    )
    if np.any(tensions > limits):
        raise ValueError('GVS tendon tension exceeds family.design force limit')

    descriptors = _mass_descriptors(topology, parameters.quadrature_points_per_segment, parameters.basis)
    mass, gravity = _mass_and_gravity(
        topology, q, gravity_robot_base_m_s2, parameters, descriptors
    )
    bias = _velocity_bias(topology, q, qdot, parameters, descriptors)
    elastic, damping = constitutive_forces(
        topology[0], q, qdot, parameters.quadrature_points_per_segment, parameters.basis
    )
    lengths = _tendon_lengths(topology, q, parameters.integration_steps_per_segment, parameters.basis)
    tendon_jacobian = np.zeros((len(lengths), len(q)))
    h = parameters.finite_difference_step
    for coordinate in range(len(q)):
        delta = np.zeros(len(q))
        delta[coordinate] = h
        tendon_jacobian[:, coordinate] = (
            _tendon_lengths(
                topology, q + delta, parameters.integration_steps_per_segment, parameters.basis
            )
            - _tendon_lengths(
                topology, q - delta, parameters.integration_steps_per_segment, parameters.basis
            )
        ) / (2.0 * h)
    tendon_force = -tendon_jacobian.T @ tensions
    rhs = tendon_force + gravity - bias - elastic - damping
    qdd = np.linalg.solve(mass, rhs)
    kinematics = _Kinematics(
        topology, q, parameters.integration_steps_per_segment, parameters.basis
    ).output(samples_per_segment)
    return dict(
        coordinate_order=coordinate_order(topology[0], parameters.basis),
        q=q,
        qdot=qdot,
        qdd=qdd,
        mass_matrix=mass,
        velocity_bias=bias,
        elastic_force=elastic,
        damping_force=damping,
        gravity_force=gravity,
        tendon_generalized_force=tendon_force,
        tendon_order=tendon_order,
        tendon_lengths_m=lengths,
        tendon_length_jacobian=tendon_jacobian,
        kinematics=kinematics,
    )


def _vec3(value):
    return tuple(float(item) for item in value)


def _matrix3(value):
    return tuple(tuple(float(item) for item in row) for row in value)


def _pose(transform):
    from extensions.tendon_family.contracts import GVSPose
    return GVSPose(
        position_m=_vec3(transform[:3, 3]),
        rotation_matrix=_matrix3(transform[:3, :3]),
    )


class GVSModel:
    """Registered adapter for real variable-strain continuum dynamics."""

    def __init__(self, parameters):
        from extensions.tendon_family.contracts import GVSModelParameters
        self.parameters = GVSModelParameters.model_validate(parameters)

    def describe(self, robot, registry):
        from schemas.platform import Payload
        from extensions.tendon_family.contracts import Design, GVSDescription
        if robot.structure.contract != 'family.design':
            raise ValueError('GVS_REQUIRES_FAMILY_DESIGN')
        design = registry.parse(robot.structure)
        if not isinstance(design, Design):
            raise ValueError('GVS_REQUIRES_FAMILY_DESIGN')
        result = GVSDescription.model_validate(describe(design, self.parameters.basis))
        return Payload(
            contract='family.gvs_description',
            data=result.model_dump(mode='json'),
        )

    def evaluate(self, robot, environment, request, registry):
        from schemas.platform import Payload
        from extensions.tendon_family.contracts import (
            Design,
            GVSDynamicsRequest,
            GVSDynamicsResult,
            GVSSegmentKinematics,
        )
        if robot.structure.contract != 'family.design':
            raise ValueError('GVS_REQUIRES_FAMILY_DESIGN')
        design = registry.parse(robot.structure)
        query = registry.parse(request)
        assembly = registry.parse(environment)
        if not isinstance(design, Design):
            raise ValueError('GVS_REQUIRES_FAMILY_DESIGN')
        if not isinstance(query, GVSDynamicsRequest):
            raise ValueError('GVS_DYNAMICS_REQUEST_REQUIRED')
        if not isinstance(assembly, Assembly):
            raise ValueError('GVS_REQUIRES_EXPERIMENT_ASSEMBLY')
        if assembly.external_forces:
            raise ValueError('GVS_EXTERNAL_APPLIED_FORCES_UNSUPPORTED')

        mount_rotation = quaternion_wxyz_to_rotation(
            assembly.mount.quaternion_wxyz
        )
        gravity_robot = mount_rotation.T @ np.asarray(
            assembly.environment.gravity_m_s2, dtype=float
        )
        raw = evaluate_dynamics(
            design=design,
            q=query.state.q,
            qdot=query.state.qdot,
            tendon_tensions_n=query.input.tendon_tensions_n,
            gravity_robot_base_m_s2=gravity_robot,
            parameters=self.parameters,
            samples_per_segment=query.samples_per_segment,
        )
        kinematics = raw.pop('kinematics')
        segments = {
            name: GVSSegmentKinematics(
                base=_pose(transforms['base']),
                tip=_pose(transforms['tip']),
                backbone_points_m=[
                    _vec3(point)
                    for point in kinematics['segment_backbones_m'][name]
                ],
            )
            for name, transforms in kinematics['segment_transforms'].items()
        }
        result = GVSDynamicsResult(
            **{
                key: value.tolist() if isinstance(value, np.ndarray) else value
                for key, value in raw.items()
            },
            segments=segments,
            component_poses={
                name: _pose(transform)
                for name, transform in kinematics['component_transforms'].items()
            },
            tip=_pose(kinematics['tip_transform']),
        )
        return Payload(
            contract='family.gvs_dynamics_result',
            data=result.model_dump(mode='json'),
        )

    def build_system(self, robot, parameters, discretization, context):
        """Export x=[q,qdot], u=tendon tension as a public continuous system."""
        from schemas.platform import EvidenceRef, Payload, RobotDescription, SignalSpec
        from schemas.platform_math import DynamicSystem, SystemContext
        from extensions.tendon_family.contracts import GVSContinuousDynamicsExpression

        robot = RobotDescription.model_validate(robot)
        context = SystemContext.model_validate(context)
        if robot.structure.contract != 'family.design':
            raise ValueError('GVS_REQUIRES_FAMILY_DESIGN')
        if discretization is not None:
            raise ValueError('GVS_DOES_NOT_ACCEPT_DISCRETIZATION')
        if isinstance(parameters, Payload):
            if parameters.contract != 'family.gvs_model':
                raise ValueError('GVS_MODEL_PARAMETERS_REQUIRED')
            supplied = type(self.parameters).model_validate(parameters.data)
        else:
            supplied = type(self.parameters).model_validate(parameters)
        if supplied != self.parameters:
            raise ValueError('GVS_BOUND_PARAMETERS_MISMATCH')
        design = Design.model_validate(robot.structure.data)
        if context.scene is None:
            raise ValueError('GVS_SYSTEM_CONTEXT_REQUIRES_SCENE')
        if isinstance(context.scene, EvidenceRef):
            raise ValueError('GVS_SYSTEM_CONTEXT_SCENE_EVIDENCE_REQUIRES_RESOLUTION')
        if context.scene.contract == 'experiment.assembly':
            assembly = Assembly.model_validate(context.scene.data)
        elif context.scene.contract == 'experiment.scene':
            assembly = Scene.model_validate(context.scene.data).assembly
        else:
            raise ValueError('GVS_REQUIRES_EXPERIMENT_ASSEMBLY')
        if assembly.external_forces:
            raise ValueError('GVS_EXTERNAL_APPLIED_FORCES_UNSUPPORTED')

        coordinates = coordinate_order(design, self.parameters.basis)
        tendons = list(design.tendons)
        n = len(coordinates)
        if len(context.x0) != 2 * n or len(context.u0) != len(tendons):
            raise ValueError('MODEL_OPERATING_POINT_DIMENSION_MISMATCH')
        limits = np.asarray([tendon.force_limit_n for tendon in tendons])
        u0 = np.asarray(context.u0, dtype=float)
        if np.any(u0 < 0) or np.any(u0 > limits):
            raise ValueError('GVS_OPERATING_TENSION_OUT_OF_BOUNDS')

        mount_rotation = quaternion_wxyz_to_rotation(
            assembly.mount.quaternion_wxyz
        )
        gravity_robot = mount_rotation.T @ np.asarray(
            assembly.environment.gravity_m_s2, dtype=float
        )
        expression = GVSContinuousDynamicsExpression(
            design=design,
            parameters=self.parameters,
            gravity_robot_base_m_s2=tuple(gravity_robot),
            coordinate_order=coordinates,
            tendon_order=[tendon.id for tendon in tendons],
            tendon_force_limits_n=limits.tolist(),
        )
        state_definition = [
            SignalSpec(
                name=name,
                entity=name.split('.', 1)[0],
                dimension=1,
                units='rad/m',
                frame='segment_local',
                phase='continuous_state',
            )
            for name in coordinates
        ] + [
            SignalSpec(
                name=name + '.rate',
                entity=name.split('.', 1)[0],
                dimension=1,
                units='rad/(m*s)',
                frame='segment_local',
                phase='continuous_state',
            )
            for name in coordinates
        ]
        input_definition = [
            SignalSpec(
                name='tendon_tension',
                entity=tendon.id,
                dimension=1,
                units='N',
                frame='tendon_path',
                phase='continuous_input',
            )
            for tendon in tendons
        ]
        return DynamicSystem(
            state_definition=state_definition,
            input_definition=input_definition,
            output_definition=[],
            dynamics=Payload(
                contract='family.gvs_continuous_dynamics',
                data=expression.model_dump(mode='json'),
            ),
            x0=context.x0,
            u0=context.u0,
            time_domain='continuous',
            timestep=None,
        )


def _bound_model(ctx, basis=None):
    from schemas.platform import Binding, Payload
    from extensions.tendon_family.contracts import GVSBasisSpecification, GVSModelParameters
    definition, parameters = ctx.reg.bind(
        Binding(
            extension_id='model.gvs',
            parameters=Payload(
                contract='family.gvs_model',
                data=GVSModelParameters(
                    basis=basis if basis is not None else GVSBasisSpecification()
                ).model_dump(mode='json'),
            ),
        ),
        'dynamics_model',
    )
    return definition.resolve()(parameters)


def gvs_describe_tool(ctx, args):
    return ctx.reg.parse(_bound_model(ctx).describe(ctx.input.robot, ctx.reg))


def gvs_describe_tool_v2(ctx, args):
    return ctx.reg.parse(_bound_model(ctx, args.basis).describe(ctx.input.robot, ctx.reg))


def gvs_evaluate_tool(ctx, args, *, basis=None):
    from schemas.platform import Payload
    request = Payload(
        contract='family.gvs_dynamics_request',
        data=args.model_dump(mode='json'),
    )
    result = _bound_model(ctx, basis).evaluate(
        ctx.input.robot,
        ctx.input.task.environment,
        request,
        ctx.reg,
    )
    return ctx.reg.parse(result)


def gvs_evaluate_tool_v2(ctx, args):
    """Evaluate once, then expose only the requested public diagnostic layer."""
    from extensions.tendon_family.contracts import (
        GVSDynamicsRequest,
        GVSDynamicsResultV2,
    )

    full = gvs_evaluate_tool(ctx, GVSDynamicsRequest(
        state=args.state,
        input=args.input,
        samples_per_segment=args.samples_per_segment,
    ), basis=getattr(args, 'basis', None))
    forces = args.detail in ('forces', 'full')
    diagnostics = args.detail == 'full'
    return GVSDynamicsResultV2(
        detail=args.detail,
        coordinate_order=full.coordinate_order,
        q=full.q,
        qdot=full.qdot,
        qdd=full.qdd,
        tip=full.tip,
        segment_end_poses={name: segment.tip for name, segment in full.segments.items()},
        velocity_bias=full.velocity_bias if forces else None,
        elastic_force=full.elastic_force if forces else None,
        damping_force=full.damping_force if forces else None,
        gravity_force=full.gravity_force if forces else None,
        tendon_generalized_force=full.tendon_generalized_force if forces else None,
        mass_matrix=full.mass_matrix if diagnostics else None,
        tendon_order=full.tendon_order if diagnostics else None,
        tendon_lengths_m=full.tendon_lengths_m if diagnostics else None,
        tendon_length_jacobian=full.tendon_length_jacobian if diagnostics else None,
        backbone_points_m=(
            {name: segment.backbone_points_m for name, segment in full.segments.items()}
            if args.include_backbone else None
        ),
    )
