"""Canonical builder parameter resolution shared by planning and scheduling."""
from copy import deepcopy
from extensions.tendon_family.candidate import canonical_path, read_parameter, locate


def parameter_value(effective,path):
    path=canonical_path(path)
    space=effective['policy']['candidate_builder']['parameters']['data']
    if path in space.get('semantic_decisions',{}):
        return effective['robot']['structure']['data'].get('metadata',{}).get('design_decisions',{}).get('selections',{}).get(
            path,space['semantic_decisions'][path]['baseline_value'])
    for prefix,field in (('control/','controller'),('model/','dynamics_model')):
        if path.startswith(prefix):return read_parameter(effective['policy'][field]['parameters']['data'],path[len(prefix):])
    if path.startswith('discretization/'):return read_parameter(effective['policy']['discretization']['data'],path[15:])
    return read_parameter(effective['robot']['structure']['data'],path)


def fixed_configuration(effective,variables):
    fixed=deepcopy(effective)
    for path in variables:
        if not path.startswith('control/'):raise ValueError('BATCH_WEIGHT_PATHS_ONLY')
        obj,key=locate(fixed['policy']['controller']['parameters']['data'],path[8:]);obj[key]='<batch variable>'
    return fixed


def actual_parameter_changes(before,after,paths):
    return [dict(path=p,before=parameter_value(before,p),after=parameter_value(after,p))
            for p in paths if parameter_value(before,p)!=parameter_value(after,p)]
