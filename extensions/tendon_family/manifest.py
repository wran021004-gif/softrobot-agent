"""Explicit active research registry, with no retired workflow registrations."""
from tools.platform_registry import Extension
from dataclasses import replace
from schemas.common import Contract
class Empty(Contract):
    pass
import extensions.experiment_dynamics.contracts as m0
import extensions.optimization.contracts as m1
import extensions.reference.contracts as m2
import extensions.tendon_family.contracts as m3
import extensions.tendon_family.gvs_profile as m4
import extensions.tendon_family.generated_serial as m5
import schemas.platform as m6
import schemas.platform_operations as m7
import schemas.platform_math as m8
PLATFORM_SOURCES = (
    'extensions/tendon_family/manifest.py',
    'schemas/common.py',
    'schemas/platform.py',
    'schemas/platform_math.py',
    'schemas/platform_operations.py',
    'tools/file_lock.py',
    'tools/paths.py',
    'tools/platform_host.py',
    'tools/platform_registry.py',
    'tools/platform_store.py',
    'tools/platform_tasks.py',
    'tools/platform_validation.py',
    'tools/state_io.py',
)

PHYSICAL_SOURCES = (
    'extensions/experiment_dynamics/contracts.py',
    'extensions/tendon_family/backends.py',
    'extensions/tendon_family/candidate.py',
    'extensions/tendon_family/compiler.py',
    'extensions/tendon_family/contracts.py',
    'extensions/tendon_family/control.py',
    'extensions/tendon_family/execution.py',
    'extensions/tendon_family/generated_serial.py',
    'extensions/tendon_family/geometry.py',
    'extensions/tendon_family/gvs_structure.py',
    'extensions/tendon_family/mjcf.py',
    'extensions/tendon_family/model_applicability.py',
    'extensions/tendon_family/pcc.py',
    'extensions/tendon_family/scene.py',
    'extensions/tendon_family/sections.py',
    'extensions/tendon_family/signals.py',
    'schemas/design_spec.py',
    'schemas/environment_spec.py',
    'schemas/robot_ir.py',
)

NMPC_SOURCES = (
    'extensions/math_analysis/kernels.py',
    'extensions/math_analysis/trajectory.py',
    'extensions/math_analysis/task_capability.py',
    'tools/research/capability.py',
    'extensions/math_analysis/tools.py',
    'extensions/optimization/contracts.py',
    'extensions/optimization/ipopt.py',
    'extensions/tendon_family/control_evidence.py',
    'extensions/tendon_family/delivery_facts.py',
    'extensions/tendon_family/diagnostic_evidence.py',
    'extensions/tendon_family/gvs.py',
    'extensions/tendon_family/gvs_basis.py',
    'extensions/tendon_family/gvs_casadi.py',
    'extensions/tendon_family/gvs_codesign.py',
    'extensions/tendon_family/gvs_nmpc.py',
    'extensions/tendon_family/gvs_profile.py',
    'extensions/tendon_family/gvs_projection.py',
    'extensions/tendon_family/gvs_reporting.py',
    'extensions/tendon_family/gvs_trajectory.py',
    'extensions/tendon_family/math_analysis.py',
    'schemas/platform_analysis.py',
    'tools/execution_completion.py',
    'tools/research_tasks.py',
)

TOOL_SOURCES = (
    'schemas/platform_diagnostics.py',
    'tools/platform_tools.py',
)

