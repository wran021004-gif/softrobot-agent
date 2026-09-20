"""CasADi MX implementation of the frozen first-order bending GVS model.

MX keeps indexed pose assembly and the resulting expression graph readable and
is directly usable by later IPOPT/acados adapters.  Public contracts retain only
the typed reconstruction recipe; no CasADi object is serialized.
"""

from __future__ import annotations

from functools import lru_cache
import json

import casadi as ca
import numpy as np

from extensions.tendon_family.contracts import (
    Design,
    GVSContinuousDynamicsExpression,
    GVSEquilibriumResult,
    GVSLinearizeRequest,
    GVSModelParameters,
    GVSSystemArtifactResult,
    LinearizedModelArtifactResult,
    LQRCommand,
    LQRDescription,
    LQRSynthesisDescription,
    LQRGainArtifact,
    LQRParameters,
    LQRSynthesisResult,
    Rigid,
    Segment,
)
from extensions.tendon_family.gvs import (
    _mass_descriptors,
    _quadrature,
    _stiffness_and_damping,
    _topology,
    _bound_model,
    coordinate_order,
)
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation, rigid_transform
from schemas.platform import EvidenceRef, Payload
from schemas.platform_math import DynamicSystem, LinearizedModel


EXPRESSION_CONTRACT = 'family.gvs_continuous_dynamics'


def _dm(value):
    return ca.DM(np.asarray(value, dtype=float))


def _skew(vector):
    return ca.vertcat(
        ca.horzcat(0, -vector[2], vector[1]),
        ca.horzcat(vector[2], 0, -vector[0]),
        ca.horzcat(-vector[1], vector[0], 0),
    )


def _segment_pose(length, ky, kz):
    """Smooth constant-strain SE(3) exponential, including zero curvature."""
    curvature = ca.vertcat(0, ky, kz)
    omega = _skew(curvature)
    k2 = ca.dot(curvature, curvature)
    # A negligible regularizer keeps AD of the inactive closed-form branch
    # finite at k=0; the selected low-curvature branch remains the exact Taylor
    # form there.
    k = ca.sqrt(k2 + 1e-30)
    theta = k * length
    low = k2 < 1e-14
    # Polynomial branches avoid the removable singularities at straight strain.
    a0 = length - k2 * length**3 / 6 + k2**2 * length**5 / 120
    b0 = length**2 / 2 - k2 * length**4 / 24 + k2**2 * length**6 / 720
    c0 = length**3 / 6 - k2 * length**5 / 120 + k2**2 * length**7 / 5040
    a = ca.if_else(low, a0, ca.sin(theta) / k)
    b = ca.if_else(low, b0, (1 - ca.cos(theta)) / (k**2))
    c = ca.if_else(low, c0, (theta - ca.sin(theta)) / (k**3))
    rotation = ca.DM.eye(3) + a * omega + b * ca.mtimes(omega, omega)
    position = ca.mtimes(
        length * ca.DM.eye(3) + b * omega + c * ca.mtimes(omega, omega),
        ca.DM([1, 0, 0]),
    )
    return ca.vertcat(
        ca.horzcat(rotation, position),
        ca.DM([[0, 0, 0, 1]]),
    )


