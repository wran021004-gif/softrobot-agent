"""Frozen dynamic task validation and independent evaluation of measured samples.

No equilibrium solve, controller, integration, Store or acceptance state machine.
"""
import numpy as np
from schemas.platform import EvaluationResult, Metric, ConstraintResult
from .contracts import PassiveResponseGoal, PassiveResponseEvaluation


def task_definition(task, reg):
    from extensions.tendon_family.contracts import ConstrainedPhysicalProblem
    from extensions.experiment_dynamics.contracts import Assembly
    from extensions.tendon_family.compiler import quat
    if (task.goal.contract!='reference.passive_response_goal' or
            task.evaluator.extension_id!='evaluate.passive_response' or
            task.evaluator.parameters.contract!='reference.passive_response_evaluation' or
            task.actuator_channels or task.initializer.extension_id!='initialize.family'):
        raise ValueError('PASSIVE_TASK_BINDINGS_REQUIRED')
    goal=PassiveResponseGoal.model_validate(task.goal.data)
    bounds=PassiveResponseEvaluation.model_validate(task.evaluator.parameters.data)
    problem=ConstrainedPhysicalProblem.model_validate(task.physical_problem)
    assembly=Assembly.model_validate(task.environment.data)
    loads={v.name:v for v in problem.loads}
    if (set(goal.load_conditions)!=set(loads)-{problem.baseline_load} or
            any(loads[problem.baseline_load].force_world_n) or
            any(b.load_condition not in goal.load_conditions or b.material_s not in problem.monitor_s for b in bounds.bounds)):
        raise ValueError('FROZEN_PASSIVE_LOADS_AND_MONITORS_REQUIRED')
    if set(goal.load_conditions)!={b.load_condition for b in bounds.bounds}:
        raise ValueError('EVERY_LOAD_REQUIRES_FROZEN_BOUNDS')
    if (not np.allclose(problem.mount_rotation,quat(assembly.mount.quaternion_wxyz),rtol=0,atol=1e-12) or
            tuple(problem.mount_position)!=assembly.mount.position_m or tuple(problem.gravity)!=assembly.environment.gravity_m_s2 or
            assembly.external_forces):
        raise ValueError('PASSIVE_PHYSICAL_PROBLEM_AND_ASSEMBLY_MISMATCH')
    timing=task.timing
    if goal.hold_window_s[1]!=timing.duration_s:
        raise ValueError('PASSIVE_HOLD_MUST_COVER_TASK_ENDPOINT')
    for t in [goal.unloaded_until_s,goal.ramp_until_s,*goal.hold_window_s]:
        if abs(t/timing.sample_period_s-round(t/timing.sample_period_s))>1e-8:
            raise ValueError('PASSIVE_WINDOWS_REQUIRE_SAMPLE_GRID')
    if abs(timing.duration_s/timing.sample_period_s-round(timing.duration_s/timing.sample_period_s))>1e-8:
        raise ValueError('PASSIVE_COMPLETE_SAMPLE_GRID_REQUIRED')
    return goal,bounds,problem


def load_at(goal, load, time_s):
    alpha=float(np.clip((time_s-goal.unloaded_until_s)/(goal.ramp_until_s-goal.unloaded_until_s),0.,1.))
    return (np.asarray(load.force_world_n)*alpha).tolist(),('unloaded' if time_s<=goal.unloaded_until_s else
        'ramp' if time_s<goal.ramp_until_s else 'hold')


