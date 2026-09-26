"""Existing platform lifecycle and evidence envelopes, independent engine execution."""
import gzip
import json
import time
import numpy as np
from schemas.platform import BackendResult
from tools.state_io import atomic_json
from .compiler import resolve
from .scene import assemble
from .contracts import Initial, Data
from .signals import export
from .execution import resolve_execution


def physics_for(inp):
    if inp.robot.structure.contract=='family.design':
        discretization = inp.policy.discretization.data if inp.policy.discretization is not None else None
        return resolve(inp.robot.structure.data,discretization)
    if inp.robot.structure.contract=='domain.rod_design':
        from .legacy import resolve_legacy
        return resolve_legacy(inp.robot.structure.data)
    raise ValueError('UNSUPPORTED_FAMILY_DESIGN_CONTRACT')


def _mujoco_state_failed(data, previous_time):
    """MuJoCo can reset invalid velocities to finite values during mj_step."""
    import mujoco
    warnings=(mujoco.mjtWarning.mjWARN_BADQPOS,mujoco.mjtWarning.mjWARN_BADQVEL,mujoco.mjtWarning.mjWARN_BADQACC)
    return (data.time<=previous_time or any(data.warning[k].number for k in warnings)
        or not all(np.isfinite(v).all() for v in (data.qpos,data.qvel,data.qacc)))


class MatlabBackend:
    backend_id='backend.matlab_spatial'
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
        controllers=['controller.family']
        if cls.model=='mujoco_serial_bending_v1': controllers.extend(['controller.gvs_lqr','controller.gvs_sampled_lqr','controller.gvs_nmpc'])
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
            signals=export(rows,self.physics,self.scene['control']['mode'] in ('tension_reference','gvs_lqr','gvs_sampled_lqr','gvs_nmpc'),
                self.scene['control'].get('tension_execution_mode','actuator_realistic')),
            data=Payload(contract='family.backend_data',data=data.model_dump(mode='json')),
            limitations=[self.physics['applicability']['collision'],execution_limitation,
                'MATLAB lowest-envelope-vertex penalty and MuJoCo convex contact differ; no contact accuracy claim.'],initial_state=self.initial,seed=self.inp.seed)
        atomic_json(folder/'result.json',self.result.model_dump(mode='json')); return self.result

    def shared_input(self,timeout_s):
        c=dict(self.scene['control']['effective_parameters'])
        c['target_world_m']=self.scene['control']['reference'].get('target_world_m')
        commands=self.scene['control']['reference'].get('commands',{})
        c['command_vector']=[commands.get(a['id'],0.) for a in self.physics['actuators']]
        return dict(physics=self.physics,scene=self.scene,config=self.config.model_dump(mode='json'),control=c,timeout_s=timeout_s)

    def solve(self,timeout_s):
        from tools.matlab_tools import MatlabTools
        shared=self.shared_input(timeout_s); atomic_json(self.folder/'matlab_input.json',shared)
        start=time.perf_counter(); executor=MatlabTools(); self.timings['engine_start']=time.perf_counter()-start
        try:
            static=json.loads(executor.eng.tf_static(json.dumps(shared),nargout=1))
            atomic_json(self.folder/'matlab_static.json',static)
            raw=self.folder/'matlab_raw.json'
            future=executor.eng.tf_run(json.dumps(shared),str(raw.resolve()),nargout=0,background=True)
            try: future.result(timeout=timeout_s+30)
            except Exception:
                future.cancel(); raise
            out=json.loads(raw.read_text(encoding='utf8')); self.timings['solve']=out['solve_s']
            # MATLAB jsonencode represents a length-one numeric vector as scalar.
            vector_fields=('qpos_rad','qvel_rad_s','actuator_command','command_m','tendon_length_m','target_lengths_m',
                'requested_tension_n','desired_tension_n','predicted_tension_n','tension_tracking_error_n',
                'solver_tendon_length_m','tension_n','solver_qfrc_actuator_nm','solver_qfrc_passive_nm','external_torque_nm','contact_normal_approx_n')
            for row in out['trajectory']+out['observations']:
                for key in vector_fields:
                    if key in row and isinstance(row[key],(int,float)): row[key]=[row[key]]
                if 'body_positions_m' in row and len(self.physics['parts'])==1:
                    row['body_positions_m']=[row['body_positions_m']]
                    row['body_rotations']=[row['body_rotations']]
            return out['trajectory'],out['observations'],out['complete'],out['reason'] or None,out['numerical_steps']
        finally: executor.close()

    def export(self): return self.result

    def close(self): pass


