"""Sole composition and sparse-patch boundary; existing studies use frozen state."""
from copy import deepcopy
from pathlib import Path

from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import read, digest

ROOT = Path(__file__).resolve().parents[2]


def patch(base, changes):
    """Objects merge, lists replace; null replaces and must pass the owner contract.

    Null is supported for disabled limits, absent reference/boundary, and optional
    clip_range_vf/target_kl. Required numeric scientific fields reject null.
    """
    result = deepcopy(base)
    for key, value in changes.items():
        if key not in result:
            raise ValueError('UNKNOWN_CONFIGURATION_FIELD: ' + key)
        result[key] = patch(result[key], value) if isinstance(value, dict) and isinstance(result[key], dict) else deepcopy(value)
    return result


def rl_configuration(defaults, training=None, reward=None):
    """Defaults and model patches receive the identical algorithm validation."""
    from tools.rl.run import validate_settings
    result = deepcopy(defaults)
    result['ppo'] = patch(result['ppo'], training or {})
    result['reward'] = patch(result['reward'], reward or {})
    validate_settings(result)
    result['requested_overrides'] = dict(training=training or {}, reward=reward or {})
    return result


def extend_engineering_counts(spec, changes, authorization):
    """Explicit human-authorized addendum; never exposed to model tools."""
    if spec['mode']!='engineering_numerical' or not authorization:
        raise ValueError('EXPLICIT_ENGINEERING_AUTHORIZATION_REQUIRED')
    if set(changes)!={'training_stages','evaluation_episodes','physical_launches'}:
        raise ValueError('ONLY_DECLARED_VALIDATION_COUNT_EXTENSION_SUPPORTED')
    if any(type(v) is not int or v<0 for v in changes.values()):
        raise ValueError('FINITE_COUNT_REQUIRED')
    result=deepcopy(spec)
    previous=result.pop('resolved_identity')
    for key in ('training_stages','evaluation_episodes'):
        if changes[key]<spec['rl_limits'][key]:
            raise ValueError('EXTENSION_CANNOT_ERASE_CONSUMED_ALLOWANCE')
        result['rl_limits'][key]=changes[key]
    if changes['physical_launches']<spec['budgets']['physical_launches']:
        raise ValueError('EXTENSION_CANNOT_ERASE_CONSUMED_ALLOWANCE')
    result['budgets']['physical_launches']=changes['physical_launches']
    result['configuration']['policy']['budget']['backend_solves']=changes['physical_launches']
    SessionInput.model_validate(result['configuration'])
    result.setdefault('authorization_addenda',[]).append(dict(previous_resolved_identity=previous,
        counts=changes,authorization=authorization,original_failures_and_consumption_preserved=True))
    result['resolved_identity']=digest(result)
    return result


