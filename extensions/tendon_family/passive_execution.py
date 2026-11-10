"""Controller-free finite-time execution using the existing fixed-payout compiler."""
import time
import csv
import hashlib
from copy import deepcopy
from pathlib import Path
import numpy as np
import mujoco
from schemas.platform import BackendResult, Payload, Signal, SignalSpec
from tools.platform_store import plain
from tools.state_io import digest, atomic_json
from .backends import physics_for, MujocoFailureSnapshot
from .passive import PassiveModel
from .scene import assemble_physical
from extensions.reference.passive_response import task_definition, load_at


def source_binding(configuration):
    """One exact effective physical/task source; no fictitious control identity."""
    from schemas.platform import SessionInput
    inp=SessionInput.model_validate(configuration)
    from tools.platform_tasks import compile_input
    compile_input(plain(inp))
    p=physics_for(inp)
    v2=inp.task.goal.data.get('version')=='passive_response_v2'
    numerical=(dict(passive_limit_solver={k:inp.task.goal.data[k] for k in ('solreflimit','solimplimit')}) if v2 else {})
    return dict(source_kind='frozen_passive_protocol_v2' if v2 else 'frozen_passive_protocol_v1',task_identity=digest(plain(inp.task)),
        design_identity=p['design_identity'],model_identity=digest(dict(physics=p['identity'],
            backend=plain(inp.policy.backend),model=plain(inp.policy.dynamics_model),
            environment=plain(inp.task.environment),initial=plain(inp.task.initializer),timing=plain(inp.task.timing),**numerical)),
        protocol=plain(inp.task.goal),initial=plain(inp.task.initializer))


def observation_specs(inp,reg=None):
    fields=[('tip_position',3,'m','world'),('tip_velocity',3,'m/s','world'),
        ('material_position',3,'m','world'),('material_velocity',3,'m/s','world'),
        ('joint_position',1,'rad','joint_local'),('joint_velocity',1,'rad/s','joint_local'),
        ('tendon_length',1,'m','path'),('tendon_tension',1,'N','path'),('length_residual',1,'m','path')]
    p=physics_for(inp);specs=[]
    for case in inp.task.goal.data['load_conditions']:
        for name,dim,unit,frame in fields:
            entities=(p['dofs'] if name.startswith('joint_') else [t['entity'] for t in p['tendons']] if name.startswith('tendon_') or name=='length_residual'
                else ['point_'+str(i) for i,_ in enumerate(inp.task.physical_problem['monitor_s'])] if name.startswith('material_') else ['tip'])
            for entity in entities:
                specs.append(SignalSpec(name=name,entity=case+'__'+entity,dimension=dim,units=unit,frame=frame,phase='post_step'))
    return specs


def backend_result(inp,raw):
    fields=dict(tip_position='tip_m',tip_velocity='tip_velocity_m_s',material_position='material_positions_m',
        material_velocity='material_velocities_m_s',joint_position='qpos_rad',joint_velocity='qvel_rad_s',
        tendon_length='tendon_length_m',tendon_tension='actual_tension_n',length_residual='length_residual_m')
    signals=[];p=physics_for(inp)
    for spec in observation_specs(inp):
        case,entity=spec.entity.split('__',1)
        episode=next((e for e in raw.get('episodes',[]) if e['load_condition']==case),None)
        if episode is None:continue
        name=spec.name;rows=episode['samples'];field=fields[name]
        if name.startswith('material_'):index=int(entity.removeprefix('point_'))
        elif name.startswith('joint_'):index=p['dofs'].index(entity)
        elif name.startswith('tendon_') or name=='length_residual':index=[t['entity'] for t in p['tendons']].index(entity)
        else:index=None
        signals.append(Signal(spec=spec,times_s=[r['time_s'] for r in rows],
            values=[r[field] if index is None else r[field][index] if spec.dimension==3 else [r[field][index]] for r in rows]))
    v2=inp.task.goal.data.get('version')=='passive_response_v2'
    initial=(Payload(contract='reference.passive_initial_execution',version='2.0.0',data=dict(
        source=raw['initial_state_source'],state_identities={e['load_condition']:e['integration_initial']['state_identity'] for e in raw['episodes']},
        source_result=raw.get('initial_state_result'))) if v2 else inp.task.initializer.parameters)
    return BackendResult(solver_status='completed' if raw['status']=='completed' else 'failed',
        backend_id='backend.family_passive_mujoco',model_id='mujoco_passive_fixed_payout_v2' if v2 else 'mujoco_passive_fixed_payout_v1',signals=signals,
        data=Payload(contract='family.passive_dynamic_data',version='2.0.0' if v2 else '1.0.0',data=raw),initial_state=initial,seed=inp.seed,
        limitations=['MuJoCo unilateral soft tendon limits; static hard KKT feasibility does not imply dynamic acceptance.',
            'Contact-free serial bending model; no hardware, friction, mixed actuation or robustness claim.'])


def model_signature(model,*,exclude_limits=False,exclude_timestep=False):
    """Compiled numeric assembly identity; the intervention may change one array."""
    h=hashlib.sha256()
    for name in sorted(dir(model)):
        if exclude_limits and name=='tendon_limited':continue
        value=getattr(model,name)
        if isinstance(value,np.ndarray):
            h.update(name.encode());h.update(str((value.shape,value.dtype.str)).encode());h.update(value.tobytes())
    h.update(str((None if exclude_timestep else model.opt.timestep,int(model.opt.integrator),model.opt.iterations,model.opt.tolerance)).encode())
    return h.hexdigest()


def integration_state(model,data,binding):
    spec=int(mujoco.mjtState.mjSTATE_INTEGRATION)
    vector=np.empty(mujoco.mj_stateSize(model,spec));mujoco.mj_getState(model,data,vector,spec)
    value=dict(version='passive_integration_state_v2',state_spec=spec,state_vector=vector.tolist(),
        physical_binding=binding,mujoco_version=mujoco.__version__,time_s=float(data.time),
        qpos_rad=data.qpos.tolist(),qvel_rad_s=data.qvel.tolist())
    return dict(**value,state_identity=digest(value))


