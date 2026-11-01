"""User-authorized resource addendum using the existing B3 nonpass continuation protocol."""
from copy import deepcopy
import json
import subprocess
from tools.platform_host import Host
from tools.platform_store import encode, plain
from tools.research import core
from tools.research.provider import pending, record
from tools.research.config import ROOT
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.research.state import state, require_research_authorization, guard
from tools.state_io import digest

RUN='m1-elevated-auth-checked-20261101-b824e6d1'
OLD_ID='1e3776684c43d6b56bdc771d9fcc3d83628be7c4772dea4cfa0404f490426b63'
OLD_STOP='273cab079841987b69d6738e50f746de8e88781a94f4c3c50b095e85a840468a'
TOTALS=dict(provider_requests=160,public_operations=640,mathematical_evaluations=128)
PHYSICS_BOUND=128*801*600+18*600


def main():
    h=Host(ROOT/'runs/research'/RUN,RUN,actor='unified-research')
    old=state(h);ledger=h.store.remaining()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('COMMIT_ADDENDUM_BEFORE_APPLYING')
    if (old['spec']['resolved_identity']!=OLD_ID or old['research_status']!='stopped'
            or old['final_disposition']['artifact_id']!=OLD_STOP or old.get('success_gate') or old.get('selected')
            or old['pending'] or pending(h) or ledger['occupied'] or old['pilot'].get('unconsumed_response')):
        raise ValueError('EXACT_SETTLED_NONPASS_STOP_REQUIRED')
    if (ledger['used']['model_calls']!=34 or ledger['used']['tool_calls']!=32 or old['mathematical_evaluations']!=16
            or len(old['analysis_results'])!=7):raise ValueError('EXACT_RETAINED_COSTS_AND_RESULTS_REQUIRED')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:raise ValueError('UNSEALED_RESERVATIONS_BLOCK_ADDENDUM')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    authorization=dict(user_approval=True,source='Current explicit user messages in this chat',
        approval_text='不要限制数学评估的次数，预算要充足。\n扩展他们的预算，然后继续study',
        operator_selected_finite_resource_totals=TOTALS,previous_final_disposition=old['final_disposition'],
        previous_ledger=ledger,previous_freeze=old['freeze'],repair_commit=commit,previous_identity=OLD_ID,
        additional_provider_requests=97,additional_public_operations=418,additional_mathematical_evaluations=112,
        scientific_model_methods_tasks_thresholds_unchanged=True,resource_limits_increased=True,
        native_per_request_limits_unchanged=True,physical_replay_limit_unchanged=18,
        conservative_physics_step_bound=PHYSICS_BOUND,
        scope='Explicit additional autonomous research segment in the same Study. Retain the sealed nonpass STOP, all seven results, one charged remote-unknown request and every cost. No NMPC/PPO/RL, extra confirmations, new Study or success-following optimization.')
    spec=deepcopy(old['spec']);spec['budgets'].update(TOTALS)
    counts=dict(model_calls=TOTALS['provider_requests'],tool_calls=TOTALS['public_operations'])
    spec['configuration']['policy']['budget'].update(counts);spec.pop('resolved_identity')
    with h.store.transaction() as db:
        authorization['previous_state']=plain(h.store.put(db,old));addendum=plain(h.store.put(db,authorization))
        spec.setdefault('authorization_addenda',[]).append(addendum);spec['resolved_identity']=digest(spec)
        snapshot=deepcopy(h.store.session(RUN,db)['snapshot']);snapshot['input']['policy']['budget'].update(counts)
        snapshot_ref=h.store.put(db,snapshot);config=h.store.config(db);prior_hash=digest(config);config['budget'].update(counts)
        db.execute('ATTACH DATABASE ? AS authority',(str(ROOT/'runs/.platform_authorities.sqlite'),))
        changed=db.execute('UPDATE authority.grants SET config_hash=? WHERE grant_id=? AND root=? AND config_hash=?',
            (digest(config),config['grant_id'],str(h.store.root),prior_hash))
        if changed.rowcount!=1:raise ValueError('EXISTING_AUTHORITY_REQUIRED')
        db.execute("UPDATE meta SET value=? WHERE key='config'",(encode(config),))
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(snapshot_ref.artifact_id,RUN))
        current=h.store.session(RUN,db)['state']
        current.update(spec=spec,validation_extension_pending_binding=True,research_status='ready',count_closeout=False,pending_authorized_continuation=addendum)
        current.pop('final_disposition');current.pop('closed_unix')
        current.setdefault('research_continuations',[]).append(addendum);current.setdefault('validation_extensions',[]).append(addendum)
        h.store.update_state(db,RUN,current);h.store.event(db,RUN,'request_budget_extension','authorized',outputs=[addendum,snapshot_ref])
    previous=next(h.store.artifact(e['outputs'][0]) for e in reversed(h.store.events(RUN)) if e['kind']=='formal_study_authorization')
    scope=deepcopy(previous['scope']);assert REGISTERED_MATHEMATICS_SCOPE in scope['execution_scopes']
    scope.update(resolved_identity=spec['resolved_identity'],budgets=spec['budgets'],implementation_commit=commit,
        request_addendum=addendum,research_continuation=addendum,conservative_physics_steps=PHYSICS_BOUND)
    ref=record(h,'formal_study_authorization',dict(user_approval=True,source=authorization['source'],
        approval_text=authorization['approval_text'],scope=scope,scope_identity=digest(scope)))
    core.bind(h,reason='Explicit user budget expansion and additional autonomous segment after nonpass STOP; same Study, original B3 atomic authority addendum, prior STOP/results/charges retained; physical science unchanged')
    require_research_authorization(h);guard(h);now=state(h)
    assert h.store.remaining()['used']==ledger['used'] and now['profile']==old['profile']
    for key in ('candidates','analysis_results','physical_replays','control_initializations'):assert now[key]==old[key]
    assert h.store.artifact(authorization['previous_state'])['final_disposition']==old['final_disposition']
    print(json.dumps(dict(study_id=RUN,addendum=addendum,approval_reference=ref,approval_scope=digest(scope),freeze=now['freeze'],
        resolved_identity=spec['resolved_identity'],budgets=spec['budgets'],previous_stop=old['final_disposition'],
        used=h.store.remaining()['used'],math_used=now['mathematical_evaluations'],scientific_profile_unchanged=True,physics_bound=PHYSICS_BOUND)))


if __name__=='__main__':main()
