"""Canonical builder parameter resolution shared by planning and scheduling."""
from copy import deepcopy
from extensions.tendon_family.candidate import canonical_path, read_parameter, locate
from tools.state_io import digest

STRUCTURAL_PATHS=('components/near/length_m','components/far/length_m','design/section_scale','design/material_scenario')


def parameter_value(effective,path):
    path=canonical_path(path)
    space=effective['policy']['candidate_builder']['parameters']['data']
    selections=effective['robot']['structure']['data'].get('metadata',{}).get('design_decisions',{}).get('selections',{})
    if path in selections:return selections[path]
    if path in space.get('semantic_decisions',{}):
        builder=effective['policy']['candidate_builder']
        decision=space['semantic_decisions'][path]
        if builder.get('extension_id')=='candidate.family' and builder.get('version')=='1.1.0':
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
    if space.get('semantic_decisions') or any(p.startswith('design/') for p in variables):
        design.get('metadata',{}).pop('design_decisions',None)
    for path in variables:
        decision=space.get('semantic_decisions',{}).get(path,{})
        if path in ('design/section_scale','design/material_scenario') or decision:
            components=decision.get('components',['near','far'])
            operation=decision.get('operation',path.removeprefix('design/'))
            for c in design['components']:
                if c['id'] not in components:continue
                if operation=='section_scale':
                    for station in c['sections']:
                        station['section']['parameters']={k:'<batch variable>' for k in station['section']['parameters']}
                else:c['physics']['young_pa']='<batch variable>'
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
    return scope


def comparison_scope(effective):
    from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS
    builder=effective['policy']['candidate_builder']
    if builder.get('extension_id')=='candidate.family' and builder.get('version')=='1.1.0':
        from tools.parameter_catalog import effective_catalog
        return scientific_fixed_scope(effective,effective_catalog(effective)['usable_pool'])
    return scientific_fixed_scope(effective,[*STRUCTURAL_PATHS,*REACH_WEIGHT_PATHS])


def planning_configuration(store,candidate,policy):
    """Add current authorized builder capabilities; preserve archived scientific input."""
    original=store.artifact(candidate['configuration'])['effective'];effective=deepcopy(original)
    current=policy.get('candidate_builder',{}).get('parameters',{}).get('data',{})
    builder=policy.get('candidate_builder',{})
    future=builder.get('extension_id')=='candidate.family' and builder.get('version')=='1.1.0'
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
            for path,decision in decisions.items():decision['baseline_value']=parameter_value(effective,path)
    from extensions.tendon_family.gvs_profile import execution_scope
    if execution_scope(effective)!=execution_scope(original):raise ValueError('PLANNING_CAPABILITY_PROJECTION_CHANGED_SCIENCE')
    return effective
