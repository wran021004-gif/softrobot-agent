"""Bounded saved-plan consistency checks using the existing NMPC workspace."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tarfile
import time
import numpy as np
from schemas.platform import SessionInput, EvidenceRef
from schemas.casadi_feedback import FeasibilityPlan, Result
from tools.platform_store import plain
from tools.state_io import atomic_json, read, digest
from tools.spec_tools import ROOT
from tools.nmpc_initialization import EXECUTION, CANDIDATE

SOURCE=ROOT/'evidence/nmpc_initialization_20261010'
OUT=ROOT/'evidence/nmpc_feasibility_20261011'
INSTRUCTIONS='''You are the sole DeepSeek research principal for a fresh bounded feasibility-recovery investigation. The user supplied the regeneration method; Codex supplied engineering and factual residual arithmetic, not your hypotheses or conclusions. Supplied case/procedure facts are prior context, not autonomous memory retrieval. Choose research_plan actions inspect_residuals, reintegrate_saved_tensions, warm_start_comparison, control_revision, diagnose, stop. Every scientific action names hypothesis, supporting_evidence, saved_plan.source_problem (exact immutable paired snapshot), plan_label, fixed_conditions, expected_observation, weakening_observation and revision_or_stop_rule. Regeneration preserves all tensions/timing and integrates from the measured state with the existing implicit root finder; no IPOPT. Do not repair top-level selected .2N initialization. Deduplicate returned/checkpoint tension schedules. At most two distinct saved regenerations,180s each, update20/.20s only. Prefer checking baseline15s returned schedule before a15s closed-loop revision;30s repair alone is extrapolation. Read each actual result before choosing any next scientific action. After the first regeneration, choose at most one further scientific step: another distinct regeneration OR warm_start_comparison OR control_revision OR stop. Warm comparison uses the saved regenerated result reference and corresponding cold recipe, recovery disabled, same state/timing/weights/constraints/stops; at most2 new NLP attempts,300s combined. Control revision keeps exact immutable candidate and imported preceding execution, changes only recover_returned_tensions false->true;15s return budget,30s CPU,120 iterations,weights .05/.10,substeps1, record_update_ids [20]. Full materialized configuration and actual simulator states used; no diagnostic states injected. At most1 new MuJoCo launch including failure,1800s plus30s evaluation/60s profile. Total scientific preparation/checks/recovery3600s,16 actual provider sends including auxiliary/retries last4 protected,64 public calls,6h total final30min delivery. Zero full-horizon codesign, BDF, other models/hardware. Ceilings are not quotas. Preserve fixed physics/task/acceptance in specification. Separate original NLP progress, restored discretized numerical feasibility, objective/physical improvement after regeneration, and actual sampled closed-loop improvement. .30s horizon endpoint is not .35s task acceptance. A small generalized-force residual is not Cartesian force/tendon error or small trajectory error. Same-time projection difference4.3975mm/.021396m/s remains a limitation. Initial .2N is not equilibrium. Historical simulation synchronous; latency does not skip virtual control updates. Both old budget arms ran once; outputs recovered after reporting timeout without another solve, actual stops budget_best_feasible/User_Requested_Stop, CPU30 differs from wall30. Numerical results sealed before packaging; reporting failure never authorizes a repeat. STOP cites every new result; accepted STOP seals further sends. Preserve original dispositions separately from factual corrections. No LLM superiority, unique cause, continuous-time, real-time or hardware claim. A useful procedure is how to inspect/test recovery, not always enable it.'''


def import_archive(store,db,directory):
    manifest=read(directory/'archive_manifest.json');path=directory/'immutable_artifacts.tar.gz'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['archive_sha256']:raise ValueError('ARCHIVE_HASH_MISMATCH')
    with tarfile.open(path,'r:gz') as archive:
        for member in manifest['members']:
            body=archive.extractfile(member['name']).read()
            if hashlib.sha256(body).hexdigest()!=member['sha256']:raise ValueError('SOURCE_MEMBER_HASH_MISMATCH')
            ref=store.put(db,body,member['media'])
            if ref.artifact_id!=member['sha256']:raise ValueError('SOURCE_IMPORT_HASH_MISMATCH')


def make_workspace(configuration,saved):
    from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
    inp=SessionInput.model_validate(configuration);s=saved['snapshot'];p=deepcopy(s['numerical_parameters'])
    ws=TrajectoryWorkspace(inp.task,inp.robot,p,s['measured_initial_state'],s['previous_applied_input_n'],
        settling=inp.policy.controller.parameters.data['settling'])
    ws._set_prediction_time(s['time_s'])
    for j,value in enumerate(s['measured_initial_state']):
        ws.problem.variables[f'x/0/{j}']['bounds']=[value/ws.state_scales[j]]*2
        ws.problem.initial_guess[f'x/0/{j}']=value/ws.state_scales[j]
    for t,value in zip(ws.tendons,s['previous_applied_input_n']):
        ws.problem.variables['previous_u/'+t]['bounds']=[value]*2
        ws.problem.initial_guess['previous_u/'+t]=value
    ws._prepare_tail()
    order=ws.problem.objective_function.data['variable_order']
    if order!=saved['diagnostics']['variable_order']:raise ValueError('SAVED_VARIABLE_ORDER_MISMATCH')
    if [c.name for c in ws.problem.constraints]!=saved['diagnostics']['constraint_order']:raise ValueError('SAVED_CONSTRAINT_ORDER_MISMATCH')
    if ws._set_prediction_time(s['time_s'])!=s['prediction_timing']:raise ValueError('SAVED_ABSOLUTE_TIMING_MISMATCH')
    return ws


def saved_vector(saved,label):
    points=saved['diagnostics']['retained_diagnostic_points']
    point=next(p for p in points if p['label']==label)
    return dict(zip(saved['diagnostics']['variable_order'],point['vector']))


def describe_plan(ws,values,time_s):
    from extensions.tendon_family.control_evidence import decode_plan,objective_components,plan_metrics
    order=ws.problem.objective_function.data['variable_order']
    x,u,previous=decode_plan(ws,[values[k] for k in order],order)
    check=ws.solver.evaluate_candidate(ws.problem,values)
    return dict(verification={k:v for k,v in check.items() if k!='constraint_values'},
        objective_components=objective_components(ws,x,u,previous),metrics=plan_metrics(ws,x,u,time_s),
        states=x.tolist(),tensions=u.tolist(),optimum=values)


def residual_row(name,value,coordinates,time_s,h):
    _,interval,row=name.split('_');interval=int(interval);row=int(row);n=len(coordinates)
    kinematic=row<n;denominator=10. if kinematic else .001
    return dict(constraint_name=name,interval_zero_based=interval,start_s=time_s+interval*h,end_s=time_s+(interval+1)*h,
        row_zero_based=row,coordinate=coordinates[row%n],kind='kinematic_consistency' if kinematic else 'generalized_force_balance',
        signed_scaled_residual=float(value),absolute_scaled_residual=abs(float(value)),normalization_denominator=denominator,
        physical_unit='rad/m' if kinematic else 'N*m^2/rad',signed_physical_residual=float(value)*denominator,
        absolute_physical_residual=abs(float(value))*denominator)


def force_decomposition(ws,values,row):
    from extensions.tendon_family.gvs import GVSModel
    from extensions.tendon_family.contracts import GVSModelParameters
    from extensions.tendon_family.gvs_casadi import functions_for,expression_from_system
    from schemas.platform_math import SystemContext
    p=GVSModelParameters(basis=ws.parameters.basis)
    f=functions_for(expression_from_system(GVSModel(p).build_system(ws.robot,p,None,
        SystemContext(x0=ws.nominal_x,u0=ws.nominal_u,scene=ws.scene))))
    k=row['interval_zero_based'];j=row['row_zero_based']-ws.n;h=ws.period/ws.parameters.substeps
    x=np.array([values[f'x/{k+1}/{a}'] for a in range(2*ws.n)])*ws.state_scales
    old=np.array([values[f'x/{k}/{a}'] for a in range(2*ws.n)])*ws.state_scales
    u=np.array([values[f'u/{k//ws.parameters.substeps}/{t}'] for t in ws.tendons]);a=(x[ws.n:]-old[ws.n:])/h
    zero=np.zeros(ws.n);rest=np.r_[x[:ws.n],zero]
    def r(state,acc):return np.asarray(f.implicit_residual(state,u,acc)).ravel()
    terms=f.evaluate(x,u);base=r(rest,zero)
    inertial=r(rest,a)-base;damping=terms['damping_force'].ravel()
    velocity=r(x,zero)-base-damping
    parts=dict(inertial=float(inertial[j]),velocity_dependent=float(velocity[j]),
        elastic=float(terms['elastic_force'].ravel()[j]),damping=float(damping[j]),
        gravity=-float(terms['gravity_force'].ravel()[j]),tendon=-float(terms['tendon_generalized_force'].ravel()[j]))
    exact=float(r(x,a)[j]);total=sum(parts.values());difference=total-exact
    if abs(difference)>1e-11:raise ValueError('FORCE_DECOMPOSITION_MUST_REPRODUCE_IMPLICIT_EXPRESSION')
    return dict(signed_terms=parts,sum=total,exact_implicit_residual=exact,difference=difference,physical_unit='N*m^2/rad',
        method='Inertial and velocity terms isolated from exact implicit residual at zero rate/acceleration; all contributions evaluated at following state.')


def audit_saved(configuration,saved,reference):
    from extensions.tendon_family.gvs import coordinate_order
    start=time.perf_counter();ws=make_workspace(configuration,saved);s=saved['snapshot']
    coordinates=coordinate_order(ws.robot.structure.data,ws.parameters.basis);rows=[];seen={}
    for point in saved['diagnostics']['retained_diagnostic_points']:
        label=point['label'];key=digest(point['vector'])
        if key in seen:
            rows.append(dict(label=label,identical_vector_to=seen[key]));continue
        seen[key]=label;values=saved_vector(saved,label);check=ws.solver.evaluate_candidate(ws.problem,values)
        violations=[residual_row(c.name,v,coordinates,s['time_s'],ws.period/ws.parameters.substeps)
            for c,v in zip(ws.problem.constraints,check['constraint_values'])]
        ranked=sorted(violations,key=lambda r:r['absolute_scaled_residual'],reverse=True)[:8]
        worst_force=next(r for r in sorted(violations,key=lambda r:r['absolute_scaled_residual'],reverse=True) if r['kind']=='generalized_force_balance')
        worst_force=dict(worst_force,decomposition=force_decomposition(ws,values,worst_force))
        rows.append(dict(label=label,source_reference=reference,pointer='/snapshot/plans/'+label,
            objective=check['objective'],feasible=check['feasible'],max_scaled_residual=check['scaled_violation'],
            count_above_1e_5=sum(r['absolute_scaled_residual']>1e-5 for r in violations),
            groups={kind:dict(max_scaled_residual=max(r['absolute_scaled_residual'] for r in violations if r['kind']==kind),
                count_above_1e_5=sum(r['absolute_scaled_residual']>1e-5 for r in violations if r['kind']==kind))
                for kind in ('kinematic_consistency','generalized_force_balance')},
            named_residuals=check['named_residuals'],ranked_violations=ranked,worst_force=worst_force))
    return dict(source_problem=reference,update_id=s['update_id'],time_s=s['time_s'],coordinate_order=coordinates,
        variable_order_verified=True,constraint_order_verified=True,absolute_timing_verified=True,
        normalization_source='gvs_trajectory.implicit_step_residual: kinematic /10, implicit force /.001',
        threshold=1e-5,new_nlp_attempts=0,plans=rows,cost_s=time.perf_counter()-start)


def prepare_evidence(h):
    state=h.store.session(h.run_id)['state']
    if state.get('feasibility_prepared'):return
    started=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True)
    with h.store.transaction() as db:
        import_archive(h.store,db,SOURCE)
        old=read(SOURCE/'state.json');state=h.store.session(h.run_id,db)['state']
        state.update(feasibility_recovery=True,source_binding=old['source_binding'],source_baseline_reference=old['source_baseline_reference'],
            candidate_sources=deepcopy(old['candidate_sources']),selected_states=[20],regeneration_schedules=[],new_local_nlp_attempts=0,
            local_nlp_cost_s=0.,post_regeneration_steps=0,paired_sources={},results=state['results'])
        baseline=next(r for r in old['results'] if r['operation']=='closed_loop')
        state['results'].append(dict(baseline,imported=True,source_activity=old['pilot']['activity_id']))
        targeted=['docs/nmpc_initialization_completion.md','docs/nmpc_initialization_runbook.md','docs/nmpc_initialization_procedure.md',
            'memory/nmpc_initialization_case_draft.json','examples/nmpc_initialization/specification.json']
        prior={name:plain(h.store.put(db,(ROOT/name).read_bytes(),'text/plain')) for name in targeted}
        for name in ['scientific_summary','post_stop_factual_correction','source_binding','pair_baseline_numerical','pair_baseline_snapshot','pair_variant_numerical','pair_variant_snapshot']:
            value=read(SOURCE/(name+'.json'));ref=plain(h.store.put(db,value));prior[name]=ref
            if name.endswith('_snapshot'):state['paired_sources'][name]=ref
        state['prior_context_references']=prior
        state['supplied_prior_context']=dict(source='Explicit startup reads supplied by Codex; not autonomous retrieval',
            confirmed_facts=['One paired experiment/two solves; recovered reporting with no numerical repeat.',
                'Both actual stops budget_best_feasible/User_Requested_Stop; CPU and wall limits differ.',
                'Improved recorded raw/retained candidates infeasible; selected objective1697.08574832549/.2N each.',
                'Projection difference4.3975mm and velocity vector .021396m/s remains unresolved.',
                'Historical terminal95.5mm, holding193.2mm/speed3.25m/s fail sampled acceptance.'],
            procedure_steps=['Freeze task and physics; import owned immutable vectors; distinguish raw/selected/returned.',
                'Inspect exact named/scaled rows and aligned timestamps; .30s endpoint outside .35s task acceptance.',
                'State hypothesis/weakening observation, execute once, preserve numerical result before reports.',
                'Separate model-consistency result from simulator acceptance; maintain reference-backed case/procedure drafts.'],
            admission='Known legacy EvidenceRef/ArtifactReference mismatch; no repeat admission check or fabricated approval.')
        h.store.update_state(db,h.run_id,state)
    binding=h.store.artifact(state['source_binding']);configuration=binding['source']['configuration']
    try:
        audits=[audit_saved(configuration,h.store.artifact(ref),ref) for ref in state['paired_sources'].values()]
        audit=dict(feasibility_operation='inspect_residuals',status='completed',source_binding=state['source_binding'],audits=audits,
            interpretation='Exact original discretized equations; generalized force defects do not bound trajectory error; unchanged threshold1e-5.',
            actual_executed_input_n=None,new_nlp_attempts=0,costs_s=dict(total=time.perf_counter()-started))
        with h.store.transaction() as db:
            current=h.store.session(h.run_id,db)['state'];ref=plain(h.store.put(db,audit))
            current['residual_audit_reference']=ref;current['results'].append(dict(operation='inspect_residuals',reference=ref))
            current['feasibility_prepared']=True;h.store.update_state(db,h.run_id,current)
        atomic_json(OUT/'residual_audit.json',audit)
        atomic_json(OUT/'source_binding.json',binding)
    finally:
        with h.store.transaction() as db:
            current=h.store.session(h.run_id,db)['state'];elapsed=time.perf_counter()-started
            current['numerical_s']+=elapsed;current.setdefault('preparation_costs_s',[]).append(elapsed);h.store.update_state(db,h.run_id,current)


def schedule_identity(saved,label):return digest(saved['snapshot']['plans'][label]['tensions'])


def validate_plan(store,state,args):
    FeasibilityPlan.model_validate(plain(args))
    if args.saved_plan:
        c=args.saved_plan
        if plain(c.source_problem) not in list(state['paired_sources'].values()):raise ValueError('EXACT_IMPORTED_PAIRED_SOURCE_REQUIRED')
        saved=store.artifact(c.source_problem);s=saved['snapshot']
        if s['update_id']!=20 or s['time_s']!=.20:raise ValueError('UPDATE20_ONLY')
        if s['plans'][c.plan_label]['verification']['feasible_at_1e_5']:raise ValueError('REJECTED_SAVED_PLAN_REQUIRED')
        if args.action=='reintegrate_saved_tensions':
            if c.max_wall_s>180:raise ValueError('REGENERATION_180S_CEILING')
            identity=schedule_identity(saved,c.plan_label)
            if identity in state['regeneration_schedules']:raise ValueError('IDENTICAL_TENSIONS_ALREADY_CHARGED')
            if len(state['regeneration_schedules'])>=2:raise ValueError('TWO_SCHEDULE_CEILING')
        if args.action=='warm_start_comparison':
            if c.regenerated_reference is None:raise ValueError('EXACT_REGENERATED_RESULT_REQUIRED')
            v=store.artifact(c.regenerated_reference)
            if v.get('source_problem')!=plain(c.source_problem) or v.get('plan_label')!=c.plan_label or not v.get('regenerated',{}).get('verification',{}).get('feasible'):
                raise ValueError('FEASIBLE_CORRESPONDING_REGENERATION_REQUIRED')
            if state['new_local_nlp_attempts']+2>2:raise ValueError('TWO_NEW_LOCAL_NLP_CEILING')
    if args.action in ('reintegrate_saved_tensions','warm_start_comparison','control_revision') and state['regeneration_schedules']:
        if state['post_regeneration_steps']>=1:raise ValueError('ONE_EVIDENCE_DRIVEN_NEXT_STEP_CEILING')
    if args.control:
        c=args.control
        if c.candidate.artifact_id!=CANDIDATE or plain(c.preceding_execution)!=state['source_baseline_reference']:raise ValueError('IMPORTED_FIXED_CANDIDATE_AND_BASELINE_REQUIRED')
        if (c.holding_tip_speed_weight,c.terminal_tip_speed_weight,c.feasible_return_budget_s,c.substeps,c.recover_returned_tensions,c.record_update_ids)!=(.05,.1,15.,1,True,[20]):
            raise ValueError('ONLY_RECOVERY_FALSE_TO_TRUE_WITH_FIXED_SETTINGS_PERMITTED')
        if not any(r['operation']=='reintegrate_saved_tensions' for r in state['results']):raise ValueError('REGENERATION_FEEDBACK_REQUIRED_BEFORE_REVISION')


def compact(value):
    result={k:v for k,v in value.items() if k not in ('regenerated','original_selected','original_rejected','root_steps','partial_states','rows')}
    for name in ('regenerated','original_selected','original_rejected'):
        if value.get(name):result[name]={k:v for k,v in value[name].items() if k not in ('states','tensions','optimum')}
    if value.get('rows'):result['rows']=[{k:v for k,v in row.items() if k not in ('numerical','snapshot')} for row in value['rows']]
    return result


def packet(h):
    from tools.casadi_feedback_service import SPEC,budget
    from tools.research_casadi_feedback import compact_result
    state=h.store.session(h.run_id)['state']
    summaries=[]
    for name,ref in state['paired_sources'].items():
        saved=h.store.artifact(ref)
        summaries.append(dict(label=name,source_problem=ref,budget_s=saved['parameters']['feasible_return']['budget_s'],
            plans=[dict(label=k,schedule_identity=schedule_identity(saved,k),**{a:v[a] for a in ('verification','metrics','objective_components')})
                for k,v in saved['snapshot']['plans'].items()]))
    return dict(frozen_specification=SPEC,source_binding=state['source_binding'],candidate=dict(artifact_id=CANDIDATE,media_type='application/json'),
        baseline_execution_reference=state['source_baseline_reference'],prior_context_references=state['prior_context_references'],
        supplied_prior_context=state['supplied_prior_context'],post_stop_factual_corrections=h.store.artifact(state['prior_context_references']['post_stop_factual_correction']),
        paired_saved_plans=summaries,results=[dict(operation=r['operation'],reference=r['reference'],**compact_result(h.store.artifact(r['reference'])))
            for r in state['results'] if not r.get('imported') or r['operation']=='closed_loop'],
        remaining_budget=dict(**budget(h.store),saved_regenerations=2-len(state['regeneration_schedules']),new_local_nlp_attempts=2-state['new_local_nlp_attempts'],
            post_regeneration_steps=1-state['post_regeneration_steps']),
        capabilities=dict(inspect_residuals='Reuse exact residual audit; no NLP',reintegrate_saved_tensions='180s unchanged schedule consistency check with existing implicit root finder',
            warm_start_comparison='300s combined cold versus explicit regenerated warm seed; post-solve recovery disabled',
            control_revision='Only recovery flag false->true; actual saved candidate configuration propagated into new simulation',
            stop='May stop without simulation; cite all new results, no provider sends afterward'))


def preflight(inp,args,reg):
    return dict(cost=dict(wall_s=args.choice.max_wall_s))


def numeric_operation(request,output):
    start=time.perf_counter();saved=request['saved'];choice=request['choice'];operation=request['operation']
    ws=make_workspace(request['configuration'],saved);prep=time.perf_counter()-start;s=saved['snapshot'];label=choice['plan_label']
    raw=saved_vector(saved,label);selected=saved_vector(saved,'selected')
    result=dict(feasibility_operation=operation,source_problem=choice['source_problem'],plan_label=label,
        source_pointer='/snapshot/plans/'+label,source_snapshot_id=s['snapshot_id'],status='completed',
        original_solver=dict(status=saved['result']['status'],raw_status=saved['diagnostics']['return_status'],iterations=saved['result']['iterations']),
        original_selected=describe_plan(ws,selected,s['time_s']),original_rejected=describe_plan(ws,raw,s['time_s']),
        actual_executed_input_n=None,scope='Consistency within original discretized model; no independent simulation/continuous-time validation.')
    if operation=='reintegrate_saved_tensions':
        regeneration=ws.regenerate_tensions(raw,s['measured_initial_state'],deadline=start+choice['max_wall_s'])
        result.update(root_steps=regeneration['steps'],partial_states=regeneration['partial_states'],error=regeneration['error'])
        integration=regeneration['integration_s'];verification_start=time.perf_counter()
        if regeneration['optimum'] is not None:
            repaired=regeneration['optimum'];new=describe_plan(ws,repaired,s['time_s']);result['regenerated']=new
            result['tensions_exactly_preserved']=new['tensions']==result['original_rejected']['tensions']
            if not result['tensions_exactly_preserved']:raise ValueError('TENSIONS_MUST_REMAIN_UNCHANGED')
            result['timing_exactly_preserved']=s['prediction_timing']==ws._set_prediction_time(s['time_s'])
            changes=np.array(new['states'])-result['original_rejected']['states']
            result['state_changes']=dict(q_linf_rad_m=float(np.max(abs(changes[:,:ws.n]))),qdot_linf_rad_m_s=float(np.max(abs(changes[:,ws.n:]))))
            check=new['verification'];end=new['metrics']['terminal'];old_end=result['original_selected']['metrics']['terminal']
            result['outcome']=dict(finite=bool(np.isfinite(np.array(new['states'])).all() and np.isfinite(check['objective'])),
                feasible=check['feasible'],lower_cost_than_selected=check['objective']<result['original_selected']['verification']['objective'],
                horizon_end_position_improved=end['position_error_m']<old_end['position_error_m'],horizon_end_speed_improved=end['tip_speed_m_s']<old_end['tip_speed_m_s'],
                objective_change_from_rejected=check['objective']-result['original_rejected']['verification']['objective'],closed_loop_validated=False)
        else:result.update(status='regeneration_failed',outcome=dict(finite=False,feasible=False,lower_cost_than_selected=False,closed_loop_validated=False))
        result['new_nlp_attempts']=0;result['root_solve_attempts']=len(regeneration['steps'])+int(regeneration['error'] is not None)
        result['costs_s']=dict(preparation=prep,integration=integration,verification=time.perf_counter()-verification_start,total=time.perf_counter()-start)
        # Seal complete numerical result before Host packaging or concise feedback.
        atomic_json(output,result)
    elif operation=='warm_start_comparison':
        new=request['regenerated']['regenerated'];rows=[]
        for arm in ('cold','warm'):
            if time.perf_counter()-start+60>choice['max_wall_s']:raise RuntimeError('COMPARISON_TOTAL_ALLOWANCE')
            ws=make_workspace(request['configuration'],saved);ws.parameters.recover_returned_tensions=False
            ws.solver.diagnostic_trace=True
            seed=None if arm=='cold' else dict(states=new['states'],tensions=new['tensions'])
            solved=ws.solve(s['measured_initial_state'],s['previous_applied_input_n'],warm=seed,elapsed_s=s['time_s'])
            atomic_json(Path(output).with_name('warm_'+arm+'_numerical.json'),solved)
            description=describe_plan(ws,solved['result']['optimum'],s['time_s'])
            rows.append(dict(arm=arm,verification=description['verification'],metrics=description['metrics'],objective_components=description['objective_components'],
                iterations=solved['result']['iterations'],stop_reason=solved['diagnostics']['policy_stop_reason'],raw_status=solved['diagnostics']['return_status'],
                preparation_s=solved['warm_start']['preparation_s'],solve_s=solved['total_s'],numerical=solved))
            atomic_json(output,dict(result,status='partial',rows=rows,new_nlp_attempts=len(rows)))
        result.update(rows=rows,status='completed',new_nlp_attempts=2,costs_s=dict(total=time.perf_counter()-start))
        atomic_json(output,result)


def check_tool(ctx,args):
    from tools.casadi_feedback_service import CEILINGS
    started=time.perf_counter();state=ctx.store.session(ctx.run_id)['state'];choice=plain(args.choice)
    accepted=ctx.artifact(args.plan_reference)
    if accepted['action']!=args.operation or accepted['saved_plan']!=choice:raise ValueError('OPERATION_MUST_MATCH_ACCEPTED_MODEL_PLAN')
    if args.operation=='inspect_residuals':return Result(detail=ctx.artifact(state['residual_audit_reference']))
    saved=ctx.artifact(args.choice.source_problem)
    request=dict(operation=args.operation,choice=choice,saved=saved,configuration=ctx.artifact(state['source_binding'])['source']['configuration'])
    if args.operation=='warm_start_comparison':request['regenerated']=ctx.artifact(args.choice.regenerated_reference)
    inp=ctx.folder/'saved_input.json';out=ctx.folder/'saved_numerical.json';atomic_json(inp,request)
    with ctx.store.transaction() as db:
        current=ctx.store.session(ctx.run_id,db)['state']
        if current['regeneration_schedules']:current['post_regeneration_steps']+=1
        if args.operation=='reintegrate_saved_tensions':current['regeneration_schedules'].append(schedule_identity(saved,choice['plan_label']))
        if args.operation=='warm_start_comparison':current['new_local_nlp_attempts']+=2
        current['pending']=dict(operation=args.operation,input=str(inp),output=str(out),started_unix=time.time())
        ctx.store.update_state(db,ctx.run_id,current)
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    try:
        try:
            process=subprocess.run([state['python'],'-m','tools.nmpc_feasibility',str(inp),str(out)],cwd=ROOT,env=env,
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=choice['max_wall_s']-2)
            log=process.stdout
        except subprocess.TimeoutExpired as exc:log=exc.stdout or b''
        # No automatic numerical retry after missing/partial/reporting output.
        value=read(out) if out.exists() else dict(feasibility_operation=args.operation,status='numerical_error',
            source_problem=choice['source_problem'],plan_label=choice['plan_label'],error='Worker returned no sealed result',new_nlp_attempts=0)
        numerical=ctx.save_artifact(value,'saved_numerical_result')
        value.update(numerical_reference=plain(numerical),worker_log_reference=plain(ctx.save_artifact(dict(text=log.decode('utf8',errors='replace')),'saved_worker_log')),
            actual_cost_s=time.perf_counter()-started,implementation=state['freeze'])
        ref=ctx.save_artifact(value,'saved_plan_feedback')
        with ctx.store.transaction() as db:
            current=ctx.store.session(ctx.run_id,db)['state'];current['results'].append(dict(operation=args.operation,reference=plain(ref)))
            current.pop('pending',None);ctx.store.update_state(db,ctx.run_id,current)
        atomic_json(OUT/(args.operation+'_'+args.plan_reference.artifact_id[:12]+'.json'),value)
        return Result(detail=dict(**compact(value),evidence_reference=plain(ref)))
    finally:
        with ctx.store.transaction() as db:
            current=ctx.store.session(ctx.run_id,db)['state'];elapsed=time.perf_counter()-started;current['numerical_s']+=elapsed
            if args.operation=='warm_start_comparison':current['local_nlp_cost_s']+=elapsed
            ctx.store.update_state(db,ctx.run_id,current)


def run_operation(h,plan,reference,key):
    from tools.research_execution import invoke
    choice=plain(plan.saved_plan)
    receipt=invoke(h,'math.nmpc_feasibility_check',dict(operation=plan.action,choice=choice,plan_reference=reference),request_id=key)
    feedback=h.store.artifact(receipt['output']) if receipt.get('output') else None
    if receipt['execution_status']!='completed':
        with h.store.transaction() as db:
            state=h.store.session(h.run_id,db)['state'];state['engineering_pause']=dict(receipt=receipt,reason='Inspect sealed output; never repeat numerical work.')
            h.store.update_state(db,h.run_id,state)
    return dict(receipt=receipt,feedback=feedback)


if __name__=='__main__':
    import sys
    numeric_operation(read(sys.argv[1]),Path(sys.argv[2]))
