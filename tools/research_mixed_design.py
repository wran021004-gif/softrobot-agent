"""Thin new activity: one Store, grant, Strands principal and numerical service."""
from copy import deepcopy
from pathlib import Path
from typing import Literal
import argparse
import asyncio
import json
import os
import subprocess
import time
from pydantic import Field
from schemas.common import Contract
from schemas.platform import ProjectConfig,SessionInput
from schemas.design_optimization import DesignOptimizationProblem
from tools.platform_store import Store,plain,zero
from tools.platform_host import Host
from tools.state_io import atomic_json,read,digest
from tools.research_execution import invoke
from tools.design_optimization import (solve,decode,resolved_input,validate_problem,ReceiptEvaluator,evaluate)
from extensions.tendon_family.finite_templates import catalog

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'runs/mixed-design-20261010'
OUT=ROOT/'evidence/mixed_design_20261010'
ACTIVITY='mixed-design-20261010'
STARTED=1791564694.
LIMITS=dict(model_calls=60,tool_calls=1024,backend_solves=12,worker_calls=0,wall_s=57600.)


class Disposition(Contract):
    action: Literal['continue','confirm','stop']
    candidate_id: str | None = None
    evidence_problem_identity: str
    reasoning: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)


def example(free=True):
    source=catalog()['scientific_source'];controller=source['policy']['controller']['parameters']['data']
    counts={k:dict(kind='integer',bounds=b) if free else dict(kind='fixed',value=b[0]) for k,b in
        [('segment_count',[2,4]),('proximal_tendons',[3,4]),('distal_tendons',[3,4])]}
    return plain(DesignOptimizationProblem.model_validate(dict(study_id=ACTIVITY,task=source['task'],
        execution=dict(recipe=controller['recipe'],settling=controller['settling']),variables={**counts,
            'material':dict(kind='fixed',value='baseline'),'section_scale':dict(kind='fixed',value=1.),
            'routing_scale':dict(kind='fixed',value=1.),'pretension_n':dict(kind='fixed',value=.2),
            'holding_tip_speed_weight':dict(kind='continuous',bounds=[.025,.1],initial=.05),
            'terminal_tip_speed_weight':dict(kind='fixed',value=.1)},
        method=dict(initial_structures=[dict(segment_count=3,proximal_tendons=3,distal_tendons=3),
            dict(segment_count=4,proximal_tendons=3,distal_tendons=4)] if free else []))))


def configuration():
    from tools.research_v2 import native_configuration
    base=native_configuration(ACTIVITY);problem=DesignOptimizationProblem.model_validate(example())
    base['policy'].update(budget=LIMITS,allowed_tools=[],tool_bindings={'search.design_mixed':'1.0.0','evidence.read':'1.0.0'},
        operation_allowances={'search.design_mixed':dict(timeout_s=54000.,reserve_s=30.),
            'evidence.read':dict(timeout_s=60.,reserve_s=30.)})
    base['policy']['model'].update(max_turns=60,max_repairs=10,protocol_recovery=dict(max_total=60,max_consecutive=60))
    structure=plain(problem.method.initial_structures[0]);from tools.design_optimization import continuous_space
    _,latent=continuous_space(problem,structure)
    return resolved_input(problem,decode(problem,structure,latent),ACTIVITY,base['policy'])


def host(directory=RUN):
    return Host(Path(directory),ACTIVITY)