class MujocoBackend(MatlabBackend):
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
        bids=[model.body(b['entity']).id for b in p['parts']]
        # Tree serialization can reorder siblings; never assume array order.
        jids=[model.joint(j).id for j in p['dofs']]; qi=model.jnt_qposadr[jids]; vi=model.jnt_dofadr[jids]
        tids=[model.tendon(t['entity']).id for t in p['tendons']]
        execution_mode=s['control'].get('tension_execution_mode','actuator_realistic')
        suffix='_direct_tension' if execution_mode=='ideal_tension' else '_length_servo'
        aids=[model.actuator(t['entity']+suffix).id for t in p['tendons']]
        data.qpos[qi]=s['qpos_rad']; data.qvel[vi]=s['qvel_rad_s']; mujoco.mj_forward(model,data)
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
            mujoco.mj_forward(model,data)
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
            if time.perf_counter()-start>timeout_s: complete=False; reason='MUJOCO_SOLVER_TIMEOUT'; break
            t=step*dt; g=current()
            if s['control']['mode'] in ('gvs_lqr','gvs_sampled_lqr','gvs_nmpc'):
                from .gvs_projection import project, PROJECTOR_ID
                projection=project(p,self.controller.resolved_basis,data.qpos[qi],data.qvel[vi],
                    convention=getattr(self.controller,'projector_id',PROJECTOR_ID))
                g['gvs_projection']=projection
                command=self.controller.command(t,g,np.asarray(projection['q_gvs']),np.asarray(projection['qdot_gvs']))
                if s['control']['mode']=='gvs_nmpc':
                    atomic_json(self.folder/'nmpc_updates.json',self.controller.observations)
            else:
                command=self.controller.command(t,g,data.qpos[qi].copy(),data.qvel[vi].copy())
            data.ctrl[aids]=command; data.xfrc_applied[:]=0; external=np.zeros(model.nv)
            for f in s['forces']:
                if f['start_s']<=t<f['end_s']:
                    bid=bids[f['body']]; data.xfrc_applied[bid,:3]+=f['force_n']
                    J=np.zeros((3,model.nv)); Jr=np.zeros_like(J); mujoco.mj_jacBodyCom(model,data,J,Jr,bid)
                    external+=J.T@f['force_n']
            mujoco.mj_forward(model,data)
            actual_tension=-data.actuator_force[aids]
            before=dict(solver_tendon_length_m=data.ten_length[tids].tolist(),tension_n=actual_tension.tolist(),
                solver_qfrc_actuator_nm=data.qfrc_actuator[vi].tolist(),solver_qfrc_passive_nm=data.qfrc_passive[vi].tolist(),external_torque_nm=external[vi].tolist())
            if execution_mode=='ideal_tension':
                tracking=(actual_tension-np.asarray(self.controller.last['desired_tension_n'])).tolist()
                self.controller.last['tension_tracking_error_n']=tracking
                self.controller.last['predicted_tension_n']=actual_tension.tolist()
                self.controller.observations[-1].update(tension_tracking_error_n=tracking,
                    predicted_tension_n=actual_tension.tolist(),actual_tension_n=actual_tension.tolist())
            for _ in range(substeps):
                previous_time=data.time
                mujoco.mj_step(model,data); steps+=1
                if _mujoco_state_failed(data,previous_time):
                    complete=False; reason='MUJOCO_NUMERICAL_FAILURE'
                    atomic_json(self.folder/'numerical_failure.json',dict(step=steps,
                        time_before_step_s=previous_time,engine_time_s=data.time,
                        warnings={k.name:int(data.warning[k].number) for k in
                            (mujoco.mjtWarning.mjWARN_BADQPOS,mujoco.mjtWarning.mjWARN_BADQVEL,mujoco.mjtWarning.mjWARN_BADQACC)}))
                    break
            if not complete:break
            mujoco.mj_forward(model,data)
            routes=[[data.site_xpos[model.site(f"{td['entity']}_point_{j}").id].tolist() for j in range(len(td['points']))] for td in p['tendons']]
            lengths=data.ten_length[tids].copy()
            row=dict(time_s=(step+1)*dt,solver_time_s=t,engine_time_s=data.time,tip_m=data.site_xpos[model.site('tip_site').id].tolist(),
                qpos_rad=data.qpos[qi].tolist(),qvel_rad_s=data.qvel[vi].tolist(),
                tendon_length_m=lengths.tolist(),tendon_length_change_m=(lengths-initial_lengths).tolist(),
                tendon_length_rate_m_s=((lengths-previous_lengths)/dt).tolist(),body_positions_m=data.xpos[bids].tolist(),
                body_rotations=data.xmat[bids].reshape(-1,3,3).tolist(),tendon_routes_m=routes,**self.controller.last,**before)
            if execution_mode=='actuator_realistic':
                row.update(actuator_command=self.controller.u.tolist(),command_m=command.tolist())
            rows.append(row);previous_lengths=lengths
        self.timings['solve']=time.perf_counter()-start
        return rows,self.controller.observations,complete,reason,steps
