"""Operator composition of existing transport transition; never authors science."""
import os
for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[name]='1'
import asyncio,json,sys,time
from copy import deepcopy
from pathlib import Path
from tools.state_io import read,atomic_json,digest
from tools.research.state import state,save,guard
from tools.research.provider import transition_transport
from tools.research.session_handoff import assess_live_admission,admit_formal_study
from tools.research import core
from tools.platform_host import Host

ROOT=Path(__file__).resolve().parents[3]
DOC=Path(__file__).resolve().parent
NAME='p3-passive-progressive-stiffness-autonomous-20261110-v1_2'
SOURCE='phs2d-workflow-successor-20261106'

def host():return Host(ROOT/'runs/research'/NAME,NAME,actor='user-authorized-official-api-continuation')

def invariant(h):
    s=state(h);spec=deepcopy(s['spec'])
    for key in ('resolved_identity','authorization_addenda'):spec.pop(key,None)
    spec['runtime'].pop('provider');spec['runtime'].pop('credentials_reference')
    spec['configuration']['policy'].pop('model')
    keys=('profile','candidates','plans','results','physical_replays','analysis_results','search_results',
          'mathematical_evaluations','numerical_s','pending','success_gate','selected')
    return dict(scientific_spec_identity=digest(spec),state_fields={k:s.get(k) for k in keys},
        ledger=h.store.remaining(),framework_session_id=s['pilot'].get('framework_session_id'))

def before():
    h=host();guard(h);s=state(h)
    with h.store.connect(True) as db:
        assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0
    assert not s['pending'] and not s['pilot'].get('unconsumed_response')
    value=dict(study_id=NAME,invariant=invariant(h),previous_provider=s['spec']['runtime']['provider'],
        previous_resolved_identity=s['spec']['resolved_identity'],timestamp_unix=time.time(),
        catalog_check=dict(endpoint='https://api.openai.com/v1/models',http_status=200,
            model='gpt-5.6-sol',model_available=True,inference_requests_sent=0))
    atomic_json(DOC/'official-api-continuation-before.json',value)
    print(json.dumps(dict(ready=True,ledger=value['invariant']['ledger'],inference_requests_sent=0)))

def apply():
    h=host();baseline=read(DOC/'official-api-continuation-before.json')
    assert invariant(h)==baseline['invariant']
    s=state(h);runtime=read(ROOT/'configs/research/runtime_phs2d_workflow_successor_20261106.json')
    scope=dict(study_id=NAME,resolved_identity=s['spec']['resolved_identity'],
        previous_provider_identity=digest(s['spec']['runtime']['provider']),
        provider=runtime['provider'],credentials_reference=runtime['credentials_reference'])
    approval=dict(version='provider_transport_approval_v1',approved=True,
        source='User 2026-11-10: 使用官方API接续. Continue the same Study using the existing official API credential; retain model, reasoning, scientific scope and original 80-send shared budget. No push.',
        scope=scope,scope_identity=digest(scope))
    transition=transition_transport(h,approval)
    core.bind(h,reason='User-authorized official API transport continuation after Gateway quota exhaustion; same model, scientific requirements, SDK session and complete ledger.')
    assert invariant(h)==baseline['invariant']
    evidence=assess_live_admission(h,ROOT.parent/'stage2-research-workflow-20261106/runs/research'/SOURCE,SOURCE)
    evidence_ref=save(h,evidence,'handoff_transport_evidence');s=state(h)
    scope=dict(study_id=NAME,resolved_identity=s['spec']['resolved_identity'],implementation_freeze=s['freeze'],
        capabilities=s['spec']['capabilities'],execution_scopes=['registered mathematics','physical replay','request-feedback session handoff'],
        session_handoff=dict(boundary='request_feedback',evidence=evidence_ref),provider_requests=80,
        protected_provider_requests=0,provider_extension_authorized=False)
    grant=save(h,dict(user_approval=approval['source'],scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    admission=admit_formal_study(h,grant);guard(h)
    from tools.research.agent import converse
    asyncio.run(converse(h,session_handoff=True,restore_only=True))
    assert invariant(h)==baseline['invariant']
    value=dict(study_id=NAME,transition=transition,admission=admission,authorization=grant,
        invariant_preserved=True,invariant=invariant(h),implementation=state(h)['freeze'],
        provider=state(h)['spec']['runtime']['provider'],sdk_restore=True,provider_requests_sent=0,timestamp_unix=time.time())
    atomic_json(DOC/'official-api-continuation-bound.json',value)
    print(json.dumps(dict(bound=True,invariants_preserved=True,sdk_restore=True,provider_requests_sent=0)))

if __name__=='__main__':globals()[sys.argv[1]]()
