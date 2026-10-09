"""Canonical builder parameter resolution shared by planning and scheduling."""
from copy import deepcopy
from extensions.tendon_family.candidate import canonical_path, read_parameter, locate
from tools.state_io import digest

STRUCTURAL_PATHS=('components/near/length_m','components/far/length_m','design/section_scale','design/material_scenario')


def parameter_value(effective,path):
    path=canonical_path(path)
    space=effective['policy']['candidate_builder']['parameters']['data']
    if effective['policy']['candidate_builder'].get('version')=='3.0.0':
        recipe=space['recipe']
        if path in recipe:return recipe[path]
        if path=='tendon_count' or path=='actuator_count':return recipe['proximal_tendons']+recipe['distal_tendons']
        if path.startswith('length/'):
            index=int(path.split('/')[1])
            if index>=recipe['segment_count']:raise ValueError('INACTIVE_LENGTH_COORDINATE')
            return recipe['lengths_m'][index]
    if effective['policy']['candidate_builder'].get('version')=='2.0.0':
        from extensions.tendon_family.finite_templates import template_id
        if path=='template':return template_id(effective['robot']['structure']['data'])
        if path.startswith('design/'):
            return effective['robot']['structure']['data'].get('metadata',{}).get('v2_selections',{}).get(
                path,'baseline' if path.endswith('material_scenario') else 1.)
    selections=effective['robot']['structure']['data'].get('metadata',{}).get('design_decisions',{}).get('selections',{})
    if path in selections:return selections[path]
    if path in space.get('semantic_decisions',{}):
        builder=effective['policy']['candidate_builder']
        decision=space['semantic_decisions'][path]
        if builder.get('extension_id')=='candidate.family' and builder.get('version') in ('1.1.0','1.2.0'):
            common='design/'+decision['operation']
            if common in selections:return selections[common]
        return effective['robot']['structure']['data'].get('metadata',{}).get('design_decisions',{}).get('selections',{}).get(
            path,space['semantic_decisions'][path]['baseline_value'])
    for prefix,field in (('control/','controller'),('model/','dynamics_model')):
        if path.startswith(prefix):return read_parameter(effective['policy'][field]['parameters']['data'],path[len(prefix):])
    if path.startswith('discretization/'):return read_parameter(effective['policy']['discretization']['data'],path[15:])
    return read_parameter(effective['robot']['structure']['data'],path)


def fixed_configuration(effective,variables):
    fixed=deepcopy(effective)
    design=fixed['robot']['structure']['data'];space=fixed['policy']['candidate_builder']['parameters']['data']
    if fixed['policy']['candidate_builder'].get('version')=='2.0.0':
        from extensions.tendon_family.finite_templates import selected_space
        from schemas.platform import SessionInput
        _,selected=selected_space(SessionInput.model_validate(effective),space,{})
        space=selected.model_dump(mode='json')
        # Selection bookkeeping is derived from the physical design. Physical
        # locations below, rather than metadata, enforce the fixed conditions.
        design.get('metadata',{}).pop('v2_selections',None)
    if space.get('semantic_decisions') or any(p.startswith('design/') for p in variables):
        design.get('metadata',{}).pop('design_decisions',None)
    for path in variables:
        if path=='template':
            fixed['robot']['structure']['data']='<complete finite template variable>'
            fixed['policy']['discretization']='<template-owned mesh variable>'
            fixed['task']['initializer']='<template-owned named initialization variable>'
            continue
        decision=space.get('semantic_decisions',{}).get(path,{})
        if path in ('design/section_scale','design/material_scenario') or decision:
            components=decision.get('components',['near','far'])
            operation=decision.get('operation',path.removeprefix('design/'))
            for c in design['components']:
                if c['id'] not in components:continue
                if operation=='section_scale':
                    for station in c['sections']:
                        station['section']['parameters']={k:'<batch variable>' for k in station['section']['parameters']}
                elif operation=='material_scenario':c['physics']['young_pa']='<batch variable>'
            if operation=='routing_radius_scale':
                from extensions.tendon_family.routing_radius import locations
                for row in locations(space['semantic_source']):
                    if row['owner'] not in components:continue
                    obj,key=locate(design,row['path'])
                    value=obj[int(key)] if isinstance(obj,list) else obj[key]
                    replacement=[value[0],'<batch variable>','<batch variable>']
                    obj[int(key) if isinstance(obj,list) else key]=replacement
        else:
            target=fixed['policy']['controller']['parameters']['data'] if path.startswith('control/') else design
            obj,key=locate(target,path[8:] if path.startswith('control/') else path)
            if isinstance(obj,list):obj[int(key)]='<batch variable>'
            else:obj[key]='<batch variable>'
    return fixed


