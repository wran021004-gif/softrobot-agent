"""Offline assembled-Harness pilot. There is deliberately no live execution mode."""
import argparse
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import time
from uuid import uuid4
from unittest.mock import patch

import httpx
from openai import AsyncOpenAI
from strands import tool
from strands.models.openai import OpenAIModel
from strands_harness import create_harness
from strands.experimental.context_manager import Offload

from tools.platform_store import Store, plain, zero, encode
from tools.platform_host import Host
from tools.platform_registry import registry, dependency_closure
from tools.research_investigations import InvestigationDispatcher, InvestigationReturn
from tools.state_io import digest, read, atomic_json

ROOT=Path(__file__).resolve().parents[1]
SAVED=ROOT/'evidence/research_mainline3_v1_handoff_20261009'
TARGET='fixed-C-offline-report'
SOURCE_IDS=['6314170dd823eab26d13296eb5afee1cfe24cb2f5117334414d1d66e8d266892',
    '400226bfd9f0d75d698037f494987054f3030fce7813612c11f6f4d4e5d6ab13',
    '5582561d4de48e4450f5619024d2a92296a6f7ed12c77c470cd8d573aa588627']


class DeepSeekPilotModel(OpenAIModel):
    """Public provider extension: retain DeepSeek reasoning on the next request.

    Stock OpenAIModel 1.59.0 receives reasoning but drops it when formatting
    subsequent chat-completion requests. Strands still owns the only history.
    """
    @classmethod
    def format_request_messages(cls,messages,system_prompt=None,**kwargs):
        result=super().format_request_messages([],system_prompt,**kwargs)
        for message in messages:
            # Let the public provider converter own content/tool/ID conversion.
            clean={**message,'content':[b for b in message['content'] if 'reasoningContent' not in b]}
            converted=super().format_request_messages([clean],None)
            reasoning=''.join(b['reasoningContent'].get('reasoningText',{}).get('text','')
                for b in message['content'] if 'reasoningContent' in b)
            if message['role']=='assistant' and converted:
                if reasoning:converted[0]['reasoning_content']=reasoning
                converted[0].setdefault('content',None)
            result.extend(converted)
        return result