class _SymbolicKinematics:
    def __init__(self, topology, q, integration_steps):
        self.design, self.components, self.chain, self.segments = topology
        self.q = q
        self.coefficients = {
            segment.id: q[4 * index:4 * index + 4]
            for index, segment in enumerate(self.segments)
        }
        self.integration_steps = integration_steps
        self._base_cache = {}
        self._point_cache = {}

    def _segment_local_pose(self, segment, coefficients, u):
        u = float(u)
        if not 0 <= u <= 1:
            raise ValueError('GVS segment coordinate must be within [0, 1]')
        if u == 0:
            return ca.DM.eye(4)
        steps = max(1, int(np.ceil(self.integration_steps * u)))
        ds = segment.length_m * u / steps
        transform = ca.MX.eye(4)
        for index in range(steps):
            midpoint = (index + 0.5) * u / steps
            phi1 = 2 * midpoint - 1
            ky = coefficients[0] + coefficients[1] * phi1
            kz = coefficients[2] + coefficients[3] * phi1
            transform = ca.mtimes(transform, _segment_pose(ds, ky, kz))
        return transform

    def point_pose(self, part, s):
        key = (part, float(s))
        if key in self._point_cache:
            return self._point_cache[key]
        if part == 'fixed_base':
            if abs(float(s)) > 1e-12:
                raise ValueError('fixed_base has no along-component coordinate')
            result = ca.DM.eye(4)
        else:
            component = self.components.get(part)
            if component is None:
                raise ValueError('Unknown GVS attachment component: ' + part)
            base = self.base_pose(part)
            if isinstance(component, Segment):
                result = ca.mtimes(
                    base,
                    self._segment_local_pose(
                        component, self.coefficients[part], s
                    ),
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
        if component_id in self._base_cache:
            return self._base_cache[component_id]
        component = self.components[component_id]
        parent = self.point_pose(component.connection.part, component.connection.s)
        connection = _dm(rigid_transform(
            component.connection.position_m,
            component.connection.quaternion_wxyz,
        ))
        result = ca.mtimes(parent, connection)
        self._base_cache[component_id] = result
        return result

    def attachment_pose(self, attachment, position_override=None):
        position = attachment.position_m if position_override is None else position_override
        local = _dm(rigid_transform(position, attachment.quaternion_wxyz))
        return ca.mtimes(self.point_pose(attachment.part, attachment.s), local)


def _angular_jacobian(rotation, q):
    derivative = ca.jacobian(ca.reshape(rotation, 9, 1), q)
    columns = []
    for index in range(q.numel()):
        d_rotation = ca.reshape(derivative[:, index], 3, 3)
        angular = ca.mtimes(d_rotation, rotation.T)
        angular = (angular - angular.T) / 2
        columns.append(ca.vertcat(angular[2, 1], angular[0, 2], angular[1, 0]))
    return ca.horzcat(*columns)


class GVSCasadiFunctions:
    """One native MX graph exposing dynamics terms and their derivatives."""

    def __init__(self, expression: GVSContinuousDynamicsExpression):
        self.expression = expression
        self.design = expression.design
        self.parameters = expression.parameters
        if expression.coordinate_order != coordinate_order(self.design):
            raise ValueError('GVS_EXPRESSION_COORDINATE_ORDER_MISMATCH')
        topology = _topology(self.design)
        n = len(expression.coordinate_order)
        m = len(expression.tendon_order)
        q = ca.MX.sym('q', n)
        qdot = ca.MX.sym('qdot', n)
        u = ca.MX.sym('u', m)
        state = _SymbolicKinematics(
            topology, q, self.parameters.integration_steps_per_segment
        )

        descriptors = _mass_descriptors(
            topology, self.parameters.quadrature_points_per_segment
        )
        mass = ca.MX.zeros(n, n)
        gravity = ca.MX.zeros(n, 1)
        gravity_vector = _dm(expression.gravity_robot_base_m_s2)
        for descriptor in descriptors:
            pose = (
                state.point_pose(descriptor['component'], descriptor['s'])
                if descriptor['kind'] == 'segment'
                else state.base_pose(descriptor['component'])
            )
            rotation = pose[:3, :3]
            position = pose[:3, 3] + ca.mtimes(rotation, _dm(descriptor['offset']))
            jv = ca.jacobian(position, q)
            jw = _angular_jacobian(rotation, q)
            inertia_world = ca.mtimes(
                [rotation, _dm(descriptor['inertia']), rotation.T]
            )
            mass += descriptor['mass'] * ca.mtimes(jv.T, jv)
            mass += ca.mtimes([jw.T, inertia_world, jw])
            gravity += descriptor['mass'] * ca.mtimes(jv.T, gravity_vector)
        mass = (mass + mass.T) / 2

        elastic = ca.MX.zeros(n, 1)
        damping = ca.MX.zeros(n, 1)
        nodes, weights = _quadrature(
            self.parameters.quadrature_points_per_segment
        )
        for segment_index, segment in enumerate(topology[3]):
            local_q = q[4 * segment_index:4 * segment_index + 4]
            local_qdot = qdot[4 * segment_index:4 * segment_index + 4]
            local_elastic = ca.MX.zeros(4, 1)
            local_damping = ca.MX.zeros(4, 1)
            natural = _dm(segment.natural_curvature_rad_m)
            for node, weight in zip(nodes, weights):
                phi1 = 2 * float(node) - 1
                basis = _dm([[1, phi1, 0, 0], [0, 0, 1, phi1]])
                stiffness, viscosity = _stiffness_and_damping(segment, float(node))
                scale = segment.length_m * float(weight)
                local_elastic += scale * ca.mtimes(
                    [basis.T, _dm(stiffness), ca.mtimes(basis, local_q) - natural]
                )
                local_damping += scale * ca.mtimes(
                    [basis.T, _dm(viscosity), ca.mtimes(basis, local_qdot)]
                )
            elastic[4 * segment_index:4 * segment_index + 4] = local_elastic
            damping[4 * segment_index:4 * segment_index + 4] = local_damping

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
                (ca.norm_2(b - a) for a, b in zip(positions, positions[1:])),
                ca.MX(0),
            ))
        tendon_lengths = ca.vertcat(*lengths)
        tendon_jacobian = ca.jacobian(tendon_lengths, q)
        tendon_force = -ca.mtimes(tendon_jacobian.T, u)

        mass_derivative = ca.jacobian(ca.reshape(mass, n * n, 1), q)
        bias = ca.MX.zeros(n, 1)
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    # CasADi reshape is column-major: M[i,j] -> i+n*j.
                    gamma = (
                        mass_derivative[i + n * j, k]
                        + mass_derivative[i + n * k, j]
                        - mass_derivative[j + n * k, i]
                    ) / 2
                    bias[i] += gamma * qdot[j] * qdot[k]
        qdd = ca.solve(
            mass,
            tendon_force + gravity - bias - elastic - damping,
        )
        x = ca.vertcat(q, qdot)
        xdot = ca.vertcat(qdot, qdd)

        outputs = [
            xdot, qdd, mass, elastic, damping, gravity, tendon_force,
            tendon_lengths, tendon_jacobian, bias,
        ]
        names = [
            'xdot', 'qdd', 'mass_matrix', 'elastic_force', 'damping_force',
            'gravity_force', 'tendon_generalized_force', 'tendon_lengths_m',
            'tendon_length_jacobian', 'velocity_bias',
        ]
        self.function = ca.Function('gvs_dynamics', [x, u], outputs, ['x', 'u'], names)
        self.linearization = ca.Function(
            'gvs_linearization',
            [x, u],
            [ca.jacobian(xdot, x), ca.jacobian(xdot, u), xdot],
            ['x', 'u'],
            ['A', 'B', 'drift'],
        )
        static_residual = tendon_force + gravity - elastic
        self.q_symbol = q
        self.u_symbol = u
        self.static_residual_expression = static_residual
        self.tip_position_expression = state.attachment_pose(self.design.tip)[:3, 3]
        self.static_equilibrium = ca.Function(
            'gvs_static_equilibrium',
            [q, u],
            [static_residual, ca.jacobian(static_residual, q)],
            ['q', 'u'],
            ['residual', 'jacobian'],
        )

    def evaluate(self, x, u):
        values = self.function(x=np.asarray(x, dtype=float), u=np.asarray(u, dtype=float))
        return {name: np.asarray(values[name], dtype=float) for name in self.function.name_out()}

    def linearize(self, x, u):
        values = self.linearization(
            x=np.asarray(x, dtype=float), u=np.asarray(u, dtype=float)
        )
        return tuple(np.asarray(values[name], dtype=float) for name in ('A', 'B', 'drift'))

    def equilibrium_terms(self, q, u):
        values = self.static_equilibrium(
            q=np.asarray(q, dtype=float), u=np.asarray(u, dtype=float)
        )
        return tuple(
            np.asarray(values[name], dtype=float)
            for name in ('residual', 'jacobian')
        )


