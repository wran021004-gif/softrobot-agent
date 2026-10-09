"""Thin Strands entry for one authorized bounded three-segment study."""
from copy import deepcopy
from pathlib import Path
import argparse
import asyncio
import importlib.metadata
import json
import os
import platform
import time
from uuid import uuid4

from strands.tools.tools import PythonAgentTool
from strands.tools.executors import SequentialToolExecutor
from strands.hooks.events import BeforeModelCallEvent,AfterModelCallEvent,BeforeToolCallEvent,AfterToolCallEvent
from strands.types.exceptions import MaxTokensReachedException
from tools import research_mainline5_services as service
from tools.strands_pilot import build_harness
from tools.strands_pilot_r3 import LiveBoundary,live_model_class,pilot,pending,received,settle,record
from tools.platform_store import plain,zero
from tools.state_io import atomic_json,digest,read
from tools.research_execution import invoke

INSTRUCTIONS='''You are the sole principal for the first bounded Mainline5 study. Strands owns your conversation, sequential native tools, automatic context management and session restoration. Softrobot-Agent owns permissions, science, receipts and the cumulative ledger. Choose ONE supported three-flexible-segment template T2 or T3 using the linked T0-T3 and Mainline4 evidence. You own hypothesis, variables, method, interpretation and stopping. T0/T1 are historical context only. Do not repeat solved T0 or the Strands pilot. No workers.
Mainline4 selected holding_tip_speed_weight=0.0375, terminal_tip_speed_weight=0.1 on T0; its selected and fresh exact verification both passed. Testing that EXACT pair on T2/T3 is direct parameter transfer. Historical evidence followed by a NEW search is experience/method reuse, not verification of direct transfer. Either approach is allowed; do not force a direct-transfer experiment merely for reporting. The bounded T0 weight response was non-monotonic; it is not a universal law. Only historical V1 T0 executed controller9; V2 T1-T3 and Mainline4 new runs used controller10.
Nominal task and scientific fixed fields remain frozen: target [0.29,0.035,0.19] m, mount [0,0,0.15], gravity [0,0,-9.81], seed17, template-mapped zero q/v, duration0.35, control/sample0.01, physics0.0005, final holding0.05, both position limits0.01 and max speed0.02. Complete valid execution, coverage and independent 0-8N tendon limits required. candidate.family@2.0.0, controller.gvs_nmpc@10.0.0, structural_linear basis, horizon10 deadline truncation, tolerance1e-6, 120 iterations, CPU30s, feasible-return5/15s are fixed. Ideal tension, not motor execution. Different force capacity, guide/routing and tension initialization sources confound cross-template attribution. Local affine witnesses are not nonlinear feasibility certificates; curvature residual units rad/m.
Normally vary 1-3 parameters; per-template catalogs govern all values. Holding and terminal speed weights each [0.025,0.1]. Each selected-template baseline length +/-5%; section [0.95,1.05]; routing radius [0.98,1.02]; baseline/compliant/stiff materials. All structural scales are ABSOLUTE relative to the selected template's FIXED semantic_source, never relative to the previous candidate. Inactive variables stay fixed. Physical segment ownership, once-only shared guides and source-relative transforms are preserved; actual built values must fit that template's authorized range. Near length0.16, middle/far0.055 on T2/T3; session-wide union bounds are not per-template bounds.
Tools accept native business fields directly, without arguments/reason/tool_version envelopes. Multiple calls are allowed and execute sequentially, with matched result IDs. research_prepare_candidate returns a wrapper: use nested configuration for analysis. Full schemas govern decisions. selected_candidate and plan.source_candidate must contain EXACTLY candidate_id, configuration{artifact_id,media_type}, execution_id, owner_run_id. Explanations/claims belong in reasoning and interpretations. The CURRENT_BUSINESS_PACKET supplies exact F aliases: observations use exact recorded values; evidence and every plan include current feedback aliases. Prior decision, source, latest, retained reference and selected deliverable are separate roles and may share a configuration. Never invent aliases or provenance.
research_decide validates and executes your bounded batch and returns actual outcomes, exact applied values, ownership, acceptance and reused results. Include supporting and weakening observations, variable domains, fixed conditions, joint objectives, constraints, method, budget, verification and stopping. Required fixed_conditions: robot,task,acceptance,controller_implementation,other_numerical_settings. objectives: joint_reach_holding_acceptance,terminal_error_m,holding_max_error_m,holding_max_speed_m_s. constraints: frozen_acceptance,force_bounds,finite_valid_execution. verification: candidate.apply,simulation.run,evaluation.run,control.profile_report,bound_comparison,diagnostic_revision. plan predecessor_decision copies the current packet. Normally at most TWO new backends per batch; up to FOUR needs your explicit reason. Reserve at least 990s/4 tools per new backend and 4 model calls/4 tools/600s for interpretation; use generous realistic budget. Six development, two protected verification, two identified technical replacements, ten total backend attempts, sixty actual provider sends INCLUDING summaries/errors/retries,1024 workflow,48 public math/search,12h elapsed; final30min protected. Ceilings, not targets. No retry-to-pass: valid physical failure is completed evidence.
Coordinate method search.family_coordinate@1.0.0 generates continuous proposals (fractional-width step, candidates=null); initial source may require a contemporary run when historical implementation differs. Explicit method search.family_explicit@1.0.0 is your ordered enumeration (step=null). max_candidates includes initial/known proposals; max_backend_attempts and target_changed_configurations limit NEW executions. Include replication_reason for a known scientific point if exact implementation reuse is unavailable; any contemporary reference consumes development capacity. Domain includes source values. Use mathematical tools only to answer a concrete question; historical T2/T3 local evidence remains available with original references.
After each batch consume the actual feedback before next decision. You may narrow, change permitted variables, inspect diagnostics, use relevant math, or STOP. One failed control adjustment does not prove structural modification necessary. Target one complete new batch and subsequent feedback-consuming decision; do not add activity without scientific reason. For a consequential NEW selected candidate, selecting it at STOP requests one fresh EXACT confirmation; no tuning during verification. A verification result is returned for final STOP; keep failure visible. If no consequential candidate, selected_candidate=null is valid. Only STOP is allowed after verification. Final disposition distinguishes direct transfer tested/not tested, methods actually used, valid physical outcomes, improvement and its reference, fresh confirmation, supporting/weakening evidence and unknowns. Save a few applicable source-linked findings/procedures with scope and unknowns; no robustness, global optimality, real-time, universal weights or full Mainline5/Mainline6 completion claims.'''


