"""Sequential, evidence-led route operations on existing Host sessions and Store events."""
from copy import deepcopy
from typing import Literal, get_args
from pydantic import Field
from schemas.common import Contract
from schemas.evidence import Identifier
from schemas.platform import Binding, EvidenceRef, SessionInput
from tools.platform_store import plain
from tools.state_io import digest
from .delivery_facts import TrackingFacts, ReachFacts, bound_result_facts


class Combination(Contract):
    dynamics_model: Binding
    backend: Binding
    controller: Binding


class RoutePolicy(Contract):
    source: str
    historical_case: EvidenceRef | None = None
    historical_math: EvidenceRef | None = Field(default=None, description='Optional frozen import manifest for exact historical mathematical artifacts. It grants no execution or global cross-run ownership.')
    combinations: dict[str, Combination]
    max_trials: int = Field(default=3,ge=1,le=100)
    analysis_protocol: EvidenceRef | None = None
    endpoint_target: EvidenceRef | None = None
    analysis_required_before_run: bool = False
    math_evaluation_limit: int = Field(default=24,ge=0,le=24)
    math_selection_required_before_run: bool = False
    stop_on_task_success: bool = False
    multi_category_coverage_required: bool = False
    stop_on_constant_initialization: bool = False
    guidance: str = 'Select a legal combination and structure; evaluate, inspect evidence, then continue, adjust or finish. Reserve a solve for independent review when useful.'


class RouteAction(Contract):
    node_id: Identifier = Field(description='Unique label for this route action; reuse the original request_id to recover a sealed call.')
    action: Literal['build','run','optimize','diagnose','crosscheck','video','finish'] = Field(description='build constructs only; run simulates and evaluates a saved build; optimize searches and evaluates; diagnose analyzes saved results; crosscheck executes independently; video renders saved results; finish delivers an evaluated candidate.')
    combination: str | None = Field(default=None, description='OMIT for run: the saved build owns its combination. Required for build, optimize without source_node, and crosscheck. With an optimization source, omit to preserve its bindings; an explicit choice must match them.')
    changes: dict = Field(default_factory=dict, description='build/optimize only: edits from the declared space, including template, physical paths, discretization paths and control/ paths. Applied to the source configuration, or the frozen baseline when no source is supplied.')
    variables: dict[str, tuple[float,float]] = Field(default_factory=dict, description='optimize only, required: continuous numeric variables[path] = [lower_bound, upper_bound], a continuous interval, NOT two requested samples. Integer, choice, template, and discretization changes belong in explicit changes. Bounds must be within the authorized space and include the starting value.')
    max_trials: int = Field(default=1,ge=1,description='Maximum optimizer proposals, bounded by route max_trials; independent of single run, which needs one solve. Duplicate proposals may reuse saved results.')
    source_node: Identifier | None = Field(default=None, description='Completed node_id: run requires build; optimize accepts build/run/optimize; diagnose/crosscheck/video require an evaluated run or optimize node. Finish defaults to the session incumbent; supply source_node with candidate_id to select another valid candidate. Never an artifact ID.')
    candidate_id: str | None = Field(default=None, description='Optional candidate label on build; selects an optimization trial on later actions. Finish without candidate_id delivers the session-wide incumbent. A single run preserves the build candidate label.')
    evidence: list[EvidenceRef] = Field(default_factory=list, description='After the first action, cite at least one previous route node result reference here. route overview already supplies these references; a separate read is optional.')
    reason: str = Field(min_length=1,description='English explanation grounded in the current overview or cited evidence.')
    next_step: str = Field(min_length=1,description='English statement of the intended next decision or stopping condition.')
    design_statement: dict | None = Field(default=None, description='On finish, restate candidate_facts: candidate_id, configuration, owner_run_id, execution_id and parameters (path, baseline_value, effective_value, baseline_delta, unit), plus physical_changes when supplied. Checked independently of reach and prose interpretation; legacy callers may omit.')
    result_statement: ReachFacts | TrackingFacts | None = Field(default=None, description='On free-reach or tracking finish, copy the applicable factual_result exactly from the selected summary. Typed consistency is checked separately from provider reasoning; omission is not a pass.')


class RouteAnalysisAction(Contract):
    node_id: Identifier
    source_node: Identifier = Field(description='Owned completed Route build analyzed by all supplied evidence.')
    evidence: list[EvidenceRef] = Field(default_factory=list)
    linearization: EvidenceRef | None = None
    metrics: EvidenceRef | None = None
    endpoint: EvidenceRef | None = None
    screen: EvidenceRef | None = None
    historical_math_binding: EvidenceRef | None = Field(default=None, description='Owned output of analysis.bind_historical_math for source_node. Named references are inherited from it; any explicit references must match.')
    math_optimization: EvidenceRef | None = None
    selected_optimizer_candidate_id: str | None = Field(default=None, description='Exact proposal candidate_id selected from math_optimization. Required with math_optimization when mathematical proposal selection is enforced; the proposal is compared to this build by complete scientific configuration, not bookkeeping labels.')
    validation_disposition: Literal['recommended','deferred','additional_analysis']
    reason: str = Field(min_length=1)
    next_step: str = Field(min_length=1)


class RouteAnalysisActionV2(RouteAnalysisAction):
    candidate_analysis_bundle: EvidenceRef | None = Field(default=None, description='Owned completed analysis.prepare_candidate result for source_node. Component references are resolved from this bundle; explicit component references, when supplied, must match it.')


class ProposalBuildAction(Contract):
    node_id: Identifier = Field(description='Unique Route construction node identifier.')
    optimizer_result: EvidenceRef = Field(description='Exact mathematical optimizer result containing the selected proposal.')
    optimizer_candidate_id: str = Field(min_length=1, description='Exact proposal candidate_id from optimizer_result; never a build label.')
    reason: str = Field(min_length=1, description='Concise evidence-grounded reason for constructing this already-selected proposal.')
    next_step: str = Field(min_length=1, description='Intended analysis/report or stopping decision after construction.')


class RouteResult(Contract):
    detail: dict


class Inspect(Contract):
    pass


def task_result_schema(schema, task_family):
    """Small provider projection only; RouteAction retains both runtime contracts."""
    names={'task.reach':('ReachFacts','TrackingFacts'),
           'task.tracking':('TrackingFacts','ReachFacts')}
    if task_family not in names: return schema
    schema=deepcopy(schema)
    keep,remove=names[task_family]
    field=schema['properties']['result_statement']
    field['anyOf']=[{'$ref':'#/$defs/'+keep},{'type':'null'}]
    field['description']='On finish copy the selected factual_result exactly; typed consistency is checked separately from prose.'
    schema['$defs'].pop(remove,None)
    return schema


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
            state['route']=dict(source=spec.source,nodes=[],current=None,next_step='Select and evaluate an authorized candidate',incumbent=None,final=None,
                math_evaluations=dict(limit=spec.math_evaluation_limit,used=0,remaining=spec.math_evaluation_limit,
                    cache={},attempts=[]))
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
    result=dict(run_id=host.run_id,status=session['status'],task=plain(inp.task),route=route,counts=counts,
        combinations=combinations,baseline=design_summary(inp.robot.structure.data),space=dict(
            templates={name:design_summary(design) for name,design in space.get('templates',{}).items()},
            parameters=space.get('parameters',{}),control_parameters=space.get('control_parameters',{}),
            model_parameters=space.get('model_parameters',{}),discretization_parameters=space.get('discretization_parameters',{})),
        max_trials=spec.max_trials,guidance=spec.guidance,usage=host.store.remaining(host.run_id),
        project_usage=host.store.remaining(),stop_reason=session['state'].get('stop_reason'),
        limitations=['Incumbent means lowest score among valid comparable evaluated candidates in this Route session; no global optimum claim.',
            'Diagnosis is observational, not causal. Text adapter has not viewed videos.',
            'Serial bending cells only; no torsion/shear/stretch, friction, motor dynamics or general trajectory optimization.'])
    if spec.analysis_protocol and spec.endpoint_target:
        ledger=route.get('math_evaluations',dict(limit=spec.math_evaluation_limit,used=0,
            remaining=spec.math_evaluation_limit,cache={},attempts=[]))
        result['analysis_workflow']=dict(protocol=plain(spec.analysis_protocol),endpoint_target=plain(spec.endpoint_target),
            required_before_run=spec.analysis_required_before_run,math_evaluation_limit=spec.math_evaluation_limit,
            math_evaluations_used=ledger['used'],math_evaluations_remaining=ledger['remaining'],
            math_selection_required_before_run=spec.math_selection_required_before_run,
            multi_category_coverage_required=spec.multi_category_coverage_required,
            call_order=['design.build_proposal','analysis.bind_historical_math','route.record_analysis']
                if spec.historical_math else ['design.optimize_math','design.build_proposal','analysis.prepare_candidate',
                    'route.record_analysis'],
            historical_math=plain(spec.historical_math) if spec.historical_math else None,
            optimizer_scope=('Primary: official-tolerance-normalized position residual upper bound from the controller-start '
                'frozen local affine exact-ZOH model. Secondary: normalized input energy of a position-feasible witness. '
                'Terminal braking and other sampled configurations are not aggregated into this objective.'),
            optimizer_limits=('The straight-start world-x position-control mapping can be zero; prior evidence found equal '
                'primary residuals across material scenarios and tested section scales, with length changes dominant. '
                'This can favor geometric alignment and does not predict nonlinear bending, closed-loop reach, settling, '
                'real-time performance or global optimality. Screening remains advisory.'))
    return result


