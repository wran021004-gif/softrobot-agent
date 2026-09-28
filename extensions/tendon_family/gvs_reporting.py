"""Read sealed backend exports and distinguish execution, task and solve results."""
import gzip
import json
from collections import Counter
import numpy as np
from schemas.platform import EvaluationResult
from tools.platform_store import plain
from .gvs_profile import execution_scope, checked_control, SampledSettling, settling_for


def summarize(task, result, evaluation, rows, observations, motion, limits, settling=None):
    acceptance=SampledSettling.model_validate(settling or {})
    duration=task.timing.duration_s
    complete=bool(result['solver_status']=='completed' and rows and abs(rows[-1]['time_s']-duration)<1e-8)
    valid=complete and evaluation is not None and evaluation['validity']=='valid'
    tracking=task.family=='task.tracking'
    if tracking:
        from .tracking import reference_at
        desired,_=reference_at(task.goal.data,[r['time_s'] for r in rows])
        errors=np.linalg.norm(np.asarray([r['tip_m'] for r in rows])-desired,axis=1).tolist() if rows else []
    else:errors=[float(np.linalg.norm(np.asarray(r['tip_m'])-task.goal.data['target_m'])) for r in rows]
    window=[r for r in motion if r['time_s']>=duration-acceptance.window_s-1e-9]
    # Missing or partial final-window data is unavailable, never vacuous success.
    expected=round(acceptance.window_s/task.timing.sample_period_s)+1
    available=complete and len(window)==expected and len(motion)==len(rows)
    def values(key):return [o[key] for o in observations if o.get(key) is not None]
    def mean(key):return float(np.mean(values(key))) if values(key) else None
    tensions=np.array([r['tension_n'] for r in rows])
    summary=dict(complete=complete,valid_complete_execution=valid,
        official_task_success=None if evaluation is None else evaluation['task_success'],
        evaluation_validity=None if evaluation is None else evaluation['validity'],
        solver_status=result['solver_status'],last_valid_time_s=rows[-1]['time_s'] if rows else None,
        terminal_error_m=errors[-1] if complete else None,last_valid_error_m=errors[-1] if errors else None,
        maximum_error_m=max(errors) if errors else None,minimum_error_m=min(errors) if errors else None,
        terminal_tip_speed_m_s=motion[-1]['tip_speed_m_s'] if complete and motion else None,
        sampled_settling=dict(available=available,passed=all(r['tip_error_m']<=acceptance.position_limit_m and r['tip_speed_m_s']<=acceptance.speed_limit_m_s for r in window) if available else None,
            **plain(acceptance),continuous_time_guarantee=False,
            max_error_m=max(r['tip_error_m'] for r in window) if available else None,
            max_speed_m_s=max(r['tip_speed_m_s'] for r in window) if available else None),
        updates=len(observations),accepted_plans=sum(o.get('plan_accepted',o.get('optimization_constraint_violation') is not None and
            o['optimization_constraint_violation']<=1e-5 and not o.get('stop_requested',False) and
            not o.get('failure_response_used',False)) for o in observations),
        optimization_status_counts=dict(Counter(o.get('optimization_status') or 'unavailable' for o in observations)),
        raw_termination_counts=dict(Counter(o.get('optimization_raw_status') or 'unavailable' for o in observations)),
        initialization_selected=sum(o.get('optimization_selected_iteration') in (-1,0) for o in observations),
        recovered_plans=sum(o.get('plan_source')=='reintegrated_returned_iterate' for o in observations),
        accepted_noninitialization_plans=sum(bool(o.get('plan_accepted')) and
            (o.get('plan_source')=='reintegrated_returned_iterate' or
             (o.get('optimization_selected_iteration') is not None and o['optimization_selected_iteration']>0)) for o in observations),
        converged_updates=sum(not o['optimization_nonconverged'] for o in observations),
        solver_error_count=sum(o.get('solver_error') is not None for o in observations),
        solver_failure_flags=sum(o['solver_failed'] for o in observations),
        hold_last_responses=sum(o['failure_response_used'] for o in observations),
        maximum_plan_violation=max(values('optimization_constraint_violation'),default=None),
        deadline_misses=sum(o['deadline_missed'] for o in observations),
        mean_update_s=mean('update_wall_s'),per_update_delivery_s=values('update_wall_s'),
        mean_preparation_s=mean('warm_preparation_s'),mean_numerical_solve_s=mean('optimization_solve_s'),
        mean_validation_s=mean('plan_validation_s'),solver_construction_s=sum(values('solver_construction_s')),
        mean_recovery_s=mean('recovery_wall_s'),mean_recovery_integration_s=mean('recovery_integration_s'),
        mean_recovery_validation_s=mean('recovery_validation_s'),
        graph_construction_s=observations[0]['graph_construction_s'] if observations else None,
        backend_timings_s=result['data']['data']['timings_s'],
        tension_range_n=[float(tensions.min()),float(tensions.max())] if rows else None,
        force_bound_violation_n=float(max(0.,np.max(-tensions),np.max(tensions-np.asarray(limits)))) if rows else None,
        max_projection_residual_rad_m=max(values('gvs_projection_residual_max_rad_m'),default=None),
        max_rate_projection_residual_rad_m_s=max((r['rate_projection_residual_rad_m_s'] for r in motion),default=None),
        max_sampled_contacts=max((r['contacts'] for r in motion),default=None),
        real_time_demonstrated=bool(complete and observations and all(not o['deadline_missed'] for o in observations)))
    if tracking:
        summary.pop('sampled_settling')
        summary['execution_failure_reason']=result['data']['data'].get('reason')
        summary['evaluation_reason']=None if evaluation is None else evaluation.get('reason')
        summary['constraints']=[] if evaluation is None else evaluation['constraints']
        summary['tracking']=dict(reference=task.goal.data,scoring_interval_s=list(task.sampling.window_s),
            acceptance=plain(task.evaluator.parameters),metrics=[] if evaluation is None else evaluation['metrics'],
            rule='All inclusive uniform samples in scoring interval; arithmetic RMS; max <= declared limit. Complete grid required. Terminal error is at execution endpoint.',
            velocity_error_max_m_s=max((r['velocity_error_m_s'] for r in motion),default=None),continuous_time_guarantee=False)
        comparisons=[]
        for observation in observations:
            pred=observation.get('one_step_prediction')
            if pred is None:continue
            following=next((r for r in rows if abs(r['time_s']-pred['time_s'])<1e-8),None)
            if following is not None:
                comparisons.append(dict(start_s=observation['time_s'],end_s=pred['time_s'],
                    applied_input_difference_n=float(np.max(np.abs(np.asarray(observation['actual_tension_n'])-pred['applied_tension_n']))) if 'actual_tension_n' in observation else None,
                    applied_tension_n=pred['applied_tension_n'],predicted_tip_m=pred['tip_position_m'],measured_tip_m=following['tip_m'],
                    tip_difference_m=float(np.linalg.norm(np.asarray(pred['tip_position_m'])-following['tip_m']))))
        summary['one_step_prediction_comparisons']=comparisons
    return summary



