"""Capability catalog: descriptive families and executable serial scope are distinct."""
from schemas.platform import BackendResult, Payload, SessionInput
from tools.platform_registry import Extension
from . import contracts as c

CONTRACTS=[('family.'+name,'1.0.0',schema) for name,schema in [
    ('design',c.Design),('initial',c.Initial),('control',c.Control),('parameters',c.Parameters),('backend_data',c.Data),
    ('dynamics_model',c.DynamicsModel),('matlab_parameters',c.MatlabParameters),('mujoco_parameters',c.MujocoParameters),
    ('space',c.Space),('discretization',c.Discretization),('experiment_spec',c.ExperimentSpec),
    ('build_request',c.BuildRequest),('build_result',c.BuildResult)]]
SOURCES=tuple('extensions/tendon_family/'+n+'.py' for n in ('contracts','compiler','sections','geometry','legacy','scene','control','execution','backends','signals','candidate','preparation','mjcf','saved','manifest'))+(
    'tools/platform_tools.py','tools/platform_tasks.py','schemas/platform_operations.py','tools/design_compiler.py',
    'tools/matlab_tools.py','tools/state_io.py','extensions/experiment_dynamics/contracts.py',
    'extensions/experiment_dynamics/physics.py','extensions/robot_domain/contracts.py',
    'schemas/environment_spec.py','schemas/robot_ir.py','schemas/exploration.py')
MATLAB=tuple('matlab/'+n+'.m' for n in ('tf_geometry','tf_point','tf_routes','tf_terms','tf_control','tf_run','tf_observe','tf_static','tf_view'))
COMMON=dict(sources=SOURCES,contract_dependencies=tuple((n,v) for n,v,_ in CONTRACTS))
EXTENSIONS=[
    Extension('initialize.family','initializer','1.0.0',c.Initial,Payload,'extensions.tendon_family.scene:initialize',
        '具名初态；未指定的候选自由度为零',**COMMON,capabilities=dict(category='scene_assembly',role='adapter')),
    Extension('controller.family','controller','1.0.0',c.Control,Payload,'extensions.tendon_family.control:Controller',
        '理想驱动映射、确定性指令或实时末端反馈',**COMMON,capabilities=dict(category='control',role='adapter',
            channel='actuator_commands',observations=['tip_position'],reset=True,restore=False,
            algorithms={'deterministic':'deterministic_actuator_reference_v1','tip_feedback':'tip_resolved_rate_feedback_v1'},
            reference_types=['actuator_commands','task_goal'],output='named actuator command -> tendon target length',
            sampling={'control_observation':'interval_start_pre_step','force':'interval_start_pre_step_solver','state':'interval_end_post_step'})),
    Extension('candidate.family','candidate_builder','1.0.0',c.Space,SessionInput,'extensions.tendon_family.candidate:apply',
        '数值、整数、选项与完整结构模板候选',**COMMON,capabilities=dict(category='robot_design',role='adapter',
            editable=[],authorize_changes='extensions.tendon_family.candidate:authorize',
            search='External/LLM structural proposals; existing continuous search algorithms are not mixed-integer optimizers')),
    Extension('design.family_build','tool','1.0.0',c.BuildRequest,c.BuildResult,'extensions.tendon_family.candidate:build_tool',
        '构建完整候选、摘要、派生物理与适用性；不启动求解器',**COMMON,capabilities=dict(category='robot_design',role='public_tool')),
]
EXTENSIONS.append(Extension('model.serial_bending_cells','dynamics_model','1.0.0',c.DynamicsModel,Payload,
    'extensions.tendon_family.execution:model_definition','串联逐刚体、逐单元双主轴弯曲数学模型',**COMMON,
    capabilities=dict(category='mathematical_model',role='definition',coordinates='two principal bending angles per cell',
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
        'extensions.tendon_family.backends:'+binding,'具名串联多段双轴弯曲与逐根绳路',**COMMON,
        assets=MATLAB if name=='matlab_spatial' else (),dependencies=deps,resources=resources,
        capabilities=shared_capabilities))
    parameters=c.MatlabParameters if name=='matlab_spatial' else c.MujocoParameters
    contract='family.matlab_parameters' if name=='matlab_spatial' else 'family.mujoco_parameters'
    modern={**shared_capabilities,'inactive_parameters':[],'numerical_contract':contract}
    EXTENSIONS.append(Extension('backend.'+name,'backend','1.1.0',parameters,BackendResult,
        'extensions.tendon_family.backends:'+binding,'显式模型兼容关系与后端专用数值设置',sources=SOURCES,
        contract_dependencies=COMMON['contract_dependencies'],assets=MATLAB if name=='matlab_spatial' else (),
        dependencies=deps,resources=resources,capabilities=modern))
