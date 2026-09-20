"""SI family description. Reserved topology types are descriptive, never executable."""
from typing import Literal, Annotated
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.platform import EvidenceRef
from schemas.platform_math import (
    DynamicSystem,
    LinearizedModel,
    MathematicalModel,
    ModelCapabilities,
    ModelVariable,
    ParameterDefinitions,
    SystemContext,
)
from schemas.environment_spec import Vec3
from extensions.experiment_dynamics.contracts import Matrix3, Mount


Name = Annotated[str, Field(pattern=r'^[A-Za-z][A-Za-z0-9_]*$')]


class Section(Contract):
    kind: Literal['circle', 'tube', 'ellipse', 'rectangle', 'polygon']
    parameters: dict[str, float] = Field(default_factory=dict)
    outer_yz_m: list[tuple[float, float]] = Field(default_factory=list)
    holes_yz_m: list[list[tuple[float, float]]] = Field(default_factory=list)
    angle_rad: float = 0.


class Station(Contract):
    s: float = Field(ge=0, le=1)
    section: Section


class PhysicalInput(Contract):
    mode: Literal['material', 'equivalent']
    density_kg_m3: float | None = Field(default=None, gt=0)
    young_pa: float | None = Field(default=None, gt=0)
    line_density_kg_m: float | None = Field(default=None, gt=0)
    bending_ei_nm2: tuple[float, float] | None = None
    bending_viscosity_nm2_s: tuple[float, float] = (0., 0.)

    @model_validator(mode='after')
    def authority(self):
        if self.mode == 'material':
            if self.density_kg_m3 is None or self.young_pa is None or self.line_density_kg_m is not None or self.bending_ei_nm2 is not None:
                raise ValueError('MATERIAL_AUTHORITY: density and Young modulus only')
        elif self.line_density_kg_m is None or self.bending_ei_nm2 is None or self.density_kg_m3 is not None or self.young_pa is not None:
            raise ValueError('EQUIVALENT_AUTHORITY: line density and principal bending EI only')
        if any(x < 0 for x in self.bending_viscosity_nm2_s) or (self.bending_ei_nm2 and min(self.bending_ei_nm2) <= 0):
            raise ValueError('INVALID_BENDING_PARAMETERS')
        return self


class Attachment(Contract):
    part: Name = 'fixed_base'
    s: float = Field(default=0., ge=0, le=1)
    position_m: Vec3 = (0., 0., 0.)
    quaternion_wxyz: tuple[float, float, float, float] = (1., 0., 0., 0.)

    @model_validator(mode='after')
    def quaternion(self):
        Mount(quaternion_wxyz=self.quaternion_wxyz)
        return self


class Segment(Contract):
    id: Name
    kind: Literal['flexible_segment'] = 'flexible_segment'
    connection: Attachment = Field(default_factory=Attachment)
    length_m: float = Field(gt=0)
    # Compatibility input only. Recommended inputs put this numerical model
    # choice in family.discretization. Normalization removes it from Design.
    cells: int | None = Field(default=None, gt=0, strict=True, exclude=True)
    sections: list[Station] = Field(min_length=1)
    interpolation: Literal['linear', 'step'] = 'step'
    physics: PhysicalInput
    natural_curvature_rad_m: tuple[float, float] = (0., 0.)


class Rigid(Contract):
    id: Name
    kind: Literal['rigid_connector', 'guide', 'payload']
    connection: Attachment
    mass_kg: float = Field(gt=0)
    com_local_m: Vec3 = (0., 0., 0.)
    inertia_com_local_kg_m2: Matrix3
    # A separate physical/visual envelope; guide holes do not alter supplied inertia.
    envelope_halfsize_m: Vec3
    guide_holes: dict[str, Vec3] = Field(default_factory=dict)
    hole_radius_m: float = Field(default=0., ge=0)


class Reserved(Contract):
    id: Name
    kind: Literal['discrete_flexure', 'rigid_tendon_joint', 'branch', 'closed_chain', 'cable_parallel']
    description: str
    attachments: list[Attachment] = Field(default_factory=list)
    status: Literal['descriptive_only'] = 'descriptive_only'


class RoutePoint(Contract):
    attachment: Attachment
    hole: str | None = None
    role: Literal['start', 'guide', 'anchor']


