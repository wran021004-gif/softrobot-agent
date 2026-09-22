"""Capability catalog: descriptive families and executable serial scope are distinct."""
from schemas.platform import BackendResult, Payload, SessionInput
from schemas.platform_math import LinearizedModel, OptimizationProblem
from tools.platform_registry import Extension
from . import contracts as c
from . import legacy_scientific
from . import optimization as opt
from . import route

CONTRACTS=[('family.'+name,'1.0.0',schema) for name,schema in [
    ('route_policy',route.RoutePolicy),
    ('optimization_request',opt.OptimizationRequest),('search',opt.SearchParameters),('search_state',opt.SearchState),
    ('design',c.Design),('initial',c.Initial),('control',c.Control),('parameters',c.Parameters),('backend_data',c.Data),
    ('dynamics_model',c.DynamicsModel),('matlab_parameters',c.MatlabParameters),('mujoco_parameters',c.MujocoParameters),
    ('space',c.Space),('discretization',c.Discretization),('experiment_spec',c.ExperimentSpec),
    ('build_request',c.BuildRequest),('build_result',c.BuildResult),
    ('pcc_model',c.PCCModelParameters),('pcc_configuration',c.PCCConfiguration),
    ('pcc_forward_request',c.PCCForwardRequest),('pcc_kinematics_result',c.PCCKinematicsResult),
    ('pcc_describe_request',c.PCCDescribeRequest),('pcc_description',c.PCCDescription),
    ('gvs_model',c.GVSModelParameters),('gvs_dynamics_request',c.GVSDynamicsRequest),
    ('gvs_dynamics_result',c.GVSDynamicsResult),('gvs_describe_request',c.GVSDescribeRequest),
    ('gvs_description',c.GVSDescription),
    ('gvs_continuous_dynamics',c.GVSContinuousDynamicsExpression),
    ('gvs_build_system_request',c.GVSBuildSystemRequest),
    ('gvs_linearize_request',c.GVSLinearizeRequest),
    ('casadi_linearizer',c.CasadiLinearizerParameters),
    ('lqr_parameters',c.LQRParameters),('lqr_command',c.LQRCommand),
    ('lqr_describe_request',c.LQRDescribeRequest),('lqr_description',c.LQRDescription),
    ('pcc_reach_assembler_parameters',c.PCCReachAssemblerParameters),
    ('gvs_inverse_assembler_parameters',c.GVSInverseAssemblerParameters),]]
CONTRACTS += [
    ('family.pcc_forward_request', '2.0.0', c.PCCForwardRequestV2),
    ('family.pcc_kinematics_result', '2.0.0', c.PCCKinematicsResultV2),
    ('family.gvs_dynamics_request', '2.0.0', c.GVSDynamicsRequestV2),
    ('family.gvs_dynamics_request', '3.0.0', c.GVSDynamicsRequestV3),
    ('family.gvs_dynamics_result', '2.0.0', c.GVSDynamicsResultV2),
    ('family.gvs_describe_request', '2.0.0', c.GVSDescribeRequestV2),
    ('family.gvs_build_system_request', '2.0.0', c.GVSBuildSystemRequestV2),
    ('family.gvs_build_system_request', '3.0.0', c.GVSBuildSystemRequestV3),
    ('family.gvs_system_artifact_result', '1.0.0', c.GVSSystemArtifactResult),
    ('family.gvs_linearize_request', '2.0.0', c.GVSLinearizeRequestV2),
    ('family.linearized_model_artifact_result', '1.0.0', c.LinearizedModelArtifactResult),
    ('family.gvs_equilibrium_request', '1.0.0', c.GVSEquilibriumRequest),
    ('family.gvs_equilibrium_request', '2.0.0', c.GVSEquilibriumRequestV2),
    ('family.gvs_inverse_assembler_parameters', '2.0.0', c.GVSInverseAssemblerParametersV2),
    ('family.gvs_equilibrium_result', '1.0.0', c.GVSEquilibriumResult),
    ('family.lqr_synthesize_request', '1.0.0', c.LQRSynthesizeRequest),
    ('family.lqr_gain_artifact', '1.0.0', c.LQRGainArtifact),
    ('family.lqr_synthesis_result', '1.0.0', c.LQRSynthesisResult),
    ('family.lqr_synthesis_description', '2.0.0', c.LQRSynthesisDescription),
    ('family.gvs_lqr_control', '1.0.0', c.GVSLQRControl),
]
SOURCES=tuple('extensions/tendon_family/'+n+'.py' for n in ('contracts','compiler','sections','geometry','legacy','scene','control','gvs_structure','gvs_basis','gvs_projection','gvs_lqr','model_applicability','execution','backends','signals','candidate','preparation','mjcf','saved','manifest','optimization','crosscheck','route'))+(
    'tools/optimization_interfaces.py','tools/platform_search.py',
    'tools/platform_tools.py','tools/platform_tasks.py','schemas/platform_operations.py','tools/design_compiler.py',
    'tools/matlab_tools.py','tools/state_io.py','extensions/experiment_dynamics/contracts.py',
    'extensions/experiment_dynamics/physics.py','extensions/robot_domain/contracts.py',
    'schemas/environment_spec.py','schemas/robot_ir.py','schemas/exploration.py','schemas/platform_math.py')
