"""Accounted model transport and exact response recovery over the existing Store."""
from copy import deepcopy
import json, os, time
from pathlib import Path
from uuid import uuid4
import httpx
from strands.models.openai import OpenAIModel
from openai import AsyncOpenAI
from tools.platform_store import plain, zero
from tools.state_io import digest
CALLER = 'research-provider'


def provider_schema(schema):
    """Equivalent object schema without provider-forbidden root compositions.

    A true conditional applies the original conjunction/disjunction unchanged.
    Definitions stay at the root, so absolute JSON references keep their meaning.
    Canonical Pydantic and focused-schema validation still run at the Host.
    """
    result=deepcopy(schema)
    constraints={k:result.pop(k) for k in ('allOf','anyOf','oneOf','not') if k in result}
    if constraints:
        constraints.update({k:result.pop(k) for k in ('if','then','else') if k in result})
        result.update({'if':{},'then':constraints})
    return result


def model_type(provider):
    return DeepSeekModel if provider['adapter']=='deepseek' else OpenAIModel


def model_messages(host, messages, system_prompt=None):
    wire=model_type(pilot(host)['provider']).format_request_messages(messages,system_prompt)
    return gateway_history(host,wire) if pilot(host)['provider']['adapter']=='chatgpt_gateway' else wire


def gateway_history(host, messages):
    """Reattach opaque completed output from original receipts by tool call IDs."""
    wanted={tuple(c['id'] for c in m.get('tool_calls',[])):m for m in messages if m.get('tool_calls')}
    if not wanted:return messages
    for event in host.store.events(host.run_id):
        if event['kind']!='r3_response' or event['status']!='metadata_saved':continue
        reception=host.store.artifact(event['outputs'][0])
        if reception['http_status']!=200:continue
        raw=json.loads(host.store.artifact(reception['body'],raw=True))
        for choice in raw.get('choices',[]):
            original=choice.get('message',{})
            key=tuple(c['id'] for c in original.get('tool_calls',[]))
            if key in wanted and original.get('provider_output') is not None:
                # The SDK parses/re-serializes arguments (including whitespace).
                # Original calls and opaque output must share the same bytes.
                wanted[key].update(tool_calls=deepcopy(original['tool_calls']),
                    provider_output=deepcopy(original['provider_output']))
    return messages


def request_settings(provider):
    """One wire contract for Main, Reporter, validation and offline probes."""
    adapter=provider['adapter']
    if adapter not in ('deepseek','chatgpt_gateway','openai_api'):
        raise ValueError('UNSUPPORTED_RESEARCH_PROVIDER')
    result=dict(model=provider['model'],stream=False)
    if adapter=='openai_api':result['store']=False
    reasoning=provider.get('reasoning')
    if reasoning is not None:
        if reasoning not in ('none','medium'):raise ValueError('REASONING_MUST_BE_NONE_OR_MEDIUM')
        if adapter=='deepseek':
            # DeepSeek has no medium wire value. Its enabled/high profile is
            # explicitly the Provider-specific mapping, not an OpenAI enum.
            result.update(thinking=dict(type='disabled' if reasoning=='none' else 'enabled'),
                reasoning_effort='none' if reasoning=='none' else 'high')
        else:
            result['reasoning_effort']=reasoning
    elif adapter=='deepseek':
        result.update(thinking=dict(type=provider['thinking']),reasoning_effort=provider['reasoning_effort'])
    else:
        raise ValueError(('OPENAI_API' if adapter=='openai_api' else 'GATEWAY')+'_REQUIRES_EXPLICIT_REASONING_PROFILE')
    if provider.get('max_tokens') is not None:
        if adapter=='chatgpt_gateway':raise ValueError('GATEWAY_OUTPUT_CAP_UNSUPPORTED')
        result['max_completion_tokens' if adapter=='openai_api' else 'max_tokens']=provider['max_tokens']
    return result


def build_model(provider, *, api_key, transport, model_class):
    settings=validate_provider(provider)
    params={k:v for k,v in settings.items() if k not in ('model','stream','thinking')}
    if 'thinking' in settings:params['extra_body']=dict(thinking=settings['thinking'])
    client=AsyncOpenAI(api_key=api_key,base_url=provider['base_url'],max_retries=0,
        timeout=provider['timeout_s'],http_client=httpx.AsyncClient(transport=transport,follow_redirects=False))
    return model_class(model_id=provider['model'],stream=False,
        context_window_limit=provider['context_guard']['context_limit_tokens'],params=params,client=client)