def reconstruct_motion(files, rows, target):
    import mujoco
    from .gvs_projection import project
    from .contracts import ResolvedGVSBasis
    physics=json.loads(files['resolved_physics.json'])
    control=json.loads(files['control_spec.json'])
    basis=ResolvedGVSBasis.model_validate(control['projector']['resolved_basis'])
    model=mujoco.MjModel.from_xml_string(files['robot.xml'].decode('utf8'));data=mujoco.MjData(model)
    ids=[model.joint(j).id for j in physics['dofs']];qi=model.jnt_qposadr[ids];vi=model.jnt_dofadr[ids]
    motion=[]
    for row in rows:
        data.qpos[qi]=row['qpos_rad'];data.qvel[vi]=row['qvel_rad_s'];mujoco.mj_forward(model,data)
        J=np.zeros((3,model.nv));Jr=np.zeros_like(J);mujoco.mj_jacSite(model,data,J,Jr,model.site('tip_site').id)
        projection=project(physics,basis,row['qpos_rad'],row['qvel_rad_s'])
        tracking=isinstance(target,dict)
        if tracking:
            from .tracking import reference_at
            position,velocity=reference_at(target,row['time_s'])
        else:position,velocity=target,np.zeros(3)
        motion.append(dict(velocity_error_m_s=float(np.linalg.norm(J@data.qvel-velocity)),time_s=row['time_s'],tip_speed_m_s=float(np.linalg.norm(J@data.qvel)),
            tip_error_m=float(np.linalg.norm(np.asarray(row['tip_m'])-position)),contacts=int(data.ncon),
            rate_projection_residual_rad_m_s=projection['rate_projection_residual_max_rad_m_s']))
    return motion,physics


