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
    node_id: Identifier = Field(description='Unique label for this route action; reuse the original request_id to recover a sealed call.')
    action: Literal['build','run','optimize','diagnose','crosscheck','video','finish'] = Field(description='build constructs only; run simulates and evaluates a saved build; optimize searches and evaluates; diagnose analyzes saved results; crosscheck executes independently; video renders saved results; finish delivers an evaluated candidate.')
    combination: str | None = Field(default=None, description='Authorized combination name. Required for build, optimize without source_node, and crosscheck. With an optimization source, omit to preserve its bindings; an explicit choice must match them.')
    changes: dict = Field(default_factory=dict, description='build/optimize only: edits from the declared space, including template, physical paths, discretization paths and control/ paths. Applied to the source configuration, or the frozen baseline when no source is supplied.')
    variables: dict[str, tuple[float,float]] = Field(default_factory=dict, description='optimize only, required: continuous numeric variables[path] = [lower_bound, upper_bound], a continuous interval, NOT two requested samples. Integer, choice, template, and discretization changes belong in explicit changes. Bounds must be within the authorized space and include the starting value.')
    max_trials: int = Field(default=1,ge=1,description='Maximum optimizer proposals, bounded by route max_trials; independent of single run, which needs one solve. Duplicate proposals may reuse saved results.')
    source_node: Identifier | None = Field(default=None, description='Completed node_id: run requires build; optimize accepts build/run/optimize; diagnose/crosscheck/video/finish require a valid evaluated run or optimize node. Never an artifact ID.')
    candidate_id: str | None = Field(default=None, description='Optional candidate label on build; selects an optimization trial on later actions, defaulting to its best valid trial. A single run preserves the build candidate label.')
    evidence: list[EvidenceRef] = Field(default_factory=list, description='After the first action, cite at least one previous route node result reference here. route overview already supplies these references; a separate read is optional.')
    reason: str = Field(min_length=1,description='English explanation grounded in the current overview or cited evidence.')
    next_step: str = Field(min_length=1,description='English statement of the intended next decision or stopping condition.')


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
    if (choice.controller.extension_id=='controller.gvs_lqr' and
            choice.controller.parameters.data.get('development_execution_mode') is not None):
        raise ValueError('DEVELOPMENT_TENSION_EXECUTION_NOT_ROUTE_SELECTABLE')
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
    counts=dict(solves=host.store.remaining(host.run_id)['used']['backend_solves'],successful_integrations=0,evaluations=0,llm_requests=host.store.remaining(host.run_id)['used']['model_calls'],diagnoses=0,videos=0)
    import json
    with host.store.connect(True) as db:
        runs=[host.run_id]+[r['run_id'] for r in db.execute('SELECT run_id,snapshot FROM sessions')
            if host.store.artifact(dict(artifact_id=r['snapshot']),db=db).get('parent_run_id')==host.run_id]
        for r in db.execute('SELECT run_id,receipt FROM calls WHERE receipt IS NOT NULL'):
            if r['run_id'] not in runs: continue
            receipt=json.loads(r['receipt'])
            if receipt['execution_status']!='completed' or receipt.get('cache_hit'): continue
            if receipt['tool_id']=='simulation.run' and receipt.get('solver_status')=='completed': counts['successful_integrations']+=1
            key={'evaluation.run':'evaluations','diagnostics.saved_trajectory':'diagnoses','visualization.render_simulation_video':'videos'}.get(receipt['tool_id'])
            if key: counts[key]+=1
    return dict(run_id=host.run_id,status=session['status'],task=plain(inp.task),route=route,counts=counts,
        combinations=combinations,baseline=design_summary(inp.robot.structure.data),space=dict(
            templates={name:design_summary(design) for name,design in space.get('templates',{}).items()},
            parameters=space.get('parameters',{}),control_parameters=space.get('control_parameters',{}),
            model_parameters=space.get('model_parameters',{}),discretization_parameters=space.get('discretization_parameters',{})),
        max_trials=spec.max_trials,guidance=spec.guidance,usage=host.store.remaining(host.run_id),
        project_usage=host.store.remaining(),stop_reason=session['state'].get('stop_reason'),
        limitations=['Best means best valid evaluated candidate within one comparable search; no global optimum.',
            'Diagnosis is observational, not causal. Text adapter has not viewed videos.',
            'Serial bending cells only; no torsion/shear/stretch, friction, motor dynamics or general trajectory optimization.'])


