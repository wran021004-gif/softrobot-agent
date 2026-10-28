"""Existing platform lifecycle and evidence envelopes, independent engine execution."""
import gzip
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from schemas.platform import BackendResult
from tools.state_io import atomic_json
from .compiler import resolve
from .scene import assemble
from .contracts import Initial, Data
from .signals import export
from .execution import resolve_execution


def check_rigid_tool_definition(inp):
    """Bind the task-owned inertial load to an actual rigid design component."""
    expected=inp.task.goal.data['rigid_tool'];parts=inp.robot.structure.data['components']
    tool=next((c for c in parts if c['id']==expected['body']),None);tip=inp.robot.structure.data['tip']
    if (tool is None or tool['kind']!='payload' or tip['part']!=expected['body'] or tip['s']!=0
            or tip['position_m']!=expected['tip_position_local_m'] or tip['quaternion_wxyz']!=[1.,0.,0.,0.]
            or any(tool[k]!=expected[k] for k in ('mass_kg','com_local_m','inertia_com_local_kg_m2'))
            or inp.task.environment.data.get('external_forces')):
        raise ValueError('FROZEN_RIGID_TOOL_DEFINITION_MISMATCH_OR_EXTERNAL_FORCE_SUBSTITUTION')
    return expected


def check_rigid_tool_model(inp,model):
    """Inspect compiled MuJoCo inertia; a COM force cannot satisfy this binding."""
    import mujoco
    expected=check_rigid_tool_definition(inp);bid=model.body(expected['body']).id;site=model.site('tip_site').id
    rotation=np.empty(9);mujoco.mju_quat2Mat(rotation,model.body_iquat[bid]);rotation=rotation.reshape(3,3)
    tensor=rotation@np.diag(model.body_inertia[bid])@rotation.T
    matched=bool(model.body_jntnum[bid]==0 and model.site_bodyid[site]==bid
        and abs(model.body_mass[bid]-expected['mass_kg'])<=1e-12
        and np.allclose(model.body_ipos[bid],expected['com_local_m'],rtol=0,atol=1e-12)
        and np.allclose(tensor,expected['inertia_com_local_kg_m2'],rtol=0,atol=1e-12)
        and np.allclose(model.site_pos[site],expected['tip_position_local_m'],rtol=0,atol=1e-12))
    if not matched:raise ValueError('COMPILED_MUJOCO_RIGID_TOOL_BINDING_MISMATCH')
    return dict(matched=True,body=expected['body'],mass_kg=float(model.body_mass[bid]),com_local_m=model.body_ipos[bid].tolist(),
        inertia_com_local_kg_m2=tensor.tolist(),tip_position_local_m=model.site_pos[site].tolist(),
        semantics='Fixed rigid inertial tool, including gravity, translational/rotational inertia and coupling; no external-force approximation')


def save_nmpc_progress(folder, observations):
    """Persist shared graph definitions once and tolerate brief Windows readers."""
    record=observations[-1].get('complete_update_record',{})
    definition=record.get('resolved_problem')
    if definition is not None:
        # Keep the basename no longer than nmpc_updates.json: the established
        # Windows execution directory already approaches the legacy path limit.
        name='p_'+record['model_identity'][:10]+'.json';path=folder/name
        if not path.exists():atomic_json(path,definition)
        record['resolved_problem_reference']=dict(filename=name,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            definition='shared objective/constraints/model; override variables and initial_guess with this update record')
        del record['resolved_problem']
    path=folder/'nmpc_updates.json'
    try:atomic_json(path,observations)
    except PermissionError as exc:
        if getattr(exc,'winerror',None) not in (5,32,33):raise
        # Numerical work has already completed. Retry only the existing temporary
        # file's replacement, not the controller command or JSON serialization.
        deadline=time.perf_counter()+2.
        while True:
            time.sleep(.05)
            try:path.with_suffix(path.suffix+'.tmp').replace(path);break
            except PermissionError:
                if time.perf_counter()>=deadline:raise