def restore_state(model,data,value,binding):
    supplied={k:v for k,v in value.items() if k!='state_identity'}
    vector=np.asarray(value.get('state_vector',[]),dtype=float)
    spec=int(mujoco.mjtState.mjSTATE_INTEGRATION)
    if (digest(supplied)!=value.get('state_identity') or value.get('physical_binding')!=binding or
            value.get('mujoco_version')!=mujoco.__version__ or value.get('state_spec')!=spec or
            vector.shape!=(mujoco.mj_stateSize(model,spec),) or not np.isfinite(vector).all()):
        raise ValueError('COMPLETE_MATCHED_PASSIVE_INTEGRATION_STATE_REQUIRED')
    mujoco.mj_setState(model,data,vector,spec)
    if data.qpos.tolist()!=value['qpos_rad'] or data.qvel.tolist()!=value['qvel_rad_s'] or float(data.time)!=value['time_s']:
        raise ValueError('PASSIVE_STATE_LAYOUT_OR_CLOCK_MISMATCH')


def constraint_mechanism(native,data,goal):
    m=native.model;count=m.ntendon
    tension=np.zeros(count);states=[[] for _ in range(count)];residual=[[] for _ in range(count)]
    E=np.zeros((data.nefc,m.nv));J=native.tendon_jac(data)
    if mujoco.mj_isSparse(m):mujoco.mju_sparse2dense(E,data.efc_J,data.efc_J_rownnz,data.efc_J_rowadr,data.efc_J_colind)
    else:E[:]=data.efc_J.reshape(data.nefc,m.nv)
    error=0.
    for row in range(data.nefc):
        if data.efc_type[row]!=int(mujoco.mjtConstraint.mjCNSTR_LIMIT_TENDON):continue
        index=int(data.efc_id[row]);tension[index]+=float(data.efc_force[row])
        states[index].append(int(data.efc_state[row]));residual[index].append(float(data.efc_pos[row]))
        error=max(error,float(np.max(abs(E[row]+J[index]))))
    gap=data.ten_length-native.payout;labels=[]
    for i in range(count):
        if not m.tendon_limited[i]:label='disabled'
        elif tension[i]>goal.tension_tolerance_n and states[i] and max(states[i])>0 and gap[i]>=-goal.length_tolerance_m:label='taut'
        elif gap[i]<-goal.length_tolerance_m and tension[i]<=goal.tension_tolerance_n and not states[i]:label='slack'
        else:label='transition_or_indeterminate'
        labels.append(label)
    return dict(actual_tension_n=tension.tolist(),constraint_states=states,constraint_residuals_m=residual,
        constraint_active=[bool(v and max(v)>0) for v in states],constraint_classification=labels,
        constraint_direction_error=error)


