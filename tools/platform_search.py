"""Algorithm-neutral ask/tell driver; Host owns evaluation and request identity."""
from schemas.platform import EvaluationResult, Objective, Payload, SessionInput
from tools.platform_store import plain
from tools.state_io import digest


def validate_batch_plan(store, view, proposal):
    """Validate one future batch against installed ask/tell and candidate paths.

    No search proposal, solve, simulation, grant or selection is executed here.
    """
    from copy import deepcopy
    from schemas.platform_handoff import SearchBatchPlan
    from tools.platform_registry import registry
    from tools.platform_tools import _candidate
    from extensions.tendon_family.optimization import SearchParameters,CoordinateSearch
    from tools.diagnostic_revision import resolve_aliases
    plan=SearchBatchPlan.model_validate(proposal);reg=registry()
    state=store.session(view.run_id)['state'];role=state['role_context']
    from tools.diagnostic_handoff import accepted_product
    accepted_product(store,role['previous_report'],'diagnosis_report')
    selectors=resolve_aliases(state,{'plan':plan.evidence})['plan']
    feedback=store.artifact(role['result_feedback'])
    if not any(s['reference']==feedback['result'] for s in selectors):raise ValueError('PLAN_REQUIRES_PERFORMED_CHECK_EVIDENCE')
    candidate=view.latest_tested
    effective=store.artifact(candidate['configuration'])['effective']
    controller=effective['policy']['controller'];identity=controller['extension_id']+'@'+controller['version']
    if plan.fixed_controller!=identity:raise ValueError('PLAN_FIXED_CONTROLLER_MISMATCH: '+identity)
    if plan.method!='search.family_coordinate@1.0.0':raise ValueError('PLAN_METHOD_UNAVAILABLE: supported search.family_coordinate@1.0.0 (candidate ask/tell only)')
    definition=reg.get('search.family_coordinate','1.0.0','search')
    if not reg.inspect(definition,{'search.family_coordinate':'1.0.0'})['executable']:raise ValueError('PLAN_METHOD_NOT_INSTALLED')
    mappings={r['parameter']:r for r in view.parameter_impacts['mapped']}
    if not plan.variables or set(plan.variables)-mappings.keys():raise ValueError('PLAN_VARIABLE_PATHS: only demonstrated speed-weight builder paths')
    initial={}
    for path,domain in plan.variables.items():
        if len(domain)!=2:raise ValueError('PLAN_DOMAIN_REQUIRES_TWO_BOUNDS: '+path)
        lo,hi=domain
        row=mappings[path];bounds=row['granted_range'];spec=row['builder_spec']
        if not row['authorized_parameter'] or not row['implementation_supported']:raise ValueError('PLAN_BUILDER_PARAMETER_UNSUPPORTED: '+path)
        if not bounds[0]<=lo<hi<=bounds[1] or not spec['bounds'][0]<=lo<hi<=spec['bounds'][1]:raise ValueError('PLAN_DOMAIN_OUTSIDE_BUILDER_GRANT: '+path)
        if 0<lo<.0001 or hi<.0001:raise ValueError('PLAN_DOMAIN_CONTAINS_ILLEGAL_BOUNDARY_WEIGHT: zero or >=0.0001 required')
        initial[path]=row['current_value']
        if not lo<=initial[path]<=hi:raise ValueError('PLAN_START_OUTSIDE_DOMAIN: saved candidate value must be included for existing coordinate method: '+path)
        # Coordinate search visits this bounded lattice; a zero lower bound
        # excludes (0,0.0001) through the builder, and the reachable lattice
        # must never propose such a value. No numerical candidate is evaluated.
        width=hi-lo
        for origin in (lo,hi,initial[path]):
            for k in range(-plan.max_candidates,plan.max_candidates+1):
                v=min(hi,max(lo,origin+k*plan.step*width))
                if 1e-12<v<.0001-1e-12:raise ValueError('PLAN_COORDINATE_STEP_CAN_PROPOSE_ILLEGAL_SMALL_WEIGHT: increase domain/step or use positive lower bound')
        # Build both boundary configurations without constructing any workspace.
        for endpoint in (lo,hi):
            changed=plain(_candidate(SessionInput.model_validate(effective),{path:endpoint},reg))
            if changed['robot']!=effective['robot'] or changed['task']!=effective['task']:raise ValueError('PLAN_FIXED_ROBOT_TASK_CHANGED')
    CoordinateSearch(SearchParameters(initial=initial,bounds=plan.variables,max_trials=plan.max_candidates,step=plan.step))
    required_fixed={'robot','task','acceptance','controller_implementation','other_numerical_settings'}
    if not required_fixed<=set(plan.fixed_conditions):raise ValueError('PLAN_FIXED_CONDITIONS_REQUIRED: '+', '.join(sorted(required_fixed)))
    required_objectives={'joint_reach_holding_acceptance','terminal_error_m','holding_max_error_m','holding_max_speed_m_s'}
    if not required_objectives<=set(plan.objectives) or set(plan.objectives)-required_objectives-{'complete_update_s'}:raise ValueError('PLAN_PHYSICAL_OBJECTIVES_REQUIRED: '+', '.join(sorted(required_objectives)))
    if not {'frozen_acceptance','force_bounds','finite_valid_execution'}<=set(plan.constraints):raise ValueError('PLAN_CONSTRAINTS_REQUIRED: frozen_acceptance, force_bounds, finite_valid_execution')
    required_verification={'candidate.apply','simulation.run','evaluation.run','control.profile_report','bound_comparison','diagnostic_revision'}
    if not required_verification<=set(plan.verification):raise ValueError('PLAN_FRESH_VERIFICATION_REQUIRED: '+', '.join(sorted(required_verification)))
    budget=plain(plan.planned_budget);count=plan.max_candidates
    if budget['backend_solves']!=count or budget['tool_calls']<count*4 or budget['worker_calls']!=0 or budget['wall_s']<count*990:
        raise ValueError('PLAN_COSTS_INSUFFICIENT: backend_solves=max_candidates, tool_calls>=4 per candidate, wall_s>=990 per candidate, workers=0')
    fixed=deepcopy(effective)
    for path in plan.variables:fixed['policy']['controller']['parameters']['data']['recipe'][path.rsplit('/',1)[-1]]='<batch variable>'
    from tools.settling_campaign import RANKING
    return dict(plan=plain(plan),structurally_operationally_valid=True,scientific_promise=plan.scientific_promise,
        semantic_status='Model-authored promise and causal reasoning are separate from operational validation.',
        execution_authorized=False,requires_future_grant=True,baseline_replaced=False,candidate_promoted=False,
        bindings=dict(task=view.task,acceptance=view.acceptance,baseline=view.baseline,subject=candidate,
            controller=controller,dynamics_model=view.task['execution_model'],source_report=role['source_report'],
            revised_assessment=role['previous_report'],check_feedback=role['result_feedback'],evidence_selectors=selectors,
            fixed_configuration_identity=digest(fixed),fixed_configuration=fixed),
        batch_semantics='One plan for the batch. Existing coordinate ask/tell proposes bounded candidates; no batch runner implemented in this stage.',
        screening=dict(local_screening='none',raw_weighted_objectives_are_physical_ranking=False),
        final_comparison_policy=RANKING,required_fresh_steps=sorted(required_verification),
        cost_floor_per_candidate_s=dict(simulation=900,evaluation=30,profile=60),
        execution_requirements=['Future grant binding this immutable plan, candidate/work limits and capabilities.',
            'Existing search proposal method alone supplies no holding ranking or deployment authority; fresh sealed profiles and frozen physical comparison are required.',
            'Candidate-specific graph/solver and regenerated warm states; old plans and measurements remain bound to original identities.'])


