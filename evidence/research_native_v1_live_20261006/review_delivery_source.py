"""Read-only delivery audit; no provider, numerical or backend operations."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.platform_store import Store
from tools.state_io import read, atomic_json, digest
from tools.research_tasks import assemble_acceptance

directory = Path(__file__).resolve().parent
store = Store(directory)
state = read(directory / 'scheduler_state.json')
freeze = read(directory / 'freeze.json')
out = Path(freeze['experiment']['evidence_directory'])
assert state['status'] != 'running', 'Review only the settled campaign'
with store.connect(True) as db:
    calls = [dict(r) for r in db.execute('SELECT run_id,request_id,status,receipt FROM calls')]
assert all(r['receipt'] for r in calls), 'Unsettled receipt'
receipts = [json.loads(r['receipt']) for r in calls]
events = store.events(freeze['research_host'])
model_calls = []
for event in events:
    if event['kind'] != 'model_request':
        continue
    response_event = next((e for e in events if e['kind']=='model_raw_response' and e['request_id']==event['request_id']), None)
    payload = store.artifact(event['inputs'][0])
    response = store.artifact(response_event['outputs'][0]) if response_event else None
    usage = (response or {}).get('raw', {}).get('usage')
    receipt = next(r for r in receipts if r['request_id']==event['request_id'])
    # Store JSON is canonical. Transport uses json.dumps(... ensure_ascii=False)
    # with default separators: same content, larger size, no wire-byte hash claim.
    transport_size = len(json.dumps(payload, ensure_ascii=False).encode('utf8'))
    model_calls.append(dict(request_id=event['request_id'],request_reference=event['inputs'][0],
        response_reference=response_event['outputs'][0] if response_event else None,
        receipt=receipt,canonical_request_utf8_bytes=len(store.artifact(event['inputs'][0],raw=True)),
        transport_serialization_utf8_bytes=transport_size,observed_provider_usage=usage,
        configured_model=payload['model'],observed_provider_model=(response or {}).get('raw',{}).get('model')))

def resolve(reference, pointer):
    value = store.artifact(reference)
    for token in pointer.split('/')[1:]:
        token = token.replace('~1','/').replace('~0','~')
        value = value[int(token)] if isinstance(value,list) else value[token]
    return value

checked = 0
round_reviews = []
for row in state['rounds']:
    result = row['decision']
    selectors = result['evidence_selectors'] + [s for o in result['verified_observations'] for s in o['evidence_selectors']]
    for selector in selectors:
        assert resolve(selector['reference'],selector['pointer']) == selector['value'], selector
        checked += 1
    round_reviews.append(dict(index=row['index'],action=row['kind'],
        accepted_reference=row['accepted_decision'],reasoning_status=result['scientific_reasoning_status'],
        exact_observations=len(result['verified_observations']),hypotheses=result['model_interpretations'],
        unresolved=result['unresolved_uncertainties'],feedback_reference=row.get('feedback_result')))

source = state['records'][0]
baseline = store.artifact(source['facts']['configuration'])['effective']
def physical_robot(effective):
    robot = deepcopy(effective['robot'])
    robot['structure']['data'].pop('metadata',None)
    return robot
outcomes = []
for record in state['records']:
    if record['source_store'] != str(directory):
        continue
    facts = record['facts']
    effective = store.artifact(facts['configuration'])['effective']
    profile = store.artifact(facts['report']['reference'])
    detail = profile.get('detail',profile)
    acceptance = assemble_acceptance(effective,store.artifact(facts['evaluation']),profile,
        evaluation_reference=facts['evaluation'],profile_reference=facts['report']['reference'],
        motion=store.artifact(detail['motion']))
    assert acceptance == record['acceptance']
    assert effective['task'] == baseline['task']
    assert physical_robot(effective) == physical_robot(baseline)
    assert effective['policy']['controller']['version'] == '7.0.0'
    assert effective['policy']['backend'] == baseline['policy']['backend']
    unchanged=deepcopy(effective['policy']['controller'])
    unchanged['parameters']['data']['recipe']['holding_tip_speed_weight']=baseline['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']
    assert unchanged == baseline['policy']['controller']
    outcomes.append(dict(candidate=facts['candidate'],case_id='nominal',seed=17,
        task_identity=digest(effective['task']),structure_identity=digest(effective['robot']),
        physical_structure_identity=digest(physical_robot(effective)),
        original_structure_identity=digest(baseline['robot']),
        metadata_only_normalization='Common section/material provenance expanded to disjoint per-segment selectors; physical structure unchanged',
        control_parameters=effective['policy']['controller']['parameters'],acceptance=acceptance,
        update_count=detail['updates'],accepted_noninitialization_plans=detail['accepted_noninitialization_plans'],
        real_time_demonstrated=detail['real_time_demonstrated'],mean_complete_update_s=detail['mean_update_s'],
        exact_source_conditions=True,acceptance_recomposed_from_original_sources=True))
provider_totals = {}
reasoning_tokens=0
for call in model_calls:
    for key, value in (call['observed_provider_usage'] or {}).items():
        if isinstance(value,int):provider_totals[key]=provider_totals.get(key,0)+value
    reasoning_tokens+=(call['observed_provider_usage'] or {}).get('completion_tokens_details',{}).get('reasoning_tokens',0)
request2=store.artifact(model_calls[1]['request_reference'])
request2_content=json.dumps(request2,ensure_ascii=False)
for outcome in outcomes:
    assert outcome['candidate']['execution_id'] in request2_content
    for value in outcome['acceptance']['metrics'].values():assert str(value) in request2_content
backend_receipts = [r for r in receipts if r['tool_id']=='simulation.run']
report = dict(version='native_pilot_delivery_review@1.0.0',status=state['status'],stop_reason=state['stop_reason'],
    model_calls=model_calls,provider_usage_known_subtotals=provider_totals,
    known_reasoning_tokens=reasoning_tokens,provider_usage_coverage=dict(known_requests=1,unknown_requests=1,aggregate_tokens_unknown=True),
    monetary_cost_not_reported=True,post_batch_input_contains_both_exact_outcomes=True,
    exact_selector_checks=checked,round_reviews=round_reviews,outcomes=outcomes,receipts=receipts,
    backend_attempts=len(backend_receipts),fresh_references=0,repetitions=0,
    source_retained_reference=dict(candidate=source['facts']['candidate'],new_charge=False),
    controller_updates_total=sum(o['update_count'] for o in outcomes),standalone_numerical_operations=0,
    usage=store.remaining(),workers=0,subagents=0,
    canonical_fact_identity_check=read(out/'delivery.json')['final_fact_identity']==read(out/'delivery.json')['working_fact_identity'],
    evaluation_scope='Sampled offline nominal response; no matched robustness, formal baseline or context-compression comparison')
atomic_json(out/'live_review.json',report)
print(json.dumps(dict(status=report['status'],model_calls=len(model_calls),backend_attempts=len(backend_receipts),
    provider_usage=provider_totals,selector_checks=checked,usage=report['usage']),ensure_ascii=False,indent=2))
