"""Numerical subprocess; same functions serve direct and typed Host callers."""
import argparse
from copy import deepcopy
import time
import traceback
import casadi as ca
import numpy as np
from tools.state_io import atomic_json, read
from tools.platform_store import plain
from extensions.tendon_family.gvs_codesign import Workspace, expression, parameterized, integrate
from extensions.tendon_family.gvs_casadi import GVSCasadiFunctions
from extensions.optimization.ipopt import IpoptSolver


def correctness(configuration):
    started=time.perf_counter()
    # Tolerances are chosen before numerical evaluation, by physical quantity.
    tol=dict(geometry=(1e-10,1e-8), mass=(1e-12,1e-7), force=(1e-10,1e-7),
        acceleration=(1e-6,1e-7), derivative_geometry=(1e-8,2e-5),
        derivative_mass=(1e-11,2e-5), derivative_force=(1e-9,2e-5),
        derivative_acceleration=(1e-3,2e-5), constraint_direction=(2e-7,2e-5))
    w=Workspace(configuration); n=w.n; f=w.functions
    step_m=1e-5; step_d=step_m/.0055
    references=[]
    # Generate numeric designs once at baseline and the central pair, keeping
    # generator semantics (all other recipe fields and rigid pieces frozen).
    from extensions.tendon_family.generated_serial import Recipe, generate
    recipe=configuration['policy']['candidate_builder']['parameters']['data']['recipe']
    for delta in (0.,step_m,-step_m):
        cfg=deepcopy(configuration); r=deepcopy(recipe); r['lengths_m']=[.16+delta,.11-delta]
        cfg['robot']['structure']['data']=generate(Recipe.model_validate(r))[0]
        ef=expression(cfg); ref=GVSCasadiFunctions(ef)
        tip=ca.Function('reference_tip',[ref.q_symbol],[ref.tip_position_expression])
        references.append((ref,tip))
    x=ca.MX.sym('check_x',2*n); u=ca.MX.sym('check_u',w.m); a=ca.MX.sym('check_a',n); d=ca.MX.sym('check_d')
    values=f.function(x,u,d)
    selected={'tip':w.tip(x[:n],d), 'tendon_lengths':values[7], 'mass':values[2],
        'elastic':values[3],'damping':values[4],'gravity':values[5],'tendon_force':values[6],
        'tendon_jacobian':values[8],'velocity_bias':values[9], 'qdd':values[1],
        'implicit':f.implicit_residual(x,u,a,d)}
    checks=[]; passed=True
    def compare(label,actual,expected,tolerance):
        nonlocal passed
        actual=np.asarray(actual);expected=np.asarray(expected)
        error=float(np.max(np.abs(actual-expected))); scale=float(np.max(np.abs(expected)))
        ok=bool(np.isfinite(actual).all() and np.isfinite(expected).all() and error<=tolerance[0]+tolerance[1]*scale)
        checks.append(dict(name=label,max_abs_error=error,reference_scale=scale,passed=ok));passed &= ok
    derivative=ca.Function('length_partials',[x,u,a,d],
        [ca.jacobian(ca.vec(value),d) for value in selected.values()])
    for i,state in enumerate((np.zeros(2*n),np.r_[np.linspace(-2,3,n),np.linspace(-.3,.5,n)])):
        tension=np.linspace(.2,.4,w.m); accel=np.linspace(-5,7,n)
        actual=f.evaluate(state,tension,0.)
        outputs=[]
        for j,(ref,tip) in enumerate(references):
            v=ref.evaluate(state,tension)
            outputs.append(dict(tip=np.asarray(tip(state[:n]))+np.array([[0.],[0.],[.15]]),
                tendon_lengths=v['tendon_lengths_m'],mass=v['mass_matrix'],elastic=v['elastic_force'],
                damping=v['damping_force'],gravity=v['gravity_force'],tendon_force=v['tendon_generalized_force'],
                tendon_jacobian=v['tendon_length_jacobian'],velocity_bias=v['velocity_bias'],qdd=v['qdd'],
                implicit=ref.implicit_residual(state,tension,accel)))
        actual_values=[ca.Function('quantity',[x,u,a,d],[v])(state,tension,accel,0.) for v in selected.values()]
        derivatives=derivative(state,tension,accel,0.)
        for (name,value),ad in zip(zip(selected,actual_values),derivatives):
            kind='geometry' if name in ('tip','tendon_lengths','tendon_jacobian') else 'mass' if name=='mass' else 'acceleration' if name=='qdd' else 'force'
            compare(f'state{i}/{name}/baseline',value,outputs[0][name],tol[kind])
            for j,dd in ((1,step_d),(2,-step_d)):
                concrete=ca.Function('quantity',[x,u,a,d],[selected[name]])(state,tension,accel,dd)
                compare(f'state{i}/{name}/nearby{j}',concrete,outputs[j][name],tol[kind])
            finite=(np.asarray(outputs[1][name])-np.asarray(outputs[2][name]))/(2*step_d)
            compare(f'state{i}/{name}/length_partial',np.asarray(ad).ravel(),finite.reshape(-1,order='F'),tol['derivative_'+kind])
        compare(f'state{i}/virtual_work',actual['tendon_generalized_force'],
            -actual['tendon_length_jacobian'].T@tension[:,None],tol['force'])
    problem=w.assemble('B','pretension_0_2')
    order=list(problem.variables); z=np.array([problem.initial_guess[k] for k in order])
    direction=np.linspace(-.3,.4,len(z)); direction/=np.linalg.norm(direction)
    zz=ca.MX.sym('z',len(z)); g=w.value(zz)[1]
    directional=ca.Function('constraint_direction',[zz],[ca.jtimes(g,zz,ca.DM(direction))])
    epsilon=1e-6
    fd=(np.asarray(w.value(z+epsilon*direction)[1])-np.asarray(w.value(z-epsilon*direction)[1]))/(2*epsilon)
    compare('assembled_constraints/directional',directional(z),fd,tol['constraint_direction'])
    initial=np.asarray(w.value(z)[1]).ravel()[:w.steps*2*n]
    compare('coherent_guess/dynamics',initial,np.zeros_like(initial),(1e-7,0.))
    return dict(status='passed' if passed else 'failed',termination_reason='Focused numeric reference and exact-AD checks',
        tolerances=tol,central_step_m=step_m,central_step_d=step_d,checks=checks,
        coordinate_order=w.expression.coordinate_order,tendon_order=w.expression.tendon_order,
        dimensions=dict(curvature=n,reduced_state=2*n,inputs=w.m,variables=len(order),constraints=len(problem.constraints)),
        costs_s=dict(total=time.perf_counter()-started,mechanics=w.mechanics_construction_s,assembly=w.assembly_s))