def resolve(path, profile=None):
    path = Path(path).resolve()
    study = read(path)
    provenance = dict(root=dict(path=str(path), sha256=digest(study)), references={})
    if 'extends' in study:
        source=(path.parent/study.pop('extends')).resolve()
        original=read(source)
        if source.parent!=path.parent or 'extends' in original:
            raise ValueError('SAME_DIRECTORY_SINGLE_STUDY_EXTENSION_REQUIRED')
        from extensions.tendon_family.generated_serial import TopologyAuthorization
        grant=plain(TopologyAuthorization.model_validate(study.pop('topology_authorization')))
        study=patch(original,study)
        if study['study_id']==original['study_id'] or study['authorization']==original['authorization']:
            raise ValueError('NEW_STUDY_AND_EXPLICIT_TOPOLOGY_AUTHORIZATION_REQUIRED')
        study.update(topology_authorization=grant,source_study_identity=digest(original),source_study_id=original['study_id'])
        provenance['references']['source_study']=dict(path=str(source),sha256=digest(original))
    inputs = {}
    for key in ('robot', 'task', 'control', 'runtime'):
        source = (path.parent / study.pop(key)).resolve()
        inputs[key] = read(source)
        provenance['references'][key] = dict(path=str(source), sha256=digest(inputs[key]))
    if profile:
        study = patch(study, study['validation_profiles'][profile])
        study['selected_validation_profile'] = profile
    robot, task, control, runtime = (inputs[k] for k in ('robot', 'task', 'control', 'runtime'))
    control['rl_defaults']['seed'] = task['seed']
    control['rl_defaults'] = rl_configuration(control['rl_defaults'])
    if 'segments' in study['reference_parameters']:
        raise ValueError('PHYSICAL_REFERENCE_VALUES_OWNED_BY_ROBOT_SOURCE')
    segments = {p['id']: dict(length_m=p['length_m'], young_pa=p['physics']['young_pa'],
        sections={str(i): deepcopy(s['section']['parameters']) for i, s in enumerate(p['sections'])})
        for p in robot['robot']['structure']['data']['components'] if p['kind'] == 'flexible_segment'}
    study['reference_parameters']['segments'] = segments
    for key, value in study.pop('reference_edits', {}).items():
        if key not in study['allowed_parameters']:
            raise ValueError('UNDECLARED_REFERENCE_EDIT: ' + key)
        current = study['reference_parameters']
        parts = key.split('.')
        for part in parts[:-1]:
            current = current[part]
        if parts[-1] not in current:
            raise ValueError('INVALID_REFERENCE_EDIT: ' + key)
        current[parts[-1]] = value
    b = study['budgets']
    count_keys = ('provider_requests', 'protected_provider_requests', 'public_operations',
        'protected_public_operations', 'physical_launches', 'local_solves', 'offline_nlp',
        'bdf_replays', 'mathematical_evaluations')
    if any(type(b[k]) is not int or b[k] < 0 for k in count_keys):
        raise ValueError('FINITE_NONNEGATIVE_COUNT_REQUIRED')
    for total, reserved in (('provider_requests', 'protected_provider_requests'), ('public_operations', 'protected_public_operations')):
        if b[reserved] > b[total]:
            raise ValueError('PROTECTION_IS_PART_OF_TOTAL: ' + reserved)
    time_values = [b[k] for k in ('activity_s', 'numerical_s', 'local_solve_s', 'delivery_reserve_s')]
    time_values += [study[k] for k in ('analysis_cap_s', 'nmpc_execution_cap_s', 'standalone_watchdog_s')]
    time_values += list(study['execution_allowances'].values())
    time_values += [runtime[k] for k in ('rl_evaluation_hard_cap_s', 'rl_diagnostic_hard_cap_s')]
    if any(v is not None for v in time_values):
        raise ValueError('COUNT_MODE_REQUIRES_EXPLICIT_DISABLED_SCIENTIFIC_TIMING')
    if study['confirmation']['fresh_independent_repetitions'] != 0:
        raise ValueError('COUNT_MODE_USES_ZERO_EXTRA_CONFIRMATIONS')
    if (type(study['rl_limits']['training_stages']) is not int or not 1<=study['rl_limits']['training_stages']<=10 or (not profile and study['rl_limits']['training_stages']!=10)):
        raise ValueError('DECLARED_TRAINING_STAGE_LIMIT_REQUIRED')
    if any(study['rl_limits'][k] is not None for k in ('training_actions', 'training_active_seconds', 'actions_per_trial', 'seconds_per_trial')):
        raise ValueError('NO_AGGREGATE_OR_HIDDEN_PER_STAGE_CEILING_IN_COUNT_MODE')
    if study['topology_scope'] != dict(flexible_segments=2, independent_ideal_tensions=6):
        raise ValueError('CURRENT_TWO_SEGMENT_SIX_TENSION_SCOPE')
    if set(runtime['threads']) != {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'} or set(runtime['threads'].values()) != {'1'}:
        raise ValueError('SINGLE_THREAD_NUMERICS_REQUIRED')
    provider = runtime['provider']
    if not provider.get('base_url') or not provider.get('model'):
        raise ValueError('EXPLICIT_PROVIDER_REQUIRED')
    controller = deepcopy(control['controller_defaults'])
    controller['parameters']['data']['settling'] = deepcopy(task['settling'])
    for name in ('holding_tip_speed_weight', 'terminal_tip_speed_weight'):
        controller['parameters']['data']['recipe'][name] = study['reference_parameters'][name]
    cfg = dict(run_id=study['study_id'], seed=task['seed'], robot=robot['robot'], task=task['task'], policy={})
    cfg['policy'].update(controller=controller, backend=robot['backend'], dynamics_model=robot['dynamics_model'],
        discretization=robot['discretization'], candidate_builder=dict(extension_id='candidate.family', version='3.0.0',
            parameters=dict(contract='family.generator_space', version='1.0.0', data=dict(
                source_design=robot['robot']['structure']['data'], source_mesh=robot['discretization']['data'], segments=segments))),
        model=provider, policy_id='research-mainline', allowed_tools=['evidence.read'], tool_bindings={'evidence.read': '1.0.0'},
        operation_allowances={'evidence.read': dict(timeout_s=None, reserve_s=None)}, editable={},
        budget=dict(model_calls=b['provider_requests'], tool_calls=b['public_operations'], backend_solves=b['physical_launches'], worker_calls=0, wall_s=None), timeout_s=None)
    if 'topology_authorization' in study:
        builder=cfg['policy']['candidate_builder']
        builder['version']='4.0.0';builder['parameters']['contract']='family.topology_space'
        builder['parameters']['data'].update(authorization=study['topology_authorization'],topology=dict(
            version='tendon_topology_patch_v1',remove_tendons=[],upsert_tendons=[],guide_holes={}))
    cfg = plain(SessionInput.model_validate(cfg))
    from extensions.tendon_family.gvs_profile import ReachControl
    from extensions.tendon_family.contracts import current_nmpc_recipe, MujocoParameters
    data = ReachControl.model_validate(cfg['policy']['controller']['parameters']['data']).model_dump(mode='json')
    data['recipe'] = current_nmpc_recipe(data['recipe'])
    cfg['policy']['controller']['parameters']['data'] = data
    cfg['policy']['backend']['parameters']['data'] = MujocoParameters.model_validate(
        cfg['policy']['backend']['parameters']['data']).model_dump(mode='json')
    study['analysis_protocol'].update(baseline_lengths_m={k:v['length_m'] for k,v in segments.items()},
        duration_s=task['task']['timing']['duration_s'], period_s=task['task']['timing']['control_period_s'])
    from schemas.platform_analysis import TaskAnalysisProtocol
    TaskAnalysisProtocol.model_validate(study['analysis_protocol'])
    if study['scoring_window_s'] not in study['analysis_protocol']['windows_s']:
        raise ValueError('SCORING_WINDOW_MUST_BE_DECLARED')
    study.update(configuration=cfg, runtime=runtime, control=control, numerical_environment=runtime['threads'],
        rl_evaluation_allowance_s=None, rl_diagnostic_allowance_s=None, source_provenance=robot['provenance'],
        nominal_source='explicit_frozen_robot', configuration_entry=str(path), configuration_provenance=provenance,
        budget_semantics=dict(mode='count', scientific_time_limits=None, elapsed_time='measured only',
            training='initialization and continuation share admitted stage count; exact recovery retains stage',
            steps='ceil requested positive steps to a complete rollout before admission; no cumulative step ceiling',
            protection='requests and operations reserved within totals for evaluation, evidence and closeout'))
    study['resolved_identity'] = digest(study)
    return study