PCC_SOURCES=(*SOURCES,'extensions/tendon_family/pcc.py')
GVS_SOURCES=(*SOURCES,'extensions/tendon_family/gvs.py','extensions/tendon_family/gvs_casadi.py','extensions/tendon_family/pcc.py',
    'extensions/tendon_family/scientific_optimization.py','extensions/tendon_family/legacy_scientific.py')
OPT_SOURCES=(*GVS_SOURCES,'extensions/optimization/contracts.py','extensions/optimization/ipopt.py','tools/platform_optimization.py')
MATLAB=tuple('matlab/'+n+'.m' for n in ('tf_geometry','tf_point','tf_routes','tf_terms','tf_control','tf_run','tf_observe','tf_static','tf_view'))
COMMON=dict(sources=SOURCES,contract_dependencies=tuple((n,v) for n,v,_ in CONTRACTS))
EXTENSIONS=[
    Extension('route.advance','tool','1.0.0',route.RouteAction,route.RouteResult,
        'extensions.tendon_family.route:advance','Advance one evidence-led action. build constructs and validates only: no solve, score or trajectory. run executes a saved build and evaluates its saved result (one charged backend attempt). optimize searches within variables[path]=[lower_bound, upper_bound], executing and evaluating candidates (up to max_trials charged attempts); bounds are not sample values. diagnose analyzes saved results; crosscheck independently executes the same physical/control configuration on an authorized alternative backend (one charged attempt); video renders saved results; finish delivers a valid evaluation, including an unmet task tolerance. Only run, optimize and crosscheck consume solver budget. source_node and changes semantics are specified in the input schema. Cite previous node result evidence after the first action.',**COMMON,
        capabilities=dict(category='orchestration',role='public_tool',delegated_execution=True,
            preflight='extensions.tendon_family.route:preflight')),
    Extension('route.inspect','tool','1.0.0',route.Inspect,route.RouteResult,
        'extensions.tendon_family.route:inspect','Read the compact factual route overview: selected candidate, solve/evaluation existence, result references, authorized combinations and bounds, remaining budget and next-action prerequisites. The same overview is already in model context; inspect again only when needed. No solve.',**COMMON,
        capabilities=dict(category='orchestration',role='public_tool')),
    Extension('search.family_coordinate','search','1.0.0',opt.SearchParameters,Payload,
        'extensions.tendon_family.optimization:CoordinateSearch','Bounded coordinate search; first candidate is the starting configuration; jointly tunes design and control',**COMMON,
        capabilities=dict(category='parameter_search',role='adapter',checkpoint='family.search_state',
            public_entry='extensions.tendon_family.optimization:optimize',request_contract='family.optimization_request',
            numerical_discretization='fixed',trajectory_optimization='unsupported')),
    Extension('initialize.family','initializer','1.0.0',c.Initial,Payload,'extensions.tendon_family.scene:initialize',
        'Named initial state; unspecified candidate degrees of freedom start at zero',**COMMON,capabilities=dict(category='scene_assembly',role='adapter')),
    Extension('controller.family','controller','1.0.0',c.Control,Payload,'extensions.tendon_family.control:Controller',
        'Ideal actuator mapping with deterministic commands, live tip feedback, or a constant model-space tendon-tension reference',**COMMON,capabilities=dict(category='control',role='adapter',
            channel='actuator_commands',observations=['tip_position'],reset=True,restore=False,
            algorithms={'deterministic':'deterministic_actuator_reference_v1','tip_feedback':'tip_resolved_rate_feedback_v1',
                'tension_reference':'constant_tendon_tension_reference_v1'},
            reference_types=['actuator_commands','task_goal','ordered_tendon_tensions_n'],output='named actuator command -> tendon target length',
            tension_reference=dict(order_source='frozen family.design tendons',force_limit_semantics='clip each requested tension to [0, force_limit_n]',
                execution_modes=dict(
                    ideal_tension='Direct bounded tendon force; bypasses transmission, actuator velocity/travel limits and the length servo.',
                    actuator_realistic='Existing minimum-norm transmission, actuator velocity/travel limits and tendon-length servo.')),
            sampling={'control_observation':'interval_start_pre_step','force':'interval_start_pre_step_solver','state':'interval_end_post_step'})),
    Extension('controller.gvs_lqr','controller','1.0.0',c.GVSLQRControl,Payload,'extensions.tendon_family.gvs_lqr:GVSLQRController',
        'Backend-executable GVS state projection plus existing continuous LQR; backend realizes its desired tendon tensions',**COMMON,
        dependencies=('numpy','scipy','casadi'),extension_dependencies=(('controller.lqr','1.0.0'),('model.gvs','1.0.0')),
        capabilities=dict(category='control',role='adapter',channel='actuator_commands',backend_executable=True,
            command_space='desired_tendon_tension',observations=['joint_position','joint_velocity','tendon_length'],
            state_projector='backend_discrete_to_gvs_resolved_v1',model_requirement=dict(input='none'),
            derived_artifacts=['candidate_gvs_equilibrium','candidate_dynamic_system','candidate_linearization','candidate_lqr_gain'],
            backend_execution='backend.family_mujoco deterministically applies clipped desired tendon force directly',
            composition=['model.gvs','linearizer.casadi','controller.lqr','backend_tension_execution'],reset=True,restore=False)),
    Extension('candidate.family','candidate_builder','1.0.0',c.Space,SessionInput,'extensions.tendon_family.candidate:apply',
        'Candidate construction from numerical, integer, option and complete structure template choices',**COMMON,capabilities=dict(category='robot_design',role='adapter',
            editable=[],authorize_changes='extensions.tendon_family.candidate:authorize',
            search='External/LLM structural proposals; existing continuous search algorithms are not mixed-integer optimizers')),
    Extension('design.family_build','tool','1.0.0',c.BuildRequest,c.BuildResult,'extensions.tendon_family.candidate:build_tool',
        'Construct and validate a complete candidate, summary, derived physics and applicability. No dynamics solve, score or trajectory.',**COMMON,capabilities=dict(category='robot_design',role='public_tool')),
]
EXTENSIONS.append(Extension('model.serial_bending_cells','dynamics_model','1.0.0',c.DynamicsModel,Payload,
    'extensions.tendon_family.execution:model_definition','Serial rigid-body model with two principal bending axes per cell',**COMMON,
    capabilities=dict(category='mathematical_model',role='definition',coordinates='two principal bending angles per cell',
        mathematical_model=c.DynamicsModel().mathematical_model.model_dump(mode='json'),
        equations='serial rigid-body dynamics with hinge elasticity/damping and straight frictionless tendon length servos',
        physical_input='family.design',derived_representation='family.discretization + resolved_physics')))
