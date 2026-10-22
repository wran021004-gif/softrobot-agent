"""Final F3.0 revalidation through production converse; requires fresh approval.

Only the transport counter is wrapped. Offline runs replace HTTP, never SDK hooks,
guards, tools, Reporter delivery or settlement. Live ID is fixed: no retry/reset.
Raw Store/SDK/body archives stay in ignored runs; audit exports only derived facts.
"""
import argparse
import asyncio
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch
from uuid import uuid4

import httpx
from tools.platform_host import Host
from tools.research import agent, core, reporter
from tools.research.config import ROOT
from tools.research.state import state, update, save, core_hashes
from tools.research.session_handoff import unmatched
from tools.state_io import atomic_json, read, digest

SEALED_ID='f30-live-20261022'
LIVE_ID='f30-revalidate-20261022-01'
SCOPE_PATH=ROOT/'evidence/s129_integration/f30_revalidation_scope.json'


def prepare(live=False, *, approved_commit=None):
    run_id=LIVE_ID if live else 'f30-revalidate-offline-'+uuid4().hex[:8]
    directory=ROOT/'runs/research'/run_id
    if live and directory.exists():
        raise ValueError('F30_SINGLE_ATTEMPT_ALREADY_EXISTS: audit original Store; never recreate grant')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if live:
        if approved_commit!=commit:
            raise ValueError('F30_EXPLICIT_APPROVED_COMMIT_REQUIRED: pass the separately approved full HEAD SHA')
        if (subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
                or subprocess.check_output(['git','rev-parse','origin/integration/s129-research'],cwd=ROOT,text=True).strip()!=commit):
            raise ValueError('F30_CLEAN_PUSHED_COMMIT_REQUIRED')
    proposal=read(SCOPE_PATH)
    raw=read(ROOT/'configs/research/study_s125_cold.json')
    raw.update(study_id=run_id,base_commit=commit,
        mode='engineering_investigation',tool_readiness=None,capabilities=['investigation'],
        allowed_plan_actions=['diagnose','stop'],authorization='PENDING_EXPLICIT_APPROVAL: F3.0 independent scope',
        evidence_destination='evidence/s129_integration/f30_revalidation')
    raw['budgets'].update(provider_requests=3,protected_provider_requests=0,public_operations=12,
        protected_public_operations=0,physical_launches=0,mathematical_evaluations=0,offline_nlp=0,bdf_replays=0)
    raw['nmpc_limits']['executions']=0
    raw['rl_limits'].update(training_stages=0,evaluation_episodes=0)
    raw['execution_instructions']=(
        'F3.0 read-only engineering delivery validation. The saved B-line results are imported '
        'historical engineering samples, never new results of this Study. On your first response, '
        'submit exactly one research_investigate request comparing the saved baseline and changed '
        'structure results, including the fixed-control versus reoptimized-control comparison. '
        'Choose the question, focus and exact result references yourself from the current packet. '
        'Ask what the recorded signed minimax scores, replay and solver facts support and leave unknown. '
        'After the tool result and delivered Reporter L1, give a concise scientific judgment in text: '
        'compare the two structures and the two controls on the changed structure separately, '
        'explain evidential limits, and propose one scientifically useful next choice with its purpose. '
        'That choice must respect this read-only Study: propose a saved-evidence investigation or '
        'diagnosis; any new computation needs a separately authorized future Study. Do not execute it '
        'or call additional tools in that second response. No scientific workers are authorized. '
        'The runner will close the engineering grant after the finite requests; do not invent a task pass.')
    pair=read(ROOT/'evidence/s129_math_capability/gvs_pair.json')
    source=pair['supporting_artifacts'][pair['baseline']['candidate']['artifact_id']]['configuration']
    task_path=ROOT/'runs'/(run_id+'-task.json')
    atomic_json(task_path,dict(task=source['task'],seed=source['seed'],
        settling=source['policy']['controller']['parameters']['data']['settling']))
    raw['task']=str(task_path)
    path=ROOT/'configs/research'/('._'+run_id+'.json')
    atomic_json(path,raw)
    try:h=core.prepare(path)
    finally:path.unlink()
    if live:core.bind(h)
    else:update(h,freeze='offline_fixture_no_live_admission',core_hashes=core_hashes())
    for value in pair['supporting_artifacts'].values():save(h,value,'imported_F1B_supporting_artifact')
    refs=[save(h,pair[k],'imported_F1B_result') for k in ('baseline','changed')]
    update(h,analysis_results=refs)
    for ref in refs:reporter._save(h,reporter.assemble(h,[ref]),status='deterministic_only')
    s=state(h)
    scope=dict(study_id=run_id,resolved_identity=s['spec']['resolved_identity'],implementation=s['freeze'],
        endpoint=s['pilot']['provider']['base_url']+'/chat/completions',provider=s['pilot']['provider'],
        task_identity=s['spec']['canonical_task_identity'],family_space_identity=s['spec']['family_space_identity'],
        budgets=s['spec']['budgets'],nmpc_limits=s['spec']['nmpc_limits'],rl_limits=s['spec']['rl_limits'],
        main_ceiling=2,reporter_ceiling=1,worker_executions=0,
        imported_results=refs,source='evidence/s129_math_capability/gvs_pair.json',source_identity=digest(pair),
        provenance='Imported original F1-B engineering results; no F3.0 scientific executions',
        outbound=['Frozen task/design/model configuration','Saved scoped B evidence and exact references',
            'Agent tool requests/feedback and Reporter interpretations','Research ledger and implementation identities'],
        prohibited=['Credentials or environment file content','Unrelated workspace/user data','Other Studies raw SDK histories'],
        local_archive=str(directory),raw_publication_authorized=False,
        revalidation_scope=proposal,revalidation_scope_identity=digest(proposal),
        approved_commit=approved_commit if live else None)
    agent.record(h,'formal_study_authorization',dict(scope=scope,scope_identity=digest(scope),
        user_approval=('Separate explicit live invocation for '+LIVE_ID+' at approved commit '+approved_commit+
            '; <=2 main, <=1 Reporter, <=3 total requests; zero science; no retry/reset or automatic F3')
            if live else 'OFFLINE FIXTURE ONLY; HTTP mocked'))
    agent.record(h,'f30_import_manifest',scope)
    atomic_json(directory/'scope.json',scope)
    return h,refs


