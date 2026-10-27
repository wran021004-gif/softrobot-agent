"""Independent Reach and geometric path task definitions and saved-data evaluators."""
import math
from schemas.platform import SignalSpec,EvaluationResult,Metric,ConstraintResult
from extensions.reference.contracts import Empty
def reach_task(task, reg):
    from extensions.reference.contracts import ReachGoal, ReachEvaluation
    if type(reg.parse(task.goal)) is not ReachGoal or type(reg.parse(task.evaluator.parameters)) is not ReachEvaluation:
        raise ValueError('REACH_GOAL_OR_EVALUATOR_CONTRACT_MISMATCH')
    if task.evaluator.extension_id != 'evaluate.reach':
        raise ValueError('REACH_EVALUATOR_REQUIRED')
    required = [SignalSpec(name='tip_position', entity='tip', dimension=3, units='m', frame='world', phase=phase)
                for phase in ('post_step', 'sampled_state')]
    if not any(spec in task.observations for spec in required):
        raise ValueError('REQUIRED_SIGNAL: tip_position, tip, dimension=3, m, world, declared state phase')
    if task.environment.contract!='experiment.assembly':
        raise ValueError('REACH_ENVIRONMENT_ADAPTER_REQUIRED')
    expected_initializers = ('initialize.family',)
    if task.initializer.extension_id not in expected_initializers:
        raise ValueError('REACH_INITIALIZER_ADAPTER_REQUIRED')
    if any(o.metric != 'position_error' or o.units != 'm' for o in task.objectives):
        raise ValueError('EVALUATOR_METRIC_OR_UNIT_UNAVAILABLE')
    return Empty()


def tool_axis_task(task,reg):
    from extensions.reference.contracts import ToolAxisGoal,ToolAxisEvaluation
    if (type(reg.parse(task.goal)) is not ToolAxisGoal
            or type(reg.parse(task.evaluator.parameters)) is not ToolAxisEvaluation
            or task.evaluator.extension_id!='evaluate.position_tool_axis'):
        raise ValueError('TOOL_AXIS_GOAL_OR_EVALUATOR_MISMATCH')
    required=[SignalSpec(name=n,entity='tip',dimension=3,units=u,frame='world',phase='post_step')
        for n,u in (('tip_position','m'),('tip_tool_axis','1'))]
    if len(task.observations)!=2 or any(task.observations.count(s)!=1 for s in required):
        raise ValueError('TOOL_AXIS_REQUIRES_POSITION_AND_UNIT_AXIS_WORLD_POST_STEP')
    dt=task.timing.sample_period_s
    if (task.environment.contract!='experiment.assembly' or task.initializer.extension_id!='initialize.family'
            or task.sampling.window_s[0]<dt or any(abs(t/dt-round(t/dt))>1e-8 for t in task.sampling.window_s)):
        raise ValueError('TOOL_AXIS_REQUIRES_FAMILY_SCENE_AND_INCLUSIVE_POST_STEP_WINDOW')
    units=dict(max_position_error='m',max_tool_axis_angle_error='rad')
    if any(units.get(o.metric)!=o.units for o in task.objectives):
        raise ValueError('TOOL_AXIS_METRIC_OR_UNIT_UNAVAILABLE')
    return Empty()


def tool_axis_angles(axes,target):
    """True directed-axis angle in rad; rotation about that axis is unconstrained."""
    import numpy as np
    axes=np.asarray(axes,dtype=float);target=np.asarray(target,dtype=float)
    if (axes.ndim!=2 or axes.shape[1]!=3 or target.shape!=(3,) or not np.isfinite(axes).all()
            or not np.isfinite(target).all() or abs(np.linalg.norm(target)-1)>1e-10
            or not np.allclose(np.linalg.norm(axes,axis=1),1,rtol=0,atol=1e-9)):
        raise ValueError('FINITE_UNIT_WORLD_TOOL_AXIS_SIGNALS_REQUIRED')
    return np.arccos(np.clip(axes@target,-1.,1.))


