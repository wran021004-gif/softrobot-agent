"""Sequential, evidence-led route operations on existing Host sessions and Store events."""
from copy import deepcopy
from typing import Literal
from pydantic import Field
from schemas.common import Contract
from schemas.evidence import Identifier
from schemas.platform import Binding, EvidenceRef, SessionInput
from tools.platform_store import plain
from tools.state_io import digest


class Combination(Contract):
    dynamics_model: Binding
    backend: Binding
    controller: Binding


class RoutePolicy(Contract):
    source: str
    combinations: dict[str, Combination]
    max_trials: int = Field(default=3,ge=1,le=100)
    guidance: str = 'Select a legal combination and structure; evaluate, inspect evidence, then continue, adjust or finish. Reserve a solve for independent review when useful.'


class RouteAction(Contract):
    node_id: Identifier
    action: Literal['build','optimize','diagnose','crosscheck','video','finish']
    combination: str | None = None
    changes: dict = Field(default_factory=dict)
    variables: dict[str, tuple[float,float]] = Field(default_factory=dict)
    max_trials: int = Field(default=1,ge=1)
    source_node: Identifier | None = None
    candidate_id: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


class RouteResult(Contract):
    detail: dict


class Inspect(Contract):
    pass


def policy(inp):
    if inp.policy.route is None: raise ValueError('ROUTE_NOT_CONFIGURED')
    return RoutePolicy.model_validate(inp.policy.route.data)


def selected(inp, spec, name, reg):
    if name not in spec.combinations: raise ValueError('COMBINATION_NOT_AUTHORIZED')
    choice=spec.combinations[name]
    for kind in ('dynamics_model','backend','controller'):
        definition,_=reg.bind(getattr(choice,kind),kind)
        capability=reg.inspect(definition,{definition.extension_id:definition.version})
        if not capability['executable']: raise ValueError(str(capability['reasons']))
    return SessionInput.model_validate(
        {**plain(inp),'policy':{**plain(inp.policy),**plain(choice),'route':None}})


def create(root, value):
    from tools.platform_host import Host
    from tools.platform_tasks import compile_input
    from .optimization import ensure_session
    inp=SessionInput.model_validate(value); host=Host(root,inp.run_id); spec=policy(inp)
    if not spec.combinations: raise ValueError('ROUTE_COMBINATIONS_REQUIRED')
    for name in spec.combinations: compile_input(plain(selected(inp,spec,name,host.reg)),host.reg)
    ensure_session(host,inp)
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state']
        if 'route' not in state:
            state['route']=dict(source=spec.source,nodes=[],current=None,next_step='Select and evaluate an authorized candidate',final=None)
            host.store.update_state(db,host.run_id,state)
    return view(host)


def view(host):
    session=host.store.session(host.run_id); inp=SessionInput.model_validate(session['snapshot']['input'])
    spec=policy(inp); route=deepcopy(session['state'].get('route',{}))
    space=inp.policy.candidate_builder.parameters.data
    combinations={}
    for name,c in spec.combinations.items():
        definitions=[host.reg.get(getattr(c,k).extension_id,getattr(c,k).version,k) for k in ('dynamics_model','backend','controller')]
        checks=[host.reg.inspect(d,{d.extension_id:d.version}) for d in definitions]
        combinations[name]=dict(**plain(c),executable=all(c['executable'] for c in checks),
            reasons=[r for c in checks for r in c['reasons']])
    counts=dict(solves=host.store.remaining(host.run_id)['used']['backend_solves'],evaluations=0,llm_requests=host.store.remaining(host.run_id)['used']['model_calls'],diagnoses=0,videos=0)
    import json
    with host.store.connect(True) as db:
        runs=[host.run_id]+[r['run_id'] for r in db.execute('SELECT run_id,snapshot FROM sessions')
            if host.store.artifact(dict(artifact_id=r['snapshot']),db=db).get('parent_run_id')==host.run_id]
        for r in db.execute('SELECT run_id,receipt FROM calls WHERE receipt IS NOT NULL'):
            if r['run_id'] not in runs: continue
            receipt=json.loads(r['receipt'])
            if receipt['execution_status']!='completed' or receipt.get('cache_hit'): continue
            key={'evaluation.run':'evaluations','diagnostics.saved_trajectory':'diagnoses','visualization.render_simulation_video':'videos'}.get(receipt['tool_id'])
            if key: counts[key]+=1
    return dict(run_id=host.run_id,status=session['status'],task=plain(inp.task),route=route,counts=counts,
        combinations=combinations,baseline=design_summary(inp.robot.structure.data),space=dict(
            templates={name:design_summary(design) for name,design in space.get('templates',{}).items()},
            parameters=space.get('parameters',{}),control_parameters=space.get('control_parameters',{})),
        max_trials=spec.max_trials,guidance=spec.guidance,usage=host.store.remaining(host.run_id),
        project_usage=host.store.remaining(),stop_reason=session['state'].get('stop_reason'),
        limitations=['Best means best valid evaluated candidate within one comparable search; no global optimum.',
            'Diagnosis is observational, not causal. Text adapter has not viewed videos.',
            'Serial bending cells only; no torsion/shear/stretch, friction, motor dynamics or general trajectory optimization.'])


