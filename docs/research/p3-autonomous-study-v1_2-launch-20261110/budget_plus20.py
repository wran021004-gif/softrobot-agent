"""Apply exactly the user's 20-request addendum through the existing ledger."""
import os
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[key]='1'
import asyncio,json,runpy,sys,time
from copy import deepcopy
from pathlib import Path
from tools.state_io import read,atomic_json,digest
from tools.research.state import state,save,guard
from tools.research.budget import extend_provider_requests
from tools.research.session_handoff import admit_formal_study
from tools.research import core

DOC=Path(__file__).resolve().parent
prior=runpy.run_path(str(DOC/'official_api.py'))
NAME=prior['NAME'];host=prior['host']
APPROVAL='User 2026-11-10: 增加20次请求预算. Add exactly 20 shared Main/Reporter requests to this same Study, raising its total from 80 to 100; continue on Gateway account3. Preserve every used cost, failure, candidate, result, SDK session and scientific requirement. No future batch granted. No push.'

def invariant(h):
    s=state(h);spec=deepcopy(s['spec'])
    for key in ('resolved_identity','authorization_addenda'):spec.pop(key,None)
    spec['budgets'].pop('provider_requests');spec['configuration']['policy']['budget'].pop('model_calls')
    value=prior['invariant'](h)
    value['scientific_spec_identity']=digest(spec)
    value['ledger']=dict(used=value['ledger']['used'],occupied=value['ledger']['occupied'])
    return value

def settled(h):
    s=state(h)
    assert not s.get('pending') and not s['pilot'].get('unconsumed_response')
    with h.store.connect(True) as db:
        assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0

def before():
    h=host();settled(h);guard(h);s=state(h)
    assert s['spec']['budgets']['provider_requests']==80
    value=dict(study_id=NAME,invariant=invariant(h),ledger=h.store.remaining(),
        resolved_identity=s['spec']['resolved_identity'],additional_requests=20,new_total=100,timestamp_unix=time.time())
    atomic_json(DOC/'budget-plus20-before.json',value)
    print(json.dumps(dict(ready=True,ledger=value['ledger'],provider_requests_sent=0)))

def apply():
    h=host();settled(h);baseline=read(DOC/'budget-plus20-before.json');assert invariant(h)==baseline['invariant']
    s=state(h);events=h.store.events(NAME)
    prior_grant=next(h.store.artifact(e['outputs'][0]) for e in reversed(events)
        if e['kind']=='formal_study_authorization' and h.store.artifact(e['outputs'][0])['scope']['resolved_identity']==s['spec']['resolved_identity'])
    scope=dict(study_id=NAME,resolved_identity=s['spec']['resolved_identity'],previous_request_limit=80,additional_requests=20)
    extension=extend_provider_requests(h,dict(version='provider_request_extension_approval_v2',approved=True,
        source=APPROVAL,scope=scope,scope_identity=digest(scope)))
    core.bind(h,reason='Explicit user +20 shared Provider requests: 80 to 100, all science, account3 transport, costs, failures and evidence retained.')
    assert invariant(h)==baseline['invariant']
    assert h.store.remaining()['limit']['model_calls']==100
    s=state(h);scope=deepcopy(prior_grant['scope'])
    scope.update(resolved_identity=s['spec']['resolved_identity'],implementation_freeze=s['freeze'],provider_requests=100)
    grant=save(h,dict(user_approval=APPROVAL,scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    admission=admit_formal_study(h,grant);guard(h)
    from tools.research.agent import converse
    asyncio.run(converse(h,session_handoff=True,restore_only=True))
    assert invariant(h)==baseline['invariant']
    atomic_json(DOC/'budget-plus20-bound.json',dict(study_id=NAME,extension=extension,admission=admission,
        authorization=grant,implementation=s['freeze'],invariant_preserved=True,sdk_restore=True,
        provider_requests_sent=0,ledger=h.store.remaining(),timestamp_unix=time.time()))
    print(json.dumps(dict(extended=True,new_total=100,ledger=h.store.remaining(),invariants_preserved=True,sdk_restore=True)))

if __name__=='__main__':globals()[sys.argv[1]]()
