"""One live principal, accepted Strands harness, native typed plans and tools."""
from pathlib import Path
import argparse
import asyncio
import json
import os
import subprocess
import time
from schemas.platform import ProjectConfig
from schemas.casadi_feedback import Plan,CloseoutPlan,ActivityPlan
from tools.platform_host import Host
from tools.platform_store import plain,zero
from tools.research_execution import invoke
from tools.state_io import atomic_json,read,digest
from tools.spec_tools import ROOT
from tools.casadi_feedback_service import ACTIVITY,budget,RESERVATIONS,SPEC,CEILINGS

RUN=ROOT/'runs'/ACTIVITY
OUT=ROOT/'evidence/casadi_nmpc_research_20261010'
LIMITS=dict(model_calls=CEILINGS['actual_provider_requests'],tool_calls=CEILINGS['public_workflow_calls'],backend_solves=CEILINGS['physical_launches'],worker_calls=0,wall_s=CEILINGS['overall_activity_s'])
TOOLS={name:'1.0.0' for name in ['math.casadi_feedback_'+s for s in ('solve','replay','plan')]+['evidence.read']}
AUTHORIZATION=SPEC['authorization']+'; authorized non-secret research payload to https://api.deepseek.com/chat/completions; credentials for authentication only; scoped commit and ordinary push'

def activity_start():
    path=RUN/'activity_clock.json'
    if not path.exists():atomic_json(path,dict(started_unix=SPEC['started_unix'],source='goal creation; includes engineering from task start'))
    return read(path)['started_unix']


def configuration():
    from tools.research_v2 import native_configuration
    from tools.design_optimization import resolved_input
    from schemas.design_optimization import DesignOptimizationProblem
    source=DesignOptimizationProblem.model_validate(read(ROOT/'examples/casadi_codesign/case_A.json')['physical_source'])
    base=native_configuration(ACTIVITY)
    allowances={name:dict(timeout_s=RESERVATIONS.get(name.rsplit('_',1)[-1],30.)+30.,reserve_s=RESERVATIONS.get(name.rsplit('_',1)[-1],1.)) for name in TOOLS}
    base['policy'].update(budget=LIMITS,allowed_tools=[],tool_bindings=TOOLS,operation_allowances=allowances)
    base['policy']['model']['max_turns']=12
    values=dict(segment_count=2,proximal_tendons=3,distal_tendons=3,lengths_m=[.16,.11],material='baseline',
        section_scale=1.,routing_scale=1.,pretension_n=.2,holding_tip_speed_weight=.05,terminal_tip_speed_weight=.1)
    return resolved_input(source,values,ACTIVITY,base['policy'])


def host():return Host(RUN,ACTIVITY,actor='casadi-feedback-research')