def prepare(directory=RUN,*,offline=False):
    directory=Path(directory);store=Store(directory)
    if store.db.exists():return host(directory)
    cfg=configuration();suffix='-'+digest(str(directory))[:10] if offline else ''
    store.create(ProjectConfig(project_id=ACTIVITY+suffix,grant_id=ACTIVITY+'-authorized-grant'+suffix,
        budget=LIMITS,authorization_source='e2b2da0a-07e2-4f92-a50a-043ecc9a6cd7/pasted-text-1.txt plus user length and pretension freeze',
        exclusive_resources={'backend.family_mujoco':1,'provider_request':1}))
    h=host(directory);h.create(cfg);h.resume();started=time.time() if offline else STARTED
    spec=dict(activity_id=ACTIVITY,started_unix=started,deadline_unix=started+57600,execution_cutoff_unix=started+55800,
        limits=LIMITS,development_backend_limit=8,confirmation_backend_limit=2,replacement_backend_limit=2,
        public_search_limit=48,additional_workers=0,offline=offline,
        numerical_initialization=dict(source='initial_state_pretension',pretension_n=.2,
            rule='One 0.2 N value per generated tendon in compiler control order; bounded 0..8 N; no historical tensions; warm states regenerated'),
        physical_initialization='Named generated joints qpos=0 rad and qvel=0 rad/s',
        length_baseline=dict(total_flexible_length_m=.27,proximal_m=.16,distal_sum_m=.11,
            distal_allocation='equal by default',individual_bounds='topology-local baseline +/-5%',constraint='exact sum'),
        historical_roots=[str(Path('D:/softrobot-agent/.worktrees/strands-mainline5/runs/mainline5-20261009')),
            'D:/softrobot-agent/runs/mainline4-20261009','D:/softrobot-agent/runs/mainline3-v2-20261009',
            'D:/softrobot-agent/runs/mainline3-v1-complete-218a188f9f6f-fixed'])
    with store.transaction() as db:
        state=store.session(h.run_id,db)['state'];state.update(mixed_spec=spec,mixed_status='prepared',mixed_decisions=[],mixed_confirmations=[])
        state['pilot']=dict(activity_id=ACTIVITY,mode='mixed-design-strands',provider=cfg['policy']['model'],
            framework_session_id=ACTIVITY,live_model_requests=0,started_unix=started,request_deadline_unix=spec['execution_cutoff_unix'],phase='prepared')
        store.update_state(db,h.run_id,state)
    atomic_json(directory/'study_specification.json',spec);atomic_json(directory/'problem.json',example())
    atomic_json(directory/'configuration.json',cfg)
    from tools.mixed_design_history import compare
    comparison=compare();atomic_json(directory/'historical_comparison.json',comparison)
    with store.transaction() as db:
        ref=store.put(db,comparison);store.event(db,h.run_id,'historical_reasoning_import','original_ownership',outputs=[ref])
    return h


def bind(h):
    from tools.platform_tasks import compile_input
    with h.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]:raise ValueError('FREEZE_REQUIRES_ZERO_CALLS')
    before=h.store.session(h.run_id)['snapshot'];after=compile_input(before['input'],h.reg)
    after.update(project_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),worktree_dirty=False)
    if after['input_identity']!=before['input_identity']:raise ValueError('FREEZE_CHANGED_SCIENCE')
    with h.store.transaction() as db:
        ref=h.store.put(db,after);db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(ref.artifact_id,h.run_id))
        state=h.store.session(h.run_id,db)['state'];state['mixed_freeze']=after['project_commit'];h.store.update_state(db,h.run_id,state)
        h.store.event(db,h.run_id,'implementation_freeze','committed',outputs=[ref])
    spec=h.store.session(h.run_id)['state']['mixed_spec'];elapsed=time.time()-spec['started_unix']
    row,_=h.store.reserve(h.run_id,'initial-engineering',digest(spec),h.actor,{**zero(),'wall_s':elapsed},kind='engineering')
    h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=h.actor,
        tool_id='engineering.mixed_design',tool_version='1.0.0',execution_status='completed',charged=zero()),
        dict(elapsed_s=elapsed),elapsed=elapsed,kind='engineering')
    atomic_json(h.store.root/'implementation_freeze.json',dict(project_commit=after['project_commit'],dependencies=after['dependencies']))