def design_summary(design):
    return dict(id=design.get('id'),components=[dict(id=c['id'],kind=c['kind'],length_m=c.get('length_m'),
        sections=[s['section'] for s in c.get('sections',[])]) for c in design.get('components',[])],
        tendons=len(design.get('tendons',[])),actuators=len(design.get('actuators',[])))


def overview(host):
    """Small factual projection shared by inspect and provider context."""
    full=view(host); route=full['route']; nodes=route['nodes']
    completed=[n for n in nodes if n['status']=='completed']
    selected_node=next((n for n in reversed(completed) if n['action'] in ('build','run','optimize')),None)
    summary=selected_node['summary'] if selected_node else {}
    evaluated=next((n for n in reversed(completed) if n['action'] in ('run','optimize') and n['summary'].get('candidate_id')),None)
    inp=host.store.session(host.run_id)['snapshot']['input']
    space=inp['policy']['candidate_builder']['parameters']['data']
    with host.store.connect(True) as db:
        snapshot_ref=plain(EvidenceRef(artifact_id=db.execute('SELECT snapshot FROM sessions WHERE run_id=?',(host.run_id,)).fetchone()[0]))
    return dict(run_id=host.run_id,status=full['status'],stage='finished' if route['final'] else (selected_node['action'] if selected_node else 'selection'),
        selected_candidate=summary.get('candidate_id'),has_solve=full['counts']['solves']>0,
        has_evaluation=full['counts']['evaluations']>0,selected_summary=summary,
        latest_evaluated_node=evaluated['node_id'] if evaluated else None,
        frozen_input=dict(reference=snapshot_ref,task_pointer='/input/task',design_pointer='/input/robot/structure/data',
            space_pointer='/input/policy/candidate_builder/parameters/data',combinations_pointer='/input/policy/route/data/combinations'),
        route=dict(current=route['current'],next_step=route['next_step'],final=delivery_summary(route['final']),nodes=[
            {k:n[k] for k in ('node_id','action','status','result','error') if k in n} for n in nodes[-8:]]),
        combinations={name:dict(dynamics_model=c['dynamics_model']['extension_id'],backend=c['backend']['extension_id'],
            controller=c['controller']['extension_id'],
            executable=c['executable'],reasons=c['reasons']) for name,c in full['combinations'].items()},
        baseline=full['baseline'],space=dict(templates=list(space.get('templates',{})),
            parameters=space.get('parameters',{}),discretization_parameters=space.get('discretization_parameters',{}),
            control_parameters=space.get('control_parameters',{}),model_parameters=space.get('model_parameters',{})),max_trials=full['max_trials'],
        counts=full['counts'],usage=full['usage'],project_usage=full['project_usage'],
        available_actions=dict(build='Authorized combination and optional declared changes; zero solves.',
            run='Completed build source_node; one charged backend attempt plus evaluation, no variables.',
            optimize='Nonempty continuous numerical bounds only; integer/choice/template/discretization selections use explicit build changes; optional source_node; up to max_trials charged attempts.',
            diagnose='Valid run/optimize source_node; saved trajectory required; zero solves.',
            crosscheck='Valid run/optimize source_node and authorized alternative backend combination; one charged attempt plus evaluation.',
            video='Valid run/optimize source_node with saved results; zero solves.',
            finish='Valid run/optimize source_node; deliver even when task_success is false; zero solves.'),
        evidence_access='Node result references below are already available for citation. Read details only when needed. evidence.read returns content or a labeled pointer overview.',
        guidance=full['guidance'],
        limitations=full['limitations'])