def design_summary(design):
    return dict(id=design.get('id'),components=[dict(id=c['id'],kind=c['kind'],length_m=c.get('length_m'),
        sections=[s['section'] for s in c.get('sections',[])]) for c in design.get('components',[])],
    tendons=len(design.get('tendons',[])),actuators=len(design.get('actuators',[])))


def trial_facts(store, baseline, trial):
    from .candidate import candidate_facts
    execution = (trial.get('simulation') or {}).get('execution_id')
    owner = trial.get('owner_run_id') or trial.get('run_id')
    reference = trial.get('configuration')
    if execution and owner:
        reference = store.session(owner)['state']['result_executions'][execution]['candidate_input']
    return candidate_facts(baseline, store.artifact(reference), reference,
        trial['candidate_id'], owner if execution else None, execution)


def compact_reports(projection):
    """One copy per exact report binding; different executions remain distinct."""
    reports = {}
    for item in (projection.get('selected_summary'), projection.get('incumbent'),
                 projection.get('route', {}).get('final')):
        if item and item.get('profile_report') and 'profile_report_summary' in item:
            key = digest(item['profile_report'])
            detail=item.pop('profile_report_summary')
            reports[key] = dict(binding=item['profile_report'], facts=(item.get('factual_result') or detail) if 'tracking' not in detail else detail)
            if detail.get('motion_summary'): reports[key]['motion_summary']=detail['motion_summary']
            item['profile_report_summary_ref'] = key
    projection['profile_reports'] = reports
    return projection


def model_options(host, inp, combinations):
    """Compact projection of deterministic assessments for invokable model paths."""
    from .contracts import GVSBasisSpecification, GVSModelParameters
    from .model_applicability import USES, assess_model_uses
    from schemas.platform import Payload

    grants = inp.policy.tool_bindings

    def available(name, version):
        if grants.get(name) != version:
            return False
        definition = host.reg.get(name, version, 'tool')
        return (definition.capabilities.get('route_visible', False) and
                host.reg.inspect(definition, grants)['executable'])

    def option(assessment, binding, tools, backend_solves):
        declaration = host.reg.mathematical_model(binding)
        def short(reason):
            return reason if len(reason) <= 160 else reason[:157] + '...'
        return dict(model_id=assessment.model_id,
            representation=dict(kind=assessment.representation_kind,
                identity=assessment.representation_id,
                strategy=assessment.representation_strategy,
                generalized_coordinate_dimension=assessment.generalized_coordinate_dimension,
                state_dimension=assessment.state_dimension),
            uses={use: verdict.status for use, verdict in assessment.uses.items()},
            reasons={use: [short(reason) for reason in verdict.reasons]
                     for use, verdict in assessment.uses.items() if verdict.status != 'ALLOW'},
            intended_uses=declaration.intended_uses,
            assumptions=assessment.relevant_assumptions,
            unsupported_requested_physics=assessment.unsupported_requested_physics,
            validation='unavailable', tools=tools, backend_solves=backend_solves)

    def binding(model_id, contract, data=None):
        return Binding(extension_id=model_id,
            parameters=Payload(contract=contract, data=data or {}))

    options = {}
    if available('kinematics.pcc_forward', '2.0.0'):
        model = binding('model.pcc', 'family.pcc_model')
        assessment = assess_model_uses(inp.robot, inp.task, model, list(USES), registry=host.reg)
        tools = ['kinematics.pcc_forward']
        if available('kinematics.pcc_describe', '1.0.0'):
            tools.insert(0, 'kinematics.pcc_describe')
        options['pcc'] = option(assessment, model, tools,
            host.reg.get('kinematics.pcc_forward', '2.0.0').capabilities['backend_solves'])

    describe_version = grants.get('dynamics.gvs_describe')
    evaluate_version = grants.get('dynamics.gvs_evaluate')
    if (describe_version in ('1.0.0', '2.0.0') and
            evaluate_version in ('2.0.0', '3.0.0') and
            available('dynamics.gvs_describe', describe_version) and
            available('dynamics.gvs_evaluate', evaluate_version)):
        strategies = (get_args(GVSBasisSpecification.model_fields['strategy'].annotation)
                      if describe_version == '2.0.0' and evaluate_version == '3.0.0'
                      else ('first_order',))
        base_tools = ['dynamics.gvs_describe', 'dynamics.gvs_evaluate']
        equilibrium_version = grants.get('statics.gvs_equilibrium')
        build_version = grants.get('dynamics.gvs_build_system')
        assembler = host.reg.get('optimization_assembler.gvs_inverse', '2.0.0',
                                 'optimization_assembler')
        can_optimize = (available('optimization.assemble', '1.0.0') and
                        host.reg.inspect(assembler, {assembler.extension_id: assembler.version})['executable'])
        representations = {}
        for strategy in strategies:
            tools = list(base_tools)
            can_equilibrate = (equilibrium_version == '2.0.0' or
                               (strategy == 'first_order' and equilibrium_version == '1.0.0'))
            if can_equilibrate and available('statics.gvs_equilibrium', equilibrium_version):
                tools.append('statics.gvs_equilibrium')
            can_build = (build_version == '3.0.0' or
                         (strategy == 'first_order' and build_version == '2.0.0'))
            if can_build and available('dynamics.gvs_build_system', build_version):
                tools.append('dynamics.gvs_build_system')
                if available('linearization.linearize', '2.0.0'):
                    tools.append('linearization.linearize')
                    if available('control.lqr_synthesize', '1.0.0'):
                        tools.append('control.lqr_synthesize')
            if can_optimize:
                tools.append('optimization.assemble')
            parameters = GVSModelParameters(basis=GVSBasisSpecification(strategy=strategy))
            model = binding('model.gvs', 'family.gvs_model', parameters.model_dump(mode='json'))
            assessment = assess_model_uses(inp.robot, inp.task, model, list(USES), registry=host.reg)
            if assessment.representation_id is not None:
                representations[strategy] = option(assessment, model, tools,
                    host.reg.get('dynamics.gvs_evaluate', evaluate_version).capabilities['backend_solves'])
                if evaluate_version == '3.0.0':
                    representations[strategy]['basis_argument'] = dict(basis=dict(strategy=strategy))
                if can_optimize:
                    representations[strategy]['optimization_assembler'] = dict(
                        extension_id=assembler.extension_id, version=assembler.version,
                        parameter_contract='family.gvs_inverse_assembler_parameters',
                        parameter_version='2.0.0', basis=dict(strategy=strategy))
        if representations:
            options['gvs'] = dict(representations=representations)

    serial = [(name, choice) for name, choice in combinations.items()
              if choice['dynamics_model']['extension_id'] == 'model.serial_bending_cells'
              and choice['executable']]
    if serial and inp.policy.discretization is not None and grants.get('route.advance') == '1.0.0':
        model = Binding.model_validate(serial[0][1]['dynamics_model'])
        discretization = host.reg.parse(inp.policy.discretization)
        assessment = assess_model_uses(inp.robot, inp.task, model, list(USES),
            discretization=discretization, registry=host.reg)
        options['serial_bending'] = option(assessment, model, ['route.advance'], 1)
        options['serial_bending']['execution_backends'] = sorted({
            choice['backend']['extension_id'] for _, choice in serial})
    return dict(source='frozen_robot_and_task', options=options)