class Tendon(Contract):
    id: Name
    points: list[RoutePoint] = Field(min_length=2)
    diameter_m: float = Field(gt=0)
    model: Literal['straight_frictionless'] = 'straight_frictionless'
    length_servo_gain_n_m: float = Field(gt=0)
    pretension_n: float = Field(default=0., ge=0)
    force_limit_n: float = Field(gt=0)


class Transmission(Contract):
    tendon: Name
    ratio: float  # metres payout / command unit; sign is winding direction


class Actuator(Contract):
    id: Name
    command_type: Literal['displacement', 'rotation'] = 'displacement'
    units: Literal['m', 'rad'] = 'm'
    drum_radius_m: float | None = Field(default=None, gt=0)
    transmission: list[Transmission] = Field(min_length=1)
    limits: tuple[float, float]
    velocity_limit: float = Field(gt=0)

    @model_validator(mode='after')
    def consistency(self):
        if self.limits[0] >= self.limits[1] or not self.limits[0] <= 0 <= self.limits[1]:
            raise ValueError('ACTUATOR_LIMITS_MUST_CONTAIN_ZERO')
        if (self.command_type == 'rotation') != (self.units == 'rad') or (self.command_type == 'rotation') != (self.drum_radius_m is not None):
            raise ValueError('ROTATION_REQUIRES_RAD_AND_DRUM_RADIUS')
        if any(t.ratio == 0 for t in self.transmission):
            raise ValueError('ZERO_TRANSMISSION')
        return self


class Design(Contract):
    version: Literal['tendon_family_v1'] = 'tendon_family_v1'
    id: Name
    components: list[Annotated[Segment | Rigid | Reserved, Field(discriminator='kind')]] = Field(min_length=1)
    tendons: list[Tendon] = Field(min_length=1)
    actuators: list[Actuator] = Field(min_length=1)
    tip: Attachment
    metadata: dict = Field(default_factory=dict, description='Descriptive only; no hidden physical parameters')


class Initial(Contract):
    qpos_rad: dict[str, float] = Field(default_factory=dict)
    qvel_rad_s: dict[str, float] = Field(default_factory=dict)
    unspecified: Literal['zero'] = 'zero'


class Control(Contract):
    mode: Literal['deterministic', 'tip_feedback'] = 'tip_feedback'
    reference: 'Reference | None' = None
    commands: dict[str, float] = Field(default_factory=dict)
    ramp_s: float = Field(default=.1, gt=0)
    feedback_gain: float = Field(default=1., gt=0)
    damping: float = Field(default=.01, gt=0)
    max_joint_update_rad: float = Field(default=.02, gt=0)


class Reference(Contract):
    kind: Literal['task_goal', 'actuator_commands']
    commands: dict[str, float] = Field(default_factory=dict)
    units: Literal['m_or_rad_by_actuator', 'm']
    frame: Literal['actuator', 'world']

    @model_validator(mode='after')
    def meaning(self):
        if self.kind == 'task_goal' and (self.commands or self.units != 'm' or self.frame != 'world'):
            raise ValueError('TASK_GOAL_REFERENCE_REQUIRES_WORLD_METRES')
        if self.kind == 'actuator_commands' and (self.units != 'm_or_rad_by_actuator' or self.frame != 'actuator'):
            raise ValueError('ACTUATOR_REFERENCE_REQUIRES_NATIVE_UNITS')
        return self


