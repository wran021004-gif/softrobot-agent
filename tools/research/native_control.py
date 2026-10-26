"""Adapt the existing finite control search to native short trajectory evaluation.

No second optimizer, Store, evaluator or budget. Only full physical_replay can
establish frozen task acceptance; these callbacks rank sampled native proxies.
"""
from copy import deepcopy
import json
import time
import numpy as np
from tools.platform_store import plain


def window_applicability(requirements, query, assessed, point, reasons):
    q=getattr(query,'control_optimization',None)
    if q is None:
        reasons.append('Bound complete source schedule and explicit v2 search window required.')
        window=None
    else:
        window=q.settings.correction_window_s
        if (point.get('actual_time_s') is None or abs(window[0]-point['actual_time_s'])>1e-12
                or abs(window[1]-requirements.duration_s)>1e-12):
            reasons.append(f'Native optimization window must start at selected state time {point.get("actual_time_s")} s and end at task duration {requirements.duration_s} s; received {window}. Frozen initialization starts at 0 s; a later window requires a matching saved state.')
    if (abs(query.protocol.duration_s-requirements.duration_s)>1e-12 or
            abs(query.protocol.period_s-requirements.physical_inputs['control_period_s'])>1e-12):
        reasons.append('Frozen duration and input period must match protocol.')
    if query.operation=='mujoco_nonlinear_task_capability_v1' and window and abs(window[0])>1e-12:
        reasons.append('Nonlinear T1 requires the complete frozen task from 0 s.')
    coverage=[]
    expected={'terminal_error_m':'tip_position','holding_max_error_m':'tip_position','holding_max_speed_m_s':'tip_velocity'}
    if {c.constraint_id for c in requirements.constraints}!=set(expected):
        reasons.append('Native control v1 requires the registered Reach/Hold norm constraints.')
    for c in requirements.constraints:
        matched=[i for i in c.indices if window and window[0]-1e-12<=requirements.time_grid_s[i]<=window[1]+1e-12]
        supported=(c.kind=='norm_bound' and c.signal.entity=='tip' and c.signal.frame=='world' and
            c.signal.phase=='post_step' and c.signal.name==expected.get(c.constraint_id))
        if not supported:reasons.append('Unsupported native control constraint: '+c.constraint_id)
        if supported and len(matched)!=len(c.indices):reasons.append('All task position/velocity constraint samples must be covered by the native window.')
        coverage.append(dict(constraint_id=c.constraint_id,expressible=supported,
            status='diagnostic' if supported else 'not_checked',analyzed_indices=matched if supported else [],
            reason='Sampled native control proxy; remaining acceptance components require full replay.'))
    return dict(status='not_applicable' if reasons else 'applicable',reasons=reasons,
        constraint_coverage=coverage,full_task_supported=False,execution_support='independent_full_replay_required',
        model_assessment=assessed,horizon=dict(task_duration_s=requirements.duration_s,
            origin=point.get('actual_time_s'),analysis_window_s=window,period_s=query.protocol.period_s,
            interpretation='Every covered constraint sample, including checkpoint origin; no inherited prefix acceptance.'))


