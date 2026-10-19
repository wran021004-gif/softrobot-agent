"""Production Strands harness, accounted provider transport and persisted conversation."""
import asyncio
from copy import deepcopy
import json, os, time
from pathlib import Path
from uuid import uuid4
import httpx
from openai import AsyncOpenAI
from strands.models.openai import OpenAIModel
from strands_harness import create_harness
from tools.platform_store import plain,zero,encode
from tools.state_io import atomic_json,digest,read
from tools.research.state import (state, update, save, guard, enabled, protected,
    closeout_operations, admit_closeout, readable_results)
from tools.research.budget import engineering_closeout
CALLER='research-provider'
class DeepSeekModel(OpenAIModel):
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
                if reasoning:
                    converted[0]['reasoning_content']=reasoning
                converted[0].setdefault('content',None)
            result.extend(converted)
        return result

def pilot(host,db=None):
    return host.store.session(host.run_id,db)['state']['pilot']

def record(host,kind,value,status='recorded'):
    with host.store.transaction() as db:
        ref=host.store.put(db,value)
        host.store.event(db,host.run_id,kind,status,outputs=[ref])
    return plain(ref)

def pending(host):
    with host.store.connect(True) as db:
        return [dict(r) for r in db.execute("SELECT * FROM calls WHERE run_id=? AND caller=? AND status IN ('running','unknown')",(host.run_id,CALLER))]

def received(host,request_id):
    return next((host.store.artifact(e['outputs'][0]) for e in reversed(host.store.events(host.run_id))
        if e['kind']=='r3_response' and e['request_id']==request_id),None)

def settle(host,row,reception):
    status='completed' if 200<=reception['http_status']<300 else 'failed'
    return host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=CALLER,
        tool_id='model.deepseek',tool_version='1.0.0',execution_status=status,charged=zero()),
        reception,elapsed=reception['elapsed_s'],kind='r3_model')