class DynamicsModel(Contract):
    """Compatibility payload for serial bending; public capabilities use MathematicalModel."""
    model_id: Literal['serial_bending_cells_v1'] = 'serial_bending_cells_v1'
    coordinates: Literal['two_principal_bending_angles_per_cell'] = 'two_principal_bending_angles_per_cell'
    equations: Literal['serial_rigid_body_dynamics_with_hinge_bending'] = 'serial_rigid_body_dynamics_with_hinge_bending'
    tendon_model: Literal['straight_frictionless_length_servo'] = 'straight_frictionless_length_servo'
    included: tuple[str, ...] = ('rigid_body_inertia', 'gravity', 'hinge_elasticity', 'hinge_damping', 'external_body_forces')
    omitted: tuple[str, ...] = ('axial_stretch', 'shear', 'material_torsion', 'tendon_friction', 'rope_elasticity', 'motor_dynamics', 'self_collision')

    @property
    def mathematical_model(self) -> MathematicalModel:
        # Plain property: old JSON, model identity and historical payloads do not
        # acquire new fields. n_dof/n_actuator resolve from the selected design.
        return MathematicalModel(
            state_definition=[
                ModelVariable(name='joint_position', dimension='n_dof', units='rad', frame='joint_local'),
                ModelVariable(name='joint_velocity', dimension='n_dof', units='rad/s', frame='joint_local')],
            input_definition=[ModelVariable(name='actuator_command', dimension='n_actuator',
                units='m_or_rad_by_actuator', frame='actuator')],
            output_definition=[ModelVariable(name='tip_position', dimension=3, units='m', frame='world'),
                ModelVariable(name='tendon_length', dimension='n_tendon', units='m', frame='path'),
                ModelVariable(name='tendon_tension', dimension='n_tendon', units='N', frame='path')],
            required_robot_data=['family.design.components', 'family.design.tendons', 'family.design.actuators', 'family.design.tip'],
            discretization_contract='family.discretization',
            capabilities=ModelCapabilities(kinematics=True, dynamics=True),
            representations=[])  # Existing backends execute it; no standard IR exporter yet.

    @model_validator(mode='after')
    def implemented_effects(self):
        for name in ('included', 'omitted'):
            if getattr(self, name) != type(self).model_fields[name].default:
                raise ValueError('PHYSICS_SWITCH_UNSUPPORTED: '+name+' describes the registered equations')
        return self


class Parameters(Contract):
    model: Literal['matlab_serial_bending_v1', 'mujoco_serial_bending_v1'] = 'matlab_serial_bending_v1'
    max_step_s: float = Field(default=.001, gt=0, description='MATLAB only; MuJoCo uses scene timestep_s')
    rtol: float = Field(default=1e-5, gt=0, description='MATLAB ode15s only')
    atol: float = Field(default=1e-7, gt=0, description='MATLAB ode15s only')
    contact_stiffness_n_m: float = Field(default=5000., gt=0, description='MATLAB penalty only; MuJoCo contact is recorded in XML')
    contact_damping_n_s_m: float = Field(default=5., ge=0, description='MATLAB penalty only')


class MatlabParameters(Contract):
    integrator: Literal['ode15s'] = 'ode15s'
    max_step_s: float = Field(default=.001, gt=0)
    rtol: float = Field(default=1e-5, gt=0)
    atol: float = Field(default=1e-7, gt=0)
    contact_model: Literal['lowest_envelope_vertex_penalty'] = 'lowest_envelope_vertex_penalty'
    contact_stiffness_n_m: float = Field(default=5000., gt=0)
    contact_damping_n_s_m: float = Field(default=5., ge=0)


class MujocoParameters(Contract):
    integrator: Literal['implicitfast'] = 'implicitfast'
    timestep_source: Literal['task.timing.timestep_s'] = 'task.timing.timestep_s'
    contact_model: Literal['mujoco_convex_native'] = 'mujoco_convex_native'
    friction: tuple[float, float, float] = (0., 0., 0.)


class Data(Contract):
    physics_identity: str
    scene_identity: str
    timings_s: dict[str, float]
    numerical_steps: int
    reason: str | None = None
    applicability: dict
    exported_files: list[str]
    execution_plan: dict = Field(default_factory=dict)
    control_identity: str | None = None


class ExperimentSpec(Contract):
    """Immutable composition view; editable values remain in their source objects."""
    version: Literal['family_experiment_v1'] = 'family_experiment_v1'
    task_identity: str
    design_identity: str
    discretization_identity: str
    physics_identity: str
    scene_identity: str
    dynamics_model_identity: str | None = None
    control_identity: str | None = None
    source_roles: dict[str, str]


