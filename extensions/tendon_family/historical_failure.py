"""One trusted, read-only binding for the supplied Stage 3.29 failed case."""
from copy import deepcopy
from tools.state_io import read, digest
from tools.platform_store import Store, plain
from schemas.platform import SessionInput
from .candidate import candidate_facts, apply
from .contracts import Space
from .delivery_facts import bound_result_facts
from .gvs_profile import execution_scope


def bind_failure(source, experiment):
    index=read(source/'evidence_index.json')
    store=Store(source/'live')
    frozen=read(source/'frozen_input.json')
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