RESEARCH_SOURCES = (
    'tools/research/__init__.py',
    'tools/research/__main__.py',
    'tools/research/agent.py',
    'tools/research/analysis.py',
    'tools/research/budget.py',
    'tools/research/config.py',
    'tools/research/contracts.py',
    'tools/research/core.py',
    'tools/research/design.py',
    'tools/research/diagnostic.py',
    'tools/research/execution.py',
    'tools/research/execution_worker.py',
    'tools/research/experience.py',
    'tools/research/feedback.py',
    'tools/research/mechanics.py',
    'tools/research/mechanics_worker.py',
    'tools/research/numerics.py',
    'tools/research/rl.py',
    'tools/research/search.py',
    'tools/research/state.py',
    'tools/rl/__init__.py',
    'tools/rl/checks.py',
    'tools/rl/continuation.py',
    'tools/rl/env.py',
    'tools/rl/run.py',
    'tools/rl/train.py',
    'tools/service_execution.py',
)
CONTRACTS=[('experiment.assembly','1.0.0',m0.Assembly),
('optimization.ipopt_parameters','1.0.0',m1.IpoptParameters),
('reference.reach_goal','1.0.0',m2.ReachGoal),
('reference.reach_evaluation','1.0.0',m2.ReachEvaluation),
('reference.tracking_goal','1.0.0',m2.TrackingGoal),
('reference.tracking_evaluation','1.0.0',m2.TrackingEvaluation),
('family.design','1.0.0',m3.Design),
('family.initial','1.0.0',m3.Initial),
('family.dynamics_model','1.0.0',m3.DynamicsModel),
('family.mujoco_parameters','1.0.0',m3.MujocoParameters),
('family.discretization','1.0.0',m3.Discretization),
('family.gvs_model','1.0.0',m3.GVSModelParameters),
('family.gvs_reach_control','1.0.0',m4.ReachControl),
('family.generator_space','1.0.0',m5.GeneratorSpace),
('family.topology_space','1.0.0',m5.TopologyGeneratorSpace),
('platform.empty','1.0.0',Empty)]
EXTENSIONS=[Extension(extension_id='backend.family_mujoco',kind='backend',version='1.1.0',input_schema=m3.MujocoParameters,output_schema=m6.BackendResult,binding='extensions.tendon_family.backends:MujocoBackend',description='Explicit model compatibility and backend-specific numerical settings',dependencies=('numpy', 'scipy', 'mujoco'),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'simulation', 'role': 'adapter', 'model': 'mujoco_serial_bending_v1', 'models': {'model.serial_bending_cells': {'implementation_model_id': 'mujoco_serial_bending_v1', 'implementation': 'MuJoCo articulated rigid-body dynamics', 'contact_semantics': 'MuJoCo convex native contact'}}, 'conversion': 'shared serial family physics', 'families': ['task.reach'], 'robots': ['tendon_robot_family', 'tendon_driven_continuum'], 'inactive_parameters': [], 'robot_contracts': ['family.design'], 'channels': ['actuator_commands'], 'environments': ['experiment.assembly'], 'controllers': ['controller.gvs_nmpc'], 'signals': ['tip_position', 'joint_position', 'joint_velocity', 'tendon_length', 'tendon_length_change', 'tendon_length_rate', 'tendon_tension', 'desired_tendon_tension', 'tendon_target_length', 'actuator_command', 'actuator_torque', 'external_torque'], 'signal_specs_resolver': 'extensions.tendon_family.signals:observation_specs', 'signal_phases': ['post_step', 'pre_step_solver'], 'structures': ['serial flexible segments', 'fixed rigid connectors', 'guides', 'payloads'], 'sections': ['circle', 'tube', 'ellipse', 'rectangle', 'simple polygon with holes'], 'routing': 'ordered body/physical-segment stations, straight frictionless spans, intermediate anchors', 'transmission': 'independent/shared ideal displacement or drum rotation; winding sign; travel/speed and per-tendon force limits', 'tendon_tension_execution': {'controller_gvs_lqr': 'direct_bounded_tendon_force', 'controller_family_development': ['ideal_tension', 'actuator_realistic']}, 'descriptive_only': ['discrete flexure', 'rigid tendon joint', 'branch', 'closed chain', 'cable parallel'], 'omissions': ['material torsion', 'shear', 'axial stretch', 'rope elasticity', 'friction', 'self collision', 'motor dynamics'], 'operations': ['compile', 'initialize', 'run', 'export', 'close'], 'timeout': 'internal solve deadline; engine startup/shutdown not hard bounded', 'numerical_contract': 'family.mujoco_parameters'},sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES),
Extension(extension_id='controller.gvs_nmpc',kind='controller',version='11.0.0',input_schema=m4.ReachControl,output_schema=m6.Payload,binding='extensions.tendon_family.gvs_nmpc:DeadlineReachNMPCController',description='Source-based two-segment six-tension NMPC with candidate pretension and current-state warm regeneration',dependencies=('numpy', 'scipy', 'casadi'),extension_dependencies=(('model.gvs', '1.0.0'), ('solver.ipopt', '1.0.0')),resources=(),cache=False,side_effects='none',capabilities={'category': 'control', 'role': 'adapter', 'channel': 'actuator_commands', 'backend_executable': True, 'command_space': 'tendon_tensions', 'sampling': 'interval_start_pre_step; held for control period', 'reset': False, 'restore': False, 'profile_id': 'gvs_candidate_reach_v1', 'predictor': 'model.gvs', 'execution_model': 'model.serial_bending_cells', 'prepare_execution': 'extensions.tendon_family.gvs_profile:prepare_execution', 'route_applicability': 'extensions.tendon_family.gvs_profile:checked_reach', 'scope_assessment': 'extensions.tendon_family.gvs_profile:reach_assessment', 'independent_tendon_inputs': True},sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES),
Extension(extension_id='model.serial_bending_cells',kind='dynamics_model',version='1.0.0',input_schema=m3.DynamicsModel,output_schema=m6.Payload,binding='extensions.tendon_family.execution:model_definition',description='Serial rigid-body model with two principal bending axes per cell',dependencies=(),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'mathematical_model', 'role': 'definition', 'coordinates': 'two principal bending angles per cell', 'mathematical_model': {'state_definition': [{'name': 'joint_position', 'dimension': 'n_dof', 'units': 'rad', 'frame': 'joint_local'}, {'name': 'joint_velocity', 'dimension': 'n_dof', 'units': 'rad/s', 'frame': 'joint_local'}], 'input_definition': [{'name': 'actuator_command', 'dimension': 'n_actuator', 'units': 'm_or_rad_by_actuator', 'frame': 'actuator'}], 'output_definition': [{'name': 'tip_position', 'dimension': 3, 'units': 'm', 'frame': 'world'}, {'name': 'tendon_length', 'dimension': 'n_tendon', 'units': 'm', 'frame': 'path'}, {'name': 'tendon_tension', 'dimension': 'n_tendon', 'units': 'N', 'frame': 'path'}], 'required_robot_data': ['family.design.components', 'family.design.tendons', 'family.design.actuators', 'family.design.tip'], 'discretization_contract': 'family.discretization', 'capabilities': {'kinematics': True, 'statics': False, 'dynamics': True, 'linearization': False, 'gradients': False}, 'representations': [], 'intended_uses': ['reachability', 'shape_prediction', 'reduced_dynamics', 'control_trend', 'high_fidelity_validation'], 'assumptions': ['supported serial bending-cell topology', 'two principal bending hinges per cell', 'straight frictionless tendon paths'], 'unsupported_physics': ['material_torsion', 'shear', 'axial_extension', 'tendon_friction', 'rope_elasticity', 'motor_dynamics', 'self_collision']}, 'equations': 'serial rigid-body dynamics with hinge elasticity/damping and straight frictionless tendon length servos', 'physical_input': 'family.design', 'derived_representation': 'family.discretization + resolved_physics'},sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES),
Extension(extension_id='candidate.family',kind='candidate_builder',version='3.0.0',input_schema=m5.GeneratorSpace,output_schema=m6.SessionInput,binding='extensions.tendon_family.generated_serial:apply',description='Compile explicit frozen source with segment lengths, physical section dimensions and continuous modulus',dependencies=(),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'robot_design', 'role': 'adapter', 'editable': [], 'authorize_changes': 'extensions.tendon_family.generated_serial:authorize', 'parameter_declarations': 'extensions.tendon_family.generated_serial:declarations', 'parameter_capability_version': '1.0.0', 'parameter_support': {'controller': ['controller.gvs_nmpc@11.0.0'], 'backend': ['backend.family_mujoco@1.1.0'], 'model': ['model.serial_bending_cells@1.0.0'], 'task_families': ['task.reach']}, 'search': 'Shared bounded physical/control pool; caller chooses any subset.', 'candidate_initializer': 'extensions.tendon_family.generated_serial:validate_initializer'},sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES),
Extension(extension_id='initialize.family',kind='initializer',version='1.0.0',input_schema=m3.Initial,output_schema=m6.Payload,binding='extensions.tendon_family.scene:initialize',description='Named initial state; unspecified candidate degrees of freedom start at zero',dependencies=(),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'scene_assembly', 'role': 'adapter'},sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES),
Extension(extension_id='evaluate.reach',kind='evaluator',version='1.0.0',input_schema=m2.ReachEvaluation,output_schema=m6.EvaluationResult,binding='extensions.reference.implementation:evaluate_reach',description='Tip distance evaluation with the threshold from the task',dependencies=(),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'evaluation_comparison', 'role': 'adapter'},sources=PLATFORM_SOURCES + ('extensions/reference/contracts.py', 'extensions/reference/implementation.py')),
Extension(extension_id='task.reach',kind='task',version='1.0.0',input_schema=m6.TaskDefinition,output_schema=m2.Empty,binding='extensions.reference.implementation:reach_task',description='Development task using existing reach semantics',dependencies=(),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'evaluation_comparison', 'role': 'adapter'},sources=PLATFORM_SOURCES + ('extensions/reference/contracts.py', 'extensions/reference/implementation.py')),
Extension(extension_id='task.tracking',kind='task',version='1.0.0',input_schema=m6.TaskDefinition,output_schema=m2.Empty,binding='extensions.reference.implementation:tracking_task',description='World tip tracking: optional timed nodes or free ordered geometric progress',sources=PLATFORM_SOURCES + ('extensions/reference/contracts.py','extensions/reference/implementation.py')),
Extension(extension_id='evaluate.tracking',kind='evaluator',version='1.0.0',input_schema=m2.TrackingEvaluation,output_schema=m6.EvaluationResult,binding='extensions.reference.implementation:evaluate_tracking',description='Independent timed or geometric saved-trajectory evaluation with diagnostic RMS',dependencies=('numpy',),sources=PLATFORM_SOURCES + ('extensions/reference/contracts.py','extensions/reference/implementation.py')),
Extension(extension_id='evidence.read',kind='tool',version='1.0.0',input_schema=m7.ReadEvidence,output_schema=m7.EvidencePage,binding='tools.platform_tools:read_evidence',description='Read immutable saved evidence with JSON Pointer and offset paging. An oversized subtree returns a labeled pointer overview, not original content. Follow its pointers using the same source reference and next_offset at the same pointer. No solve or evaluation is performed.',dependencies=(),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'platform_services', 'role': 'public_tool'},sources=PLATFORM_SOURCES + TOOL_SOURCES),
Extension(extension_id='simulation.run',kind='tool',version='1.0.0',input_schema=m7.Simulate,output_schema=m6.BackendResult,binding='tools.platform_tools:simulate',description='Execute the frozen task and selected candidate, charging one backend attempt. Saves results and trajectory; use evaluation.run to score the result.',dependencies=(),extension_dependencies=(),resources=(),cache=True,side_effects='current session/project only',capabilities={'preflight': 'tools.platform_tools:simulation_preflight', 'cache_reuse': 'tools.platform_tools:simulation_reuse', 'category': 'simulation', 'role': 'public_tool'},sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES),
Extension(extension_id='evaluation.run',kind='tool',version='1.0.0',input_schema=m7.Evaluate,output_schema=m6.EvaluationResult,binding='tools.platform_tools:evaluate',description='Evaluate an existing saved simulation result with the frozen task evaluator. No solve; returns validity, metrics and task_success separately.',dependencies=(),extension_dependencies=(),resources=(),cache=False,side_effects='current session/project only',capabilities={'category': 'evaluation_comparison', 'role': 'public_tool'},sources=PLATFORM_SOURCES + TOOL_SOURCES),
Extension(extension_id='control.profile_report',kind='tool',version='1.0.0',input_schema=m4.ProfileReportRequest,output_schema=m4.ProfileOutput,binding='extensions.tendon_family.gvs_reporting:report',description='Summarize sealed public simulation/evaluation evidence, sampled settling, raw solve status, initialization selection, failure response and delivery cost; validate a predeclared strategy; zero solves.',dependencies=('numpy', 'mujoco'),extension_dependencies=(),resources=(),cache=False,side_effects='artifact_store',capabilities={'category': 'control', 'role': 'public_tool', 'backend_solves': 0},sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES),
Extension(extension_id='model.gvs',kind='dynamics_model',version='1.0.0',input_schema=m3.GVSModelParameters,output_schema=m6.Payload,binding='extensions.tendon_family.gvs:GVSModel',description='RobotIR-driven variable-strain continuum bending kinematics and dynamics',dependencies=('numpy', 'casadi'),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'mathematical_model', 'role': 'adapter', 'mathematical_model': {'state_definition': [{'name': 'strain_coefficients', 'dimension': 'n_gvs_coordinates', 'units': 'rad/m', 'frame': 'segment_local'}, {'name': 'strain_coefficient_rates', 'dimension': 'n_gvs_coordinates', 'units': 'rad/(m*s)', 'frame': 'segment_local'}], 'input_definition': [{'name': 'tendon_tension', 'dimension': 'n_tendons', 'units': 'N', 'frame': 'tendon_path'}], 'output_definition': [{'name': 'strain_coefficient_acceleration', 'dimension': 'n_gvs_coordinates', 'units': 'rad/(m*s^2)', 'frame': 'segment_local'}, {'name': 'tip_position', 'dimension': 3, 'units': 'm', 'frame': 'robot_base'}], 'required_robot_data': ['family.design.components.connection', 'family.design.components.length_m', 'family.design.components.sections', 'family.design.components.physics', 'family.design.components.natural_curvature_rad_m', 'family.design.components.mass_kg', 'family.design.components.com_local_m', 'family.design.components.inertia_com_local_kg_m2', 'family.design.tendons', 'family.design.tip'], 'discretization_contract': None, 'capabilities': {'kinematics': True, 'statics': True, 'dynamics': True, 'linearization': False, 'gradients': True}, 'representations': ['dynamic_system'], 'intended_uses': ['reachability', 'shape_prediction', 'static_equilibrium', 'reduced_dynamics', 'control_trend', 'linearization', 'local_model_control'], 'assumptions': ['supported serial tendon-driven continuum topology', 'selected strain basis spans deformation relevant to the use', 'inextensible centerline', 'no shear', 'no torsion', 'straight frictionless tendon spans'], 'unsupported_physics': ['contact_response', 'self_collision', 'tendon_friction', 'rope_elasticity', 'axial_extension', 'material_torsion', 'shear', 'motor_dynamics', 'external_applied_forces']}, 'physical_input': 'family.design', 'environment_input': 'experiment.assembly gravity and mount', 'generalized_coordinates': 'resolved from model basis strategy and family.design structural locations', 'strain_basis': ['first_order', 'structural_linear'], 'curvature_semantics': 'actual total geometric curvature', 'constitutive_reference': 'Segment.natural_curvature_rad_m', 'actuation_input': 'actual total nonnegative tendon tensions in N, bounded by family.design force limits; pretension is not added', 'assumptions': ['serial variable-strain continuum bending', 'inextensible centerline', 'no shear or torsion', 'straight frictionless tendon spans'], 'omissions': ['branches', 'closed chains', 'contact', 'self collision', 'material torsion', 'shear', 'axial extension', 'rope elasticity', 'tendon friction', 'motor electrical dynamics', 'external applied forces']},sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES),
Extension(extension_id='solver.ipopt',kind='solver',version='1.0.0',input_schema=m1.IpoptParameters,output_schema=m8.OptimizationResult,binding='extensions.optimization.ipopt:IpoptSolver',description='Solve explicit differentiable OptimizationProblem expressions with CasADi IPOPT.',dependencies=('numpy', 'casadi'),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'optimization', 'role': 'adapter', 'expression': 'casadi_nlp_function_v1', 'backend_solves': 0, 'search': False},sources=PLATFORM_SOURCES + ('extensions/optimization/contracts.py', 'extensions/optimization/ipopt.py')),
Extension('deepseek','model_adapter','8.0.0',Empty,m6.Payload,'tools.research.agent:build_harness','Production Strands native-tool integration',sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES + RESEARCH_SOURCES),
Extension('strategy.tool','strategy','1.0.0',Empty,m6.Payload,'tools.research.agent:build_harness','Production Strands native-tool integration',sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES + RESEARCH_SOURCES)]