class GVSStaticCasadiExpressions:
    """Static residual and tip graph without assembling inertial dynamics."""

    def __init__(self, expression: GVSContinuousDynamicsExpression):
        self.expression = expression
        self.design = expression.design
        self.parameters = expression.parameters
        topology = _topology(self.design)
        n = len(expression.coordinate_order)
        q = ca.MX.sym('q', n)
        u = ca.MX.sym('u', len(expression.tendon_order))
        state = _SymbolicKinematics(
            topology, q, self.parameters.integration_steps_per_segment
        )

        gravity = ca.MX.zeros(n, 1)
        gravity_vector = _dm(expression.gravity_robot_base_m_s2)
        for descriptor in _mass_descriptors(
            topology, self.parameters.quadrature_points_per_segment
        ):
            pose = (
                state.point_pose(descriptor['component'], descriptor['s'])
                if descriptor['kind'] == 'segment'
                else state.base_pose(descriptor['component'])
            )
            rotation = pose[:3, :3]
            position = pose[:3, 3] + ca.mtimes(rotation, _dm(descriptor['offset']))
            gravity += descriptor['mass'] * ca.mtimes(
                ca.jacobian(position, q).T, gravity_vector
            )

        elastic = ca.MX.zeros(n, 1)
        nodes, weights = _quadrature(
            self.parameters.quadrature_points_per_segment
        )
        for segment_index, segment in enumerate(topology[3]):
            local_q = q[4 * segment_index:4 * segment_index + 4]
            local_elastic = ca.MX.zeros(4, 1)
            natural = _dm(segment.natural_curvature_rad_m)
            for node, weight in zip(nodes, weights):
                phi1 = 2 * float(node) - 1
                basis = _dm([[1, phi1, 0, 0], [0, 0, 1, phi1]])
                stiffness, _ = _stiffness_and_damping(segment, float(node))
                local_elastic += segment.length_m * float(weight) * ca.mtimes(
                    [basis.T, _dm(stiffness), ca.mtimes(basis, local_q) - natural]
                )
            elastic[4 * segment_index:4 * segment_index + 4] = local_elastic

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
                (ca.norm_2(b - a) for a, b in zip(positions, positions[1:])),
                ca.MX(0),
            ))
        tendon_force = -ca.mtimes(ca.jacobian(ca.vertcat(*lengths), q).T, u)
        self.q_symbol = q
        self.u_symbol = u
        self.static_residual_expression = tendon_force + gravity - elastic
        self.tip_position_expression = state.attachment_pose(self.design.tip)[:3, 3]


