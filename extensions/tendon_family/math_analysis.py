"""Candidate-bound world-tip outputs and phase-aware saved operating points."""
from types import SimpleNamespace
import numpy as np
import casadi as ca
from schemas.platform import SessionInput, SignalSpec
from schemas.platform import Binding, Payload
from schemas.platform_math import SystemContext
from schemas.platform_analysis import (AnalysisProtocol, TaskAnalysisProtocol, EndpointLinearizedModel,
    EndpointOutputLinearization, AnalysisResult)
from tools.platform_store import plain
from tools.state_io import digest
from .gvs import GVSModel
from .contracts import GVSModelParameters, GVSEquilibriumRequestV2
from .gvs_casadi import functions_for, expression_from_system, gvs_equilibrium_tool
from .pcc import quaternion_wxyz_to_rotation
from extensions.math_analysis.kernels import LIMITATIONS


def saved_points(case,p):
    observations=case['saved'].get('controller_observations.json',[])
    commands=case['saved'].get('actual_commands.json',[])
    points=[]
    for requested in p.samples_s:
        found=[(i,r) for i,r in enumerate(observations) if abs(r['time_s']-requested)<1e-9]
        if len(found)!=1:
            points.append(dict(requested_time_s=requested,available=False,reason='Exact saved state missing or ambiguous')); continue
        i,r=found[0]; t=r['time_s']
        following=[(j,c) for j,c in enumerate(commands) if abs(c['time_s']-t)<1e-9]
        prior=[(j,c) for j,c in enumerate(commands) if c['time_s']<t-1e-9]
        if r['phase']!='current_state_before_integration' or len(following)!=1:
            points.append(dict(requested_time_s=requested,available=False,reason='Unsupported phase or missing applied interval command')); continue
        j,c=following[0]
        # In these saved ideal-tension executions, actual_tension_n is the applied
        # next-interval value; verify against the backend actual_commands artifact.
        u=r.get('actual_tension_n')
        if u is None or not np.allclose(u,c['desired_tension_n'],rtol=0,atol=1e-12):
            points.append(dict(requested_time_s=requested,available=False,reason='Applied tension unavailable or inconsistent')); continue
        x=r['gvs_q']+r['gvs_qdot']
        if not np.allclose(x,r['measured_initial_state'],rtol=0,atol=1e-12): raise ValueError('SAVED_STATE_INCONSISTENT')
        points.append(dict(requested_time_s=requested,actual_time_s=t,phase=r['phase'],available=True,x=x,u=u,
            observation_index=i,command_index=j,command_interval_s=[t,min(t+p.period_s,p.duration_s)],
            input_interpretation='actual applied input for interval starting at this pre-step state',
            preceding_input_n=None if not prior else prior[-1][1]['desired_tension_n'],
            preceding_input_reason='initial condition; no preceding interval' if not prior else 'input producing the current observation',
            remaining_task_s=max(0.,p.duration_s-t)))
    return points


def make_graph_from_input(inp,point):
    inp=SessionInput.model_validate(inp)
    params=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
    system=GVSModel(params).build_system(inp.robot,params,None,SystemContext(x0=point['x'],u0=point['u'],scene=inp.task.environment))
    f=functions_for(expression_from_system(system))
    x,u,_=f._linearization_symbols
    mount=inp.task.environment.data['mount']
    h=ca.DM(quaternion_wxyz_to_rotation(mount['quaternion_wxyz']))@f.tip_position_expression+ca.DM(mount['position_m'])
    n=x.numel()//2
    # J(q) qdot is differentiated as one expression, retaining dJ/dq*qdot.
    velocity=ca.jtimes(h,x[:n],x[n:])
    output=ca.Function('world_tip_analysis',[x,u],[h,ca.jacobian(h,x),ca.jacobian(h,u),
        velocity,ca.jacobian(velocity,x),ca.jacobian(velocity,u)])
    return inp,system,f,output


def make_graph(case,point):
    return make_graph_from_input(case['effective'],point)