def evaluate_tool_axis(task,result,source,reg,identity):
    import numpy as np
    tool_axis_task(task,reg)
    common=dict(source=source,evaluator=task.evaluator.extension_id,evaluator_version=task.evaluator.version,comparison_identity=identity)
    def unavailable(validity,reason):
        return EvaluationResult(validity=validity,task_success=None,metrics=[],constraints=[],reason=reason,**common)
    if result.solver_status!='completed':return unavailable('incomplete','SOLVER_NOT_COMPLETE')
    dt=task.timing.sample_period_s;expected=np.arange(1,round(task.timing.duration_s/dt)+1)*dt
    found={}
    for spec in task.observations:
        rows=[s for s in result.signals if s.spec.name==spec.name]
        if not rows:return unavailable('incomplete','MISSING_'+spec.name)
        if len(rows)!=1 or rows[0].spec!=spec:return unavailable('invalid','TOOL_AXIS_SIGNAL_CONTRACT_MISMATCH')
        signal=rows[0]
        if len(signal.times_s)!=len(expected):return unavailable('incomplete','INCOMPLETE_TOOL_AXIS_SAMPLING')
        if not np.allclose(signal.times_s,expected,rtol=0,atol=1e-12):return unavailable('invalid','TOOL_AXIS_TIME_GRID_MISMATCH')
        found[spec.name]=np.asarray(signal.values)
    goal=reg.parse(task.goal);limits=reg.parse(task.evaluator.parameters)
    try:angles=tool_axis_angles(found['tip_tool_axis'],goal.target_axis_world)
    except ValueError as exc:return unavailable('invalid',str(exc))
    lo,hi=task.sampling.window_s;scored=(expected>=lo-1e-12)&(expected<=hi+1e-12)
    position=float(max(np.linalg.norm(found['tip_position'][scored]-goal.target_m,axis=1)))
    angle=float(max(angles[scored]))
    values=[('tool_position','max_position_error',position,limits.position_tolerance_m,'m'),
        ('tool_axis_direction','max_tool_axis_angle_error',angle,limits.angle_tolerance_rad,'rad')]
    return EvaluationResult(validity='valid',task_success=all(v<=limit for _,_,v,limit,_ in values),
        metrics=[Metric(name=n,value=v,units=u) for _,n,v,_,u in values],
        constraints=[ConstraintResult(name=n,satisfied=v<=limit,observed=v,limit=limit,units=u) for n,_,v,limit,u in values],**common)

def evaluate_signals(task, result, source, reg, comparison_identity, mode):
    if result.solver_status != 'completed':
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
            evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity, reason='SOLVER_NOT_COMPLETE')
    signal_name = 'tip_position' if mode == 'reach' else 'tendon_length'
    spec = next(s for s in task.observations if s.name == signal_name)
    signal = next((s for s in result.signals if s.spec == spec), None)
    if signal is None or not signal.times_s or abs(signal.times_s[-1] - task.timing.duration_s) > 1e-8:
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
            evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity, reason='MISSING_SIGNAL_OR_DURATION')
    first = 0 if signal.spec.phase == 'sampled_state' else 1
    if any(abs(t - (i + first) * task.timing.sample_period_s) > 1e-8 for i, t in enumerate(signal.times_s)):
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
            evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity, reason='INCOMPLETE_SAMPLING')
    goal = reg.parse(task.goal)
    params = reg.parse(task.evaluator.parameters)
    if mode == 'reach':
        value = math.dist(signal.values[-1], goal.target_m)
        metrics, limit = [Metric(name='position_error', value=value, units='m')], params.tolerance_m
    else:
        errors = [abs(v[0] - goal.length_m) for t, v in zip(signal.times_s, signal.values)
                  if task.sampling.window_s[0] - 1e-9 <= t <= task.sampling.window_s[1] + 1e-9]
        if not errors:
            raise ValueError('EMPTY_EVALUATION_WINDOW')
        value, limit = max(errors), params.max_deviation_m
        metrics = [Metric(name='max_deviation', value=value, units='m'),
                   Metric(name='rms_deviation', value=math.sqrt(sum(e * e for e in errors) / len(errors)), units='m')]
    return EvaluationResult(validity='valid', task_success=value <= limit, metrics=metrics,
        constraints=[ConstraintResult(name='task_bound', satisfied=value <= limit, observed=value, limit=limit, units='m')],
        source=source, evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity)

def evaluate_reach(task, result, source, reg, identity):
    return evaluate_signals(task, result, source, reg, identity, 'reach')


