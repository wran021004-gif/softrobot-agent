"""Isolated real Harness continuation driver; synthetic mode is protocol evidence only."""
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import httpx
from tools.platform_store import plain,zero
from tools.research import core
from tools.research.agent import build_harness,LiveBoundary,live_model_class,load_credential,record,pending,plan_schema,decision_packet
from tools.research.config import ROOT
from tools.research.contracts import EvidenceQuery
from tools.research.session_handoff import handoff,validate_snapshot,unmatched,snapshot_files
from tools.research.state import state,update
from tools.state_io import read,atomic_json,digest

SPEC=ROOT/'configs/research/study_s127_4_handoff.json'
OUT=ROOT/'evidence/s127_4_handoff'


def prepare():
    raw=read(ROOT/'configs/research/study_s125_cold.json')
    raw.update(study_id='s127-4b-sdk-20261021',tool_readiness=None,
        evidence_destination='runs/s127_4_handoff_export',
        authorization='S12.7.4B independent preparation only; live Provider transfer requires a separate exact-scope approval. No historical budget.',
        capabilities=['control_correction','physical_replay'],
        allowed_plan_actions=['generate','initialize_control','physical_replay','stop'])
    raw['budgets'].update(provider_requests=6,protected_provider_requests=0,public_operations=40,protected_public_operations=2,
        physical_launches=2,mathematical_evaluations=0,offline_nlp=0,bdf_replays=0)
    raw['nmpc_limits']['executions']=0
    raw['rl_limits'].update(training_stages=0,training_actions=1,actions_per_trial=1,evaluation_episodes=0)
    raw['execution_instructions']+='\nISOLATED S12.7.4B SDK RECOVERY VALIDATION, not a Cold-start efficacy study. Choose freely among declared legal tools or STOP. In each invocation perform at most one scientific action (or evidence reads), then consume its real feedback and return a short conclusion without another tool. Prefer a low-cost structure generation or baseline control initialization where scientifically useful. No mathematics, NMPC or PPO is available. At most two small fixed-input physical launches are shared across both sessions; unused capacity is never spent merely to exhaust it.'
    runtime=read(ROOT/'configs/research/runtime.json');runtime['provider']['max_tokens']=8192
    runtime_path=ROOT/'runs/s127_4_handoff_runtime.json';atomic_json(runtime_path,runtime)
    raw['runtime']=str(runtime_path)
    if SPEC.exists() and read(SPEC)!=raw:raise ValueError('FROZEN_B_SPEC_CHANGED')
    atomic_json(SPEC,raw)
    scope=dict(stage='S12.7.4B',spec_identity=digest(raw),endpoint=runtime['provider']['base_url'],
        model=runtime['provider']['model'],max_output_tokens=8192,request_ceiling=6,automatic_retries=0,
        new_physical_ceiling=2,mathematics=0,nmpc=0,ppo=0,
        scientific_actions=raw['allowed_plan_actions'],new_session_scientific_action_ceiling=1,
        transfer_scope='New isolated Study task/domain, generated candidates and explicit controls, own receipts/results/budgets, research_plan and evidence_read schemas. Old SDK invocation history including complete reasoning and tool IDs goes back only within that old invocation; new session starts with authoritative handoff packet and no copied old tool history. No S12.6 records, unrelated files or credential contents.',
        publication_scope='Code and derived statistics/hashes only. Complete raw requests/responses/reasoning, Store and SDK snapshots stay under ignored runs/.',
        status='not_run',independent_authorization_required=True)
    atomic_json(OUT/'scope.json',scope)
    return scope


def admit_read_only_resume(h,scope,approval):
    """Only a completed read-only old SDK prefix may continue this same grant."""
    s=state(h)
    if (s['research_status']=='stopped' or s['pending'] or pending(h) or s['pilot'].get('unconsumed_response')
        or s['pilot'].get('handoff') or s['pilot'].get('handoff_preparation') or s['candidates'] or s['control_initializations']):
        raise ValueError('READ_ONLY_RESUME_REQUIRES_CLEAN_OLD_SESSION_WITHOUT_SCIENCE')
    if (h.store.remaining()['limit']['model_calls']!=scope['request_ceiling']
        or h.store.remaining()['remaining']['model_calls']<2
        or s['pilot']['provider']['max_tokens']!=scope['max_output_tokens']):
        raise ValueError('ORIGINAL_RESUME_BUDGET_OR_OUTPUT_CONFIGURATION_MISMATCH')
    approvals=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='s127_4b_authorization']
    if approval not in approvals:raise ValueError('ORIGINAL_STORED_AUTHORIZATION_REQUIRED')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:raise ValueError('UNSETTLED_RECEIPT_BLOCKS_READ_ONLY_RESUME')
    core.guard(h)
    return dict(state_identity=digest(s),ledger=h.store.remaining())