def linear_model(case,point,p,case_ref,graph):
    inp,system,f,output=graph
    A,B,d=f.linearize(point['x'],point['u']); y,C,D,v,Cv,Dv=output(point['x'],point['u'])
    qscale=[]
    for spec in system.state_definition[:len(system.x0)//2]:
        if spec.units!='rad/m': raise ValueError('UNSUPPORTED_BASIS_UNITS')
        qscale.append(1/p.baseline_lengths_m[spec.entity])
    binding={**case['binding'], 'basis':plain(f.resolved),'parameters':plain(f.parameters),
        'target_m':inp.task.goal.data['target_m'], 'mount':inp.task.environment.data['mount'],
        'tension_limits_n':f.expression.tendon_force_limits_n,'model_identity':digest(plain(f.expression)),
        'output_expression':'R_world_base * symbolic_tip_position(q) + p_world_base; AD in x and u',
        'coordinate_order':f.expression.coordinate_order,'tendon_order':f.expression.tendon_order,
        'analysis_protocol_identity':digest(plain(p)),'task_duration_s':inp.task.timing.duration_s,
        'control_period_s':inp.task.timing.control_period_s,'physics_timestep_s':inp.task.timing.timestep_s,
        'initializer':plain(inp.task.initializer),'controller':plain(inp.policy.controller),
        'endpoint_requirements':dict(official_reach=plain(inp.task.evaluator),
            terminal_braking_diagnostic=inp.policy.controller.parameters.data.get('settling'))}
    position=EndpointOutputLinearization(name='tip_position',units='m',value0=np.asarray(y).reshape(-1).tolist(),
        C=np.asarray(C).tolist(),D=np.asarray(D).tolist(),scales=[p.output_scale_m]*3)
    velocity=EndpointOutputLinearization(name='tip_velocity',units='m/s',value0=np.asarray(v).reshape(-1).tolist(),
        C=np.asarray(Cv).tolist(),D=np.asarray(Dv).tolist(),scales=[p.output_scale_m/p.duration_s]*3)
    return EndpointLinearizedModel(state_definition=system.state_definition,input_definition=system.input_definition,
        output_definition=[SignalSpec(name='tip_position',entity='tip',dimension=3,units='m',frame='world',phase='instantaneous')],
        x0=point['x'],u0=point['u'],y0=np.asarray(y).reshape(-1).tolist(),A=A.tolist(),B=B.tolist(),
        C=np.asarray(C).tolist(),D=np.asarray(D).tolist(),drift=d.reshape(-1).tolist(),time_domain='continuous',
        binding=binding,operating_point={k:v for k,v in point.items() if k not in ('x','u')},
        state_scales=qscale+[v/p.duration_s for v in qscale],input_scales=[p.input_scale_n]*len(system.u0),
        output_scales=[p.output_scale_m]*3,
        normalization_derivation='Structural-linear nodal curvature coefficients [ky,kz] at dimensionless knots; each coefficient scale 1/baseline section length, rate scale 1/(length*0.35 s); tensions 8 N; world tip 0.01 m.',
        protocol_identity=digest(plain(p)),evidence=[case_ref],endpoint_outputs=[position,velocity])


def derivative_check(model,graph,p):
    _,_,f,h=graph; x=np.asarray(model.x0); u=np.asarray(model.u0)
    dx=np.asarray(model.state_scales)*np.cos(np.arange(len(x))+1); du=np.asarray(model.input_scales)*np.sin(np.arange(len(u))+1)
    step=p.derivative_step
    fd=(f.evaluate(x+step*dx,u+step*du)['xdot']-f.evaluate(x-step*dx,u-step*du)['xdot']).ravel()/(2*step)
    ad=np.asarray(model.A)@dx+np.asarray(model.B)@du
    plus=h(x+step*dx,u+step*du); minus=h(x-step*dx,u-step*du)
    fy=(np.asarray(plus[0])-np.asarray(minus[0])).ravel()/(2*step)
    ay=np.asarray(model.C)@dx+np.asarray(model.D)@du
    # Compare derivatives after physical output/state normalization.
    def compare(a,b,scale):
        a=a/scale; b=b/scale
        return dict(passed=bool(np.allclose(a,b,atol=p.derivative_atol,rtol=p.derivative_rtol)),
            max_absolute_error=float(max(abs(a-b))),max_scaled_error=float(max(abs(a-b)/(p.derivative_atol+p.derivative_rtol*abs(b)))))
    velocity=next(row for row in model.endpoint_outputs if row.name=='tip_velocity')
    fvelocity=(np.asarray(plus[3])-np.asarray(minus[3])).ravel()/(2*step)
    avelocity=np.asarray(velocity.C)@dx+np.asarray(velocity.D)@du
    return dict(step=step,dynamics=compare(fd,ad,model.state_scales),output=compare(fy,ay,model.output_scales),
        tip_velocity=compare(fvelocity,avelocity,velocity.scales))


def linearize_saved(ctx,args):
    case=ctx.artifact(args.case)
    protocol_type=TaskAnalysisProtocol if ctx.request.tool_version=='2.0.0' else AnalysisProtocol
    p=protocol_type.model_validate(ctx.artifact(args.protocol)); points=saved_points(case,p)
    good=[r for r in points if r['available']]
    if not good: return AnalysisResult(kind='linearization',protocol=args.protocol,bindings=[case['binding']],records=points,evidence=[args.case],limitations=LIMITATIONS)
    graph=make_graph(case,good[0]); records=[]
    for point in points:
        if not point['available']: records.append(point); continue
        model=linear_model(case,point,p,args.case,graph)
        ref=ctx.save_artifact(model)
        records.append(dict(point=model.operating_point,model=plain(ref),derivative_check=derivative_check(model,graph,p) if point is good[0] else None))
    if not getattr(args,'include_static_equilibrium',True):
        return AnalysisResult(kind='linearization',protocol=args.protocol,bindings=[case['binding']],records=records,
            evidence=[args.case],limitations=LIMITATIONS)
    inp,system,f,_=graph
    # Exactly one bounded existing damped Newton solve. <= 262 residual calls:
    # 21 main evaluations + 20*12 line searches + final residual. No recovery.
    eq=gvs_equilibrium_tool(SimpleNamespace(input=inp,reg=ctx.reg),GVSEquilibriumRequestV2(
        basis=f.parameters.basis,initial_q=good[0]['x'][:len(system.x0)//2],
        tendon_tensions_n=dict(zip(f.expression.tendon_order,good[0]['u'])),
        tolerance=p.static_force_tolerance,max_iterations=p.static_max_iterations))
    equilibrium=dict(attempts=1,result=plain(eq),max_residual_evaluations=13*p.static_max_iterations+2,
        initialization='first requested saved measured q; first actually applied tension',force_tolerance=p.static_force_tolerance)
    if eq.converged:
        point=dict(x=eq.q_equilibrium+[0.]*len(eq.q_equilibrium),u=good[0]['u'],phase='computed_static_equilibrium',
            actual_time_s=None,remaining_task_s=None,available=True,equilibrium=equilibrium)
        model=linear_model(case,point,p,args.case,graph); records.append(dict(point=model.operating_point,model=plain(ctx.save_artifact(model))))
    else: records.append(dict(equilibrium=equilibrium,available=False,reason='Bounded static solve unsuccessful'))
    return AnalysisResult(kind='linearization',protocol=args.protocol,bindings=[case['binding']],records=records,evidence=[args.case],limitations=LIMITATIONS)


def _configuration_boundary(inp,binding):
    """Explicit execution-before-screening information boundary."""
    from .gvs_basis import resolve_basis
    tendons=inp.robot.structure.data['tendons']; control=inp.policy.controller.parameters.data
    coordinate_order=binding.get('coordinate_order')
    if coordinate_order is None:
        coordinate_order=list(resolve_basis(inp.robot.structure.data,binding['basis']).coordinate_order)
    return dict(study_candidate_id=binding['candidate_id'],build_node=binding['source_node'],
        robot=plain(inp.robot),task=plain(inp.task),initializer=plain(inp.task.initializer),
        model=dict(extension_id='model.gvs',version='1.0.0',basis=binding['basis']),
        controller_recipe=inp.policy.controller.parameters.data['recipe'],
        analysis_binding=dict(candidate_id=binding['candidate_id'],configuration=binding.get('configuration'),
            effective_configuration_identity=binding.get('effective_configuration_identity',digest(plain(inp))),
            task_identity=binding.get('task_identity',digest(plain(inp.task))),
            target_m=inp.task.goal.data['target_m'],duration_s=inp.task.timing.duration_s,
            control_period_s=inp.task.timing.control_period_s,physics_timestep_s=inp.task.timing.timestep_s,
            initializer=plain(inp.task.initializer),controller_numerical_source=control.get('numerical_source'),
            tendon_order=binding.get('tendon_order',[row['id'] for row in tendons]),
            tension_bounds_n=binding.get('tension_bounds_n',[[0.,row['force_limit_n']] for row in tendons]),
            basis=binding['basis'],coordinate_order=coordinate_order,endpoint_frame='world',
            endpoint_requirements=binding.get('endpoint_requirements',dict(official_reach=plain(inp.task.evaluator),
                terminal_braking_diagnostic=control.get('settling')))),
        discretization=plain(inp.policy.discretization),mount=inp.task.environment.data['mount'],
        excluded_fields=['execution trajectories','evaluator results','terminal errors','observed tensions','optimizer histories'],
        execution_data_used=False)


def _candidate_points(inp,graph,p):
    """Configuration-only standardized and controller-declared operating points."""
    from scipy.optimize import least_squares, minimize
    _,system,f,output=graph; n=len(system.x0)//2
    design=inp.robot.structure.data
    limits=np.asarray([row['force_limit_n'] for row in design['tendons']],dtype=float)
    pretension=np.clip([row['pretension_n'] for row in design['tendons']],0,limits)
    from .gvs_profile import reach_numerical
    numerical=reach_numerical(inp)
    x0=np.asarray(numerical.get('measured_initial_state'),dtype=float)
    if x0.shape!=(2*n,):
        q=np.asarray(numerical['nominal']['q0'],dtype=float)
        if q.shape!=(n,): raise ValueError('CONTROLLER_INITIALIZER_PROJECTION_UNSUPPORTED')
        x0=np.r_[q,np.zeros(n)]
    q0=x0[:n]
    controller_start=np.asarray(numerical['nominal']['u0'],dtype=float)
    if controller_start.shape!=limits.shape or np.any(controller_start<0) or np.any(controller_start>limits):
        raise ValueError('CONTROLLER_START_INPUT_UNSUPPORTED')
    initial_tip=np.asarray(output(x0,pretension)[0]).reshape(-1)
    target=np.asarray(inp.task.goal.data['target_m'],dtype=float)
    tolerance=float(inp.task.evaluator.parameters.data['tolerance_m'])
    points=[dict(name='standardized_initial_pretension',x=x0.tolist(),u=pretension.tolist(),available=True,
        phase='configuration_standardized_initial_pretension',scope='standardized initial/pretension',remaining_task_s=p.duration_s,actual_time_s=None,
        construction=dict(method='actual initializer projected by existing controller preparation plus declared tendon pretension',
            position_residual_m=float(np.linalg.norm(initial_tip-target)),static_equilibrium=False,
            achieved_world_point_m=initial_tip.tolist(),initializer_source=plain(inp.task.initializer),
            input_source='family.design.tendons[].pretension_n',execution_data_used=False)),
        dict(name='controller_start_input',x=x0.tolist(),u=controller_start.tolist(),available=True,
            phase='configuration_controller_start_input',scope='controller-start input',remaining_task_s=p.duration_s,actual_time_s=None,
            construction=dict(method='existing immutable controller preparation/numerical-source logic',
                position_residual_m=float(np.linalg.norm(np.asarray(output(x0,controller_start)[0]).reshape(-1)-target)),
                achieved_world_point_m=np.asarray(output(x0,controller_start)[0]).reshape(-1).tolist(),static_equilibrium=False,
                numerical_source=inp.policy.controller.parameters.data.get('numerical_source'),
                preparation_provenance=numerical['provenance'],execution_trajectory_used=False))]

    qsym,usym=f.q_symbol,f.u_symbol
    mount=inp.task.environment.data['mount']
    world=ca.DM(quaternion_wxyz_to_rotation(mount['quaternion_wxyz']))@f.tip_position_expression+ca.DM(mount['position_m'])
    variables=ca.vertcat(qsym,usym); residual=f.static_residual_expression
    static_fun=ca.Function('candidate_target_static',[variables],[world,residual,
        ca.jacobian(world,variables),ca.jacobian(residual,variables)])
    z0=np.r_[q0,pretension]
    def static_values(z):
        h,r,Jh,Jr=static_fun(z)
        return (np.asarray(h).reshape(-1),np.asarray(r).reshape(-1),np.asarray(Jh),np.asarray(Jr))
    def objective(z):
        h,_,_,_=static_values(z); return float(np.sum(((h-target)/p.output_scale_m)**2)+1e-6*np.sum((z[n:]/p.input_scale_n)**2))
    def objective_jac(z):
        h,_,Jh,_=static_values(z)
        gradient=2*Jh.T@((h-target)/(p.output_scale_m**2)); gradient[n:]+=2e-6*z[n:]/(p.input_scale_n**2)
        return gradient
    def equality(z): return static_values(z)[1]
    def equality_jac(z): return static_values(z)[3]
    solved=minimize(objective,z0,jac=objective_jac,bounds=[(None,None)]*n+list(zip(np.zeros(len(limits)),limits)),
        constraints=[dict(type='eq',fun=equality,jac=equality_jac)],method='SLSQP',
        options=dict(maxiter=p.construction_max_iterations,ftol=1e-12,disp=False))
    h,r,_,_=static_values(solved.x); pos_res=float(np.linalg.norm(h-target)); force_res=float(np.linalg.norm(r,np.inf))
    available=bool(solved.success and pos_res<=tolerance+p.endpoint_check_atol and force_res<=p.static_force_tolerance)
    target_record=dict(name='target_equilibrium',available=available,scope='target-associated static attempt',
        construction=dict(method='single bounded-tension target-associated static SLSQP attempt; no recovery',
            solver='scipy.optimize.SLSQP',success=bool(solved.success),status=int(solved.status),message=str(solved.message),
            iterations=int(solved.nit),maximum_iterations=p.construction_max_iterations,
            requested_world_point_m=target.tolist(),achieved_world_point_m=h.tolist(),
            position_residual_m=pos_res,position_limit_m=tolerance,static_residual_inf=force_res,
            static_force_tolerance=p.static_force_tolerance,tension_bounds_n=[np.zeros(len(limits)).tolist(),limits.tolist()],
            q_bounds='unbounded, matching existing GVS inverse-static authorization',execution_data_used=False))
    if available:
        target_record.update(x=np.r_[solved.x[:n],np.zeros(n)].tolist(),u=solved.x[n:].tolist(),
            phase='configuration_target_static_equilibrium',remaining_task_s=p.duration_s,actual_time_s=None)
    else: target_record['reason']='Target-associated equilibrium unavailable within the frozen single-attempt limits.'
    points.append(target_record)

    halfway=(initial_tip+target)/2
    def halfway_residual(q): return (np.asarray(output(np.r_[q,np.zeros(n)],pretension)[0]).reshape(-1)-halfway)/p.output_scale_m
    def halfway_jac(q): return np.asarray(output(np.r_[q,np.zeros(n)],pretension)[1])[:,:n]/p.output_scale_m
    waypoint=least_squares(halfway_residual,q0,jac=halfway_jac,max_nfev=p.construction_max_iterations,
        xtol=1e-12,ftol=1e-12,gtol=1e-12)
    waypoint_tip=np.asarray(output(np.r_[waypoint.x,np.zeros(n)],pretension)[0]).reshape(-1)
    waypoint_available=bool(waypoint.success and np.all(np.isfinite(waypoint.x)))
    waypoint_record=dict(name='halfway_waypoint',available=waypoint_available,scope='geometric intermediate point',
        construction=dict(method='single bounded-evaluation inverse-kinematic least-squares attempt at fixed halfway world point',
            solver='scipy.optimize.least_squares',success=bool(waypoint.success),status=int(waypoint.status),
            function_evaluations=int(waypoint.nfev),maximum_evaluations=p.construction_max_iterations,
            requested_world_point_m=halfway.tolist(),achieved_world_point_m=waypoint_tip.tolist(),
            position_residual_m=float(np.linalg.norm(waypoint_tip-halfway)),static_equilibrium=False,
            input_source='family.design.tendons[].pretension_n',execution_data_used=False))
    if waypoint_available:
        waypoint_record.update(x=np.r_[waypoint.x,np.zeros(n)].tolist(),u=pretension.tolist(),
            phase='configuration_geometric_intermediate_non_equilibrium',remaining_task_s=p.duration_s,actual_time_s=None)
    else: waypoint_record['reason']='Geometric intermediate construction unavailable within the frozen single-attempt limits.'
    points.append(waypoint_record)
    return points


def _validate_task_protocol(inp,p):
    if not np.isclose(p.duration_s,inp.task.timing.duration_s,rtol=0,atol=p.horizon_alignment_atol_s):
        raise ValueError('ANALYSIS_PROTOCOL_TASK_DURATION_MISMATCH')
    if not np.isclose(p.period_s,inp.task.timing.control_period_s,rtol=0,atol=p.horizon_alignment_atol_s):
        raise ValueError('ANALYSIS_PROTOCOL_CONTROL_PERIOD_MISMATCH')


def linearize_candidate_configuration(ctx,inp,binding,p,protocol_ref):
    from .model_applicability import assess_model_uses
    _validate_task_protocol(inp,p)
    binding={**binding,'analysis_protocol_identity':digest(plain(p))}
    boundary=_configuration_boundary(inp,binding)
    if any(key in boundary for key in ('trajectory','evaluation','terminal_error','actual_tension_n','optimizer_history')):
        raise ValueError('CONFIGURATION_ONLY_BOUNDARY_VIOLATION')
    n=len(binding['coordinate_order']); limits=[row['force_limit_n'] for row in inp.robot.structure.data['tendons']]
    seed=dict(x=[0.]*(2*n),u=[row['pretension_n'] for row in inp.robot.structure.data['tendons']])
    graph=make_graph_from_input(inp,seed); points=_candidate_points(inp,graph,p); records=[]
    for point in points:
        if not point['available']:
            records.append(point); continue
        case=dict(effective=plain(inp),binding={**binding,'target_m':inp.task.goal.data['target_m'],
            'tension_limits_n':limits,'configuration_only_identity':digest(boundary)})
        model=linear_model(case,point,p,binding['configuration'],graph)
        records.append(dict(point=model.operating_point,model=plain(ctx.save_artifact(model)),
            derivative_check=derivative_check(model,graph,p) if point['name']=='halfway_waypoint' else None,
            construction=point['construction']))
    model_binding=Binding(extension_id='model.gvs',version='1.0.0',parameters=Payload(
        contract='family.gvs_model',data=dict(basis=inp.policy.controller.parameters.data['recipe']['basis'])))
    applicability=assess_model_uses(inp.robot,inp.task,model_binding,
        ['reachability','static_equilibrium','linearization','local_model_control'],registry=ctx.reg)
    records.insert(0,dict(configuration_only_input=boundary,configuration_only_identity=digest(boundary),
        applicability=plain(applicability),operating_point_rule=p.candidate_rule,
        requested_operating_points=len(points),analysis_binding=boundary['analysis_binding']))
    return AnalysisResult(kind='candidate_linearization',protocol=protocol_ref,bindings=[binding],records=records,
        evidence=[binding['configuration']],limitations=LIMITATIONS+[
            'Retrospective emulation of information available before execution; candidates and outcomes already existed.',
            'Intermediate waypoint is geometric and is not asserted to be a static equilibrium.'])


def linearize_candidate(ctx,args):
    from .candidate_analysis import resolve_candidate
    inp,binding=resolve_candidate(ctx,args.source_node)
    p=TaskAnalysisProtocol.model_validate(ctx.artifact(args.protocol))
    return linearize_candidate_configuration(ctx,inp,binding,p,args.protocol)


def saved_case(ctx,args):
    from collections import Counter
    from schemas.platform_diagnostics import DiagnosticFact
    c=ctx.artifact(args.case)
    protocol_type=TaskAnalysisProtocol if ctx.request.tool_version=='2.0.0' else AnalysisProtocol
    p=protocol_type.model_validate(ctx.artifact(args.protocol))
    rows=c['saved'].get('controller_observations.json',[])
    commands=c['saved'].get('actual_commands.json',[])
    trajectory=c['saved'].get('trajectory.json.gz',[])
    target=np.asarray(SessionInput.model_validate(c['effective']).task.goal.data['target_m'],dtype=float)
    selected=[]
    requested=set(round(float(t),12) for t in p.samples_s)
    graph=None
    for i,row in enumerate(rows):
        t=float(row['time_s'])
        if round(t,12) not in requested: continue
        command_matches=[(j,item) for j,item in enumerate(commands) if abs(item['time_s']-t)<1e-9]
        command_index=command_matches[0][0] if len(command_matches)==1 else None
        previous=commands[command_index-1] if command_index is not None and command_index>0 else None
        following=next((item for item in rows if abs(item['time_s']-(t+p.period_s))<1e-9),None)
        prediction=row.get('one_step_prediction')
        discrepancy=None
        if prediction and following:
            difference=np.asarray(following['tip_position_m'])-np.asarray(prediction['tip_position_m'])
            discrepancy=dict(actual_sample_time_s=following['time_s'],predicted_time_s=prediction['time_s'],
                actual_minus_prediction_m=difference.tolist(),norm_m=float(np.linalg.norm(difference)))
        backend_velocity=[]
        tr_index=next((j for j,item in enumerate(trajectory) if abs(item['time_s']-t)<1e-9),None)
        if tr_index is not None:
            for a,b,label in ((tr_index-1,tr_index,'backward_interval_average'),(tr_index,tr_index+1,'forward_interval_average')):
                if a>=0 and b<len(trajectory):
                    ta,tb=trajectory[a]['time_s'],trajectory[b]['time_s']
                    value=(np.asarray(trajectory[b]['tip_m'])-np.asarray(trajectory[a]['tip_m']))/(tb-ta)
                    backend_velocity.append(dict(kind=label,value_m_s=value.tolist(),interval_s=[ta,tb],
                        frame='world',source='saved backend tip positions; finite difference, not instantaneous'))
        if graph is None:
            point=dict(x=row['gvs_q']+row['gvs_qdot'],u=row['actual_tension_n'])
            graph=make_graph(c,point)
        x=row['gvs_q']+row['gvs_qdot']; gvs_velocity=np.asarray(graph[3](x,row['actual_tension_n'])[3]).reshape(-1)
        current=np.asarray(row['actual_tension_n'],dtype=float)
        prior=None if previous is None else np.asarray(previous['desired_tension_n'],dtype=float)
        selected.append(dict(candidate_id=c['binding']['candidate_id'],observation_index=i,command_index=command_index,
            timestamp_s=t,phase=row.get('phase'),evidence=[plain(args.case)],
            projected_state=dict(q_rad_m=row['gvs_q'],qdot_rad_m_s=row['gvs_qdot'],
                measured_initial_state=row['measured_initial_state'],projection_residual_max_rad_m=row.get('gvs_projection_residual_max_rad_m')),
            world_tip_position_m=row['tip_position_m'],tip_minus_target_m=(np.asarray(row['tip_position_m'])-target).tolist(),
            target_error_norm_m=float(np.linalg.norm(np.asarray(row['tip_position_m'])-target)),
            previous_applied_input_n=None if prior is None else prior.tolist(),next_interval_applied_input_n=current.tolist(),
            next_interval_s=[t,min(t+p.period_s,p.duration_s)],
            tension_change_from_previous_n=None if prior is None else (current-prior).tolist(),
            selected_iteration=row.get('optimization_selected_iteration'),selection_kind='optimized_noninitialization'
                if (row.get('optimization_selected_iteration') or 0)>0 else 'initialization',
            solver_status=dict(status=row.get('optimization_status'),raw_status=row.get('optimization_raw_status'),
                failed=row.get('solver_failed'),nonconverged=row.get('optimization_nonconverged'),error=row.get('solver_error')),
            recovery_status=row.get('feasibility_recovery'),validation_status=dict(plan_accepted=row.get('plan_accepted'),
                constraint_violation=row.get('optimization_constraint_violation'),returned_violation=row.get('optimization_returned_violation'),
                plan_source=row.get('plan_source'),policy_stop_reason=row.get('policy_stop_reason')),
            one_step_prediction=prediction,one_step_discrepancy=discrepancy,
            backend_tip_velocity_estimates=backend_velocity,
            gvs_derived_instantaneous_tip_velocity=dict(value_m_s=gvs_velocity.tolist(),frame='world',
                source='J_tip(q) * projected GVS qdot; distinct from backend finite differences'),
            update_cost_breakdown_s={k:row.get(k) for k in ('graph_construction_s','solver_construction_s','state_preparation_s',
                'warm_preparation_s','optimization_solve_s','plan_validation_s','recovery_integration_s','recovery_validation_s',
                'recovery_wall_s','controller_boundary_wall_s','update_wall_s')}))
    positive=[row for row in rows if (row.get('optimization_selected_iteration') or 0)>0]
    command_changes=[]
    for i,(before,after) in enumerate(zip(commands,commands[1:]),start=1):
        delta=np.asarray(after['desired_tension_n'])-np.asarray(before['desired_tension_n'])
        if np.any(np.abs(delta)>1e-12): command_changes.append(dict(command_index=i,time_s=after['time_s'],delta_n=delta.tolist()))
    fact=DiagnosticFact(fact_id='saved-terminal-error',statement=f"Saved evaluator terminal error {c['factual_result']['terminal_error_m']} m; task accepted {c['factual_result']['task_accepted']}.",evidence=[args.case])
    return AnalysisResult(kind='saved_case',protocol=args.protocol,bindings=[c['binding']],
        records=[dict(factual_result=c['factual_result'],samples=saved_points(c,p),observation_count=len(rows),
            plan_sources=dict(Counter(r.get('plan_source','missing') for r in rows)),
            selected_iterations=dict(Counter(str(r.get('optimization_selected_iteration')) for r in rows)),
            first_positive_noninitialization_time_s=None if not positive else positive[0]['time_s'],
            initialization_selected_all_updates=not positive,command_changes=command_changes,
            diagnostic_samples=selected,
            saved_tension_bound_usage=dict(count=len(rows),saturated_entries=sum(sum(r.get('force_limit_saturated',[])) for r in rows)))],
        evidence=[args.case],facts=[fact],limitations=LIMITATIONS+['Observations do not establish causal attribution.'])
