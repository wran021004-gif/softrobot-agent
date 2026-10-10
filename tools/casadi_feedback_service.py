"""Fresh activity authorization, operation-specific reservations and evidence."""
import os
import subprocess
import time
import numpy as np
from schemas.casadi_feedback import Result, Candidate
from tools.platform_store import plain
from tools.state_io import atomic_json, read, digest
from tools.spec_tools import ROOT

SPEC=read(ROOT/'examples/casadi_nmpc/specification.json')
CEILINGS=SPEC['budgets']
ACTIVITY=SPEC['study_id']
RESERVATIONS=dict(diagnose=900.,speed=600.,solve=900.,replay=450.)


def preflight(inp,args,reg):
    if inp.run_id!=ACTIVITY:raise ValueError('FRESH_FEEDBACK_ACTIVITY_REQUIRED')
    return {}


def budget(store):
    state=store.session(ACTIVITY)['state'];ledger=store.remaining()
    return dict(numerical_s=float(CEILINGS['total_numerical_s'])-state['numerical_s'],
        nlp_solves=CEILINGS['full_nlp_solves']-state['nlp_solves'],
        independent_replays=CEILINGS['new_independent_replays']-state.get('replays',0),
        provider_requests=ledger['remaining']['model_calls'],protected_provider_sends=4,
        public_tool_calls=ledger['remaining']['tool_calls'],backend_launches=ledger['remaining']['backend_solves'],
        activity_s=state['cutoff_unix']+CEILINGS['delivery_reserve_s']-time.time(),
        scientific_window_s=state['cutoff_unix']-time.time())


def validate_schedule(candidate):
    u=np.asarray(candidate['tensions_n']);x=np.asarray(candidate['states']);d=candidate['d']
    if u.shape!=(35,6) or x.ndim!=2 or x.shape[1]!=24 or not np.isfinite(np.r_[u.ravel(),x.ravel(),d]).all() or not -1.-1e-8<=d<=1.+1e-8 or u.min() < -1e-8 or u.max()>8.+1e-8:
        raise ValueError('FINITE_LEGAL_DESIGN_AND_35_BOUNDED_SIX_CHANNEL_INPUTS_REQUIRED')
    return dict(candidate,tensions_n=np.clip(u,0.,8.).tolist(),replay_input_clip_max_n=float(np.max(np.abs(u-np.clip(u,0.,8.)))))