class LiveBoundary(httpx.AsyncBaseTransport):
    """One durable reservation per actual send, including auxiliary summarization.

    No auth headers are persisted. Complete response bytes are saved before JSON
    decoding. An unconsumed confirmed response is replayed only for its exact
    request; uncertainty blocks further sends and retains its reservation.
    """
    def __init__(self,host,transport=None,*,allow_truncated_response=False):
        self.host=host
        self.inner=transport or httpx.AsyncHTTPTransport(retries=0)
        self.last_request=None
        self.allow_truncated_response=allow_truncated_response

    async def handle_async_request(self,request):
        host=self.host
        store=host.store
        run=host.run_id
        wire=json.loads(request.content)
        expected=pilot(host)['provider']
        if (str(request.url)!=expected['base_url'].rstrip('/')+'/chat/completions'
            or wire.get('model')!=expected['model'] or wire.get('thinking')!={'type':expected['thinking']}
            or wire.get('reasoning_effort')!=expected['reasoning_effort'] or wire.get('max_tokens')!=expected['max_tokens']
            or wire.get('stream') is not False or wire.get('tool_choice','auto')!='auto'):
            raise ValueError('R3_PROVIDER_CONFIGURATION_MISMATCH')
        saved=pilot(host).get('unconsumed_response')
        if saved:
            row=store.lookup(run,saved)
            if row['request_hash']!=digest(wire):
                raise ValueError('R3_SAVED_RESPONSE_MUST_BE_PROCESSED_FIRST')
            reception=received(host,saved)
            if not reception:
                raise ValueError('R3_SAVED_RESPONSE_MISSING')
            self.last_request=saved
            record(host,'r3_response_replay',dict(request_id=saved,new_send=False))
            return httpx.Response(reception['http_status'],content=store.artifact(reception['body'],raw=True),request=request)
        if pending(host):
            raise ValueError('R3_UNCONFIRMED_ATTEMPT_BLOCKS_SEND')
        def guard(db):
            if store.remaining(db=db)['remaining']['model_calls']<1:
                raise ValueError('PROVIDER_COUNT_EXHAUSTED')
        with store.transaction() as db:
            raw_request=store.put(db,wire)
        key='r3-request-'+uuid4().hex
        try:
            row,_=store.reserve(run,key,digest(wire),CALLER,{**zero(),'model_calls':1,'wall_s':0.},
                resources=['provider_request'],inputs=[raw_request],kind='r3_model',guard=guard)
        except ValueError as exc:
            record(host,'r3_send_rejected',dict(request=plain(raw_request),sent=False,reason=str(exc)),status='blocked')
            raise
        self.last_request=key
        purpose='conversation' if wire.get('tools') else 'summarization'
        with store.transaction() as db:
            state=store.session(run,db)['state']
            state['pilot']['live_model_requests']+=1
            store.update_state(db,run,state)
            metadata=store.put(db,dict(request=plain(raw_request),purpose=purpose,pid=os.getpid(),
                endpoint=str(request.url),timeout_s=request.extensions.get('timeout'),client_retries=0,transport_retries=0))
            store.event(db,run,'r3_request','sent',request=key,execution=row['execution_id'],outputs=[metadata])
        started=time.monotonic()
        try:
            response=await self.inner.handle_async_request(request)
            body=await response.aread()
            # The first commit contains original bytes, even if metadata decoding fails.
            with store.transaction() as db:
                raw_body=store.put(db,body,media='application/octet-stream')
                reception=dict(body=plain(raw_body),http_status=response.status_code,elapsed_s=time.monotonic()-started,
                    purpose=purpose,pid=os.getpid(),usage=None,finish_reasons=None,money=None,
                    reasoning_tokens=None,usage_source='provider response; missing fields unknown')
                ref=store.put(db,reception)
                state=store.session(run,db)['state']
                if 200<=response.status_code<300:
                    state['pilot']['unconsumed_response']=key
                store.update_state(db,run,state)
                store.event(db,run,'r3_response','received',request=key,execution=row['execution_id'],outputs=[ref])
            try:
                parsed=json.loads(body)
                usage=parsed.get('usage')
                reception.update(usage=usage,finish_reasons=[c.get('finish_reason') for c in parsed.get('choices',[])],
                    reasoning_tokens=(usage or {}).get('completion_tokens_details',{}).get('reasoning_tokens'))
            except (ValueError,AttributeError,TypeError):
                pass
            with store.transaction() as db:
                ref=store.put(db,reception)
                store.event(db,run,'r3_response','metadata_saved',request=key,execution=row['execution_id'],outputs=[ref])
            settle(host,row,reception)
            if 'length' in (reception['finish_reasons'] or []) and not self.allow_truncated_response:
                raise ValueError('R3_LENGTH_TRUNCATED_NO_NATIVE_SUBMISSION')
            return httpx.Response(response.status_code,content=body,request=request)
        except BaseException as exc:
            # Local archive/settlement failures do not erase already saved reception.
            reception=received(host,key)
            if reception:
                settle(host,row,reception)
            else:
                store.mark_unknown(run,key)
            record(host,'r3_boundary_failure',dict(request_id=key,exception_type=type(exc).__name__,
                response_saved=reception is not None),status='stopped')
            raise

    def consumed(self):
        with self.host.store.transaction() as db:
            state=self.host.store.session(self.host.run_id,db)['state']
            if state['pilot'].get('unconsumed_response')==self.last_request:
                state['pilot'].pop('unconsumed_response')
                self.host.store.update_state(db,self.host.run_id,state)
                self.host.store.event(db,self.host.run_id,'r3_response_processing','decoded',request=self.last_request)

    async def aclose(self):
        await self.inner.aclose()

def live_model_class(boundary):
    class AccountedDeepSeekModel(DeepSeekModel):
        async def stream(self,*args,**kwargs):
            async for item in super().stream(*args,**kwargs):
                yield item
            boundary.consumed()  # Failed conversion leaves the saved response available.
    return AccountedDeepSeekModel

def load_credential(path):
    if not os.environ.get('DEEPSEEK_API_KEY') and path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            key,sep,value=line.strip().removeprefix('export ').partition('=')
            if sep and key.strip()=='DEEPSEEK_API_KEY':
                os.environ['DEEPSEEK_API_KEY']=value.strip().strip('"').strip("'")
    if not os.environ.get('DEEPSEEK_API_KEY'):
        raise ValueError('MODEL_KEY_MISSING')