@lru_cache(maxsize=8)
def _cached_functions(serialized_expression):
    expression = GVSContinuousDynamicsExpression.model_validate_json(
        serialized_expression, strict=True
    )
    return GVSCasadiFunctions(expression)


def functions_for(expression):
    parsed = GVSContinuousDynamicsExpression.model_validate(expression)
    serialized = json.dumps(parsed.model_dump(mode='json'), sort_keys=True, separators=(',', ':'))
    return _cached_functions(serialized)


def expression_from_system(system: DynamicSystem) -> GVSContinuousDynamicsExpression:
    if not isinstance(system.dynamics, Payload) or system.dynamics.contract != EXPRESSION_CONTRACT:
        raise ValueError('CASADI_LINEARIZER_UNSUPPORTED_EXPRESSION')
    return GVSContinuousDynamicsExpression.model_validate(system.dynamics.data)


def evaluate_system(system: DynamicSystem, x, u):
    return functions_for(expression_from_system(system)).evaluate(x, u)['xdot'].reshape(-1)


class CasadiLinearizer:
    """Generic public Linearizer dispatching through a typed expression adapter."""

    def __init__(self, parameters=None):
        pass

    def linearize(self, system: DynamicSystem) -> LinearizedModel:
        system = DynamicSystem.model_validate(system)
        if system.time_domain != 'continuous':
            raise ValueError('CASADI_LINEARIZER_REQUIRES_CONTINUOUS_SYSTEM')
        functions = functions_for(expression_from_system(system))
        A, B, drift = functions.linearize(system.x0, system.u0)
        return LinearizedModel(
            state_definition=system.state_definition,
            input_definition=system.input_definition,
            output_definition=system.output_definition,
            x0=system.x0,
            u0=system.u0,
            A=A.tolist(),
            B=B.tolist(),
            drift=drift.reshape(-1).tolist(),
            time_domain='continuous',
            timestep=None,
        )