def inspect_evidence(task, raw):
    """Validate complete local clocks, shapes, loads and measured engine state."""
    from tools.state_io import digest
    goal=PassiveResponseGoal.model_validate(task.goal.data)
    problem=task.physical_problem
    source=raw.get('physical_binding',{})
    if (raw.get('kind')!='passive_dynamic_execution_v1' or source.get('task_identity')!=digest(task.model_dump(mode='json')) or
            raw.get('active_actuators')!=0 or not source.get('model_identity') or not source.get('design_identity')):
        return 'invalid','PASSIVE_EXECUTION_SOURCE_MISMATCH'
    if raw.get('numerical_failure'):
        return 'invalid','MUJOCO_NUMERICAL_FAILURE'
    episodes=raw.get('episodes',[])
    if len(episodes)!=len(goal.load_conditions) or [e.get('load_condition') for e in episodes]!=goal.load_conditions:
        return 'incomplete','REQUIRED_LOAD_CASE_MISSING'
    count=round(task.timing.duration_s/task.timing.sample_period_s)
    expected=np.arange(count+1)*task.timing.sample_period_s
    loads={v['name']:v for v in problem['loads']}
    total_steps=round(task.timing.duration_s/task.timing.timestep_s)
    n=raw.get('joint_count',0);nt=len(raw.get('tendon_order',[]));nm=len(problem['monitor_s'])
    if n<=0 or nt<=0:return 'invalid','MISSING_MODEL_DIMENSIONS'
    for episode in episodes:
        rows=episode.get('samples',[])
        if (not episode.get('complete') or len(rows)!=count+1 or episode.get('physics_steps')!=total_steps or
                not np.allclose([r.get('time_s',-1) for r in rows],expected,rtol=0,atol=1e-10)):
            return 'incomplete','COMPLETE_DYNAMIC_GRID_REQUIRED'
        if episode.get('checked_physics_steps')!=total_steps:
            return 'incomplete','PER_STEP_SAFETY_COVERAGE_REQUIRED'
        if episode.get('initial_state')!=raw.get('initial_state'):
            return 'invalid','RESET_STATE_MISMATCH'
        try:
            for row in rows:
                shapes=dict(qpos_rad=(n,),qvel_rad_s=(n,),tip_m=(3,),tip_velocity_m_s=(3,),
                    material_positions_m=(nm,3),material_velocities_m_s=(nm,3),tendon_length_m=(nt,),
                    length_residual_m=(nt,),actual_tension_n=(nt,),force_world_n=(3,))
                for field,shape in shapes.items():
                    a=np.asarray(row[field],dtype=float)
                    if a.shape!=shape or not np.isfinite(a).all():return 'invalid','NONFINITE_OR_MALFORMED_PHYSICAL_STATE'
                from types import SimpleNamespace
                expected_force,phase=load_at(goal,SimpleNamespace(**loads[episode['load_condition']]),row['time_s'])
                if phase!=row['phase'] or not np.allclose(row['force_world_n'],expected_force,rtol=0,atol=1e-12):
                    return 'invalid','FROZEN_FORCE_PROTOCOL_MISMATCH'
                if abs(row['engine_time_s']-row['time_s'])>1e-9:return 'invalid','ENGINE_CLOCK_MISMATCH'
                if not np.allclose(np.asarray(row['tendon_length_m'])-raw['payout_lengths_m'],row['length_residual_m'],rtol=0,atol=1e-12):
                    return 'invalid','MEASURED_LENGTH_RESIDUAL_MISMATCH'
                if min(row['actual_tension_n'])<0:return 'invalid','UNILATERAL_TENSION_SIGN_MISMATCH'
                if any(w['number'] for w in row['warnings']):return 'invalid','MUJOCO_WARNING'
                if not isinstance(row['ncon'],int) or row['solver_iterations']<0:return 'invalid','SOLVER_STATE_MISSING'
            if (rows[0]['qpos_rad']!=raw['initial_state']['qpos_rad'] or
                    rows[0]['qvel_rad_s']!=raw['initial_state']['qvel_rad_s']):return 'invalid','RESET_STATE_MISMATCH'
        except (KeyError,TypeError,ValueError):
            return 'incomplete','REQUIRED_MEASUREMENTS_MISSING'
    if raw.get('physics_steps')!=len(episodes)*total_steps:return 'incomplete','PHYSICS_COST_OR_EPISODE_COVERAGE_MISMATCH'
    return 'valid',None


def reduce_vector(bound, vector):
    if bound.reduction=='component':return float(np.asarray(bound.direction_world)@vector)
    if bound.reduction=='projection_norm':return float(np.linalg.norm(np.asarray(bound.projection_world)@vector))
    return float(np.linalg.norm(vector))


