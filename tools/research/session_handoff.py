"""Coordinate SDK files and the existing Store; no decisions or scientific launches."""
from copy import deepcopy
import json
import os
from pathlib import Path
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.state import state

INVOCATION_PROMPT='Use actual saved evidence, choose your next research action or STOP, then consume feedback and decide freely.'

def state_identity(value):
    value=deepcopy(value);value['pilot'].pop('handoff_preparation',None)
    return digest(value)


def initial_messages(study_id):
    return [dict(role='user',content=[dict(text=(
        'Research Session prepared and identity-bound to the saved handoff preparation. '
        'No prior conversation copied. The next model request supplies the authoritative '
        'current state in CURRENT_RESEARCH_PACKET. Full history and original scientific '
        'evidence remain queryable from Store. Study: '+study_id))])]


def selected_evidence_facts(parsed, query, limit):
    """Keep bounded selected facts through handoff; full evidence stays in L2."""
    summary=query.get('view')=='summary' and isinstance(parsed,dict) and 'value' in parsed
    value=parsed['value'] if summary else parsed
    if not isinstance(value,dict):return None
    facts=dict(selected_value={},available_keys=list(value),omitted_keys=list(value),
        scope='Partial selected evidence; omitted fields remain at the original query. '
            +('Values retain the original deterministic preview semantics.' if summary else 'Retained fields are exact; no full-read credit from this projection.'))
    def size(item):return len(json.dumps(item).encode())
    if size(facts)>limit:return None
    # Scalars cannot disappear merely because a sibling array is large.
    keys=sorted(value,key=lambda k:isinstance(value[k],(dict,list)))
    for key in keys:
        candidate=deepcopy(facts)
        candidate['selected_value'][key]=value[key]
        candidate['omitted_keys'].remove(key)
        if size(candidate)<=limit:facts=candidate
    return facts


def feedback_delivery(host, tool_ids, *, compact=False):
    """Project the verified last tool round, without synthesizing SDK messages."""
    from tools.research.research_context import compact_evidence
    rows=[];remaining=6000 if compact else 16000
    originals={}
    for event in host.store.events(host.run_id):
        if event['kind']=='model_original_tool_feedback':
            value=host.store.artifact(event['outputs'][0])
            originals[value['tool_use']['toolUseId']]=(event['outputs'][0],value)
    for key in tool_ids:
        reference,value=originals[key];result=value['result']
        row=dict(tool_id=key,tool=value['tool_use']['name'],query=value['tool_use']['input'],
            status=result['status'],feedback_reference=reference,
            original_result_query=dict(reference=reference,view='full',pointer='/result'))
        if compact and len(json.dumps(row['query']).encode())>1000:
            query=row.pop('query')
            row['query_summary']={k:query[k] for k in ('action','operation','model_source','operating_point') if k in query}
            row['original_input_query']=dict(reference=reference,view='full',pointer='/tool_use/input')
        if compact and len(json.dumps(rows+[row]).encode())>10000:
            break
        size=len(json.dumps(result,separators=(',',':')).encode())
        query=value['tool_use']['input']
        default_view='summary' if state(host)['spec'].get('research_decisions',{}).get('context_limits') else 'full'
        whole_read=(compact and value['tool_use']['name']=='evidence_read' and result['status']=='success'
            and query.get('view',default_view)=='full' and not query.get('pointer'))
        # A deliberate whole-result read is the formal SELECT interface. It is
        # delivered exactly even when large; the unchanged hard context guard
        # still applies to the actual complete request. Ordinary reads stay small.
        if whole_read or size<=min(2000 if compact else 6000,remaining):
            row.update(delivery='exact_feedback',result=result);remaining-=size
        else:
            try:parsed=json.loads(''.join(b.get('text','') for b in result['content']))
            except ValueError:parsed={}
            facts=compact_evidence(parsed,reference)['value']
            if len(json.dumps(facts).encode())>min(3000,remaining):
                def important(node):
                    if not isinstance(node,dict):return dict(value_type=type(node).__name__)
                    keep=('status','reference','candidate','source','source_kind','evaluation_reference',
                        'operation','task_acceptance','task_gap','error_code','field','expected')
                    return {**{k:node[k] for k in keep if k in node},
                        **(dict(acceptance_metrics=node['original_acceptance'].get('metrics')) if node.get('original_acceptance') else {})}
                facts=dict(total=len(parsed),recent=[important(v) for v in parsed[-3:]]) if isinstance(parsed,list) else important(parsed)
            if value['tool_use']['name']=='evidence_read' and result['status']=='success':
                selected=selected_evidence_facts(parsed,value['tool_use']['input'],min(3000,remaining))
                if selected is not None:facts=selected
            if result['status']=='error' and isinstance(parsed,dict):
                # Error reason/expectation must survive beside the exact input
                # already in row.query, even when navigation details are large.
                facts={k:parsed[k] for k in ('status','error_code','field','reason','expected',
                    'worker_started','scientific_execution_started','charged_method_counts','full_error_reference') if k in parsed}
            if (value['tool_use']['name']=='evidence_read' and
                    value['tool_use']['input'].get('view')=='mathematical_capabilities' and isinstance(parsed,dict)):
                for field in ('request_template','execution_limits','required_parameters','measured_control_initialization'):
                    if field in parsed and len(json.dumps({**facts,field:parsed[field]}).encode())<=min(3000,remaining):
                        facts[field]=parsed[field]
            row.update(delivery='summary_only',facts=facts);remaining-=len(json.dumps(facts).encode())
        rows.append(row)
    return dict(version='pending_feedback_delivery_v1',items=rows,
        **(dict(total_tools=len(tool_ids),omitted_tools=len(tool_ids)-len(rows)) if compact else {}),
        scope='Deterministic Store projection of settled tools; delivery does not establish model understanding. Summary grants no complete-read credit.')