def tracking_task(task, reg):
    from extensions.reference.contracts import TrackingGoal, TrackingEvaluation
    if (type(reg.parse(task.goal)) is not TrackingGoal
            or type(reg.parse(task.evaluator.parameters)) is not TrackingEvaluation
            or task.evaluator.extension_id!='evaluate.tracking'):
        raise ValueError('TRACKING_GOAL_OR_EVALUATOR_CONTRACT_MISMATCH')
    goal=reg.parse(task.goal)
    if goal.time_requirement=='timed':
        period=task.timing.sample_period_s
        if abs(goal.times_s[-1]-task.timing.duration_s)>1e-12 or abs(task.timing.duration_s/period-round(task.timing.duration_s/period))>1e-8:
            raise ValueError('TIMED_REFERENCE_HORIZON_MISMATCH')
        if task.sampling.window_s[0]<period or any(abs(t/period-round(t/period))>1e-8 for t in task.sampling.window_s):
            raise ValueError('TIMED_WINDOW_REQUIRES_INCLUSIVE_POST_STEP_GRID')
    spec=SignalSpec(name='tip_position',entity='tip',dimension=3,units='m',frame='world',phase='post_step')
    if task.observations.count(spec)!=1:
        raise ValueError('TRACKING_REQUIRES_WORLD_METRE_POST_STEP_TIP_SIGNAL')
    if task.environment.contract!='experiment.assembly' or task.initializer.extension_id!='initialize.family':
        raise ValueError('TRACKING_ENVIRONMENT_OR_INITIALIZER_UNSUPPORTED')
    metrics = {'max_position_error','rms_position_error','terminal_position_error'}
    if goal.time_requirement == 'none':
        metrics.add('path_coverage_error')
    if any(o.metric not in metrics or o.units!='m' for o in task.objectives):
        raise ValueError('TRACKING_METRIC_OR_UNIT_UNAVAILABLE')
    return Empty()


def polyline_samples(vertices,step):
    """Uniform geometric arc-length samples, independent of recording timestamps."""
    import numpy as np
    vertices=np.asarray(vertices,dtype=float)
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(vertices,axis=0),axis=1))]
    # Repeated measured positions are legitimate pauses, not extra path length.
    keep=np.r_[True,np.diff(arc)>0];vertices=vertices[keep];arc=arc[keep]
    if arc[-1]==0:return vertices[:1]
    grid=np.linspace(0.,arc[-1],math.ceil(arc[-1]/step)+1)
    return np.column_stack([np.interp(grid,arc,vertices[:,j]) for j in range(3)])


def project_polyline(points,vertices):
    """Nearest segment distance and deterministic earliest arc-length projection."""
    import numpy as np
    vertices=np.asarray(vertices,dtype=float);points=np.asarray(points,dtype=float)
    legs=np.diff(vertices,axis=0);lengths=np.linalg.norm(legs,axis=1)
    if not np.any(lengths):return np.linalg.norm(points-vertices[0],axis=1),np.zeros(len(points))
    starts=vertices[:-1][lengths>0];legs=legs[lengths>0];lengths=lengths[lengths>0]
    alpha=np.clip(np.einsum('nsi,si->ns',points[:,None,:]-starts,legs)/(lengths**2),0.,1.)
    distances=np.linalg.norm(points[:,None,:]-(starts+alpha[:,:,None]*legs),axis=2)
    choice=np.argmin(distances,axis=1);rows=np.arange(len(points))
    progress=np.r_[0.,np.cumsum(lengths)][choice]+alpha[rows,choice]*lengths[choice]
    return distances[rows,choice],progress


def tracking_condition_specs(task):
    """The registered evaluator's hard conditions, shared with research views."""
    timed = task['goal']['data']['time_requirement'] == 'timed'
    rows = [('tracking_max_error', 'max_position_error',
             'Maximum error against r(t) at every scored post-step sample' if timed else
             'Maximum reference-path distance over measured vertices and arc-length samples')]
    if not timed:
        rows += [
            ('path_coverage', 'path_coverage_error', 'Maximum measured-polyline distance over reference arc-length samples and vertices'),
            ('path_start', None, 'Distance from first measured position to first reference vertex'),
            ('path_end', 'terminal_position_error', 'Distance from last measured position to last reference vertex'),
            ('path_progress_regression', 'progress_regression', 'Maximum running-maximum minus current nearest-path arc-length progress')]
    return [dict(condition_id=name, metric=metric, meaning=meaning,
                 evaluation_binding=dict(source='EvaluationResult', constraint=name, metric=metric),
                 limit=task['evaluator']['parameters']['data']['max_error_m'], units='m')
            for name, metric, meaning in rows]