def actual_parameter_changes(before,after,paths):
    return [dict(path=p,before=parameter_value(before,p),after=parameter_value(after,p))
            for p in paths if parameter_value(before,p)!=parameter_value(after,p)]


def scientific_fixed_scope(effective,variables):
    from extensions.tendon_family.gvs_profile import execution_scope
    scope=execution_scope(effective);masked=fixed_configuration(effective,variables)
    scope['robot']['identity']=digest(masked['robot']);scope['controller']=masked['policy']['controller']
    if 'template' in variables:
        scope['discretization']=masked['policy']['discretization']
        scope['task']['identity']=digest(masked['task'])
        scope['task']['initializer']=digest(masked['task']['initializer'])
    return scope


def comparison_scope(effective):
    from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS
    builder=effective['policy']['candidate_builder']
    if builder.get('version')=='3.0.0':
        from extensions.tendon_family.gvs_profile import execution_scope
        return execution_scope(effective)  # Exact generated recipe; no historical rebinding.
    if builder.get('extension_id')=='candidate.family' and builder.get('version') in ('1.1.0','1.2.0','2.0.0'):
        from tools.parameter_catalog import effective_catalog
        return scientific_fixed_scope(effective,effective_catalog(effective)['usable_pool'])
    return scientific_fixed_scope(effective,[*STRUCTURAL_PATHS,*REACH_WEIGHT_PATHS])


def planning_configuration(store,candidate,policy):
    """Add current authorized builder capabilities; preserve archived scientific input."""
    return project_planning_configuration(store.artifact(candidate['configuration'])['effective'],policy)


def project_planning_configuration(original,policy):
    """Shared source projection for archived planning and the fixed study runner."""
    effective=deepcopy(original)
    if policy.get('candidate_builder',{}).get('version')=='3.0.0':
        if original['policy']['candidate_builder'].get('version')!='3.0.0':
            raise ValueError('HISTORICAL_GENERATOR_REBINDING_FORBIDDEN_USE_REASONING_EVIDENCE')
        return effective
    current=policy.get('candidate_builder',{}).get('parameters',{}).get('data',{})
    builder=policy.get('candidate_builder',{})
    if builder.get('extension_id')=='candidate.family' and builder.get('version')=='2.0.0':
        from extensions.tendon_family.finite_templates import check_robot
        check_robot(original['robot']['structure']['data'],original['policy']['discretization']['data'])
        effective['policy']['candidate_builder']=deepcopy(builder)
        effective['policy']['editable']=deepcopy(policy['editable'])
        # Controller 9 evidence remains historical. Only future preparation
        # adopts the explicitly authorized V10 compatibility envelope, whose
        # numerical recipe must be identical to the original recipe.
        old=original['policy']['controller'];current_controller=policy['controller']
        if old['extension_id']!=current_controller['extension_id'] or old['version'] not in ('9.0.0','10.0.0'):
            raise ValueError('V2_PLANNING_CONTROLLER_PROJECTION_UNSUPPORTED')
        effective['policy']['controller']['version']='10.0.0'
        from extensions.tendon_family.gvs_profile import execution_scope
        checked=deepcopy(effective);checked['policy']['controller']['version']=old['version']
        if execution_scope(checked)!=execution_scope(original):raise ValueError('PLANNING_CAPABILITY_PROJECTION_CHANGED_SCIENCE')
        return effective
    future=builder.get('extension_id')=='candidate.family' and builder.get('version') in ('1.1.0','1.2.0')
    if future or any(p in current.get('parameters',{}) for p in STRUCTURAL_PATHS):
        if future:
            source_space=original['policy']['candidate_builder']['parameters']['data']
            if digest(source_space.get('semantic_source'))!=digest(current.get('semantic_source')):
                raise ValueError('PLANNING_SEMANTIC_SOURCE_IDENTITY_MISMATCH')
        effective['policy']['candidate_builder']=deepcopy(policy['candidate_builder'])
        effective['policy']['editable']=deepcopy(policy['editable'])
        if future:
            # A planning grant must retain the selected archived source's values,
            # including v1 common selectors, rather than apply incumbent defaults.
            decisions=effective['policy']['candidate_builder']['parameters']['data'].get('semantic_decisions',{})
            old=original['policy']['candidate_builder']['parameters']['data']
            selected=original['robot']['structure']['data'].get('metadata',{}).get('design_decisions',{}).get('selections',{})
            for path,decision in decisions.items():
                common='design/'+decision['operation']
                legacy=old.get('semantic_decisions',{}).get(common,{})
                if path in selected:value=selected[path]
                elif common in selected:value=selected[common]
                elif path in old.get('semantic_decisions',{}):value=old['semantic_decisions'][path]['baseline_value']
                elif legacy and set(decision['components'])<=set(legacy['components']):value=legacy['baseline_value']
                elif decision['operation']=='routing_radius_scale':
                    from extensions.tendon_family.routing_radius import normalize
                    scales=normalize(deepcopy(original['robot']['structure']['data']),current['semantic_source'])
                    value=scales[decision['components'][0]]
                else:raise ValueError('PLANNING_SEMANTIC_SELECTION_UNAVAILABLE: '+path)
                decision['baseline_value']=value
    from extensions.tendon_family.gvs_profile import execution_scope
    if execution_scope(effective)!=execution_scope(original):raise ValueError('PLANNING_CAPABILITY_PROJECTION_CHANGED_SCIENCE')
    return effective


