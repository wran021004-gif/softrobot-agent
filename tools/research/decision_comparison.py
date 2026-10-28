"""Matched Provider-only decisions, with a shared-ledger, protected one-shot probe."""
from copy import deepcopy
import json
from jsonschema import Draft202012Validator
from tools.state_io import digest
from tools.research.agent import received
from tools.research.contracts import Plan,AnalysisRequest,EvidenceQuery,ExperienceQuery,PLAN_RESEARCH_INTENTS

VERSION='matched_thinking_decision_v1'


def ids(value):
    if isinstance(value,dict):
        out={value['artifact_id']} if isinstance(value.get('artifact_id'),str) else set()
        return out.union(*(ids(v) for v in value.values()))
    if isinstance(value,list):return set().union(*(ids(v) for v in value))
    return set()


def freeze_original(host,request_id):
    """Read exact saved input/receipt and decision-time packet; no source writes."""
    events=host.store.events(host.run_id)
    sends=[e for e in events if e['kind']=='r3_request' and e['request_id']==request_id]
    if len(sends)!=1:raise ValueError('EXACT_ORIGINAL_REQUEST_REQUIRED')
    send=sends[0];meta=host.store.artifact(send['outputs'][0]);wire=host.store.artifact(meta['request'])
    row=host.store.lookup(host.run_id,request_id);rec=received(host,request_id)
    if not row or not row['receipt'] or digest(wire)!=row['request_hash'] or not rec or rec['http_status']!=200:
        raise ValueError('ORIGINAL_SETTLED_REQUEST_AND_RESPONSE_REQUIRED')
    receipt=json.loads(row['receipt']);stored=host.store.artifact(receipt['output'])
    if receipt['charged']['model_calls']!=1 or stored['body']!=rec['body'] or stored['usage']!=rec['usage']:
        raise ValueError('ORIGINAL_PROVIDER_RECEIPT_MISMATCH')
    body=json.loads(host.store.artifact(rec['body'],raw=True))
    if len(body.get('choices',[]))!=1 or body['choices'][0].get('finish_reason') not in ('tool_calls','stop'):
        raise ValueError('COMPLETE_BASELINE_PROVIDER_RESPONSE_REQUIRED')
    if wire.get('thinking')!={'type':'enabled'} or wire.get('reasoning_effort')!='high':
        raise ValueError('MATCHED_HIGH_THINKING_BASELINE_REQUIRED')
    if any(m.get('role') not in ('system','user') or m.get('reasoning_content') or m.get('tool_calls') for m in wire['messages']):
        raise ValueError('CLEAN_NO_HISTORICAL_REASONING_OR_TOOL_FIELDS_REQUIRED')
    last=wire['messages'][-1].get('content','')
    if not isinstance(last,str) or not last.startswith('CURRENT_RESEARCH_PACKET\n'):
        raise ValueError('EXACT_ORIGINAL_DECISION_PACKET_REQUIRED')
    packet=json.loads(last.split('\n',1)[1])
    recorded=[e for e in events if e['kind']=='model_decision_packet' and e['sequence']<send['sequence']]
    if not recorded or host.store.artifact(recorded[-1]['outputs'][0])!=packet:
        raise ValueError('ORIGINAL_DECISION_PACKET_MISMATCH')
    if packet.get('study_id')!=host.run_id or packet['research']['candidate_status']['control_sources_initialized']!=0:
        raise ValueError('ORIGINAL_PRE_CONTROL_DECISION_STATE_REQUIRED')
    return dict(version=VERSION,request_id=request_id,request_reference=meta['request'],response_reference=rec['body'],
        original_request_identity=digest(wire),original_schema_identity=digest(wire.get('tools',[])),
        original_packet_identity=digest(packet),receipt_execution_id=row['execution_id'],
        original_usage=rec['usage'],original_elapsed_s=rec['elapsed_s'],
        original_finish_reason=body['choices'][0]['finish_reason'],wire=wire,packet=packet,response=body)


def nonthinking_wire(original):
    """Only change the mode and remove its conflicting thinking-effort field."""
    if original.get('thinking')!={'type':'enabled'} or original.get('reasoning_effort')!='high':
        raise ValueError('HIGH_THINKING_BASELINE_REQUIRED')
    result=deepcopy(original);result['thinking']={'type':'disabled'};result.pop('reasoning_effort')
    if {k:v for k,v in result.items() if k not in ('thinking','reasoning_effort')} != {k:v for k,v in original.items() if k not in ('thinking','reasoning_effort')}:
        raise ValueError('UNMATCHED_NONTHINKING_REQUEST')
    return result


def comparison_budget(source, *, aggregate_used, aggregate_limit=8, probe_limit=1):
    """Calculate capacity, but reject separate ledgers without shared authority."""
    ledger=source.store.remaining();s=source.store.session(source.run_id)['state']
    protected=s['spec']['budgets']['protected_provider_requests']
    remaining=ledger['remaining']['model_calls']
    arithmetic=(probe_limit==1 and remaining-protected>=1 and aggregate_used+probe_limit+protected<=aggregate_limit)
    return dict(aggregate_used=aggregate_used,aggregate_limit=aggregate_limit,comparison_cap=probe_limit,
        original_remaining=remaining,original_protected=protected,arithmetic_fits=arithmetic,
        separate_project_ledgers_share_atomic_reservation=False,admitted=False,
        reason='INDEPENDENT_STORE_HAS_NO_SHARED_ATOMIC_P2_BUDGET_AUTHORITY',
        required='An existing shared authority must atomically debit the cumulative P2 allowance while preserving the source Store and its protected requests.')


