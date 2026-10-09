"""Linked formal closeout using the saved Strands session and existing Store authority."""
import argparse
from copy import deepcopy
import hashlib
import importlib.metadata
import shutil
from pathlib import Path
import time

from tools.strands_pilot import ROOT, TARGET, Host, InvestigationDispatcher
from tools.strands_pilot_r3 import (pilot, pending, record, build_live, live_scope,
    set_phase, context_proof, reopen_live, export, audit)
from tools.platform_store import Store, plain, zero, encode
from tools.state_io import atomic_json, digest

AUTHORIZATION = ('User authorization 2026-10-09: linked formal-submission closeout; '
    'saved V1 fixed-C evidence and necessary saved session context to https://api.deepseek.com '
    'using existing deepseek-flash; 24 additional provider attempts shared by conversation, '
    'corrections, summaries and retries; 2h including preparation; zero scientific solves '
    'and robot executions; normal commit and push of feat/strands-runtime-pilot.')
PROMPT = """The original 40-attempt activity stopped without a valid submission. This is its
explicitly authorized linked formal closeout, with one shared allowance of 24 additional
provider attempts and a two-hour overall limit. Your saved conversation, summary, source
index, original pages and prior independent inspections have been restored. Continue the
existing four judgments: arrival, holding position, holding speed and joint acceptance.
Check only evidence still needed for this existing decision, submit your formal decision
through submit_result revision 1, then get_receipt. Do not rediscover the directory or repeat
the complete analysis. Do not force another retrieval or summary demonstration. The complete
native schema is now exposed and evidence_used has no item-count maximum. scope is a list
of SourceFact objects. Partial objects cannot cite whole-object pointers: use individual
fields or exact complete objects. supporting_facts must match the extraction report's
facts exactly; supplementary original facts belong in evidence_used. Correct concrete
validation feedback within this same allowance. Multiple native reads may be requested
together; the framework executes each sequentially. Preserve exact numerical evidence,
identity, applicability and limitations. No new experiment, solve, agent or candidate.
"""


def preserved_files(directory):
    """Read-only fingerprints of the stopped ledger and framework persistence."""
    files=[directory/'business/platform.sqlite', *sorted((directory/'sessions').rglob('*'))]
    return {p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file()}


def prepare(directory, source_directory, source_activity, started_unix):
    directory=Path(directory).resolve();source_directory=Path(source_directory).resolve()
    if not directory.is_relative_to(ROOT/'runs'):raise ValueError('PILOT_DIRECTORY_MUST_BE_UNDER_WORKTREE_RUNS')
    if directory.exists():raise ValueError('CLOSEOUT_EXISTS_USE_RESUME_NO_NEW_ALLOWANCE')
    old=Host(source_directory/'business',source_activity,actor='strands-pilot')
    session=old.store.session(source_activity);prior=pilot(old)
    if prior.get('mode')!='live-r3' or prior.get('phase')!='stopped_budget':
        raise ValueError('STOPPED_ORIGINAL_R3_REQUIRED')
    if pending(old) or prior.get('unconsumed_response'):raise ValueError('UNRESOLVED_ORIGINAL_REQUEST_BLOCKS_CLOSEOUT')
    if prior['live_model_requests']!=40:raise ValueError('EXPECTED_HISTORICAL_40_ATTEMPTS')
    if time.time()>=started_unix+7200:raise ValueError('CLOSEOUT_AUTHORIZATION_EXPIRED')
    activity=source_activity+'-closeout'
    before=preserved_files(source_directory)
    budget={**zero(),'model_calls':24,'tool_calls':512,'wall_s':7200.}
    snapshot=deepcopy(session['snapshot']);snapshot['input']['run_id']=activity
    snapshot['input']['policy']['budget']=budget
    snapshot['input_identity']=digest(snapshot['input'])
    store=Store(directory/'business')
    store.create(dict(project_id=activity,grant_id=activity,authorization_source=AUTHORIZATION,
        budget=budget,exclusive_resources={'provider_request':1}))
    store.create_session(snapshot)
    # Import immutable originals and saved read artifacts through the public Store
    # mechanism. Historical calls, charges and failed submissions stay in the old Store.
    with old.store.connect(True) as db:
        artifacts=[dict(r) for r in db.execute('SELECT id,media,body FROM artifacts')]
    with store.transaction() as db:
        for row in artifacts:
            ref=store.put(db,row['body'],media=row['media'])
            if ref.artifact_id!=row['id']:raise ValueError('HISTORICAL_ARTIFACT_IDENTITY_CHANGED')
        state=deepcopy(session['state'])
        grant=state['role_context']['investigation_grant'];grant['deadline_unix']=started_unix+7200
        if 'investigation_grant_identity' in state:state['investigation_grant_identity']=digest(grant)
        state['pilot'].update(activity_id=activity,started_unix=started_unix,deadline_unix=started_unix+7200,
            request_deadline_unix=started_unix+7200-prior['provider']['timeout_s'],phase='closeout_ready',
            framework_session_id=prior.get('framework_session_id',source_activity),live_model_requests=0,
            predecessor=dict(activity=source_activity,directory=str(source_directory),phase=prior['phase'],
                ledger=old.store.remaining(),file_fingerprints=before),authorization=AUTHORIZATION)
        store.update_state(db,activity,state,'running')
        store.event(db,activity,'closeout_authorization','authorized',outputs=[store.put(db,dict(
            authorization=AUTHORIZATION,predecessor=state['pilot']['predecessor'],
            inherited_inspection_ids=[r['inspection_id'] for r in state.get('principal_investigation_reads',[])],
            target=TARGET,sources=prior['sources'],report=prior['report'],budget=budget))])
    shutil.copytree(source_directory/'sessions',directory/'sessions')
    if preserved_files(source_directory)!=before:raise ValueError('ORIGINAL_RECORD_CHANGED')
    host=Host(store.root,activity,actor='strands-pilot');host.folder.mkdir(parents=True,exist_ok=True)
    atomic_json(directory/'authorization.json',dict(activity=activity,authorization=AUTHORIZATION,
        started_unix=started_unix,deadline_unix=started_unix+7200,predecessor=state['pilot']['predecessor']))
    return host


