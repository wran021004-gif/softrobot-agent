"""Compact trusted research views and declared archive import using the existing Store."""
from copy import deepcopy
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.state import state, save, update
from tools.research.feedback import task_gap
from tools.research.evidence_policy import summarize_evidence, hypothesis_catalog, comparable_task


def import_history(host):
    """Import hash-verified observations only; never promote historical execution IDs."""
    from tools.research.numerics import archived
    from tools.research.design import generate_candidate
    from tools.research.physical_replay import binding, schedule_identity
    s=state(host)
    if s.get('research_history_imported'):return
    entries=[]
    for item in s['spec']['research_decisions'].get('history',[]):
        folder=item['folder'];ref=item['reference'];result=archived(folder,ref)
        old=archived(folder,result['candidate']);cfg=old['configuration']
        if comparable_task(s['spec'],cfg['task'])!=s['spec']['canonical_task']:raise ValueError('HISTORY_TASK_IDENTITY_MISMATCH')
        source=archived(folder,result['source_reference'])
        binding(cfg,source['trajectory'])
        parameters=deepcopy(old['parameters']);parameters['family_space_identity']=s['spec']['family_space_identity']
        candidate=generate_candidate(host,parameters,dict(origin='engineering_history_materialization',source=ref))['candidate']
        new=host.store.artifact(candidate)['configuration']
        if schedule_identity(cfg,source['trajectory'])!=schedule_identity(new,source['trajectory']):
            raise ValueError('HISTORY_PHYSICAL_IDENTITY_MISMATCH')
        binding(new,source['trajectory'])
        for r,v in ((result['candidate'],old),(result['source_reference'],source),(ref,result)):
            if save(host,v,'declared_historical_evidence')!=r:raise ValueError('HISTORY_CONTENT_IDENTITY_MISMATCH')
        from tools.research.feedback import import_experiment
        import_experiment(host,folder,ref,'fixed_tension')
        raw=archived(folder,result['raw_reference'])
        if save(host,raw,'declared_historical_raw')!=result['raw_reference']:raise ValueError('HISTORY_RAW_IDENTITY_MISMATCH')
        entries.append(dict(reference=ref,candidate=candidate,source=result['source_reference'],
            historical_candidate=result['candidate'],folder=folder,historical_only=True))
    mathematics=[]
    for item in s['spec']['research_decisions'].get('mathematics',[]):
        value=archived(item['folder'],item['reference'])
        if value.get('candidate'):
            candidate=archived(item['folder'],value['candidate'])
            if comparable_task(s['spec'],candidate['configuration']['task'])!=s['spec']['canonical_task']:raise ValueError('HISTORY_MATH_TASK_IDENTITY_MISMATCH')
            if save(host,candidate,'declared_historical_math_candidate')!=value['candidate']:raise ValueError('HISTORY_MATH_CANDIDATE_MISMATCH')
        if save(host,value,'declared_historical_mathematics')!=item['reference']:raise ValueError('HISTORY_MATH_IDENTITY_MISMATCH')
        mathematics.append(item['reference'])
    update(host,research_history=entries,research_mathematics=mathematics,research_history_imported=True)


def observation(host,ref,historical=False):
    from tools.research_tasks import task_adapter
    result=host.store.artifact(ref);cfg=host.store.artifact(result['candidate'])['configuration']
    raw_ref=result.get('raw_reference');adapter=task_adapter(cfg)
    return dict(reference=plain(ref),candidate=result['candidate'],source=result.get('source_reference'),
        task_identity=digest(cfg['task']),historical_only=historical,task_gap=task_gap(result),
        constraints=result['acceptance'].get('components',{}),
        violations=adapter.violation_samples(host.store.artifact(raw_ref)) if raw_ref else dict(status='unavailable',samples=[]),
        raw_reference=raw_ref,evidence=summarize_evidence(result,ref))


