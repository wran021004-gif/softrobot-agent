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


def search(starts,evaluate,settings):
    """evaluate(start, source, metadata) returns task_gap, outputs, refs and costs.

    All probes participate in validity-first ranking. A failed model direction
    never vetoes a legal physical evaluation. Restart deterministically from
    starts; the callback recovers completed Store receipts, not optimizer state.
    """
    cfg=LocalControlSearchSettings.model_validate(settings);n=4*len(cfg.knots_s)
    if not starts:raise ValueError('BOUND_STARTS_REQUIRED')
    if len({digest([s['schedule']['trajectory']['task_identity'],s['task_options']]) for s in starts})!=1:
        raise ValueError('COMPARABLE_TASKS_REQUIRED')
    for s in starts:
        tr=s['schedule']['trajectory']
        if len(tr['tendon_order'])!=4 or len(tr['tensions_n'])!=35 or not all(tr.get(k) for k in ('model_identity','design_identity','task_identity')):
            raise ValueError('BOUND_35_BY_4_START_REQUIRED')
    rows=[];best=None;centers={};radii={s['id']:cfg.initial_radius_n for s in starts};stop='iteration_limit'

    def vectors(row,start):return constraint_vectors(row['outputs'],**start['task_options'])

    def attempt(start,x,label,base=None,predicted=None,radius=None):
        nonlocal best
        if len(rows)>=cfg.evaluation_requests:raise SearchStopped('evaluation_request_budget')
        if not np.isfinite(x).all() or np.any(abs(x)>cfg.coefficient_limit_n+1e-12):raise ValueError('ILLEGAL_COEFFICIENTS')
        source=deepcopy(start['schedule']);tr=source['trajectory']
        tr['tensions_n']=corrected_tensions(tr['tensions_n'],tr['times_s'][:-1],cfg.knots_s,x,start['limits']).tolist()
        meta=dict(algorithm=cfg.method,start=start['id'],coefficients_n=x.tolist(),label=label,
            sequence_hash=digest(tr['tensions_n']),prediction_base=base['reference'] if base else None,
            predicted_improvement=predicted,trust_radius_n=radius,prospective_guarantee=False,
            applicability='Local sampled response at the stated candidate only; no regional error bound',
            extrapolation=bool(base and radius is not None and np.max(abs(x-np.asarray(base['coefficients_n'])))>radius+1e-12))
        source['provenance']=dict(source['provenance'],search=meta)
        row=dict(evaluate(start,source,meta),**meta)
        valid=row['task_gap']['valid_complete'] and row['task_gap']['normalized_gap'] is not None
        if not valid:row['task_gap']={**row['task_gap'],'normalized_gap':None}
        actual=(base['task_gap']['normalized_gap']-row['task_gap']['normalized_gap']) if base and valid else None
        row.update(actual_improvement=actual,direction_agrees=(predicted*actual>0) if predicted and actual else None)
        if valid and (best is None or ranking_key(row)<ranking_key(best)):best=row
        row['best_valid_reference']=best['reference'] if best else None
        rows.append(row)
        if valid and row['task_gap']['accepted']:raise SearchStopped('first_original_task_pass')
        return row

    try:
        for start in starts:
            row=attempt(start,np.zeros(n),'baseline')
            if row['task_gap']['valid_complete']:centers[start['id']]=row
        if not centers:raise SearchStopped('no_valid_start')
        active=sorted((s for s in starts if s['id'] in centers),key=lambda s:ranking_key(centers[s['id']]))
        for iteration in range(cfg.iterations):
            start=active[iteration%len(active)];center=centers[start['id']];x=np.asarray(center['coefficients_n'])
            radius=radii[start['id']]
            if radius<cfg.minimum_radius_n:
                if all(r<cfg.minimum_radius_n for r in radii.values()):raise SearchStopped('stagnation')
                continue
            if cfg.method=='pattern':
                improved=False
                # Late knots first; a complete sweep still covers earlier control.
                for j in reversed(range(n)):
                    for direction in (1,-1):
                        trial=x.copy();trial[j]=np.clip(x[j]+direction*radius,-cfg.coefficient_limit_n,cfg.coefficient_limit_n)
                        if np.array_equal(trial,x):continue
                        row=attempt(start,trial,'coordinate',base=center,radius=radius)
                        if ranking_key(row)<ranking_key(center):centers[start['id']]=row;improved=True;break
                    if improved:break
                if not improved:radii[start['id']]*=.5
            else:
                y=vectors(center,start);columns=[];valid=True
                for j in range(n):
                    trial=x.copy();h=min(cfg.difference_step_n,radius)
                    h=h if x[j]+h<=cfg.coefficient_limit_n else -h;trial[j]+=h
                    row=attempt(start,trial,'finite_difference',base=center,radius=radius)
                    if not row['task_gap']['valid_complete']:valid=False;break
                    columns.append((vectors(row,start)-y)/h)
                if not valid:radii[start['id']]*=.5;continue
                tr=start['schedule']['trajectory'];basis=correction_basis(tr['times_s'][:-1],cfg.knots_s,4)
                solved=constrained_response_step(y,np.stack(columns,axis=-1),x,tr['tensions_n'],basis,
                    start['limits'],radius,cfg.coefficient_limit_n)
                if not solved['success']:raise SearchStopped('numerical_failure: '+solved['numerical_status'])
                predicted=center['task_gap']['normalized_gap']-solved['predicted_gap']
                row=attempt(start,x+solved['delta'],'local_response_proposal',base=center,predicted=predicted,radius=radius)
                row['local_solver']={k:v for k,v in solved.items() if k!='delta'}
                radii[start['id']]=trust_radius(radius,predicted,row['actual_improvement'],cfg.coefficient_limit_n)
                row['next_trust_radius_n']=radii[start['id']]
                eligible=[r for r in rows if r['start']==start['id'] and r['task_gap']['valid_complete']]
                centers[start['id']]=min(eligible,key=ranking_key)
    except SearchStopped as exc:stop=str(exc)
    return dict(version='local_control_search_v1',algorithm=cfg.method,stop_reason=stop,
        candidates=rows,best=best,trust_radii_n=radii,prospective_guarantee=False,
        interpretation='Finite control search outcome; structural infeasibility remains unknown.')
