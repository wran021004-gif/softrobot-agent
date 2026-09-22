"""Trusted PCC reach and GVS inverse OptimizationAssembler implementations."""
from __future__ import annotations

import casadi as ca
import numpy as np

from extensions.experiment_dynamics.contracts import Assembly
from extensions.optimization.ipopt import expression_payload
from extensions.tendon_family.contracts import (
    Design,
    GVSContinuousDynamicsExpression,
    GVSInverseAssemblerParameters,
    GVSModelParameters,
    PCCReachAssemblerParameters,
    Rigid,
    Segment,
)
from extensions.tendon_family.gvs import coordinate_order
from extensions.tendon_family.gvs_casadi import GVSStaticCasadiExpressions, _segment_pose
from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation, rigid_transform
from schemas.platform import Binding, Objective, Payload, RobotDescription, TaskDefinition
from schemas.platform_math import (
    MathematicalModel,
    OptimizationConstraint,
    OptimizationProblem,
    OptimizationSpecification,
    ParameterDefinitions,
    SystemContext,
)


def _design(robot):
    robot = RobotDescription.model_validate(robot)
    if robot.structure.contract != 'family.design':
        raise ValueError('OPTIMIZATION_REQUIRES_FAMILY_DESIGN')
    return Design.model_validate(robot.structure.data)


def _assembly(task):
    task = TaskDefinition.model_validate(task)
    if task.environment.contract != 'experiment.assembly':
        raise ValueError('OPTIMIZATION_REQUIRES_EXPERIMENT_ASSEMBLY')
    return Assembly.model_validate(task.environment.data)


def _task_target(task):
    task = TaskDefinition.model_validate(task)
    value = task.goal.data.get('target_m')
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError('OPTIMIZATION_REQUIRES_TASK_TARGET_M')
    return np.asarray(value, dtype=float)


def _world_tip(local_tip, assembly):
    rotation = ca.DM(quaternion_wxyz_to_rotation(assembly.mount.quaternion_wxyz))
    return ca.mtimes(rotation, local_tip) + ca.DM(assembly.mount.position_m)


def _pcc_tip(design, configuration, length_variables):
    components = {component.id: component for component in design.components}
    curvature = {
        name: (value.curvature_y_rad_m, value.curvature_z_rad_m)
        for name, value in configuration.segments.items()
    }
    expected = {component.id for component in design.components if isinstance(component, Segment)}
    if set(curvature) != expected:
        raise ValueError('PCC_CONFIGURATION_SEGMENTS_MISMATCH')
    base_cache = {}
    point_cache = {}

    def point_pose(part, s):
        key = (part, float(s))
        if key in point_cache:
            return point_cache[key]
        if part == 'fixed_base':
            if abs(float(s)) > 1e-12:
                raise ValueError('fixed_base has no nonzero coordinate')
            result = ca.DM.eye(4)
        else:
            component = components[part]
            base = base_pose(part)
            if isinstance(component, Segment):
                length = length_variables.get(component.id, component.length_m)
                ky, kz = curvature[component.id]
                result = ca.mtimes(base, _segment_pose(length * float(s), ky, kz))
            elif isinstance(component, Rigid):
                if abs(float(s)) > 1e-12:
                    raise ValueError('Rigid PCC component does not support nonzero s')
                result = base
            else:
                raise ValueError('PCC_OPTIMIZATION_REQUIRES_SERIAL_EXECUTABLE_TOPOLOGY')
        point_cache[key] = result
        return result

    def base_pose(name):
        if name not in base_cache:
            component = components[name]
            connection = ca.DM(rigid_transform(
                component.connection.position_m,
                component.connection.quaternion_wxyz,
            ))
            base_cache[name] = ca.mtimes(
                point_pose(component.connection.part, component.connection.s), connection
            )
        return base_cache[name]

    attachment = ca.DM(rigid_transform(design.tip.position_m, design.tip.quaternion_wxyz))
    return ca.mtimes(point_pose(design.tip.part, design.tip.s), attachment)[:3, 3]


def pcc_authorization(robot, space, parameters):
    PCCReachAssemblerParameters.model_validate(parameters)
    return dict(space)