def execute(inp,folder=None,*,disabled_limits=(),initial_state=None,initial_state_result=None,common_equilibrium=None,execution_checks='full',execution_profile=None):
    from tools.platform_registry import registry
    goal,bounds,problem=task_definition(inp.task,registry())
    v2=goal.version=='passive_response_v2'
    if execution_checks not in ('full','screening') or execution_checks=='screening' and not v2:
        raise ValueError('SUPPORTED_PASSIVE_EXECUTION_CHECKS_REQUIRED')
    from extensions.reference.passive_program import execution_scope
    scope=execution_scope(inp.task,execution_profile) if v2 else None
    exploration=bool(scope and scope['purpose']=='exploration')
    if execution_profile is not None and scope['purpose']=='final_acceptance' and execution_checks!='full':raise ValueError('FINAL_ACCEPTANCE_REQUIRES_FROZEN_CHECKS')
    route_sampling=scope['route_sampling'] if execution_profile is not None else 'score_grid' if execution_checks=='screening' else getattr(goal,'route_check','not_required')
    recording=scope['recording'] if scope else None
    sample_period=scope['sample_period_s'] if scope else inp.task.timing.sample_period_s
    original=v2 and goal.execution_protocol=='phs2d_original_v1'
    hard=v2 and goal.execution_protocol in ('phs2d_original_v1','hard_equilibrium_continuous_v1')
    if (disabled_limits or initial_state is not None) and not v2:raise ValueError('PASSIVE_V2_STATE_OR_INTERVENTION_REQUIRED')
    if initial_state is not None and not goal.allow_saved_state:raise ValueError('SAVED_PASSIVE_STATE_NOT_ALLOWED_BY_FROZEN_TASK')
    p=physics_for(inp);scene=assemble_physical(inp,p)
    order=[t['entity'] for t in p['tendons']]
    if v2 and (len(set(disabled_limits))!=len(disabled_limits) or any(name not in order for name in disabled_limits)):
        raise ValueError('EXACT_UNIQUE_PASSIVE_LIMIT_NAMES_REQUIRED')
    if disabled_limits and goal.allowed_ablation!='disable_selected_passive_limits':raise ValueError('PASSIVE_LIMIT_ABLATION_NOT_GRANTED_BY_TASK')
    if v2 and recording=='full_physics_csv' and folder is None:raise ValueError('L2_FOLDER_REQUIRED_FOR_FULL_PHYSICS_TRACE')
    scene['control']=dict(tension_execution_mode='passive_fixed_payout_v1')
    if v2:scene['control'].update(solreflimit=goal.solreflimit,solimplimit=goal.solimplimit)
    folder=Path(folder) if folder else None
    if folder:
        folder.mkdir(parents=True,exist_ok=True)
        if (folder/'passive.xml').exists() or (folder/'passive_progress.json').exists():
            raise ValueError('PRESERVE_EXISTING_PASSIVE_EXECUTION_RECOVER_WITHOUT_RELAUNCH')
    started=time.perf_counter()
    native=PassiveModel(p,plain(problem),folder/'passive.xml' if folder else None,scene=scene)
    if v2:native.design_components=inp.robot.structure.data['components']
    model=native.model
    compile_s=time.perf_counter()-started
    binding=source_binding(plain(inp))
    raw=dict(kind='passive_dynamic_execution_v1',status='incomplete',physical_binding=binding,
        active_actuators=int(model.nu),joint_count=model.nv,coordinate_order=p['dofs'],tendon_order=[t['entity'] for t in p['tendons']],
        material_point_bindings=native.points[:-1],tip_binding=native.points[-1],
        payout_lengths_m=native.payout.tolist(),initial_state=dict(qpos_rad=scene['qpos_rad'],qvel_rad_s=scene['qvel_rad_s']),
        episodes=[],physics_steps=0,attempted_steps=0,native_forward_calls=0,model_builds=1,
        timings_s=dict(model_compile=compile_s),mujoco_version=mujoco.__version__,
        solver_options=dict(timestep_s=float(model.opt.timestep),integrator=int(model.opt.integrator),
            iterations=int(model.opt.iterations),tolerance=float(model.opt.tolerance)))
    if execution_profile is not None:
        raw['execution_profile']=scope
    if execution_checks=='screening':
        policy=dict(version='sparse_route_screening_v1',level='screening',route_check=route_sampling,
            route_period_s=inp.task.timing.sample_period_s,qualification='original_dense_windows',
            recording=goal.recording,task_acceptance='unmeasured')
        raw['execution_checks']={**policy,'identity':digest(policy)}
    from extensions.reference.passive_program import execution_identity
    raw['execution_identity']=execution_identity(plain(inp),profile=execution_profile,execution_checks=execution_checks,intervention=disabled_limits,initial_state=initial_state)
    base_limited=model.tendon_limited.copy();disabled=[];unchanged=None
    if v2:
        if len(set(disabled_limits))!=len(disabled_limits) or any(name not in raw['tendon_order'] for name in disabled_limits):raise ValueError('EXACT_UNIQUE_PASSIVE_LIMIT_NAMES_REQUIRED')
        if disabled_limits and goal.allowed_ablation!='disable_selected_passive_limits':raise ValueError('PASSIVE_LIMIT_ABLATION_NOT_GRANTED_BY_TASK')
        disabled=[model.tendon(name).id for name in disabled_limits]
        unchanged=model_signature(model,exclude_limits=True)
        raw.update(kind='passive_dynamic_execution_v2',base_model_signature=model_signature(model),
            initial_state_source='saved_integration_state' if initial_state is not None else goal.initial_source,
            initial_state_result=plain(initial_state_result),trace_files=[],
            intervention=dict(kind='disable_selected_passive_limits' if disabled else 'none',tendons=list(disabled_limits),
                timing='after_identical_unloaded_qualification',only_limit_array_changed=True))
        if goal.execution_protocol=='hard_equilibrium_continuous_v1':
            raw['numerical_invariant_model_signature']=model_signature(model,exclude_timestep=True)
    dt=inp.task.timing.timestep_s;steps=round(inp.task.timing.duration_s/dt);stride=round(sample_period/dt)
    physics_score_stride=round(inp.task.timing.sample_period_s/dt)
    failure=MujocoFailureSnapshot(model,binding['model_identity'],folder)
    tendon_ids={model.tendon(t['entity']).id:i for i,t in enumerate(p['tendons'])}
    state_saves=0;state_restores=0;static_forwards=0;constraint_checks=0
    def saved_state(data):
        nonlocal state_saves
        state_saves+=1
        return integration_state(model,data,binding)
    def checkpoint():
        raw.update(physics_steps=failure.completed_steps,attempted_steps=failure.attempted_steps,
            native_forward_calls=failure.forward_evaluations)
        raw['cost']=dict(model_builds=1,physics_steps=failure.completed_steps,attempted_steps=failure.attempted_steps,
            native_forward_calls=failure.forward_evaluations,episodes_started=len(raw['episodes']),
            episodes_completed=sum(e['complete'] for e in raw['episodes']),material_point_jacobian_calls=native.cost['material_point_jacobian_calls'])
        if v2:raw['cost'].update(integration_state_saves=state_saves,integration_state_restores=state_restores,
            static_balance_forwards=static_forwards,constraint_observations=constraint_checks,
            tendon_jacobian_extractions=native.cost['tendon_jacobian_extractions'],
            route_checked_poses=sum(e.get('route_geometry',{}).get('checked_poses',0) for e in raw['episodes']),
            route_segment_body_checks=sum(e.get('route_geometry',{}).get('segment_body_checks',0) for e in raw['episodes']))
        if hard:
            raw['cost'].update({k:raw['cost'].get(k,0)+v for k,v in raw.get('cost_initialization',{}).items()})
        if original:
            for key in ('route_checked_poses','route_segment_body_checks'):
                field='checked_poses' if key=='route_checked_poses' else 'segment_body_checks'
                raw['cost'][key]-=sum(e.get('shared_baseline_route_cost',{}).get(field,0) for e in raw['episodes'])
        raw['timings_s']['total']=time.perf_counter()-started
        if folder:atomic_json(folder/'passive_progress.json',raw)
    if v2:checkpoint()
    shared=None
    if hard:
        from .passive_equilibrium import solve
        native.protocol['static_solver'].update(goal.unloaded_static_solver)
        unloaded=native.load(problem.baseline_load)
        equilibrium=common_equilibrium if common_equilibrium is not None else solve(native,unloaded.material_s,unloaded.force_world_n,multistart=goal.unloaded_multistart)
        raw['unloaded_equilibrium']=equilibrium
        raw['cost_initialization']=equilibrium['numerical_cost'] if common_equilibrium is None else {}
        if equilibrium['status']!='qualified_local_minimum':
            raw.update(status='invalid',reason='UNLOADED_HARD_EQUILIBRIUM_NOT_QUALIFIED')
            checkpoint()
            return backend_result(inp,raw)
        initial_qpos=np.asarray(equilibrium['equilibrium']['qpos'])+goal.initial_perturbation_rad*np.sin(np.arange(model.nv))
        raw['initial_state']=dict(qpos_rad=initial_qpos.tolist(),qvel_rad_s=[0.]*model.nv)
        checkpoint()
    cases=scope['load_conditions'] if scope else goal.load_conditions
    for case in cases:
        steps=round(scope['end_s'][case]/dt) if scope else steps
        if v2:model.tendon_limited[:]=base_limited
        data=mujoco.MjData(model);mujoco.mj_resetData(model,data)
        data.qpos[:]=scene['qpos_rad'];data.qvel[:]=scene['qvel_rad_s']
        if hard:data.qpos[:]=raw['initial_state']['qpos_rad'];data.qvel[:]=0.
        if initial_state is not None:restore_state(model,data,initial_state,binding);state_restores+=1
        load=native.load(case)
        episode=dict(load_condition=case,initial_state=raw['initial_state'],complete=False,samples=[],
            physics_steps=0,checked_physics_steps=0,maximum_contacts=0,
            maximum_tension_n=0.,maximum_length_excess_m=0.)
        raw['episodes'].append(episode)
        mechanism=None;map_error=0.;trace=None;writer=None
        if v2:
            episode.update(integration_initial=saved_state(data),engine_origin_s=float(data.time),state_resets=1,
                qualification_samples=[],qualifications={},phase_boundaries=[],maximum_constraint_direction_error=0.,
                maximum_force_map_error_nm=0.,minimum_constraint_multiplier_n=0.,maximum_capacity_ratio=0.,
                maximum_enabled_length_excess_m=0.,stage_extrema={},constraint_transitions=[])
            episode['route_geometry']=dict(sampling=route_sampling,checked_poses=0,segment_body_checks=0,status='not_required',first_issue=None)
            if recording=='full_physics_csv':
                path=folder/('episode_'+str(len(raw['episodes'])-1)+'.csv');trace=path.open('x',newline='')
                writer=csv.writer(trace)
                columns=['time_s','stage','engine_time_s','force_x_n','force_y_n','force_z_n']
                for prefix,count in [('qpos',model.nq),('qvel',model.nv),('length_m',model.ntendon),
                        ('tension_n',model.ntendon),('length_residual_m',model.ntendon),('constraint_state',model.ntendon),('constraint_residual_m',model.ntendon)]:
                    columns.extend(prefix+'_'+str(i) for i in range(count))
                columns+=['contacts','warnings','constraint_direction_error_m_rad','force_map_error_nm']
                writer.writerow(columns)
        def refresh(t):
            nonlocal map_error
            force,phase=load_at(goal,load,t)
            if not original:failure.call(data,mujoco.mj_forward,'passive_state_geometry')
            _,J=native.apply_force(data,load.material_s,force)
            if v2:map_error=float(np.max(abs(data.qfrc_applied-J.T@np.asarray(force))))
            failure.call(data,mujoco.mj_forward,'passive_loaded_constraints')
            return force,phase
        def tension():
            if v2:return mechanism['actual_tension_n']
            values=np.zeros(model.ntendon)
            for j in range(data.nefc):
                if data.efc_type[j]==int(mujoco.mjtConstraint.mjCNSTR_LIMIT_TENDON):
                    values[tendon_ids[int(data.efc_id[j])]]+=abs(float(data.efc_force[j]))
            return values.tolist()
        def safety(time_s=0.):
            nonlocal mechanism,constraint_checks
            if v2:
                mechanism=constraint_mechanism(native,data,goal);constraint_checks+=1
                episode['maximum_constraint_direction_error']=max(episode['maximum_constraint_direction_error'],mechanism['constraint_direction_error'])
                episode['maximum_force_map_error_nm']=max(episode['maximum_force_map_error_nm'],map_error)
                episode['minimum_constraint_multiplier_n']=min(episode['minimum_constraint_multiplier_n'],min(tension()))
                episode['maximum_capacity_ratio']=max(episode['maximum_capacity_ratio'],max(v/t['force_limit_n'] for v,t in zip(tension(),p['tendons'])))
                enabled=[i for i in range(model.ntendon) if model.tendon_limited[i]]
                episode['maximum_enabled_length_excess_m']=max(episode['maximum_enabled_length_excess_m'],max([0.]+[float(data.ten_length[i]-native.payout[i]) for i in enabled]))
                phase=load_at(goal,load,time_s)[1]
                stage=next(s for s in goal.programs[case] if s.name==phase)
                extrema=episode['stage_extrema'].setdefault(phase,dict(physics_steps=0,observation={},scoring={}))
                extrema['physics_steps']+=int(time_s>0)
                for scope,window in (('observation',stage.observation_window_s),('scoring',stage.scoring_window_s)):
                    if not window[0]-1e-10<=time_s<=window[1]+1e-10:continue
                    values=dict(maximum_tension=max(tension()),maximum_length_excess=max([0.]+[float(data.ten_length[i]-native.payout[i]) for i in enabled]),
                        maximum_joint_position=float(max(abs(data.qpos))),maximum_joint_speed=float(max(abs(data.qvel))))
                    for name,value in values.items():extrema[scope][name]=max(extrema[scope].get(name,0.),value)
                previous=episode.get('last_constraint_classification')
                if previous is not None and previous!=mechanism['constraint_classification']:
                    episode['constraint_transitions'].append(dict(time_s=time_s,stage=phase,previous=previous,
                        current=mechanism['constraint_classification'],actual_tension_n=tension(),
                        length_residual_m=(data.ten_length-native.payout).tolist(),constraint_states=mechanism['constraint_states']))
                episode['last_constraint_classification']=mechanism['constraint_classification']
                if route_sampling=='every_physics_step' or route_sampling=='score_grid' and abs(time_s/sample_period-round(time_s/sample_period))<1e-8:
                    from .route_validation import validate_routes
                    check=validate_routes(native,[data.qpos],data=data);record=episode['route_geometry']
                    record['checked_poses']+=1;record['segment_body_checks']+=check['segment_body_checks']
                    if check['issues'] and record['first_issue'] is None:record['first_issue']=dict(time_s=time_s,**check['issues'][0])
                    record['status']='illegal' if record['first_issue'] else 'legal_at_checked_poses'
            episode['maximum_contacts']=max(episode['maximum_contacts'],int(data.ncon))
            episode['maximum_tension_n']=max(episode['maximum_tension_n'],max(tension()))
            episode['maximum_length_excess_m']=max(episode['maximum_length_excess_m'],max(0.,float(max(data.ten_length-native.payout))))
        def sample(t,force,phase):
            nonlocal static_forwards
            points=[native.point(data,b) for b in native.points]
            value=dict(time_s=t,engine_time_s=float(data.time),qpos_rad=data.qpos.tolist(),qvel_rad_s=data.qvel.tolist(),
                tip_m=points[-1][0].tolist(),tip_velocity_m_s=(points[-1][1]@data.qvel).tolist(),
                material_positions_m=[x[0].tolist() for x in points[:-1]],material_velocities_m_s=[(x[1]@data.qvel).tolist() for x in points[:-1]],
                tendon_length_m=data.ten_length.tolist(),length_residual_m=(data.ten_length-native.payout).tolist(),
                actual_tension_n=tension(),taut=[bool(v>0) for v in tension()],force_world_n=force,phase=phase,
                ncon=int(data.ncon),nefc=int(data.nefc),solver_iterations=int(np.max(data.solver_niter)),
                warnings=[dict(number=int(w.number),lastinfo=int(w.lastinfo)) for w in data.warning])
            if v2:
                static=mujoco.MjData(model)
                if goal.static_balance_reference=='copied_integration_zero_velocity':mujoco.mj_copyData(static,model,data)
                else:static.qpos[:]=data.qpos
                static.qvel[:]=0.
                if not original:failure.call(static,mujoco.mj_forward,'passive_static_geometry')
                native.apply_force(static,load.material_s,force)
                failure.call(static,mujoco.mj_forward,'passive_static_balance');static_forwards+=1 if original else 2
                balance=static.qfrc_passive+static.qfrc_applied-static.qfrc_bias+static.qfrc_constraint
                scale=max(float(np.max(abs(v))) for v in (static.qfrc_passive,static.qfrc_applied,static.qfrc_bias,static.qfrc_constraint))
                value.update(**mechanism,static_balance_inf_nm=float(np.max(abs(balance))),
                    generalized_force_scale_nm=scale,normalized_static_balance=float(np.max(abs(balance)))/scale if scale>0 else None,
                    force_map_error_nm=map_error,
                    taut=[label=='taut' for label in mechanism['constraint_classification']])
                if original:
                    value.update(qacc_rad_s2=data.qacc.tolist(),qacc_warmstart=data.qacc_warmstart.tolist(),
                        applied_force_nm=data.qfrc_applied.tolist(),passive_force_nm=data.qfrc_passive.tolist(),
                        bias_force_nm=data.qfrc_bias.tolist(),constraint_force_nm=data.qfrc_constraint.tolist(),
                        static_balance_nm=balance.tolist())
            return value
        try:
            start_tick=0
            if original and shared is not None:
                # One freshly integrated baseline belongs to this execution. Logical
                # episode prefixes reference it; they are never charged as new steps.
                episode.update(deepcopy(shared))
                episode['load_condition']=case;episode['complete']=False
                episode['shared_unloaded_reference']=raw['episodes'][0]['load_condition']
                episode['shared_baseline_route_cost']=deepcopy(shared['route_geometry'])
                episode['executed_physics_steps']=0
                start_tick=round(goal.programs[case][0].end_s/dt)
                data.qpos[:]=episode['qualified_state']['qpos_rad'];data.qvel[:]=0.
                episode['loading_initial']=saved_state(data)
                episode['state_resets']=2
                failure.call(data,mujoco.mj_forward,'passive_loading_initial_geometry')
                refresh(start_tick*dt)
            else:
                if original:failure.call(data,mujoco.mj_forward,'passive_original_initial_geometry')
                force,phase=refresh(0.);safety();first=sample(0.,force,phase);episode['samples'].append(first)
                if v2 and not exploration and any(q.sampling=='every_physics_step' and q.window_s[0]==0 for q in goal.qualifications):episode['qualification_samples'].append(first)
            checkpoint()
            for tick in range(start_tick,steps):
                if v2 and disabled and tick==round(goal.programs[case][0].end_s/dt):
                    if not episode.get('qualified_state'):raise ValueError('QUALIFIED_COMMON_INITIAL_STATE_REQUIRED_BEFORE_ABLATION')
                    model.tendon_limited[disabled]=False
                    if model_signature(model,exclude_limits=True)!=unchanged:raise ValueError('ABLATION_CHANGED_BASE_PHYSICAL_ASSEMBLY')
                    episode['intervention_at_s']=tick*dt
                # v1 is unchanged. v2 explicitly freezes interval-start/end force semantics.
                applied_time=(tick+1)*dt if v2 and goal.force_sampling=='interval_end' else tick*dt
                if hard:
                    force,phase=load_at(goal,load,applied_time)
                    _,J=native.apply_force(data,load.material_s,force)
                    map_error=float(np.max(abs(data.qfrc_applied-J.T@np.asarray(force))))
                else:force,phase=refresh(applied_time)
                failure.call(data,mujoco.mj_step,'passive_time_integration')
                episode['physics_steps']+=1
                if hard:
                    failure.call(data,mujoco.mj_forward,'passive_original_post_step_geometry')
                    if original and (tick+1)%physics_score_stride==0:
                        native.apply_force(data,load.material_s,force)
                        failure.call(data,mujoco.mj_forward,'passive_original_snapshot_constraints')
                else:force,phase=refresh(applied_time if v2 else (tick+1)*dt)
                now=(tick+1)*dt
                if v2:phase=load_at(goal,load,now)[1]
                safety(now);episode['checked_physics_steps']+=1
                dense=v2 and not exploration and any(q.sampling=='every_physics_step' and q.window_s[0]-1e-10<=now<=q.window_s[1]+1e-10 for q in goal.qualifications)
                if (tick+1)%stride==0 or dense:
                    row=sample(now,force,phase)
                    window=scope['observation_window_s'] if exploration else None
                    if (tick+1)%stride==0 and (not window or window[0]-1e-10<=now<=window[1]+1e-10):episode['samples'].append(row)
                    if dense:episode['qualification_samples'].append(row)
                    if not v2:checkpoint()
                if writer:
                    writer.writerow([now,phase,float(data.time),*force,*data.qpos,*data.qvel,*data.ten_length,*tension(),
                        *(data.ten_length-native.payout),*[max(s) if s else -1 for s in mechanism['constraint_states']],
                        *[s[0] if s else '' for s in mechanism['constraint_residuals_m']],
                        int(data.ncon),sum(w.number for w in data.warning),mechanism['constraint_direction_error'],map_error])
                if v2 and any(abs(now-stage.end_s)<1e-10 for stage in goal.programs[case]):
                    from extensions.reference.passive_program import qualification
                    boundary_state=saved_state(data)
                    episode['phase_boundaries'].append(dict(stage=phase,time_s=now,integration_state=boundary_state))
                    for rule in goal.qualifications:
                        if abs(rule.window_s[1]-now)>1e-10:continue
                        selected=episode['qualification_samples'] if rule.sampling=='every_physics_step' and not exploration else episode['samples']
                        qualified=qualification(selected,rule,disabled_limits=disabled if disabled and episode.get('intervention_at_s') is not None else ())
                        if exploration:
                            qualified.update(sampling='score_grid',scope='Exploratory sampled diagnostic; frozen every-step qualification is not established')
                        episode['qualifications'][rule.stage]=qualified
                        if rule.stage==goal.unloaded_stage:
                            if not qualified['passed'] and not exploration:raise ValueError('UNLOADED_DYNAMIC_QUALIFICATION_FAILED')
                            episode['qualified_state']=boundary_state
                    checkpoint()
                    if original and abs(now-goal.programs[case][0].end_s)<1e-10:
                        shared=deepcopy({k:v for k,v in episode.items() if k not in ('load_condition','loading_initial')})
                        raw['shared_unloaded_identity']=digest(shared)
                        data=mujoco.MjData(model);data.qpos[:]=boundary_state['qpos_rad']
                        episode['loading_initial']=saved_state(data);episode['state_resets']=2
                        failure.call(data,mujoco.mj_forward,'passive_loading_initial_geometry')
                        refresh(now)
            episode['complete']=True
            if original:episode['executed_physics_steps']=steps-start_tick
        except Exception as exc:
            raw['reason']=str(exc)
            if v2:raw['status']='invalid'
            if getattr(exc,'mujoco_diagnostic',None):raw['numerical_failure']=exc.mujoco_diagnostic
            checkpoint();break
        finally:
            if trace:
                trace.close()
                with path.open('rb') as stream:identity=hashlib.file_digest(stream,'sha256').hexdigest()
                raw['trace_files'].append(dict(path=path.name,sha256=identity,bytes=path.stat().st_size,
                    physics_steps=episode.get('executed_physics_steps',episode['physics_steps']),load_condition=case,format='full_physics_csv_v2'))
        checkpoint()
    if len(raw['episodes'])==len(cases) and all(e['complete'] for e in raw['episodes']):raw['status']='completed'
    if exploration:
        raw['acceptance_status']='not_evaluated'
        raw['observation_coverage']=[dict(load_condition=e['load_condition'],times_s=[r['time_s'] for r in e['samples']],route_geometry=e['route_geometry']) for e in raw['episodes']]
    checkpoint()
    return backend_result(inp,raw)