def validate_proposals(wire,packet,body):
    """Schema/Pydantic and visible-reference checks only; no scientific dispatch."""
    tools={v['function']['name']:v['function'] for v in wire.get('tools',[])}
    from tools.research.reporter import InvestigationRequest
    contracts={'research_plan':Plan,'research_analysis':AnalysisRequest,'evidence_read':EvidenceQuery,
        'experience_retrieve':ExperienceQuery,'research_investigate':InvestigationRequest}
    known=ids(packet);out=[]
    choices=body.get('choices',[])
    if len(choices)!=1:return dict(status='invalid_response',proposals=[],scientific_execution='not_dispatched')
    choice=choices[0]
    if choice.get('finish_reason') not in ('tool_calls','stop'):
        return dict(status='incomplete',finish_reason=choice.get('finish_reason'),proposals=[],scientific_execution='not_dispatched')
    for call in (choice.get('message') or {}).get('tool_calls',[]):
        name=call.get('function',{}).get('name');row=dict(tool=name,scientific_execution='not_dispatched',full_scientific_admission='not_tested')
        try:
            if name not in tools:raise ValueError('TOOL_NOT_ADVERTISED')
            data=json.loads(call['function']['arguments'])
            errors=list(Draft202012Validator(tools[name]['parameters']).iter_errors(data))
            if errors:raise ValueError('SENT_SCHEMA_REJECTED: '+errors[0].message)
            if name not in contracts:
                row.update(status='schema_only',reason='NO_READ_ONLY_PYDANTIC_CHECK_FOR_TOOL');out.append(row);continue
            parsed=contracts[name].model_validate(data)
            refs=ids(data);missing=sorted(refs-known)
            if missing:raise ValueError('REFERENCE_NOT_VISIBLE_IN_FROZEN_PACKET: '+','.join(missing))
            if name=='research_plan':
                if parsed.action not in packet['research']['actions']:raise ValueError('ACTION_NOT_AVAILABLE_IN_FROZEN_PACKET')
                if not parsed.decision or parsed.decision.research_intent!=PLAN_RESEARCH_INTENTS[parsed.action]:raise ValueError('ACTION_INTENT_MISMATCH')
                row.update(action=parsed.action,selected_method=parsed.decision.selected_method,
                    candidate=(parsed.decision.selected_candidate.model_dump(mode='json') if parsed.decision.selected_candidate else None))
            row.update(status='contract_and_visible_references_valid',reference_count=len(refs))
        except (ValueError,TypeError,KeyError) as exc:row.update(status='rejected',reason=str(exc)[:500])
        out.append(row)
    return dict(status='complete',finish_reason=choice.get('finish_reason'),proposals=out,scientific_execution='not_dispatched',
        limitation='Read-only contract/visible-reference checks do not establish full scientific admission, optimization or task acceptance.')


class ProtectedProbeStore:
    """Add a probe-specific check inside the existing Store reservation transaction."""
    def __init__(self, store, parent, child, parent_state_identity):
        self.store,self.parent,self.child,self.parent_state_identity=store,parent,child,parent_state_identity

    def __getattr__(self,name):
        return getattr(self.store,name)

    def reserve(self,run_id,request_id,request_hash,caller,cost,**kwargs):
        previous=kwargs.pop('guard',None)
        def guard(db):
            if previous:previous(db)
            parent=self.store.session(self.parent,db)['state']
            remaining=self.store.remaining(db=db)
            parent_remaining=self.store.remaining(self.parent,db)
            protected=parent['spec']['budgets']['protected_provider_requests']
            if run_id!=self.child or cost['model_calls']!=1 or any(cost[k] for k in ('tool_calls','backend_solves','worker_calls')):
                raise ValueError('PROBE_PROVIDER_ONLY_GRANT_REQUIRED')
            if digest(parent)!=self.parent_state_identity or parent.get('pending') or parent.get('pilot',{}).get('unconsumed_response'):
                raise ValueError('SOURCE_STATE_CHANGED_OR_BUSY')
            if protected!=2 or remaining['used']['model_calls']!=5 or remaining['limit']['model_calls']!=8:
                raise ValueError('ORIGINAL_P2_BUDGET_CHANGED')
            if min(remaining['remaining']['model_calls'],parent_remaining['remaining']['model_calls'])<=protected:
                raise ValueError('PROTECTED_PROVIDER_CAPACITY')
            if db.execute("SELECT 1 FROM calls WHERE status IN ('running','unknown') LIMIT 1").fetchone():
                raise ValueError('UNCONFIRMED_EXECUTION_BLOCKS_PROBE')
            if db.execute('SELECT 1 FROM calls WHERE run_id=? LIMIT 1',(self.child,)).fetchone():
                raise ValueError('PROBE_ALREADY_ATTEMPTED_NO_RETRY')
        return self.store.reserve(run_id,request_id,request_hash,caller,cost,guard=guard,**kwargs)