for name,binding,model,deps,resources in [
    ('matlab_spatial','MatlabBackend','matlab_serial_bending_v1',('numpy','matlab.engine'),('matlab_engine',)),
    ('family_mujoco','MujocoBackend','mujoco_serial_bending_v1',('numpy','scipy','mujoco'),())]:
    shared_capabilities=dict(category='mathematical_models' if name=='matlab_spatial' else 'simulation',role='adapter',
            model=model,models={'model.serial_bending_cells':dict(implementation_model_id=model,
                implementation='MATLAB native spatial serial dynamics' if name=='matlab_spatial' else 'MuJoCo articulated rigid-body dynamics',
                contact_semantics='lowest-envelope-vertex penalty contact' if name=='matlab_spatial' else 'MuJoCo convex native contact')},
            conversion='shared serial family physics',families=['task.reach'],robots=['tendon_robot_family','tendon_driven_continuum'],
            inactive_parameters=[] if name=='matlab_spatial' else ['max_step_s','rtol','atol','contact_stiffness_n_m','contact_damping_n_s_m'],
            robot_contracts=['family.design','domain.rod_design'],channels=['actuator_commands'],environments=['experiment.assembly'],
            controllers=['controller.family']+(['controller.gvs_lqr'] if name=='family_mujoco' else []),signals=['tip_position','joint_position','joint_velocity','tendon_length','tendon_length_change','tendon_length_rate','tendon_tension','desired_tendon_tension','tendon_target_length','actuator_command','actuator_torque','external_torque'],
            signal_specs_resolver='extensions.tendon_family.signals:observation_specs',signal_phases=['post_step','pre_step_solver'],
            structures=['serial flexible segments','fixed rigid connectors','guides','payloads'],
            sections=['circle','tube','ellipse','rectangle','simple polygon with holes'],
            routing='ordered body/physical-segment stations, straight frictionless spans, intermediate anchors',
            transmission='independent/shared ideal displacement or drum rotation; winding sign; travel/speed and per-tendon force limits',
            tendon_tension_execution=(dict(controller_gvs_lqr='direct_bounded_tendon_force',
                controller_family_development=['ideal_tension','actuator_realistic']) if name=='family_mujoco'
                else dict(controller_family='actuator_realistic')),
            descriptive_only=['discrete flexure','rigid tendon joint','branch','closed chain','cable parallel'],
            omissions=['material torsion','shear','axial stretch','rope elasticity','friction','self collision','motor dynamics'],
            operations=['compile','initialize','run','export','close'],timeout='internal solve deadline; engine startup/shutdown not hard bounded')
    EXTENSIONS.append(Extension('backend.'+name,'backend','1.0.0',c.Parameters,BackendResult,
        'extensions.tendon_family.backends:'+binding,'Named serial multi-segment biaxial bending and individual tendon routes',**COMMON,
        assets=MATLAB if name=='matlab_spatial' else (),dependencies=deps,resources=resources,
        capabilities=shared_capabilities))
    parameters=c.MatlabParameters if name=='matlab_spatial' else c.MujocoParameters
    contract='family.matlab_parameters' if name=='matlab_spatial' else 'family.mujoco_parameters'
    modern={**shared_capabilities,'inactive_parameters':[],'numerical_contract':contract}
    EXTENSIONS.append(Extension('backend.'+name,'backend','1.1.0',parameters,BackendResult,
        'extensions.tendon_family.backends:'+binding,'Explicit model compatibility and backend-specific numerical settings',sources=SOURCES,
        contract_dependencies=COMMON['contract_dependencies'],assets=MATLAB if name=='matlab_spatial' else (),
        dependencies=deps,resources=resources,capabilities=modern))

