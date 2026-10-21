"""Bounded F2 engineering check using the original Store, SDK and handoff path.

Explicit --live sends real requests under the user's F2 grant. No science workers.
Each invocation creates a new grant; a failed live run is never automatically retried.
"""
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
from uuid import uuid4
import httpx
from tools.research import core, reporter
from tools.research.agent import (LiveBoundary, build_harness, live_model_class,
    load_credential, record, decision_packet, pending, plan_schema)
from tools.research.config import ROOT
from tools.research.contracts import AnalysisRequest
from tools.research.session_handoff import handoff, reconcile, unmatched
from tools.research.state import state, update, save
from tools.platform_store import plain, zero
from tools.state_io import read, atomic_json, digest


def prepare(live):
    raw=read(ROOT/'configs/research/study_s125_cold.json')
    raw.update(study_id='s129-f2-'+('live-' if live else 'offline-')+uuid4().hex[:10],
        tool_readiness=None,capabilities=['analysis'],allowed_plan_actions=['diagnose','stop'],
        authorization='User F2 engineering grant: <=7 main + <=3 Reporter real requests; saved B evidence only; no physical/NMPC/RL workers.')
    raw['budgets'].update(provider_requests=10,protected_provider_requests=0,public_operations=20,
        protected_public_operations=0,physical_launches=0,mathematical_evaluations=1,offline_nlp=0,bdf_replays=0)
    raw['nmpc_limits']['executions']=0
    raw['rl_limits'].update(training_stages=0,evaluation_episodes=0)
    raw['execution_instructions']='F2 engineering validation only. Use saved mathematical evidence; no scientific execution. '
    raw['execution_instructions']+='After one requested tool, consume its feedback and answer concisely. Numerical replay is not optimality or physical acceptance.'
    for k in ('defaults','family_space','control','task'):raw[k]=str((ROOT/'configs/research'/raw[k]).resolve())
    path=ROOT/'configs/research'/('._'+raw['study_id']+'.json');atomic_json(path,raw)
    try:h=core.prepare(path)
    finally:path.unlink()
    if live:core.bind(h)
    else:update(h,freeze='offline_F2_engineering_fixture')
    pair=read(ROOT/'evidence/s129_math_capability/gvs_pair.json')
    for value in pair['supporting_artifacts'].values():save(h,value,'saved_B_engineering_artifact')
    refs=[save(h,pair[k],'saved_B_engineering_result') for k in ('baseline','changed')]
    update(h,analysis_results=refs)
    for ref in refs:reporter._save(h,reporter.assemble(h,[ref]),status='deterministic_only')
    record(h,'f2_engineering_scope',dict(live=live,main_ceiling=7,reporter_ceiling=3,
        imported_results=refs,new_scientific_executions=0,production_admission=False,
        candidate_handoff_authorized_only_for_this_engineering_study=True))
    p=deepcopy(state(h)['pilot']);p['session_handoff_live_admitted']=True;update(h,pilot=p)
    return h,refs