class Space(Contract):
    # Physical design paths or full physical-design options.
    parameters: ParameterDefinitions = Field(default_factory=dict)
    control_parameters: ParameterDefinitions = Field(default_factory=dict)
    model_parameters: ParameterDefinitions = Field(default_factory=dict, description=
        'model/<path> in dynamics_model parameters: model-specific tuning such as regularization. '
        'Real material Young modulus stays in physical parameters; basis order belongs to discretization_parameters.')
    templates: dict[str, Design] = Field(default_factory=dict)
    # A complete template that changes flexible-segment IDs must declare its
    # complete mesh here. Baseline meshes are never guessed onto new segments.
    template_discretizations: dict[str, 'Discretization'] = Field(default_factory=dict)
    # Numerical-model edits use "discretization/cells/<segment>" paths.
    discretization_parameters: ParameterDefinitions = Field(default_factory=dict)

    @model_validator(mode='after')
    def template_meshes(self):
        if any(not path.startswith('model/') for path in self.model_parameters):
            raise ValueError('MODEL_PARAMETER_PATH_REQUIRES_MODEL_PREFIX')
        unknown = set(self.template_discretizations) - set(self.templates)
        if unknown:
            raise ValueError('DISCRETIZATION_FOR_UNKNOWN_TEMPLATE: '+','.join(sorted(unknown)))
        return self


class Discretization(Contract):
    version: Literal['serial_bending_discretization_v1'] = 'serial_bending_discretization_v1'
    model: Literal['serial_bending_cells_v1'] = 'serial_bending_cells_v1'
    cells: dict[Name, int] = Field(min_length=1)
    coordinates: Literal['two_principal_bending_angles_per_cell'] = 'two_principal_bending_angles_per_cell'

    @model_validator(mode='after')
    def positive_cells(self):
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in self.cells.values()):
            raise ValueError('DISCRETIZATION_CELLS_MUST_BE_POSITIVE_INTEGERS')
        return self


class BuildRequest(Contract):
    baseline: Design
    space: Space
    discretization: Discretization | None = None
    changes: dict = Field(default_factory=dict)


class BuildResult(Contract):
    status: Literal['valid', 'physically_invalid', 'backend_unsupported']
    candidate: Design | None = None
    discretization: Discretization | None = None
    summary: list[dict] = Field(default_factory=list)
    resolved_physics: dict | None = None
    applicability: dict = Field(default_factory=dict)
    source_roles: dict[str, str] = Field(default_factory=dict)
    reason: str | None = None


class PCCModelParameters(Contract):
    model_id: Literal['pcc_constant_curvature_v1'] = 'pcc_constant_curvature_v1'

    @property
    def mathematical_model(self) -> MathematicalModel:
        return MathematicalModel(
            state_definition=[
                ModelVariable(
                    name='segment_curvature',
                    dimension='2*n_flexible_segments',
                    units='rad/m',
                    frame='segment_local',
                )
            ],
            input_definition=[],
            output_definition=[
                ModelVariable(
                    name='tip_position',
                    dimension=3,
                    units='m',
                    frame='robot_base',
                ),
                ModelVariable(
                    name='tip_rotation_matrix',
                    dimension=9,
                    units='1',
                    frame='robot_base',
                ),
            ],
            required_robot_data=[
                'family.design.components',
                'family.design.tip',
            ],
            discretization_contract=None,
            capabilities=ModelCapabilities(
                kinematics=True,
                statics=False,
                dynamics=False,
                linearization=False,
                gradients=False,
            ),
            representations=[],
        )


class PCCSegmentConfiguration(Contract):
    curvature_y_rad_m: FiniteFloat = Field(
        description=(
            'Actual total geometric curvature about local +y in rad/m; '
            'not an increment relative to natural_curvature_rad_m.'
        )
    )
    curvature_z_rad_m: FiniteFloat = Field(
        description=(
            'Actual total geometric curvature about local +z in rad/m; '
            'not an increment relative to natural_curvature_rad_m.'
        )
    )


class PCCConfiguration(Contract):
    segments: dict[Name, PCCSegmentConfiguration] = Field(min_length=1)


class PCCForwardRequest(Contract):
    configuration: PCCConfiguration
    samples_per_segment: int = Field(default=51, ge=2, le=1001)


class PCCPose(Contract):
    position_m: Vec3
    rotation_matrix: Matrix3


class PCCSegmentKinematics(Contract):
    base: PCCPose
    tip: PCCPose
    backbone_points_m: list[Vec3] = Field(min_length=2)


