"""Trusted fixed-design GVS dynamic transcription and reusable NMPC workspace."""
import time
from contextvars import ContextVar
from contextlib import contextmanager
import casadi as ca
import numpy as np
from schemas.platform import Binding, Objective, Payload
from schemas.platform_math import OptimizationConstraint, OptimizationProblem, SystemContext
from extensions.optimization.ipopt import IpoptSolver, expression_payload
from .contracts import GVSModelParameters, GVSTrajectoryParameters
from .gvs import GVSModel, coordinate_order
from .gvs_casadi import expression_from_system, functions_for
from .pcc import quaternion_wxyz_to_rotation


_FUNCTION_PROVIDER=ContextVar('gvs_trajectory_function_provider',default=None)


@contextmanager
def use_trajectory_functions(provider):
    """Execution-scoped experimental evaluator; default production is unchanged."""
    token=_FUNCTION_PROVIDER.set(provider)
    try:yield
    finally:_FUNCTION_PROVIDER.reset(token)


def trajectory_functions(expression):
    original=functions_for(expression);provider=_FUNCTION_PROVIDER.get()
    return original if provider is None else provider(original)


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
    if p.holding_tip_speed_weight:
        for k in range(1,p.horizon*p.substeps+1):
            result[f'holding/{k}']=dict(type='number',bounds=[0.,1.],units='1')
    return result


def tracking_authorization(robot, space, parameters):
    result=trajectory_authorization(robot,space,parameters)
    p=GVSTrajectoryParameters.model_validate(parameters)
    for k in range(1,p.horizon*p.substeps+1):
        for quantity,unit in (('position','m'),('velocity','m/s')):
            for j in range(3):
                result[f'reference/{quantity}/{k}/{j}']=dict(type='number',bounds=[0.,0.],units=unit)
    return result


