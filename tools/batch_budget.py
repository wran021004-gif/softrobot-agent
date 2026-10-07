"""One reservation calculation for context, plan review and execution."""
from tools.execution_completion import EXECUTION_ALLOWANCES

INTERPRETATION_RESERVE=dict(wall_s=600.,model_calls=4,tool_calls=4)
PREPARATION_RESERVE_S=5.


def downstream_available(store,run_id,db=None,*,as_of_unix=None):
    project=store.remaining(None,db)['remaining'];session=store.remaining(run_id,db)['remaining']
    permissions=store.session(run_id,db)['state'].get('role_context',{}).get('campaign_permissions')
    if permissions:
        conditional=permissions.get('phase_budget_policy')=='conditional_verification@3.0.0'
        if conditional:
            # Delivery is protected by the existing Host phase reservation.
            # Verification backend count is protected, but its future time and
            # operations are gated only when a complete schedule is frozen.
            spendable=store.spendable(run_id,db)['remaining']
            for k,v in dict(model_calls=2,tool_calls=10,wall_s=1200.).items():
                project[k]=max(0,project[k]-v)
        if permissions.get('elapsed_deadline_unix'):
            import time
            project['wall_s']=min(project['wall_s'],max(0,permissions['elapsed_deadline_unix']-(time.time() if as_of_unix is None else as_of_unix)))
        # Child executions charge the project, not the research-role session.
        # Protect the full frozen paired allowance until search has ended.
        reserve=dict(backend_solves=20) if conditional else dict(backend_solves=20,tool_calls=60,wall_s=19800.)
        for k,v in reserve.items():
            project[k]=max(0,project[k]-v)
        if conditional:
            project={k:min(v,spendable[k]) for k,v in project.items()}
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