class PCCKinematicsResult(Contract):
    model_id: Literal['pcc_constant_curvature_v1'] = 'pcc_constant_curvature_v1'
    frame: Literal['robot_base'] = 'robot_base'
    configuration: PCCConfiguration
    chain: list[Name] = Field(min_length=1)
    segments: dict[Name, PCCSegmentKinematics]
    tip: PCCPose


class PCCForwardRequestV2(Contract):
    configuration: PCCConfiguration
    include_backbone: bool = False
    samples_per_segment: int = Field(default=51, ge=2, le=1001)


class PCCKinematicsResultV2(Contract):
    model_id: Literal['pcc_constant_curvature_v1'] = 'pcc_constant_curvature_v1'
    frame: Literal['robot_base'] = 'robot_base'
    configuration: PCCConfiguration
    chain: list[Name] = Field(min_length=1)
    segment_end_poses: dict[Name, PCCPose]
    tip: PCCPose
    backbone_points_m: dict[Name, list[Vec3]] | None = None


class PCCDescribeRequest(Contract):
    pass


class PCCSegmentDescription(Contract):
    segment: Name
    coordinates: tuple[
        Literal['curvature_y_rad_m'],
        Literal['curvature_z_rad_m'],
    ] = ('curvature_y_rad_m', 'curvature_z_rad_m')


class PCCDescription(Contract):
    model_id: Literal['pcc_constant_curvature_v1'] = 'pcc_constant_curvature_v1'
    frame: Literal['robot_base'] = 'robot_base'
    segments: list[PCCSegmentDescription] = Field(min_length=1)
    curvature_semantics: Literal['actual_total_curvature'] = 'actual_total_curvature'
    natural_curvature_role: Literal['constitutive_reference_only'] = 'constitutive_reference_only'


class GVSModelParameters(Contract):
    model_id: Literal['gvs_variable_strain_bending_v1'] = 'gvs_variable_strain_bending_v1'
    integration_steps_per_segment: int = Field(default=24, ge=4, le=200)
    quadrature_points_per_segment: int = Field(default=5, ge=2, le=20)
    finite_difference_step: float = Field(default=1e-6, gt=0, le=1e-3)

    @property
    def mathematical_model(self) -> MathematicalModel:
        return MathematicalModel(
            state_definition=[
                ModelVariable(
                    name='strain_coefficients',
                    dimension='4*n_flexible_segments',
                    units='rad/m',
                    frame='segment_local',
                ),
                ModelVariable(
                    name='strain_coefficient_rates',
                    dimension='4*n_flexible_segments',
                    units='rad/(m*s)',
                    frame='segment_local',
                ),
            ],
            input_definition=[
                ModelVariable(
                    name='tendon_tension',
                    dimension='n_tendons',
                    units='N',
                    frame='tendon_path',
                )
            ],
            output_definition=[
                ModelVariable(
                    name='strain_coefficient_acceleration',
                    dimension='4*n_flexible_segments',
                    units='rad/(m*s^2)',
                    frame='segment_local',
                ),
                ModelVariable(
                    name='tip_position',
                    dimension=3,
                    units='m',
                    frame='robot_base',
                ),
            ],
            required_robot_data=[
                'family.design.components.length_m',
                'family.design.components.sections',
                'family.design.components.physics',
                'family.design.components.natural_curvature_rad_m',
                'family.design.components.mass_kg',
                'family.design.components.com_local_m',
                'family.design.components.inertia_com_local_kg_m2',
                'family.design.tendons',
            ],
            discretization_contract=None,
            capabilities=ModelCapabilities(
                kinematics=True,
                statics=True,
                dynamics=True,
                linearization=False,
                gradients=True,
            ),
            representations=['dynamic_system'],
        )


NonNegativeFinite = Annotated[FiniteFloat, Field(ge=0)]