class CappedBoundary(agent.LiveBoundary):
    """Reject before reservation/send, counting durable sends including failures."""
    async def handle_async_request(self, request):
        if not state(self.host)['pilot'].get('unconsumed_response'):
            role=getattr(self,'purpose',None) or ('conversation' if json.loads(request.content).get('tools') else 'summarization')
            usage=reporter.provider_usage(self.host)
            ceiling={'conversation':2,'reporter':1}.get(role,0)
            if usage.get(role,{}).get('requests',0)>=ceiling:
                raise ValueError('F30_ROLE_CAP_NO_SEND: '+role)
            if role=='conversation' and usage.get(role,{}).get('requests',0)==1:
                if not any(saved['interpretation_for'] and saved['interpretation_status']=='available'
                        for _,saved in reporter.current_reports(self.host)):
                    raise ValueError('F30_ACCEPTED_REPORTER_REQUIRED_NO_SEND')
        return await super().handle_async_request(request)


def mock_http(refs):
    mains=0
    def respond(request):
        nonlocal mains
        wire=json.loads(request.content)
        if not wire.get('tools'):
            from tests.research.test_s129_agent_reporting import reporter_response
            return reporter_response(request)
        mains+=1
        if mains==1:
            names={t['function']['name'] for t in wire['tools']}
            assert names=={'research_plan','research_investigate','evidence_read'},names
            message=dict(role='assistant',content=None,tool_calls=[dict(id='f30-native-investigate',type='function',
                function=dict(name='research_investigate',arguments=json.dumps(dict(
                    question='Compare both structures and both controls; what remains unproved?',references=refs))))])
            finish='tool_calls'
        else:
            assert mains==2
            packet=json.loads(wire['messages'][0]['content'].split('\nCURRENT_RESEARCH_PACKET\n')[1].split('\nPROTECTED CLOSEOUT:')[0])
            assert any(r['reporter_status']=='available' for r in packet['research']['latest_reports'])
            message=dict(role='assistant',content='OFFLINE FIXTURE: no scientific judgment or live admission.')
            finish='stop'
        return httpx.Response(200,json=dict(id='offline-f30',object='chat.completion',created=1,model=wire['model'],
            choices=[dict(index=0,finish_reason=finish,message=message)],
            usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12)))
    return httpx.MockTransport(respond)


