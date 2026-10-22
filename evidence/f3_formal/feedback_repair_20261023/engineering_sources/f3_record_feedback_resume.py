"""Non-secret proof of committed real handoff and healthy original-Study resumption."""
import json
import time
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.state import state,save
from tools.research.agent import received
from tools.rl.run import process_birth
from tools.state_io import read,atomic_json
h=Host(ROOT/'runs/research/f3-autonomous-20261022-01','f3-autonomous-20261022-01',actor='unified-research')
proof=read(ROOT/'runs/f3-request-handoff-verification.json');s=state(h);status=read(ROOT/'runs/f3-formal-supervision.json')
p=h.store.artifact(proof['preparation']);wire=h.store.artifact(proof['wire_reference'])
packet=json.loads(wire['messages'][-1]['content'].split('\n',1)[1]);r=packet['research']
assert p['version']=='research_session_handoff_v3' and p['boundary_kind']=='request_feedback' and p['invocation_completed'] is False
assert received(h,proof['provider_request'])['http_status']==200
assert r['mathematics_authorization']['registered_study_scope_authorized'] is True
assert r['recorded_evidence_corrections']['version']=='engineering_evidence_feedback_correction_v1'
assert packet['candidate_profile_bindings'] and packet['evaluation_profile']['version']==2
assert r['budget']['provider_budget']['remaining_total']==128-p['budget']['used']['model_calls']
assert process_birth(status['pid'])==status['birth'] and process_birth(status['cli_pid'])==status['cli_birth']
value=dict(study_id=h.run_id,freeze=s['freeze'],observed_unix=time.time(),
    live_admitted=s['pilot']['session_handoff_live_admitted'],evaluation_version=s['profile']['version'],
    first_real_handoff=proof,provider_used_at_rotation=p['budget']['used']['model_calls'],
    first_post_handoff_request_bytes=len(json.dumps(wire,separators=(',',':'),ensure_ascii=False).encode()),
    first_post_handoff_http_status=200,evidence_corrections_delivered=True,formal_math_grant_delivered=True,
    t2_readiness=r['optimal_sensitivity_readiness']['status'],
    first_post_handoff_provider_remaining=r['budget']['provider_budget']['remaining_total'],
    current_provider_used=s['pilot']['live_model_requests'],current_physical_used=h.store.remaining()['used']['backend_solves'],
    nmpc_launches=s['nmpc_launches'],supervisor_alive=True,main_cli_alive=True,
    heartbeat='runs/f3-formal-supervision.json',heartbeat_interval_s=10,
    original_configuration_and_budgets_retained=True,raw_session_exports_published=False,
    scope='After resuming the settled native session, a genuine tool-feedback boundary was rotated before the following request. The original invocation was suspended, not marked complete. No retrospective task pass or model-understanding guarantee is claimed.')
save(h,value,'feedback_repair_real_resume_verification')
atomic_json(ROOT/'evidence/f3_formal/feedback_repair_20261023/live_resume_verification.json',value)
print(json.dumps(value))
