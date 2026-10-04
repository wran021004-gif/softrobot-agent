"""Freeze the current family capability grant without modifying historical profiles."""
from copy import deepcopy
from tools.state_io import read,digest
from tools.candidate_parameters import STRUCTURAL_PATHS


def structural_input(effective,profile):
    from extensions.tendon_family.gvs_profile import candidate_reach_input,execution_scope
    original=deepcopy(effective);result=deepcopy(effective)
    if result['policy']['controller']['extension_id']!='controller.gvs_nmpc' or result['policy']['controller']['version']!=profile['controller_version']:
        raise ValueError('CURRENT_CONTROLLER_VERSION_REQUIRED')
    declared=candidate_reach_input('milestone4-semantic-source')['robot']['structure']['data']
    provenance=result['robot']['structure']['data'].get('metadata',{}).get('design_decisions',{})
    if digest(declared)!=profile['semantic_source_identity'] or provenance.get('source_identity')!=digest(declared):
        raise ValueError('ORIGINAL_SEMANTIC_SOURCE_IDENTITY_MISMATCH')
    space=result['policy']['candidate_builder']['parameters']['data']
    if space.get('semantic_source') and digest(space['semantic_source'])!=digest(declared):raise ValueError('DO_NOT_REBASE_ABSOLUTE_DECISIONS')
    space['parameters'].update(deepcopy(profile['parameters']))
    space.update(semantic_decisions=deepcopy(profile['semantic_decisions']),semantic_source=declared)
    result['policy']['editable'].update({p:s['bounds'] for p,s in profile['parameters'].items() if s['type']=='number'})
    if execution_scope(result)!=execution_scope(original):raise ValueError('STRUCTURAL_GRANT_CHANGED_SOURCE_SCIENCE')
    return result


def research_planning_input(effective,profile,*,budget,model,tool_bindings):
    """Project evaluated science into the authorized research host policy.

    Execution children deliberately have zero model allowance and execution-only
    tools. Those administrative restrictions are not a research planning grant.
    The Store still enforces the cumulative project ceiling independently.
    """
    from extensions.tendon_family.gvs_profile import execution_scope
    result=structural_input(effective,profile)
    result['policy'].update(budget=deepcopy(budget),model=deepcopy(model),tool_bindings=deepcopy(tool_bindings))
    if 'design.submit_search_plan' not in tool_bindings or 'design.respond_diagnosis' not in tool_bindings:
        raise ValueError('RESEARCH_PLANNING_HANDOFF_TOOLS_REQUIRED')
    if execution_scope(result)!=execution_scope(effective):raise ValueError('RESEARCH_POLICY_CHANGED_SCIENCE')
    return result
