"""Frozen condition bindings and joint selection over existing candidates/results."""
from copy import deepcopy
import json

from tools.platform_store import plain
from tools.research.state import state, save, update
from tools.state_io import digest


def configuration_for_condition(configuration, condition):
    cfg=deepcopy(configuration)
    task=deepcopy(condition['task'])
    if task['initializer']['parameters']['data'].get('rule')=='all_candidate_dofs_zero_v1':
        task['initializer']['parameters']['data']=deepcopy(cfg['task']['initializer']['parameters']['data'])
        for key in ('qpos_rad','qvel_rad_s'):
            task['initializer']['parameters']['data'][key]={k:0. for k in task['initializer']['parameters']['data'][key]}
    cfg.update(task=task,seed=condition['seed'])
    if condition.get('execution'):
        cfg['policy'].update(deepcopy(condition['execution']))
    else:
        # Only an inherited Reach-compatible controller owns this legacy field.
        data=cfg['policy']['controller']['parameters']['data']
        if 'settling' in data:data['settling']=deepcopy(condition.get('settling'))
    from schemas.platform import SessionInput
    from tools.platform_registry import registry
    inp=SessionInput.model_validate(cfg)
    _,parameters=registry().bind(inp.policy.backend,'backend')
    cfg['policy']['backend']['parameters']['data']=plain(parameters)
    cfg=plain(SessionInput.model_validate(cfg))
    if shared_physics(configuration)!=shared_physics(cfg):
        raise ValueError('CONDITIONS_REQUIRE_IDENTICAL_PHYSICAL_MODEL_AND_DISCRETIZATION')
    return cfg


def shared_physics(configuration):
    """Compare the real compiled structure/assembly, allowing frozen COM forces."""
    from schemas.platform import SessionInput
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble_physical
    cfg=SessionInput.model_validate(configuration);physics=physics_for(cfg)
    assembly=assemble_physical(cfg,physics)['assembly']
    assembly.pop('external_forces',None)
    backend=plain(cfg.policy.backend);backend.pop('version')
    return dict(physics=physics,assembly=assembly,backend=backend,
        dynamics_model=plain(cfg.policy.dynamics_model),discretization=plain(cfg.policy.discretization))


def condition_candidate(host, reference, condition_id, *, create=True):
    """Resolve an exact frozen-condition clone; preparation may only look up."""
    from tools.research.design import verify_candidate, full_science, family_candidate_identity
    from tools.platform_tasks import compile_input
    s=state(host)
    condition=next((c for c in s['spec'].get('task_conditions',[]) if c['condition_id']==condition_id),None)
    if condition is None:raise ValueError('UNKNOWN_FROZEN_TASK_CONDITION: '+condition_id)
    parent=verify_candidate(host,reference)
    root=parent.get('structure_candidate',plain(reference))
    parent=verify_candidate(host,root)
    cfg=configuration_for_condition(parent['configuration'],condition)
    if cfg==parent['configuration']:return root
    identity=family_candidate_identity(cfg,s)
    if identity in s['candidates']:return s['candidates'][identity]
    if not create:return None
    compile_input(cfg,host.reg)
    candidate=deepcopy(parent)
    candidate.update(identity=identity,candidate_id='core-'+identity,condition_id=condition_id,
        structure_candidate=root,configuration=cfg,scientific_configuration=full_science(cfg),
        configuration_reference=save(host,cfg,'resolved_candidate_configuration'),
        task_identity=digest(condition['task']),effective_task_identity=digest(cfg['task']),
        initialization_provenance=dict(condition_id=condition_id,effective=cfg['task']['initializer'],
            inherited_acceptance=False),provenance=dict(origin='frozen_task_condition',parent=root))
    ref=save(host,candidate,'candidate_constructed')
    update(host,candidates={**state(host)['candidates'],identity:ref})
    return ref