def initialize(directory,activity,model_budget=32,*,authorization=None,started_unix=None):
    """Import exact saved artifacts into a new read/decision-only business session.

    Robot setup is frozen data, not recompiled or granted for execution. Only
    pure business-service dependencies are active on this imported session.
    """
    directory=Path(directory).resolve()
    if not directory.is_relative_to(ROOT/'runs'):raise ValueError('PILOT_DIRECTORY_MUST_BE_UNDER_WORKTREE_RUNS')
    if not activity.startswith('strands-pilot-'):raise ValueError('PILOT_ACTIVITY_NAMESPACE_REQUIRED')
    if directory.exists():raise ValueError('PILOT_ALREADY_EXISTS_USE_RESUME')
    bundle=read(SAVED/'fixed_bundle.json')
    cfg=deepcopy(bundle['snapshot']['input']);cfg['run_id']=activity
    began=time.time() if started_unix is None else started_unix
    live=authorization is not None
    duration=21600. if live else 3600.
    budget={**zero(),'model_calls':40 if live else model_budget,'tool_calls':512 if live else 128,'wall_s':duration}
    cfg['policy'].update(budget=budget,allowed_tools=['research.investigation_read','research.investigation_disposition'],
        tool_bindings={'research.investigation_read':'1.0.0','research.investigation_disposition':'1.0.0'},
        operation_allowances={},timeout_s=5.)
    store=Store(directory/'business')
    store.create(dict(project_id=activity,grant_id=activity,authorization_source=authorization or 'R0-R2 offline pilot; fixtures only',
        budget=budget,exclusive_resources={'provider_request':1} if live else {}))
    reg=registry()
    snap=dict(input=cfg,input_identity=digest(cfg),initial=bundle['snapshot']['initial'],
        instance_identity=bundle['snapshot']['instance_identity'],
        dependencies=dependency_closure([reg.get('research.investigation_read','1.0.0'),
            reg.get('research.investigation_disposition','1.0.0')],reg),
        import_scope='saved robot data; pure evidence and formal-decision services only')
    store.create_session(snap)
    with store.transaction() as db:
        refs=[]
        for identity in SOURCE_IDS:
            value=bundle['artifacts'][identity];ref=plain(store.put(db,value))
            if ref['artifact_id']!=identity:raise ValueError('SAVED_SOURCE_IDENTITY_MISMATCH')
            refs.append(ref)
        # An explicit fixture report, not a new model or robot experiment.
        evaluation=bundle['artifacts'][SOURCE_IDS[0]]
        report=plain(InvestigationReturn(facts=[dict(statement='Saved official reach error',reference=refs[0],
            pointer='/metrics/0/value',value=evaluation['metrics'][0]['value'])],
            interpretation='Extraction-only report from the saved fixed-C evaluation; no new experiment or scientific interpretation.' if live else 'Offline fixture report extracted from the original fixed-C evaluation.',
            unknowns=['Physical cause and live model compatibility are unassessed.']))
        report_ref=plain(store.put(db,report))
        long_ref=None if live else plain(store.put(db,[dict(identity='controlled-long-original',index=i,value=0.0268176708469683,
            units='m/s',padding='Controlled offload fixture material. '*8) for i in range(64)]))
        directory_ref=plain(store.put(db,dict(sources=refs,report=report_ref,**({} if live else dict(long_material=long_ref)),
            target=TARGET,meaning='Saved fixed-C source identities; new principal judgment, no new robot experiment' if live else 'Saved fixed-C source identities; new offline disposition namespace')))
        state=store.session(activity,db)['state']
        state.update(role_context=dict(role='principal',investigation_grant=dict(evidence=[*refs,report_ref,directory_ref]+([long_ref] if long_ref else []),
            include_completed_reports=True,deadline_unix=began+duration)),
            historical_investigations={TARGET:dict(status='completed',result=report_ref,kind='extraction_only_report' if live else 'explicit_fixture_report',
                source_bindings=refs,new_investigation_executed=False)},
            pilot=dict(activity_id=activity,started_unix=began,deadline_unix=began+duration,
                provider=deepcopy(bundle['snapshot']['input']['policy']['model']),directory=directory_ref,
                sources=refs,report=report_ref,long_material=long_ref,fixture_requests=0,fixture_tokens=0,
                live_model_requests=0,mathematical_solves=0,robot_backend_executions=0))
        if live:state['pilot'].update(mode='live-r3',request_deadline_unix=began+duration-1800.,phase='prepared')
        store.update_state(db,activity,state,'running')
    host=Host(store.root,activity,actor='strands-pilot')
    host.folder.mkdir(parents=True,exist_ok=True)
    return host


class FixtureBoundary:
    """HTTP-boundary fixtures, raw archives, and the existing budget authority."""
    def __init__(self,host,responses,crash_before_request=False):
        self.host=host;self.responses=iter(responses);self.crash_before_request=crash_before_request;self.calls=0
        self.stop_after=len(responses)

    def __call__(self,request):
        store=self.host.store;run=self.host.run_id
        if self.crash_before_request and self.calls>=self.stop_after:
            # The prior evidence message has already been saved by Strands.
            os._exit(73)
        self.calls+=1
        wire=json.loads(request.content)
        state=store.session(run)['state']
        if time.time()>=state['pilot']['deadline_unix']:raise ValueError('PILOT_DEADLINE_EXPIRED')
        request_id='fixture-request-'+uuid4().hex
        with store.transaction() as db:raw_request=store.put(db,wire)
        purpose='summarization' if not wire.get('tools') else 'conversation'
        try:
            row,_=store.reserve(run,request_id,digest(wire),'fixture-provider',
                {**zero(),'model_calls':1,'wall_s':5.},inputs=[raw_request],kind='fixture_model')
        except ValueError:
            with store.transaction() as db:
                blocked=store.put(db,dict(purpose=purpose,request=plain(raw_request),sent=False))
                store.event(db,run,'fixture_budget','rejected',outputs=[blocked])
            raise
        with store.transaction() as db:
            state=store.session(run,db)['state'];state['pilot']['fixture_requests']+=1
            store.update_state(db,run,state)
            store.event(db,run,'fixture_request','sent',request=request_id,execution=row['execution_id'],outputs=[raw_request])
        response=next(self.responses)
        if response=='unresolved':
            store.mark_unknown(run,request_id)
            raise httpx.ReadTimeout('Controlled sent request without confirmed response',request=request)
        if response=='kill-unresolved':os._exit(75)
        with store.transaction() as db:
            raw_response=store.put(db,response)
            state=store.session(run,db)['state']
            state['pilot']['fixture_tokens']+=response.get('usage',{}).get('total_tokens',0)
            store.update_state(db,run,state)
            store.event(db,run,'fixture_response','received',request=request_id,execution=row['execution_id'],outputs=[raw_response])
        store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller='fixture-provider',
            tool_id='model.fixture',execution_status='completed',charged=zero()),
            dict(simulated=True,usage=response.get('usage'),real_provider_usage=None,real_cost=None),kind='fixture_model')
        return httpx.Response(200,json=response,request=request)


