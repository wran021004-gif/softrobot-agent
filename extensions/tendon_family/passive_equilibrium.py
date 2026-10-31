"""Native potential minimization and passive KKT/tangent diagnostics, no persistence."""
import numpy as np
import mujoco
from scipy.optimize import minimize,nnls,LinearConstraint
from scipy.linalg import null_space
from .passive import material_point


class StaticProblem:
    def __init__(self,native,s=.5,force=0.):
        self.native=native;self.m=native.model;self.s=s;self.force=np.asarray(force if np.ndim(force) else [force,0.,0.],dtype=float)
        self.d=mujoco.MjData(self.m);self.last=None
        self.cost=dict(native_forward_calls=0,objective_calls=0,gradient_calls=0,constraint_calls=0,
            constraint_jacobian_calls=0,hessian_columns=0,optimizer_iterations=0,QP_calls=0,equilibrium_solves=0,KKT_solves=0)

    def at(self,q):
        q=np.asarray(q)
        if self.last is None or not np.array_equal(q,self.last):
            self.d.qpos[:]=q;self.d.qvel[:]=0.;self.d.qfrc_applied[:]=0.;self.d.qacc_warmstart[:]=0.
            mujoco.mj_forward(self.m,self.d);self.last=q.copy();self.cost['native_forward_calls']+=1
        return self.d

    def objective(self,q):
        self.cost['objective_calls']+=1;d=self.at(q)
        elastic=.5*np.sum(self.m.jnt_stiffness*(q-self.m.qpos_spring)**2)
        gravity=-np.sum(self.m.body_mass*(d.xipos@self.m.opt.gravity))
        point=self.native.point(d,material_point(self.native.physics,self.s))[0]
        return float(elastic+gravity-np.asarray(self.force)@point)

    def gradient(self,q):
        self.cost['gradient_calls']+=1;d=self.at(q)
        J=self.native.point(d,material_point(self.native.physics,self.s))[1]
        return d.qfrc_bias-d.qfrc_passive-self.force@J

    def constraint(self,q):
        self.cost['constraint_calls']+=1
        return self.at(q).ten_length.copy()-self.native.payout

    def jacobian(self,q):
        self.cost['constraint_jacobian_calls']+=1
        return self.native.tendon_jac(self.at(q))

    def hessian(self,q,tensions):
        h=self.native.protocol['static_solver']['hessian_step_rad'];eye=np.eye(self.m.nv)
        def grad(x):return self.gradient(x)+self.jacobian(x).T@tensions
        H=np.column_stack([(grad(q+h*v)-grad(q-h*v))/(2*h) for v in eye])
        self.cost['hessian_columns']+=self.m.nv
        return (H+H.T)/2,float(np.max(abs(H-H.T)))

    def qualify(self,q):
        opts=self.native.protocol['static_solver'];g=self.constraint(q);J=self.jacobian(q);grad=self.gradient(q)
        active=(g>=-opts['active_tolerance_m'])&np.array(self.m.tendon_limited,dtype=bool)
        tension=np.zeros(self.m.ntendon)
        if np.any(active):tension[active]=nnls(J[active].T,-grad,maxiter=1000)[0]
        residual=grad+J.T@tension;H,asym=self.hessian(q,tension)
        positive=tension>1e-7
        # Positive-definite on this larger subspace suffices on the critical cone.
        Z=null_space(J[positive],rcond=opts['rank_relative_tolerance']);eig=np.linalg.eigvalsh(Z.T@H@Z)
        sv=np.linalg.svd(J[active],compute_uv=False);rank=int(np.sum(sv>max(1e-12,(sv[0] if len(sv) else 0)*opts['rank_relative_tolerance'])))
        station=float(np.max(abs(residual)));primal=float(max(0,np.max(g))) if np.any(self.m.tendon_limited) else 0.
        comp=float(np.max(abs(tension*g)));capacity=all(tension[i]<=t['force_limit_n'] for i,t in enumerate(self.native.physics['tendons']))
        positions=[self.native.point(self.at(q),b)[0].tolist() for b in self.native.points]
        kkt=station<=opts['stationarity_tolerance_nm'] and primal<=opts['length_tolerance_m'] and comp<=opts['complementarity_tolerance_nm']
        stable=bool(not len(eig) or eig[0]>opts['minimum_reduced_eigenvalue'])
        return dict(qpos=q.tolist(),tensions_n=tension.tolist(),length_residual_m=g.tolist(),stationarity_vector_nm=residual.tolist(),
            stationarity_inf_nm=station,primal_violation_m=primal,complementarity_nm=comp,dual_violation_n=0.,
            active=active.tolist(),positive=positive.tolist(),active_rank=rank,active_singular_values=sv.tolist(),
            LICQ=rank==int(sum(active)),strict_complementarity=bool(np.all(positive[active])),
            reduced_eigenvalues=eig.tolist(),reduced_condition=float(eig[-1]/eig[0]) if len(eig) and eig[0]>0 else None,
            hessian_asymmetry=asym,H=H.tolist(),Jlength=J.tolist(),positions=positions,objective=self.objective(q),
            native_contacts=int(self.at(q).ncon),capacity=capacity,kkt_pass=bool(kkt),second_order_sufficient=stable,
            status='qualified_local_minimum' if kkt and stable and capacity and self.at(q).ncon==0 else 'unqualified',
            stability_scope='finite-difference sufficient positivity on nullspace of positive multipliers; no global or hardware certificate')