def validate_provider(provider):
    settings=request_settings(provider)
    if provider['adapter']=='chatgpt_gateway':
        caps=provider.get('model_capabilities') or {}
        if not provider.get('model') or caps.get('model')!=provider['model'] or not caps.get('tools') or not caps.get('catalog_source'):
            raise ValueError('EXPLICIT_ACCOUNT_MODEL_AND_TOOL_CAPABILITIES_REQUIRED')
        if caps.get('verification') not in ('offline_contract','account_verified'):
            raise ValueError('MODEL_CAPABILITY_VERIFICATION_REQUIRED')
        if provider['reasoning'] not in caps.get('reasoning',[]):
            raise ValueError('MODEL_REASONING_NOT_VERIFIED')
        if not provider.get('context_guard') or not caps.get('max_request_bytes'):
            raise ValueError('EXPLICIT_GATEWAY_CAPACITY_REQUIRED')
    return settings


def credential(provider, path):
    """Secrets stay outside frozen configuration, Store and framework snapshots."""
    if provider['adapter']=='deepseek':
        load_credential(Path(path).expanduser())
        return os.environ['DEEPSEEK_API_KEY']
    config=json.loads(Path(path).expanduser().read_text(encoding='utf-8-sig'))
    prefix='OPENAI_API' if provider['adapter']=='openai_api' else 'GATEWAY'
    configured=config['base_url'].rstrip('/')
    target=provider['base_url'].rstrip('/')
    if target not in (configured,configured+'/v1'):
        raise ValueError(prefix+'_CREDENTIAL_ENDPOINT_MISMATCH')
    if config.get('model') and provider.get('model') and config['model']!=provider['model']:
        raise ValueError(prefix+'_CREDENTIAL_MODEL_MISMATCH')
    key=config['api_key']
    if provider['adapter']=='openai_api' and not key.strip():
        raise ValueError('OPENAI_API_KEY_MISSING_FILL_LOCAL_CREDENTIAL_FILE')
    return key


async def discover_models(provider, api_key, *, transport=None):
    """Explicit caller operation; never invoked by config resolution or prepare.

    Catalog availability does not verify tool support or establish price order.
    """
    async with httpx.AsyncClient(transport=transport,proxy=provider.get('proxy_url') if transport is None else None,
            follow_redirects=False,timeout=provider['timeout_s']) as client:
        response=await client.get(provider['base_url'].rstrip('/')+'/models',headers={'Authorization':'Bearer '+api_key})
        response.raise_for_status()
        return dict(models=response.json()['data'],pricing='unknown',tool_support='requires_separate_verification')

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
        tool_id='model.'+pilot(host)['provider']['adapter'],tool_version='1.0.0',execution_status=status,charged=zero()),
        reception,elapsed=reception['elapsed_s'],kind='r3_model')


