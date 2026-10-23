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
            grant['version']!='family_sensitivity_v1' or not isinstance(grant['variables'],list)
            or not grant['variables'] or any(not isinstance(v,str) for v in grant['variables'])
            or len(set(grant['variables']))!=len(grant['variables'])):
        raise ValueError('EXPLICIT_VERSIONED_FAMILY_SENSITIVITY_GRANT_REQUIRED')
    request=dict(family_space_identity=digest(space),segment_count=max(space['executable_segment_counts']),
        tendon_count=space['executable_tendon_count_bounds'][0])
    if space['version']=='serial_family_space_v2':request['version']='serial_family_generation_v2'
    domains={r['parameter_id']:r for r in parameter_capabilities(space,request)}
    for path in grant['variables']:
        if (not isinstance(path,str) or not re.fullmatch(r'segments\.(0|[1-9][0-9]*)\.(length_m|young_pa)',path)
                or path not in domains or domains[path]['minimum']>=domains[path]['maximum']):
            raise ValueError('EXECUTABLE_FAMILY_CONTINUOUS_DOMAIN_REQUIRED: '+str(path))
    return deepcopy(grant)


def family_parameters(spec, candidate, path):
    """Resolve sparse defaults, then verify the actual generator output, without solving."""
    from extensions.tendon_family.family_space import parse_build, parameter_capabilities
    from extensions.tendon_family.generated_serial import generate_family
    grant=spec.get('family_sensitivity_variables',{})
    if grant.get('version')!='family_sensitivity_v1' or path not in grant.get('variables',[]):
        raise ValueError('AUTHORIZED_FAMILY_CONTINUOUS_PARAMETER_REQUIRED')
    if candidate.get('generation_version') not in ('serial_family_generation_v1','serial_family_generation_v2'):
        raise ValueError('CURRENT_GENERATED_FAMILY_CANDIDATE_REQUIRED')
    build=parse_build(dict(space=spec['family_space'],request=candidate['parameters']))
    params=plain(build.request)
    domains={r['parameter_id']:r for r in parameter_capabilities(spec['family_space'],params)}
    if path not in domains:raise ValueError('PARAMETER_NOT_IN_CURRENT_CANDIDATE_TOPOLOGY')
    for i in range(params['segment_count']):
        choice=params['segments'].setdefault(str(i),{})
        for key in ('length_m','young_pa'):
            if choice.get(key) is None:choice[key]=domains[f'segments.{i}.{key}']['default']
        # Parse omitted and explicit segments identically, including optional fields.
    params=plain(parse_build(dict(space=spec['family_space'],request=params)).request)
    robot,mesh,_=generate_family(build)
    cfg=candidate['configuration']
    if (robot!=cfg['robot']['structure']['data'] or mesh!=cfg['policy']['discretization']['data']
            or cfg['policy']['candidate_builder']['parameters']['data']!=plain(build)):
        raise ValueError('GENERATED_CONFIGURATION_DOES_NOT_MATCH_FROZEN_REQUEST')
    domain=domains[path];index=path.split('.')[1]
    source=('segment_domains.'+index if index in spec['family_space']['segment_domains'] else 'segment_domain')
    return params,dict(path=path,units=domain['unit'],bounds=[domain['minimum'],domain['maximum']],
        source='current frozen FamilySpace continuous domain',bounds_source=dict(
            family_space_identity=spec['family_space_identity'],path=source+'.'+path.split('.')[-1]))


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


def method_admission(spec, query, used=0):
    methods = spec.get('mathematical_methods', {})
    required = [CONIC] + ([SENSITIVITY] if query.optimal_sensitivity else [])
    count = 1 + 4*len(query.optimal_sensitivity.steps) if query.optimal_sensitivity else 2
    remaining = max(0, spec['budgets']['mathematical_evaluations']-used)
    reasons = []
    if spec.get('canonical_task',{}).get('family')=='task.tracking':
        reasons.append('TRACKING_ROBOT_MODEL_CONSTRUCTION_UNSUPPORTED')
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
        capability_solves=len(query.optimal_sensitivity.model_results) if query.optimal_sensitivity else 1,
        dual_face_solves=2*len(query.optimal_sensitivity.steps) if query.optimal_sensitivity else 0,
        environment=environment, accounting='Reserve all planned solve attempts; failures and unused reserved attempts remain spent; receipt reuse costs zero.',
        alternatives=['Read existing registered evidence without a new solve.',
            'Request an already authorized SLSQP analysis if its budget fits.',
            'Obtain separately authorized candidate models, optional dependencies or a new Study grant.'])


