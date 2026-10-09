"""Bounded live R3 entry point; Strands owns history and continuation, Store owns accounting."""
import argparse
from contextlib import contextmanager, ExitStack
import importlib.metadata
import json
import os
from pathlib import Path
import time
from unittest.mock import patch
from uuid import uuid4

import httpx
from strands.experimental.context_manager import Offload
from strands.hooks.events import BeforeToolCallEvent, AfterToolCallEvent, AfterModelCallEvent
from strands.tools.executors import SequentialToolExecutor

from tools.strands_pilot import (ROOT, TARGET, SOURCE_IDS, initialize, build_harness,
    DeepSeekPilotModel, FORBIDDEN_BOUNDARIES, Host, InvestigationDispatcher)
from tools.platform_store import plain, zero, encode
from tools.state_io import atomic_json, digest
from tools.research_investigations import PrincipalDisposition

CALLER='deepseek-r3'
AUTHORIZATION='User goal-objective.md bd8fc323-b0bd-48b8-ad5a-f33a04f07e95: R3 live DeepSeek, saved V1 evidence, 40 provider attempts, 512 public tools, 6h including preparation; zero scientific executions; normal pilot-branch push.'


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


def reopen_live(directory,activity):
    host=Host(Path(directory)/'business',activity,actor='strands-pilot')
    if pilot(host).get('mode')!='live-r3':raise ValueError('R3_LIVE_ACTIVITY_REQUIRED')
    for row in pending(host):
        reception=received(host,row['request_id'])
        if reception:settle(host,row,reception)
        else:host.store.mark_unknown(activity,row['request_id'])
    return host


class LiveBoundary(httpx.AsyncBaseTransport):
    """One durable reservation per actual send, including auxiliary summarization.

    No auth headers are persisted. Complete response bytes are saved before JSON
    decoding. An unconsumed confirmed response is replayed only for its exact
    request; uncertainty blocks further sends and retains its reservation.
    """
    def __init__(self,host,transport=None):
        self.host=host
        self.inner=transport or httpx.AsyncHTTPTransport(retries=0)
        self.last_request=None

    async def handle_async_request(self,request):
        host=self.host;store=host.store;run=host.run_id
        wire=json.loads(request.content)
        expected=pilot(host)['provider']
        if (str(request.url)!=expected['base_url'].rstrip('/')+'/chat/completions'
            or wire.get('model')!='deepseek-flash' or wire.get('thinking')!={'type':'enabled'}
            or wire.get('reasoning_effort')!='high' or wire.get('max_tokens')!=32768
            or wire.get('stream') is not False or wire.get('tool_choice','auto')!='auto'):
            raise ValueError('R3_PROVIDER_CONFIGURATION_MISMATCH')
        saved=pilot(host).get('unconsumed_response')
        if saved:
            row=store.lookup(run,saved)
            if row['request_hash']!=digest(wire):raise ValueError('R3_SAVED_RESPONSE_MUST_BE_PROCESSED_FIRST')
            reception=received(host,saved)
            if not reception:raise ValueError('R3_SAVED_RESPONSE_MISSING')
            self.last_request=saved
            record(host,'r3_response_replay',dict(request_id=saved,new_send=False))
            return httpx.Response(reception['http_status'],content=store.artifact(reception['body'],raw=True),request=request)
        if pending(host):raise ValueError('R3_UNCONFIRMED_ATTEMPT_BLOCKS_SEND')
        def guard(db):
            if time.time()>=pilot(host,db)['request_deadline_unix']:raise ValueError('R3_DELIVERY_WINDOW_NO_MORE_REQUESTS')
        with store.transaction() as db:
            raw_request=store.put(db,wire)
        key='r3-request-'+uuid4().hex
        try:
            row,_=store.reserve(run,key,digest(wire),CALLER,{**zero(),'model_calls':1,'wall_s':600.},
                resources=['provider_request'],inputs=[raw_request],kind='r3_model',guard=guard)
        except ValueError as exc:
            record(host,'r3_send_rejected',dict(request=plain(raw_request),sent=False,reason=str(exc)),status='blocked')
            raise
        self.last_request=key
        purpose='conversation' if wire.get('tools') else 'summarization'
        with store.transaction() as db:
            state=store.session(run,db)['state'];state['pilot']['live_model_requests']+=1
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
                if 200<=response.status_code<300:state['pilot']['unconsumed_response']=key
                store.update_state(db,run,state)
                store.event(db,run,'r3_response','received',request=key,execution=row['execution_id'],outputs=[ref])
            try:
                parsed=json.loads(body)
                usage=parsed.get('usage')
                reception.update(usage=usage,finish_reasons=[c.get('finish_reason') for c in parsed.get('choices',[])],
                    reasoning_tokens=(usage or {}).get('completion_tokens_details',{}).get('reasoning_tokens'))
            except (ValueError,AttributeError,TypeError):pass
            with store.transaction() as db:
                ref=store.put(db,reception)
                store.event(db,run,'r3_response','metadata_saved',request=key,execution=row['execution_id'],outputs=[ref])
            settle(host,row,reception)
            if 'length' in (reception['finish_reasons'] or []):
                raise ValueError('R3_LENGTH_TRUNCATED_NO_NATIVE_SUBMISSION')
            return httpx.Response(response.status_code,content=body,request=request)
        except BaseException as exc:
            # Local archive/settlement failures do not erase already saved reception.
            reception=received(host,key)
            if reception:settle(host,row,reception)
            else:store.mark_unknown(run,key)
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
    class AccountedDeepSeekModel(DeepSeekPilotModel):
        async def stream(self,*args,**kwargs):
            async for item in super().stream(*args,**kwargs):yield item
            boundary.consumed()  # Failed conversion leaves the saved response available.
    return AccountedDeepSeekModel


