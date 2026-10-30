"""Deterministic scientific choices -> existing registered AnalysisRequest.

No optimizer, state machine, source ledger or execution admission lives here.
"""
from copy import deepcopy

from tools.platform_store import plain
from tools.research.contracts import ScientificQuestion, ScientificQuestionV2, ScientificControlEffort, LocalControlSearchSettings
from tools.research.state import state, protected
from tools.research.nonlinear_capability import T1, T2

INTERFACE = 'scientific_question_v1'


def enabled(spec):
    return spec.get('research_decisions',{}).get('analysis_interface') in (INTERFACE,'scientific_question_v2')


def question_contract(spec):
    return ScientificQuestionV2 if spec.get('research_decisions',{}).get('analysis_interface')=='scientific_question_v2' else ScientificQuestion


def question_schema(spec):
    schema=question_contract(spec).model_json_schema()
    if question_contract(spec) is ScientificQuestionV2:
        for key in ('search_strategy','requested_budget'):schema['properties'].pop(key)
        schema['$defs']['ScientificControlScope']['properties']['mode']['description']='Choose the full frozen task or a local correction window. control_search_effort specifies 2–4 uniform knots; local corrections require interior knots and zero endpoint corrections. Evaluation always covers the full frozen task.'
    return schema


def control_settings(spec, effort, *, window=None, channels=None):
    """Shared v2 effort mapping; original LocalControlSearchSettings is final authority."""
    q=ScientificControlEffort.model_validate(effort)
    duration=spec['analysis_protocol']['duration_s'];a,b=window or (0.,duration)
    if not 0<=a<b<=duration:raise ValueError('LOCAL_WINDOW_MUST_BE_INSIDE_FROZEN_TASK')
    if window is not None and q.knot_count<3:raise ValueError('LOCAL_WINDOW_REQUIRES_INTERIOR_KNOT_AND_ZERO_ENDPOINTS')
    domain=LocalControlSearchSettings.model_json_schema()['properties']
    limits=spec.get('native_control_limits',{})
    iterations=q.iterations if q.iterations is not None else min(q.evaluation_requests,limits.get('iterations',domain['iterations']['maximum']),domain['iterations']['maximum'])
    settings=dict(version='local_control_search_v2',method=q.method,
        knots_s=[a+(b-a)*i/(q.knot_count-1) for i in range(q.knot_count)],
        correction_window_s=[0.,duration],iterations=iterations,evaluation_requests=q.evaluation_requests)
    settings['knots_s'][-1]=b
    if window is not None:
        settings['active_coefficients']=list(range(channels,(q.knot_count-1)*channels))
    result=LocalControlSearchSettings.model_validate(settings)
    for name,limit in limits.items():
        actual=len(result.knots_s) if name=='knots_s' else getattr(result,name)
        if actual>limit:raise ValueError('ORIGINAL_STUDY_NATIVE_CONTROL_LIMIT: '+name)
    return result


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
    from pydantic import ValidationError
    from tools.research.task_constraints import mathematical_method_view
    from tools.research.agent import bind_selected_analysis_request
    from tools.research.design import verify_candidate
    from tools.research.optimal_capability import family_analysis_parameters
    try:
        question = question_contract(state(host)['spec']).model_validate(payload)
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
    if q.question_type=='control_feasibility':
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
    if method==T1:
        if q.source_selection.comparison_candidates or q.source_selection.t1_results:
            return feedback('unsupported','CONTROL_SEARCH_REQUIRES_A_CONTROL_SOURCE_NOT_STRUCTURAL_EVIDENCE')
        effort=getattr(q,'control_search_effort',None)
        if isinstance(q,ScientificQuestionV2) and (effort is None or q.search_strategy is not None or q.requested_budget is not None):
            return feedback('needs_choice','USE_CONTROL_SEARCH_EFFORT_WITH_INDEPENDENT_KNOT_ITERATION_AND_CALLBACK_FIELDS',fields=['control_search_effort'])
        plan_budget = intent['agent_hypothesis']['decision'].get('requested_budget',0)
        budget = q.requested_budget if q.requested_budget is not None else plan_budget or None
        if effort:budget=effort.evaluation_requests
        missing = [name for name in ('control_scope',) if getattr(q,name) is None]
        if not effort and q.search_strategy is None:missing.append('search_strategy')
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
        if effort:
            try:
                settings=plain(control_settings(spec,effort,window=q.control_scope.window_s if q.control_scope.mode=='time_window' else None,
                    channels=len(c['configuration']['robot']['structure']['data']['tendons'])))
                knots=settings['knots_s']
            except ValueError as exc:
                return feedback('needs_choice','SEARCH_SETTINGS_OUTSIDE_ORIGINAL_CONTRACT',field='control_search_effort',reason_detail=str(exc))
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
        if q.control_scope or q.search_strategy or getattr(q,'control_search_effort',None) or q.source_selection.control_source:
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
    full = bind_selected_analysis_request(host,compiled,tool_use_id=tool_use_id,selection=(method,detail),scientific_question=payload)
    return dict(status='ready',method=method,request=full,scientific_execution_started=False,
        execution_admission='Original analysis.dispatch owns final source, applicability, authorization and budget admission.',
        limitations=detail['limitations'],cost_scope=detail['cost_scope'])