def historical_parameter_projection(original,policy):
    """Read-only selector interpretation; never a scientific/cache identity.

    Reject inconsistent provenance or selectors instead of using current defaults.
    Only the current grant declares which segment operations can be interpreted.
    """
    projected=project_planning_configuration(original,policy)
    space=projected['policy']['candidate_builder']['parameters']['data']
    decisions=space.get('semantic_decisions',{})
    if projected['policy']['candidate_builder'].get('version') in ('1.1.0','1.2.0') and decisions:
        from math import isclose
        from extensions.tendon_family.design_decisions import MATERIAL_FACTORS
        design=original['robot']['structure']['data']
        provenance=design.get('metadata',{}).get('design_decisions',{})
        if provenance.get('source_identity')!=digest(space.get('semantic_source')):
            raise ValueError('HISTORICAL_SEMANTIC_PROVENANCE_MISMATCH')
        actual={c['id']:c for c in design['components']}
        source={c['id']:c for c in space['semantic_source']['components']}
        for path,decision in decisions.items():
            value=parameter_value(projected,path)
            for name in decision['components']:
                a,b=actual[name],source[name]
                if decision['operation']=='section_scale':
                    if len(a['sections'])!=len(b['sections']):raise ValueError('HISTORICAL_SELECTOR_SECTION_LAYOUT_MISMATCH: '+path)
                    for station,base in zip(a['sections'],b['sections']):
                        x,y=station['section'],base['section']
                        if x['kind']!=y['kind'] or x['parameters'].keys()!=y['parameters'].keys():
                            raise ValueError('HISTORICAL_SELECTOR_SECTION_LAYOUT_MISMATCH: '+path)
                        if any(not isclose(v,y['parameters'][k]*value,rel_tol=1e-12,abs_tol=0.) for k,v in x['parameters'].items()):
                            raise ValueError('HISTORICAL_SELECTOR_PHYSICAL_VALUE_MISMATCH: '+path)
                elif decision['operation']=='material_scenario':
                    if not isclose(a['physics']['young_pa'],b['physics']['young_pa']*MATERIAL_FACTORS[value],rel_tol=1e-12,abs_tol=0.):
                        raise ValueError('HISTORICAL_SELECTOR_PHYSICAL_VALUE_MISMATCH: '+path)
                elif decision['operation']=='routing_radius_scale':
                    from extensions.tendon_family.routing_radius import normalize
                    scales=normalize(deepcopy(design),space['semantic_source'])
                    if not isclose(scales[name],value,rel_tol=1e-12,abs_tol=0.):
                        raise ValueError('HISTORICAL_SELECTOR_PHYSICAL_VALUE_MISMATCH: '+path)
                else:raise ValueError('HISTORICAL_SELECTOR_OPERATION_UNAVAILABLE: '+path)
    return projected


def historical_parameter_comparison(original,policy,paths):
    """Unavailable parameter reads retain the original historical evidence."""
    try:
        projected=historical_parameter_projection(original,policy)
        space=policy['candidate_builder']['parameters']['data']
        allowed={**space.get('parameters',{}),**space.get('control_parameters',{}),
                 **space.get('model_parameters',{}),**space.get('discretization_parameters',{})}
        if projected['policy']['candidate_builder'].get('version')=='2.0.0':
            from extensions.tendon_family.finite_templates import selected_space
            from schemas.platform import SessionInput
            _,selected=selected_space(SessionInput.model_validate(projected),
                projected['policy']['candidate_builder']['parameters']['data'],{})
            allowed={**selected.parameters,**selected.control_parameters,'template':{}}
        if set(paths)-set(allowed):raise ValueError('HISTORICAL_PARAMETER_OUTSIDE_CURRENT_GRANT')
        return dict(available=True,values={p:parameter_value(projected,p) for p in paths},
            original_configuration_identity=digest(original),parameter_projection_identity=digest(projected),
            role='Parameter comparison only; original bytes and implementation still gate scientific match/reuse')
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        return dict(available=False,values=None,reason=str(exc),original_configuration_identity=digest(original),
            role='Historical evidence retained; unavailable mapping is not candidate invalidity or proof of novelty')
