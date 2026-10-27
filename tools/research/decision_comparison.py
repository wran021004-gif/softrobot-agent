"""Offline matched Provider-only decision preparation; never sends or executes tools.

A separate Store is not a shared P2 budget.  The live comparison remains
blocked until an existing atomic authority can charge both projects without
mutating the original Study or spending its protected requests.
"""
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