def calculate(configuration, binding, query, point, requirements, context, checkpoint=None):
    from extensions.tendon_family.mujoco_analysis import NativeModel
    from tools.research.local_control_search import search
    from tools.research.control_correction import task_measure
    from tools.research_tasks import task_adapter
    from tools.research.native_analysis import assessment, applicability
    from tools.research.analysis import scoped_result
    from schemas.platform import SessionInput
    started=time.perf_counter();q=query.control_optimization;settings=q.settings
    if configuration['task']['family']!='task.reach':raise ValueError('NATIVE_CONTROL_V1_SUPPORTS_REACH_HOLD_ONLY')
    source=context['schedule'];tr=source['trajectory'];times=np.asarray(tr['times_s'])
    k=round(point['actual_time_s']/query.protocol.period_s)
    prefix=point.get('prefix_tensions_n')
    if point.get('native_replay'):prefix=[r['tension_n'] for r in point['native_replay']['rows']]
    if prefix is None or not np.array_equal(np.asarray(prefix).reshape(k,len(tr['tendon_order'])),np.asarray(tr['tensions_n'])[:k]):
        raise ValueError('CHECKPOINT_REQUIRES_IDENTICAL_VERIFIED_CONTROL_PREFIX')
    native=NativeModel(configuration)
    if checkpoint:checkpoint('native_progress_0000',dict(stage='native_model_built',completed_rollouts=0,
        cost={**native.cost,'kernel_wall_s':time.perf_counter()-started}))
    point,start=native.reconstruct(point) if point.get('native_replay') else (point,native.restore(point))
    if not np.allclose(native.limits[:,0],0,atol=0,rtol=0):raise ValueError('ZERO_LOWER_TENSION_BOUND_REQUIRED')
    adapter=task_adapter(configuration);limits=adapter.ranking_limits()
    options=dict(target=configuration['task']['goal']['data']['target_m'],holding_start=adapter.holding_start_s(),
        position_limit=limits['holding_max_error_m'],terminal_position_limit=limits['terminal_error_m'],speed_limit=limits['holding_max_speed_m_s'])
    if abs(configuration['task']['timing']['sample_period_s']-query.protocol.period_s)>1e-12:
        raise ValueError('NATIVE_CONTROL_V1_REQUIRES_MATCHED_SAMPLE_AND_CONTROL_GRIDS')
    initial=dict(id='native',schedule=source,limits=native.limits[:,1].tolist(),task_options=options)
    evaluations=[]
    peak_state=None
    def evaluate(_start, schedule, metadata):
        nonlocal peak_state
        try:
            outputs=native.rollout_sequence(start,times[k:],schedule['trajectory']['tensions_n'][k:],
                **(dict(capture_speed_after_s=options['holding_start']) if not evaluations else {}))
            peak_state=outputs.pop('peak_speed_state',peak_state)
        except Exception:
            if checkpoint:checkpoint('native_progress_'+str(len(evaluations)+1).zfill(4),dict(
                callback_status='incomplete',completed_rollouts=len(evaluations),
                latest_complete_measure=evaluations[-1] if evaluations else None,
                cost={**native.cost,'kernel_wall_s':time.perf_counter()-started}))
            raise

        measure=task_measure(outputs,**options)
        hold=np.asarray(outputs['times_s'])>=options['holding_start']-1e-12
        p=np.linalg.norm(np.asarray(outputs['tip_positions_m'])-options['target'],axis=1)
        v=np.linalg.norm(outputs['tip_velocities_m_s'],axis=1)
        ratios=np.r_[p[-1]/options['terminal_position_limit'],p[hold]/options['position_limit'],v[hold]/options['speed_limit']]
        sample_times=np.r_[outputs['times_s'][-1],np.asarray(outputs['times_s'])[hold],np.asarray(outputs['times_s'])[hold]]
        worst=int(np.argmax(ratios));measure['worst_constraint']=dict(
            kind='terminal_position' if worst==0 else 'holding_position' if worst<=sum(hold) else 'holding_speed',
            time_s=float(sample_times[worst]),normalized_signed_excess=float(ratios[worst]-1))
        evaluations.append(measure)
        if checkpoint:checkpoint('native_progress_'+str(len(evaluations)).zfill(4),dict(completed_rollouts=len(evaluations),latest=measure,
            cost={**native.cost,'kernel_wall_s':time.perf_counter()-started}))
        return dict(reference='native-rollout-'+str(len(evaluations)-1),outputs=outputs,measure=measure,
            task_gap=dict(valid_complete=True,accepted=False,normalized_gap=measure['normalized_gap'],
                components=dict(terminal=ratios[0]-1,position=float(max(p[hold])/options['position_limit']-1),
                    speed=float(max(v[hold])/options['speed_limit']-1))),
            cost_s=0.,independent_evaluation_executed=False)
    result=search([initial],evaluate,settings,evaluation_kind='native_short_rollout',
        rank_key=lambda row:(row['measure']['signed_maximum_excess'],row['measure']['sum_normalized_excess']),
        stop_when=lambda row:row['measure']['signed_maximum_excess']<=-settings.safety_margin_fraction)
    best=result['best'];optimized=deepcopy(source)
    if best is None:raise ValueError('NO_VALID_NATIVE_CONTROL_PREDICTION')
    from tools.research.control_correction import corrected_tensions
    optimized['trajectory']['tensions_n']=corrected_tensions(tr['tensions_n'],times[:-1],settings.knots_s,
        best['coefficients_n'],native.limits[:,1],settings.correction_window_s).tolist()
    optimized.update(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured')
    optimized['provenance']=dict(method=query.operation,source=context['source'],candidate=binding['candidate'],
        state_provenance=point.get('provenance'),settings=plain(settings),inherited_acceptance=False)
    cost=dict(**native.cost,optimization_iterations=result['iterations_started'],
        completed_response_steps=len(result['local_responses']),
        optimization_evaluations=len(evaluations),kernel_wall_s=time.perf_counter()-started)
    raw=dict(initial_state=point,original_schedule=source,optimized_schedule=optimized,optimization=result,cost=cost,
        external_force_execution=dict(forces=native.scene['forces'],semantics=native.scene['semantics'].get('external_forces')))
    if peak_state is not None:
        peak_state.update(candidate=binding['candidate'],configuration_identity=binding['effective_configuration_identity'],
            provenance=dict(method='baseline_rollout_holding_speed_peak',source=context['source'],inherited_acceptance=False))
        raw['baseline_peak_speed_state']=peak_state
    baseline=evaluations[0];comparison=dict(baseline=baseline,best=best['measure'])
    quantities=[dict(name=name,value=row[field],unit=unit,
        source_pointer='/native_dynamics/optimization/'+('candidates/0' if label=='baseline' else 'best')+'/measure/'+field)
        for label,row in comparison.items() for name,field,unit in [
            (label+'_holding_max_speed','holding_max_speed_m_s','m/s'),
            (label+'_holding_max_position_error','holding_max_position_error_m','m'),
            (label+'_signed_maximum_excess','signed_maximum_excess','1')]]
    summary=dict(question='Bounded native sequence control optimization',basis=dict(model='model.mujoco_native@1.0.0',
        state_time_s=point['actual_time_s'],window_s=settings.correction_window_s,channels=native.tendons,
        search_dimension=result['search_dimension'],sample_count=len(best['outputs']['times_s'])),quantities=quantities,
        comparison=comparison,solver=dict(stop_reason=result['stop_reason'],
            last_local_solver=next((r['local_solver'] for r in reversed(result['candidates']) if r.get('local_solver')),None)),
        interpretation='Cloned nonlinear native sequence predictions with the existing bounded local control search.',
        limitations=['Local sampled simulation estimate; no global optimum, hardware or regional guarantee.'],
        unresolved=['Full 0-to-duration replay and independent frozen acceptance remain required.'],cost=cost,
        control_schedule_pointer='/control_schedule_reference',detail_pointer='/native_dynamics',
        next_actions=['physical_replay using control_schedule_reference','Read local_responses to revise parameterization or radius','Rebuild a legal prefix for each changed structure'])
    fit=applicability(requirements,query,assessment(SessionInput.model_validate(configuration),requirements),point)
    value=dict(status='computed',operation=query.operation,binding={**binding,'model_identity':binding['effective_configuration_identity']},
        model_identity=binding['effective_configuration_identity'],protocol=plain(query.protocol),
        operating_point={key:point[key] for key in ('actual_time_s','phase','input_units')},native_dynamics=raw,native_analysis=summary,
        task_acceptance='unmeasured',local_model_constraints=dict(status='diagnostic_only'),proxy_values={},
        internal_calculations=[dict(purpose=query.operation,**cost)],limitations=summary['limitations'])
    value=scoped_result(value,requirements,fit,query)
    if query.operation=='mujoco_nonlinear_task_capability_v1':
        from tools.research.nonlinear_capability import t1_summary,control_sensitivities
        value['nonlinear_capability']=t1_summary(value,settings)
        raw['control_task_sensitivity']=control_sensitivities(result,requirements)
    json.dumps(value,allow_nan=False)  # Fail before worker publication, with last progress retained.
    return value