def context(host):
    from tools.research.candidate_portfolio import ranking_key
    from tools.research_tasks import task_adapter
    from tools.research.budget import protected, closeout_operations, stage_usage
    s=state(host);spec=s['spec']
    rows=[observation(host,e['reference'],True) for e in s.get('research_history',[])]
    rows += [observation(host,r) for r in [*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]]
    valid=sorted((r for r in rows if r['task_gap']['valid_complete']),key=ranking_key)
    best=valid[0] if valid else None
    mapped={e['reference']['artifact_id']:e for e in s.get('research_history',[])}
    if best and best['reference']['artifact_id'] in mapped:
        best={**best,'executable_candidate':mapped[best['reference']['artifact_id']]['candidate']}
    # Pareto coordinates come from registered normalized task components.
    def dominates(a,b):
        def axes(r):
            return {k:v['value']/v['limit'] for k,v in r['constraints'].items()
                if type(v.get('value')) in (int,float) and type(v.get('limit')) in (int,float) and v['limit']>0}
        x=axes(a);y=axes(b)
        return x.keys()==y.keys() and all(x[k]<=y[k] for k in x) and any(x[k]<y[k] for k in x)
    pareto=[r['reference'] for r in valid if not any(dominates(q,r) for q in valid)]
    evidence=[summarize_evidence(host.store.artifact(r),r) for r in [*s.get('research_mathematics',[]),*s.get('analysis_results',[]),*s.get('mechanics_results',[])]]
    evidence=[{k:v[k] for k in ('claim_kind','verification_status','model_identity','candidate_identity','task_identity',
        'supported_inferences','unsupported_inferences','evidence_reference','numerical_evidence_pointer','prospective_guarantee')} for v in evidence]
    return dict(version='research_context_v1',task_identity=spec.get('canonical_task_identity',digest(s['base_configuration']['task'])),
        task=task_adapter(s['base_configuration']).describe(),structure_domain=s.get('family_space_reference'),
        capabilities=spec['capabilities'],best_valid=best,pareto_candidates=pareto,
        observations=[{k:r[k] for k in ('reference','candidate','task_identity','historical_only','task_gap')} for r in rows],
        evidence=evidence,unresolved_hypotheses=hypothesis_catalog(),history=s.get('research_history',[]),
        control_search_starts=[dict(candidate=e['candidate'],source=e['source'],historical_observation=e['reference'],
            ownership='Current executable candidate; observation retains sealed historical ownership') for e in sorted(
                s.get('research_history',[]),key=lambda e:ranking_key(dict(task_gap=task_gap(host.store.artifact(e['reference'])))))],
        actions=[] if s['research_status']=='stopped' else closeout_operations(host)['research_plan'] if protected(host) else spec['allowed_plan_actions'],
        budget=host.store.remaining(),completed_decisions=s.get('plans',[]),
        method_limits=dict(mathematical_evaluations=spec['budgets']['mathematical_evaluations'],offline_nlp=spec['budgets']['offline_nlp'],
            bdf_replays=spec['budgets']['bdf_replays'],nmpc=spec['nmpc_limits'],rl=spec['rl_limits']),
        method_used={k:s.get(k,0) for k in ('mathematical_evaluations','offline_nlp','bdf_replays','nmpc_launches','admitted_training_stages','physical_replay_launches')},
        method_remaining={k:max(0,total-used) for k,total,used in (
            ('mathematical_evaluations',spec['budgets']['mathematical_evaluations'],s.get('mathematical_evaluations',0)),
            ('offline_nlp',spec['budgets']['offline_nlp'],s.get('offline_nlp',0)),('bdf_replays',spec['budgets']['bdf_replays'],s.get('bdf_replays',0)),
            ('nmpc',spec['nmpc_limits']['executions'],s.get('nmpc_launches',0)),('rl_stages',spec['rl_limits']['training_stages'],s.get('admitted_training_stages',0)))},
        rl_accounting=stage_usage(s),
        control_search_usage='action=control_search, control_search={candidate,source,settings,adaptation_from?}; decision fields required. v2 dimensions come from schedule. Optional correction_window_s masks all changes outside the window. Current optimizer supports registered reach-hold norm constraints only; other tasks return unsupported. Full original task always evaluated.')
