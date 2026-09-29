"""Compact read-only comparison of owned, already evaluated Route records."""
from schemas.common import Contract
from pydantic import Field


class CompareRequest(Contract):
    source_nodes: list[str] = Field(default_factory=list, max_length=4,
        description='Evaluated run nodes; empty selects up to four latest evaluated runs. No new execution.')


def feedback(trial):
    s=trial.get('profile_report_summary',{})
    return dict(candidate_facts=trial.get('candidate_facts'), factual_result=trial.get('factual_result'), evaluation=trial.get('evaluation'),
        length_allocation=length_allocation(trial.get('candidate_facts')),
        report=trial.get('profile_report'), observations={k:s.get(k) for k in (
            'valid_complete_execution','official_task_success','terminal_error_m','error_phases','motion_summary',
            'drive_utilization','updates','accepted_plans','initialization_selected','accepted_noninitialization_plans','converged_updates','solver_error_count',
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
    from .historical_failure import cases
    rows=[]
    selected=cases(prior)
    if 'cases' in prior:
        selected=[min(selected,key=lambda c:c['factual_result']['terminal_error_m'])]
    for case in selected:
        compared=_historical_comparisons(host,baseline,case)
        if 'cases' in prior:
            # Detailed facts live once in exploration samples / current delivery.
            for row in compared:
                row['candidate_id']=row.pop('candidate_facts')['candidate_id']
                row['terminal_error_m']=row.pop('factual_result')['terminal_error_m']
                row['historical_candidate_id']=case['candidate_facts']['candidate_id']
                row['comparison_scope']='Compare fresh samples to best supplied historical sample; all supplied measurements are in exploration_summary.'
        rows.extend(compared)
    return rows


def length_allocation(candidate):
    if not candidate: return None
    values={p['path']:p['effective_value'] for p in candidate['parameters']}
    near=values['components/near/length_m'];far=values['components/far/length_m']
    return dict(length_pair_m=[near,far],total_length_m=near+far,near_minus_far_m=near-far,
        meaningful_independent_lengths=abs((near-far)-.04)>=.001-1e-9)


def _historical_comparisons(host, baseline, prior):
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
            length_allocation=length_allocation(candidate),initialization_selected=facts['initialization_selected'],
            accepted_noninitialization_plans=facts['accepted_noninitialization_plans'],
            terminal_error_delta_m=None if facts['terminal_error_m'] is None else facts['terminal_error_m']-before['terminal_error_m'],
            scope='Historical execution is supplied prior evidence, not owned or charged by this session; sampled comparison, no causal or global claim.'))
    return rows


def exploration_summary(host, baseline, prior):
    from .historical_failure import cases
    from .route import trial_facts
    from .delivery_facts import bound_result_facts
    def sample(candidate,result,**extra):
        values={p['path']:p['effective_value'] for p in candidate['parameters']}
        near=values['components/near/length_m']; far=values['components/far/length_m']
        return dict(candidate_id=candidate['candidate_id'],owner_run_id=candidate['owner_run_id'],
            execution_id=candidate['execution_id'],parameters=candidate['parameters'],
            coverage=candidate.get('multi_category_coverage'),terminal_error_m=result['terminal_error_m'],
            task_accepted=result['task_accepted'],valid_complete_execution=result['valid_complete_execution'],
            length_pair_m=[near,far],total_length_m=near+far,near_minus_far_m=near-far,
            meaningful_independent_lengths=abs((near-far)-.04)>=.001-1e-9,
            initialization_selected=result['initialization_selected'],
            accepted_noninitialization_plans=result['accepted_noninitialization_plans'],**extra)
    historical=[sample(c['candidate_facts'],c['factual_result'],motion_summary=c.get('motion_summary'),
        detail_export=c.get('detail_export')) for c in cases(prior)] if prior else []
    fresh=[]
    nodes=host.store.session(host.run_id)['state']['route']['nodes']
    for node in nodes:
        if node['action']!='run' or node['status']!='completed': continue
        trial=host.store.artifact(node['result'])
        candidate=trial_facts(host.store,baseline,trial)
        result=bound_result_facts(host.store,trial,candidate)
        if result is None: continue
        fresh.append(sample(candidate,result,node_id=node['node_id'],evidence=node['result'],
            motion_summary=trial.get('profile_report_summary',{}).get('motion_summary')))
        build=next(n for n in nodes if n['node_id']==node['selection']['source_node'])
        parent_id=build['selection'].get('source_node')
        if parent_id:
            parent=next(n for n in nodes if n['node_id']==parent_id)
            facts=trial_facts(host.store,baseline,host.store.artifact(parent['result']))
            old={r['path']:r['effective_value'] for r in facts['parameters']}
            fresh[-1]['parent_changes']=dict(source_node=parent_id,changes=[dict(path=r['path'],
                parent_value=old[r['path']],current_value=r['effective_value']) for r in candidate['parameters']
                if old[r['path']]!=r['effective_value']])
        else: fresh[-1]['build_parent']='frozen baseline; parameter rows state baseline values and deltas'
    def tested(rows):
        values={}
        for row in rows:
            for p in row['parameters']:
                bucket=values.setdefault(p['path'],[])
                if p['effective_value'] not in bucket: bucket.append(p['effective_value'])
        return dict(values_tested=values,constant_decisions={k:v[0] for k,v in values.items() if len(v)==1},
            sample_count=len(rows))
    valid=[r for r in historical+fresh if r['valid_complete_execution'] and r['terminal_error_m'] is not None]
    best=min(valid,key=lambda r:r['terminal_error_m']) if valid else None
    def best_of(rows):
        valid=[r for r in rows if r['valid_complete_execution'] and r['terminal_error_m'] is not None]
        row=min(valid,key=lambda r:r['terminal_error_m']) if valid else None
        return None if row is None else {k:row[k] for k in ('candidate_id','owner_run_id','execution_id','terminal_error_m','task_accepted')}
    return dict(historical=tested(historical),fresh=tested(fresh),historical_samples=historical,fresh_samples=fresh,
        best_historical=best_of(historical),best_fresh=best_of(fresh),
        length_coupling=dict(reference_difference_m=.04,meaningful_departure_m=.001,
            historical_relationship_unbroken=all(abs(r['near_minus_far_m']-.04)<=1e-9 for r in historical),
            evaluated_relationship_unbroken=all(abs(r['near_minus_far_m']-.04)<=1e-9 for r in historical+fresh),
            meaningful_departure_evaluated=any(r['meaningful_independent_lengths'] for r in valid),
            historical_limitation=(f'All {len(historical)} supplied evaluated cases lie on near-minus-far=0.04 m. Independent allocation has not yet been evaluated in that history. '
                + ('Both lengths have changed across these cases, but remain coupled.' if len({tuple(r['length_pair_m']) for r in historical})>1 else 'The sampled lengths are constant.'))
                if historical and all(abs(r['near_minus_far_m']-.04)<=1e-9 for r in historical) else 'See evaluated length pairs; sampled coverage does not identify causal effects.',
            scope='Exploration assessment only, not feasibility or task acceptance. Departure does not identify each segment causal effect. Plan counts are diagnostic, not proof of causation or convergence.'),
        best_measured=None if best is None else {k:best[k] for k in ('candidate_id','owner_run_id','execution_id','terminal_error_m','task_accepted')},
        remaining_resources=host.store.remaining()['remaining'],
        scope='Evaluated samples only. Baseline coverage is not exploration coverage; bounds do not establish exhaustion. Historical samples are not fresh executions.')


def prior_overview(prior):
    """Keep source identities and detail paths, avoiding repeated full result facts."""
    if 'cases' not in prior: return prior
    return dict(kind=prior['kind'],attribution=prior['attribution'],cases=[dict(
        source_session_id=c['source_session_id'],owner_run_id=c['owner_run_id'],source_directory=c['source_directory'],
        candidate_id=c['candidate_facts']['candidate_id'],configuration=c['candidate_facts']['configuration'],
        execution_id=c['factual_result']['execution_id'],evaluation=c['factual_result']['evaluation'],
        report=c['factual_result']['report'],detail_export=c['detail_export'],compatibility=c['compatibility']) for c in prior['cases']],
        evidence_access='Original bindings belong to the source store. Read detail_export with evidence.read in this session; exploration_summary contains compact measurements.')
