"""Two fixed sealing points and assessment rules, using the existing Store/events."""
from copy import deepcopy
import time
import numpy as np
from tools.platform_store import plain
from tools.state_io import digest
from .diagnostic_math import NonlinearModel
from .milestone5_preparation import fixed_input, LOCAL_VERSION, PREVIEW_VERSION
from .milestone5_validation import local_score, speed_change_direction

RULES=dict(primary_objective='Lowest sampled maximum holding speed, conditional on predicted terminal and holding position feasibility.',
    speed_tie_margin_m_s=1e-4,position_limit_m=.01,speed_limit_m_s=.02,numerical_speed_tolerance_m_s=1e-4,
    velocity_vector_tolerance_m_s=1e-4,direction_neutral_m_s=1e-4,
    local_direction='Compare predicted change to projected initial speed, observed change to observed initial speed. Absolute change <=1e-4 is neutral; predicted change within numerical uncertainty of +/-1e-4 is indeterminate.',
    constraint_handling='Position or terminal failure makes eligibility unresolved; forecast speed <=.02 is predicted-safe, otherwise predicted-violating. Always evaluate both candidates.',
    empirical_allowance=None,abstention='Incomplete/nonfinite/infeasible history, position violation, or speed gap <=1e-4: abstain. Resolved history rank is a testable forecast, not a proven safe rejection.',
    screening_usefulness='Universal abstention fails useful screening; report pairwise order errors, resolved coverage, accuracy, false rejection and false-safe counts.',
    original_gates='Accurate local numerics, useful prospective full-task discrimination/order, broader repeatability and real-time operation remain required. No threshold is relaxed.',
    readiness_dimensions=['implementation','registration','numerical_stability','backend_accuracy','discrimination','budget_admission','prospective_execution'])


def pair_decision(histories):
    candidates=[];usable=True
    for h in histories:
        metrics=h.get('metrics',{});valid=h.get('complete',False) and bool(h.get('rows')) and all(r['accepted'] for r in h['rows']) and all(np.isfinite(list(metrics.values())))
        position_safe=valid and metrics['holding_max_error_m']<=.01 and metrics['terminal_error_m']<=.01
        usable=usable and position_safe and all(r['accepted'] for r in h.get('rows',[]))
        candidates.append(dict(candidate_id=h['candidate_id'],metrics=metrics,valid=bool(valid),
            eligibility='abstain' if not position_safe else 'predicted_safe' if metrics['holding_max_speed_m_s']<=.02 else 'predicted_violating'))
    if len(candidates)!=2:raise ValueError('PAIR_REQUIRED')
    gap=None if not usable else candidates[1]['metrics']['holding_max_speed_m_s']-candidates[0]['metrics']['holding_max_speed_m_s']
    resolved=usable and abs(gap)>RULES['speed_tie_margin_m_s']
    order=[r['candidate_id'] for r in sorted(candidates,key=lambda r:r['metrics']['holding_max_speed_m_s'])] if resolved else None
    return dict(candidates=candidates,order=order,status='resolved' if resolved else 'abstain',gap_m_s=gap,
        hypothetical_rejection=None if order is None else order[-1],safety_claim=False,rules=RULES)


def seal_pair(store,run_id,protocol,scenario,forecasts):
    """Atomic pair seal, rejected after any backend reservation; never revise."""
    expected={r['recipe_id'] for r in protocol['recipes']}
    if {f['recipe_id'] for f in forecasts}!=expected:raise ValueError('BOTH_CANDIDATE_FORECASTS_REQUIRED')
    for f in forecasts:
        if f['scenario_id']!=scenario['scenario_id'] or f['version']!=PREVIEW_VERSION or not f['complete']:
            raise ValueError('FORECAST_SCOPE_OR_COVERAGE')
        from .gvs_profile import execution_scope
        recipe=next(r for r in protocol['recipes'] if r['recipe_id']==f['recipe_id'])
        expected_cfg=deepcopy(recipe['configuration']);expected_cfg['task']['initializer']=deepcopy(scenario['configuration']['task']['initializer'])
        if f.get('scientific_identity')!=digest(execution_scope(expected_cfg)):
            raise ValueError('FORECAST_CONFIGURATION_BINDING')
    value=dict(protocol_identity=digest(protocol),scenario_identity=digest(scenario),interval_s=protocol['task_interval_s'],
        controller_version=protocol['controller'],predictor_version=PREVIEW_VERSION,forecasts=forecasts,
        pair_decision=pair_decision(forecasts),classification='prospective sealed before either candidate backend')
    with store.transaction() as db:
        if db.execute("SELECT COUNT(*) FROM calls WHERE request_id='complete-simulation'").fetchone()[0]:raise ValueError('BACKEND_ALREADY_STARTED')
        state=store.session(run_id,db)['state'];previous=state.get('m5_pair_seal')
        if previous:
            if store.artifact(previous)!=value:raise ValueError('PAIR_SEAL_IMMUTABLE')
            return previous
        ref=store.put(db,value);state['m5_pair_seal']=plain(ref);store.update_state(db,run_id,state)
        store.event(db,run_id,'m5_pair_forecast','sealed_before_either_backend',outputs=[ref])
    return plain(ref)


