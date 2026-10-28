"""Native passive rope mechanics and moving material-point force, without Store."""
from pathlib import Path
import numpy as np
import mujoco
from .mjcf import compile_xml


def material_point(physics, s):
    """Use compiler attachment convention; s excludes rigid connector lengths."""
    if not 0 <= s <= 1:
        raise ValueError('MATERIAL_S_OUT_OF_RANGE')
    cells=[(i,p) for i,p in enumerate(physics['parts']) if p['dofs']]
    target=s*sum(p['length_m'] for _,p in cells)
    for k,(i,p) in enumerate(cells):
        if target < p['length_m']-1e-14 or k==len(cells)-1:
            return dict(body=i,position_m=[float(np.clip(target,0,p['length_m'])),0.,0.])
        target-=p['length_m']


class PassiveModel:
    def __init__(self, physics, protocol, payout, folder, unrestricted=False):
        self.physics=physics; self.protocol=protocol
        self.payout=np.array(payout,dtype=float)
        self.scene=dict(mount_position=protocol['mount_position'],mount_rotation=protocol['mount_rotation'],
            gravity=protocol['gravity'],floor_id='floor',floor_z_m=0.,timestep_s=protocol['timestep_s'],
            control=dict(tension_execution_mode='passive_fixed_payout_v1',
                payout_lengths_m=dict(zip([t['entity'] for t in physics['tendons']],payout)),
                solreflimit=protocol['solreflimit'],solimplimit=protocol['solimplimit']))
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        path=compile_xml(physics,self.scene,None,folder/'model.xml')
        self.model=m=mujoco.MjModel.from_xml_path(str(path))
        m.opt.iterations=100; m.opt.tolerance=1e-10
        if unrestricted:m.tendon_limited[:]=False
        self.unrestricted=unrestricted
        self.body_ids=[m.body(p['entity']).id for p in physics['parts']]
        self.base=m.body('fixed_base').id
        self.points=[material_point(physics,s) for s in protocol['monitor_s']]+[physics['tip']]
        assert m.nu==0 and m.nq==m.nv==len(physics['dofs'])

    def point(self, d, binding):
        bid=self.base if binding['body']<0 else self.body_ids[binding['body']]
        p=d.xpos[bid]+d.xmat[bid].reshape(3,3)@binding['position_m']
        J=np.zeros((3,self.model.nv))
        mujoco.mj_jac(self.model,d,J,None,p,bid)
        return p,J,bid

    def apply_force(self,d,s,force):
        d.qfrc_applied[:]=0.; d.xfrc_applied[:]=0.
        p,J,bid=self.point(d,material_point(self.physics,s))
        mujoco.mj_applyFT(self.model,d,np.array([force,0.,0.]),np.zeros(3),p,bid,d.qfrc_applied)
        return p,J

    def tendon_jac(self,d):
        m=self.model
        if not mujoco.mj_isSparse(m):return d.ten_J.reshape(m.ntendon,m.nv).copy()
        J=np.zeros((m.ntendon,m.nv))
        mujoco.mju_sparse2dense(J,d.ten_J,m.ten_J_rownnz,m.ten_J_rowadr,m.ten_J_colind)
        return J

    def snapshot(self,d,s,force):
        self.apply_force(d,s,force);mujoco.mj_forward(self.model,d)
        items=[self.point(d,p) for p in self.points]
        pF,JF,_=self.point(d,material_point(self.physics,s))
        Jl=self.tendon_jac(d); tensions=np.zeros(self.model.ntendon);rows=[]
        E=d.efc_J.reshape(d.nefc,self.model.nv) if not mujoco.mj_isSparse(self.model) else None
        if E is None:
            E=np.zeros((d.nefc,self.model.nv))
            mujoco.mju_sparse2dense(E,d.efc_J,d.efc_J_rownnz,d.efc_J_rowadr,d.efc_J_colind)
        for r in range(d.nefc):
            if d.efc_type[r]!=int(mujoco.mjtConstraint.mjCNSTR_LIMIT_TENDON):continue
            t=int(d.efc_id[r]); lam=float(d.efc_force[r]);tensions[t]+=lam
            rows.append(dict(tendon=t,multiplier_n=lam,upper_sign_error=float(np.max(np.abs(E[r]+Jl[t]))),
                residual_m=float(d.efc_pos[r]),state=int(d.efc_state[r])))
        balance=d.qfrc_passive+d.qfrc_applied-d.qfrc_bias+d.qfrc_constraint
        static=mujoco.MjData(self.model);mujoco.mj_copyData(static,self.model,d)
        static.qvel[:]=0.;self.apply_force(static,s,force);mujoco.mj_forward(self.model,static)
        static_balance=static.qfrc_passive+static.qfrc_applied-static.qfrc_bias+static.qfrc_constraint
        extra={}
        if self.protocol.get('diagnostic_recording'):
            cold=mujoco.MjData(self.model);cold.qpos[:]=d.qpos;mujoco.mj_forward(self.model,cold)
            self.apply_force(cold,s,force);mujoco.mj_forward(self.model,cold)
            cold_balance=cold.qfrc_passive+cold.qfrc_applied-cold.qfrc_bias+cold.qfrc_constraint
            extra=dict(qacc=d.qacc.tolist(),dynamic_balance_nm=balance.tolist(),static_balance_nm=static_balance.tolist(),
                cold_static_balance_nm=cold_balance.tolist(),cold_static_balance_inf_nm=float(np.max(abs(cold_balance))),
                passive_force_nm=d.qfrc_passive.tolist(),bias_force_nm=d.qfrc_bias.tolist(),applied_force_nm=d.qfrc_applied.tolist(),
                constraint_force_nm=d.qfrc_constraint.tolist(),qacc_warmstart=d.qacc_warmstart.tolist())
        return dict(**extra,time_s=float(d.time),qpos=d.qpos.tolist(),qvel=d.qvel.tolist(),
            positions=[p.tolist() for p,_,_ in items],speeds=[float(np.linalg.norm(J@d.qvel)) for _,J,_ in items],
            force_point=pF.tolist(),force_n=float(force),tendon_lengths=d.ten_length.tolist(),
            length_change=(d.ten_length-self.payout).tolist(),tensions_n=tensions.tolist(),constraint_rows=rows,
            taut=(tensions>1e-6).tolist(),balance_inf_nm=float(np.max(np.abs(balance))),
            static_balance_inf_nm=float(np.max(np.abs(static_balance))),qvel_inf=float(np.max(np.abs(d.qvel))),
            contacts=int(d.ncon),solver_iterations=np.array(d.solver_niter).tolist(),
            warnings=np.array(d.warning.number).tolist(),force_map_error=float(np.max(np.abs(d.qfrc_applied-JF[0]*force))))

    def run(self,q0,s,force,*,attempt,initial=False):
        m=self.model;p=self.protocol;d=mujoco.MjData(m)
        if q0 is not None:d.qpos[:]=q0
        mujoco.mj_forward(m,d)
        samples=[self.snapshot(d,s,0.)];count=round(p['equilibrium_max_s' if initial else 'load_max_s']/m.opt.timestep)
        for k in range(count):
            t=k*m.opt.timestep
            a=1. if initial else min(t/p['ramp_s'],1.)
            value=force*a*a*(3-2*a)
            self.apply_force(d,s,value)
            previous=float(d.time);attempt();mujoco.mj_step(m,d)
            if not np.isfinite(d.qpos).all() or d.time<=previous or np.any(d.warning.number):
                return dict(status='numerical_failure',samples=samples,failed_step=k+1)
            # Refresh moving frame before the next force mapping and sampled measurements.
            mujoco.mj_forward(m,d)
            if d.ncon:
                samples.append(self.snapshot(d,s,value))
                return dict(status='contact_failure',samples=samples,failed_step=k+1)
            if (k+1)%p['sample_every_steps']==0:samples.append(self.snapshot(d,s,value))
        tail=[r for r in samples if r['time_s']>=d.time-p['tail_s']-1e-9]
        positions=np.array([r['positions'] for r in tail]);drift=float(np.max(np.linalg.norm(positions-positions[0],axis=2)))
        excess=max(max(r['length_change']) for r in tail)
        checks=dict(tip_speed=max(r['speeds'][-1] for r in tail)<=p['tip_speed_limit_m_s'],
            monitor_speed=max(max(r['speeds']) for r in tail)<=p['monitor_speed_limit_m_s'],
            drift=drift<=p['tail_drift_limit_m'],qvel=max(r['qvel_inf'] for r in tail)<=p['qvel_inf_limit_rad_s'],
            static_balance=max(r['static_balance_inf_nm'] for r in tail)<=p['static_balance_inf_limit_nm'],
            rope_excess=self.unrestricted or excess<=p['length_excess_limit_m'],
            rope_direction=all(row['multiplier_n']>=-1e-10 and row['upper_sign_error']<1e-8 for r in tail for row in r['constraint_rows']),
            rope_capacity=max(max(r['tensions_n'][i]/t['force_limit_n'] for i,t in enumerate(self.physics['tendons'])) for r in tail)<=1.)
        return dict(status='stable' if all(checks.values()) else 'unsettled_or_constraint_failure',
            samples=samples,checks=checks,tail_drift_m=drift,tail_excess_m=excess)