def solve(native,s=.5,force=0.,initial=None,multistart=False):
    problem=StaticProblem(native,s,force);problem.cost['equilibrium_solves']+=1;opts=native.protocol['static_solver'];n=native.model.nv
    starts=[np.zeros(n) if initial is None else np.array(initial)]
    if multistart:starts.append(starts[0]+.001*np.sin(np.arange(n)))
    trials=[]
    for start in starts:
        # SI objective is scaled uniformly for SLSQP stopping; physical KKT unscaled.
        cons=[] if native.unrestricted else [dict(type='ineq',fun=lambda q:-1000*problem.constraint(q),jac=lambda q:-1000*problem.jacobian(q))]
        result=minimize(lambda q:1000*problem.objective(q),start,jac=lambda q:1000*problem.gradient(q),
            method='SLSQP',constraints=cons,options=dict(ftol=opts['ftol'],maxiter=opts['max_iterations']))
        problem.cost['optimizer_iterations']+=int(result.nit)
        checked=problem.qualify(result.x)
        if not result.success:checked['status']='unqualified'
        checked.update(optimizer_success=bool(result.success),optimizer_message=result.message,iterations=int(result.nit),initial=start.tolist())
        trials.append(checked)
    good=[x for x in trials if x['status']=='qualified_local_minimum']
    best=min(good or trials,key=lambda x:(x['primal_violation_m'],x['stationarity_inf_nm']))
    return dict(method='passive_equilibrium_v1',s=s,force_n=force,status=best['status'],equilibrium=best,trials=trials,
        multistart_same_branch=bool(max(np.linalg.norm(np.array(x['qpos'])-best['qpos']) for x in trials)<1e-4) if multistart else None,
        numerical_cost=problem.cost,task_acceptance='unmeasured',regularization='none',
        assumptions='native 3D hinges, frictionless straight cable, rigid body gravity, ideal hard unilateral lengths; separate from MuJoCo soft constraint equilibrium')


def tangent(native,equilibrium,s,force,locations,increment=.1,direction_world=(1.,0.,0.)):
    if equilibrium['status']!='qualified_local_minimum':raise ValueError('QUALIFIED_EQUILIBRIUM_REQUIRED')
    problem=StaticProblem(native,s,force);q=np.array(equilibrium['qpos']);tension=np.array(equilibrium['tensions_n'])
    H,asym=problem.hessian(q,tension);d=problem.at(q);J=problem.jacobian(q);g=problem.constraint(q)
    Jtip=native.point(d,native.physics['tip'])[1];active=np.array(equilibrium['active']);positive=np.array(equilibrium['positive'])
    predictions=[]
    for loc in locations:
        JF=native.point(d,material_point(native.physics,loc))[1]
        for sign in (1,-1):
            rhs=np.asarray(direction_world)@JF*increment*sign;constraints=[]
            # Remove linearly dependent positive rows without changing their row space.
            if positive.any():
                _,sv,V=np.linalg.svd(J[positive],full_matrices=False);A=V[sv>max(sv[0]*1e-8,1e-12)]
                constraints.append(LinearConstraint(A,0.,0.))
            boundary=active&~positive
            if boundary.any():constraints.append(LinearConstraint(J[boundary],-np.inf,0.))
            r=minimize(lambda x:500*x@H@x-1000*rhs@x,np.zeros(native.model.nv),jac=lambda x:1000*(H@x-rhs),
                constraints=constraints,method='SLSQP',options=dict(ftol=1e-12,maxiter=200))
            problem.cost['QP_calls']+=1;problem.cost['optimizer_iterations']+=int(r.nit)
            dx=float(np.asarray(direction_world)@JF@r.x);tip=float(np.linalg.norm((Jtip@r.x)[:2]))
            predictions.append(dict(s=loc,force_increment_n=sign*increment,point_dx_m=abs(dx),tip_xy_m=tip,ratio=tip/max(abs(dx),1e-15),
                dq=r.x.tolist(),success=bool(r.success),iterations=int(r.nit),message=r.message))
    return dict(method='passive_constrained_compliance_v2',status='smooth_fixed_active_set' if equilibrium['LICQ'] and equilibrium['strict_complementarity'] else 'nonsmooth_or_degenerate',
        includes_external_geometric_hessian=True,base_force_n=force,base_s=s,predictions=predictions,numerical_cost=problem.cost,
        active_rank=equilibrium['active_rank'],H=H.tolist(),hessian_asymmetry=asym,
        caveat='finite increments are local extrapolations; slack activation and multiplier sign changes require nonlinear equilibrium solve')


