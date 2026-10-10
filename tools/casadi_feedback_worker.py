"""Bounded numerical operations; launched only by the shared Store boundary."""
import argparse
import time
import traceback
import casadi as ca
import numpy as np
from extensions.tendon_family.gvs_codesign import Workspace, integrate
from extensions.optimization.ipopt import IpoptSolver
from tools.platform_store import plain
from tools.state_io import read, atomic_json
from tools.spec_tools import ROOT

HISTORY=ROOT/'evidence/casadi_codesign_pilot_20261010'


def outputs(w, candidate):
    x=np.asarray(candidate['states']);d=candidate['d']
    return dict(times_s=candidate['times_s'],
        tip_positions_m=[np.asarray(w.tip(row[:w.n],d)).ravel().tolist() for row in x],
        tip_velocities_m_s=[np.asarray(w.velocity(row[:w.n],row[w.n:],d)).ravel().tolist() for row in x])


def compare(a,b):
    t=np.arange(36)*.01; end=min(a['times_s'][-1],b['times_s'][-1]);t=t[t<=end+1e-12]
    result=dict(common_times_s=t.tolist(),complete_horizon=bool(end>=.35-1e-12))
    for key,label in [('tip_positions_m','tip_m'),('tip_velocities_m_s','speed_m_s')]:
        aa=np.asarray(a[key]);bb=np.asarray(b[key])
        av=np.array([np.interp(t,a['times_s'],aa[:,j]) for j in range(3)]).T
        bv=np.array([np.interp(t,b['times_s'],bb[:,j]) for j in range(3)]).T
        delta=np.linalg.norm(av-bv,axis=1)
        result['max_'+label]=float(max(delta));result['per_node_'+label]=delta.tolist()
    return result


def diagnose(configuration):
    started=time.perf_counter();saved=read(HISTORY/'07_solve_A.json')['candidate']
    selected=read(HISTORY/'selected_latest_A.json')
    if selected['selection']['iteration']!=59 or selected['selection']['source_solver']['artifact_id']!='baae52d1f11518a40982491879c4a0ab380c519a617a0588e989a0e496bebbf2':
        raise ValueError('CORRECTED_A_PROVENANCE_MISMATCH')
    traces={'saved_nlp':None};rollouts={};ws={}
    for substeps,label in [(1,'tight_original'),(2,'tight_refined')]:
        w=Workspace(configuration,substeps);ws[label]=w
        rollout=w.rollout(saved['tensions_n'],saved['d'])
        candidate=dict(saved,states=rollout['states'],times_s=rollout['times_s'],substeps=substeps)
        rollouts[label]=dict(rollout,metrics=w.metrics(candidate) if not rollout['failure'] else None)
        traces[label]=outputs(w,candidate)
    w=ws['tight_original'];traces['saved_nlp']=outputs(w,saved)
    saved_bdf=read(HISTORY/'09_replay_A.json');traces['saved_bdf']=saved_bdf['trajectory']
    precision,trajectory=integrate(w.functions,w.tip,w.velocity,saved,
        configuration['task']['goal']['data']['target_m'],rtol=1e-10,atol_q=1e-11,atol_v=1e-9)
    traces['precision_bdf']=trajectory
    comparisons={a+'_vs_'+b:compare(traces[a],traces[b]) for a,b in [
        ('saved_nlp','tight_original'),('tight_original','tight_refined'),
        ('tight_refined','saved_bdf'),('saved_bdf','precision_bdf')]}
    # Direct residuals of saved optimizer states distinguish defect from grid effects.
    saved_residuals=[]
    for k in range(35):
        r=np.asarray(w.step(saved['states'][k],saved['states'][k+1],saved['tensions_n'][k],saved['d'])).ravel()
        saved_residuals.append(dict(step=k,max_normalized_residual=float(max(abs(r))),
            kinematic_max_rad_m=float(max(abs(r[:w.n]))*10.),force_balance_max_N_m2_rad=float(max(abs(r[w.n:]))*.001)))
    return dict(status='completed' if all(not v['failure'] for v in rollouts.values()) and precision['status']=='completed' else 'inconclusive',
        termination_reason='Fixed corrected-A iteration-59 inputs and lengths; reconstructed continuously from zero; no design search',
        provenance=dict(source_solver=selected['selection']['source_solver'],selected_candidate=selected['reference'],
            saved_replay_path=str(HISTORY/'09_replay_A.json'),historical_implementation=saved_bdf['implementation']),
        comparisons=comparisons,rollouts=rollouts,saved_nlp_metrics=w.metrics(saved),saved_nlp_residuals=saved_residuals,
        precision_bdf=precision,traces=traces,nlp_invocations=0,costs_s=dict(total=time.perf_counter()-started))


