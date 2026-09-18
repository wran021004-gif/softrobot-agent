"""Capability catalog: descriptive families and executable serial scope are distinct."""
from schemas.platform import BackendResult, Payload, SessionInput
from tools.platform_registry import Extension
from . import contracts as c
from . import optimization as opt
from . import route

CONTRACTS=[('family.'+name,'1.0.0',schema) for name,schema in [
    ('route_policy',route.RoutePolicy),
    ('optimization_request',opt.OptimizationRequest),('search',opt.SearchParameters),('search_state',opt.SearchState),
    ('design',c.Design),('initial',c.Initial),('control',c.Control),('parameters',c.Parameters),('backend_data',c.Data),
    ('dynamics_model',c.DynamicsModel),('matlab_parameters',c.MatlabParameters),('mujoco_parameters',c.MujocoParameters),
    ('space',c.Space),('discretization',c.Discretization),('experiment_spec',c.ExperimentSpec),
    ('build_request',c.BuildRequest),('build_result',c.BuildResult)]]
SOURCES=tuple('extensions/tendon_family/'+n+'.py' for n in ('contracts','compiler','sections','geometry','legacy','scene','control','execution','backends','signals','candidate','preparation','mjcf','saved','manifest','optimization','crosscheck','route'))+(
    'tools/optimization_interfaces.py','tools/platform_search.py',
    'tools/platform_tools.py','tools/platform_tasks.py','schemas/platform_operations.py','tools/design_compiler.py',
    'tools/matlab_tools.py','tools/state_io.py','extensions/experiment_dynamics/contracts.py',
    'extensions/experiment_dynamics/physics.py','extensions/robot_domain/contracts.py',
    'schemas/environment_spec.py','schemas/robot_ir.py','schemas/exploration.py','schemas/platform_math.py')
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
        'Ideal actuator mapping with deterministic commands or live tip feedback',**COMMON,capabilities=dict(category='control',role='adapter',
            channel='actuator_commands',observations=['tip_position'],reset=True,restore=False,
            algorithms={'deterministic':'deterministic_actuator_reference_v1','tip_feedback':'tip_resolved_rate_feedback_v1'},
            reference_types=['actuator_commands','task_goal'],output='named actuator command -> tendon target length',
            sampling={'control_observation':'interval_start_pre_step','force':'interval_start_pre_step_solver','state':'interval_end_post_step'})),
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
            controllers=['controller.family'],signals=['tip_position','joint_position','joint_velocity','tendon_length','tendon_tension','tendon_target_length','actuator_command','actuator_torque','external_torque'],
            signal_specs_resolver='extensions.tendon_family.signals:observation_specs',signal_phases=['post_step','pre_step_solver'],
            structures=['serial flexible segments','fixed rigid connectors','guides','payloads'],
            sections=['circle','tube','ellipse','rectangle','simple polygon with holes'],
            routing='ordered body/physical-segment stations, straight frictionless spans, intermediate anchors',
            transmission='independent/shared ideal displacement or drum rotation; winding sign; travel/speed and per-tendon force limits',
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
