"""Explicit admission and saved-model binding for the optional T1/T2 kernels.

No candidate creation, alternate Store, worker launcher or budget owner lives here.
"""
from copy import deepcopy
import math
import sys

from tools.platform_store import plain
from tools.state_io import digest
from tools.research.state import state

CONIC = 'sampled-affine-conic-minimax-v1'
SENSITIVITY = 'controlled-capability-sensitivity-v1'


def freeze_family_variables(space, grant):
    """Study-only opt-in; domains remain owned by the frozen family generator."""
    import re
    from extensions.tendon_family.family_space import parameter_capabilities
    if (not isinstance(grant,dict) or set(grant)!={'version','variables'} or
            grant['version'] not in ('family_sensitivity_v1','family_sensitivity_v2') or not isinstance(grant['variables'],list)
            or not grant['variables'] or any(not isinstance(v,str) for v in grant['variables'])
            or len(set(grant['variables']))!=len(grant['variables'])):
        raise ValueError('EXPLICIT_VERSIONED_FAMILY_SENSITIVITY_GRANT_REQUIRED')
    if grant['version']=='family_sensitivity_v2':
        # Authorization is a path selector, never a second physical domain. Resolve
        # existence, type and effectiveness against each actual candidate later.
        if any(not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*(?:\.(?:[A-Za-z_][A-Za-z_0-9]*|0|[1-9][0-9]*|\*))*',v) for v in grant['variables']):
            raise ValueError('FAMILY_PARAMETER_PATH_SELECTOR_REQUIRED')
        return deepcopy(grant)
    request=dict(family_space_identity=digest(space),segment_count=max(space['executable_segment_counts']),
        tendon_count=space['executable_tendon_count_bounds'][0])
    if space['version']=='serial_family_space_v2':request['version']='serial_family_generation_v2'
    domains={r['parameter_id']:r for r in parameter_capabilities(space,request)}
    for path in grant['variables']:
        radius=re.fullmatch(r'spans\.(0|[1-9][0-9]*)\.radius_m',path)
        domain=domains.get('spans.*.radius_m' if radius else path)
        supported=bool(radius and int(radius[1])<space['executable_tendon_count_bounds'][1]) or bool(re.fullmatch(r'segments\.(0|[1-9][0-9]*)\.(length_m|young_pa)',path))
        if not supported or not domain or domain['minimum']>=domain['maximum']:
            raise ValueError('EXECUTABLE_FAMILY_CONTINUOUS_DOMAIN_REQUIRED: '+str(path))
    return deepcopy(grant)


def family_variable_authorized(spec,path):
    grant=spec.get('family_sensitivity_variables',{})
    if grant.get('version')=='family_sensitivity_v1':return path in grant.get('variables',[])
    if grant.get('version')!='family_sensitivity_v2':return False
    return any(len(p.split('.'))==len(path.split('.')) and all(a=='*' or a==b for a,b in zip(p.split('.'),path.split('.')))
        for p in grant.get('variables',[]))


def family_analysis_parameters(spec,candidate):
    from extensions.tendon_family.family_space import parameter_capabilities
    rows=parameter_capabilities(spec['family_space'],candidate['parameters'])
    for row in rows:
        path=row['parameter_id'];row['study_authorized']=family_variable_authorized(spec,path) and '*' not in path
        legacy_fixed=path.startswith('segments.') and (path.endswith('.young_pa') or '.sections.' in path)
        row['applicable_mathematical_methods']=[m for m in row['supported_methods'] if m!='generate' and
            'analysis' in spec.get('capabilities',[]) and
            ((m=='fixed_input_structure_v1' and (legacy_fixed or row['study_authorized'])) or
             (m!='fixed_input_structure_v1' and row['study_authorized'] and spec.get('mathematical_methods',{}).get(m)))]
        if (row['continuous_perturbation'] and row['study_authorized'] and 'analysis' in spec.get('capabilities',[])
                and spec.get('mathematical_methods',{}).get(CONIC) and spec.get('mathematical_methods',{}).get(SENSITIVITY)):
            row['applicable_mathematical_methods'].append(SENSITIVITY)
        if not row['study_authorized']:row['authorization_reason']='Not selected by frozen family_sensitivity_variables'
    return rows


def family_parameters(spec, candidate, path, *, continuous=True):
    """Resolve one authorized actual path and verify the existing generated model."""
    from extensions.tendon_family.family_space import parse_build, resolved_request
    from extensions.tendon_family.generated_serial import generate_family
    if not family_variable_authorized(spec,path):raise ValueError('AUTHORIZED_FAMILY_CONTINUOUS_PARAMETER_REQUIRED')
    if candidate.get('generation_version') not in ('serial_family_generation_v1','serial_family_generation_v2'):
        raise ValueError('CURRENT_GENERATED_FAMILY_CANDIDATE_REQUIRED')
    build=parse_build(dict(space=spec['family_space'],request=candidate['parameters']))
    params=resolved_request(spec['family_space'],candidate['parameters'])
    if spec['family_sensitivity_variables']['version']=='family_sensitivity_v1':
        # Preserve the original sparse normalization of the sealed v1 contract.
        params=plain(build.request)
        from extensions.tendon_family.family_space import parameter_capabilities, Span
        old_domains={r['parameter_id']:r for r in parameter_capabilities(spec['family_space'],params)}
        if path.startswith('spans.'):
            params['spans']=params['spans'] or [plain(Span(last_segment=params['segment_count']-1,count=params['tendon_count']))]
            for span in params['spans']:
                if span['radius_m'] is None:span['radius_m']=spec['family_space']['routing_domains']['radius_m']['default']
        for i in range(params['segment_count']):
            choice=params['segments'].setdefault(str(i),{})
            for key in ('length_m','young_pa'):
                if choice.get(key) is None:choice[key]=old_domains[f'segments.{i}.{key}']['default']
        params=plain(parse_build(dict(space=spec['family_space'],request=params)).request)
    domains={r['parameter_id']:r for r in family_analysis_parameters(spec,candidate) if '*' not in r['parameter_id']}
    if path not in domains:raise ValueError('PARAMETER_NOT_IN_CURRENT_CANDIDATE_TOPOLOGY')
    domain=domains[path]
    if not domain['effective_in_current_execution']:raise ValueError('PARAMETER_HAS_NO_EFFECT_ON_GENERATED_ROUTING: '+domain['analysis_reason'])
    if continuous and not domain['continuous_perturbation']:raise ValueError('PARAMETER_NOT_CONTINUOUS_STRUCTURAL_DIRECTION: '+domain['analysis_reason'])
    robot,mesh,_=generate_family(build);cfg=candidate['configuration']
    if (robot!=cfg['robot']['structure']['data'] or mesh!=cfg['policy']['discretization']['data']
            or cfg['policy']['candidate_builder']['parameters']['data']!=plain(build)):
        raise ValueError('GENERATED_CONFIGURATION_DOES_NOT_MATCH_FROZEN_REQUEST')
    return params,dict(path=path,units=domain['unit'],bounds=[domain.get('minimum'),domain.get('maximum')],
        current_value=domain['current_value'],category=domain['category'],data_type=domain['data_type'],choices=domain['choices'],
        continuous_perturbation=domain['continuous_perturbation'],physical_component=domain['physical_component'],
        comparison_path=domain.get('comparison_path',path),input_set_changes=domain.get('input_set_changes',False),
        source='current frozen FamilySpace continuous domain',affected_tendon_indices=domain.get('affected_tendon_indices'),
        bounds_source=dict(family_space_identity=spec['family_space_identity'],path=domain['domain_source']))


def dependencies():
    """The existing worker launches sys.executable; inspect that interpreter."""
    result = dict(python=sys.executable, available=False)
    try:
        import cvxpy
        import clarabel
        result.update(available='CLARABEL' in cvxpy.installed_solvers(),
                      cvxpy=cvxpy.__version__, clarabel=clarabel.__version__)
    except (ImportError, OSError) as exc:
        result['reason'] = str(exc)
    return result


def conic_subproblems(requirements):
    """Exact enumerated branch count used by the existing PATH kernel."""
    paths=[c for c in requirements.constraints if c.kind=='path_bound'] if requirements is not None else []
    return max(1,len(paths[0].indices)-2) if paths and len(paths[0].path_vertices_m)==3 else 1


def method_admission(spec, query, used=0, *, requirements=None):
    methods = spec.get('mathematical_methods', {})
    required = [CONIC] + ([SENSITIVITY] if query.optimal_sensitivity else [])
    if requirements is None and spec.get('configuration'):
        from tools.research.task_constraints import describe_analysis_requirements
        requirements=describe_analysis_requirements(spec['configuration'],{})
    branches=conic_subproblems(requirements)
    models=1+2*len(query.optimal_sensitivity.steps) if query.optimal_sensitivity else 1
    dual=2*len(query.optimal_sensitivity.steps) if query.optimal_sensitivity else 0
    count = models*branches+dual+(0 if query.optimal_sensitivity else 1)
    remaining = max(0, spec['budgets']['mathematical_evaluations']-used)
    reasons = []
    if requirements is None and spec.get('canonical_task'):
        reasons.append('TASK_REQUIREMENTS_REQUIRED_FOR_INTERNAL_SOLVE_ACCOUNTING')
    if any(not methods.get(m) for m in required):
        reasons.append('EXPLICIT_FROZEN_MATHEMATICAL_METHOD_AUTHORIZATION_REQUIRED')
    environment = dependencies()
    if not environment['available']:reasons.append('OPTIONAL_CVXPY_CLARABEL_UNAVAILABLE_IN_WORKER_PYTHON')
    if remaining < count:reasons.append('INSUFFICIENT_MATHEMATICAL_EVALUATIONS')
    return dict(status='not_applicable' if reasons else 'admissible', reasons=reasons,
        methods=required, expected_mathematical_evaluations=count, remaining_evaluations=remaining,
        model_builds=0 if query.optimal_sensitivity else 1,
        model_reuse=None if query.optimal_sensitivity else 0,
        model_reuse_status='requires_saved_context_validation' if query.optimal_sensitivity else 'not_requested',
        required_candidate=plain(query.candidate),
        required_model_results=[plain(r) for r in query.optimal_sensitivity.model_results] if query.optimal_sensitivity else [],
        capability_solves=models*branches,kernel_subproblems_per_model=branches,
        dual_face_solves=dual,
        environment=environment, accounting='Reserve all planned solve attempts; failures and unused reserved attempts remain spent; receipt reuse costs zero.',
        alternatives=['Read existing registered evidence without a new solve.',
            'Request an already authorized SLSQP analysis if its budget fits.',
            'Obtain separately authorized candidate models, optional dependencies or a new Study grant.'])


def sensitivity_cost(steps, reused, remaining, *, conic_authorized=False, subproblems=1):
    """Planning only: reuse counts must come from validated complete stencils."""
    required=1+2*steps;kernel=required*subproblems+2*steps
    missing=None if reused is None else required-reused
    methods=[dict(operation='linearization',evaluations=1)]
    if conic_authorized:methods.append(dict(operation='task_capability',method=CONIC,evaluations=1+subproblems))
    totals=[kernel+missing*m['evaluations'] for m in methods] if missing is not None else None
    return dict(required_models=required,validated_reusable_models=reused,missing_models=missing,
        kernel_evaluations=kernel,kernel_subproblems_per_model=subproblems,preparation_methods=methods,remaining_total_range=totals,
        budget_sufficient=None if totals is None else remaining>=max(totals),
        wall_cost='unknown',other_budgets='Candidate generation, Provider and physical launches are separate.',
        assumptions='Preparation methods require their own task/model admission; no automatic generation or solve.')


def candidate_methods(host, reference, *, analysis_metadata=None):
    """Candidate-specific discovery; executable T2 uses the same saved-context gate."""
    from tools.research.design import verify_candidate, parameter_value
    from tools.research.contracts import AnalysisRequest
    s=state(host);spec=s['spec'];candidate=verify_candidate(host,reference)
    from tools.research.task_constraints import describe_analysis_requirements
    requirements=describe_analysis_requirements(candidate['configuration'],{})
    branches=conic_subproblems(requirements)
    methods=spec.get('mathematical_methods',{});remaining=max(0,spec['budgets']['mathematical_evaluations']-s.get('mathematical_evaluations',0))
    variables=(spec.get('family_sensitivity_variables',{}).get('variables',[]) if spec.get('start_mode')=='family_space'
        else [p for p in spec['allowed_parameters'] if p.endswith(('.length_m','.young_pa'))])
    if spec.get('family_sensitivity_variables',{}).get('version')=='family_sensitivity_v2':
        variables=[r['parameter_id'] for r in family_analysis_parameters(spec,candidate) if r['study_authorized'] and r['continuous_perturbation']]
    # Stencil discovery needs identity/eligibility, not every Native rollout.
    # Read once before the variable loop; execution still validates original models.
    if analysis_metadata is None:
        analysis_metadata=[(ref,host.store.artifact(ref,paths=('status','implementation','model','protocol',
            'candidate','requested_operation.operating_point'))) for ref in s.get('analysis_results',[])]
    eligible=[(ref,raw) for ref,raw in analysis_metadata if raw.get('status')=='computed'
        and raw.get('implementation')==s['freeze'] and raw.get('model') and raw.get('protocol')==spec['analysis_protocol']]
    rows=[]
    for variable in variables:
        row=dict(variable=variable,status='missing_models',ready_stencils=[],incomplete_stencils=[],rejections=[])
        models=[]
        for ref,raw in eligible:
            try:
                c=verify_candidate(host,raw['candidate'])
                p=family_parameters(spec,c,variable)[0] if spec.get('start_mode')=='family_space' else c['parameters']
                models.append((ref,raw,parameter_value(p,variable)))
            except (ValueError,KeyError):continue
        try:
            if spec.get('start_mode')=='family_space':
                parameters,parameter=family_parameters(spec,candidate,variable)
            else:
                parameters=candidate['parameters'];parameter=dict(path=variable,
                    units='m' if variable.endswith('length_m') else 'Pa',bounds=spec['allowed_parameters'][variable])
            origin=parameter_value(parameters,variable)
            row.update(parameter=parameter,current_value=origin,
                maximum_symmetric_step=min(origin-parameter['bounds'][0],parameter['bounds'][1]-origin))
        except ValueError as exc:row.update(status='not_applicable',reason=str(exc))
        for base,raw,origin in models:
            if raw['candidate']!=plain(reference):continue
            # Discover only already registered symmetric groups. No candidate/model creation.
            for h in sorted({abs(value-origin) for _,_,value in models if value!=origin},reverse=True):
                for k in (1,2):
                    steps=[h] if k==1 else [h,h/2]
                    refs=[base];missing=[]
                    for offset in [v for step in steps for v in (-step,step)]:
                        match=next((r for r,_,v in models if math.isclose(v-origin,offset,rel_tol=1e-10,abs_tol=0.)),None)
                        if match is not None:refs.append(match)
                        else:missing.append(origin+offset)
                    if missing:
                        row['incomplete_stencils'].append(dict(steps=steps,missing_parameter_values=missing,
                            unvalidated_model_results=refs,operating_point=raw['requested_operation']['operating_point']))
                        continue
                    try:
                        query=AnalysisRequest.model_validate(dict(candidate=reference,operation='task_capability',
                            operating_point=raw['requested_operation']['operating_point'],protocol=spec['analysis_protocol'],
                            capability_method=CONIC,optimal_sensitivity=dict(variable=variable,steps=steps,model_results=refs)))
                        sensitivity_context(host,query)
                        fit=method_admission(spec,query,s.get('mathematical_evaluations',0),requirements=requirements)
                        row['ready_stencils'].append(dict(request=plain(query),admission=fit,
                            cost=sensitivity_cost(k,len(refs),remaining,conic_authorized=bool(methods.get(CONIC)),subproblems=branches)))
                    except (ValueError,KeyError) as exc:
                        if str(exc) not in row['rejections']:row['rejections'].append(str(exc))
        if row['ready_stencils']:
            row['status']='executable' if any(v['admission']['status']=='admissible' for v in row['ready_stencils']) else 'not_applicable'
        rows.append(row)
    reasons=[]
    if not all(methods.get(m) for m in (CONIC,SENSITIVITY)):reasons.append('method_not_authorized')
    if not dependencies()['available']:reasons.append('worker_dependency_unavailable')
    if remaining<3*branches+2:reasons.append('insufficient_budget')
    if not variables:reasons.append('no_authorized_continuous_variable')
    if not any(r['ready_stencils'] for r in rows):reasons.append('missing_validated_model_stencil')
    return dict(method=SENSITIVITY,status='executable' if not reasons and any(r['status']=='executable' for r in rows) else 'not_applicable',
        reasons=reasons,variables=rows,remaining_evaluations=remaining,
        planning=[sensitivity_cost(k,None,remaining,conic_authorized=bool(methods.get(CONIC)),subproblems=branches) for k in (1,2)],
        from_zero_examples=[sensitivity_cost(k,0,remaining,conic_authorized=bool(methods.get(CONIC)),subproblems=branches) for k in (1,2)],
        model_preparation=dict(steps='Agent chooses h, optionally h/2, inside the parameter bounds; no automatic perturbation.',
            required_values=['d0','d0-h','d0+h','d0-h/2 (two scales)','d0+h/2 (two scales)'],
            reuse='Only ready_stencils passed sensitivity_context; incomplete groups are unvalidated inventory.',
            request_template=dict(candidate='<generated stencil candidate>',operation='linearization',
                operating_point='controller_start_input',scoring_window_s=spec['analysis_protocol']['windows_s'][0],protocol=spec['analysis_protocol']),
            alternative=dict(operation='task_capability',capability_method=CONIC),
            evidence_query=dict(reference=plain(reference),view='working_set',pointer='/all_fresh_results')))


def sensitivity_context(host, query):
    """Validate current owned models and one authorized continuous parameter."""
    from tools.research.design import verify_candidate, parameter_value, set_parameter
    from tools.research.task_constraints import describe_analysis_requirements, check_analysis_applicability, model_assessment
    from schemas.platform import SessionInput
    from schemas.platform_analysis import EndpointLinearizedModel
    s = state(host); request = query.optimal_sensitivity; path = request.variable
    if len(request.steps)==2 and not math.isclose(request.steps[0]/2,request.steps[1],rel_tol=1e-10,abs_tol=0.):
        raise ValueError('EXPLICIT_STENCIL_REQUIRES_H_AND_HALF_H')
    family=s['spec'].get('start_mode')=='family_space'
    continuous=(path.startswith('segments.') and path.split('.')[-1] in ('length_m','young_pa')) or (family and path.startswith('spans.') and path.endswith('.radius_m'))
    if (not family and (len(path.split('.')) != 3 or not continuous or path not in s['spec']['allowed_parameters'])):
        raise ValueError('AUTHORIZED_CONTINUOUS_PARAMETER_REQUIRED')
    points=[]; base_candidate=None; base_result=None
    bounds=None if family else s['spec']['allowed_parameters'][path]
    parameter=None; base_parameters=None; model_identities=[]
    for reference in map(plain,request.model_results):
        if reference not in s.get('analysis_results',[]):
            raise ValueError('REGISTERED_CURRENT_STUDY_MODEL_REQUIRED')
        raw=host.store.artifact(reference)
        c=verify_candidate(host,raw['candidate'])
        parameters=c['parameters']
        if family:
            parameters,parameter=family_parameters(s['spec'],c,path);bounds=parameter['bounds']
        if (raw.get('implementation')!=s['freeze'] or raw.get('status')!='computed'
                or raw.get('protocol')!=plain(query.protocol) or not raw.get('model')
                or raw.get('requested_operation',{}).get('operating_point')!=query.operating_point):
            raise ValueError('CURRENT_IMPLEMENTATION_PROTOCOL_AND_OPERATING_POINT_REQUIRED')
        if base_candidate is None:
            base_candidate=c; base_result=raw; base_parameters=parameters
            if raw['candidate']!=plain(query.candidate):raise ValueError('BASELINE_CANDIDATE_MISMATCH')
        value=parameter_value(parameters,path)
        for allowed,(lo,hi) in s['spec']['allowed_parameters'].items():
            current=parameter_value(c['parameters'],allowed)
            if not isinstance(current,(int,float)) or not math.isfinite(current) or not lo<=current<=hi:
                raise ValueError('CANDIDATE_PARAMETERS_OUTSIDE_CURRENT_STUDY_GRANT')
        if not isinstance(value,(int,float)) or not math.isfinite(value) or not bounds[0]<=value<=bounds[1]:
            raise ValueError('PARAMETER_OUTSIDE_CURRENT_STUDY_RANGE')
        expected=deepcopy(base_parameters);set_parameter(expected,path,value)
        cfg=c['configuration']; base_cfg=base_candidate['configuration']
        if (expected!=parameters or c['source_identity']!=base_candidate['source_identity']
                or c['profile_identity']!=base_candidate['profile_identity'] or cfg['task']!=base_cfg['task']
                or cfg['seed']!=base_cfg['seed']
                or any(cfg['policy'][k]!=base_cfg['policy'][k] for k in ('controller','backend','dynamics_model','discretization'))):
            raise ValueError('SINGLE_PARAMETER_FIXED_TASK_SOURCE_AND_MODEL_REQUIRED')
        m=EndpointLinearizedModel.model_validate(raw['model']); binding=raw['binding']
        if family:
            model_identities.append(m.binding.get('model_identity'))
            if (m.protocol_identity!=digest(plain(query.protocol)) or
                    m.binding.get('analysis_protocol_identity')!=m.protocol_identity):
                raise ValueError('MODEL_FROZEN_PROTOCOL_IDENTITY_MISMATCH')
        if (binding.get('candidate')!=raw['candidate'] or binding.get('candidate_id')!=c['candidate_id']
                or binding.get('effective_configuration_identity')!=digest(cfg)
                or binding.get('task_identity')!=digest(cfg['task'])
                or any(m.binding.get(k)!=binding.get(k) for k in ('candidate_id','effective_configuration_identity','task_identity','source_identity'))):
            raise ValueError('MODEL_CANDIDATE_CONFIGURATION_BINDING_MISMATCH')
        inp=SessionInput.model_validate(cfg)
        req=describe_analysis_requirements(inp,binding)
        if plain(req)!=raw['task_analysis']:raise ValueError('FROZEN_TASK_REQUIREMENT_MISMATCH')
        applicability=check_analysis_applicability(req,query,model_assessment(inp,req,query.operation,model=m),model=m)
        if applicability['status']=='not_applicable':raise ValueError('MODEL_NOT_APPLICABLE_TO_FROZEN_TASK')
        points.append(dict(value=value,parameters=parameters,model=plain(m),requirements=plain(req),
            initial_delta=None,source_reference=dict(reference=reference,pointer='/model'),construction_s=0.,
            context=dict(source_identity=c['source_identity'],
                topology_identity=digest([m.binding['coordinate_order'],m.binding['tendon_order']]),
                fixed_configuration_identity=digest(dict(task=cfg['task'],controller=cfg['policy']['controller'],
                    backend=cfg['policy']['backend'],dynamics=cfg['policy']['dynamics_model'])),
                construction_rule=query.operating_point)))
    origin=points[0]['value']; actual=sorted(p['value']-origin for p in points[1:])
    expected=sorted(v for h in request.steps for v in (-h,h))
    if any(not math.isclose(a,b,rel_tol=1e-10,abs_tol=0.) for a,b in zip(actual,expected)):
        raise ValueError('EXISTING_MODEL_VALUES_DO_NOT_MATCH_EXPLICIT_STENCIL')
    if family and (not all(model_identities) or len(set(model_identities))!=len(points)):
        raise ValueError('DISTINCT_GENERATED_MODEL_IDENTITIES_REQUIRED')
    parameter=parameter or dict(path=path,units='m' if path.endswith('length_m') else 'Pa',
        bounds=bounds,source='current frozen Study allowed_parameters',
        bounds_source=dict(study=host.run_id,resolved_identity=s['spec']['resolved_identity'],path=path))
    # T2 independently verifies coordinates, maps, coverage and task equality again.
    return dict(kind=SENSITIVITY,points=points,parameter=parameter,baseline=base_result)


def calculate_sensitivity(context, query, checkpoint=None):
    from schemas.platform_analysis import EndpointLinearizedModel, TaskAnalysisRequirement
    from extensions.math_analysis.capability_sensitivity import capability_sensitivity
    from tools.research.analysis import scoped_result
    points=[dict(p,model=EndpointLinearizedModel.model_validate(p['model']),
        requirements=TaskAnalysisRequirement.model_validate(p['requirements'])) for p in context['points']]
    events=[]
    def progress(kind,stage,detail):
        event=dict(kind=kind,stage=stage,detail=detail)
        events.append(event)
        if checkpoint:checkpoint('optimal_call_'+str(len(events)).zfill(3),event)
    sensitivity=capability_sensitivity(points,context['parameter'],query.protocol,progress=progress)
    base=context['baseline']
    result={k:deepcopy(base[k]) for k in ('binding','protocol','model','operating_point','limitations')}
    result.update(status='computed' if sensitivity['status']=='computed_diagnostic' else 'not_applicable',
        operation='task_capability',task_acceptance='unmeasured',optimal_sensitivity=sensitivity,
        numerical_call_events=events,
        internal_calculations=[dict(purpose=SENSITIVITY,**sensitivity.get('computation_cost',{}))],
        model_reuse=dict(count=len(points),new_model_builds=0,sources=sensitivity.get('source_references',[])))
    applicability=deepcopy(base['analysis_applicability'])
    if result['status']=='not_applicable':
        applicability.update(status='not_applicable',reasons=[sensitivity.get('reason','Controlled sensitivity unavailable')])
    result=scoped_result(result,points[0]['requirements'],applicability,query)
    return result
