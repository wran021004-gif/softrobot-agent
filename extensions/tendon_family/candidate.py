"""Bounded typed edits or complete frozen templates; no executable edit strings."""
from copy import deepcopy
import math
from .contracts import Design, BuildRequest, BuildResult
from .compiler import resolve, Unsupported


def authorize(inp, space, changes):
    for key,value in changes.items():
        if key == 'template':
            if not isinstance(value,str) or value not in space.templates: raise ValueError('TEMPLATE_NOT_AUTHORIZED')
            continue
        spec = space.parameters.get(key)
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


def validate_final(data,space,changes,task_bounds):
    for path in dict.fromkeys([*space.parameters,*task_bounds]):
        spec = space.parameters.get(path,dict(type='number',bounds=task_bounds.get(path)))
        active = True
        for dependency,expected in spec.get('when',{}).items():
            try:
                active = active and read_parameter(data,dependency) == expected
            except ValueError:
                active = False
        if not active:
            if path in changes: raise ValueError('CONDITIONAL_PARAMETER_INACTIVE: '+path)
            continue
        check_value(path,read_parameter(data,path),spec,task_bounds)


def build(value, *, task_bounds=None):
    req = BuildRequest.model_validate(value)
    authorize(None,req.space,req.changes)
    design = req.space.templates[req.changes['template']] if 'template' in req.changes else req.baseline
    data = deepcopy(design.model_dump(mode='json')); summary = []
    if 'template' in req.changes:
        summary.append(dict(operation='complete_template',template=req.changes['template'],defaults='entire explicit template saved in candidate'))
    try:
        for path,value in req.changes.items():
            if path == 'template': continue
            obj,key = locate(data,path)
            old = obj[int(key)] if isinstance(obj,list) else obj[key]
            if isinstance(obj,list): obj[int(key)] = value
            else: obj[key] = value
            summary.append(dict(operation='set',path=path,before=old,after=value))
        validate_final(data,req.space,req.changes,task_bounds or {})
        candidate = Design.model_validate(data)
        physics = resolve(candidate)
        return BuildResult(status='valid',candidate=candidate,summary=summary,resolved_physics=physics,applicability=physics['applicability'])
    except Unsupported as exc:
        return BuildResult(status='backend_unsupported',candidate=Design.model_validate(data),summary=summary,reason=str(exc))
    except (ValueError,KeyError,IndexError,StopIteration) as exc:
        return BuildResult(status='physically_invalid',summary=summary,reason=str(exc))


def apply(inp, parameters, changes):
    result = build(dict(baseline=inp.robot.structure.data,space=parameters,changes=changes),task_bounds=inp.policy.editable)
    if result.status != 'valid': raise ValueError(result.status.upper()+': '+str(result.reason))
    inp.robot.structure.data.clear(); inp.robot.structure.data.update(result.candidate.model_dump(mode='json'))
    return inp


def build_tool(ctx, args):
    return build(args,task_bounds=ctx.input.policy.editable)