def context_config(model,continuation=False):
    # Small thresholds exercise public built-in mechanisms on real evidence.
    # Per-text summaries avoid mixed-content fallback and retain tool IDs/reasoning.
    return dict(strategies=[
        Offload.truncate(['tool::read_original'],{'preview_tokens':64}).when(threshold=400),
        Offload.summarize('user_text',{'model':model}).when(threshold=2000 if continuation else 150,preserve_recent=1),
        Offload.summarize('assistant_text',{'model':model}).when(threshold=2000 if continuation else 400,preserve_recent=1)])


INSTRUCTIONS="""You are the sole principal reviewing saved V1 fixed-C evidence. Read evidence
through discover_evidence and read_original; never infer identities of a new experiment.
Evaluate arrival, holding position, holding speed and joint acceptance, preserving exact
values, units, criteria, task/candidate/source execution identities and limitations.
This activity allows evidence reading and a new principal judgment only, zero computation.
Use retrieve_context to recover offloaded originals. Tool result previews are incomplete;
page originals where necessary. Before submission, inspect exact cited fields.
Native submit_result takes decision and revision=1. decision has investigation_id (directory
target), report (directory report reference), disposition accept/defer/reject, adopted_claims,
evidence_used, remaining_unknowns and reason. Each adopted claim contains statement,
supporting_facts, scope and support_explanation. Each fact is
{statement, reference, pointer, value, source_identity:{}}. supporting_facts must be drawn
from the extraction-only report facts. Put supplementary independently read original
facts in evidence_used; leave additional_support empty (it requires a selection-provenance
service outside this pilot). For accept, adopt only report-supported claims; put your
full assessment of the other sources in reason, linked to evidence_used.
scope contains inspected source identity fields. All cited values must match
originals exactly. Read the report before using it. The extraction-only report asserts no
joint success. Acceptance of source-supported claims does not mean success of the robot task.
scope is a LIST of SourceFact objects, not a free-form identity dictionary; for example
an independently inspected /source_execution_id string from the evaluation. evidence_used
is also a list of SourceFact objects (at most 12); adopted_claims is a list (at most 8).
Only the directory's three sources and report are in this grant. Linked simulation,
configuration and prediction references are metadata, not newly authorized readable sources.
Do not retry an unchanged failed read. Use pointer-targeted pages for relevant fields;
finish with limitations when referenced material is outside the granted source scope.
Return concrete corrections after validation feedback. Do not submit until asked in the
post-restart stage. Normal text is provisional; only the native tool records a decision.
Do not call another agent or any execution tool. After committing, query get_receipt.
"""

READ_PROMPT="""Review the saved V1 fixed-C case: does the saved execution satisfy arrival,
holding position, holding speed and joint acceptance? Discover the evidence directory,
read the saved evaluation, holding-window report, joint-acceptance record, extraction-only
report and identity fields through the public tools. Inspect the original numerical values
and acceptance criteria. Cite artifact identities and JSON pointers, distinguish valid
execution from task success, and explain limits on causal claims and new-candidate scope.
If a long result is offloaded, recover it or page its source. End this stage with your
provisional assessment and a plan for native submission after the process restart. Do not
submit_result in this stage. You will retain the same activity and session on continuation.
"""