def design_summary(design):
    return dict(id=design.get('id'),components=[dict(id=c['id'],kind=c['kind'],length_m=c.get('length_m'),
        sections=[s['section'] for s in c.get('sections',[])]) for c in design.get('components',[])],
        tendons=len(design.get('tendons',[])),actuators=len(design.get('actuators',[])))


def inspect(ctx,args): return RouteResult(detail=view(ctx.host))


def preflight(inp,args,reg):
    spec=policy(inp)
    if args.max_trials>spec.max_trials: raise ValueError('ROUTE_TRIAL_LIMIT')
    if args.action in ('build','optimize','crosscheck'):
        selected(inp,spec,args.combination,reg)
    return dict(cost={'wall_s':0.})


def source_trial(ctx,args,route):
    node=next((n for n in route['nodes'] if n['node_id']==args.source_node and n['status']=='completed'),None)
    if not node or node['action']!='optimize': raise ValueError('EVALUATED_SOURCE_NODE_REQUIRED')
    result=ctx.store.artifact(node['result'])
    trial=next((t for t in result['trials'] if t['candidate_id']==args.candidate_id),None) if args.candidate_id else result.get('best')
    if not trial or trial.get('status')!='valid': raise ValueError('VALID_CANDIDATE_REQUIRED')
    from tools.platform_host import Host
    child=Host(ctx.store.root,result['run_id'])
    metadata=ctx.store.session(child.run_id)['state']['result_executions'][trial['simulation']['execution_id']]
    return child,{**trial,'configuration':metadata['candidate_input'],
        'evaluation_data':ctx.store.artifact(trial['evaluation'])}


def summarize(out):
    best=out.get('best')
    return dict(status=out.get('status','completed'),run_id=out.get('run_id'),stop_reason=out.get('stop_reason'),
        candidate_id=best.get('candidate_id') if best else out.get('candidate_id'),
        evaluation=best.get('evaluation_data') if best else out.get('evaluation'),
        configuration=best.get('configuration') if best else out.get('configuration'),
        proposals=out.get('proposals'),distinct_candidates=out.get('distinct_candidates'),actual_solves=out.get('actual_solves'),
        findings=out.get('findings'))


def diagnosis_summary(report):
    def fact(row):
        item={k:v for k,v in row.items() if k not in ('sample_indices','difference_intervals_s','values','possible_causes','recommendations')}
        item['values']={k:v for k,v in row.get('values',{}).items() if k not in ('times_s','error_m')}
        return item
    return dict(numerical=report.get('numerical'),events=[fact(r) for r in report.get('events',[])[:6]],
        event_count=len(report.get('events',[])),queries=[fact(r) for r in report.get('queries',[])
            if r.get('observation')=='tip_error_over_time'][:1],missing=report.get('missing',[])[:6],
        limitations=report.get('limitations',[]),details='Read product.report with evidence.read paging')