def local_forecast(configuration,state,command,backend_position,backend_velocity,t,step_s=.000125):
    """Inputs are the pre-step command and observation only; no trajectory argument."""
    start=time.perf_counter();model=NonlinearModel(configuration,state,command,step_s)
    p,v,*_=model.motion(state[:model.n],state[model.n:]);p=np.asarray(p).ravel();v=np.asarray(v).ravel()
    end=fixed_input(model,state,command,.01,time.perf_counter()+30.)
    # Current-state resolution comparison is causal; development differences are not safety bounds.
    coarse_model=NonlinearModel(configuration,state,command,2*step_s)
    coarse=fixed_input(coarse_model,state,command,.01,time.perf_counter()+15.)
    uncertainty=dict(speed_m_s=abs(end['speed_m_s']-coarse['speed_m_s']),
        velocity_norm_m_s=float(np.linalg.norm(np.asarray(end['velocity_m_s'])-coarse['velocity_m_s'])),
        position_norm_m=float(np.linalg.norm(np.asarray(end['position_m'])-coarse['position_m'])))
    return dict(version=LOCAL_VERSION,start_s=t,end_s=t+.01,endpoint_position_m=end['position_m'],
        endpoint_velocity_m_s=end['velocity_m_s'],endpoint_speed_m_s=end['speed_m_s'],
        initial_projected_speed_m_s=float(np.linalg.norm(v)),initial_backend_speed_m_s=float(np.linalg.norm(backend_velocity)),
        initial_projected_velocity_m_s=v.tolist(),initial_backend_velocity_m_s=np.asarray(backend_velocity).tolist(),
        initial_projected_position_m=p.tolist(),initial_backend_position_m=np.asarray(backend_position).tolist(),
        input_n=list(command),initial_state=list(state),input_information_time_s=t,
        causal_input_policy='Current bounded direct command, held .01 s; no future measured input',
        integration_step_s=step_s,max_scaled_residual=end['max_scaled_residual'],cost_s=time.perf_counter()-start,
        numerical_uncertainty=uncertainty,numerical_stable=uncertainty['speed_m_s']<=1e-4 and uncertainty['velocity_norm_m_s']<=1e-4,
        supported_role='Directional diagnosis; endpoint accuracy and constraint classification scored separately.')


def checkpoint_observer(store,run_id,configuration,seal,protocol):
    def capture(update_id,t,controller,geometry,velocity,actual):
        if update_id not in (20,30):return
        if abs(t-update_id*.01)>1e-9:raise ValueError('CHECKPOINT_CLOCK')
        desired=np.asarray(controller.last['desired_tension_n'])
        if np.max(abs(desired-actual))>1e-9:raise ValueError('CAUSAL_COMMAND_MAPPING_MISMATCH')
        prediction=local_forecast(configuration,controller.observations[-1]['measured_initial_state'],desired,
            geometry['tip'],velocity,t,protocol['local_step_s'])
        prediction.update(pair_seal=seal,configuration_identity=digest(configuration),update_id=update_id)
        with store.transaction() as db:
            session=store.session(run_id,db)
            if session['state'].get('m5_pair_seal')!=seal:raise ValueError('PAIR_SEAL_REQUIRED')
            calls=list(db.execute("SELECT * FROM calls WHERE run_id=? AND request_id='complete-simulation' AND status='running'",(run_id,)))
            if len(calls)!=1:raise ValueError('ACTIVE_BACKEND_CALL_REQUIRED')
            call=calls[0];prediction['execution_id']=call['execution_id'];ref=store.put(db,prediction)
            store.event(db,run_id,'m5_local_prediction','sealed_before_step',request=call['request_id'],execution=call['execution_id'],
                inputs=[seal],outputs=[ref])
    return capture


