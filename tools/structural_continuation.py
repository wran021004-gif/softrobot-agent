"""Narrow same-session repair migration and accepted-plan continuation guards."""
from copy import deepcopy
from tools.state_io import digest, read
from tools.platform_store import plain
from tools.platform_registry import dependency_closure

VERSION='v3-structural-read-continuation@3.5.0'
ATTACHMENT='9dae342a-539d-453e-a481-0fa61888934d'
SOURCES={'tools/candidate_parameters.py','tools/platform_search.py','tools/context_assembly.py'}


def retire_settled_draft(w):
    """Retain obsolete correction evidence without reopening that correction."""
    with w.store.transaction() as db:
        state=w.store.session(w.host.run_id,db)['state']
        if state.get('pending') or state.get('protocol_correction'):
            raise ValueError('UNSETTLED_PROTOCOL_WORK_CANNOT_BE_RETIRED')
        draft=state.get('unaccepted_draft')
        if not draft:return None
        accepted=state.get('handoffs',{}).get('research_decision')
        if not accepted or not w.store.artifact(accepted,db=db).get('decision'):
            raise ValueError('NO_ACCEPTED_DECISION_AFTER_PROTOCOL_DRAFT')
        ref=plain(w.store.put(db,dict(original_draft=draft,accepted_decision=accepted,
            reason='Completed subsequent native decisions; old rejected draft is historical, not a pending correction',
            corrections_consumed=state.get('protocol_corrections_used',0))))
        w.store.event(db,w.host.run_id,'settled_protocol_draft','archived',outputs=[ref],version='3.4.0')
        state.pop('unaccepted_draft');w.store.update_state(db,w.host.run_id,state)
    return ref


def migrate(w,authorization):
    """Change only declared read-path source hashes; all grants/science survive."""
    session=w.store.session(w.host.run_id);before=deepcopy(session['snapshot'])
    if session['state'].get('structural_read_migration'):raise ValueError('STRUCTURAL_MIGRATION_ALREADY_RECORDED')
    changed=w.host.compatibility()['changed']
    if not changed:raise ValueError('STRUCTURAL_MIGRATION_REQUIRES_OBSERVED_IMPLEMENTATION_CHANGE')
    after=deepcopy(before)
    for key in changed:
        name,version=key.split('@')
        current=dependency_closure([w.host.reg.get(name,version)],w.host.reg)[key]
        old=before['dependencies'][key];allowed=deepcopy(old)
        for path in SOURCES:
            if path in old['sources']:
                if current['sources'][path]!=w.freeze['implementation']['files'][path]:
                    raise ValueError('STRUCTURAL_MIGRATION_IMPLEMENTATION_NOT_FROZEN: '+path)
                allowed['sources'][path]=current['sources'][path]
        if current!=allowed or current==old:raise ValueError('STRUCTURAL_MIGRATION_EXCEEDS_SHARED_READ_REPAIR: '+key)
        after['dependencies'][key]=current
    with w.store.transaction() as db:
        boundary=dict(version=VERSION,authorization=authorization,campaign_id=w.store.config(db)['project_id'],
            session_id=w.host.run_id,grant_identity=digest(w.store.config(db)),original_clock=w.freeze['live_clock'],
            before_snapshot=plain(w.store.put(db,before)),after_snapshot=plain(w.store.put(db,after)),
            predecessor_migration=session['state'].get('authorized_dependency_migration'),
            changed_dependencies=changed,changed_sources=sorted(SOURCES),implementation=w.freeze['implementation'],
            previous_repairs=4,cumulative_material_repairs=6,science_changed=False,new_session=False)
        ref=plain(w.store.put(db,boundary))
        w.store.event(db,w.host.run_id,'structural_read_migration','completed',outputs=[ref],version='3.4.0')
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(boundary['after_snapshot']['artifact_id'],w.host.run_id))
        state=session['state'];state['structural_read_migration']=ref;w.store.update_state(db,w.host.run_id,state)
    verify_migration(w.store,w.host.run_id,digest(before),digest(after))
    if not w.host.compatibility()['compatible']:raise ValueError('STRUCTURAL_MIGRATION_STILL_INCOMPATIBLE')
    return boundary


def verify_migration(store,run_id,before_identity,after_identity):
    from tools.platform_registry import registry
    session=store.session(run_id);ref=session['state'].get('structural_read_migration')
    if not ref:raise ValueError('STRUCTURAL_MIGRATION_REQUIRED')
    b=store.artifact(ref);before=store.artifact(b['before_snapshot']);after=store.artifact(b['after_snapshot']);auth=b['authorization']
    if (b['version']!=VERSION or b['session_id']!=run_id or b['campaign_id']!=store.config()['project_id'] or
        digest(before)!=before_identity or digest(after)!=after_identity or after!=session['snapshot'] or
        b['grant_identity']!=digest(store.config()) or b['original_clock']!=read(store.root/'live_clock.json') or
        auth['source_attachment']!=ATTACHMENT or auth['same_session']!=run_id or auth['same_campaign']!=b['campaign_id'] or
        auth['clock']!=b['original_clock'] or auth['original_limits']!=store.config()['budget'] or
        auth['previous_repairs']!=4 or auth['additional_material_live_repairs']!=3 or auth['cumulative_repair_ceiling']!=7 or
        b['previous_repairs']!=4 or b['cumulative_material_repairs']!=6 or b['changed_sources']!=sorted(SOURCES) or
        b['science_changed'] is not False or b['new_session'] is not False):
        raise ValueError('STRUCTURAL_MIGRATION_BINDING_CHANGED')
    if b['predecessor_migration']!=session['state'].get('authorized_dependency_migration'):
        raise ValueError('STRUCTURAL_MIGRATION_PREDECESSOR_CHANGED')
    predecessor=store.artifact(b['predecessor_migration'])
    if predecessor['after_snapshot']!=b['before_snapshot']:
        raise ValueError('STRUCTURAL_MIGRATION_ORIGINAL_SNAPSHOT_CHANGED')
    expected=deepcopy(before);reg=registry()
    actual_changes=[]
    for key,old in before['dependencies'].items():
        new=after['dependencies'].get(key)
        if new!=old:
            actual_changes.append(key);allowed=deepcopy(old)
            for path in SOURCES:
                if path in old['sources']:allowed['sources'][path]=new['sources'][path]
            if allowed!=new:raise ValueError('STRUCTURAL_MIGRATION_CHANGED_SCIENCE')
            expected['dependencies'][key]=new
        name,version=key.split('@')
        if new!=dependency_closure([reg.get(name,version)],reg)[key]:raise ValueError('STRUCTURAL_MIGRATION_IMPLEMENTATION_CHANGED')
    if expected!=after or actual_changes!=b['changed_dependencies']:
        raise ValueError('STRUCTURAL_MIGRATION_CHANGED_AUTHORIZATION')
    if not any(e['kind']=='structural_read_migration' and e['status']=='completed' and e['outputs']==[ref] for e in store.events(run_id)):
        raise ValueError('STRUCTURAL_MIGRATION_EVENT_MISSING')
    if not any(e['kind']=='continuation_authorization' and store.artifact(e['outputs'][0])==auth for e in store.events(run_id)):
        raise ValueError('STRUCTURAL_CONTINUATION_AUTHORIZATION_MISSING')
    return True
