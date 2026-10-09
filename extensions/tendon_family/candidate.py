"""Bounded typed edits or complete frozen templates; no executable edit strings."""
from copy import deepcopy
import math
from .contracts import Design, Discretization, BuildRequest, BuildResult
from .compiler import normalize_inputs, resolve, Unsupported

REACH_WEIGHT_PATHS = ('control/recipe/terminal_tip_speed_weight',
                      'control/recipe/holding_tip_speed_weight')


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
        specs = (space.control_parameters if normalized.startswith('control/') else
                 space.model_parameters if normalized.startswith('model/') else
                 space.discretization_parameters if normalized.startswith('discretization/') else space.parameters)
        spec = specs.get(normalized)
        if spec is None and not normalized.startswith('model/'):
            spec = space.parameters.get(key)  # Legacy physical/discretization aliases.
        if spec is None: raise ValueError('PARAMETER_NOT_AUTHORIZED: '+key)
        if normalized in REACH_WEIGHT_PATHS and inp is not None and key not in inp.policy.editable:
            raise ValueError('PARAMETER_NOT_AUTHORIZED: '+key)
        check_value(key, value, spec, inp.policy.editable if inp is not None else {})
        if normalized in REACH_WEIGHT_PATHS:
            if not 0 <= value <= 1 or 0 < value < .0001:
                raise ValueError('REACH_WEIGHT_REQUIRES_ZERO_OR_0001_TO_1: '+key)


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


def candidate_facts(baseline, configuration, reference, candidate_id, owner_run_id=None, execution_id=None):
    """Project declared paths from frozen input and effective input, never labels/prose."""
    from tools.platform_store import plain
    from tools.state_io import digest
    baseline = plain(baseline)
    effective = configuration.get('effective', configuration)  # CandidateInput is a wrapper.
    space = baseline['policy']['candidate_builder']['parameters']['data']

    def value(inp, path):
        path = canonical_path(path)
        if baseline['policy']['candidate_builder'].get('version')=='2.0.0':
            from tools.candidate_parameters import parameter_value
            return parameter_value(inp,path)
        if path in space.get('semantic_decisions', {}):
            return inp['robot']['structure']['data'].get('metadata', {}).get('design_decisions', {}).get('selections', {}).get(path, space['semantic_decisions'][path]['baseline_value'])
        for prefix, field in (('control/', 'controller'), ('model/', 'dynamics_model')):
            if path.startswith(prefix):
                return read_parameter(inp['policy'][field]['parameters']['data'], path[len(prefix):])
        if path.startswith('discretization/'):
            return read_parameter(inp['policy']['discretization']['data'], path[len('discretization/'):])
        return read_parameter(inp['robot']['structure']['data'], path)

    parameters = []
    for group in ('parameters', 'control_parameters', 'model_parameters', 'discretization_parameters'):
        for path, spec in space.get(group, {}).items():
            values = {}
            for label, inp in (('baseline_value', baseline), ('effective_value', effective)):
                try:
                    active = all(value(inp, p) == v for p, v in spec.get('when', {}).items())
                    values[label] = value(inp, path) if active else None
                except ValueError:  # A complete template can remove an entity/path.
                    values[label] = None
            before, after = values.values()
            numeric = all(isinstance(v, (float, int)) and not isinstance(v, bool) for v in (before, after))
            unit = spec.get('unit', spec.get('units'))
            if unit is None:
                # Existing physical fields encode SI units in their names.
                unit = next((u for suffix, u in (('_rad_m', 'rad/m'), ('_m_s', 'm/s'),
                    ('_m', 'm'), ('_s', 's'), ('_rad', 'rad'), ('_pa', 'Pa'), ('_kg', 'kg'), ('_n', 'N'))
                    if path.lower().endswith(suffix)), None)
            parameters.append(dict(path=path, **values, baseline_delta=after-before if numeric else None, unit=unit))
    extra = {}
    if baseline['policy']['candidate_builder'].get('version')=='2.0.0':
        from .finite_templates import template_id
        from .design_decisions import physical_summary
        design=effective['robot']['structure']['data']
        extra=dict(template=template_id(design),physical_summary=physical_summary(design,effective['policy']['discretization']['data']),
            topology_changes=dict(before_components=[c['id'] for c in baseline['robot']['structure']['data']['components']],
                after_components=[c['id'] for c in design['components']],
                before_tendons=[t['id'] for t in baseline['robot']['structure']['data']['tendons']],
                after_tendons=[t['id'] for t in design['tendons']]))
    elif space.get('semantic_decisions'):
        from .design_decisions import physical_effects, physical_summary
        design = effective['robot']['structure']['data']
        effects = physical_effects(space['semantic_source'], design)
        extra = dict(physical_changes=effects, semantic_provenance=design.get('metadata', {}).get('design_decisions'),
            physical_summary=physical_summary(design, effective['policy']['discretization']['data']),
            multi_category_coverage=bool(any(r['category']=='length' and abs(r['baseline_delta'])>=.001-1e-12 for r in effects)
                and any(r['path']=='design/section_scale' and abs(r['baseline_delta'])>=.01-1e-12 for r in parameters)
                and any(r['path']=='design/material_scenario' and r['effective_value']!='baseline' for r in parameters)))
    return dict(**extra, candidate_id=candidate_id, configuration=plain(reference),
        frozen_baseline_identity=digest(baseline), effective_identity=digest(effective),
        owner_run_id=owner_run_id, execution_id=execution_id, parameters=parameters)