def physics_for(inp):
    if inp.robot.structure.contract=='family.design':
        discretization = inp.policy.discretization.data if inp.policy.discretization is not None else None
        return resolve(inp.robot.structure.data,discretization)
    raise ValueError('UNSUPPORTED_FAMILY_DESIGN_CONTRACT')


def _mujoco_state_failed(data, previous_time):
    """MuJoCo can reset invalid velocities to finite values during mj_step."""
    import mujoco
    warnings=(mujoco.mjtWarning.mjWARN_BADQPOS,mujoco.mjtWarning.mjWARN_BADQVEL,mujoco.mjtWarning.mjWARN_BADQACC)
    return (data.time<=previous_time or any(data.warning[k].number for k in warnings)
        or not all(np.isfinite(v).all() for v in (data.qpos,data.qvel,data.qacc)))


def _bind_mujoco_forces(model, scene):
    """Resolve the validated TimedForce schema to named engine bodies and ticks."""
    dt=model.opt.timestep
    return tuple((model.body(f['entity']).id,round(f['start_s']/dt),round(f['end_s']/dt),
        np.asarray(f['force_n'],dtype=float)) for f in scene['forces'])


def _apply_mujoco_forces(model, data, forces):
    """World N at body COM, [start,end), held through one actual engine step.

    Integer ticks avoid accumulated engine-time rounding at grid boundaries.
    xfrc_applied[:3] is force; [3:] is a zero COM couple, not a tip load.
    """
    tick=round(data.time/model.opt.timestep)
    data.xfrc_applied[:]=0
    for bid,start,end,force in forces:
        if start<=tick<end:data.xfrc_applied[bid,:3]+=force


class MujocoFailureSnapshot:
    """One reusable pre-call buffer; serialize only on a catchable engine failure."""
    def __init__(self,model,identity,folder=None):
        import mujoco
        self.model=model;self.identity=identity;self.completed_steps=0;self.folder=folder
        self.attempted_steps=0;self.forward_evaluations=0
        self.spec=mujoco.mjtState.mjSTATE_INTEGRATION
        self.buffer=np.empty(mujoco.mj_stateSize(model,self.spec))

    def call(self,data,operation,location):
        import mujoco
        m=self.model
        mujoco.mj_getState(m,data,self.buffer,self.spec)
        before=dict(time_s=float(data.time),ncon=int(data.ncon),nefc=int(data.nefc),
            qpos=data.qpos.copy(),qvel=data.qvel.copy(),
            ctrl=data.ctrl.copy(),actuator_force=data.actuator_force.copy(),
            warnings=[dict(number=int(w.number),lastinfo=int(w.lastinfo)) for w in data.warning])
        if operation is mujoco.mj_step:self.attempted_steps+=1
        try:
            operation(m,data)
            if operation is mujoco.mj_forward:self.forward_evaluations+=1
            if operation is mujoco.mj_step:
                if _mujoco_state_failed(data,before['time_s']):raise ValueError('MUJOCO_NUMERICAL_FAILURE')
                self.completed_steps+=1
        except Exception as exc:
            # Last pre-call state is known; the failing native call's internal
            # progress and partially mutated state are deliberately not asserted.
            exc.mujoco_diagnostic=dict(version='mujoco_failure_snapshot_v1',model_identity=self.identity,
                mujoco_version=mujoco.__version__,
                error_location=location,operation=operation.__name__,reason=str(exc),
                state_spec=int(self.spec),integration_state=self.buffer.tolist(),
                time_before_call_s=before['time_s'],qpos=before['qpos'].tolist(),qvel=before['qvel'].tolist(),
                control_before_call=before['ctrl'].tolist(),last_evaluated_actuator_force=before['actuator_force'].tolist(),
                control_units='Frozen model actuator units; ideal tendon tension uses N',
                constraints_before_call=dict(ncon=before['ncon'],nefc=before['nefc']),warnings_before_call=before['warnings'],
                warnings_after_call=[dict(number=int(w.number),lastinfo=int(w.lastinfo)) for w in data.warning],
                model_options=dict(timestep_s=float(m.opt.timestep),integrator=int(m.opt.integrator),
                    solver=int(m.opt.solver),jacobian=int(m.opt.jacobian),iterations=int(m.opt.iterations)),
                confirmed_completed_steps=self.completed_steps,attempted_steps=self.attempted_steps,
                forward_evaluations=self.forward_evaluations,failed_call_internal_steps='unknown',
                missing=['Exact native failure-instant state','Partial internal solver progress'],
                scope='Engineering diagnosis only; no complete trajectory, optimizer update or infeasibility inference')
            if self.folder is not None:atomic_json(Path(self.folder)/'numerical_failure.json',exc.mujoco_diagnostic)
            raise