def submit_batch_plan(ctx,args):
    from tools.platform_handoff import require_role,transition
    from tools.working_state import project_working_state
    require_role(ctx,'design')
    result=validate_batch_plan(ctx.store,project_working_state(ctx.store,ctx.run_id),args)
    accepted=transition(ctx,'search_batch_plan',result)
    with ctx.store.transaction() as db:
        state=ctx.store.session(ctx.run_id,db)['state'];state['experiment_plan']=plain(accepted.reference)
        ctx.store.update_state(db,ctx.run_id,state)
    return accepted


def score(evaluation, objectives):
    evaluation = EvaluationResult.model_validate(evaluation)
    if len(objectives) != 1:
        raise ValueError('MULTIOBJECTIVE_RANKING_ADAPTER_REQUIRED')
    if evaluation.validity != 'valid':
        return None
    objective = Objective.model_validate(objectives[0])
    metric = next((m for m in evaluation.metrics if m.name == objective.metric), None)
    if metric is None or metric.units != objective.units:
        raise ValueError('METRIC_MISSING_OR_UNIT_MISMATCH')
    return metric.value if objective.direction == 'minimize' else -metric.value


def rank(evaluations, objectives):
    parsed = [EvaluationResult.model_validate(e) for e in evaluations]
    if len({e.comparison_identity for e in parsed}) > 1:
        raise ValueError('INCOMPARABLE_TASK_INSTANCE_BACKEND_OR_MODEL')
    rows = [(score(e, objectives), e) for e in parsed]
    return [plain(e) for s, e in sorted((r for r in rows if r[0] is not None), key=lambda r: r[0])]