def experiment_coverage(facts):
    """Fixed multi-category experiment rule, derived from effective facts."""
    values={row['path']:row['effective_value'] for row in facts['parameters']}
    checks=dict(length=any(isinstance(values.get(path),(int,float)) and
        abs(values[path]-baseline)>=.001-1e-12 for path,baseline in
        (('components/near/length_m',.16),('components/far/length_m',.12))),
        section=isinstance(values.get('design/section_scale'),(int,float)) and
            abs(values['design/section_scale']-1.)>=.01-1e-12,
        material=values.get('design/material_scenario') in ('compliant','stiff'))
    return dict(required=True,eligible=all(checks.values()),checks=checks)


def check_design_statement(facts, statement):
    """Structured interpretation only; a prose review remains independently required."""
    if statement is None:
        return dict(status='not_supplied', accepted=False, mismatches=[])
    mismatches = []
    for key in ('candidate_id', 'configuration', 'owner_run_id', 'execution_id'):
        if statement.get(key) != facts.get(key):
            mismatches.append(key)
    if 'physical_changes' in facts:
        physical_check=check_design_statement(dict(parameters=facts['physical_changes']),
            dict(parameters=statement.get('physical_changes',[])))
        if not physical_check['accepted']:
            mismatches.append('physical_changes')
    rows = statement.get('parameters', [])
    actual = {r.get('path'): r for r in rows if isinstance(r, dict)}
    if len(actual) != len(rows) or set(actual) != {r['path'] for r in facts['parameters']}:
        mismatches.append('parameter_paths')
    for expected in facts['parameters']:
        row = actual.get(expected['path'], {})
        for key in ('baseline_value', 'effective_value', 'baseline_delta', 'unit'):
            a, b = expected[key], row.get(key)
            numeric = all(isinstance(v, (float, int)) and not isinstance(v, bool) for v in (a, b))
            equal = math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12) if numeric else type(a) is type(b) and a == b
            if key not in row or not equal:
                mismatches.append(expected['path'] + ':' + key)
    return dict(status='matched' if not mismatches else 'mismatch', accepted=not mismatches, mismatches=mismatches)


def validate_final(data,discretization,space,changes,task_bounds):
    specifications = {canonical_path(k):v for k,v in space.parameters.items()}
    specifications.update({canonical_path(k):v for k,v in space.discretization_parameters.items()})
    normalized_task = {canonical_path(k):v for k,v in task_bounds.items()}
    normalized_changes = {canonical_path(k):v for k,v in changes.items()}
    for path in dict.fromkeys([*specifications,*normalized_task]):
        if path in space.semantic_decisions: continue
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


def build(value, *, task_bounds=None, semantic_expander=None):
    req = BuildRequest.model_validate(value)
    authorize(None,req.space,req.changes)
    if any(path.startswith('model/') for path in req.changes):
        raise ValueError('MODEL_PARAMETER_REQUIRES_SESSION_CANDIDATE: use candidate.family with dynamics_model binding')
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
            if path == 'template' or path in req.space.semantic_decisions: continue
            path = canonical_path(path)
            target = discretization if path.startswith('discretization/') else data
            local_path = path.removeprefix('discretization/')
            obj,key = locate(target,local_path)
            old = obj[int(key)] if isinstance(obj,list) else obj[key]
            if isinstance(obj,list): obj[int(key)] = value
            else: obj[key] = value
            summary.append(dict(operation='set',path=path,before=old,after=value))
        from .design_decisions import expand
        (semantic_expander or expand)(data, req.space, req.changes)
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


