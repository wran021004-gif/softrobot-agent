"""One bounded, isolated saved-evidence decision probe; scientific workers are unreachable."""
import argparse
import asyncio
from copy import deepcopy
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import httpx
from jsonschema import Draft202012Validator
from schemas.platform import ProjectConfig
from tools.platform_host import Host
from tools.platform_store import plain
from tools.research import agent, core, reporter, analysis
from tools.research.config import ROOT
from tools.research.contracts import Plan, AnalysisRequest
from tools.research.evidence_policy import admit_decision
from tools.research.state import state, update, science_hashes
from tools.state_io import digest
from tests.research.c3_readiness_audit import FrozenDecisionBoundary

PROBE_ID='main-off-saved-c3-v4-20261028'
DEST=ROOT/'runs/research'/PROBE_ID
POLICY={'version':'research_roles_v2',
    'main':{'thinking':'disabled','reasoning_effort':'none'},
    'reporter':{'thinking':'enabled','reasoning_effort':'low'}}
SOURCE_DB=ROOT.parent/'b3-r0-decision-efficiency/runs/research/b3-r1-history-assisted-050/platform.sqlite'
INSTRUCTIONS=('You are the research decision Agent. Use the frozen task and saved observations to choose a scientific direction freely. '
    'Distinguish independent measurements, mathematical predictions and unresolved hypotheses. Cite sources and state what would support or weaken your hypothesis. '
    'This is a read-only probe using a historical case, not a new Study. Mathematical method availability is hypothetical probe-only eligibility. '
    'All proposed scientific workers and physical operations are intercepted; no new scientific result is produced. Use English.')