EXTENSIONS.append(
    Extension(
        'model.pcc',
        'dynamics_model',
        '1.0.0',
        c.PCCModelParameters,
        Payload,
        'extensions.tendon_family.pcc:PCCModel',
        'Serial multi-segment constant-curvature PCC forward kinematics',
        sources=PCC_SOURCES,
        contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy',),
        capabilities=dict(
            category='mathematical_model',
            role='adapter',
            mathematical_model=(
                c.PCCModelParameters()
                .mathematical_model
                .model_dump(mode='json')
            ),
            physical_input='family.design',
            configuration='per-flexible-segment constant curvature',
            coordinates='curvature_y_rad_m + curvature_z_rad_m per flexible segment',
            curvature_semantics='actual total geometric curvature; natural curvature is not added',
            assumptions=[
                'constant curvature per flexible segment',
                'inextensible centerline',
                'no shear',
                'no torsion',
            ],
        ),
    )
)
EXTENSIONS.append(
    Extension(
        'kinematics.pcc_describe',
        'tool',
        '1.0.0',
        c.PCCDescribeRequest,
        c.PCCDescription,
        'extensions.tendon_family.pcc:pcc_describe_tool',
        (
            'Describe the frozen family.design PCC flexible-segment names and '
            'their actual-total-curvature y/z coordinates. Read-only; no '
            'simulation, mechanics, tendon inference or backend solve.'
        ),
        sources=PCC_SOURCES,
        contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy',),
        extension_dependencies=(('model.pcc', '1.0.0'),),
        cache=True,
        side_effects='none',
        capabilities=dict(
            category='mathematical_models',
            role='public_tool',
            route_visible=True,
            model='model.pcc',
            backend_solves=0,
        ),
    )
)
EXTENSIONS.append(
    Extension(
        'linearizer.casadi',
        'linearizer',
        '1.0.0',
        c.CasadiLinearizerParameters,
        LinearizedModel,
        'extensions.tendon_family.gvs_casadi:CasadiLinearizer',
        'Automatic-differentiation linearizer for registered typed CasADi expressions.',
        sources=GVS_SOURCES,
        contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'casadi'),
        capabilities=dict(
            category='linearization', role='adapter',
            input='DynamicSystem', derivatives='casadi_automatic_differentiation',
        ),
    )
)
EXTENSIONS.append(
    Extension(
        'controller.lqr',
        'controller',
        '1.0.0',
        c.LQRParameters,
        c.LQRCommand,
        'extensions.tendon_family.gvs_casadi:ContinuousLQRController',
        'Continuous-time LQR around an equilibrium LinearizedModel with physical tendon-tension clamping.',
        sources=GVS_SOURCES,
        contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'scipy'),
        capabilities=dict(
            category='control', role='adapter',
            model_requirement=dict(input='linearized_model', capabilities=['linearization']),
            input='state', output='bounded model-space tendon tensions', channel='model_tendon_tension',
            command_space='model_tendon_tension', backend_executable=False,
            equilibrium_required=True, reset=True, restore=True,
        ),
    )
)
EXTENSIONS.append(
    Extension(
        'model.gvs',
        'dynamics_model',
        '1.0.0',
        c.GVSModelParameters,
        Payload,
        'extensions.tendon_family.gvs:GVSModel',
        'RobotIR-driven variable-strain continuum bending kinematics and dynamics',
        sources=GVS_SOURCES,
        contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'casadi'),
        capabilities=dict(
            category='mathematical_model',
            role='adapter',
            mathematical_model=(
                c.GVSModelParameters().mathematical_model.model_dump(mode='json')
            ),
            physical_input='family.design',
            environment_input='experiment.assembly gravity and mount',
            generalized_coordinates='resolved from model basis strategy and family.design structural locations',
            strain_basis=['first_order', 'structural_linear'],
            curvature_semantics='actual total geometric curvature',
            constitutive_reference='Segment.natural_curvature_rad_m',
            actuation_input=(
                'actual total nonnegative tendon tensions in N, bounded by '
                'family.design force limits; pretension is not added'
            ),
            assumptions=[
                'serial variable-strain continuum bending',
                'inextensible centerline',
                'no shear or torsion',
                'straight frictionless tendon spans',
            ],
            omissions=[
                'branches', 'closed chains', 'contact', 'self collision',
                'material torsion', 'shear', 'axial extension', 'rope elasticity',
                'tendon friction', 'motor electrical dynamics',
                'external applied forces',
            ],
        ),
    )
)
EXTENSIONS.append(
    Extension(
        'dynamics.gvs_describe',
        'tool',
        '1.0.0',
        c.GVSDescribeRequest,
        c.GVSDescription,
        'extensions.tendon_family.gvs:gvs_describe_tool',
        (
            'Describe the robot GVS coordinate order, resolved '
            'strain basis and nonnegative tendon-tension inputs. No solve.'
        ),
        sources=GVS_SOURCES,
        contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy',),
        extension_dependencies=(('model.gvs', '1.0.0'),),
        cache=True,
        side_effects='none',
        capabilities=dict(
            category='mathematical_models', role='public_tool',
            route_visible=True, model='model.gvs', backend_solves=0,
        ),
    )
)
EXTENSIONS.extend(legacy_scientific.registrations(
    c,
    pcc_sources=PCC_SOURCES,
    gvs_sources=GVS_SOURCES,
    contract_dependencies=COMMON['contract_dependencies'],
))

