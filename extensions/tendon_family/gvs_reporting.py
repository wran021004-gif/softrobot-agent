"""Read sealed backend exports and distinguish execution, task and solve results."""
import gzip
import json
from collections import Counter
import numpy as np
from schemas.platform import EvaluationResult
from tools.platform_store import plain
from .gvs_profile import execution_scope, checked_control, SampledSettling, settling_for


def motion_summary(motion, signed_error, duration, window_s, tolerance):
    """Sampled diagnostics only; the existing endpoint evaluator remains authority."""
    minimum=min(motion,key=lambda r:r['tip_error_m']) if motion else None
    late=[r for r in motion if duration-window_s-1e-9<=r['time_s']<=duration+1e-9]
    terminal=motion[-1] if motion and abs(motion[-1]['time_s']-duration)<1e-8 else None
    return dict(minimum_sampled_error_m=None if minimum is None else minimum['tip_error_m'],
        minimum_sampled_error_time_s=None if minimum is None else minimum['time_s'],
        terminal_error_m=None if terminal is None else terminal['tip_error_m'],
        signed_terminal_position_error_m=signed_error,error_convention='actual_tip minus target; world frame',
        terminal_tip_speed_m_s=None if terminal is None else terminal['tip_speed_m_s'],
        late_interval_s=[duration-window_s,duration],
        late_sample_interval_s=[late[0]['time_s'],late[-1]['time_s']] if late else None,
        late_error_change_m=late[-1]['tip_error_m']-late[0]['tip_error_m'] if len(late)>1 else None,
        late_change_definition='last sampled error minus first sampled error in stated interval',
        entered_tolerance_earlier_but_ended_outside=None if terminal is None else bool(
            terminal['tip_error_m']>tolerance and any(r['time_s']<duration and r['tip_error_m']<=tolerance for r in motion)),
        tolerance_m=tolerance,scope='Sampled observations, not continuous-time guarantees or new acceptance criteria.')


