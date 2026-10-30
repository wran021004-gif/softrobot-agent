"""Deterministic scientific choices -> existing registered AnalysisRequest.

No optimizer, state machine, source ledger or execution admission lives here.
"""
from copy import deepcopy

from tools.platform_store import plain
from tools.research.contracts import ScientificQuestion, LocalControlSearchSettings
from tools.research.state import state, protected
from tools.research.nonlinear_capability import T1, T2

INTERFACE = 'scientific_question_v1'


def enabled(spec):
    return spec.get('research_decisions',{}).get('analysis_interface') in (INTERFACE,'scientific_question_v2')


def question_contract(spec):
    from tools.research.contracts import ScientificQuestionV2
    return ScientificQuestionV2 if spec.get('research_decisions',{}).get('analysis_interface')=='scientific_question_v2' else ScientificQuestion


def completed_question_plan(host):
    from tools.research.research_context import research_intent
    intent = research_intent(host)['latest_decision'] or {}
    decision = (intent.get('agent_hypothesis') or {}).get('decision') or {}
    if (intent.get('action') == 'diagnose' and intent.get('execution_status') == 'completed'
            and intent.get('candidate') and decision.get('selected_candidate') == intent['candidate']):
        return intent
    return None


def compile_question(host, payload, *, tool_use_id):
    """Return actionable preparation/choice feedback or the original full contract."""
    if state(host)['spec'].get('research_decisions',{}).get('analysis_interface')=='scientific_question_v2':
        return compile_v2(host,payload,tool_use_id=tool_use_id)
    return compile_v1(host,payload,tool_use_id=tool_use_id)