def abandon_unrecoverable_reporter_attempt(host,request_id,*,authorization):
    """Explicit operator-only local disposition. Never recover output or retry a send."""
    from tools.research.state import state
    from tools.research.session_handoff import session_storage_path,unmatched
    from tools.research.reporter import current_reports
    if (authorization.get('approved') is not True
            or authorization.get('scope')!='abandon_unrecoverable_reporter_attempt_v1'
            or authorization.get('study_id')!=host.run_id
            or authorization.get('request_id')!=request_id
            or not authorization.get('source_sha256') or not authorization.get('reason')):
        raise ValueError('EXACT_USER_AUTHORIZATION_REQUIRED')
    events=host.store.events(host.run_id)
    prior=[e for e in events if e['kind']=='reporter_attempt_abandoned_locally' and e['request_id']==request_id]
    if prior:
        saved=host.store.artifact(prior[0]['outputs'][0])
        if saved['authorization']!=authorization:raise ValueError('ABANDONMENT_AUTHORIZATION_MISMATCH')
        return saved
    sends=[e for e in events if e['kind']=='r3_request' and e['request_id']==request_id]
    row=host.store.lookup(host.run_id,request_id)
    if len(sends)!=1 or not row or row['caller']!=CALLER or row['status']!='unknown' or row['receipt']:
        raise ValueError('ONE_UNKNOWN_PROVIDER_ATTEMPT_REQUIRED')
    send=sends[0];meta=host.store.artifact(send['outputs'][0]);wire=host.store.artifact(meta['request'])
    if (meta.get('purpose')!='reporter' or wire.get('tools') or wire.get('functions')
            or not wire['messages'][0]['content'].startswith('You are a read-only scientific Reporter.')):
        raise ValueError('ONLY_READONLY_REPORTER_ATTEMPTS_CAN_BE_ABANDONED')
    if received(host,request_id) is not None:raise ValueError('SAVED_RESPONSE_MUST_USE_ORIGINAL_RECOVERY')
    payload=json.loads(wire['messages'][-1]['content']);base=payload['report_reference']
    saved_base=host.store.artifact(base)
    attempts=[e for e in events if e['kind']=='reporter_attempt' and e['sequence']<send['sequence']]
    if (not attempts or host.store.artifact(attempts[-1]['outputs'][0])['base_report']!=base['artifact_id']
            or saved_base['interpretation_for'] or saved_base['report']['interpretations']):
        raise ValueError('ORIGINAL_DETERMINISTIC_REPORT_REQUIRED')
    current=next(((r,v) for r,v in current_reports(host) if (v['interpretation_for'] or r)==base),None)
    if not current or current[1]['interpretation_status'] not in ('deferred','unavailable'):
        raise ValueError('UNAVAILABLE_REPORTER_INTERPRETATION_REQUIRED')
    before=state(host)
    if before.get('pending') or before['pilot'].get('unconsumed_response'):
        raise ValueError('PAIRED_SETTLED_MAIN_FEEDBACK_REQUIRED')
    known=[r for key in ('analysis_results','results','physical_replays','mechanics_results','rl_evaluations','joint_results','matched_state_results','control_search_results') for r in before.get(key,[])]
    if any(card['identity']['result']['reference'] not in known for card in saved_base['report']['results']):
        raise ValueError('SEALED_REGISTERED_SCIENTIFIC_RESULTS_REQUIRED')
    for folder in ('analyses','physical_replay','mechanics','local_diagnostics'):
        for path in (host.store.root/folder).glob('*/boundary.json'):
            if not json.loads(path.read_text(encoding='utf-8')).get('termination_confirmed'):
                raise ValueError('UNSEALED_SCIENTIFIC_WORKER_BLOCKS_ABANDONMENT')
    if any(v.get('active_reservation') or v.get('status',{}).get('worker_alive',False) for v in before.get('rl_runs',{}).values()):
        raise ValueError('UNSEALED_SCIENTIFIC_WORKER_BLOCKS_ABANDONMENT')
    session=before['pilot']['framework_session_id']
    snapshot=Path(session_storage_path(host.store.root/'framework_sessions'))/'session'/session/'scopes/agent/default/snapshots/snapshot_latest.json'
    snapshot_body=snapshot.read_bytes();messages=json.loads(snapshot_body)['data']['messages']
    anchors=[(e,host.store.artifact(e['outputs'][0])) for e in events if e['kind']=='science_delivery_boundary' and e['sequence']<send['sequence']]
    anchor=anchors[-1][1] if anchors else {}
    if (not anchors or anchor.get('session_id')!=session or not anchor.get('paired')
            or not anchor.get('receipts_settled') or anchor['sdk_message_identity']!=digest(messages)
            or unmatched(messages)):
        raise ValueError('ORIGINAL_PAIRED_SDK_SNAPSHOT_REQUIRED')
    if any(e['kind']=='r3_request' and e['sequence']>anchors[-1][0]['sequence']
            and host.store.artifact(e['outputs'][0]).get('purpose')!='reporter' for e in events):
        raise ValueError('NO_MAIN_SEND_AFTER_TRUSTED_FEEDBACK_REQUIRED')
    if any(e['kind']=='r3_request' and e['sequence']>send['sequence'] for e in events):
        raise ValueError('UNKNOWN_ATTEMPT_MUST_BE_LAST_SEND')
    used=host.store.remaining()['used']['model_calls']
    if (used!=before['pilot']['live_model_requests'] or used!=authorization.get('expected_provider_requests')
            or json.loads(row['charged'])['model_calls']!=1 or json.loads(row['reserved'])['model_calls']!=1):
        raise ValueError('ORIGINAL_PROVIDER_CHARGE_MUST_BE_PRESERVED')
    disposition=dict(version='local_reporter_attempt_abandonment_v1',study_id=host.run_id,request_id=request_id,
        original_send=sends[0]['outputs'][0],original_wire=meta['request'],base_report=base,
        provider_outcome='unknown',response_saved=False,reporter_interpretation='unavailable',
        scientific_results_preserved=True,upstream_cancelled=False,new_send=False,
        tokens=None,money=None,provider_elapsed_s=None,provider_requests_charged=1,
        local_execution_status='cancelled',authorization=authorization,sdk_message_identity=digest(messages),
        scope='Local reservation abandonment only. Unknown upstream execution and costs remain unknown; no response or interpretation reconstructed.')
    with host.store.transaction() as db:
        latest=host.store.session(host.run_id,db)['state']
        unsealed=db.execute('select request_id,status from calls where receipt is null').fetchall()
        if latest!=before or [tuple(r) for r in unsealed]!=[(request_id,'unknown')]:
            raise ValueError('QUIESCENT_SINGLE_UNKNOWN_BOUNDARY_REQUIRED')
        if any(json.loads(r[0]).get('request_id')==request_id for r in db.execute("select body from events where json_extract(body,'$.kind')='r3_response'")):
            raise ValueError('SAVED_RESPONSE_MUST_USE_ORIGINAL_RECOVERY')
        if snapshot.read_bytes()!=snapshot_body:raise ValueError('SDK_CHANGED_DURING_ABANDONMENT')
        if current[1]['interpretation_status']=='deferred':
            unavailable=dict(saved_base,interpretation_for=base,interpretation_status='unavailable',
                error='REPORTER_ATTEMPT_ABANDONED_LOCALLY_PROVIDER_OUTCOME_UNKNOWN',
                rejection_details=dict(request_id=request_id,provider_outcome='unknown',response_saved=False))
            ref=host.store.put(db,unavailable)
            host.store.event(db,host.run_id,'research_report','recorded',outputs=[ref])
        receipt=host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=CALLER,
            tool_id='model.'+before['pilot']['provider']['adapter'],execution_status='cancelled',charged=zero(),
            error='LOCAL_REPORTER_ABANDONMENT_UPSTREAM_OUTCOME_UNKNOWN'),disposition,
            elapsed=json.loads(row['charged'])['wall_s'],kind='reporter_attempt_local_disposition',db=db)
        host.store.event(db,host.run_id,'reporter_attempt_abandoned_locally','cancelled',request=request_id,
            execution=row['execution_id'],caller=CALLER,inputs=[meta['request'],base],outputs=[receipt['output']])
    return disposition