def playback_tensions(inp, physics, scene, commands, folder, *, step_observer=None, xml_path=None):
    """Run a fixed SI tension sequence through the existing candidate MuJoCo scene."""
    import mujoco
    from .mjcf import compile_xml
    from tools.platform_registry import registry

    started=time.perf_counter()
    if scene['control']['tension_execution_mode']!='ideal_tension':
        raise ValueError('PHYSICAL_PLAYBACK_REQUIRES_IDEAL_TENSION')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    xml=(Path(xml_path) if xml_path is not None else
        compile_xml(physics,scene,registry().parse(inp.policy.backend.parameters),folder/'robot.xml'))
    model=mujoco.MjModel.from_xml_path(str(xml));data=mujoco.MjData(model)
    tool_binding=check_rigid_tool_model(inp,model) if inp.task.family=='task.oriented_tracking' else None
    if tool_binding is not None:atomic_json(folder/'rigid_tool_binding.json',tool_binding)
    forces=_bind_mujoco_forces(model,scene)
    safety=MujocoFailureSnapshot(model,physics['identity'],folder)
    joints=[model.joint(name).id for name in physics['dofs']]
    qi=model.jnt_qposadr[joints];vi=model.jnt_dofadr[joints]
    names=[t['entity'] for t in physics['tendons']]
    aids=[model.actuator(name+'_direct_tension').id for name in names]
    tids=[model.tendon(name).id for name in names]
    if (model.actuator_trnid[aids,0].tolist()!=tids or
        not np.all(model.actuator_trntype[aids]==mujoco.mjtTrn.mjTRN_TENDON) or
        not np.all(model.actuator_gainprm[aids,0]==-1) or
        not np.all(model.actuator_gear[aids,0]==1) or
        not np.all(model.actuator_dyntype[aids]==mujoco.mjtDyn.mjDYN_NONE)):
        raise ValueError('PHYSICAL_PLAYBACK_REQUIRES_IDEAL_DIRECT_TENSION')
    limits=model.actuator_ctrlrange[aids]
    u=np.asarray(commands,dtype=float)
    intervals=round(scene['duration_s']/scene['control_period_s'])
    substeps=round(scene['control_period_s']/model.opt.timestep)
    if (u.shape!=(intervals,len(aids)) or not np.isfinite(u).all() or
        np.any(u<limits[:,0]) or np.any(u>limits[:,1]) or
        substeps<1 or abs(intervals*scene['control_period_s']-scene['duration_s'])>1e-12 or
        abs(substeps*model.opt.timestep-scene['control_period_s'])>1e-12):
        raise ValueError('PHYSICAL_PLAYBACK_GRID_OR_TENSION_MISMATCH')
    mujoco.mj_resetData(model,data)
    data.qpos[qi]=scene['qpos_rad'];data.qvel[vi]=scene['qvel_rad_s']
    tip=model.site('tip_site').id
    jac=np.zeros((3,model.nv))
    def sample(k,requested,actual):
        _apply_mujoco_forces(model,data,forces)
        safety.call(data,mujoco.mj_forward,'playback.sample')
        mujoco.mj_jacSite(model,data,jac,None,tip)
        position=data.site_xpos[tip].copy();velocity=jac@data.qvel
        return dict(control_step=k,time_s=k*scene['control_period_s'],engine_time_s=float(data.time),
            **(dict(tip_tool_axis_world=(data.site_xmat[tip].reshape(3,3)@np.asarray(inp.task.goal.data['axis_local'])).tolist())
                if inp.task.family in ('task.position_tool_axis','task.oriented_tracking') else {}),
            tip_m=position.tolist(),tip_velocity_m_s=velocity.tolist(),
            speed_m_s=float(np.linalg.norm(velocity)),qpos_rad=data.qpos[qi].tolist(),qvel_rad_s=data.qvel[vi].tolist(),
            requested_tension_n=None if requested is None else requested.tolist(),actual_tension_n=actual.tolist())
    rows=[sample(0,None,np.zeros(len(aids)))];atomic_json(folder/'samples.json',rows)
    # Observers receive a detached copy, including integration state and caches.
    # Forward operations there cannot alter warmstarts or the executing MjData.
    def observe(step,interval):
        if step_observer is not None:
            detached=mujoco.MjData(model)
            mujoco.mj_copyData(detached,model,data)
            step_observer(model,detached,step,interval)
    observe(0,-1)
    steps=0;failure=None;maximum_contacts=0;contact_steps=0;first_contact_time=None
    for k,command in enumerate(u):
        data.ctrl[aids]=command
        _apply_mujoco_forces(model,data,forces)
        safety.call(data,mujoco.mj_forward,'playback.apply')
        actual=-data.actuator_force[aids].copy()
        if not np.allclose(actual,command,rtol=0,atol=1e-9):
            failure=dict(interval=k,reason='DIRECT_TENSION_NOT_APPLIED',requested=command.tolist(),actual=actual.tolist());break
        for j in range(substeps):
            _apply_mujoco_forces(model,data,forces)
            previous=float(data.time);safety.call(data,mujoco.mj_step,'playback.step');steps+=1
            observe(steps,k)
            if inp.task.family=='task.oriented_tracking':
                maximum_contacts=max(maximum_contacts,int(data.ncon))
                if data.ncon:
                    contact_steps+=1
                    if first_contact_time is None:
                        first_contact_time=float(data.time)
                        atomic_json(folder/'first_environment_contact.json',dict(contact_free=False,first_contact_time_s=first_contact_time,
                            observed_contacts=int(data.ncon),checked_physics_steps=steps,scope='Partial refutation of contact-free execution, not a complete trajectory'))
            if _mujoco_state_failed(data,previous):
                failure=dict(interval=k,substep=j+1,reason='MUJOCO_NUMERICAL_FAILURE',time_s=float(data.time));break
        if failure:break
        rows.append(sample(k+1,command,-data.actuator_force[aids].copy()))
        atomic_json(folder/'samples.json',rows)
    return dict(status='completed' if failure is None and len(rows)==intervals+1 else 'incomplete',
        **(dict(rigid_tool_binding=tool_binding,environment_contact=dict(maximum_contacts=maximum_contacts,
            contact_steps=contact_steps,first_contact_time_s=first_contact_time,checked_physics_steps=steps,
            contact_free=maximum_contacts==0)) if tool_binding is not None else {}),
        failure=failure,samples=rows,physics_steps=steps,command_intervals=len(rows)-1,
        physics_step_attempts=safety.attempted_steps,
        cost=dict(model_builds=1,rollouts=1,physics_steps=steps,physics_step_attempts=safety.attempted_steps,
            forward_evaluations=safety.forward_evaluations,kernel_wall_s=time.perf_counter()-started),
        external_force_execution=dict(forces=scene['forces'],semantics=scene['semantics'].get('external_forces')),
        model_identity=physics['identity'],scene_identity=scene['identity'],
        xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest(),tendon_order=names,
        physics_timestep_s=float(model.opt.timestep),integrator=int(model.opt.integrator),
        physical_backend='backend.family_mujoco',tension_execution_mode='ideal_tension')


