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
PLAN_TOOL_DESCRIPTION=('Propose/search/execute/initialize_control/physical_replay/diagnose. '
    'control_search uses physical replay callbacks; Native mathematical sequence optimization uses research_analysis, not a selected_method label. '
    'Diagnose reads existing evidence; selected_method does not execute a mathematical/native worker '
    '(use research_analysis with its registered template). Only an explicit diagnostic payload requests local solves. '
    'Control sources and optional NMPC handoff are described in control_initialization_methods. '
    'Select an exact publicly read fresh complete passing evaluation and freeze it; zero configured extra repetitions seals immediately. '
    'Positive configured confirmations preserve failures and identity. History never satisfies fresh gates; failures/counters persist. STOP seals study.')
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
            if not row['receipt']:settle(host,row,reception)
            record(host,'r3_response_replay',dict(request_id=saved,new_send=False))
            if not self.allow_truncated_response:self.require_complete()
            return httpx.Response(reception['http_status'],content=store.artifact(reception['body'],raw=True),request=request)
        if pending(host):
            raise ValueError('R3_UNCONFIRMED_ATTEMPT_BLOCKS_SEND')
        from tools.research.provider_context import capacity_estimate
        capacity=capacity_estimate(request.content,expected)
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
        purpose=getattr(self,'purpose',None) or ('conversation' if wire.get('tools') else 'summarization')
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


def read_tool_evidence(host,query):
    """Apply compact defaults without replacing an explicit retrieval view."""
    from tools.research.core import read_evidence
    if state(host)['spec'].get('research_decisions',{}).get('context_limits'):
        query={'view':'summary',**query}
    return read_evidence(host,query)


def plan_schema(actions, *, decision_required=False,family_version=None):
    """Advertise only executable action payloads and their reachable definitions."""
    from tools.research.contracts import Plan, PLAN_PAYLOADS, PLAN_OPTIONAL_PAYLOADS, PLAN_RESEARCH_INTENTS
    schema=Plan.model_json_schema()
    if family_version:
        schema['properties']['search']['anyOf']=[{'$ref':'#/$defs/FamilyMixedSearch'},{'type':'null'}]
        generation='GenerationRequestV2' if family_version=='serial_family_space_v2' else 'GenerationRequest'
        schema['properties']['generation']['anyOf']=[{'$ref':'#/$defs/'+generation},{'type':'null'}]
    payloads=PLAN_PAYLOADS
    allowed={payloads[a] for a in actions if a in payloads}
    allowed.update(f for a in actions for f in PLAN_OPTIONAL_PAYLOADS.get(a,()))
    for field in set(payloads.values())-allowed:schema['properties'].pop(field,None)
    schema['properties']['action']={'type':'string','enum':actions}
    if decision_required:
        schema['required'].append('decision')
        schema['properties']['decision']={'$ref':'#/$defs/ResearchDecision'}
    schema['allOf']=[]
    for intent in dict.fromkeys(PLAN_RESEARCH_INTENTS[a] for a in actions):
        owners=[a for a in actions if PLAN_RESEARCH_INTENTS[a]==intent]
        schema['allOf'].append({'if':{'properties':{'action':{'enum':owners}}},
            'then':{'properties':{'decision':{'properties':{'research_intent':{'const':intent}}}}}})
    for field in dict.fromkeys(payloads.values()):
        owners=[a for a in actions if payloads.get(a)==field or field in PLAN_OPTIONAL_PAYLOADS.get(a,())]
        if not owners:continue
        required_by=[a for a in owners if field not in PLAN_OPTIONAL_PAYLOADS.get(a,())]
        branch=dict(required=[field],properties={field:{'not':{'type':'null'}}}) if required_by else {}
        if required_by and required_by!=owners:
            branch={'if':{'properties':{'action':{'enum':required_by}}},'then':branch}
        if len(actions)==1:
            if required_by:
                schema['required'].append(field)
                schema['properties'][field].pop('default',None)
                schema['properties'][field]['anyOf']=[v for v in schema['properties'][field]['anyOf'] if v.get('type')!='null']
        else:
            schema['allOf'].append({'if':{'properties':{'action':{'enum':owners}}},'then':branch,
                'else':{'properties':{field:{'type':'null'}}}})
    schema['allOf'].append({'if':{'properties':{'action':{'not':{'enum':['select','confirm']}}}},
        'then':{'properties':{'revise_selection':{'const':False}}}})
    if decision_required:
        bound=[a for a in actions if a in ('execute','initialize_control','control_search','physical_replay')]
        schema['allOf'].append({'if':{'properties':{'action':{'enum':bound}}},'then':{'properties':{
            'decision':{'required':['selected_candidate'],'properties':{'selected_candidate':{'$ref':'#/$defs/EvidenceRef'}}}}}})
    needed=set()
    def visit(v):
        if isinstance(v,dict):
            if '$ref' in v:
                name=v['$ref'].rsplit('/',1)[-1]
                if name not in needed:
                    needed.add(name);visit(schema['$defs'][name])
            for x in v.values():visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    visit(schema['properties'])
    schema['$defs']={k:v for k,v in schema['$defs'].items() if k in needed}
    return schema


