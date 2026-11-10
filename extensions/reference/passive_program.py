"""Finite passive program validation, force sampling and measured qualification.

No integration, control channel, Store, optimizer or benchmark-specific runner.
"""
import numpy as np


def validate_program(task,goal,bounds,problem):
    dt=task.timing.timestep_s;sample=task.timing.sample_period_s;duration=task.timing.duration_s
    def grid(t,period):
        if abs(t/period-round(t/period))>1e-8:raise ValueError('PASSIVE_PROGRAM_REQUIRES_INTEGRATION_AND_SAMPLE_GRID')
    grid(sample,dt);grid(duration,sample)
    for case,stages in goal.programs.items():
        if stages[-1].end_s!=duration:raise ValueError('COMPLETE_PASSIVE_PROGRAM_TIME_COVERAGE_REQUIRED')
        names={s.name:s for s in stages}
        for stage in stages:
            for t in (stage.start_s,stage.end_s,stage.ramp_until_s,*stage.observation_window_s,*stage.scoring_window_s):
                grid(t,dt);grid(t,sample)
        for q in goal.qualifications:
            if q.stage not in names:raise ValueError('QUALIFICATION_STAGE_MISSING')
            stage=names[q.stage]
            if not stage.start_s<=q.window_s[0]<q.window_s[1]<=stage.end_s:raise ValueError('QUALIFICATION_WINDOW_OUTSIDE_STAGE')
            if q.window_s[1]!=stage.end_s:raise ValueError('QUALIFICATION_MUST_END_AT_ITS_STATE_BOUNDARY')
            for t in q.window_s:grid(t,sample)
        for bound in bounds.bounds:
            if bound.load_condition!=case:continue
            if bound.window not in names or bound.reference_window not in names:raise ValueError('FROZEN_RESPONSE_WINDOW_REQUIRED')
            if bound.material_s not in problem.monitor_s:raise ValueError('FROZEN_MATERIAL_MONITOR_REQUIRED')
        for stiffness in bounds.progressive_stiffness:
            if stiffness.load_condition==case and (any(s not in names for s in (*stiffness.stages,stiffness.reference_stage)) or stiffness.material_s not in problem.monitor_s):
                raise ValueError('FROZEN_STIFFNESS_STAGES_AND_MATERIAL_POINT_REQUIRED')
    if any(b.load_condition not in goal.load_conditions for b in bounds.bounds) or set(b.load_condition for b in bounds.bounds)!=set(goal.load_conditions):
        raise ValueError('EVERY_PASSIVE_EPISODE_REQUIRES_BOUNDS')
    if any(s.load_condition not in goal.load_conditions for s in bounds.progressive_stiffness):raise ValueError('UNKNOWN_STIFFNESS_EPISODE')
    if bounds.mechanism and goal.allowed_ablation=='none':raise ValueError('FROZEN_MECHANISM_INTERVENTION_REQUIRED')
    if bounds.numerical_confirmation:
        if (goal.execution_protocol!='hard_equilibrium_continuous_v1' or not bounds.mechanism
                or goal.recording!='full_physics_csv' or goal.route_check!='every_physics_step'
                or dt not in (bounds.numerical_confirmation.half_timestep_s,2*bounds.numerical_confirmation.half_timestep_s)):
            raise ValueError('COMPLETE_HARD_EQUILIBRIUM_NUMERICAL_CONFIRMATION_REQUIRED')


def force_at(goal,case,time_s):
    stages=goal.programs[case]
    if time_s<0 or time_s>stages[-1].end_s+1e-10:raise ValueError('TIME_OUTSIDE_FROZEN_PASSIVE_PROGRAM')
    stage=next((s for s in stages if time_s<=s.end_s+1e-12),stages[-1])
    if stage.interpolation=='hold':alpha=1.
    else:
        alpha=float(np.clip((time_s-stage.start_s)/(stage.ramp_until_s-stage.start_s),0.,1.))
        if stage.interpolation=='smoothstep':alpha=alpha*alpha*(3-2*alpha)
    force=np.asarray(stage.force_start_world_n)+(np.asarray(stage.force_end_world_n)-stage.force_start_world_n)*alpha
    return force.tolist(),stage.name


