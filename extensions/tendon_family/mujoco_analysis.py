"""Native ideal-tension mechanics and bounded short responses; no GVS or Store.

MuJoCo 3.13 numerical semantics. Native integration checkpoints are never
replaced by a projected state. Structure comparisons require identical named
hinges and transplant qpos/qvel only, with reset solver history in every model.
"""
from io import BytesIO
import time
import mujoco
import numpy as np

from schemas.platform import SessionInput
from tools.platform_store import plain
from .backends import (physics_for, _mujoco_state_failed, MujocoFailureSnapshot,
    _bind_mujoco_forces, _apply_mujoco_forces)
from .scene import assemble_physical
from .mjcf import compile_xml


class NativeModel:
    def __init__(self, configuration):
        from tools.platform_registry import registry
        inp=SessionInput.model_validate(configuration)
        if inp.policy.backend.extension_id!='backend.family_mujoco':
            raise ValueError('NATIVE_ANALYSIS_REQUIRES_MUJOCO_BACKEND')
        self.physics=physics_for(inp);self.scene=assemble_physical(inp,self.physics)
        self.scene['control']=dict(tension_execution_mode='ideal_tension')
        xml=BytesIO()
        compile_xml(self.physics,self.scene,registry().parse(inp.policy.backend.parameters),xml)
        self.model=mujoco.MjModel.from_xml_string(xml.getvalue().decode('utf8'))
        m=self.model
        self.forces=_bind_mujoco_forces(m,self.scene)
        self.safety=MujocoFailureSnapshot(m,self.physics['identity'])
        self.order=self.physics['dofs'];self.tendons=[t['entity'] for t in self.physics['tendons']]
        jids=[m.joint(n).id for n in self.order]
        self.qi=m.jnt_qposadr[jids];self.vi=m.jnt_dofadr[jids]
        self.aids=[m.actuator(n+'_direct_tension').id for n in self.tendons]
        self.tids=[m.tendon(n).id for n in self.tendons];self.tip=m.site('tip_site').id
        self.limits=m.actuator_ctrlrange[self.aids].copy()
        if m.nq!=len(self.order) or m.nv!=len(self.order) or m.na:
            raise ValueError('NATIVE_V1_REQUIRES_COMPLETE_NAMED_HINGE_STATE')
        self.cost=dict(model_builds=1,forward_evaluations=0,physics_steps=0,physics_step_attempts=0,rollouts=0,mechanics_evaluations=0)

    def forward(self, d):
        _apply_mujoco_forces(self.model,d,self.forces)
        self.safety.call(d,mujoco.mj_forward,'native.forward');self.cost['forward_evaluations']+=1
        self.check_supported(d)

    def check_supported(self, d, previous_time=None):
        """Reject unsupported engine constraints, including between control samples."""
        if d.ncon or d.nefc or any(w.number for w in d.warning) or not np.isfinite(d.qacc).all():
            diagnostic=dict(time_s=float(d.time),constraint_count=int(d.nefc),contact_count=int(d.ncon),
                contacts=[dict(geom1=self.model.geom(int(c.geom1)).name,geom2=self.model.geom(int(c.geom2)).name,
                    distance_m=float(c.dist)) for c in d.contact],
                evaluation_interval_s=[previous_time,float(d.time)] if previous_time is not None else [float(d.time)] ,
                phase='last_engine_constraint_evaluation',cost=dict(self.cost),
                external_forces=self.scene['forces'],xfrc_applied_world=d.xfrc_applied.tolist())
            self.last_diagnostic=diagnostic
            error=ValueError('NATIVE_V1_REQUIRES_FINITE_CONTACT_FREE_UNCONSTRAINED_STATE')
            error.native_diagnostic=diagnostic
            raise error

    def restore(self, point, *, comparable=False):
        m=self.model;d=mujoco.MjData(m)
        if point['dof_order']!=self.order or point['tendon_order']!=self.tendons:
            raise ValueError('NATIVE_STATE_NAMED_COORDINATES_MISMATCH')
        if comparable:
            d.qpos[self.qi]=point['qpos_rad'];d.qvel[self.vi]=point['qvel_rad_s']
            d.time=point['actual_time_s']
        else:
            if point['physics_identity']!=self.physics['identity']:
                raise ValueError('NATIVE_STATE_PHYSICS_IDENTITY_MISMATCH')
            spec=mujoco.mjtState.mjSTATE_INTEGRATION
            saved=np.asarray(point['integration_state'],dtype=float)
            if (point['state_spec']!=int(spec) or saved.shape!=(mujoco.mj_stateSize(m,spec),)
                    or not np.isfinite(saved).all()):raise ValueError('COMPLETE_FINITE_NATIVE_INTEGRATION_STATE_REQUIRED')
            mujoco.mj_setState(m,d,saved,spec)
            if (abs(d.time-point['actual_time_s'])>1e-12 or
                    not np.array_equal(d.qpos[self.qi],point['qpos_rad']) or
                    not np.array_equal(d.qvel[self.vi],point['qvel_rad_s'])):
                raise ValueError('NATIVE_STATE_TIME_OR_COORDINATE_MISMATCH')
        if np.any(d.qfrc_applied):raise ValueError('NATIVE_V1_UNSCHEDULED_GENERALIZED_FORCE_UNSUPPORTED')
        # The frozen scene owns xfrc_applied, including after checkpoint restore.
        self.forward(d)
        return d

    def reconstruct(self, point):
        """Verify the saved prefix once and retain complete engine integration state."""
        scene=point['native_replay']['scene'];d=mujoco.MjData(self.model)
        if point['physics_identity']!=self.physics['identity']:raise ValueError('NATIVE_REPLAY_PHYSICS_MISMATCH')
        if any(scene[k]!=self.scene[k] for k in ('forces','qpos_rad','qvel_rad_s','control_period_s','timestep_s')):
            raise ValueError('NATIVE_REPLAY_FROZEN_SCENE_MISMATCH')
        d.qpos[self.qi]=scene['qpos_rad'];d.qvel[self.vi]=scene['qvel_rad_s']
        if not point['native_replay']['rows']:self.forward(d)
        worst=0.
        for row in point['native_replay']['rows']:
            self.apply(d,row['tension_n'])
            for _ in range(round(scene['control_period_s']/self.model.opt.timestep)):
                _apply_mujoco_forces(self.model,d,self.forces);self.cost['physics_step_attempts']+=1
                previous=float(d.time);self.safety.call(d,mujoco.mj_step,'native.prefix');self.cost['physics_steps']+=1
                self.check_supported(d,previous)
                if _mujoco_state_failed(d,previous):raise ValueError('NATIVE_PREFIX_NUMERICAL_FAILURE')
            self.forward(d);motion,_=self.motion(d)
            differences=[abs(d.time-row['time_s']),*abs(d.qpos[self.qi]-row['qpos_rad']),*abs(d.qvel[self.vi]-row['qvel_rad_s']),
                *abs(np.asarray(motion['tip_position_m'])-row['tip_m'])]
            worst=max(worst,max(differences))
            if worst>1e-10:raise ValueError('NATIVE_PREFIX_DOES_NOT_REPRODUCE_SAVED_EXECUTION')
        saved=self.checkpoint(d)
        saved.update(candidate=point['candidate'],configuration_identity=point['configuration_identity'],u=point['u'],
            prefix_tensions_n=[r['tension_n'] for r in point['native_replay']['rows']],
            provenance=point['provenance'],prefix_verification=dict(samples=len(point['native_replay']['rows']),max_absolute_difference=worst))
        return saved,d

    def checkpoint(self, d):
        spec=mujoco.mjtState.mjSTATE_INTEGRATION
        saved=np.empty(mujoco.mj_stateSize(self.model,spec));mujoco.mj_getState(self.model,d,saved,spec)
        return dict(physics_identity=self.physics['identity'],dof_order=self.order,tendon_order=self.tendons,
            state_spec=int(spec),integration_state=saved.tolist(),qpos_rad=d.qpos[self.qi].tolist(),
            qvel_rad_s=d.qvel[self.vi].tolist(),actual_time_s=float(d.time),
            phase='interval_start_native',input_units='N',u=d.ctrl[self.aids].tolist())

    def apply(self, d, u):
        u=np.asarray(u,dtype=float)
        if u.shape!=(len(self.aids),) or not np.isfinite(u).all() or np.any(u<self.limits[:,0]) or np.any(u>self.limits[:,1]):
            raise ValueError('LEGAL_ABSOLUTE_NATIVE_TENSIONS_REQUIRED')
        d.ctrl[self.aids]=u;self.forward(d)
        actual=-d.actuator_force[self.aids].copy()
        if not np.allclose(actual,u,atol=1e-10,rtol=0):raise ValueError('NATIVE_ACTUAL_TENSION_MISMATCH')
        return actual

    def motion(self, d):
        jac=np.zeros((3,self.model.nv));mujoco.mj_jacSite(self.model,d,jac,None,self.tip)
        return dict(time_s=float(d.time),tip_position_m=d.site_xpos[self.tip].tolist(),
            tip_velocity_m_s=(jac@d.qvel).tolist()),jac

    def mechanics(self, d, u):
        m=self.model;self.apply(d,u);self.cost['mechanics_evaluations']+=1
        mass=np.empty((m.nv,m.nv));mujoco.mj_fullM(m,d,mass)
        motion,jac=self.motion(d);jdot=np.zeros_like(jac)
        mujoco.mj_jacDot(m,d,jdot,None,d.site_xpos[self.tip],m.site_bodyid[self.tip])
        zero=mujoco.MjData(m);mujoco.mj_copyData(zero,m,d);zero.qvel[:]=0;self.forward(zero)
        moments=np.zeros((m.nu,m.nv))
        mujoco.mju_sparse2dense(moments,d.actuator_moment,d.moment_rownnz,d.moment_rowadr,d.moment_colind)
        mapping=-moments[self.aids].T
        response=np.empty((len(self.aids),m.nv));mujoco.mj_solveM(m,d,response,mapping.T.copy())
        passive=np.empty((1,m.nv));mujoco.mj_solveM(m,d,passive,d.qfrc_passive[None,:].copy())
        external=np.zeros(m.nv)
        for bid in {f[0] for f in self.forces}:
            com_jac=np.zeros((3,m.nv));mujoco.mj_jacBodyCom(m,d,com_jac,None,bid)
            external+=com_jac.T@d.xfrc_applied[bid,:3]
        external_response=np.empty((1,m.nv));mujoco.mj_solveM(m,d,external_response,external[None,:].copy())
        tendon_jac=np.zeros((m.ntendon,m.nv))
        mujoco.mju_sparse2dense(tendon_jac,d.ten_J,m.ten_J_rownnz,m.ten_J_rowadr,m.ten_J_colind)
        balance=mass@d.qacc-d.qfrc_smooth-d.qfrc_constraint
        acceleration=jac@d.qacc+jdot@d.qvel;drive=jac@response.T;v=np.asarray(motion['tip_velocity_m_s'])
        speed=float(np.linalg.norm(v))
        speed_map=v@drive/speed if speed>0 else None
        speed_rate=float(v@acceleration/speed) if speed>0 else None
        braking_input=np.where(speed_map>=0,self.limits[:,0],self.limits[:,1]) if speed>0 else None
        speed_range=None if speed==0 else [float(speed_rate+np.sum(np.minimum(speed_map*(self.limits[:,0]-u),speed_map*(self.limits[:,1]-u)))),
            float(speed_rate+np.sum(np.maximum(speed_map*(self.limits[:,0]-u),speed_map*(self.limits[:,1]-u))))]
        return dict(**motion,mass_matrix_kg_m2=mass[np.ix_(self.vi,self.vi)].tolist(),qacc_rad_s2=d.qacc[self.vi].tolist(),
            qpos_rad=d.qpos[self.qi].tolist(),qvel_rad_s=d.qvel[self.vi].tolist(),
            coordinates=dict(dof_order=self.order,tendon_order=self.tendons,tip_frame='world',
                input_semantics='absolute ideal tension in N; engine actuator force has negative sign'),
            validity=dict(time_s=float(d.time),scope='instantaneous state and input only',contact_count=int(d.ncon),
                constraint_count=int(d.nefc),external_applied_force=bool(np.any(d.xfrc_applied))),
            external_force_execution=dict(forces=self.scene['forces'],
                semantics=self.scene['semantics'].get('external_forces'),xfrc_applied_world=d.xfrc_applied.tolist()),
            mass_factorization=dict(source='MuJoCo mj_factorM / mj_solveM',
                inverse_diagonal=d.qLDiagInv[self.vi].tolist(),inverse_diagonal_unit='1/(kg*m^2)'),
            input_bounds_n=self.limits.tolist(),input_saturation=dict(
                lower=np.isclose(np.asarray(u),self.limits[:,0],atol=1e-10,rtol=0).tolist(),
                upper=np.isclose(np.asarray(u),self.limits[:,1],atol=1e-10,rtol=0).tolist()),
            generalized_forces_nm={**{key:getattr(d,'qfrc_'+key)[self.vi].tolist() for key in
                ('bias','passive','spring','damper','actuator','applied','constraint','smooth')},
                'external_body':external[self.vi].tolist()},
            gravity_bias_nm=zero.qfrc_bias[self.vi].tolist(),
            velocity_bias_nm=(d.qfrc_bias-zero.qfrc_bias)[self.vi].tolist(),
            tip_jacobian_m_rad=jac[:,self.vi].tolist(),tip_acceleration_m_s2=acceleration.tolist(),
            tendon_lengths_m=d.ten_length[self.tids].tolist(),tendon_jacobian_m_rad=tendon_jac[self.tids][:,self.vi].tolist(),
            input_force_map_nm_n=mapping[self.vi].tolist(),
            tip_acceleration_input_map_m_s2_n=drive.tolist(),
            passive_tip_acceleration_contribution_m_s2=(jac@passive[0]).tolist(),
            external_tip_acceleration_contribution_m_s2=(jac@external_response[0]).tolist(),
            function_metrics=dict(drive_singular_values_m_s2_n=np.linalg.svd(drive,compute_uv=False).tolist(),
                speed_derivative_m_s2=speed_rate,
                speed_derivative_input_map_m_s2_n=speed_map.tolist() if speed>0 else None,
                instantaneous_speed_derivative_range_m_s2=speed_range,
                minimum_speed_derivative_tensions_n=braking_input.tolist() if speed>0 else None),
            mass_balance_residual_inf_nm=float(np.max(abs(balance))),
            actuator_map_residual_inf_nm=float(np.max(abs(mapping@u-d.qfrc_actuator))),
            mass_condition_number=float(np.linalg.cond(mass)),actual_tensions_n=(-d.actuator_force[self.aids]).tolist(),
            component_order=dict(bodies=[m.body(i).name for i in range(m.nbody)],joints=[m.joint(i).name for i in range(m.njnt)]),
            components=dict(body_mass_kg=m.body_mass.tolist(),body_inertia_kg_m2=m.body_inertia.tolist(),
                joint_stiffness_nm_rad=m.jnt_stiffness.tolist(),damping_nm_s_rad=m.dof_damping.tolist(),
                body_positions_m=m.body_pos.tolist(),site_positions_m=m.site_pos.tolist()))

    def rollout(self, start, u, horizon):
        m=self.model;steps=round(horizon/m.opt.timestep)
        if steps<1 or abs(steps*m.opt.timestep-horizon)>1e-12:raise ValueError('NATIVE_ALIGNED_HORIZON_REQUIRED')
        d=mujoco.MjData(m);mujoco.mj_copyData(d,m,start);actual=self.apply(d,u)
        self.cost['rollouts']+=1
        for _ in range(steps):
            _apply_mujoco_forces(m,d,self.forces);self.cost['physics_step_attempts']+=1
            previous=float(d.time);self.safety.call(d,mujoco.mj_step,'native.rollout');self.cost['physics_steps']+=1
            self.check_supported(d,previous)
            if _mujoco_state_failed(d,previous):raise ValueError('NATIVE_SHORT_ROLLOUT_NUMERICAL_FAILURE')
        self.forward(d);motion,_=self.motion(d)
        return dict(**motion,actual_tensions_n=actual.tolist(),qpos_rad=d.qpos[self.qi].tolist(),qvel_rad_s=d.qvel[self.vi].tolist())

    def rollout_sequence(self, start, times, tensions, *, capture_speed_after_s=None):
        """Clone one integration state; sample its origin and every interval end."""
        times=np.asarray(times,dtype=float);tensions=np.asarray(tensions,dtype=float)
        steps=np.rint(np.diff(times)/self.model.opt.timestep).astype(int)
        if (len(times)<2 or tensions.shape!=(len(times)-1,len(self.aids)) or
                not np.isfinite(times).all() or abs(times[0]-start.time)>1e-12 or
                np.any(steps<1) or np.max(abs(steps*self.model.opt.timestep-np.diff(times)))>1e-12):
            raise ValueError('NATIVE_ALIGNED_SEQUENCE_REQUIRED')
        d=mujoco.MjData(self.model);mujoco.mj_copyData(d,self.model,start)
        self.forward(d);samples=[self.motion(d)[0]];actual=[]
        peak=None;peak_speed=-1.
        def retain_peak():
            nonlocal peak,peak_speed
            if capture_speed_after_s is not None and d.time>=capture_speed_after_s-1e-12:
                speed=float(np.linalg.norm(samples[-1]['tip_velocity_m_s']))
                if speed>peak_speed:peak=self.checkpoint(d);peak_speed=speed
        retain_peak()
        self.cost['rollouts']+=1
        for count,u in zip(steps,tensions):
            actual.append(self.apply(d,u).tolist())
            for _ in range(count):
                _apply_mujoco_forces(self.model,d,self.forces);self.cost['physics_step_attempts']+=1
                previous=float(d.time);self.safety.call(d,mujoco.mj_step,'native.sequence');self.cost['physics_steps']+=1
                self.check_supported(d,previous)
                if _mujoco_state_failed(d,previous):raise ValueError('NATIVE_SEQUENCE_NUMERICAL_FAILURE')
            self.forward(d);samples.append(self.motion(d)[0])
            retain_peak()
        result=dict(times_s=[s['time_s'] for s in samples],
            tip_positions_m=[s['tip_position_m'] for s in samples],
            tip_velocities_m_s=[s['tip_velocity_m_s'] for s in samples],actual_tensions_n=actual)
        if peak is not None:result['peak_speed_state']=peak
        return result


