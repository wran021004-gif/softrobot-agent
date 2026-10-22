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
    if any(not methods.get(m) for m in required):
        reasons.append('EXPLICIT_FROZEN_MATHEMATICAL_METHOD_AUTHORIZATION_REQUIRED')
    environment = dependencies()
    if not environment['available']:reasons.append('OPTIONAL_CVXPY_CLARABEL_UNAVAILABLE_IN_WORKER_PYTHON')
    if remaining < count:reasons.append('INSUFFICIENT_MATHEMATICAL_EVALUATIONS')
    return dict(status='not_applicable' if reasons else 'admissible', reasons=reasons,
        methods=required, expected_mathematical_evaluations=count, remaining_evaluations=remaining,
        model_builds=0 if query.optimal_sensitivity else 1,
        model_reuse=len(query.optimal_sensitivity.model_results) if query.optimal_sensitivity else 0,
        required_candidate=plain(query.candidate),
        required_model_results=[plain(r) for r in query.optimal_sensitivity.model_results] if query.optimal_sensitivity else [],
        capability_solves=len(query.optimal_sensitivity.model_results) if query.optimal_sensitivity else 1,
        dual_face_solves=2*len(query.optimal_sensitivity.steps) if query.optimal_sensitivity else 0,
        environment=environment, accounting='Reserve all planned solve attempts; failures and unused reserved attempts remain spent; receipt reuse costs zero.',
        alternatives=['Read existing registered evidence without a new solve.',
            'Request an already authorized SLSQP analysis if its budget fits.',
            'Obtain separately authorized candidate models, optional dependencies or a new Study grant.'])


def sensitivity_context(host, query):
    """Validate current owned models and one authorized continuous parameter."""
    from tools.research.design import verify_candidate, parameter_value, set_parameter
    from tools.research.task_constraints import describe_analysis_requirements, check_analysis_applicability, model_assessment
    from schemas.platform import SessionInput
    from schemas.platform_analysis import EndpointLinearizedModel
    s = state(host); request = query.optimal_sensitivity; path = request.variable
    if (len(path.split('.')) != 3 or not path.startswith('segments.')
            or path.split('.')[-1] not in ('length_m','young_pa')
            or path not in s['spec']['allowed_parameters']):
        raise ValueError('AUTHORIZED_CONTINUOUS_PARAMETER_REQUIRED')
    points=[]; base_candidate=None; base_result=None
    bounds=s['spec']['allowed_parameters'][path]
    for reference in map(plain,request.model_results):
        if reference not in s.get('analysis_results',[]):
            raise ValueError('REGISTERED_CURRENT_STUDY_MODEL_REQUIRED')
        raw=host.store.artifact(reference)
        c=verify_candidate(host,raw['candidate'])
        if (raw.get('implementation')!=s['freeze'] or raw.get('status')!='computed'
                or raw.get('protocol')!=plain(query.protocol) or not raw.get('model')
                or raw.get('requested_operation',{}).get('operating_point')!=query.operating_point):
            raise ValueError('CURRENT_IMPLEMENTATION_PROTOCOL_AND_OPERATING_POINT_REQUIRED')
        if base_candidate is None:
            base_candidate=c; base_result=raw
            if raw['candidate']!=plain(query.candidate):raise ValueError('BASELINE_CANDIDATE_MISMATCH')
        value=parameter_value(c['parameters'],path)
        for allowed,(lo,hi) in s['spec']['allowed_parameters'].items():
            current=parameter_value(c['parameters'],allowed)
            if not isinstance(current,(int,float)) or not math.isfinite(current) or not lo<=current<=hi:
                raise ValueError('CANDIDATE_PARAMETERS_OUTSIDE_CURRENT_STUDY_GRANT')
        if not isinstance(value,(int,float)) or not math.isfinite(value) or not bounds[0]<=value<=bounds[1]:
            raise ValueError('PARAMETER_OUTSIDE_CURRENT_STUDY_RANGE')
        expected=deepcopy(base_candidate['parameters']);set_parameter(expected,path,value)
        cfg=c['configuration']; base_cfg=base_candidate['configuration']
        if (expected!=c['parameters'] or c['source_identity']!=base_candidate['source_identity']
                or c['profile_identity']!=base_candidate['profile_identity'] or cfg['task']!=base_cfg['task']
                or any(cfg['policy'][k]!=base_cfg['policy'][k] for k in ('controller','backend','dynamics_model'))):
            raise ValueError('SINGLE_PARAMETER_FIXED_TASK_SOURCE_AND_MODEL_REQUIRED')
        m=EndpointLinearizedModel.model_validate(raw['model']); binding=raw['binding']
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
        points.append(dict(value=value,parameters=c['parameters'],model=plain(m),requirements=plain(req),
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
    parameter=dict(path=path,units='m' if path.endswith('length_m') else 'Pa',
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