def baseline_arm(raw):
    """Recover the exact primary arm from a composite result without its twin."""
    pair=raw['paired_ablation'];value={k:v for k,v in raw.items() if k not in ('paired_ablation','boundary','implementation','cost_observation_scope','unobserved_work_possible','numerical_confirmation')}
    value.update(cost=pair['baseline_cost'],timings_s=pair['baseline_timings_s'],
        trace_files=pair['baseline_trace_files'],model_builds=1,status=pair['baseline_status'])
    if pair.get('baseline_reason') is None:value.pop('reason',None)
    else:value['reason']=pair['baseline_reason']
    return value


def paired_raw(first,second,folder,requested_tendons,elapsed,*,interrupted=False):
    """Assemble measured arms, including durable partials; never execute here."""
    pair=dict(status='incomplete' if interrupted else 'not_executed_baseline_invalid' if second is None else
        'completed' if first['status']=='completed' and second['status']=='completed' else 'incomplete',
        requested_tendons=list(requested_tendons),baseline_cost=first['cost'],baseline_timings_s=first['timings_s'],
        baseline_trace_files=first['trace_files'],baseline_status=first['status'],baseline_reason=first.get('reason'))
    arms=[('baseline',first)]+([('ablation',second)] if second else [])
    if second is not None:pair['ablation']=second
    for arm,value in arms:
        pair.setdefault('arm_receipts',{})[arm]=dict(version='passive_native_arm_receipt_v2',
            parent_execution_id=Path(folder).name,execution_id=Path(folder).name+'/'+arm,execution_status=value['status'],
            raw_identity=digest(value),physical_binding=value.get('physical_binding'),intervention=value.get('intervention'),
            cost=value.get('cost'),elapsed_s=value.get('timings_s',{}).get('total'),
            qualified_states={e['load_condition']:e.get('qualified_state',{}).get('state_identity') for e in value.get('episodes',[])},
            scope='One fresh native model/data execution owned by the enclosing Worker reservation; no separate autonomous Study.')
    complete=pair['status']=='completed'
    return dict(**{k:v for k,v in first.items() if k not in ('status','model_builds','cost','timings_s','trace_files')},
        status='completed' if complete else 'incomplete' if interrupted or second is not None else first['status'],
        paired_ablation=pair,model_builds=sum(v.get('model_builds',0) for _,v in arms),
        cost={key:sum(v['cost'].get(key,0) for _,v in arms) for key in set().union(*(v['cost'] for _,v in arms))},
        timings_s=dict(total=elapsed,**{arm:v.get('timings_s',{}).get('total',0.) for arm,v in arms}),
        trace_files=[dict(v,path=arm+'/'+v['path']) for arm,value in arms for v in value.get('trace_files',[])],
        cost_observation_scope='last_durable_observed_lower_bounds' if interrupted else 'complete_observed_native_counts',
        unobserved_work_possible=interrupted)


