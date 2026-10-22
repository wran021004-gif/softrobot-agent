"""Explicit core-only follow-up for Provider string / SDK text-part equivalence."""
from copy import deepcopy
import json
from tools.platform_host import Host
from tools.research.config import ROOT
from tools.research.core import bind
from tools.research.state import state,save
from tools.state_io import read,atomic_json,digest
h=Host(ROOT/'runs/research/f3-autonomous-20261022-01','f3-autonomous-20261022-01',actor='unified-research')
before=state(h);ledger=h.store.remaining()
assert before['freeze']=='07fde5edb7596f9c05b10964053d555ee0c8d831'
assert not before['pilot'].get('session_handoff_live_admitted')
bind(h,'Real read-only handoff admission found exact Provider response text represented by SDK as a list of text parts. Canonicalize only string/text-part representation while preserving exact text, reasoning, tool IDs and parsed arguments. No request was sent on the rejected admission. Core-only repair under existing continuous user authorization; science profile, all original costs/results/configuration retained.',before['spec'])
after=state(h)
assert after['profile']==before['profile'] and after['profile_history']==before['profile_history']
assert h.store.remaining()==ledger and after['spec']==before['spec']
prior=read(ROOT/'runs/f3-continuous-authorization-ref.json');grant=deepcopy(h.store.artifact(prior))
grant['scope']['freeze']=after['freeze'];grant['scope_identity']=digest(grant['scope'])
grant['previous_authorization']=prior;grant['implementation_migration']=after['core_repairs'][-1]
authorization=save(h,grant,'continuous_engineering_authorization')
atomic_json(ROOT/'runs/f3-continuous-authorization-ref.json',authorization)
value=dict(study_id=h.run_id,previous_freeze=before['freeze'],freeze=after['freeze'],
    science_profile_unchanged=True,evaluation_version=after['profile']['version'],ledger_unchanged=True,
    provider_used=ledger['used']['model_calls'],physical_used=ledger['used']['backend_solves'],
    core_repair=after['core_repairs'][-1],standing_authorization=authorization,no_new_provider_request_or_science=True)
save(h,value,'request_boundary_format_migration')
atomic_json(ROOT/'runs/f3-boundary-format-migration-result.json',value)
atomic_json(ROOT/'evidence/f3_formal/feedback_repair_20261023/boundary_format_binding.json',value)
print(json.dumps(value))
