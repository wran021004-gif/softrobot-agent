"""Fresh activity authorization, operation-specific reservations and evidence."""
import os
import subprocess
import time
import numpy as np
from schemas.casadi_feedback import Result, Candidate
from tools.platform_store import plain
from tools.state_io import atomic_json, read, digest
from tools.spec_tools import ROOT

ACTIVITY='casadi-feedback-research-20261010'
RESERVATIONS=dict(diagnose=900.,speed=600.,solve=900.,replay=450.)


def preflight(inp,args,reg):
    if inp.run_id!=ACTIVITY:raise ValueError('FRESH_FEEDBACK_ACTIVITY_REQUIRED')
    return {}


def budget(store):
    state=store.session(ACTIVITY)['state'];ledger=store.remaining()
    return dict(numerical_s=7200.-state['numerical_s'],initial_investigation_s=1800.-state['investigation_s'],
        nlp_solves=4-state['nlp_solves'],initial_solves=2-state['batch_counts']['initial'],revision_solves=2-state['batch_counts']['revision'],
        provider_requests=ledger['remaining']['model_calls'],protected_provider_sends=4,
        public_tool_calls=ledger['remaining']['tool_calls'],backend_launches=ledger['remaining']['backend_solves'],
        activity_s=state['cutoff_unix']+1800.-time.time(),scientific_window_s=state['cutoff_unix']-time.time())


def validate_schedule(candidate):
    u=np.asarray(candidate['tensions_n']);x=np.asarray(candidate['states']);d=candidate['d']
    if u.shape!=(35,6) or x.ndim!=2 or x.shape[1]!=24 or not np.isfinite(np.r_[u.ravel(),x.ravel(),d]).all() or not -1.-1e-8<=d<=1.+1e-8 or u.min() < -1e-8 or u.max()>8.+1e-8:
        raise ValueError('FINITE_LEGAL_DESIGN_AND_35_BOUNDED_SIX_CHANNEL_INPUTS_REQUIRED')
    return dict(candidate,tensions_n=np.clip(u,0.,8.).tolist(),replay_input_clip_max_n=float(np.max(np.abs(u-np.clip(u,0.,8.)))))


def plan(ctx,args):
    state=ctx.store.session(ctx.run_id)['state']
    if state['research_status']=='stopped':raise ValueError('MODEL_STOP_SEALED')
    if state.get('pending'):raise ValueError('UNKNOWN_NUMERICAL_OUTCOME_INSPECT_FIRST')
    for ref in args.supporting_evidence:ctx.artifact(ref)
    new_results=[r for r in state['results'] if r['operation'] in ('solve','replay')]
    if args.action!='batch' and not any(r['operation']=='solve' for r in new_results):raise ValueError('FIRST_MODEL_BATCH_EXECUTION_REQUIRED')
    if new_results and not any(plain(ref)==r['reference'] for ref in args.supporting_evidence for r in new_results):
        raise ValueError('DECISION_MUST_CITE_ACTUAL_RETURNED_EVIDENCE')
    batch='initial' if not state['plans'] else 'revision'
    if args.action=='batch':
        if sum(p['action']=='batch' for p in state['plans'])>=2:raise ValueError('AT_MOST_TWO_MODEL_BATCHES')
        if new_results and not any(r['operation']=='replay' for r in new_results):raise ValueError('CONSUME_INITIAL_REPLAY_BEFORE_REVISION')
        needed=len(args.candidates)
        if state['batch_counts'][batch]+needed>2 or state['nlp_solves']+needed>4:raise ValueError('FOUR_SOLVE_CEILING')
        if state['numerical_s']+needed*(RESERVATIONS['solve']+RESERVATIONS['replay'])>7200.:raise ValueError('BATCH_RESERVATION_EXCEEDS_NUMERICAL_ALLOWANCE')
        if ctx.store.remaining()['remaining']['model_calls']<=4:raise ValueError('FINAL_FOUR_PROVIDER_SENDS_PROTECTED')
        if time.time()+needed*1350.>=state['cutoff_unix']:raise ValueError('BATCH_CANNOT_FIT_SCIENTIFIC_WINDOW')
        for candidate in args.candidates:
            if candidate.substeps==2 and not state.get('refined_grid_supported'):raise ValueError('FINER_GRID_REQUIRES_DISCREPANCY_EVIDENCE')
            if candidate.source_candidate:validate_schedule(ctx.artifact(candidate.source_candidate).get('candidate',ctx.artifact(candidate.source_candidate)))
    if args.action=='diagnostic_replay':
        if state.get('model_diagnostic_count',0)>=1:raise ValueError('ONE_SUPPORTED_MODEL_DIAGNOSTIC')
        validate_schedule(ctx.artifact(args.diagnostic_candidate).get('candidate',ctx.artifact(args.diagnostic_candidate)))
    ref=ctx.save_artifact(plain(args),'model_plan_original')
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state']
        current['plans'].append(dict(reference=plain(ref),action=args.action,batch=batch))
        if args.action=='stop':current['research_status']='stopped';current['final_disposition']=plain(ref)
        elif args.action=='diagnostic_replay':current['model_diagnostic_count']=current.get('model_diagnostic_count',0)+1
        ctx.store.update_state(db,ctx.run_id,current)
    return Result(detail=dict(accepted=True,plan_reference=plain(ref),batch=batch,action=args.action,remaining_budget=budget(ctx.store)))


