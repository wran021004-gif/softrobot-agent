"""Explicit public-operation addendum and nonpass continuation, same R1 ledger."""
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
    if old['spec']['resolved_identity']!='6f2b9ec2753364f63da994ae538d2cca2f3136480f670f94615d05f7566470ce':
        raise ValueError('SECOND_ADDENDUM_IDENTITY_REQUIRED_NO_REPEATED_EXTENSION')
    if (old['research_status']!='stopped' or old.get('success_gate') or old.get('selected')
            or old['final_disposition']['artifact_id']!='90e356dcc684c02f4e557065afc9f982d235dd8b14e777b62bc8d6e35ae0221a'
            or old['pending'] or pending(host) or ledger['occupied'] or old['pilot'].get('unconsumed_response')):
        raise ValueError('EXACT_SETTLED_NONPASS_STOP_REQUIRED')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:
            raise ValueError('UNSEALED_RESERVATIONS_BLOCK_ADDENDUM')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    authorization=dict(user_approval=True,
        source='Trusted user reply request_user_input_async/call_9d088123c6a144288abfbfa2c2b80a5e',
        approval_text='同意上述额度与追加研究段（建议）',
        approval_scope='Public operations +96 to 288, Provider stays 144, scientific limits unchanged; explicit additional segment in same Study with sealed STOP and all history retained',
        additional_provider_requests=0,additional_public_operations=96,
        previous_final_disposition=old['final_disposition'],
        scientific_limits_unchanged=True,previous_ledger=ledger,
        previous_freeze=old['freeze'],repair_commit=commit,
        previous_identity=old['spec']['resolved_identity'])
    spec=deepcopy(old['spec'])
    spec['budgets']['public_operations']+=96
    counts=dict(model_calls=spec['budgets']['provider_requests'],tool_calls=spec['budgets']['public_operations'])
    spec['configuration']['policy']['budget'].update(counts)
    spec.pop('resolved_identity')
    # Immutable addendum lives in the original Store, not a second budget file.
    with host.store.transaction() as db:
        authorization['previous_state']=plain(host.store.put(db,old))
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
        current.update(spec=spec,validation_extension_pending_binding=True,research_status='ready',
            count_closeout=False,pending_authorized_continuation=addendum)
        current.pop('final_disposition');current.pop('closed_unix')
        current.setdefault('research_continuations',[]).append(addendum)
        current.setdefault('validation_extensions',[]).append(addendum)
        host.store.update_state(db,run,current)
        host.store.event(db,run,'request_budget_extension','authorized',outputs=[addendum,snapshot_ref])
    previous=next(host.store.artifact(e['outputs'][0]) for e in reversed(host.store.events(run))
        if e['kind']=='formal_study_authorization')
    scope=deepcopy(previous['scope'])
    scope.update(resolved_identity=spec['resolved_identity'],budgets=spec['budgets'],
        frozen_implementation=commit,request_addendum=addendum,research_continuation=addendum)
    record(host,'formal_study_authorization',dict(user_approval=True,source=authorization['source'],
        approval_text=authorization['approval_text'],scope=scope,scope_identity=digest(scope)))
    core.bind(host,reason='Explicit user authorization after sealed nonpass STOP: additional segment in same Study, public operations +96 to 288, Provider stays 144; old STOP/state archived immutably and all costs retained; science unchanged')
    guard(host)
    assert host.store.remaining()['used']==ledger['used']
    assert state(host)['profile']==old['profile']
    assert state(host)['results']==old['results']
    assert state(host)['spec']['budgets']=={**old['spec']['budgets'],
        'provider_requests':144,'public_operations':288}
    print(json.dumps(dict(addendum=addendum,freeze=state(host)['freeze'],
        resolved_identity=spec['resolved_identity'],ledger=host.store.remaining(),
        scientific_profile_unchanged=True,old_evidence_and_costs_retained=True)))


if __name__=='__main__':main()