SUMMARY_PROMPT="""Before the planned process restart, finish the provisional source-bound review.
Give a compact progress note identifying the evidence examined, remaining evidence to
check, and offloaded reference keys needed to recover exact source pages. Do not submit
the decision yet. The framework handles context summarization and persistent history.
"""

RESUME_PROMPT="""Continue the same saved V1 fixed-C principal review after the planned process
restart. First call retrieve_context on at least one offloaded read_original reference
shown in the saved history; recover a full original page, not only a search snippet.
Recheck its exact numerical values and identity against the original evidence, using
read_original for any missing cited fields. Then submit your formal source-bound principal
decision for the directory target with revision 1, using the documented native schema;
query get_receipt and explain arrival, holding position, holding speed and joint outcome.
Keep scientific conclusions within the saved execution. A different candidate or cause
remains unassessed. If the tool reports invalid facts, correct only the concrete issue.
"""


def build_live(host,transport=None,key=None):
    boundary=LiveBoundary(host,transport)
    if key is None:
        from examples.gvs_nmpc_route_experiment import load_credential
        load_credential(Path.home()/'.codex/.env')
        key=os.environ['DEEPSEEK_API_KEY']
    continuation=pilot(host)['phase']=='checkpoint_saved'
    agent=build_harness(host,transport=boundary,api_key=key,context_config=lambda model:context_config(model,continuation),
        instructions=INSTRUCTIONS,model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),
        decision_contract=PrincipalDisposition)
    # Evidence and submission already reserve their public operation in Store.
    # Receipt lookup and built-in stash retrieval need the same public-tool budget.
    auxiliary={}
    def before(event):
        use=event.tool_use
        with host.store.transaction() as db:
            # Count even invalid public operations in the same Store, without
            # creating a second schedulable allowance or double-charging reads.
            count=db.execute("SELECT COUNT(*) FROM events WHERE run_id=? AND json_extract(body,'$.kind')='r3_tool_dispatch'",(host.run_id,)).fetchone()[0]
            if count>=host.store.config(db)['budget']['tool_calls']:raise ValueError('R3_PUBLIC_TOOL_BUDGET_EXHAUSTED')
            host.store.event(db,host.run_id,'r3_tool_dispatch','recorded',outputs=[host.store.put(db,dict(pid=os.getpid(),tool_use=use))])
        if use['name'] in ('get_receipt','retrieve_context'):
            row,_=host.store.reserve(host.run_id,'r3-tool-'+use['toolUseId'],digest(use),'r3-public-tool',
                {**zero(),'tool_calls':1},kind='r3_aux_tool')
            auxiliary[use['toolUseId']]=row
    def after(event):
        use=event.tool_use
        record(host,'r3_tool_result',dict(pid=os.getpid(),tool_use=use,result=event.result))
        row=auxiliary.pop(use['toolUseId'],None)
        if row:
            host.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],
                caller='r3-public-tool',tool_id=use['name'],execution_status='completed',charged=zero()),
                event.result,kind='r3_aux_tool')
    agent.hooks.add_callback(BeforeToolCallEvent,before)
    agent.hooks.add_callback(AfterToolCallEvent,after)
    def disable_retry(event):event.retry=False
    agent.hooks.add_callback(AfterModelCallEvent,disable_retry,order=1000)
    record(host,'r3_framework_configuration',dict(pid=os.getpid(),tool_executor='SequentialToolExecutor',
        tool_offload_threshold=400,preview_tokens=64,user_summary_threshold=2000 if continuation else 150,
        assistant_summary_threshold=2000 if continuation else 400,preserve_recent=1,
        overflow_retries=False,client_retries=0,transport_retries=0,summary_model='same registered deepseek-flash'))
    return agent


@contextmanager
def live_scope():
    with ExitStack() as stack:
        counts={name:0 for name in FORBIDDEN_BOUNDARIES if not name.startswith('httpx.')}
        for name in counts:
            def prohibited(*args,_name=name,**kwargs):
                counts[_name]+=1;raise AssertionError('R3_SCOPE_BOUNDARY_INVOKED: '+_name)
            stack.enter_context(patch(name,side_effect=prohibited))
        yield counts


