"""Refresh current-session research authority before each real request."""
from copy import deepcopy
import json
import time
from tools.platform_store import plain
from tools.state_io import digest,read


def accounting_binding(store,run_id,*,as_of_unix=None):
    """Bind the existing ledger and its phase projection, without a new grant."""
    from tools.batch_budget import downstream_available,operational_view
    from tools.context_assembly import ROOT
    now=time.time() if as_of_unix is None else as_of_unix
    with store.connect(True) as db:
        db.execute('BEGIN')
        session=store.session(run_id,db)
        calls=[dict(r) for r in db.execute('SELECT * FROM calls ORDER BY rowid')]
        events=[json.loads(r[0]) for r in db.execute('SELECT body FROM events ORDER BY seq')]
        raw=store.remaining(None,db)
        phase=downstream_available(store,run_id,db,as_of_unix=now)
        config=store.config(db)
        operational=operational_view(store,run_id,db,as_of_unix=now)
    clock_path=store.root/'live_clock.json'
    value=dict(version='current_phase_accounting@3.2.0',source_store=store.root.relative_to(ROOT).as_posix(),
        campaign_id=config['project_id'],session_id=run_id,session_snapshot=digest(session['snapshot']),
        grant_identity=digest(config),clock=read(clock_path) if clock_path.exists() else None,
        accounting=raw,research_capacity=phase,as_of_unix=now,
        phase_policy=session['state'].get('role_context',{}).get('campaign_permissions'),
        call_rows=[{k:r[k] for k in ('run_id','request_id','execution_id','status','reserved','charged','receipt','parent_id','resources')} for r in calls],
        event_sequence=max((e['sequence'] for e in events),default=0))
    _ledger_prefixes(value,events)
    value['operational_facts']=operational
    with store.transaction() as db:ref=plain(store.put(db,value))
    return dict(reference=ref,source_store=value['source_store'],session_id=run_id,campaign_id=config['project_id'])


def _ledger_prefixes(value,events):
    """Replay existing reservation/settlement events and verify every call."""
    from tools.platform_store import zero
    replay={};prefixes=[];reservations={}
    for e in events:
        eid=e.get('execution_id');key=(e['run_id'],e.get('request_id'))
        if e['status']=='reserved' and eid:
            if key in reservations:raise ValueError('ACCOUNTING_DUPLICATED_RESERVATION')
            reservations[key]=e;replay[key]=dict(execution_id=eid,status='running',cost=e['cost'])
        elif key in replay and e.get('parent_id')==reservations[key]['event_id'] and e['status'] in ('completed','failed','rejected'):
            if e['kind'] not in ('model_raw_response','model_transport','model_decision','model_length_failure','model_protocol_failure','result_provenance') and (e['cost'].get('tool_calls',0)+e['cost'].get('model_calls',0)+e['cost'].get('backend_solves',0) or e['kind']=='engineering'):
                if replay[key]['status']!='running' and replay[key]['cost']!=e['cost']:raise ValueError('ACCOUNTING_REPEATED_SETTLEMENT_CHANGED')
                replay[key]=dict(execution_id=eid,status=e['status'],cost=e['cost'])
        used=zero()
        for row in replay.values():
            for k,v in row['cost'].items():used[k]+=v
        prefixes.append(used)
    actual={ (r['run_id'],r['request_id']):r for r in value['call_rows'] }
    if set(actual)!=set(replay):raise ValueError('ACCOUNTING_DISCARDED_OR_UNRECORDED_CALL')
    for key,row in actual.items():
        charged=json.loads(row['charged']);reserved=json.loads(row['reserved']);expected=replay[key]
        if row['execution_id']!=expected['execution_id'] or charged!=expected['cost'] or reserved!=reservations[key]['cost']:
            raise ValueError('ACCOUNTING_LOST_CHARGE_OR_CHANGED_RESERVATION')
        if any(charged[k]!=reserved[k] for k in charged if k!='wall_s'):
            raise ValueError('ACCOUNTING_ATTEMPT_COUNT_CHANGED')
        if row['receipt']:
            receipt=json.loads(row['receipt'])
            if receipt['charged']!=charged or receipt['execution_status']!=row['status'] or row['status']!=expected['status']:
                raise ValueError('ACCOUNTING_RECEIPT_CHARGE_MISMATCH')
        elif row['status'] not in ('running','unknown'):raise ValueError('ACCOUNTING_MISSING_SETTLEMENT_RECEIPT')
        if not row['receipt'] and charged!=reserved:raise ValueError('ACCOUNTING_UNSETTLED_COST_CHANGED')
    if prefixes and prefixes[-1]!=value['accounting']['used']:raise ValueError('ACCOUNTING_AGGREGATE_MISMATCH')
    return prefixes