def advance(ctx,args):
    from tools.platform_host import Host
    from tools.platform_tools import _candidate
    from tools.platform_tasks import compile_input
    from .optimization import optimize
    from .crosscheck import crosscheck,invoke
    spec=policy(ctx.input)
    route=ctx.store.session(ctx.run_id)['state']['route']
    if route['final']: raise ValueError('ROUTE_ALREADY_FINISHED')
    if any(n['node_id']==args.node_id for n in route['nodes']): raise ValueError('NODE_ID_ALREADY_USED: resume original tool request')
    if route['current']: raise ValueError('ROUTE_NODE_UNRESOLVED')
    if args.action=='optimize' and not args.variables:
        raise ValueError('OPTIMIZATION_VARIABLES_REQUIRED')
    # Subsequent choices must cite a concrete completed node result (not only prose).
    results={n['result']['artifact_id'] for n in route['nodes'] if n.get('result')}
    for n in route['nodes']:
        sealed=ctx.store.lookup(ctx.run_id,n['request_id'])
        if sealed and sealed['receipt']:
            import json
            receipt=json.loads(sealed['receipt'])
            if receipt.get('output'): results.add(receipt['output']['artifact_id'])
    if results and not results.intersection(r.artifact_id for r in args.evidence):
        raise ValueError('ROUTE_EVIDENCE_REQUIRED: cite a previous node result')
    node=dict(node_id=args.node_id,action=args.action,request_id=ctx.request.request_id,
        execution_id=ctx.row['execution_id'],selection=plain(args),status='running')
    route['nodes'].append(node); route['current']=args.node_id; route['next_step']=args.next_step
    _save(ctx,route,'started')
    try:
        if args.action in ('build','optimize'):
            inp=selected(ctx.input,spec,args.combination,ctx.reg)
            inp=_candidate(inp,args.changes,ctx.reg)
            data=plain(inp); data['run_id']=ctx.run_id[:40]+'-'+digest(args.node_id)[:16]
            data['policy']['allowed_tools']=[]
            data['policy']['tool_bindings']={k:v for k,v in ctx.input.policy.tool_bindings.items() if k in (
                'simulation.run','evaluation.run','diagnostics.saved_trajectory','visualization.render_simulation_video','evidence.read')}
            data['policy']['budget']['backend_solves']=args.max_trials
            if args.action=='build':
                compiled=compile_input(data,ctx.reg)
                with ctx.store.transaction() as db: ref=ctx.store.put(db,compiled['input'])
                out=dict(status='built',configuration=plain(ref),actual_solves=0,findings=design_summary(data['robot']['structure']['data']))
            else:
                out=optimize(ctx.store.root,dict(session=data,variables=args.variables,max_trials=args.max_trials),
                    parent_run_id=ctx.run_id,parent_event_id=ctx.row['parent_id'])
                if out['status']=='unknown': raise TimeoutError('UNCONFIRMED child execution')
        elif args.action in ('diagnose','crosscheck','video','finish'):
            child,trial=source_trial(ctx,args,route)
            if args.action=='crosscheck':
                choice=spec.combinations[args.combination]
                effective=ctx.store.artifact(trial['configuration'])['effective']
                if effective['policy']['dynamics_model']!=plain(choice.dynamics_model) or effective['policy']['controller']!=plain(choice.controller):
                    # Control parameters can have been optimized. Crosscheck preserves them.
                    if effective['policy']['dynamics_model']!=plain(choice.dynamics_model) or effective['policy']['controller']['extension_id']!=choice.controller.extension_id:
                        raise ValueError('CROSSCHECK_MUST_PRESERVE_MODEL_AND_CONTROL')
                out=crosscheck(ctx.store.root,child.run_id,trial['candidate_id'],trial['configuration'],plain(choice.backend),
                    parent_run_id=ctx.run_id,parent_event_id=ctx.row['parent_id'])
            elif args.action in ('diagnose','video'):
                tool='diagnostics.saved_trajectory' if args.action=='diagnose' else 'visualization.render_simulation_video'
                sim=trial['simulation']
                receipt=invoke(child,'route-'+args.node_id,tool,dict(result=sim['output'],execution_id=sim['execution_id']))
                product=ctx.store.artifact(receipt['output']); report=ctx.store.artifact(product['report'])
                out=dict(candidate_id=trial['candidate_id'],configuration=trial['configuration'],receipt=receipt,product=product,
                    findings=diagnosis_summary(report) if args.action=='diagnose' else dict(video_generated=True,viewed_by_model=False))
            else:
                out=delivery(ctx,route,child,trial,args.reason)
                route['final']=out
    except Exception as exc:
        node.update(status='unknown' if isinstance(exc,TimeoutError) else 'failed',error=str(exc))
        route['current']=args.node_id if isinstance(exc,TimeoutError) else None
        _save(ctx,route,node['status'])
        raise
    with ctx.store.transaction() as db: ref=ctx.store.put(db,out)
    node.update(status='completed',result=plain(ref),summary=summarize(out))
    route['current']=None
    _save(ctx,route,'completed',stop=args.action=='finish')
    return RouteResult(detail=dict(node=node,result=plain(ref),summary=node['summary'],final=route['final']))