async def run(authorization=None,*,offline=False,spec_path=SPEC,out=OUT,stage='S12.7.4B',resume=False):
    from strands.hooks import BeforeModelCallEvent,BeforeToolCallEvent,AfterToolCallEvent
    from strands.tools.executors import SequentialToolExecutor
    from strands.tools.tools import PythonAgentTool
    scope=read(out/'scope.json');raw=read(spec_path)
    if digest(raw)!=scope['spec_identity']:raise ValueError('FROZEN_B_SPEC_CHANGED')
    if scope.get('runtime_identity') and digest(read((spec_path.parent/raw['runtime']).resolve()))!=scope['runtime_identity']:
        raise ValueError('FROZEN_B_RUNTIME_CHANGED')
    if not offline:
        approval=read(authorization) if authorization else {}
        if (approval.get('stage')!=stage or approval.get('scope_identity')!=digest(scope)
            or approval.get('request_ceiling')!=scope['request_ceiling'] or not approval.get('user_approval')):
            raise ValueError('INDEPENDENT_'+stage.replace('.','_')+'_TRANSFER_AUTHORIZATION_REQUIRED')
    else:
        from uuid import uuid4
        raw['study_id']='s127-4b-fixture-'+uuid4().hex[:8]
        # Keep dependencies adjacent through absolute references in the fixture leaf.
        for k in ('defaults','family_space','control','task'):
            raw[k]=str((spec_path.parent/raw[k]).resolve())
        fixture=spec_path.parent/'._s127_4_sdk_fixture.json';atomic_json(fixture,raw)
    from tools.platform_host import Host
    study=raw['study_id'];directory=ROOT/'runs/research'/study
    if resume:
        if offline:raise ValueError('READ_ONLY_RESUME_REQUIRES_ORIGINAL_LIVE_GRANT')
        h=Host(directory,study,actor='unified-research')
        prefix=admit_read_only_resume(h,scope,approval)
    else:
        if (directory/'store.sqlite3').exists() or directory.exists():raise ValueError('EXISTING_B_GRANT_NO_AUTOMATIC_RESEND')
        try:h=core.prepare(fixture if offline else spec_path)
        finally:
            if offline:fixture.unlink()
        core.bind(h)
    if not offline:
        with h.store.transaction() as db:
            # Keep the exact separately approved transfer identity in the existing Store.
            if not resume:
                ref=h.store.put(db,approval);h.store.event(db,h.run_id,'s127_4b_authorization','approved',outputs=[ref])
        load_credential(Path(state(h)['spec']['runtime']['credentials_reference']).expanduser())
    phase='old';completed=[];fixture_requests=0
    def synthetic(request):
        nonlocal fixture_requests
        from tests.research.s7_study import engineering_plan
        fixture_requests+=1;calls=[]
        if fixture_requests in (1,3):
            if fixture_requests==1:
                plan=engineering_plan('generate','DESIGN_MODIFICATION',generation=dict(version='serial_family_generation_v2',
                    family_space_identity=state(h)['spec']['family_space_identity'],segment_count=2,tendon_count=4,spans=[]))
            else:
                candidate=list(state(h)['candidates'].values())[-1]
                plan=engineering_plan('initialize_control','CONTROL_SEARCH',candidate,control_seed=dict(candidate=candidate,method='baseline'))
            calls=[dict(id='fixture-tool-'+str(fixture_requests),type='function',function=dict(name='research_plan',arguments=json.dumps(plan)))]
        return httpx.Response(200,json=dict(id='synthetic-'+str(fixture_requests),object='chat.completion',created=1,model=scope['model'],
            choices=[dict(index=0,finish_reason='tool_calls' if calls else 'stop',message=dict(role='assistant',content=None if calls else 'Consumed fixture feedback.',
                reasoning_content='Explicit synthetic fixture, never live scientific reasoning.',**({'tool_calls':calls} if calls else {})))],
            usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12)))
    class ScopedBoundary(LiveBoundary):
        async def handle_async_request(self,request):
            wire=json.loads(request.content)
            if set(t['function']['name'] for t in wire.get('tools',[]))-{'research_plan','evidence_read'}:
                raise ValueError('UNSCOPED_B_TOOL_SCHEMA')
            secret=os.environ.get('DEEPSEEK_API_KEY')
            if secret and secret.encode() in request.content:raise ValueError('CREDENTIAL_IN_REQUEST_BODY')
            if b'credentials_reference' in request.content:raise ValueError('PRIVATE_RUNTIME_IN_REQUEST_BODY')
            return await super().handle_async_request(request)
    boundary=ScopedBoundary(h,httpx.MockTransport(synthetic) if offline else None)
    def execute(use,**kwargs):
        before=deepcopy(state(h))
        try:
            if use['name']=='research_plan':value=core.dispatch(h,use['input'],'native-'+use['toolUseId'])
            else:
                key='native-'+use['toolUseId'];row,fresh=h.store.reserve(h.run_id,key,digest(use['input']),h.actor,{**zero(),'tool_calls':1})
                value=core.read_evidence(h,use['input']) if fresh else h.store.artifact(json.loads(row['receipt'])['output'])
                if fresh:h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=h.actor,
                    tool_id='research.core_evidence',tool_version='1.0.0',execution_status='completed',charged=zero()),value)
            completed.append(dict(phase=phase,name=use['name'],action=use['input'].get('action'),id=use['toolUseId'],value=record(h,'s127_4b_tool_output',value)))
            return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text=json.dumps(value,separators=(',',':')))])
        except (ValueError,KeyError,TypeError) as exc:
            key='native-'+use['toolUseId'];reserved=h.store.lookup(h.run_id,key)
            if reserved and not reserved['receipt']:
                h.store.complete(reserved,dict(request_id=key,execution_id=reserved['execution_id'],caller=h.actor,
                    tool_id=use['name'],tool_version='1.0.0',execution_status='failed',charged=zero()),dict(error=str(exc)))
            from tools.research.agent import error_feedback
            return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(error_feedback(h,use,exc,before)))])
    tools=[PythonAgentTool(name,dict(name=name,description=description,inputSchema={'json':schema}),execute)
        for name,description,schema in [('research_plan','Execute one legal bounded scientific Plan or STOP',plan_schema(raw['allowed_plan_actions'],decision_required=True)),
            ('evidence_read','Read own exact immutable evidence',EvidenceQuery.model_json_schema())]]
    def build(session_id=None):
        agent=build_harness(h,transport=boundary,api_key='offline-fixture' if offline else os.environ['DEEPSEEK_API_KEY'],
            instructions=state(h)['spec']['execution_instructions'],model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),
            research_tools=tools,configuration_path=directory/'framework_configuration.json',session_directory=directory/'sdk',session_id=session_id)
        agent.tool_registry.registry.pop('retrieve_context',None)
        return agent
    def attach(agent):
        def before(event):
            if len(pending(h)) or state(h).get('pending'):raise ValueError('UNSETTLED_OUTCOME')
            if h.store.remaining()['remaining']['model_calls']<1 or state(h)['research_status']=='stopped':
                event.cancel='No further request permitted';return
            packet=decision_packet(h)
            agent.system_prompt=state(h)['spec']['execution_instructions']+'\nCURRENT_RESEARCH_PACKET\n'+json.dumps(packet,separators=(',',':'))
        def before_tool(event):
            record(h,'model_original_tool_request',dict(tool_use=event.tool_use))
            if (event.tool_use['name']=='research_plan' and event.tool_use['input'].get('action')!='stop'
                and any(r['phase']==phase and r['name']=='research_plan' and r['action']!='stop' for r in completed)):
                event.cancel_tool='One scientific action per invocation; consume its feedback and conclude.'
        def after_tool(event):
            record(h,'model_original_tool_feedback',dict(tool_use=event.tool_use,result=event.result))
            key='native-'+event.tool_use['toolUseId']
            if h.store.lookup(h.run_id,key) is None:
                row,_=h.store.reserve(h.run_id,key,digest(event.tool_use),h.actor,{**zero(),'tool_calls':1})
                h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=h.actor,
                    tool_id=event.tool_use['name'],tool_version='1.0.0',execution_status='completed',charged=zero()),event.result)
        agent.hooks.add_callback(BeforeModelCallEvent,before);agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
        agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    attached=set()
    async def invoke(agent):
        if id(agent) not in attached:attach(agent);attached.add(id(agent))
        await agent.invoke_async('Inspect the authoritative current state, choose one useful legal action or STOP, consume its feedback, then conclude this invocation.')
        record(h,'model_original_turn',dict(session_id=agent._session_manager.session_id,sdk_message_identity=digest(agent.messages)))
        await agent._session_manager.save_snapshot(agent,is_latest=True)
    result=dict(stage=stage,mode='synthetic_protocol_fixture' if offline else 'live',study_id=study,
        offline_protocol_passed=False,live_sdk_continuation_passed=False,live_scientific_action_passed=False,
        production_recovery_validated=False,production_handoff_admitted=False)
    def scientific_actions(which):
        actions=[]
        for row in completed:
            if row['phase']!=which or row['name']!='research_plan':continue
            value=h.store.artifact(row['value'])['result']
            if (row['action']=='generate' and value.get('status')=='generated'
                or row['action']=='initialize_control' and bool(value.get('source'))
                or row['action']=='physical_replay' and bool(value.get('reference'))
                and h.store.artifact(value['reference']).get('status')=='evaluated'):actions.append(row)
        return actions
    try:
        old=build()
        if resume:
            turns=[h.store.artifact(e['outputs'][0]) for e in h.store.events(h.run_id) if e['kind']=='model_original_turn']
            if (not turns or turns[-1]['sdk_message_identity']!=digest(old.messages) or unmatched(old.messages)
                or not old.messages or old.messages[-1]['role']!='assistant'
                or turns[-1]['session_id']!=old._session_manager.session_id):
                raise ValueError('ORIGINAL_COMPLETED_SDK_PREFIX_REQUIRED')
            record(h,'s127_6b_read_only_continuation',dict(**prefix,original_sdk_message_identity=digest(old.messages),
                new_invocation=True,original_requests_resent=False,budget_reset=False,
                driver_source_identity=digest(Path(__file__).read_text(encoding='utf8'))))
        await invoke(old)
        while (not scientific_actions('old') and not any(r['name']=='research_plan' for r in completed)
            and state(h)['research_status']!='stopped' and h.store.remaining()['remaining']['model_calls']>=4):
            await invoke(old)
        old_messages=deepcopy(old.messages);ledger=deepcopy(h.store.remaining());science=deepcopy(state(h)['candidates'])
        result['old_complete_tool_round']=bool(scientific_actions('old')) and not unmatched(old.messages) and old.messages[-1]['role']=='assistant'
        result['live_old_tool_round_passed']=not offline and result['old_complete_tool_round']
        if not result['old_complete_tool_round'] or state(h)['research_status']=='stopped':
            result['reason']='Old invocation did not establish a complete continuing tool boundary';return result
        ref,new=await handoff(h,old,build,directory/'sdk')
        assert old.messages==old_messages and h.store.remaining()==ledger and state(h)['candidates']==science
        assert not any('toolUse' in b or 'toolResult' in b for m in new.messages for b in m['content'])
        result.update(handoff_reference=ref,snapshot_independently_reopened=True,ledger_at_handoff=ledger,
            snapshot_file_count=len(snapshot_files(directory/'sdk',new._session_manager.session_id)))
        before_new_requests=state(h)['pilot']['live_model_requests']
        phase='new';await invoke(new)
        while (not scientific_actions('new') and not any(r['phase']=='new' and r['name']=='research_plan' for r in completed)
            and state(h)['research_status']!='stopped' and h.store.remaining()['remaining']['model_calls']>=2):
            await invoke(new)
        restored=await validate_snapshot(h,ref,build,directory/'sdk')
        assert restored.messages==new.messages and not unmatched(new.messages)
        assert all(state(h)['candidates'].get(k)==v for k,v in science.items())
        assert not pending(h) and state(h)['pending'] is None and not state(h)['pilot'].get('unconsumed_response')
        with h.store.connect(True) as db:assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0
        actions=scientific_actions('new')
        new_requests=state(h)['pilot']['live_model_requests']-before_new_requests
        continued=new_requests>0 and new.messages[-1]['role']=='assistant'
        assert len(actions)<=1
        result.update(offline_protocol_passed=offline and continued,live_sdk_continuation_passed=not offline and continued,
            live_scientific_action_passed=bool(actions) and not offline and continued,new_session_requests=new_requests,real_tool_actions=completed,
            old_sdk_history_unchanged=True,cumulative_budget_continuous=True,no_unsettled_calls=True)
        return result
    except Exception as exc:
        result.update(status='blocked',error_type=type(exc).__name__,reason=str(exc),
            provider_diagnostic=getattr(exc,'diagnostic',None))
        raise
    finally:
        result.update(ledger=h.store.remaining(),new_provider_requests=0 if offline else state(h)['pilot']['live_model_requests'],
            synthetic_http_requests=fixture_requests if offline else 0,physics=state(h).get('physical_replay_launches',0))
        atomic_json(out/('offline.json' if offline else 'live.json'),result)
        await boundary.aclose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--offline',action='store_true');parser.add_argument('--authorization',type=Path)
    args=parser.parse_args()
    if args.prepare:print(json.dumps(prepare()))
    elif args.offline or args.authorization:print(json.dumps(asyncio.run(run(args.authorization,offline=args.offline))))
    else:parser.error('Choose --prepare, --offline or --authorization')