def prepare(directory=service.RUN,*,offline=False):
    w=service.prepare(directory,offline=offline)
    if not w.spec.get('strands_bound'):
        service.import_t0_math(w);service.import_mainline4(w)
        w.spec.update(strands_bound=True,history_root=str(service.HISTORY_ROOT),
            start_source='Actual user goal creation time 1791547493; retained once including implementation',
            provider_settings=dict(model='deepseek-flash',thinking='enabled',reasoning_effort='high',max_tokens=32768,timeout_s=600.))
        provider=deepcopy(service.configuration()['policy']['model'])
        with w.store.transaction() as db:
            state=w.store.session(w.host.run_id,db)['state']
            state['pilot']=dict(activity_id=w.spec['activity_id'],mode='mainline5-strands',
                provider=provider,framework_session_id=w.host.run_id,live_model_requests=0,
                started_unix=w.spec['started_unix'],request_deadline_unix=w.spec['execution_cutoff_unix'],phase='prepared')
            w.store.update_state(db,w.host.run_id,state)
        service.persist(w);atomic_json(w.directory/'study_specification.json',w.spec)
    return w


def accepted(w,ref):
    row=next((r for r in w.rounds if r['accepted_decision']==ref),None)
    if row:return row
    row=dict(index=len(w.rounds),accepted_decision=ref,decision=w.store.artifact(ref))
    w.rounds.append(row);w.previous_decision=ref;service.persist(w)
    return row