def compile_v1(host, payload, *, tool_use_id, source_question=None):
    """Original V1 adapter, also reused for V2's explicit short fixed-input question."""
    from pydantic import ValidationError
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.agent import bind_selected_analysis_request
    from tools.research.design import verify_candidate
    from tools.research.optimal_capability import family_analysis_parameters
    from tools.research.optimal_capability import CONIC
    try:
        question = ScientificQuestion.model_validate(payload)
    except ValidationError as exc:
        return dict(status='needs_choice',reason='INVALID_SCIENTIFIC_INPUT',issues=[
            dict(field='.'.join(map(str,e['loc'])),reason=e['msg']) for e in exc.errors()],scientific_execution_started=False)
    q = question
    def feedback(status, reason, **extra):
        return dict(status=status,reason=reason,question=plain(q),scientific_execution_started=False,**extra)
    s = state(host);spec = s['spec']
    if protected(host) or s['research_status']=='stopped':
        return feedback('blocked','ORIGINAL_PROTECTED_CLOSEOUT_OR_STOP')
    intent = completed_question_plan(host)
    if not intent:
        return feedback('needs_prerequisite','COMPLETED_CANDIDATE_BOUND_DIAGNOSE_REQUIRED',
            preparation=dict(tool='research_plan',action='diagnose',fields=['hypothesis','decision.selected_candidate']))
    candidate = intent['candidate']
    if q.question_type=='structure_parameter_effect' and not q.parameter_paths and intent['agent_hypothesis']['decision'].get('selected_variables'):
        q = q.model_copy(update={'parameter_paths':intent['agent_hypothesis']['decision']['selected_variables']})
    try:
        c = verify_candidate(host,candidate)
        view = mathematical_method_view(host,candidate)
    except (ValueError,KeyError) as exc:
        return feedback('needs_prerequisite',str(exc))
    if q.question_type=='bounded_control_initialization':
        if (q.effect_semantics is not None or q.parameter_paths or q.fixed_input or q.tensions_n is not None
                or q.response_horizon_s is not None or q.control_scope or q.search_strategy
                or q.requested_budget is not None or any(plain(q.source_selection).values())):
            return feedback('unsupported','BOUNDED_INITIALIZATION_REQUIRES_LOCAL_AFFINE_SEQUENCE_SEMANTICS',
                scope='Frozen initial GVS model, complete task and physical input box; no Native search, structural comparison or source transfer.')
        method = CONIC
    elif q.question_type=='control_feasibility':
        if q.effect_semantics not in (None,'reoptimized_task_capability'):
            return feedback('unsupported','CONTROL_FEASIBILITY_REQUIRES_CONTROL_REOPTIMIZATION')
        if q.parameter_paths or q.fixed_input or q.tensions_n is not None or q.response_horizon_s is not None:
            return feedback('unsupported','STRUCTURAL_OR_FIXED_INPUT_FIELDS_DO_NOT_DESCRIBE_CONTROL_FEASIBILITY')
        method = T1
    else:
        if not spec.get('family_space') or not c.get('generation_version'):
            return feedback('unsupported','C2_STRUCTURAL_QUESTIONS_REQUIRE_REGISTERED_FAMILYSPACE_PATHS')
        if q.effect_semantics is None:
            return feedback('needs_choice','STRUCTURAL_EFFECT_SEMANTICS_REQUIRED',
                choices=dict(effect_semantics=['fixed_input_response','reoptimized_task_capability']))
        if q.effect_semantics not in ('fixed_input_response','reoptimized_task_capability'):
            return feedback('unsupported','SCIENTIFIC_SEMANTICS_NOT_ADAPTED',
                missing_capability=q.effect_semantics,
                detail_query=dict(reference=candidate,view='mathematical_capabilities',pointer='/capability_inventory'))
        if not q.parameter_paths:
            return feedback('needs_choice','REGISTERED_PARAMETER_PATH_REQUIRED',
                choices=dict(parameter_paths=[r['parameter_id'] for r in family_analysis_parameters(spec,c)
                    if r['continuous_perturbation'] and r['effective_in_current_execution']]))
        if len(q.parameter_paths)!=1:
            return feedback('unsupported','C2_SUPPORTS_ONE_INDEPENDENT_CONTINUOUS_PATH_PER_QUESTION')
        method = 'fixed_input_structure_v1' if q.effect_semantics=='fixed_input_response' else T2
        rows = {r['parameter_id']:r for r in family_analysis_parameters(spec,c)}
        row = rows.get(q.parameter_paths[0])
        if not row or not row['continuous_perturbation'] or not row['effective_in_current_execution']:
            return feedback('unsupported','REGISTERED_EFFECTIVE_CONTINUOUS_PARAMETER_REQUIRED',
                field='parameter_paths',parameter=row)
        if method not in row['applicable_mathematical_methods']:
            return feedback('blocked','ORIGINAL_PARAMETER_METHOD_AUTHORIZATION_REQUIRED',parameter=row)
    detail = view['methods'].get(method)
    if not detail:
        return feedback('blocked','ORIGINAL_FROZEN_METHOD_GRANT_REQUIRED',method=method)
    status = detail['planning_status']
    if status in ('unauthorized','insufficient_budget','blocked'):
        return feedback('blocked','ORIGINAL_METHOD_ADMISSION_BLOCKED',method=method,missing=detail['missing'])
    if status=='unsupported':
        return feedback('unsupported','ORIGINAL_METHOD_TASK_OR_MODEL_UNSUPPORTED',method=method,missing=detail['missing'])
    metrics = {r['constraint']['constraint_id'] for r in view['research_opportunities']['metrics'] if r.get('constraint')}
    if q.focus_metric and q.focus_metric not in metrics:
        return feedback('unsupported','FOCUS_MUST_NAME_A_REGISTERED_TASK_CONSTRAINT',
            field='focus_metric',choices=sorted(metrics))
    if method==CONIC:
        compiled = dict(model_source='gvs',operating_point='standardized_initial_pretension')
    elif method==T1:
        if q.source_selection.comparison_candidates or q.source_selection.t1_results:
            return feedback('unsupported','CONTROL_SEARCH_REQUIRES_A_CONTROL_SOURCE_NOT_STRUCTURAL_EVIDENCE')
        plan_budget = intent['agent_hypothesis']['decision'].get('requested_budget',0)
        budget = q.requested_budget if q.requested_budget is not None else plan_budget or None
        missing = [name for name in ('control_scope','search_strategy') if getattr(q,name) is None]
        if budget is None:missing.append('requested_budget')
        if missing:
            return feedback('needs_choice','CONTROL_SEARCH_SCIENTIFIC_CHOICES_REQUIRED',fields=missing,
                choices=dict(control_scope=['full_task','time_window'],search_strategy=['response','pattern']))
        from tools.research.physical_replay import binding, explicit_control_source, numerically_verified_source
        sources = [r['source'] for r in s.get('control_initializations',[]) if r['candidate']==candidate]
        for ref in s.get('analysis_results',[]):
            raw = host.store.artifact(ref)
            if raw.get('candidate')==candidate and raw.get('control_schedule_reference'):
                sources.append(raw['control_schedule_reference'])
        selected = plain(q.source_selection.control_source) if q.source_selection.control_source else None
        legal = [];trajectories = []
        for ref in ([selected] if selected else sources):
            if ref in legal:continue
            try:
                raw = host.store.artifact(ref)
                if not (explicit_control_source(raw) or numerically_verified_source(raw)):continue
                binding(c['configuration'],raw['trajectory'])
            except (ValueError,KeyError):continue
            if raw['trajectory'] not in trajectories:
                legal.append(ref);trajectories.append(raw['trajectory'])
        if not legal:
            return feedback('needs_prerequisite','COMPLETE_LEGAL_CONTROL_SOURCE_REQUIRED',
                preparation=dict(tool='research_plan',action='initialize_control',control_seed=dict(candidate=candidate,method='baseline')))
        if len(legal)>1:
            return feedback('needs_choice','SCIENTIFICALLY_DISTINCT_CONTROL_SOURCES',choices=dict(control_source=legal))
        duration = spec['analysis_protocol']['duration_s']
        if q.control_scope.mode=='full_task':
            if q.control_scope.window_s is not None:
                return feedback('needs_choice','FULL_TASK_SCOPE_HAS_NO_LOCAL_WINDOW')
            knots = [0.,duration];active = None
        else:
            window = q.control_scope.window_s
            if window is None or not 0<=window[0]<window[1]<=duration:
                return feedback('needs_choice','LOCAL_WINDOW_MUST_BE_INSIDE_FROZEN_TASK',task_duration_s=duration)
            a,b = window
            # np.interp extends endpoints. Zero endpoint coefficients and only an
            # active middle knot make the actual correction zero outside [a,b].
            knots = [a,(a+b)/2,b]
            channels = len(c['configuration']['robot']['structure']['data']['tendons'])
            active = list(range(channels,2*channels))
        settings = dict(version='local_control_search_v2',method=q.search_strategy,knots_s=knots,
            correction_window_s=[0.,duration],evaluation_requests=budget)
        if active is not None:settings['active_coefficients']=active
        try:defaults = LocalControlSearchSettings.model_validate(settings)
        except ValidationError as exc:
            return feedback('needs_choice','SEARCH_SETTINGS_OUTSIDE_ORIGINAL_CONTRACT',
                issues=[dict(field='.'.join(map(str,e['loc'])),reason=e['msg']) for e in exc.errors()])
        for name,limit in spec.get('native_control_limits',{}).items():
            actual = len(knots) if name=='knots_s' else getattr(defaults,name)
            if actual>limit:
                return feedback('blocked','ORIGINAL_STUDY_NATIVE_CONTROL_LIMIT',field=name,requested=actual,maximum=limit)
        compiled = dict(control_optimization=dict(source=legal[0],settings=settings))
    else:
        if q.control_scope or q.search_strategy or q.source_selection.control_source:
            return feedback('unsupported','STRUCTURAL_COMPARISON_REUSES_FIXED_INPUT_OR_SAVED_T1_SETTINGS')
        path = q.parameter_paths[0]
        if method==T2:
            if q.fixed_input or q.tensions_n is not None or q.response_horizon_s is not None or q.source_selection.comparison_candidates:
                return feedback('unsupported','REOPTIMIZED_EFFECT_REQUIRES_SAVED_T1_EVIDENCE_NOT_FIXED_INPUT')
            if q.requested_budget is not None:
                return feedback('unsupported','T2_IS_ONE_AGGREGATION_NOT_A_NEW_SEARCH_BUDGET')
            ready = [r for r in detail.get('ready_requests',[]) if r['nonlinear_response']['variable']==path]
            if q.source_selection.t1_results:
                ready = [r for r in ready if r['nonlinear_response']['t1_results']==[plain(ref) for ref in q.source_selection.t1_results]]
            if not ready:
                return feedback('needs_prerequisite','COMPARABLE_COMPLETED_BASELINE_MINUS_PLUS_T1_REQUIRED',
                    missing=['baseline T1','symmetric minus/plus candidates and T1','same input, search settings, frozen task and initialization'],
                    preparation=detail.get('preparation'),scientific_choices=['parameter step/direction','candidate contrasts','T1 control search choices'],
                    detail_query=detail['detail_query'])
            if len(ready)>1:
                return feedback('needs_choice','MULTIPLE_COMPARABLE_T1_STENCILS',
                    choices=dict(t1_results=[r['nonlinear_response']['t1_results'] for r in ready]))
            compiled = dict(nonlinear_response=deepcopy(ready[0]['nonlinear_response']))
        else:
            if q.source_selection.t1_results or q.requested_budget is not None:
                return feedback('unsupported','FIXED_INPUT_RESPONSE_DOES_NOT_USE_T1_OR_SEARCH_BUDGET')
            missing = [name for name in ('fixed_input','response_horizon_s') if getattr(q,name) is None]
            if missing:
                return feedback('needs_choice','FIXED_INPUT_AND_SHORT_RESPONSE_HORIZON_REQUIRED',fields=missing,
                    choices=dict(fixed_input=['frozen_initial_tensions','constant_tensions']))
            if (q.fixed_input=='constant_tensions') != (q.tensions_n is not None):
                return feedback('needs_choice','CONSTANT_TENSIONS_REQUIRE_AN_EXPLICIT_VECTOR_ONLY')
            from tools.research.native_analysis import structure_context
            from tools.research.contracts import NativeStructureResponse
            selected = [plain(ref) for ref in q.source_selection.comparison_candidates]
            contrasts = []
            for ref in (selected or list(s['candidates'].values())):
                if ref==candidate:continue
                try:
                    other = verify_candidate(host,ref)
                    structure_context(c,[(ref,other)],NativeStructureResponse(variable=path,candidates=[ref]),spec=spec)
                except (ValueError,KeyError,IndexError):continue
                contrasts.append(ref)
            if (selected and contrasts!=selected) or not contrasts:
                return feedback('needs_prerequisite','LEGAL_SAME_TASK_SINGLE_PARAMETER_CONTRAST_REQUIRED',
                    preparation=dict(tool='research_plan',action='generate',parameter_path=path),scientific_choices=['contrast direction and step'])
            if not selected and len(contrasts)>1:
                return feedback('needs_choice','MULTIPLE_STRUCTURAL_CONTRASTS',choices=dict(comparison_candidates=contrasts))
            native = dict(horizon_s=q.response_horizon_s)
            if q.tensions_n is not None:native['tensions_n']=q.tensions_n
            compiled = dict(operating_point='standardized_initial_pretension',native=native,
                structure_response=dict(variable=path,candidates=contrasts))
    if source_question is not None:
        for name in ('saved_state','execution','update_id'):
            if source_question.get(name) is not None:compiled[name]=source_question[name]
        if source_question.get('saved_state') or source_question.get('execution'):compiled['operating_point']='saved_state'
    full = bind_selected_analysis_request(host,compiled,tool_use_id=tool_use_id,selection=(method,detail),scientific_question=source_question or payload)
    return dict(status='ready',method=method,request=full,scientific_execution_started=False,
        execution_admission='Original analysis.dispatch owns final source, applicability, authorization and budget admission.',
        limitations=detail['limitations'],cost_scope=detail['cost_scope'])