class GVSTrajectoryAssembler:
    def __init__(self,parameters): self.parameters=GVSTrajectoryParameters.model_validate(parameters)

    def assemble(self,task,robot,space,mathematical_model,specification,context):
        p=self.parameters
        tracking=task.family=='task.tracking'
        expected=(tracking_authorization if tracking else trajectory_authorization)(robot,{},p)
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
        functions=trajectory_functions(expression_from_system(system))
        steps=p.horizon*p.substeps
        decision_symbols={name:ca.MX.sym('v_'+str(i)) for i,name in enumerate(expected)}
        symbols={name:value*expected[name].get('physical_scale',1.) for name,value in decision_symbols.items()}
        X=[ca.vertcat(*[symbols[f'x/{k}/{j}'] for j in range(2*n)]) for k in range(steps+1)]
        tendons=[t['id'] for t in robot.structure.data['tendons']]
        U=[ca.vertcat(*[symbols[f'u/{k}/{t}'] for t in tendons]) for k in range(p.horizon)]
        previous=ca.vertcat(*[symbols['previous_u/'+t] for t in tendons])
        assembly=task.environment.data; rotation=quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
        local_tip=ca.Function('local_tip',[functions.q_symbol],[functions.tip_position_expression])
        tip_rate=ca.MX.sym('tip_rate',n)
        local_velocity=ca.Function('local_tip_velocity',[functions.q_symbol,tip_rate],
            [ca.jacobian(functions.tip_position_expression,functions.q_symbol)@tip_rate]) if tracking or p.terminal_tip_speed_weight or p.holding_tip_speed_weight else None
        target=None if tracking else ca.DM(task.goal.data['target_m']); mount=ca.DM(assembly['mount']['position_m'])
        dt=task.timing.control_period_s; h=dt/p.substeps; constraints={}; objective=0
        if task.evaluator.extension_id!=('evaluate.tracking' if tracking else 'evaluate.reach'):
            raise ValueError('GVS_TRAJECTORY_REQUIRES_REACH_EVALUATOR')
        tolerance=p.position_error_scale_m or task.evaluator.parameters.data['max_position_error_m' if tracking else 'tolerance_m']
        step_residual=implicit_step_residual(functions,n,m,h)
        mapped=step_residual.map(steps,'thread',p.evaluation_threads)
        residuals=mapped(ca.horzcat(*X[:-1]),ca.horzcat(*X[1:]),
            ca.horzcat(*[U[k//p.substeps] for k in range(steps)]))
        for k in range(steps):
            x,y,u=X[k],X[k+1],U[k//p.substeps]
            residual=residuals[:,k]
            for j in range(2*n): constraints[f'dynamics_{k}_{j}']=residual[j]
            tip=ca.mtimes(ca.DM(rotation),local_tip(y[:n]))+mount
            if tracking:
                target=ca.vertcat(*[symbols[f'reference/position/{k+1}/{j}'] for j in range(3)])
                target_velocity=ca.vertcat(*[symbols[f'reference/velocity/{k+1}/{j}'] for j in range(3)])
                velocity_error=ca.mtimes(ca.DM(rotation),local_velocity(y[:n],y[n:]))-target_velocity
            objective+=h*(p.tracking_weight*ca.sumsqr((tip-target)/tolerance)+p.velocity_weight*ca.sumsqr(velocity_error/p.tip_speed_scale_m_s if tracking else y[n:]))
            if p.holding_tip_speed_weight:
                speed=ca.mtimes(ca.DM(rotation),local_velocity(y[:n],y[n:]))
                objective+=h*p.holding_tip_speed_weight*symbols[f'holding/{k+1}']*ca.sumsqr(speed/p.tip_speed_scale_m_s)
        for k,u in enumerate(U):
            objective+=dt*(p.tension_weight*ca.sumsqr(u)+p.variation_weight*ca.sumsqr(u-(previous if k==0 else U[k-1])))
        objective+=p.terminal_weight*ca.sumsqr((tip-target)/tolerance)+p.terminal_velocity_weight*ca.sumsqr(velocity_error/p.tip_speed_scale_m_s if tracking else X[-1][n:])
        if local_velocity is not None:
            world_velocity=ca.mtimes(ca.DM(rotation),local_velocity(X[-1][:n],X[-1][n:]))
            objective+=p.terminal_tip_speed_weight*ca.sumsqr((world_velocity-target_velocity if tracking else world_velocity)/p.tip_speed_scale_m_s)
        objective*=specification.objectives[0].weight
        bundle,selectors=expression_payload(list(expected),dict(variables=decision_symbols,expression=objective),constraints)
        variables={name:dict(spec) for name,spec in expected.items()}
        for j,value in enumerate(context.x0):
            scale=variables[f'x/0/{j}']['physical_scale'];variables[f'x/0/{j}']['bounds']=[value/scale,value/scale]
        for t,value in zip(tendons,context.u0): variables['previous_u/'+t]['bounds']=[value,value]
        # These are fixed scheduling inputs, never optimized decisions. Generic
        # assembly starts at task time zero with no hold enabled; the workspace
        # fixes them from explicit execution time and acceptance configuration.
        if p.holding_tip_speed_weight:
            for k in range(1,steps+1):variables[f'holding/{k}']['bounds']=[0.,0.]
        guess=dict(specification.initial_guess)
        if tracking:
            from .tracking import reference_at
            positions,velocities=reference_at(task.goal.data,np.arange(1,steps+1)*h)
            for quantity,values in (('position',positions),('velocity',velocities)):
                for k,row in enumerate(values,1):
                    for j,value in enumerate(row):
                        name=f'reference/{quantity}/{k}/{j}'
                        variables[name]['bounds']=[float(value)]*2
                        guess[name]=float(value)
        if p.holding_tip_speed_weight:
            for k in range(1,steps+1):guess[f'holding/{k}']=0.
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
    def __init__(self,task,robot,parameters,nominal_x,nominal_u,*,settling=None):
        from tools.platform_registry import registry
        from tools.platform_optimization import assemble_optimization
        from schemas.platform_math import OptimizationSpecification, ObjectiveSelection, ConstraintSelection
        self.parameters=GVSTrajectoryParameters.model_validate(parameters); self.n=len(nominal_x)//2
        self.tracking=task.family=='task.tracking'
        self.reference=task.goal.data if self.tracking else None
        self.duration=task.timing.duration_s;self.holding_start=None
        if self.parameters.holding_tip_speed_weight:
            if settling is None:raise ValueError('GVS_HOLDING_COST_REQUIRES_SETTLING_CONFIGURATION')
            from .gvs_profile import SampledSettling
            self.holding_start=self.duration-SampledSettling.model_validate(settling).window_s
        self.state_scales=np.r_[np.full(self.n,self.parameters.curvature_scale_rad_m),
            np.full(self.n,self.parameters.rate_scale_rad_m_s)]
        self.m=len(nominal_u);self.nominal_x=list(nominal_x);self.nominal_u=list(nominal_u)
        self.tendons=[t['id'] for t in robot.structure.data['tendons']]
        self.period=task.timing.control_period_s; self.target=task.goal.data.get('target_m')
        self.goal_tolerance=task.evaluator.parameters.data['max_position_error_m' if self.tracking else 'tolerance_m']
        reg=registry();start=time.perf_counter()
        binding=Binding(extension_id='optimization_assembler.gvs_tracking' if self.tracking else 'optimization_assembler.gvs_trajectory',parameters=Payload(
            contract='family.gvs_trajectory_parameters',data=self.parameters.model_dump(mode='json')))
        space=(tracking_authorization if self.tracking else trajectory_authorization)(robot,{},self.parameters)
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
            functions=trajectory_functions(expression_from_system(system))
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

    def _set_prediction_time(self,elapsed_s):
        if self.tracking:
            from .tracking import reference_at
            if elapsed_s is None or not np.isfinite(elapsed_s) or elapsed_s<0:
                raise ValueError('TRACKING_REQUIRES_ABSOLUTE_EXECUTION_TIME')
            times=elapsed_s+np.arange(self.parameters.horizon*self.parameters.substeps+1)*self.period/self.parameters.substeps
            self.reference_positions,self.reference_velocities=reference_at(self.reference,times)
            for quantity,values in (('position',self.reference_positions),('velocity',self.reference_velocities)):
                for k,row in enumerate(values[1:],1):
                    for j,value in enumerate(row):
                        name=f'reference/{quantity}/{k}/{j}'
                        self.problem.variables[name]['bounds']=[float(value)]*2
                        self.problem.initial_guess[name]=float(value)
            return dict(current_time_s=float(elapsed_s),node_times_s=times.tolist(),
                reference_position_m=self.reference_positions.tolist(),reference_velocity_m_s=self.reference_velocities.tolist(),
                beyond_task='Evaluate frozen reference at absolute node time; clamp outside reference interval')
        if self.holding_start is None:return None
        if elapsed_s is None or not np.isfinite(elapsed_s) or elapsed_s<0:
            raise ValueError('GVS_HOLDING_COST_REQUIRES_CURRENT_EXECUTION_TIME')
        times=elapsed_s+np.arange(1,self.parameters.horizon*self.parameters.substeps+1)*self.period/self.parameters.substeps
        braking_start=max(0.,self.holding_start-self.parameters.holding_brake_lead_s)
        weights=(times>=braking_start-1e-9).astype(float)
        for k,weight in enumerate(weights,1):
            self.problem.variables[f'holding/{k}']['bounds']=[float(weight)]*2
            self.problem.initial_guess[f'holding/{k}']=float(weight)
        return dict(current_time_s=float(elapsed_s),node_times_s=times.tolist(),holding_active=weights.tolist(),
            task_endpoint_s=self.duration,holding_start_s=self.holding_start,
            braking_start_s=braking_start,holding_brake_lead_s=self.parameters.holding_brake_lead_s,
            beyond_task='Holding continues beyond the task endpoint inside the prediction only; execution duration is unchanged.')

    def solve(self,measured_x,previous_u,warm=None,*,elapsed_s=None):
        update_start=time.perf_counter()
        prediction_timing=self._set_prediction_time(elapsed_s)
        for j,value in enumerate(measured_x):self.problem.variables[f'x/0/{j}']['bounds']=[float(value)/self.state_scales[j]]*2
        for t,value in zip(self.tendons,previous_u): self.problem.variables['previous_u/'+t]['bounds']=[float(value)]*2
        source=warm if warm is not None else self.last
        # Recording is opt-in and never feeds values back into preparation/selection.
        recording = None
        if self.solver.diagnostic_trace:
            from copy import deepcopy
            recording = dict(warm_source='explicit' if warm is not None else 'previous_selected',
                warm_before_preparation=None if source is None else deepcopy({k:source[k] for k in ('states','tensions')}))
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
        if not self.tracking and self.parameters.feasible_return is not None and self._tail_solver is not None:
            metrics=[]
            for k in range(self.parameters.horizon*self.parameters.substeps+1):
                state=np.array([self.problem.initial_guess[f'x/{k}/{j}'] for j in range(2*self.n)])*self.state_scales
                tip,speed=self._motion(state[:self.n],state[self.n:])
                metrics.append((np.linalg.norm(np.asarray(tip).ravel()-self.target),np.linalg.norm(np.asarray(speed))))
            seed_settled=all(e<=self.parameters.seed_position_tolerance_fraction*self.goal_tolerance
                and v<=self.parameters.seed_speed_limit_m_s for e,v in metrics)
        preparation_s=time.perf_counter()-update_start
        start=time.perf_counter(); result=self.solver.solve(self.problem,seed_settled=seed_settled);total=time.perf_counter()-start
        recovery=dict(enabled=self.parameters.recover_returned_tensions,attempted=False,selected=False,wall_s=0.)
        if self.parameters.recover_returned_tensions and result.status in ('converged','iteration_limit','feasible_early_stop'):
            result,recovery=self._recover_returned(result,measured_x)
        values=result.optimum;steps=self.parameters.horizon*self.parameters.substeps
        X=np.array([[values[f'x/{k}/{j}']*self.state_scales[j] for j in range(2*self.n)] for k in range(steps+1)])
        U=np.array([[values[f'u/{k}/{t}'] for t in self.tendons] for k in range(self.parameters.horizon)])
        output=dict(states=X.tolist(),tensions=U.tolist(),result=result.model_dump(mode='json'),
            prediction_timing=prediction_timing,
            decision_state_scales=self.state_scales.tolist(),
            diagnostics=self.solver.last_diagnostics,total_s=total,graph_s=self.graph_s,
            recovery=recovery,
            warm_start=dict(executed_intervals=int(source is not None and warm is None),
                preparation_s=preparation_s,regenerated_all_states=self.parameters.regenerate_warm_states,seed_settled=seed_settled,tail_initialization=tails),
            nominal_operating_state=self.nominal_x,measured_initial_state=list(measured_x),
            previous_tensions_n=list(previous_u),
            period_s=self.period,substeps=self.parameters.substeps,
            integration='implicit Euler in mass/force form; q scale 10 rad/m, force scale .001 N*m^2/rad',
            cost='Stage weights per second on squared tip/position scale, curvature rate/(1 rad/(m*s)), tension/(1 N) and delta tension/(1 N); terminal weights on squared tip/position scale, curvature rate and world tip speed/speed scale. Optional holding speed cost starts at max(0, task duration minus settling window minus holding_brake_lead_s), using absolute prediction-node times. Acceptance timing is unchanged. Position scale defaults to task tolerance. Smoothing is a design penalty.',
            cost_scales=dict(position_m=self.parameters.position_error_scale_m or self.goal_tolerance,
                tip_speed_m_s=self.parameters.tip_speed_scale_m_s))
        # A feasible finite-iteration plan can drive suboptimal NMPC. Keep its
        # nonconverged solver status; feasibility never implies optimality.
        accepted=result.status in ('converged','iteration_limit','feasible_early_stop') and result.constraint_violation<=1e-5
        if self.tracking:
            output['prediction_timing']['seed_settled_shortcut']='disabled for tracking, including constant references'
            output['cost']='Squared position and world tip velocity reference errors; terminal reference at terminal node; bounded tension and tension variation. No zero-speed holding schedule.'
        output['accepted']=accepted
        output['optimization_converged']=result.status=='converged'
        if self.parameters.recover_returned_tensions:
            def terminal_motion(values):
                state=np.array([values[f'x/{steps}/{j}'] for j in range(2*self.n)])*self.state_scales
                tip,speed=self._motion(state[:self.n],state[self.n:])
                return dict(error_m=float(np.linalg.norm(np.asarray(tip).ravel()-(self.reference_positions[-1] if self.tracking else self.target))),
                    speed_m_s=float(np.linalg.norm(np.asarray(speed))),
                    velocity_error_m_s=float(np.linalg.norm(np.asarray(speed).ravel()-self.reference_velocities[-1])) if self.tracking else None)
            output['feedback']=dict(initial_objective=self.solver.last_diagnostics['initial_objective'],
                delivered_objective=result.objective_value,
                first_command_change_from_initialization_n=float(max(abs(values[f'u/0/{t}']-self.problem.initial_guess[f'u/0/{t}']) for t in self.tendons)),
                initial_terminal=terminal_motion(self.problem.initial_guess),delivered_terminal=terminal_motion(values))
        # A finite unfinished iterate is still a useful next optimization guess.
        # Command acceptance remains the separate, stricter feasibility check.
        if result.status in ('converged','iteration_limit','feasible_early_stop'):self.last=output
        output['update_wall_s']=time.perf_counter()-update_start
        if recording is not None:
            output['recording'] = recording
        return output

    def _recover_returned(self,result,measured_x):
        """One feasibility recovery, with unchanged objective and constraints.

        IPOPT can lower tracking cost before its shooting defects meet delivery
        tolerance. Reintegrate that returned control once; never force selection
        or discard the already verified feasible candidate on a failed recovery.
        """
        start=time.perf_counter();d=self.solver.last_diagnostics
        recovery=dict(enabled=True,attempted=False,selected=False,wall_s=0.,
            source='returned_ipopt_tensions_reintegrated_from_current_measurement',
            parent_iteration=result.iterations,selected_before_objective=result.objective_value,
            initial_objective=d['initial_objective'],error=None)
        raw=self.solver.last_returned_optimum
        if raw is None or d['returned_iterate_objective']>=result.objective_value:
            return result,recovery
        recovery['attempted']=True
        repaired=dict(raw);state=np.asarray(measured_x)
        for j,v in enumerate(state):repaired[f'x/0/{j}']=float(v/self.state_scales[j])
        try:
            integration_start=time.perf_counter()
            for k in range(1,self.parameters.horizon*self.parameters.substeps+1):
                u=np.array([raw[f'u/{(k-1)//self.parameters.substeps}/{t}'] for t in self.tendons])
                guess=np.array([raw[f'x/{k}/{j}'] for j in range(2*self.n)])*self.state_scales
                state,_=self._extend_tail(state,u,guess)
                for j,v in enumerate(state):repaired[f'x/{k}/{j}']=float(v/self.state_scales[j])
            recovery['integration_s']=time.perf_counter()-integration_start
            validation_start=time.perf_counter()
            check=self.solver.evaluate_candidate(self.problem,repaired)
            recovery.update(check,validation_s=time.perf_counter()-validation_start)
            if check['feasible'] and check['objective']<result.objective_value:
                recovery['selected']=True
                recovery['first_command_change_n']=float(max(abs(repaired[f'u/0/{t}']-result.optimum[f'u/0/{t}']) for t in self.tendons))
                # Feasibility recovery is not an IPOPT convergence event.
                result=result.model_copy(update=dict(optimum=repaired,objective_value=check['objective'],
                    constraint_violation=check['scaled_violation'],status='feasible_early_stop'))
        except RuntimeError as exc:
            recovery['error']=str(exc)
        recovery['wall_s']=time.perf_counter()-start
        return result,recovery