class IncompleteModelOutput(ValueError):
    """Confirmed Provider output, never a transport failure or scientific action."""
    def __init__(self,diagnostic):
        self.diagnostic=diagnostic
        code='R3_LENGTH_TRUNCATED_NO_NATIVE_SUBMISSION' if 'length' in diagnostic['finish_reasons'] else 'R3_INCOMPLETE_NO_NATIVE_SUBMISSION'
        super().__init__(code+': '+json.dumps(diagnostic,separators=(',',':')))


class RequestBoundaryHandoff(Exception):
    """Unwind the SDK loop before a send; never a completed model invocation."""


class CompletedBoundaryHandoff(RequestBoundaryHandoff):
    """A completed invocation, before the next request, may be rotated."""


class SupervisorReviewPause(RequestBoundaryHandoff):
    """The verified paired-feedback boundary, before spending closeout capacity."""


def provider_outcome(host,request_id):
    """Read durable transport/output facts without consuming or settling anything."""
    reception=received(host,request_id)
    row=host.store.lookup(host.run_id,request_id)
    if not reception:
        receipt=json.loads(row['receipt']) if row and row['receipt'] else {}
        abandoned=receipt.get('error')=='LOCAL_REPORTER_ABANDONMENT_UPSTREAM_OUTCOME_UNKNOWN'
        return dict(request_id=request_id,transport='outcome_unknown',outcome_unknown=True,
            response_saved=False,provider_charged=abandoned,model_output='unknown',finish_reasons=[],
            **(dict(local_disposition='abandoned_reporter_attempt',charged_model_requests=1,tokens=None,money=None) if abandoned else {}),
            native_tool_action='not_submitted')
    reasons=[];calls=[];decoded=False
    try:
        choices=json.loads(host.store.artifact(reception['body'],raw=True)).get('choices',[])
        reasons=[c.get('finish_reason') for c in choices]
        calls=[t for c in choices for t in (c.get('message') or {}).get('tool_calls',[])]
        decoded=bool(choices)
    except (ValueError,AttributeError,TypeError):pass
    complete=decoded and all(r in ('stop','tool_calls') for r in reasons)
    return dict(request_id=request_id,transport='confirmed_http_'+str(reception['http_status']),
        http_status=reception['http_status'],outcome_unknown=False,response_saved=True,
        provider_charged=bool(row and row['receipt']),finish_reasons=reasons,
        model_output='complete_unvalidated' if complete else 'confirmed_incomplete',
        native_tool_action='fields_present_unvalidated' if calls else 'not_produced',
        scientific_execution='not_admitted_by_provider_response',body=reception['body'])

