"""Bind fresh fixed-case receipts into the existing native working ledger."""
import json
from tools.research_spec import apply_frozen_case,load_spec
from tools.study_history import scientific_match
from extensions.tendon_family.gvs_profile import execution_scope
from extensions.tendon_family.delivery_facts import bound_result_facts


def verification_record(store, row, implementation, *, expected_configuration=None):
    """Require this project's actual receipts, not an imported scientific match."""
    receipt=row.get('receipt') or {}
    eid=receipt.get('execution_id'); owner=row['candidate_id']
    if not (eid and receipt.get('cache_hit') is False and receipt.get('charged',{}).get('backend_solves')==1):
        raise ValueError('VERIFICATION_REQUIRES_FRESH_CHARGED_RECEIPT')
    actual=store.lookup(owner,receipt['request_id'])
    if not actual or not actual.get('receipt') or json.loads(actual['receipt'])!=receipt:
        raise ValueError('VERIFICATION_RECEIPT_NOT_OWNED_BY_CURRENT_PROJECT')
    if not row.get('acceptance'):
        return None
    if receipt['execution_status']!='completed' or row['acceptance']['execution_id']!=eid:
        raise ValueError('VERIFICATION_ACCEPTANCE_EXECUTION_MISMATCH')
    effective=store.artifact(row['configuration'])['effective']
    cases=load_spec()['cases']
    expected=apply_frozen_case(expected_configuration or effective,row['case_id'],row['seed'],cases)
    if not scientific_match(effective,expected)['scientific_match']:
        raise ValueError('VERIFICATION_FROZEN_CONFIGURATION_OR_CASE_MISMATCH')
    reports=[r for r in row['receipts'] if r['tool_id']=='control.profile_report']
    if len(reports)!=1 or reports[0]['output']!=row['profile']:
        raise ValueError('VERIFICATION_PROFILE_RECEIPT_MISMATCH')
    for r in row['receipts']:
        call=store.lookup(owner,r['request_id'])
        if not call or not call.get('receipt') or json.loads(call['receipt'])!=r:
            raise ValueError('VERIFICATION_RECEIPT_NOT_OWNED_BY_CURRENT_PROJECT')
    candidate=dict(candidate_id=owner,owner_run_id=owner,execution_id=eid,configuration=row['configuration'])
    binding=dict(reference=row['profile'],owner_run_id=owner,execution_id=eid,request_id=reports[0]['request_id'])
    facts=bound_result_facts(store,dict(profile_report=binding,evaluation=row['evaluation'],simulation=receipt),candidate)
    if not facts:raise ValueError('VERIFICATION_COMPLETE_BOUND_FACTS_REQUIRED')
    from tools.platform_search import bound_acceptance
    if bound_acceptance(store,facts)!=row['acceptance']:
        raise ValueError('VERIFICATION_ACCEPTANCE_DIFFERS_FROM_SEALED_SOURCES')
    return dict(role='verification_'+row.get('verification_role',row['purpose']),phase='verification',facts=facts,acceptance=row['acceptance'],
        execution_id=eid,owner_run_id=owner,case_id=row['case_id'],seed=row['seed'],repetition=row['repetition'],
        implementation=implementation,execution_scope=execution_scope(effective),source_store=str(store.root),
        receipts={k:next(r for r in row['receipts'] if r['tool_id']==tool) for k,tool in
            dict(simulation='simulation.run',evaluation='evaluation.run',profile='control.profile_report').items()},
        reuse_reason='Fresh frozen verification observation; never search evidence or a cached repetition.')


def verification_view(progress, final_result=None):
    """Case/role/metric view, keeping full receipts in the existing archive."""
    view=dict(plan={k:v for k,v in progress['plan'].items() if k!='source_search'},
        outcomes=[dict(role=g['role'],candidate_id=r['candidate_id'],case_id=r['case_id'],seed=r['seed'],
            repetition=r['repetition'],execution_id=r.get('receipt',{}).get('execution_id'),
            status=r.get('acceptance',{}).get('status','pending_or_incomplete'),
            accepted=r.get('acceptance',{}).get('accepted'),metrics=r.get('acceptance',{}).get('metrics'),
            configuration=r.get('configuration')) for g in progress['groups'] for r in g['records']],
        usage=progress['usage'],scope='Fresh frozen verification phase; no reuse as search, no population claim.')
    if final_result is not None:
        view.update(complete=final_result['complete'],comparison=final_result['comparison'],
            improvement_supported=final_result['improvement_supported'],
            aggregates=[dict(role=g['role'],acceptance={k:v for k,v in g['acceptance'].items() if k!='entries'})
                        for g in final_result['aggregates']])
    return view


def incomplete_verification_experiments(progress, *, archive):
    result=[]
    for group in progress['groups']:
        for row in group['records']:
            if row.get('acceptance'):continue
            receipt=row.get('receipt') or {}
            if not receipt.get('execution_id'):continue
            result.append(dict(experiment_id=receipt['execution_id'],status='failed' if receipt.get('execution_status')=='failed' else 'incomplete',
                phase='verification',case_id=row['case_id'],seed=row['seed'],repetition=row['repetition'],
                role=group['role'],receipt=receipt,cache_hit=receipt.get('cache_hit'),
                recorded_result=archive.snapshot(row),observed_metrics=None))
    return result