def error_feedback(host, use, exc, before):
    """Small correction response; exact rejected payload and traceback stay in Store."""
    import traceback
    s=state(host)
    full=record(host,'tool_request_error',dict(tool_use=use,error=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
    counts=lambda v:tuple(v.get(k,0) for k in ('physical_replay_launches','nmpc_launches','mathematical_evaluations','offline_nlp','bdf_replays','local_solves','admitted_training_stages'))
    message=str(exc);code=message.split(':',1)[0].split('\n',1)[0]
    field=None;expected=message[:300];refs=[]
    if hasattr(exc,'errors'):
        errors=exc.errors(include_url=False,include_context=False,include_input=False)
        field='.'.join(map(str,errors[0]['loc'])) or None
        expected='; '.join(e['msg'] for e in errors[:3])[:400]
        code=errors[0]['type']
    hints={
        'NATIVE_ANALYSIS_REQUIRES_EXACT_STATE_OR_FROZEN_INITIALIZATION':('operating_point','Native methods use model_source=mujoco and operating_point=standardized_initial_pretension with no saved source, or operating_point=saved_state with saved_state OR execution+update_id. Retrieve method details for source/window requirements.'),
        'DISPOSITION_REQUIRES_EXACT_ACTUAL_READ':('experience_disposition','Keys must identify an actual experience_retrieve operation=read receipt or its exact entry_id@revision. Scientific artifact IDs, invented hypothesis names, search results and SELECT physical evidence are not experience keys. If this Study does not expose legal experience_retrieve, remove the inapplicable experience_disposition field; do not guess IDs.'),
        'explicit evidence_read of this completed evaluation required':('selected_execution','Publicly evidence_read the exact selected_execution with view=full and pointer="" before SELECT; /acceptance alone does not satisfy the whole-result read required here.'),
        'ORDERED_V2_CORRECTION_WINDOW_REQUIRED':('control_search.settings.correction_window_s','0 <= window[0] <= knots[0] < knots[-1] <= window[1] <= task duration'),
        'DECISION_CANDIDATE_MISMATCH':('decision.selected_candidate','Match the exact action candidate (for physical_replay, physical_replay.candidate); source is a control/result reference and must not replace the candidate.'),
        'MUJOCO_REQUIRES_EXPLICIT_NATIVE_METHOD_AND_MODEL_SOURCE':('operation/model_source','Unsupported method-model combination: instantaneous_braking_v1 is not a MuJoCo native method. Choose a registered operation and its supported model_source from mathematical_capabilities; native options cannot make an unsupported combination executable.'),
        'CONTROL_SOURCE_REQUIRES_EXACT_PARENT':('control_seed.parent','When control_seed.source is supplied, supply its exact parent candidate too. For complete measured NMPC input, parent must equal control_seed.candidate; source is the execution result, not the candidate.'),
        'PHYSICAL_REPLAY_CANDIDATE_TASK_MODEL_OR_SEQUENCE_MISMATCH':('source','Use a candidate-bound source; initialize_control explicitly rebinds inherited controls'),
        'UNREGISTERED_RESEARCH_EVIDENCE':('supporting_evidence','Readable does not mean registered. Query working_set /citation_eligibility; use only registered references whose supported_inferences match the claim. Reading does not register evidence.'),
        'REGISTERED_CURRENT_ANALYSIS_REQUIRED':('control_seed.response_evidence','Request input_sensitivity for the selected candidate, then use its registered result reference'),
        'VERIFIED_CANDIDATE_INPUT_SENSITIVITY_REQUIRED':('control_seed.response_evidence','Use computed, numerically verified input_sensitivity bound to this candidate, model, task, operating point and tendon order'),
        'STOP_MUST_CITE_ALL_NEW_EXPERIMENT_RESULTS':('supporting_evidence','Explicitly cite the complete current research.all_fresh_results index and explain the conclusions'),
        'ENGINEERING_TOOL_UNAVAILABLE':('action','Choose an available operation from current packet; engine failure is not scientific infeasibility')}
    for marker,(f,hint) in hints.items():
        if marker in message:code=marker;field=f;expected=hint
    if 'ACTION_REQUIRES_ONLY_' in message:
        from tools.research.contracts import PLAN_PAYLOADS
        field=PLAN_PAYLOADS.get(use['input'].get('action'),'action')
        expected='Action '+str(use['input'].get('action'))+' requires non-null '+field+' and no other action payload. '+message[message.index('ACTION_REQUIRES_ONLY_'):].split('\n')[0][:160]
        if use['input'].get('action')=='physical_replay':expected+='; put candidate/source inside physical_replay and match decision.selected_candidate to physical_replay.candidate; omit top-level candidate.'
    if hasattr(exc,'errors') and any(e['loc'] and e['loc'][0]=='protocol' and e['type']=='extra_forbidden' for e in errors):
        field='protocol';expected='Use the complete frozen analysis_protocol from the method request_template/protocol in mathematical_capabilities. Do not add protocol fields; holding duration belongs to the frozen task.'
    if hasattr(exc,'errors'):
        setting_error=next((e for e in errors if e['type']=='extra_forbidden' and
            tuple(e['loc'][-2:])==('settings','regularization')),None)
        if setting_error:
            from tools.research.contracts import LocalControlSearchSettings
            field='.'.join(map(str,setting_error['loc']))
            expected=('regularization is not supported. Use only LocalControlSearchSettings fields: '
                +', '.join(LocalControlSearchSettings.model_fields)+'. Plan control_search uses physical replay callbacks; '
                'Native optimization requires research_analysis and the registered request_template. '
                'Do not rename fields or assume zero integration; normal authorization and cost admission still apply.')
    if isinstance(exc,(KeyError,IndexError)) and use.get('name')=='evidence_read':
        code='INVALID_EVIDENCE_POINTER';field='pointer';expected='Read the parent pointer with view=summary to obtain actual child keys'
        if use['input'].get('reference') and not getattr(exc,'evidence_navigation',None):
            refs=[use['input']['reference']]
            try:
                value=host.store.artifact(refs[0]);parent=''
                for part in use['input'].get('pointer','').strip('/').split('/') if use['input'].get('pointer') else []:
                    key=part.replace('~1','/').replace('~0','~')
                    if isinstance(value,dict) and key not in value:break
                    if isinstance(value,list) and (not key.isdigit() or int(key)>=len(value)):break
                    value=value[int(key)] if isinstance(value,list) else value[key];parent+='/'+part
                if isinstance(value,dict):expected='Available children at '+(parent or '/')+': '+', '.join(value)
                elif isinstance(value,list):expected='List at '+(parent or '/')+' has '+str(len(value))+' items; use view=range or an index from 0 through '+str(len(value)-1)
                if use['input'].get('fields'):field='fields'
            except (ValueError,KeyError,IndexError,TypeError):pass
        derived=getattr(exc,'evidence_navigation',{}).get('derived_view_query')
        if derived:
            code='EVIDENCE_VIEW_MISMATCH';field='view'
            expected='Use this exact derived-view query: '+json.dumps(derived,separators=(',',':'))
    if code=='RESEARCH_INTENT_ACTION_MISMATCH':
        from tools.research.contracts import PLAN_RESEARCH_INTENTS
        field='decision.research_intent';action=use['input']['action']
        expected=f'action={action} requires decision.research_intent={PLAN_RESEARCH_INTENTS[action]}'
    if 'EVIDENCE_RANGE_REQUIRES_LIST_POINTER' in message:
        field='pointer';expected='Read the current reference root with view=summary, then use an advertised list read_pointer with view=range'
    if code=='BATCH_REQUEST_EXCEEDS_FROZEN_SHARED_CAPACITY':
        from tools.research.budget import decision_budget
        science=decision_budget(host)['science_budget']
        requested=(use['input'].get('control_search') or {}).get('settings',{}).get('evaluation_requests')
        maximum=s['spec']['budgets']['physical_launches']+1
        field='control_search.settings.evaluation_requests'
        expected=(f'Plan control_search cap {requested} exceeds frozen declared callback maximum {maximum} '
            '(physical_launches + one possibly reusable baseline). Each new callback uses a full physical replay; '
            f'raw remaining shared launches={science["remaining_physical"]}, full replays={science["remaining_full_replays"]}. '
            'These are remaining totals, not permission or a guarantee that a batch fits. Response FD needs a baseline plus '
            'effective coefficient probes and one candidate per completed update. Native optimization instead requires '
            'research_analysis with its registered template and mathematical allowance; internal native rollouts are not independent replay credits.')
    navigation=getattr(exc,'evidence_navigation',{})
    if use['name']=='evidence_read' and 'EVIDENCE_FIELDS_REQUIRES_NONEMPTY_FIELDS' in message:
        code='EVIDENCE_FIELDS_REQUIRES_NONEMPTY_FIELDS';field='fields'
        query={k:use['input'][k] for k in ('reference','pointer') if k in use['input']}
        query['view']='summary'
        expected='Empty fields select no information. Read the object summary, then select at least one advertised child key. Use exact query: '+json.dumps(query,separators=(',',':'))
    if navigation:
        query=navigation['corrected_query']
        if navigation.get('derived_view_query'):code='EVIDENCE_VIEW_MISMATCH';field='view'
        elif use['input'].get('fields'):field='fields'
        else:field='pointer'
        expected='Use exact query: '+json.dumps(query,separators=(',',':'))
    if 'PROTECTED_EVIDENCE_READ_REQUIRES' in message:
        field='reference';expected='Only current result references are readable during closeout; use all_fresh_results and select a fresh pass or STOP'
    citation={}
    if code=='UNREGISTERED_RESEARCH_EVIDENCE' or code.startswith(('INFERENCE_NOT_SUPPORTED','EVIDENCE_TASK_IDENTITY','EVIDENCE_DESIGN_IDENTITY','EVIDENCE_MODEL_SCOPE')):
        from tools.research.evidence_policy import registered_references,citation_inventory
        known=registered_references(host)
        refs=[r for r in use['input'].get('supporting_evidence',[]) if r not in known]
        anchor=next(iter(known),s.get('family_space_reference'))
        citation=dict(rejected_references=refs,reason=message[:300],registered_count=len({r['artifact_id'] for r in known}),
            recent_registered=citation_inventory(host)[-3:],
            inventory_query=dict(reference=anchor,view='working_set',pointer='/citation_eligibility'),
            missing_validation='FamilySpace/raw samples do not establish independent task acceptance. Use a bound registered physical evaluation or scoped mathematical result for the corresponding claim.')
    return dict(status='rejected' if counts(before)==counts(s) else 'execution_failed',error_code=code[:100],field=field,
        evidence_navigation=getattr(exc,'evidence_navigation',None),
        expected=expected,scientific_execution_started=counts(before)!=counts(s),relevant_references=refs,full_error_reference=full,**citation)

def build_harness(host,*,transport,api_key,instructions,model_class,tool_executor,research_tools,configuration_path,session_directory,session_id=None):
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
    compact=bool(s['spec'].get('research_decisions',{}).get('context_limits'))
    context=dict(strategies=[Offload.truncate('tool_results',{'preview_tokens':500 if compact else 1024}).when(threshold=1500 if compact else 4096)])
    agent=create_harness(model=model,tools=research_tools,instructions=instructions,
        builtin_tools=[],builtin_plugins=[],background_tasks=False,memory=False,skills=False,
        context_manager=context,session=dict(id=session_id or s['pilot']['framework_session_id'],dir=str(session_directory)),
        retry_strategy=None,callback_handler=None,caching=False,tool_executor=tool_executor)
    atomic_json(configuration_path,dict(harness='strands-harness==0.2.0',sdk='strands-agents==1.59.0',
        provider=provider,registered_tools=sorted(agent.tool_names),session_id=session_id or s['pilot']['framework_session_id'],
        retry_controllers=0,context='public tool-result offload and retrieval',offload_threshold=1500 if compact else 4096,
        offload_preview_tokens=500 if compact else 1024,
        dynamic_context='request-only tail via public OpenAIModel.format_request; native SDK history unchanged',
        transport='accounted live boundary'))
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

async def deliver_science_before_decision(host,agent,transport):
    """Settle L1 only after native results are paired and durably recoverable.

    This is an intra-invocation boundary, not session_handoff.safe_boundary.
    The latter additionally requires a completed invocation and remains unchanged.
    """
    from tools.research.reporter import current_reports, complete_reports
    from tools.research.session_handoff import unmatched
    if pending(host) or state(host)['pilot'].get('unconsumed_response'):
        raise ValueError('SCIENCE_DELIVERY_REQUIRES_CONSUMED_PROVIDER_RESPONSE')
    if not any(v['interpretation_status']=='deferred' for _,v in current_reports(host)):return
    if state(host).get('pending') or unmatched(agent.messages):
        raise ValueError('SCIENCE_DELIVERY_REQUIRES_PAIRED_SETTLED_TOOLS')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE run_id=? AND receipt IS NULL',(host.run_id,)).fetchone()[0]:
            raise ValueError('SCIENCE_DELIVERY_REQUIRES_SETTLED_RECEIPTS')
    original={}
    for event in host.store.events(host.run_id):
        if event['kind']=='model_original_tool_feedback':
            value=host.store.artifact(event['outputs'][0]);original[value['tool_use']['toolUseId']]=value['result']
    for message in agent.messages:
        for block in message['content']:
            result=block.get('toolResult')
            # Public SDK offload may replace large evidence-read text with a
            # retrievable preview. Identity/status pairing must survive; original
            # content is already immutable in Store and the SDK stash.
            if result and result['toolUseId'] in original and result['status']!=original[result['toolUseId']]['status']:
                raise ValueError('SCIENCE_DELIVERY_ORIGINAL_TOOL_STATUS_MISMATCH')
    await agent._session_manager.save_snapshot(agent,is_latest=True)
    record(host,'science_delivery_boundary',dict(session_id=agent._session_manager.session_id,
        sdk_message_identity=digest(agent.messages),paired=True,receipts_settled=True))
    await complete_reports(host,transport)
    if pending(host) or state(host)['pilot'].get('unconsumed_response') or any(
            v['interpretation_status']=='deferred' for _,v in current_reports(host)):
        raise ValueError('SCIENCE_DELIVERY_INCOMPLETE_BLOCKS_DECISION')


async def pause_completed_invocation(host,agent,completed):
    """Pause only at the existing durable handoff boundary, with delivered reports."""
    from tools.research.session_handoff import safe_boundary, trusted_history
    from tools.research.reporter import current_reports
    await wait_training(host)
    if any(v['interpretation_status']=='deferred' for _,v in current_reports(host)):
        raise ValueError('REPORTER_DELIVERY_REQUIRED_BEFORE_SUPERVISOR_PAUSE')
    await agent._session_manager.save_snapshot(agent,is_latest=True)
    with host.store.connect(True) as db:
        safe_boundary(host,state(host),db,agent.messages)
    trusted_history(host,agent)
    record(host,'supervisor_pause',dict(completed_invocations=completed,
        session_id=agent._session_manager.session_id,sdk_message_identity=digest(agent.messages),
        research_status=state(host)['research_status'],budgets_preserved=True))


async def converse(host,*,session_handoff=False,pause_after_completed_invocations=None,handoff_before_next_request=False,handoff_request_bytes=None,pause_exploration_remaining=None,restore_only=False):
    if pause_after_completed_invocations is not None and (type(pause_after_completed_invocations) is not int or pause_after_completed_invocations<1):
        raise ValueError('POSITIVE_COMPLETED_INVOCATION_COUNT_REQUIRED')
    from tools.research.state import require_authorization
    require_authorization(host)
    if state(host)['spec'].get('initial_structure_strategy'):
        from tools.research.tool_readiness import execution_environment
        if execution_environment(state(host)['spec'])['status']!='ready':
            raise ValueError('HOST_MATH_NMPC_ENVIRONMENT_PREFLIGHT_REQUIRED_BEFORE_PROVIDER')
    from tools.research.core import guard,dispatch,experience,read_evidence,packet
    from tools.research.contracts import Plan,ExperienceQuery,EvidenceQuery,AnalysisRequest,RLRequest
    from tools.research.reporter import InvestigationRequest, investigate, scientific_feedback, complete_reports
    if session_handoff and not state(host)['pilot'].get('session_handoff_live_admitted'):
        raise ValueError('LIVE_PROVIDER_CONTINUATION_UNVERIFIED_HANDOFF_NOT_ADMITTED')
    if handoff_request_bytes is not None and (type(handoff_request_bytes) is not int or handoff_request_bytes<1):
        raise ValueError('POSITIVE_HANDOFF_REQUEST_BYTES_REQUIRED')
    if pause_exploration_remaining is not None and (type(pause_exploration_remaining) is not int or pause_exploration_remaining<0):
        raise ValueError('NONNEGATIVE_EXPLORATION_REVIEW_THRESHOLD_REQUIRED')
    if (handoff_before_next_request or handoff_request_bytes is not None or pause_exploration_remaining is not None) and (not session_handoff or state(host)['pilot'].get('session_handoff_boundary')!='request_feedback'):
        raise ValueError('REQUEST_FEEDBACK_LIVE_ADMISSION_REQUIRED')
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
    boundary=Boundary(host)
    def handler(kind):
        def run(use,**kwargs):
            before=state(host)
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
                        elif kind=='investigate':
                            value=investigate(host,use['input'])
                        else:
                            value=read_tool_evidence(host,use['input'])
                        host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
                            tool_id='research.core_'+kind,tool_version='1.0.0',execution_status='completed',charged=zero()),value)
                original=value
                if kind not in ('evidence','investigate') and state(host)['spec'].get('research_decisions',{}).get('context_limits'):
                    from tools.research.research_context import tool_feedback
                    value=tool_feedback(host,value)
                if kind in ('plan','analysis','rl') and state(host)['spec'].get('research_decisions'):
                    report=scientific_feedback(host,original,before)
                    if report is not None:value=report
                if isinstance(original,dict) and original.get('inference_assessment'):
                    value['inference_assessment']=original['inference_assessment']
                return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text=json.dumps(value,separators=(',',':')))])
            except Exception as exc:
                key='native-'+use['toolUseId']
                reserved=host.store.lookup(host.run_id,key)
                if reserved and not reserved['receipt']:
                    host.store.complete(reserved,dict(request_id=key,execution_id=reserved['execution_id'],caller=host.actor,
                        tool_id='research.core_'+kind,tool_version='1.0.0',execution_status='failed',error=str(exc),charged=zero()),dict(error=str(exc)))
                from tools.research.feedback import facts
                if state(host)['spec'].get('research_decisions'):
                    return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(error_feedback(host,use,exc,before)))])
                return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(dict(
                    error=type(exc).__name__,message=str(exc),decision_facts=facts(host))))])
        return run
    rl_mode=enabled(state(host)['spec'],'rl')
    formal=bool(state(host)['spec'].get('capabilities'))
    instructions=state(host)['spec']['execution_instructions']
    native=[PythonAgentTool(name,dict(name=name,description=description,inputSchema={'json':schema.model_json_schema()}),handler(kind))
        for name,description,schema,kind in [('research_plan',PLAN_TOOL_DESCRIPTION,Plan,'plan'),
            ('experience_retrieve','Read-only case/procedure draft search/read with provenance',ExperienceQuery,'experience'),
            ('evidence_read','Read exact immutable evidence and JSON pointer',EvidenceQuery,'evidence')]]
    if formal or rl_mode:
        actions=['propose','stop','diagnose','select','confirm'] if formal and state(host)['spec'].get('mode')!='rl_interface' else ['propose','stop']
        if formal and state(host)['spec'].get('mode')!='rl_interface':
            actions += [a for a,c in [('execute','nmpc'),('search','search'),('mechanics','mathematics'),('replay','replay')] if enabled(state(host)['spec'],c)]
        actions=state(host)['spec'].get('allowed_plan_actions',actions)
        schema=plan_schema(actions,decision_required=bool(state(host)['spec'].get('research_decisions')))
        native[0].tool_spec={**native[0].tool_spec,'inputSchema':{'json':schema}}
    if state(host)['spec'].get('nominal_source') or state(host)['spec'].get('start_mode')=='family_space':
        native.append(PythonAgentTool('research_analysis',dict(name='research_analysis',description='Candidate-bound mathematics. model_source selects the reduced provider or native MuJoCo methods independently of control. saved_state or execution plus update_id selects a source-bound state; native methods support standardized_initial_pretension from frozen initialization, or a complete native checkpoint or verified measured prefix. Each calculation charged once; task acceptance unmeasured.',inputSchema={'json':AnalysisRequest.model_json_schema()}),handler('analysis')))
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
    if state(host)['spec'].get('research_decisions') and not state(host)['spec'].get('rl_evaluation_source'):
        native.append(PythonAgentTool('research_investigate',dict(name='research_investigate',
            description='Submit a read-only investigation of saved results and optional exact reads. Returns a saved report reference; formal interpretation arrives before the next research decision. No new scientific computation; internal reads give no SELECT/STOP credit.',
            inputSchema={'json':InvestigationRequest.model_json_schema()}),handler('investigate')))
    if formal:
        native[1].tool_spec={**native[1].tool_spec,'description':'Unavailable outside scoped milestone evidence'}
    agent=None
    def build_session(session_id=None):
        restored=build_harness(host,transport=boundary,api_key=os.environ['DEEPSEEK_API_KEY'],instructions=instructions,
            model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),research_tools=[t for t in native if t is not native[1]] if state(host)['spec'].get('rl_evaluation_source') else native,
            configuration_path=host.store.root/'framework_configuration.json',session_directory=host.store.root/'framework_sessions',session_id=session_id)
        # Dynamic schemas and removed tools are part of the verified boundary.
        # Recreate that exact registry before snapshot verification, including on
        # process restart. before_model will derive the next legal schema again.
        definitions=None
        if agent is not None:
            from tools.research.session_handoff import schemas
            definitions=schemas(agent)
        else:
            s=state(host)
            for key in ('handoff_preparation','handoff'):
                ref=s['pilot'].get(key)
                saved=host.store.artifact(ref) if ref else {}
                if saved.get('next_session')==(session_id or s['pilot']['framework_session_id']):
                    definitions=saved['tool_schemas'];break
        if definitions is not None:
            registry=restored.tool_registry.registry
            if set(definitions)-set(registry):raise ValueError('SAVED_SESSION_TOOL_IMPLEMENTATION_UNAVAILABLE')
            for name in list(registry):
                if name not in definitions:registry.pop(name)
            for name,spec in definitions.items():registry[name].tool_spec=deepcopy(spec)
        return restored
    agent=build_session()
    from tools.research.session_handoff import unmatched, recover_feedback, trusted_history, INVOCATION_PROMPT
    try:
        saved=state(host)['pilot'].get('unconsumed_response')
        reporter_saved=bool(saved and (received(host,saved) or {}).get('purpose')=='reporter')
        # An interrupted pre-decision Reporter owns a saved tool-result snapshot,
        # not a completed invocation. Verify its exact Store anchor before using
        # the existing incomplete-history recovery path.
        intra_reporter=False
        if reporter_saved:
            anchors=[host.store.artifact(e['outputs'][0]) for e in host.store.events(host.run_id)
                if e['kind']=='science_delivery_boundary']
            if anchors and anchors[-1]['session_id']==agent._session_manager.session_id:
                intra_reporter=anchors[-1]['sdk_message_identity']==digest(agent.messages)
        if state(host)['pilot'].get('handoff'):
            from tools.research.session_handoff import reconcile
            agent=await reconcile(host,build_session,host.store.root/'framework_sessions',allow_incomplete=not reporter_saved or intra_reporter)
        else:
            trusted_history(host,agent,allow_incomplete=not reporter_saved or intra_reporter)
        await complete_reports(host,boundary.inner,recover_only=True)
        if unmatched(agent.messages):await recover_feedback(host,agent)
        continuation=state(host).get('pending_authorized_continuation')
        if continuation:
            approval=host.store.artifact(continuation)
            prior=host.store.artifact(approval['previous_state'])
            if (not approval.get('user_approval') or prior['research_status']!='stopped'
                    or prior.get('success_gate') or approval['previous_final_disposition']!=prior['final_disposition']):
                raise ValueError('EXPLICIT_NONPASS_STOP_CONTINUATION_REQUIRED')
            guard(host)
            preparation=state(host)['pilot'].get('handoff')
            source=(host.store.artifact(host.store.artifact(preparation)['source_state']) if preparation else {})
            if source.get('pending_authorized_continuation')!=continuation:
                current=decision_packet(host)['research']
                native[0].tool_spec={**native[0].tool_spec,'inputSchema':{'json':plan_schema(current['actions'],
                    decision_required=True,family_version=state(host)['spec'].get('family_space',{}).get('version'))}}
                # Restore the authorized tools removed by the previous closeout.
                for tool in native:
                    if tool is not native[1]:agent.tool_registry.registry[tool.tool_name]=tool
                from tools.research.session_handoff import handoff
                preparation,agent=await handoff(host,agent,build_session,host.store.root/'framework_sessions')
            update(host,pending_authorized_continuation=None)
            record(host,'authorized_continuation_activated',dict(authorization=continuation,
                previous_stop=approval['previous_final_disposition'],handoff=preparation,
                session_id=agent._session_manager.session_id,tools=sorted(agent.tool_registry.registry),next_request_sent=False))
    except BaseException:
        await boundary.aclose()
        raise
    if restore_only:
        record(host,'sdk_restore_verified',dict(session_id=agent._session_manager.session_id,
            sdk_message_identity=digest(agent.messages),unmatched_tool_ids=list(unmatched(agent.messages)),
            next_request_sent=False))
        await boundary.aclose()
        return
    if (state(host)['spec'].get('mode')=='rl_interface' or state(host)['spec'].get('capabilities')) and not state(host).get('live_started_unix'):
        s=state(host);pilot=deepcopy(s['pilot'])
        pilot.update(request_deadline_unix=None,bounded_request_reservation=False)
        update(host,live_started_unix=time.time(),pilot=pilot)
    if state(host)['spec'].get('rl_evaluation_source') or state(host)['spec'].get('mode')=='engineering_investigation':
        agent.tool_registry.registry.pop('retrieve_context',None)
    async def before_model(event):
        s=state(host)
        if s['research_status']=='stopped':
            event.cancel='Accepted native STOP; no additional request'
            return
        if s['pilot'].get('unconsumed_response'):
            saved=s['pilot']['unconsumed_response']
            if (received(host,saved) or {}).get('purpose')=='reporter':
                raise ValueError('REPORTER_RESPONSE_MUST_BE_ARCHIVED_BEFORE_MAIN_DECISION')
            ev=next(e for e in host.store.events(host.run_id) if e['kind']=='r3_request' and e['request_id']==saved)
            original=host.store.artifact(host.store.artifact(ev['outputs'][0])['request'])
            agent.system_prompt=next(m['content'] for m in original['messages'] if m['role']=='system')
            definitions={t['function']['name']:t['function'] for t in original.get('tools',[])}
            registry=agent.tool_registry.registry
            if set(definitions)-set(registry):raise ValueError('SAVED_REQUEST_TOOL_IMPLEMENTATION_UNAVAILABLE')
            for name in list(registry):
                if name not in definitions:registry.pop(name)
            for name,definition in definitions.items():
                registry[name].tool_spec=dict(name=name,description=definition.get('description',''),
                    inputSchema={'json':definition['parameters']})
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
        if s['spec'].get('research_decisions'):
            await deliver_science_before_decision(host,agent,boundary.inner)
        for name,contract in (('evidence_read',EvidenceQuery),('research_investigate',InvestigationRequest)):
            tool=agent.tool_registry.registry.get(name)
            if tool:tool.tool_spec={**tool.tool_spec,'inputSchema':{'json':contract.model_json_schema()}}
        current=decision_packet(host)
        if formal:agent.tool_registry.registry.pop('experience_retrieve',None)
        if 'research' in current:
            native[0].tool_spec={**native[0].tool_spec,'description':PLAN_TOOL_DESCRIPTION,'inputSchema':{'json':plan_schema(current['research']['actions'],decision_required=bool(s['spec'].get('research_decisions')),
                family_version=s['spec']['family_space']['version'] if s['spec'].get('start_mode')=='family_space' else None)}}
        if not enabled(s['spec'],'analysis') or s['spec']['budgets']['mathematical_evaluations']<=s.get('mathematical_evaluations',0):
            agent.tool_registry.registry.pop('research_analysis',None)
        # Provider readiness is checked per selected model by analysis.dispatch;
        # unavailable MATLAB must not hide authorized native MuJoCo mathematics.
        record(host,'model_decision_packet',current)
        agent.system_prompt=instructions
        boundary.research_packet=deepcopy(current)
        if current.get('research',{}).get('budget',{}).get('closeout',{}).get('next_request_will_protect',protected(host)):
            permitted=closeout_operations(host)
            schema=plan_schema(permitted['research_plan'],decision_required=bool(s['spec'].get('research_decisions')))
            native[0].tool_spec={**native[0].tool_spec,'inputSchema':{'json':schema}}
            agent.tool_registry.registry.pop('experience_retrieve',None)
            agent.tool_registry.registry.pop('research_analysis',None)
            if rl_mode:
                rl_tool=next(t for t in native if t.tool_name=='research_rl')
                schema=deepcopy(rl_tool.tool_spec['inputSchema']['json'])
                schema['properties']['operation']['enum']=permitted['research_rl']
                schema['properties']['run_id']['enum']=list(s.get('rl_runs',{}))
                rl_tool.tool_spec={**rl_tool.tool_spec,'inputSchema':{'json':schema}}
            agent.tool_registry.registry.pop('research_investigate',None)
            schema=EvidenceQuery.model_json_schema()
            schema['$defs']['EvidenceRef']['properties']['artifact_id']['enum']=[r['artifact_id'] for r in readable_results(s,host)]
            native[2].tool_spec={**native[2].tool_spec,'inputSchema':{'json':schema}}
            retrieval=agent.tool_registry.registry.get('retrieve_context')
            if retrieval:
                from strands.tools.tools import normalize_tool_spec
                spec=deepcopy(normalize_tool_spec(retrieval.tool_spec))
                spec['inputSchema']['json']['properties']['reference']['enum']=feedback_context_references()
                retrieval.tool_spec=spec
            boundary.research_packet['protected_closeout_rule']='PROTECTED CLOSEOUT: status/stop existing workers, pinned published-policy evaluation, explicit evidence reads, selected passing solution confirmations and truthful STOP. No start/resume/solve/exploration.'
        if (session_handoff and state(host)['pilot'].get('session_handoff_boundary')=='request_feedback'
                and agent.messages and agent.messages[-1]['role']=='user'
                and any('toolResult' in b for b in agent.messages[-1]['content'])):
            wire=agent.model.format_request(agent.messages,agent.tool_registry.get_all_tool_specs(),agent.system_prompt)
            size=len(httpx.Request('POST',s['pilot']['provider']['base_url']+'/chat/completions',json=wire).content)
            provider=s['pilot']['provider'];context=provider['context_guard']
            review=(pause_exploration_remaining is not None and not protected(host)
                and current['research']['budget']['provider_budget']['science_capable_main_requests']<=pause_exploration_remaining)
            if review:
                from tools.research.session_handoff import request_feedback_boundary
                await request_feedback_boundary(host,agent)
                raise SupervisorReviewPause('Settled boundary before next request; supervisor budget review required')
            if handoff_before_next_request or (handoff_request_bytes is not None and size>=handoff_request_bytes) or size+provider['max_tokens']+context['framing_headroom_tokens']>context['context_limit_tokens']:
                from tools.research.session_handoff import request_feedback_boundary
                await request_feedback_boundary(host,agent)
                raise RequestBoundaryHandoff('Verified request-feedback boundary; next model send has not started')
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
        saved=dict(tool_use=event.tool_use,result=event.result)
        if event.tool_use['name']=='evidence_read' and event.tool_use['input'].get('view') in ('working_set','mathematical_capabilities','capabilities'):
            saved['source_state_identity']=digest(state(host))
        record(host,'model_original_tool_feedback',saved)
        key='native-'+event.tool_use['toolUseId']
        if host.store.lookup(host.run_id,key) is None:
            row,_=host.store.reserve(host.run_id,key,digest(event.tool_use),host.actor,{**zero(),'tool_calls':1})
            host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
                tool_id=event.tool_use['name'],tool_version='1.0.0',execution_status='completed',charged=zero()),event.result)
    agent.hooks.add_callback(BeforeModelCallEvent,before_model)
    agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
    agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    try:
        completed_invocations=0
        while state(host)['research_status']!='stopped':
            if host.store.remaining()['remaining']['model_calls']<1:
                engineering_closeout(host,'Provider request count exhausted without model STOP/selection')
                break
            try:
                result=await agent.invoke_async(INVOCATION_PROMPT)
            except Exception as exc:
                cause=exc;seen=set()
                while cause is not None and id(cause) not in seen and not isinstance(cause,RequestBoundaryHandoff):
                    seen.add(id(cause));cause=cause.__cause__
                if not isinstance(cause,RequestBoundaryHandoff):raise
                if isinstance(cause,SupervisorReviewPause):
                    record(host,'supervisor_pause',dict(boundary='request_feedback',session_id=agent._session_manager.session_id,
                        sdk_message_identity=digest(agent.messages),budgets_preserved=True,next_request_sent=False,
                        budget=decision_packet(host)['research']['budget']))
                    break
                record(host,'sdk_invocation_suspended_for_handoff',dict(session_id=agent._session_manager.session_id,
                    sdk_message_identity=digest(agent.messages),invocation_completed=False,next_request_sent=False))
                from tools.research.session_handoff import handoff
                _,agent=await handoff(host,agent,build_session,host.store.root/'framework_sessions',boundary='request_feedback')
                handoff_before_next_request=False
                agent.hooks.add_callback(BeforeModelCallEvent,before_model)
                agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
                agent.hooks.add_callback(AfterToolCallEvent,after_tool)
                continue
            record(host,'model_original_turn',dict(result=str(result),session_id=agent._session_manager.session_id,
                sdk_message_identity=digest(agent.messages)))
            if state(host)['pending'] or pending(host):
                raise ValueError('PENDING_OUTCOME_REQUIRES_LOCAL_RECOVERY')
            if state(host)['spec'].get('research_decisions'):
                await complete_reports(host,boundary.inner)
            completed_invocations+=1
            if (pause_after_completed_invocations is not None and completed_invocations>=pause_after_completed_invocations
                    and state(host)['research_status']!='stopped' and not state(host).get('success_gate')):
                await pause_completed_invocation(host,agent,completed_invocations)
                break
            if session_handoff and state(host)['research_status']!='stopped' and not state(host).get('success_gate'):
                from tools.research.session_handoff import handoff, reconcile
                previous=agent
                try:_,agent=await handoff(host,agent,build_session,host.store.root/'framework_sessions')
                except Exception as exc:
                    s=state(host)
                    if s['pending'] or pending(host) or s['pilot'].get('unconsumed_response'):raise
                    if s['pilot']['framework_session_id']!=previous._session_manager.session_id:
                        agent=await reconcile(host,build_session,host.store.root/'framework_sessions')
                    else:
                        agent=build_session(previous._session_manager.session_id)
                        if agent.messages!=previous.messages:raise ValueError('OLD_SDK_HISTORY_NOT_DURABLE') from exc
                        record(host,'session_handoff_not_committed',dict(reason=str(exc),old_session_retained=True))
                agent.hooks.add_callback(BeforeModelCallEvent,before_model)
                agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
                agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    finally:
        await boundary.aclose()