def build_harness(host,responses=None,*,context_test=False,crash_after_submit=False,crash_before_request=False,
        transport=None,api_key=None,context_config=None,instructions=None,model_class=DeepSeekPilotModel,tool_executor=None,
        decision_contract=None,research_tools=None,configuration_path=None,session_directory=None):
    state=host.store.session(host.run_id)['state'];provider=state['pilot']['provider']
    dispatcher=InvestigationDispatcher(host)

    def invoke_read(reference,pointer='',offset=0,limit=16,byte_limit=4096,tool_version='1.0.0'):
        receipt=host.invoke(dict(request_id='pilot-read-'+uuid4().hex,tool_id='research.investigation_read',
            tool_version=tool_version,arguments=dict(reference=reference,pointer=pointer,offset=offset,limit=limit,byte_limit=byte_limit),
            reason='Native pilot evidence access'))
        return dict(receipt=receipt,page=host.store.artifact(receipt['output']) if receipt.get('output') else None)

    @tool
    def discover_evidence(offset:int=0,limit:int=4)->dict:
        """Discover saved source identities and the formal target with paginated original reads."""
        return invoke_read(state['pilot']['directory'],offset=offset,limit=limit)

    @tool
    def read_original(reference:dict,pointer:str='',offset:int=0,limit:int=16,byte_limit:int=4096,tool_version:str='1.0.0')->dict:
        """Read the original referenced evidence at a JSON pointer, with explicit pagination and version."""
        return invoke_read(reference,pointer,offset,limit,byte_limit,tool_version)

    @tool
    def submit_result(decision:(decision_contract or dict),revision:int)->dict:
        """Submit a principal decision through the existing validator. A revision key is stable across delivery IDs."""
        try:receipt=dispatcher.submit_disposition(decision,revision)
        except (ValueError,TypeError) as exc:return dict(error=str(exc),issue=getattr(exc,'issue',None))
        if crash_after_submit:os._exit(74)
        return receipt

    @tool
    def get_receipt(investigation_id:str,revision:int)->dict:
        """Retrieve the committed formal receipt by target and revision, after a restart or lost tool return."""
        return dict(receipt=dispatcher.disposition_receipt(investigation_id,revision))

    client=AsyncOpenAI(api_key=api_key or 'offline-fixture-no-credential',base_url=provider['base_url'],max_retries=0,
        timeout=provider['timeout_s'],http_client=httpx.AsyncClient(transport=transport or httpx.MockTransport(
            FixtureBoundary(host,responses,crash_before_request=crash_before_request)),follow_redirects=False))
    model=model_class(model_id=provider['model'],stream=False,
        context_window_limit=provider['context_guard']['context_limit_tokens'],
        params=dict(max_tokens=provider['max_tokens'],reasoning_effort=provider['reasoning_effort'],
            extra_body=dict(thinking=dict(type=provider['thinking']))),
        client=client)
    context='auto'
    if context_test:
        # Public built-in strategies, not another compressor or capacity estimator.
        context=dict(strategies=[Offload.truncate('tool_results',{'preview_tokens':32}).when(threshold=150),
            Offload.summarize('user_text',{'model':model}).when(threshold=250,preserve_recent=1)])
    if context_config is not None:context=context_config(model)
    agent=create_harness(model=model,tools=research_tools if research_tools is not None else [discover_evidence,read_original,submit_result,get_receipt],
        instructions=instructions or 'Inspect the saved evidence, submit your formal principal decision using the native tool, and recover its receipt. This activity permits evidence and decisions only.',
        builtin_tools=[],builtin_plugins=[],background_tasks=False,memory=False,skills=False,
        context_manager=context,session=dict(id=state['pilot'].get('framework_session_id',host.run_id),dir=str(session_directory or host.store.root.parent/'sessions')),
        retry_strategy=None,callback_handler=None,caching=False,tool_executor=tool_executor)
    atomic_json(configuration_path or host.store.root.parent/'configuration.json',dict(harness='strands-harness==0.2.0',sdk='strands-agents==1.59.0',
        provider=provider,registered_tools=sorted(agent.tool_names),session_id=state['pilot'].get('framework_session_id',host.run_id),
        disabled=['shell','read','write','edit','web_fetch','web_search','programmatic_tool_caller','subagent',
            'background_tasks','memory','skills','todos','environment'],retry_controllers=0,
        context='public R3 strategies' if context_config else 'public test strategies' if context_test else 'auto',
        transport='accounted live boundary' if transport else 'httpx.MockTransport; fixtures only'))
    return agent