def verify_accounting_transition(state,authority,archive):
    """Permit only event-proven release under the same immutable authorization."""
    binding=authority['accounting_binding']
    from tools.context_assembly import ROOT
    store=next((s for s in archive.stores if s.root.relative_to(ROOT).as_posix()==binding['source_store']),None)
    if store is None:raise ValueError('ACCOUNTING_CURRENT_STORE_REQUIRED')
    value=store.artifact(binding['reference']);session=store.session(binding['session_id'])
    if (value['source_store']!=binding['source_store'] or value['session_id']!=binding['session_id'] or value['campaign_id']!=store.config()['project_id'] or
        binding['campaign_id']!=value['campaign_id'] or value['session_snapshot']!=digest(session['snapshot']) or
        value['grant_identity']!=digest(store.config())):raise ValueError('ACCOUNTING_GRANT_OR_SESSION_CHANGED')
    old_stamp=state['authority'].get('current_authority')
    if old_stamp and (old_stamp['campaign_id']!=value['campaign_id'] or old_stamp['session_id']!=value['session_id']):
        raise ValueError('ACCOUNTING_STALE_SESSION')
    actual=store.remaining();old_raw=state.get('budget_accounting') or actual
    if old_raw['limit']!=actual['limit'] or authority['budget_accounting']!=actual or value['accounting']!=actual:
        raise ValueError('ACCOUNTING_LIMIT_OR_LEDGER_CHANGED')
    old_clock=state['authority'].get('campaign_clock')
    path=store.root/'live_clock.json';clock=read(path) if path.exists() else None
    if clock!=value['clock'] or authority.get('campaign_clock')!=clock or (old_clock is not None and clock!=old_clock):raise ValueError('ACCOUNTING_CLOCK_CHANGED')
    from tools.batch_budget import downstream_available
    policy=value['phase_policy'] or {}
    if policy.get('phase_budget_policy')=='conditional_verification@3.0.0' and (policy.get('reserved_verification_backends')!=20 or policy.get('search_backend_limit')!=8):
        raise ValueError('ACCOUNTING_PHASE_POLICY_CHANGED')
    if clock and policy.get('elapsed_deadline_unix')!=clock['deadline_unix']:raise ValueError('ACCOUNTING_PHASE_DEADLINE_CHANGED')
    expected=downstream_available(store,binding['session_id'],as_of_unix=value['as_of_unix'])
    if authority['remaining_budget']!=expected or value['research_capacity']!=expected:
        raise ValueError('ACCOUNTING_WRONG_PHASE_CAPACITY')
    with store.connect(True) as db:events=[json.loads(r[0]) for r in db.execute('SELECT body FROM events ORDER BY seq')]
    prefixes=_ledger_prefixes(value,events)
    if not any(p==old_raw['used'] for p in prefixes) and any(old_raw['used'].values()):raise ValueError('ACCOUNTING_PREVIOUS_SPENDING_NOT_IN_LEDGER')
    old_binding=state['authority'].get('accounting_binding')
    if old_binding:
        previous=store.artifact(old_binding['reference'])
        verify_accounting_snapshot(store,previous)
        if previous['grant_identity']!=value['grant_identity']:
            raise ValueError('ACCOUNTING_AUTHORIZATION_CHANGED')
        if previous['session_snapshot']!=value['session_snapshot']:
            verify_dependency_migration(store,binding['session_id'],previous['session_snapshot'],value['session_snapshot'])
        if previous['clock'] is not None and previous['clock']!=value['clock']:raise ValueError('ACCOUNTING_CLOCK_CHANGED')
        old_policy=deepcopy(previous['phase_policy'] or {});new_policy=deepcopy(value['phase_policy'] or {})
        if previous['clock'] is None:old_policy.pop('elapsed_deadline_unix',None);new_policy.pop('elapsed_deadline_unix',None)
        if old_policy!=new_policy:raise ValueError('ACCOUNTING_PHASE_POLICY_CHANGED')
        # Every previous call survives; settlement can only replace a reservation.
        current={(r['run_id'],r['request_id']):r for r in value['call_rows']}
        for old in previous['call_rows']:
            new=current.get((old['run_id'],old['request_id']))
            if not new or any(new[k]!=old[k] for k in ('execution_id','reserved','parent_id')) or (old['receipt'] and new!=old):
                raise ValueError('ACCOUNTING_SETTLED_HISTORY_CHANGED')
    return True