def build_harness(host,*,transport,api_key,instructions,model_class,tool_executor,research_tools,configuration_path,session_directory):
    from strands.experimental.context_manager import Offload
    s=state(host)
    provider=s['pilot']['provider']
    client=AsyncOpenAI(api_key=api_key,base_url=provider['base_url'],max_retries=0,
        timeout=provider['timeout_s'],http_client=httpx.AsyncClient(transport=transport,follow_redirects=False))
    model=model_class(model_id=provider['model'],stream=False,
        context_window_limit=provider['context_guard']['context_limit_tokens'],
        params=dict(max_tokens=provider['max_tokens'],reasoning_effort=provider['reasoning_effort'],
            extra_body=dict(thinking=dict(type=provider['thinking']))),client=client)
    # Public offload stores originals for retrieval; no auxiliary model requests.
    context=dict(strategies=[Offload.truncate('tool_results',{'preview_tokens':1024}).when(threshold=4096)])
    agent=create_harness(model=model,tools=research_tools,instructions=instructions,
        builtin_tools=[],builtin_plugins=[],background_tasks=False,memory=False,skills=False,
        context_manager=context,session=dict(id=s['pilot']['framework_session_id'],dir=str(session_directory)),
        retry_strategy=None,callback_handler=None,caching=False,tool_executor=tool_executor)
    atomic_json(configuration_path,dict(harness='strands-harness==0.2.0',sdk='strands-agents==1.59.0',
        provider=provider,registered_tools=sorted(agent.tool_names),session_id=s['pilot']['framework_session_id'],
        retry_controllers=0,context='public tool-result offload and retrieval',transport='accounted live boundary'))
    return agent

async def wait_training(host):
    """No provider turns or summary snapshots while an owned worker is active."""
    from tools.research.rl import reconcile, dispatch as rl_dispatch
    from tools.rl import run
    while True:
        active=False
        for run_id in state(host).get('rl_runs',{}):
            status=reconcile(host,run_id,lightweight=True)
            active=active or status['worker_alive']
        if not active:
            return
        await asyncio.sleep(2.)

