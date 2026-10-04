"""One reservation calculation for context, plan review and execution."""
from tools.execution_completion import EXECUTION_ALLOWANCES

INTERPRETATION_RESERVE=dict(wall_s=600.,model_calls=4,tool_calls=4)
PREPARATION_RESERVE_S=5.


def downstream_available(store,run_id,db=None):
    project=store.remaining(None,db)['remaining'];session=store.remaining(run_id,db)['remaining']
    return {k:min(v,session[k]) for k,v in project.items()}


def batch_requirement(count, *, interpretation=None, planning=None,preparation_reserve_s=0.):
    interpretation=INTERPRETATION_RESERVE if interpretation is None else interpretation
    planning=dict(model_calls=1,tool_calls=1,wall_s=0.) if planning is None else planning
    operations={k:v['reserve_s'] for k,v in EXECUTION_ALLOWANCES.items()}
    requirement=dict(backend_solves=count,worker_calls=0,
        model_calls=interpretation.get('model_calls',0)+planning.get('model_calls',0),
        tool_calls=4*count+interpretation.get('tool_calls',0)+planning.get('tool_calls',0),
        wall_s=count*(sum(operations.values())+preparation_reserve_s)+interpretation.get('wall_s',0)+planning.get('wall_s',0))
    return dict(requirement=requirement,operation_reservations_s=operations,
        preparation='candidate.apply is one charged workflow call; physical rebuild wall time is charged there and in simulation preparation.',
        candidate_preparation_reserve_s=preparation_reserve_s,protected_interpretation=interpretation,planning=planning)


def budget_capacity(count, available, **kwargs):
    result=batch_requirement(count,**kwargs)
    result.update(available=available,shortfalls={k:max(0,v-available.get(k,0)) for k,v in result['requirement'].items()})
    result['sufficient']=not any(result['shortfalls'].values())
    return result