def compliance(native,q,tensions,locations,force):
    """Directional local QP plus bilateral nullspace diagnostic at known equilibrium."""
    from scipy.optimize import minimize, LinearConstraint
    from scipy.linalg import null_space
    m=native.model;d=mujoco.MjData(m);d.qpos[:]=q;mujoco.mj_forward(m,d)
    J=native.tendon_jac(d);Jtip=native.point(d,native.physics['tip'])[1]
    # Hessian of the Lagrangian includes gravity and taut-rope geometric stiffness.
    def gradient(x):
        e=mujoco.MjData(m);e.qpos[:]=x;mujoco.mj_forward(m,e)
        return e.qfrc_bias-e.qfrc_passive+native.tendon_jac(e).T@tensions
    h=1e-5;eye=np.eye(m.nv)
    K=np.column_stack([(gradient(np.array(q)+h*v)-gradient(np.array(q)-h*v))/(2*h) for v in eye])
    asym=float(np.max(np.abs(K-K.T)));K=(K+K.T)/2
    near=((d.ten_length>=native.payout-1e-7)|(np.array(tensions)>1e-6))&np.array(m.tendon_limited,dtype=bool)
    A=J[near];Z=null_space(A,rcond=1e-9);reduced=Z.T@K@Z
    eig=np.linalg.eigvalsh(reduced);sv=np.linalg.svd(A,compute_uv=False)
    predictions=[]
    for s in locations:
        JF=native.point(d,material_point(native.physics,s))[1]
        for sign in (1,-1):
            load=JF[0]*force*sign
            bilateral=Z@np.linalg.solve(reduced,Z.T@load)
            positive=np.array(tensions)[near]>1e-6
            constraints=[]
            if np.any(positive):constraints.append(LinearConstraint(A[positive],0.,0.))
            if np.any(~positive):constraints.append(LinearConstraint(A[~positive],-np.inf,0.))
            result=minimize(lambda x:.5*x@K@x-load@x,np.zeros(m.nv),jac=lambda x:K@x-load,
                constraints=constraints,method='SLSQP',options=dict(ftol=1e-12,maxiter=200))
            def measure(x):
                middle=float(JF[0]@x);tip=float(np.linalg.norm((Jtip@x)[:2]))
                return dict(point_x_m=middle,tip_xy_m=tip,ratio=tip/max(abs(middle),1e-15))
            predictions.append(dict(s=s,force_n=sign*force,unilateral=measure(result.x),bilateral=measure(bilateral),
                success=bool(result.success),message=result.message,iterations=int(result.nit),
                inequality_residual=float(max(0,np.max(A@result.x))) if len(A) else 0.))
    return dict(method='passive_constrained_compliance_v1',model='native 48 hinge coordinates',
        assumption='no-load equilibrium; positive multipliers held taut, zero multipliers unilateral; finite-force extrapolation only; MuJoCo soft penetration idealized as hard boundary',
        jacobian_rank=int(np.linalg.matrix_rank(A,tol=1e-9)),nullity=int(Z.shape[1]),singular_values=sv.tolist(),
        reduced_eigenvalues=eig.tolist(),stiffness_asymmetry=asym,predictions=predictions,
        K=K.tolist(),Jlength=J.tolist(),Jtip=Jtip.tolist(),q=q)