def copy_ownership(host, source):
    """Copy genuine child ownership and sealed events; archive calls separately.

    Historical charged calls never enter the probe's shared provider ledger.
    Every byte is verified by the existing content-addressed Store.
    """
    if not SOURCE_DB.is_file():raise ValueError('ORIGINAL_C3_EXECUTION_STORE_REQUIRED')
    db=sqlite3.connect(SOURCE_DB.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    ownership=[]
    try:
        for ref in source.saved_state['results']:
            result=source.artifact(ref);execution=result['execution_id']
            owner=result['execution']['design_statement']['owner_run_id']
            row=db.execute('SELECT * FROM sessions WHERE run_id=?',(owner,)).fetchone()
            if row is None:raise ValueError('ORIGINAL_EXECUTION_SESSION_MISSING')
            owner_state=json.loads(row['state']);metadata=owner_state.get('result_executions',{}).get(execution)
            if not metadata:raise ValueError('ORIGINAL_EXECUTION_OWNERSHIP_MISSING')
            events=list(db.execute('SELECT body FROM events WHERE run_id=? ORDER BY seq',(owner,)))
            calls=[dict(r) for r in db.execute('SELECT * FROM calls WHERE run_id=?',(owner,))]
            boundary=next(e for e in source.snapshot['events'] if e['sequence']==425)['timestamp']
            if any(json.loads(e['body'])['timestamp']>boundary for e in events):
                raise ValueError('ORIGINAL_EXECUTION_EVENT_AFTER_FROZEN_BOUNDARY')
            simulations=[json.loads(e['body']) for e in events if json.loads(e['body']).get('kind')=='simulation' and json.loads(e['body']).get('execution_id')==execution]
            if not simulations or result['owning_study']!=source.preparation['study_id']:
                raise ValueError('ORIGINAL_EXECUTION_PROVENANCE_MISMATCH')
            # The output receipt in the frozen result must match this execution.
            receipt=result['execution']['completion_stages']['simulation']['receipt']
            if receipt['execution_id']!=execution or receipt.get('output',{}).get('artifact_id')!=metadata['artifact_id']:
                raise ValueError('ORIGINAL_EXECUTION_RECEIPT_MISMATCH')
            queue=[dict(row),*[json.loads(e['body']) for e in events],calls]
            seen=set()
            def refs(v):
                if isinstance(v,dict):
                    if isinstance(v.get('artifact_id'),str) and isinstance(v.get('media_type'),str):yield v['artifact_id']
                    for item in v.values():yield from refs(item)
                elif isinstance(v,list):
                    for item in v:yield from refs(item)
            queue.extend([owner_state,json.loads(row['snapshot'])] if row['snapshot'].startswith('{') else [owner_state])
            pending=[row['snapshot']]
            while queue or pending:
                if queue:pending.extend(refs(queue.pop()));continue
                identity=pending.pop()
                if identity in seen:continue
                seen.add(identity);artifact=db.execute('SELECT body,media FROM artifacts WHERE id=?',(identity,)).fetchone()
                if artifact is None:raise ValueError('ORIGINAL_EXECUTION_ARTIFACT_MISSING: '+identity)
                body=artifact['body'];media=artifact['media']
                with host.store.transaction() as dest:copied=host.store.put(dest,body,media=media)
                if copied.artifact_id!=identity:raise ValueError('ORIGINAL_EXECUTION_ARTIFACT_CHANGED')
                if media=='application/json':
                    try:queue.append(json.loads(body))
                    except (ValueError,UnicodeError):pass
            with host.store.transaction() as dest:
                dest.execute('INSERT INTO sessions VALUES (?,?,?,?)',tuple(row))
                dest.executemany('INSERT INTO events (run_id,body) VALUES (?,?)',[(owner,e['body']) for e in events])
                calls_ref=plain(host.store.put(dest,dict(source_store=str(SOURCE_DB),owner=owner,calls=calls)))
            ownership.append(dict(owner=owner,execution_id=execution,result=ref,source_calls=calls_ref,
                events=len(events),calls=len(calls),artifact_count=len(seen)))
    finally:db.close()
    return ownership


def prepare(directory=DEST, run_id=PROBE_ID, *, authorization=None, analysis_interface='bound_scientific_variables_v1'):
    if analysis_interface not in ('bound_scientific_variables_v1','bound_scientific_variables_v2'):
        raise ValueError('VERSIONED_ANALYSIS_INTERFACE_REQUIRED')
    if directory.exists():raise ValueError('PROBE_DIRECTORY_EXISTS_NO_RESET_OR_RETRY')
    source=FrozenDecisionBoundary(ROOT,'A');s=deepcopy(source.saved_state)
    provider=deepcopy(s['pilot']['provider']);provider.update(POLICY['main']);provider.update(max_tokens=None,output_context_reserve_tokens=32768)
    b=s['spec']['budgets'];b.update(provider_requests=8,protected_provider_requests=0,public_operations=30,protected_public_operations=0,physical_launches=0)
    s['spec']['physical_replay_limit']=0;s['spec']['nmpc_limits']['executions']=0
    s['spec'].pop('initial_structure_strategy',None)  # Existing candidate; no launch readiness claim.
    s['spec']['execution_instructions']=INSTRUCTIONS
    s['spec']['authorization']=authorization or 'OFFLINE_FIXTURE_ONLY_NO_LIVE_PROVIDER_AUTHORIZATION'
    s['spec']['research_decisions'].update(architecture='english_decision_v1',role_policy=deepcopy(POLICY),
        analysis_interface=analysis_interface)
    s['spec']['runtime']['provider']=deepcopy(provider)
    s['plans']=[];s['pending']=None;s['research_status']='ready';s['success_gate']=None;s['selected']=None
    s['pilot']=dict(provider=provider,live_model_requests=0,framework_session_id=run_id,request_deadline_unix=None)
    snap=deepcopy(source.snapshot['session']['snapshot']);snap['input']['run_id']=run_id
    budget=dict(model_calls=8,tool_calls=30,backend_solves=0,worker_calls=0,wall_s=None)
    snap['input']['policy']['budget']=budget
    h=Host(directory,run_id,actor='probe-only')
    h.store.create(ProjectConfig(project_id=run_id,grant_id=run_id+'-provider-only',
        authorization_source=s['spec']['authorization'],
        budget=budget,exclusive_resources={'provider_request':1}))
    h.store.create_session(snap)
    # Copy only artifacts already reachable at the frozen boundary. Their original
    # bytes and Store identities remain unchanged; the historical archive is read-only.
    for member in source.archive.getmembers():
        if not member.name.startswith('artifacts/'):continue
        name=Path(member.name).name;identity=name.rsplit('.',1)[0]
        if identity not in source.allowed:continue
        body=source.archive.extractfile(member).read()
        media='application/json' if name.endswith('.json') else 'application/octet-stream'
        with h.store.transaction() as db:
            ref=h.store.put(db,body,media=media)
        if ref.artifact_id!=identity:raise ValueError('ARCHIVE_ARTIFACT_IDENTITY_MISMATCH')
    ownership=copy_ownership(h,source)
    update(h,**s)
    result_ids={r['artifact_id'] for key in ('results','physical_replays','analysis_results','mechanics_results','rl_evaluations') for r in s.get(key,[])}
    for event in source.events:
        outputs=event.get('outputs',[])
        if event['kind']=='research_report' or any(r['artifact_id'] in result_ids for r in outputs):
            with h.store.transaction() as db:
                h.store.event(db,run_id,event['kind'],event['status'],outputs=outputs)
    diff=[k for k,v in s['profile']['science_hashes'].items() if science_hashes().get(k)!=v]
    agent.record(h,'probe_scope',dict(source_study=source.preparation['study_id'],
        source_state=source.preparation['source_state'],archive=source.folder,source_boundary_sequence=425,
        maximum_main=8,maximum_reporter=0,maximum_total=8,backend_solves=0,worker_calls=0,
        first_analysis_feedback_turn_reserved=True,live_authorization=authorization,
        analysis_interface=analysis_interface,
        original_ownership=ownership,
        hypothetical_mathematical_eligibility=True,historical_scientific_code_changes=diff,
        no_scientific_dispatch=True,automatic_retries=0))
    source.archive.close()
    return h


class CappedTransport(httpx.AsyncBaseTransport):
    def __init__(self,inner,counts=None,*,host):
        self.inner=inner;self.counts=counts or {'conversation':0,'reporter':0};self.host=host
    def admit(self,wire):
        role='conversation' if wire.get('tools') else 'reporter'
        if self.counts[role]>={'conversation':8,'reporter':0}[role] or sum(self.counts.values())>=8:
            raise ValueError('PROBE_LIVE_ROLE_CAP_NO_SEND')
        feedback=any(e['kind']=='model_original_tool_feedback' and
            self.host.store.artifact(e['outputs'][0])['tool_use']['name']=='research_analysis'
            for e in self.host.store.events(self.host.run_id))
        if self.counts['conversation']>=7 and not feedback:
            agent.record(self.host,'probe_incomplete',dict(reason='First analysis feedback turn cannot be guaranteed; remaining request is reserved.',requests=self.counts))
            raise ValueError('PROBE_FEEDBACK_TURN_RESERVED_NO_SEND')
        return role,feedback
    async def handle_async_request(self,request):
        role,feedback=self.admit(json.loads(request.content))
        if feedback:
            agent.record(self.host,'probe_analysis_feedback_delivery',dict(request_number=self.counts['conversation']+1,
                scope='Actual next request; model correction or understanding must be assessed from its response.'))
        self.counts[role]+=1
        return await self.inner.handle_async_request(request)
    async def aclose(self):await self.inner.aclose()


def safe_guard(host,expensive=False):
    remaining=host.store.remaining()
    if remaining['limit']['backend_solves']!=0 or remaining['limit']['worker_calls']!=0 or expensive:
        raise ValueError('PROBE_SCIENTIFIC_EXECUTION_FORBIDDEN')
    if state(host).get('pending'):raise ValueError('PROBE_PENDING_EXECUTION')


def intercepts(host):
    original=core.dispatch
    def plan(h,value,request_id,origin='model'):
        parsed=Plan.model_validate(value);admit_decision(h,parsed)
        if parsed.action=='diagnose' and parsed.diagnostic is None:
            return original(h,value,request_id,origin=origin)
        item=dict(status='probe_only_not_executed',action=parsed.action,
            execution_feedback=dict(status='probe_only_not_executed',worker_started=False,
                scientific_execution_started=False,reason='Scientific actions are intercepted; no observation or acceptance was generated.'))
        agent.record(h,'probe_plan_intercept',dict(plan=plain(parsed),outcome=item))
        return dict(result=item,scientific_results=[])
    def math(h,query,key,*,guard,origin='model'):
        selected=agent.selected_analysis(h,None)
        if not selected:raise ValueError('PROBE_NO_SETTLED_SELECTED_METHOD')
        method,detail=selected;schema=agent.selected_analysis_schema(method,detail)
        Draft202012Validator(schema).validate(query)
        q=AnalysisRequest.model_validate(query)
        from tools.research.design import verify_candidate
        candidate=verify_candidate(h,q.candidate)
        if plain(q.protocol)!=state(h)['spec']['analysis_protocol']:raise ValueError('PROBE_PROTOCOL_MISMATCH')
        if q.operation!=detail['operation']:raise ValueError('PROBE_METHOD_MISMATCH')
        source=detail.get('request_template',{}).get('model_source')
        if source and q.model_source!=source:raise ValueError('PROBE_MODEL_SOURCE_MISMATCH')
        from schemas.platform import SessionInput
        from tools.research.task_constraints import describe_analysis_requirements,model_assessment,check_analysis_applicability
        from tools.research.state import guard as original_guard
        inp=SessionInput.model_validate(candidate['configuration'])
        requirements=describe_analysis_requirements(inp,{})
        exact_point=None
        if q.model_source=='mujoco':
            from tools.research.numerics import native_point
            exact_point=native_point(h,q,candidate['configuration'])
        applicability=check_analysis_applicability(requirements,q,model_assessment(inp,requirements,q.operation,model_source=q.model_source),exact_point=exact_point)
        try:
            original_guard(h,expensive=True);guard_status='passed'
        except ValueError as exc:
            guard_status=str(exc)
        changed=[k for k,v in state(h)['profile']['science_hashes'].items() if science_hashes().get(k)!=v]
        outcome=dict(status='probe_only_not_executed',method=method,operation=q.operation,
            schema_valid=True,typed_request_valid=True,candidate_binding_valid=True,protocol_matches=True,
            model_source=q.model_source,task_identity=detail.get('task_identity'),
            deterministic_applicability=plain(applicability),original_guard=guard_status,
            exact_source_validation=('native_point_validated_without_worker_reconstruction' if q.model_source=='mujoco' else
                'not_required_for_declared_point' if q.operating_point!='saved_state' else 'not_run_original_reduced_saved_source_admission'),
            full_scientific_preflight='not_run_historical_dependencies_changed' if changed else 'not_run',
            execution_feedback=dict(status='probe_only_not_executed',worker_started=False,scientific_execution_started=False,
                reason='No worker launched and no scientific result or task acceptance was produced.'))
        agent.record(h,'probe_analysis_intercept',dict(request=plain(q),outcome=outcome))
        return dict(result=outcome,scientific_results=[])
    return plan,math


async def run(host,inner,*,max_requests=8):
    previous=reporter.provider_usage(host)
    counts={role:previous.get(role,{}).get('requests',0) for role in ('conversation','reporter')}
    plan,math=intercepts(host);transport=CappedTransport(inner,counts,host=host)
    original_boundary=agent.LiveBoundary.handle_async_request
    async def admitted_boundary(boundary,request):
        # Reserve the feedback turn before the production ledger records an
        # attempted send. Exact saved-response replay needs no new allowance.
        if not state(host)['pilot'].get('unconsumed_response'):
            transport.admit(json.loads(request.content))
        return await original_boundary(boundary,request)
    # Probe-only patch scope: all scientific Plan and analysis dispatch is
    # intercepted, and the shared ledger has zero worker/backend capacity.
    with (patch('tools.research.core.guard',safe_guard),patch('tools.research.agent.guard',safe_guard),
         patch('tools.research.core.dispatch',side_effect=plan),patch('tools.research.analysis.dispatch',side_effect=math),
         patch('tools.research.rl.dispatch',side_effect=ValueError('PROBE_RL_FORBIDDEN')),
         patch.object(agent.LiveBoundary,'handle_async_request',admitted_boundary),
         patch('tools.research.research_context.mathematics_authorization',return_value={
             'registered_study_scope_authorized':True,'methods':[],
             'method_preconditions':'Probe-only eligibility; no scientific execution authorized.'}),
         patch('httpx.AsyncHTTPTransport',return_value=transport)):
        await agent.converse(host,max_new_provider_requests=max_requests,pause_after_completed_invocations=1)
    return transport.counts


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--continue-once',action='store_true')
    parser.add_argument('--authorization',help='Exact separately granted provider-only authorization, up to 8 Main requests, zero workers.')
    parser.add_argument('--probe-id',default=PROBE_ID,help='New independent Store/ledger identity; existing directories are never reset.')
    parser.add_argument('--analysis-interface',choices=('bound_scientific_variables_v1','bound_scientific_variables_v2'),default='bound_scientific_variables_v1')
    args=parser.parse_args()
    if not args.live or not args.authorization:raise SystemExit('A new explicit independent provider-only authorization and --live are required; prior v1-v3 grants are exhausted.')
    import re
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,95}',args.probe_id):raise ValueError('BOUNDED_PROBE_ID_REQUIRED')
    destination=ROOT/'runs/research'/args.probe_id
    agent.load_credential(Path('~/.codex/.env').expanduser())
    if args.continue_once:
        h=Host(destination,args.probe_id,actor='probe-only');usage=reporter.provider_usage(h)
        if (usage.get('conversation',{}).get('requests',0)>6 or usage.get('reporter',{}).get('requests',0)!=0
                or state(h)['spec']['authorization']!=args.authorization
                or state(h)['spec']['research_decisions']['analysis_interface']!=args.analysis_interface
                or agent.pending(h) or state(h)['pilot'].get('unconsumed_response')
                or any(e['kind']=='probe_continuation' for e in h.store.events(h.run_id))):
            raise ValueError('PROBE_CONTINUATION_REQUIRES_SETTLED_INVOCATION_AND_FEEDBACK_RESERVE')
        agent.record(h,'probe_continuation',dict(reason='Ordinary continuation; no repair, method direction or worker execution.',max_new_requests=8-usage.get('conversation',{}).get('requests',0)))
        counts=asyncio.run(run(h,httpx.AsyncHTTPTransport(retries=0)))
    else:
        h=prepare(destination,args.probe_id,authorization=args.authorization,analysis_interface=args.analysis_interface)
        counts=asyncio.run(run(h,httpx.AsyncHTTPTransport(retries=0)))
    print(json.dumps(dict(probe=args.probe_id,store=str(destination),requests=counts,usage=reporter.provider_usage(h),
        ledger=h.store.remaining(),scientific_workers=0,physical_launches=0),ensure_ascii=False))

if __name__=='__main__':main()