def window_rows(rows,window):
    return [r for r in rows if window[0]-1e-10<=r['time_s']<=window[1]+1e-10]


def confirmation_task(task,variant):
    """The only permitted numerical changes to the frozen physical task."""
    from schemas.platform import TaskDefinition
    value=task.model_dump(mode='json');spec=value['evaluator']['parameters']['data']['numerical_confirmation']
    if variant=='half_timestep':value['timing']['timestep_s']=spec['half_timestep_s']
    elif variant=='initial_perturbation':value['goal']['data']['initial_perturbation_rad']=spec['perturbation_rad']
    else:raise ValueError('UNKNOWN_PASSIVE_CONFIRMATION_VARIANT')
    return TaskDefinition.model_validate(value)


def qualification(rows,rule,*,disabled_limits=()):
    selected=window_rows(rows,rule.window_s)
    if not selected:return dict(passed=None,reason='QUALIFICATION_WINDOW_MISSING',checks={})
    positions=np.asarray([r['material_positions_m']+[r['tip_m']] for r in selected])
    drift=float(np.max(np.linalg.norm(positions-positions[0],axis=2)))
    checks=dict(tip_speed=max(np.linalg.norm(r['tip_velocity_m_s']) for r in selected)<=rule.tip_speed_max_m_s,
        monitor_speed=max(np.max(np.linalg.norm(r['material_velocities_m_s'],axis=1)) for r in selected)<=rule.monitor_speed_max_m_s,
        qvel=max(max(abs(v) for v in r['qvel_rad_s']) for r in selected)<=rule.qvel_max_rad_s,
        tail_drift=drift<=rule.tail_drift_max_m,
        static_balance=max(r['static_balance_inf_nm'] for r in selected)<=rule.static_balance_max_nm,
        length_excess=max(max([0.]+[v for i,v in enumerate(r['length_residual_m']) if i not in disabled_limits]) for r in selected)<=rule.length_excess_max_m,
        no_contacts=all(r['ncon']==0 for r in selected),no_warnings=all(not any(w['number'] for w in r['warnings']) for r in selected))
    diagnostics={}
    if rule.qvel_role=='diagnostic':diagnostics['qvel']=checks.pop('qvel')
    speed_covers_drift=(rule.sampling=='every_physics_step' and
        len(selected)>1 and selected[0]['time_s']==rule.window_s[0] and selected[-1]['time_s']==rule.window_s[1] and
        (rule.window_s[1]-rule.window_s[0])*max(rule.tip_speed_max_m_s,rule.monitor_speed_max_m_s)<=rule.tail_drift_max_m)
    if rule.drift_role=='speed_covered_diagnostic' and speed_covers_drift:diagnostics['tail_drift']=checks.pop('tail_drift')
    if rule.initial_lateral_max_m is not None:
        checks['initial_lateral']=float(np.max(np.linalg.norm(positions[-1,:,:2],axis=1)))<=rule.initial_lateral_max_m
    result=dict(passed=bool(all(checks.values())),checks={k:bool(v) for k,v in checks.items()},window_s=list(rule.window_s),
        drift_m=drift,sampling=rule.sampling,scope='Measured finite unloaded/stage window; no general stability proof')
    if rule.qvel_role=='diagnostic' or rule.drift_role!='qualification':
        result.update(diagnostic_checks=diagnostics,observed=dict(
            tip_speed_m_s=float(max(np.linalg.norm(r['tip_velocity_m_s']) for r in selected)),
            monitor_speed_m_s=float(max(np.max(np.linalg.norm(r['material_velocities_m_s'],axis=1)) for r in selected)),
            qvel_rad_s=max(max(abs(v) for v in r['qvel_rad_s']) for r in selected),
            static_balance_inf_nm=max(r['static_balance_inf_nm'] for r in selected),
            generalized_force_scale_nm=max((r['generalized_force_scale_nm'] for r in selected if r.get('generalized_force_scale_nm') is not None),default=None),
            normalized_static_balance=max((r['normalized_static_balance'] for r in selected if r.get('normalized_static_balance') is not None),default=None)),
            static_balance_calibration='incomplete; original absolute threshold retained')
    return result