def mechanics(native,condition,material_s):
    """Registered observations at a real hard equilibrium; no task acceptance."""
    load=native.load(condition);unloaded=native.load(native.problem.baseline_load)
    baseline=solve(native,unloaded.material_s,unloaded.force_world_n)
    loaded=baseline if condition==native.problem.baseline_load else solve(native,load.material_s,load.force_world_n,baseline['equilibrium']['qpos'])
    cost={k:baseline['numerical_cost'][k]+(loaded['numerical_cost'][k] if loaded is not baseline else 0) for k in baseline['numerical_cost']}
    p=StaticProblem(native,load.material_s,load.force_world_n);eq=loaded['equilibrium'];q=np.array(eq['qpos'])
    data=p.at(q);point,Jpoint,_=native.point(data,material_point(native.physics,material_s));Jtip=native.point(data,native.physics['tip'])[1]
    basepoint=native.point(p.at(np.array(baseline['equilibrium']['qpos'])),material_point(native.physics,material_s))[0]
    J=np.array(eq['Jlength']);positive=np.array(eq['positive']);active=np.array(eq['active'])
    qualified=baseline['status']==loaded['status']=='qualified_local_minimum'
    smooth=qualified and eq['LICQ'] and eq['strict_complementarity']
    Z=null_space(J[positive]);H=np.array(eq['H']);K=Z.T@H@Z
    C=Z@np.linalg.solve(K,Z.T) if smooth and K.size else np.zeros_like(H) if smooth else None
    from .passive_inverse import row_match
    matched=row_match(J[positive],Jtip)
    data=p.at(q);native.apply_force(data,load.material_s,load.force_world_n);mujoco.mj_forward(native.model,data)
    for k,v in cost.items():native.cost[k]=native.cost.get(k,0)+v+p.cost[k]
    native.cost['native_forward_calls']+=1
    return dict(physical_problem='passive_unilateral_equilibrium',time_s=0.,qpos_rad=q.tolist(),qvel_rad_s=[0.]*len(q),
        coordinates=dict(dof_order=native.physics['dofs'],tendon_order=[t['entity'] for t in native.physics['tendons']]),
        actual_tensions_n=eq['tensions_n'],input_bounds_n=[],constraint_length_jacobian=J.tolist(),
        constraint_active_set=eq['active'],constraint_multiplier=eq['tensions_n'],slack_margin=(-np.array(eq['length_residual_m'])).tolist(),
        constrained_motion_subspace=Z.tolist() if smooth else None,tangent_stiffness=K.tolist() if smooth else None,
        tangent_compliance=(Jpoint@C@Jpoint.T).tolist() if C is not None else None,
        material_point_force_response=(Jpoint@C@Jpoint.T).tolist() if C is not None else None,
        re_equilibrated_position_response=(point-basepoint).tolist() if qualified else None,
        constraint_tip_row_residual=matched['horizontal_row_residuals'],equilibrium=loaded,baseline_equilibrium=baseline,
        constraint_state=dict(status='smooth_fixed_active_set' if smooth else 'nonsmooth_or_degenerate' if qualified else 'unqualified',
            qualified=qualified,LICQ=eq['LICQ'],strict_complementarity=eq['strict_complementarity'],
            active_count=int(sum(active)),positive_count=int(sum(positive)),slack_count=int(sum(~active)),boundary_count=int(sum(active&~positive)),
            stationarity_inf_nm=eq['stationarity_inf_nm'],primal_violation_m=eq['primal_violation_m'],
            native_soft_reaction_inf_nm=float(np.max(abs(data.qfrc_constraint))),native_soft_length_residual_m=(data.ten_length-native.payout).tolist()),
        feasible_cone=dict(equalities=J[positive].tolist(),inequalities=J[active&~positive].tolist(),
            meaning='J_positive dq=0; J_boundary dq<=0. Slack rows impose no local motion equality.'),
        point_binding=dict(material_s=material_s,load=load.model_dump(mode='json'),frame='world'),
        components=dict(joint_stiffness_nm_rad=native.model.jnt_stiffness.tolist(),constraint_payout_m=native.payout.tolist()),registered_acceptance='not_registered')