def input_response(native, start, u, options):
    """Two actual-input step sizes; central where legal, otherwise one-sided."""
    u=np.asarray(u);base=native.rollout(start,u,options.horizon_s)
    def output(row):return np.r_[row['tip_position_m'],row['tip_velocity_m_s']]
    y=output(base);matrices=[];probes=[]
    for h in (options.difference_step_n,options.difference_step_n/2):
        cols=[]
        for j in range(len(u)):
            lo,hi=native.limits[j];minus=u.copy();plus=u.copy()
            if u[j]-h>=lo and u[j]+h<=hi:minus[j]-=h;plus[j]+=h
            elif hi-u[j]>=u[j]-lo:plus[j]=min(hi,u[j]+h)
            else:minus[j]=max(lo,u[j]-h)
            left=base if np.array_equal(minus,u) else native.rollout(start,minus,options.horizon_s)
            right=base if np.array_equal(plus,u) else native.rollout(start,plus,options.horizon_s)
            delta=right['actual_tensions_n'][j]-left['actual_tensions_n'][j]
            cols.append((output(right)-output(left))/delta)
            probes.append(dict(channel=native.tendons[j],requested_step_n=h,actual_denominator_n=delta,
                scheme='central' if minus[j]<u[j]<plus[j] else 'one_sided',minus=left,plus=right))
        matrices.append(np.column_stack(cols))
    # Position and velocity have different units, so assess each block separately.
    errors={key:float(np.linalg.norm((matrices[1]-matrices[0])[sl])/max(np.linalg.norm(matrices[1][sl]),1e-15))
        for key,sl in [('position',slice(0,3)),('velocity',slice(3,6))]}
    return dict(baseline=base,position_input_jacobian_m_n=matrices[1][:3].tolist(),
        velocity_input_jacobian_m_s_n=matrices[1][3:].tolist(),coarse_response=matrices[0].tolist(),
        step_consistency_relative=errors,step_consistency_passed=max(errors.values())<.05,
        probes=probes,scope='Local fixed-state, fixed-horizon, absolute legal tensions; two FD sizes are not a regional error bound.')


