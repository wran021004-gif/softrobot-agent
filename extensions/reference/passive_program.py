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


def qualification(rows,rule,*,disabled_limits=()):
    selected=window_rows(rows,rule.window_s)
    if not selected:return dict(passed=False,reason='QUALIFICATION_WINDOW_MISSING',checks={})
    positions=np.asarray([r['material_positions_m']+[r['tip_m']] for r in selected])
    drift=float(np.max(np.linalg.norm(positions-positions[0],axis=2)))
    checks=dict(tip_speed=max(np.linalg.norm(r['tip_velocity_m_s']) for r in selected)<=rule.tip_speed_max_m_s,
        monitor_speed=max(np.max(np.linalg.norm(r['material_velocities_m_s'],axis=1)) for r in selected)<=rule.monitor_speed_max_m_s,
        qvel=max(max(abs(v) for v in r['qvel_rad_s']) for r in selected)<=rule.qvel_max_rad_s,
        tail_drift=drift<=rule.tail_drift_max_m,
        static_balance=max(r['static_balance_inf_nm'] for r in selected)<=rule.static_balance_max_nm,
        length_excess=max(max([0.]+[v for i,v in enumerate(r['length_residual_m']) if i not in disabled_limits]) for r in selected)<=rule.length_excess_max_m,
        no_contacts=all(r['ncon']==0 for r in selected),no_warnings=all(not any(w['number'] for w in r['warnings']) for r in selected))
    if rule.initial_lateral_max_m is not None:
        checks['initial_lateral']=float(np.max(np.linalg.norm(positions[-1,:,:2],axis=1)))<=rule.initial_lateral_max_m
    return dict(passed=bool(all(checks.values())),checks={k:bool(v) for k,v in checks.items()},window_s=list(rule.window_s),
        drift_m=drift,sampling=rule.sampling,scope='Measured finite unloaded/stage window; no general stability proof')