def prepare_shared_probe(source, baseline, child_id):
    """Create an explicitly authorized provider-only child in the original ledger."""
    from types import SimpleNamespace
    from tools.research.agent import record
    from tools.research.state import update
    state=source.store.session(source.run_id)['state']
    if baseline['original_request_identity']!=digest(baseline['wire']):raise ValueError('BASELINE_IDENTITY_MISMATCH')
    if state.get('pending') or state.get('pilot',{}).get('unconsumed_response'):raise ValueError('SOURCE_BUSY')
    ledger=source.store.remaining()
    if ledger['limit']['model_calls']!=8 or ledger['used']['model_calls']!=5 or ledger['remaining']['model_calls']!=3 or state['spec']['budgets']['protected_provider_requests']!=2:
        raise ValueError('ORIGINAL_P2_BUDGET_CHANGED')
    budget=dict(tool_calls=0,model_calls=1,backend_solves=0,worker_calls=0,wall_s=None)
    snapshot=dict(input=dict(run_id=child_id,policy=dict(budget=budget)),parent_run_id=source.run_id,
        purpose='authorized matched provider-only decision observation')
    source.store.create_session(snapshot)  # Duplicate child ID always fails closed.
    provider=deepcopy(state['pilot']['provider']);provider.update(thinking='disabled',reasoning_effort=None)
    child=SimpleNamespace(store=source.store,run_id=child_id)
    update(child,pilot=dict(provider=provider,live_model_requests=0),probe=dict(
        baseline_request=baseline['request_id'],baseline_identity=baseline['original_request_identity'],
        paired_identity=digest(nonthinking_wire(baseline['wire'])),parent_state_identity=digest(state)))
    record(child,'provider_only_authorization',dict(user_approved=True,provider_requests=1,protected_requests=2,
        scientific_executions=0,automatic_retries=0,parent_run_id=source.run_id,
        baseline_request=baseline['request_id'],paired_identity=digest(nonthinking_wire(baseline['wire']))))
    return child


async def execute_shared_probe(source, child, baseline, api_key, *, transport=None):
    """Send once, archive the real receipt, inspect only; never dispatch tool calls."""
    import httpx
    from types import SimpleNamespace
    from tools.platform_store import plain
    from tools.research.agent import LiveBoundary,received,record
    probe=child.store.session(child.run_id)['state']['probe']
    wire=nonthinking_wire(baseline['wire'])
    if digest(wire)!=probe['paired_identity'] or baseline['original_request_identity']!=probe['baseline_identity']:
        raise ValueError('PROBE_FROZEN_IDENTITY_MISMATCH')
    with child.store.connect(True) as db:
        if db.execute('SELECT 1 FROM calls WHERE run_id=? LIMIT 1',(child.run_id,)).fetchone():
            raise ValueError('PROBE_ALREADY_ATTEMPTED_NO_RETRY')
    body=json.dumps(wire,ensure_ascii=False,separators=(',',':')).encode('utf8')
    if not api_key or api_key.encode() in body or b'credentials_reference' in body:
        raise ValueError('PRIVATE_CREDENTIAL_IN_REQUEST_OR_MISSING')
    wrapped=SimpleNamespace(store=ProtectedProbeStore(child.store,source.run_id,child.run_id,probe['parent_state_identity']),run_id=child.run_id)
    boundary=LiveBoundary(wrapped,transport=transport,allow_truncated_response=True,max_model_calls=6)
    boundary.purpose='matched_thinking_off_provider_only'
    provider=child.store.session(child.run_id)['state']['pilot']['provider']
    request=httpx.Request('POST',provider['base_url'].rstrip('/')+'/chat/completions',content=body,
        headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},
        extensions={'timeout':dict(connect=30,read=600,write=30,pool=30)})
    try:
        response=await boundary.handle_async_request(request)
        reception=received(child,boundary.last_request)
        result=dict(version=VERSION,baseline_request=baseline['request_id'],request_id=boundary.last_request,
            baseline_identity=baseline['original_request_identity'],paired_identity=digest(wire),
            request_bytes=len(body),http_status=response.status_code,usage=reception['usage'],elapsed_s=reception['elapsed_s'],
            response_reference=reception['body'],scientific_execution='not_dispatched')
        try:
            decoded=json.loads(response.content)
            result['validation']=validate_proposals(wire,baseline['packet'],decoded)
        except (ValueError,TypeError,AttributeError):
            result['validation']=dict(status='invalid_response',scientific_execution='not_dispatched')
        result['baseline_validation']=validate_proposals(baseline['wire'],baseline['packet'],baseline['response'])
        result['ledger_after']=child.store.remaining()
        record(child,'provider_only_comparison',result,status='observed')
        if response.is_success and result['validation']['status']=='complete':boundary.consumed()
        return result
    finally:
        await boundary.aclose()
