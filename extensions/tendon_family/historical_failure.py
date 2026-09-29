"""One trusted, read-only binding for the supplied Stage 3.29 failed case."""
from copy import deepcopy
from tools.state_io import read, digest
from tools.platform_store import Store, plain
from schemas.platform import SessionInput
from .candidate import candidate_facts, apply
from .contracts import Space
from .delivery_facts import bound_result_facts
from .gvs_profile import execution_scope


def bind_failure(source, experiment, index=None, store=None, frozen_path='frozen_input.json'):
    index=read(source/'evidence_index.json') if index is None else index
    store=Store(source/'live') if store is None else store
    frozen=read(source/frozen_path)
    selected=store.artifact(index['configuration'])
    effective=selected['effective']
    report=index['profile_report']
    session=store.session(index['live_session'])
    owner=store.session(report['owner_run_id'])
    metadata=owner['state']['result_executions'][report['execution_id']]
    if metadata['candidate_input']!=index['configuration']:
        raise ValueError('HISTORICAL_CONFIGURATION_BINDING_MISMATCH')
    facts=candidate_facts(frozen,selected,index['configuration'],index['candidate_id'],
        report['owner_run_id'],report['execution_id'])
    summary=store.artifact(report['reference'])['detail']
    trial=dict(profile_report=report,evaluation=index['evaluation'],simulation=dict(output=summary['simulation']))
    result=bound_result_facts(store,trial,facts)
    if not result['valid_complete_execution'] or result['task_accepted'] is not False:
        raise ValueError('SUPPLIED_COMPLETE_FAILED_CASE_REQUIRED')
    # Require the identical baseline/task/space and reconstruct the old declared
    # design with today's expansion. Source-code hashes are recorded separately.
    current=SessionInput.model_validate(experiment)
    if plain(current.robot)!=frozen['robot'] or plain(current.task)!=frozen['task']:
        raise ValueError('HISTORICAL_BASELINE_OR_TASK_MISMATCH')
    if plain(current.policy.candidate_builder)!=frozen['policy']['candidate_builder']:
        raise ValueError('HISTORICAL_DESIGN_SPACE_MISMATCH')
    space=Space.model_validate(current.policy.candidate_builder.parameters.data)
    revised=apply(deepcopy(current),space,{r['path']:r['effective_value'] for r in facts['parameters']})
    old_scope=execution_scope(effective);new_scope=execution_scope(revised)
    if old_scope!=new_scope or summary['execution_scope']!=old_scope:
        raise ValueError('HISTORICAL_SCIENTIFIC_CONDITIONS_MISMATCH')
    from .route import policy
    if any(plain(getattr(choice,k))!=plain(getattr(current.policy,k))
           for choice in policy(current).combinations.values()
           for k in ('controller','backend','dynamics_model')):
        raise ValueError('HISTORICAL_COMBINATION_MISMATCH')
    return dict(kind='supplied_historical_failure',experiment_description='autonomous design revision from supplied historical failure evidence',
        source_session_id=index['live_session'],owner_run_id=report['owner_run_id'],
        source_state_identity=digest(session['state']),source_directory=str(source),
        candidate_facts={k:v for k,v in facts.items() if k not in ('physical_summary','semantic_provenance','physical_changes')},factual_result=result,
        compatibility=dict(scientific_conditions_match=True,scope_identity=digest(old_scope),
            checked=['frozen task and evaluator','controller recipe and physical execution mode','initializer',
                'discretization and basis','baseline robot, scene, gravity, payload, routing and rigid parts','declared design expansion'],
            historical_source_commit=session['snapshot'].get('project_commit'),
            source_hash_policy='Reporting source hashes may differ; scientific conditions compared by value, not source hash.'),
        attribution='Supplied by developer. Not a current-session execution, selectable incumbent, or charged backend attempt. Prior provider conclusions excluded.')


def cases(prior):
    return prior.get('cases',[prior])