def report(ctx,args):
    from .gvs_profile import ProfileOutput
    checked_control(ctx.input)
    def receipt(request,tool):
        row=ctx.store.lookup(ctx.run_id,request)
        value=json.loads(row['receipt']) if row and row['receipt'] else None
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
    if execution_scope(candidate['effective'])!=execution_scope(ctx.input):
        raise ValueError('REPORT_CANDIDATE_SCOPE_MISMATCH')
    bundle=None
    for event in ctx.store.events(ctx.run_id):
        if event['kind']=='simulation' and event['execution_id']==sim['execution_id']:
            for ref in event['outputs']:
                if ref['media_type']=='application/json':
                    value=ctx.artifact(ref)
                    if isinstance(value,dict) and 'files' in value and value.get('result')==sim['output']:
                        bundle=value
    if bundle is None:raise ValueError('SEALED_BACKEND_EXPORTS_REQUIRED')
    files={f['filename']:ctx.store.artifact(f['reference'],raw=True) for f in bundle['files']}
    rows=json.loads(gzip.decompress(files['trajectory.json.gz']))
    observations=json.loads(files['controller_observations.json'])
    motion,physics=reconstruct_motion(files,rows,ctx.input.task.goal.data if ctx.input.task.family=='task.tracking' else ctx.input.task.goal.data['target_m'])
    output=summarize(ctx.input.task,ctx.artifact(sim['output']),plain(evaluation),rows,observations,motion,
        [t['force_limit_n'] for t in physics['tendons']],None if ctx.input.task.family=='task.tracking' else settling_for(ctx.input))
    preparations=[e['outputs'][0] for e in ctx.store.events(ctx.run_id)
        if e['kind']=='control_preparation' and e['execution_id']==sim['execution_id']]
    output.update(task=plain(ctx.input.task),execution_scope=execution_scope(ctx.input),
        control_parameters=plain(ctx.input.policy.controller.parameters),
        numerical_preparation=None if not preparations else ctx.artifact(preparations[-1]))
    output.update(simulation=sim['output'],evaluation=ev['output'],execution_id=sim['execution_id'],
        configuration=metadata['candidate_input'],candidate_id=candidate['candidate_id'],
        simulation_wall_s=sim['charged']['wall_s'] if 'charged' in sim else None,
        motion=plain(ctx.save_artifact(motion,'sampled_backend_motion')))
    # The trusted report validates a predeclared strategy against this new run.
    declared=ctx.store.session(ctx.run_id)['state'].get('control_profile_strategy')
    if declared:
        from tools.platform_skills import library
        from tools.skill_policy import strategy_hash
        from schemas.skill import SkillValidationEvidence
        skill=library(ctx.host).get(declared['skill_ref'])
        if strategy_hash(skill)!=declared['strategy_sha256']:
            raise ValueError('DECLARED_STRATEGY_CHANGED')
        worked=bool(output['valid_complete_execution'] and output['official_task_success'] and
            output['accepted_plans']==output['updates'] and output['hold_last_responses']==0)
        validation=SkillValidationEvidence(**declared,run_id=ctx.run_id,worked=worked,
            summary='Trusted public frozen-task reach and plan acceptance check; settling and real-time results remain separate. No causal or transfer claim.')
        output['strategy_validation']=plain(ctx.save_artifact(validation,'skill_validation_experiment'))
        output['strategy_worked']=worked
    return ProfileOutput(detail=output)


def markdown(summary):
    s=summary
    if 'tracking' in s:
        from .delivery_facts import tracking_facts
        facts = s.get('factual_result') or tracking_facts(s)
        return ('# Public GVS tracking result\n\nProgram-generated factual result:\n\n```json\n'+
            json.dumps(facts,indent=2)+'\n```\n\nSampled simulation acceptance; provider reasoning and its review are separate.\n')
    settling=s['sampled_settling']
    return ('# Public GVS NMPC result\n\n'
        f"Complete execution: {s['complete']}; valid: {s['evaluation_validity']}; official task success: {s['official_task_success']}.\n\n"
        f"Terminal error: {s['terminal_error_m']} m; sampled settling: {settling['passed']} (available: {settling['available']}).\n\n"
        f"Accepted plans: {s['accepted_plans']}/{s['updates']}; converged: {s['converged_updates']}; initialization selected: {s['initialization_selected']}; hold-last responses: {s['hold_last_responses']}.\n\n"
        f"Raw termination counts: {s['raw_termination_counts']}.\n\n"
        f"Mean delivered update: {s['mean_update_s']} s; preparation: {s['mean_preparation_s']} s; numerical solve: {s['mean_numerical_solve_s']} s; validation: {s['mean_validation_s']} s. Deadline misses: {s['deadline_misses']}/{s['updates']}.\n\n"
        f"Sampled acceptance: last {settling['window_s']} s, position <= {settling['position_limit_m']} m, speed <= {settling['speed_limit_m_s']} m/s.\n\n"
        'One frozen free-reach simulation with ideal tendon tensions. No actuator, contact, robustness or global stability claim. Settling checks are sampled.\n')
