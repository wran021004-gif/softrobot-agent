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



def trajectory_authorization(robot, space, parameters):
    p=GVSTrajectoryParameters.model_validate(parameters); n=len(coordinate_order(robot.structure.data,p.basis))
    result={}
    for k in range(p.horizon*p.substeps+1):
        for j in range(2*n):
            result[f'x/{k}/{j}']=dict(type='number',bounds=[None,None],units='1',
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
        model_params=GVSModelParameters(basis=p.basis)
        system=GVSModel(model_params).build_system(robot,model_params,None,SystemContext(
            x0=context.x0,u0=context.u0,scene=task.environment))
        functions=functions_for(expression_from_system(system))
        n=len(context.x0)//2; m=len(context.u0); steps=p.horizon*p.substeps
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
        previous_state=ca.MX.sym('previous_state',2*n)
        next_state=ca.MX.sym('next_state',2*n)
        tension=ca.MX.sym('tension',m)
        step_residual=ca.Function('gvs_implicit_step_residual',[previous_state,next_state,tension],
            [ca.vertcat((next_state[:n]-previous_state[:n]-h*next_state[n:])/10.,
                functions.implicit_residual(next_state,tension,(next_state[n:]-previous_state[n:])/h)/.001)],
            {'jac_penalty':0})
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
        objective+=p.terminal_weight*ca.sumsqr((tip-target)/tolerance)
        objective*=specification.objectives[0].weight
        bundle,selectors=expression_payload(list(expected),dict(variables=decision_symbols,expression=objective),constraints)
        variables={name:dict(spec) for name,spec in expected.items()}
        for j,value in enumerate(context.x0):
            scale=variables[f'x/0/{j}']['physical_scale'];variables[f'x/0/{j}']['bounds']=[value/scale,value/scale]
        for t,value in zip(tendons,context.u0): variables['previous_u/'+t]['bounds']=[value,value]
        guess=dict(specification.initial_guess)
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
            max_cpu_s=self.parameters.max_cpu_s))
        self.last=None

    def solve(self,measured_x,previous_u,warm=None):
        for j,value in enumerate(measured_x):self.problem.variables[f'x/0/{j}']['bounds']=[float(value)/self.state_scales[j]]*2
        for t,value in zip(self.tendons,previous_u): self.problem.variables['previous_u/'+t]['bounds']=[float(value)]*2
        source=warm if warm is not None else self.last
        if source is not None:
            X=np.asarray(source['states']);U=np.asarray(source['tensions']);s=0 if warm is not None else self.parameters.substeps
            for k in range(len(X)):
                for j in range(2*self.n):self.problem.initial_guess[f'x/{k}/{j}']=float(X[min(k+s,len(X)-1),j])/self.state_scales[j]
            for k in range(len(U)):
                for j,t in enumerate(self.tendons):self.problem.initial_guess[f'u/{k}/{t}']=float(U[min(k+(warm is None),len(U)-1),j])
        start=time.perf_counter(); result=self.solver.solve(self.problem);total=time.perf_counter()-start
        values=result.optimum;steps=self.parameters.horizon*self.parameters.substeps
        X=np.array([[values[f'x/{k}/{j}']*self.state_scales[j] for j in range(2*self.n)] for k in range(steps+1)])
        U=np.array([[values[f'u/{k}/{t}'] for t in self.tendons] for k in range(self.parameters.horizon)])
        output=dict(states=X.tolist(),tensions=U.tolist(),result=result.model_dump(mode='json'),
            decision_state_scales=self.state_scales.tolist(),
            diagnostics=self.solver.last_diagnostics,total_s=total,graph_s=self.graph_s,
            nominal_operating_state=self.nominal_x,measured_initial_state=list(measured_x),
            period_s=self.period,substeps=self.parameters.substeps,
            integration='implicit Euler in mass/force form; q scale 10 rad/m, force scale .001 N*m^2/rad',
            cost='Stage weights per second on tip/tolerance, velocity/(1 rad/(m*s)), tension/(1 N) and delta tension/(1 N); dimensionless terminal weight. Smoothing is a design penalty.')
        # A feasible finite-iteration plan can drive suboptimal NMPC. Keep its
        # nonconverged solver status; feasibility never implies optimality.
        accepted=result.status in ('converged','iteration_limit') and result.constraint_violation<=1e-5
        output['accepted']=accepted
        output['optimization_converged']=result.status=='converged'
        if accepted:self.last=output
        return output