def recent_round(host):
    """One response and its settled feedback, grouped by durable request identity."""
    from tools.research.config import conversation_policy
    if not conversation_policy(state(host)['spec']):return None
    events=host.store.events(host.run_id);feedback=[];request=None;settled=None
    for event in events:
        if event['kind']=='r3_request':
            meta=host.store.artifact(event['outputs'][0])
            if meta.get('purpose')=='conversation':request=event;feedback=[]
        elif event['kind']=='model_original_tool_feedback' and request:
            feedback.append(host.store.artifact(event['outputs'][0])['tool_use']['toolUseId'])
            settled=(request,list(feedback))
    if settled is None:return None
    request,feedback=settled
    return dict(version='recent_research_round_v1',request_id=request['request_id'],
        request_reference=request['outputs'][0],feedback=feedback_delivery(host,feedback,compact=True),
        scope='Latest settled response/tool unit, not a fixed SDK message count. Intent is not a scientific result.')


def rotation_ready(host, messages):
    """Defer automatic rotation for live work; retain identity/pairing failures."""
    with host.store.connect(True) as db:
        try:settled_boundary(state(host),db,messages)
        except ValueError as exc:
            if str(exc) in ('PENDING_FEEDBACK_OR_EXECUTION','UNSETTLED_OUTCOME','WORKER_RECOVERY_REQUIRED','SELECT_REQUIRED','STOPPED'):
                return False
            raise
    return True


def pending_feedback_delivery(host):
    """The existing preparation owns delivery until a confirmed saved request."""
    ref=state(host)['pilot'].get('handoff')
    if not ref:return None
    delivery=host.store.artifact(ref).get('pending_feedback_delivery')
    if not delivery:return None
    events=host.store.events(host.run_id)
    confirmed={e['request_id'] for e in events if e['kind']=='r3_response'
        and 200<=host.store.artifact(e['outputs'][0]).get('http_status',0)<300}
    for event in events:
        if event['kind']!='r3_request' or event['request_id'] not in confirmed:continue
        wire=host.store.artifact(host.store.artifact(event['outputs'][0])['request'])
        tail=wire['messages'][-1].get('content')
        if isinstance(tail,str) and tail.startswith('CURRENT_RESEARCH_PACKET\n'):
            packet=json.loads(tail.split('\n',1)[1])
            research=packet.get('research',{})
            shown=research.get('pending_feedback_delivery') or (research.get('research_state') or {}).get('pending_feedback')
            if shown==delivery:return None
    return delivery


def unmatched(messages):
    outstanding={};seen=set()
    for message in messages:
        if message['role']=='assistant' and outstanding:raise ValueError('MISSING_TOOL_RESULT')
        for block in message['content']:
            if 'toolUse' in block:
                if message['role']!='assistant':raise ValueError('INVALID_TOOL_USE_ROLE')
                use=block['toolUse'];key=use['toolUseId']
                if key in seen:raise ValueError('DUPLICATE_TOOL_ID')
                seen.add(key);outstanding[key]=use
            if 'toolResult' in block:
                if message['role']!='user':raise ValueError('INVALID_TOOL_RESULT_ROLE')
                key=block['toolResult']['toolUseId']
                if key not in outstanding:raise ValueError('UNPAIRED_TOOL_RESULT')
                outstanding.pop(key)
    return outstanding


def schemas(agent):
    from strands.tools.tools import normalize_tool_spec
    return {name:deepcopy(normalize_tool_spec(tool.tool_spec)) for name,tool in sorted(agent.tool_registry.registry.items())}


def settled_boundary(current,db,messages):
    if current['research_status']=='stopped':raise ValueError('STOPPED')
    if current.get('success_gate'):raise ValueError('SELECT_REQUIRED')
    if current.get('pending') or current['pilot'].get('unconsumed_response'):raise ValueError('PENDING_FEEDBACK_OR_EXECUTION')
    if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:raise ValueError('UNSETTLED_OUTCOME')
    if any(e.get('active_reservation') or e.get('status',{}).get('worker_alive',True)
            for e in current.get('rl_runs',{}).values()):raise ValueError('WORKER_RECOVERY_REQUIRED')
    if unmatched(messages):raise ValueError('MISSING_TOOL_RESULT')


def safe_boundary(host,current,db,messages,*,boundary='completed_invocation'):
    settled_boundary(current,db,messages)
    if boundary=='request_feedback':
        anchors=[host.store.artifact(e['outputs'][0]) for e in host.store.events(host.run_id)
            if e['kind']=='request_feedback_boundary']
        if not anchors or anchors[-1]['session_id']!=current['pilot']['framework_session_id']:
            raise ValueError('VERIFIED_REQUEST_FEEDBACK_BOUNDARY_REQUIRED')
        if anchors[-1]['sdk_message_identity']!=digest(messages):raise ValueError('REQUEST_BOUNDARY_HISTORY_CHANGED')
        return
    if boundary!='completed_invocation':raise ValueError('UNKNOWN_HANDOFF_BOUNDARY')
    if not messages or messages[-1]['role']!='assistant':raise ValueError('OLD_FEEDBACK_MUST_BE_CONSUMED_FIRST')
    turns=[host.store.artifact(e['outputs'][0]) for e in host.store.events(host.run_id) if e['kind']=='model_original_turn']
    complete=next((t for t in reversed(turns) if t.get('session_id')==current['pilot']['framework_session_id']),None)
    if current['pilot'].get('session_handoff_live_admitted') and complete is None:raise ValueError('DURABLE_COMPLETED_INVOCATION_REQUIRED')
    if complete and complete['sdk_message_identity']!=digest(messages):raise ValueError('OLD_SDK_HISTORY_NOT_DURABLE')


