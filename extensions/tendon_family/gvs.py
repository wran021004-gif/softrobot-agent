"""First-order variable-strain continuum bending dynamics.

Each flexible segment uses the deterministic coordinate order

    kappa_y_0, kappa_y_1, kappa_z_0, kappa_z_1

with ``phi0(s)=1`` and ``phi1(s)=2*s/L-1``.  The strain is the actual
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

from extensions.experiment_dynamics.contracts import Assembly
from extensions.tendon_family.contracts import Design, Reserved, Rigid, Segment
from extensions.tendon_family.pcc import (
    quaternion_wxyz_to_rotation,
    rigid_transform,
    segment_pose_at,
)
from extensions.tendon_family.sections import at as section_at
from extensions.tendon_family.sections import properties as section_properties


MODEL_ID = 'gvs_variable_strain_bending_v1'
LOCAL_COORDINATES = (
    ('kappa_y_0', 'y', 'constant'),
    ('kappa_y_1', 'y', 'linear'),
    ('kappa_z_0', 'z', 'constant'),
    ('kappa_z_1', 'z', 'linear'),
)


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


def coordinate_order(design) -> list[str]:
    """Resolve the fixed first-order GVS coordinate ordering."""
    _, _, _, segments = _topology(design)
    return [
        f'{segment.id}.{coordinate}'
        for segment in segments
        for coordinate, _, _ in LOCAL_COORDINATES
    ]


def describe(design) -> dict:
    parsed, _, _, segments = _topology(design)
    coordinates = []
    for segment in segments:
        for coordinate, axis, mode in LOCAL_COORDINATES:
            coordinates.append(dict(
                name=f'{segment.id}.{coordinate}',
                segment=segment.id,
                mode=mode,
                axis=axis,
                units='rad/m',
            ))
    return dict(
        model_id=MODEL_ID,
        frame='robot_base',
        basis=('phi0(s)=1', 'phi1(s)=2*s/L-1'),
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


def _configuration(topology, q):
    _, _, _, segments = topology
    values = np.asarray(q, dtype=float)
    expected = 4 * len(segments)
    if values.shape != (expected,) or not np.all(np.isfinite(values)):
        raise ValueError(f'GVS q must contain {expected} finite coordinates')
    return values, {
        segment.id: values[4 * index:4 * index + 4]
        for index, segment in enumerate(segments)
    }


def _segment_local_pose(segment, coefficients, u, integration_steps):
    u = float(u)
    if not 0.0 <= u <= 1.0:
        raise ValueError('GVS segment coordinate must be within [0, 1]')
    if u == 0.0:
        return np.eye(4)
    steps = max(1, math.ceil(integration_steps * u))
    ds = segment.length_m * u / steps
    transform = np.eye(4)
    for index in range(steps):
        normalized_midpoint = (index + 0.5) * u / steps
        phi1 = 2.0 * normalized_midpoint - 1.0
        ky = coefficients[0] + coefficients[1] * phi1
        kz = coefficients[2] + coefficients[3] * phi1
        transform = transform @ segment_pose_at(ds, ky, kz)
    return transform


class _Kinematics:
    def __init__(self, topology, q, integration_steps):
        self.design, self.components, self.chain, self.segments = topology
        self.q, self.coefficients = _configuration(topology, q)
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


def forward_kinematics(design, q, samples_per_segment=21, integration_steps_per_segment=24):
    """Integrate the variable-curvature continuum pose in the robot base frame."""
    topology = _topology(design)
    return _Kinematics(topology, q, integration_steps_per_segment).output(
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


def _quadrature(count):
    nodes, weights = np.polynomial.legendre.leggauss(count)
    return (nodes + 1.0) / 2.0, weights / 2.0


def constitutive_forces(design, q, qdot, quadrature_points_per_segment=5):
    """Return positive-LHS elastic and viscous generalized forces."""
    topology = _topology(design)
    values, coefficients = _configuration(topology, q)
    rates = np.asarray(qdot, dtype=float)
    if rates.shape != values.shape or not np.all(np.isfinite(rates)):
        raise ValueError('GVS qdot must match q and contain finite values')
    elastic = np.zeros_like(values)
    damping = np.zeros_like(values)
    nodes, weights = _quadrature(quadrature_points_per_segment)
    for segment_index, segment in enumerate(topology[3]):
        local_q = coefficients[segment.id]
        local_qdot = rates[4 * segment_index:4 * segment_index + 4]
        local_elastic = np.zeros(4)
        local_damping = np.zeros(4)
        natural = np.asarray(segment.natural_curvature_rad_m, dtype=float)
        for u, weight in zip(nodes, weights):
            phi1 = 2.0 * u - 1.0
            basis = np.array([
                [1.0, phi1, 0.0, 0.0],
                [0.0, 0.0, 1.0, phi1],
            ])
            stiffness, viscosity = _stiffness_and_damping(segment, float(u))
            scale = segment.length_m * weight
            local_elastic += scale * basis.T @ stiffness @ (basis @ local_q - natural)
            local_damping += scale * basis.T @ viscosity @ (basis @ local_qdot)
        start = 4 * segment_index
        elastic[start:start + 4] = local_elastic
        damping[start:start + 4] = local_damping
    return elastic, damping


def _mass_descriptors(topology, quadrature_points):
    nodes, weights = _quadrature(quadrature_points)
    descriptors = []
    for segment in topology[3]:
        for u, weight in zip(nodes, weights):
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


def _observe_mass(topology, q, integration_steps, descriptors):
    state = _Kinematics(topology, q, integration_steps)
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
    q, _ = _configuration(topology, q)
    descriptors = descriptors or _mass_descriptors(
        topology, parameters.quadrature_points_per_segment
    )
    base = _observe_mass(
        topology, q, parameters.integration_steps_per_segment, descriptors
    )
    n = len(q)
    jacobian_v = [np.zeros((3, n)) for _ in descriptors]
    jacobian_w = [np.zeros((3, n)) for _ in descriptors]
    h = parameters.finite_difference_step
    for coordinate in range(n):
        delta = np.zeros(n)
        delta[coordinate] = h
        plus = _observe_mass(
            topology, q + delta, parameters.integration_steps_per_segment, descriptors
        )
        minus = _observe_mass(
            topology, q - delta, parameters.integration_steps_per_segment, descriptors
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


def _tendon_lengths(topology, q, integration_steps):
    state = _Kinematics(topology, q, integration_steps)
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
    values, _ = _configuration(topology, q)
    lengths = _tendon_lengths(
        topology, values, parameters.integration_steps_per_segment
    )
    jacobian = np.zeros((len(lengths), len(values)))
    h = parameters.finite_difference_step
    for coordinate in range(len(values)):
        delta = np.zeros(len(values))
        delta[coordinate] = h
        plus = _tendon_lengths(
            topology, values + delta, parameters.integration_steps_per_segment
        )
        minus = _tendon_lengths(
            topology, values - delta, parameters.integration_steps_per_segment
        )
        jacobian[:, coordinate] = (plus - minus) / (2.0 * h)
    return [tendon.id for tendon in topology[0].tendons], lengths, jacobian


def tendon_lengths(design, q, parameters):
    """Return straight-frictionless tendon lengths without differentiating."""
    topology = _topology(design)
    values, _ = _configuration(topology, q)
    return _tendon_lengths(
        topology, values, parameters.integration_steps_per_segment
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
    q, _ = _configuration(topology, q)
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

    descriptors = _mass_descriptors(topology, parameters.quadrature_points_per_segment)
    mass, gravity = _mass_and_gravity(
        topology, q, gravity_robot_base_m_s2, parameters, descriptors
    )
    bias = _velocity_bias(topology, q, qdot, parameters, descriptors)
    elastic, damping = constitutive_forces(
        topology[0], q, qdot, parameters.quadrature_points_per_segment
    )
    lengths = _tendon_lengths(topology, q, parameters.integration_steps_per_segment)
    tendon_jacobian = np.zeros((len(lengths), len(q)))
    h = parameters.finite_difference_step
    for coordinate in range(len(q)):
        delta = np.zeros(len(q))
        delta[coordinate] = h
        tendon_jacobian[:, coordinate] = (
            _tendon_lengths(
                topology, q + delta, parameters.integration_steps_per_segment
            )
            - _tendon_lengths(
                topology, q - delta, parameters.integration_steps_per_segment
            )
        ) / (2.0 * h)
    tendon_force = -tendon_jacobian.T @ tensions
    rhs = tendon_force + gravity - bias - elastic - damping
    qdd = np.linalg.solve(mass, rhs)
    kinematics = _Kinematics(
        topology, q, parameters.integration_steps_per_segment
    ).output(samples_per_segment)
    return dict(
        coordinate_order=coordinate_order(topology[0]),
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
        result = GVSDescription.model_validate(describe(design))
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


def _bound_model(ctx):
    from schemas.platform import Binding, Payload
    from extensions.tendon_family.contracts import GVSModelParameters
    definition, parameters = ctx.reg.bind(
        Binding(
            extension_id='model.gvs',
            parameters=Payload(
                contract='family.gvs_model',
                data=GVSModelParameters().model_dump(mode='json'),
            ),
        ),
        'dynamics_model',
    )
    return definition.resolve()(parameters)


def gvs_describe_tool(ctx, args):
    return ctx.reg.parse(_bound_model(ctx).describe(ctx.input.robot, ctx.reg))


def gvs_evaluate_tool(ctx, args):
    from schemas.platform import Payload
    request = Payload(
        contract='family.gvs_dynamics_request',
        data=args.model_dump(mode='json'),
    )
    result = _bound_model(ctx).evaluate(
        ctx.input.robot,
        ctx.input.task.environment,
        request,
        ctx.reg,
    )
    return ctx.reg.parse(result)