class GVSContinuousDynamicsExpression(Contract):
    """Serializable recipe for the trusted CasADi GVS expression adapter."""
    expression_id: Literal['family.gvs_continuous_dynamics'] = 'family.gvs_continuous_dynamics'
    model_id: Literal['gvs_variable_strain_bending_v1'] = 'gvs_variable_strain_bending_v1'
    symbolic_type: Literal['MX'] = 'MX'
    design: Design
    parameters: GVSModelParameters
    gravity_robot_base_m_s2: Vec3
    coordinate_order: list[str] = Field(min_length=1)
    tendon_order: list[Name] = Field(min_length=1)
    tendon_force_limits_n: list[Annotated[FiniteFloat, Field(gt=0)]] = Field(min_length=1)

    @model_validator(mode='after')
    def dimensions(self):
        if len(self.coordinate_order) != 4 * sum(
            isinstance(component, Segment) for component in self.design.components
        ):
            raise ValueError('GVS_EXPRESSION_COORDINATE_ORDER_MISMATCH')
        expected = [tendon.id for tendon in self.design.tendons]
        if self.tendon_order != expected or len(self.tendon_force_limits_n) != len(expected):
            raise ValueError('GVS_EXPRESSION_TENDON_ORDER_MISMATCH')
        if self.tendon_force_limits_n != [tendon.force_limit_n for tendon in self.design.tendons]:
            raise ValueError('GVS_EXPRESSION_FORCE_LIMIT_MISMATCH')
        return self


class GVSBuildSystemRequest(Contract):
    context: SystemContext


class GVSLinearizeRequest(Contract):
    system: DynamicSystem


class GVSBuildSystemRequestV2(Contract):
    x0: list[FiniteFloat]
    u0: list[FiniteFloat]


class GVSSystemArtifactResult(Contract):
    model_id: Literal['gvs_variable_strain_bending_v1'] = 'gvs_variable_strain_bending_v1'
    system: EvidenceRef
    state_dimension: int = Field(gt=0)
    input_dimension: int = Field(gt=0)
    environment_source: Literal['frozen_task_environment'] = 'frozen_task_environment'


class GVSLinearizeRequestV2(Contract):
    system: DynamicSystem | EvidenceRef


class LinearizedModelArtifactResult(Contract):
    model: EvidenceRef
    source_system: EvidenceRef | None = None
    state_dimension: int = Field(gt=0)
    input_dimension: int = Field(gt=0)
    time_domain: Literal['continuous', 'discrete']
    drift_norm_inf: NonNegativeFinite


class CasadiLinearizerParameters(Contract):
    pass


class LQRParameters(Contract):
    Q: list[list[FiniteFloat]]
    R: list[list[FiniteFloat]]
    tendon_order: list[Name] = Field(min_length=1)
    force_limits_n: list[float] = Field(min_length=1)
    equilibrium_tolerance: float = Field(default=1e-7, gt=0)

    @model_validator(mode='after')
    def matrices_and_limits(self):
        if len(self.Q) == 0 or any(len(row) != len(self.Q) for row in self.Q):
            raise ValueError('LQR_Q_MUST_BE_SQUARE')
        if len(self.R) == 0 or any(len(row) != len(self.R) for row in self.R):
            raise ValueError('LQR_R_MUST_BE_SQUARE')
        if len(self.tendon_order) != len(self.force_limits_n) or len(self.R) != len(self.tendon_order):
            raise ValueError('LQR_INPUT_DIMENSION_MISMATCH')
        if any(limit <= 0 for limit in self.force_limits_n):
            raise ValueError('LQR_FORCE_LIMIT_MUST_BE_POSITIVE')
        return self


class LQRCommand(Contract):
    tendon_order: list[Name]
    tendon_tensions_n: list[NonNegativeFinite]
    raw_tendon_tensions_n: list[FiniteFloat]
    saturated: list[bool]


class LQRDescribeRequest(Contract):
    pass


class LQRDescription(Contract):
    algorithm: Literal['continuous_time_lqr'] = 'continuous_time_lqr'
    model_input: Literal['LinearizedModel'] = 'LinearizedModel'
    required_parameters: tuple[
        Literal['Q'], Literal['R'], Literal['tendon_order'],
        Literal['force_limits_n'], Literal['equilibrium_tolerance'],
    ] = ('Q', 'R', 'tendon_order', 'force_limits_n', 'equilibrium_tolerance')
    state_observation: Literal[
        'ordered vector matching LinearizedModel.state_definition'
    ] = 'ordered vector matching LinearizedModel.state_definition'
    command_output: Literal['bounded_model_space_tendon_tensions_n'] = 'bounded_model_space_tendon_tensions_n'
    equation: Literal['u=u0-K*(x-x0)'] = 'u=u0-K*(x-x0)'
    equilibrium_requirement: Literal['norm(drift,inf)<=equilibrium_tolerance'] = 'norm(drift,inf)<=equilibrium_tolerance'
    bound_semantics: Literal['clip_each_tendon_to_[0,force_limit_n]'] = 'clip_each_tendon_to_[0,force_limit_n]'


