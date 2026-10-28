"""Accounted model transport and exact response recovery over the existing Store."""
from copy import deepcopy
import json, os, time
from uuid import uuid4
import httpx
from strands.models.openai import OpenAIModel
from tools.platform_store import plain, zero
from tools.state_io import digest
CALLER = 'research-provider'

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
        return dict(request_id=request_id,transport='outcome_unknown',outcome_unknown=True,
            response_saved=False,provider_charged=False,model_output='unknown',finish_reasons=[],
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
        self.inner=transport or httpx.AsyncHTTPTransport(retries=0)
        self.last_request=None
        self.allow_truncated_response=allow_truncated_response
        self.max_model_calls=max_model_calls

    async def handle_async_request(self,request):
        host=self.host
        store=host.store
        run=host.run_id
        wire=json.loads(request.content)
        purpose=getattr(self,'purpose',None) or ('conversation' if wire.get('tools') else 'summarization')
        from tools.research.config import role_provider
        expected=role_provider(host.store.session(run)['state']['spec'],pilot(host)['provider'],purpose)
        if (str(request.url)!=expected['base_url'].rstrip('/')+'/chat/completions'
            or wire.get('model')!=expected['model'] or wire.get('thinking')!={'type':expected['thinking']}
            or wire.get('reasoning_effort')!=expected['reasoning_effort']
            or (('max_tokens' in wire) if expected.get('max_tokens') is None else wire.get('max_tokens')!=expected['max_tokens'])
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
    class AccountedDeepSeekModel(DeepSeekModel):
        def format_request(self,*args,**kwargs):
            request=super().format_request(*args,**kwargs)
            saved=pilot(boundary.host).get('unconsumed_response')
            if saved:
                event=next(e for e in boundary.host.store.events(boundary.host.run_id)
                    if e['kind']=='r3_request' and e['request_id']==saved)
                original=boundary.host.store.artifact(boundary.host.store.artifact(event['outputs'][0])['request'])
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
    return AccountedDeepSeekModel

def load_credential(path):
    if not os.environ.get('DEEPSEEK_API_KEY') and path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            key,sep,value=line.strip().removeprefix('export ').partition('=')
            if sep and key.strip()=='DEEPSEEK_API_KEY':
                os.environ['DEEPSEEK_API_KEY']=value.strip().strip('"').strip("'")
    if not os.environ.get('DEEPSEEK_API_KEY'):
        raise ValueError('MODEL_KEY_MISSING')