def verify_accounting_snapshot(store, value):
    """Compare historical call rows and events at the snapshot's explicit cutoff.

    Never compare historical remaining seconds with a later live clock. This
    validates facts only; downstream_available at today's clock owns authority.
    """
    with store.connect(True) as db:
        events=[json.loads(r[0]) for r in db.execute(
            'SELECT body FROM events WHERE seq<=? ORDER BY seq',(value['event_sequence'],))]
    _ledger_prefixes(value,events)
    return dict(verified=True,as_of_unix=value['as_of_unix'],event_sequence=value['event_sequence'],
        execution_authorized=False)


def restored_execution(state, stores=(), *, as_of_unix=None):
    """Read current authority independently of a restored historical state."""
    from tools.context_assembly import ROOT
    from tools.batch_budget import downstream_available
    cutoff=time.time() if as_of_unix is None else as_of_unix
    historical=state['authority'];binding=historical.get('accounting_binding') or {}
    stamp=historical.get('current_authority') or {}
    session_id=binding.get('session_id') or stamp.get('session_id') or state['archive_scope'].get('context_id')
    stop=historical.get('stop') or {};status=str(stop.get('status','')).lower()
    sealed=bool(stop.get('sealed_cases') or 'stop' in status or status in ('sealed','closed','finished'))
    deadline=(historical.get('campaign_clock') or {}).get('deadline_unix')
    deadline=deadline or historical.get('elapsed_deadline_unix')
    live=None
    for candidate in stores:
        if binding.get('source_store') and candidate.root.relative_to(ROOT).as_posix()!=binding['source_store']:continue
        try:session=candidate.session(session_id)
        except ValueError:continue
        if stamp.get('campaign_id') and candidate.config()['project_id']!=stamp['campaign_id']:continue
        live=candidate;break
    legal={};capacity={};compatible=False;reason='Current session authority unavailable; historical evidence only'
    if live is not None:
        if binding:
            saved=live.artifact(binding['reference'])
            verify_accounting_snapshot(live,saved)
            if saved['grant_identity']!=digest(live.config()):raise ValueError('ACCOUNTING_AUTHORIZATION_CHANGED')
        session=live.session(session_id);role=session['state'].get('role_context',{})
        live_deadline=role.get('campaign_permissions',{}).get('elapsed_deadline_unix')
        if live_deadline is not None:deadline=min(deadline,live_deadline) if deadline else live_deadline
        capacity=downstream_available(live,session_id,as_of_unix=cutoff)
        if role.get('autonomous_scheduling'):
            from tools.research_scheduler import capabilities
            legal=capabilities(live,session_id,role.get('research_records',[]),as_of_unix=cutoff)['legal']
        # A generic restored view has no operation grant. Host still owns
        # checking tools; an archived menu alone cannot supply the current one.
        reason='Current Store/session checked; Host dispatch checks still required'
        from tools.platform_host import Host
        compatible=Host(live.root,session_id).compatibility()['compatible']
        if not compatible:
            legal={'stop':dict(execution_authorized=False,reason='Current dependency freeze is incompatible')}
            reason='Current dependency freeze is incompatible; historical evidence remains readable'
        sealed=sealed or session['status']!='running' or bool(role.get('research_final_reporting'))
    expired=deadline is not None and cutoff>=deadline
    if sealed or expired:
        legal={'stop':dict(execution_authorized=False,reason='Scope sealed' if sealed else 'Deadline expired')}
    if expired:capacity={k:0 for k in capacity}
    return dict(as_of_unix=cutoff,elapsed_deadline_unix=deadline,expired=expired,sealed=sealed,
        legal_actions=legal,remaining_budget=capacity,current_session_verified=live is not None,
        implementation_compatible=compatible,
        host_dispatch_required=True,historical_snapshot_is_authority=False,reason=reason)