def check_live_problem(h,problem):
    problem,_=validate_problem(problem);frozen=DesignOptimizationProblem.model_validate(read(h.store.root/'problem.json'))
    if plain(problem.task)!=plain(frozen.task) or plain(problem.execution)!=plain(frozen.execution):raise ValueError('FIRST_STUDY_TASK_AND_NUMERICS_FROZEN')
    if plain(problem.lengths)!=plain(frozen.lengths):raise ValueError('FIRST_STUDY_LENGTH_BASELINES_AND_SUM_FROZEN')
    for k in ('material','section_scale','routing_scale','pretension_n','terminal_tip_speed_weight'):
        if plain(problem.variables[k])!=plain(frozen.variables[k]):raise ValueError('FIRST_STUDY_FIXED_PARAMETER: '+k)
    state=h.store.session(h.run_id)['state']
    if state['mixed_status'] in ('stopped','confirmation_returned'):raise ValueError('STUDY_ONLY_FINAL_STOP_ALLOWED')
    with h.store.connect(True) as db:
        calls=[dict(r) for r in db.execute("SELECT * FROM calls WHERE request_id='complete-simulation'")]
        search_calls=[dict(r) for r in db.execute("SELECT receipt FROM calls WHERE receipt IS NOT NULL")]
    if sum(json.loads(r['receipt'])['tool_id']=='search.design_mixed' for r in search_calls)>=48:raise ValueError('PUBLIC_SEARCH_OPERATION_CEILING')
    development=sum(not r['run_id'].startswith('confirm-') for r in calls)
    existing=state.get('design_searches',{}).get(digest(plain(problem)),{})
    remaining=problem.budget.max_evaluations-len(existing.get('evaluated',[]))
    if development+remaining>8:raise ValueError('DEVELOPMENT_BACKEND_CEILING')
    if len(state.get('design_searches',{}))>=48 and not existing:raise ValueError('PUBLIC_SEARCH_CEILING')
    return problem


def decide(h,request,request_id=None):
    d=Disposition.model_validate(request);state=h.store.session(h.run_id)['state'];search=state.get('design_searches',{}).get(d.evidence_problem_identity)
    request_id=request_id or 'disposition-'+digest(plain(d))
    saved=state.get('mixed_disposition_receipts',{}).get(request_id)
    if saved:
        if saved['input']!=plain(d):raise ValueError('DISPOSITION_ID_COLLISION')
        return saved['result']
    if not search or not search['evaluated']:raise ValueError('DECISION_REQUIRES_ACTUAL_SEARCH_EVIDENCE')
    if state['mixed_status']=='confirmation_returned' and d.action!='stop':raise ValueError('ONLY_STOP_AFTER_EXACT_CONFIRMATION')
    if state['mixed_status']=='stopped':raise ValueError('STOP_ALREADY_SEALED')
    confirmation=None
    with h.store.transaction() as db:
        current=h.store.session(h.run_id,db)['state'];pending=current.get('mixed_pending_disposition')
        intent=dict(request_id=request_id,input=plain(d))
        if pending and pending!=intent:raise ValueError('PENDING_DISPOSITION_MUST_RECOVER_FIRST')
        current['mixed_pending_disposition']=intent;h.store.update_state(db,h.run_id,current)
    charged,_=h.store.reserve(h.run_id,request_id,digest(plain(d)),h.actor,{**zero(),'tool_calls':1,'wall_s':30.},kind='principal_disposition')
    started=time.monotonic()
    if d.action=='confirm':
        selected=next((r for r in search['evaluated'] if r['candidate_id']==d.candidate_id),None)
        if selected is None:raise ValueError('EXACT_EVALUATED_CANDIDATE_REQUIRED')
        if state['mixed_confirmations']:raise ValueError('SECOND_CONFIRMATION_REQUIRES_CONCRETE_UNRESOLVED_CLAIM')
        problem=DesignOptimizationProblem.model_validate(search['problem'])
        structure={k:selected['resolved']['parameters'][k] for k in ('segment_count','proximal_tendons','distal_tendons','material')}
        confirmation=evaluate(problem,structure,selected['latent_coordinates'],'confirm-'+d.evidence_problem_identity[:10],
            'confirmation',ReceiptEvaluator(h),selected['candidate_id'])
        if not confirmation.get('execution_status'):raise ValueError('CONFIRMATION_NOT_COMPLETE: '+str(confirmation))
    with h.store.transaction() as db:
        state=h.store.session(h.run_id,db)['state'];ref=h.store.put(db,d);state['mixed_decisions'].append(plain(ref))
        if confirmation:state['mixed_confirmations'].append(confirmation)
        state['mixed_status']='stopped' if d.action=='stop' else 'confirmation_returned' if confirmation else 'feedback_consumed'
        result=dict(status=state['mixed_status'],decision=plain(ref),confirmation=confirmation)
        state.setdefault('mixed_disposition_receipts',{})[request_id]=dict(input=plain(d),result=result)
        state.pop('mixed_pending_disposition',None)
        h.store.update_state(db,h.run_id,state);h.store.event(db,h.run_id,'principal_disposition',d.action,outputs=[ref])
        h.store.complete(charged,dict(request_id=request_id,execution_id=charged['execution_id'],caller=h.actor,
            tool_id='research.design_decide',tool_version='1.0.0',execution_status='completed',charged=zero()),
            result,elapsed=0. if confirmation else time.monotonic()-started,kind='principal_disposition',db=db)
    return result