class SerialBackend:
    backend_id='backend.serial_base'
    model='matlab_serial_bending_v1'
    tension_execution_modes=('actuator_realistic',)

    @classmethod
    def check(cls,inp,parameters,control):
        if getattr(parameters,'model',cls.model)!=cls.model: raise ValueError('BACKEND_MODEL_IDENTITY_MISMATCH')
        if cls.model=='mujoco_serial_bending_v1' and hasattr(parameters,'max_step_s'):
            from .contracts import Parameters
            defaults=Parameters()
            if any(getattr(parameters,k)!=getattr(defaults,k) for k in ('max_step_s','rtol','atol','contact_stiffness_n_m','contact_damping_n_s_m')):
                raise ValueError('MATLAB_ONLY_SOLVER_PARAMETERS: MuJoCo uses scene timestep and its recorded XML contact settings')
        if inp.task.initializer.extension_id!='initialize.family': raise ValueError('NAMED_FAMILY_INITIALIZER_REQUIRED')
        controllers=['controller.gvs_nmpc','controller.sorosim_matlab_nmpc']
        if inp.policy.controller.extension_id not in controllers: raise ValueError('FAMILY_CONTROLLER_REQUIRED')
        from tools.platform_registry import registry
        resolve_execution(inp,registry())
        p=physics_for(inp); scene=assemble(inp,p)
        mode=scene['control'].get('tension_execution_mode','actuator_realistic')
        if mode not in cls.tension_execution_modes:
            raise ValueError('TENDON_TENSION_EXECUTION_UNSUPPORTED: '+mode+' by '+cls.backend_id)

    def compile(self,inp,reg):
        start=time.perf_counter(); self.inp=inp
        self.config=reg.parse(inp.policy.backend.parameters); self.execution=resolve_execution(inp,reg); self.physics=physics_for(inp)
        self.scene=assemble(inp,self.physics)
        mode=self.scene['control'].get('tension_execution_mode','actuator_realistic')
        if mode not in self.tension_execution_modes:
            raise ValueError('TENDON_TENSION_EXECUTION_UNSUPPORTED: '+mode+' by '+self.backend_id)
        self.timings={'prepare_compile':time.perf_counter()-start}

    def initialize(self,initial,controller):
        if Initial.model_validate(initial.data).model_dump(mode='json')!=self.scene['initial']: raise ValueError('INITIAL_STATE_MISMATCH')
        self.initial=initial; self.controller=controller
        controller.configure(self.physics,self.scene['control'])

    def run(self,folder,timeout_s):
        self.folder=folder; folder.mkdir(parents=True,exist_ok=True)
        for name,value in [('robot_description',self.inp.robot.structure.model_dump(mode='json')),('resolved_physics',self.physics),
                           ('model_discretization',self.physics['discretization']),('experiment_scene',self.scene),
                           ('experiment_spec',self.scene['experiment_spec']),('dynamics_execution',self.execution),
                           ('control_spec',self.scene['control']),('solver_configuration',self.config.model_dump(mode='json'))]:
            atomic_json(folder/(name+'.json'),value)
        start=time.perf_counter()
        rows,observations,complete,reason,steps=self.solve(timeout_s)
        self.timings['backend_call']=time.perf_counter()-start
        with gzip.open(folder/'trajectory.json.gz','wt',encoding='utf8') as stream: json.dump(rows,stream,allow_nan=False)
        atomic_json(folder/'controller_observations.json',observations)
        if getattr(self.controller,'control_snapshots',None):
            atomic_json(folder/'control_snapshots.json',self.controller.control_snapshots)
        command_fields=('requested_tension_n','desired_tension_n','predicted_tension_n','tension_tracking_error_n',
            'force_limit_saturated','actuator_saturated','tension_command_unrealizable')
        atomic_json(folder/'actual_commands.json',[dict(time_s=r['solver_time_s'],
            **({'actuator_command':r['actuator_command'],'target_lengths_m':r['command_m']}
               if 'actuator_command' in r else {}),
            **{key:r[key] for key in command_fields if key in r}) for r in rows])
        from schemas.platform import Payload
        data=Data(physics_identity=self.physics['identity'],scene_identity=self.scene['identity'],timings_s=self.timings,
            numerical_steps=steps,reason=reason,applicability=self.physics['applicability'],exported_files=sorted(p.name for p in folder.iterdir()),
            execution_plan=self.execution,control_identity=self.scene['control']['identity'])
        execution_mode=self.scene['control'].get('tension_execution_mode','actuator_realistic')
        execution_limitation=('Direct bounded MuJoCo tendon force; tendon lengths are measured responses, not a real-robot constitutive law.'
            if execution_mode=='ideal_tension' else
            'Ideal length servos, tension only, slack gives zero tension; no motor inertia.')
        self.result=BackendResult(solver_status='completed' if complete else 'failed',backend_id=self.backend_id,model_id=self.execution['implementation_model_id'],
            signals=export(rows,self.physics,self.scene['control']['mode'] in ('gvs_nmpc','sorosim_nmpc'),
                self.scene['control'].get('tension_execution_mode','actuator_realistic')),
            data=Payload(contract='family.backend_data',data=data.model_dump(mode='json')),
            limitations=[self.physics['applicability']['collision'],execution_limitation,
                'MATLAB lowest-envelope-vertex penalty and MuJoCo convex contact differ; no contact accuracy claim.'],initial_state=self.initial,seed=self.inp.seed)
        atomic_json(folder/'result.json',self.result.model_dump(mode='json')); return self.result

    def shared_input(self,timeout_s):
        c=dict(self.scene['control']['effective_parameters'])
        commands=self.scene['control']['reference'].get('commands',{})
        c['command_vector']=[commands.get(a['id'],0.) for a in self.physics['actuators']]
        return dict(physics=self.physics,scene=self.scene,config=self.config.model_dump(mode='json'),control=c,timeout_s=timeout_s)


    def export(self): return self.result

    def close(self):
        close=getattr(getattr(self,'controller',None),'close',None)
        if close is not None: close()


