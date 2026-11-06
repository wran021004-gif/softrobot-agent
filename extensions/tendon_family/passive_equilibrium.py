"""Native potential minimization and passive KKT/tangent diagnostics, no persistence."""
import numpy as np
import mujoco
from scipy.optimize import minimize,nnls,LinearConstraint
from scipy.linalg import null_space
from .passive import material_point


class StaticProblem:
    def __init__(self,native,s=.5,force=0.):
        from .backends import MujocoFailureSnapshot
        self.native=native;self.m=native.model;self.s=s;self.force=np.asarray(force if np.ndim(force) else [force,0.,0.],dtype=float)
        self.d=mujoco.MjData(self.m);self.last=None
        self.failure=MujocoFailureSnapshot(self.m,native.physics['identity'])
        self.cost=dict(native_forward_calls=0,objective_calls=0,gradient_calls=0,constraint_calls=0,
            constraint_jacobian_calls=0,hessian_columns=0,optimizer_iterations=0,QP_calls=0,equilibrium_solves=0,KKT_solves=0,multiplier_fits=0)

    def at(self,q):
        q=np.asarray(q)
        if self.last is None or not np.array_equal(q,self.last):
            self.d.qpos[:]=q;self.d.qvel[:]=0.;self.d.qfrc_applied[:]=0.;self.d.qacc_warmstart[:]=0.
            try:self.failure.call(self.d,mujoco.mj_forward,'passive_hard_equilibrium_forward')
            except Exception as exc:
                exc.native_diagnostic=dict(kind='passive_static_forward_failure',
                    cost=dict(self.cost,model_builds=self.native.cost['model_builds'],
                        material_point_jacobian_calls=self.native.cost['material_point_jacobian_calls'],
                        tendon_jacobian_extractions=self.native.cost['tendon_jacobian_extractions'],
                        native_forward_attempts=self.cost['native_forward_calls']+1,physics_steps=0,rollouts=0),
                    scope='Partial static counters before failed forward; no dynamics or qualified equilibrium. Failed native call internal progress unknown.')
                raise
            self.last=q.copy();self.cost['native_forward_calls']+=1
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
        if np.any(active):
            tension[active]=nnls(J[active].T,-grad,maxiter=opts['multiplier_max_iterations'])[0];self.cost['multiplier_fits']+=1
        residual=grad+J.T@tension;H,asym=self.hessian(q,tension)
        positive=tension>opts['positive_multiplier_tolerance_n']
        # Positive-definite on this larger subspace suffices on the critical cone.
        Z=null_space(J[positive],rcond=opts['rank_relative_tolerance']);eig=np.linalg.eigvalsh(Z.T@H@Z)
        sv=np.linalg.svd(J[active],compute_uv=False);rank=int(np.sum(sv>max(1e-12,(sv[0] if len(sv) else 0)*opts['rank_relative_tolerance'])))
        station=float(np.max(abs(residual)));primal=float(max(0,np.max(g))) if np.any(self.m.tendon_limited) else 0.
        comp=float(np.max(abs(tension*g)));capacity=all(tension[i]<=t['force_limit_n'] for i,t in enumerate(self.native.physics['tendons']))
        positions=[self.native.point(self.at(q),b)[0].tolist() for b in self.native.points]
        kkt=station<=opts['stationarity_tolerance_nm'] and primal<=opts['length_tolerance_m'] and comp<=opts['complementarity_tolerance_nm']
        stable=bool(not len(eig) or eig[0]>opts['minimum_reduced_eigenvalue'])
        checks=dict(length_constraints=primal<=opts['length_tolerance_m'],dual_nonnegative=bool(np.all(tension>=0)),
            stationarity=station<=opts['stationarity_tolerance_nm'],complementarity=comp<=opts['complementarity_tolerance_nm'],
            tension_capacity=bool(capacity),KKT=bool(kkt),LICQ=rank==int(sum(active)),
            strict_complementarity=bool(np.all(positive[active])),second_order_sufficient=stable,contact_free=self.at(q).ncon==0)
        return dict(qpos=q.tolist(),tensions_n=tension.tolist(),length_residual_m=g.tolist(),stationarity_vector_nm=residual.tolist(),
            stationarity_inf_nm=station,primal_violation_m=primal,complementarity_nm=comp,dual_violation_n=0.,
            active=active.tolist(),positive=positive.tolist(),positive_rank=int(np.linalg.matrix_rank(J[positive],tol=max(1e-12,opts['rank_relative_tolerance']*np.linalg.norm(J[positive],ord=2)))) if positive.any() else 0,
            active_rank=rank,active_singular_values=sv.tolist(),
            LICQ=rank==int(sum(active)),strict_complementarity=bool(np.all(positive[active])),
            reduced_eigenvalues=eig.tolist(),reduced_condition=float(eig[-1]/eig[0]) if len(eig) and eig[0]>0 else None,
            hessian_asymmetry=asym,H=H.tolist(),Jlength=J.tolist(),positions=positions,objective=self.objective(q),
            native_contacts=int(self.at(q).ncon),capacity=capacity,kkt_pass=bool(kkt),second_order_sufficient=stable,qualification_checks=checks,
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
        before=dict(problem.cost)
        trial=dict(initial=start.tolist(),initial_forward_completed=False,optimizer_entered=False,stage='initial_forward')
        try:
            gap=problem.constraint(start).tolist();contacts=int(problem.at(start).ncon)
            trial.update(initial_forward_completed=True,initial_contacts=contacts,initial_length_residual_m=gap,
                optimizer_entered=True,stage='optimizer')
            result=minimize(lambda q:1000*problem.objective(q),start,jac=lambda q:1000*problem.gradient(q),
                method='SLSQP',constraints=cons,options=dict(ftol=opts['ftol'],maxiter=opts['max_iterations']))
            problem.cost['optimizer_iterations']+=int(result.nit)
            trial.update(optimizer_success=bool(result.success),optimizer_status=int(result.status),
                optimizer_message=str(result.message),iterations=int(result.nit),qpos=result.x.tolist(),stage='qualification')
            checked=problem.qualify(result.x)
        except Exception as exc:
            # Preserve the formal abort behavior and expose what was actually tried.
            trial.update(status='aborted',failure_stage=trial['stage'],reason=str(exc),
                numerical_cost={k:v-before[k] for k,v in problem.cost.items()})
            exc.equilibrium_progress=dict(trials=trials,starts_requested=len(starts),starts_attempted=len(trials)+1,
                failed_trial=trial,
                initial_forward_completed=problem.cost['native_forward_calls']>0,
                numerical_cost=dict(problem.cost))
            raise
        # Preserve PHS qualification: independent physical KKT/second-order
        # checks, not SLSQP's line-search flag, establish numerical eligibility.
        # A failed solver termination remains explicit alongside those checks.
        checked['solver_termination']='converged' if result.success else 'nonconverged_numerically_qualified' if checked['status']=='qualified_local_minimum' else 'nonconverged_unqualified'
        checked.update(trial,stage='completed',status=checked['status'],
            numerical_cost={k:v-before[k] for k,v in problem.cost.items()})
        trials.append(checked)
    good=[x for x in trials if x['status']=='qualified_local_minimum']
    best=min(good or trials,key=lambda x:(x['primal_violation_m'],x['stationarity_inf_nm']))
    return dict(method='passive_equilibrium_v1',s=s,force_n=force,status=best['status'],equilibrium=best,trials=trials,
        multistart_same_branch=bool(max(np.linalg.norm(np.array(x['qpos'])-best['qpos']) for x in trials)<1e-4) if multistart else None,
        numerical_cost=problem.cost,solver_settings=dict(opts),task_acceptance='unmeasured',regularization='none',
        assumptions='native 3D hinges, frictionless straight cable, rigid body gravity, ideal hard unilateral lengths; separate from MuJoCo soft constraint equilibrium')


def qualification_diagnosis(result=None, *, failure=None, multistart=False):
    """Physical eligibility facts, never a structural infeasibility conclusion."""
    progress=getattr(failure,'equilibrium_progress',{}) if failure is not None else {}
    trials=(result or progress).get('trials',[]);eq=(result or {}).get('equilibrium')
    qualified=bool(eq and eq['status']=='qualified_local_minimum')
    snapshot=getattr(failure,'mujoco_diagnostic',{}) if failure is not None else {}
    collision=snapshot.get('partial_failed_call_observations',{})
    rows=[{k:t[k] for k in ('status','solver_termination','initial','initial_forward_completed','optimizer_entered','stage',
        'optimizer_status','optimizer_success','optimizer_message','iterations',
        'initial_contacts','initial_length_residual_m','native_contacts','length_residual_m','stationarity_inf_nm',
        'primal_violation_m','dual_violation_n','complementarity_nm','kkt_pass','capacity','LICQ','strict_complementarity',
        'second_order_sufficient','qualification_checks','numerical_cost') if k in t} for t in trials]
    initial_failure=failure is not None and not progress.get('initial_forward_completed',False)
    if failure is not None:
        rows.append({**progress.get('failed_trial',{}),
            'status':'initial_forward_failure' if initial_failure else 'numerically_unresolved',
            'solver_termination':'aborted','termination_error':str(failure)})
    status=('qualified' if qualified else 'initial_forward_failure' if initial_failure else
        'numerically_unresolved' if failure is not None or any(not t['optimizer_success'] for t in trials) else 'unqualified')
    layers=[]
    if failure is not None:layers.append('initial_forward_failure' if initial_failure else 'numerical_solver_failure')
    if any(t.get('initial_contacts',0) or t.get('native_contacts',0) for t in trials):layers.append('contact')
    if collision.get('ncon',0):layers.append('contact_observed_after_failed_forward')
    if any(not t['optimizer_success'] for t in trials):layers.append('equilibrium_nonconvergence')
    if any(t['primal_violation_m']>(result or {}).get('solver_settings',{}).get('length_tolerance_m',0.) for t in trials):layers.append('unilateral_length_violation')
    if eq and not eq['kkt_pass']:layers.append('KKT_not_qualified')
    if eq and not eq['capacity']:layers.append('tension_capacity')
    if eq and not eq['second_order_sufficient']:layers.append('reduced_stiffness_not_positive')
    return dict(status=status,qualified=qualified,starts_requested=progress.get('starts_requested',2 if multistart else 1),
        starts_attempted=progress.get('starts_attempted',len(trials)),trials=rows,
        starts_skipped_after_abort=progress.get('starts_requested',0)-progress.get('starts_attempted',0),
        failure_layers=layers,initial_forward_completed=not initial_failure,
        failure_stage=progress.get('failed_trial',{}).get('failure_stage'),
        numerical_failure=snapshot or None,
        failed_forward_geometry=({k:collision[k] for k in ('ncon','nefc','valid_complete_state','interpretation') if k in collision} if collision else None),
        termination_error=str(failure) if failure is not None else None,
        best_working_point=({k:eq[k] for k in ('kkt_pass','capacity','second_order_sufficient','native_contacts','LICQ','strict_complementarity',
            'stationarity_inf_nm','primal_violation_m','dual_violation_n','complementarity_nm','qualification_checks') if k in eq} if eq else None),
        stability_qualified=bool(qualified and eq['second_order_sufficient']),
        valid_followup=['local unilateral mechanism','finite-deformation comparison','independent complete dynamics'] if qualified else
            ['legal initialization comparison','constraint geometry and payout','taut/slack branch diagnosis'],
        unresolved_explanations=[] if qualified else ['constraint geometry','unilateral branch changes','solver failure to find a qualified point'],
        task_acceptance='unmeasured',
        scope='Frozen hard-equilibrium eligibility only. Unqualified-point stiffness/gradients do not prove stability or structural infeasibility; dynamic qualification and task acceptance remain independent.')


def tangent(native,equilibrium,s,force,locations,increment=.1,direction_world=(1.,0.,0.)):
    if equilibrium['status']!='qualified_local_minimum':raise ValueError('QUALIFIED_EQUILIBRIUM_REQUIRED')
    problem=StaticProblem(native,s,force);q=np.array(equilibrium['qpos']);tension=np.array(equilibrium['tensions_n'])
    opts=native.protocol['static_solver']
    H,asym=problem.hessian(q,tension);d=problem.at(q);J=problem.jacobian(q);g=problem.constraint(q)
    Jtip=native.point(d,native.physics['tip'])[1];active=np.array(equilibrium['active']);positive=np.array(equilibrium['positive'])
    predictions=[]
    for loc in locations:
        JF=native.point(d,material_point(native.physics,loc))[1]
        for sign in (1,-1):
            rhs=np.asarray(direction_world)@JF*increment*sign;constraints=[]
            # Remove linearly dependent positive rows without changing their row space.
            if positive.any():
                _,sv,V=np.linalg.svd(J[positive],full_matrices=False);A=V[sv>max(sv[0]*opts['rank_relative_tolerance'],1e-12)]
                constraints.append(LinearConstraint(A,0.,0.))
            boundary=active&~positive
            if boundary.any():constraints.append(LinearConstraint(J[boundary],-np.inf,0.))
            r=minimize(lambda x:500*x@H@x-1000*rhs@x,np.zeros(native.model.nv),jac=lambda x:1000*(H@x-rhs),
                constraints=constraints,method='SLSQP',options=dict(ftol=opts['qp_ftol'],maxiter=opts['qp_max_iterations']))
            problem.cost['QP_calls']+=1;problem.cost['optimizer_iterations']+=int(r.nit)
            dx=float(np.asarray(direction_world)@JF@r.x);tip=float(np.linalg.norm((Jtip@r.x)[:2]))
            predictions.append(dict(s=loc,force_increment_n=sign*increment,point_dx_m=abs(dx),tip_xy_m=tip,ratio=tip/max(abs(dx),1e-15),
                point_response_m=(JF@r.x).tolist(),tip_response_m=(Jtip@r.x).tolist(),
                dq=r.x.tolist(),success=bool(r.success),iterations=int(r.nit),message=r.message))
    return dict(method='passive_constrained_compliance_v2',status='smooth_fixed_active_set' if equilibrium['LICQ'] and equilibrium['strict_complementarity'] else 'nonsmooth_or_degenerate',
        includes_external_geometric_hessian=True,base_force_n=force,base_s=s,predictions=predictions,numerical_cost=problem.cost,
        active_rank=equilibrium['active_rank'],H=H.tolist(),hessian_asymmetry=asym,
        caveat='finite increments are local extrapolations; slack activation and multiplier sign changes require nonlinear equilibrium solve')


def mechanics(native,condition,material_s,initial=None,direction_world=None,*,baseline_result=None,unloaded_multistart=False,qualification_only=False):
    """Registered observations at a real hard equilibrium; no task acceptance."""
    load=native.load(condition);unloaded=native.load(native.problem.baseline_load)
    try:
        baseline=baseline_result if baseline_result is not None else solve(native,unloaded.material_s,unloaded.force_world_n,
            initial[0] if initial else None,multistart=unloaded_multistart)
    except Exception as exc:
        if not qualification_only or not hasattr(exc,'equilibrium_progress'):raise
        for k,v in exc.equilibrium_progress['numerical_cost'].items():native.cost[k]=native.cost.get(k,0)+v
        native.cost['native_forward_attempts']=native.cost['native_forward_calls']+1
        return dict(physical_problem='passive_unilateral_equilibrium',equilibrium=None,baseline_equilibrium=None,
            constraint_state=dict(status='unqualified',qualified=False),task_observations=[],
            point_binding=dict(material_s=material_s,load=unloaded.model_dump(mode='json'),frame='world'),
            qualification_diagnosis=qualification_diagnosis(failure=exc,multistart=unloaded_multistart))
    loaded=baseline if condition==native.problem.baseline_load else solve(native,load.material_s,load.force_world_n,initial[1] if initial else baseline['equilibrium']['qpos'])
    cost={k:(baseline['numerical_cost'][k] if baseline_result is None else 0)+(loaded['numerical_cost'][k] if loaded is not baseline else 0) for k in baseline['numerical_cost']}
    p=StaticProblem(native,load.material_s,load.force_world_n);eq=loaded['equilibrium'];q=np.array(eq['qpos'])
    data=p.at(q);point,Jpoint,_=native.point(data,material_point(native.physics,material_s));Jtip=native.point(data,native.physics['tip'])[1]
    basepoint=native.point(p.at(np.array(baseline['equilibrium']['qpos'])),material_point(native.physics,material_s))[0]
    J=np.array(eq['Jlength']);positive=np.array(eq['positive']);active=np.array(eq['active'])
    qualified=baseline['status']==loaded['status']=='qualified_local_minimum'
    smooth=qualified and eq['LICQ'] and eq['strict_complementarity']
    Z=null_space(J[positive]);H=np.array(eq['H']);K=Z.T@H@Z
    C=Z@np.linalg.solve(K,Z.T) if smooth and K.size else np.zeros_like(H) if smooth else None
    increment=native.protocol['static_solver']['qp_increment_n']
    response=tangent(native,eq,load.material_s,load.force_world_n,[material_s],increment=increment,direction_world=direction_world) if qualified and direction_world is not None else None
    if response:
        for key,value in response['numerical_cost'].items():cost[key]+=value
    data=p.at(q);native.apply_force(data,load.material_s,load.force_world_n);mujoco.mj_forward(native.model,data)
    for k,v in cost.items():native.cost[k]=native.cost.get(k,0)+v+p.cost[k]
    native.cost['native_forward_calls']+=1
    return dict(physical_problem='passive_unilateral_equilibrium',time_s=0.,qpos_rad=q.tolist(),qvel_rad_s=[0.]*len(q),
        coordinates=dict(dof_order=native.physics['dofs'],tendon_order=[t['entity'] for t in native.physics['tendons']]),
        actual_tensions_n=eq['tensions_n'],input_bounds_n=[],constraint_length_jacobian=J.tolist(),
        material_point_jacobian_m_rad=Jpoint.tolist(),
        constraint_active_set=eq['active'],constraint_multiplier=eq['tensions_n'],slack_margin=(-np.array(eq['length_residual_m'])).tolist(),
        constraint_boundary_set=(active&~positive).tolist(),constraint_slack_set=(~active).tolist(),
        constraint_tension_margin_n=[t['force_limit_n']-v for t,v in zip(native.physics['tendons'],eq['tensions_n'])],
        constrained_motion_subspace=Z.tolist() if smooth else None,tangent_stiffness=K.tolist() if smooth else None,
        tangent_compliance=(Jpoint@C@Jpoint.T).tolist() if C is not None else None,
        directional_material_response=(np.array([r['point_response_m'] for r in response['predictions']])/increment).tolist() if response and all(r['success'] for r in response['predictions']) else None,
        directional_response=response,
        re_equilibrated_position_response=(point-basepoint).tolist() if qualified else None,
        equilibrium=loaded,baseline_equilibrium=baseline,
        qualification_diagnosis=qualification_diagnosis(baseline,multistart=unloaded_multistart),
        tip_jacobian_m_rad=Jtip.tolist(),tendon_jacobian_m_rad=J.tolist(),
        constraint_state=dict(status='smooth_fixed_active_set' if smooth else 'nonsmooth_or_degenerate' if qualified else 'unqualified',
            qualified=qualified,LICQ=eq['LICQ'],strict_complementarity=eq['strict_complementarity'],
            optimizer_success=eq['optimizer_success'],solver_termination=eq['solver_termination'],
            maximum_constraint_tension_n=float(np.max(eq['tensions_n'])),minimum_slack_margin_m=float(np.min(-np.array(eq['length_residual_m']))),
            within_declared_tendon_capacity=eq['capacity'],
            minimum_reduced_stiffness_nm_rad=min(eq['reduced_eigenvalues'],default=None),
            active_count=int(sum(active)),positive_count=int(sum(positive)),slack_count=int(sum(~active)),boundary_count=int(sum(active&~positive)),
            stationarity_inf_nm=eq['stationarity_inf_nm'],primal_violation_m=eq['primal_violation_m'],
            native_soft_reaction_inf_nm=float(np.max(abs(data.qfrc_constraint))),native_soft_length_residual_m=(data.ten_length-native.payout).tolist()),
        feasible_cone=dict(equalities=J[positive].tolist(),inequalities=J[active&~positive].tolist(),
            meaning='J_positive dq=0; J_boundary dq<=0. Slack rows impose no local motion equality.'),
        point_binding=dict(material_s=material_s,load=load.model_dump(mode='json'),frame='world'),
        components=dict(joint_stiffness_nm_rad=native.model.jnt_stiffness.tolist(),damping_nm_s_rad=native.model.dof_damping.tolist(),
            constraint_payout_m=native.payout.tolist()),registered_acceptance='not_registered')