def execute_pair(inp,folder,disabled_limits,*,initial_state=None,initial_state_result=None,execution_checks='full',execution_profile=None,baseline=None,ablation=None):
    """Two fresh native executions in one contained, fully accounted Worker.

    Each arm owns a complete raw record and a separate immutable execution
    receipt; the existing parent reservation owns the aggregate physical cost.
    """
    names=[t['entity'] for t in physics_for(inp)['tendons']]
    if not disabled_limits or len(set(disabled_limits))!=len(disabled_limits) or any(name not in names for name in disabled_limits):
        raise ValueError('EXACT_UNIQUE_PASSIVE_LIMIT_NAMES_REQUIRED')
    folder=Path(folder);started=time.perf_counter()
    checks=dict(execution_checks=execution_checks) if execution_checks!='full' else {}
    if execution_profile is not None:checks['execution_profile']=execution_profile
    from extensions.reference.passive_program import execution_identity
    def reused_arm(saved,intervention):
        expected=execution_identity(plain(inp),profile=execution_profile,execution_checks=execution_checks,initial_state=initial_state,intervention=intervention)
        if saved['raw'].get('execution_identity')!=expected or saved['raw'].get('status')!='completed' or not saved.get('source'):raise ValueError('EXACT_MATCHED_ARM_RESULT_REQUIRED')
        if saved['raw'].get('trace_files') and not saved.get('execution_directory'):raise ValueError('REUSED_ARM_TRACE_SOURCE_REQUIRED')
        raw=deepcopy(saved['raw'])
        for trace in raw.get('trace_files',[]):trace['path']=str(Path(saved['execution_directory'])/trace['path'])
        return raw
    first=reused_arm(baseline,()) if baseline is not None else execute(inp,folder/'baseline',initial_state=initial_state,initial_state_result=initial_state_result,**checks).data.data
    combined=paired_raw(first,None,folder,disabled_limits,time.perf_counter()-started,interrupted=True)
    atomic_json(folder/'passive_progress.json',combined)
    if ablation is not None and ([e['load_condition'] for e in first['episodes']]!=[e['load_condition'] for e in ablation['raw']['episodes']] or
            any(a.get('integration_initial')!=b.get('integration_initial') or a.get('qualified_state')!=b.get('qualified_state')
                for a,b in zip(first['episodes'],ablation['raw']['episodes']))):ablation=None
    try:
        second=reused_arm(ablation,disabled_limits) if ablation is not None else execute(inp,folder/'ablation',disabled_limits=disabled_limits,initial_state=initial_state,
            initial_state_result=initial_state_result,common_equilibrium=first.get('unloaded_equilibrium'),**checks).data.data
    except Exception as exc:
        from tools.state_io import read
        path=folder/'ablation/passive_progress.json'
        second=read(path) if path.exists() else dict(status='incomplete',reason=str(exc),cost={})
        second.update(status='incomplete',reason=str(exc))
    combined=paired_raw(first,second,folder,disabled_limits,time.perf_counter()-started,interrupted=second.get('physical_binding') is None)
    for name,saved,arm in [('baseline',baseline,first),('ablation',ablation,second)]:
        if saved is None:continue
        combined['paired_ablation'][name+'_reuse']={k:v for k,v in saved.items() if k!='raw'}
        receipt=combined['paired_ablation']['arm_receipts'][name]
        receipt.update(source=saved['source'],execution_id=saved['source']['reference']['artifact_id']+saved['source']['pointer'],
            actual_new_cost=saved['actual_new_cost'],scope='Existing exact native arm Result; no fresh execution.')
        combined['cost']={k:v-arm['cost'].get(k,0) for k,v in combined['cost'].items()}
        combined['model_builds']-=arm.get('model_builds',0)
        combined['timings_s'][name]=0.
    if baseline is not None or ablation is not None:
        combined['trace_files']=[dict(v,path=v['path'] if saved is not None else name+'/'+v['path'])
            for name,value,saved in [('baseline',first,baseline),('ablation',second,ablation)] for v in value.get('trace_files',[])]
    atomic_json(folder/'passive_progress.json',combined)
    return backend_result(inp,combined)


