"""Coordinate SDK files and the existing Store; no decisions or scientific launches."""
from copy import deepcopy
import json
import os
from pathlib import Path
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.state import state


def state_identity(value):
    value=deepcopy(value);value['pilot'].pop('handoff_preparation',None)
    return digest(value)


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


def safe_boundary(host,current,db,messages):
    if current['research_status']=='stopped':raise ValueError('STOPPED')
    if current.get('success_gate'):raise ValueError('SELECT_REQUIRED')
    if current.get('pending') or current['pilot'].get('unconsumed_response'):raise ValueError('PENDING_FEEDBACK_OR_EXECUTION')
    if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:raise ValueError('UNSETTLED_OUTCOME')
    if any(e.get('active_reservation') or e.get('status',{}).get('worker_alive',True)
            for e in current.get('rl_runs',{}).values()):raise ValueError('WORKER_RECOVERY_REQUIRED')
    if unmatched(messages):raise ValueError('MISSING_TOOL_RESULT')
    if not messages or messages[-1]['role']!='assistant':raise ValueError('OLD_FEEDBACK_MUST_BE_CONSUMED_FIRST')
    turns=[host.store.artifact(e['outputs'][0]) for e in host.store.events(host.run_id) if e['kind']=='model_original_turn']
    complete=next((t for t in reversed(turns) if t.get('session_id')==current['pilot']['framework_session_id']),None)
    if current['pilot'].get('session_handoff_live_admitted') and complete is None:raise ValueError('DURABLE_COMPLETED_INVOCATION_REQUIRED')
    if complete and complete['sdk_message_identity']!=digest(messages):raise ValueError('OLD_SDK_HISTORY_NOT_DURABLE')


def snapshot_files(directory,session_id,*,flush=False):
    root=Path(directory).resolve()/'session'/session_id
    files=sorted(root.rglob('*.json'));result={}
    if not any(p.name=='snapshot_latest.json' for p in files):raise ValueError('SDK_SNAPSHOT_MISSING')
    for path in files:
        if len(str(path))+38>=260:raise ValueError('SDK_WINDOWS_PATH_TOO_LONG')
        with path.open('r+b' if flush else 'rb') as stream:
            body=stream.read()
            if flush:os.fsync(stream.fileno())
        result[str(path.relative_to(root))]=digest(body.hex())
    return result


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
        if event['kind']!='model_original_turn':continue
        value=host.store.artifact(event['outputs'][0])
        if value.get('session_id')==session_id and value.get('sdk_message_identity'):
            anchors.append(value)
    if anchors:
        anchor=anchors[-1]
        if digest(agent.messages)!=anchor['sdk_message_identity']:raise ValueError('SDK_HISTORY_IDENTITY_MISMATCH_OR_UNTRUSTED_SUFFIX')
        if unmatched(agent.messages):raise ValueError('SDK_COMPLETED_HISTORY_HAS_UNPAIRED_TOOLS')
        return 'completed'
    if initial_messages is not None:
        if agent.messages!=initial_messages:raise ValueError('SDK_INITIAL_CONTEXT_MISMATCH')
        verification=host.store.artifact(s['pilot']['handoff_verification'])
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


async def handoff(host,agent,build,directory,*,stage=lambda name:None):
    """Prepare -> persist -> independently reopen -> verify -> atomic pointer commit."""
    from tools.research.agent import decision_packet
    current=state(host);committed=current['pilot'].get('handoff')
    if committed:
        prior=host.store.artifact(committed);session_id=agent._session_manager.session_id
        repeated_old=(prior['previous_session']==session_id and prior['completed_boundary_identity']==digest(agent.messages))
        untouched_new=(prior['next_session']==session_id and agent.messages==prior['initial_messages'])
        if repeated_old or untouched_new:return committed,await validate_snapshot(host,committed,build,directory)
    if agent._session_manager.session_id!=current['pilot']['framework_session_id']:raise ValueError('OLD_SESSION_ID_MISMATCH')
    # Preserve the original SDK reasoning/tool IDs before recording a handoff boundary.
    await agent._session_manager.save_snapshot(agent,is_latest=True)
    restored=build(current['pilot']['framework_session_id'])
    if restored.messages!=agent.messages:raise ValueError('OLD_SDK_HISTORY_NOT_DURABLE')
    stage('before_prepare')
    with host.store.transaction() as db:
        s=host.store.session(host.run_id,db)['state'];safe_boundary(host,s,db,agent.messages)
        prior=s['pilot'].get('handoff_preparation')
        if prior:
            value=host.store.artifact(prior)
            if value['source_state_identity']!=state_identity(s) or value['completed_boundary_identity']!=digest(agent.messages):
                raise ValueError('PREPARATION_STATE_CHANGED_KEEP_OLD_SESSION')
            preparation=prior
        else:
            packet=decision_packet(host)
            initial=[dict(role='user',content=[dict(text='Authoritative research handoff, no prior chat copied:\n'+json.dumps(packet,separators=(',',':')))])]
            value=dict(version='research_session_handoff_v2',study_id=host.run_id,implementation=s['freeze'],
                previous_session=s['pilot']['framework_session_id'],source_state_identity=state_identity(s),
                source_state=plain(host.store.put(db,s)),completed_boundary_identity=digest(agent.messages),
                completed_boundary=plain(host.store.put(db,dict(session_id=s['pilot']['framework_session_id'],messages=agent.messages))),
                budget=host.store.remaining(db=db),scientific_results=[r for key in
                    ('results','mechanics_results','physical_replays','matched_state_results','rl_evaluations','analysis_results')
                    for r in s.get(key,[])],
                tool_schemas=schemas(agent),initial_messages=initial)
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
        safe_boundary(host,s,db,agent.messages)
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
            elif use['name']=='research_investigate':
                if row['request_hash']!=digest(use['input']):raise ValueError('ORIGINAL_TOOL_IDENTITY_MISMATCH')
            else:raise ValueError('SDK_RECOVERY_REQUIRES_SAVED_FEEDBACK_FOR_THIS_TOOL')
            if use['name']=='research_analysis':
                from tools.research.analysis import compact_result
                value=compact_result(value,receipt['output'])
            if use['name']!='research_investigate' and s['spec'].get('research_decisions',{}).get('context_limits'):value=tool_feedback(host,value)
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