def overview(host):
    """Small factual projection shared by inspect and provider context."""
    full=view(host); route=full['route']; nodes=route['nodes']
    completed=[n for n in nodes if n['status']=='completed']
    selected_node=next((n for n in reversed(completed) if n['action'] in ('build','run','optimize')),None)
    summary=deepcopy(selected_node['summary']) if selected_node else {}
    evaluated=next((n for n in reversed(completed) if n['action'] in ('run','optimize') and n['summary'].get('candidate_id')),None)
    inp=SessionInput.model_validate(host.store.session(host.run_id)['snapshot']['input'])
    # Read-only projection also repairs context for old immutable route evidence.
    if selected_node and summary.get('candidate_id'):
        result=host.store.artifact(selected_node['result'])
        summary['candidate_facts']=trial_facts(host.store, inp, result.get('best') or result)
        if policy(inp).multi_category_coverage_required:
            from .candidate import experiment_coverage
            summary['coverage']=experiment_coverage(summary['candidate_facts'])
        facts=bound_result_facts(host.store,result.get('best') or result,summary['candidate_facts'])
        if facts is not None:summary['factual_result']=facts
    incumbent=deepcopy(route.get('incumbent'))
    if incumbent:
        node=next(n for n in nodes if n['node_id']==incumbent['node_id'])
        result=host.store.artifact(node['result'])
        trial=(next(t for t in result['trials'] if t['candidate_id']==incumbent['candidate_id'])
               if node['action']=='optimize' else result)
        incumbent['candidate_facts']=trial_facts(host.store, inp, trial)
        facts=bound_result_facts(host.store,trial,incumbent['candidate_facts'])
        if facts is not None:incumbent['factual_result']=facts
    space=inp.policy.candidate_builder.parameters.data
    with host.store.connect(True) as db:
        snapshot_ref=plain(EvidenceRef(artifact_id=db.execute('SELECT snapshot FROM sessions WHERE run_id=?',(host.run_id,)).fetchone()[0]))
    projection=dict(run_id=host.run_id,status=full['status'],stage='finished' if route['final'] else (selected_node['action'] if selected_node else 'selection'),
        selected_candidate=summary.get('candidate_id'),has_solve=full['counts']['solves']>0,
        has_evaluation=full['counts']['evaluations']>0,selected_summary=summary,
        latest_evaluated_node=evaluated['node_id'] if evaluated else None,
        incumbent=incumbent,
        frozen_input=dict(reference=snapshot_ref,task_pointer='/input/task',design_pointer='/input/robot/structure/data',
            space_pointer='/input/policy/candidate_builder/parameters/data',combinations_pointer='/input/policy/route/data/combinations'),
        route=dict(current=route['current'],next_step=route['next_step'],final=delivery_summary(route['final']),nodes=[
            {k:n[k] for k in ('node_id','action','status','result','error') if k in n} for n in nodes[-8:]]),
        combinations={name:dict(dynamics_model=c['dynamics_model']['extension_id'],backend=c['backend']['extension_id'],
            controller=c['controller']['extension_id'],
            executable=c['executable'],reasons=c['reasons']) for name,c in full['combinations'].items()},
        model_options=model_options(host, inp, full['combinations']),
        control_profiles=control_profiles(host,inp,full['combinations']),
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
            finish='Deliver session-wide valid incumbent by default; source_node plus candidate_id explicitly selects another valid candidate; zero solves.'),
        evidence_access='Node result references below are already available for citation. Read details only when needed. evidence.read returns content or a labeled pointer overview.',
        guidance=full['guidance'],
        limitations=full['limitations'])
    if full.get('analysis_workflow'):
        projection['analysis_workflow']=full['analysis_workflow']
        from types import SimpleNamespace
        from .candidate_analysis import candidate_analysis_status
        session=host.store.session(host.run_id)
        analysis_ctx=SimpleNamespace(host=host,store=host.store,reg=host.reg,run_id=host.run_id,
            input=inp,snapshot=session['snapshot'],artifact=host.store.artifact)
        statuses=[]
        for build_node in (row for row in nodes if row.get('action')=='build' and row.get('status')=='completed'):
            status=candidate_analysis_status(analysis_ctx,build_node['node_id'])
            try:
                check_run_eligibility(host,build_node['node_id'])
                status['run_prerequisites']=dict(satisfied=True)
            except ValueError as exc:
                status['run_prerequisites']=dict(satisfied=False,blocking_error=str(exc),
                    required_next_step=(f"Call analysis.prepare_candidate with source_node={build_node['node_id']!r}, then "
                        'register its bundle with route.record_analysis@2.0.0 and cite the build result.'))
            statuses.append(status)
        projection['candidate_analysis_status']=statuses
        projection['available_actions']['build_proposal']='Construct one exact named optimizer proposal without retyping its configuration; zero solves.'
        if full['analysis_workflow'].get('historical_math'):
            projection['available_actions']['bind_historical_math']='Bind frozen named historical references to the exact proposal build; zero new mathematics and zero solves.'
        projection['available_actions']['record_analysis']='Register an exact candidate-analysis bundle (or legacy explicit/historical chain) on a completed build; advisory and zero backend solves.'
        projection['available_actions']['prepare_candidate']='Complete or reuse the exact candidate-bound four-part analysis bundle for source_node; zero backend solves and no design choice.'
    if route.get('final',{}):
        final=route['final']
        if final.get('configuration') and final.get('simulation'):
            projection['route']['final']['candidate_facts']=trial_facts(host.store,inp,final)
    projection['result_contract']=dict(task_family=inp.task.family,
        result_type='tracking' if inp.task.family=='task.tracking' else 'free_reach',
        delivery='Copy selected factual_result into result_statement; keep design_statement checks. No tracking metrics required for free reach.')
    projection['experiment_progress']=dict(evaluated_candidate_count=full['counts']['evaluations'],
        remaining_execution_opportunities=full['project_usage']['remaining']['backend_solves'])
    prior=policy(inp).historical_case
    if prior:
        bound=host.store.artifact(prior)
        from .candidate_comparison import historical_comparisons, exploration_summary, prior_overview
        projection['historical_case']=prior_overview(bound)
        projection['historical_comparisons']=historical_comparisons(host,inp,bound)
        projection['exploration_summary']=exploration_summary(host,inp,bound)
    return compact_reports(projection)


def inspect(ctx,args): return RouteResult(detail=overview(ctx.host))


def profile_capability(inp,reg):
    definition,_=reg.bind(inp.policy.controller,'controller')
    if not definition.capabilities.get('profile_id'): return None
    check=definition.hook('route_applicability')
    if check: check(inp)
    capability=dict(definition.capabilities)
    assess=definition.hook('scope_assessment')
    if assess:capability['scope_assessment']=assess(inp)
    return capability


def control_profiles(host,inp,combinations):
    """Only authorized combinations with matching physical/execution scope are options."""
    rows=[]
    for name,choice in combinations.items():
        if not choice['executable']: continue
        candidate=SessionInput.model_validate({**plain(inp),'policy':{**plain(inp.policy),
            **{k:choice[k] for k in ('dynamics_model','backend','controller')}}})
        try: capability=profile_capability(candidate,host.reg)
        except ValueError: continue
        if not capability: continue
        required=('route.advance','simulation.run','evaluation.run')
        authorized=all(t in inp.policy.tool_bindings for t in required)
        rows.append(dict(combination=name,profile_id=capability['profile_id'],
            controller=choice['controller'],predictor=capability['predictor'],
            execution_model=capability['execution_model'],command_space=capability['command_space'],
            applicability='compatible_unvalidated' if capability.get('scope_assessment') else 'matching',executable=authorized,
            scope_assessment=capability.get('scope_assessment'),
            reasons=[] if authorized else ['Required Route execution tools are not granted'],
            discovery=capability.get('discovery_tool') if capability.get('discovery_tool') in inp.policy.tool_bindings else None,
            report_authorized=capability.get('route_report_tool') in inp.policy.tool_bindings,
            historical_cost=capability.get('historical_cost')))
    return rows


def preflight(inp,args,reg):
    spec=policy(inp)
    if spec.multi_category_coverage_required and args.action in ('optimize','crosscheck'):
        raise ValueError('COVERED_EXPERIMENT_REQUIRES_PROPOSAL_BUILD_AND_RUN')
    if inp.task.family=='task.tracking' and args.action in ('optimize','crosscheck'):
        raise ValueError('TRACKING_ROUTE_REQUIRES_EXPLICIT_ANALYZED_BUILD_AND_RUN')
    if args.max_trials>spec.max_trials: raise ValueError('ROUTE_TRIAL_LIMIT')
    if args.action in ('build','crosscheck') or (args.action=='optimize' and (args.combination or not args.source_node)):
        selected(inp,spec,args.combination,reg)
    if args.source_node and args.action=='build': raise ValueError('BUILD_SOURCE_NOT_SUPPORTED: use optimize to modify a saved source or build from baseline')
    if args.action not in ('build','optimize') and (args.changes or args.variables):
        raise ValueError('CHANGES_AND_VARIABLES_ONLY_FOR_BUILD_OR_OPTIMIZE')
    if args.action=='run' and args.combination:
        from tools.platform_validation import ToolArgumentError
        raise ToolArgumentError('arguments.combination: RUN_PRESERVES_BUILD_COMBINATION; omit combination and retain the explicit build source_node')
    if args.action in ('run','diagnose','crosscheck','video') and not args.source_node:
        raise ValueError('SOURCE_NODE_REQUIRED')
    if args.action=='finish' and args.candidate_id and not args.source_node:
        raise ValueError('EXPLICIT_CANDIDATE_REQUIRES_SOURCE_NODE')
    if args.action=='build' and args.variables: raise ValueError('VARIABLES_ONLY_FOR_OPTIMIZE')
    return dict(cost={'wall_s':0.})


