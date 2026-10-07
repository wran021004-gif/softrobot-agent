"""Read-only factual review of the existing continuation, without live dispatch."""
from pathlib import Path
import json,time
from tools.platform_store import Store
from tools.state_io import read,atomic_json,digest
from tools.candidate_parameters import parameter_value

root=Path('runs/research_native_development_v3_20261007').resolve()
out=Path('evidence/research_native_development_v3_20261007/continuation_20261007').resolve()
store=Store(root);run='research_native_development_v3_20261007-research'
session=store.session(run);state=read(root/'scheduler_state.json')
delivery=read(out/'campaign_delivery.json')
with store.connect(True) as db:calls=[dict(r) for r in db.execute('SELECT * FROM calls ORDER BY rowid')]
new_models=[r for r in calls if r['run_id']==run and r['request_id'] in ('model-4','model-5')]
backends=[r for r in calls if json.loads(r['charged'])['backend_solves']]
assert len(backends)==2 and {r['execution_id'] for r in backends}=={
    '871e8b83c5d14f9ba813fb65dcb0cc29','ed8e838859714c17930b16ba7a46e8e1'}
assert len(new_models)==2 and all(r['status']=='completed' and r['receipt'] for r in new_models)
assert state['status']=='failed' and state['repairs']==4 and not state['sealed_cases']
assert state['stop_reason']=='CONSTRAINED_PARAMETER_MISSING: design/near_section_scale'
batch=session['state']['search_batch']
assert not batch['proposals'] and batch['pending'] is None
missing=[]
for h in batch['historical_results']:
    try:parameter_value(store.artifact(h['facts']['configuration'])['effective'],'design/near_section_scale')
    except ValueError as exc:missing.append(dict(execution_id=h['execution_id'],error=str(exc)))
new_round=next(r for r in state['rounds'] if r['index']==2)
assert new_round['decision']['decision']['action']=='structure_search'
assert new_round['decision']['decision']['plan']['candidates']==[
    {'design/near_section_scale':1.0},{'design/near_section_scale':1.05}]
boundary=read(out/'dependency_migration_boundary.json')
assert store.artifact(boundary['migration']['before_snapshot'])['input']==store.artifact(boundary['migration']['after_snapshot'])['input']
clock=read(root/'live_clock.json');assert clock==read(out/'authorization.json')['clock']
assert clock['origin_unix']==1791341029.4261196 and clock['deadline_unix']==1791377029.4261196
old=read(out.parent/'reviewed_delivery.json')['costs']['final_settled_usage']
known={k:delivery['known_token_subtotal'][k]-read(out.parent/'reviewed_delivery.json')['costs']['known_token_subtotal'][k]
       for k in ('prompt_tokens','completion_tokens','total_tokens')}
issues=[
    dict(location='model-4 same-condition comparison rationale',
         review='The unchanged incumbent was historical and task identities differ (unspecified-zero vs explicit-zero). Arithmetic differences are descriptive, not a fresh matched reference; no new incumbent execution occurred.'),
    dict(location='model-4 two control axes bracketed / untested structure claims',
         review='Finite terminal-weight points and historical holding-weight points do not exhaust continuous axes or prove structural search has highest information. A changed near-section perturbed event exists in history; zero new structural execution occurred in this continuation.'),
    dict(location='model-4 eligibility wording',
         review='The frozen host selection rule allows an effective changed fresh nominal joint pass nondominated among eligible search rows; it does not require componentwise dominance over the incumbent. The existing terminal=.10 point remains eligible despite a historical tradeoff; no protocol change or promotion was adopted.'),
    dict(location='model-5 changed terminal/holding weight scope',
         review='Both completed current research executions changed terminal tip-speed weight only; holding weight remained .05 and physical structure was unchanged.'),
    dict(location='model-5 previous unaccepted draft / STOP',
         review='model-4 was accepted and its immutable structure_search plan was recorded. Execution then failed before apply or backend dispatch. model-5 is STOP-only fault reporting, not a free scientific successor or executed research seal.'),
]
result=dict(version='v3-continuation-review@3.3.0',status='sealed_engineering_stop',
    source_attachment=read(out/'authorization.json')['source_attachment'],
    same_campaign=True,same_session=True,grant_unchanged=True,clock=clock,
    live_elapsed_s=time.time()-clock['origin_unix'],deadline_remaining_s=clock['deadline_unix']-time.time(),
    original_answers_unchanged=True,prior_checkpoint_preserved=True,
    new_provider_calls=[dict(request_id=r['request_id'],execution_id=r['execution_id'],
        charged=json.loads(r['charged']),effect='Accepted freely chosen feedback-linked structure_search' if r['request_id']=='model-4' else 'Accepted STOP-only engineering fault report, not executed as scientific STOP') for r in new_models],
    incremental_backend_attempts=0,cumulative_backend_attempts=2,old_backend_execution_ids=[r['execution_id'] for r in backends],
    feedback=dict(free_successor_obtained=True,second_batch_planned=True,second_batch_executed=False,
        accepted_plan=new_round['accepted_decision'],method='search.family_explicit@1.0.0',
        candidates=new_round['decision']['decision']['plan']['candidates'],batch_id=batch['batch_id'],
        candidates_prepared=0,backend_dispatched=0),
    engineering=dict(previous_repairs=2,additional_authorized_repairs_used=2,cumulative_repairs=4,
        repair1=read(out/'continuation_repair_boundary.json')['receipt'],repair2=boundary['receipt'],
        unresolved=dict(location='tools/platform_search.py:_run_batch historical known-point loop',
            operation='parameter_value(saved historical effective, design/near_section_scale)',
            missing_historical_selectors=missing),further_live_repairs_authorized=False),
    mathematics=dict(new_standalone_numerical_operations=0,method='Model-authored finite enumeration and recorded arithmetic differences; not executed mathematical optimization',
        retained_support='Frozen normalized squared tip-speed objective interpretation; retained M5 forecast evidence has no screening authority',
        unexercised=['Quantitative optimizer','New linearization/endpoint calculation','New retained diagnostic query','Structural backend execution','Fresh matched verification']),
    verification=read(out/'verification_not_started.json'),issues=issues,
    corrections=dict(total=session['state'].get('protocol_corrections_used',0),
        consecutive=session['state'].get('protocol_corrections_consecutive',0),new_protocol_corrections=0,
        transport_retries_total=session['state'].get('transport_retries_used',0),new_transport_retries=0),
    usage_at_driver_export=delivery['usage'],incremental_driver_export_usage={k:delivery['usage']['used'][k]-old['used'][k] for k in old['used']},
    incremental_known_provider_tokens=known,cumulative_known_provider_tokens=delivery['known_token_subtotal'],
    token_unknowns=False,monetary_billing='unknown',standalone_numerical_operations=0,workers=0,additional_roles=0,
    next_task='Offline historical known-point selector projection at _run_batch, using saved records and current planning policy with unchanged physical scope. Further paid execution needs explicit new repair authorization and must use this same ledger and original clock if still valid; never replay old completed attempts or treat the accepted plan as completed experiments.',
    limitations=['Development observations only','No robustness/superiority/global-optimality/causality claim','No hardware or real-time deployment claim','Research roadmap remains incomplete'])
atomic_json(out/'independent_live_review.json',result)
print(json.dumps(dict(status=result['status'],new_models=len(new_models),new_backends=0,
    corrections=result['corrections'],incremental_tokens=known,issues=len(issues)),ensure_ascii=False))