EXTENSIONS.append(Extension(extension_id='optimization_assembler.gvs_trajectory',kind='optimization_assembler',version='1.0.0',input_schema=m3.GVSTrajectoryParameters,output_schema=m8.OptimizationProblem,binding='extensions.tendon_family.gvs_trajectory:GVSTrajectoryAssembler',description='Fixed-design free-reach implicit dynamic trajectory transcription',dependencies=('numpy', 'casadi', 'scipy'),extension_dependencies=(),resources=(),cache=False,side_effects='none',capabilities={'category': 'optimization', 'role': 'adapter', 'model': 'model.gvs', 'model_version': '1.0.0', 'authorization': 'extensions.tendon_family.gvs_trajectory:trajectory_authorization', 'supported_objectives': ['dynamic_tip_tracking'], 'supported_constraints': ['initial_state', 'implicit_dynamics', 'tendon_force_bounds'], 'target_source': 'frozen Task goal and evaluator tolerance'},sources=PLATFORM_SOURCES + PHYSICAL_SOURCES + NMPC_SOURCES + TOOL_SOURCES))
CONTRACTS.append(('family.gvs_trajectory_parameters','1.0.0',m3.GVSTrajectoryParameters))
CONTRACTS.append(('family.backend_data','1.0.0',m3.Data))