# Compact, evidence-oriented public interfaces. Historical registrations live in
# legacy_scientific.py and remain available to exact-version session bindings.
EXTENSIONS.extend([
    Extension(
        'dynamics.gvs_describe', 'tool', '2.0.0',
        c.GVSDescribeRequestV2, c.GVSDescription,
        'extensions.tendon_family.gvs:gvs_describe_tool_v2',
        'Describe frozen GVS coordinates for an explicit trusted basis strategy; no solve.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy',), extension_dependencies=(('model.gvs', '1.0.0'),),
        cache=True, side_effects='none',
        capabilities=dict(category='mathematical_models', role='public_tool', route_visible=True,
            model='model.gvs', backend_solves=0),
    ),
    Extension(
        'kinematics.pcc_forward', 'tool', '2.0.0',
        c.PCCForwardRequestV2, c.PCCKinematicsResultV2,
        'extensions.tendon_family.pcc:pcc_forward_tool_v2',
        'Compute compact PCC tip and segment-end poses; backbone samples are opt-in.',
        sources=PCC_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy',), extension_dependencies=(('model.pcc', '1.0.0'),),
        cache=True, side_effects='none',
        capabilities=dict(category='mathematical_models', role='public_tool', route_visible=True,
            model='model.pcc', output_layering='compact_with_backbone_opt_in', backend_solves=0),
    ),
    Extension(
        'dynamics.gvs_evaluate', 'tool', '2.0.0',
        c.GVSDynamicsRequestV2, c.GVSDynamicsResultV2,
        'extensions.tendon_family.gvs:gvs_evaluate_tool_v2',
        'Evaluate frozen GVS dynamics with summary, force, or full diagnostics; backbone samples are opt-in.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy',), extension_dependencies=(('model.gvs', '1.0.0'),),
        cache=True, side_effects='none',
        capabilities=dict(category='mathematical_models', role='public_tool', route_visible=True,
            model='model.gvs', output_layering=['summary', 'forces', 'full'], backend_solves=0),
    ),
    Extension(
        'dynamics.gvs_evaluate', 'tool', '3.0.0',
        c.GVSDynamicsRequestV3, c.GVSDynamicsResultV2,
        'extensions.tendon_family.gvs:gvs_evaluate_tool_v2',
        'Evaluate frozen GVS dynamics with an explicit trusted basis strategy.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy',), extension_dependencies=(('model.gvs', '1.0.0'),),
        cache=True, side_effects='none',
        capabilities=dict(category='mathematical_models', role='public_tool', route_visible=True,
            model='model.gvs', output_layering=['summary', 'forces', 'full'], backend_solves=0),
    ),
    Extension(
        'dynamics.gvs_build_system', 'tool', '2.0.0',
        c.GVSBuildSystemRequestV2, c.GVSSystemArtifactResult,
        'extensions.tendon_family.gvs_casadi:gvs_build_system_tool_v2',
        'Save a GVS DynamicSystem at x0/u0 using the frozen task environment and return its EvidenceRef.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'casadi'), extension_dependencies=(('model.gvs', '1.0.0'),),
        cache=True, side_effects='artifact_store',
        capabilities=dict(category='mathematical_models', role='public_tool', route_visible=True,
            model='model.gvs', representation='dynamic_system', environment='frozen_task', backend_solves=0),
    ),
    Extension(
        'dynamics.gvs_build_system', 'tool', '3.0.0',
        c.GVSBuildSystemRequestV3, c.GVSSystemArtifactResult,
        'extensions.tendon_family.gvs_casadi:gvs_build_system_tool_v2',
        'Save a GVS DynamicSystem for an explicit trusted basis strategy and frozen task environment.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'casadi'), extension_dependencies=(('model.gvs', '1.0.0'),),
        cache=True, side_effects='artifact_store',
        capabilities=dict(category='mathematical_models', role='public_tool', route_visible=True,
            model='model.gvs', representation='dynamic_system', environment='frozen_task', backend_solves=0),
    ),
    Extension(
        'linearization.linearize', 'tool', '2.0.0',
        c.GVSLinearizeRequestV2, c.LinearizedModelArtifactResult,
        'extensions.tendon_family.gvs_casadi:linearize_tool_v2',
        'Resolve a DynamicSystem inline or by EvidenceRef, save its AD linearization, and return a compact reference.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'casadi'), extension_dependencies=(('linearizer.casadi', '1.0.0'),),
        cache=True, side_effects='artifact_store',
        capabilities=dict(category='linearization', role='public_tool', route_visible=True,
            evidence_input=True, evidence_output=True, backend_solves=0),
    ),
    Extension(
        'statics.gvs_equilibrium', 'tool', '1.0.0',
        c.GVSEquilibriumRequest, c.GVSEquilibriumResult,
        'extensions.tendon_family.gvs_casadi:gvs_equilibrium_tool',
        'Solve frozen-robot static GVS equilibrium for specified tendon tensions from an initial q.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'casadi'), extension_dependencies=(('model.gvs', '1.0.0'),),
        cache=True, side_effects='none',
        capabilities=dict(category='statics', role='public_tool', route_visible=True,
            model='model.gvs', equation='tendon+gravity-elastic=0', backend_solves=0),
    ),
    Extension(
        'statics.gvs_equilibrium', 'tool', '2.0.0',
        c.GVSEquilibriumRequestV2, c.GVSEquilibriumResult,
        'extensions.tendon_family.gvs_casadi:gvs_equilibrium_tool',
        'Solve frozen-robot static GVS equilibrium for an explicit trusted basis strategy.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'casadi'), extension_dependencies=(('model.gvs', '1.0.0'),),
        cache=True, side_effects='none',
        capabilities=dict(category='statics', role='public_tool', route_visible=True,
            model='model.gvs', equation='tendon+gravity-elastic=0', backend_solves=0),
    ),
    Extension(
        'control.lqr_synthesize', 'tool', '1.0.0',
        c.LQRSynthesizeRequest, c.LQRSynthesisResult,
        'extensions.tendon_family.gvs_casadi:lqr_synthesize_tool',
        'Synthesize continuous LQR from a LinearizedModel reference using compact semantic weights and frozen actuator facts.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'scipy'), extension_dependencies=(('controller.lqr', '1.0.0'),),
        cache=True, side_effects='artifact_store',
        capabilities=dict(category='control', role='public_tool', route_visible=True,
            evidence_input=True, evidence_output=True, command_space='model_tendon_tension',
            backend_executable=False, backend_solves=0),
    ),
    Extension(
        'control.lqr_describe', 'tool', '2.0.0',
        c.LQRDescribeRequest, c.LQRSynthesisDescription,
        'extensions.tendon_family.gvs_casadi:lqr_describe_tool_v2',
        'Describe the semantic LinearizedModel-to-LQR synthesis workflow and frozen tendon authority.',
        sources=GVS_SOURCES, contract_dependencies=COMMON['contract_dependencies'],
        dependencies=('numpy', 'scipy'), extension_dependencies=(('controller.lqr', '1.0.0'),),
        cache=True, side_effects='none',
        capabilities=dict(category='control', role='public_tool', route_visible=True,
                          recommended=True, backend_solves=0),
    ),
])

