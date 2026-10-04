"""One reservation calculation for context, plan review and execution."""
from tools.execution_completion import EXECUTION_ALLOWANCES

INTERPRETATION_RESERVE=dict(wall_s=600.,model_calls=4,tool_calls=4)


def batch_requirement(count, *, interpretation=None, planning=None):
    interpretation=INTERPRETATION_RESERVE if interpretation is None else interpretation
    planning=dict(model_calls=1,tool_calls=1,wall_s=0.) if planning is None else planning
    operations={k:v['reserve_s'] for k,v in EXECUTION_ALLOWANCES.items()}
    requirement=dict(backend_solves=count,worker_calls=0,
        model_calls=interpretation.get('model_calls',0)+planning.get('model_calls',0),
        tool_calls=4*count+interpretation.get('tool_calls',0)+planning.get('tool_calls',0),
        wall_s=count*sum(operations.values())+interpretation.get('wall_s',0)+planning.get('wall_s',0))
    return dict(requirement=requirement,operation_reservations_s=operations,
        preparation='candidate.apply is one charged workflow call; physical rebuild wall time is charged there and in simulation preparation.',
        protected_interpretation=interpretation,planning=planning)


def budget_capacity(count, available, **kwargs):
    result=batch_requirement(count,**kwargs)
    result.update(available=available,shortfalls={k:max(0,v-available.get(k,0)) for k,v in result['requirement'].items()})
    result['sufficient']=not any(result['shortfalls'].values())
    return result