_source_builder=next(e for e in EXTENSIONS if (e.extension_id,e.version)==('candidate.family','3.0.0'))
EXTENSIONS.append(replace(_source_builder,version='4.0.0',input_schema=m5.TopologyGeneratorSpace,
    description='Explicitly authorized source-relative tendon topology with stable independent input order',
    capabilities={**_source_builder.capabilities,
        'parameter_declarations':'extensions.tendon_family.generated_serial:topology_declarations'}))

from .family_space import FamilyBuild
CONTRACTS.append(('family.serial_space_build','1.0.0',FamilyBuild))
EXTENSIONS.append(replace(_source_builder,version='5.0.0',input_schema=FamilyBuild,
    description='Independent two-segment construction from a frozen declarative serial family space',
    capabilities={**_source_builder.capabilities,
        'parameter_declarations':'extensions.tendon_family.generated_serial:family_declarations'},
    sources=_source_builder.sources+('extensions/tendon_family/family_space.py',)))

from .family_space import FamilyBuildV2
CONTRACTS.append(('family.serial_space_build_v2','1.0.0',FamilyBuildV2))
EXTENSIONS.append(replace(_source_builder,version='6.0.0',input_schema=FamilyBuildV2,
    description='Frozen serial family with one to nine independently parameterized flexible segments',
    capabilities={**_source_builder.capabilities,
        'parameter_declarations':'extensions.tendon_family.generated_serial:serial_declarations'},
    sources=_source_builder.sources+('extensions/tendon_family/family_space.py',)))