class ContinuousLQRController:
    """Continuous LQR with an explicit equilibrium gate and final tension clamp."""

    def __init__(self, parameters):
        self.parameters = LQRParameters.model_validate(parameters)
        self.model = None
        self.K = None
        self.last_command = None

    def configure_model(self, model):
        from scipy.linalg import solve_continuous_are

        model = LinearizedModel.model_validate(model)
        if model.time_domain != 'continuous':
            raise ValueError('LQR_REQUIRES_CONTINUOUS_LINEARIZED_MODEL')
        nx = len(model.x0)
        nu = len(model.u0)
        if len(self.parameters.Q) != nx or len(self.parameters.R) != nu:
            raise ValueError('LQR_MODEL_WEIGHT_DIMENSION_MISMATCH')
        tendon_order = [spec.entity for spec in model.input_definition]
        if any(spec.dimension != 1 for spec in model.input_definition):
            raise ValueError('LQR_REQUIRES_SCALAR_TENDON_INPUT_SPECS')
        if tendon_order != self.parameters.tendon_order:
            raise ValueError('LQR_TENDON_ORDER_MISMATCH')
        drift = np.zeros(nx) if model.drift is None else np.asarray(model.drift)
        if np.linalg.norm(drift, ord=np.inf) > self.parameters.equilibrium_tolerance:
            raise ValueError('LQR_OPERATING_POINT_NOT_EQUILIBRIUM')
        A = np.asarray(model.A, dtype=float)
        B = np.asarray(model.B, dtype=float)
        Q = np.asarray(self.parameters.Q, dtype=float)
        R = np.asarray(self.parameters.R, dtype=float)
        if not np.allclose(Q, Q.T) or np.min(np.linalg.eigvalsh(Q)) < -1e-12:
            raise ValueError('LQR_Q_MUST_BE_POSITIVE_SEMIDEFINITE')
        if not np.allclose(R, R.T) or np.min(np.linalg.eigvalsh(R)) <= 0:
            raise ValueError('LQR_R_MUST_BE_POSITIVE_DEFINITE')
        solution = solve_continuous_are(A, B, Q, R)
        self.K = np.linalg.solve(R, B.T @ solution)
        self.model = model
        return self.K.copy()

    def command(self, time_s, observations):
        if self.model is None or self.K is None:
            raise ValueError('LQR_MODEL_NOT_CONFIGURED')
        state = observations.get('state') if isinstance(observations, dict) else observations
        state = np.asarray(state, dtype=float)
        if state.shape != (len(self.model.x0),) or not np.all(np.isfinite(state)):
            raise ValueError('LQR_STATE_DIMENSION_MISMATCH')
        raw = np.asarray(self.model.u0) - self.K @ (state - np.asarray(self.model.x0))
        bounded = np.clip(raw, 0, np.asarray(self.parameters.force_limits_n))
        result = LQRCommand(
            tendon_order=self.parameters.tendon_order,
            tendon_tensions_n=bounded.tolist(),
            raw_tendon_tensions_n=raw.tolist(),
            saturated=(bounded != raw).tolist(),
        )
        self.last_command = result
        return result

    def reset(self):
        self.last_command = None

    def restore(self, state):
        self.last_command = None if state is None else LQRCommand.model_validate(state.data)

    def finish(self, interrupted=False):
        pass

    def checkpoint(self):
        return Payload(
            contract='family.lqr_command',
            data=(self.last_command or LQRCommand(
                tendon_order=self.parameters.tendon_order,
                tendon_tensions_n=[0] * len(self.parameters.tendon_order),
                raw_tendon_tensions_n=[0] * len(self.parameters.tendon_order),
                saturated=[False] * len(self.parameters.tendon_order),
            )).model_dump(mode='json'),
        )