def preflight_proposal(inp,args,reg):
    spec=policy(inp)
    if not spec.analysis_protocol or not spec.endpoint_target:
        raise ValueError('ROUTE_ANALYSIS_NOT_CONFIGURED')
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


def update_incumbent(ctx,route,node,out):
    """Track session-wide comparable evidence without copying the full trial."""
    if node['action']=='run': trials=[out]
    elif node['action']=='optimize': trials=out.get('trials',[])
    else: return
    for trial in trials:
        if trial.get('status')!='valid' or trial.get('score') is None or not trial.get('evaluation'):
            continue
        evaluation=ctx.store.artifact(trial['evaluation'])
        if evaluation.get('validity')!='valid': continue
        previous=route.get('incumbent')
        comparison=evaluation.get('comparison_identity')
        if previous and previous['comparison_identity']!=comparison: continue
        if previous is None or trial['score']<previous['score']:
            summary={k:evaluation[k] for k in ('validity','task_success','metrics','source_execution_id') if k in evaluation}
            route['incumbent']=dict(node_id=node['node_id'],search_run_id=out.get('run_id') if node['action']=='optimize' else None,
                candidate_id=trial['candidate_id'],owner_run_id=trial.get('owner_run_id',out.get('run_id')),
                evaluation_ref=trial['evaluation'],evaluation=summary,score=trial['score'],
                comparison_identity=comparison,candidate_facts=trial_facts(ctx.store,ctx.input,trial),
                **{k:trial[k] for k in ('profile_report','profile_report_summary','factual_result') if k in trial})


def _proposal_ids(optimized):
    return [row.get('candidate_id') for row in optimized.get('proposals',[]) if row.get('candidate_id')]


def _proposal_error(field,value,valid,code='ROUTE_SELECTED_OPTIMIZER_PROPOSAL_NOT_FOUND'):
    return ValueError(f'{code}: field={field}; submitted={value!r}; valid_optimizer_candidate_ids={valid!r}')