def speed(configuration):
    started=time.perf_counter();saved=read(HISTORY/'07_solve_A.json')['candidate']
    records={};arrays={};tol=dict(absolute=1e-8,relative=1e-8)
    for mode in ('reverse','automatic'):
        w=Workspace(configuration,local_ad=mode);t=time.perf_counter()
        z=ca.MX.sym('local_z',4*w.n+w.m+1)
        value=ca.Function('local_'+mode,[z],[w.step(z[:2*w.n],z[2*w.n:4*w.n],z[4*w.n:4*w.n+w.m],z[-1])])
        jac=value.jacobian();local_construction=time.perf_counter()-t
        local=[];local_arrays=[]
        for k in (0,29,34):
            point=np.r_[saved['states'][k],saved['states'][k+1],saved['tensions_n'][k],saved['d']]
            v=np.asarray(value(point));t=time.perf_counter();j=np.asarray(jac(point,ca.DM.zeros(2*w.n)));cold=time.perf_counter()-t
            times=[]
            for _ in range(2):
                t=time.perf_counter();j=np.asarray(jac(point,ca.DM.zeros(2*w.n)));times.append(time.perf_counter()-t)
            local.append(dict(step=k,cold_s=cold,warmed_s=times));local_arrays.append((v,j))
        problem=w.assemble('A','pretension_0_2');point=[]
        for name in problem.variables:
            pieces=name.split('/')
            point.append(saved['d'] if pieces[0]=='design' else saved['states'][int(pieces[1])][int(pieces[2])]/w.scales[int(pieces[2])] if pieces[0]=='x' else saved['tensions_n'][int(pieces[1])][int(pieces[2])]/8.)
        t=time.perf_counter();zz=ca.MX.sym('full_z',len(point));g=w.value(zz)[1]
        fn=ca.Function('full_auto_'+mode,[zz],[g]);jj=fn.jacobian();full_construction=time.perf_counter()-t
        vv=np.asarray(fn(point));times=[]
        for _ in range(3):
            t=time.perf_counter();matrix=np.asarray(jj(point,ca.DM.zeros(g.numel())));times.append(time.perf_counter()-t)
        arrays[mode]=dict(local=local_arrays,full=(vv,matrix))
        records[mode]=dict(mechanics_construction_s=w.mechanics_construction_s,local_derivative_construction_s=local_construction,
            local=local,assembly_s=w.assembly_s,full_derivative_construction_s=full_construction,
            full_cold_s=times[0],full_warmed_s=times[1:])
    errors=[];passed=True
    for a,b in zip(arrays['reverse']['local']+[arrays['reverse']['full']],arrays['automatic']['local']+[arrays['automatic']['full']]):
        for av,bv in zip(a,b):
            error=np.abs(av-bv);errors.append(float(error.max()))
            passed &= bool(np.isfinite(error).all() and np.all(error<=tol['absolute']+tol['relative']*np.abs(av)))
    baseline=np.mean(records['reverse']['full_warmed_s']);trial=np.mean(records['automatic']['full_warmed_s'])
    setup=records['automatic']['mechanics_construction_s']+records['automatic']['assembly_s']+records['automatic']['full_derivative_construction_s']
    repayment=setup/(baseline-trial) if baseline>trial else None
    adopted=bool(passed and baseline>trial*1.05 and repayment is not None and repayment<=30.)
    import unittest,io
    from tests.test_casadi_feedback import PlanTests,numerical_semantics
    stream=io.StringIO();checks=unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromTestCase(PlanTests))
    semantics=numerical_semantics(configuration)
    passed=passed and checks.wasSuccessful()
    return dict(status='passed' if passed else 'failed',termination_reason='Single change: remove local step forced-reverse AD; full NLP remains exact automatic AD',
        modes=records,max_abs_errors=errors,tolerances=tol,equivalence_passed=passed,
        full_warmed_speed_ratio=float(baseline/trial),setup_repayment_jacobian_calls=repayment,
        selected_local_ad='automatic' if adopted else 'reverse',adopted=adopted,
        setup_repayment_assumption='30 full Jacobian calls per one bounded solve; no extra NLP benchmarking',
        focused_checks=dict(unit_tests=checks.testsRun,output=stream.getvalue(),semantics=semantics),
        nlp_invocations=0,costs_s=dict(total=time.perf_counter()-started))