def assess_local(prediction,observed,uncertainty):
    score=local_score(prediction,observed);delta=score['predicted_speed_change_m_s']
    if min(abs(delta-1e-4),abs(delta+1e-4))<=uncertainty:
        score.update(predicted_direction='indeterminate',direction_verdict='unresolved')
    score.update(numerical_uncertainty_m_s=uncertainty,
        vector_within_tolerance=score['velocity_error_norm_m_s']<=1e-4,
        speed_false_safe=prediction['endpoint_speed_m_s']<=.02 and observed['speed_m_s']>.02,
        speed_false_unsafe=prediction['endpoint_speed_m_s']>.02 and observed['speed_m_s']<=.02,
        position_false_safe=float(np.linalg.norm(np.asarray(prediction['endpoint_position_m'])-observed['target_m']))<=.01 and observed['error_m']>.01,
        position_error_vector_m=(np.asarray(prediction['endpoint_position_m'])-observed['position_m']).tolist(),
        velocity_error_vector_m_s=(np.asarray(prediction['endpoint_velocity_m_s'])-observed['velocity_m_s']).tolist())
    score['threshold_scope']='holding' if prediction['start_s']>=.3-1e-9 else 'diagnostic_nonholding'
    score['physical_holding_false_safe']=score['threshold_scope']=='holding' and (score['speed_false_safe'] or score['position_false_safe'])
    if not prediction.get('numerical_stable',True):score.update(direction_verdict='unresolved',supported_use='Numerical stability unresolved; quantitative/constraint use unsupported')
    return score


def assess_screening(decision,outcomes,preview_s,evaluation_s):
    if len(outcomes)!=2:raise ValueError('BOTH_COMPLETE_OUTCOMES_REQUIRED')
    actual=sorted(outcomes,key=lambda o:o['holding_max_speed_m_s']);gap=actual[1]['holding_max_speed_m_s']-actual[0]['holding_max_speed_m_s']
    actual_order=[o['candidate_id'] for o in actual] if gap>1e-4 else None
    resolved=decision['order'] is not None;correct=resolved and actual_order==decision['order']
    rejected=decision['hypothetical_rejection'];rejected_outcome=next((o for o in outcomes if o['candidate_id']==rejected),None)
    false_rejection=bool(rejected_outcome and (rejected_outcome['joint_acceptance'] or (actual_order is not None and rejected==actual_order[0])))
    false_safe=[];eligibility_correct=0;eligibility_resolved=0
    for candidate in decision['candidates']:
        outcome=next(o for o in outcomes if o['candidate_id']==candidate['candidate_id'])
        if candidate['eligibility']=='predicted_safe' and not outcome['joint_acceptance']:false_safe.append(candidate['candidate_id'])
        if candidate['eligibility']!='abstain':
            eligibility_resolved+=1
            eligibility_correct+=int((candidate['eligibility']=='predicted_safe')==outcome['joint_acceptance'])
    return dict(resolved_coverage=int(resolved),pairwise_order_verdict='unresolved' if not resolved else 'correct' if correct else 'incorrect',
        accuracy_among_resolved=None if not resolved else float(correct),abstained=not resolved,
        false_rejection_of_better_or_acceptable=false_rejection,predicted_safe_observed_violating=false_safe,
        preview_cost_s=preview_s,complete_evaluation_cost_s=evaluation_s,actual_validation_savings=0,
        ranking_planned_pairs=1,ranking_resolved_pairs=int(resolved),
        eligibility_planned_candidates=2,eligibility_resolved_candidates=eligibility_resolved,
        eligibility_resolved_coverage=eligibility_resolved/2,
        eligibility_accuracy_among_resolved=None if not eligibility_resolved else eligibility_correct/eligibility_resolved,
        hypothetical_future_execution_savings=int(rejected is not None),actual_order=actual_order,
        qualification='No validated savings, confidence bound or generalization from one pair.')