def verify_preservation(host):
    prior=pilot(host)['predecessor']
    if preserved_files(Path(prior['directory']))!=prior['file_fingerprints']:
        raise ValueError('STOPPED_ORIGINAL_RECORD_CHANGED')
    return dict(original_files_unchanged=True,predecessor=prior['activity'])


def execute(host, feedback=None, recover_response=False, transport=None, key=None):
    versions={k:importlib.metadata.version(k) for k in ('strands-harness','strands-agents')}
    if versions!={'strands-harness':'0.2.0','strands-agents':'1.59.0'}:raise ValueError('PINNED_R3_DEPENDENCIES_REQUIRED')
    if pilot(host)['phase']!='closeout_ready':raise ValueError('CLOSEOUT_NOT_READY')
    if pending(host):raise ValueError('UNCONFIRMED_ATTEMPT_STOPPED')
    if time.time()>=pilot(host)['request_deadline_unix']:raise ValueError('CLOSEOUT_DELIVERY_WINDOW_EXPIRED')
    if host.store.spendable(host.run_id)['remaining']['model_calls']<1 and not (
        recover_response and pilot(host).get('unconsumed_response')):
        raise ValueError('CLOSEOUT_PROVIDER_BUDGET_EXHAUSTED')
    verify_preservation(host)
    with live_scope() as counts:
        agent=build_live(host,transport,key)
        restored=context_proof(agent)
        record(host,'closeout_restoration',dict(context=restored,framework_session_id=pilot(host)['framework_session_id']))
        try:
            result=agent(None if recover_response else feedback or PROMPT)
        except Exception as exc:
            record(host,'r3_invocation_failure',dict(action='closeout',exception_type=type(exc).__name__,
                scope=counts,budget=host.store.remaining()),status='stopped')
            raise
        record(host,'r3_invocation',dict(action='closeout',result=str(result),context=context_proof(agent),scope=counts))
    receipt=InvestigationDispatcher(host).disposition_receipt(TARGET,1)
    if not receipt:raise ValueError('CLOSEOUT_NO_FORMAL_RECEIPT_CORRECTION_PERMITTED')
    if pending(host) or pilot(host).get('unconsumed_response'):raise ValueError('CLOSEOUT_NOT_AT_SAVED_BOUNDARY')
    set_phase(host,'submitted')
    return receipt


def evidence(host, destination):
    export(host,destination)
    observed=audit(host)
    receipt=InvestigationDispatcher(host).disposition_receipt(TARGET,1)
    first=host.store.artifact(receipt['output']) if receipt else None
    again=InvestigationDispatcher(host).disposition_receipt(TARGET,1)
    observed.update(assessment='Formal submission closed; cumulative R3 evidence linked' if receipt else 'Closeout incomplete',
        predecessor=pilot(host)['predecessor'],preservation=verify_preservation(host),
        prior_evidence='evidence/strands_runtime_pilot_r3_20261009/acceptance.json',
        lookup_same_record=bool(receipt) and receipt==again and first==host.store.artifact(again['output']))
    atomic_json(destination/'acceptance.json',observed)
    return observed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','resume','receipt','export'])
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--source-directory',type=Path)
    parser.add_argument('--source-activity',default='strands-pilot-r3-20261009')
    parser.add_argument('--started-unix',type=float)
    parser.add_argument('--evidence-directory',type=Path)
    parser.add_argument('--feedback')
    parser.add_argument('--recover-response',action='store_true')
    args=parser.parse_args()
    if args.action=='prepare':
        if args.source_directory is None or args.started_unix is None:parser.error('prepare requires source directory and original authorization start time')
        host=prepare(args.directory,args.source_directory,args.source_activity,args.started_unix)
    else:host=reopen_live(args.directory,args.source_activity+'-closeout')
    if args.action=='resume':execute(host,args.feedback,args.recover_response)
    if args.action=='receipt':
        before=host.store.remaining();dispatcher=InvestigationDispatcher(host)
        receipt=dispatcher.disposition_receipt(TARGET,1)
        repeated=dispatcher.disposition_receipt(TARGET,1)
        if receipt!=repeated or before!=host.store.remaining():raise ValueError('RECEIPT_LOOKUP_CHANGED_STATE')
        atomic_json(args.directory/'receipt.json',dict(receipt=receipt,
            record=host.store.artifact(receipt['output']) if receipt else None,
            repeated_read_equal=True,ledger_unchanged=True))
    if args.action=='export':
        if not args.evidence_directory:parser.error('export requires evidence directory')
        evidence(host,args.evidence_directory)
    print(encode(dict(activity=host.run_id,phase=pilot(host)['phase'],budget=host.store.remaining(),
        preservation=verify_preservation(host))))


if __name__=='__main__':main()
