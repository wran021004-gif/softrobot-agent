"""Store-reserved process dispatch and compact mathematical feedback."""
from pathlib import Path
import os
import subprocess
import time
from schemas.casadi_codesign import Feedback
from tools.state_io import atomic_json, read, digest
from tools.platform_store import plain
from tools.spec_tools import ROOT


def specification(case):
    return read(ROOT/'examples/casadi_codesign'/f'case_{case}.json')


def preflight(inp,args,reg):
    if inp.run_id != 'casadi-codesign-pilot-20261010':
        raise ValueError('FRESH_CASADI_PILOT_ACTIVITY_REQUIRED')
    return {}


def dispatch(ctx,args,operation):
    state=ctx.store.session(ctx.run_id)['state'];case=getattr(args,'case',None)
    if 'casadi_freeze' not in state:raise ValueError('COMMITTED_IMPLEMENTATION_FREEZE_REQUIRED')
    if state.get('casadi_pending'):raise ValueError('UNKNOWN_NUMERICAL_OUTCOME_INSPECT_PENDING_FILES_NO_REPEAT')
    if operation!='check' and state.get('casadi_check',{}).get('status')!='passed':raise ValueError('FOCUSED_CORRECTNESS_CHECK_REQUIRED')
    candidate=None
    if operation=='replay':
        artifact=ctx.artifact(args.candidate);candidate=artifact.get('candidate',artifact)
        if 'tensions_n' not in candidate:raise ValueError('RETURNED_CANDIDATE_REQUIRED')
        import numpy as np
        u=np.asarray(candidate['tensions_n']);x=np.asarray(candidate['states']);d=candidate['d']
        if u.shape!=(35,6) or not np.isfinite(np.r_[u.ravel(),x.ravel(),d]).all() or u.min() < -1e-8 or u.max()>8.+1e-8:
            raise ValueError('FINITE_BOUNDED_SCHEDULE_REQUIRED')
        # Tiny solver bound roundoff is recorded and removed only for replay.
        candidate=dict(candidate,tensions_n=np.clip(u,0.,8.).tolist(),replay_input_clip_max_n=float(np.max(np.abs(u-np.clip(u,0.,8.)))))
        case=candidate['case']
    reserve=1800. if operation=='solve' else 900.
    if state['casadi_numerical_s']+reserve>7200. or time.time()+reserve>=state['casadi_cutoff_unix']:
        raise ValueError('OPERATION_CANNOT_FIT_REMAINING_BUDGET')
    if operation=='solve':
        category=args.category
        if state['casadi_solves']>=6 or state['casadi_solve_categories'][category]>=2:
            raise ValueError('NLP_SOLVE_CEILING_REACHED')
        if category=='primary' and (args.initialization!='pretension_0_2' or args.substeps!=1):
            raise ValueError('PRIMARY_INITIALIZATION_AND_GRID_FROZEN')
    inp,out,progress=ctx.folder/'worker_input.json',ctx.folder/'worker_output.json',ctx.folder/'worker_progress.json'
    request=dict(operation=operation,configuration=plain(ctx.input),arguments=plain(args),implementation=state['casadi_freeze'],progress=str(progress))
    if candidate:request['candidate']=candidate
    atomic_json(inp,request)
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state']
        current['casadi_pending']=dict(operation=operation,input=str(inp),output=str(out),progress=str(progress),reserved_s=reserve,started_unix=time.time())
        if operation=='solve':
            current['casadi_solves']+=1;current['casadi_solve_categories'][args.category]+=1
        ctx.store.update_state(db,ctx.run_id,current)
    started=time.perf_counter()
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    # An interrupted/timeout process retains its pending identity. A known
    # output is recovered explicitly, never by resending the scientific work.
    process=subprocess.run([state['casadi_python'],'-m','tools.casadi_codesign_worker',str(inp),str(out)],
        cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=reserve)
    elapsed=time.perf_counter()-started
    log=ctx.save_artifact(dict(encoding='utf8',text=process.stdout.decode('utf8',errors='replace')),'casadi_worker_log')
    result=read(out) if out.exists() else dict(status='numerical_error',termination_reason='Worker returned no output',returncode=process.returncode)
    result.update(implementation=state['casadi_freeze'],operation=operation,problem_identity=digest(specification(case or 'A')),
        process_elapsed_s=elapsed,log_reference=plain(log),arguments=plain(args))
    ref=ctx.save_artifact(result,'casadi_'+operation)
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state'];current['casadi_numerical_s']+=elapsed
        current.pop('casadi_pending',None)
        current.setdefault('casadi_results',[]).append(dict(operation=operation,case=case,status=result['status'],reference=plain(ref)))
        if operation=='check':current['casadi_check']=dict(status=result['status'],reference=plain(ref))
        ctx.store.update_state(db,ctx.run_id,current)
    state=ctx.store.session(ctx.run_id)['state']
    trajectory=None
    if result.get('candidate'):trajectory=ctx.save_artifact(result['candidate'],'casadi_trajectory')
    if result.get('trajectory'):trajectory=ctx.save_artifact(result['trajectory'],'casadi_replay_trajectory')
    return Feedback(operation=operation,case=case,problem_identity=result['problem_identity'],
        implementation_identity=state['casadi_freeze'],candidate_identity=digest(result['candidate']) if result.get('candidate') else digest(candidate) if candidate else None,
        evidence_identity=ref.artifact_id,status=result['status'],termination_reason=result['termination_reason'],
        iterations=result.get('iterations',0),design_values=dict(lengths_m=result.get('candidate',candidate or {}).get('lengths_m')) if (result.get('candidate') or candidate) else {},
        objective_components=result.get('objective_components',{}),largest_residuals=result.get('largest_residuals',[]),
        derivative_check=state.get('casadi_check',{}),replay=result.get('replay',{}),
        mathematical_feasibility=result.get('mathematical_feasibility','not_established'),trajectory=trajectory,
        full_artifacts=[ref,log],consumption=dict(numerical_s=state['casadi_numerical_s'],nlp_invocations=state['casadi_solves'],
            categories=state['casadi_solve_categories'],backend_launches=0,provider_requests=0,operation_costs_s=result.get('costs_s',{})),
        remaining_budget=dict(numerical_s=7200.-state['casadi_numerical_s'],nlp_invocations=6-state['casadi_solves'],
            physical_launches=2,provider_requests=4,activity_s=state['casadi_cutoff_unix']+1800.-time.time(),store=ctx.store.remaining()))


def check(ctx,args):return dispatch(ctx,args,'check')
def solve(ctx,args):return dispatch(ctx,args,'solve')
def replay(ctx,args):return dispatch(ctx,args,'replay')