class PCCReachAssembler:
    def __init__(self, parameters):
        self.parameters = PCCReachAssemblerParameters.model_validate(parameters)

    def assemble(self, task, robot, space, mathematical_model, specification, context):
        MathematicalModel.model_validate(mathematical_model)
        specification = OptimizationSpecification.model_validate(specification)
        design = _design(robot)
        if len(specification.variables) != 1:
            raise ValueError('PCC_REACH_REQUIRES_ONE_AUTHORIZED_LENGTH_VARIABLE')
        path = specification.variables[0]
        parts = path.split('/')
        if len(parts) != 3 or parts[0] != 'components' or parts[2] != 'length_m':
            raise ValueError('PCC_REACH_VARIABLE_MUST_BE_COMPONENT_LENGTH')
        segment = next((item for item in design.components if item.id == parts[1]), None)
        if not isinstance(segment, Segment):
            raise ValueError('PCC_REACH_VARIABLE_MUST_REFERENCE_FLEXIBLE_SEGMENT')
        if set(item.template_id for item in specification.objectives) != {'tip_position_error_squared'}:
            raise ValueError('PCC_REACH_OBJECTIVE_REQUIRED')
        if set(item.template_id for item in specification.constraints) != {'authorized_design_bounds'}:
            raise ValueError('PCC_REACH_AUTHORIZED_DESIGN_BOUNDS_REQUIRED')
        variable = ca.MX.sym('pcc_length')
        local_tip = _pcc_tip(design, self.parameters.configuration, {segment.id: variable})
        target = ca.DM(_task_target(task))
        objective_expression = ca.sumsqr(_world_tip(local_tip, _assembly(task)) - target)
        weight = sum(item.weight for item in specification.objectives)
        objective_expression *= weight
        bundle, _ = expression_payload(
            [path], {'variables': {path: variable}, 'expression': objective_expression}, {}
        )
        initial = dict(specification.initial_guess)
        initial.setdefault(path, segment.length_m)
        return OptimizationProblem(
            variables={path: space[path]},
            objective=Objective(metric='tip_position_error_squared', direction='minimize', units='m^2'),
            objective_function=bundle,
            constraints=[],
            model_reference=Binding(
                extension_id='model.pcc',
                parameters=Payload(contract='family.pcc_model', data={}),
            ),
            initial_guess=initial,
        )


def gvs_authorization(robot, space, parameters):
    parameters = GVSInverseAssemblerParameters.model_validate(parameters)
    design = _design(robot)
    result = dict(space)
    for name in coordinate_order(design, parameters.basis):
        result['q/' + name] = {'type': 'number', 'bounds': [None, None], 'units': 'rad/m'}
    for tendon in design.tendons:
        result['tendon_tensions_n/' + tendon.id] = {
            'type': 'number', 'bounds': [0.0, tendon.force_limit_n], 'units': 'N'
        }
    return result


