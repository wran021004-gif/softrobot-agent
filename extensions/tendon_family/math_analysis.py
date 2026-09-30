"""Candidate-bound world-tip outputs and phase-aware saved operating points."""
from types import SimpleNamespace
import numpy as np
import casadi as ca
from schemas.platform import SessionInput, SignalSpec
from schemas.platform_math import SystemContext
from schemas.platform_analysis import AnalysisProtocol, OutputLinearizedModel, AnalysisResult
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


def make_graph(case,point):
    inp=SessionInput.model_validate(case['effective'])
    params=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
    system=GVSModel(params).build_system(inp.robot,params,None,SystemContext(x0=point['x'],u0=point['u'],scene=inp.task.environment))
    f=functions_for(expression_from_system(system))
    x,u,_=f._linearization_symbols
    mount=inp.task.environment.data['mount']
    h=ca.DM(quaternion_wxyz_to_rotation(mount['quaternion_wxyz']))@f.tip_position_expression+ca.DM(mount['position_m'])
    output=ca.Function('world_tip_analysis',[x,u],[h,ca.jacobian(h,x),ca.jacobian(h,u)])
    return inp,system,f,output


def linear_model(case,point,p,case_ref,graph):
    inp,system,f,output=graph
    A,B,d=f.linearize(point['x'],point['u']); y,C,D=output(point['x'],point['u'])
    qscale=[]
    for spec in system.state_definition[:len(system.x0)//2]:
        if spec.units!='rad/m': raise ValueError('UNSUPPORTED_BASIS_UNITS')
        qscale.append(1/p.baseline_lengths_m[spec.entity])
    binding={**case['binding'], 'basis':plain(f.resolved),'parameters':plain(f.parameters),
        'target_m':inp.task.goal.data['target_m'], 'mount':inp.task.environment.data['mount'],
        'tension_limits_n':f.expression.tendon_force_limits_n,'model_identity':digest(plain(f.expression)),
        'output_expression':'R_world_base * symbolic_tip_position(q) + p_world_base; AD in x and u',
        'coordinate_order':f.expression.coordinate_order,'tendon_order':f.expression.tendon_order}
    return OutputLinearizedModel(state_definition=system.state_definition,input_definition=system.input_definition,
        output_definition=[SignalSpec(name='tip_position',entity='tip',dimension=3,units='m',frame='world',phase='instantaneous')],
        x0=point['x'],u0=point['u'],y0=np.asarray(y).reshape(-1).tolist(),A=A.tolist(),B=B.tolist(),
        C=np.asarray(C).tolist(),D=np.asarray(D).tolist(),drift=d.reshape(-1).tolist(),time_domain='continuous',
        binding=binding,operating_point={k:v for k,v in point.items() if k not in ('x','u')},
        state_scales=qscale+[v/p.duration_s for v in qscale],input_scales=[p.input_scale_n]*len(system.u0),
        output_scales=[p.output_scale_m]*3,
        normalization_derivation='Structural-linear nodal curvature coefficients [ky,kz] at dimensionless knots; each coefficient scale 1/baseline section length, rate scale 1/(length*0.35 s); tensions 8 N; world tip 0.01 m.',
        protocol_identity=digest(plain(p)),evidence=[case_ref])


def derivative_check(model,graph,p):
    _,_,f,h=graph; x=np.asarray(model.x0); u=np.asarray(model.u0)
    dx=np.asarray(model.state_scales)*np.cos(np.arange(len(x))+1); du=np.asarray(model.input_scales)*np.sin(np.arange(len(u))+1)
    step=p.derivative_step
    fd=(f.evaluate(x+step*dx,u+step*du)['xdot']-f.evaluate(x-step*dx,u-step*du)['xdot']).ravel()/(2*step)
    ad=np.asarray(model.A)@dx+np.asarray(model.B)@du
    fy=(np.asarray(h(x+step*dx,u+step*du)[0])-np.asarray(h(x-step*dx,u-step*du)[0])).ravel()/(2*step)
    ay=np.asarray(model.C)@dx+np.asarray(model.D)@du
    # Compare derivatives after physical output/state normalization.
    def compare(a,b,scale):
        a=a/scale; b=b/scale
        return dict(passed=bool(np.allclose(a,b,atol=p.derivative_atol,rtol=p.derivative_rtol)),
            max_absolute_error=float(max(abs(a-b))),max_scaled_error=float(max(abs(a-b)/(p.derivative_atol+p.derivative_rtol*abs(b)))))
    return dict(step=step,dynamics=compare(fd,ad,model.state_scales),output=compare(fy,ay,model.output_scales))


def linearize_saved(ctx,args):
    case=ctx.artifact(args.case); p=AnalysisProtocol.model_validate(ctx.artifact(args.protocol)); points=saved_points(case,p)
    good=[r for r in points if r['available']]
    if not good: return AnalysisResult(kind='linearization',protocol=args.protocol,bindings=[case['binding']],records=points,evidence=[args.case],limitations=LIMITATIONS)
    graph=make_graph(case,good[0]); records=[]
    for point in points:
        if not point['available']: records.append(point); continue
        model=linear_model(case,point,p,args.case,graph)
        ref=ctx.save_artifact(model)
        records.append(dict(point=model.operating_point,model=plain(ref),derivative_check=derivative_check(model,graph,p) if point is good[0] else None))
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


def saved_case(ctx,args):
    from collections import Counter
    from schemas.platform_diagnostics import DiagnosticFact
    c=ctx.artifact(args.case); p=AnalysisProtocol.model_validate(ctx.artifact(args.protocol))
    rows=c['saved'].get('controller_observations.json',[])
    fact=DiagnosticFact(fact_id='saved-terminal-error',statement=f"Saved evaluator terminal error {c['factual_result']['terminal_error_m']} m; task accepted {c['factual_result']['task_accepted']}.",evidence=[args.case])
    return AnalysisResult(kind='saved_case',protocol=args.protocol,bindings=[c['binding']],
        records=[dict(factual_result=c['factual_result'],samples=saved_points(c,p),observation_count=len(rows),
            plan_sources=dict(Counter(r.get('plan_source','missing') for r in rows)),
            selected_iterations=dict(Counter(str(r.get('optimization_selected_iteration')) for r in rows)),
            saved_tension_bound_usage=dict(count=len(rows),saturated_entries=sum(sum(r.get('force_limit_saturated',[])) for r in rows)))],
        evidence=[args.case],facts=[fact],limitations=LIMITATIONS+['Observations do not establish causal attribution.'])
