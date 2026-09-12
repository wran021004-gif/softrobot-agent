"""Session-specific extension; old envelope and HUMAN_POLICY behavior stay intact."""
from tools.spec_tools import ROOT, load_yaml
from tools.artifact_tools import file_hash

AUTH = 'configs/experiments/round3_closeout_authorization.yaml'
POLICY = 'configs/experiments/round3_closeout.yaml'
FEEDBACK = dict(gain_rad2_per_m2=.3, update_every_steps=20, max_bend_update_rad=.01,
               max_command_update_m=.0001, min_tendon_length_m=.001, max_tendon_length_m=1.)
STAGES = {'A': {'M1':4, 'MUJOCO':4}, 'B':{'M1':16, 'MUJOCO':4},
          'C':{'M1':0, 'MUJOCO':4}, 'D':{'M1':8, 'MUJOCO':4}, 'E':{'M1':0, 'MUJOCO':4}}


def validate_closeout_authority(policy, path, envelope):
    authority = load_yaml(ROOT/AUTH)
    if (path != (ROOT/POLICY).resolve() or policy.approval_source != AUTH or
        authority['scope'] != 'ROUND3_DETERMINISTIC_CLOSEOUT' or
        authority['parent_approval_source'] != envelope['approval_source'] or
        policy.policy_id != 'round3_deterministic_closeout_v1' or
        policy.task_contract_source != 'tasks/reach_free/contract.yaml' or
        policy.baseline_design != 'configs/design_tendon_arm.yaml' or
        policy.purpose != 'DESIGN_SEARCH' or
        policy.feedback_parameters.model_dump() != FEEDBACK or
        policy.evaluation_budget != 48 or policy.mujoco_validation_budget != 20 or
        policy.seed != 17 or policy.allowed_controller_levels != ('C1','C2') or
        policy.allowed_model_levels != ('M0','M1') or
        set(v.name for v in policy.variables) != {'total_length_m','tendon_routing_radius_m','tendon_count'}):
        raise ValueError('CLOSEOUT_SCOPE_MISMATCH: exact session policy required')
    paths = [ROOT/AUTH, ROOT/authority['parent_approval_source'], ROOT/authority['instruction_source']]
    for name, expected in authority['frozen_hashes'].items():
        source = ROOT/name
        if file_hash(source) != expected:
            raise ValueError('Frozen closeout authority changed: '+name)
        paths.append(source)
    if file_hash(ROOT/authority['instruction_source']) != authority['instruction_sha256']:
        raise ValueError('Closeout instruction snapshot changed')
    if authority['feedback_parameters'] != FEEDBACK or authority['stage_budgets'] != STAGES:
        raise ValueError('Closeout fixed parameters/budgets changed')
    return paths


def analysis_permission(operation):
    from tools.experiment_policy_tools import validate_experiment_policy
    validated = validate_experiment_policy(ROOT/POLICY)
    authority = load_yaml(ROOT/AUTH)
    if operation not in authority['independent_analysis_operations']:
        raise ValueError('Independent analysis operation not authorized')
    return validated