async def request_feedback_boundary(host,agent):
    """Anchor a real response and its paired feedback; no invocation completion."""
    from tools.research.agent import DeepSeekModel, received, record
    from tools.research.reporter import current_reports
    s=state(host);messages=agent.messages
    with host.store.connect(True) as db:settled_boundary(s,db,messages)
    if (not messages or messages[-1]['role']!='user'
            or not any('toolResult' in b for b in messages[-1]['content'])):
        raise ValueError('PAIRED_TOOL_FEEDBACK_REQUEST_BOUNDARY_REQUIRED')
    if any(v['interpretation_status']=='deferred' for _,v in current_reports(host)):
        raise ValueError('REPORTER_DELIVERY_REQUIRED_BEFORE_REQUEST_HANDOFF')
    events=host.store.events(host.run_id)
    main=[e for e in events if e['kind']=='r3_request'
        and host.store.artifact(e['outputs'][0])['purpose']=='conversation']
    if not main:raise ValueError('REAL_MAIN_RESPONSE_REQUIRED')
    event=main[-1];reception=received(host,event['request_id']);row=host.store.lookup(host.run_id,event['request_id'])
    if not reception or reception['http_status']!=200 or not row['receipt']:
        raise ValueError('REAL_SETTLED_MAIN_RESPONSE_REQUIRED')
    meta=host.store.artifact(event['outputs'][0]);wire=host.store.artifact(meta['request'])
    body=json.loads(host.store.artifact(reception['body'],raw=True));choice=body['choices'][0]
    if len(body['choices'])!=1 or choice['finish_reason']!='tool_calls':raise ValueError('COMPLETE_NATIVE_TOOL_RESPONSE_REQUIRED')
    index=max(i for i,m in enumerate(messages) if m['role']=='assistant')
    prefix=wire['messages']
    if prefix[-1]['role']=='user' and str(prefix[-1].get('content','')).startswith('CURRENT_RESEARCH_PACKET\n'):prefix=prefix[:-1]
    if DeepSeekModel.format_request_messages(messages[:index],wire['messages'][0]['content'])!=prefix:
        raise ValueError('REQUEST_BOUNDARY_ORIGINAL_WIRE_PREFIX_MISMATCH')
    def assistant(value):
        content=value.get('content')
        # Strands encodes Provider string content as OpenAI text-part blocks.
        # Normalize that representation only; preserve every text character.
        if isinstance(content,str):content=[dict(type='text',text=content)] if content else None
        return dict(content=content or None,reasoning=value.get('reasoning_content',''),
            tools=[dict(id=t['id'],name=t['function']['name'],arguments=json.loads(t['function']['arguments']))
                for t in value.get('tool_calls',[])])
    actual=DeepSeekModel.format_request_messages([messages[index]])
    if len(actual)!=1 or assistant(actual[0])!=assistant(choice['message']):
        raise ValueError('REQUEST_BOUNDARY_ORIGINAL_RESPONSE_MISMATCH')
    uses={b['toolUse']['toolUseId']:b['toolUse'] for b in messages[index]['content'] if 'toolUse' in b}
    originals={host.store.artifact(e['outputs'][0])['tool_use']['toolUseId']:host.store.artifact(e['outputs'][0])
        for e in events if e['kind']=='model_original_tool_feedback'}
    results={b['toolResult']['toolUseId']:b['toolResult'] for m in messages[index+1:] for b in m['content'] if 'toolResult' in b}
    if set(uses)!=set(results):raise ValueError('EXACT_REQUEST_FEEDBACK_IDS_REQUIRED')
    for key,use in uses.items():
        original=originals.get(key)
        if not original or original['tool_use']!=use or original['result']['status']!=results[key]['status']:
            raise ValueError('ORIGINAL_REQUEST_FEEDBACK_REQUIRED')
        if original['result']!=results[key]:
            stash=getattr(agent.context_manager,'_stash',None)
            if stash is None:raise ValueError('SDK_OFFLOAD_ORIGINAL_REQUIRED')
            for i,block in enumerate(original['result']['content']):
                if await stash.retrieve(key+'_'+str(i))!=block:raise ValueError('SDK_OFFLOAD_ORIGINAL_MISMATCH')
    await agent._session_manager.save_snapshot(agent,is_latest=True)
    proof=dict(version='request_feedback_boundary_v1',session_id=s['pilot']['framework_session_id'],
        sdk_message_identity=digest(messages),last_model_request=event['request_id'],
        original_wire=meta['request'],original_response=reception['body'],tool_ids=sorted(uses),
        receipts_settled=True,reporter_delivered=True,invocation_completed=False)
    return record(host,'request_feedback_boundary',proof)


def snapshot_files(directory,session_id,*,flush=False):
    from tools.research.agent import session_storage_path
    root=Path(session_storage_path(Path(directory).resolve()))/'session'/session_id
    files=sorted(root.rglob('*.json'));result={}
    if not any(p.name=='snapshot_latest.json' for p in files):raise ValueError('SDK_SNAPSHOT_MISSING')
    for path in files:
        with path.open('r+b' if flush else 'rb') as stream:
            body=stream.read()
            if flush:os.fsync(stream.fileno())
        result[str(path.relative_to(root))]=digest(body.hex())
    return result