def completion(name=None,args=None,text=None,call_id='call-pilot'):
    message=dict(role='assistant',content=text,reasoning_content='Controlled reasoning preserved across native tool turns.')
    if name:message['tool_calls']=[dict(id=call_id,type='function',function=dict(name=name,arguments=json.dumps(args)))]
    return dict(id='fixture-completion',object='chat.completion',created=1,model='deepseek-flash',
        choices=[dict(index=0,finish_reason='tool_calls' if name else 'stop',message=message)],
        usage=dict(prompt_tokens=100,completion_tokens=20,total_tokens=120))


def fixture_decision(host):
    """Controlled scientific judgment belongs in the fixture, not task instructions."""
    pilot=host.store.session(host.run_id)['state']['pilot'];ref=pilot['sources'][0]
    value=host.store.artifact(ref)
    fact=dict(statement='Saved official reach error',reference=ref,pointer='/metrics/0/value',value=value['metrics'][0]['value'])
    scope=dict(statement='Original source execution',reference=ref,pointer='/source_execution_id',value=value['source_execution_id'])
    return dict(investigation_id=TARGET,report=pilot['report'],disposition='accept',
        adopted_claims=[dict(statement='Retain the exact saved official reach result within its original execution.',
            supporting_facts=[fact],scope=[scope],support_explanation='Exact saved metric and bound original execution; this does not imply joint success.')],
        remaining_unknowns=['Live-model compatibility and physical causal explanations unassessed.'],reason='Offline fixture partial adoption only.')


def normal_responses(host,correction=False,reads=True):
    pilot=host.store.session(host.run_id)['state']['pilot'];decision=fixture_decision(host)
    responses=[]
    if reads:
        responses.extend([completion('discover_evidence',dict(offset=0,limit=2),'Inspect source discovery','discover-1'),
            completion('discover_evidence',dict(offset=2,limit=3),call_id='discover-2'),
            completion('read_original',dict(reference=pilot['sources'][0],pointer='/metrics/0'),call_id='metric-read'),
            completion('read_original',dict(reference=pilot['sources'][0],pointer='/source_execution_id',limit=64),call_id='scope-read'),
            completion('read_original',dict(reference=pilot['sources'][1],pointer='/detail/sampled_settling'),call_id='holding-original'),
            completion('read_original',dict(reference=pilot['sources'][2],pointer='/detail/components'),call_id='joint-original')])
    if correction:
        invalid=deepcopy(decision);invalid['adopted_claims'][0]['supporting_facts'][0]['value']=0.5
        responses.append(completion('submit_result',dict(decision=invalid,revision=1),call_id='invalid-submit'))
    responses.extend([completion('submit_result',dict(decision=decision,revision=1),call_id='valid-submit'),
        completion('get_receipt',dict(investigation_id=TARGET,revision=1),call_id='receipt-read'),
        completion(text='Offline decision complete; saved physical limitations remain.')])
    return responses