def assess(w, problem, values):
    order=list(problem.variables);vector=np.array([values[key] for key in order]);_,g=w.value(vector);g=np.asarray(g).ravel()
    residuals=[]
    for name,val in zip(order,vector):
        bounds=problem.variables[name]['bounds'];err=max(0.,bounds[0]-val if bounds[0] is not None else 0.,val-bounds[1] if bounds[1] is not None else 0.)
        residuals.append(dict(name=name,normalized_violation=float(err),kind='variable_bound'))
    soft=[]
    for c,val in zip(problem.constraints,g):
        err=max(0.,c.lower-val if c.lower is not None else 0.,val-c.upper if c.upper is not None else 0.)
        (residuals if c.name.startswith('dynamics_') else soft).append(dict(name=c.name,normalized_violation=float(err),kind='dynamics' if c.name.startswith('dynamics_') else 'relaxed_task'))
    candidate=w.decode(values);metrics=w.metrics(candidate);hard=max(r['normalized_violation'] for r in residuals)
    gaps=dict(position=max(0.,(max(metrics['terminal_position_error_m'],metrics['holding_max_position_error_m'])/.01)**2-1.),
        speed=max(0.,(metrics['holding_max_speed_m_s']/.02)**2-1.))
    relaxed=max([hard]+[r['normalized_violation'] for r in soft]);components=w.components(vector)
    candidate.update(case='B',mathematical_feasible=bool(hard<=1e-5 and max(gaps.values())<=1e-5),
        relaxed_feasible=bool(relaxed<=1e-5),slacks=dict(position=values['slack/position'],speed=values['slack/speed']))
    return dict(candidate=candidate,hard_max_normalized_violation=hard,relaxed_max_normalized_violation=relaxed,
        relaxed_nlp_feasible=bool(relaxed<=1e-5),original_task_feasible=candidate['mathematical_feasible'],
        original_task_gaps=gaps,slack_values=candidate['slacks'],trajectory_metrics=metrics,
        largest_hard_residuals=sorted(residuals,key=lambda r:r['normalized_violation'],reverse=True)[:8],
        largest_relaxed_task_residuals=sorted(soft,key=lambda r:r['normalized_violation'],reverse=True)[:4],
        effort=float(components[0]),variation_weighted=float(components[1]))