async def inspect_confirmed_incomplete(host,agent,directory):
    """Verify a settled truncated main response and its exact prior SDK feedback.

    This read-only assessment never disposes a response, mutates messages, or
    authorizes a worker. Unknown outcomes and any post-send action fail closed.
    """
    from tools.research.agent import DeepSeekModel,received,pending
    s=state(host);key=s['pilot'].get('unconsumed_response')
    if not key:raise ValueError('CONFIRMED_INCOMPLETE_RESPONSE_REQUIRED')
    if (s.get('pending') or pending(host) or any(e.get('active_reservation') or e.get('status',{}).get('worker_alive',True)
            for e in s.get('rl_runs',{}).values())):raise ValueError('UNKNOWN_PROVIDER_OR_SCIENTIFIC_WORKER')
    if s['research_status']=='stopped' or s.get('success_gate'):raise ValueError('OPEN_NONPASS_STUDY_REQUIRED')
    if agent._session_manager.session_id!=s['pilot']['framework_session_id']:raise ValueError('OLD_SESSION_ID_MISMATCH')
    if unmatched(agent.messages):raise ValueError('MISSING_PRIOR_TOOL_FEEDBACK')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE run_id=? AND receipt IS NULL',(host.run_id,)).fetchone()[0]:
            raise ValueError('UNSETTLED_OUTCOME')
    events=host.store.events(host.run_id)
    sends=[e for e in events if e['kind']=='r3_request' and e['request_id']==key]
    if len(sends)!=1:raise ValueError('EXACT_ORIGINAL_PROVIDER_REQUEST_REQUIRED')
    send=sends[0];meta=host.store.artifact(send['outputs'][0]);row=host.store.lookup(host.run_id,key)
    if meta['purpose']!='conversation' or not row or not row['receipt']:raise ValueError('SETTLED_MAIN_PROVIDER_RECEIPT_REQUIRED')
    receipt=json.loads(row['receipt']);request=host.store.artifact(meta['request']);reception=received(host,key)
    if (receipt['request_id']!=key or receipt['tool_id']!='model.deepseek' or
            receipt['execution_status']!='completed' or receipt['charged']['model_calls']!=1 or
            digest(request)!=row['request_hash'] or not reception or reception['http_status']!=200):
        raise ValueError('ORIGINAL_REQUEST_RESPONSE_RECEIPT_MISMATCH')
    body=json.loads(host.store.artifact(reception['body'],raw=True));choices=body.get('choices',[])
    if len(choices)!=1 or choices[0].get('finish_reason')!='length':
        raise ValueError('EXPLICIT_LENGTH_TRUNCATION_REQUIRED')
    if reception.get('usage')!=body.get('usage') or reception.get('finish_reasons')!=['length']:
        raise ValueError('ORIGINAL_RESPONSE_METADATA_MISMATCH')
    wire=request['messages'];prefix=wire[:-1] if (wire and wire[-1].get('role')=='user' and
        isinstance(wire[-1].get('content'),str) and wire[-1]['content'].startswith('CURRENT_RESEARCH_PACKET\n')) else wire
    if not wire or wire[0].get('role')!='system' or DeepSeekModel.format_request_messages(agent.messages,wire[0]['content'])!=prefix:
        raise ValueError('SAVED_REQUEST_AND_SDK_HISTORY_MISMATCH')
    packets=[e for e in events if e['kind']=='model_decision_packet' and e['sequence']<send['sequence']]
    if not packets or prefix is wire:raise ValueError('ORIGINAL_DECISION_PACKET_REQUIRED')
    packet=host.store.artifact(packets[-1]['outputs'][0])
    if json.loads(wire[-1]['content'].split('\n',1)[1])!=packet:raise ValueError('ORIGINAL_DECISION_PACKET_MISMATCH')
    original_freeze=packet.get('implementation')
    if not isinstance(original_freeze,str):raise ValueError('ORIGINAL_IMPLEMENTATION_IDENTITY_REQUIRED')
    migrated=original_freeze
    for repair in s.get('core_repairs',[]):
        if repair['previous_commit']==migrated:
            if repair.get('material_behavior_change'):raise ValueError('SCIENCE_CHANGING_MIGRATION_NOT_ADMITTED')
            migrated=repair['commit']
    if migrated!=s['freeze']:raise ValueError('IMPLEMENTATION_MIGRATION_CHAIN_REQUIRED')
    if not agent.messages or agent.messages[-1]['role']!='user':raise ValueError('PRIOR_TOOL_FEEDBACK_BOUNDARY_REQUIRED')
    uses={b['toolUse']['toolUseId']:b['toolUse'] for m in agent.messages for b in m['content'] if 'toolUse' in b}
    results={b['toolResult']['toolUseId']:b['toolResult'] for m in agent.messages for b in m['content'] if 'toolResult' in b}
    originals={host.store.artifact(e['outputs'][0])['tool_use']['toolUseId']:host.store.artifact(e['outputs'][0])
        for e in events if e['kind']=='model_original_tool_feedback' and e['sequence']<send['sequence']}
    if not uses or set(uses)!=set(results):raise ValueError('PRIOR_TOOL_FEEDBACK_PAIR_REQUIRED')
    for tool_id,use in uses.items():
        original=originals.get(tool_id)
        if not original or original['tool_use']!=use or original['result']['status']!=results[tool_id]['status']:
            raise ValueError('PRIOR_TOOL_FEEDBACK_IDENTITY_MISMATCH')
        if original['result']!=results[tool_id]:
            stash=getattr(agent.context_manager,'_stash',None)
            if stash is None:raise ValueError('SDK_OFFLOAD_ORIGINAL_REQUIRED')
            for i,block in enumerate(original['result']['content']):
                if await stash.retrieve(tool_id+'_'+str(i))!=block:raise ValueError('SDK_OFFLOAD_ORIGINAL_MISMATCH')
    post=[e for e in events if e['sequence']>send['sequence'] and e['kind'] in
        ('r3_request','model_original_tool_request','model_original_tool_feedback','original_research_plan','candidate_constructed',
         'candidate_analysis','physical_replay','tool')]
    if post:raise ValueError('POST_TRUNCATION_TOOL_EXECUTION_NOT_EXCLUDED')
    last_ids=[b['toolResult']['toolUseId'] for b in agent.messages[-1]['content'] if 'toolResult' in b]
    if not last_ids or set(last_ids)-set(uses):raise ValueError('LAST_TRUSTED_FEEDBACK_REQUIRED')
    files=snapshot_files(directory,s['pilot']['framework_session_id'])
    return dict(version='confirmed_incomplete_provider_output_v1',study_id=host.run_id,
        implementation=s['freeze'],original_request_implementation=original_freeze,original_decision_packet=packets[-1]['outputs'][0],
        original_tool_schema_identity=digest(request.get('tools',[])),request_id=key,request=meta['request'],response=reception['body'],
        http_status=reception['http_status'],finish_reasons=['length'],usage=reception['usage'],
        receipt_execution_id=row['execution_id'],original_session=s['pilot']['framework_session_id'],
        sdk_message_identity=digest(agent.messages),old_snapshot_files=files,last_feedback_tool_ids=last_ids,
        prior_tool_count=len(uses),truncated_tool_fields_executed=False,
        original_budget=host.store.remaining(),source_state_identity=state_identity(s),
        interpretation='Confirmed and charged incomplete output; no tool fields accepted or executed.')