def audit(run_id):
    if run_id==SEALED_ID:
        raise ValueError('F30_SEALED_HISTORY_READ_ONLY: do not rewrite its audit or SDK files')
    h=Host(ROOT/'runs/research'/run_id,run_id,actor='unified-research')
    s=state(h);events=h.store.events(run_id);requests=[];wires=[]
    for i,event in enumerate(events):
        if event['kind']!='r3_request':continue
        metadata=h.store.artifact(event['outputs'][0]);wire=h.store.artifact(metadata['request']);wires.append(wire)
        requests.append(dict(event_index=i,request_id=event['request_id'],purpose=metadata['purpose'],
            request_identity=digest(wire),request_reference=metadata['request'],
            tools=[t['function']['name'] for t in wire.get('tools',[])]))
    feedback=[h.store.artifact(e['outputs'][0]) for e in events if e['kind']=='model_original_tool_feedback']
    reports=reporter.current_reports(h)
    interpretations=[dict(reference=r,status=v['interpretation_status'],error=v['error'])
        for r,v in reports if v['interpretation_for']]
    sources_valid=True;facts_unchanged=True
    for _,saved in reports:
        if not saved['interpretation_for']:continue
        base=h.store.artifact(saved['interpretation_for'])['report']
        facts_unchanged &= ({k:v for k,v in saved['report'].items() if k!='interpretations'}==
            {k:v for k,v in base.items() if k!='interpretations'})
        for interpretation in saved['report']['interpretations']:
            for source in interpretation['sources']:
                try:core.read_evidence(h,source,record_read=False)
                except (ValueError,KeyError,IndexError):sources_valid=False
    sdk_error=None;messages=[];sdk_reopened=False
    try:
        # Native SDK session loader restores the actual durable snapshot; no harness copy.
        from strands.tools.executors import SequentialToolExecutor
        reopened=agent.build_harness(h,transport=httpx.MockTransport(lambda r: (_ for _ in ()).throw(AssertionError('Audit never sends'))),
            api_key='offline-audit',instructions=s['spec']['execution_instructions'],model_class=agent.DeepSeekModel,
            tool_executor=SequentialToolExecutor(),research_tools=[],configuration_path=h.store.root/'audit_framework.json',
            session_directory=h.store.root/'framework_sessions')
        messages=reopened.messages
        anchors=[h.store.artifact(e['outputs'][0]) for e in events if e['kind']=='model_original_turn']
        assert anchors and digest(messages)==anchors[-1]['sdk_message_identity']
        assert not unmatched(messages)
        uses=[b['toolUse'] for m in messages for b in m['content'] if 'toolUse' in b]
        results=[b['toolResult'] for m in messages for b in m['content'] if 'toolResult' in b]
        assert all(f['tool_use'] in uses and any(r['toolUseId']==f['tool_use']['toolUseId']
            and r['status']==f['result']['status'] for r in results) for f in feedback)
        sdk_reopened=True
    except Exception as exc:sdk_error=type(exc).__name__+': '+str(exc)
    counters={k:s.get(k,0) for k in ('mathematical_evaluations','physical_replay_launches','nmpc_launches',
        'offline_nlp','bdf_replays','admitted_training_stages','charged_starts')}
    receipt_checks=[]
    for f in feedback:
        use=f['tool_use'];row=h.store.lookup(run_id,'native-'+use['toolUseId'])
        receipt=json.loads(row['receipt']) if row and row['receipt'] else None
        receipt_checks.append(dict(tool_use_id=use['toolUseId'],name=use['name'],status=f['result']['status'],
            paired=f['result']['toolUseId']==use['toolUseId'],receipt=receipt))
    main_wires=[w for w,r in zip(wires,requests) if r['purpose']=='conversation']
    delivered=False
    if len(main_wires)==2:
        content=main_wires[1]['messages'][0]['content']
        if '\nCURRENT_RESEARCH_PACKET\n' in content:
            packet=json.loads(content.split('\nCURRENT_RESEARCH_PACKET\n')[1].split('\nPROTECTED CLOSEOUT:')[0])
            delivered=any(r['reporter_status']=='available' and r['delivery_mode']=='reporter_interpreted'
                for r in packet['research']['latest_reports'])
    completed=[i for i,e in enumerate(events) if e['kind']=='reporter_completed']
    scope=read(h.store.root/'scope.json')
    unchanged=all(digest(h.store.artifact(r))==r['artifact_id'] for r in scope['imported_results'])
    roles=[r['purpose'] for r in requests]
    result=dict(study_id=run_id,implementation=s['freeze'],mode='real_provider' if run_id==LIVE_ID else 'offline_mock',
        requests=requests,usage=reporter.provider_usage(h),ledger=h.store.remaining(),scientific_counters=counters,
        tool_pairing=receipt_checks,reporter_revisions=interpretations,second_main_received_L1=delivered,
        reporter_sources_resolve=sources_valid,reporter_authoritative_fields_unchanged=facts_unchanged,
        store_independently_reopened=True,sdk_independently_reopened=sdk_reopened,sdk_error=sdk_error,
        original_B_hashes_unchanged=unchanged,unknown_sends=len(agent.pending(h)),
        unconsumed_response=s['pilot'].get('unconsumed_response'),research_status=s['research_status'],
        final_disposition=h.store.artifact(s['final_disposition']) if s.get('final_disposition') else None,
        scope_identity=digest(scope),scientific_admission='pending_semantic_audit',
        sdk_message_identity=digest(messages) if sdk_reopened else None)
    with h.store.connect(True) as db:
        result['unsettled_receipts']=db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]
    result['technical_checks_passed']=bool(roles==['conversation','reporter','conversation'] and delivered
        and completed and completed[-1]<requests[-1]['event_index'] and sdk_reopened and unchanged
        and sources_valid and facts_unchanged
        and receipt_checks and all(r['paired'] and r['receipt'] and r['status']=='success' for r in receipt_checks)
        and not any(counters.values()) and not result['unknown_sends'] and not result['unconsumed_response']
        and not result['unsettled_receipts'])
    result['scientific_admission']=('pending_semantic_audit' if result['technical_checks_passed'] else 'failed') if run_id==LIVE_ID else 'not_admitted_offline_fixture'
    result['f3_started']=False
    atomic_json(h.store.root/'f30_audit.json',result)
    return result