def gvs_build_system_tool(ctx, args):
    model = _bound_model(ctx)
    context = args.context
    if isinstance(context.scene, EvidenceRef):
        context = context.model_copy(update={
            'scene': Payload.model_validate(ctx.artifact(context.scene))
        })
    return model.build_system(
        ctx.input.robot,
        model.parameters,
        None,
        context,
    )


def gvs_build_system_tool_v2(ctx, args):
    """Export at x0/u0 while taking all physical context from the frozen task."""
    from schemas.platform_math import SystemContext

    model = _bound_model(ctx)
    system = model.build_system(
        ctx.input.robot,
        model.parameters,
        None,
        SystemContext(x0=args.x0, u0=args.u0, scene=ctx.input.task.environment),
    )
    reference = ctx.save_artifact(system, 'dynamic_system')
    return GVSSystemArtifactResult(
        system=reference,
        state_dimension=len(system.x0),
        input_dimension=len(system.u0),
    )


def linearize_tool(ctx, args: GVSLinearizeRequest):
    return CasadiLinearizer().linearize(args.system)


def linearize_tool_v2(ctx, args):
    source = args.system if isinstance(args.system, EvidenceRef) else None
    system = DynamicSystem.model_validate(
        ctx.artifact(args.system) if source is not None else args.system
    )
    linear = CasadiLinearizer().linearize(system)
    reference = ctx.save_artifact(linear, 'linearized_model')
    drift = np.zeros(len(linear.x0)) if linear.drift is None else np.asarray(linear.drift)
    return LinearizedModelArtifactResult(
        model=reference,
        source_system=source,
        state_dimension=len(linear.x0),
        input_dimension=len(linear.u0),
        time_domain=linear.time_domain,
        drift_norm_inf=float(np.linalg.norm(drift, ord=np.inf)),
    )


def gvs_equilibrium_tool(ctx, args):
    """Solve tendon + gravity - elastic = 0 with a damped AD Newton method."""
    from extensions.tendon_family.contracts import Design
    from schemas.platform_math import SystemContext

    design = Design.model_validate(ctx.input.robot.structure.data)
    order = [tendon.id for tendon in design.tendons]
    if set(args.tendon_tensions_n) != set(order):
        raise ValueError('GVS tendon tensions must cover exactly: ' + ', '.join(order))
    tensions = np.asarray([args.tendon_tensions_n[name] for name in order], dtype=float)
    limits = np.asarray([tendon.force_limit_n for tendon in design.tendons], dtype=float)
    if np.any(tensions > limits):
        raise ValueError('GVS tendon tension exceeds family.design force limit')

    model = _bound_model(ctx)
    n = len(coordinate_order(design))
    q = np.asarray(args.initial_q, dtype=float)
    if q.shape != (n,):
        raise ValueError('GVS_EQUILIBRIUM_INITIAL_Q_DIMENSION_MISMATCH')
    system = model.build_system(
        ctx.input.robot,
        model.parameters,
        None,
        SystemContext(
            x0=np.r_[q, np.zeros(n)].tolist(),
            u0=tensions.tolist(),
            scene=ctx.input.task.environment,
        ),
    )
    functions = functions_for(expression_from_system(system))
    iterations = 0
    converged = False
    for iteration in range(args.max_iterations + 1):
        residual, jacobian = functions.equilibrium_terms(q, tensions)
        residual = residual.reshape(-1)
        norm = float(np.linalg.norm(residual, ord=np.inf))
        if norm <= args.tolerance:
            converged = True
            iterations = iteration
            break
        if iteration == args.max_iterations:
            iterations = iteration
            break
        try:
            step = np.linalg.solve(jacobian, -residual)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(jacobian, -residual, rcond=None)[0]
        alpha = 1.0
        accepted = False
        for _ in range(12):
            candidate = q + alpha * step
            candidate_residual, _ = functions.equilibrium_terms(candidate, tensions)
            if np.linalg.norm(candidate_residual, ord=np.inf) < norm:
                q = candidate
                accepted = True
                break
            alpha *= 0.5
        if not accepted:
            q = q + alpha * step
        iterations = iteration + 1
    residual, _ = functions.equilibrium_terms(q, tensions)
    return GVSEquilibriumResult(
        coordinate_order=coordinate_order(design),
        tendon_order=order,
        q_equilibrium=q.tolist(),
        residual_norm=float(np.linalg.norm(residual, ord=np.inf)),
        converged=converged,
        iterations=iterations,
    )