def _optimizer_source(ctx,reference):
    """Accept only a same-run optimizer receipt or the one frozen historical import."""
    import json
    wanted=plain(reference)
    with ctx.store.connect(True) as db:
        for row in db.execute('SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(ctx.run_id,)):
            receipt=json.loads(row['receipt'])
            if (receipt.get('tool_id')=='design.optimize_math' and receipt.get('execution_status')=='completed'
                    and receipt.get('output')==wanted):
                return dict(mode='current_run',tool_version=receipt['tool_version'])
    frozen=policy(ctx.input).historical_math
    if frozen:
        manifest=ctx.artifact(frozen)
        if manifest.get('kind')!='historical_math_import_manifest':
            raise ValueError('ROUTE_HISTORICAL_MATH_MANIFEST_KIND_MISMATCH')
        if manifest.get('optimizer_result')==wanted:
            return dict(mode='historical_import',tool_version=manifest.get('optimizer_tool_version'),
                import_manifest=plain(frozen),manifest=manifest)
    raise ValueError('ROUTE_OPTIMIZER_RESULT_NOT_OWNED_OR_FROZEN_IMPORT: field=optimizer_result; submitted='+repr(wanted))


def _build_data(ctx,inp,node_id,max_trials):
    data=plain(SessionInput.model_validate(inp));data['run_id']=ctx.run_id[:40]+'-'+digest(node_id)[:16]
    data['policy']['allowed_tools']=[]
    data['policy']['tool_bindings']={k:v for k,v in ctx.input.policy.tool_bindings.items() if k in (
        'simulation.run','evaluation.run','diagnostics.saved_trajectory','visualization.render_simulation_video','evidence.read')}
    capability=profile_capability(SessionInput.model_validate(data),ctx.reg)
    report_tool=capability.get('route_report_tool') if capability else None
    if report_tool in ctx.input.policy.tool_bindings:
        data['policy']['tool_bindings'][report_tool]=ctx.input.policy.tool_bindings[report_tool]
    data['policy']['budget']['backend_solves']=max_trials
    data['policy']['search']=None
    return data


def _compiled_build(ctx,inp,node_id,max_trials):
    """Shared Route build compiler used by ordinary and proposal-bound construction."""
    from tools.platform_tasks import compile_input
    data=_build_data(ctx,inp,node_id,max_trials)
    compiled=compile_input(data,ctx.reg)
    with ctx.store.transaction() as db:
        reference=ctx.store.put(db,compiled['input'])
    return data,compiled,plain(reference)


def build_proposal(ctx,args):
    """Construct one exact optimizer proposal and retain its immutable source identity."""
    spec=policy(ctx.input);route=ctx.store.session(ctx.run_id)['state']['route']
    if route['final']: raise ValueError('ROUTE_ALREADY_FINISHED')
    if any(n['node_id']==args.node_id for n in route['nodes']):
        raise ValueError('NODE_ID_ALREADY_USED: resume original tool request')
    if route['current']: raise ValueError('ROUTE_NODE_UNRESOLVED')
    optimized=ctx.artifact(args.optimizer_result)
    valid=_proposal_ids(optimized)
    if optimized.get('kind')!='mathematical_design_optimization':
        raise ValueError('ROUTE_MATH_OPTIMIZATION_RESULT_REQUIRED: field=optimizer_result; submitted='+repr(plain(args.optimizer_result)))
    source=_optimizer_source(ctx,args.optimizer_result)
    matches=[row for row in optimized.get('proposals',[]) if row.get('candidate_id')==args.optimizer_candidate_id]
    if len(matches)>1:
        raise _proposal_error('optimizer_candidate_id',args.optimizer_candidate_id,valid,'ROUTE_OPTIMIZER_PROPOSAL_ID_NOT_UNIQUE')
    if not matches:
        raise _proposal_error('optimizer_candidate_id',args.optimizer_candidate_id,valid)
    proposal=matches[0];proposal_ref=proposal.get('configuration')
    evaluation=next((row for row in optimized.get('evaluations',[]) if
        row.get('candidate_id')==args.optimizer_candidate_id and row.get('configuration')==proposal_ref),None)
    if proposal_ref not in optimized.get('evidence',[]) or evaluation is None:
        raise ValueError('ROUTE_OPTIMIZER_PROPOSAL_EVIDENCE_CHAIN_MISMATCH: field=optimizer_candidate_id; submitted='+repr(args.optimizer_candidate_id))
    proposed=SessionInput.model_validate(ctx.artifact(proposal_ref))
    if plain(proposed.task)!=plain(ctx.input.task):
        raise ValueError('ROUTE_PROPOSAL_FROZEN_TASK_MISMATCH: field=proposal_configuration; submitted='+repr(proposal_ref))
    combination=next((name for name,choice in spec.combinations.items() if all(
        plain(getattr(proposed.policy,key))==plain(getattr(choice,key)) for key in ('dynamics_model','backend','controller'))),None)
    if combination is None:
        raise ValueError('ROUTE_PROPOSAL_COMBINATION_NOT_AUTHORIZED: field=proposal_configuration; submitted='+repr(proposal_ref))
    from .candidate_analysis import scientific_configuration,scientific_configuration_identity
    scientific_id=scientific_configuration_identity(proposed)
    declared=(evaluation.get('candidate_binding') or {}).get('scientific_configuration_identity')
    if declared and declared!=scientific_id:
        raise ValueError('ROUTE_OPTIMIZER_PROPOSAL_SCIENTIFIC_IDENTITY_MISMATCH: field=proposal_configuration; submitted='+repr(proposal_ref))
    if source['mode']=='historical_import':
        manifest=source['manifest']
        if manifest.get('optimizer_candidate_id')!=args.optimizer_candidate_id:
            raise _proposal_error('optimizer_candidate_id',args.optimizer_candidate_id,
                [manifest.get('optimizer_candidate_id')],'ROUTE_HISTORICAL_IMPORT_PROPOSAL_MISMATCH')
        if manifest.get('proposal_configuration')!=proposal_ref or manifest.get('scientific_configuration_identity')!=scientific_id:
            raise ValueError('ROUTE_HISTORICAL_IMPORT_PROPOSAL_CONFIGURATION_MISMATCH')
    node=dict(node_id=args.node_id,action='build',request_id=ctx.request.request_id,
        execution_id=ctx.row['execution_id'],selection=plain(args),status='running')
    route['nodes'].append(node);route['current']=args.node_id;route['next_step']=args.next_step;_save(ctx,route,'started')
    try:
        data,compiled,configuration=_compiled_build(ctx,proposed,args.node_id,1)
        built_input=SessionInput.model_validate(compiled['input'])
        if scientific_configuration(built_input)!=scientific_configuration(proposed):
            raise ValueError('ROUTE_BUILT_PROPOSAL_SCIENTIFIC_CONFIGURATION_MISMATCH')
        provenance=dict(build_candidate_id=args.node_id,optimizer_candidate_id=args.optimizer_candidate_id,
            source_build_node=args.node_id,
            optimizer_starting_build_node=optimized.get('starting_binding',{}).get('source_node'),
            optimizer_result=plain(args.optimizer_result),proposal_configuration=proposal_ref,
            scientific_configuration_identity=scientific_id,optimizer_source=source['mode'],
            original_optimizer_owner_run_id=optimized.get('starting_binding',{}).get('owner_run_id'),
            optimizer_tool=dict(id='design.optimize_math',version=source.get('tool_version','1.0.0')),
            proposal_parameters=proposal.get('parameters'),material_scenario=proposal.get('material_scenario'))
        out=dict(status='built',candidate_id=args.node_id,build_candidate_id=args.node_id,
            optimizer_candidate_id=args.optimizer_candidate_id,source_build_node=provenance['source_build_node'],
            optimizer_result=plain(args.optimizer_result),proposal_configuration=proposal_ref,
            scientific_configuration_identity=scientific_id,configuration=configuration,
            proposal_provenance=provenance,simulated=False,evaluated=False,
            facts='Exact optimizer proposal built and validated; not simulated or evaluated.',actual_solves=0,
            findings=design_summary(data['robot']['structure']['data']))
        out['candidate_facts']=trial_facts(ctx.store,ctx.input,out)
    except Exception as exc:
        node.update(status='failed',error=str(exc));route['current']=None;_save(ctx,route,'failed');raise
    with ctx.store.transaction() as db: ref=ctx.store.put(db,out)
    node.update(status='completed',result=plain(ref),summary=summarize(out));route['current']=None;_save(ctx,route,'completed')
    return RouteResult(detail=dict(node={k:node[k] for k in ('node_id','action','status')},
        result=plain(ref),summary=node['summary'],proposal_provenance=provenance,final=delivery_summary(route['final'])))


def _built_run_inputs(ctx,args,route):
    """Apply the exact run gate without beginning backend/controller work."""
    node,built=source_node(ctx,args,route)
    if node['action']!='build': raise ValueError('BUILT_SOURCE_NODE_REQUIRED')
    candidate=built['candidate_id']
    if args.candidate_id and args.candidate_id!=candidate: raise ValueError('CANDIDATE_SELECTION_MISMATCH')
    inp=ctx.store.artifact(built['configuration'])
    if policy(ctx.input).multi_category_coverage_required:
        from .candidate import candidate_facts,experiment_coverage
        coverage=experiment_coverage(candidate_facts(ctx.input,inp,built['configuration'],candidate))
        if not coverage['eligible']:
            raise ValueError('MULTI_CATEGORY_COVERAGE_REQUIRED: '+str(coverage['checks']))
    if policy(ctx.input).stop_on_constant_initialization:
        for previous in route['nodes']:
            if previous.get('action')=='run' and previous.get('status')=='completed':
                facts=ctx.store.artifact(previous['result']).get('factual_result') or {}
                ranges=facts.get('applied_tension_ranges',[])
                if (facts.get('valid_complete_execution') and facts.get('control_updates',0)>0
                        and facts.get('initialization_selected')==facts['control_updates']
                        and len(ranges)==6 and all(r['minimum_n']==r['maximum_n'] for r in ranges)):
                    raise ValueError('CONSTANT_INITIALIZATION_STOP_POLICY: deliver the valid run; no blind design retries')
    if policy(ctx.input).stop_on_task_success and (route.get('incumbent') or {}).get('evaluation',{}).get('task_success') is True:
        raise ValueError('TASK_SUCCESS_STOP_POLICY: finish the passing incumbent')
    if policy(ctx.input).analysis_required_before_run:
        reports=[]
        for item in route['nodes']:
            if item.get('action')=='analyze' and item.get('status')=='completed' and item.get('result'):
                report=ctx.store.artifact(item['result'])
                if (report.get('build_configuration')==built['configuration']
                        and report.get('source_build_node')==args.source_node
                        and report.get('build_candidate_id')==built['candidate_id']): reports.append(report)
        if not reports:
            raise ValueError(f"CANDIDATE_BOUND_SHARED_ANALYSIS_REQUIRED_BEFORE_EXECUTION: candidate={candidate!r}; "
                f"source_node={args.source_node!r}; required_operation=analysis.prepare_candidate(source_node={args.source_node!r}) "
                'then route.record_analysis@2.0.0 with candidate_analysis_bundle and the build result in evidence')
        if policy(ctx.input).math_selection_required_before_run and not any(r.get('math_selection_trace',{}).get('matches_proposal') for r in reports):
            raise ValueError('MATH_OPTIMIZER_PROPOSAL_MATCH_REQUIRED_BEFORE_EXECUTION')
    prior=policy(ctx.input).historical_case
    if prior:
        from .candidate import candidate_facts
        from .historical_failure import cases
        previous=cases(ctx.artifact(prior))
        current=candidate_facts(ctx.input,inp,built['configuration'],candidate)['parameters']
        if any({r['path']:r['effective_value'] for r in c['candidate_facts']['parameters']}==
               {r['path']:r['effective_value'] for r in current} for c in previous):
            raise ValueError('FRESH_REVISION_REQUIRED: identical historical design would not count; change a declared decision before run')
    capability=profile_capability(SessionInput.model_validate(inp),ctx.reg)
    if capability and capability.get('required_candidate_analysis'):
        from .candidate_analysis import require_completed_analysis
        require_completed_analysis(ctx,built,capability['required_candidate_analysis'])
    return node,built,candidate,inp


def check_run_eligibility(host,source_node_id,candidate_id=None):
    """Read-only verification of the same preconditions used immediately by run."""
    from types import SimpleNamespace
    session=host.store.session(host.run_id)
    ctx=SimpleNamespace(host=host,store=host.store,reg=host.reg,run_id=host.run_id,
        input=SessionInput.model_validate(session['snapshot']['input']),artifact=host.store.artifact)
    args=SimpleNamespace(source_node=source_node_id,candidate_id=candidate_id)
    _,built,candidate,inp=_built_run_inputs(ctx,args,session['state']['route'])
    from .candidate_analysis import scientific_configuration_identity
    return dict(eligible=True,source_node=source_node_id,candidate_id=candidate,
        build_configuration=built['configuration'],
        scientific_configuration_identity=scientific_configuration_identity(inp))


def run_built(ctx,args,route):
    """Execute the immutable build with stable child request identities, without search."""
    from tools.platform_host import Host
    from .optimization import ensure_session
    from .crosscheck import invoke
    from tools.platform_search import score
    _,built,candidate,inp=_built_run_inputs(ctx,args,route)
    child=Host(ctx.store.root,inp['run_id'],actor='route-executor')
    ensure_session(child,inp,parent_run_id=ctx.run_id,parent_event_id=ctx.row['parent_id'])
    sim=invoke(child,'single-simulation','simulation.run',dict(candidate_id=candidate,changes={}))
    ev=invoke(child,'single-evaluation','evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']))
    result=ctx.store.artifact(ev['output'])
    metadata=ctx.store.session(child.run_id)['state']['result_executions'][sim['execution_id']]
    reported={}
    capability=profile_capability(SessionInput.model_validate(inp),ctx.reg)
    report_tool=capability.get('route_report_tool') if capability else None
    if report_tool in inp['policy']['tool_bindings']:
        receipt=invoke(child,'single-profile-report',report_tool,dict(
            simulation_request_id='single-simulation',evaluation_request_id='single-evaluation'),parent=ctx.row['parent_id'])
        detail=ctx.store.artifact(receipt['output'])['detail']
        reported=dict(profile_report=dict(reference=receipt['output'],owner_run_id=child.run_id,
            execution_id=sim['execution_id'],request_id='single-profile-report'),
            profile_report_summary={k:v for k,v in detail.items() if k!='per_update_delivery_s'})
    from .candidate import candidate_facts
    facts=candidate_facts(ctx.input,ctx.store.artifact(metadata['candidate_input']),metadata['candidate_input'],
        candidate,child.run_id,sim['execution_id'])
    from .delivery_facts import bound_result_facts
    factual_result=bound_result_facts(ctx.store,dict(**reported,evaluation=ev['output'],simulation=sim),facts)
    if factual_result is not None: reported['factual_result']=factual_result
    return dict(status='valid' if result['validity']=='valid' else 'solver_failed',run_id=child.run_id,candidate_facts=facts,
        candidate_id=candidate,build_configuration=built['configuration'],configuration=metadata['candidate_input'],
        **{k:built[k] for k in ('build_candidate_id','optimizer_candidate_id','source_build_node','optimizer_result',
            'proposal_configuration','scientific_configuration_identity','proposal_provenance') if k in built},
        simulation=sim,evaluation=ev['output'],evaluation_data=result,metrics=result['metrics'],
        task_success=result['task_success'],score=score(result,inp['task']['objectives']),
        simulated=True,evaluated=True,actual_solves=ctx.store.remaining(child.run_id)['used']['backend_solves'],**reported)


