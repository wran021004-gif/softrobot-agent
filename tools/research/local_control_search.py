"""Finite deterministic search; caller owns Store, budgets, execution and recovery."""
from copy import deepcopy
import numpy as np
from tools.research.contracts import LocalControlSearchSettings
from tools.research.control_correction import (corrected_tensions, correction_basis,
    constraint_vectors, constrained_response_step)
from tools.research.candidate_portfolio import ranking_key
from tools.state_io import digest


class SearchStopped(Exception):
    """Callback may signal the existing Store's exhausted physical allowance."""


def trust_radius(radius,predicted,actual,maximum):
    if predicted is None or actual is None or predicted<=0 or actual<=0 or actual/predicted<.25:return radius*.5
    return min(maximum,radius*1.5) if actual/predicted>.75 else radius


def search(starts,evaluate,settings,*,evaluation_kind='physical',stop_when=None,rank_key=ranking_key):
    """evaluate(start, source, metadata) returns task_gap, outputs, refs and costs.

    All probes participate in validity-first ranking. A failed model direction
    never vetoes a legal physical evaluation. Restart deterministically from
    starts; the callback recovers completed Store receipts, not optimizer state.
    """
    cfg=LocalControlSearchSettings.model_validate(settings)
    if not starts:raise ValueError('BOUND_STARTS_REQUIRED')
    channels=len(starts[0]['schedule']['trajectory']['tendon_order']);n=channels*len(cfg.knots_s)
    selected=list(range(n)) if cfg.active_coefficients is None else cfg.active_coefficients
    if any(i>=n for i in selected):raise ValueError('ACTIVE_COEFFICIENT_OUTSIDE_BOUND_DIMENSIONS')
    if len({s['id'] for s in starts})!=len(starts):raise ValueError('UNIQUE_SEARCH_START_IDS_REQUIRED')
    if len({digest({k:s['schedule']['trajectory'][k] for k in ('times_s','tendon_order')}) for s in starts})!=1:
        raise ValueError('COMPATIBLE_TENDON_ORDER_AND_GRID_REQUIRED')
    if len({digest([s['schedule']['trajectory']['task_identity'],s['task_options']]) for s in starts})!=1:
        raise ValueError('COMPARABLE_TASKS_REQUIRED')
    for s in starts:
        tr=s['schedule']['trajectory']
        if cfg.version=='local_control_search_v1' and (len(tr['tendon_order'])!=4 or len(tr['tensions_n'])!=35):
            raise ValueError('BOUND_35_BY_4_START_REQUIRED')
        times=np.asarray(tr['times_s']);u=np.asarray(tr['tensions_n'])
        if (channels<1 or len(tr['tendon_order'])!=channels or u.shape!=(len(times)-1,channels)
                or len(s['limits'])!=channels or len(times)<2 or not np.isfinite(times).all()
                or times[0]!=0 or np.any(np.diff(times)<=0)
                or not all(tr.get(k) for k in ('model_identity','design_identity','task_identity'))
                or cfg.knots_s[-1]>times[-1] or (cfg.correction_window_s and cfg.correction_window_s[1]>times[-1])):
            raise ValueError('BOUND_ALIGNED_CONTROL_GRID_REQUIRED')
    rows=[];best=None;centers={};radii={s['id']:cfg.initial_radius_n for s in starts};stop='iteration_limit'
    seen=set();information=set();ineffective=[];responses=[];iterations_started=0

    def vectors(row,start):return constraint_vectors(row['outputs'],**start['task_options'])
    def applied(start,x):
        tr=start['schedule']['trajectory']
        return corrected_tensions(tr['tensions_n'],tr['times_s'][:-1],cfg.knots_s,x,start['limits'],cfg.correction_window_s)

    def attempt(start,x,label,base=None,predicted=None,radius=None,solver=None):
        nonlocal best
        if len(rows)>=cfg.evaluation_requests:raise SearchStopped('evaluation_request_budget')
        if not np.isfinite(x).all() or np.any(abs(x)>cfg.coefficient_limit_n+1e-12):raise ValueError('ILLEGAL_COEFFICIENTS')
        source=deepcopy(start['schedule']);tr=source['trajectory']
        tr['tensions_n']=applied(start,x).tolist()
        identity=digest([tr[k] for k in ('task_identity','model_identity','design_identity','tendon_order','times_s','tensions_n')])
        meta=dict(algorithm=cfg.method,start=start['id'],coefficients_n=x.tolist(),label=label,
            active_coefficients=selected,search_dimension=len(selected),
            safety_margin_fraction=cfg.safety_margin_fraction,
            sequence_hash=digest(tr['tensions_n']),duplicate_applied_sequence=identity in seen,
            prediction_base=base['reference'] if base else None,
            predicted_improvement=predicted,trust_radius_n=radius,prospective_guarantee=False,
            applicability='Local sampled response at the stated candidate only; no regional error bound',
            extrapolation=bool(base and radius is not None and np.max(abs(x-np.asarray(base['coefficients_n'])))>radius+1e-12))
        source['provenance']=dict(source['provenance'],search=meta)
        row=dict(evaluate(start,source,meta),**meta)
        if solver is not None:row['local_solver']={k:v for k,v in solver.items() if k!='delta'}
        seen.add(identity)
        valid=row['task_gap']['valid_complete'] and row['task_gap']['normalized_gap'] is not None
        if not valid:row['task_gap']={**row['task_gap'],'normalized_gap':None}
        actual=(base['task_gap']['normalized_gap']-row['task_gap']['normalized_gap']) if base and valid else None
        row.update(actual_improvement=actual,direction_agrees=(predicted*actual>0) if predicted and actual else None)
        if valid and (best is None or rank_key(row)<rank_key(best)):best=row
        row['best_valid_reference']=best['reference'] if best else None
        rows.append(row)
        if valid and stop_when is not None and stop_when(row):raise SearchStopped('local_target_reached')
        if valid and row['task_gap']['accepted']:raise SearchStopped('first_original_task_pass')
        return row

    try:
        for start in starts:
            row=attempt(start,np.zeros(n),'baseline')
            if row['task_gap']['valid_complete']:centers[start['id']]=row
        if not centers:raise SearchStopped('no_valid_start')
        active=sorted((s for s in starts if s['id'] in centers),key=lambda s:rank_key(centers[s['id']]))
        for iteration in range(cfg.iterations):
            iterations_started+=1
            start=active[iteration%len(active)];center=centers[start['id']];x=np.asarray(center['coefficients_n'])
            radius=radii[start['id']]
            if radius<cfg.minimum_radius_n:
                if all(r<cfg.minimum_radius_n for r in radii.values()):raise SearchStopped('stagnation')
                continue
            if cfg.method=='pattern':
                improved=False
                # Late knots first; a complete sweep still covers earlier control.
                for j in reversed(selected):
                    for direction in (1,-1):
                        trial=x.copy();trial[j]=np.clip(x[j]+direction*radius,-cfg.coefficient_limit_n,cfg.coefficient_limit_n)
                        if np.array_equal(trial,x):continue
                        if np.max(abs(applied(start,trial)-applied(start,x)))<=1e-12:
                            ineffective.append(dict(start=start['id'],coefficient=j,label='coordinate',reason='no_applied_input_change'));continue
                        row=attempt(start,trial,'coordinate',base=center,radius=radius)
                        if rank_key(row)<rank_key(center):centers[start['id']]=row;improved=True;break
                    if improved:break
                if not improved:radii[start['id']]*=.5
            else:
                y=vectors(center,start);columns=[];directions=[];effective=[];valid=True
                base_u=applied(start,x)
                tr=start['schedule']['trajectory'];basis=correction_basis(tr['times_s'][:-1],cfg.knots_s,channels,cfg.correction_window_s)
                for j in selected:
                    h0=min(cfg.difference_step_n,radius);trial=None
                    for step in dict.fromkeys((h0,-h0,radius,-radius)):
                        probe=x.copy();probe[j]=np.clip(x[j]+step,-cfg.coefficient_limit_n,cfg.coefficient_limit_n)
                        delta_u=applied(start,probe)-base_u
                        if np.max(abs(delta_u))>1e-12:
                            trial=probe;h=trial[j]-x[j];break
                        ineffective.append(dict(start=start['id'],coefficient=j,step_n=step,reason='no_applied_input_change'))
                    if trial is None:continue
                    row=attempt(start,trial,'finite_difference',base=center,radius=radius)
                    if not row['task_gap']['valid_complete']:valid=False;break
                    projected=not np.allclose(delta_u.reshape(-1),basis[:,j]*h,rtol=0,atol=1e-12)
                    token=(start['id'],center['sequence_hash'],row['sequence_hash'])
                    row.update(projected_response=projected,effective_input_change_inf_n=float(np.max(abs(delta_u))),
                        provides_new_local_information=token not in information,
                        derivative_scope='one-sided projected control response' if projected else 'one-sided unclipped control response')
                    information.add(token);directions.append(delta_u.reshape(-1)/h);effective.append(j)
                    columns.append((vectors(row,start)-y)/h)
                if not valid:radii[start['id']]*=.5;continue
                jac=np.stack(columns,axis=-1) if columns else None
                rank=int(np.linalg.matrix_rank(jac.reshape(-1,len(columns)))) if columns else 0
                singular=np.linalg.svd(jac.reshape(-1,len(columns)),compute_uv=False) if columns else np.array([])
                responses.append(dict(start=start['id'],iteration=iteration,effective_coefficients=effective,
                    response_rank=rank,input_direction_rank=int(np.linalg.matrix_rank(np.stack(directions,axis=-1))) if directions else 0,
                    singular_values=singular.tolist(),resolved_subspace_condition=float(singular[0]/singular[rank-1]) if rank else None,
                    diagnostic='no_effective_response' if not rank else 'rank_deficient_response' if rank<len(effective) else 'resolved_local_response'))
                if not rank:
                    active.remove(start)
                    if not active:raise SearchStopped('degenerate_local_response')
                    continue
                solved=constrained_response_step(y,jac,x[effective],tr['tensions_n'],basis[:,effective],
                    start['limits'],radius,cfg.coefficient_limit_n,safety_margin_fraction=cfg.safety_margin_fraction)
                if not solved['success']:raise SearchStopped('numerical_failure: '+solved['numerical_status'])
                predicted=center['task_gap']['normalized_gap']-solved['predicted_gap']
                proposal=x.copy();proposal[effective]+=solved['delta']
                row=attempt(start,proposal,'local_response_proposal',base=center,predicted=predicted,radius=radius,solver=solved)
                radii[start['id']]=trust_radius(radius,predicted,row['actual_improvement'],cfg.coefficient_limit_n)
                row['next_trust_radius_n']=radii[start['id']]
                eligible=[r for r in rows if r['start']==start['id'] and r['task_gap']['valid_complete']]
                centers[start['id']]=min(eligible,key=rank_key)
    except SearchStopped as exc:stop=str(exc)
    return dict(version=cfg.version,algorithm=cfg.method,stop_reason=stop,
        iterations_started=iterations_started,
        cost_feedback=dict(request_budget=cfg.evaluation_requests,evaluation_callbacks=len(rows),
            evaluation_kind=evaluation_kind,
            new_physical_evaluations=sum(not r.get('cache_hit',False) for r in rows) if evaluation_kind=='physical' else 0,
            cache_reuses=sum(r.get('cache_hit',False) for r in rows),unique_input_sequences=len(seen),
            duplicate_applied_sequences=sum(r['duplicate_applied_sequence'] for r in rows),
            ineffective_probe_attempts=len(ineffective),unique_response_probes=len(information),
            charged_numerical_s=sum(r.get('cost_s',0.) for r in rows)),
        start_feedback=[dict(start=s['id'],initial_gap=next((r['task_gap'] for r in rows if r['start']==s['id']),None),
            best=min((r for r in rows if r['start']==s['id'] and r['task_gap']['valid_complete']),key=rank_key,default=None)) for s in starts],
        local_responses=responses,ineffective_probes=ineffective,
        active_coefficients=selected,search_dimension=len(selected),start_count=len(starts),
        finite_difference_evaluations=sum(r['label']=='finite_difference' for r in rows),
        candidates=rows,best=best,trust_radii_n=radii,prospective_guarantee=False,
        interpretation='Finite control search outcome; structural infeasibility remains unknown.')


