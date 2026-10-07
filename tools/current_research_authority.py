"""Refresh current-session research authority before each real request."""
from copy import deepcopy
import json
import time
from tools.platform_store import plain


def refresh(host):
    role=host.store.session(host.run_id)['state'].get('role_context',{})
    if not role.get('refresh_current_authority'):return
    from tools.research_scheduler import capabilities
    from tools.context_assembly import EvidenceArchive,ROOT,update_working_state
    cap=capabilities(host.store,host.run_id,role['research_records'])
    if role.get('research_final_reporting'):
        cap['legal']={'stop':dict(reason='Sealed trajectory: final interpretation only',execution_authorized=False)}
        cap['unavailable'].update({k:'Research trajectory closed' for k in ('control_search','structure_search','diagnosis')})
    working=deepcopy(role['research_working_state']);packet=deepcopy(role['research_packet'])
    authority=deepcopy(role['context_authority'])
    state=host.store.session(host.run_id)['state']
    revision=state.get('current_authority_revision',0)+1
    snapshot=dict(campaign_id=host.store.config()['project_id'],session_id=host.run_id,revision=revision,
        generated_unix=time.time(),capabilities=deepcopy(cap),accounting=host.store.remaining(),
        elapsed_deadline_unix=role.get('campaign_permissions',{}).get('elapsed_deadline_unix'),
        source='Current session and cumulative successor ledger; archived context is evidence only')
    with host.store.transaction() as db:reference=plain(host.store.put(db,snapshot))
    stamp=dict(reference=reference,campaign_id=snapshot['campaign_id'],session_id=host.run_id,revision=revision)
    cap['authority_snapshot']=stamp;packet['capabilities']=cap
    authority.update(legal_actions=deepcopy(cap['legal']),remaining_budget=deepcopy(cap['remaining']),
        budget_accounting=host.store.remaining(),current_authority=stamp)
    archive=EvidenceArchive.from_manifest(ROOT/role['research_working_manifest'],
        scope=working['archive_scope'],stores=(host.store,))
    working=update_working_state(working,archive=archive,evidence_packet=packet,authority=authority)
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state'];current=state['role_context']
        current.update(research_packet=packet,research_working_state=working,context_authority=authority,
            research_working_manifest=archive.manifest(),authority_snapshot=stamp)
        state['current_authority_revision']=revision
        host.store.update_state(db,host.run_id,state)


def check_payload(host,payload):
    role=host.store.session(host.run_id)['state'].get('role_context',{})
    if not role.get('refresh_current_authority'):return
    packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
    stamp=role['authority_snapshot'];snapshot=host.store.artifact(stamp['reference'])
    if stamp['session_id']!=host.run_id or stamp['campaign_id']!=host.store.config()['project_id'] or packet['capabilities']['authority_snapshot']!=stamp:
        raise ValueError('REQUEST_CURRENT_AUTHORITY_BINDING_MISMATCH')
    actual=snapshot['capabilities']
    if packet['capabilities']['legal']!=actual['legal'] or packet['capabilities']['remaining']!=actual['remaining']:
        raise ValueError('REQUEST_CURRENT_AUTHORITY_MENU_OR_BUDGET_MISMATCH')
    function=next(t for t in payload['tools'] if t['function']['name']=='research_decide')
    if set(function['function']['parameters']['anyOf'][0]['properties']['action']['enum'])!=set(actual['legal']):
        raise ValueError('REQUEST_CURRENT_AUTHORITY_SCHEMA_MISMATCH')


def dispatch_snapshot(store,run_id,role,cap,action):
    if not role.get('refresh_current_authority'):return None
    stamp=role.get('authority_snapshot')
    if not stamp or stamp['session_id']!=run_id:raise ValueError('CURRENT_AUTHORITY_SNAPSHOT_REQUIRED')
    snapshot=store.artifact(stamp['reference'])
    if snapshot['session_id']!=run_id or snapshot['revision']!=stamp['revision'] or snapshot['campaign_id']!=store.config()['project_id'] or stamp['campaign_id']!=snapshot['campaign_id']:
        raise ValueError('CURRENT_AUTHORITY_SNAPSHOT_MISMATCH')
    if action not in cap['legal'] and action in snapshot['capabilities']['legal']:
        raise ValueError('CURRENT_AUTHORITY_CHANGED: '+cap['unavailable'].get(action,'Action no longer executable'))
    return dict(request=stamp,current_capabilities=cap,current_accounting=store.remaining(),
        revalidated_before_dispatch=True,archive_cannot_authorize=True)