async def converse(host):
    from tools.research.core import guard,dispatch,experience,read_evidence,packet
    from tools.research.contracts import Plan,ExperienceQuery,EvidenceQuery,AnalysisRequest,RLRequest
    if state(host)['spec'].get('mode') == 'engineering_numerical':
        raise ValueError('NUMERICAL_MODE_FORBIDS_APPLICATION_MODEL_ENDPOINTS')
    from strands.tools.tools import PythonAgentTool
    from strands.tools.executors import SequentialToolExecutor
    from strands.hooks.events import BeforeModelCallEvent, BeforeToolCallEvent, AfterToolCallEvent
    def feedback_context_references():
        refs=[]
        for event in host.store.events(host.run_id):
            if event['kind']!='model_original_tool_feedback':
                continue
            value=host.store.artifact(event['outputs'][0])
            use=value['tool_use']
            if use['name'] not in ('research_plan','research_rl','research_analysis') or (use['name']=='research_plan' and use['input'].get('action') in ('stop',None)):
                continue
            if value['result']['status']!='success':
                continue
            refs.extend(use['toolUseId']+'_'+str(i) for i,_ in enumerate(value['result'].get('content',[])))
        return refs
    if (state(host)['spec'].get('mode')=='rl_interface' or state(host)['spec'].get('capabilities')) and not state(host).get('live_started_unix'):
        s=state(host)
        started=time.time()
        pilot=deepcopy(s['pilot'])
        pilot.update(request_deadline_unix=None,bounded_request_reservation=False)
        update(host,live_started_unix=started,pilot=pilot)
    guard(host)
    if pending(host):
        raise ValueError('UNKNOWN_PROVIDER_OUTCOME_RECOVER_BEFORE_SEND')
    load_credential(Path(state(host)['spec']['runtime']['credentials_reference']).expanduser())
    class Boundary(LiveBoundary):
        async def handle_async_request(self,request):
            s=state(host)
            if s['research_status']=='stopped' or s['pending']:
                raise ValueError('SEALED_STOP_OR_PENDING_WORK_BLOCKS_SEND')
            if not s['pilot'].get('unconsumed_response'):
                wire=json.loads(request.content)
                if protected(host):
                    definitions={t['function']['name']:t['function'] for t in wire.get('tools',[])}
                    action=definitions.get('research_plan',{}).get('parameters',{}).get('properties',{}).get('action',{})
                    permitted=closeout_operations(host)
                    if action.get('enum')!=permitted['research_plan'] or set(definitions)-{'research_plan','research_rl','evidence_read','retrieve_context'}:
                        raise ValueError('PROTECTED_SEND_REQUIRES_CLOSEOUT_NATIVE_SCHEMA')
                    rl=definitions.get('research_rl')
                    if rl and rl['parameters']['properties']['operation'].get('enum')!=permitted['research_rl']:
                        raise ValueError('PROTECTED_RL_SEND_REQUIRES_EXISTING_WORK')
                    retrieval=definitions.get('retrieve_context')
                    if retrieval:
                        advertised=retrieval.get('parameters',{}).get('properties',{}).get('reference',{}).get('enum')
                        if advertised is None or not set(advertised)<=set(feedback_context_references()):
                            raise ValueError('PROTECTED_CONTEXT_RETRIEVAL_REQUIRES_EXISTING_FEEDBACK')
            return await super().handle_async_request(request)
    boundary=Boundary(host,allow_truncated_response=True)
    def handler(kind):
        def run(use,**kwargs):
            try:
                if kind=='plan':
                    value=dispatch(host,use['input'],'native-'+use['toolUseId'])
                elif kind=='analysis':
                    from tools.research.analysis import dispatch as analysis_dispatch
                    value=analysis_dispatch(host,use['input'],'native-'+use['toolUseId'],guard=guard)
                elif kind=='rl':
                    from tools.research.rl import dispatch as rl_dispatch
                    value=rl_dispatch(host,use['input'],'native-'+use['toolUseId'])
                else:
                    key='native-'+use['toolUseId']
                    row,fresh=host.store.reserve(host.run_id,key,digest(use['input']),host.actor,{**zero(),'tool_calls':1})
                    if not fresh and row['receipt']:
                        value=host.store.artifact(json.loads(row['receipt'])['output'])
                    else:
                        if kind=='experience':
                            value=experience(host,use['input'])
                        else:
                            value=read_evidence(host,use['input'])
                        host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
                            tool_id='research.core_'+kind,tool_version='1.0.0',execution_status='completed',charged=zero()),value)
                return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text=json.dumps(value))])
            except Exception as exc:
                key='native-'+use['toolUseId']
                reserved=host.store.lookup(host.run_id,key)
                if reserved and not reserved['receipt']:
                    host.store.complete(reserved,dict(request_id=key,execution_id=reserved['execution_id'],caller=host.actor,
                        tool_id='research.core_'+kind,tool_version='1.0.0',execution_status='failed',error=str(exc),charged=zero()),dict(error=str(exc)))
                from tools.research.feedback import facts
                return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(dict(
                    error=type(exc).__name__,message=str(exc),decision_facts=facts(host))))])
        return run
    rl_mode=enabled(state(host)['spec'],'rl')
    formal=bool(state(host)['spec'].get('capabilities'))
    instructions=state(host)['spec']['execution_instructions']
    native=[PythonAgentTool(name,dict(name=name,description=description,inputSchema={'json':schema.model_json_schema()}),handler(kind))
        for name,description,schema,kind in [('research_plan','Propose/search/execute/diagnose; Select an exact publicly read fresh complete passing evaluation and freeze it; zero configured extra repetitions seals immediately. Positive configured confirmations preserve failures and identity. History never satisfies fresh gates; failures/counters persist. STOP seals study.',Plan,'plan'),
            ('experience_retrieve','Read-only case/procedure draft search/read with provenance',ExperienceQuery,'experience'),
            ('evidence_read','Read exact immutable evidence and JSON pointer',EvidenceQuery,'evidence')]]
    if formal or rl_mode:
        actions=['propose','stop','diagnose','select','confirm'] if formal and state(host)['spec'].get('mode')!='rl_interface' else ['propose','stop']
        if formal and state(host)['spec'].get('mode')!='rl_interface':
            actions += [a for a,c in [('execute','nmpc'),('search','search'),('mechanics','mathematics'),('replay','replay')] if enabled(state(host)['spec'],c)]
        actions=state(host)['spec'].get('allowed_plan_actions',actions)
        schema=Plan.model_json_schema()
        schema['properties']['action']={'type':'string','enum':actions}
        native[0].tool_spec={**native[0].tool_spec,'inputSchema':{'json':schema}}
    if state(host)['spec'].get('nominal_source') or state(host)['spec'].get('start_mode')=='family_space':
        native.append(PythonAgentTool('research_analysis',dict(name='research_analysis',description='Candidate-bound mathematics; saved_state or execution plus update_id selects exact projected state at previous applied input with actual remaining task time. Historical candidate binding required. Each calculation charged once; task acceptance unmeasured.',inputSchema={'json':AnalysisRequest.model_json_schema()}),handler('analysis')))
    if rl_mode:
        native.append(PythonAgentTool('research_rl',dict(name='research_rl',description='start initializes; resume recovers original stage; continue creates a new stage from exact parent run_id/checkpoint with supported sparse training/reward changes and additional finite allocation. Query, stop, independently evaluate or diagnose an owned frozen candidate RL run',
            inputSchema={'json':RLRequest.model_json_schema()}),handler('rl')))
    if state(host)['spec'].get('rl_evaluation_source'):
        schema=RLRequest.model_json_schema()
        schema['properties']['operation']['enum']=state(host)['spec']['allowed_rl_operations']
        source=state(host)['spec']['rl_evaluation_source']
        schema['properties']['run_id']['enum']=[source['run_id']]
        schema['properties']['checkpoint']['enum']=[source['checkpoint']]
        native[-1].tool_spec={**native[-1].tool_spec,'inputSchema':{'json':schema}}
    if formal:
        native[1].tool_spec={**native[1].tool_spec,'description':'Unavailable outside scoped milestone evidence'}
    agent=build_harness(host,transport=boundary,api_key=os.environ['DEEPSEEK_API_KEY'],instructions=instructions,
        model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),research_tools=[t for t in native if t is not native[1]] if state(host)['spec'].get('rl_evaluation_source') else native,
        configuration_path=host.store.root/'framework_configuration.json',session_directory=host.store.root/'framework_sessions')
    if state(host)['spec'].get('rl_evaluation_source'):
        agent.tool_registry.registry.pop('retrieve_context',None)
    async def before_model(event):
        s=state(host)
        if s['research_status']=='stopped':
            event.cancel='Accepted native STOP; no additional request'
            return
        if s['pilot'].get('unconsumed_response'):
            saved=s['pilot']['unconsumed_response']
            ev=next(e for e in host.store.events(host.run_id) if e['kind']=='r3_request' and e['request_id']==saved)
            original=host.store.artifact(host.store.artifact(ev['outputs'][0])['request'])
            agent.system_prompt=next(m['content'] for m in original['messages'] if m['role']=='system')
            return
        remaining=host.store.remaining()['remaining']
        if remaining['model_calls']<1 or remaining['tool_calls']<2:
            engineering_closeout(host,'No remaining provider/public-operation capacity for model closeout')
            event.cancel='Engineering count-budget closure; no fabricated model STOP'
            return
        guard(host)
        if rl_mode:
            await wait_training(host)
        s=state(host)
        if s['research_status']=='stopped':
            event.cancel='Study stopped while waiting'
            return
        guard(host)
        current=decision_packet(host)
        record(host,'model_decision_packet',current)
        agent.system_prompt=instructions+'\nCURRENT_RESEARCH_PACKET\n'+json.dumps(current)
        if protected(host):
            permitted=closeout_operations(host)
            schema=Plan.model_json_schema()
            schema['properties']['action']={'enum':permitted['research_plan'],'type':'string'}
            native[0].tool_spec={**native[0].tool_spec,'inputSchema':{'json':schema}}
            agent.tool_registry.registry.pop('experience_retrieve',None)
            agent.tool_registry.registry.pop('research_analysis',None)
            if rl_mode:
                schema=deepcopy(native[-1].tool_spec['inputSchema']['json'])
                schema['properties']['operation']['enum']=permitted['research_rl']
                schema['properties']['run_id']['enum']=list(s.get('rl_runs',{}))
                native[-1].tool_spec={**native[-1].tool_spec,'inputSchema':{'json':schema}}
            schema=EvidenceQuery.model_json_schema()
            schema['$defs']['EvidenceRef']['properties']['artifact_id']['enum']=[r['artifact_id'] for r in readable_results(s,host)]
            native[2].tool_spec={**native[2].tool_spec,'inputSchema':{'json':schema}}
            retrieval=agent.tool_registry.registry.get('retrieve_context')
            if retrieval:
                from strands.tools.tools import normalize_tool_spec
                spec=deepcopy(normalize_tool_spec(retrieval.tool_spec))
                spec['inputSchema']['json']['properties']['reference']['enum']=feedback_context_references()
                retrieval.tool_spec=spec
            agent.system_prompt+='\nPROTECTED CLOSEOUT: status/stop existing workers, pinned published-policy evaluation, explicit evidence reads, selected passing solution confirmations and truthful STOP. No start/resume/solve/exploration.'
    def before_tool(event):
        if state(host)['spec'].get('rl_evaluation_source') and event.tool_use['name'] not in ('research_plan','research_rl','evidence_read'):
            event.cancel_tool='Only declared follow-up evaluation, evidence reads and STOP are permitted.'
        if formal and event.tool_use['name']=='experience_retrieve':
            event.cancel_tool='Use only scoped milestone evidence; unrelated workspace retrieval is unauthorized.'
        record(host,'model_original_tool_request',dict(tool_use=event.tool_use))
        if protected(host) and event.tool_use['name'] not in ('research_plan','research_rl','evidence_read','retrieve_context'):
            event.cancel_tool='Protected closeout permits only existing work, evidence and STOP.'
        try:
            admit_closeout(host,event.tool_use['name'],event.tool_use['input'])
        except ValueError as exc:
            event.cancel_tool=str(exc)
        if state(host)['research_status']=='stopped':
            event.cancel_tool='Accepted STOP seals further workflow work.'
        if protected(host) and event.tool_use['name']=='retrieve_context' and event.tool_use['input'].get('reference') not in feedback_context_references():
            event.cancel_tool='Protected closeout permits existing execution feedback only.'
    def after_tool(event):
        record(host,'model_original_tool_feedback',dict(tool_use=event.tool_use,result=event.result))
        key='native-'+event.tool_use['toolUseId']
        if host.store.lookup(host.run_id,key) is None:
            row,_=host.store.reserve(host.run_id,key,digest(event.tool_use),host.actor,{**zero(),'tool_calls':1})
            host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
                tool_id=event.tool_use['name'],tool_version='1.0.0',execution_status='completed',charged=zero()),event.result)
    agent.hooks.add_callback(BeforeModelCallEvent,before_model)
    agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
    agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    try:
        while state(host)['research_status']!='stopped':
            if host.store.remaining()['remaining']['model_calls']<1:
                engineering_closeout(host,'Provider request count exhausted without model STOP/selection')
                break
            result=await agent.invoke_async('Use actual saved evidence, choose your next research action or STOP, then consume feedback and decide freely.')
            record(host,'model_original_turn',dict(result=str(result)))
            if state(host)['pending'] or pending(host):
                raise ValueError('PENDING_OUTCOME_REQUIRES_LOCAL_RECOVERY')
    finally:
        await boundary.aclose()