def lqr_synthesize_tool(ctx, args):
    """Build diagonal weights, derive robot facts, and persist the full gain."""
    from extensions.tendon_family.contracts import Design

    model_reference = args.model if isinstance(args.model, EvidenceRef) else None
    model = LinearizedModel.model_validate(
        ctx.artifact(args.model) if model_reference is not None else args.model
    )
    if model_reference is None:
        model_reference = ctx.save_artifact(model, 'linearized_model')
    design = Design.model_validate(ctx.input.robot.structure.data)
    tendon_order = [tendon.id for tendon in design.tendons]
    force_limits = [tendon.force_limit_n for tendon in design.tendons]
    if [spec.entity for spec in model.input_definition] != tendon_order:
        raise ValueError('LQR_FROZEN_ROBOT_TENDON_ORDER_MISMATCH')
    state_names = [spec.name for spec in model.state_definition]
    unknown = set(args.state_weight_overrides) - set(state_names)
    if unknown:
        raise ValueError('LQR_UNKNOWN_STATE_WEIGHT_OVERRIDE: ' + ', '.join(sorted(unknown)))
    q_diagonal = [
        float(args.state_weight_overrides.get(
            name,
            args.state_rate_weight if name.endswith('.rate') else args.curvature_weight,
        ))
        for name in state_names
    ]
    r_diagonal = [float(args.tendon_tension_weight)] * len(tendon_order)
    parameters = LQRParameters(
        Q=np.diag(q_diagonal).tolist(),
        R=np.diag(r_diagonal).tolist(),
        tendon_order=tendon_order,
        force_limits_n=force_limits,
        equilibrium_tolerance=args.equilibrium_tolerance,
    )
    gain = ContinuousLQRController(parameters).configure_model(model)
    A = np.asarray(model.A, dtype=float)
    B = np.asarray(model.B, dtype=float)
    closed_loop = np.linalg.eigvals(A - B @ gain)
    max_real = float(np.max(closed_loop.real))
    controllability = np.hstack([np.linalg.matrix_power(A, index) @ B for index in range(len(model.x0))])
    rank = int(np.linalg.matrix_rank(controllability))
    unstable = [value for value in np.linalg.eigvals(A) if value.real >= -1e-10]
    stabilizability_issue = any(
        np.linalg.matrix_rank(np.hstack([value * np.eye(len(model.x0)) - A, B])) < len(model.x0)
        for value in unstable
    )
    gain_reference = ctx.save_artifact(LQRGainArtifact(
        K=gain.tolist(),
        Q_diagonal=q_diagonal,
        R_diagonal=r_diagonal,
        x0=model.x0,
        u0=model.u0,
        tendon_order=tendon_order,
        force_limits_n=force_limits,
    ), 'lqr_gain')
    return LQRSynthesisResult(
        operating_point=model_reference,
        gain=gain_reference,
        gain_shape=gain.shape,
        closed_loop_stable=max_real < 0.0,
        max_real_closed_loop_eigenvalue=max_real,
        controllability_rank=rank,
        stabilizability_issue=stabilizability_issue,
        tendon_order=tendon_order,
    )


def lqr_describe_tool(ctx, args):
    return LQRDescription()


def lqr_describe_tool_v2(ctx, args):
    return LQRSynthesisDescription()
