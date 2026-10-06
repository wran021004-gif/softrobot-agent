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
    from extensions.tendon_family.optimization import batch_search
    from tools.diagnostic_revision import resolve_aliases
    plan=SearchBatchPlan.model_validate(proposal);reg=registry()
    state=store.session(view.run_id)['state'];role=state['role_context']
    from tools.diagnostic_handoff import accepted_product
    if not role.get('autonomous_scheduling'):
        accepted_product(store,role['previous_report'],'diagnosis_report')
    selectors=resolve_aliases(state,{'plan':plan.evidence})['plan']
    feedback=store.artifact(role['result_feedback'])
    if not any(s['reference']==feedback['result'] for s in selectors):
        from tools.diagnostic_revision import ensure_aliases
        aliases=ensure_aliases(state)['aliases']
        available=[a for a,h in aliases.items() if state['fact_catalog'][h]['selector']['reference']==feedback['result']]
        raise ValueError('PLAN_REQUIRES_PERFORMED_CHECK_EVIDENCE: evidence must include an exact result alias, e.g. '+', '.join(available[:8]))
    from tools.study_history import select_source
    from tools.candidate_parameters import fixed_configuration, parameter_value, actual_parameter_changes,planning_configuration,comparison_scope
    from tools.batch_budget import budget_capacity, batch_requirement, downstream_available
    if role.get('require_source_binding') and (plan.source_candidate is None or plain(plan.predecessor_decision)!=role.get('predecessor_decision')):
        raise ValueError('PLAN_EXPLICIT_SOURCE_AND_PREDECESSOR_REQUIRED')
    candidate=select_source(role.get('research_records',[]),plan.source_candidate,view.latest_tested)
    current_input=store.session(view.run_id)['snapshot']['input']
    effective=planning_configuration(store,candidate,current_input['policy'])
    if role.get('required_structure_identity'):
        from extensions.tendon_family.gvs_profile import execution_scope
        if execution_scope(effective)['robot']['identity']!=role['required_structure_identity']:
            raise ValueError('PLAN_ADAPTATION_STRUCTURE_MISMATCH')
    if comparison_scope(effective)!=comparison_scope(current_input):
        raise ValueError('PLAN_SOURCE_OUTSIDE_CURRENT_TASK')
    from tools.parameter_impacts import parameter_impacts
    controller=effective['policy']['controller'];identity=controller['extension_id']+'@'+controller['version']
    if plan.fixed_controller!=identity:raise ValueError('PLAN_FIXED_CONTROLLER_MISMATCH: '+identity)
    if plan.method not in ('search.family_coordinate@1.0.0','search.family_explicit@1.0.0'):raise ValueError('PLAN_METHOD_UNAVAILABLE')
    method,version=plan.method.split('@')
    definition=reg.get(method,version,'search')
    if not reg.inspect(definition,{method:version})['executable']:raise ValueError('PLAN_METHOD_NOT_INSTALLED')
    explicit=method=='search.family_explicit'
    if explicit:
        if plan.step is not None or not plan.candidates or len(plan.candidates)!=plan.max_candidates:
            raise ValueError('PLAN_EXPLICIT_SEQUENCE_REQUIRED: null step, candidates count equals max_candidates')
    elif plan.step is None or plan.candidates is not None:raise ValueError('PLAN_COORDINATE_STEP_REQUIRED_WITHOUT_EXPLICIT_POINTS')
    mappings={r['parameter']:r for r in parameter_impacts(effective,reference=candidate['configuration'])['mapped']}
    if role.get('allowed_batch_variables') and set(plan.variables)-set(role['allowed_batch_variables']):
        raise ValueError('PLAN_SUBSTAGE_VARIABLE_SCOPE')
    if role.get('max_variable_count') and len(plan.variables)>role['max_variable_count']:
        raise ValueError('PLAN_SUBSTAGE_VARIABLE_COUNT')
    if not plan.variables or set(plan.variables)-mappings.keys():raise ValueError('PLAN_VARIABLE_PATHS: only demonstrated speed-weight builder paths')
    from schemas.parameter_domains import domain as parameter_domain
    from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS
    initial={};domains=plain(plan.variables);search_bounds={}
    for path,value_domain in plan.variables.items():
        spec_domain=parameter_domain(value_domain)
        row=mappings[path];bounds=row['granted_range'];spec=row['builder_spec']
        if not row['authorized_parameter'] or not row['implementation_supported']:raise ValueError('PLAN_BUILDER_PARAMETER_UNSUPPORTED: '+path)
        initial[path]=parameter_value(effective,path)
        if spec_domain['kind']=='discrete':
            if not explicit or spec['type']!='choice':raise ValueError('PLAN_DISCRETE_REQUIRES_EXPLICIT_ENUMERATION: '+path)
            choices=spec_domain['choices']
            if not set(choices)<=set(spec['options']) or initial[path] not in choices:raise ValueError('PLAN_CHOICES_OUTSIDE_BUILDER_OR_SOURCE: '+path)
            search_bounds[path]=spec_domain
            continue
        if spec['type']!='number':raise ValueError('PLAN_CONTINUOUS_BUILDER_REQUIRED: '+path)
        lo,hi=spec_domain['bounds'];search_bounds[path]=[lo,hi]
        if not bounds[0]<=lo<hi<=bounds[1] or not spec['bounds'][0]<=lo<hi<=spec['bounds'][1]:raise ValueError('PLAN_DOMAIN_OUTSIDE_BUILDER_GRANT: '+path)
        if path in REACH_WEIGHT_PATHS and (0<lo<.0001 or hi<.0001):raise ValueError('PLAN_DOMAIN_CONTAINS_ILLEGAL_BOUNDARY_WEIGHT: zero or >=0.0001 required')
        if not lo<=initial[path]<=hi:raise ValueError('PLAN_START_OUTSIDE_DOMAIN: saved candidate value must be included for existing coordinate method: '+path)
        # Coordinate search visits this bounded lattice; a zero lower bound
        # excludes (0,0.0001) through the builder, and the reachable lattice
        # must never propose such a value. No numerical candidate is evaluated.
        width=hi-lo
        for origin in (() if explicit else (lo,hi,initial[path])):
            for k in range(-plan.max_candidates,plan.max_candidates+1):
                v=min(hi,max(lo,origin+k*plan.step*width))
                if path in REACH_WEIGHT_PATHS and 1e-12<v<.0001-1e-12:raise ValueError('PLAN_COORDINATE_STEP_CAN_PROPOSE_ILLEGAL_SMALL_WEIGHT: increase domain/step or use positive lower bound')
        # Build both boundary configurations without constructing any workspace.
        for endpoint in (lo,hi):
            changed=plain(_candidate(SessionInput.model_validate(effective),{path:endpoint},reg))
            if fixed_configuration(changed,plan.variables)!=fixed_configuration(effective,plan.variables):raise ValueError('PLAN_FIXED_ROBOT_TASK_CHANGED')
    parameters=dict(initial=initial,bounds=search_bounds)
    parameters.update(candidates=plan.candidates) if explicit else parameters.update(max_trials=plan.max_candidates,step=plan.step)
    batch_search(plan.method,parameters)
    differences=[]
    if explicit:
        for point in plan.candidates:
            for path,value in point.items():
                if path in REACH_WEIGHT_PATHS and 0<value<.0001:raise ValueError('PLAN_EXPLICIT_ILLEGAL_SMALL_WEIGHT')
            changed=plain(_candidate(SessionInput.model_validate(effective),point,reg))
            actual=actual_parameter_changes(effective,changed,plan.variables)
            if digest(fixed_configuration(changed,plan.variables))!=digest(fixed_configuration(effective,plan.variables)):
                raise ValueError('PLAN_ACTUAL_FIXED_FIELDS_CHANGED')
            differences.append(dict(proposed=point,actual_changes=actual,unchanged_declared_fields=sorted(set(point)-{r['path'] for r in actual})))
        if not plan.replication_reason and any(not any(r['path']==path for d in differences for r in d['actual_changes']) for path in plan.variables):
            raise ValueError('PLAN_DECLARED_VARIABLE_NEVER_CHANGES')
        if plan.replication_reason and len({digest(p) for p in plan.candidates})!=len(plan.candidates):
            raise ValueError('PLAN_REPLICATION_ONE_EXECUTION_PER_CONFIGURATION_PER_BATCH')
    required_fixed={'robot','task','acceptance','controller_implementation','other_numerical_settings'}
    if not required_fixed<=set(plan.fixed_conditions):raise ValueError('PLAN_FIXED_CONDITIONS_REQUIRED: '+', '.join(sorted(required_fixed)))
    required_objectives={'joint_reach_holding_acceptance','terminal_error_m','holding_max_error_m','holding_max_speed_m_s'}
    if not required_objectives<=set(plan.objectives) or set(plan.objectives)-required_objectives-{'complete_update_s'}:raise ValueError('PLAN_PHYSICAL_OBJECTIVES_REQUIRED: '+', '.join(sorted(required_objectives)))
    if not {'frozen_acceptance','force_bounds','finite_valid_execution'}<=set(plan.constraints):raise ValueError('PLAN_CONSTRAINTS_REQUIRED: frozen_acceptance, force_bounds, finite_valid_execution')
    required_verification={'candidate.apply','simulation.run','evaluation.run','control.profile_report','bound_comparison','diagnostic_revision'}
    if not required_verification<=set(plan.verification):raise ValueError('PLAN_FRESH_VERIFICATION_REQUIRED: '+', '.join(sorted(required_verification)))
    budget=plain(plan.planned_budget);count=plan.max_backend_attempts or plan.max_candidates
    from tools.batch_budget import PREPARATION_RESERVE_S
    prep_reserve=PREPARATION_RESERVE_S if effective['policy']['candidate_builder']['parameters']['data'].get('semantic_decisions') else 0.
    execution_floor=batch_requirement(count,interpretation={},planning={},preparation_reserve_s=prep_reserve)['requirement']
    if budget['backend_solves']!=count or budget['worker_calls']!=0 or any(budget[k]<v for k,v in execution_floor.items()):
        raise ValueError('PLAN_COSTS_INSUFFICIENT: backend_solves=explicit max_backend_attempts (legacy max_candidates), tool_calls>=4 per new execution, wall_s>=990 per new execution, workers=0')
    if plan.max_backend_attempts is not None and (plan.max_backend_attempts>plan.max_candidates or
            (plan.target_changed_configurations or 1)>plan.max_backend_attempts):raise ValueError('PLAN_CAPS_INCONSISTENT')
    capacity=budget_capacity(count,budget,preparation_reserve_s=prep_reserve)
    # Execution and interpretation follow this planning phase. Its local call
    # limit/protected capacity must not be counted as the downstream grant.
    available=budget_capacity(count,downstream_available(store,view.run_id),planning={},preparation_reserve_s=prep_reserve)
    if role.get('require_source_binding') and (not capacity['sufficient'] or not available['sufficient']):
        raise ValueError('PLAN_TOTAL_CAPACITY_INSUFFICIENT: '+str(dict(planned=capacity['shortfalls'],available=available['shortfalls'])))
    fixed=fixed_configuration(effective,plan.variables)
    if effective==store.artifact(candidate['configuration'])['effective']:
        execution_source=candidate['configuration']
    else:
        with store.transaction() as db:
            execution_source=plain(store.put(db,dict(effective=effective,source_configuration=candidate['configuration'],
                classification='Current authorized builder projection; source performance evidence remains bound to archived configuration.')))
    from tools.settling_campaign import RANKING
    return dict(plan=plain(plan),structurally_operationally_valid=True,scientific_promise=plan.scientific_promise,
        semantic_status='Model-authored promise and causal reasoning are separate from operational validation.',
        actual_differences=differences,budget_requirement=capacity,available_capacity=available,
        execution_authorized=False,requires_future_grant=True,baseline_replaced=False,candidate_promoted=False,
        bindings=dict(task=view.task,acceptance=view.acceptance,baseline=view.baseline,subject=candidate,
            source_configuration=candidate['configuration'],execution_source_configuration=execution_source,
            controller=controller,dynamics_model=view.task['execution_model'],source_report=role['source_report'],
            revised_assessment=role.get('previous_report'),check_feedback=role['result_feedback'],evidence_selectors=selectors,
            fixed_configuration_identity=digest(fixed),fixed_configuration=fixed),
        batch_semantics='One immutable plan for the batch. Registered coordinate or finite ask/tell scheduling uses the same receipt executor; plan submission executes nothing.',
        screening=dict(local_screening='none',raw_weighted_objectives_are_physical_ranking=False),
        final_comparison_policy=RANKING,required_fresh_steps=sorted(required_verification),
        cost_floor_per_candidate_s=dict(apply=prep_reserve,**{k.split('.')[0] if k!='control.profile_report' else 'profile':v for k,v in batch_requirement(1)['operation_reservations_s'].items()}),
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


def physical_feedback(baseline, candidate, acceptance):
    """Scalar coordinate guidance; the frozen physical comparison stays separate."""
    import math
    from tools.settling_campaign import compare_results
    comparison=compare_results(baseline,candidate)
    metrics=comparison['candidate']
    limits=[acceptance['terminal']['value'],acceptance['holding']['position']['value'],
        acceptance['holding']['speed']['value']]
    holding=acceptance['holding']
    for facts in (baseline,candidate):
        settling=facts['sampled_settling']
        if [settling['position_limit_m'],settling['speed_limit_m_s'],settling['window_s']]!=[
                holding['position']['value'],holding['speed']['value'],holding['duration']['value']]:
            raise ValueError('BATCH_ACCEPTANCE_CHANGED')
    vector=[metrics[k] for k in comparison['ranking_rule']['physical_metrics']]
    legal=(metrics['valid_complete_execution'] and candidate['sampled_settling']['available']
        and metrics['force_bound_violation_n']==0 and metrics['solver_error_count']==0
        and all(math.isfinite(v) and v>=0 for v in vector))
    if not all(math.isfinite(v) and v>0 for v in limits):raise ValueError('BATCH_ACCEPTANCE_LIMITS_REQUIRED')
    # Acceptance occupies [0,1); nonacceptance [1,2). The bounded normalized
    # physical loss is monotone in each metric. A trade-off can guide ask/tell,
    # but its classification is never changed to "overall improvement".
    score=(int(not metrics['joint_reach_holding_passed'])+
        sum(v/(v+limit) for v,limit in zip(vector,limits))/len(vector)) if legal else None
    return dict(score=score,comparison=comparison,physical_metrics=metrics,
        rule='Joint acceptance bucket plus mean v/(v+frozen_limit); minimize. Trade-offs may guide exploration, never promotion.',
        guidance_only=True,candidate_promoted=False)


def _save_batch(host,batch):
    with host.store.transaction() as db:
        state=host.store.session(host.run_id,db)['state'];state['search_batch']=batch
        host.store.update_state(db,host.run_id,state)


def prepare_offline_batch(host,plan_ref,*,starting_facts=None,interpretation_reserve_s=600.,mode='offline_injected',retained_baseline=None,historical_results=()):
    """Bind an accepted immutable plan in a separate offline grant, with no live adapter."""
    from copy import deepcopy
    from tools.diagnostic_handoff import accepted_product
    from schemas.platform_handoff import SearchBatchPlan
    from extensions.tendon_family.optimization import batch_search
    from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS
    from extensions.tendon_family.gvs_profile import execution_scope
    from tools.candidate_parameters import fixed_configuration,parameter_value
    record=accepted_product(host.store,plan_ref,'search_batch_plan')
    plan=SearchBatchPlan.model_validate(record['plan'])
    if not record['structurally_operationally_valid'] or record['execution_authorized']:
        raise ValueError('BATCH_REQUIRES_VALID_UNEXECUTED_PLAN')
    if plan.fixed_controller!='controller.gvs_nmpc@7.0.0' or plan.method not in ('search.family_coordinate@1.0.0','search.family_explicit@1.0.0'):
        raise ValueError('BATCH_FIXED_IMPLEMENTATION_REQUIRED')
    from tools.candidate_parameters import STRUCTURAL_PATHS,comparison_scope,scientific_fixed_scope
    if not plan.variables or set(plan.variables)-set((*REACH_WEIGHT_PATHS,*STRUCTURAL_PATHS)):raise ValueError('BATCH_UNSUPPORTED_PARAMETER_PATHS')
    state=host.store.session(host.run_id)['state'];existing=state.get('search_batch')
    if existing:
        if existing['plan']!=plan_ref:raise ValueError('BATCH_PLAN_IMMUTABLE')
        return existing
    source_configuration=record['bindings'].get('execution_source_configuration',record['bindings']['subject']['configuration'])
    effective=host.store.artifact(source_configuration)['effective']
    fixed=fixed_configuration(effective,plan.variables)
    if digest(fixed)!=record['bindings']['fixed_configuration_identity']:
        raise ValueError('BATCH_SOURCE_CONFIGURATION_MISMATCH')
    snapshot=host.store.session(host.run_id)['snapshot']['input']
    if comparison_scope(snapshot)!=comparison_scope(effective):
        raise ValueError('BATCH_HOST_SCIENCE_MISMATCH')
    budget=host.store.spendable(host.run_id)['remaining']
    if mode=='offline_injected' and any(budget[k] for k in ('backend_solves','model_calls','worker_calls')):
        raise ValueError('OFFLINE_BATCH_REQUIRES_ZERO_LIVE_GRANT')
    count=plan.max_backend_attempts or plan.max_candidates
    if mode=='live':
        if (plan.max_backend_attempts is None or plan.target_changed_configurations is None or
                budget['backend_solves']<count or budget['worker_calls']!=0 or not starting_facts or not retained_baseline):
            raise ValueError('LIVE_BATCH_EXPLICIT_CAPS_AND_TWO_REFERENCES_REQUIRED')
        if retained_baseline['candidate']!=record['bindings']['baseline']:raise ValueError('BATCH_RETAINED_BASELINE_MISMATCH')
    floor=sum(record['cost_floor_per_candidate_s'].values())
    from tools.batch_budget import budget_capacity
    capacity=budget_capacity(count,budget,interpretation=dict(wall_s=interpretation_reserve_s),planning={},
        preparation_reserve_s=record['cost_floor_per_candidate_s'].get('apply',0.))
    if mode=='offline_injected':
        # Injected stages reserve workflow/time only, under the zero-live guard.
        capacity['requirement']['backend_solves']=0
        capacity['shortfalls']['backend_solves']=0
        capacity['sufficient']=not any(capacity['shortfalls'].values())
    if interpretation_reserve_s<0 or not capacity['sufficient']:
        raise ValueError('BATCH_RESERVATION_CAPACITY_REQUIRED: 990 seconds and 4 tools per proposal, plus explicit interpretation reserve')
    initial={p:parameter_value(effective,p) for p in plan.variables}
    from schemas.parameter_domains import domain
    parameters=dict(initial=initial,bounds={p:domain(d) if domain(d)['kind']=='discrete' else domain(d)['bounds'] for p,d in plan.variables.items()})
    parameters.update(candidates=plan.candidates) if plan.method=='search.family_explicit@1.0.0' else parameters.update(max_trials=plan.max_candidates,step=plan.step)
    algorithm=batch_search(plan.method,parameters)
    if starting_facts and starting_facts['candidate']!=record['bindings']['subject']:
        raise ValueError('BATCH_START_EVIDENCE_MISMATCH')
    for facts in (starting_facts,retained_baseline):
        if facts and (facts['candidate']['execution_id']!=facts['execution_id'] or facts['candidate']['configuration']!=facts['configuration']):
            raise ValueError('BATCH_REFERENCE_FACT_BINDING_MISMATCH')
    permitted=[]
    for saved in historical_results:
        facts=saved['facts'];original=host.store.artifact(facts['configuration'])['effective']
        if (saved['execution_id']!=facts['execution_id'] or saved['owner_run_id']!=facts['candidate']['owner_run_id']
                or saved['execution_scope']!=execution_scope(original)):
            raise ValueError('BATCH_HISTORICAL_SOURCE_BINDING_MISMATCH')
        comparable=comparison_scope(effective)==comparison_scope(original)
        if not comparable:raise ValueError('BATCH_HISTORICAL_FIXED_SCIENCE_MISMATCH')
        permitted.append({**saved,'available_for_reasoning':True,'comparable_under_task':comparable,
            'reusable_under_plan':scientific_fixed_scope(effective,plan.variables)==scientific_fixed_scope(original,plan.variables),
            'exact_reuse_rule':'Full execution_scope must additionally equal proposed candidate; no cross-structure result rebinding.'})
    batch=dict(plan=plan_ref,batch_id='batch-'+plan_ref['artifact_id'][:16],mode=mode,
        method=plan.method,parameters=plain(algorithm.parameters),algorithm=plain(algorithm.save()),pending=None,
        proposals=[],configurations={},starting_facts=starting_facts,base_configuration=source_configuration,
        retained_baseline=retained_baseline,max_backend_attempts=count,target_changed_configurations=plan.target_changed_configurations,
        historical_results=permitted,
        interpretation_reserve_s=interpretation_reserve_s,usage_start=host.store.remaining()['used'],stop_reason=None,
        replication_reason=plan.replication_reason,
        grant=host.store.config(),interpretation_reserve=dict(model_calls=4,tool_calls=4))
    _save_batch(host,batch)
    return batch


def offline_batch_result(host):
    """Compact public result suitable for the existing evidence handover path."""
    batch=host.store.session(host.run_id)['state']['search_batch']
    now=host.store.remaining()['used'];used={k:v-batch['usage_start'][k] for k,v in now.items()}
    rows=list(batch['configurations'].values())
    from tools.study_history import execution_chronology
    chronology=execution_chronology(host.store,rows) if batch['mode']=='live' else None
    return dict(contract='platform.search_batch_result',version='1.0.0',mode=batch['mode'],plan=batch['plan'],
        execution_chronology=chronology,
        batch_id=batch['batch_id'],status='completed' if batch['stop_reason'] in ('proposal_limit','pilot_target_complete') else 'stopped' if batch['stop_reason'] else 'pending' if batch['pending'] else 'prepared',
        stop_reason=batch['stop_reason'],pending=batch['pending'],proposals=batch['proposals'],
        candidates=[{k:v for k,v in row.items() if k!='effective'} for row in rows],
        accounting=dict(proposals=len(batch['proposals']),distinct_configurations=len(rows),
            reused_evaluations=sum(p.get('reused',False) for p in batch['proposals']),
            historical_start_reuse=sum(p.get('reuse_kind')=='historical_start' for p in batch['proposals']),
            retained_baseline_reuse=sum(p.get('reuse_kind')=='retained_baseline' for p in batch['proposals']),
            other_historical_reuse=sum(p.get('reuse_kind')=='historical_candidate' for p in batch['proposals']),
            duplicate_result_reuse=sum(p.get('reuse_kind')=='duplicate' for p in batch['proposals']),
            new_backend_attempts=used['backend_solves'],offline_execution_attempts=sum(not r['reused'] and 'simulation' in r['stages'] for r in rows) if batch['mode']=='offline_injected' else 0,
            completed_new_evaluations=sum(not r['reused'] and r.get('feedback') is not None for r in rows),usage=used),
        completed_evaluations=sum(not r['reused'] and r['stages'].get('evaluation',{}).get('execution_status')=='completed' for r in rows),
        completed_profiles=sum(not r['reused'] and r['stages'].get('profile',{}).get('execution_status')=='completed' for r in rows),
        fully_evaluated_distinct_changed_configurations=sum(not r['reused'] and not r.get('replication_of') and r.get('feedback') is not None for r in rows),
        fully_evaluated_new_executions=sum(not r['reused'] and r.get('feedback') is not None for r in rows),
        deliberate_replications=sum(bool(r.get('replication_of')) and r.get('feedback') is not None for r in rows),
        physical_acceptance_authority='Frozen full comparison; optimizer guidance does not promote a candidate.',
        execution_authorized=batch['mode']=='live',candidate_promoted=False,grant=batch.get('grant'))


def run_offline_batch(host,inject,*,stop_after_stage=None):
    batch=host.store.session(host.run_id)['state']['search_batch']
    if batch['mode']!='offline_injected':raise ValueError('SYNTHETIC_OUTPUTS_CANNOT_SATISFY_LIVE_ACCEPTANCE')
    return _run_batch(host,inject,stop_after_stage=stop_after_stage)


def run_live_batch(host,*,stop_after_stage=None):
    from tools.live_batch_execution import LiveBatchExecution
    if host.store.session(host.run_id)['state']['search_batch']['mode']!='live':raise ValueError('LIVE_BATCH_GRANT_REQUIRED')
    return _run_batch(host,LiveBatchExecution(host),stop_after_stage=stop_after_stage)


def _run_batch(host,inject,*,stop_after_stage=None):
    from tools.candidate_parameters import parameter_value,fixed_configuration
    from tools.execution_completion import EXECUTION_ALLOWANCES
    """Injected apply/simulation/evaluation/profile outputs only; no provider or physics.

    The callback receives (stage, candidate, retained stage receipts). Its profile
    output supplies factual_result in the existing complete-execution shape.
    SQLite seals each synthetic receipt before continuing; unknown work is never
    automatically replayed. A future live adapter still needs a separate grant.
    """
    import json,time
    from schemas.platform import CandidateInput
    from extensions.tendon_family.optimization import batch_search
    from tools.platform_tools import _candidate
    from tools.platform_store import zero
    from copy import deepcopy
    batch=host.store.session(host.run_id)['state']['search_batch']
    record=host.store.artifact(batch['plan']);source=host.store.artifact(batch['base_configuration'])['effective']
    algorithm=batch_search(batch.get('method','search.family_coordinate@1.0.0'),batch['parameters'])
    algorithm.restore(batch['algorithm']['data'])
    stages=(('apply',record['cost_floor_per_candidate_s'].get('apply',0.)),*[(stage,EXECUTION_ALLOWANCES[tool]['reserve_s']) for stage,tool in
        [('simulation','simulation.run'),('evaluation','evaluation.run'),('profile','control.profile_report')]])
    while batch['pending'] or not algorithm.stopped():
        if batch['stop_reason']:break
        if batch['pending'] is None:
            build_started=time.monotonic()
            changes=algorithm.propose();raw_changes=dict(changes)
            # A coordinate return to a known point must not create a second
            # execution just because subtraction changed its last float bit.
            known=[batch['parameters']['initial'],*[p['changes'] for p in batch['proposals']]]
            for saved in batch.get('historical_results',[]):
                saved_input=host.store.artifact(saved['facts']['configuration'])['effective']
                known.append({p:parameter_value(saved_input,p) for p in changes})
            canonicalized=[]
            for path,value in changes.items():
                old=next((p[path] for p in known if path in p and
                    (abs(p[path]-value)<=1e-12 if isinstance(value,(int,float)) and isinstance(p[path],(int,float)) else p[path]==value)),value)
                if old!=value:canonicalized.append(path);changes[path]=old
            if canonicalized:algorithm.state=algorithm.state.model_copy(update=dict(pending=algorithm.space.encode(changes)))
            effective=plain(_candidate(SessionInput.model_validate(source),changes,host.reg));identity=digest(effective)
            fixed=fixed_configuration(effective,batch['parameters']['bounds'])
            if digest(fixed)!=record['bindings']['fixed_configuration_identity']:raise ValueError('BATCH_CANDIDATE_CHANGED_FIXED_CONFIGURATION')
            proposal=dict(index=len(batch['proposals']),changes=changes,optimizer_changes=raw_changes,
                roundoff_canonicalized=canonicalized,identity=identity,reused=False)
            from tools.candidate_parameters import actual_parameter_changes
            proposal['actual_changes']=actual_parameter_changes(source,effective,changes)
            batch['proposals'].append(proposal);previous=batch['configurations'].get(identity)
            start=None
            if proposal['index']==0 and batch['starting_facts']:
                from extensions.tendon_family.gvs_profile import execution_scope
                original=host.store.artifact(batch['starting_facts']['configuration'])['effective']
                if execution_scope(effective)==execution_scope(original):start=batch['starting_facts']
            retained=None
            historical=None
            if not previous and batch.get('historical_results'):
                from extensions.tendon_family.gvs_profile import execution_scope
                historical=next((r for r in batch['historical_results'] if r.get('reusable_under_plan',True) and r['execution_scope']==execution_scope(effective)),None)
                if historical and not batch.get('replication_reason'):
                    facts=historical['facts']
                    previous=dict(candidate_id=facts['candidate']['candidate_id'],configuration=facts['configuration'],identity=identity,
                        changes=changes,stages={k:dict(execution_status='historical_reused') for k,_ in stages},reused=True,
                        execution_id=facts['execution_id'],historical_source=historical,
                        feedback=physical_feedback(batch['starting_facts'],facts,record['bindings']['acceptance']))
                    from tools.settling_campaign import compare_results
                    previous['retained_baseline_comparison']=compare_results(batch['retained_baseline'],facts)
                    batch['configurations'][identity]=previous
            if not previous and not start and batch.get('retained_baseline'):
                from extensions.tendon_family.gvs_profile import execution_scope
                candidate=batch['retained_baseline']
                original=host.store.artifact(candidate['configuration'])['effective']
                if execution_scope(effective)==execution_scope(original):retained=candidate
            replication_of=None
            if batch.get('replication_reason'):
                replication_of=(historical['facts']['candidate'] if historical else
                    start['candidate'] if start else retained['candidate'] if retained else None)
                previous=start=retained=None
                if replication_of:proposal.update(replication_of=replication_of,replication_reason=batch['replication_reason'])
            if previous or start or retained:
                if start and not previous:
                    previous=dict(candidate_id=start['candidate']['candidate_id'],configuration=start['configuration'],identity=identity,
                        stages={k:dict(execution_status='historical_reused') for k,_ in stages},reused=True,
                        changes=changes,
                        feedback=physical_feedback(start,start,record['bindings']['acceptance']))
                    if batch.get('retained_baseline'):
                        from tools.settling_campaign import compare_results
                        previous['retained_baseline_comparison']=compare_results(batch['retained_baseline'],start)
                    batch['configurations'][identity]=previous
                if retained:
                    previous=dict(candidate_id=retained['candidate']['candidate_id'],configuration=retained['configuration'],identity=identity,
                        changes=changes,stages={k:dict(execution_status='historical_reused') for k,_ in stages},reused=True,
                        feedback=physical_feedback(batch['starting_facts'],retained,record['bindings']['acceptance']),
                        retained_baseline_comparison=physical_feedback(retained,retained,record['bindings']['acceptance'])['comparison'])
                    batch['configurations'][identity]=previous
                kind=historical['role'] if historical else 'historical_start' if start else 'retained_baseline' if retained else 'duplicate'
                proposal.update(reused=True,reused_from=previous['candidate_id'],reuse_kind=kind,
                    reused_execution_id=previous.get('execution_id'),reuse_reason=historical['reuse_reason'] if historical else 'Known complete result; no new backend attempt.')
                if batch['mode']=='live':print('BATCH reuse',proposal['index'],kind,changes,flush=True)
                algorithm.feedback(previous['feedback']['score']);batch['algorithm']=plain(algorithm.save());_save_batch(host,batch);continue
            candidate_id=batch['batch_id']+'-'+str(proposal['index'])
            prepared=CandidateInput(candidate_id=candidate_id,baseline_identity=digest(source),builder=source['policy']['candidate_builder']['extension_id'],
                builder_version=source['policy']['candidate_builder']['version'],changes=changes,allowed=source['policy']['editable'],
                effective=effective,content_identity=identity)
            with host.store.transaction() as db:configuration=plain(host.store.put(db,prepared))
            batch['pending']=dict(candidate_id=candidate_id,configuration=configuration,identity=identity,changes=changes,
                candidate_build_s=time.monotonic()-build_started,replication_of=replication_of,
                replication_reason=batch.get('replication_reason') if replication_of else None)
            batch['configurations'][identity]=dict(**batch['pending'],stages={},reused=False)
            batch['algorithm']=plain(algorithm.save());_save_batch(host,batch)
        candidate=batch['pending'];row=batch['configurations'][candidate['identity']]
        live=batch['mode']=='live'
        if live:
            # Reconcile sealed child receipts before testing new-work caps.
            executor=inject.candidate_host(candidate)
            for stage,_ in stages[1:]:
                old=executor.store.lookup(executor.run_id,'complete-'+stage)
                if old and old['receipt'] and stage not in row['stages']:
                    row['stages'][stage]=json.loads(old['receipt'])
                elif old and not old['receipt']:
                    executor.store.mark_unknown(executor.run_id,'complete-'+stage)
                    row['stages'][stage]=dict(execution_status='unknown',execution_id=old['execution_id'],charged=json.loads(old['charged']),output=None)
                    batch['stop_reason']='unresolved_execution';_save_batch(host,batch)
                    return offline_batch_result(host)
            _save_batch(host,batch)
            used=offline_batch_result(host)['accounting']['usage'];remaining=host.store.remaining()['remaining']
            missing=[s for s,_ in stages if s not in row['stages']]
            if 'simulation' in missing and used['backend_solves']>=batch['max_backend_attempts']:
                batch['stop_reason']='backend_attempt_limit';_save_batch(host,batch);break
            needed=sum(s for k,s in stages if k in missing)
            if (remaining['wall_s']<needed+batch['interpretation_reserve_s'] or remaining['tool_calls']<len(missing)+4 or remaining['model_calls']<4):
                batch['stop_reason']='insufficient_delivery_capacity';_save_batch(host,batch);break
        for stage,reserve_s in stages:
            if live and stage in row['stages']:
                receipt=row['stages'][stage]
                if receipt['execution_status']!='completed':return offline_batch_result(host)
                continue
            request_id=candidate['candidate_id']+'-'+stage
            old=host.store.lookup(host.run_id,request_id)
            if old and not old['receipt']:
                host.store.mark_unknown(host.run_id,request_id)
                row['stages'][stage]=dict(execution_status='unknown',request_id=request_id,execution_id=old['execution_id'],
                    charged=json.loads(old['charged']),output=None)
                _save_batch(host,batch)
                return offline_batch_result(host)
            if old:receipt=json.loads(old['receipt'])
            elif live and stage!='apply':
                print('BATCH stage',candidate['candidate_id'],stage,candidate['changes'],flush=True)
                receipt=inject.stage(stage,deepcopy(candidate))
            else:
                if host.store.spendable(host.run_id)['remaining']['wall_s']<reserve_s+batch['interpretation_reserve_s']:
                    return offline_batch_result(host)
                reservation,_=host.store.reserve(host.run_id,request_id,digest(dict(candidate=candidate,stage=stage)),host.actor,
                    {**zero(),'tool_calls':1,'wall_s':reserve_s})
                started=time.monotonic()
                output=host.store.artifact(candidate['configuration']) if stage=='apply' else inject(stage,deepcopy(candidate),deepcopy(row['stages']))
                receipt=host.store.complete(reservation,dict(request_id=request_id,execution_id=reservation['execution_id'],caller=host.actor,
                    tool_id='candidate.apply' if live else 'offline.batch.'+stage,tool_version='1.0.0',execution_status='completed' if stage=='apply' else output.get('execution_status','completed'),charged=zero()),
                    dict(mode=batch['mode'],configuration=candidate['configuration'],result=output),
                    time.monotonic()-started+(candidate.get('candidate_build_s',0.) if stage=='apply' else 0.))
            row['stages'][stage]=receipt;_save_batch(host,batch)
            if receipt['execution_status']!='completed':
                if live:
                    batch['stop_reason']='unresolved_execution' if receipt['execution_status']=='unknown' else 'material_execution_failure'
                    _save_batch(host,batch)
                return offline_batch_result(host)
            if stop_after_stage==stage:return offline_batch_result(host)
        if live:
            completed=inject.facts(deepcopy(candidate));facts=completed['factual_result'];row['execution']=completed
            row['executed_configuration']=completed['configuration']
            row['execution_id']=completed['execution_id'] if 'execution_id' in completed else facts['execution_id']
        else: facts=host.store.artifact(row['stages']['profile']['output'])['result']['factual_result']
        if (not live and (facts['configuration']!=candidate['configuration'] or facts['candidate']['configuration']!=candidate['configuration'])
                or facts['candidate']['candidate_id']!=candidate['candidate_id']):
            raise ValueError('BATCH_RESULT_CONFIGURATION_MISMATCH')
        baseline=batch['starting_facts']
        if baseline is None:batch['starting_facts']=baseline=facts
        row['feedback']=physical_feedback(baseline,facts,record['bindings']['acceptance'])
        if batch.get('retained_baseline'):
            from tools.settling_campaign import compare_results
            row['retained_baseline_comparison']=compare_results(batch['retained_baseline'],facts)
        row['joint_acceptance']=row['feedback']['physical_metrics']['joint_reach_holding_passed']
        algorithm.feedback(row['feedback']['score']);batch['pending']=None;batch['algorithm']=plain(algorithm.save())
        if row['feedback']['score'] is None:batch['stop_reason']='invalid_physical_result'
        if live and not batch['stop_reason'] and sum(not r['reused'] and r.get('feedback') is not None for r in batch['configurations'].values())>=batch['target_changed_configurations']:
            batch['stop_reason']='pilot_target_complete'
        _save_batch(host,batch)
    if not batch['stop_reason']:batch['stop_reason']='proposal_limit'
    _save_batch(host,batch)
    result=offline_batch_result(host)
    with host.store.transaction() as db:
        ref=host.store.put(db,result);state=host.store.session(host.run_id,db)['state'];state['search_batch_result']=plain(ref)
        host.store.update_state(db,host.run_id,state)
        host.store.event(db,host.run_id,'search_batch','live_result' if batch['mode']=='live' else 'offline_result',inputs=[batch['plan']],outputs=[ref])
    return result
