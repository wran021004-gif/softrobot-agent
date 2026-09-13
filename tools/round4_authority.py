"""Narrow session extension of the existing experiment validator."""
from tools.spec_tools import ROOT, load_yaml
from tools.artifact_tools import file_hash
from tools.closeout_authority import FEEDBACK

AUTH = 'configs/experiments/round4_authorization.yaml'
POLICY = 'configs/experiments/round4_length.yaml'


def check_authority():
    a = load_yaml(ROOT / AUTH)
    if (a['scope'] != 'ROUND4_LENGTH_AND_TOOL_VALIDATION' or a['feedback_parameters'] != FEEDBACK
        or a['limits'] != dict(length_screen=24, length_mujoco=28, development_mujoco=12, mechanics=24)):
        raise ValueError('ROUND4_SCOPE_MISMATCH')
    paths = [ROOT / AUTH, ROOT / a['instruction_source']]
    if file_hash(paths[-1]) != a['instruction_sha256']:
        raise ValueError('Round4 instruction changed')
    for name, expected in a['frozen_hashes'].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError('Frozen source changed: ' + name)
        paths.append(ROOT / name)
    return paths


def validate_round4_authority(policy, path, envelope):
    paths = check_authority()
    if (path != (ROOT / POLICY).resolve() or policy.policy_id != 'round4_length_v1'
        or policy.approval_source != AUTH or policy.task_contract_source != 'tasks/reach_free/contract.yaml'
        or policy.baseline_design != 'configs/experiments/round4_baseline.yaml'
        or policy.purpose != 'DESIGN_SEARCH' or policy.feedback_parameters.model_dump() != FEEDBACK
        or policy.evaluation_budget != 52 or policy.mujoco_validation_budget != 28 or policy.seed != 17
        or policy.allowed_controller_levels != ('C1', 'C2') or policy.allowed_model_levels != ('M0', 'M1')
        or [v.model_dump() for v in policy.variables] != [dict(name='total_length_m', unit='m', lower_bound=.05, upper_bound=.8, constraints=('positive',))]):
        raise ValueError('ROUND4_SCOPE_MISMATCH: fixed length-only policy required')
    d = load_yaml(ROOT / policy.baseline_design)
    if any(d[k] != v for k,v in dict(total_length_m=.298, tendon_routing_radius_m=.018,
            tendon_count=8, body_radius_m=.02, segments=8, sections=1).items()):
        raise ValueError('Round4 fixed design changed')
    if load_yaml(ROOT / AUTH)['parent_approval_source'] != envelope['approval_source']:
        raise ValueError('Round4 parent approval mismatch')
    return paths
