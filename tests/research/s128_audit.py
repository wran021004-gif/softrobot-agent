"""S12.8 local freeze, explicit approval record and read-only derived audit.

Never invokes the research Agent or numerical workers; raw archives stay local.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from tools.platform_host import Host
from tools.research.config import ROOT, resolve
from tools.research.state import state, science_hashes, core_hashes, require_authorization
from tools.research.agent import pending, received, record
from tools.state_io import atomic_json, read, digest
from tests.research.s128_preflight import SPEC, OUT, provider_scope

BASE='096488569644d8bdd9b2907486585adec563b41e'


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf8').strip()


def host():
    study=read(OUT/'cold_start.json')['study_id']
    return Host(ROOT/'runs/research'/study,study,actor='unified-research')


def freeze():
    from tools.research.core import bind
    h=host();s=state(h)
    if 'freeze' in s:raise ValueError('ALREADY_FROZEN; audit without rebinding')
    if git('status','--porcelain'):raise ValueError('COMMIT_ALL_PREPARATION_BEFORE_FREEZE')
    commit=git('rev-parse','HEAD');remote=git('ls-remote','origin','refs/heads/feat/sorosim-matlab-nmpc').split()[0]
    if commit!=remote:raise ValueError('PUSH_AND_VERIFY_REMOTE_BEFORE_FREEZE')
    assert s['spec']==resolve(SPEC)
    assert not pending(h) and not s['candidates']
    assert not h.store.remaining()['used']['model_calls'] and not h.store.remaining()['used']['backend_solves']
    bind(h)
    files=git('ls-files','tools','extensions','schemas','tasks','matlab','configs','tests','AGENTS.md','requirements.txt','requirements-strands-mainline5.lock').splitlines()
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}
    value=dict(study_id=h.run_id,freeze_source_commit=commit,remote_sha_at_freeze=remote,
        resolved_identity=s['spec']['resolved_identity'],scope_identity=digest(provider_scope(s['spec'])),
        source_files=hashes,science_hashes=science_hashes(),core_hashes=core_hashes(),
        canonical_task_identity=s['spec']['canonical_task_identity'],family_space_identity=s['spec']['family_space_identity'],
        budgets=s['spec']['budgets'],rl_limits=s['spec']['rl_limits'],nmpc_limits=s['spec']['nmpc_limits'],
        store=str(h.store.root),framework_session_id=s['pilot']['framework_session_id'],
        authorization='pending; no actual Provider request or scientific worker permitted',
        runtime_environment=read(OUT/'cold_start.json')['versions'],rl_environment=read(OUT/'rl_environment.json'),
        matlab_readiness_identity=digest(read(OUT/'readiness_verified.json')),
        production_handoff_admitted=False,raw_publication_authorized=False)
    atomic_json(OUT/'freeze.json',value)
    return value


def record_approval(path):
    """Call only after an actual explicit user response; never invent its content."""
    h=host();s=state(h);frozen=read(OUT/'freeze.json');scope=provider_scope(s['spec']);approval=read(Path(path))
    if (approval.get('stage')!='S12.8' or approval.get('study_id')!=h.run_id
            or approval.get('scope_identity')!=digest(scope) or not approval.get('user_approval')
            or approval.get('freeze_source_commit')!=frozen['freeze_source_commit']):
        raise ValueError('INDEPENDENT_S128_APPROVAL_OF_EXACT_SCOPE_AND_FREEZE_REQUIRED')
    if frozen['freeze_source_commit']!=s['freeze']:raise ValueError('FREEZE_CHANGED')
    if any(e['kind']=='formal_study_authorization' for e in h.store.events(h.run_id)):
        raise ValueError('APPROVAL_ALREADY_RECORDED; do not replace original approval')
    ref=record(h,'formal_study_authorization',dict(approval,scope=scope))
    require_authorization(h)
    receipt=dict(stage='S12.8',study_id=h.run_id,status='explicitly_approved',scope_identity=digest(scope),
        freeze_source_commit=s['freeze'],local_approval_reference=ref,raw_publication_authorized=False)
    atomic_json(OUT/'authorization.json',receipt)
    return receipt


def audit():
    h=host();s=state(h);before=digest(s);ledger=h.store.remaining();events=h.store.events(h.run_id)
    requests=[];usage=Counter()
    for event in events:
        if event['kind']!='r3_request':continue
        reception=received(h,event['request_id']);wire=h.store.artifact(h.store.artifact(event['outputs'][0])['request'])
        assert wire['max_tokens']==131072 and wire['model']=='deepseek-flash'
        body=json.loads(h.store.artifact(reception['body'],raw=True)) if reception else {}
        for key in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'):
            usage[key]+=body.get('usage',{}).get(key,0)
        requests.append(dict(request_id=event['request_id'],response_saved=bool(reception),
            finish_reasons=[c.get('finish_reason') for c in body.get('choices',[])],
            reasoning_messages=sum(bool(c.get('message',{}).get('reasoning_content')) for c in body.get('choices',[]))))
    frozen=read(OUT/'freeze.json')
    assert s['freeze']==frozen['freeze_source_commit']
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in frozen['source_files'].items())
    assert core_hashes()==s['core_hashes'] and science_hashes()==s['profile']['science_hashes']
    sealed=git('diff','--name-only',BASE,'--','evidence/s126_cold','evidence/s127_4_decision',
        'evidence/s127_4_handoff','evidence/s127_6_decision','evidence/s127_6_handoff','tasks')
    assert not sealed,sealed
    with h.store.connect(True) as db:unsettled=db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]
    try:require_authorization(h);approved=True
    except ValueError:approved=False
    old=Host(ROOT/'runs/research/s126-cold-live-20261020','s126-cold-live-20261020')
    old_identity=digest(state(old))
    assert old_identity=='d366a9a2791a6d35d881ca5c11bf82c182e03c38b912536ce8b900dfb071b5f3'
    result=dict(status='authorized_ready' if approved else 'frozen_awaiting_independent_formal_approval',
        study_id=h.run_id,source_commit=s['freeze'],current_local_sha=git('rev-parse','HEAD'),
        source_hashes_match=True,old_sealed_files_unchanged=True,old_s126_state_identity=old_identity,
        store_state_identity=before,ledger=ledger,provider_requests=requests,actual_usage=dict(usage),
        unsettled_receipts=unsettled,pending=pending(h),worker_pending=s.get('pending'),
        candidate_count=len(s['candidates']),research_status=s['research_status'],
        selected=s.get('selected'),selected_solution=s.get('selected_solution'),
        original_task_acceptance='not_evaluated' if not s['results'] and not s['physical_replays'] and not s.get('rl_evaluations') else 'requires_independent_result_reconstruction',
        method_counts={k:s.get(k,0) for k in ('mathematical_evaluations','offline_nlp','bdf_replays',
            'nmpc_launches','physical_replay_launches','admitted_training_stages')},
        authorization_approved=approved,production_handoff_admitted=False,
        actual_provider_requests=len(requests),formal_agent_started=bool(s.get('live_started_unix')),
        scientific_success_proven=False,raw_data_published=False)
    assert digest(state(h))==before and h.store.remaining()==ledger and h.store.events(h.run_id)==events
    assert len(requests)==ledger['used']['model_calls']
    if not approved:assert not requests and not ledger['used']['backend_solves']
    atomic_json(ROOT/'evidence/s128_acceptance/status.json',result)
    from tools.research.budget import stage_usage
    atomic_json(ROOT/'evidence/s128_costs/counts.json',dict(study_id=h.run_id,actual_provider_requests=len(requests),
        usage=dict(usage),ledger=ledger,methods=result['method_counts'],rl_training=stage_usage(s)))
    return result


if __name__=='__main__':
    if '--freeze' in sys.argv:value=freeze()
    elif '--record-approval' in sys.argv:value=record_approval(sys.argv[sys.argv.index('--record-approval')+1])
    else:value=audit()
    print(json.dumps({k:value.get(k) for k in ('status','study_id','freeze_source_commit','source_commit','actual_provider_requests')}))