async def run(live=False, *, approved_commit=None):
    h,refs=prepare(live,approved_commit=approved_commit)
    agent.record(h,'f30_validation_started',dict(live=live,no_retry=True))
    error=None
    with ExitStack() as stack:
        stack.enter_context(patch('tools.research.agent.LiveBoundary',CappedBoundary))
        if not live:
            stack.enter_context(patch('httpx.AsyncHTTPTransport',return_value=mock_http(refs)))
            stack.enter_context(patch('tools.research.agent.load_credential'))
            stack.enter_context(patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline-fixture'}))
        try:await agent.converse(h)
        except Exception as exc:
            error=type(exc).__name__+': '+str(exc)
            agent.record(h,'f30_execution_failure',dict(error=error,no_retry=True),status='stopped')
    result=audit(h.run_id);result['execution_error']=error
    atomic_json(h.store.root/'f30_audit.json',result)
    atomic_json(ROOT/'runs'/('f30_revalidation_live.json' if live else 'f30_revalidation_offline.json'),result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--approved-commit',help='Full final SHA separately approved for live revalidation; preparation is not approval')
    parser.add_argument('--audit',metavar='STUDY_ID')
    args=parser.parse_args()
    print(json.dumps(audit(args.audit) if args.audit else asyncio.run(run(args.live,approved_commit=args.approved_commit)),ensure_ascii=False))