EXTENSIONS.extend([
    Extension(
        'optimization_assembler.pcc_reach', 'optimization_assembler', '1.0.0',
        c.PCCReachAssemblerParameters, OptimizationProblem,
        'extensions.tendon_family.scientific_optimization:PCCReachAssembler',
        'Build one-variable PCC reach problems from an authorized length and the frozen Task target.',
        sources=OPT_SOURCES, dependencies=('numpy', 'casadi'),
        contract_dependencies=COMMON['contract_dependencies'] + (
            ('platform.optimization_problem', '1.0.0'),
            ('optimization.casadi_nlp_expression', '1.0.0'),
            ('optimization.casadi_nlp_selector', '1.0.0'),
        ),
        extension_dependencies=(('model.pcc', '1.0.0'),),
        capabilities=dict(category='optimization', role='adapter', model='model.pcc', model_version='1.0.0',
            authorization='extensions.tendon_family.scientific_optimization:pcc_authorization',
            supported_objectives=['tip_position_error_squared'],
            supported_constraints=['authorized_design_bounds'],
            target_source='frozen_task.goal.target_m', backend_solves=0),
    ),
    Extension(
        'optimization_assembler.gvs_inverse', 'optimization_assembler', '1.0.0',
        c.GVSInverseAssemblerParameters, OptimizationProblem,
        'extensions.tendon_family.scientific_optimization:GVSInverseAssembler',
        'Build GVS inverse-shape or static inverse-tip problems from frozen robot/task facts.',
        sources=OPT_SOURCES, dependencies=('numpy', 'casadi'),
        contract_dependencies=COMMON['contract_dependencies'] + (
            ('platform.optimization_problem', '1.0.0'),
            ('optimization.casadi_nlp_expression', '1.0.0'),
            ('optimization.casadi_nlp_selector', '1.0.0'),
        ),
        extension_dependencies=(('model.gvs', '1.0.0'),),
        capabilities=dict(category='optimization', role='adapter', model='model.gvs', model_version='1.0.0',
            authorization='extensions.tendon_family.scientific_optimization:gvs_authorization',
            supported_objectives=['inverse_shape_static', 'tip_position_error_squared', 'tendon_effort'],
            supported_constraints=['static_equilibrium', 'tendon_force_bounds'],
            target_source='q_target for inverse_shape; frozen_task.goal.target_m for inverse_tip_static',
            backend_solves=0),
    ),
    Extension(
        'optimization_assembler.gvs_inverse', 'optimization_assembler', '2.0.0',
        c.GVSInverseAssemblerParametersV2, OptimizationProblem,
        'extensions.tendon_family.scientific_optimization:GVSInverseAssembler',
        'Build GVS inverse-shape or static inverse-tip problems with an explicit trusted basis strategy.',
        sources=OPT_SOURCES, dependencies=('numpy', 'casadi'),
        contract_dependencies=COMMON['contract_dependencies'] + (
            ('platform.optimization_problem', '1.0.0'),
            ('optimization.casadi_nlp_expression', '1.0.0'),
            ('optimization.casadi_nlp_selector', '1.0.0'),
        ),
        extension_dependencies=(('model.gvs', '1.0.0'),),
        capabilities=dict(category='optimization', role='adapter', model='model.gvs', model_version='1.0.0',
            authorization='extensions.tendon_family.scientific_optimization:gvs_authorization',
            supported_objectives=['inverse_shape_static', 'tip_position_error_squared', 'tendon_effort'],
            supported_constraints=['static_equilibrium', 'tendon_force_bounds'],
            target_source='q_target for inverse_shape; frozen_task.goal.target_m for inverse_tip_static',
            backend_solves=0),
    ),
])