def apply_decision(w,row):
    if row.get('feedback_result') or row.get('stop_processed'):return
    d=row['decision']['decision']
    if d.get('plan'):
        from extensions.tendon_family.finite_templates import template_id
        source=w.store.artifact(d['plan']['source_candidate']['configuration'])['effective']
        selected=template_id(source['robot']['structure']['data'])
        if selected not in ('T2','T3'):raise ValueError('MAINLINE5_REQUIRES_T2_OR_T3_SOURCE')
        if w.spec.get('selected_template') not in (None,selected):raise ValueError('MAINLINE5_SINGLE_TARGET_TEMPLATE')
        w.spec['selected_template']=selected
    service.execute(w,row)
    if d['action']=='stop':
        if w.status!='verification_reporting' and not w.verification:
            service.verify_selection(w)
        if w.verification and not row.get('verification_feedback_consumed'):
            current=w.store.artifact(w.feedback)['result']
            consumed=any(s['reference']==current for s in row['decision']['evidence_selectors'])
            if not consumed:w.status='verification_reporting'
            else:row['verification_feedback_consumed']=True
        row['stop_processed']=True
    service.persist(w)


def native_tools(w):
    tools=[]
    for name,version in service.NATIVE.items():
        definition=w.host.reg.get(name,version,'tool')
        schema=definition.input_schema.model_json_schema()
        if name=='research.decide':
            ref=dict(type='object',additionalProperties=False,required=['candidate_id','configuration','execution_id','owner_run_id'],
                properties={k:dict(type='string') for k in ('candidate_id','execution_id','owner_run_id')})
            ref['properties']['configuration']=dict(type='object',additionalProperties=False,required=['artifact_id','media_type'],
                properties={k:dict(type='string') for k in ('artifact_id','media_type')})
            schema['properties']['selected_candidate']={'anyOf':[{'type':'null'},ref]}
            schema['$defs']['SearchBatchPlan']['properties']['source_candidate']={'anyOf':[{'type':'null'},ref]}
        def handler(use,_name=name,_version=version,**kwargs):
            request_id='mainline5-native-'+use['toolUseId']
            old=w.store.lookup(w.host.run_id,request_id)
            if not old:service.configure(w)
            if w.status=='model_stopped':raise ValueError('RESEARCH_STOP_SEALED')
            if _name not in w.store.session(w.host.run_id)['state']['role_context']['phase_tools']:
                raise ValueError('TOOL_OUTSIDE_CURRENT_RESEARCH_PHASE')
            if _name=='research.decide' and use['input'].get('plan'):
                from extensions.tendon_family.finite_templates import template_id
                plan=use['input']['plan'];candidate=plan.get('source_candidate') or {}
                from tools.study_history import select_source
                select_source(w.records,candidate)
                source=w.store.artifact(candidate['configuration'])['effective']
                target=template_id(source['robot']['structure']['data'])
                if target not in ('T2','T3') or w.spec.get('selected_template') not in (None,target):
                    raise ValueError('MAINLINE5_SINGLE_T2_OR_T3_SOURCE_REQUIRED')
                if 'template' in plan['variables']:raise ValueError('MAINLINE5_TARGET_TEMPLATE_FIXED_WITHIN_STUDY')
                if (plan.get('max_backend_attempts') or plan['max_candidates'])>2 and not plan.get('rationale'):
                    raise ValueError('LARGER_BATCH_REQUIRES_PRINCIPAL_REASON')
            receipt=invoke(w.host,_name,use['input'],request_id=request_id)
            result=dict(receipt=receipt,content=w.store.artifact(receipt['output']) if receipt.get('output') else None)
            if _name=='research.decide' and receipt['execution_status']=='completed':
                row=accepted(w,result['content']['reference']);apply_decision(w,row)
                result.update(research_status=w.status,feedback=w.store.artifact(w.feedback))
            return dict(toolUseId=use['toolUseId'],status='success' if receipt['execution_status']=='completed' else 'error',
                content=[{'text':json.dumps(result,ensure_ascii=False)}])
        tools.append(PythonAgentTool(name.replace('.','_'),dict(name=name.replace('.','_'),
            description=definition.description if hasattr(definition,'description') else name,
            inputSchema={'json':schema}),handler))
    return tools