def decision_packet(host):
    from tools.research.core import packet
    if state(host)['spec'].get('research_decisions'):
        from tools.research.research_context import context
        from extensions.tendon_family.family_space import decision_summary
        s=state(host);spec=s['spec']
        return dict(research=context(host),implementation=s['freeze'],study_id=host.run_id,
            candidates=[r for r in s['candidates'].values() if host.store.artifact(r)['profile_identity']==s['profile']['identity']],family_space=decision_summary(spec['family_space'],s['family_space_reference'],
                dict(actions=spec['allowed_plan_actions'],capabilities=spec['capabilities'])),analysis_protocol=spec['analysis_protocol'],
            guidance='Use exact evidence refs and a typed decision in every research_plan. Source references contain complete trajectory; evidence_read is available. New designs need explicit control adaptation. Do not infer global feasibility/infeasibility. Stop at first complete pass; publicly read and select it. STOP must cite every new result.')
    result=packet(host)
    spec=result.pop('specification')
    result['configuration_identity']=spec['resolved_identity']
    result['study']={k:spec[k] for k in ('study_id','capabilities','allowed_parameters','reference_parameters','analysis_protocol','scoring_window_s','budgets','rl_limits','confirmation','budget_semantics')}
    if 'topology_authorization' in spec:
        result['study']['topology_authorization']=spec['topology_authorization']
    if spec.get('fidelity_policy'):
        result['study'].update(fidelity_policy=spec['fidelity_policy'],final_evaluation_identity=spec['final_evaluation_identity'],
            family_search=spec.get('family_search'),search_contract='family_mixed_search_v1',
            search_usage='research_plan(action=search): select groups, counts, objective, screening_fidelity and finite caps; no fixed robot. Mathematical evidence cannot satisfy final task acceptance.')
    if spec.get('start_mode')=='family_space':
        from extensions.tendon_family.family_space import decision_summary
        result['study'].update(start_mode='family_space',family_space=decision_summary(
            spec['family_space'],state(host)['family_space_reference'],
            dict(actions=spec['allowed_plan_actions'],capabilities=spec['capabilities'])),
            family_space_identity=spec['family_space_identity'],candidate_initialization=spec['candidate_initialization'],
            canonical_task_identity=spec['canonical_task_identity'])
    result['available_actions']=spec['allowed_plan_actions']
    s=state(host)
    result['implementation']=dict(commit=s['freeze'],repairs=s.get('core_repairs',[]),
        counters_preserved=True,prelaunch_failure_rule='A recorded failure before durable launch intent proves no worker started; its charged attempt remains spent. An explicit implementation repair is not a retry of already-executed unchanged science.')
    return result