def jacobian_execution(configuration):
    """Compare existing exact-AD execution modes on the same assembled graph."""
    started=time.perf_counter();w=Workspace(configuration);problem=w.assemble('B','pretension_0_2')
    z=ca.MX.sym('execution_z',len(problem.variables));g=w.value(z)[1]
    values=np.array([problem.initial_guess[name] for name in problem.variables]);records={};matrices={}
    atol,rtol=1e-8,1e-8
    for mode in ('reverse','automatic'):
        t=time.perf_counter();opts={'ad_weight':1.} if mode=='reverse' else {}
        f=ca.Function('execution_constraints_'+mode,[z],[g],opts);j=f.jacobian()
        construction=time.perf_counter()-t;t=time.perf_counter();matrix=j(values,ca.DM.zeros(g.numel()))
        elapsed=time.perf_counter()-t;matrices[mode]=np.asarray(matrix)
        records[mode]=dict(construction_s=construction,evaluation_s=elapsed,nnz=matrix.sparsity().nnz())
    error=np.abs(matrices['reverse']-matrices['automatic'])
    passed=bool(np.isfinite(error).all() and np.all(error<=atol+rtol*np.abs(matrices['reverse'])))
    return dict(status='passed' if passed else 'failed',scope='jacobian_execution',
        termination_reason='Exact automatic versus forced reverse AD on the same full-horizon constraint graph; no NLP invocation',
        tolerances=dict(absolute=atol,relative=rtol),max_abs_error=float(error.max()),
        design_column_nonzeros=int(np.count_nonzero(matrices['reverse'][:,0])),modes=records,
        mathematical_equations='unchanged',nlp_invocations=0,costs_s=dict(total=time.perf_counter()-started))