def prepare():
    h=host();STARTED=activity_start()
    if h.store.db.exists():return h
    h.store.create(ProjectConfig(project_id=ACTIVITY,grant_id=ACTIVITY+'-authorized',authorization_source=AUTHORIZATION,
        budget=LIMITS,exclusive_resources={'provider_request':1,'backend.family_mujoco':1}))
    h.create(configuration());h.resume()
    with h.store.transaction() as db:
        cfg=h.store.session(ACTIVITY,db)['snapshot']['input'];state=h.store.session(ACTIVITY,db)['state']
        state.update(started_unix=STARTED,cutoff_unix=STARTED+CEILINGS['overall_activity_s']-CEILINGS['delivery_reserve_s'],numerical_s=0.,investigation_s=0.,nlp_solves=0,
            python='D:/softrobot-agent/.mainline5-env/Scripts/python.exe',
            results=[],plans=[],dispatched_candidates=[],research_status='ready',spec_identity=digest(read(ROOT/'examples/casadi_nmpc/specification.json')))
        state['pilot']=dict(activity_id=ACTIVITY,provider=cfg['policy']['model'],framework_session_id=ACTIVITY,
            live_model_requests=0,started_unix=STARTED,request_deadline_unix=STARTED+CEILINGS['overall_activity_s']-CEILINGS['delivery_reserve_s'])
        from tools.casadi_closed_loop import import_latest
        history,results,sources=import_latest(h.store,db)
        state.update(historical=history,results=results,candidate_sources=sources,
            refined_grid_supported=True,speed_check_passed=True,local_ad='reverse',replays=0)
        h.store.update_state(db,ACTIVITY,state)
        h.store.event(db,ACTIVITY,'historical_import','read_only_provenance_preserved',outputs=[h.store.put(db,history)])
    atomic_json(RUN/'activity.json',dict(activity_id=ACTIVITY,authorization=AUTHORIZATION,started_unix=STARTED,limits=LIMITS,
        numerical_limit_s=CEILINGS['total_numerical_s'],initial_investigation_limit_s=0.,delivery_reserve_s=1800.,nlp_limit=2,replay_limit=3,
        solve_limit_s=900.,ipopt_cpu_wall_s=570.,process_reservations=RESERVATIONS,
        physical_launch_limit=2,physical_allowance_s=1800.,protected_provider_sends=4,
        base_commit=SPEC['base_commit'],historical_activities='sealed STOP; unused allowance unavailable'))
    return h


def bind(h,repair=False,reason=None):
    from tools.platform_tasks import compile_input
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('COMMIT_BEFORE_BIND_OR_MIGRATION')
    state=h.store.session(ACTIVITY)['state']
    if state.get('pending'):raise ValueError('PENDING_OUTCOME_BLOCKS_MIGRATION')
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:raise ValueError('UNSEALED_RESERVATION_BLOCKS_BIND')
        if not repair and db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]:raise ValueError('INITIAL_BIND_REQUIRES_ZERO_CALLS')
    old=h.store.session(ACTIVITY)['snapshot'];snapshot=compile_input(old['input'],h.reg)
    if snapshot['instance_identity']!=old['instance_identity']:raise ValueError('MIGRATION_CHANGED_FROZEN_TASK')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    snapshot.update(project_commit=commit,worktree_dirty=False)
    with h.store.transaction() as db:
        ref=h.store.put(db,snapshot);db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(ref.artifact_id,ACTIVITY))
        state=h.store.session(ACTIVITY,db)['state']
        if repair:
            record=dict(previous_commit=state['freeze'],commit=commit,reason=reason,reset_budgets=False,
                dependencies_changed=[k for k,v in snapshot['dependencies'].items() if old['dependencies'].get(k)!=v])
            repair_ref=h.store.put(db,record);state.setdefault('feedback_repairs',[]).append(plain(repair_ref))
            h.store.event(db,ACTIVITY,'scoped_repair_migration','committed',outputs=[repair_ref])
        state['freeze']=commit;h.store.update_state(db,ACTIVITY,state)
        h.store.event(db,ACTIVITY,'implementation_freeze','committed',outputs=[ref])
    atomic_json(RUN/'implementation_freeze.json',dict(commit=commit,snapshot_reference=plain(ref),dependency_identity=digest(snapshot['dependencies'])))


def compact_result(value):
    keys=('status','termination_reason','iterations','solver_termination','checkpoint_reference','candidate_export_status',
        'trajectory_metrics','original_task_feasible','original_task_gaps','hard_max_normalized_violation',
        'relaxed_nlp_feasible','objective_components','physical_eligible','costs_s','process_elapsed_s',
        'acceptance','control','revision','resolved_configuration','wiring_reference','holding_motion',
        'sampling','unknowns','failure_categories','execution_references','actual_duration_s','completed_control_updates',
        'nmpc_internal_solves','offline_nlp_slots_charged')
    result={k:value[k] for k in keys if k in value}
    if value.get('replay'):result['replay']={k:v for k,v in value['replay'].items() if k not in ('integration_counts','sampled_evaluator')}
    if value.get('profile'):
        result['control_model_feedback']={k:v for k,v in value['profile'].items() if k not in ('task','numerical_preparation','control_parameters','execution_scope')}
    return result