def compile_v2(host, payload, *, tool_use_id):
    """Resolve physical meaning and actual domains; original worker owns execution."""
    from pydantic import ValidationError
    from tools.research.contracts import ScientificQuestionV2,MechanismStudy
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.design import verify_candidate
    from tools.research.agent import bind_selected_analysis_request
    from tools.research.structure_research import METHOD,parameters,prepare_context,group_matches
    try:q=ScientificQuestionV2.model_validate(payload)
    except ValidationError as exc:
        return dict(status='needs_choice',reason='INVALID_SCIENTIFIC_V2_INPUT',issues=[
            dict(field='.'.join(map(str,e['loc'])),reason=e['msg']) for e in exc.errors()],scientific_execution_started=False)
    def feedback(status,reason,**extra):
        return dict(status=status,reason=reason,question=plain(q),scientific_execution_started=False,**extra)
    s=state(host);spec=s['spec']
    if protected(host) or s['research_status']=='stopped':return feedback('blocked','ORIGINAL_PROTECTED_CLOSEOUT_OR_STOP')
    intent=completed_question_plan(host)
    if not intent:return feedback('needs_prerequisite','COMPLETED_CANDIDATE_BOUND_DIAGNOSE_REQUIRED',
        preparation=dict(tool='research_plan',action='diagnose',fields=['hypothesis','decision.selected_candidate']))
    if q.effect_semantics=='reoptimized_task_capability':
        return compile_reoptimized(host,q,payload,tool_use_id=tool_use_id,intent=intent)
    if q.effect_semantics not in ('mechanism_effect','fixed_input_response'):
        return feedback('unsupported','V2_EFFECT_NOT_IMPLEMENTED',detail={
            'closed_loop_performance':'Requires complete feedback execution and independent frozen task evaluation; no closed-loop derivative adapted.',
            're_equilibrated_passive_response':'Requires qualified passive equilibrium, unilateral active set and KKT regularity; no passive adapter.'}[q.effect_semantics])
    if q.control_treatment!='fixed_absolute_tensions':return feedback('unsupported','FIXED_ABSOLUTE_TENSIONS_REQUIRED')
    if q.control_scope or q.search_strategy or any(plain(q.source_selection).values()):
        return feedback('unsupported','M0_AND_SHORT_M1_REQUIRE_POINT_INPUTS_NOT_CONTROL_SEARCH_OR_M2_SOURCES')
    if q.operating_point in ('re_equilibrated','preserved_physical_state'):
        return feedback('unsupported','WORKING_POINT_MAPPING_NOT_IMPLEMENTED')
    saved=bool(q.saved_state or q.execution)
    if q.operating_point=='frozen_task_initial_state' and (saved or q.update_id is not None):
        return feedback('needs_choice','FROZEN_INITIAL_STATE_CANNOT_USE_SAVED_STATE_SOURCE')
    if q.operating_point=='saved_native_state' and not saved:
        return feedback('needs_prerequisite','SAVED_NATIVE_POINT_REQUIRES_REAL_OWNED_STATE_SOURCE')
    if (q.execution is None)!=(q.update_id is None) or q.saved_state and q.execution:
        return feedback('needs_choice','UNAMBIGUOUS_NATIVE_SOURCE_AND_INTERVAL_REQUIRED')
    candidate=intent['candidate'];c=verify_candidate(host,candidate);view=mathematical_method_view(host,candidate)
    rows=parameters(spec,c);by_path={r['parameter_id']:r for r in rows}
    paths=q.parameter_paths or (intent['agent_hypothesis']['decision'].get('selected_variables') or [])
    if len(paths)>2:return feedback('needs_choice','SELECT_AT_MOST_TWO_PARAMETERS')
    if not paths and q.parameter_group:
        matches=[r['parameter_id'] for r in rows if r['mechanism_differentiation']['supported'] and group_matches(r,q.parameter_group)]
        if 1<=len(matches)<=2:paths=matches
        elif q.operation in ('differentiate','optimize'):
            return feedback('needs_choice','SELECT_UP_TO_TWO_EFFECTIVE_PARAMETERS_FROM_GROUP',choices=dict(parameter_paths=matches))
    if q.operation in ('differentiate','optimize') and not paths:
        return feedback('needs_choice','REGISTERED_PARAMETER_SELECTION_REQUIRED',choices=dict(parameter_paths=[
            r['parameter_id'] for r in rows if r['mechanism_differentiation']['supported']]))
    for path in paths:
        row=by_path.get(path)
        if row is None:return feedback('unsupported','REGISTERED_STRUCTURAL_PARAMETER_REQUIRED',path=path)
        if q.operation!='inspect' and row.get('input_set_changes'):
            return feedback('unsupported','INPUT_FEASIBLE_SET_CHANGE_REQUIRES_SEPARATE_SEMANTICS')
        if q.parameter_group and not group_matches(row,q.parameter_group):return feedback('needs_choice','PARAMETER_PATH_AND_GROUP_DISAGREE')
        if q.operation in ('differentiate','optimize') and not row['mechanism_differentiation']['supported']:
            reason=row['mechanism_differentiation']['reason']
            return feedback('blocked' if reason=='ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED' else 'unsupported',reason,path=path)
    budget=q.requested_budget or intent['agent_hypothesis']['decision'].get('requested_budget')
    if not budget:return feedback('needs_choice','EXPLICIT_LOCAL_EVALUATION_CAP_REQUIRED')
    point_fields=dict(operating_point='saved_state' if saved else 'standardized_initial_pretension')
    for name in ('saved_state','execution','update_id'):
        if getattr(q,name) is not None:point_fields[name]=plain(getattr(q,name))
    if q.effect_semantics=='fixed_input_response':
        if not isinstance(q.target,str):return feedback('needs_choice','SHORT_RESPONSE_REQUIRES_REGISTERED_TASK_CONSTRAINT_OR_NATIVE_OBSERVABLE')
        constraints={r['constraint']['constraint_id'] for r in view['research_opportunities']['metrics'] if r.get('constraint')}
        if q.target not in constraints|{'tip_position','tip_velocity'}:return feedback('unsupported','UNREGISTERED_SHORT_RESPONSE_TARGET')
        if q.response_horizon_s is None:return feedback('needs_choice','EXPLICIT_SHORT_RESPONSE_HORIZON_REQUIRED')
        if q.operating_point=='fixed_generalized_pose':return feedback('unsupported','EXISTING_M1_PRESERVES_RECORDED_VELOCITY_NOT_ZERO_POSE_MAPPING')
        if q.operation=='optimize':return feedback('unsupported','SHORT_RESPONSE_DOES_NOT_OPTIMIZE_A_STRUCTURE_OR_CONTROL')
        method='short_input_response_v1' if q.operation=='inspect' else 'fixed_input_structure_v1'
        needed=1 if method=='short_input_response_v1' else 1+max(1,len(q.comparison_candidates))
        if budget<needed or spec['budgets']['mathematical_evaluations']-s.get('mathematical_evaluations',0)<needed:
            return feedback('blocked','SHARED_MATHEMATICAL_BUDGET_CANNOT_FIT',required_evaluations=needed)
        if method=='fixed_input_structure_v1':
            if len(paths)!=1:return feedback('needs_choice','SHORT_STRUCTURE_RESPONSE_REQUIRES_ONE_REGISTERED_PATH')
            legacy=dict(question_type='structure_parameter_effect',effect_semantics='fixed_input_response',parameter_paths=paths,
                fixed_input='constant_tensions' if q.tensions_n is not None else 'frozen_initial_tensions',
                response_horizon_s=q.response_horizon_s,source_selection=dict(comparison_candidates=plain(q.comparison_candidates)))
            if q.target in constraints:legacy['focus_metric']=q.target
            if q.tensions_n is not None:legacy['tensions_n']=q.tensions_n
            result=compile_v1(host,legacy,tool_use_id=tool_use_id,source_question=payload)
            if result['status']=='ready':result['response_scope']='Existing M1 fixed-input short response only; no full task improvement.'
            return result
        detail=view['methods'][method]
        if detail['planning_status'] in ('unauthorized','blocked','unsupported','insufficient_budget'):
            return feedback('blocked','ORIGINAL_SHORT_RESPONSE_ADMISSION_REQUIRED',missing=detail['missing'])
        compiled={**point_fields,'native':dict(horizon_s=q.response_horizon_s)}
        if q.tensions_n is not None:compiled['native']['tensions_n']=q.tensions_n
        full=bind_selected_analysis_request(host,compiled,tool_use_id=tool_use_id,selection=(method,detail),scientific_question=payload)
        return dict(status='ready',method=method,request=full,scientific_execution_started=False,
            response_scope='Existing legal-tension short input response at two input scales, not structural or full task capability.',required_evaluations=needed)
    if q.response_horizon_s is not None:return feedback('unsupported','INSTANTANEOUS_MECHANISM_HAS_NO_RESPONSE_HORIZON')
    detail=view['methods'].get(METHOD)
    if not detail or detail['planning_status'] in ('unauthorized','blocked','unsupported','insufficient_budget'):
        return feedback('blocked','ORIGINAL_MECHANISM_ADMISSION_REQUIRED',missing=detail['missing'] if detail else ['V2 method grant'])
    if isinstance(q.target,str):
        constraints={r['constraint']['constraint_id'] for r in view['research_opportunities']['metrics'] if r.get('constraint')}
        return feedback('unsupported','TASK_TARGET_REQUIRES_M1_OR_M2_TASK_RESPONSE' if q.target in constraints else 'UNREGISTERED_TARGET')
    study=MechanismStudy(operation=q.operation,target=q.target,parameter_paths=paths,
        point_semantics=q.operating_point,max_evaluations=budget,local_radius_fraction=q.local_radius_fraction,
        comparison_candidates=q.comparison_candidates)
    try:context=prepare_context(spec,c,study,[(plain(r),verify_candidate(host,r)) for r in q.comparison_candidates])
    except ValueError as exc:return feedback('blocked' if str(exc).startswith('MECHANISM_QUESTION_BUDGET') else 'unsupported',str(exc))
    needed=context['evaluations']
    if spec['budgets']['mathematical_evaluations']-s.get('mathematical_evaluations',0)<needed:
        return feedback('blocked','SHARED_MATHEMATICAL_BUDGET_CANNOT_FIT',required_evaluations=needed)
    compiled={**point_fields,'mechanism_study':plain(study)}
    if q.tensions_n is not None:compiled['native']=dict(tensions_n=q.tensions_n)
    full=bind_selected_analysis_request(host,compiled,tool_use_id=tool_use_id,selection=(METHOD,detail),scientific_question=payload)
    return dict(status='ready',method=METHOD,request=full,scientific_execution_started=False,
        hypothesis=q.hypothesis or intent['agent_hypothesis'].get('hypothesis'),required_evaluations=needed,
        minimum_evaluations=context['minimum_evaluations'],limitations=detail['limitations'],cost_scope=detail['cost_scope'])