def reopen(directory,activity):
    host=Host(Path(directory)/'business',activity,actor='strands-pilot')
    # A process death at the sent boundary leaves the original reservation.
    with host.store.connect(True) as db:
        pending=[r['request_id'] for r in db.execute("SELECT request_id FROM calls WHERE run_id=? AND caller='fixture-provider' AND status='running'",(activity,))]
    for key in pending:host.store.mark_unknown(activity,key)
    return host


FORBIDDEN_BOUNDARIES=(
    'httpx.AsyncHTTPTransport.handle_async_request','httpx.HTTPTransport.handle_request',
    'tools.platform_host.Host.run','tools.platform_host.Host.context',
    'tools.platform_models.run_loop','tools.platform_models.payload_for','tools.platform_models.input_for',
    'tools.platform_models.DeepSeekAdapter._transport',
    'tools.research_investigations.InvestigationDispatcher._interact',
    'tools.research_investigations.InvestigationDispatcher._append_correction',
    'tools.research_investigations.InvestigationDispatcher.engineering_recovery',
    'tools.context_assembly.compact_investigation_request',
    'tools.platform_tools.simulate','tools.research_mainline3.fixed_pipeline',
    'tools.research_execution.linearize_configuration',
    'extensions.optimization.ipopt.IpoptSolver.solve',
    'extensions.tendon_family.backends.MujocoBackend.solve',
    'scipy.optimize.minimize','scipy.optimize.least_squares','scipy.integrate.solve_ivp')


@contextmanager
def offline_scope():
    """Fail closed at old-runtime, network and scientific execution boundaries."""
    with ExitStack() as stack:
        counters={name:0 for name in FORBIDDEN_BOUNDARIES}
        for name in counters:
            def prohibited(*args,_name=name,**kwargs):
                counters[_name]+=1
                raise AssertionError('OFFLINE_SCOPE_BOUNDARY_INVOKED: '+_name)
            stack.enter_context(patch(name,side_effect=prohibited))
        yield counters


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','resume','scenarios'])
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--activity',default='strands-pilot-offline')
    parser.add_argument('--fault',choices=['read','submit','unresolved'])
    parser.add_argument('--scenario',choices=list('ABCDEFG'))
    args=parser.parse_args()
    if args.action=='scenarios':
        from tests.test_strands_pilot import run_scenarios
        result=run_scenarios(args.directory,args.scenario)
        print(encode(dict(assessment=result['assessment'],scenarios=sorted(result['scenarios']),
            evidence=str(args.directory/'results.json'))));return
    host=initialize(args.directory,args.activity,1 if args.fault=='unresolved' else 32) if args.action=='start' else reopen(args.directory,args.activity)
    responses=normal_responses(host,reads=args.action=='start')
    if args.fault=='read':responses=responses[:6]
    if args.fault=='unresolved':responses=['kill-unresolved']
    agent=build_harness(host,responses,crash_after_submit=args.fault=='submit',crash_before_request=args.fault=='read')
    prompt='Continue the saved-evidence principal review and retrieve the formal receipt.'
    if args.fault=='unresolved':prompt+=' Controlled long context material.'*2000
    agent(prompt)
    if InvestigationDispatcher(host).disposition_receipt(TARGET,1) is None:
        raise ValueError('NO_FORMAL_SUBMISSION_RECEIPT')
    print(encode(dict(activity=host.run_id,receipt=InvestigationDispatcher(host).disposition_receipt(TARGET,1),
        budget=host.store.remaining(),counts=host.store.session(host.run_id)['state']['pilot'])))


if __name__=='__main__':
    with offline_scope():main()