def set_phase(host,phase,**details):
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state'];state['pilot']['phase']=phase
        host.store.update_state(db,host.run_id,state)
        host.store.event(db,host.run_id,'r3_phase',phase,outputs=[host.store.put(db,dict(pid=os.getpid(),**details))])


def context_proof(agent):
    text=encode(agent.messages)
    return dict(summary='[Summarized:' in text,offloaded='[ref:' in text,
        message_count=len(agent.messages),pid=os.getpid())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','read','checkpoint','resume','receipt','export','audit'])
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--activity',default='strands-pilot-r3-20261009')
    parser.add_argument('--started-unix',type=float)
    parser.add_argument('--evidence-directory',type=Path)
    parser.add_argument('--recover-response',action='store_true',help='Continue the persisted framework invocation without adding a prompt; exact saved response replay only.')
    parser.add_argument('--feedback',help='Concrete local repair or source-validation feedback for the same activity.')
    args=parser.parse_args()
    versions={k:importlib.metadata.version(k) for k in ('strands-harness','strands-agents')}
    if versions!={'strands-harness':'0.2.0','strands-agents':'1.59.0'}:raise ValueError('PINNED_R3_DEPENDENCIES_REQUIRED')
    if args.action=='prepare':
        host=initialize(args.directory,args.activity,authorization=AUTHORIZATION,started_unix=args.started_unix)
    else:host=reopen_live(args.directory,args.activity)
    if args.action in ('read','checkpoint','resume'):
        if pending(host):raise ValueError('R3_UNCONFIRMED_ATTEMPT_STOPPED')
        if (host.store.spendable(host.run_id)['remaining']['model_calls']<1
            and not (args.recover_response and pilot(host).get('unconsumed_response'))):
            raise ValueError('R3_PROVIDER_BUDGET_EXHAUSTED_NO_MORE_REQUESTS')
        phase=pilot(host)['phase']
        expected={'read':'prepared','checkpoint':'read_complete','resume':'checkpoint_saved'}[args.action]
        if phase!=expected:raise ValueError('R3_PHASE_MISMATCH: '+phase+' expected '+expected)
        with live_scope() as counts:
            agent=build_live(host)
            prompt={'read':READ_PROMPT,'checkpoint':SUMMARY_PROMPT,'resume':RESUME_PROMPT}[args.action]
            try:result=agent(None if args.recover_response else args.feedback or prompt)
            except Exception as exc:
                record(host,'r3_invocation_failure',dict(action=args.action,pid=os.getpid(),
                    exception_type=type(exc).__name__,scope=counts,budget=host.store.remaining()),status='stopped')
                raise
            proof=context_proof(agent)
            record(host,'r3_invocation',dict(action=args.action,pid=os.getpid(),result=str(result),context=proof,scope=counts))
            if args.action=='checkpoint' and not (proof['summary'] and proof['offloaded']):
                raise ValueError('R3_CONTEXT_MECHANISMS_NOT_OBSERVED')
            if pending(host) or pilot(host).get('unconsumed_response'):raise ValueError('R3_NOT_AT_SAVED_BOUNDARY')
            next_phase={'read':'read_complete','checkpoint':'checkpoint_saved','resume':'submitted'}[args.action]
            if args.action=='resume' and InvestigationDispatcher(host).disposition_receipt(TARGET,1) is None:
                raise ValueError('R3_NO_FORMAL_RECEIPT')
            set_phase(host,next_phase,context=proof)
    if args.action=='receipt':
        dispatcher=InvestigationDispatcher(host)
        before=host.store.remaining();first=dispatcher.disposition_receipt(TARGET,1);second=dispatcher.disposition_receipt(TARGET,1)
        if first!=second or before!=host.store.remaining():raise ValueError('R3_RECEIPT_LOOKUP_CHANGED_STATE')
        atomic_json(args.directory/'receipt.json',dict(receipt=first,repeated_read_equal=True,ledger_unchanged=True))
    if args.action=='export':
        if not args.evidence_directory:raise ValueError('EVIDENCE_DIRECTORY_REQUIRED')
        export(host,args.evidence_directory)
    if args.action=='audit':
        if not args.evidence_directory:raise ValueError('EVIDENCE_DIRECTORY_REQUIRED')
        atomic_json(args.evidence_directory/'acceptance.json',audit(host))
    print(encode(dict(activity=host.run_id,phase=pilot(host)['phase'],budget=host.store.remaining(),
        pending=len(pending(host)),deadline_unix=pilot(host)['deadline_unix'])))