def solve(configuration,args,progress=None):
    started=time.perf_counter();w=Workspace(configuration,args['substeps'])
    problem=w.assemble(args['case'],args['initialization'])
    options=dict(max_iterations=1000,tolerance=1e-7,acceptable_tolerance=1e-6,
        constraint_jacobian_mode=args.get('jacobian_mode','reverse'),retain_feasible_iterate=True,hessian_approximation='limited-memory',
        # IPOPT checks deadlines between iterations. The first primary reached
        # 608.7 s with 600 s options; retain it and reserve a 30 s margin henceforth.
        max_cpu_s=570.,max_wall_s=570.,print_level=5)
    solver=IpoptSolver(options); solver.diagnostic_trace=True
    if progress: atomic_json(progress,dict(phase='solver_construction',unix=time.time()))
    # IPOPT construction is measured separately by the existing adapter.
    result=solver.solve(problem)
    candidate=w.decode(result.optimum)
    values=np.array([result.optimum[name] for name in problem.variables]); components=w.components(values)
    diagnostics=solver.last_diagnostics
    constraint=np.array(diagnostics['constraint_values']); largest=[]
    for i,c in enumerate(problem.constraints):
        violation=max(0.,(c.lower-constraint[i]) if c.lower is not None else 0.,(constraint[i]-c.upper) if c.upper is not None else 0.)
        if c.name.startswith('dynamics_'):
            _,k,j=c.name.split('_'); k,j=int(k),int(j)
            units='rad/m' if j<w.n else 'N*m^2/rad'; physical=violation*(10. if j<w.n else .001)
            t=(k+1)*w.h
        else:
            limit=.02 if c.name.startswith('holding_speed_') else .01
            units='m/s' if c.name.startswith('holding_speed_') else 'm'
            physical=max(0.,limit*np.sqrt(max(0.,constraint[i]))-limit)
            t=.35 if c.name=='terminal_position' else int(c.name.rsplit('_',1)[1])*w.h
        largest.append(dict(name=c.name,time_s=t,normalized_violation=violation,physical_violation=physical,units=units))
    largest.sort(key=lambda r:r['normalized_violation'],reverse=True)
    candidate.update(case=args['case'],initialization=args['initialization'],mathematical_feasible=bool(result.constraint_violation<=1e-5))
    return dict(status=result.status,termination_reason=diagnostics['return_status'],iterations=result.iterations,
        mathematical_feasibility='feasible_at_1e_5' if candidate['mathematical_feasible'] else 'infeasible_returned_iterate',
        objective_components=dict(effort=float(components[0]),variation_weighted=float(components[1]),total=result.objective_value),
        largest_residuals=largest[:12], normalized_max_violation=result.constraint_violation,
        trajectory_metrics=w.metrics(candidate),candidate=candidate,raw_returned=w.decode(solver.last_returned_optimum),
        optimization_result=plain(result),diagnostics=diagnostics,options=options,
        costs_s=dict(mechanics_construction=w.mechanics_construction_s,assembly_and_guess=w.assembly_s,
            solver_construction=diagnostics['construction_s'],solve=diagnostics['solve_s'],total=time.perf_counter()-started))


def replay(configuration,candidate):
    started=time.perf_counter();w=Workspace(configuration,candidate['substeps'])
    target=configuration['task']['goal']['data']['target_m']
    result,trajectory=integrate(w.functions,w.tip,w.velocity,candidate,target)
    return dict(status=result['status'],termination_reason=result['method'],case=candidate['case'],
        replay=result,trajectory=trajectory,mathematical_feasibility='feasible_at_1e_5' if candidate['mathematical_feasible'] else 'diagnostic_infeasible',
        physical_eligible=bool(candidate['mathematical_feasible'] and result['gates_passed']),
        costs_s=dict(mechanics_construction=w.mechanics_construction_s,total=time.perf_counter()-started))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('input');parser.add_argument('output');args=parser.parse_args()
    request=read(args.input);started=time.perf_counter()
    try:
        if request['operation']=='check':
            result=(jacobian_execution if request['arguments'].get('scope')=='jacobian_execution' else correctness)(request['configuration'])
        elif request['operation']=='solve':result=solve(request['configuration'],request['arguments'],request.get('progress'))
        else:result=replay(request['configuration'],request['candidate'])
    except Exception as exc:
        result=dict(status='numerical_error',termination_reason=str(exc),exception_type=type(exc).__name__,
            traceback=traceback.format_exc(),costs_s=dict(total=time.perf_counter()-started))
        traceback.print_exc()
    # Existing IPOPT diagnostics use +/-inf for absent bounds. Preserve them as
    # explicit nulls in standard JSON instead of nonstandard NaN/Infinity.
    def clean(value):
        if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
        if isinstance(value,list):return [clean(v) for v in value]
        if isinstance(value,float) and not np.isfinite(value):return None
        return value
    atomic_json(args.output,clean(result))


if __name__=='__main__':main()
