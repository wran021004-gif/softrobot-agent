"""One bounded, isolated saved-evidence decision probe; scientific workers are unreachable."""
import argparse
import asyncio
from copy import deepcopy
import json
import os
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

PROBE_ID='main-off-saved-c3-20261028'
DEST=ROOT/'runs/research'/PROBE_ID
POLICY={'version':'research_roles_v1',
    'main':{'thinking':'disabled','reasoning_effort':'none','max_tokens':4096},
    'reporter':{'thinking':'enabled','reasoning_effort':'low','max_tokens':2048}}
INSTRUCTIONS=('You are the research decision Agent. Use the frozen task and saved observations to choose a scientific direction freely. '
    'Distinguish independent measurements, mathematical predictions and unresolved hypotheses. Cite sources and state what would support or weaken your hypothesis. '
    'This is a read-only probe using a historical case, not a new Study. Mathematical method availability is hypothetical probe-only eligibility. '
    'All proposed scientific workers and physical operations are intercepted; no new scientific result is produced. Use English.')


def prepare(directory=DEST, run_id=PROBE_ID):
    if directory.exists():raise ValueError('PROBE_DIRECTORY_EXISTS_NO_RESET_OR_RETRY')
    source=FrozenDecisionBoundary(ROOT,'A');s=deepcopy(source.saved_state)
    provider=deepcopy(s['pilot']['provider']);provider.update(POLICY['main'])
    b=s['spec']['budgets'];b.update(provider_requests=8,protected_provider_requests=0,public_operations=30,protected_public_operations=0,physical_launches=0)
    s['spec']['physical_replay_limit']=0;s['spec']['nmpc_limits']['executions']=0
    s['spec'].pop('initial_structure_strategy',None)  # Existing candidate; no launch readiness claim.
    s['spec']['execution_instructions']=INSTRUCTIONS
    s['spec']['authorization']='User authorized this bounded provider-only decision probe; no scientific worker execution.'
    s['spec']['research_decisions'].update(architecture='english_decision_v1',role_policy=deepcopy(POLICY))
    s['spec']['runtime']['provider']=deepcopy(provider)
    s['plans']=[];s['pending']=None;s['research_status']='ready';s['success_gate']=None;s['selected']=None
    s['pilot']=dict(provider=provider,live_model_requests=0,framework_session_id=run_id,request_deadline_unix=None)
    snap=deepcopy(source.snapshot['session']['snapshot']);snap['input']['run_id']=run_id
    budget=dict(model_calls=8,tool_calls=30,backend_solves=0,worker_calls=0,wall_s=None)
    snap['input']['policy']['budget']=budget
    h=Host(directory,run_id,actor='probe-only')
    h.store.create(ProjectConfig(project_id=run_id,grant_id=run_id+'-provider-only',
        authorization_source='User authorized up to 8 real Provider requests and zero scientific workers.',
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
        maximum_main=6,maximum_reporter=2,maximum_total=8,backend_solves=0,worker_calls=0,
        hypothetical_mathematical_eligibility=True,historical_scientific_code_changes=diff,
        no_scientific_dispatch=True,automatic_retries=0))
    source.archive.close()
    return h


class CappedTransport(httpx.AsyncBaseTransport):
    def __init__(self,inner):self.inner=inner;self.counts={'conversation':0,'reporter':0}
    async def handle_async_request(self,request):
        wire=json.loads(request.content);role='conversation' if wire.get('tools') else 'reporter'
        if self.counts[role]>={'conversation':6,'reporter':2}[role] or sum(self.counts.values())>=8:
            raise ValueError('PROBE_LIVE_ROLE_CAP_NO_SEND')
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
        changed=[k for k,v in state(h)['profile']['science_hashes'].items() if science_hashes().get(k)!=v]
        outcome=dict(status='probe_only_not_executed',method=method,operation=q.operation,
            schema_valid=True,typed_request_valid=True,candidate_binding_valid=True,protocol_matches=True,
            model_source=q.model_source,full_scientific_preflight='not_run_historical_dependencies_changed' if changed else 'not_run',
            execution_feedback=dict(status='probe_only_not_executed',worker_started=False,scientific_execution_started=False,
                reason='No worker launched and no scientific result or task acceptance was produced.'))
        agent.record(h,'probe_analysis_intercept',dict(request=plain(q),outcome=outcome))
        return dict(result=outcome,scientific_results=[])
    return plan,math


async def run(host,inner,*,max_requests=6):
    plan,math=intercepts(host);transport=CappedTransport(inner)
    # Probe-only patch scope: all scientific Plan and analysis dispatch is
    # intercepted, and the shared ledger has zero worker/backend capacity.
    with (patch('tools.research.core.guard',safe_guard),patch('tools.research.agent.guard',safe_guard),
         patch('tools.research.core.dispatch',side_effect=plan),patch('tools.research.analysis.dispatch',side_effect=math),
         patch('tools.research.rl.dispatch',side_effect=ValueError('PROBE_RL_FORBIDDEN')),
         patch('tools.research.research_context.mathematics_authorization',return_value={
             'registered_study_scope_authorized':True,'methods':[],
             'method_preconditions':'Probe-only eligibility; no scientific execution authorized.'}),
         patch('httpx.AsyncHTTPTransport',return_value=transport)):
        await agent.converse(host,max_new_provider_requests=max_requests,pause_after_completed_invocations=1)
    return transport.counts


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    if not args.live:raise SystemExit('Use --live only after offline boundary validation; no automatic resend.')
    agent.load_credential(Path('~/.codex/.env').expanduser())
    h=prepare();counts=asyncio.run(run(h,httpx.AsyncHTTPTransport(retries=0)))
    print(json.dumps(dict(probe=PROBE_ID,store=str(DEST),requests=counts,usage=reporter.provider_usage(h),
        ledger=h.store.remaining(),scientific_workers=0,physical_launches=0),ensure_ascii=False))

if __name__=='__main__':main()