def execution_scope(task,profile=None):
    """Resolve request scope without changing the one frozen TaskDefinition."""
    from .contracts import PassiveExecutionProfile,PassiveResponseGoalV2
    goal=PassiveResponseGoalV2.model_validate(task.goal.data)
    q=PassiveExecutionProfile.model_validate(profile or dict(purpose='final_acceptance'))
    final=q.purpose=='final_acceptance'
    if final and any((q.load_conditions,q.stage_prefix,q.observation_window_s,q.sample_period_s,q.route_sampling,q.recording,q.requested_observables)):
        raise ValueError('FINAL_ACCEPTANCE_REQUIRES_COMPLETE_FROZEN_PROTOCOL')
    observables={o.name for o in task.observations}
    observables.update(b[key] for b in task.evaluator.parameters.data['bounds'] for key in ('name','quantity'))
    observables.update(('tip_position','tip_velocity','material_position','material_velocity','joint_position','joint_velocity',
        'tendon_length','tendon_tension','length_residual','stiffness_ratio','slack_to_taut','tendon_transitions','stage_qualification'))
    if set(q.requested_observables)-observables:raise ValueError('UNREGISTERED_REQUESTED_OBSERVABLE')
    cases=q.load_conditions or goal.load_conditions
    if len(set(cases))!=len(cases) or not set(cases)<=set(goal.load_conditions):raise ValueError('SELECT_FROZEN_LOAD_CONDITIONS')
    ends={}
    for case in cases:
        stages=goal.programs[case]
        if q.stage_prefix and q.stage_prefix not in [s.name for s in stages]:raise ValueError('UNKNOWN_STAGE_PREFIX')
        ends[case]=next(s.end_s for s in stages if s.name==q.stage_prefix) if q.stage_prefix else stages[-1].end_s
    period=q.sample_period_s or task.timing.sample_period_s
    dt=task.timing.timestep_s
    if abs(period/dt-round(period/dt))>1e-8 or period<task.timing.sample_period_s or any(abs(t/period-round(t/period))>1e-8 for t in ends.values()):
        raise ValueError('OBSERVATION_PERIOD_REQUIRES_ALIGNED_COARSER_GRID')
    window=q.observation_window_s
    if window and not 0<=window[0]<window[1]<=min(ends.values()):raise ValueError('OBSERVATION_WINDOW_OUTSIDE_EXECUTED_PREFIX')
    return dict(purpose=q.purpose,load_conditions=list(cases),stage_prefix=q.stage_prefix,end_s=ends,
        observation_window_s=list(window) if window else None,sample_period_s=period,
        route_sampling=q.route_sampling or (goal.route_check if final else 'score_grid'),
        recording=q.recording or (goal.recording if final else 'sampled'),
        requested_observables=q.requested_observables,fidelity=q.fidelity,
        acceptance_status='not_evaluated' if not final else 'pending')


def execution_identity(configuration,*,profile=None,execution_checks='full',intervention=(),initial_state=None):
    """Exact physical calculation identity, shared by admission, Worker and Store reuse."""
    from importlib.metadata import version
    import os,sys
    from schemas.platform import TaskDefinition
    from tools.state_io import digest
    from tools.research.state import science_hashes
    task=configuration['task'];policy=configuration['policy']
    scope=execution_scope(TaskDefinition.model_validate(task),profile) if task['goal']['data'].get('version')=='passive_response_v2' else None
    if scope and profile is None and execution_checks=='screening':scope.update(purpose='exploration',route_sampling='score_grid',acceptance_status='not_evaluated')
    fields=dict(version='physical_execution_identity_v1',task_identity=digest(task),design_identity=digest(configuration['robot']),
        model_backend={k:policy[k] for k in ('backend','dynamics_model','discretization')},
        implementation=science_hashes(),runtime=dict(mujoco=version('mujoco'),numpy=version('numpy'),scipy=version('scipy'),python=sys.version,
            threads={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}),
        solver_configuration=dict(timing=task['timing'],static=task['goal']['data'].get('unloaded_static_solver'),
            passive_limits={k:task['goal']['data'].get(k) for k in ('solreflimit','solimplimit')}),
        initial_state_identity=digest(initial_state if initial_state is not None else task['initializer']),
        scope=scope,execution_checks=execution_checks,intervention=sorted(intervention),seed=configuration.get('seed'))
    return dict(identity=digest(fields),fields=fields)