def summarize(task, result, evaluation, rows, observations, motion, limits, settling=None):
    acceptance = SampledSettling.model_validate(settling or {})
    duration = task.timing.duration_s
    complete = bool(result['solver_status'] == 'completed' and rows and (abs(rows[-1]['time_s'] - duration) < 1e-08))
    valid = complete and evaluation is not None and (evaluation['validity'] == 'valid')
    tracking = False
    errors = [float(np.linalg.norm(np.asarray(r['tip_m']) - task.goal.data['target_m'])) for r in rows]
    window = [r for r in motion if r['time_s'] >= duration - acceptance.window_s - 1e-09]
    expected = round(acceptance.window_s / task.timing.sample_period_s) + 1
    available = complete and len(window) == expected and (len(motion) == len(rows))

    def values(key):
        return [o[key] for o in observations if o.get(key) is not None]

    def mean(key):
        return float(np.mean(values(key))) if values(key) else None
    tensions = np.array([r['tension_n'] for r in rows])
    summary = dict(
        complete=complete,
        valid_complete_execution=valid,
        terminal_position_m=rows[-1]['tip_m'] if complete else None,
        official_task_success=None if evaluation is None else evaluation['task_success'],
        evaluation_validity=None if evaluation is None else evaluation['validity'],
        solver_status=result['solver_status'],
        last_valid_time_s=rows[-1]['time_s'] if rows else None,
        terminal_error_m=errors[-1] if complete else None,
        last_valid_error_m=errors[-1] if errors else None,
        maximum_error_m=max(errors) if errors else None,
        minimum_error_m=min(errors) if errors else None,
        terminal_tip_speed_m_s=motion[-1]['tip_speed_m_s'] if complete and motion else None,
        sampled_settling=dict(available=available, passed=all((r['tip_error_m'] <= acceptance.position_limit_m and r['tip_speed_m_s'] <= acceptance.speed_limit_m_s for r in window)) if available else None, **plain(acceptance), continuous_time_guarantee=False, max_error_m=max((r['tip_error_m'] for r in window)) if available else None, max_speed_m_s=max((r['tip_speed_m_s'] for r in window)) if available else None),
        updates=len(observations),
        applied_control_updates=sum((o.get('actual_tension_n') is not None for o in observations)),
        accepted_plans=sum((o.get('plan_accepted', o.get('optimization_constraint_violation') is not None and o['optimization_constraint_violation'] <= 1e-05 and (not o.get('stop_requested', False)) and (not o.get('failure_response_used', False))) for o in observations)),
        optimization_status_counts=dict(Counter((o.get('optimization_status') or 'unavailable' for o in observations))),
        raw_termination_counts=dict(Counter((o.get('optimization_raw_status') or 'unavailable' for o in observations))),
        initialization_selected=sum((o.get('optimization_selected_iteration') in (-1, 0) for o in observations)),
        recovered_plans=sum((o.get('plan_source') == 'reintegrated_returned_iterate' for o in observations)),
        recovery_attempts=sum((bool((o.get('feasibility_recovery') or {}).get('attempted')) for o in observations)),
        recovery_failures=sum((bool((o.get('feasibility_recovery') or {}).get('error')) for o in observations)),
        recovery_root_solves=sum(((o.get('feasibility_recovery') or {}).get('root_solve_attempts', 0) for o in observations)),
        other_feasible_deliveries=sum((bool(o.get('plan_accepted')) and o.get('plan_source') != 'reintegrated_returned_iterate' for o in observations)),
        accepted_noninitialization_plans=sum((bool(o.get('plan_accepted')) and (o.get('plan_source') == 'reintegrated_returned_iterate' or (o.get('optimization_selected_iteration') is not None and o['optimization_selected_iteration'] > 0)) for o in observations)),
        converged_updates=sum((not o['optimization_nonconverged'] for o in observations)),
        early_stopped_plans=sum((o.get('optimization_status') == 'feasible_early_stop' for o in observations)),
        unusable_plans=sum((not o.get('plan_accepted', False) for o in observations)),
        policy_stop_reason_counts=dict(Counter((o['policy_stop_reason'] for o in observations if o.get('policy_stop_reason')))),
        execution_failure_reason=result['data']['data'].get('reason'),
        solver_error_count=sum((o.get('solver_error') is not None for o in observations)),
        solver_failure_flags=sum((o['solver_failed'] for o in observations)),
        hold_last_responses=sum((o['failure_response_used'] for o in observations)),
        maximum_plan_violation=max(values('optimization_constraint_violation'), default=None),
        deadline_misses=sum((o['deadline_missed'] for o in observations)),
        mean_update_s=mean('update_wall_s'),
        per_update_delivery_s=values('update_wall_s'),
        mean_preparation_s=mean('warm_preparation_s'),
        mean_numerical_solve_s=mean('optimization_solve_s'),
        mean_validation_s=mean('plan_validation_s'),
        solver_construction_s=sum(values('solver_construction_s')),
        mean_recovery_s=mean('recovery_wall_s'),
        mean_recovery_integration_s=mean('recovery_integration_s'),
        mean_recovery_validation_s=mean('recovery_validation_s'),
        graph_construction_s=observations[0]['graph_construction_s'] if observations else None,
        backend_timings_s=result['data']['data']['timings_s'],
        tension_range_n=[float(tensions.min()), float(tensions.max())] if rows else None,
        force_bound_violation_n=float(max(0.0, np.max(-tensions), np.max(tensions - np.asarray(limits)))) if rows else None,
        max_projection_residual_rad_m=max(values('gvs_projection_residual_max_rad_m'), default=None),
        max_rate_projection_residual_rad_m_s=max((r['rate_projection_residual_rad_m_s'] for r in motion), default=None),
        max_sampled_contacts=max((r['contacts'] for r in motion), default=None),
        real_time_demonstrated=bool(complete and observations and all((not o['deadline_missed'] for o in observations))),
    )
    summary['motion_summary'] = motion_summary(motion, None if not complete else (np.asarray(rows[-1]['tip_m']) - task.goal.data['target_m']).tolist(), duration, acceptance.window_s, task.evaluator.parameters.data['tolerance_m'])
    comparisons, missing = aligned_predictions(rows, observations, motion)
    summary['one_step_prediction_comparisons'] = comparisons
    summary['one_step_prediction_summary'] = dict(aligned_count=len(comparisons), missing=missing, maximum_tip_difference_m=max((r['tip_difference_m'] for r in comparisons), default=None), mean_tip_difference_m=float(np.mean([r['tip_difference_m'] for r in comparisons])) if comparisons else None, velocity_matched_count=sum((r.get('velocity_difference_m_s') is not None for r in comparisons)), velocity_missing=[dict(time_s=r['start_s'], reason=r['velocity_missing_reason']) for r in comparisons if r.get('velocity_missing_reason')], maximum_velocity_vector_difference_m_s=max((r['velocity_difference_m_s'] for r in comparisons if r.get('velocity_difference_m_s') is not None), default=None), maximum_speed_magnitude_difference_m_s=max((r['speed_magnitude_difference_m_s'] for r in comparisons if r.get('speed_magnitude_difference_m_s') is not None), default=None), frame='world', scope='Only accepted first-step predictions matched to next execution timestamp; no future-plan replay comparison')
    invalid=[r for r in missing if 'shape invalid' in r['reason']]
    diagnostic=summary['one_step_prediction_summary'];diagnostic['available']=bool(comparisons) and not invalid
    if invalid:
        diagnostic['status']='unavailable_invalid_vector_shape'
        diagnostic['valid_subset']={k:diagnostic[k] for k in ('maximum_tip_difference_m','maximum_velocity_vector_difference_m_s','maximum_speed_magnitude_difference_m_s')}
        for key in ('maximum_tip_difference_m','mean_tip_difference_m','maximum_velocity_vector_difference_m_s','maximum_speed_magnitude_difference_m_s'):diagnostic[key]=None
    summary['drive_utilization'] = [dict(tendon_index=i, limit_n=limit, maximum_n=float(tensions[:, i].max()) if rows else None, minimum_n=float(tensions[:, i].min()) if rows else None, near_upper_fraction=float(np.mean(tensions[:, i] >= 0.99 * limit)) if rows else None, near_zero_fraction=float(np.mean(tensions[:, i] <= 1e-06)) if rows else None) for i, limit in enumerate(limits)]
    summary['error_phases'] = [dict(interval_s=[a, b], maximum_error_m=max(es, default=None), final_error_m=es[-1] if es else None) for a, b in ((0.0, duration / 3), (duration / 3, 2 * duration / 3), (2 * duration / 3, duration)) for es in [[e for r, e in zip(rows, errors) if a - 1e-09 <= r['time_s'] <= b + 1e-09]]]
    summary['diagnostic_hypotheses'] = []
    summary['diagnostic_limitations'] = ['Sampled observations do not identify a dominant cause.', 'Force proximity alone does not imply a required physical design change.', 'Ideal tensions; omitted shear, stretch, torsion, tendon friction and actuator dynamics.']
    return summary



