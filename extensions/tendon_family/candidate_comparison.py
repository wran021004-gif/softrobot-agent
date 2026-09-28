"""Compact read-only comparison of owned, already evaluated Route records."""
from schemas.common import Contract
from pydantic import Field


class CompareRequest(Contract):
    source_nodes: list[str] = Field(default_factory=list, max_length=4,
        description='Evaluated run nodes; empty selects up to four latest evaluated runs. No new execution.')


def feedback(trial):
    s=trial.get('profile_report_summary',{})
    return dict(candidate_facts=trial.get('candidate_facts'), factual_result=trial.get('factual_result'), evaluation=trial.get('evaluation'),
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
        from .delivery_facts import bound_result_facts
        trial['factual_result']=bound_result_facts(ctx.store,trial,trial['candidate_facts'])
        rows.append(dict(node_id=node['node_id'],evidence=node['result'],**feedback(trial)))
    from .route import policy
    prior=policy(ctx.input).historical_case
    return RouteResult(detail=dict(candidates=rows,backend_solves=0,
        historical_comparisons=historical_comparisons(ctx.host,ctx.input,ctx.artifact(prior)) if prior else [],
        scope='Executed samples only; no new scoring, causal attribution or optimum claim'))


def historical_comparisons(host, baseline, prior):
    from .route import trial_facts
    from .delivery_facts import bound_result_facts
    before=prior['factual_result']
    old={r['path']:r['effective_value'] for r in prior['candidate_facts']['parameters']}
    rows=[]
    for node in host.store.session(host.run_id)['state']['route']['nodes']:
        if node['action']!='run' or node['status']!='completed': continue
        trial=host.store.artifact(node['result'])
        candidate=trial_facts(host.store,baseline,trial)
        facts=bound_result_facts(host.store,trial,candidate)
        if facts is None: continue
        changes=[dict(path=r['path'],historical=old[r['path']],current=r['effective_value'])
            for r in candidate['parameters'] if old[r['path']]!=r['effective_value']]
        rows.append(dict(node_id=node['node_id'],current_evidence=node['result'],
            historical_execution_id=before['execution_id'],historical_owner_run_id=prior['owner_run_id'],
            current_owner_run_id=candidate['owner_run_id'],candidate_facts={k:v for k,v in candidate.items() if k not in ('physical_summary','semantic_provenance','physical_changes')},factual_result=facts,
            changed_decisions=changes,meaningful_revision=bool(changes and facts['valid_complete_execution']),
            terminal_error_delta_m=None if facts['terminal_error_m'] is None else facts['terminal_error_m']-before['terminal_error_m'],
            scope='Historical execution is supplied prior evidence, not owned or charged by this session; sampled comparison, no causal or global claim.'))
    return rows
