"""Existing explicit core migration; preserve original Study/evidence/charges."""
from copy import deepcopy
import json
import subprocess
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.core import bind
from tools.research.state import state,save,science_hashes,core_hashes
from tools.research.agent import decision_packet,pending
from tools.state_io import atomic_json,read,digest
h=Host(ROOT/'runs/research/f3-autonomous-20261022-01','f3-autonomous-20261022-01',actor='unified-research')
before=state(h);ledger=h.store.remaining();checkpoint=read(ROOT/'runs/f3-request-boundary-checkpoint-20261023/state.json')
assert before['freeze']=='bc480c62f19bb3613003ec7dc03dbf04658f8816'
assert not before['pending'] and not pending(h) and not before['pilot'].get('unconsumed_response')
assert ledger==read(ROOT/'runs/f3-request-boundary-checkpoint-20261023/ledger.json')
assert [k for k in before.keys()|checkpoint.keys() if before.get(k)!=checkpoint.get(k)]==['engineering_feedback_correction']
atomic_json(ROOT/'runs/f3-feedback-pre-migration-state.json',before)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
reason=('User-authorized F3 engineering repair and request-feedback handoff. Fix MATLAB singleton-row loss before control input selection, reject scalar tendon broadcasting, invalidate malformed prediction diagnostics, preserve complete mathematics/residual/scope feedback and exact evidence navigation, repair Reporter source-catalog admission and separate formal mathematics grant from method prerequisites. Actual control behavior changes: increment evaluation profile, retain all old candidates/results/acceptance/costs and require new current-profile candidates for future execution. No strategy/candidate is chosen by the supervisor; original frozen task/family/configuration and all budgets unchanged.')
bind(h,reason,before['spec'])
after=state(h)
allowed={'freeze','core_hashes','core_repairs','validation_extension_pending_binding','scientific_dependencies','profile','profile_history','research_history_imported'}
changed=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
assert not set(changed)-allowed,changed
assert after['profile']['version']==before['profile']['version']+1
assert after['profile_history'][:-1]==before['profile_history']
assert after['spec']==before['spec'] and h.store.remaining()==ledger
assert core_hashes()==after['core_hashes'] and science_hashes()==after['profile']['science_hashes'] and h.compatibility()['compatible']
old_grant=read(ROOT/'runs/f3-continuous-authorization-ref.json');grant=deepcopy(h.store.artifact(old_grant))
grant['scope']['freeze']=commit;grant['scope_identity']=digest(grant['scope']);grant['previous_authorization']=old_grant
grant['source']='Existing user authorization for continuous engineering repair/recovery, ordinary pushes and real model calls within this original Study; latest user clarified approved registered mathematics versus missing T2 materials. This successor follows the tested explicit migration; limits unchanged.'
grant['implementation_migration']=after['core_repairs'][-1]
authorization=save(h,grant,'continuous_engineering_authorization');atomic_json(ROOT/'runs/f3-continuous-authorization-ref.json',authorization)
packet=decision_packet(h)
assert packet['research']['mathematics_authorization']['registered_study_scope_authorized'] is True
assert packet['evaluation_profile']['identity']==after['profile']['identity']
assert packet['candidates'] and all(not r['executable_under_current_profile'] for r in packet['candidate_profile_bindings'])
assert packet['research']['optimal_sensitivity_readiness']['status']=='requires_current_profile_candidate'
assert h.store.remaining()==ledger
value=dict(study_id=h.run_id,previous_freeze=before['freeze'],freeze=commit,
    resolved_identity=after['spec']['resolved_identity'],changed_state_keys=changed,
    previous_profile=before['profile']['identity'],profile=after['profile']['identity'],evaluation_version=after['profile']['version'],
    core_repair=after['core_repairs'][-1],standing_authorization=authorization,
    old_science_and_costs_retained=True,original_configuration_and_budget_unchanged=True,
    provider_used=ledger['used']['model_calls'],physical_used=ledger['used']['backend_solves'],nmpc_launches=after['nmpc_launches'],
    current_l0_identity=digest(packet),historical_candidates_retained_without_silent_rebinding=True,
    no_new_provider_request_or_science=True)
save(h,value,'feedback_repair_migration_verification');atomic_json(ROOT/'runs/f3-feedback-migration-result.json',value)
atomic_json(ROOT/'evidence/f3_formal/feedback_repair_20261023/implementation_binding.json',value)
print(json.dumps(value))