def packet(h):
    state=h.store.session(ACTIVITY)['state'];history=state['historical'];results=[]
    for row in state['results']:
        value=h.store.artifact(row['reference'])
        if row['operation'] in ('diagnose','speed') and row.get('imported'):
            detail={'status':value['status'],'reuse':'Already executed mechanics/mesh/precision diagnosis and unsuccessful AD speed trial; do not repeat.'}
        else:detail=compact_result(value)
        results.append(dict(operation=row['operation'],reference=row['reference'],candidate=row.get('candidate'),
            imported=row.get('imported',False),source_activity=row.get('source_activity'),**detail))
    candidates=[dict(reference=dict(artifact_id=aid,media_type='application/json'),**source,
        design_values={k:h.store.artifact(dict(artifact_id=aid,media_type='application/json'))[k] for k in ('d','lengths_m','selection')})
        for aid,source in state['candidate_sources'].items()]
    return dict(frozen_specification=SPEC,candidates=candidates,results=results,imported_history=history,
        established_facts=dict(prior_cycle='Two NLP attempts, two completed BDF replays, nine actual sends and accepted native STOP; both failed independent acceptance.',
            initial=dict(iterations=22,predicted_holding_speed_m_s=.01974186,bdf_holding_speed_m_s=.04312197),
            revision=dict(iterations=34,termination='Maximum_CpuTime_Exceeded',selected_iteration=3,predicted_holding_speed_m_s=.01915398,bdf_holding_speed_m_s=.04218082),
            interpretation='About 2.18 percent replay speed improvement; initialization also changed and revision did not establish convergence. No isolated objective effect or unique cause.',
            distinction='Optimization nodes, saved-input dense BDF and future NMPC feedback MuJoCo are separate evidence. NMPC success would not validate the old open-loop schedule.'),
        accepted_plans=state['plans'],research_status=state['research_status'],remaining_budget=budget(h.store),
        capabilities=dict(research_plan='Choose solve, referenced diagnosis, diagnostic_replay, closed_loop, control_revision or stop. One expensive experiment per decision; any action may be first.',
            evidence_read='Exact immutable EvidenceRef and JSON pointer; compact facts already supplied',
            physical='At most two MuJoCo feedback executions, no real hardware; failed open-loop acceptance does not block exploratory eligibility.'))




INSTRUCTIONS='You are the sole research principal in a bounded research activity. Choose freely from the native research_plan action menu: solve (one existing mathematical choice followed by independent BDF), diagnose (read-only referenced synthesis, no new numerical experiment), diagnostic_replay (one supported BDF numerical operation), closed_loop (evaluate an immutable saved candidate structure under target-based NMPC), control_revision (same candidate, preceding closed-loop result EvidenceRef, exact changes to two weights), or stop. Any may be the first action, including a justified STOP using imported evidence. No mandatory new NLP, replay or NMPC. Do not rediscover supplied history. Engineering and prior numerical diagnostics were implemented by Codex; your original choices remain separate from facts and corrections. All experiment requests need hypothesis, supporting_evidence, expected_observation, weakening_observation, fixed_conditions, parameters, revision_or_stop_rule, disposition and limitations. Closed-loop control.candidate is an exact immutable candidate reference, never manually reconstruct lengths. Holding speed weight default .05 and terminal speed weight default .10, both allowed .025 to .10. Other NMPC recipe fields frozen, initialization initial_state_pretension numerical guesses (not equilibrium). Saved offline schedule is not NMPC reference or applied sequence. Failed historical open-loop replay does not forbid valid structure-under-feedback testing or change historical acceptance. Control-only revision cites the preceding result, keeps candidate unchanged, and changes weights. Changing structure and control requires closed_loop and explicit joint attribution. Consume actual returned evidence before another experiment. Final STOP must cite all new scientific results if any. Preserve frozen two segments, six ideal bounded tensions 0..8 N, topology, materials, routing, basis, target, mount, gravity, named zero initial state, duration .35 s, control/sample .01 s, physics .0005 s, inclusive final .05 s holding, position .01 m/speed .02 m/s limits and seed17. Existing single constant d in [-1,1] only. Two new offline full-horizon NLP attempts, three BDF attempts, two MuJoCo launches including unsuccessful launches,900 s per NLP worker (570 s IPOPT),450 s per BDF,1800 s simulation plus existing30/60 s evaluation/profile,7200 total scientific/check/recovery seconds,16 actual provider sends including auxiliary/retries with last4 for feedback and STOP,64 public calls,6h including engineering with final30min delivery protected,zero other LLMs/hardware. NMPC internal solves belong to their launch, not standalone NLP slots. Ceilings are not quotas. Existing numerical checkpoint recovery, dependency guard and engineering pause apply. Acceptance is sampled .01 s for closed loop, unlike dense .0005 s BDF; no continuous-time or real-time guarantee. Report scientific, numerical, engineering and missing evidence distinctly. Do not infer global optimum, physical impossibility, unique cause, LLM superiority or old open-loop validation. Accepted native STOP seals all further provider sends.'


