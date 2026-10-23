"""Read-only post-run HTTP/STOP audit; no new Provider or physical execution."""
from collections import Counter
from datetime import datetime,timedelta,timezone
import json
import numpy as np
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state,core_hashes,science_hashes
from tools.research.agent import received,pending
from tools.research.evidence_policy import comparable_task
from tools.state_io import atomic_json,digest

h=Host(ROOT/'runs/research/f3-autonomous-20261022-01','f3-autonomous-20261022-01',actor='unified-research')
s=state(h);ledger=h.store.remaining();events=h.store.events(h.run_id)
selected=h.store.artifact(s['selected']);candidate=h.store.artifact(selected['candidate'])
raw=h.store.artifact(selected['raw_reference']);evaluation=h.store.artifact(selected['evaluation_reference'])
acceptance=selected['acceptance'];samples=raw['samples'];cfg=candidate['configuration']
assert s['research_status']=='stopped' and s['success_gate']['observed_task_pass'] and s['success_gate']['model_selection_complete']
assert acceptance['accepted'] and all(c['passed'] for c in acceptance['components'].values())
assert acceptance['issues']==acceptance['missing']==[] and not s['pending'] and not pending(h) and not ledger['occupied']
assert candidate['profile_identity']==s['profile']['identity'] and candidate['evaluation_version']==2
assert comparable_task(s['spec'],cfg['task'])==s['spec']['canonical_task']
assert raw['task_identity']==acceptance['task_identity']==digest(cfg['task'])
assert raw['candidate']==selected['candidate'] and raw['source_reference']==selected['source_reference']
assert raw['implementation']==selected['implementation']==s['freeze']
assert raw['status']=='completed' and raw['failure'] is None and raw['physics_steps']==700
assert core_hashes()==s['core_hashes'] and science_hashes()==s['profile']['science_hashes'] and h.compatibility()['compatible']
assert abs(samples[-1]['time_s']-.35)<1e-12 and len(samples)==36
holding=[row for row in samples if .30-1e-12<=row['time_s']<=.35+1e-12]
assert len(holding)==6
target=np.asarray(cfg['task']['goal']['data']['target_m'])
positions=np.asarray([row['tip_m'] for row in samples]);velocities=np.asarray([row['tip_velocity_m_s'] for row in samples])
assert positions.shape==velocities.shape==(36,3) and np.isfinite(positions).all() and np.isfinite(velocities).all()
assert np.allclose(np.linalg.norm(positions-target,axis=1),[row['position_error_m'] for row in samples],rtol=0,atol=1e-12)
assert np.allclose(np.linalg.norm(velocities,axis=1),[row['speed_m_s'] for row in samples],rtol=0,atol=1e-12)
metrics=dict(terminal_error_m=samples[-1]['position_error_m'],holding_max_error_m=max(row['position_error_m'] for row in holding),
    holding_max_speed_m_s=max(row['speed_m_s'] for row in holding))
assert metrics==acceptance['metrics']
assert metrics['terminal_error_m']<=.01 and metrics['holding_max_error_m']<=.01 and metrics['holding_max_speed_m_s']<=.02
assert all(len(row['actual_tension_n'])==4 and all(0<=x<=8 for x in row['actual_tension_n']) for row in samples)
counts=Counter();finishes=Counter();requests=[]
for event in events:
    if event['kind']!='r3_request':continue
    meta=h.store.artifact(event['outputs'][0]);response=received(h,event['request_id'])
    counts['no_saved_response' if response is None else 'HTTP_'+str(response['http_status'])]+=1
    if response is not None:
        body=json.loads(h.store.artifact(response['body'],raw=True))
        finishes.update(choice['finish_reason'] for choice in body['choices'])
        assert response['http_status']==200 and body['choices'] and 'error' not in body
        assert all(choice['finish_reason'] in ('tool_calls','stop') for choice in body['choices'])
        if event['sequence']>=816:
            requests.append(dict(sequence=event['sequence'],request_id=event['request_id'],purpose=meta['purpose'],
                http_status=response['http_status'],finish_reasons=response['finish_reasons'],receipt_settled=bool(h.store.lookup(h.run_id,event['request_id'])['receipt'])))
assert requests and all(r['receipt_settled'] for r in requests)
assert state(h)==s and h.store.remaining()==ledger
result=dict(study_id=h.run_id,investigation='HTTP 200 is successful transport; no current HTTP fault requiring recovery.',
    http_responses=dict(counts),finish_reasons=dict(finishes),post_handoff_requests=requests,
    historical_missing_response='One earlier response-loss request was separately authorized and locally settled; its cost and remote outcome unknown are retained.',
    actual_stop_cause='First fresh complete original-task physical pass, publicly read and selected by the main Agent; configured immediate success closeout.',
    status=s['research_status'],closed_at_shanghai=datetime.fromtimestamp(s['closed_unix'],timezone(timedelta(hours=8))).isoformat(),
    selected=s['selected'],candidate=selected['candidate'],source=selected['source_reference'],raw=selected['raw_reference'],
    metrics=metrics,limits=dict(position_m=.01,holding_speed_m_s=.02),holding_samples=6,physics_steps=700,
    all_original_acceptance_components_pass=True,raw_metrics_independently_cross_checked=True,
    current_profile_and_original_canonical_task_bound=True,no_pending_calls_or_leases=True,
    ledger=ledger,no_new_provider_or_science=True,sealed_state_and_ledger_unchanged=True,
    configured_repetitions=s['spec']['confirmation']['fresh_independent_repetitions'],
    scope='One complete simulated original-task pass. Repeatability, robustness, continuous-time guarantees and hardware performance remain unassessed. No sealed Study restart or budget reset performed.')
atomic_json(ROOT/'evidence/f3_formal/feedback_repair_20261023/http200_investigation.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('post_handoff_requests','ledger')}))