def plan(ctx,args):
    state=ctx.store.session(ctx.run_id)['state']
    if state['research_status']=='stopped':raise ValueError('MODEL_STOP_SEALED')
    if state.get('pending'):raise ValueError('UNKNOWN_NUMERICAL_OUTCOME_INSPECT_FIRST')
    if state.get('engineering_pause') and args.action!='stop':raise ValueError('ENGINEERING_PAUSE_REQUIRES_LOCAL_RECOVERY')
    for ref in args.supporting_evidence:ctx.artifact(ref)
    new_results=[r for r in state['results'] if not r.get('imported')]
    if new_results and not any(plain(ref)==r['reference'] for ref in args.supporting_evidence for r in new_results):
        raise ValueError('DECISION_MUST_CITE_ACTUAL_RETURNED_EVIDENCE')
    if args.action=='stop' and any(r['reference'] not in [plain(ref) for ref in args.supporting_evidence] for r in new_results):
        raise ValueError('FINAL_STOP_MUST_ACCOUNT_FOR_ALL_NEW_RESULTS')
    if args.action not in ('stop','diagnose'):
        send=state.get('pilot',{}).get('live_model_requests',0)
        if state.get('last_expensive_decision_send')==send:
            raise ValueError('ONE_EXPENSIVE_EXPERIMENT_PER_PROVIDER_DECISION_CONSUME_FEEDBACK_FIRST')
        if ctx.store.remaining()['remaining']['model_calls']<=4:raise ValueError('FINAL_FOUR_PROVIDER_SENDS_PROTECTED')
        reserve={'solve':1350.,'diagnostic_replay':450.,'closed_loop':1890.,'control_revision':1890.}[args.action]
        if state['numerical_s']+reserve>CEILINGS['total_numerical_s'] or time.time()+reserve>=state['cutoff_unix']:
            raise ValueError('OPERATION_CANNOT_FIT_REMAINING_BUDGET')
    batch='initial' if state['nlp_solves']==0 else 'revision'
    if args.action=='solve':
        if state['nlp_solves']>=CEILINGS['full_nlp_solves']:raise ValueError('TWO_ATTEMPT_CEILING')
        if state.get('replays',0)>=CEILINGS['new_independent_replays']:raise ValueError('THREE_REPLAY_CEILING')
        for candidate in args.candidates:
            if candidate.substeps==2 and not state.get('refined_grid_supported'):raise ValueError('FINER_GRID_REQUIRES_DISCREPANCY_EVIDENCE')
            if candidate.source_candidate:validate_schedule(ctx.artifact(candidate.source_candidate).get('candidate',ctx.artifact(candidate.source_candidate)))
    if args.action=='diagnostic_replay':
        if state.get('replays',0)>=CEILINGS['new_independent_replays']:raise ValueError('THREE_REPLAY_CEILING')
        validate_schedule(ctx.artifact(args.diagnostic_candidate).get('candidate',ctx.artifact(args.diagnostic_candidate)))
    if args.action in ('closed_loop','control_revision'):
        from tools.casadi_closed_loop import validate_control,resolve_candidate
        source,revision=validate_control(ctx.store,state,args.control,args.action)
        if ctx.store.remaining()['remaining']['backend_solves']<=0:raise ValueError('TWO_CLOSED_LOOP_LAUNCH_CEILING')
        resolve_candidate(ctx.store,args.control.candidate,source,args.control,ctx.run_id,plain(ctx.input.policy))
    ref=ctx.save_artifact(plain(args),'model_plan_original')
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state']
        current['plans'].append(dict(reference=plain(ref),action=args.action,batch=batch if args.action=='solve' else None))
        if args.action not in ('stop','diagnose'):current['last_expensive_decision_send']=send
        if args.action=='stop':current['research_status']='stopped';current['final_disposition']=plain(ref)
        ctx.store.update_state(db,ctx.run_id,current)
    return Result(detail=dict(accepted=True,plan_reference=plain(ref),batch=batch,action=args.action,remaining_budget=budget(ctx.store)))