def replay_saved_traces(inp,raw,folder):
    """Read every saved row and reconstruct measured positions without stepping."""
    goal,_,problem=task_definition(inp.task,__import__('tools.platform_registry',fromlist=['registry']).registry())
    scene=assemble_physical(inp,physics_for(inp));scene['control']=dict(tension_execution_mode='passive_fixed_payout_v1',
        solreflimit=goal.solreflimit,solimplimit=goal.solimplimit)
    native=PassiveModel(physics_for(inp),plain(problem),scene=scene);m=native.model;data=mujoco.MjData(m)
    native.design_components=inp.robot.structure.data['components']
    capacities=np.array([t['force_limit_n'] for t in native.physics['tendons']])
    rows_checked=0;forwards=0;route_checks=0;maximum=0.;dt=inp.task.timing.timestep_s
    for trace,episode in zip(raw['trace_files'],raw['episodes']):
        path=Path(folder)/trace['path']
        with path.open('rb') as stream:identity=hashlib.file_digest(stream,'sha256').hexdigest()
        if identity!=trace['sha256'] or path.stat().st_size!=trace['bytes']:raise ValueError('SAVED_TRACE_BYTES_MISMATCH')
        expected={round(r['time_s']/dt):r for r in episode['samples']+episode['qualification_samples']}
        with path.open(newline='') as stream:
            count=0
            for count,row in enumerate(csv.DictReader(stream),1):
                t=float(row['time_s']);q=np.array([float(row['qpos_'+str(i)]) for i in range(m.nq)])
                v=np.array([float(row['qvel_'+str(i)]) for i in range(m.nv)])
                lengths=np.array([float(row['length_m_'+str(i)]) for i in range(m.ntendon)])
                tensions=np.array([float(row['tension_n_'+str(i)]) for i in range(m.ntendon)])
                gaps=np.array([float(row['length_residual_m_'+str(i)]) for i in range(m.ntendon)])
                force,phase=load_at(goal,native.load(episode['load_condition']),t)
                disabled=raw['intervention']['tendons'] if t>goal.programs[episode['load_condition']][0].end_s+1e-10 else []
                enabled=[i for i,name in enumerate(raw['tendon_order']) if name not in disabled]
                if (abs(t-count*dt)>1e-8 or not np.isfinite(np.r_[q,v]).all()
                        or row['stage']!=phase or abs(float(row['engine_time_s'])-t)>1e-8
                        or not np.allclose([float(row['force_'+a+'_n']) for a in 'xyz'],force,rtol=0,atol=1e-12)
                        or not np.isfinite(np.r_[lengths,tensions,gaps]).all()
                        or not np.allclose(lengths-native.payout,gaps,rtol=0,atol=1e-12)
                        or min(tensions)<-goal.multiplier_sign_tolerance_n or np.max(tensions/capacities)>1.
                        or max([0.]+[gaps[i] for i in enabled])>goal.length_tolerance_m
                        or int(row['contacts']) or int(row['warnings'])
                        or float(row['constraint_direction_error_m_rad'])>goal.constraint_direction_tolerance
                        or float(row['force_map_error_nm'])>goal.force_map_tolerance_nm):
                    raise ValueError('SAVED_TRACE_STEP_CHECK_FAILED')
                mujoco.mj_resetData(m,data);data.qpos[:]=q;data.qvel[:]=v;mujoco.mj_forward(m,data);forwards+=1
                from .route_validation import validate_routes
                route=validate_routes(native,[q],data=data);route_checks+=route['segment_body_checks']
                if route['issues']:raise ValueError('SAVED_STATE_ILLEGAL_ROUTE')
                if count not in expected:continue
                recorded=expected[count]
                if not np.allclose(q,recorded['qpos_rad'],rtol=0,atol=1e-14) or not np.allclose(v,recorded['qvel_rad_s'],rtol=0,atol=1e-14):
                    raise ValueError('SAVED_TRACE_STATE_MISMATCH')
                positions=np.array([native.point(data,b)[0] for b in native.points])
                measured=np.array(recorded['material_positions_m']+[recorded['tip_m']])
                maximum=max(maximum,float(np.max(np.linalg.norm(positions-measured,axis=1))))
            if count!=trace['physics_steps']:raise ValueError('SAVED_TRACE_ROW_COVERAGE_MISMATCH')
            rows_checked+=count
    if maximum>1e-10:raise ValueError('SAVED_STATE_POSITION_RECONSTRUCTION_MISMATCH')
    return dict(status='verified',integrations=0,raw_identity=digest(raw),traces=raw['trace_files'],
        rows_checked=rows_checked,route_checked_poses=forwards,maximum_position_difference_m=maximum,
        cost=dict(model_builds=1,native_forward_calls=forwards,route_checked_poses=forwards,route_segment_body_checks=route_checks,
            material_point_jacobian_calls=native.cost['material_point_jacobian_calls']))


