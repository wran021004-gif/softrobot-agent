"""Re-read saved evidence and revalidate saved Reporter output; no new science/send."""
import json
from types import SimpleNamespace
import httpx
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state,save,update
from tools.research.agent import pending,received,record
from tools.research.core import read_evidence
from tools.research.evidence_views import recorded_math_summary,recorded_control_diagnostics,data_access,recorded_static_summary
from tools.research.research_context import mathematics_authorization,resolved_candidate_facts,ordered_candidates
from tools.research import reporter
from tools.state_io import atomic_json,digest

h=Host(ROOT/'runs/research/f3-autonomous-20261022-01','f3-autonomous-20261022-01',actor='unified-research')
s=state(h);ledger=h.store.remaining()
assert not s['pending'] and not pending(h) and not s['pilot'].get('unconsumed_response')
folder=ROOT/'evidence/f3_formal/feedback_repair_20261023';folder.mkdir(parents=True,exist_ok=True)
originals={r['artifact_id']:digest(h.store.artifact(r)) for key in ('results','physical_replays','analysis_results','mechanics_results') for r in s.get(key,[])}
math=[dict(reference=r,summary=recorded_math_summary(h.store.artifact(r),r)) for r in s.get('mechanics_results',[])]
static=[dict(reference=r,summary=recorded_static_summary(h.store.artifact(r),r)) for r in s.get('analysis_results',[])]
controls=[]
for ref in s['results']:
    value=h.store.artifact(ref);diagnostic=recorded_control_diagnostics(h,value)
    access=data_access(h,ref,value)
    for query in access['queries']:read_evidence(h,query,record_read=False)
    # Every advertised per-update location is executable, with exactly the saved binding.
    for row in access['updates']:
        observation=read_evidence(h,row['observation_query'],record_read=False)
        assert observation['time_s']==row['time_s']
    controls.append(dict(reference=ref,original_acceptance=value['acceptance'],diagnostic=diagnostic,
        executable_navigation_verified=True,raw_acceptance_unchanged=True))
reviews=[]
events=h.store.events(h.run_id)
for event in events:
    if event['kind']!='r3_request':continue
    meta=h.store.artifact(event['outputs'][0])
    if meta['purpose']!='reporter':continue
    reception=received(h,event['request_id']);wire=h.store.artifact(meta['request'])
    payload=json.loads(wire['messages'][-1]['content']);base=payload['report_reference']
    old=[(r,v) for r,v in reporter.entries(h) if v.get('interpretation_for')==base and v['interpretation_status']=='unavailable']
    if not old:continue
    body=h.store.artifact(reception['body'],raw=True);output=json.loads(body)['choices'][0]['message']['content']
    catalog=payload.get('source_catalog',{});ids=[key for row in json.loads(output)['interpretations'] for key in row.get('source_ids',[])]
    assert ids and all(key in catalog for key in ids)
    prior=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='reporter_saved_output_revalidation'
        and h.store.artifact(e['outputs'][0])['original_provider_request']==event['request_id']]
    if prior:review=prior[-1]
    else:
        revision=reporter._finish(h,SimpleNamespace(last_request=event['request_id']),wire,
            httpx.Response(reception['http_status'],content=body))
        assert h.store.artifact(revision)['interpretation_status']=='available'
        review=dict(original_provider_request=event['request_id'],original_unavailable_report=old[0][0],
            revalidated_revision=revision,source_catalog=meta['request'],original_response=reception['body'],
            all_source_ids_were_in_original_catalog=True,new_provider_requests=0,
            scope='Revalidation of saved original output after source-catalog gate repair. Original unavailable revision and original delivery history retained; this revision was not available to earlier decisions.')
        record(h,'reporter_saved_output_revalidation',review)
    reviews.append(review)
authorization=mathematics_authorization(h,s)
assert authorization['registered_study_scope_authorized'] is True
correction=dict(version='engineering_evidence_feedback_correction_v1',
    mathematics_authorization=authorization,
    mathematics=math,static_constructions=static,
    historical_control_updates=[dict(reference=row['reference'],
        invalid_prediction_updates=row['diagnostic']['invalid_prediction_updates'],
        accepted_plan_input_mismatch_updates=row['diagnostic']['accepted_plan_input_mismatch_updates'],
        prediction_aggregate_available=row['diagnostic']['prediction_aggregate_available'],
        terminal_update=row['diagnostic']['relevant_updates'][-1],
        full_observations_query=row['diagnostic']['full_observations_query']) for row in controls],
    reporter_saved_output_revalidation=reviews,
    scope='Deterministic corrections from immutable current-Study evidence. Historical physical acceptance is unchanged. Tiny positive violations remain strict false, not an infeasibility proof. No counterfactual successful rollout, complete-update contract, new method prerequisites or causal mechanism is fabricated.')
correction_ref=save(h,correction,'engineering_evidence_feedback_correction')
update(h,engineering_feedback_correction=correction_ref)
assert h.store.remaining()==ledger
assert state(h)['spec']==s['spec']
assert originals=={r['artifact_id']:digest(h.store.artifact(r)) for key in ('results','physical_replays','analysis_results','mechanics_results') for r in s.get(key,[])}
for name,value in [('recorded_evidence_correction.json',correction),('control_diagnostics.json',controls),
        ('reporter_revalidation.json',reviews),('verification.json',dict(study_id=h.run_id,
            provider_used=ledger['used']['model_calls'],physical_used=ledger['used']['backend_solves'],
            ledger_unchanged=True,original_scientific_artifacts_unchanged=True,all_advertised_queries_executed=True,
            reporter_revalidated_without_send=len(reviews),correction_reference=correction_ref,
            no_new_science_or_provider_requests=True))]:atomic_json(folder/name,value)
print(json.dumps(dict(correction=correction_ref,revalidated=len(reviews),controls=len(controls),ledger_unchanged=True)))