def aligned_predictions(rows, observations, motion=None):
    comparisons=[]; missing=[]
    for o in observations:
        pred=o.get('one_step_prediction')
        reason=None
        if pred is None:
            reason='accepted first-step prediction unavailable'
        elif not vector3(pred.get('tip_position_m')) or (pred.get('tip_velocity_m_s') is not None and not vector3(pred['tip_velocity_m_s'])):
            reason='prediction vector shape invalid: world position and velocity must each be finite shape [3]'
        elif pred.get('frame','world')!='world':
            reason='coordinate frame mismatch'
        else:
            following=[r for r in rows if abs(r['time_s']-pred['time_s'])<1e-8]
            intervening=any(o['time_s']+1e-8<r['time_s']<pred['time_s']-1e-8 for r in observations)
            actual=o.get('actual_tension_n')
            difference=None if actual is None else float(np.max(np.abs(np.asarray(actual)-pred['applied_tension_n'])))
            if len(following)!=1: reason='next execution timestamp missing or ambiguous'
            elif not vector3(following[0].get('tip_m')):reason='measured position vector shape invalid'
            elif intervening: reason='intervening control update'
            elif difference is None: reason='applied input unavailable'
            elif difference>1e-8: reason='applied input mismatch'
            else:
                r=following[0]
                comparison=dict(start_s=o['time_s'],end_s=pred['time_s'],frame='world',
                    applied_input_difference_n=difference,applied_tension_n=pred['applied_tension_n'],
                    predicted_tip_m=pred['tip_position_m'],measured_tip_m=r['tip_m'],
                    tip_difference_m=float(np.linalg.norm(np.asarray(pred['tip_position_m'])-r['tip_m'])))
                measured=[m for m in (motion or []) if abs(m['time_s']-pred['time_s'])<1e-8]
                velocity=pred.get('tip_velocity_m_s')
                if velocity is None:
                    comparison['velocity_missing_reason']='predicted velocity vector unavailable'
                elif len(measured)!=1 or not vector3(measured[0].get('tip_velocity_m_s')):
                    comparison['velocity_missing_reason']='saved-state world velocity missing or ambiguous'
                else:
                    actual_velocity=measured[0]['tip_velocity_m_s']
                    comparison.update(predicted_tip_velocity_m_s=velocity,measured_tip_velocity_m_s=actual_velocity,
                        velocity_difference_m_s=float(np.linalg.norm(np.asarray(velocity)-actual_velocity)),
                        speed_magnitude_difference_m_s=float(abs(np.linalg.norm(velocity)-np.linalg.norm(actual_velocity))))
                comparisons.append(comparison)
        if reason:missing.append(dict(time_s=o['time_s'],reason=reason))
    return comparisons,missing