def evaluate_tracking(task,result,source,reg,identity):
    """Timed r(t) samples or ordered geometric path, using the frozen goal mode."""
    import numpy as np
    tracking_task(task,reg)
    common=dict(source=source,evaluator=task.evaluator.extension_id,
        evaluator_version=task.evaluator.version,comparison_identity=identity)
    def unavailable(validity,reason):
        return EvaluationResult(validity=validity,task_success=None,metrics=[],constraints=[],reason=reason,**common)
    if result.solver_status!='completed':return unavailable('incomplete','SOLVER_NOT_COMPLETE')
    spec=next(s for s in task.observations if s.name=='tip_position')
    signals=[s for s in result.signals if s.spec.name=='tip_position']
    if not signals:return unavailable('incomplete','MISSING_TIP_POSITION')
    if len(signals)!=1 or signals[0].spec!=spec:return unavailable('invalid','TRACKING_SIGNAL_CONTRACT_MISMATCH')
    signal=signals[0]
    if len(signal.values)<2:return unavailable('incomplete','INSUFFICIENT_PATH_SAMPLES')
    goal=reg.parse(task.goal);params=reg.parse(task.evaluator.parameters)
    if goal.time_requirement=='timed':
        dt=task.timing.sample_period_s
        expected=[i*dt for i in range(1,round(task.timing.duration_s/dt)+1)]
        if any(not any(abs(t-e)<=1e-12 for e in expected) for t in signal.times_s):
            return unavailable('invalid','TIMED_TRACKING_TIME_GRID_MISMATCH')
        if len(signal.times_s)!=len(expected):return unavailable('incomplete','INCOMPLETE_TIMED_SAMPLING')
        errors=[math.dist(v,goal.at_time(min(t,goal.times_s[-1]))[0]) for t,v in zip(signal.times_s,signal.values)]
        lo,hi=task.sampling.window_s;scored=[e for t,e in zip(signal.times_s,errors) if lo-1e-12<=t<=hi+1e-12]
        maximum=max(scored)
        return EvaluationResult(validity='valid',task_success=maximum<=params.max_error_m,
            metrics=[Metric(name=n,value=v,units='m') for n,v in (('max_position_error',maximum),
                ('rms_position_error',math.sqrt(sum(e*e for e in scored)/len(scored))),('terminal_position_error',errors[-1]))],
            constraints=[ConstraintResult(name='tracking_max_error',satisfied=maximum<=params.max_error_m,
                observed=maximum,limit=params.max_error_m,units='m')],**common)
    measured=polyline_samples(signal.values,params.geometry_step_m)
    reference=polyline_samples(goal.vertices_m,params.geometry_step_m)
    errors,_=project_polyline(measured,goal.vertices_m)
    vertex_errors,progress=project_polyline(signal.values,goal.vertices_m)
    coverage,_=project_polyline(np.vstack([reference,goal.vertices_m]),signal.values)
    maximum=float(max(max(errors),max(vertex_errors)))
    rms=float(np.sqrt(np.mean(errors**2)))
    start=math.dist(signal.values[0],goal.vertices_m[0]);end=math.dist(signal.values[-1],goal.vertices_m[-1])
    regression=float(max(np.maximum.accumulate(progress)-progress))
    observed=dict(tracking_max_error=maximum,path_coverage=float(max(coverage)),
        path_start=start,path_end=end,path_progress_regression=regression)
    checks=[(row['condition_id'],observed[row['condition_id']])
            for row in tracking_condition_specs(task.model_dump(mode='json'))]
    return EvaluationResult(validity='valid',task_success=all(v<=params.max_error_m for _,v in checks),
        metrics=[Metric(name=name,value=value,units='m') for name,value in (
            ('max_position_error',maximum),('rms_position_error',rms),('terminal_position_error',end),
            ('path_coverage_error',float(max(coverage))),('progress_regression',regression))],
        constraints=[ConstraintResult(name=name,satisfied=v<=params.max_error_m,observed=v,limit=params.max_error_m,units='m') for name,v in checks],**common)

