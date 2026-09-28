"""Compact read-only comparison of owned, already evaluated Route records."""
from schemas.common import Contract
from pydantic import Field


class CompareRequest(Contract):
    source_nodes: list[str] = Field(default_factory=list, max_length=4,
        description='Evaluated run nodes; empty selects up to four latest evaluated runs. No new execution.')


def feedback(trial):
    s=trial.get('profile_report_summary',{})
    return dict(candidate_facts=trial.get('candidate_facts'), evaluation=trial.get('evaluation'),
        report=trial.get('profile_report'), observations={k:s.get(k) for k in (
            'valid_complete_execution','official_task_success','terminal_error_m','error_phases',
            'drive_utilization','updates','accepted_plans','converged_updates','solver_error_count',
            'hold_last_responses','max_projection_residual_rad_m','max_rate_projection_residual_rad_m_s',
            'mean_update_s','simulation_wall_s','backend_timings_s','one_step_prediction_summary',
            'one_step_prediction_evidence','sampled_settling','real_time_demonstrated')},
        hypotheses=s.get('diagnostic_hypotheses',[]), limitations=s.get('diagnostic_limitations',[]))


def compare(ctx,args):
    from .route import RouteResult, trial_facts
    nodes=[n for n in ctx.store.session(ctx.run_id)['state']['route']['nodes']
        if n['action']=='run' and n['status']=='completed']
    if args.source_nodes:
        if set(args.source_nodes)-{n['node_id'] for n in nodes}:
            raise ValueError('OWNED_EVALUATED_RUN_REQUIRED')
        nodes=[n for n in nodes if n['node_id'] in args.source_nodes]
    rows=[]
    for node in nodes[-4:]:
        trial=ctx.artifact(node['result'])
        trial['candidate_facts']=trial_facts(ctx.store,ctx.input,trial)
        rows.append(dict(node_id=node['node_id'],evidence=node['result'],**feedback(trial)))
    return RouteResult(detail=dict(candidates=rows,backend_solves=0,
        scope='Executed samples only; no new scoring, causal attribution or optimum claim'))