def export(host,destination):
    """Non-secret request bodies, original responses, events, and receipt; no headers."""
    destination.mkdir(parents=True,exist_ok=True)
    events=host.store.events(host.run_id)
    artifacts={r['artifact_id']:host.store.artifact(r) for r in pilot(host)['sources']}
    for event in events:
        for ref in [*event['inputs'],*event['outputs']]:
            if ref['artifact_id'] not in artifacts:
                if ref['media_type']=='application/octet-stream':
                    body=host.store.artifact(ref,raw=True)
                    path=destination/(ref['artifact_id']+'.response.bin');path.write_bytes(body)
                    artifacts[ref['artifact_id']]=dict(file=path.name,media_type=ref['media_type'])
                else:artifacts[ref['artifact_id']]=host.store.artifact(ref)
    for event in events:
        if event['kind']=='r3_response':
            reception=host.store.artifact(event['outputs'][0]);ref=reception['body']
            path=destination/(ref['artifact_id']+'.response.bin')
            path.write_bytes(host.store.artifact(ref,raw=True))
            artifacts[ref['artifact_id']]=dict(file=path.name,media_type=ref['media_type'])
    receipt=InvestigationDispatcher(host).disposition_receipt(TARGET,1)
    atomic_json(destination/'raw_archive.json',dict(activity=host.run_id,events=events,artifacts=artifacts))
    atomic_json(destination/'receipt.json',dict(receipt=receipt,record=host.store.artifact(receipt['output']) if receipt else None))
    atomic_json(destination/'accounting.json',dict(activity=host.run_id,pilot=pilot(host),ledger=host.store.remaining(),
        pending=pending(host),money=None,reasoning_usage='Provider fields only; absent means unknown'))