def dispatch(ctx,args,operation):
    state=ctx.store.session(ctx.run_id)['state'];reserve=RESERVATIONS[operation]
    if 'freeze' not in state:raise ValueError('COMMIT_AND_BIND_BEFORE_DISPATCH')
    if state.get('pending'):raise ValueError('UNKNOWN_NUMERICAL_OUTCOME_INSPECT_PENDING_FILES_NO_REPEAT')
    if state['research_status']=='stopped':raise ValueError('MODEL_STOP_SEALED')
    if state['numerical_s']+reserve>7200. or time.time()+reserve>=state['cutoff_unix']:raise ValueError('OPERATION_CANNOT_FIT_REMAINING_BUDGET')
    request=dict(activity=ACTIVITY,store_root=str(ctx.store.root),request_id=ctx.request.request_id,
        operation=operation,configuration=plain(ctx.input),arguments=plain(args),implementation=state['freeze'],
        local_ad=state.get('local_ad','reverse'))
    if operation in ('diagnose','speed'):
        if any(r['operation']==operation for r in state['results']):raise ValueError('PRESCRIBED_OPERATION_ALREADY_RECORDED')
        if state['investigation_s']+reserve>1800.:raise ValueError('INITIAL_INVESTIGATION_CEILING')
    if operation=='speed' and not any(r['operation']=='diagnose' for r in state['results']):raise ValueError('DIAGNOSE_BEFORE_SPEED')
    if operation=='solve':
        if not state.get('speed_check_passed'):raise ValueError('CHANGED_DERIVATIVE_EXECUTION_CHECK_REQUIRED')
        if state['nlp_solves']>=4 or state['batch_counts'][args.batch]>=2:raise ValueError('NLP_SOLVE_CEILING')
        accepted=next((p for p in state['plans'] if p['reference']==plain(args.plan_reference)),None)
        if not accepted or accepted['action']!='batch' or accepted['batch']!=args.batch:raise ValueError('ACCEPTED_MODEL_PLAN_REQUIRED')
        original=ctx.artifact(args.plan_reference)
        choices=plain(Candidate.model_validate({k:v for k,v in plain(args).items() if k in Candidate.model_fields}))
        if args.candidate_index>=len(original['candidates']) or choices!=original['candidates'][args.candidate_index]:raise ValueError('SOLVE_MUST_MATCH_MODEL_PLAN')
        key=args.plan_reference.artifact_id+':'+str(args.candidate_index)
        if key in state['dispatched_candidates']:raise ValueError('PLAN_CANDIDATE_ALREADY_DISPATCHED')
        if args.source_candidate:
            artifact=ctx.artifact(args.source_candidate);source=validate_schedule(artifact.get('candidate',artifact));request['saved_tensions']=source['tensions_n']
    if operation=='replay':
        artifact=ctx.artifact(args.candidate);request['candidate']=validate_schedule(artifact.get('candidate',artifact))
    inp,out,progress=ctx.folder/'worker_input.json',ctx.folder/'worker_output.json',ctx.folder/'worker_progress.json'
    request['progress']=str(progress);atomic_json(inp,request)
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state'];current['pending']=dict(operation=operation,input=str(inp),output=str(out),progress=str(progress),
            request_id=ctx.request.request_id,reserved_s=reserve,started_unix=time.time())
        if operation=='solve':
            current['nlp_solves']+=1;current['batch_counts'][args.batch]+=1;current['dispatched_candidates'].append(key)
        ctx.store.update_state(db,ctx.run_id,current)
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    started=time.perf_counter()
    try:
        process=subprocess.run([state['python'],'-m','tools.casadi_feedback_worker',str(inp),str(out)],cwd=ROOT,env=env,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=reserve)
        stdout=process.stdout;result=read(out) if out.exists() else dict(status='numerical_error',termination_reason='Worker returned no output',returncode=process.returncode)
    except subprocess.TimeoutExpired as exc:
        # subprocess.run has killed and waited for this known timeout, so settle it once.
        stdout=exc.stdout or b'';result=dict(status='worker_timeout',termination_reason='Known killed/waited worker exceeded operation-specific process ceiling',reserved_s=reserve)
    elapsed=time.perf_counter()-started
    log=ctx.save_artifact(dict(text=stdout.decode('utf8',errors='replace')),'feedback_worker_log')
    result.update(operation=operation,arguments=plain(args),implementation=state['freeze'],problem_identity=state['spec_identity'],
        process_elapsed_s=elapsed,log_reference=plain(log),solve_ceiling_overrun_s=max(0.,result.get('costs_s',{}).get('solve',0.)-600.))
    ref=ctx.save_artifact(result,'feedback_'+operation)
    candidate_ref=ctx.save_artifact(result['candidate'],'feedback_candidate') if result.get('candidate') else None
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state'];current['numerical_s']+=elapsed;current.pop('pending',None)
        if operation in ('diagnose','speed'):current['investigation_s']+=elapsed
        current['results'].append(dict(operation=operation,status=result['status'],reference=plain(ref),candidate=plain(candidate_ref) if candidate_ref else None))
        if operation=='diagnose':
            comparisons=result.get('comparisons',{});a=comparisons.get('tight_original_vs_tight_refined',{});b=comparisons.get('tight_refined_vs_saved_bdf',{})
            current['refined_grid_supported']=bool(a.get('complete_horizon') and b.get('complete_horizon') and
                (a.get('max_tip_m',0.)>.001 or a.get('max_speed_m_s',0.)>.002))
        if operation=='speed':current['local_ad']=result.get('selected_local_ad','reverse');current['speed_check_passed']=result['status']=='passed'
        ctx.store.update_state(db,ctx.run_id,current)
    fields=('status','termination_reason','iterations','hard_max_normalized_violation','largest_hard_residuals','largest_relaxed_task_residuals',
        'relaxed_nlp_feasible','original_task_feasible','original_task_gaps','slack_values','trajectory_metrics','objective_components',
        'slack_definition','acceptance','physical_validation','replay','physical_eligible','comparisons','saved_nlp_metrics','precision_bdf',
        'full_warmed_speed_ratio','setup_repayment_jacobian_calls','selected_local_ad','adopted','equivalence_passed','costs_s','process_elapsed_s','solve_ceiling_overrun_s')
    compact={k:result[k] for k in fields if k in result}
    if result.get('candidate'):compact['design_values']=dict(d=result['candidate']['d'],lengths_m=result['candidate']['lengths_m'],selection=result['candidate']['selection'])
    return Result(detail=dict(**compact,operation=operation,evidence_reference=plain(ref),candidate_reference=plain(candidate_ref) if candidate_ref else None,
        candidate_identity=digest(result['candidate']) if result.get('candidate') else None,implementation_identity=state['freeze'],
        remaining_budget=budget(ctx.store),consumption=dict(numerical_s=ctx.store.session(ctx.run_id)['state']['numerical_s'],store=ctx.store.remaining()['used'])))


def diagnose(ctx,args):return dispatch(ctx,args,'diagnose')
def speed(ctx,args):return dispatch(ctx,args,'speed')
def solve(ctx,args):return dispatch(ctx,args,'solve')
def replay(ctx,args):return dispatch(ctx,args,'replay')