class MujocoBackend(SerialBackend):
    backend_id='backend.family_mujoco'
    model='mujoco_serial_bending_v1'
    tension_execution_modes=('ideal_tension','actuator_realistic')

    def solve(self,timeout_s):
        import mujoco
        from .mjcf import compile_xml
        p,s=self.physics,self.scene
        start=time.perf_counter(); path=self.folder/'robot.xml'
        compile_xml(p,s,self.config,path); model=mujoco.MjModel.from_xml_path(str(path))
        data=mujoco.MjData(model); pose=mujoco.MjData(model)
        safety=MujocoFailureSnapshot(model,p['identity'],self.folder)
        forces=_bind_mujoco_forces(model,s)
        bids=[model.body(b['entity']).id for b in p['parts']]
        # Tree serialization can reorder siblings; never assume array order.
        jids=[model.joint(j).id for j in p['dofs']]; qi=model.jnt_qposadr[jids]; vi=model.jnt_dofadr[jids]
        tids=[model.tendon(t['entity']).id for t in p['tendons']]
        execution_mode=s['control'].get('tension_execution_mode','actuator_realistic')
        suffix='_direct_tension' if execution_mode=='ideal_tension' else '_length_servo'
        aids=[model.actuator(t['entity']+suffix).id for t in p['tendons']]
        data.qpos[qi]=s['qpos_rad']; data.qvel[vi]=s['qvel_rad_s']; safety.call(data,mujoco.mj_forward,'backend.initialize')
        actuator_ids=({'direct_tension_ids':aids} if execution_mode=='ideal_tension' else {'servo_ids':aids})
        atomic_json(self.folder/'compiled_physics.json',dict(physics_identity=p['identity'],body_ids=bids,qpos_indices=qi.tolist(),qvel_indices=vi.tolist(),
            tendon_ids=tids,**actuator_ids,tension_execution_mode=execution_mode,
            actuator_entities=[a['id'] for a in p['actuators']] if execution_mode=='actuator_realistic' else [],
            transmission=p['transmission'] if execution_mode=='actuator_realistic' else None,
            mass_kg=model.body_mass[bids].tolist(),com_local_m=model.body_ipos[bids].tolist(),
            inertia_principal_kg_m2=model.body_inertia[bids].tolist(),inertia_quaternion_wxyz=model.body_iquat[bids].tolist(),
            stiffness_nm_rad=model.jnt_stiffness[jids].tolist(),damping_nm_s_rad=model.dof_damping[vi].tolist()))
        self.timings['engine_compile']=time.perf_counter()-start
        rows=[]; steps=0; start=time.perf_counter(); dt=s['control_period_s']; substeps=round(dt/s['timestep_s'])
        initial_lengths=data.ten_length[tids].copy(); previous_lengths=initial_lengths.copy()
        def current():
            safety.call(data,mujoco.mj_forward,'backend.sample')
            J=np.zeros((3,model.nv)); Jr=np.zeros_like(J); mujoco.mj_jacSite(model,data,J,Jr,model.site('tip_site').id)
            # Dense Jacobian from the engine's current explicit tendon routing.
            jac=np.zeros((model.ntendon,model.nv))
            if data.ten_J.size==model.ntendon*model.nv: jac[:]=data.ten_J.reshape(model.ntendon,model.nv)
            else:
                for k in range(model.ntendon):
                    layout=model if hasattr(model,'ten_J_rowadr') else data
                    adr=layout.ten_J_rowadr[k]; nnz=layout.ten_J_rownnz[k]
                    jac[k,layout.ten_J_colind[adr:adr+nnz]]=data.ten_J[adr:adr+nnz]
            return dict(tip=data.site_xpos[model.site('tip_site').id].copy(),Jtip=J[:,vi],lengths=data.ten_length[tids].copy(),Jlength=jac[tids][:,vi])
        complete=True; reason=None
        for step in range(round(s['duration_s']/dt)):
            limit=getattr(self,'engineering_control_update_limit',None)
            if limit is not None:
                if type(limit) is not int or not 1<=limit<=5:raise ValueError('BOUNDED_ENGINEERING_UPDATES_REQUIRED')
                if step>=limit:
                    complete=False;reason='ENGINEERING_CONTROL_UPDATE_LIMIT';break
            if timeout_s is not None and time.perf_counter()-start>timeout_s:
                complete=False
                reason='MUJOCO_SOLVER_TIMEOUT'
                break
            update_start=time.perf_counter()
            t=step*dt; g=current()
            if s['control']['mode'] in ('gvs_nmpc','sorosim_nmpc'):
                from .gvs_projection import project, PROJECTOR_ID
                projection=project(p,self.controller.resolved_basis,data.qpos[qi],data.qvel[vi],
                    convention=getattr(self.controller,'projector_id',PROJECTOR_ID))
                g['gvs_projection']=projection
                state_preparation_s=time.perf_counter()-update_start
                command=self.controller.command(t,g,np.asarray(projection['q_gvs']),np.asarray(projection['qdot_gvs']))
                if s['control']['mode'] in ('gvs_nmpc','sorosim_nmpc'):
                    elapsed=time.perf_counter()-update_start
                    timing=dict(controller_boundary_wall_s=self.controller.last['update_wall_s'],
                        state_preparation_s=state_preparation_s,update_wall_s=elapsed,
                        deadline_missed=elapsed>dt)
                    self.controller.last.update(timing)
                    self.controller.observations[-1].update(timing)
                    save_nmpc_progress(self.folder,self.controller.observations)
                    if self.controller.stop_requested:
                        complete=False;reason='NMPC_SUSTAINED_UNUSABLE_REPLANNING';break
            else:
                command=self.controller.command(t,g,data.qpos[qi].copy(),data.qvel[vi].copy())
            data.ctrl[aids]=command; _apply_mujoco_forces(model,data,forces); external=np.zeros(model.nv)
            for bid in {f[0] for f in forces}:
                if np.any(data.xfrc_applied[bid,:3]):
                    J=np.zeros((3,model.nv)); Jr=np.zeros_like(J); mujoco.mj_jacBodyCom(model,data,J,Jr,bid)
                    external+=J.T@data.xfrc_applied[bid,:3]
            safety.call(data,mujoco.mj_forward,'backend.apply')
            actual_tension=-data.actuator_force[aids]
            before=dict(solver_tendon_length_m=data.ten_length[tids].tolist(),tension_n=actual_tension.tolist(),
                solver_qfrc_actuator_nm=data.qfrc_actuator[vi].tolist(),solver_qfrc_passive_nm=data.qfrc_passive[vi].tolist(),external_torque_nm=external[vi].tolist())
            if execution_mode=='ideal_tension':
                tracking=(actual_tension-np.asarray(self.controller.last['desired_tension_n'])).tolist()
                self.controller.last['tension_tracking_error_n']=tracking
                self.controller.last['predicted_tension_n']=actual_tension.tolist()
                self.controller.observations[-1].update(tension_tracking_error_n=tracking,
                    predicted_tension_n=actual_tension.tolist(),actual_tension_n=actual_tension.tolist())
                from .control_evidence import PRE_STEP_OBSERVER
                observer = PRE_STEP_OBSERVER.get()
                if observer is not None:
                    capture_start = time.perf_counter()
                    observer(step, t, self.controller, g, g['Jtip'] @ data.qvel[vi], actual_tension)
                    capture_s = time.perf_counter() - capture_start
                    self.controller.last['prediction_seal_wall_s'] = capture_s
                    self.controller.observations[-1]['prediction_seal_wall_s'] = capture_s
                    self.controller.last['update_wall_s'] += capture_s
                    self.controller.last['deadline_missed'] = self.controller.last['update_wall_s'] > dt
                    self.controller.observations[-1].update(
                        update_wall_s=self.controller.last['update_wall_s'],
                        deadline_missed=self.controller.last['deadline_missed'])
            for _ in range(substeps):
                _apply_mujoco_forces(model,data,forces)
                previous_time=data.time
                safety.call(data,mujoco.mj_step,'backend.step'); steps+=1
                if _mujoco_state_failed(data,previous_time):
                    complete=False; reason='MUJOCO_NUMERICAL_FAILURE'
                    atomic_json(self.folder/'numerical_failure.json',dict(step=steps,
                        time_before_step_s=previous_time,engine_time_s=data.time,
                        warnings={k.name:int(data.warning[k].number) for k in
                            (mujoco.mjtWarning.mjWARN_BADQPOS,mujoco.mjtWarning.mjWARN_BADQVEL,mujoco.mjtWarning.mjWARN_BADQACC)}))
                    break
            if not complete:break
            motion=current()
            routes=[[data.site_xpos[model.site(f"{td['entity']}_point_{j}").id].tolist() for j in range(len(td['points']))] for td in p['tendons']]
            lengths=data.ten_length[tids].copy()
            row=dict(time_s=(step+1)*dt,solver_time_s=t,engine_time_s=data.time,tip_m=motion['tip'].tolist(),
                tip_velocity_m_s=(motion['Jtip']@data.qvel[vi]).tolist(),
                qpos_rad=data.qpos[qi].tolist(),qvel_rad_s=data.qvel[vi].tolist(),
                tendon_length_m=lengths.tolist(),tendon_length_change_m=(lengths-initial_lengths).tolist(),
                tendon_length_rate_m_s=((lengths-previous_lengths)/dt).tolist(),body_positions_m=data.xpos[bids].tolist(),
                body_rotations=data.xmat[bids].reshape(-1,3,3).tolist(),tendon_routes_m=routes,**self.controller.last,**before)
            if execution_mode=='actuator_realistic':
                row.update(actuator_command=self.controller.u.tolist(),command_m=command.tolist())
            rows.append(row);previous_lengths=lengths
        self.timings['solve']=time.perf_counter()-start
        return rows,self.controller.observations,complete,reason,steps


class NativeSequenceMujocoBackend(MujocoBackend):
    """Advertise the new observation only on the implemented explicit-schedule route."""
    @classmethod
    def check(cls,inp,parameters,control):
        super().check(inp,parameters,control)
        if inp.task.family=='task.oriented_tracking':check_rigid_tool_definition(inp)

    def solve(self,timeout_s):
        raise ValueError('TOOL_AXIS_REQUIRES_EXPLICIT_NATIVE_SEQUENCE_AND_PHYSICAL_REPLAY; NMPC orientation is not implemented')
