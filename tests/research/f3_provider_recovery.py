"""Explicitly authorized local delivery-loss settlement; no Provider/tool sends."""
import argparse
import json
from tools.platform_host import Host
from tools.platform_store import plain, zero
from tools.research.config import ROOT
from tools.research.state import state, require_authorization, core_hashes, science_hashes
from tools.research.agent import pending, received, DeepSeekModel
from tools.research.session_handoff import unmatched, snapshot_files
from tools.rl.run import process_birth
from tools.state_io import read, digest, atomic_json

ERROR='LOCAL_PROVIDER_RESPONSE_LOST_REMOTE_OUTCOME_UNKNOWN'
POLICY=dict(remote_outcome='unknown',local_outcome='response_lost_authorized_continuation',
    retain_original_charge=True,release_only_this_provider_lease=True,
    same_study_store_session=True,new_request_requires_new_charge=True,
    no_fabricated_response=True,no_completed_experiment_relaunch=True)


def inspect(host,request_id):
    require_authorization(host)
    s=state(host);rows=pending(host)
    if s['research_status']=='stopped' or s.get('pending') or s['pilot'].get('unconsumed_response'):
        raise ValueError('SETTLED_ACTIVE_STUDY_REQUIRED')
    if (core_hashes()!=s.get('core_hashes') or science_hashes()!=s['profile']['science_hashes']
            or not host.compatibility()['compatible']):raise ValueError('FROZEN_IMPLEMENTATION_REQUIRED')
    if len(rows)!=1 or rows[0]['request_id']!=request_id or rows[0]['status']!='unknown':
        raise ValueError('EXACT_SINGLE_UNKNOWN_PROVIDER_REQUIRED')
    row=rows[0]
    if row['receipt'] or received(host,request_id):raise ValueError('SAVED_RESPONSE_REQUIRES_EXACT_RECOVERY')
    if json.loads(row['reserved'])!={**zero(),'model_calls':1} or json.loads(row['charged'])!=json.loads(row['reserved']):
        raise ValueError('ONE_RETAINED_PROVIDER_CHARGE_REQUIRED')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL AND NOT (run_id=? AND request_id=?)',
                (host.run_id,request_id)).fetchone()[0]:raise ValueError('OTHER_UNSETTLED_WORK')
    if any(e.get('active_reservation') or e.get('status',{}).get('worker_alive',True)
            for e in s.get('rl_runs',{}).values()):raise ValueError('ACTIVE_RL_WORKER')
    events=host.store.events(host.run_id)
    event=next(e for e in events if e['kind']=='r3_request' and e['request_id']==request_id)
    meta=host.store.artifact(event['outputs'][0])
    if meta['purpose']!='conversation' or process_birth(meta['pid']) is not None:
        raise ValueError('EXITED_MAIN_PROVIDER_OWNER_REQUIRED')
    wire=host.store.artifact(meta['request'])
    if digest(wire)!=row['request_hash']:raise ValueError('ORIGINAL_REQUEST_HASH_MISMATCH')
    directory=host.store.root/'framework_sessions'
    paths=list((directory/'session'/s['pilot']['framework_session_id']).rglob('snapshot_latest.json'))
    if len(paths)!=1:raise ValueError('EXACT_SDK_SNAPSHOT_REQUIRED')
    data=read(paths[0])['data'];messages=data['messages']
    if (unmatched(messages) or wire['messages'][-1]['role']!='user'
            or DeepSeekModel.format_request_messages(messages,wire['messages'][0]['content'])!=wire['messages'][:-1]):
        raise ValueError('SDK_ORIGINAL_WIRE_HISTORY_MISMATCH')
    requests={};feedback={}
    for e in events:
        if e['kind'] in ('model_original_tool_request','model_original_tool_feedback'):
            value=host.store.artifact(e['outputs'][0]);use=value['tool_use']
            (requests if e['kind']=='model_original_tool_request' else feedback)[use['toolUseId']]=use
    if requests!=feedback:raise ValueError('UNPAIRED_OR_CHANGED_NATIVE_FEEDBACK')
    ledger=host.store.remaining()
    return dict(study_id=host.run_id,resolved_identity=s['spec']['resolved_identity'],freeze=s['freeze'],
        request_id=request_id,request_hash=row['request_hash'],original_wire=meta['request'],
        source_state_identity=digest(s),source_call_identity=digest(row),ledger_identity=digest(ledger),
        native_history_identity=digest(messages),native_tool_pairs=len(requests),
        sdk_files=snapshot_files(directory,s['pilot']['framework_session_id']),
        policy=POLICY,provider_used=ledger['used']['model_calls'],provider_limit=ledger['limit']['model_calls'])


def loss_disposition(host,row):
    """Accept only a separately approved local loss receipt; remote stays unknown."""
    if not row.get('receipt'):return None
    receipt=json.loads(row['receipt'])
    if receipt['execution_status']!='failed' or receipt.get('error')!=ERROR:return None
    value=host.store.artifact(receipt['output'])
    approval=host.store.artifact(value['authorization']);scope=approval['scope'];s=state(host)
    if (value.get('version')!='provider_response_loss_disposition_v1' or value.get('remote_outcome')!='unknown'
            or approval.get('user_approval') is not True or approval.get('scope_identity')!=digest(scope)
            or scope.get('policy')!=POLICY or scope.get('study_id')!=host.run_id
            or scope.get('resolved_identity')!=s['spec']['resolved_identity'] or scope.get('freeze')!=s['freeze']
            or scope.get('request_id')!=row['request_id'] or scope.get('request_hash')!=row['request_hash']
            or receipt['charged']!=json.loads(row['reserved'])):
        raise ValueError('INVALID_AUTHORIZED_LOSS_RECEIPT')
    if not any(e['kind']=='provider_response_loss_authorization' and value['authorization'] in e['outputs']
            for e in host.store.events(host.run_id)):raise ValueError('LOSS_AUTHORIZATION_EVENT_REQUIRED')
    return value