def reuse_start(host, effective, trial):
    """Match one explicit source's frozen conditions; never search a global cache."""
    source = host.store.session(trial['owner_run_id'])['snapshot']
    current = host.store.session(host.run_id)['snapshot']
    original = host.store.artifact(trial['configuration'])['effective']
    # Session identity, search policy and budget do not change the simulated
    # candidate. Everything else (including task/control/numerics) must match.
    original['run_id'] = effective['run_id']
    for key in ('search', 'budget'):
        original['policy'][key] = effective['policy'][key]
    if digest(original) != digest(effective) or source['instance_identity'] != current['instance_identity']:
        return None
    if any(current['dependencies'].get(k) != v for k,v in source['dependencies'].items()
           if not k.startswith('search.')):
        return None
    evaluation = EvaluationResult.model_validate(host.store.artifact(trial['evaluation']))
    simulation = trial['simulation']
    metadata = host.store.session(trial['owner_run_id'])['state']['result_executions'][simulation['execution_id']]
    if (evaluation.validity != 'valid' or simulation['solver_status'] != 'completed'
            or evaluation.source_execution_id != simulation['execution_id']
            or plain(evaluation.source) != simulation['output']
            or evaluation.candidate_id != trial['candidate_id']
            or metadata['candidate_input'] != trial['configuration']):
        return None
    return {**trial, 'score':score(evaluation,effective['task']['objectives']),
        'comparison_identity':evaluation.comparison_identity, 'reused_evaluation':True}