def apply(inp, parameters, changes, *, semantic_expander=None):
    explicit = inp.policy.discretization.data if inp.policy.discretization is not None else None
    design_changes={k:v for k,v in changes.items() if not k.startswith(('control/','model/'))}
    design_bounds={k:v for k,v in inp.policy.editable.items() if not k.startswith(('control/','model/'))}
    result = build(dict(baseline=inp.robot.structure.data,space=parameters,discretization=explicit,changes=design_changes),task_bounds=design_bounds,
        semantic_expander=semantic_expander)
    if result.status != 'valid': raise ValueError(result.status.upper()+': '+str(result.reason))
    from .contracts import Control, GVSLQRControl
    from .contracts import GVSTrajectoryParameters
    from .gvs_profile import ProfileControl, ReachControl
    from .tracking import TrackingControl
    control_type=({'1.0.0':GVSTrajectoryParameters,'2.0.0':ProfileControl,'3.0.0':ReachControl,'4.0.0':ReachControl,'5.0.0':TrackingControl,'6.0.0':ReachControl,'7.0.0':ReachControl,'8.0.0':ReachControl,'9.0.0':ReachControl,'10.0.0':ReachControl,'11.0.0':ReachControl}[inp.policy.controller.version]
        if inp.policy.controller.extension_id=='controller.gvs_nmpc' else
        GVSLQRControl if inp.policy.controller.extension_id in ('controller.gvs_lqr','controller.gvs_sampled_lqr') else Control)
    control=control_type.model_validate(inp.policy.controller.parameters.data).model_dump(mode='json')
    for path,value in changes.items():
        if path.startswith('control/'):
            if control_type is ReachControl and path in REACH_WEIGHT_PATHS:
                if path not in inp.policy.editable or path not in parameters.control_parameters:
                    raise ValueError('PARAMETER_NOT_AUTHORIZED: '+path)
                check_value(path,value,parameters.control_parameters[path],inp.policy.editable)
                if not 0 <= value <= 1 or 0 < value < .0001:
                    raise ValueError('REACH_WEIGHT_REQUIRES_ZERO_OR_0001_TO_1: '+path)
                control['recipe'][path.rsplit('/',1)[1]]=value
                continue
            key=path.removeprefix('control/')
            allowed=(('curvature_weight','state_rate_weight','tendon_tension_weight')
                if control_type is GVSLQRControl else ('feedback_gain','damping','max_joint_update_rad','ramp_s'))
            if key not in allowed:
                raise ValueError('CONTROL_PARAMETER_UNSUPPORTED: '+path)
            control[key]=value
    for path,spec in parameters.control_parameters.items():
        check_value(path,read_parameter(control,path.removeprefix('control/')),spec,inp.policy.editable)
    if parameters.model_parameters:
        if inp.policy.dynamics_model is None:
            raise ValueError('MODEL_PARAMETER_REQUIRES_EXPLICIT_MODEL')
        model_data=deepcopy(inp.policy.dynamics_model.parameters.data)
        for path,value in changes.items():
            if path.startswith('model/'):
                obj,key=locate(model_data,path.removeprefix('model/'))
                if isinstance(obj,list): obj[int(key)]=value
                else: obj[key]=value
        for path,spec in parameters.model_parameters.items():
            check_value(path,read_parameter(model_data,path.removeprefix('model/')),spec,inp.policy.editable)
        inp.policy.dynamics_model.parameters.data.clear()
        inp.policy.dynamics_model.parameters.data.update(model_data)
    inp.policy.controller.parameters.data.clear()
    inp.policy.controller.parameters.data.update(control_type.model_validate(control).model_dump(mode='json'))
    inp.robot.structure.data.clear(); inp.robot.structure.data.update(result.candidate.model_dump(mode='json'))
    from schemas.platform import Payload
    model = Payload(contract='family.discretization',data=result.discretization.model_dump(mode='json'))
    return inp.model_copy(update={'policy':inp.policy.model_copy(update={'discretization':model})})


def build_tool(ctx, args):
    return build(args,task_bounds=ctx.input.policy.editable)