def summarize(out):
    best=out.get('best')
    ev=best.get('evaluation_data') if best else out.get('evaluation_data',out.get('evaluation'))
    sim=best.get('simulation') if best else out.get('simulation')
    summary=dict(status=out.get('status','completed'),run_id=out.get('run_id'),stop_reason=out.get('stop_reason'),
        candidate_id=best.get('candidate_id') if best else out.get('candidate_id'),
        evaluation={k:ev[k] for k in ('validity','metrics','task_success','candidate_id','source_execution_id') if k in ev} if isinstance(ev,dict) else None,
        evaluation_ref=best.get('evaluation') if best else out.get('evaluation_ref',out.get('evaluation')),
        simulation={k:sim[k] for k in ('output','execution_id','solver_status') if k in sim} if sim else None,
        simulated=bool(sim and sim.get('solver_status')=='completed'),
        evaluated=bool(isinstance(ev,dict) and ev.get('source_execution_id') and ev.get('validity')),
        task_success=best.get('task_success') if best else out.get('task_success'),
        facts=out.get('facts'),
        candidate_facts=(best or out).get('candidate_facts'),
        configuration=best.get('configuration') if best else out.get('configuration'),
        proposals=out.get('proposals'),distinct_candidates=out.get('distinct_candidates'),actual_solves=out.get('actual_solves'),
        new_evaluations=out.get('new_evaluations'),reused_evaluations=out.get('reused_evaluations'),
        findings=out.get('findings'),
        **{k:out[k] for k in ('build_candidate_id','optimizer_candidate_id','source_build_node',
            'optimizer_result','proposal_configuration','scientific_configuration_identity','proposal_provenance',
            'references','historical_math_binding') if k in out},
        **{k:(best or out)[k] for k in ('profile_report','profile_report_summary','factual_result') if k in (best or out)})
    if out.get('screen'):
        summary.update(analysis_report=out['screen'],math_optimization=out.get('math_optimization'),
            math_selection_trace=out.get('math_selection_trace'),
            validation_disposition=out.get('validation_disposition'))
    return summary


def delivery_summary(final):
    if final is None: return None
    return {k:final[k] for k in ('delivery_status','explicit_delivery','candidate_id','run_id','configuration',
        'evaluation_ref','task_success','crosscheck_status','stop_reason','selection_basis',
        'profile_report','profile_report_summary','candidate_facts','design_statement','design_statement_check',
        'interpretation_status','factual_result','result_statement','result_statement_check','build_candidate_id',
        'optimizer_candidate_id','source_build_node','optimizer_result','proposal_configuration',
        'scientific_configuration_identity','proposal_provenance') if k in final}


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
            if args.action=='build':
                data,compiled,configuration=_compiled_build(ctx,inp,args.node_id,args.max_trials)
                out=dict(status='built',candidate_id=args.candidate_id or args.node_id,configuration=configuration,
                    simulated=False,evaluated=False,facts='Built, not simulated, not evaluated. No task error or trajectory exists. Use run with this build node to execute and evaluate.',
                    actual_solves=0,findings=design_summary(data['robot']['structure']['data']))
                out['candidate_facts']=trial_facts(ctx.store,ctx.input,out)
            else:
                data=_build_data(ctx,inp,args.node_id,args.max_trials)
                out=optimize(ctx.store.root,dict(session=data,variables=args.variables,max_trials=args.max_trials),
                    parent_run_id=ctx.run_id,parent_event_id=ctx.row['parent_id'],starting_trial=starting_trial,actor='route-executor')
                if out['status']=='unknown': raise TimeoutError('UNCONFIRMED child execution')
                if out['status'] not in ('completed',): raise ValueError('OPTIMIZATION_EXECUTION_FAILED: '+str(out.get('stop_reason')))
                for trial in out.get('trials',[]):
                    if trial.get('configuration') and trial.get('simulation'):
                        trial['candidate_facts']=trial_facts(ctx.store,ctx.input,trial)
                if out.get('best'):
                    out['best']['candidate_facts']=trial_facts(ctx.store,ctx.input,out['best'])
        elif args.action=='run':
            out=run_built(ctx,args,route)
        elif args.action in ('diagnose','crosscheck','video','finish'):
            if args.action=='finish' and args.candidate_id is None:
                incumbent=route.get('incumbent')
                if incumbent is None: raise ValueError('VALID_SESSION_INCUMBENT_REQUIRED')
                from types import SimpleNamespace
                selected_args=SimpleNamespace(source_node=incumbent['node_id'],candidate_id=incumbent['candidate_id'])
            else:
                selected_args=args
            child,trial=source_trial(ctx,selected_args,route)
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
                if args.action=='diagnose':
                    from .candidate_comparison import feedback
                    trial['factual_result']=bound_result_facts(ctx.store,trial,trial_facts(ctx.store,ctx.input,trial))
                    out['findings']['design_feedback']=feedback(trial)
            else:
                out=delivery(ctx,route,child,trial,args.reason,args.design_statement,plain(args.result_statement))
                out['selection_basis']='explicit valid candidate' if args.candidate_id else 'session-wide incumbent'
                if (out.get('factual_result') or {}).get('result_type')=='free_reach' and not out['result_statement_check']['accepted']:
                    raise ValueError('REACH_RESULT_STATEMENT_REQUIRED: copy factual_result into result_statement')
                out['explicit_delivery']=True
                route['final']=out
    except Exception as exc:
        node.update(status='unknown' if isinstance(exc,TimeoutError) else 'failed',error=str(exc))
        route['current']=args.node_id if isinstance(exc,TimeoutError) else None
        _save(ctx,route,node['status'])
        raise
    with ctx.store.transaction() as db: ref=ctx.store.put(db,out)
    node.update(status='completed',result=plain(ref),summary=summarize(out))
    update_incumbent(ctx,route,node,out)
    route['current']=None
    _save(ctx,route,'completed',stop=args.action=='finish')
    return RouteResult(detail=dict(node={k:node[k] for k in ('node_id','action','status')},
        result=plain(ref),summary=node['summary'],final=delivery_summary(route['final'])))