def sensitivity_cost(steps, reused, remaining, *, conic_authorized=False):
    """Planning only: reuse counts must come from validated complete stencils."""
    required=1+2*steps;kernel=1+4*steps
    missing=None if reused is None else required-reused
    methods=[dict(operation='linearization',evaluations=1)]
    if conic_authorized:methods.append(dict(operation='task_capability',method=CONIC,evaluations=2))
    totals=[kernel+missing*m['evaluations'] for m in methods] if missing is not None else None
    return dict(required_models=required,validated_reusable_models=reused,missing_models=missing,
        kernel_evaluations=kernel,preparation_methods=methods,remaining_total_range=totals,
        budget_sufficient=None if totals is None else remaining>=max(totals),
        wall_cost='unknown',other_budgets='Candidate generation, Provider and physical launches are separate.',
        assumptions='Preparation methods require their own task/model admission; no automatic generation or solve.')


def candidate_methods(host, reference):
    """Candidate-specific discovery; executable T2 uses the same saved-context gate."""
    from tools.research.design import verify_candidate, parameter_value
    from tools.research.contracts import AnalysisRequest
    s=state(host);spec=s['spec'];candidate=verify_candidate(host,reference)
    methods=spec.get('mathematical_methods',{});remaining=max(0,spec['budgets']['mathematical_evaluations']-s.get('mathematical_evaluations',0))
    variables=(spec.get('family_sensitivity_variables',{}).get('variables',[]) if spec.get('start_mode')=='family_space'
        else [p for p in spec['allowed_parameters'] if p.endswith(('.length_m','.young_pa'))])
    rows=[]
    for variable in variables:
        row=dict(variable=variable,status='missing_models',ready_stencils=[],rejections=[])
        models=[]
        for ref in s.get('analysis_results',[]):
            raw=host.store.artifact(ref)
            if (raw.get('status')!='computed' or raw.get('implementation')!=s['freeze'] or not raw.get('model')
                    or raw.get('protocol')!=spec['analysis_protocol']):continue
            try:
                c=verify_candidate(host,raw['candidate'])
                p=family_parameters(spec,c,variable)[0] if spec.get('start_mode')=='family_space' else c['parameters']
                models.append((ref,raw,parameter_value(p,variable)))
            except (ValueError,KeyError):continue
        try:
            if spec.get('start_mode')=='family_space':family_parameters(spec,candidate,variable)
        except ValueError as exc:row.update(status='not_applicable',reason=str(exc))
        for base,raw,origin in models:
            if raw['candidate']!=plain(reference):continue
            # Discover only already registered symmetric groups. No candidate/model creation.
            for plus,_,value in models:
                h=value-origin
                if h<=0:continue
                for k in (1,2):
                    steps=[h] if k==1 else [h,h/2]
                    refs=[base]
                    for offset in [v for step in steps for v in (-step,step)]:
                        match=next((r for r,_,v in models if math.isclose(v-origin,offset,rel_tol=1e-10,abs_tol=0.)),None)
                        if match is not None:refs.append(match)
                    if len(refs)!=1+2*k:continue
                    try:
                        query=AnalysisRequest.model_validate(dict(candidate=reference,operation='task_capability',
                            operating_point=raw['requested_operation']['operating_point'],protocol=spec['analysis_protocol'],
                            capability_method=CONIC,optimal_sensitivity=dict(variable=variable,steps=steps,model_results=refs)))
                        sensitivity_context(host,query)
                        fit=method_admission(spec,query,s.get('mathematical_evaluations',0))
                        row['ready_stencils'].append(dict(request=plain(query),admission=fit,
                            cost=sensitivity_cost(k,len(refs),remaining,conic_authorized=bool(methods.get(CONIC)))))
                    except (ValueError,KeyError) as exc:
                        if str(exc) not in row['rejections']:row['rejections'].append(str(exc))
        if row['ready_stencils']:
            row['status']='executable' if any(v['admission']['status']=='admissible' for v in row['ready_stencils']) else 'not_applicable'
        rows.append(row)
    reasons=[]
    if not all(methods.get(m) for m in (CONIC,SENSITIVITY)):reasons.append('method_not_authorized')
    if not dependencies()['available']:reasons.append('worker_dependency_unavailable')
    if remaining<5:reasons.append('insufficient_budget')
    if not variables:reasons.append('no_authorized_continuous_variable')
    if not any(r['ready_stencils'] for r in rows):reasons.append('missing_validated_model_stencil')
    return dict(method=SENSITIVITY,status='executable' if not reasons and any(r['status']=='executable' for r in rows) else 'not_applicable',
        reasons=reasons,variables=rows,remaining_evaluations=remaining,
        planning=[sensitivity_cost(k,None,remaining,conic_authorized=bool(methods.get(CONIC))) for k in (1,2)],
        from_zero_examples=[sensitivity_cost(k,0,remaining,conic_authorized=bool(methods.get(CONIC))) for k in (1,2)])


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
    if (len(path.split('.')) != 3 or not path.startswith('segments.')
            or path.split('.')[-1] not in ('length_m','young_pa')
            or (not family and path not in s['spec']['allowed_parameters'])):
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
        applicability=check_analysis_applicability(req,query,model_assessment(inp,req,query.operation),model=m)
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