def dispatch(host,plan,key,*,origin='model'):
    """One public batch; every new rollout uses the original public replay path."""
    from tools.platform_store import plain
    from tools.research import core
    from tools.research.state import state, save, update, guard
    from tools.research.design import verify_candidate
    from tools.research.physical_replay import evaluate_schedule, binding, initialize_schedule, schedule_identity
    from tools.research.control_correction import task_outputs
    from tools.research.feedback import task_gap
    from tools.research_tasks import task_adapter
    guard(host,True);q=plan.control_search
    if 'control_search' not in state(host)['spec']['capabilities']:raise ValueError('CONTROL_SEARCH_CAPABILITY_REQUIRED')
    from tools.research.evidence_policy import admit_decision
    admit_decision(host,plan)
    if q.settings.evaluation_requests>state(host)['spec']['budgets']['physical_launches']+1:
        raise ValueError('BATCH_REQUEST_EXCEEDS_FROZEN_SHARED_CAPACITY')
    def make_start(item,index):
        cfg=verify_candidate(host,item.candidate)['configuration'];adapter=task_adapter(cfg)
        if cfg['task']['family']!='task.reach':raise ValueError('UNSUPPORTED_CONTROL_SEARCH_TASK_CONSTRAINTS')
        source=host.store.artifact(item.source)
        from tools.research.physical_replay import explicit_control_source, numerically_verified_source
        if not (explicit_control_source(source) or numerically_verified_source(source)):
            raise ValueError('VERIFIED_OR_EXPLICIT_CONTROL_START_REQUIRED')
        if item.adaptation_from:
            parent=host.store.artifact(item.adaptation_from)
            if source.get('trajectory') is None:raise ValueError('CONTROL_SCHEDULE_SOURCE_REQUIRED')
            binding(parent['configuration'],source['trajectory'])
            old_task=deepcopy(parent['configuration']['task']);new_task=deepcopy(cfg['task'])
            for task in (old_task,new_task):task['initializer']['parameters']['data']={}
            if old_task!=new_task:raise ValueError('CROSS_TASK_ADAPTATION_REQUIRES_INDEPENDENT_TRANSFER_STUDY')
            source=initialize_schedule(cfg,source,item.adaptation_from)
        binding(cfg,source['trajectory'])
        limits=adapter.ranking_limits()
        tendon_limits={t['id']:t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']}
        return dict(id=str(index)+'-'+plain(item.source)['artifact_id'],candidate=plain(item.candidate),schedule=source,
            configuration=cfg,source=plain(item.source),
            limits=[tendon_limits[t] for t in source['trajectory']['tendon_order']],
            task_options=dict(target=cfg['task']['goal']['data']['target_m'],holding_start=adapter.holding_start_s(),
                position_limit=limits['holding_max_error_m'],terminal_position_limit=limits['terminal_error_m'],speed_limit=limits['holding_max_speed_m_s']))
    if q.settings.version!='local_control_search_v2':raise ValueError('PUBLIC_SEARCH_REQUIRES_V2_SETTINGS')
    starts=[make_start(item,i) for i,item in enumerate([q,*q.additional_starts])]
    def factory(start,action,**kwargs):
        value={k:getattr(plan,k) for k in ('hypothesis','supporting_evidence','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')}
        decision=plain(plan.decision);decision.update(research_intent='PHYSICAL_VALIDATION',selected_candidate=start['candidate'],requested_budget=1,claimed_inference='empirical_search')
        return dict(value,action=action,decision=decision,**kwargs)
    def evaluate(start,schedule,metadata):
        from tools.research.budget import protected
        cfg=start['configuration']
        if protected(host):raise SearchStopped('protected_closeout')
        guard(host,True)
        schedule['provenance']['batch_request']=key
        # Exact historical observations are reusable baselines, never fresh passes.
        result=None;cached=False
        for entry in state(host).get('research_history',[]):
            old=host.store.artifact(entry['reference']);old_cfg=host.store.artifact(old['candidate'])['configuration']
            old_source=host.store.artifact(old['source_reference'])
            if schedule_identity(cfg,schedule['trajectory'])==schedule_identity(old_cfg,old_source['trajectory']):
                if task_gap(old)['accepted']:raise SearchStopped('historical_pass_requires_separately_authorized_fresh_validation')
                result=dict(reference=entry['reference'],**old);cached=True;break
        if result is None:
            from tools.research.budget import backend_capacity
            available=host.store.remaining()['remaining']['tool_calls']-state(host)['spec']['budgets']['protected_public_operations']
            if available<1 or backend_capacity(host)<1:raise SearchStopped('protected_or_shared_budget_exhausted')
            result,cached=evaluate_schedule(host,start['candidate'],schedule,lambda action,**kw:factory(start,action,**kw),origin=origin)
        gap=task_gap(result)
        return dict(reference=result['reference'],source=result['source_reference'],candidate=start['candidate'],
            task_gap=gap,cache_hit=cached,cost_s=0. if cached else result['charged_numerical_s'],
            outputs=task_outputs(host.store.artifact(result['raw_reference'])) if gap['valid_complete'] else None,
            original_acceptance=result['acceptance'])
    result=search(starts,evaluate,q.settings)
    result.update(starts=[{k:s[k] for k in ('id','candidate','source')} for s in starts],candidate=plain(q.candidate),source=plain(q.source),adaptation_from=plain(q.adaptation_from),
        adaptation_budget=q.settings.evaluation_requests,plan_decision=plain(plan.decision))
    ref=save(host,result,'public_control_search_result')
    update(host,control_search_results=[*state(host).get('control_search_results',[]),ref])
    return dict(reference=ref,best=result['best'],stop_reason=result['stop_reason'],
        cost_feedback=result['cost_feedback'],start_feedback=result['start_feedback'],local_responses=result['local_responses'],
        evaluation_requests=len(result['candidates']),new_physical_evaluations=sum(not r['cache_hit'] for r in result['candidates']))