# The predictor is separate from policy.dynamics_model (MuJoCo's cell model).
from .sorosim_control import SorosimReachControl
SOROSIM_SOURCES = PLATFORM_SOURCES + PHYSICAL_SOURCES + (
    'extensions/tendon_family/sorosim_analysis.py',
    'extensions/tendon_family/sorosim_codesign.py',
    'tools/research/mechanics.py',
    'tools/research/mechanics_worker.py',
    'extensions/tendon_family/math_analysis.py',
    'tools/research/analysis.py',
    'tools/research/execution_worker.py',
    'matlab/sorosim_control/sr_analysis.m',
    'matlab/sorosim_control/sr_codesign.m',
    'extensions/tendon_family/sorosim_spec.py',
    'extensions/tendon_family/sorosim_session.py',
    'extensions/tendon_family/sorosim_control.py',
    'extensions/tendon_family/control_evidence.py',
    'extensions/tendon_family/gvs_reporting.py',
    'schemas/platform_analysis.py',
    'tools/research/config.py',
    'tools/research/task_constraints.py',
    'tools/research_tasks.py',
    'extensions/tendon_family/gvs_basis.py',
    'extensions/tendon_family/gvs_projection.py',
    'extensions/tendon_family/gvs_profile.py',
    'extensions/tendon_family/gvs.py',
    'matlab/sorosim_control/sr_gateway.m',
    'matlab/sorosim_control/sr_trajectory_outputs.m',
    'matlab/sorosim_control/sr_model.m',
    'matlab/sorosim_control/sr_routing.m',
    'matlab/sorosim_control/sr_checks.m',
    'matlab/sorosim_control/sr_diagnose.m',
    'matlab/sorosim_control/sr_optimality.m',
    'matlab/sorosim_control/sr_dynamics.m',
    'matlab/sorosim_control/sr_derivatives.m',
    'matlab/sorosim_control/sr_nmpc.m',
    'matlab/sorosim_control/sr_nmpc_callbacks.m',
    'configs/research/control.json',
    'configs/research/control_sorosim.json',
    'configs/research/sorosim_dependency.json',
)
CONTRACTS += [('family.sorosim_model','1.0.0',m3.SorosimModelParameters),
              ('family.sorosim_reach_control','1.0.0',SorosimReachControl)]