INSTRUCTIONS='''You are the sole principal for a new bounded mixed robot design study. Use the supplied public typed problem to define or refine a solve and inspect actual results. Strands owns conversation/context/restoration, numerical software owns per-candidate proposal/evaluation. No other workers. Tool calls execute sequentially with matched IDs. Freeze the supplied nominal task, structural basis, inherited controller11 deadline recipe, material baseline, section/routing1, total flexible length0.27m, topology-dependent [.16, equal shares of .11] length baseline +/-5%, terminal speed weight0.1, and explicit initial_state_pretension 0.2N per tendon. Physical initial q/v are named zeros. The first study must search segment count and both group counts, length allocation, and may search holding weight. Normally initialize TWO signatures (3,3,3) and (4,3,4), then let feedback drive continuous proposals; these are declared structural coverage, not a model-authored full vector list. The public solver returns best feasible separately from best observed infeasible, with exact outcomes and unsearched scope. Do not claim no feasible design exists on budget exhaustion. Prefer fewer actuators among accepted designs; sum of tension limits is not tip force or power, and motor mass is unknown. At most8 development,2 exact confirmation,2 identified technical replacements,12 total backend launches;60 actual provider requests including summaries;1024 tools;48 public search/math;16 hours total including implementation;final30min protected. Usually run one four-evaluation study. After feedback decide stop or justified refinement. For a consequential nominated new candidate use ONE exact fresh confirmation, including an infeasible incumbent if it matters to the claim; no tuning during confirmation. After confirmation ONLY STOP, keeping failures visible. Original historical T0 result remains valid in scope, T2 six developments and one confirmation failed; two stiff holding speeds0.09248005 and0.21090378 are individual observations, not statistical variance or proof of bugs. Cite exact candidate and problem identities and read retained artifacts for details. Original model output is preserved. No global optimum, robustness, real-time or arbitrary topology claims.'''