def calculate(configuration, point, options, operation, comparisons=None):
    """Full numerical evidence plus costs. Research/task semantics stay outside."""
    started=time.perf_counter();native=NativeModel(configuration)
    point,start=native.reconstruct(point) if point.get('native_replay') else (point,native.restore(point))
    u=point['u'] if options.tensions_n is None else options.tensions_n
    mechanics=native.mechanics(start,u)
    raw=dict(initial_state=point,mechanics=mechanics,physics_identity=native.physics['identity'],design_identity=native.physics['design_identity'],
        physical_scene_identity=native.scene['identity'],
        external_force_execution=dict(forces=native.scene['forces'],semantics=native.scene['semantics'].get('external_forces')),
        representation='native named MuJoCo hinges; world tip; ideal absolute SI tensions',
        runtime=dict(mujoco=mujoco.__version__,timestep_s=native.model.opt.timestep,integrator=int(native.model.opt.integrator)),
        state_comparison='Exact integration checkpoint')
    if operation=='short_input_response_v1':raw['input_response']=input_response(native,start,u,options)
    if operation=='fixed_input_structure_v1':
        # Identical named qpos/qvel, reset warmstart/ctrl/applied forces in ALL models.
        start=native.restore(point,comparable=True)
        base=dict(mechanics=native.mechanics(start,u),terminal=native.rollout(start,u,options.horizon_s))
        raw.update(structure_baseline=base,structure_responses=[],state_comparison='Same named qpos/qvel and absolute input; reset solver history in all models; not equal equilibrium or energy')
        for comparison in comparisons:
            other=NativeModel(comparison['configuration']);data=other.restore(point,comparable=True)
            changed=dict(mechanics=other.mechanics(data,u),terminal=other.rollout(data,u,options.horizon_s))
            raw['structure_responses'].append(dict(**{k:v for k,v in comparison.items() if k!='configuration'},
                physics_identity=other.physics['identity'],**changed))
            for key,value in other.cost.items():native.cost[key]+=value
    raw['cost']=dict(**native.cost,kernel_wall_s=time.perf_counter()-started)
    return raw,native,start