class ResearchBoundary(LiveBoundary):
    def __init__(self,host,transport=None):
        super().__init__(host,transport,allow_truncated_response=True)

    async def handle_async_request(self,request):
        wire=json.loads(request.content)
        if wire.get('tools') and not pilot(self.host).get('unconsumed_response'):
            from tools.current_research_authority import check_payload
            # Bind the actual Strands system context, never a historical fixed message index.
            content=next(m['content'] for m in wire['messages'] if m['role']=='system')
            packet=json.loads(content.split('\nCURRENT_BUSINESS_PACKET\n',1)[1])
            check_payload(self.host,wire,research_packet=packet)
        return await super().handle_async_request(request)


def build_live(w,*,transport=None,key=None):
    boundary=ResearchBoundary(w.host,transport)
    if key is None:
        from examples.gvs_nmpc_route_experiment import load_credential
        load_credential(Path.home()/'.codex/.env');key=os.environ['DEEPSEEK_API_KEY']
    tools=native_tools(w)
    agent=build_harness(w.host,transport=boundary,api_key=key,instructions=INSTRUCTIONS,
        model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),research_tools=tools,
        configuration_path=w.directory/'framework_configuration.json',session_directory=w.directory/'framework_sessions')
    auxiliary={}
    def before_model(event):
        if w.status in ('model_stopped','execution_stopped'):
            event.cancel='Mainline5 business disposition sealed';return
        saved=pilot(w.host).get('unconsumed_response')
        if saved:
            row=w.store.lookup(w.host.run_id,saved)
            original=w.store.artifact(json.loads(row['inputs'])[0]) if 'inputs' in row else None
            if original is None:
                sent=next(e for e in w.store.events(w.host.run_id) if e['kind']=='r3_request' and e['request_id']==saved)
                original=w.store.artifact(w.store.artifact(sent['outputs'][0])['request'])
            agent.system_prompt=next(m['content'] for m in original['messages'] if m['role']=='system')
            decision=next(t['function']['parameters'] for t in original.get('tools',[]) if t['function']['name']=='research_decide')
            for t in tools:
                if t.tool_name=='research_decide':t.tool_spec['inputSchema']['json']['properties']['action']['enum']=decision['properties']['action']['enum']
            return  # Confirmed replay adds no send; dispatch still revalidates current authority.
        packet=service.configure(w)
        agent.system_prompt=INSTRUCTIONS+'\nCURRENT_BUSINESS_PACKET\n'+json.dumps(packet,ensure_ascii=False)
        allowed=packet['capabilities']['legal']
        for t in tools:
            if t.tool_name=='research_decide':t.tool_spec['inputSchema']['json']['properties']['action']['enum']=list(allowed)
    def before_tool(event):
        use=event.tool_use
        if w.store.remaining()['remaining']['tool_calls']<1:raise ValueError('PUBLIC_TOOL_BUDGET_EXHAUSTED')
        record(w.host,'mainline5_native_dispatch',dict(tool_use=use))
        if use['name']=='retrieve_context':
            row,_=w.store.reserve(w.host.run_id,'mainline5-framework-'+use['toolUseId'],digest(use),'framework-retrieval',
                {**zero(),'tool_calls':1},kind='framework_tool');auxiliary[use['toolUseId']]=row
    def after_tool(event):
        use=event.tool_use;record(w.host,'mainline5_native_result',dict(tool_use=use,result=event.result))
        row=auxiliary.pop(use['toolUseId'],None)
        business=w.store.lookup(w.host.run_id,'mainline5-native-'+use['toolUseId'])
        if row is None and (not business or json.loads(business['charged'])['tool_calls']==0):
            row,_=w.store.reserve(w.host.run_id,'mainline5-public-'+use['toolUseId'],digest(use),'public-native',
                {**zero(),'tool_calls':1},kind='public_tool')
        if row:w.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=row['caller'],
            tool_id=use['name'],tool_version='1.0.0',execution_status='completed',charged=zero()),event.result,kind='public_tool')
    agent.hooks.add_callback(BeforeModelCallEvent,before_model)
    agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
    agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    def disable_retry(event):event.retry=False
    agent.hooks.add_callback(AfterModelCallEvent,disable_retry,order=1000)
    return agent