def apply(host,approval):
    if (approval.get('version')!='provider_response_loss_authorization_v1' or approval.get('user_approval') is not True
            or approval.get('scope_identity')!=digest(approval.get('scope')) or not approval.get('source')):
        raise ValueError('EXPLICIT_IDENTITY_BOUND_LOSS_APPROVAL_REQUIRED')
    scope=approval['scope'];row=host.store.lookup(host.run_id,scope['request_id'])
    if row and row['receipt']:
        prior=loss_disposition(host,row)
        if prior and host.store.artifact(prior['authorization'])['scope_identity']==approval['scope_identity']:
            return dict(already_applied=True,receipt=json.loads(row['receipt']))
        raise ValueError('EXISTING_RECEIPT_MUST_NOT_CHANGE')
    actual=inspect(host,scope['request_id'])
    if actual!=scope:raise ValueError('APPROVED_RECOVERY_SCOPE_CHANGED')
    with host.store.transaction() as db:
        current=host.store.lookup(host.run_id,scope['request_id'],db)
        before=host.store.remaining(db=db)
        if (digest(current)!=scope['source_call_identity'] or digest(before)!=scope['ledger_identity']
                or digest(host.store.session(host.run_id,db)['state'])!=scope['source_state_identity']
                or snapshot_files(host.store.root/'framework_sessions',state(host)['pilot']['framework_session_id'])!=scope['sdk_files']):
            raise ValueError('RECOVERY_BOUNDARY_CHANGED')
        authorization=plain(host.store.put(db,approval));original=plain(host.store.put(db,current))
        host.store.event(db,host.run_id,'provider_response_loss_authorization','approved',
            request=current['request_id'],outputs=[authorization,original])
        output=dict(version='provider_response_loss_disposition_v1',remote_outcome='unknown',
            local_outcome=POLICY['local_outcome'],authorization=authorization,original_call=original,
            original_wire=scope['original_wire'],no_response_fabricated=True,no_tool_submitted=True)
        receipt=host.store.complete(current,dict(request_id=current['request_id'],execution_id=current['execution_id'],
            caller=current['caller'],tool_id='model.deepseek',tool_version='1.0.0',execution_status='failed',
            error=ERROR,charged=zero()),output,elapsed=json.loads(current['charged'])['wall_s'],
            kind='provider_response_loss_disposition',db=db)
        after=host.store.remaining(db=db)
        if before['used']!=after['used'] or before['remaining']!=after['remaining'] or before['limit']!=after['limit']:
            raise ValueError('LOSS_SETTLEMENT_MUST_RETAIN_ALL_COSTS')
        if digest(host.store.session(host.run_id,db)['state'])!=scope['source_state_identity']:
            raise ValueError('LOSS_SETTLEMENT_MUST_NOT_CHANGE_RESEARCH_STATE')
    return dict(already_applied=False,receipt=receipt,ledger=host.store.remaining(),authorization=authorization)


def approve_from_standing(host,reference,request_id):
    """Derive only this verified loss disposition from the user's standing scope."""
    grant=host.store.artifact(reference);scope=grant.get('scope',{});s=state(host)
    frozen_limits={k:s['spec'][k] for k in ('budgets','nmpc_limits','rl_limits')}
    if (grant.get('version')!='continuous_engineering_authorization_v1' or grant.get('user_approval') is not True
            or grant.get('scope_identity')!=digest(scope) or scope.get('study_id')!=host.run_id
            or scope.get('resolved_identity')!=s['spec']['resolved_identity'] or scope.get('freeze')!=s['freeze']
            or scope.get('limits_identity')!=digest(frozen_limits)
            or 'verified_provider_response_loss' not in scope.get('operations',[])):
        raise ValueError('CURRENT_STUDY_STANDING_ENGINEERING_APPROVAL_REQUIRED')
    exact=inspect(host,request_id)
    return dict(version='provider_response_loss_authorization_v1',user_approval=True,scope=exact,
        scope_identity=digest(exact),standing_authorization=reference,
        source='Current user explicitly authorized continuous engineering recovery within original finite Study limits; '
            'this exact exited-owner response loss passed the same original-wire/SDK/receipt checks.')


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['inspect','apply'])
    p.add_argument('--run-id',required=True);p.add_argument('--request-id');p.add_argument('--authorization');p.add_argument('--output')
    a=p.parse_args();h=Host(ROOT/'runs/research'/a.run_id,a.run_id,actor='unified-research')
    if a.command=='inspect':
        if not a.request_id:p.error('--request-id required')
        value=inspect(h,a.request_id)
    else:
        if not a.authorization:p.error('--authorization required')
        value=apply(h,read(a.authorization))
    if a.output:atomic_json(a.output,value)
    print(json.dumps(value))


if __name__=='__main__':main()