def trusted_history(host,agent,*,initial_messages=None,files=None,preparation=None,allow_incomplete=False):
    """Check normal recovery boundaries against existing Store identities."""
    s=state(host);session_id=agent._session_manager.session_id
    if session_id!=s['pilot']['framework_session_id']:raise ValueError('STORE_SESSION_POINTER_MISMATCH')
    # An interrupted tool round is not a clean boundary. Its original receipts
    # and feedback remain owned by recover_feedback(), never replayed here.
    if allow_incomplete and (s['pilot'].get('unconsumed_response') or unmatched(agent.messages) or (agent.messages and
            agent.messages[-1]['role']=='user' and any('toolResult' in b for b in agent.messages[-1]['content']))):
        return 'incomplete'
    anchors=[]
    for event in host.store.events(host.run_id):
        if event['kind'] not in ('model_original_turn','request_feedback_boundary'):continue
        value=host.store.artifact(event['outputs'][0])
        if value.get('session_id')==session_id and value.get('sdk_message_identity'):
            anchors.append(value)
    if anchors:
        anchor=anchors[-1]
        if digest(agent.messages)!=anchor['sdk_message_identity']:raise ValueError('SDK_HISTORY_IDENTITY_MISMATCH_OR_UNTRUSTED_SUFFIX')
        if unmatched(agent.messages):raise ValueError('SDK_COMPLETED_HISTORY_HAS_UNPAIRED_TOOLS')
        return 'request_feedback' if anchor.get('version')=='request_feedback_boundary_v1' else 'completed'
    if initial_messages is not None:
        verification=host.store.artifact(s['pilot']['handoff_verification'])
        if agent.messages!=initial_messages:
            # The SDK snapshots a deterministic invocation prompt before the
            # first before_model hook. A migration pause there has sent nothing.
            normalized=[{k:v for k,v in m.items() if k!='tracking_id'} for m in agent.messages]
            suffix=normalized[len(initial_messages):]
            events=host.store.events(host.run_id)
            committed=[e for e in events if e['kind']=='session_handoff' and e['status']=='committed'
                and e['outputs'][0]==preparation]
            unsent=bool(committed and not any(e['kind']=='r3_request' and e['sequence']>committed[-1]['sequence'] for e in events))
            if (normalized[:len(initial_messages)]!=initial_messages or not suffix
                    or any(m!=dict(role='user',content=[dict(text=INVOCATION_PROMPT)]) for m in suffix)
                    or not unsent or verification.get('preparation')!=preparation or not verification.get('independently_restored')):
                raise ValueError('SDK_INITIAL_CONTEXT_MISMATCH')
            from tools.research.agent import record
            record(host,'sdk_unsent_invocation_verified',dict(preparation=preparation,session_id=session_id,
                sdk_message_identity=digest(agent.messages),messages=agent.messages,snapshot_files=files,
                next_request_sent=False,invocation_completed=False))
            return 'initial_unsent_invocation'
        if (verification.get('preparation')!=preparation or not verification.get('independently_restored')
                or files!=verification['snapshot_files']):raise ValueError('SDK_COMMITTED_SNAPSHOT_FILES_MISMATCH')
        return 'initial'
    if agent.messages or any(e['kind']=='r3_request' for e in host.store.events(host.run_id)):
        raise ValueError('SDK_HISTORY_HAS_NO_TRUSTED_STORE_ANCHOR')
    return 'empty'


