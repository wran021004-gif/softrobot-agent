"""Compose existing audited transport migration for the user-selected account."""
import os
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[key]='1'
import asyncio,json,runpy,sys,time
from pathlib import Path
from tools.state_io import read,atomic_json,digest
from tools.research.state import state,save,guard
from tools.research.provider import transition_transport
from tools.research.session_handoff import assess_live_admission,admit_formal_study
from tools.research import core

DOC=Path(__file__).resolve().parent
prior=runpy.run_path(str(DOC/'official_api.py'))
ROOT=prior['ROOT'];NAME=prior['NAME'];host=prior['host'];invariant=prior['invariant']
SOURCE='phs2d-topology-successor-20261106'
APPROVAL='User 2026-11-10: 切换成gateway第三个账号继续study. Use the existing third Gateway account on port8789 and continue the same Study, model and reasoning, preserving all scientific scope, SDK session, evidence and the original 80-send shared budget. No push.'

def settled(h):
    s=state(h)
    assert not s.get('pending') and not s['pilot'].get('unconsumed_response')
    with h.store.connect(True) as db:
        assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0

def before():
    h=host();settled(h);s=state(h)
    value=dict(study_id=NAME,invariant=invariant(h),previous_provider=s['spec']['runtime']['provider'],
        previous_resolved_identity=s['spec']['resolved_identity'],timestamp_unix=time.time(),
        target_account='account3',target_endpoint='http://127.0.0.1:8789/v1',
        catalog_check=dict(model='gpt-5.6-sol',model_available=True,inference_requests_sent=0))
    atomic_json(DOC/'gateway-account3-before.json',value)
    print(json.dumps(dict(ready=True,used=value['invariant']['ledger']['used']['model_calls'],provider_requests_sent=0)))

def apply():
    h=host();settled(h);baseline=read(DOC/'gateway-account3-before.json');assert invariant(h)==baseline['invariant']
    s=state(h);runtime=read(ROOT/'configs/research/runtime_phs2d_topology_successor_20261106.json')
    runtime['provider']['base_url']='http://127.0.0.1:8789/v1'
    runtime['provider']['model_capabilities']['catalog_source']='Account3 explicit user selection; authenticated GET /v1/models on 2026-11-10 confirmed gpt-5.6-sol. Existing Gateway function-tool and medium contract; real account3 research acceptance recorded separately.'
    runtime['credentials_reference']='~/.softrobot-agent/chatgpt-api-account3.json'
    scope=dict(study_id=NAME,resolved_identity=s['spec']['resolved_identity'],
        previous_provider_identity=digest(s['spec']['runtime']['provider']),provider=runtime['provider'],
        credentials_reference=runtime['credentials_reference'])
    transition=transition_transport(h,dict(version='provider_transport_approval_v1',approved=True,
        source=APPROVAL,scope=scope,scope_identity=digest(scope)))
    core.bind(h,reason='User-selected third Gateway account continuation; audited loopback transport instance support only. Scientific profile, candidates, results, original session and ledger retained.')
    assert invariant(h)==baseline['invariant']
    evidence=assess_live_admission(h,ROOT.parent/'stage2-research-workflow-20261106/runs/research'/SOURCE,SOURCE)
    evidence_ref=save(h,evidence,'handoff_transport_evidence');s=state(h)
    scope=dict(study_id=NAME,resolved_identity=s['spec']['resolved_identity'],implementation_freeze=s['freeze'],
        capabilities=s['spec']['capabilities'],execution_scopes=['registered mathematics','physical replay','request-feedback session handoff'],
        session_handoff=dict(boundary='request_feedback',evidence=evidence_ref),provider_requests=80,
        protected_provider_requests=0,provider_extension_authorized=False)
    grant=save(h,dict(user_approval=APPROVAL,scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    admission=admit_formal_study(h,grant);guard(h)
    from tools.research.agent import converse
    asyncio.run(converse(h,session_handoff=True,restore_only=True))
    assert invariant(h)==baseline['invariant']
    value=dict(study_id=NAME,account='account3',endpoint=runtime['provider']['base_url'],transition=transition,
        admission=admission,authorization=grant,invariant_preserved=True,implementation=state(h)['freeze'],
        sdk_restore=True,provider_requests_sent=0,ledger=h.store.remaining(),timestamp_unix=time.time())
    atomic_json(DOC/'gateway-account3-bound.json',value)
    print(json.dumps(dict(bound=True,invariants_preserved=True,sdk_restore=True,provider_requests_sent=0)))

if __name__=='__main__':globals()[sys.argv[1]]()
