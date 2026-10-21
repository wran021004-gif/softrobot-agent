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


async def run(authorization=None,*,offline=False):
    from strands.hooks import BeforeModelCallEvent,BeforeToolCallEvent,AfterToolCallEvent
    from strands.tools.executors import SequentialToolExecutor
    from strands.tools.tools import PythonAgentTool
    scope=read(OUT/'scope.json');raw=read(SPEC)
    if digest(raw)!=scope['spec_identity']:raise ValueError('FROZEN_B_SPEC_CHANGED')
    if not offline:
        approval=read(authorization) if authorization else {}
        if (approval.get('stage')!='S12.7.4B' or approval.get('scope_identity')!=digest(scope)
            or approval.get('request_ceiling')!=6 or not approval.get('user_approval')):
            raise ValueError('INDEPENDENT_S127_4B_TRANSFER_AUTHORIZATION_REQUIRED')
    else:
        from uuid import uuid4
        raw['study_id']='s127-4b-fixture-'+uuid4().hex[:8]
        # Keep dependencies adjacent through absolute references in the fixture leaf.
        for k in ('defaults','family_space','control','task'):
            raw[k]=str((SPEC.parent/raw[k]).resolve())
        fixture=SPEC.parent/'._s127_4_sdk_fixture.json';atomic_json(fixture,raw)
    from tools.platform_host import Host
    study=raw['study_id'];directory=ROOT/'runs/research'/study
    if (directory/'store.sqlite3').exists() or directory.exists():raise ValueError('EXISTING_B_GRANT_NO_AUTOMATIC_RESEND')
    try:h=core.prepare(fixture if offline else SPEC)
    finally:
        if offline:fixture.unlink()
    core.bind(h)
    if not offline:
        with h.store.transaction() as db:
            # Keep the exact separately approved transfer identity in the existing Store.
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
    boundary=LiveBoundary(h,httpx.MockTransport(synthetic) if offline else None)
    def execute(use,**kwargs):
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
            return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(dict(error=str(exc))))])
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
            if any(r['phase']==phase and r['name']=='research_plan' and r['action']!='stop' for r in completed):
                event.cancel_tool='One scientific action per invocation; consume its feedback and conclude.'
        def after_tool(event):record(h,'model_original_tool_feedback',dict(tool_use=event.tool_use,result=event.result))
        agent.hooks.add_callback(BeforeModelCallEvent,before);agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
        agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    async def invoke(agent):
        attach(agent)
        await agent.invoke_async('Inspect the authoritative current state, choose one useful legal action or STOP, consume its feedback, then conclude this invocation.')
        record(h,'model_original_turn',dict(session_id=agent._session_manager.session_id,sdk_message_identity=digest(agent.messages)))
        await agent._session_manager.save_snapshot(agent,is_latest=True)
    result=dict(stage='S12.7.4B',mode='synthetic_protocol_fixture' if offline else 'live',study_id=study,
        offline_protocol_passed=False,live_sdk_continuation_passed=False,live_scientific_action_passed=False,
        production_recovery_validated=False,production_handoff_admitted=False)
    try:
        old=build();await invoke(old)
        old_messages=deepcopy(old.messages);ledger=deepcopy(h.store.remaining());science=deepcopy(state(h)['candidates'])
        result['old_complete_tool_round']=bool(completed) and not unmatched(old.messages) and old.messages[-1]['role']=='assistant'
        if not result['old_complete_tool_round'] or state(h)['research_status']=='stopped':
            result['reason']='Old invocation did not establish a complete continuing tool boundary';return result
        ref,new=await handoff(h,old,build,directory/'sdk')
        assert old.messages==old_messages and h.store.remaining()==ledger and state(h)['candidates']==science
        assert not any('toolUse' in b or 'toolResult' in b for m in new.messages for b in m['content'])
        result.update(handoff_reference=ref,snapshot_independently_reopened=True,ledger_at_handoff=ledger,
            snapshot_file_count=len(snapshot_files(directory/'sdk',new._session_manager.session_id)))
        phase='new';await invoke(new)
        restored=await validate_snapshot(h,ref,build,directory/'sdk')
        assert restored.messages==new.messages and not unmatched(new.messages)
        assert all(state(h)['candidates'].get(k)==v for k,v in science.items())
        assert not pending(h) and state(h)['pending'] is None and not state(h)['pilot'].get('unconsumed_response')
        with h.store.connect(True) as db:assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0
        actions=[]
        for row in completed:
            if row['phase']!='new' or row['name']!='research_plan':continue
            value=h.store.artifact(row['value'])['result']
            actual=(row['action']=='generate' and value.get('status')=='generated'
                or row['action']=='initialize_control' and bool(value.get('source'))
                or row['action']=='physical_replay' and bool(value.get('reference'))
                and h.store.artifact(value['reference']).get('status')=='evaluated')
            if actual:actions.append(row)
        result.update(offline_protocol_passed=offline,live_sdk_continuation_passed=not offline,
            live_scientific_action_passed=bool(actions) and not offline,real_tool_actions=completed,
            old_sdk_history_unchanged=True,cumulative_budget_continuous=True,no_unsettled_calls=True)
        return result
    finally:
        result.update(ledger=h.store.remaining(),new_provider_requests=0 if offline else state(h)['pilot']['live_model_requests'],
            synthetic_http_requests=fixture_requests if offline else 0,physics=state(h).get('physical_replay_launches',0))
        atomic_json(OUT/('offline.json' if offline else 'live.json'),result)
        await boundary.aclose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--offline',action='store_true');parser.add_argument('--authorization',type=Path)
    args=parser.parse_args()
    if args.prepare:print(json.dumps(prepare()))
    elif args.offline or args.authorization:print(json.dumps(asyncio.run(run(args.authorization,offline=args.offline))))
    else:parser.error('Choose --prepare, --offline or --authorization')