def feedback_context_references(h):
    """Only native feedback containing new executions is relevant in closeout."""
    references=[]
    for event in h.store.events(ACTIVITY):
        if event['kind']!='model_original_tool_feedback':continue
        value=h.store.artifact(event['outputs'][0]);use=value['tool_use']
        if use['name']!='research_plan' or use['input'].get('action') not in ('solve','diagnose','diagnostic_replay','closed_loop','control_revision'):continue
        result=value['result']
        if result['status']!='success':continue
        for index,content in enumerate(result.get('content',[])):
            try:feedback=json.loads(content.get('text','{}'))
            except ValueError:continue
            if feedback.get('operations'):references.append(use['toolUseId']+'_'+str(index))
    return references


def provider_guard(h,wire):
    """Check every actual send, including auxiliary requests and retries."""
    state=h.store.session(ACTIVITY)['state']
    if state.get('research_status')=='stopped':raise ValueError('ACCEPTED_STOP_NO_MORE_SENDS')
    if state.get('engineering_pause'):raise ValueError('ENGINEERING_PAUSE_NO_MORE_SENDS')
    if state.get('pending'):raise ValueError('UNKNOWN_NUMERICAL_OUTCOME_NO_PROVIDER_SEND')
    if not h.compatibility()['compatible']:raise ValueError('DEPENDENCIES_CHANGED_BEFORE_PROVIDER_SEND')
    if h.store.remaining()['remaining']['model_calls']<=4:
        definitions={t['function']['name']:t['function'] for t in wire.get('tools',[])}
        plan=definitions.get('research_plan',{}).get('parameters',{})
        action=plan.get('properties',{}).get('action',{})
        if action.get('const')!='stop' or set(definitions)-{'research_plan','evidence_read','retrieve_context'}:
            raise ValueError('PROTECTED_SEND_REQUIRES_NATIVE_STOP_SCHEMA_NO_AUXILIARY_SUMMARY')
        retrieval=definitions.get('retrieve_context')
        if retrieval:
            advertised=retrieval.get('parameters',{}).get('properties',{}).get('reference',{}).get('enum')
            if advertised is None or not set(advertised)<=set(feedback_context_references(h)):
                raise ValueError('PROTECTED_RETRIEVAL_REQUIRES_NEW_EXECUTION_FEEDBACK_REFERENCES')


from tools.strands_pilot_r3 import LiveBoundary


def protect_context_tool(retrieval,references):
    from copy import deepcopy
    from strands.tools.tools import normalize_tool_spec
    spec=deepcopy(normalize_tool_spec(retrieval.tool_spec))
    spec['inputSchema']['json']['properties']['reference']['enum']=references
    retrieval.tool_spec=spec