async def run(live=False):
    from strands.hooks import BeforeModelCallEvent, BeforeToolCallEvent, AfterToolCallEvent
    from strands.tools.tools import PythonAgentTool
    from strands.tools.executors import SequentialToolExecutor
    if live:load_credential(Path(read(ROOT/'configs/research/runtime.json')['credentials_reference']).expanduser())
    h,refs=prepare(live);sessions=[];checkpoints=[];calls=[];original=[digest(h.store.artifact(r)) for r in refs]
    class CappedTransport(httpx.AsyncBaseTransport):
        def __init__(self):self.inner=httpx.AsyncHTTPTransport(retries=0)
        async def handle_async_request(self,request):
            wire=json.loads(request.content);role='conversation' if wire.get('tools') else 'reporter'
            if calls.count(role)>=(7 if role=='conversation' else 3):raise ValueError('F2_ROLE_CAP_NO_SEND')
            calls.append(role)
            if live:return await self.inner.handle_async_request(request)
            from tests.research.test_s129_agent_reporting import reporter_response
            from tests.research.test_s127_session_recovery import response
            if role=='reporter':return reporter_response(request)
            if calls.count(role)==1:
                return httpx.Response(200,json=dict(id='fixture',object='chat.completion',created=1,model=wire['model'],
                    choices=[dict(index=0,finish_reason='tool_calls',message=dict(role='assistant',content=None,
                        reasoning_content='Synthetic engineering fixture',tool_calls=[dict(id='f2-original-investigation',
                            type='function',function=dict(name='research_investigate',arguments=json.dumps(dict(
                                question='Is the structure comparison certified?',references=refs))))]))],
                    usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12)))
            return response(request)
        async def aclose(self):await self.inner.aclose()
    transport=CappedTransport();boundary=LiveBoundary(h,transport)
    def execute(use,**kwargs):
        key='native-'+use['toolUseId']
        if use['name']=='research_plan':value=core.dispatch(h,use['input'],key)
        else:
            row,fresh=h.store.reserve(h.run_id,key,digest(use['input']),h.actor,{**zero(),'tool_calls':1})
            if not fresh:raise ValueError('ORIGINAL_RECEIPT_RECOVERY_REQUIRED')
            value=reporter.investigate(h,use['input'])
            h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=h.actor,
                tool_id='research.core_investigate',tool_version='1.0.0',execution_status='completed',charged=zero()),value)
        return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text=json.dumps(value))])
    tools=[PythonAgentTool(name,dict(name=name,description=description,inputSchema={'json':schema}),execute)
        for name,description,schema in (
            ('research_investigate','Read-only investigation of saved engineering evidence',reporter.InvestigationRequest.model_json_schema()),
            ('research_plan','Record a diagnostic hypothesis using saved evidence; no worker',plan_schema(['diagnose'],decision_required=True)))]
    def build(session_id=None):
        agent=build_harness(h,transport=boundary,api_key=os.environ.get('DEEPSEEK_API_KEY','offline'),
            instructions=state(h)['spec']['execution_instructions'],model_class=live_model_class(boundary),
            tool_executor=SequentialToolExecutor(),research_tools=tools,configuration_path=h.store.root/'framework.json',
            session_directory=h.store.root/'sdk',session_id=session_id)
        agent.tool_registry.registry.pop('retrieve_context',None)
        def cap(event):
            if calls.count('conversation')>=7:event.cancel='F2 main request ceiling reached; no send'
        agent.hooks.add_callback(BeforeModelCallEvent,cap)
        return agent
    result=dict(mode='live' if live else 'offline_mock_usage',study_id=h.run_id,store=str(h.store.root),
        passed=False,production_handoff_admitted=False,analysis_schema_has_task_capability=
            'task_capability' in AnalysisRequest.model_json_schema()['properties']['operation']['enum'])
    try:
        agent=build()
        prompts=[
            'Call research_investigate once to compare the three signed G values and ask whether replay establishes optimality. References: '+json.dumps(refs),
            'Read the handoff packet. Call research_plan action=diagnose once to record hypothesis H-F2: solver convergence versus local-model limits remains unresolved. Use the original result references as supporting_evidence; decision={hypothesis_id:H-F2,research_intent:DIAGNOSE,selected_method:saved evidence,claimed_inference:empirical_search}; fill the required hypothesis/expected_observation/weakening_observation/fixed_conditions/stopping_condition/interpretation fields. Consume feedback then conclude.',
            'Use the handoff packet and previous intent. Without tools, state the three signed scores, convergence, replay scope, H-F2, and what remains unproved.']
        for i,prompt in enumerate(prompts):
            sessions.append(agent._session_manager.session_id)
            agent.hooks.add_callback(BeforeToolCallEvent,lambda event:record(h,'model_original_tool_request',dict(tool_use=event.tool_use)))
            agent.hooks.add_callback(AfterToolCallEvent,lambda event:record(h,'model_original_tool_feedback',dict(tool_use=event.tool_use,result=event.result)))
            if i==0:prompt+='\n'+json.dumps(decision_packet(h))
            await agent.invoke_async(prompt)
            record(h,'model_original_turn',dict(session_id=sessions[-1],sdk_message_identity=digest(agent.messages)))
            await agent._session_manager.save_snapshot(agent,is_latest=True)
            assert not unmatched(agent.messages) and not pending(h) and not state(h)['pilot'].get('unconsumed_response')
            await reporter.complete_reports(h,transport)
            if i<2:
                ledger=h.store.remaining();ref,agent=await handoff(h,agent,build,h.store.root/'sdk')
                assert h.store.remaining()==ledger
                checkpoints.append(ref)
        reopened=await reconcile(h,build,h.store.root/'sdk')
        assert reopened.messages==agent.messages and original==[digest(h.store.artifact(r)) for r in refs]
        assert not pending(h) and not state(h)['pilot'].get('unconsumed_response')
        from tools.platform_host import Host
        reopened_store=Host(h.store.root,h.run_id,actor=h.actor)
        assert reopened_store.store.remaining()==h.store.remaining()
        assert reporter.provider_usage(h).get('reporter',{}).get('requests',0)>0
        result.update(passed=True,sdk_reopened=True,store_reopened=True,scientific_artifacts_unchanged=True)
    except Exception as exc:result['error']=type(exc).__name__+': '+str(exc)
    finally:
        result.update(sessions=sessions,handoffs=checkpoints,usage=reporter.provider_usage(h),ledger=h.store.remaining(),
            unsettled=pending(h),unconsumed=state(h)['pilot'].get('unconsumed_response'),new_scientific_executions=0,
            reporter_statuses=[s['interpretation_status'] for _,s in reporter.entries(h)])
        atomic_json(h.store.root/'f2_check.json',result)
        atomic_json(ROOT/'runs'/('s129_f2_live.json' if live else 's129_f2_offline.json'),result)
        await boundary.aclose()
    print(json.dumps(result,ensure_ascii=False));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true')
    args=parser.parse_args();asyncio.run(run(args.live))