def solve(configuration,args,local_ad,saved_tensions=None,progress=None):
    started=time.perf_counter();w=Workspace(configuration,args['substeps'],local_ad)
    problem=w.assemble('B',args['initialization'],args,saved_tensions)
    options=dict(max_iterations=1000,tolerance=1e-7,acceptable_tolerance=1e-6,constraint_jacobian_mode='automatic',
        retain_feasible_iterate=True,hessian_approximation='limited-memory',max_cpu_s=570.,max_wall_s=570.,print_level=5)
    solver=IpoptSolver(options);solver.diagnostic_trace=True
    if progress:atomic_json(progress,dict(phase='solver_construction',unix=time.time()))
    result=solver.solve(problem);diagnostics=solver.last_diagnostics
    pool=[]
    for point in diagnostics['retained_diagnostic_points']:
        if (point['iteration'] or 0)<0:continue
        values=dict(zip(diagnostics['variable_order'],point['vector']));item=assess(w,problem,values)
        item.update(iteration=point['iteration'],role=point['label']);pool.append(item)
    if not pool:pool=[dict(assess(w,problem,result.optimum),iteration=result.iterations,role='returned')]
    # Hard validity first; compare frozen task gaps, never softened constraint error alone.
    def rank(item):
        hard=item['hard_max_normalized_violation'];gaps=item['original_task_gaps']
        return (hard>1e-5,hard if hard>1e-5 else 0.,max(gaps.values()),sum(gaps.values()),item['effort']+item['variation_weighted'])
    chosen=min(pool,key=rank);candidate=chosen['candidate']
    candidate.update(initialization=args['initialization'],selection=dict(label='hard_validity_then_original_task_gaps_then_effort',iteration=chosen['iteration']))
    return dict(status=result.status,termination_reason=diagnostics['return_status'],iterations=result.iterations,
        **chosen,candidate=candidate,retained_candidate_assessments=[{k:v for k,v in p.items() if k!='candidate'} for p in pool],
        objective_components=dict(effort=chosen['effort'],variation_weighted=chosen['variation_weighted'],
            selected_search_objective=args['position_weight']*chosen['slack_values']['position']+args['speed_weight']*chosen['slack_values']['speed']+args['secondary_coefficient']*(chosen['effort']+chosen['variation_weighted'])),
        slack_definition='Two shared nonnegative slacks: one for all terminal/holding normalized position squared constraints; one for all holding normalized speed squared constraints',
        acceptance='Original hard dynamics/bounds and unsoftened position/speed limits; slack is never subtracted',
        physical_validation='not_run',diagnostics=diagnostics,raw_returned=w.decode(solver.last_returned_optimum),
        optimization_result=plain(result),options=options,initial_rollout=w.initial_rollout,
        costs_s=dict(mechanics_construction=w.mechanics_construction_s,assembly_and_guess=w.assembly_s,
            solver_construction=diagnostics['construction_s'],solve=diagnostics['solve_s'],total=time.perf_counter()-started))


def main():
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');args=p.parse_args()
    request=read(args.input);started=time.perf_counter()
    from tools.platform_store import Store
    store=Store(request['store_root']);state=store.session(request['activity'])['state']
    pending=state.get('pending',{})
    if request['activity']!='casadi-feedback-research-20261010' or pending.get('request_id')!=request['request_id'] or pending.get('input')!=str(args.input):
        raise ValueError('DIRECT_WORKER_REQUIRES_SHARED_ACTIVE_RESERVATION')
    try:
        op=request['operation'];cfg=request['configuration']
        if op=='diagnose':result=diagnose(cfg)
        elif op=='speed':result=speed(cfg)
        elif op=='solve':result=solve(cfg,request['arguments'],request['local_ad'],request.get('saved_tensions'),request.get('progress'))
        else:
            from tools.casadi_codesign_worker import replay
            result=replay(cfg,request['candidate'])
    except Exception as exc:
        result=dict(status='numerical_error',termination_reason=str(exc),exception_type=type(exc).__name__,
            traceback=traceback.format_exc(),costs_s=dict(total=time.perf_counter()-started));traceback.print_exc()
    def clean(v):
        if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
        if isinstance(v,list):return [clean(x) for x in v]
        if isinstance(v,float) and not np.isfinite(v):return None
        return v
    atomic_json(args.output,clean(result))


if __name__=='__main__':main()