class FeedbackBoundary(LiveBoundary):
    async def handle_async_request(self,request):
        if not self.host.store.session(ACTIVITY)['state']['pilot'].get('unconsumed_response'):
            provider_guard(self.host,json.loads(request.content))
        return await super().handle_async_request(request)


def execute_batch(h,plan,accepted,key):
    """Preserve unexecuted choices when delivery or extraction fails."""
    operations=[]
    for index,choice in enumerate(plan.candidates):
        args=dict(**plain(choice),batch=accepted['batch'],plan_reference=accepted['plan_reference'],candidate_index=index)
        receipt=invoke(h,'math.casadi_feedback_solve',args,request_id=key+'-solve-'+str(index))
        feedback=h.store.artifact(receipt['output']) if receipt.get('output') else None
        operation=dict(receipt=receipt,feedback=feedback);operations.append(operation)
        detail=feedback.get('detail',{}) if feedback else {}
        error=receipt['execution_status']!='completed' or detail.get('status') in ('engineering_error','numerical_error')
        candidate=detail.get('candidate_reference')
        if candidate and not error:
            rr=invoke(h,'math.casadi_feedback_replay',dict(candidate=candidate),request_id=key+'-replay-'+str(index))
            replay_feedback=h.store.artifact(rr['output']) if rr.get('output') else None
            operation['replay']=dict(receipt=rr,feedback=replay_feedback)
            error=rr['execution_status']!='completed' or (replay_feedback or {}).get('detail',{}).get('status') in ('engineering_error','numerical_error')
        if error:
            with h.store.transaction() as db:
                state=h.store.session(ACTIVITY,db)['state']
                state['engineering_pause']=dict(plan_reference=accepted['plan_reference'],failed_index=index,
                    unexecuted_choices=[plain(c) for c in plan.candidates[index+1:]],reason='Interface, extraction, serialization or delivery failure')
                h.store.update_state(db,ACTIVITY,state)
            break
    return operations