def compile_reoptimized(host,q,payload,*,tool_use_id,intent):
    """Select admitted saved Conic/T1 sources; never generate models or run T1."""
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.agent import bind_selected_analysis_request
    from tools.research.optimal_capability import CONIC,SENSITIVITY,family_parameters
    from tools.research.design import verify_candidate,parameter_value
    candidate=intent['candidate'];c=verify_candidate(host,candidate);s=state(host);spec=s['spec']
    view=mathematical_method_view(host,candidate)
    def feedback(status,reason,**extra):
        return dict(status=status,reason=reason,scientific_execution_started=False,**extra)
    if q.control_treatment!='reoptimized':return feedback('needs_choice','M2_REQUIRES_EXPLICIT_REOPTIMIZED_CONTROL_TREATMENT')
    if q.operating_point!='frozen_task_initial_state' or q.saved_state or q.execution or q.update_id is not None:
        return feedback('unsupported','M2_REQUIRES_COMPLETE_FROZEN_INITIAL_TASK_AND_MATCHED_CONTROL_SOURCES')
    if q.tensions_n is not None or q.response_horizon_s is not None or q.comparison_candidates or q.source_selection.comparison_candidates:
        return feedback('unsupported','M2_USES_FULL_TASK_MODEL_OR_SAVED_T1_NOT_SHORT_FIXED_INPUT_FIELDS')
    metrics={r['constraint']['constraint_id'] for r in view['research_opportunities']['metrics'] if r.get('constraint')}
    if not isinstance(q.target,str) or q.target not in metrics|{'best_found_J','optimal_task_violation'}:
        return feedback('needs_choice','M2_REQUIRES_REGISTERED_TASK_CONSTRAINT_OR_TASK_VIOLATION',choices=sorted(metrics))
    paths=q.parameter_paths or intent['agent_hypothesis']['decision'].get('selected_variables') or []
    sources=q.source_selection
    if sources.model_results and sources.t1_results:return feedback('needs_choice','SELECT_CONIC_MODELS_OR_NATIVE_T1_NOT_A_MIXED_GRADIENT')
    if q.operation=='optimize':
        if paths:return feedback('needs_prerequisite','GENERATE_CONTRAST_THEN_OPTIMIZE_CONTROL_PER_CANDIDATE',
            preparation=dict(tool='research_plan',action='generate'),automatic_T1=False)
        if sources.model_results or sources.t1_results:return feedback('unsupported','CONTROL_OPTIMIZATION_REQUIRES_A_BOUND_CONTROL_SOURCE')
        legacy=dict(question_type='control_feasibility',effect_semantics='reoptimized_task_capability',
            source_selection=dict(control_source=plain(sources.control_source)) if sources.control_source else {})
        for key in ('control_scope','search_strategy','requested_budget'):
            if getattr(q,key) is not None:legacy[key]=plain(getattr(q,key))
        if q.target in metrics:legacy['focus_metric']=q.target
        return compile_v1(host,legacy,tool_use_id=tool_use_id,source_question=payload)
    if q.control_scope or q.search_strategy or sources.control_source:
        return feedback('unsupported','SAVED_M2_REUSES_MATCHED_RECORDED_SEARCH_SETTINGS')
    if not paths:
        if q.operation!='inspect':return feedback('needs_choice','M2_STRUCTURAL_PARAMETER_PATH_REQUIRED')
        if sources.model_results or sources.t1_results:return feedback('needs_choice','STRUCTURAL_SOURCES_REQUIRE_A_REGISTERED_PATH')
        return compile_v1(host,dict(question_type='bounded_control_initialization'),tool_use_id=tool_use_id,source_question=payload)
    from tools.research.structure_research import parameters,group_matches
    rows={r['parameter_id']:r for r in parameters(spec,c)}
    for path in paths:
        if path not in rows or not rows[path]['mechanism_differentiation']['supported']:
            return feedback('unsupported','M2_REQUIRES_EFFECTIVE_AUTHORIZED_CONTINUOUS_PARAMETER',path=path)
        if q.parameter_group and not group_matches(rows[path],q.parameter_group):return feedback('needs_choice','PARAMETER_PATH_AND_GROUP_DISAGREE')
    conic=view['methods'].get(SENSITIVITY,{});model_choices=[]
    if len(paths)==1 and not sources.t1_results:
        for row in conic.get('readiness',{}).get('variables',[]):
            if row['variable']!=paths[0]:continue
            for ready in row.get('ready_stencils',[]):
                request=ready['request']
                if ready['admission']['status']!='admissible':continue
                if sources.model_results and request['optimal_sensitivity']['model_results']!=[plain(ref) for ref in sources.model_results]:continue
                model_choices.append((request,ready['admission']['expected_mathematical_evaluations']))
    method=None;compiled=None;needed=None
    if len(model_choices)>1:
        return feedback('needs_choice','SELECT_COMPARABLE_CONIC_MODEL_STENCIL',choices=[r['optimal_sensitivity'] for r,_ in model_choices])
    if model_choices:
        request,needed=model_choices[0];method=SENSITIVITY
        compiled=dict(model_source='gvs',operating_point=request['operating_point'],optimal_sensitivity=request['optimal_sensitivity'])
    elif sources.model_results:
        if conic.get('planning_status') in ('unauthorized','blocked','insufficient_budget','unsupported'):
            return feedback('blocked','ORIGINAL_M2_METHOD_ADMISSION_BLOCKED',missing=conic.get('missing'),method=SENSITIVITY)
        return feedback('needs_prerequisite','ADMITTED_SAVED_CONIC_MODEL_STENCIL_REQUIRED',
            missing=conic.get('missing'),detail_query=conic.get('detail_query'),preparation=conic.get('readiness',{}).get('model_preparation'))
    else:
        detail=view['methods'].get(T2,{})
        if (not detail or detail.get('planning_status')=='unauthorized') and not sources.t1_results and conic.get('formal_execution_authorized'):
            return feedback('needs_prerequisite','ADMITTED_SAVED_CONIC_MODEL_STENCIL_REQUIRED',
                detail_query=conic.get('detail_query'),preparation=conic.get('readiness',{}).get('model_preparation'),automatic_T1=False)
        if not detail or detail.get('planning_status') in ('unauthorized','blocked','insufficient_budget'):
            return feedback('blocked','ORIGINAL_M2_METHOD_ADMISSION_BLOCKED',missing=detail.get('missing',['Native T2 method grant']),method=T2)
        if detail.get('planning_status')=='unsupported':
            return feedback('unsupported','ORIGINAL_NATIVE_T2_TASK_UNSUPPORTED',missing=detail['missing'],
                conic_detail_query=conic.get('detail_query'),task_constraints=sorted(metrics))
        selected=[plain(ref) for ref in sources.t1_results];choices=[]
        for path in paths:
            found=[r for r in detail.get('ready_requests',[]) if r['nonlinear_response']['variable']==path and
                (not selected or r['nonlinear_response']['t1_results'][0]==selected[0] and
                    all(ref in selected for ref in r['nonlinear_response']['t1_results']))]
            if not found:return feedback('needs_prerequisite','COMPARABLE_COMPLETED_BASELINE_MINUS_PLUS_T1_REQUIRED',
                missing=['matched frozen task, state, absolute initial sequence, search settings and finite budget'],
                preparation=[dict(tool='research_plan',action='generate',parameter_path=path),
                    dict(tool='research_plan',action='initialize_control'),dict(tool='research_plan',action='diagnose')],
                next_question='Choose reoptimized_task_capability/optimize for each candidate only if you decide to fund its original control search.',
                conic_detail_query=conic.get('detail_query'),detail_query=detail.get('detail_query'),automatic_T1=False)
            if len(found)>1 and not selected:return feedback('needs_choice','MULTIPLE_COMPARABLE_T1_STENCILS',
                choices=[r['nonlinear_response'] for r in found])
            choices.extend(found)
        refs=[ref for r in choices for ref in r['nonlinear_response']['t1_results']]
        if selected and any(ref not in refs for ref in selected):return feedback('needs_choice','SELECTED_T1_SOURCES_NOT_IN_THE_REQUESTED_STENCIL')
        if len({r['nonlinear_response']['t1_results'][0]['artifact_id'] for r in choices})!=1:
            return feedback('needs_choice','M2_PATHS_REQUIRE_ONE_SHARED_MATCHED_BASELINE')
        if len(choices)==1:response=choices[0]['nonlinear_response']
        else:
            directions=[]
            for i,r in enumerate(choices):
                request=r['nonlinear_response'];path=request['variable'];refs=request['t1_results']
                base=host.store.artifact(refs[0]);minus=host.store.artifact(refs[1])
                a=family_parameters(spec,verify_candidate(host,base['candidate']),path)[0]
                b=family_parameters(spec,verify_candidate(host,minus['candidate']),path)[0]
                h=parameter_value(a,path)-parameter_value(b,path)
                directions.append(dict(direction_id=path+'/'+str(i),variables={path:1.},coordinate_unit=request['unit'],
                    coordinates=[0.,-h,h],t1_results=refs))
            response=dict(version='nonlinear_response_v2',directions=directions)
        method=T2;needed=1;compiled=dict(nonlinear_response=response)
    detail=view['methods'][method]
    if detail['planning_status'] in ('unauthorized','blocked','insufficient_budget','unsupported'):
        return feedback('blocked','ORIGINAL_M2_METHOD_ADMISSION_BLOCKED',missing=detail['missing'],method=method)
    if (q.requested_budget is not None and q.requested_budget<needed) or view['remaining_evaluations']<needed:
        return feedback('blocked','SHARED_MATHEMATICAL_BUDGET_CANNOT_FIT',required_evaluations=needed)
    full=bind_selected_analysis_request(host,compiled,tool_use_id=tool_use_id,selection=(method,detail),scientific_question=payload)
    return dict(status='ready',method=method,request=full,required_evaluations=needed,scientific_execution_started=False,
        effect_scope='Conditional affine optimal capability sensitivity' if method==SENSITIVITY else
            'Saved matched finite-budget Native structural secants; fixed-control and reoptimized effects remain separate.',
        strict_optimal_value_gradient=False,automatic_T1=False,limitations=detail['limitations'])