class LQRSynthesizeRequest(Contract):
    model: LinearizedModel | EvidenceRef
    curvature_weight: FiniteFloat = Field(default=1.0, gt=0)
    state_rate_weight: FiniteFloat = Field(default=0.1, gt=0)
    tendon_tension_weight: FiniteFloat = Field(default=1.0, gt=0)
    state_weight_overrides: dict[str, NonNegativeFinite] = Field(default_factory=dict)
    equilibrium_tolerance: FiniteFloat = Field(
        default=1e-7, gt=0,
        description='Maximum infinity norm of LinearizedModel drift in state-derivative units.',
    )


class LQRGainArtifact(Contract):
    controller_type: Literal['continuous_time_lqr'] = 'continuous_time_lqr'
    K: list[list[FiniteFloat]]
    Q_diagonal: list[NonNegativeFinite]
    R_diagonal: list[FiniteFloat]
    x0: list[FiniteFloat]
    u0: list[FiniteFloat]
    tendon_order: list[Name] = Field(min_length=1)
    force_limits_n: list[FiniteFloat] = Field(min_length=1)


class LQRSynthesisResult(Contract):
    controller_type: Literal['continuous_time_lqr'] = 'continuous_time_lqr'
    operating_point: EvidenceRef
    gain: EvidenceRef
    gain_shape: tuple[int, int]
    closed_loop_stable: bool
    max_real_closed_loop_eigenvalue: FiniteFloat
    controllability_rank: int = Field(ge=0)
    stabilizability_issue: bool
    tendon_order: list[Name] = Field(min_length=1)
    force_bounds_source: Literal['frozen_robot.family.design'] = 'frozen_robot.family.design'
    command_space: Literal['model_tendon_tension'] = 'model_tendon_tension'
    backend_executable: Literal[False] = False


class GVSState(Contract):
    q: list[FiniteFloat]
    qdot: list[FiniteFloat]


class GVSInput(Contract):
    tendon_tensions_n: dict[Name, NonNegativeFinite] = Field(
        description=(
            'Actual total nonnegative tendon tensions in N; values are not '
            'inferred from actuators and design pretension is not added.'
        )
    )


class GVSDynamicsRequest(Contract):
    state: GVSState
    input: GVSInput
    samples_per_segment: int = Field(default=21, ge=2, le=201)


class GVSDynamicsRequestV2(Contract):
    state: GVSState
    input: GVSInput
    detail: Literal['summary', 'forces', 'full'] = 'summary'
    include_backbone: bool = False
    samples_per_segment: int = Field(default=21, ge=2, le=201)


class GVSPose(Contract):
    position_m: Vec3
    rotation_matrix: Matrix3


class GVSSegmentKinematics(Contract):
    base: GVSPose
    tip: GVSPose
    backbone_points_m: list[Vec3] = Field(min_length=2)


class GVSDynamicsResult(Contract):
    model_id: Literal['gvs_variable_strain_bending_v1'] = 'gvs_variable_strain_bending_v1'
    frame: Literal['robot_base'] = 'robot_base'
    coordinate_order: list[str] = Field(min_length=1)
    q: list[FiniteFloat]
    qdot: list[FiniteFloat]
    qdd: list[FiniteFloat]
    mass_matrix: list[list[FiniteFloat]]
    velocity_bias: list[FiniteFloat]
    elastic_force: list[FiniteFloat]
    damping_force: list[FiniteFloat]
    gravity_force: list[FiniteFloat]
    tendon_generalized_force: list[FiniteFloat]
    tendon_order: list[Name]
    tendon_lengths_m: list[FiniteFloat]
    tendon_length_jacobian: list[list[FiniteFloat]]
    segments: dict[Name, GVSSegmentKinematics]
    component_poses: dict[Name, GVSPose]
    tip: GVSPose
    dynamics_equation: Literal[
        'M*qdd+c+elastic+damping=tendon+gravity'
    ] = 'M*qdd+c+elastic+damping=tendon+gravity'
    limitations: tuple[str, ...] = (
        'branches',
        'closed_chains',
        'contact',
        'self_collision',
        'material_torsion',
        'shear',
        'axial_extension',
        'rope_elasticity',
        'tendon_friction',
        'motor_dynamics',
        'external_applied_forces',
    )


