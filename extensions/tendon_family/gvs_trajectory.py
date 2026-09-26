"""Trusted fixed-design GVS dynamic transcription and reusable NMPC workspace."""
import time
import casadi as ca
import numpy as np
from schemas.platform import Binding, Objective, Payload
from schemas.platform_math import OptimizationConstraint, OptimizationProblem, SystemContext
from extensions.optimization.ipopt import IpoptSolver, expression_payload
from .contracts import GVSModelParameters, GVSTrajectoryParameters
from .gvs import GVSModel, coordinate_order
from .gvs_casadi import expression_from_system, functions_for
from .pcc import quaternion_wxyz_to_rotation


def implicit_step_residual(functions,n,m,h):
    """Shared shooting and tail-initialization residual in physical coordinates."""
    previous=ca.MX.sym('previous_state',2*n);following=ca.MX.sym('next_state',2*n)
    tension=ca.MX.sym('tension',m)
    return ca.Function('gvs_implicit_step_residual',[previous,following,tension],
        [ca.vertcat((following[:n]-previous[:n]-h*following[n:])/10.,
            functions.implicit_residual(following,tension,(following[n:]-previous[n:])/h)/.001)],
        {'jac_penalty':0})



def trajectory_authorization(robot, space, parameters):
    p=GVSTrajectoryParameters.model_validate(parameters)
    coordinates=coordinate_order(robot.structure.data,p.basis); n=len(coordinates)
    result={}
    for k in range(p.horizon*p.substeps+1):
        for j in range(2*n):
            result[f'x/{k}/{j}']=dict(type='number',bounds=[None,None],units='1',
                physical_coordinate=coordinates[j%n]+('.rate' if j>=n else ''),
                physical_scale=p.curvature_scale_rad_m if j<n else p.rate_scale_rad_m_s,
                physical_units='rad/m' if j<n else 'rad/(m*s)')
    for k in range(p.horizon):
        for t in robot.structure.data['tendons']:
            result[f'u/{k}/{t["id"]}']=dict(type='number',bounds=[0.,t['force_limit_n']],units='N')
    for t in robot.structure.data['tendons']:
        result['previous_u/'+t['id']]=dict(type='number',bounds=[0.,t['force_limit_n']],units='N')
    return result