def inspect(ctx,args): return RouteResult(detail=overview(ctx.host))


def preflight(inp,args,reg):
    spec=policy(inp)
    if args.max_trials>spec.max_trials: raise ValueError('ROUTE_TRIAL_LIMIT')
    if args.action in ('build','crosscheck') or (args.action=='optimize' and (args.combination or not args.source_node)):
        selected(inp,spec,args.combination,reg)
    if args.source_node and args.action=='build': raise ValueError('BUILD_SOURCE_NOT_SUPPORTED: use optimize to modify a saved source or build from baseline')
    if args.action not in ('build','optimize') and (args.changes or args.variables):
        raise ValueError('CHANGES_AND_VARIABLES_ONLY_FOR_BUILD_OR_OPTIMIZE')
    if args.action=='run' and args.combination: raise ValueError('RUN_PRESERVES_BUILD_COMBINATION: omit combination')
    if args.action in ('run','diagnose','crosscheck','video','finish') and not args.source_node:
        raise ValueError('SOURCE_NODE_REQUIRED')
    if args.action=='build' and args.variables: raise ValueError('VARIABLES_ONLY_FOR_OPTIMIZE')
    return dict(cost={'wall_s':0.})


def source_node(ctx,args,route):
    node=next((n for n in route['nodes'] if n['node_id']==args.source_node and n['status']=='completed'),None)
    if not node: raise ValueError('COMPLETED_SOURCE_NODE_REQUIRED')
    return node,ctx.store.artifact(node['result'])


def source_trial(ctx,args,route):
    node,result=source_node(ctx,args,route)
    if node['action'] not in ('run','optimize'): raise ValueError('EVALUATED_SOURCE_NODE_REQUIRED: use a run or optimize node')
    if node['action']=='run':
        trial=result
        if args.candidate_id and args.candidate_id!=trial['candidate_id']: raise ValueError('CANDIDATE_SELECTION_MISMATCH')
    else:
        trial=next((t for t in result['trials'] if t['candidate_id']==args.candidate_id),None) if args.candidate_id else result.get('best')
    if not trial or trial.get('status')!='valid': raise ValueError('VALID_CANDIDATE_REQUIRED')
    from tools.platform_host import Host
    child=Host(ctx.store.root,trial.get('owner_run_id',result['run_id']),actor='route-executor')
    metadata=ctx.store.session(child.run_id)['state']['result_executions'][trial['simulation']['execution_id']]
    return child,{**trial,'owner_run_id':child.run_id,'search_run_id':result['run_id'] if node['action']=='optimize' else None,
        'configuration':metadata['candidate_input'],
        'evaluation_data':ctx.store.artifact(trial['evaluation'])}


def source_configuration(ctx,args,route):
    node,result=source_node(ctx,args,route)
    if node['action']=='build': return ctx.store.artifact(result['configuration'])
    _,trial=source_trial(ctx,args,route)
    return ctx.store.artifact(trial['configuration'])['effective']