class GVSInverseAssembler:
    def __init__(self, parameters):
        self.parameters = GVSInverseAssemblerParameters.model_validate(parameters)

    def assemble(self, task, robot, space, mathematical_model, specification, context):
        MathematicalModel.model_validate(mathematical_model)
        specification = OptimizationSpecification.model_validate(specification)
        design = _design(robot)
        assembly = _assembly(task)
        if assembly.external_forces:
            raise ValueError('GVS_EXTERNAL_APPLIED_FORCES_UNSUPPORTED')
        coordinates = coordinate_order(design, self.parameters.basis)
        tendon_order = [tendon.id for tendon in design.tendons]
        q_paths = ['q/' + name for name in coordinates]
        tension_paths = ['tendon_tensions_n/' + name for name in tendon_order]
        rotation = quaternion_wxyz_to_rotation(assembly.mount.quaternion_wxyz)
        gravity_robot = rotation.T @ np.asarray(assembly.environment.gravity_m_s2, dtype=float)
        model_parameters = GVSModelParameters(basis=self.parameters.basis)
        functions = GVSStaticCasadiExpressions(GVSContinuousDynamicsExpression(
            design=design,
            parameters=model_parameters,
            gravity_robot_base_m_s2=tuple(gravity_robot),
            coordinate_order=coordinates,
            tendon_order=tendon_order,
            tendon_force_limits_n=[tendon.force_limit_n for tendon in design.tendons],
        ))
        symbols = {name: ca.MX.sym('v_' + str(index)) for index, name in enumerate(specification.variables)}
        objective_ids = [item.template_id for item in specification.objectives]
        constraint_ids = {item.template_id for item in specification.constraints}

        if self.parameters.template == 'inverse_shape':
            if specification.variables != tension_paths:
                raise ValueError('INVERSE_SHAPE_REQUIRES_ALL_TENDONS_IN_ROBOT_ORDER')
            if objective_ids != ['inverse_shape_static']:
                raise ValueError('INVERSE_SHAPE_STATIC_OBJECTIVE_REQUIRED')
            if constraint_ids != {'tendon_force_bounds'}:
                raise ValueError('INVERSE_SHAPE_TENDON_FORCE_BOUNDS_REQUIRED')
            q_target = np.asarray(self.parameters.q_target, dtype=float)
            if q_target.shape != (len(coordinates),):
                raise ValueError('INVERSE_SHAPE_Q_TARGET_DIMENSION_MISMATCH')
            q_value = ca.DM(q_target)
            tension_value = ca.vertcat(*[symbols[name] for name in tension_paths])
            residual = ca.substitute(
                functions.static_residual_expression,
                ca.vertcat(functions.q_symbol, functions.u_symbol),
                ca.vertcat(q_value, tension_value),
            )
            objective_expression = specification.objectives[0].weight * ca.sumsqr(residual)
            constraints = {}
            metric = 'inverse_shape_static_residual_squared'
            units = 'generalized_force^2'
        else:
            expected = q_paths + tension_paths
            if specification.variables != expected:
                raise ValueError('INVERSE_TIP_STATIC_REQUIRES_Q_AND_TENDONS_IN_MODEL_ORDER')
            if not objective_ids or objective_ids[0] != 'tip_position_error_squared' or set(objective_ids) - {'tip_position_error_squared', 'tendon_effort'}:
                raise ValueError('INVERSE_TIP_STATIC_OBJECTIVES_INVALID')
            if constraint_ids != {'static_equilibrium', 'tendon_force_bounds'}:
                raise ValueError('INVERSE_TIP_STATIC_CONSTRAINTS_REQUIRED')
            q_value = ca.vertcat(*[symbols[name] for name in q_paths])
            tension_value = ca.vertcat(*[symbols[name] for name in tension_paths])
            replacements = ca.vertcat(q_value, tension_value)
            originals = ca.vertcat(functions.q_symbol, functions.u_symbol)
            residual = ca.substitute(functions.static_residual_expression, originals, replacements)
            local_tip = ca.substitute(functions.tip_position_expression, originals, replacements)
            world_tip = _world_tip(local_tip, assembly)
            target = ca.DM(_task_target(task))
            weights = {item.template_id: item.weight for item in specification.objectives}
            objective_expression = weights['tip_position_error_squared'] * ca.sumsqr(world_tip - target)
            if 'tendon_effort' in weights:
                objective_expression += weights['tendon_effort'] * ca.sumsqr(tension_value)
            constraints = {
                'static_equilibrium_' + str(index): residual[index]
                for index in range(len(coordinates))
            }
            metric = 'inverse_tip_static_tip_error_squared'
            units = 'm^2'

        bundle, selectors = expression_payload(
            specification.variables,
            {'variables': symbols, 'expression': objective_expression},
            constraints,
        )
        problem_constraints = [
            OptimizationConstraint(
                name=name,
                expression=selector,
                units='generalized_force',
                lower=0.0,
                upper=0.0,
            )
            for name, selector in zip(constraints, selectors)
        ]
        return OptimizationProblem(
            variables={name: space[name] for name in specification.variables},
            objective=Objective(metric=metric, direction='minimize', units=units),
            objective_function=bundle,
            constraints=problem_constraints,
            model_reference=Binding(
                extension_id='model.gvs',
                parameters=Payload(
                    contract='family.gvs_model',
                    data=model_parameters.model_dump(mode='json'),
                ),
            ),
            initial_guess=specification.initial_guess,
        )