class GVSTrajectoryAssembler:
    def __init__(self,parameters): self.parameters=GVSTrajectoryParameters.model_validate(parameters)

    def assemble(self,task,robot,space,mathematical_model,specification,context):
        p=self.parameters
        expected=trajectory_authorization(robot,{},p)
        if specification.variables!=list(expected) or space!=expected:
            raise ValueError('GVS_TRAJECTORY_REQUIRES_FIXED_DESIGN_ORDER_AND_PHYSICAL_BOUNDS')
        if specification.horizon!=p.horizon or [s.template_id for s in specification.objectives]!=['dynamic_tip_tracking']:
            raise ValueError('GVS_TRAJECTORY_SPECIFICATION_MISMATCH')
        if {s.template_id for s in specification.constraints}!={'initial_state','implicit_dynamics','tendon_force_bounds'}:
            raise ValueError('GVS_TRAJECTORY_CONSTRAINTS_REQUIRED')
        n=len(coordinate_order(robot.structure.data,p.basis))
        m=len(robot.structure.data['tendons'])
        if len(context.x0)!=2*n or len(context.u0)!=m:
            raise ValueError('GVS_TRAJECTORY_INITIAL_STATE_AND_PREVIOUS_TENSION_REQUIRED: '
                f'context.x0 requires {2*n} [q,qdot] values; context.u0 requires {m} tendon tensions')
        model_params=GVSModelParameters(basis=p.basis)
        system=GVSModel(model_params).build_system(robot,model_params,None,SystemContext(
            x0=context.x0,u0=context.u0,scene=task.environment))
        functions=functions_for(expression_from_system(system))
        steps=p.horizon*p.substeps
        decision_symbols={name:ca.MX.sym('v_'+str(i)) for i,name in enumerate(expected)}
        symbols={name:value*expected[name].get('physical_scale',1.) for name,value in decision_symbols.items()}
        X=[ca.vertcat(*[symbols[f'x/{k}/{j}'] for j in range(2*n)]) for k in range(steps+1)]
        tendons=[t['id'] for t in robot.structure.data['tendons']]
        U=[ca.vertcat(*[symbols[f'u/{k}/{t}'] for t in tendons]) for k in range(p.horizon)]
        previous=ca.vertcat(*[symbols['previous_u/'+t] for t in tendons])
        assembly=task.environment.data; rotation=quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
        local_tip=ca.Function('local_tip',[functions.q_symbol],[functions.tip_position_expression])
        target=ca.DM(task.goal.data['target_m']); mount=ca.DM(assembly['mount']['position_m'])
        dt=task.timing.control_period_s; h=dt/p.substeps; constraints={}; objective=0
        if task.evaluator.extension_id!='evaluate.reach':
            raise ValueError('GVS_TRAJECTORY_REQUIRES_REACH_EVALUATOR')
        tolerance=task.evaluator.parameters.data['tolerance_m']
        step_residual=implicit_step_residual(functions,n,m,h)
        mapped=step_residual.map(steps,'thread',p.evaluation_threads)
        residuals=mapped(ca.horzcat(*X[:-1]),ca.horzcat(*X[1:]),
            ca.horzcat(*[U[k//p.substeps] for k in range(steps)]))
        for k in range(steps):
            x,y,u=X[k],X[k+1],U[k//p.substeps]
            residual=residuals[:,k]
            for j in range(2*n): constraints[f'dynamics_{k}_{j}']=residual[j]
            tip=ca.mtimes(ca.DM(rotation),local_tip(y[:n]))+mount
            objective+=h*(p.tracking_weight*ca.sumsqr((tip-target)/tolerance)+p.velocity_weight*ca.sumsqr(y[n:]))
        for k,u in enumerate(U):
            objective+=dt*(p.tension_weight*ca.sumsqr(u)+p.variation_weight*ca.sumsqr(u-(previous if k==0 else U[k-1])))
        objective+=p.terminal_weight*ca.sumsqr((tip-target)/tolerance)+p.terminal_velocity_weight*ca.sumsqr(X[-1][n:])
        objective*=specification.objectives[0].weight
        bundle,selectors=expression_payload(list(expected),dict(variables=decision_symbols,expression=objective),constraints)
        variables={name:dict(spec) for name,spec in expected.items()}
        for j,value in enumerate(context.x0):
            scale=variables[f'x/0/{j}']['physical_scale'];variables[f'x/0/{j}']['bounds']=[value/scale,value/scale]
        for t,value in zip(tendons,context.u0): variables['previous_u/'+t]['bounds']=[value,value]
        guess=dict(specification.initial_guess)
        for t,value in zip(tendons,context.u0):guess['previous_u/'+t]=value
        for k in range(steps+1):
            for j,value in enumerate(context.x0):guess.setdefault(f'x/{k}/{j}',value/variables[f'x/{k}/{j}']['physical_scale'])
        for k in range(p.horizon):
            for t,value in zip(tendons,context.u0): guess.setdefault(f'u/{k}/{t}',value)
        return OptimizationProblem(variables=variables,objective=Objective(metric='gvs_dynamic_tracking_cost',direction='minimize',units='dimensionless'),
            objective_function=bundle,constraints=[OptimizationConstraint(name=name,expression=selector,units='scaled_residual',lower=0.,upper=0.)
                for name,selector in zip(constraints,selectors)],initial_guess=guess,horizon=p.horizon,
            model_reference=Binding(extension_id='model.gvs',parameters=Payload(contract='family.gvs_model',data=model_params.model_dump(mode='json'))))


class TrajectoryWorkspace:
    """One graph and IPOPT instance; each update changes fixed initial bounds."""
    def __init__(self,task,robot,parameters,nominal_x,nominal_u):
        from tools.platform_registry import registry
        from tools.platform_optimization import assemble_optimization
        from schemas.platform_math import OptimizationSpecification, ObjectiveSelection, ConstraintSelection
        self.parameters=GVSTrajectoryParameters.model_validate(parameters); self.n=len(nominal_x)//2
        self.state_scales=np.r_[np.full(self.n,self.parameters.curvature_scale_rad_m),
            np.full(self.n,self.parameters.rate_scale_rad_m_s)]
        self.m=len(nominal_u);self.nominal_x=list(nominal_x);self.nominal_u=list(nominal_u)
        self.tendons=[t['id'] for t in robot.structure.data['tendons']]
        self.period=task.timing.control_period_s; self.target=task.goal.data['target_m']
        self.goal_tolerance=task.evaluator.parameters.data['tolerance_m']
        reg=registry();start=time.perf_counter()
        binding=Binding(extension_id='optimization_assembler.gvs_trajectory',parameters=Payload(
            contract='family.gvs_trajectory_parameters',data=self.parameters.model_dump(mode='json')))
        space=trajectory_authorization(robot,{},self.parameters)
        self.problem=assemble_optimization(reg,binding,task=task,robot=robot,space=space,
            mathematical_model=GVSModelParameters(basis=self.parameters.basis).mathematical_model,
            specification=OptimizationSpecification(variables=list(space),horizon=self.parameters.horizon,
                objectives=[ObjectiveSelection(template_id='dynamic_tip_tracking')],constraints=[ConstraintSelection(template_id=k)
                    for k in ('initial_state','implicit_dynamics','tendon_force_bounds')]),
            context=SystemContext(x0=nominal_x,u0=nominal_u,scene=task.environment))
        self.graph_s=time.perf_counter()-start
        self.solver=IpoptSolver(dict(max_iterations=self.parameters.max_iterations,tolerance=self.parameters.tolerance,
            max_cpu_s=self.parameters.max_cpu_s,retain_feasible_iterate=True,
            feasible_return=self.parameters.feasible_return,
            constraint_jacobian_mode=self.parameters.constraint_jacobian_mode))
        self.robot=robot;self.scene=task.environment;self._tail_solver=None
        self.last=None

    def _extend_tail(self,state,tension,guess=None):
        construction=time.perf_counter()
        if self._tail_solver is None:
            p=GVSModelParameters(basis=self.parameters.basis)
            system=GVSModel(p).build_system(self.robot,p,None,SystemContext(
                x0=self.nominal_x,u0=self.nominal_u,scene=self.scene))
            functions=functions_for(expression_from_system(system))
            q=functions.q_symbol;v=ca.MX.sym('motion_rate',self.n)
            local_tip=functions.tip_position_expression
            assembly=self.scene.data
            world_tip=ca.mtimes(ca.DM(quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])),local_tip)+ca.DM(assembly['mount']['position_m'])
            self._motion=ca.Function('warm_tip_motion',[q,v],[world_tip,ca.jacobian(world_tip,q)@v])
            self._tail_residual=implicit_step_residual(functions,self.n,self.m,self.period/self.parameters.substeps)
            y=ca.MX.sym('scaled_next',2*self.n);old=ca.MX.sym('old',2*self.n);u=ca.MX.sym('u',self.m)
            residual=ca.Function('tail_residual',[y,old,u],
                [self._tail_residual(old,y*self.state_scales,u)],{'ad_weight':1.})
            self._tail_solver=ca.rootfinder('tail_step','newton',residual,{'abstol':1e-10,'max_iter':30})
        construction_s=time.perf_counter()-construction
        start=time.perf_counter()
        repeated_defect=float(np.max(abs(np.asarray(self._tail_residual(state,state,tension)))))
        following=np.asarray(self._tail_solver(np.asarray(state if guess is None else guess)/self.state_scales,state,tension)).ravel()*self.state_scales
        defect=float(np.max(abs(np.asarray(self._tail_residual(state,following,tension)))))
        return following,dict(construction_s=construction_s,integration_s=time.perf_counter()-start,
            repeated_terminal_scaled_defect=repeated_defect,extended_tail_scaled_defect=defect)

    def solve(self,measured_x,previous_u,warm=None):
        update_start=time.perf_counter()
        for j,value in enumerate(measured_x):self.problem.variables[f'x/0/{j}']['bounds']=[float(value)/self.state_scales[j]]*2
        for t,value in zip(self.tendons,previous_u): self.problem.variables['previous_u/'+t]['bounds']=[float(value)]*2
        source=warm if warm is not None else self.last
        tails=[]
        if source is not None:
            X=np.asarray(source['states']);U=np.asarray(source['tensions']);s=0 if warm is not None else self.parameters.substeps
            # An explicit warm seed already starts at the current horizon. The
            # last plan has executed exactly one command interval (s nodes).
            if s:
                X=np.concatenate([X[s:],np.repeat(X[-1:],s,axis=0)])
                U=np.concatenate([U[1:],U[-1:]])
                if not self.parameters.regenerate_warm_states:
                    for k in range(len(X)-s,len(X)):
                        X[k],diagnostic=self._extend_tail(X[k-1],U[-1]);tails.append(diagnostic)
            if self.parameters.regenerate_warm_states:
                X=X.copy();X[0]=measured_x
                for k in range(1,len(X)):
                    X[k],diagnostic=self._extend_tail(X[k-1],U[(k-1)//self.parameters.substeps],X[k])
                    tails.append(diagnostic)
            for k in range(len(X)):
                for j in range(2*self.n):self.problem.initial_guess[f'x/{k}/{j}']=float(X[k,j])/self.state_scales[j]
            for k in range(len(U)):
                for j,t in enumerate(self.tendons):self.problem.initial_guess[f'u/{k}/{t}']=float(U[k,j])
        elif self.parameters.regenerate_warm_states:
            state=np.asarray(measured_x)
            for k in range(self.parameters.horizon):
                for t,value in zip(self.tendons,previous_u):self.problem.initial_guess[f'u/{k}/{t}']=float(value)
            for k in range(1,self.parameters.horizon*self.parameters.substeps+1):
                state,diagnostic=self._extend_tail(state,previous_u);tails.append(diagnostic)
                for j,value in enumerate(state):self.problem.initial_guess[f'x/{k}/{j}']=float(value)/self.state_scales[j]
        for j,value in enumerate(measured_x):self.problem.initial_guess[f'x/0/{j}']=float(value)/self.state_scales[j]
        for t,value in zip(self.tendons,previous_u):self.problem.initial_guess['previous_u/'+t]=float(value)
        preparation_s=time.perf_counter()-update_start
        seed_settled=False
        if self.parameters.feasible_return is not None and self._tail_solver is not None:
            metrics=[]
            for k in range(self.parameters.horizon*self.parameters.substeps+1):
                state=np.array([self.problem.initial_guess[f'x/{k}/{j}'] for j in range(2*self.n)])*self.state_scales
                tip,speed=self._motion(state[:self.n],state[self.n:])
                metrics.append((np.linalg.norm(np.asarray(tip).ravel()-self.target),np.linalg.norm(np.asarray(speed))))
            seed_settled=all(e<=.5*self.goal_tolerance and v<=.02 for e,v in metrics)
        preparation_s=time.perf_counter()-update_start
        start=time.perf_counter(); result=self.solver.solve(self.problem,seed_settled=seed_settled);total=time.perf_counter()-start
        values=result.optimum;steps=self.parameters.horizon*self.parameters.substeps
        X=np.array([[values[f'x/{k}/{j}']*self.state_scales[j] for j in range(2*self.n)] for k in range(steps+1)])
        U=np.array([[values[f'u/{k}/{t}'] for t in self.tendons] for k in range(self.parameters.horizon)])
        output=dict(states=X.tolist(),tensions=U.tolist(),result=result.model_dump(mode='json'),
            decision_state_scales=self.state_scales.tolist(),
            diagnostics=self.solver.last_diagnostics,total_s=total,graph_s=self.graph_s,
            warm_start=dict(executed_intervals=int(source is not None and warm is None),
                preparation_s=preparation_s,regenerated_all_states=self.parameters.regenerate_warm_states,seed_settled=seed_settled,tail_initialization=tails),
            nominal_operating_state=self.nominal_x,measured_initial_state=list(measured_x),
            previous_tensions_n=list(previous_u),
            period_s=self.period,substeps=self.parameters.substeps,
            integration='implicit Euler in mass/force form; q scale 10 rad/m, force scale .001 N*m^2/rad',
            cost='Stage weights per second on squared tip/tolerance, curvature rate/(1 rad/(m*s)), tension/(1 N) and delta tension/(1 N); terminal weights on squared tip/tolerance and curvature rate. Smoothing is a design penalty.')
        # A feasible finite-iteration plan can drive suboptimal NMPC. Keep its
        # nonconverged solver status; feasibility never implies optimality.
        accepted=result.status in ('converged','iteration_limit','feasible_early_stop') and result.constraint_violation<=1e-5
        output['accepted']=accepted
        output['optimization_converged']=result.status=='converged'
        # A finite unfinished iterate is still a useful next optimization guess.
        # Command acceptance remains the separate, stricter feasibility check.
        if result.status in ('converged','iteration_limit','feasible_early_stop'):self.last=output
        output['update_wall_s']=time.perf_counter()-update_start
        return output