def run_search(host, starting_trial=None):
    inp = host.store.session(host.run_id)['snapshot']['input']
    binding = inp['policy']['search']
    if binding is None:
        raise ValueError('SEARCH_NOT_CONFIGURED')
    definition, parameters = host.reg.bind(binding, 'search')
    if len(inp['task']['objectives']) != 1 and not definition.capabilities.get('feedback_adapter'):
        raise ValueError('MULTIOBJECTIVE_SEARCH_ADAPTER_REQUIRED')
    algorithm = definition.resolve()(parameters)
    saved = host.store.session(host.run_id)['state'].get('search')
    if saved:
        algorithm.restore(host.reg.parse(saved['algorithm']).model_dump(mode='json'))
        if saved.get('stop_reason'):
            return _outcome(host,saved,'completed',saved['stop_reason'])
    else:
        saved = dict(algorithm=plain(algorithm.save()), pending=None, trials=[])
    saved.setdefault('duplicates', [])
    saved.setdefault('proposals', len(saved['trials']))
    while saved['pending'] is not None or not algorithm.stopped():
        if saved['pending'] is None:
            saved['pending'] = dict(index=saved['proposals'], candidate=algorithm.propose())
            saved['proposals'] += 1
            saved['algorithm'] = plain(algorithm.save())
            _save(host, saved)
        pending = saved['pending']
        prefix = 'search-' + str(pending['index'])
        from tools.platform_tools import _candidate
        try:
            effective = _candidate(SessionInput.model_validate(inp), pending['candidate'], host.reg)
            identity = digest(plain(effective))  # task, design, control, model and numerical conditions
        except ValueError:
            identity = None  # preserve the existing invalid-candidate receipt path
        if pending['index'] == 0 and starting_trial and identity:
            reused = reuse_start(host, plain(effective), starting_trial)
            if reused:
                algorithm.feedback(reused['score'])
                saved['trials'].append({**reused,'candidate':pending['candidate'],'effective_identity':identity})
                saved.update(algorithm=plain(algorithm.save()),pending=None)
                _save(host,saved)
                continue
        for trial in saved['trials']:
            if 'effective_identity' not in trial:
                try: trial['effective_identity'] = digest(plain(_candidate(SessionInput.model_validate(inp), trial['candidate'], host.reg)))
                except ValueError: trial['effective_identity'] = None
        previous = next((t for t in saved['trials'] if identity and t.get('effective_identity') == identity), None)
        if previous:
            algorithm.feedback(previous.get('score'))
            saved['duplicates'].append(dict(proposal=prefix, original_candidate=previous['candidate_id'], effective_identity=identity))
            saved.update(algorithm=plain(algorithm.save()), pending=None)
            _save(host, saved)
            # A complete coordinate sweep with no new configuration cannot progress.
            dimensions = len(getattr(getattr(algorithm, 'space', None), 'variables', [None]))
            if len(saved['duplicates']) >= 2 * dimensions and all(
                    d['proposal'] == 'search-' + str(saved['proposals'] - 2 * dimensions + i)
                    for i, d in enumerate(saved['duplicates'][-2 * dimensions:])):
                saved['stop_reason']='no_new_candidate'
                _save(host,saved)
                return _outcome(host,saved, 'completed', 'no_new_candidate')
            continue
        candidate_id = prefix
        if any(t['candidate_id'] == candidate_id for t in saved['trials']):
            candidate_id += '-' + digest(host.run_id)[:12]  # Preserve the reused source's original label.
        simulation = host.invoke(dict(request_id=prefix + '-simulation', tool_id='simulation.run', tool_version=inp['policy']['tool_bindings']['simulation.run'],
            arguments=dict(candidate_id=candidate_id, changes=pending['candidate']), reason='Execute search candidate', cache='reuse'))
        if simulation['execution_status'] != 'completed':
            error=simulation.get('error','')
            invalid=simulation['execution_status']=='rejected' and any(s in error for s in (
                 'PHYSICALLY_INVALID','PARAMETER_','CONDITIONAL_','TEMPLATE_','UNSUPPORTED','INITIAL_UNKNOWN','UNKNOWN_FORCE',
                 'GVS_OPERATING_POINT_','LQR_OPERATING_POINT_','GVS_LQR_'))
            if invalid:
                algorithm.feedback(None)
                saved['trials'].append(dict(candidate_id=candidate_id,owner_run_id=host.run_id,candidate=pending['candidate'],score=None,
                    status='unsupported' if 'UNSUPPORTED' in error else 'invalid_candidate',simulation=simulation))
                saved.update(algorithm=plain(algorithm.save()),pending=None); _save(host,saved)
                continue
            return _outcome(host,saved,simulation['execution_status'],error,pending)
        evaluation = host.invoke(dict(request_id=prefix + '-evaluation', tool_id='evaluation.run', tool_version=inp['policy']['tool_bindings']['evaluation.run'],
            arguments=dict(result=simulation['output'], execution_id=simulation['execution_id']), reason='Evaluate candidate with the frozen task evaluator'))
        if evaluation['execution_status'] != 'completed':
            return _outcome(host,saved,evaluation['execution_status'],evaluation.get('error',''),pending)
        result = EvaluationResult.model_validate(host.store.artifact(evaluation['output']))
        if definition.capabilities.get('feedback_adapter'):
            from importlib import import_module
            module, name = definition.capabilities['feedback_adapter'].split(':')
            scalar = getattr(import_module(module), name)(result, inp['task']['objectives'])
        else:
            scalar = score(result, inp['task']['objectives'])
        algorithm.feedback(scalar)
        saved['trials'].append(dict(candidate_id=candidate_id,owner_run_id=host.run_id,candidate=pending['candidate'], effective_identity=identity, evaluation=evaluation['output'],
            simulation=simulation,score=scalar,comparison_identity=result.comparison_identity,
            status='valid' if result.validity=='valid' else 'solver_failed',task_success=result.task_success))
        saved.update(algorithm=plain(algorithm.save()), pending=None)
        _save(host, saved)
    return _outcome(host,saved,'completed','search_trial_limit')


def _outcome(host,saved,status,reason,pending=None):
    valid=[t for t in saved['trials'] if t.get('score') is not None]
    if len({t.get('comparison_identity') for t in valid})>1:
        raise ValueError('INCOMPARABLE_TASK_INSTANCE_BACKEND_OR_MODEL')
    return dict(status=status,stop_reason=reason,pending=pending,trials=saved['trials'],algorithm=saved['algorithm'],
        proposals=saved.get('proposals',len(saved['trials'])), distinct_candidates=len(saved['trials']), duplicates=saved.get('duplicates',[]),
        actual_solves=host.store.remaining(host.run_id)['used']['backend_solves'],
        reused_evaluations=sum(bool(t.get('reused_evaluation')) for t in saved['trials']),
        new_evaluations=sum(bool(t.get('evaluation')) and not t.get('reused_evaluation',False) for t in saved['trials']),
        solve_count_meaning='Charged backend attempts from the ledger, including failures before a trial was appended',
        baseline=saved['trials'][0] if saved['trials'] else None,
        best=min(valid,key=lambda t:t['score']) if valid else None)


def _save(host, saved):
    host.reg.parse(saved['algorithm'])
    with host.store.transaction() as db:
        state = host.store.session(host.run_id, db)['state']
        state['search'] = saved
        host.store.update_state(db, host.run_id, state)