def build_live(h):
    from strands.tools.tools import PythonAgentTool
    from strands.tools.executors import SequentialToolExecutor
    from strands.hooks.events import BeforeModelCallEvent,BeforeToolCallEvent,AfterToolCallEvent
    from tools.strands_pilot import build_harness
    from tools.strands_pilot_r3 import LiveBoundary,live_model_class,record
    from examples.gvs_nmpc_route_experiment import load_credential
    load_credential(Path.home()/'.codex/.env');boundary=LiveBoundary(h,allow_truncated_response=True)
    definitions=[('solve_design',DesignOptimizationProblem),('design_decide',Disposition)]
    tools=[]
    for name,schema in definitions:
        def handler(use,_name=name,**kwargs):
            if _name=='solve_design':
                problem=check_live_problem(h,use['input'])
                receipt=invoke(h,'search.design_mixed',plain(problem),request_id='mixed-native-'+use['toolUseId'])
                if receipt['execution_status']!='completed':value=dict(receipt=receipt)
                else:
                    result=h.store.artifact(receipt['output']);value=compact(result);value.update(receipt=receipt,result_reference=receipt['output'])
            else:value=decide(h,use['input'],request_id='mixed-native-'+use['toolUseId'])
            return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text=json.dumps(value,ensure_ascii=False))])
        tools.append(PythonAgentTool(name,dict(name=name,description='Bounded numerical solve with actual receipt-backed evidence' if name=='solve_design' else 'Consume actual evidence; nominate exact confirmation or stop',
            inputSchema={'json':schema.model_json_schema()}),handler))
    definition=h.reg.get('evidence.read');
    def read_handler(use,**kwargs):
        receipt=invoke(h,'evidence.read',use['input'],request_id='mixed-native-'+use['toolUseId'])
        return dict(toolUseId=use['toolUseId'],status='success' if receipt['execution_status']=='completed' else 'error',
            content=[dict(text=json.dumps(dict(receipt=receipt,content=h.store.artifact(receipt['output']) if receipt.get('output') else None)))])
    tools.append(PythonAgentTool('evidence_read',dict(name='evidence_read',description='Retrieve full immutable artifacts by exact reference',inputSchema={'json':definition.input_schema.model_json_schema()}),read_handler))
    agent=build_harness(h,transport=boundary,api_key=os.environ['DEEPSEEK_API_KEY'],instructions=INSTRUCTIONS,
        model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),research_tools=tools,
        configuration_path=h.store.root/'framework_configuration.json',session_directory=h.store.root/'framework_sessions')
    def before_model(event):
        state=h.store.session(h.run_id)['state']
        if state['mixed_status']=='stopped':event.cancel='Principal STOP sealed';return
        if state['pilot'].get('unconsumed_response'):
            key=state['pilot']['unconsumed_response']
            event=next(e for e in h.store.events(h.run_id) if e['kind']=='r3_request' and e['request_id']==key)
            original=h.store.artifact(h.store.artifact(event['outputs'][0])['request'])
            agent.system_prompt=next(m['content'] for m in original['messages'] if m['role']=='system')
            return
        packet=dict(status=state['mixed_status'],default_problem=read(h.store.root/'problem.json'),
            results=[compact(result_from_state(h,s)) for s in state.get('design_searches',{}).values()],
            confirmations=[compact(dict(evaluated=[r])) for r in state['mixed_confirmations']],remaining=h.store.remaining(),
            history=read(h.store.root/'historical_comparison.json') if (h.store.root/'historical_comparison.json').exists() else None)
        agent.system_prompt=INSTRUCTIONS+'\nCURRENT_BUSINESS_PACKET\n'+json.dumps(packet,ensure_ascii=False)
    def before_tool(event):record(h,'mixed_native_dispatch',dict(tool_use=event.tool_use))
    def after_tool(event):
        record(h,'mixed_native_result',dict(tool_use=event.tool_use,result=event.result))
        key='mixed-native-'+event.tool_use['toolUseId']
        if h.store.lookup(h.run_id,key) is None:
            row,_=h.store.reserve(h.run_id,key,digest(event.tool_use),h.actor,{**zero(),'tool_calls':1,'wall_s':0.})
            h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=h.actor,
                tool_id=event.tool_use['name'],tool_version='1.0.0',execution_status='failed',charged=zero()),event.result,kind='native_rejected')
    agent.hooks.add_callback(BeforeModelCallEvent,before_model);agent.hooks.add_callback(BeforeToolCallEvent,before_tool)
    agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    return agent


def compact(result):
    return {k:v for k,v in result.items() if k not in ('evaluated','best_feasible','best_observed_infeasible')} | dict(
        best_feasible=result.get('best_feasible',{}).get('candidate_id') if result.get('best_feasible') else None,
        best_observed_infeasible=result.get('best_observed_infeasible',{}).get('candidate_id') if result.get('best_observed_infeasible') else None,
        evaluated=[{k:r[k] for k in ('candidate_id','phase','scientific_identity','latent_coordinates','feasible','objective_values','execution_status','used_feedback')}
            | dict(parameters=r['resolved']['parameters'],evidence={k:v for k,v in r['evidence'].items() if k in
                ('configuration','execution_id','owner_run_id','profile')},timing={k:r['evidence'].get('feedback',{}).get(k) for k in
                ('actual_applied_control_updates','simulation_wall_s','deadline_misses','mean_complete_update_s')}) for r in result['evaluated']])


