"""Physical scene construction, then separately bound task/control metadata."""
from schemas.platform import Payload
from tools.state_io import digest
from extensions.experiment_dynamics.contracts import Assembly
from .contracts import Initial
from .compiler import quat


def initialize(parameters, seed):
    return Payload(contract='family.initial',data=parameters.model_dump(mode='json'))


def assemble_physical(inp,p):
    """Mount, environment, initial state and clocks; no goal or controller needed."""
    assembly=Assembly.model_validate(inp.task.environment.data)
    a=assembly.model_dump(mode='json'); env=assembly.environment
    if len(env.objects)!=1 or env.objects[0].kind!='plane' or env.objects[0].name!=assembly.floor_id:
        raise ValueError('SCENE_REQUIRES_ONE_NAMED_FLOOR')
    if not env.objects[0].conaffinity & 1: raise ValueError('SCENE_FLOOR_MUST_COLLIDE_WITH_ROBOT')
    initial=Initial.model_validate(inp.task.initializer.parameters.data)
    for state in (initial.qpos_rad,initial.qvel_rad_s):
        if set(state)-set(p['dofs']): raise ValueError('INITIAL_UNKNOWN_JOINT: '+str(set(state)-set(p['dofs'])))
    t=inp.task.timing
    if t.control_period_s!=t.sample_period_s or abs(t.duration_s/t.control_period_s-round(t.duration_s/t.control_period_s))>1e-8:
        raise ValueError('FAMILY_REQUIRES_SAMPLES_AT_CONTROL_GRID_AND_WHOLE_INTERVALS')
    forces=[]
    for f in assembly.external_forces:
        if f.entity not in [b['entity'] for b in p['parts']]: raise ValueError('UNKNOWN_FORCE_BODY: '+f.entity)
        if f.end_s>t.duration_s or any(abs(x/t.control_period_s-round(x/t.control_period_s))>1e-8 for x in (f.start_s,f.end_s)):
            raise ValueError('FORCE_WINDOW_MUST_BE_ON_CONTROL_GRID')
        forces.append(dict(body=[b['entity'] for b in p['parts']].index(f.entity),**f.model_dump(mode='json')))
    scene=dict(physics_identity=p['identity'],assembly=a,initial=initial.model_dump(mode='json'),
        qpos_rad=[initial.qpos_rad.get(j,0.) for j in p['dofs']],qvel_rad_s=[initial.qvel_rad_s.get(j,0.) for j in p['dofs']],
        mount_rotation=quat(assembly.mount.quaternion_wxyz).tolist(),mount_position=list(assembly.mount.position_m),
        gravity=list(env.gravity_m_s2),floor_z_m=env.objects[0].position_m[2],floor_id=assembly.floor_id,
        forces=forces,duration_s=t.duration_s,
        timestep_s=t.timestep_s,control_period_s=t.control_period_s,sample_period_s=t.sample_period_s,
        observation_phase='post_step',
        entity_mapping=dict(parts=p['entity_map'],dofs=list(p['dofs']),tendons=[x['entity'] for x in p['tendons']],
            actuators=[x['id'] for x in p['actuators']]),
        semantics=dict(units='SI',world_frame=inp.robot.frame,force_frame='world',
            initial_state='named model coordinates; unspecified joints are zero',
            timing='control observations and force signals are interval-start/pre-step; saved state signals are interval-end/post-step'))
    scene['identity']=digest(scene)
    return scene


def assemble(inp,p):
    from tools.platform_registry import registry
    from tools.research_tasks import task_adapter
    scene=assemble_physical(inp,p)
    physical_scene_identity=scene.pop('identity')
    definition=registry().get(inp.policy.controller.extension_id,inp.policy.controller.version,'controller')
    resolver=definition.hook('resolve_control')
    if resolver is None:
        if inp.policy.controller.extension_id!='controller.gvs_nmpc':raise ValueError('ACTIVE_RESEARCH_CONTROLLER_REQUIRED')
        from .gvs_nmpc import resolve_gvs_nmpc_control
        resolver=resolve_gvs_nmpc_control
    control=resolver(inp,p)
    adapter=task_adapter(inp)
    reference=adapter.control_reference()
    task_identity=digest(inp.task.model_dump(mode='json'))
    scene.update(control=control,task_identity=task_identity,task_reference=reference,
        physical_scene_identity=physical_scene_identity)
    # Optional renderer marker only. Neither physics nor execution consumes it.
    if reference['kind']=='constant':
        scene['target_world_m']=adapter.reference_at([0.])[0][0].tolist()
    scene['identity']=digest(scene)
    from .execution import resolve_execution
    dynamics_model_identity=resolve_execution(inp,registry())['dynamics_model_identity']
    scene['experiment_spec']=dict(version='family_experiment_v1',task_identity=task_identity,
        design_identity=p['design_identity'],discretization_identity=p['discretization_identity'],
        physics_identity=p['identity'],scene_identity=scene['identity'],dynamics_model_identity=dynamics_model_identity,
        control_identity=control['identity'],
        source_roles=dict(task='SessionInput.task',environment_mount_forces='TaskDefinition.environment',
            initial_state='TaskDefinition.initializer',run_plan='ExperimentPolicy backend/controller/discretization',
            resolved_physics='derived from family.design + family.discretization'))
    return scene