def vector3(value):
    value=np.asarray(value)
    return value.shape==(3,) and np.issubdtype(value.dtype,np.number) and bool(np.isfinite(value).all())


def reconstruct_motion(files, rows, target):
    import mujoco
    from .gvs_projection import project
    from .contracts import ResolvedGVSBasis
    physics = json.loads(files['resolved_physics.json'])
    control = json.loads(files['control_spec.json'])
    basis = ResolvedGVSBasis.model_validate(control['projector']['resolved_basis'])
    model = mujoco.MjModel.from_xml_string(files['robot.xml'].decode('utf8'))
    data = mujoco.MjData(model)
    ids = [model.joint(j).id for j in physics['dofs']]
    qi = model.jnt_qposadr[ids]
    vi = model.jnt_dofadr[ids]
    motion = []
    for row in rows:
        data.qpos[qi] = row['qpos_rad']
        data.qvel[vi] = row['qvel_rad_s']
        mujoco.mj_forward(model, data)
        J = np.zeros((3, model.nv))
        Jr = np.zeros_like(J)
        mujoco.mj_jacSite(model, data, J, Jr, model.site('tip_site').id)
        projection = project(physics, basis, row['qpos_rad'], row['qvel_rad_s'])
        tracking = False
        position, velocity = (target, np.zeros(3))
        motion.append(dict(tip_velocity_m_s=(J @ data.qvel).tolist(), tip_position_m=list(row['tip_m']), velocity_error_m_s=float(np.linalg.norm(J @ data.qvel - velocity)), time_s=row['time_s'], tip_speed_m_s=float(np.linalg.norm(J @ data.qvel)), tip_error_m=float(np.linalg.norm(np.asarray(row['tip_m']) - position)), contacts=int(data.ncon), rate_projection_residual_rad_m_s=projection['rate_projection_residual_max_rad_m_s']))
    return (motion, physics)