def result_from_state(h,state):
    # Retrieval only; never resumes a solver while presenting current context.
    from tools.design_optimization import rank
    p=DesignOptimizationProblem.model_validate(state['problem']);rows=state['evaluated']
    feasible=[r for r in rows if r['feasible']];failed=[r for r in rows if not r['feasible']]
    return dict(problem_identity=state['problem_identity'],termination_reason=state['termination'],evaluated=rows,
        best_feasible=min(feasible,key=lambda r:rank(r,p)) if feasible else None,
        best_observed_infeasible=min(failed,key=lambda r:rank(r,p)) if failed else None,search_updates=state['updates'])


async def converse(h):
    agent=build_live(h)
    while h.store.session(h.run_id)['state']['mixed_status']!='stopped':
        from strands.types.exceptions import MaxTokensReachedException
        try:await agent.invoke_async('Use the current business packet to solve/refine the typed problem, inspect returned evidence, and decide. After confirmation consume its actual result and STOP.')
        except MaxTokensReachedException:
            from tools.strands_pilot_r3 import record
            record(h,'mixed_incomplete_response',dict(reason='max_tokens',partial_history_owner='Strands'))
        from tools.strands_pilot_r3 import pending
        if pending(h):raise ValueError('UNRESOLVED_PROVIDER_OUTCOME_NO_BLIND_REPLAY')


def recover_numerical(h):
    """Reconcile accepted parent operations using their exact saved problem.

    Existing sealed simulations remain authoritative; an unknown child never
    launches again. Original parent reservation and usage are retained.
    """
    with h.store.connect(True) as db:
        rows=[dict(r) for r in db.execute('SELECT * FROM calls WHERE run_id=? AND receipt IS NULL',(h.run_id,))]
    for row in rows:
        if row['caller']=='deepseek-r3':continue
        event=next(e for e in h.store.events(h.run_id) if e['execution_id']==row['execution_id'] and e['status']=='reserved')
        request=h.store.artifact(event['inputs'][0]) if event['inputs'] else None
        if not request or request.get('tool_id')!='search.design_mixed':continue
        result=solve(request['arguments'],h)
        if result.status=='pending_execution':raise ValueError('UNKNOWN_CHILD_EXECUTION_RETAINED_NO_REPLAY')
        h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=row['caller'],
            tool_id='search.design_mixed',tool_version='1.0.0',execution_status='completed',charged=zero()),plain(result),kind='reconciled_search')
    pending=h.store.session(h.run_id)['state'].get('mixed_pending_disposition')
    if pending:decide(h,pending['input'],request_id=pending['request_id'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','bind','run','direct','status','recover','export'])
    parser.add_argument('--directory',type=Path,default=RUN);parser.add_argument('--problem',type=Path)
    args=parser.parse_args();h=prepare(args.directory) if args.command=='prepare' else host(args.directory)
    if args.command=='bind':bind(h)
    elif args.command in ('run','recover'):
        if not h.store.session(h.run_id)['state'].get('mixed_freeze'):raise ValueError('COMMIT_AND_BIND_BEFORE_LIVE_EXECUTION')
        if args.command=='recover':recover_numerical(h)
        asyncio.run(converse(h))
    elif args.command=='direct':
        problem=check_live_problem(h,read(args.problem or h.store.root/'problem.json'))
        receipt=invoke(h,'search.design_mixed',plain(problem),request_id='direct-'+digest(plain(problem)))
        print(json.dumps(receipt));
        if receipt.get('output'):atomic_json(h.store.root/'direct_result.json',h.store.artifact(receipt['output']))
    elif args.command=='export':
        from tools.mixed_design_summary import export
        print(json.dumps(export(h)))
    else:print(json.dumps(dict(status=h.store.session(h.run_id)['state']['mixed_status'],remaining=h.store.remaining()),ensure_ascii=False))


if __name__=='__main__':main()