def verify_dependency_migration(store,run_id,before_identity,after_identity):
    """Verify the one explicitly authorized v3 infrastructure revision only."""
    structural=store.session(run_id)['state'].get('structural_read_migration')
    if structural:
        from tools.structural_continuation import verify_migration
        return verify_migration(store,run_id,before_identity,after_identity)
    from tools.platform_registry import dependency_closure,registry
    session=store.session(run_id)
    ref=session['state'].get('authorized_dependency_migration')
    if not ref:raise ValueError('ACCOUNTING_AUTHORIZATION_CHANGED')
    boundary=store.artifact(ref)
    before=store.artifact(boundary['before_snapshot']);after=store.artifact(boundary['after_snapshot'])
    key='research.decide@1.0.0';path='tools/research_scheduler.py'
    auth=boundary['authorization']
    if (boundary['version']!='v3-dependency-continuation@3.3.0' or boundary['session_id']!=run_id or
        boundary['campaign_id']!=store.config()['project_id'] or
        digest(before)!=before_identity or digest(after)!=after_identity or after!=session['snapshot'] or
        boundary['grant_identity']!=digest(store.config()) or
        boundary['original_clock']!=read(store.root/'live_clock.json') or
        auth['additional_material_live_repairs']!=2 or auth['same_campaign']!=boundary['campaign_id'] or
        auth['same_session']!=run_id or auth['clock']!=boundary['original_clock'] or
        auth['source_attachment']!='0b4a8cdb-8e3b-48d7-975c-ee44dd2fce54' or boundary['additional_material_repairs_used']!=2):
        raise ValueError('ACCOUNTING_DEPENDENCY_MIGRATION_BINDING_CHANGED')
    expected=deepcopy(before)
    expected['dependencies'][key]=deepcopy(after['dependencies'][key])
    if expected!=after:raise ValueError('ACCOUNTING_MIGRATION_CHANGED_AUTHORIZATION_OR_OTHER_DEPENDENCIES')
    old=before['dependencies'][key];new=after['dependencies'][key]
    allowed=deepcopy(old);allowed['sources'][path]=new['sources'][path]
    if old==new or allowed!=new:raise ValueError('ACCOUNTING_MIGRATION_CHANGED_SCIENCE')
    current=dependency_closure([registry().get('research.decide','1.0.0')],registry())[key]
    if new!=current:raise ValueError('ACCOUNTING_MIGRATION_IMPLEMENTATION_CHANGED')
    if not any(e['kind']=='authorized_dependency_migration' and e['status']=='completed' and
        e['outputs']==[ref] for e in store.events(run_id)):
        raise ValueError('ACCOUNTING_MIGRATION_EVENT_MISSING')
    return True


def refresh(host, *, as_of_unix=None):
    session=host.store.session(host.run_id);role=session['state'].get('role_context',{})
    if session['status']!='running':return  # Offline historical preparation is read only.
    if not role.get('refresh_current_authority'):
        stop=role.get('context_authority',{}).get('stop') or {}
        historical_stop=stop.get('sealed_cases') or 'stop' in str(stop.get('status','')).lower()
        if not role.get('autonomous_scheduling') or session['status']!='running' or historical_stop:return
    from tools.research_scheduler import capabilities
    from tools.context_assembly import EvidenceArchive,ROOT,update_working_state
    generated=time.time() if as_of_unix is None else as_of_unix
    cap=capabilities(host.store,host.run_id,role['research_records'],as_of_unix=generated)
    if role.get('research_final_reporting'):
        cap['legal']={'stop':dict(reason='Sealed trajectory: final interpretation only',execution_authorized=False)}
        cap['unavailable'].update({k:'Research trajectory closed' for k in ('control_search','structure_search','diagnosis')})
    working=deepcopy(role['research_working_state']);packet=deepcopy(role['research_packet'])
    # A successful live refresh replaces the ephemeral restoration projection
    # with a newly bound current snapshot. Keeping both menus would duplicate
    # context and can misbind the exact snapshot at check_payload.
    working.pop('current_execution',None)
    authority=deepcopy(role['context_authority'])
    state=host.store.session(host.run_id)['state']
    revision=state.get('current_authority_revision',0)+1
    snapshot=dict(campaign_id=host.store.config()['project_id'],session_id=host.run_id,revision=revision,
        generated_unix=generated,capabilities=deepcopy(cap),accounting=host.store.remaining(),
        elapsed_deadline_unix=role.get('campaign_permissions',{}).get('elapsed_deadline_unix'),
        source='Current session and cumulative successor ledger; archived context is evidence only')
    with host.store.transaction() as db:reference=plain(host.store.put(db,snapshot))
    stamp=dict(reference=reference,campaign_id=snapshot['campaign_id'],session_id=host.run_id,revision=revision)
    cap['authority_snapshot']=stamp;packet['capabilities']=cap
    authority.update(legal_actions=deepcopy(cap['legal']),remaining_budget=deepcopy(cap['remaining']),
        budget_accounting=host.store.remaining(),current_authority=stamp,
        operational_facts=cap['operational_facts'])
    authority['accounting_binding']=accounting_binding(host.store,host.run_id,as_of_unix=generated)
    archive=EvidenceArchive.from_manifest(ROOT/role['research_working_manifest'],
        scope=working['archive_scope'],stores=(host.store,))
    working=update_working_state(working,archive=archive,evidence_packet=packet,authority=authority)
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state'];current=state['role_context']
        current.update(research_packet=packet,research_working_state=working,context_authority=authority,
            research_working_manifest=archive.manifest(),authority_snapshot=stamp,refresh_current_authority=True)
        state['current_authority_revision']=revision
        host.store.update_state(db,host.run_id,state)


def check_payload(host,payload):
    session=host.store.session(host.run_id)
    if session['status']!='running':return  # Sending is denied separately at the boundary.
    role=session['state'].get('role_context',{})
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