async def validate_snapshot(host,preparation,build,directory,*,initial=False,allow_incomplete=False):
    value=host.store.artifact(preparation)
    files=snapshot_files(directory,value['next_session'])
    agent=build(value['next_session'])
    if not await agent._session_manager.restore_snapshot(agent):raise ValueError('SDK_SNAPSHOT_MISSING')
    if agent._session_manager.session_id!=value['next_session']:raise ValueError('SDK_SESSION_ID_MISMATCH')
    marker=agent.state.get('research_handoff')
    if marker!=dict(preparation=preparation,state_identity=value['source_state_identity']):raise ValueError('SDK_HANDOFF_IDENTITY_MISMATCH')
    if schemas(agent)!=value['tool_schemas']:raise ValueError('SDK_TOOL_SCHEMA_MISMATCH')
    for ref in value['scientific_results']:host.store.artifact(ref)
    if value['study_id']!=host.run_id:raise ValueError('SDK_HANDOFF_STUDY_MISMATCH')
    if initial:
        if agent.messages!=value['initial_messages']:raise ValueError('SDK_INITIAL_CONTEXT_MISMATCH')
    else:
        s=state(host)
        if s['pilot'].get('handoff')!=preparation:raise ValueError('STORE_HANDOFF_POINTER_MISMATCH')
        trusted_history(host,agent,initial_messages=value['initial_messages'],files=files,preparation=preparation,allow_incomplete=allow_incomplete)
    return agent


async def reconcile(host,build,directory,*,allow_incomplete=False):
    """A preparation never switches automatically; a broken committed pointer blocks."""
    s=state(host);ref=s['pilot'].get('handoff')
    if not ref:return None
    value=host.store.artifact(ref)
    if value['next_session']!=s['pilot']['framework_session_id']:raise ValueError('STORE_SESSION_POINTER_MISMATCH')
    return await validate_snapshot(host,ref,build,directory,allow_incomplete=allow_incomplete)


async def handoff(host,agent,build,directory,*,stage=lambda name:None,boundary='completed_invocation'):
    """Prepare -> persist -> independently reopen -> verify -> atomic pointer commit."""
    current=state(host);committed=current['pilot'].get('handoff')
    if committed:
        prior=host.store.artifact(committed);session_id=agent._session_manager.session_id
        repeated_old=(prior['previous_session']==session_id and prior.get('boundary_identity',prior.get('completed_boundary_identity'))==digest(agent.messages))
        untouched_new=(prior['next_session']==session_id and agent.messages==prior['initial_messages'])
        if repeated_old or untouched_new:return committed,await validate_snapshot(host,committed,build,directory)
    if agent._session_manager.session_id!=current['pilot']['framework_session_id']:raise ValueError('OLD_SESSION_ID_MISMATCH')
    # Preserve the original SDK reasoning/tool IDs before recording a handoff boundary.
    await agent._session_manager.save_snapshot(agent,is_latest=True)
    restored=build(current['pilot']['framework_session_id'])
    if restored.messages!=agent.messages:raise ValueError('OLD_SDK_HISTORY_NOT_DURABLE')
    stage('before_prepare')
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state'];safe_boundary(host,s,db,agent.messages,boundary=boundary)
        prior=s['pilot'].get('handoff_preparation')
        if prior:
            value=host.store.artifact(prior)
            if value['source_state_identity']!=state_identity(s) or value.get('boundary_identity',value.get('completed_boundary_identity'))!=digest(agent.messages):
                raise ValueError('PREPARATION_STATE_CHANGED_KEEP_OLD_SESSION')
            preparation=prior
        else:
            initial=initial_messages(host.run_id)
            value=dict(version='research_session_handoff_v2',study_id=host.run_id,implementation=s['freeze'],
                previous_session=s['pilot']['framework_session_id'],source_state_identity=state_identity(s),
                source_state=plain(host.store.put(db,s)),completed_boundary_identity=digest(agent.messages),
                completed_boundary=plain(host.store.put(db,dict(session_id=s['pilot']['framework_session_id'],messages=agent.messages))),
                budget=host.store.remaining(db=db),scientific_results=[r for key in
                    ('results','mechanics_results','physical_replays','matched_state_results','rl_evaluations','analysis_results')
                    for r in s.get(key,[])],
                tool_schemas=schemas(agent),initial_messages=initial)
            if boundary=='request_feedback':
                value['version']='research_session_handoff_v3';value['boundary_kind']=boundary
                value['boundary_identity']=value.pop('completed_boundary_identity')
                value['boundary']=value.pop('completed_boundary')
                value['invocation_completed']=False
                anchor=next(host.store.artifact(e['outputs'][0]) for e in reversed(host.store.events(host.run_id))
                    if e['kind']=='request_feedback_boundary')
                from tools.research.config import conversation_policy
                value['pending_feedback_delivery']=feedback_delivery(host,anchor['tool_ids'],compact=bool(conversation_policy(s['spec'])))
            value['next_session']='rh-'+digest(value)[:24]
            preparation=plain(host.store.put(db,value));s['pilot']['handoff_preparation']=preparation
            host.store.update_state(db,host.run_id,s)
            host.store.event(db,host.run_id,'session_handoff','prepared',outputs=[preparation])
    stage('prepared')
    new=build(value['next_session'])
    # A prior partial write is either a valid same-preparation snapshot or an error.
    if new.messages:
        new=await validate_snapshot(host,preparation,build,directory,initial=True)
    else:
        new.messages=deepcopy(value['initial_messages'])
        new.state.set('research_handoff',dict(preparation=preparation,state_identity=value['source_state_identity']))
        stage('writing_snapshot')
        await new._session_manager.save_snapshot(new,is_latest=True)
    snapshot_files(directory,value['next_session'],flush=True)
    stage('snapshot_saved')
    new=await validate_snapshot(host,preparation,build,directory,initial=True)
    files=snapshot_files(directory,value['next_session'])
    stage('verified')
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state']
        if s['pilot'].get('handoff')==preparation:return preparation,new
        safe_boundary(host,s,db,agent.messages,boundary=boundary)
        if (s['pilot'].get('handoff_preparation')!=preparation or state_identity(s)!=value['source_state_identity']
                or host.store.remaining(db=db)!=value['budget'] or schemas(agent)!=value['tool_schemas']):
            raise ValueError('HANDOFF_STATE_OR_LEDGER_CHANGED')
        if files!=snapshot_files(directory,value['next_session']):raise ValueError('SDK_SNAPSHOT_CHANGED_BEFORE_COMMIT')
        verification=host.store.put(db,dict(preparation=preparation,snapshot_files=files,independently_restored=True))
        s['pilot'].update(framework_session_id=value['next_session'],handoff=preparation,handoff_verification=plain(verification))
        s['pilot'].pop('handoff_preparation',None)
        host.store.update_state(db,host.run_id,s)
        host.store.event(db,host.run_id,'session_handoff','committed',outputs=[preparation,verification])
    stage('committed')
    return preparation,new