class GVSDynamicsResultV2(Contract):
    model_id: Literal['gvs_variable_strain_bending_v1'] = 'gvs_variable_strain_bending_v1'
    frame: Literal['robot_base'] = 'robot_base'
    detail: Literal['summary', 'forces', 'full']
    coordinate_order: list[str] = Field(min_length=1)
    q: list[FiniteFloat]
    qdot: list[FiniteFloat]
    qdd: list[FiniteFloat]
    tip: GVSPose
    segment_end_poses: dict[Name, GVSPose]
    velocity_bias: list[FiniteFloat] | None = None
    elastic_force: list[FiniteFloat] | None = None
    damping_force: list[FiniteFloat] | None = None
    gravity_force: list[FiniteFloat] | None = None
    tendon_generalized_force: list[FiniteFloat] | None = None
    mass_matrix: list[list[FiniteFloat]] | None = None
    tendon_order: list[Name] | None = None
    tendon_lengths_m: list[FiniteFloat] | None = None
    tendon_length_jacobian: list[list[FiniteFloat]] | None = None
    backbone_points_m: dict[Name, list[Vec3]] | None = None
    dynamics_equation: Literal[
        'M*qdd+c+elastic+damping=tendon+gravity'
    ] = 'M*qdd+c+elastic+damping=tendon+gravity'


class GVSEquilibriumRequest(Contract):
    tendon_tensions_n: dict[Name, NonNegativeFinite]
    initial_q: list[FiniteFloat]
    tolerance: FiniteFloat = Field(
        default=1e-10, gt=0,
        description='Maximum infinity norm of the static generalized-force residual.',
    )
    max_iterations: int = Field(default=50, ge=1, le=500)


class GVSEquilibriumResult(Contract):
    model_id: Literal['gvs_variable_strain_bending_v1'] = 'gvs_variable_strain_bending_v1'
    coordinate_order: list[str] = Field(min_length=1)
    tendon_order: list[Name] = Field(min_length=1)
    q_equilibrium: list[FiniteFloat]
    residual_norm: NonNegativeFinite
    converged: bool
    iterations: int = Field(ge=0)
    solver: Literal['casadi_ad_damped_newton'] = 'casadi_ad_damped_newton'


class GVSDescribeRequest(Contract):
    pass


class GVSCoordinateDescription(Contract):
    name: str
    segment: Name
    mode: Literal['constant', 'linear']
    axis: Literal['y', 'z']
    units: Literal['rad/m'] = 'rad/m'


class GVSTendonInputDescription(Contract):
    tendon: Name
    units: Literal['N'] = 'N'
    constraint: Literal['nonnegative'] = 'nonnegative'
    force_limit_n: float = Field(gt=0)
    design_pretension_n: float = Field(ge=0)


class GVSDescription(Contract):
    model_id: Literal['gvs_variable_strain_bending_v1'] = 'gvs_variable_strain_bending_v1'
    frame: Literal['robot_base'] = 'robot_base'
    basis: tuple[Literal['phi0(s)=1'], Literal['phi1(s)=2*s/L-1']] = (
        'phi0(s)=1',
        'phi1(s)=2*s/L-1',
    )
    curvature_semantics: Literal['actual_total_curvature'] = 'actual_total_curvature'
    natural_curvature_role: Literal['zero_elastic_energy_reference'] = 'zero_elastic_energy_reference'
    coordinates: list[GVSCoordinateDescription] = Field(min_length=1)
    tendon_inputs: list[GVSTendonInputDescription] = Field(min_length=1)
    limitations: tuple[str, ...] = (
        'branches',
        'closed_chains',
        'contact',
        'self_collision',
        'material_torsion',
        'shear',
        'axial_extension',
        'rope_elasticity',
        'tendon_friction',
        'motor_dynamics',
        'external_applied_forces',
    )