def recover_business(w):
    for row in pending(w.host):
        response=received(w.host,row['request_id'])
        if response:settle(w.host,row,response)
        else:w.store.mark_unknown(w.host.run_id,row['request_id'])
    ref=w.store.session(w.host.run_id)['state'].get('handoffs',{}).get('research_decision')
    if ref:apply_decision(w,accepted(w,ref))
    if pending(w.host):raise ValueError('UNKNOWN_PROVIDER_OUTCOME_REQUIRES_RECONCILIATION')


def run(directory=service.RUN):
    w=service.restore(directory)
    if w.spec['offline']:raise ValueError('OFFLINE_FIXTURE_CANNOT_RUN_PAID_WORK')
    recover_business(w)
    if w.status=='model_stopped':service.export(w);return w
    if not (w.directory/'implementation_freeze.json').exists():raise ValueError('FREEZE_COMMITTED_IMPLEMENTATION_FIRST')
    if w.status not in ('verification_reporting','execution_stopped'):w.status='running'
    service.persist(w)
    try:
        agent=build_live(w)
        prompt=None if pilot(w.host).get('unconsumed_response') else (
            'Continue the same authorized Mainline5 activity from CURRENT_BUSINESS_PACKET. Consume actual saved feedback and deliver research_decide. Do not repeat sealed executions.')
        asyncio.run(converse(w,agent,prompt))
    except Exception as exc:
        atomic_json(w.directory/'failure.json',dict(type=type(exc).__name__,message=str(exc),usage=w.store.remaining()))
        service.persist(w);service.export(w);raise
    service.persist(w);service.export(w)
    return w


async def converse(w,agent,prompt):
    # Keep the injected AsyncOpenAI client's connections on one event loop
    # across explicit continuation calls and framework summary requests.
    while w.status not in ('model_stopped','execution_stopped'):
        if time.time()>=w.spec['execution_cutoff_unix']:raise ValueError('DELIVERY_WINDOW_REACHED')
        try:await agent.invoke_async(prompt)
        except MaxTokensReachedException:
            record(w.host,'mainline5_incomplete_response',dict(reason='max_tokens',
                partial_history_owner='Strands',decision_accepted=False))
        if w.status not in ('model_stopped','execution_stopped'):
            prompt=('No final formal research disposition was received. Continue through a native tool now. '
                'Use the current exact schema and F aliases. Choose one justified bounded next action; '
                'you do not need to solve the whole study before observing its first outcomes. '
                'If the preceding response was length-truncated, it is retained as incomplete reasoning, not an accepted decision. '
                'Do not replay sealed experiments; STOP remains available when justified.')


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','bind','run','recover','status','export'])
    p.add_argument('--directory',type=Path,default=service.RUN);args=p.parse_args()
    if args.action=='prepare':w=prepare(args.directory)
    elif args.action in ('run','recover'):w=run(args.directory)
    else:
        w=service.restore(args.directory)
        if args.action=='bind':service.bind(w)
        elif args.action=='export':service.export(w)
    print(json.dumps(dict(status=w.status,selected_template=w.spec.get('selected_template'),
        usage=w.store.remaining(),verification=w.verification),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