def run_built(ctx,args,route):
    """Execute the immutable build with stable child request identities, without search."""
    from tools.platform_host import Host
    from .optimization import ensure_session
    from .crosscheck import invoke
    from tools.platform_search import score
    node,built=source_node(ctx,args,route)
    if node['action']!='build': raise ValueError('BUILT_SOURCE_NODE_REQUIRED')
    candidate=built['candidate_id']
    if args.candidate_id and args.candidate_id!=candidate: raise ValueError('CANDIDATE_SELECTION_MISMATCH')
    inp=ctx.store.artifact(built['configuration'])
    child=Host(ctx.store.root,inp['run_id'],actor='route-executor')
    ensure_session(child,inp,parent_run_id=ctx.run_id,parent_event_id=ctx.row['parent_id'])
    sim=invoke(child,'single-simulation','simulation.run',dict(candidate_id=candidate,changes={}))
    ev=invoke(child,'single-evaluation','evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']))
    result=ctx.store.artifact(ev['output'])
    metadata=ctx.store.session(child.run_id)['state']['result_executions'][sim['execution_id']]
    return dict(status='valid' if result['validity']=='valid' else 'solver_failed',run_id=child.run_id,
        candidate_id=candidate,build_configuration=built['configuration'],configuration=metadata['candidate_input'],
        simulation=sim,evaluation=ev['output'],evaluation_data=result,metrics=result['metrics'],
        task_success=result['task_success'],score=score(result,inp['task']['objectives']),
        simulated=True,evaluated=True,actual_solves=ctx.store.remaining(child.run_id)['used']['backend_solves'])


def summarize(out):
    best=out.get('best')
    ev=best.get('evaluation_data') if best else out.get('evaluation_data',out.get('evaluation'))
    sim=best.get('simulation') if best else out.get('simulation')
    return dict(status=out.get('status','completed'),run_id=out.get('run_id'),stop_reason=out.get('stop_reason'),
        candidate_id=best.get('candidate_id') if best else out.get('candidate_id'),
        evaluation={k:ev[k] for k in ('validity','metrics','task_success','candidate_id','source_execution_id') if k in ev} if isinstance(ev,dict) else None,
        evaluation_ref=best.get('evaluation') if best else out.get('evaluation_ref',out.get('evaluation')),
        simulation={k:sim[k] for k in ('output','execution_id','solver_status') if k in sim} if sim else None,
        simulated=bool(sim and sim.get('solver_status')=='completed'),
        evaluated=bool(isinstance(ev,dict) and ev.get('source_execution_id') and ev.get('validity')),
        task_success=best.get('task_success') if best else out.get('task_success'),
        facts=out.get('facts'),
        configuration=best.get('configuration') if best else out.get('configuration'),
        proposals=out.get('proposals'),distinct_candidates=out.get('distinct_candidates'),actual_solves=out.get('actual_solves'),
        new_evaluations=out.get('new_evaluations'),reused_evaluations=out.get('reused_evaluations'),
        findings=out.get('findings'))