def bind_sources(descriptors, experiment, destination):
    from pathlib import Path
    bound=[]
    for descriptor in descriptors:
        prior=bind_cases(Path(descriptor['directory']),experiment,descriptor['candidate_ids'],destination,descriptor)
        bound.extend(prior['cases'])
    identities=[(c['source_session_id'],c['factual_result']['execution_id']) for c in bound]
    if len(set(identities))!=len(identities):
        raise ValueError('DUPLICATE_HISTORICAL_EXECUTION')
    return dict(kind='supplied_prior_cases',cases=bound,
        attribution='Explicitly supplied historical samples only; no source ownership imported, no rerun or new backend charge. Provider conclusions excluded.')


def bind_cases(source, experiment, candidate_ids, destination, descriptor=None):
    """Bind only explicitly selected evaluated cases; export details, never owners."""
    import gzip
    from pathlib import Path
    from .gvs_reporting import motion_summary
    if descriptor is None:
        descriptor=dict(source_session_id=read(source/'evidence_index.json')['run_id'],
            records='actual_revised_candidates.json',live_store='live',ledger='platform.sqlite.gz',
            frozen_input='frozen_input.json')
    source_id=descriptor['source_session_id']
    records=read(source/descriptor['records'])
    selected=[r for r in records if r['candidate_facts']['candidate_id'] in candidate_ids]
    if len(selected)!=len(candidate_ids) or len(set(candidate_ids))!=len(candidate_ids):
        raise ValueError('EXPLICIT_HISTORICAL_CASES_REQUIRED')
    store=Store(source/descriptor['live_store'])
    if not store.db.is_file():
        retained=destination.root/'historical_ledgers'/source_id
        retained.mkdir(parents=True,exist_ok=True)
        store=Store(retained)
        store.db.write_bytes(gzip.decompress((source/descriptor['ledger']).read_bytes()))
    session=store.session(source_id)
    frozen=read(source/descriptor['frozen_input'])
    if session['snapshot']['input']!=frozen:
        # Older callers supply the unresolved input; scientific equality is
        # checked below. Explicit descriptors require the resolved snapshot.
        if 'directory' in descriptor: raise ValueError('HISTORICAL_SOURCE_SNAPSHOT_MISMATCH')
    bound=[]
    for record in selected:
        facts=record['candidate_facts']; result=record['factual_result']
        node=next((n for n in session['state']['route']['nodes']
            if n['node_id']==record['node_id'] and n['action']=='run' and n['status']=='completed'),None)
        if node is None or node['result']!=record['evidence']:
            raise ValueError('HISTORICAL_SOURCE_NODE_MISMATCH')
        from .route import trial_facts
        trial=store.artifact(node['result'])
        ledger_facts=trial_facts(store,session['snapshot']['input'],trial)
        if ledger_facts!=facts or bound_result_facts(store,trial,ledger_facts)!=result:
            raise ValueError('HISTORICAL_RECORD_LEDGER_MISMATCH')
        binding=dict(live_session=source_id,configuration=facts['configuration'],
            candidate_id=facts['candidate_id'],profile_report=result['report'],evaluation=result['evaluation'])
        case=bind_failure(source,experiment,binding,store,descriptor['frozen_input'])
        report=store.artifact(result['report']['reference'])['detail']
        motion=store.artifact(report['motion'])
        case['motion_summary']=motion_summary(motion,case['factual_result']['signed_position_error_m'],
            experiment['task']['timing']['duration_s'],report['sampled_settling']['window_s'],
            experiment['task']['evaluator']['parameters']['data']['tolerance_m'])
        # An explicitly attributed, small export permits ordinary evidence.read.
        detail=dict(source_session_id=source_id,owner_run_id=case['owner_run_id'],
            source_directory=str(source),configuration=store.artifact(facts['configuration']),
            report=store.artifact(result['report']['reference']),evaluation=store.artifact(result['evaluation']),
            sampled_motion=motion,source_bindings=binding)
        with destination.transaction() as db:
            case['detail_export']=plain(destination.put(db,detail))
        bound.append(case)
    return dict(kind='supplied_prior_cases',cases=bound,
        attribution='Explicitly supplied historical samples only; no source ownership imported, no rerun or new backend charge. Provider conclusions excluded.')