async def recover_confirmed_incomplete(host,agent,build,directory,*,stage=lambda name:None):
    """Atomically dispose only a verified truncated response and switch SDK sessions."""
    from tools.research.state import guard
    guard(host)
    current=state(host);committed=current['pilot'].get('handoff')
    if committed:
        prior=host.store.artifact(committed)
        if prior.get('version')=='research_session_handoff_incomplete_v1' and not current['pilot'].get('unconsumed_response'):
            if agent._session_manager.session_id in (prior['previous_session'],prior['next_session']):
                return committed,await validate_snapshot(host,committed,build,directory)
    proof=await inspect_confirmed_incomplete(host,agent,directory)
    # Reopen the original SDK snapshot independently, without rewriting it.
    old=build(proof['original_session'])
    if old.messages!=agent.messages or schemas(old)!=schemas(agent):raise ValueError('OLD_SDK_SNAPSHOT_OR_SCHEMA_MISMATCH')
    old_files=snapshot_files(directory,proof['original_session'])
    if old_files!=proof['old_snapshot_files']:raise ValueError('OLD_SDK_SNAPSHOT_CHANGED')
    stage('before_prepare')
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state']
        if state_identity(s)!=proof['source_state_identity'] or host.store.remaining(db=db)!=proof['original_budget']:
            raise ValueError('INCOMPLETE_SOURCE_STATE_OR_BUDGET_CHANGED')
        prior=s['pilot'].get('handoff_preparation')
        if prior:
            value=host.store.artifact(prior)
            if (value.get('version')!='research_session_handoff_incomplete_v1' or
                    value.get('disposition_proof')!=proof):raise ValueError('PREPARATION_STATE_CHANGED_KEEP_OLD_SESSION')
            preparation=prior
        else:
            text=('The preceding Provider response was confirmed truncated and charged. '
                'Its tool fields were not executed and are not scientific evidence. '
                'Use the current Study packet, retained candidate and verified last tool feedback. '
                'Choose one next useful research action with a concise hypothesis, observation and stopping condition.')
            initial=initial_messages(host.run_id)+[dict(role='user',content=[dict(text=text)])]
            disposition=plain(host.store.put(db,proof))
            value=dict(version='research_session_handoff_incomplete_v1',study_id=host.run_id,
                implementation=s['freeze'],previous_session=proof['original_session'],
                source_state_identity=proof['source_state_identity'],source_state=plain(host.store.put(db,s)),
                boundary_identity=proof['sdk_message_identity'],disposition=disposition,disposition_proof=proof,
                budget=proof['original_budget'],scientific_results=[r for k in
                    ('results','mechanics_results','physical_replays','matched_state_results','rl_evaluations','analysis_results')
                    for r in s.get(k,[])],tool_schemas=schemas(agent),initial_messages=initial,
                pending_feedback_delivery=feedback_delivery(host,proof['last_feedback_tool_ids']),invocation_completed=False)
            value['next_session']='rh-'+digest(value)[:24]
            preparation=plain(host.store.put(db,value));s['pilot']['handoff_preparation']=preparation
            host.store.update_state(db,host.run_id,s)
            host.store.event(db,host.run_id,'incomplete_provider_disposition','prepared',outputs=[disposition,preparation])
    stage('prepared')
    new=build(value['next_session'])
    if new.messages:new=await validate_snapshot(host,preparation,build,directory,initial=True)
    else:
        new.messages=deepcopy(value['initial_messages'])
        new.state.set('research_handoff',dict(preparation=preparation,state_identity=value['source_state_identity']))
        stage('writing_snapshot')
        await new._session_manager.save_snapshot(new,is_latest=True)
    snapshot_files(directory,value['next_session'],flush=True)
    stage('snapshot_saved')
    new=await validate_snapshot(host,preparation,build,directory,initial=True)
    files=snapshot_files(directory,value['next_session']);stage('verified')
    checked=await inspect_confirmed_incomplete(host,agent,directory)
    if checked!=proof or schemas(agent)!=value['tool_schemas']:raise ValueError('INCOMPLETE_BOUNDARY_CHANGED')
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state']
        if s['pilot'].get('handoff')==preparation:return preparation,new
        if (s['pilot'].get('handoff_preparation')!=preparation or state_identity(s)!=proof['source_state_identity'] or
                s['pilot'].get('unconsumed_response')!=proof['request_id'] or s.get('pending') or
                host.store.remaining(db=db)!=proof['original_budget'] or
                db.execute('SELECT COUNT(*) FROM calls WHERE run_id=? AND receipt IS NULL',(host.run_id,)).fetchone()[0] or
                files!=snapshot_files(directory,value['next_session'])):
            raise ValueError('INCOMPLETE_COMMIT_STATE_CHANGED')
        verification=host.store.put(db,dict(preparation=preparation,snapshot_files=files,independently_restored=True))
        disposition=host.store.put(db,dict(version='confirmed_incomplete_provider_output_v1',
            proof=value['disposition'],preparation=preparation,verification=plain(verification),
            decision='archived_not_executed',new_session=value['next_session']))
        s['pilot'].update(framework_session_id=value['next_session'],handoff=preparation,
            handoff_verification=plain(verification),incomplete_provider_disposition=plain(disposition))
        # Removal is inseparable from the audited disposition and verified pointer switch.
        del s['pilot']['unconsumed_response'];del s['pilot']['handoff_preparation']
        host.store.update_state(db,host.run_id,s)
        host.store.event(db,host.run_id,'incomplete_provider_disposition','committed',outputs=[disposition,preparation,verification])
        host.store.event(db,host.run_id,'session_handoff','committed',outputs=[preparation,verification])
    stage('committed')
    return preparation,new