def evaluate(task, result, source, reg, identity):
    goal,bounds,problem=task_definition(task,reg)
    raw=result.data.data
    validity,reason=inspect_evidence(task,raw)
    if result.solver_status!='completed' and validity=='valid':validity,reason='incomplete','BACKEND_EXECUTION_NOT_COMPLETED'
    kwargs=dict(source=source,evaluator=task.evaluator.extension_id,evaluator_version=task.evaluator.version,
        comparison_identity=identity)
    if validity!='valid':return EvaluationResult(validity=validity,task_success=None,metrics=[],constraints=[],reason=reason,**kwargs)
    metrics=[];constraints=[]
    for b in bounds.bounds:
        rows=next(e['samples'] for e in raw['episodes'] if e['load_condition']==b.load_condition)
        baseline=next(r for r in rows if abs(r['time_s']-goal.unloaded_until_s)<1e-10)
        selected=[r for r in rows if (b.window=='full' or b.window=='unloaded' and r['time_s']<=goal.unloaded_until_s+1e-10 or
            b.window=='hold' and goal.hold_window_s[0]-1e-10<=r['time_s']<=goal.hold_window_s[1]+1e-10)]
        values=[]
        for row in selected:
            i=problem.monitor_s.index(b.material_s)
            point=reduce_vector(b,np.asarray(row['material_positions_m'][i])-baseline['material_positions_m'][i])
            tip=reduce_vector(b,np.asarray(row['tip_m'])-baseline['tip_m'])
            if b.quantity=='displacement_ratio' and point==0:
                return EvaluationResult(validity='invalid',task_success=None,metrics=[],constraints=[],reason='ZERO_DISPLACEMENT_RATIO_DENOMINATOR',**kwargs)
            value={'material_displacement':lambda:point,'tip_displacement':lambda:tip,
                'displacement_difference':lambda:tip-b.material_scale*point,'displacement_ratio':lambda:tip/point,
                'maximum_tension':lambda:max(row['actual_tension_n']),
                'maximum_length_excess':lambda:max(0.,max(row['length_residual_m'])),
                'material_speed':lambda:reduce_vector(b,np.asarray(row['material_velocities_m_s'][i])),
                'tip_speed':lambda:reduce_vector(b,np.asarray(row['tip_velocity_m_s'])),
                'unloaded_tip_drift':lambda:reduce_vector(b,np.asarray(row['tip_m'])-rows[0]['tip_m']),
                'maximum_joint_position':lambda:max(abs(v) for v in row['qpos_rad']),
                'maximum_joint_speed':lambda:max(abs(v) for v in row['qvel_rad_s'])}[b.quantity]()
            values.append(value)
        if b.window=='full' and b.quantity in ('maximum_tension','maximum_length_excess'):
            episode=next(e for e in raw['episodes'] if e['load_condition']==b.load_condition)
            field='maximum_tension_n' if b.quantity=='maximum_tension' else 'maximum_length_excess_m'
            if field not in episode:
                return EvaluationResult(validity='incomplete',task_success=None,metrics=[],constraints=[],reason='PER_STEP_CONSTRAINT_EXTREMA_MISSING',**kwargs)
            values.append(episode[field])
        if not np.isfinite(values).all():
            return EvaluationResult(validity='invalid',task_success=None,metrics=[],constraints=[],reason='NONFINITE_DYNAMIC_METRIC',**kwargs)
        for suffix,limit,value,satisfied in [('minimum',b.minimum,min(values),b.minimum is None or min(values)>=b.minimum),
                ('maximum',b.maximum,max(values),b.maximum is None or max(values)<=b.maximum)]:
            if limit is None:continue
            name=b.name+'_'+suffix
            metrics.append(Metric(name=name,value=value,units=b.physical_unit))
            constraints.append(ConstraintResult(name=name,satisfied=satisfied,observed=value,limit=limit,units=b.physical_unit))
    if bounds.prohibit_contact:
        maximum=max(e['maximum_contacts'] for e in raw['episodes'])
        metrics.append(Metric(name='maximum_contacts',value=maximum,units='count'))
        constraints.append(ConstraintResult(name='no_contact',satisfied=maximum==0,observed=maximum,limit=0,units='count'))
    return EvaluationResult(validity='valid',task_success=all(c.satisfied for c in constraints),metrics=metrics,constraints=constraints,**kwargs)