async def converse(h):
    from strands.tools.tools import PythonAgentTool
    from strands.tools.executors import SequentialToolExecutor
    from strands.hooks.events import BeforeModelCallEvent,BeforeToolCallEvent,AfterToolCallEvent
    from tools.strands_pilot import build_harness
    from tools.strands_pilot_r3 import LiveBoundary,live_model_class,record,pending
    from examples.gvs_nmpc_route_experiment import load_credential
    if pending(h):raise ValueError('UNKNOWN_PROVIDER_OUTCOME_INSPECT_BEFORE_SEND')
    load_credential(Path.home()/'.codex'/'.env')
    if not os.environ.get('DEEPSEEK_API_KEY'):raise ValueError('DEEPSEEK_API_KEY_UNAVAILABLE')
    boundary=FeedbackBoundary(h,allow_truncated_response=True)
    def plan_handler(use,**kwargs):
        receipt=invoke(h,'math.casadi_feedback_plan',use['input'],request_id='native-'+use['toolUseId'])
        result=h.store.artifact(receipt['output']) if receipt.get('output') else None
        value=dict(plan_receipt=receipt,plan_result=result,operations=[])
        if receipt['execution_status']=='completed':
            plan=Plan.model_validate(use['input']);accepted=result['detail']
            if plan.action=='solve':
                value['operations']=execute_batch(h,plan,accepted,'native-'+use['toolUseId'])
            elif plan.action in ('closed_loop','control_revision'):
                from tools.casadi_closed_loop import run_closed_loop
                try:
                    feedback=run_closed_loop(h,plan.control,accepted['plan_reference'],plan.action)
                    value['operations'].append(dict(feedback=dict(detail=compact_result(feedback['detail']),evidence_reference=feedback['evidence_reference'])))
                except Exception as exc:
                    with h.store.transaction() as db:
                        state=h.store.session(ACTIVITY,db)['state']
                        failure=dict(status='engineering_error',exception_type=type(exc).__name__,reason=str(exc),pending=state.get('pending'))
                        ref=h.store.put(db,failure);state['engineering_pause']=dict(reference=plain(ref),reason=str(exc))
                        h.store.update_state(db,ACTIVITY,state)
                    value['operations'].append(dict(feedback=failure,evidence_reference=plain(ref)))
            elif plan.action=='diagnose':
                detail=dict(status='completed',scope='Read-only referenced diagnosis; model hypothesis remains in original plan',
                    plan_reference=accepted['plan_reference'],evidence=[plain(r) for r in plan.supporting_evidence],numerical_s=0.,
                    facts=[dict(reference=plain(r),**compact_result(h.store.artifact(r))) for r in plan.supporting_evidence])
                with h.store.transaction() as db:
                    ref=h.store.put(db,detail);state=h.store.session(ACTIVITY,db)['state']
                    state['results'].append(dict(operation='referenced_diagnosis',reference=plain(ref),candidate=None))
                    h.store.update_state(db,ACTIVITY,state)
                value['operations'].append(dict(feedback=detail,evidence_reference=plain(ref)))
            elif plan.action=='diagnostic_replay':
                rr=invoke(h,'math.casadi_feedback_replay',dict(candidate=plain(plan.diagnostic_candidate)),request_id='native-'+use['toolUseId']+'-diagnostic')
                value['operations'].append(dict(receipt=rr,feedback=h.store.artifact(rr['output']) if rr.get('output') else None))
        value['remaining_budget']=budget(h.store);record(h,'model_plan_execution_feedback',value)
        return dict(toolUseId=use['toolUseId'],status='success' if receipt['execution_status']=='completed' else 'error',content=[dict(text=json.dumps(value))])
    def read_handler(use,**kwargs):
        if h.store.remaining()['remaining']['model_calls']<=4:
            state=h.store.session(ACTIVITY)['state']
            allowed={r['reference']['artifact_id'] for r in state['results'] if not r.get('imported')}
            if use['input']['reference']['artifact_id'] not in allowed:
                return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text='Protected closeout: consume already supplied new results and submit STOP; historical rediscovery is unavailable.')])
        receipt=invoke(h,'evidence.read',use['input'],request_id='native-'+use['toolUseId'])
        value=dict(receipt=receipt,content=h.store.artifact(receipt['output']) if receipt.get('output') else None)
        return dict(toolUseId=use['toolUseId'],status='success' if receipt['execution_status']=='completed' else 'error',content=[dict(text=json.dumps(value))])
    tools=[PythonAgentTool('research_plan',dict(name='research_plan',description='Choose a bounded mathematical solve, referenced diagnosis, candidate feedback execution, control revision, or evidence-based STOP',inputSchema={'json':ActivityPlan.model_json_schema()}),plan_handler)]
    definition=h.reg.get('evidence.read');tools.append(PythonAgentTool('evidence_read',dict(name='evidence_read',description=definition.description,inputSchema={'json':definition.input_schema.model_json_schema()}),read_handler))
    agent=build_harness(h,transport=boundary,api_key=os.environ['DEEPSEEK_API_KEY'],instructions=INSTRUCTIONS,
        model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),research_tools=tools,
        configuration_path=RUN/'framework_configuration.json',session_directory=RUN/'framework_sessions')
    cancelled=[]
    def before_model(event):
        state=h.store.session(ACTIVITY)['state']
        if state['pilot'].get('unconsumed_response'):
            key=state['pilot']['unconsumed_response'];ev=next(e for e in h.store.events(ACTIVITY) if e['kind']=='r3_request' and e['request_id']==key)
            original=h.store.artifact(h.store.artifact(ev['outputs'][0])['request'])
            agent.system_prompt=next(m['content'] for m in original['messages'] if m['role']=='system');return
        if state['research_status']=='stopped':
            event.cancel='Original native final disposition sealed; no extra closing provider send';return
        compatibility=h.compatibility()
        if not compatibility['compatible']:
            record(h,'engineering_dependency_checkpoint',compatibility,status='migration_required')
            cancelled.append('Committed repair migration required before another provider send')
            event.cancel=cancelled[-1];return
        current=packet(h);record(h,'model_decision_packet',current)
        agent.system_prompt=INSTRUCTIONS+'\nCURRENT_RESEARCH_PACKET\n'+json.dumps(current)
        if current['remaining_budget']['provider_requests']<=4:
            tools[0].tool_spec={**tools[0].tool_spec,'inputSchema':{'json':CloseoutPlan.model_json_schema()}}
            from copy import deepcopy
            schema=deepcopy(tools[1].tool_spec['inputSchema']['json'])
            schema['$defs']['EvidenceRef']['properties']['artifact_id']['enum']=[r['reference']['artifact_id'] for r in state['results'] if not r.get('imported')]
            tools[1].tool_spec={**tools[1].tool_spec,'inputSchema':{'json':schema}}
            retrieval=agent.tool_registry.registry.get('retrieve_context')
            if retrieval:
                protect_context_tool(retrieval,feedback_context_references(h))
            agent.system_prompt+='\nPROTECTED CLOSEOUT: native plan schema now permits STOP only; evidence reads are restricted to outstanding new-result references. Actual remaining sends are those in remaining_budget, with no separate extra reserve.'
    def before_tool(event):
        record(h,'model_original_tool_request',dict(tool_use=event.tool_use))
        if (h.store.remaining()['remaining']['model_calls']<=4 and event.tool_use['name']=='retrieve_context'
            and event.tool_use['input'].get('reference') not in feedback_context_references(h)):
            event.cancel_tool='Protected closeout permits retrieval of new execution feedback only.'
    def after_tool(event):
        record(h,'model_original_tool_feedback',dict(tool_use=event.tool_use,result=event.result))
        key='native-'+event.tool_use['toolUseId']
        if h.store.lookup(ACTIVITY,key) is None:
            row,_=h.store.reserve(ACTIVITY,key,digest(event.tool_use),h.actor,{**zero(),'tool_calls':1,'wall_s':0.})
            h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=h.actor,
                tool_id=event.tool_use['name'],tool_version='1.0.0',
                execution_status='completed' if event.result['status']=='success' else 'failed',charged=zero()),event.result,
                kind='native_context' if event.tool_use['name']=='retrieve_context' else 'native_rejected')
    agent.hooks.add_callback(BeforeModelCallEvent,before_model);agent.hooks.add_callback(BeforeToolCallEvent,before_tool);agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    try:
        while h.store.session(ACTIVITY)['state']['research_status']!='stopped':
            from strands.types.exceptions import MaxTokensReachedException
            try:
                result=await agent.invoke_async('Use the current research packet. Choose any supported action or STOP, consume returned evidence, and decide the next direction. Final disposition must cite real evidence.')
                record(h,'model_original_turn',dict(result=str(result)))
            except MaxTokensReachedException:record(h,'model_incomplete_response',dict(reason='max_tokens',partial_history_owner='Strands'))
            if cancelled:raise ValueError(cancelled[-1])
            if h.store.session(ACTIVITY)['state'].get('engineering_pause'):raise ValueError('ENGINEERING_PAUSE_NO_MORE_PROVIDER_SENDS')
            if pending(h):raise ValueError('UNKNOWN_PROVIDER_OUTCOME_NO_BLIND_REPEAT')
            if not h.compatibility()['compatible']:raise ValueError('COMMITTED_REPAIR_MIGRATION_REQUIRED_NO_MORE_SENDS')
    except Exception as exc:
        record(h,'live_cycle_incomplete',dict(exception_type=type(exc).__name__,message=str(exc),remaining_budget=budget(h.store)),status='incomplete');raise
    finally:await boundary.aclose()