def dispatch(ctx,args,operation):
    state=ctx.store.session(ctx.run_id)['state'];reserve=RESERVATIONS[operation]
    if 'freeze' not in state:raise ValueError('COMMIT_AND_BIND_BEFORE_DISPATCH')
    if state.get('pending'):raise ValueError('UNKNOWN_NUMERICAL_OUTCOME_INSPECT_PENDING_FILES_NO_REPEAT')
    if state.get('engineering_pause'):raise ValueError('ENGINEERING_PAUSE_REQUIRES_LOCAL_RECOVERY')
    if state['research_status']=='stopped':raise ValueError('MODEL_STOP_SEALED')
    if state['numerical_s']+reserve>float(CEILINGS['total_numerical_s']) or time.time()+reserve>=state['cutoff_unix']:raise ValueError('OPERATION_CANNOT_FIT_REMAINING_BUDGET')
    request=dict(activity=ACTIVITY,store_root=str(ctx.store.root),request_id=ctx.request.request_id,
        operation=operation,configuration=plain(ctx.input),arguments=plain(args),implementation=state['freeze'],
        local_ad=state.get('local_ad','reverse'))
    if operation in ('diagnose','speed'):
        raise ValueError('HISTORICAL_DIAGNOSIS_AND_SPEED_IMPORTED_NO_RERUN')
    if operation=='solve':
        if not state.get('speed_check_passed'):raise ValueError('CHANGED_DERIVATIVE_EXECUTION_CHECK_REQUIRED')
        if state['nlp_solves']>=CEILINGS['full_nlp_solves']:raise ValueError('NLP_SOLVE_CEILING')
        accepted=next((p for p in state['plans'] if p['reference']==plain(args.plan_reference)),None)
        if not accepted or accepted['action']!='solve' or accepted['batch']!=args.batch:raise ValueError('ACCEPTED_MODEL_PLAN_REQUIRED')
        original=ctx.artifact(args.plan_reference)
        choices=plain(Candidate.model_validate({k:v for k,v in plain(args).items() if k in Candidate.model_fields}))
        if args.candidate_index>=len(original['candidates']) or choices!=original['candidates'][args.candidate_index]:raise ValueError('SOLVE_MUST_MATCH_MODEL_PLAN')
        key=args.plan_reference.artifact_id+':'+str(args.candidate_index)
        if key in state['dispatched_candidates']:raise ValueError('PLAN_CANDIDATE_ALREADY_DISPATCHED')
        if args.source_candidate:
            artifact=ctx.artifact(args.source_candidate);source=validate_schedule(artifact.get('candidate',artifact));request['saved_tensions']=source['tensions_n']
    if operation=='replay':
        if state.get('replays',0)>=CEILINGS['new_independent_replays']:raise ValueError('THREE_REPLAY_CEILING')
        artifact=ctx.artifact(args.candidate);request['candidate']=validate_schedule(artifact.get('candidate',artifact))
    inp,out,progress=ctx.folder/'worker_input.json',ctx.folder/'worker_output.json',ctx.folder/'worker_progress.json'
    request['progress']=str(progress);atomic_json(inp,request)
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state'];current['pending']=dict(operation=operation,input=str(inp),output=str(out),progress=str(progress),
            request_id=ctx.request.request_id,reserved_s=reserve,started_unix=time.time())
        if operation=='replay':current['replays']=current.get('replays',0)+1
        if operation=='solve':
            current['nlp_solves']+=1;current['dispatched_candidates'].append(key)
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
    checkpoint=read(progress) if progress.exists() else None
    checkpoint_ref=None
    if operation=='solve':
        returned=bool(checkpoint and checkpoint.get('phase')=='solver_returned')
        entered=returned or b'Total number of variables' in stdout or b'iter    objective' in stdout
        if returned:checkpoint_ref=ctx.save_artifact(checkpoint,'feedback_numeric_checkpoint')
        result.update(solver_entered=entered,solver_returned=returned,
            checkpoint_reference=plain(checkpoint_ref) if checkpoint_ref else None,
            candidate_export_status='exported' if result.get('candidate') else 'unavailable')
        if returned and not result.get('candidate'):
            # Settle packaging locally before any subsequent scientific dispatch.
            failure=dict(result);recovery_input=ctx.folder/'recovery_input.json'
            recovery_request=dict(request,operation='recover');atomic_json(recovery_input,recovery_request)
            with ctx.store.transaction() as db:
                current=ctx.store.session(ctx.run_id,db)['state'];current['pending']['input']=str(recovery_input)
                ctx.store.update_state(db,ctx.run_id,current)
            remaining=reserve-(time.perf_counter()-started)
            if remaining>0:
                try:
                    process=subprocess.run([state['python'],'-m','tools.casadi_feedback_worker',str(recovery_input),str(out)],cwd=ROOT,env=env,
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=remaining)
                    stdout+=process.stdout;result=read(out)
                except subprocess.TimeoutExpired as exc:
                    stdout+=exc.stdout or b''
                    result=dict(status='engineering_error',termination_reason='Checkpoint recovery exceeded original worker allowance')
            result.update(original_packaging_failure=failure,solver_entered=entered,solver_returned=True,
                checkpoint_reference=plain(checkpoint_ref),candidate_export_status='recovered' if result.get('candidate') else 'unavailable')
        if returned and 'solver_termination' not in result:result['solver_termination']=checkpoint['diagnostics']['return_status']
    elapsed=time.perf_counter()-started
    log=ctx.save_artifact(dict(text=stdout.decode('utf8',errors='replace')),'feedback_worker_log')
    result.update(operation=operation,arguments=plain(args),implementation=state['freeze'],problem_identity=state['spec_identity'],
        process_elapsed_s=elapsed,log_reference=plain(log),solve_ceiling_overrun_s=max(0.,result.get('costs_s',{}).get('solve',0.)-CEILINGS['solve_limit_s']))
    ref=ctx.save_artifact(result,'feedback_'+operation)
    candidate_ref=ctx.save_artifact(result['candidate'],'feedback_candidate') if result.get('candidate') else None
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state'];current['numerical_s']+=elapsed;current.pop('pending',None)
        if operation in ('diagnose','speed'):current['investigation_s']+=elapsed
        current['results'].append(dict(operation=operation,status=result['status'],reference=plain(ref),candidate=plain(candidate_ref) if candidate_ref else None,
            source_candidate=plain(args.candidate) if operation=='replay' else None))
        if candidate_ref:
            configuration_ref=ctx.store.put(db,request['configuration'])
            current.setdefault('candidate_sources',{})[candidate_ref.artifact_id]=dict(configuration=plain(configuration_ref),checkpoint=plain(checkpoint_ref) if checkpoint_ref else None,solve=plain(ref),source_activity=ACTIVITY)
        if result['status'] in ('engineering_error','numerical_error'):
            current['engineering_pause']=dict(reference=plain(ref),reason=result['termination_reason'])
        if operation=='diagnose':
            comparisons=result.get('comparisons',{});a=comparisons.get('tight_original_vs_tight_refined',{});b=comparisons.get('tight_refined_vs_saved_bdf',{})
            current['refined_grid_supported']=bool(a.get('complete_horizon') and b.get('complete_horizon') and
                (a.get('max_tip_m',0.)>.001 or a.get('max_speed_m_s',0.)>.002))
        if operation=='speed':current['local_ad']=result.get('selected_local_ad','reverse');current['speed_check_passed']=result['status']=='passed'
        ctx.store.update_state(db,ctx.run_id,current)
    fields=('status','termination_reason','iterations','hard_max_normalized_violation','largest_hard_residuals','largest_relaxed_task_residuals',
        'relaxed_nlp_feasible','original_task_feasible','original_task_gaps','slack_values','trajectory_metrics','objective_components',
        'slack_definition','acceptance','physical_validation','replay','physical_eligible','comparisons','saved_nlp_metrics','precision_bdf',
        'full_warmed_speed_ratio','setup_repayment_jacobian_calls','selected_local_ad','adopted','equivalence_passed','costs_s','process_elapsed_s','solve_ceiling_overrun_s',
        'solver_entered','solver_returned','solver_termination','checkpoint_reference','candidate_export_status','original_packaging_failure','recovered_without_nlp')
    compact={k:result[k] for k in fields if k in result}
    if result.get('candidate'):compact['design_values']=dict(d=result['candidate']['d'],lengths_m=result['candidate']['lengths_m'],selection=result['candidate']['selection'])
    return Result(detail=dict(**compact,operation=operation,evidence_reference=plain(ref),candidate_reference=plain(candidate_ref) if candidate_ref else None,
        candidate_identity=digest(result['candidate']) if result.get('candidate') else None,implementation_identity=state['freeze'],
        remaining_budget=budget(ctx.store),consumption=dict(numerical_s=ctx.store.session(ctx.run_id)['state']['numerical_s'],
            process_elapsed_s=elapsed,store=ctx.store.remaining()['used'],store_active_reservation_s=reserve)))


def diagnose(ctx,args):return dispatch(ctx,args,'diagnose')
def speed(ctx,args):return dispatch(ctx,args,'speed')
def solve(ctx,args):return dispatch(ctx,args,'solve')
def replay(ctx,args):return dispatch(ctx,args,'replay')