def decision_packet(host):
    from tools.research.core import packet
    from tools.research.research_context import ordered_candidates
    if state(host)['spec'].get('research_decisions'):
        from tools.research.research_context import agent_decision_brief,controller_capabilities
        from extensions.tendon_family.family_space import decision_summary
        from tools.research_tasks import task_adapter
        s=state(host);spec=s['spec']
        research=agent_decision_brief(host)
        controller=controller_capabilities(host)
        controller.pop('parameter_schema')
        controller['parameter_schema_query']=dict(reference=research['evidence_access']['reference'],
            view='working_set',pointer='/controller_capabilities/parameter_schema')
        return dict(research=research,implementation=s['freeze'],study_id=host.run_id,
            evaluation_profile={k:s['profile'][k] for k in ('identity','version')},
            implementation_migration=s.get('core_repairs',[])[-1] if s.get('core_repairs') else None,
            controller_capabilities=controller,
            candidates=ordered_candidates(host,s)[-spec.get('research_decisions',{}).get('context_limits',{}).get('candidates',3):],
            candidate_profile_bindings=[dict(candidate=r,profile_identity=host.store.artifact(r)['profile_identity'],
                executable_under_current_profile=host.store.artifact(r)['profile_identity']==s['profile']['identity'])
                for r in ordered_candidates(host,s)[-spec.get('research_decisions',{}).get('context_limits',{}).get('candidates',3):]],
            family_space=decision_summary(spec['family_space'],s['family_space_reference'],
                dict(actions=spec['allowed_plan_actions'],capabilities=spec['capabilities'])) if spec.get('start_mode')=='family_space' else None,
            source_relative_design=dict(reference_parameters=spec['reference_parameters'],allowed_parameters=spec['allowed_parameters'],
                length_constraint=spec.get('length_constraint')) if spec.get('start_mode')!='family_space' else None,
            analysis_protocol=spec['analysis_protocol'],
            guidance='Tool results acknowledge execution and saved references; use latest_reports L1 for scientific decisions. Signed score direction, comparison scope and optimality come from structured facts. Use exact evidence refs and a typed decision in every research_plan. evidence_read and research_investigate permit drill-down. Reporter interpretations are hypotheses, never authoritative facts or action choices. Choose the next research method freely. New designs need explicit control adaptation. Do not infer global feasibility/infeasibility. Stop at the first complete task pass; for a multi-condition Study this means every frozen condition on the identical structure. Publicly read each evaluation and select the complete result set. Retrieve the exact stop_result_index before STOP; cite every new result.')
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