def report_configuration(candidate, baseline):
    """Report the receipt-owned executed geometry, retaining baseline ownership."""
    from schemas.platform import CandidateInput
    from tools.state_io import digest
    owned=CandidateInput.model_validate(candidate)
    if owned.baseline_identity!=digest(plain(baseline)) or owned.content_identity!=digest(plain(owned.effective)):
        raise ValueError('REPORT_CANDIDATE_SCOPE_MISMATCH')
    checked_control(owned.effective)
    return owned.effective

def report(ctx,args):
    from .gvs_profile import ProfileOutput
    checked_control(ctx.input)
    def receipt(request,tool):
        from tools.execution_completion import completed_receipt
        value=completed_receipt(ctx.store,ctx.run_id,request)
        if value is None or value['tool_id']!=tool or value['execution_status']!='completed':
            raise ValueError('SEALED_COMPLETED_RECEIPT_REQUIRED: '+request)
        return value
    sim=receipt(args.simulation_request_id,'simulation.run')
    ev=receipt(args.evaluation_request_id,'evaluation.run')
    evaluation=EvaluationResult.model_validate(ctx.artifact(ev['output']))
    if evaluation.source_execution_id!=sim['execution_id']:
        raise ValueError('REPORT_EVALUATION_EXECUTION_MISMATCH')
    metadata=ctx.store.session(ctx.run_id)['state']['result_executions'][sim['execution_id']]
    candidate=ctx.artifact(metadata['candidate_input'])
    executed=report_configuration(candidate,ctx.input)
    bundle=None
    for event in ctx.store.events(ctx.run_id):
        if event['kind']=='simulation' and event['execution_id']==sim['execution_id']:
            for ref in event['outputs']:
                if ref['media_type']=='application/json':
                    value=ctx.artifact(ref)
                    if isinstance(value,dict) and 'files' in value and value.get('result')==sim['output']:
                        bundle=value
    imported=ctx.store.session(ctx.run_id)['state'].get('completion_import')
    if bundle is None and imported:
        from .diagnostic_evidence import BoundReader
        source=BoundReader(ctx.store,imported['binding']).resolve(sim['execution_id'])
        bundle=ctx.artifact(source['manifest'])
    if bundle is None:raise ValueError('SEALED_BACKEND_EXPORTS_REQUIRED')
    files={f['filename']:ctx.store.artifact(f['reference'],raw=True) for f in bundle['files']}
    rows=json.loads(gzip.decompress(files['trajectory.json.gz']))
    observations=json.loads(files['controller_observations.json'])
    motion,physics=reconstruct_motion(files,rows,executed.task.goal.data if executed.task.family=='task.tracking' else executed.task.goal.data['target_m'])
    output=summarize(executed.task,ctx.artifact(sim['output']),plain(evaluation),rows,observations,motion,
        [t['force_limit_n'] for t in physics['tendons']],None if executed.task.family=='task.tracking' else settling_for(executed))
    preparations=[e['outputs'][0] for e in ctx.store.events(ctx.run_id)
        if e['kind']=='control_preparation' and e['execution_id']==sim['execution_id']]
    output.update(task=plain(executed.task),execution_scope=execution_scope(executed),
        control_parameters=plain(executed.policy.controller.parameters),
        numerical_preparation=None if not preparations else ctx.artifact(preparations[-1]))
    output.update(simulation=sim['output'],evaluation=ev['output'],execution_id=sim['execution_id'],
        configuration=metadata['candidate_input'],candidate_id=candidate['candidate_id'],
        simulation_wall_s=sim['charged']['wall_s'] if 'charged' in sim else None,
        motion=plain(ctx.save_artifact(motion,'sampled_backend_motion')))
    comparisons=output.pop('one_step_prediction_comparisons')
    output['one_step_prediction_evidence']=plain(ctx.save_artifact(comparisons,'one_step_prediction_comparisons'))
    output['drive_utilization']=[dict(row,tendon=physics['tendons'][i]['entity']) for i,row in enumerate(output['drive_utilization'])]
    return ProfileOutput(detail=output)