def record_analysis(ctx,args):
    """Attach one exact shared report chain without expanding the legacy Route action contract."""
    spec=policy(ctx.input);route=ctx.store.session(ctx.run_id)['state']['route']
    if route['final']: raise ValueError('ROUTE_ALREADY_FINISHED')
    if not spec.analysis_protocol or not spec.endpoint_target: raise ValueError('ROUTE_ANALYSIS_NOT_CONFIGURED')
    if any(n['node_id']==args.node_id for n in route['nodes']): raise ValueError('NODE_ID_ALREADY_USED: resume original tool request')
    if route['current']: raise ValueError('ROUTE_NODE_UNRESOLVED')
    results={n['result']['artifact_id'] for n in route['nodes'] if n.get('result')}
    if results and not results.intersection(r.artifact_id for r in args.evidence):
        raise ValueError('ROUTE_EVIDENCE_REQUIRED: cite a previous node result')
    node=dict(node_id=args.node_id,action='analyze',request_id=ctx.request.request_id,
        execution_id=ctx.row['execution_id'],selection=plain(args),status='running')
    route['nodes'].append(node);route['current']=args.node_id;route['next_step']=args.next_step;_save(ctx,route,'started')
    try:
        build_node,built=source_node(ctx,args,route)
        if build_node['action']!='build': raise ValueError('ANALYSIS_REQUIRES_BUILD_SOURCE_NODE')
        expected=built['configuration'];historical=None;bundle=None
        refs={name:plain(getattr(args,name)) if getattr(args,name) else None
            for name in ('linearization','metrics','endpoint','screen')}
        bundle_ref=plain(getattr(args,'candidate_analysis_bundle',None)) if getattr(args,'candidate_analysis_bundle',None) else None
        if bundle_ref and args.historical_math_binding:
            raise ValueError('ROUTE_ANALYSIS_BUNDLE_AND_HISTORICAL_BINDING_CONFLICT')
        if bundle_ref:
            import json
            owned=False
            with ctx.store.connect(True) as db:
                for row in db.execute('SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(ctx.run_id,)):
                    receipt=json.loads(row['receipt'])
                    if (receipt.get('tool_id')=='analysis.prepare_candidate'
                            and receipt.get('execution_status')=='completed' and receipt.get('output')==bundle_ref):
                        owned=True;break
            if not owned:
                raise ValueError('ROUTE_CANDIDATE_ANALYSIS_BUNDLE_OWNED_TOOL_RESULT_REQUIRED: field=candidate_analysis_bundle; submitted='+repr(bundle_ref))
            bundle=ctx.artifact(bundle_ref)
            from .candidate_analysis import candidate_analysis_scope
            _,binding,bundle_protocol,bundle_target,_,_,scope_identity=candidate_analysis_scope(ctx,args.source_node)
            if (bundle.get('kind')!='candidate_analysis_bundle' or not bundle.get('complete')
                    or bundle.get('source_node')!=args.source_node
                    or bundle.get('build_candidate_id')!=built['candidate_id']
                    or bundle.get('configuration')!=expected
                    or bundle.get('scientific_configuration_identity')!=binding['scientific_configuration_identity']
                    or bundle.get('analysis_scope_identity')!=scope_identity):
                raise ValueError(f"ROUTE_CANDIDATE_ANALYSIS_BUNDLE_BUILD_OR_SCOPE_MISMATCH: candidate={built['candidate_id']!r}; source_node={args.source_node!r}")
            if bundle.get('protocol')!=bundle_protocol or bundle.get('target')!=bundle_target:
                raise ValueError(f"ROUTE_CANDIDATE_ANALYSIS_BUNDLE_PROTOCOL_OR_TARGET_MISMATCH: candidate={built['candidate_id']!r}; source_node={args.source_node!r}")
            for name in refs:
                inherited=(bundle.get('components',{}).get(name) or {}).get('reference')
                if inherited is None:
                    raise ValueError(f"ROUTE_CANDIDATE_ANALYSIS_BUNDLE_COMPONENT_REQUIRED: candidate={built['candidate_id']!r}; component={name!r}; required_operation=analysis.prepare_candidate(source_node={args.source_node!r})")
                if refs[name] is not None and refs[name]!=inherited:
                    raise ValueError(f'ROUTE_CANDIDATE_ANALYSIS_BUNDLE_REFERENCE_CONFLICT: field={name}; submitted={refs[name]!r}; bundle_original={inherited!r}')
                refs[name]=inherited
        if args.historical_math_binding:
            import json
            owned=False
            with ctx.store.connect(True) as db:
                for row in db.execute('SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(ctx.run_id,)):
                    receipt=json.loads(row['receipt'])
                    if (receipt.get('tool_id')=='analysis.bind_historical_math'
                            and receipt.get('execution_status')=='completed'
                            and receipt.get('output')==plain(args.historical_math_binding)):
                        owned=True;break
            if not owned:
                raise ValueError('ROUTE_HISTORICAL_MATH_BINDING_OWNED_TOOL_RESULT_REQUIRED: field=historical_math_binding; submitted='+repr(plain(args.historical_math_binding)))
            historical=ctx.artifact(args.historical_math_binding)
            if (historical.get('kind')!='historical_math_binding' or historical.get('source_build_node')!=args.source_node
                    or historical.get('build_candidate_id')!=built['candidate_id']
                    or historical.get('scientific_configuration_identity')!=built.get('scientific_configuration_identity')):
                raise ValueError('ROUTE_HISTORICAL_MATH_BUILD_BINDING_MISMATCH')
            for name in refs:
                inherited=historical.get('references',{}).get(name,{}).get('reference')
                if refs[name] is not None and refs[name]!=inherited:
                    raise ValueError(f'ROUTE_HISTORICAL_REFERENCE_CONFLICT: field={name}; submitted={refs[name]!r}; stored_original={inherited!r}')
                refs[name]=inherited
        missing=[name for name,value in refs.items() if value is None]
        if missing:
            raise ValueError(f"ROUTE_ANALYSIS_REFERENCE_REQUIRED: candidate={built['candidate_id']!r}; fields={missing!r}; "
                f"required_operation=analysis.prepare_candidate(source_node={args.source_node!r})")
        linear=ctx.artifact(refs['linearization']);metrics=ctx.artifact(refs['metrics'])
        endpoint=ctx.artifact(refs['endpoint']);screen=ctx.artifact(refs['screen'])
        for result,kind in ((linear,'candidate_linearization'),(metrics,'control_metrics'),
                (endpoint,'bounded_endpoint'),(screen,'design_screen')):
            wrong_binding=(historical is None and result.get('bindings') and any(
                b.get('configuration')!=expected
                or (b.get('candidate_id') is not None and b.get('candidate_id')!=built['candidate_id'])
                or (b.get('source_node') is not None and b.get('source_node')!=args.source_node)
                for b in result['bindings']))
            if result.get('kind')!=kind or not result.get('bindings') or wrong_binding:
                raise ValueError(f"ROUTE_ANALYSIS_CANDIDATE_BINDING_MISMATCH: candidate={built['candidate_id']!r}; component={kind!r}; source_node={args.source_node!r}; required_operation=analysis.prepare_candidate(source_node={args.source_node!r})")
        if screen['evidence']!=[refs['linearization'],refs['metrics'],refs['endpoint']]:
            raise ValueError('ROUTE_SCREEN_EVIDENCE_CHAIN_MISMATCH')
        if screen['protocol']!=plain(spec.analysis_protocol) or endpoint['protocol']!=plain(spec.analysis_protocol):
            raise ValueError('ROUTE_ANALYSIS_PROTOCOL_MISMATCH')
        if plain(spec.endpoint_target) not in endpoint['evidence']:
            raise ValueError('ROUTE_ENDPOINT_TARGET_EVIDENCE_MISMATCH')
        stored=built.get('proposal_provenance')
        if stored and args.math_optimization and plain(args.math_optimization)!=stored['optimizer_result']:
            raise ValueError('ROUTE_OPTIMIZER_RESULT_CONFLICT: field=math_optimization; '
                f'submitted={plain(args.math_optimization)!r}; build_stored_original={stored["optimizer_result"]!r}')
        if stored and args.selected_optimizer_candidate_id and args.selected_optimizer_candidate_id!=stored['optimizer_candidate_id']:
            optimized=ctx.artifact(stored['optimizer_result'])
            raise ValueError('ROUTE_OPTIMIZER_PROPOSAL_ID_CONFLICT: field=selected_optimizer_candidate_id; '
                f'submitted={args.selected_optimizer_candidate_id!r}; valid_optimizer_candidate_ids={_proposal_ids(optimized)!r}; '
                f'build_stored_original={stored["optimizer_candidate_id"]!r}')
        math_ref=(stored or {}).get('optimizer_result') or (plain(args.math_optimization) if args.math_optimization else None)
        selected_id=(stored or {}).get('optimizer_candidate_id') or args.selected_optimizer_candidate_id
        math_optimization=None
        selection_trace=dict(required=spec.math_selection_required_before_run,matches_proposal=False)
        if math_ref:
            import json
            if historical is not None:
                if historical.get('optimizer_result')!=math_ref or historical.get('optimizer_candidate_id')!=selected_id:
                    raise ValueError('ROUTE_HISTORICAL_MATH_OPTIMIZER_BINDING_MISMATCH')
                owned=True
            else:
                owned=False
                with ctx.store.connect(True) as db:
                    for row in db.execute('SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL',(ctx.run_id,)):
                        receipt=json.loads(row['receipt'])
                        if (receipt.get('tool_id')=='design.optimize_math' and receipt.get('execution_status')=='completed'
                                and receipt.get('output')==math_ref):
                            owned=True;break
            if not owned: raise ValueError('ROUTE_MATH_OPTIMIZATION_OWNED_TOOL_RESULT_REQUIRED')
            if not stored and math_ref not in [plain(ref) for ref in args.evidence]:
                raise ValueError('ROUTE_MATH_OPTIMIZATION_EVIDENCE_CITATION_REQUIRED')
            optimized=ctx.artifact(math_ref)
            if optimized.get('kind')!='mathematical_design_optimization':
                raise ValueError('ROUTE_MATH_OPTIMIZATION_RESULT_REQUIRED')
            if optimized.get('protocol')!=plain(spec.analysis_protocol) or optimized.get('target')!=plain(spec.endpoint_target):
                raise ValueError('ROUTE_MATH_OPTIMIZATION_PROTOCOL_OR_TARGET_MISMATCH')
            start=optimized.get('starting_binding',{})
            if historical is None:
                start_node=next((n for n in route['nodes'] if n.get('node_id')==start.get('source_node')
                    and n.get('action')=='build' and n.get('status')=='completed'),None)
                if (start.get('owner_run_id')!=ctx.run_id or start_node is None
                        or ctx.artifact(start_node['result']).get('configuration')!=start.get('configuration')):
                    raise ValueError('ROUTE_MATH_OPTIMIZATION_STARTING_BUILD_OWNERSHIP_MISMATCH')
            math_optimization=math_ref
            if spec.math_selection_required_before_run and not selected_id:
                raise ValueError('ROUTE_SELECTED_OPTIMIZER_CANDIDATE_ID_REQUIRED')
            proposals=[row for row in optimized.get('proposals',[])
                if row.get('candidate_id')==selected_id]
            if len(proposals)>1: raise _proposal_error('selected_optimizer_candidate_id',selected_id,
                _proposal_ids(optimized),'ROUTE_OPTIMIZER_PROPOSAL_ID_NOT_UNIQUE')
            matched=proposals[0] if proposals else None
            from .candidate_analysis import scientific_configuration,scientific_configuration_identity
            build_input=SessionInput.model_validate(ctx.artifact(expected))
            if matched:
                proposal_ref=matched.get('configuration')
                evaluation=next((row for row in optimized.get('evaluations',[]) if
                    row.get('candidate_id')==matched['candidate_id'] and row.get('configuration')==proposal_ref),None)
                if (proposal_ref not in optimized.get('evidence',[]) or evaluation is None):
                    raise ValueError('ROUTE_OPTIMIZER_PROPOSAL_EVIDENCE_CHAIN_MISMATCH')
                proposed=SessionInput.model_validate(ctx.artifact(proposal_ref))
                if scientific_configuration(proposed)!=scientific_configuration(build_input):
                    raise ValueError('ROUTE_SELECTED_PROPOSAL_SCIENTIFIC_CONFIGURATION_MISMATCH')
                declared=(evaluation.get('candidate_binding') or {}).get('scientific_configuration_identity')
                if declared and declared!=scientific_configuration_identity(proposed):
                    raise ValueError('ROUTE_OPTIMIZER_PROPOSAL_SCIENTIFIC_IDENTITY_MISMATCH')
            elif selected_id:
                raise _proposal_error('selected_optimizer_candidate_id',selected_id,_proposal_ids(optimized))
            selection_trace=dict(required=spec.math_selection_required_before_run,matches_proposal=matched is not None,
                scientific_configuration_identity=scientific_configuration_identity(build_input),
                optimizer_candidate_id=None if matched is None else matched['candidate_id'],
                optimizer_configuration=None if matched is None else matched['configuration'],
                optimizer_objective=None if matched is None else matched['objective'],
                optimizer_starting_build=start.get('configuration'),optimizer_result=math_ref,
                proposal_configuration=None if matched is None else matched['configuration'],
                build_candidate_id=built['candidate_id'],source_build_node=args.source_node,
                provenance_inherited_from_build=stored is not None,
                historical_computation=historical is not None)
        report=screen['records'][0]
        tool_ids=dict(linearization='analysis.linearize_candidate',metrics='analysis.control_metrics',
            endpoint='analysis.bounded_endpoint',screen='design.screen')
        references=(historical['references'] if historical is not None else {
            name:dict(reference=reference,kind=result['kind'],tool_id=tool_ids[name],
                tool_version=ctx.input.policy.tool_bindings.get(tool_ids[name]),
                source_binding=result['bindings'][0],historical_computation=False)
            for name,reference,result in ((name,refs[name],value) for name,value in (
                ('linearization',linear),('metrics',metrics),('endpoint',endpoint),('screen',screen)))})
        out=dict(status='analyzed',candidate_id=built['candidate_id'],source_node=args.source_node,
            source_build_node=args.source_node,
            build_candidate_id=built['candidate_id'],optimizer_candidate_id=selected_id,
            build_configuration=expected,protocol=screen['protocol'],linearization=refs['linearization'],
            metrics=refs['metrics'],endpoint=refs['endpoint'],screen=refs['screen'],references=references,
            math_optimization=math_optimization,shared_report_identity=digest(screen),
            math_selection_trace=selection_trace,
            historical_math_binding=plain(args.historical_math_binding) if args.historical_math_binding else None,
            validation_disposition=args.validation_disposition,disposition_reason=args.reason,
            hard_rejection=False,screen_priority=report['priority_reasoning'],
            advisory_scope='Shared local mathematics informs prioritization only; execution remains the physical validation authority.',
            actual_solves=0,simulated=False,evaluated=False)
        if bundle_ref: out['candidate_analysis_bundle']=bundle_ref
    except Exception as exc:
        node.update(status='failed',error=str(exc));route['current']=None;_save(ctx,route,'failed');raise
    with ctx.store.transaction() as db: ref=ctx.store.put(db,out)
    node.update(status='completed',result=plain(ref),summary=summarize(out));route['current']=None;_save(ctx,route,'completed')
    return RouteResult(detail=dict(node={k:node[k] for k in ('node_id','action','status')},
        result=plain(ref),summary=node['summary'],final=delivery_summary(route['final'])))


def preflight_analysis(inp,args,reg):
    spec=policy(inp)
    if not spec.analysis_protocol or not spec.endpoint_target: raise ValueError('ROUTE_ANALYSIS_NOT_CONFIGURED')
    return dict(cost={'wall_s':0.})


def _save(ctx,route,status,stop=False):
    with ctx.store.transaction() as db:
        state=ctx.store.session(ctx.run_id,db)['state']; state['route']=route
        if stop: state['stop_reason']=route['final']['stop_reason']
        ctx.store.update_state(db,ctx.run_id,state,'stopped' if stop else None)
        ref=ctx.store.put(db,route)
        ctx.store.event(db,ctx.run_id,'route_node',status,parent=ctx.row['parent_id'],
            request=ctx.request.request_id,execution=ctx.row['execution_id'],outputs=[ref])


def delivery(ctx,route,child,trial,reason,design_statement=None,result_statement=None):
    configuration=ctx.store.artifact(trial['configuration'])['effective']
    from .candidate import check_design_statement
    baseline=ctx.store.session(ctx.host.run_id)['snapshot']['input']
    facts=trial_facts(ctx.store,baseline,trial)
    from .delivery_facts import bound_result_facts, check_result_statement
    factual_result=bound_result_facts(ctx.store,trial,facts)
    result_check=check_result_statement(factual_result,result_statement) if factual_result else None
    if result_check is not None and not result_check['accepted'] and (result_statement is not None or (design_statement is not None and factual_result.get('result_type')=='free_reach')):
        raise ValueError(('REACH' if factual_result.get('result_type')=='free_reach' else 'TRACKING')+'_RESULT_STATEMENT_MISMATCH: '+str(result_check))
    reviews=[]; diagnoses=[]
    for n in route['nodes']:
        if n.get('result') and n['action'] in ('crosscheck','diagnose'):
            data=ctx.store.artifact(n['result'])
            if data.get('source_configuration',data.get('configuration'))==trial['configuration']:
                (reviews if n['action']=='crosscheck' else diagnoses).append(dict(result=n['result'],summary=n['summary']))
    search_run=trial.get('search_run_id') or child.run_id
    best=route.get('incumbent')
    return dict(delivery_status='evaluated',candidate_id=trial['candidate_id'],run_id=child.run_id,configuration=trial['configuration'],
        candidate_facts=facts,design_statement=design_statement,design_statement_check=check_design_statement(facts,design_statement),
        interpretation_status='prose_review_required',
        factual_result=factual_result,result_statement=result_statement,result_statement_check=result_check,
        search_run_id=trial.get('search_run_id'),actual_solves=0,new_evaluations=0,
        simulation=trial['simulation'],
        dynamics_model=configuration['policy']['dynamics_model'],backend=configuration['policy']['backend'],
        controller=configuration['policy']['controller'],evaluation_ref=trial['evaluation'],evaluation=trial['evaluation_data'],
        task_success=trial['task_success'],crosschecks=reviews,crosscheck_status='reviewed' if reviews else 'not_reviewed',
        diagnoses=diagnoses,stop_reason=reason,best_scope='session-wide valid comparable evaluated candidates; no global optimum',
        best_valid_evaluation=dict(node_id=best['node_id'],search_run_id=best['search_run_id'],candidate_id=best['candidate_id'],
            evaluation_ref=best['evaluation_ref'],evaluation=best['evaluation'],score=best['score']) if best else None,
        limitations=view(ctx.host)['limitations'],
        **{k:trial[k] for k in ('profile_report','profile_report_summary','build_candidate_id','optimizer_candidate_id',
            'source_build_node','optimizer_result','proposal_configuration','scientific_configuration_identity',
            'proposal_provenance') if k in trial})


def finalize_stop(host):
    """Host delivery on a terminal budget/turn/capability stop; no invented LLM choice."""
    from types import SimpleNamespace
    session=host.store.session(host.run_id); route=session['state'].get('route')
    if not route or route.get('final') or session['status'] in ('running','created','paused','needs_input'):
        return
    reason=session['state'].get('stop_reason',session['status'])
    ctx=SimpleNamespace(host=host,store=host.store)
    final=dict(delivery_status='incomplete',candidate_id=None,evaluated=False,stop_reason=reason,crosscheck_status='not_reviewed')
    incumbent=route.get('incumbent')
    if incumbent:
        child,trial=source_trial(ctx,SimpleNamespace(source_node=incumbent['node_id'],candidate_id=incumbent['candidate_id']),route)
        final=delivery(ctx,route,child,trial,reason)
    final['selection_basis']='Host terminal summary of session-wide incumbent; not an explicit model delivery'
    final['explicit_delivery']=False
    route['final']=final
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state'];state['route']=route
        host.store.update_state(db,host.run_id,state)
        ref=host.store.put(db,final);host.store.event(db,host.run_id,'route_delivery','terminal',outputs=[ref])
