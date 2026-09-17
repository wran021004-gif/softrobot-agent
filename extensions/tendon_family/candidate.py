"""Bounded typed edits or complete frozen templates; no executable edit strings."""
from copy import deepcopy
import math
from .contracts import Design, Discretization, BuildRequest, BuildResult
from .compiler import normalize_inputs, resolve, Unsupported


def canonical_path(path):
    parts = path.split('/')
    if len(parts) == 3 and parts[0] == 'components' and parts[2] == 'cells':
        return 'discretization/cells/' + parts[1]
    return path


def authorize(inp, space, changes):
    for key,value in changes.items():
        if key == 'template':
            if not isinstance(value,str) or value not in space.templates: raise ValueError('TEMPLATE_NOT_AUTHORIZED')
            continue
        normalized = canonical_path(key)
        specs = space.discretization_parameters if normalized.startswith('discretization/') else space.parameters
        spec = specs.get(normalized) or space.parameters.get(key)
        if spec is None: raise ValueError('PARAMETER_NOT_AUTHORIZED: '+key)
        check_value(key, value, spec, inp.policy.editable if inp is not None else {})


def check_value(key, value, spec, task_bounds):
    kind = spec.get('type')
    if kind in ('number','integer'):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value): raise ValueError('NUMBER_REQUIRED: '+key)
        if kind == 'integer' and not isinstance(value,int): raise ValueError('INTEGER_REQUIRED: '+key)
        lo,hi = spec['bounds']
        if not lo <= value <= hi: raise ValueError('PARAMETER_OUT_OF_BOUNDS: '+key)
    elif kind == 'choice':
        if value not in spec['options']: raise ValueError('OPTION_NOT_AUTHORIZED: '+key)
    else: raise ValueError('UNKNOWN_SPACE_PARAMETER_TYPE: '+str(kind))
    if key in task_bounds:
        lo,hi = task_bounds[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('TASK_PARAMETER_OUT_OF_BOUNDS: '+key)


def locate(data,path):
    keys = path.split('/')
    obj = data
    for key in keys[:-1]:
        obj = next(x for x in obj if x['id'] == key) if isinstance(obj,list) and not key.isdigit() else obj[int(key)] if isinstance(obj,list) else obj[key]
    return obj, keys[-1]


def read_parameter(data,path):
    try:
        obj,key = locate(data,path)
        return obj[int(key)] if isinstance(obj,list) else obj[key]
    except (KeyError,IndexError,StopIteration,TypeError) as exc:
        raise ValueError('CONSTRAINED_PARAMETER_MISSING: '+path) from exc


def validate_final(data,discretization,space,changes,task_bounds):
    specifications = {canonical_path(k):v for k,v in space.parameters.items()}
    specifications.update({canonical_path(k):v for k,v in space.discretization_parameters.items()})
    normalized_task = {canonical_path(k):v for k,v in task_bounds.items()}
    normalized_changes = {canonical_path(k):v for k,v in changes.items()}
    for path in dict.fromkeys([*specifications,*normalized_task]):
        spec = specifications.get(path,dict(type='number',bounds=normalized_task.get(path)))
        target = discretization if path.startswith('discretization/') else data
        local_path = path.removeprefix('discretization/')
        if local_path.startswith('cells/') and local_path.split('/',1)[1] not in discretization.get('cells',{}):
            if path in normalized_changes:
                raise ValueError('DISCRETIZATION_SEGMENT_INACTIVE: '+path)
            continue
        active = True
        for dependency,expected in spec.get('when',{}).items():
            try:
                dependency_target = discretization if dependency.startswith('discretization/') else data
                active = active and read_parameter(dependency_target,dependency.removeprefix('discretization/')) == expected
            except ValueError:
                active = False
        if not active:
            if path in normalized_changes: raise ValueError('CONDITIONAL_PARAMETER_INACTIVE: '+path)
            continue
        check_value(path,read_parameter(target,local_path),spec,normalized_task)


def build(value, *, task_bounds=None):
    req = BuildRequest.model_validate(value)
    authorize(None,req.space,req.changes)
    template = req.changes.get('template')
    design = req.space.templates[template] if template else req.baseline
    # Select the complete entity structure before validating its mesh. A
    # structure-changing template owns a complete mesh, or the request must
    # explicitly provide one matching the final segment IDs.
    selected_discretization = req.space.template_discretizations.get(template) if template else req.discretization
    if template and selected_discretization is None:
        selected_discretization = req.discretization
    design, base_discretization, compatibility = normalize_inputs(design,selected_discretization)
    data = deepcopy(design.model_dump(mode='json')); discretization = deepcopy(base_discretization.model_dump(mode='json')); summary = []
    source = compatibility
    if template:
        source = 'space.template_discretizations.'+template if template in req.space.template_discretizations else compatibility
        summary.append(dict(operation='complete_template',template=template,
            defaults='entire explicit template saved in candidate',discretization_source=source,
            baseline_discretization_reused=template not in req.space.template_discretizations))
    try:
        for path,value in req.changes.items():
            if path == 'template': continue
            path = canonical_path(path)
            target = discretization if path.startswith('discretization/') else data
            local_path = path.removeprefix('discretization/')
            obj,key = locate(target,local_path)
            old = obj[int(key)] if isinstance(obj,list) else obj[key]
            if isinstance(obj,list): obj[int(key)] = value
            else: obj[key] = value
            summary.append(dict(operation='set',path=path,before=old,after=value))
        validate_final(data,discretization,req.space,req.changes,task_bounds or {})
        candidate = Design.model_validate(data)
        model = Discretization.model_validate(discretization)
        physics = resolve(candidate,model)
        return BuildResult(status='valid',candidate=candidate,discretization=model,summary=summary,resolved_physics=physics,
            applicability=physics['applicability'],source_roles=dict(entity_design='baseline or selected complete template',
                physical_inputs='candidate component physics and tendon declarations',model_discretization=source))
    except Unsupported as exc:
        return BuildResult(status='backend_unsupported',candidate=Design.model_validate(data),summary=summary,reason=str(exc))
    except (ValueError,KeyError,IndexError,StopIteration) as exc:
        return BuildResult(status='physically_invalid',summary=summary,reason=str(exc))


def apply(inp, parameters, changes):
    explicit = inp.policy.discretization.data if inp.policy.discretization is not None else None
    result = build(dict(baseline=inp.robot.structure.data,space=parameters,discretization=explicit,changes=changes),task_bounds=inp.policy.editable)
    if result.status != 'valid': raise ValueError(result.status.upper()+': '+str(result.reason))
    inp.robot.structure.data.clear(); inp.robot.structure.data.update(result.candidate.model_dump(mode='json'))
    from schemas.platform import Payload
    model = Payload(contract='family.discretization',data=result.discretization.model_dump(mode='json'))
    return inp.model_copy(update={'policy':inp.policy.model_copy(update={'discretization':model})})


def build_tool(ctx, args):
    return build(args,task_bounds=ctx.input.policy.editable)