def joint_assessment(host, references, *, require_reads=True):
    """Check actual Store receipts and original acceptance, independent of order."""
    from tools.research.config import same_robot_structure
    from tools.research.design import verify_candidate
    from tools.research.feedback import eligibility, result_view
    from tools.research.physical_replay import binding
    from tools.research_tasks import aggregate_acceptance, _source_issue, _outcome_issue
    s=state(host);conditions=s['spec'].get('task_conditions',[])
    if not conditions:raise ValueError('FROZEN_TASK_CONDITIONS_REQUIRED')
    records=[];by_condition={};root=None;baseline=None;views=[];schedule=[]
    from tools.research_tasks import task_adapter
    from tools.research.evidence_views import acceptance_certificate
    for reference in references:
        reference=plain(reference)
        result=host.store.artifact(reference)
        choice=eligibility(host,reference,selection=True,condition_member=True,evidence_only=not require_reads)
        reasons=choice['reasons']
        if reasons:raise ValueError('; '.join(reasons))
        candidate=verify_candidate(host,result['candidate']);cfg=candidate['configuration']
        condition_id=candidate.get('condition_id',conditions[0]['condition_id'])
        condition=next((c for c in conditions if c['condition_id']==condition_id),None)
        if condition is None:raise ValueError('UNKNOWN_FROZEN_TASK_CONDITION')
        if condition_id in by_condition:raise ValueError('DUPLICATE_TASK_CONDITION')
        structure=candidate.get('structure_candidate',result['candidate'])
        expected=configuration_for_condition(verify_candidate(host,structure)['configuration'],condition)
        if cfg!=expected:raise ValueError('FROZEN_CONDITION_CONFIGURATION_MISMATCH')
        if baseline is not None and (not same_robot_structure(baseline,cfg) or
                baseline['policy']['discretization']!=cfg['policy']['discretization']):
            raise ValueError('JOINT_SELECTION_REQUIRES_IDENTICAL_STRUCTURE_AND_DISCRETIZATION')
        if baseline is not None and shared_physics(baseline)!=shared_physics(cfg):
            raise ValueError('JOINT_SELECTION_REQUIRES_IDENTICAL_PHYSICAL_MODEL')
        if baseline is None:baseline=cfg;root=structure
        if not result.get('source_reference'):
            raise ValueError('JOINT_SELECTION_REQUIRES_INDEPENDENT_PHYSICAL_REPLAY')
        source=host.store.artifact(result['source_reference'])
        binding(cfg,source['trajectory'])
        with host.store.connect(True) as db:
            row=db.execute('SELECT receipt FROM calls WHERE run_id=? AND execution_id=?',
                (host.run_id,result['execution_id'])).fetchone()
        receipt=json.loads(row['receipt']) if row and row['receipt'] else None
        if not receipt or receipt['execution_status']!='completed' or receipt['output']!=reference:
            raise ValueError('COMPLETED_OWNED_PHYSICAL_REPLAY_RECEIPT_REQUIRED')
        for issue in (_source_issue(result['acceptance']),_outcome_issue(result['acceptance'])):
            if issue:raise ValueError(issue)
        certificate=acceptance_certificate(host,reference)
        if not certificate['complete_acceptance_view']:
            raise ValueError('COMPLETE_ORIGINAL_CONDITION_CERTIFICATE_REQUIRED')
        if (host.store.artifact(result['profile_reference'])!=result['profile'] or
                result['acceptance']['task_identity']!=digest(cfg['task']) or result['profile']['task']!=cfg['task'] or
                result['acceptance']['sources']!=dict(evaluation=result['evaluation_reference'],profile=result['profile_reference'])):
            raise ValueError('CONDITION_RESULT_SOURCE_BINDING_MISMATCH')
        records.append(dict(case_id=condition_id,seed=cfg['seed'],repetition=0,
            acceptance=result['acceptance'],receipt=receipt,evaluation=result['evaluation_reference'],
            profile=result['profile_reference'],simulation=result['raw_reference'],
            evaluation_data=host.store.artifact(result['evaluation_reference']),profile_summary=result['profile']))
        by_condition[condition_id]=reference
        views.append(result_view(host,reference))
        schedule.append(dict(case_id=condition_id,seed=cfg['seed'],repetition=0,
            task_family=cfg['task']['family'],task_identity=digest(cfg['task']),
            protocol_id=task_adapter(cfg).execution_requirements()['protocol_id']))
    if set(by_condition)!={c['condition_id'] for c in conditions}:
        raise ValueError('ALL_FROZEN_TASK_CONDITIONS_REQUIRED')
    heterogeneous=len({(c['task_family'],c['protocol_id']) for c in schedule})>1
    schedule=sorted(schedule,key=lambda slot:next(i for i,c in enumerate(conditions) if c['condition_id']==slot['case_id']))
    if not heterogeneous:schedule=[{k:v for k,v in row.items() if k in ('case_id','seed','repetition')} for row in schedule]
    aggregate=aggregate_acceptance(records,len(conditions),schedule=schedule,
        condition_contract='heterogeneous_conditions_v1' if heterogeneous else None)
    if not aggregate['all_scheduled_accepted']:raise ValueError('ALL_CONDITION_ACCEPTANCE_REQUIRED')
    return dict(kind='joint_condition_result_v1',**(dict(version='2.0.0') if heterogeneous else {}),status='evaluated',candidate=root,owning_study=host.run_id,
        condition_results=[by_condition[c['condition_id']] for c in conditions],aggregation=aggregate,
        task_gap=_joint_gap(views,condition_ids=list(by_condition),heterogeneous=heterogeneous),
        costs={key:sum(r['receipt']['charged'][key] for r in records) for key in records[0]['receipt']['charged']},
        cost_scope='Sum of independent condition receipts; initialization and Native search remain in the cumulative Study ledger.')