def execute_confirmation(inp,folder,source,source_result,source_execution_id):
    """Complete numerical scope using the ordinary executor and recorded CSVs."""
    from extensions.reference.passive_program import confirmation_task
    from extensions.reference.passive_evaluation_v2 import stiffness,inspect
    from extensions.reference.contracts import PassiveResponseEvaluationV2
    ev=PassiveResponseEvaluationV2.model_validate(inp.task.evaluator.parameters.data)
    folder=Path(folder);started=time.perf_counter();names=source['paired_ablation']['requested_tendons']
    raw=execute_pair(inp,folder/'independent',names).data.data
    # Preserve the signed pair before adding the enclosing validation fields.
    pair=deepcopy(raw);base=baseline_arm(pair)
    raw['status']='incomplete'
    certificate=dict(version='passive_numerical_confirmation_v1',source_result=plain(source_result),
        source_execution_id=source_execution_id,independent_execution_id=folder.name+'/independent',
        source_raw_identity=digest(source),source_binding=source['physical_binding'],executions={},saved_state_replay={},
        source_displacements_m={s.load_condition:stiffness(inp.task,baseline_arm(source),s)['displacement_m'] for s in ev.progressive_stiffness})
    raw['numerical_confirmation']=certificate
    traces=[dict(t,path='independent/'+t['path']) for t in pair['trace_files']]
    costs=[pair['cost']]
    def checkpoint():
        raw['cost']={k:sum(c.get(k,0) for c in costs) for k in set().union(*(c.keys() for c in costs))}
        raw['trace_files']=traces;raw['timings_s']['total']=time.perf_counter()-started
        atomic_json(folder/'passive_progress.json',raw)
    checkpoint()
    if inspect(inp.task,base)[0]!='valid' or 'ablation' not in pair['paired_ablation']:return backend_result(inp,raw)
    for variant in ev.numerical_confirmation.variants:
        effective=confirmation_task(inp.task,variant);varied=inp.model_copy(update=dict(task=effective))
        value=execute(varied,folder/variant,common_equilibrium=base['unloaded_equilibrium']).data.data
        certificate['executions'][variant]=dict(task=plain(effective),raw=value,raw_identity=digest(value),execution_id=folder.name+'/'+variant)
        costs.append(value['cost']);traces.extend(dict(t,path=variant+'/'+t['path']) for t in value['trace_files']);checkpoint()
        if inspect(effective,value)[0]!='valid':return backend_result(inp,raw)
    arms=dict(baseline=(inp,base,folder/'independent/baseline'),
        ablation=(inp,pair['paired_ablation']['ablation'],folder/'independent/ablation'),
        **{v:(inp.model_copy(update=dict(task=confirmation_task(inp.task,v))),certificate['executions'][v]['raw'],folder/v)
            for v in ev.numerical_confirmation.variants})
    for name,(effective,value,directory) in arms.items():
        replay=replay_saved_traces(effective,value,directory);certificate['saved_state_replay'][name]=replay
        costs.append(replay['cost']);checkpoint()
    raw['status']=pair['status'];checkpoint()
    return backend_result(inp,raw)


class NoActiveControl:
    """Registry execution declaration; intentionally has no command method."""
    def __init__(self,*args):pass
    def close(self):pass


class PassiveBackend:
    @classmethod
    def check(cls,inp,parameters,control):
        from tools.platform_registry import registry
        task_definition(inp.task,registry())
        if (inp.policy.controller.extension_id!='controller.no_active_control' or inp.robot.channels or
                inp.robot.structure.data.get('actuators') or not inp.robot.structure.data.get('fixed_payout_lengths_m')):
            raise ValueError('PASSIVE_NO_ACTIVE_CONTROL_ASSEMBLY_REQUIRED')
        assemble_physical(inp,physics_for(inp))
    def compile(self,inp,reg):self.inp=inp
    def initialize(self,initial,controller):
        if initial!=self.inp.task.initializer.parameters:raise ValueError('PASSIVE_INITIAL_STATE_MISMATCH')
    def run(self,folder,timeout_s):
        self.result=execute(self.inp,folder)
        atomic_json(Path(folder)/'result.json',plain(self.result))
        return self.result
    def export(self):return self.result
    def close(self):pass