def _save(ctx,route,status,stop=False):
    with ctx.store.transaction() as db:
        state=ctx.store.session(ctx.run_id,db)['state']; state['route']=route
        if stop: state['stop_reason']=route['final']['stop_reason']
        ctx.store.update_state(db,ctx.run_id,state,'stopped' if stop else None)
        ref=ctx.store.put(db,route)
        ctx.store.event(db,ctx.run_id,'route_node',status,parent=ctx.row['parent_id'],
            request=ctx.request.request_id,execution=ctx.row['execution_id'],outputs=[ref])


def delivery(ctx,route,child,trial,reason):
    configuration=ctx.store.artifact(trial['configuration'])['effective']
    reviews=[]; diagnoses=[]
    for n in route['nodes']:
        if n.get('result') and n['action'] in ('crosscheck','diagnose'):
            data=ctx.store.artifact(n['result'])
            if data.get('source_configuration',data.get('configuration'))==trial['configuration']:
                (reviews if n['action']=='crosscheck' else diagnoses).append(dict(result=n['result'],summary=n['summary']))
    search=ctx.store.session(child.run_id)['state']['search']
    best=min((t for t in search['trials'] if t.get('score') is not None),key=lambda t:t['score'])
    return dict(candidate_id=trial['candidate_id'],run_id=child.run_id,configuration=trial['configuration'],
        dynamics_model=configuration['policy']['dynamics_model'],backend=configuration['policy']['backend'],
        controller=configuration['policy']['controller'],evaluation_ref=trial['evaluation'],evaluation=trial['evaluation_data'],
        task_success=trial['task_success'],crosschecks=reviews,crosscheck_status='reviewed' if reviews else 'not_reviewed',
        diagnoses=diagnoses,stop_reason=reason,best_scope='best valid evaluated in selected search; not global optimum',
        best_valid_evaluation=dict(candidate_id=best['candidate_id'],evaluation_ref=best['evaluation'],score=best['score']),
        limitations=view(ctx.host)['limitations'])


def finalize_stop(host):
    """Host delivery on a terminal budget/turn/capability stop; no invented LLM choice."""
    from types import SimpleNamespace
    session=host.store.session(host.run_id); route=session['state'].get('route')
    if not route or route.get('final') or session['status'] in ('running','created','paused','needs_input'):
        return
    reason=session['state'].get('stop_reason',session['status'])
    ctx=SimpleNamespace(host=host,store=host.store)
    final=dict(candidate_id=None,stop_reason=reason,crosscheck_status='not_reviewed')
    for node in reversed(route['nodes']):
        if node['action']=='optimize' and node.get('result') and host.store.artifact(node['result']).get('best'):
            child,trial=source_trial(ctx,SimpleNamespace(source_node=node['node_id'],candidate_id=None),route)
            final=delivery(ctx,route,child,trial,reason);break
    final['selection_basis']='Host terminal summary: best of most recent valid search; not a new LLM decision'
    route['final']=final
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state'];state['route']=route
        host.store.update_state(db,host.run_id,state)
        ref=host.store.put(db,final);host.store.event(db,host.run_id,'route_delivery','terminal',outputs=[ref])
