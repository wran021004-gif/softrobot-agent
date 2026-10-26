"""Second authorized R1 request addendum; no scientific actions or new ledger."""
from copy import deepcopy
import json
import subprocess
from tools.platform_host import Host
from tools.platform_store import encode, plain
from tools.research import core
from tools.research.agent import pending, record
from tools.research.config import ROOT
from tools.research.state import state, guard
from tools.state_io import digest


def main():
    run='b3-r1-history-assisted-050'
    host=Host(ROOT/'runs/research'/run,run,actor='unified-research')
    old=state(host);ledger=host.store.remaining()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('COMMIT_REPAIR_AND_ADDENDUM_BEFORE_APPLYING')
    if old['spec']['resolved_identity']!='f5545840fe3563453ba8f0d8cc30f32335cacd46de88fa2e555fbcf295193d7c':
        raise ValueError('FIRST_ADDENDUM_IDENTITY_REQUIRED_NO_REPEATED_EXTENSION')
    if old['research_status']!='ready' or old['pending'] or pending(host) or ledger['occupied'] or old['pilot'].get('unconsumed_response'):
        raise ValueError('SETTLED_READY_STUDY_REQUIRED')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:
            raise ValueError('UNSEALED_RESERVATIONS_BLOCK_ADDENDUM')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    authorization=dict(user_approval=True,
        source='Trusted user chat 2026-10-26: increase Provider and record Agent errors/repair plan; reply to request_user_input_async/call_c80f7d4138f54d378d4bb24461df252a',
        approval_text='再增加 48 次，总上限 144',
        additional_provider_requests=48,additional_public_operations=0,
        scientific_limits_unchanged=True,previous_ledger=ledger,
        previous_freeze=old['freeze'],repair_commit=commit,
        previous_identity=old['spec']['resolved_identity'])
    spec=deepcopy(old['spec'])
    spec['budgets']['provider_requests']+=48
    counts=dict(model_calls=spec['budgets']['provider_requests'],tool_calls=spec['budgets']['public_operations'])
    spec['configuration']['policy']['budget'].update(counts)
    spec.pop('resolved_identity')
    # Immutable addendum lives in the original Store, not a second budget file.
    with host.store.transaction() as db:
        addendum=plain(host.store.put(db,authorization))
        spec.setdefault('authorization_addenda',[]).append(addendum)
        spec['resolved_identity']=digest(spec)
        snapshot=deepcopy(host.store.session(run,db)['snapshot'])
        snapshot['input']['policy']['budget'].update(counts)
        snapshot_ref=host.store.put(db,snapshot)
        config=host.store.config(db);previous_config_hash=digest(config)
        config['budget'].update(counts)
        # Keep the existing grant/root and atomically update its authority hash.
        # SQLite's attached transaction also retains every original call/event.
        db.execute('ATTACH DATABASE ? AS authority',(str(ROOT/'runs/.platform_authorities.sqlite'),))
        changed=db.execute('UPDATE authority.grants SET config_hash=? WHERE grant_id=? AND root=? AND config_hash=?',
            (digest(config),config['grant_id'],str(host.store.root),previous_config_hash))
        if changed.rowcount!=1:raise ValueError('EXISTING_AUTHORITY_REQUIRED')
        db.execute("UPDATE meta SET value=? WHERE key='config'",(encode(config),))
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(snapshot_ref.artifact_id,run))
        current=host.store.session(run,db)['state']
        current.update(spec=spec,validation_extension_pending_binding=True)
        current.setdefault('validation_extensions',[]).append(addendum)
        host.store.update_state(db,run,current)
        host.store.event(db,run,'request_budget_extension','authorized',outputs=[addendum,snapshot_ref])
    previous=next(host.store.artifact(e['outputs'][0]) for e in reversed(host.store.events(run))
        if e['kind']=='formal_study_authorization')
    scope=deepcopy(previous['scope'])
    scope.update(resolved_identity=spec['resolved_identity'],budgets=spec['budgets'],
        frozen_implementation=commit,request_addendum=addendum)
    record(host,'formal_study_authorization',dict(user_approval=True,source=authorization['source'],
        approval_text=authorization['approval_text'],scope=scope,scope_identity=digest(scope)))
    core.bind(host,reason='Second explicit user addendum: +48 Provider to total 144; public operations remain 192; same Study, all evidence and cumulative costs retained; science unchanged')
    guard(host)
    assert host.store.remaining()['used']==ledger['used']
    assert state(host)['profile']==old['profile']
    assert state(host)['results']==old['results']
    assert state(host)['spec']['budgets']=={**old['spec']['budgets'],
        'provider_requests':144,'public_operations':192}
    print(json.dumps(dict(addendum=addendum,freeze=state(host)['freeze'],
        resolved_identity=spec['resolved_identity'],ledger=host.store.remaining(),
        scientific_profile_unchanged=True,old_evidence_and_costs_retained=True)))


if __name__=='__main__':main()