_gvs_model = next(e for e in EXTENSIONS if e.extension_id=='model.gvs')
_sr_math = {**_gvs_model.capabilities['mathematical_model'],
    'capabilities':dict(kinematics=True,statics=True,dynamics=True,linearization=True,gradients=True),
    'representations':['linearized_model'], 'intended_uses':['reachability','shape_prediction','static_equilibrium','linearization','reduced_dynamics','local_model_control']}
EXTENSIONS.append(Extension(extension_id='model.sorosim_gvs',kind='dynamics_model',version='1.0.0',
    input_schema=m3.SorosimModelParameters,output_schema=m6.Payload,
    binding='extensions.tendon_family.sorosim_spec:SorosimModel',
    description='Pinned SoRoSim mathematical predictor; capabilities gated by numerical evidence',
    dependencies=('numpy','scipy','matlab.engine'), sources=SOROSIM_SOURCES,
    capabilities=dict(category='mathematical_model',role='adapter',mathematical_model=_sr_math,
        upstream='GVSRobotics/SoRoSim@24d573a3e864ffda87c42ee462a6ed620133cc7b',
        operations=['routing','dynamics','derivatives','analysis','codesign'], unsupported_operations=['topology derivatives'],
        validation='S1/S2 local mechanics; S4 analysis requires per-result derivative and residual checks')))