class LiveBoundary(httpx.AsyncBaseTransport):
    """One durable reservation per actual send, including auxiliary summarization.

    No auth headers are persisted. Complete response bytes are saved before JSON
    decoding. An unconsumed confirmed response is replayed only for its exact
    request; uncertainty blocks further sends and retains its reservation.
    """
    def __init__(self,host,transport=None,*,allow_truncated_response=False,max_model_calls=None):
        self.host=host
        self.inner=transport or httpx.AsyncHTTPTransport(retries=0,proxy=pilot(host)['provider'].get('proxy_url'))
        self.last_request=None
        self.allow_truncated_response=allow_truncated_response
        self.max_model_calls=max_model_calls
        self.request_phase=None

    async def handle_async_request(self,request):
        host=self.host
        store=host.store
        run=host.run_id
        wire=json.loads(request.content)
        purpose=getattr(self,'purpose',None) or ('conversation' if wire.get('tools') else 'summarization')
        from tools.research.config import role_provider
        expected=role_provider(host.store.session(run)['state']['spec'],pilot(host)['provider'],purpose)
        settings=request_settings(expected)
        if (str(request.url)!=expected['base_url'].rstrip('/')+'/chat/completions'
            or any(wire.get(k)!=v for k,v in settings.items())
            or any(k in wire and k not in settings for k in ('thinking','reasoning_effort','max_tokens'))
            or wire.get('tool_choice','auto')!='auto'):
            raise ValueError('R3_PROVIDER_CONFIGURATION_MISMATCH')
        if expected['adapter']=='chatgpt_gateway':
            caps=expected['model_capabilities']
            if caps.get('verification')!='account_verified' and not isinstance(self.inner,httpx.MockTransport):
                raise ValueError('GATEWAY_MODEL_NOT_ACCOUNT_VERIFIED')
        saved=pilot(host).get('unconsumed_response')
        if saved:
            row=store.lookup(run,saved)
            if row['request_hash']!=digest(wire):
                raise ValueError('R3_SAVED_RESPONSE_MUST_BE_PROCESSED_FIRST')
            reception=received(host,saved)
            if not reception:
                raise ValueError('R3_SAVED_RESPONSE_MISSING')
            self.last_request=saved
            send=next(e for e in store.events(run) if e['kind']=='r3_request' and e['request_id']==saved)
            self.request_phase=store.artifact(send['outputs'][0]).get('request_phase')
            if not row['receipt']:settle(host,row,reception)
            record(host,'r3_response_replay',dict(request_id=saved,new_send=False))
            if not self.allow_truncated_response:self.require_complete()
            return httpx.Response(reception['http_status'],content=store.artifact(reception['body'],raw=True),request=request)
        if pending(host):
            raise ValueError('R3_UNCONFIRMED_ATTEMPT_BLOCKS_SEND')
        from tools.research.provider_context import capacity_estimate
        capacity=capacity_estimate(request.content,expected)
        def guard(db):
            if self.max_model_calls is not None and store.remaining(db=db)['used']['model_calls']>=self.max_model_calls:
                raise ValueError('SUPERVISOR_PROVIDER_REQUEST_LIMIT')
            if store.remaining(db=db)['remaining']['model_calls']<1:
                raise ValueError('PROVIDER_COUNT_EXHAUSTED')
            from tools.research.budget import provider_allowance
            self.request_phase=provider_allowance(host,db)['request_phase']
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
        with store.transaction() as db:
            state=store.session(run,db)['state']
            state['pilot']['live_model_requests']+=1
            store.update_state(db,run,state)
            metadata=store.put(db,dict(request=plain(raw_request),purpose=purpose,pid=os.getpid(),
                input_bytes=len(request.content),
                context_capacity=capacity,
                **(dict(request_phase=self.request_phase) if self.request_phase is not None else {}),
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
            if not self.allow_truncated_response:self.require_complete()
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

    def require_complete(self):
        if not self.last_request:return
        diagnostic=provider_outcome(self.host,self.last_request)
        if (diagnostic.get('http_status',0) in range(200,300)
            and diagnostic['model_output']=='confirmed_incomplete'):
            raise IncompleteModelOutput(diagnostic)

    def consumed(self):
        self.require_complete()
        with self.host.store.transaction() as db:
            state=self.host.store.session(self.host.run_id,db)['state']
            if state['pilot'].get('unconsumed_response')==self.last_request:
                state['pilot'].pop('unconsumed_response')
                self.host.store.update_state(db,self.host.run_id,state)
                self.host.store.event(db,self.host.run_id,'r3_response_processing','decoded',request=self.last_request)

    async def aclose(self):
        await self.inner.aclose()

def live_model_class(boundary):
    class AccountedModel(model_type(pilot(boundary.host)['provider'])):
        def format_request(self,*args,**kwargs):
            request=super().format_request(*args,**kwargs)
            if pilot(boundary.host)['provider']['adapter']=='chatgpt_gateway':
                request['messages']=gateway_history(boundary.host,request['messages'])
            saved=pilot(boundary.host).get('unconsumed_response')
            if not saved:
                for tool in request.get('tools',[]):
                    function=tool.get('function',{})
                    if 'parameters' in function:function['parameters']=provider_schema(function['parameters'])
            if saved:
                event=next(e for e in boundary.host.store.events(boundary.host.run_id)
                    if e['kind']=='r3_request' and e['request_id']==saved)
                original=boundary.host.store.artifact(boundary.host.store.artifact(event['outputs'][0])['request'])
                original_tools={t['function']['name']:t['function'].get('parameters') for t in original.get('tools',[]) if 'function' in t}
                for tool in request.get('tools',[]):
                    function=tool.get('function',{})
                    if 'parameters' not in function:continue
                    projected=provider_schema(function['parameters'])
                    if original_tools.get(function.get('name'))==projected:function['parameters']=projected
                last=original['messages'][-1]
                # Preserve the saved tail verbatim. LiveBoundary still checks the
                # entire wire hash; no new L0 may reinterpret a saved response.
                if last.get('role')=='user' and isinstance(last.get('content'),str) and last['content'].startswith('CURRENT_RESEARCH_PACKET\n'):
                    request['messages'].append(deepcopy(last))
            elif getattr(boundary,'research_packet',None) is not None:
                request['messages'].append(dict(role='user',content='CURRENT_RESEARCH_PACKET\n'+
                    json.dumps(boundary.research_packet,separators=(',',':'))))
            return request

        async def stream(self,*args,**kwargs):
            # Reject saved incomplete output before even the first SDK event.
            boundary.require_complete()
            try:
                async for item in super().stream(*args,**kwargs):
                    boundary.require_complete()
                    yield item
            except Exception as exc:
                try:boundary.require_complete()
                except IncompleteModelOutput as confirmed:raise confirmed from exc
                raise
            boundary.consumed()  # Failed conversion leaves the saved response available.
    return AccountedModel

def load_credential(path):
    if not os.environ.get('DEEPSEEK_API_KEY') and path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            key,sep,value=line.strip().removeprefix('export ').partition('=')
            if sep and key.strip()=='DEEPSEEK_API_KEY':
                os.environ['DEEPSEEK_API_KEY']=value.strip().strip('"').strip("'")
    if not os.environ.get('DEEPSEEK_API_KEY'):
        raise ValueError('MODEL_KEY_MISSING')