async def recover_feedback(host,agent):
    """Pair only saved original results in the old SDK; never execute a tool here."""
    from tools.research.agent import record, pending
    from tools.research.research_context import tool_feedback
    s=state(host)
    if s.get('pending') or pending(host) or s['pilot'].get('unconsumed_response'):raise ValueError('SETTLE_ORIGINAL_OUTCOME_FIRST')
    if agent._session_manager.session_id!=s['pilot']['framework_session_id']:raise ValueError('OLD_SESSION_REQUIRED')
    outstanding=unmatched(agent.messages)
    if not outstanding:return 0
    results=[]
    for key,use in outstanding.items():
        events=host.store.events(host.run_id)
        feedback=[host.store.artifact(e['outputs'][0]) for e in events if e['kind']=='model_original_tool_feedback']
        matched=[f for f in feedback if f['tool_use']==use]
        if matched:
            if any(f['result']!=matched[0]['result'] for f in matched):raise ValueError('CONFLICTING_SAVED_TOOL_FEEDBACK')
            result=matched[0]['result']
        else:
            requests=[host.store.artifact(e['outputs'][0])['tool_use'] for e in events if e['kind']=='model_original_tool_request']
            if use not in requests:raise ValueError('ORIGINAL_TOOL_REQUEST_REQUIRED')
            row=host.store.lookup(host.run_id,'native-'+key+('-analysis' if use['name']=='research_analysis' else ''))
            if not row or not row['receipt']:raise ValueError('ORIGINAL_TOOL_RECEIPT_REQUIRED_NO_REEXECUTION')
            receipt=json.loads(row['receipt'])
            if receipt['execution_status']!='completed':raise ValueError('FAILED_TOOL_REQUIRES_ORIGINAL_FEEDBACK')
            value=host.store.artifact(receipt['output'])
            if use['name']=='research_plan':
                from tools.research.contracts import Plan
                if row['request_hash']!=digest(plain(Plan.model_validate(use['input']))):raise ValueError('ORIGINAL_TOOL_IDENTITY_MISMATCH')
            elif use['name']=='research_analysis':
                # Recover the frozen request; a newer admission contract must not reinterpret it.
                query=value['requested_operation']
                if row['request_hash']!=digest(query) or any(query.get(k)!=v for k,v in use['input'].items()):raise ValueError('ORIGINAL_TOOL_IDENTITY_MISMATCH')
            elif use['name'] in ('research_investigate','research_route','research_recall'):
                if row['request_hash']!=digest(use['input']):raise ValueError('ORIGINAL_TOOL_IDENTITY_MISMATCH')
            else:raise ValueError('SDK_RECOVERY_REQUIRES_SAVED_FEEDBACK_FOR_THIS_TOOL')
            if use['name']=='research_analysis':
                from tools.research.analysis import compact_result
                value=compact_result(value,receipt['output'])
            if use['name'] not in ('research_investigate','research_route','research_recall') and s['spec'].get('research_decisions',{}).get('context_limits'):value=tool_feedback(host,value)
            if use['name'] in ('research_plan','research_analysis') and s['spec'].get('research_decisions'):
                from tools.research.reporter import scientific_feedback
                report=scientific_feedback(host,host.store.artifact(receipt['output']),receipt=receipt)
                if report is not None:value=report
            result=dict(toolUseId=key,status='success',content=[dict(text=json.dumps(value,separators=(',',':')))])
            record(host,'model_original_tool_feedback',dict(tool_use=use,result=result,recovered_from_receipt=True))
        if result.get('toolUseId')!=key:raise ValueError('SAVED_TOOL_RESULT_ID_MISMATCH')
        results.append(dict(toolResult=result))
    agent.messages.append(dict(role='user',content=results))
    await agent._session_manager.save_snapshot(agent,is_latest=True)
    return len(results)  # Old invocation must consume feedback before handoff is admitted.