def delivery_summary(final):
    if final is None: return None
    return {k:final[k] for k in ('delivery_status','explicit_delivery','candidate_id','run_id','configuration',
        'evaluation_ref','task_success','crosscheck_status','stop_reason','selection_basis') if k in final}


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
            starting_trial=None
            if args.source_node:
                inp=SessionInput.model_validate(source_configuration(ctx,args,route))
                if source_node(ctx,args,route)[0]['action'] in ('run','optimize'):
                    _,starting_trial=source_trial(ctx,args,route)
                if args.combination:
                    choice=spec.combinations[args.combination]
                    if any(plain(getattr(inp.policy,k))!=plain(getattr(choice,k)) for k in ('dynamics_model','backend','controller')):
                        raise ValueError('SOURCE_COMBINATION_MISMATCH: omit combination to preserve the saved configuration')
            else:
                inp=selected(ctx.input,spec,args.combination,ctx.reg)
            inp=_candidate(inp,args.changes,ctx.reg)
            data=plain(inp); data['run_id']=ctx.run_id[:40]+'-'+digest(args.node_id)[:16]
            data['policy']['allowed_tools']=[]
            data['policy']['tool_bindings']={k:v for k,v in ctx.input.policy.tool_bindings.items() if k in (
                'simulation.run','evaluation.run','diagnostics.saved_trajectory','visualization.render_simulation_video','evidence.read')}
            data['policy']['budget']['backend_solves']=args.max_trials
            data['policy']['search']=None
            if args.action=='build':
                compiled=compile_input(data,ctx.reg)
                with ctx.store.transaction() as db: ref=ctx.store.put(db,compiled['input'])
                out=dict(status='built',candidate_id=args.candidate_id or args.node_id,configuration=plain(ref),
                    simulated=False,evaluated=False,facts='Built, not simulated, not evaluated. No task error or trajectory exists. Use run with this build node to execute and evaluate.',
                    actual_solves=0,findings=design_summary(data['robot']['structure']['data']))
            else:
                out=optimize(ctx.store.root,dict(session=data,variables=args.variables,max_trials=args.max_trials),
                    parent_run_id=ctx.run_id,parent_event_id=ctx.row['parent_id'],starting_trial=starting_trial,actor='route-executor')
                if out['status']=='unknown': raise TimeoutError('UNCONFIRMED child execution')
                if out['status'] not in ('completed',): raise ValueError('OPTIMIZATION_EXECUTION_FAILED: '+str(out.get('stop_reason')))
        elif args.action=='run':
            out=run_built(ctx,args,route)
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
                    parent_run_id=ctx.run_id,parent_event_id=ctx.row['parent_id'],actor='route-executor')
            elif args.action in ('diagnose','video'):
                tool='diagnostics.saved_trajectory' if args.action=='diagnose' else 'visualization.render_simulation_video'
                sim=trial['simulation']
                receipt=invoke(child,'route-'+args.node_id,tool,dict(result=sim['output'],execution_id=sim['execution_id']),parent=ctx.row['parent_id'])
                product=ctx.store.artifact(receipt['output']); report=ctx.store.artifact(product['report'])
                out=dict(candidate_id=trial['candidate_id'],configuration=trial['configuration'],receipt=receipt,product=product,
                    findings=diagnosis_summary(report) if args.action=='diagnose' else dict(video_generated=True,viewed_by_model=False))
            else:
                out=delivery(ctx,route,child,trial,args.reason)
                out['explicit_delivery']=True
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
    return RouteResult(detail=dict(node={k:node[k] for k in ('node_id','action','status')},
        result=plain(ref),summary=node['summary'],final=delivery_summary(route['final'])))


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
    search_run=trial.get('search_run_id') or child.run_id
    search=ctx.store.session(search_run)['state'].get('search')
    best=min((t for t in search['trials'] if t.get('score') is not None),key=lambda t:t['score']) if search else trial
    return dict(delivery_status='evaluated',candidate_id=trial['candidate_id'],run_id=child.run_id,configuration=trial['configuration'],
        search_run_id=search_run if search else None,actual_solves=0,new_evaluations=0,
        simulation=trial['simulation'],
        dynamics_model=configuration['policy']['dynamics_model'],backend=configuration['policy']['backend'],
        controller=configuration['policy']['controller'],evaluation_ref=trial['evaluation'],evaluation=trial['evaluation_data'],
        task_success=trial['task_success'],crosschecks=reviews,crosscheck_status='reviewed' if reviews else 'not_reviewed',
        diagnoses=diagnoses,stop_reason=reason,best_scope='best valid evaluated in selected search; not global optimum' if search else 'one selected evaluated candidate; no search ranking',
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
    final=dict(delivery_status='incomplete',candidate_id=None,evaluated=False,stop_reason=reason,crosscheck_status='not_reviewed')
    for node in reversed(route['nodes']):
        if node['action'] in ('run','optimize') and node.get('result') and (host.store.artifact(node['result']).get('best') or host.store.artifact(node['result']).get('status')=='valid'):
            child,trial=source_trial(ctx,SimpleNamespace(source_node=node['node_id'],candidate_id=None),route)
            final=delivery(ctx,route,child,trial,reason);break
    final['selection_basis']='Host terminal summary of the most recent valid evaluated source; not an explicit model delivery'
    final['explicit_delivery']=False
    route['final']=final
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state'];state['route']=route
        host.store.update_state(db,host.run_id,state)
        ref=host.store.put(db,final);host.store.event(db,host.run_id,'route_delivery','terminal',outputs=[ref])