def export(h):
    import tarfile,io,hashlib
    OUT.mkdir(parents=True,exist_ok=True);manifest=[]
    with h.store.connect(True) as db,tarfile.open(OUT/'immutable_artifacts.tar.gz','w:gz') as tar:
        for row in db.execute('SELECT id,media,body FROM artifacts ORDER BY id'):
            name='artifacts/'+row['id']+('.json' if row['media']=='application/json' else '.bin')
            info=tarfile.TarInfo(name);info.size=len(row['body']);tar.addfile(info,io.BytesIO(row['body']))
            manifest.append(dict(name=name,sha256=row['id'],bytes=info.size,media=row['media']))
        calls=[dict(row) for row in db.execute('SELECT * FROM calls ORDER BY rowid')]
    state=h.store.session(ACTIVITY)['state']
    for name,value in [('activity.json',read(RUN/'activity.json')),('implementation_freeze.json',read(RUN/'implementation_freeze.json')),
        ('state.json',state),('events.json',h.store.events(ACTIVITY)),('ledger.json',h.store.remaining()),('calls.json',calls),('final_packet.json',packet(h))]:atomic_json(OUT/name,value)
    for i,row in enumerate(state['results']):atomic_json(OUT/f'{i:02d}_{row["operation"]}.json',h.store.artifact(row['reference']))
    for i,row in enumerate(state['results']):
        value=h.store.artifact(row['reference'])
        if value.get('checkpoint_reference'):atomic_json(OUT/f'{i:02d}_numeric_checkpoint.json',h.store.artifact(value['checkpoint_reference']))
        if row.get('candidate'):atomic_json(OUT/f'{i:02d}_candidate.json',h.store.artifact(row['candidate']))
    for i,row in enumerate(state['plans']):atomic_json(OUT/f'plan_{i:02d}_{row["action"]}.json',h.store.artifact(row['reference']))
    atomic_json(OUT/'archive_manifest.json',dict(members=manifest,archive_sha256=hashlib.sha256((OUT/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()))
    return dict(results=len(state['results']),plans=len(state['plans']),remaining=budget(h.store))


def stop(h):
    state=h.store.session(ACTIVITY)['state']
    if state.get('pending'):raise ValueError('PENDING_OUTCOME_REQUIRES_RECOVERY')
    elapsed=time.time()-state['started_unix'];engineering=max(0.,elapsed-h.store.remaining()['used']['wall_s'])
    row,fresh=h.store.reserve(ACTIVITY,'engineering-closeout',digest({'started':state['started_unix']}),h.actor,{**zero(),'wall_s':engineering},kind='engineering')
    if fresh:h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=h.actor,
        tool_id='engineering.casadi_feedback',tool_version='1.0.0',execution_status='completed',charged=zero()),dict(elapsed_activity_s=elapsed),elapsed=engineering)
    with h.store.transaction() as db:
        state=h.store.session(ACTIVITY,db)['state'];state['completed_unix']=time.time()
        state['closeout_status']='accepted_model_stop' if state.get('final_disposition') else 'incomplete_engineering_closeout'
        h.store.update_state(db,ACTIVITY,state,'stopped');h.store.event(db,ACTIVITY,'activity_completion',state['closeout_status'])


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','bind','migrate','recover','live','status','export','stop'])
    p.add_argument('--reason');args=p.parse_args();h=prepare() if args.command=='prepare' else host()
    if args.command in ('bind','migrate'):bind(h,args.command=='migrate',args.reason)
    if args.command=='recover':
        from tools.casadi_closed_loop import finish_closed_loop
        print(json.dumps(finish_closed_loop(h)));return
    if args.command=='live':asyncio.run(converse(h))
    if args.command=='stop':stop(h)
    if args.command=='export':print(json.dumps(export(h)));return
    print(json.dumps(dict(status=h.store.session(ACTIVITY)['status'],state=h.store.session(ACTIVITY)['state'],remaining=budget(h.store))))


if __name__=='__main__':main()