_sr_controller = next(e for e in EXTENSIONS if e.extension_id=='controller.gvs_nmpc' and e.version=='11.0.0')
EXTENSIONS.append(replace(_sr_controller,extension_id='controller.sorosim_matlab_nmpc',version='1.0.0',
    input_schema=SorosimReachControl,binding='extensions.tendon_family.sorosim_control:SorosimNMPCController',
    description='SoRoSim predictor with MATLAB fmincon SQP and independent MuJoCo execution',
    dependencies=('numpy','scipy','matlab.engine'),extension_dependencies=(('model.sorosim_gvs','1.0.0'),),
    sources=SOROSIM_SOURCES,capabilities={**_sr_controller.capabilities,
        'predictor':'model.sorosim_gvs','profile_id':'sorosim_candidate_reach_v1',
        'resolve_control':'extensions.tendon_family.sorosim_control:resolve_control',
        'route_applicability':'extensions.tendon_family.sorosim_control:checked_control'}))
for _i,_entry in enumerate(EXTENSIONS):
    if _entry.extension_id == 'backend.family_mujoco':
        EXTENSIONS[_i] = replace(_entry,capabilities={**_entry.capabilities,
            'controllers':[*_entry.capabilities['controllers'],'controller.sorosim_matlab_nmpc']})
    if _entry.kind == 'candidate_builder':
        _support = _entry.capabilities.get('parameter_support')
        if _support:
            EXTENSIONS[_i] = replace(_entry,capabilities={**_entry.capabilities,'parameter_support':{
                **_support,'controller':[*_support['controller'],'controller.sorosim_matlab_nmpc@1.0.0']}})