def audit(host):
    """Independent observations; never constructs a scientific decision or receipt."""
    from tools.platform_handoff import pointer
    events=host.store.events(host.run_id)
    requests=[(e,host.store.artifact(e['outputs'][0])) for e in events if e['kind']=='r3_request']
    responses=[(e,host.store.artifact(e['outputs'][0])) for e in events if e['kind']=='r3_response' and e['status']=='metadata_saved']
    wires=[host.store.artifact(r['request']) for _,r in requests]
    invocations=[host.store.artifact(e['outputs'][0]) for e in events if e['kind']=='r3_invocation']
    checkpoints=[e for e in events if e['kind']=='r3_phase' and e['status']=='checkpoint_saved']
    checkpoint=checkpoints[-1]['sequence'] if checkpoints else 10**20
    before_pids={r['pid'] for e,r in requests if e['sequence']<checkpoint}
    after_requests=[(e,r) for e,r in requests if e['sequence']>checkpoint]
    retrievals=[];errors=[]
    for event in events:
        if event['kind']!='r3_tool_result':continue
        value=host.store.artifact(event['outputs'][0]);result=value['result'];use=value['tool_use']
        try:text_value=json.loads(result['content'][0].get('text','null'))
        except ValueError:text_value=None
        if use['name']=='submit_result' and isinstance(text_value,dict) and 'error' in text_value:
            errors.append(dict(sequence=event['sequence'],error=text_value['error'],issue=text_value.get('issue')))
        if event['sequence']>checkpoint and use['name']=='retrieve_context' and result['status']=='success':
            try:
                original=json.loads(text_value['text']);page=original['page']
                equal=page==host.store.artifact(original['receipt']['output'])
            except (KeyError,TypeError,ValueError):continue
            retrievals.append(dict(sequence=event['sequence'],pid=value['pid'],stash_reference=use['input']['reference'],
                source=page['source'],pointer=page['pointer'],exact_public_page_equal=equal,
                public_page_output=original['receipt']['output']))
    evaluation=host.store.artifact(pilot(host)['sources'][0])
    holding=host.store.artifact(pilot(host)['sources'][1])['detail']['sampled_settling']
    joint=host.store.artifact(pilot(host)['sources'][2])['detail']
    frozen=dict(arrival=dict(value=evaluation['metrics'][0]['value'],limit=evaluation['constraints'][0]['limit'],unit='m',
        passed=evaluation['metrics'][0]['value']<=evaluation['constraints'][0]['limit']),
        holding_position=dict(value=holding['max_error_m'],limit=holding['position_limit_m'],unit='m',passed=holding['max_error_m']<=holding['position_limit_m']),
        holding_speed=dict(value=holding['max_speed_m_s'],limit=holding['speed_limit_m_s'],unit='m/s',passed=holding['max_speed_m_s']<=holding['speed_limit_m_s']),
        joint=dict(status=joint['status'],accepted=joint['accepted'],execution_id=joint['execution_id']))
    totals={}
    for field in ('prompt_tokens','completion_tokens','total_tokens'):
        values=[(r.get('usage') or {}).get(field) for _,r in responses]
        totals[field]=sum(values) if all(type(v) is int for v in values) else None
    reasoning=[r['reasoning_tokens'] for _,r in responses]
    totals['reasoning_tokens']=sum(reasoning) if all(type(v) is int for v in reasoning) else None
    dispatcher=InvestigationDispatcher(host);budget_before=host.store.remaining()
    receipt=dispatcher.disposition_receipt(TARGET,1)
    repeated=dispatcher.disposition_receipt(TARGET,1)
    business=[e for e in events if e['kind']=='principal_disposition']
    citations=[]
    if receipt:
        for link in host.store.artifact(receipt['output'])['inspection_links']:
            fact=link['fact']
            citations.append(dict(reference=fact['reference'],pointer=fact['pointer'],
                original_value_equal=encode(pointer(host.store.artifact(fact['reference']),fact['pointer']))==encode(fact['value']),
                inspection_ids=link['inspection_ids']))
    return dict(activity=host.run_id,assessment='Formal result observed; manual semantic acceptance required' if receipt and len(business)==1 and retrievals else 'R3 incomplete; evidence-backed stop',
        request_boundary=dict(attempts=len(requests),confirmed_responses=len(responses),pending=pending(host),
            summaries=sum(r['purpose']=='summarization' for _,r in requests),
            actual_wire_configuration_preserved=all(w.get('model')=='deepseek-flash' and w.get('thinking')=={'type':'enabled'}
                and w.get('reasoning_effort')=='high' and w.get('max_tokens')==32768 and w.get('tool_choice','auto')=='auto' for w in wires),
            actual_timeout_600s=all(set(r['timeout_s'].values())=={600.} for _,r in requests),usage_totals=totals,money=None),
        framework=dict(checkpoint_observed=bool(checkpoints),invocations=invocations,
            restored_requests=len(after_requests),pids_before=sorted(before_pids),pids_after=sorted({r['pid'] for _,r in after_requests}),
            distinct_new_process=bool(after_requests) and all(r['pid'] not in before_pids for _,r in after_requests),
            restored_tool_history=[dict(sequence=e['sequence'],paired_tool_ids=[m['tool_call_id'] for m in w['messages'] if m['role']=='tool'],
                tool_pairs_complete=all(m['tool_call_id'] in {c['id'] for a in w['messages'] for c in a.get('tool_calls',[])} for m in w['messages'] if m['role']=='tool'),
                assistant_reasoning_fields=sum('reasoning_content' in m for m in w['messages'] if m['role']=='assistant'))
                for e,r in after_requests if r['purpose']=='conversation' for w in [host.store.artifact(r['request'])]][:2],retrievals=retrievals),
        frozen_facts=frozen,formal=dict(receipt=receipt,business_effects=len(business),validation_failures=errors,
            repeated_lookup_equal=receipt==repeated,lookup_ledger_unchanged=budget_before==host.store.remaining(),
            citations=citations,complete=receipt is not None),
        scope=dict(mathematical_solves=pilot(host)['mathematical_solves'],backend_solves=host.store.remaining()['used']['backend_solves'],
            robot_executions=pilot(host)['robot_backend_executions'],legacy_turn=host.store.session(host.run_id)['state']['turn'],
            legacy_notes=host.store.session(host.run_id)['state']['model_notes'],
            public_tool_operations=sum(e['kind']=='r3_tool_dispatch' for e in events),
            completed_invocation_scope_records=len(invocations),
            zero_forbidden_calls_in_completed_invocations=all(all(v==0 for v in i['scope'].values()) for i in invocations),
            failed_invocation_scope_records=sum(e['kind']=='r3_invocation_failure' for e in events)),
        limitation='Planned saved-boundary continuation only. No claim of recovery after a real in-flight crash, long-term reliability, cost reduction, or improved science. Formal source validation does not replace manual semantic review.')


if __name__=='__main__':main()