def register_joint_result(host, references):
    value=joint_assessment(host,references)
    ref=save(host,value,'joint_condition_result')
    s=state(host)
    if ref not in s.get('joint_results',[]):update(host,joint_results=[*s.get('joint_results',[]),ref])
    return ref


def _joint_gap(rows, *, condition_ids=None, heterogeneous=False):
    if heterogeneous:
        return dict(normalized_gap=None,components={},common_scale=False,
            condition_gaps={key:row['task_gap'] for key,row in zip(condition_ids,rows)},
            valid_complete=all(r['task_gap']['valid_complete'] for r in rows),accepted=all(r['passed'] for r in rows),
            dominant_constraints=[dict(study_condition_id=key,**d) for key,row in zip(condition_ids,rows)
                for d in row['task_gap']['dominant_constraints']],
            interpretation='Per-condition TaskGap and joint acceptance only; no declared common scientific ranking scale.')
    gaps=[r['task_gap']['normalized_gap'] for r in rows]
    return dict(normalized_gap=max(gaps) if all(g is not None for g in gaps) else None,
        components={str(i)+':'+k:v for i,r in enumerate(rows) for k,v in r['task_gap']['components'].items()},
        valid_complete=all(r['task_gap']['valid_complete'] for r in rows),accepted=all(r['passed'] for r in rows),
        dominant_constraints=[d for r in rows for d in r['task_gap']['dominant_constraints']])


def joint_view(host, reference):
    from tools.research.feedback import result_view
    value=host.store.artifact(reference)
    rows=[result_view(host,r) for r in value['condition_results']]
    view=deepcopy(rows[0])
    identity=dict(conditions=[r['solution_identity'] for r in rows])
    passed=all(r['passed'] for r in rows) and value['aggregation']['all_scheduled_accepted']
    heterogeneous=value['aggregation']['version']=='2.0.0'
    condition_ids=[r['case_id'] for r in value['aggregation']['schedule']]
    gap=_joint_gap(rows,condition_ids=condition_ids,heterogeneous=heterogeneous)
    view.update(candidate=value['candidate'],evidence=plain(reference),condition_results=value['condition_results'],
        complete=all(r['complete'] for r in rows),passed=passed,task_gap=gap,
        task_performance='passed' if passed else 'failed',failed_metrics=[m for r in rows for m in r['failed_metrics']],
        controller_route='joint_conditions',controller=dict(route='joint_conditions',conditions=[r['controller'] for r in rows]),
        solution_identity=identity,solution_identity_sha256=digest(identity),
        fresh_current_study=all(r['fresh_current_study'] for r in rows),costs=value['costs'],
        aggregation=value['aggregation'],evaluation_evidence=dict(reference=plain(reference),conditions=value['condition_results']))
    if heterogeneous:
        view.update(task=dict(family='heterogeneous_conditions',conditions=[dict(condition_id=key,task=row['task'])
            for key,row in zip(condition_ids,rows)]),metrics={},
            condition_metrics={key:row['metrics'] for key,row in zip(condition_ids,rows)})
    return view
