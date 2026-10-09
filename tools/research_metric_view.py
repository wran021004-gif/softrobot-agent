"""Interpret the original evaluator/configuration, keeping recorded vs recomputed results."""
import math
from tools.state_io import digest

VERSION = 'research.metric_view@1.0.0'


def archived_recomputation_presentation(view,reference):
    """Interpret archived result fields; no calculation or investigator execution."""
    rows=[]
    for pointer,item in [('/reach',view['reach']),('/holding/position',view['holding']['position']),('/holding/speed',view['holding']['speed'])]:
        available=item.get('independent_recomputation')=='available'
        result=item.get('recomputed_result')
        rows.append(dict(reference=reference,pointer=pointer,
            availability='available' if available else 'unavailable',
            assessment=('pass' if result is True else 'fail' if result is False else 'cannot_assess') if available else 'cannot_assess',
            archived_result=result,result_pointer=pointer+'/recomputed_result',
            availability_pointer=pointer+'/independent_recomputation',
            origin='Recomputation from archived evidence; not a new investigator calculation',
            official_result_preserved=True))
    return dict(version='research.archived_recomputation_presentation@1.0.0',observations=rows,
        rules='An available Boolean false is a failed criterion. It is not absence of recomputation. /official has no recomputation fields; cite actual archived pointers.')


def build(facts, resolve):
    refs = dict(configuration=facts['configuration'], evaluation=facts['evaluation'],
                profile=facts['report']['reference'], simulation=facts['simulation'])
    configuration = resolve(refs['configuration']); cfg = configuration.get('effective', configuration)
    ev = resolve(refs['evaluation']); profile = resolve(refs['profile'])['detail']
    eid = facts['execution_id']
    if ev['source_execution_id'] != eid or profile['execution_id'] != eid or profile['evaluation'] != refs['evaluation'] or ev['source'] != refs['simulation']:
        raise ValueError('CROSS_EXECUTION_METRIC_VIEW')
    if (ev['evaluator'], ev['evaluator_version']) != ('evaluate.reach', '1.0.0'):
        raise ValueError('UNSUPPORTED_HISTORICAL_EVALUATOR')
    task = cfg['task']; limit = task['evaluator']['parameters']['data']['tolerance_m']
    if task['evaluator']['version'] != ev['evaluator_version'] or profile['task'] != task:
        raise ValueError('HISTORICAL_TASK_DEFINITION_MISMATCH')
    settling = profile['sampled_settling']; acceptance = cfg['policy']['controller']['parameters']['data']['settling']
    if any(settling[k] != acceptance[k] for k in ('window_s', 'position_limit_m', 'speed_limit_m_s')):
        raise ValueError('HISTORICAL_HOLDING_DEFINITION_MISMATCH')
    duration = task['timing']['duration_s']; period = task['timing']['sample_period_s']
    interval = [duration - acceptance['window_s'], duration]
    metric = next((m for m in ev['metrics'] if m['name'] == 'position_error' and m['units'] == 'm'), None)
    bound = next((b for b in ev['constraints'] if b['name'] == 'task_bound' and b['units'] == 'm'), None)
    if metric is None or bound is None or bound['limit'] != limit or bound['observed'] != metric['value']:
        raise ValueError('HISTORICAL_REACH_CRITERION_MISMATCH')
    def item(value, unit, window, sources, recorded=None, recomputed=None, missing=None, criterion=None):
        return dict(value=value, unit=unit, time_window_s=window, sources=sources,
                    criterion_version=criterion, recorded_result=recorded,
                    recomputed_result=recomputed, independent_recomputation='unavailable' if missing else 'available',
                    missing_material=missing or [])
    def source(name, pointer): return dict(reference=refs[name], pointer=pointer)
    recompute = None; missing = []
    try:
        sim = resolve(refs['simulation'])
        signal = next(s for s in sim['signals'] if s['spec']['name'] == 'tip_position' and s['spec']['frame'] == 'world' and s['spec']['units'] == 'm')
        complete = sim['solver_status'] == 'completed' and len(signal['times_s']) == round(duration / period) and all(abs(t-(i+1)*period)<=1e-8 for i,t in enumerate(signal['times_s']))
        if not complete: raise ValueError('INCOMPLETE_ORIGINAL_SIGNAL')
        recompute = math.dist(signal['values'][-1], task['goal']['data']['target_m'])
        if recompute != metric['value']: raise ValueError('RECOMPUTED_REACH_MISMATCH')
    except (KeyError, StopIteration): missing = ['original complete world tip signal']
    motion_ref = profile.get('motion'); selected = None
    if motion_ref:
        try:
            motion = resolve(motion_ref)
            selected = [r for r in motion if interval[0]-1e-9 <= r['time_s'] <= interval[1]+1e-9]
            grid = [interval[0]+i*period for i in range(round(acceptance['window_s']/period)+1)]
            if len(selected)!=len(grid) or any(abs(r['time_s']-t)>1e-8 for r,t in zip(selected,grid)): selected=None
        except KeyError: pass
    holding = {}
    for name, field, threshold, unit in [('position','max_error_m','position_limit_m','m'), ('speed','max_speed_m_s','speed_limit_m_s','m/s')]:
        computed = max(r['tip_error_m' if name=='position' else 'tip_speed_m_s'] for r in selected) if selected else None
        if computed is not None and computed != settling[field]: raise ValueError('RECOMPUTED_HOLDING_MISMATCH')
        holding[name] = item(settling[field], unit, interval,
            [source('profile', '/detail/sampled_settling/'+field)],
            recorded=None, recomputed=settling[field]<=acceptance[threshold] if computed is not None else None,
            missing=[] if computed is not None else ['complete original motion samples'], criterion='controller.gvs_nmpc@'+cfg['policy']['controller']['version']+'/sampled_settling')
        holding[name]['threshold'] = acceptance[threshold]
        holding[name]['motion_source'] = dict(reference=motion_ref, pointer='')
    reach = item(metric['value'], 'm', [duration,duration], [source('evaluation','/metrics/0'), source('configuration','/effective/task/evaluator')],
                 recorded=bound['satisfied'], recomputed=recompute<=limit if recompute is not None else None, missing=missing, criterion='evaluate.reach@1.0.0')
    reach['threshold'] = limit
    return dict(version=VERSION, candidate_id=facts['candidate']['candidate_id'], execution_id=eid, configuration=refs['configuration'],
        definition_identity=digest(dict(evaluator=task['evaluator'], controller=cfg['policy']['controller'], timing=task['timing'])),
        reach=reach, holding=dict(**holding, recorded_window_result=settling['passed'], recorded_available=settling['available'], continuous_time_guarantee=False),
        integrity=dict(evaluation_validity=ev['validity'], execution_complete=profile['valid_complete_execution'], solver_error_count=profile['solver_error_count'], force_bound_violation_n=profile['force_bound_violation_n'],
            sources=[source('evaluation','/validity'),source('profile','/detail')]),
        official=dict(recorded_result=ev['task_success'], source=source('evaluation','/task_success'),
            definition='Historical evaluate.reach@1.0.0 checks complete sampled execution and terminal distance only; sampled holding is separately recorded by profile. Never infer component failure solely from overall failure.'),
        limitations=['Unavailable independent recomputation does not erase a recorded official result.', 'One-step prediction agreement is neither reach nor holding acceptance.', 'Recomputed holding uses archived motion samples, not a new backend solve or continuous guarantee.'])
