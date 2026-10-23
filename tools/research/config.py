"""Sole composition and sparse-patch boundary; existing studies use frozen state."""
from copy import deepcopy
from pathlib import Path

from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import read, digest, effective_input

ROOT = Path(__file__).resolve().parents[2]


def same_robot_structure(left, right):
    """Compare actual structural payloads, independent of task/control identity."""
    a, b = effective_input(left)['robot'], effective_input(right)['robot']
    return a['family'] == b['family'] and a['structure'] == b['structure']


def configuration_ownership(configuration):
    """Describe existing owners/grants; this view grants no editing authority."""
    value = plain(configuration)
    cfg = effective_input(value)
    grant = value.get('allowed_parameters')
    structural_grant = None if grant is None else {k: v for k, v in grant.items() if k.startswith('segments.')}
    control_grant = None if grant is None else {k: v for k, v in grant.items() if not k.startswith('segments.')}
    space = value.get('family_space')
    design_space, generator = None, None
    if space is not None:
        from extensions.tendon_family.family_space import decision_summary
        design_space = decision_summary(space, evidence=None, operations=[])
        generator = design_space['executable_domain']
        # Keep controller weights with their owner, while preserving the original
        # full family_space field below for existing readers.
        family_control_domains = design_space.pop('control_domains')
        lo, hi = space['segment_count_bounds']
        declared_only = dict(segment_counts=[n for n in range(lo, hi+1)
            if n not in space['executable_segment_counts']],
            tendon_counts=design_space['currently_unavailable']['tendon_counts'])
    else:
        family_control_domains, declared_only = None, None
        builder = cfg.get('policy', {}).get('candidate_builder')
        if builder:
            from tools.platform_registry import registry
            declaration = registry().get(builder['extension_id'], builder['version'], 'candidate_builder').hook('parameter_declarations')
            generator = declaration() if declaration else None
    return dict(
        frozen_task=dict(paths=['/task', '/seed'], owner='reviewed TaskDefinition and frozen study'),
        frozen_acceptance=dict(paths=['/task/evaluator', '/policy/controller/parameters/data/settling'],
            owner='registered evaluator and frozen acceptance protocol; legacy Reach settling stays in place'),
        structure=dict(paths=['/robot/structure'], owner='robot source and frozen structural grant',
            grant=structural_grant, family_space=space, design_space=design_space,
            generator_capability=generator, declared_only=declared_only,
            family_search=value.get('family_search'), topology_authorization=value.get('topology_authorization'),
            study_authorization=value.get('authorization'), start_mode=value.get('start_mode'),
            length_constraint=value.get('length_constraint'),
            authorization_scope='grant is legacy continuous authorization; FamilySpace declares domains and generator bounds, '
                'not permission. family_search limits mixed search groups/counts/cost; continuous query bounds are checked '
                'by existing search_domains against selected family domains. topology_authorization grants source-relative '
                'patches only. Agent operations also require frozen allowed_plan_actions/capabilities and available budgets; '
                'generation support never grants physical execution. Missing Study grants remain unknown.'),
        control=dict(paths=['/policy/controller/parameters/data/recipe', '/policy/controller/parameters/data/solver'],
            grant=control_grant,
            family_domains=family_control_domains,
            study_paths=['/control/rl_defaults/reward', '/control/rl_defaults/ppo'],
            owner='candidate control/reward/training configuration within registered schema and study grant; may differ by task'),
        algorithm_authorization=dict(owner='frozen study capabilities and continuation grants',
            capabilities=value.get('capabilities'), actions=value.get('allowed_plan_actions'),
            nmpc_limits=value.get('nmpc_limits'), rl_limits=value.get('rl_limits')),
        budget=dict(owner='frozen study ceilings and existing runtime ledger; views never reset usage',
            study=value.get('budgets'), execution=cfg.get('policy', {}).get('budget')))


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
    from tools.research.contracts import RewardConfiguration
    # Old saved stages retain their exact dictionaries. New registered terms
    # become explicit only when selected for start/continue.
    for key in reward or {}:
        if key not in result['reward'] and key in RewardConfiguration.model_fields:
            result['reward'][key] = RewardConfiguration.model_fields[key].default
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


def resolve(path, profile=None, *, backend_profile=None):
    path = Path(path).resolve()
    study = read(path)
    family_sensitivity=study.pop('family_sensitivity_variables',None)
    methods=study.pop('mathematical_methods',None)
    if methods is not None:
        if (not isinstance(methods,dict) or not methods or
                set(methods)-{'sampled-affine-conic-minimax-v1','controlled-capability-sensitivity-v1'} or
                any(not isinstance(v,str) or not v.strip() for v in methods.values())):
            raise ValueError('EXPLICIT_VERSIONED_MATHEMATICAL_METHOD_AUTHORIZATION_REQUIRED')
    decisions=study.pop('research_decisions',None)
    readiness=study.pop('tool_readiness',None)
    provenance = dict(root=dict(path=str(path), sha256=digest(study)), references={})
    correction=study.pop('correction_search',None)
    local_search=study.pop('local_control_search',None)
    family_mode=study.get('start_mode')=='family_space'
    additions={key:study.pop(key) for key in ('fidelity_policy','family_search') if key in study}
    if family_mode:
        from extensions.tendon_family.family_space import parse_space
        source=(path.parent/study.pop('defaults')).resolve()
        original=read(source)
        if source.parent!=path.parent or 'extends' in original or 'defaults' in original:
            raise ValueError('SAME_DIRECTORY_SINGLE_FAMILY_DEFAULTS_REQUIRED')
        family_source=(path.parent/study.pop('family_space')).resolve()
        family_definition=read(family_source)
        if 'base_space' in family_definition:
            base_source=(family_source.parent/family_definition.pop('base_space')).resolve()
            if base_source.parent!=family_source.parent:
                raise ValueError('SAME_DIRECTORY_SINGLE_FAMILY_BASE_REQUIRED')
            base_definition=read(base_source)
            if (base_definition.get('version')!='serial_family_space_v1'
                    or 'base_space' in base_definition or 'extends' in base_definition):
                raise ValueError('SAME_DIRECTORY_SINGLE_FAMILY_BASE_REQUIRED')
            family_definition['assembly']={**base_definition['assembly'],**family_definition.get('assembly',{})}
            family_definition={**base_definition,**family_definition}
            provenance['references']['family_space_base']=dict(path=str(base_source),sha256=digest(base_definition))
        family_space=plain(parse_space(family_definition))
        initialization=study.pop('candidate_initialization')
        if initialization!='all_candidate_dofs_zero_v1':
            raise ValueError('EXPLICIT_CANDIDATE_ZERO_INITIALIZATION_REQUIRED')
        study.pop('start_mode')
        scope=study.pop('topology_scope',{})
        study=patch(original,study)
        if scope:
            if set(scope)!={'segment_counts','tendon_counts'} or scope['segment_counts']!=[2] or scope['tendon_counts']!=[4]:
                raise ValueError('VALIDATED_TWO_SEGMENT_FOUR_TENDON_SCOPE_REQUIRED')
            family_space.update(executable_segment_counts=[2],executable_tendon_count_bounds=[4,4])
        study.update(start_mode='family_space',family_space=family_space,
            family_space_identity=digest(family_space),candidate_initialization=initialization)
        provenance['references'].update(defaults=dict(path=str(source),sha256=digest(original)),
            family_space=dict(path=str(family_source),sha256=digest(family_space)))
    elif study.get('start_mode', 'reference_candidate')!='reference_candidate':
        raise ValueError('UNKNOWN_RESEARCH_START_MODE')
    if additions:
        if not family_mode:
            raise ValueError('NEW_FIDELITY_SEARCH_POLICY_REQUIRES_FAMILY_STUDY')
        from tools.research.contracts import FidelityPolicy
        policy=plain(FidelityPolicy.model_validate(additions['fidelity_policy']))
        cells=family_space['serial_assembly']['cell_count_bounds']
        if any(not cells[0]<=level['cells_per_segment']<=cells[1] for level in [*policy['screening'].values(),policy['final_evaluation']]):
            raise ValueError('FIDELITY_OUTSIDE_FROZEN_MESH_DOMAIN')
        grant=additions.get('family_search')
        if grant and (grant['method']!='bounded_mixed_coordinate_v1' or
                not set(grant['segment_counts'])<=set(family_space['executable_segment_counts']) or
                any(not family_space['executable_tendon_count_bounds'][0]<=v<=family_space['executable_tendon_count_bounds'][1] for v in grant['tendon_counts']) or
                not all(type(grant[k]) is int and 1<=grant[k]<=128 for k in ('max_proposals','max_evaluations'))):
            raise ValueError('BOUNDED_EXECUTABLE_FAMILY_SEARCH_GRANT_REQUIRED')
        study.update(additions,fidelity_policy=policy)
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
    if backend_profile is not None:
        if backend_profile != 'sorosim_matlab_v1':
            raise ValueError('UNSUPPORTED_MATHEMATICAL_BACKEND_PROFILE: '+str(backend_profile))
        study['control']='control_sorosim.json'
        study['mathematical_backend_profile']=backend_profile
    inputs = {}
    if family_mode:
        study.pop('robot', None)  # Historical compositions may name it; never read it.
    for key in (('task', 'control', 'runtime') if family_mode else ('robot', 'task', 'control', 'runtime')):
        source = (path.parent / study.pop(key)).resolve()
        inputs[key] = read(source)
        provenance['references'][key] = dict(path=str(source), sha256=digest(inputs[key]))
        if key == 'control' and 'extends' in inputs[key]:
            base = (source.parent / inputs[key].pop('extends')).resolve()
            original = read(base)
            if base.parent != source.parent or 'extends' in original:
                raise ValueError('SAME_DIRECTORY_SINGLE_CONTROL_EXTENSION_REQUIRED')
            inputs[key] = patch(original, inputs[key])
            provenance['references']['control_base'] = dict(path=str(base), sha256=digest(original))
        if key=='task' and 'extends' in inputs[key]:
            base=(source.parent/inputs[key].pop('extends')).resolve()
            original=read(base)
            if base.parent!=source.parent or 'extends' in original:
                raise ValueError('SAME_DIRECTORY_SINGLE_TASK_EXTENSION_REQUIRED')
            inputs[key]=patch(original,inputs[key])
            provenance['references']['task_base']=dict(path=str(base),sha256=digest(original))
    if profile:
        study = patch(study, study['validation_profiles'][profile])
        study['selected_validation_profile'] = profile
    task, control, runtime = (inputs[k] for k in ('task', 'control', 'runtime'))
    if family_mode:
        robot, bootstrap = family_bootstrap(family_space, study.pop('family_execution'))
    else:
        robot = inputs['robot']
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
    replay_limit=study.get('physical_replay_limit')
    if replay_limit is not None and (type(replay_limit) is not int or not 0<=replay_limit<=b['physical_launches']):
        raise ValueError('PHYSICAL_REPLAY_LIMIT_MUST_SHARE_BACKEND_CEILING')
    count_keys = ('provider_requests', 'protected_provider_requests', 'public_operations',
        'protected_public_operations', 'physical_launches', 'local_solves', 'offline_nlp',
        'bdf_replays', 'mathematical_evaluations')
    if any(type(b[k]) is not int or b[k] < 0 for k in count_keys):
        raise ValueError('FINITE_NONNEGATIVE_COUNT_REQUIRED')
    if study['mode']=='engineering_investigation':
        if (study['capabilities']!=['investigation']
                or not set(study['allowed_plan_actions'])<= {'diagnose','stop'}
                or any(b[k] for k in ('physical_launches','local_solves','offline_nlp','bdf_replays','mathematical_evaluations'))
                or study['nmpc_limits']['executions']
                or any(study['rl_limits'][k] for k in ('training_stages','evaluation_episodes'))):
            raise ValueError('READ_ONLY_INVESTIGATION_REQUIRES_ZERO_SCIENCE_AND_DIAGNOSTIC_ACTIONS')
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
    stages=study['rl_limits']['training_stages'];rl='rl' in study['capabilities']
    if type(stages) is not int or not (1 if rl else 0)<=stages<=10:
        raise ValueError('DECLARED_TRAINING_STAGE_LIMIT_REQUIRED')
    limits=study['rl_limits']
    if any(limits[k] is not None for k in ('training_active_seconds','seconds_per_trial')):
        raise ValueError('COUNT_MODE_DISALLOWS_SCIENTIFIC_TIME_LIMITS')
    for name in ('training_actions','actions_per_trial'):
        value=limits[name]
        if value is not None and (type(value) is not int or value<1):
            raise ValueError('POSITIVE_FINITE_RL_ACTION_COUNT_REQUIRED')
    if not family_mode and study['topology_scope'] != dict(flexible_segments=2, independent_ideal_tensions=6):
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
    if family_mode:
        source_initial = cfg['task']['initializer']['parameters']['data']
        if source_initial['unspecified'] != 'zero' or any(
                v != 0 for key in ('qpos_rad','qvel_rad_s') for v in source_initial[key].values()):
            raise ValueError('FAMILY_ZERO_RULE_REQUIRES_AUTHORIZED_ZERO_SOURCE_TASK')
        cfg['policy']['candidate_builder'] = bootstrap['builder']
        cfg['task']['initializer']['parameters']['data'] = bootstrap['initializer']
    cfg = plain(SessionInput.model_validate(cfg))
    if additions:
        backend=cfg['policy']['backend']
        backend_name=backend['extension_id']+'@'+backend['version']
        if any(level['backend']!=backend_name for level in [*policy['screening'].values(),policy['final_evaluation']]):
            raise ValueError('FIDELITY_REQUIRES_FROZEN_BACKEND')
    from extensions.tendon_family.gvs_profile import ReachControl
    if cfg['policy']['controller']['extension_id'] == 'controller.sorosim_matlab_nmpc':
        from extensions.tendon_family.sorosim_control import SorosimReachControl
        ReachControl = SorosimReachControl
    from extensions.tendon_family.contracts import current_nmpc_recipe, MujocoParameters
    data = ReachControl.model_validate(cfg['policy']['controller']['parameters']['data']).model_dump(mode='json')
    data['recipe'] = current_nmpc_recipe(data['recipe'])
    cfg['policy']['controller']['parameters']['data'] = data
    cfg['policy']['backend']['parameters']['data'] = MujocoParameters.model_validate(
        cfg['policy']['backend']['parameters']['data']).model_dump(mode='json')
    study['analysis_protocol'].update(baseline_lengths_m={k:v['length_m'] for k,v in segments.items()},
        duration_s=task['task']['timing']['duration_s'], period_s=task['task']['timing']['control_period_s'])
    if family_mode:
        study['analysis_protocol']['baseline_lengths_m']={k:v['length_m'] for k,v in segments.items()}
        if family_space['version']=='serial_family_space_v2':
            study['analysis_protocol']['baseline_lengths_m']={f'segment_{i}':
                family_space['segment_domains'].get(str(i),family_space['segment_domain'])['length_m']['default']
                for i in range(family_space['segment_count_bounds'][1])}
            study['analysis_length_scale_source']='frozen_family_domain_defaults_v1'
    from schemas.platform_analysis import TaskAnalysisProtocol
    TaskAnalysisProtocol.model_validate(study['analysis_protocol'])
    if study['scoring_window_s'] not in study['analysis_protocol']['windows_s']:
        raise ValueError('SCORING_WINDOW_MUST_BE_DECLARED')
    study.update(configuration=cfg, runtime=runtime, control=control, numerical_environment=runtime['threads'],
        rl_evaluation_allowance_s=None, rl_diagnostic_allowance_s=None, source_provenance=robot['provenance'],
        nominal_source='explicit_frozen_robot', configuration_entry=str(path), configuration_provenance=provenance,
        budget_semantics=dict(mode='count', scientific_time_limits=None, elapsed_time='measured only',
            training='initialization and continuation share admitted stage count; exact recovery retains stage',
            steps='ceil requested positive steps to a complete rollout before admission; declared action ceilings apply when present',
            protection='requests and operations reserved within totals for evaluation, evidence and closeout'))
    if family_mode:
        initial=cfg['task']['initializer']['parameters']['data']
        if initial['unspecified']!='zero' or any(v!=0 for key in ('qpos_rad','qvel_rad_s') for v in initial[key].values()):
            raise ValueError('FAMILY_ZERO_RULE_REQUIRES_AUTHORIZED_ZERO_SOURCE_TASK')
        canonical_task=deepcopy(cfg['task'])
        canonical_task['initializer']['parameters']['data']=dict(rule=study['candidate_initialization'])
        study.update(canonical_task=canonical_task,canonical_task_identity=digest(canonical_task),
            nominal_source=None,reference_parameters={},allowed_parameters={},
            topology_scope=dict(declarative_segment_counts=family_space['segment_count_bounds'],
                declarative_tendon_counts=family_space['tendon_count_bounds'],
                executable_segment_counts=family_space['executable_segment_counts'],
                executable_tendon_counts=family_space['executable_tendon_count_bounds']),
            implementation_scaffold=dict(purpose='Host SessionInput compatibility only; not an Agent candidate',
                source=dict(family_space_identity=study['family_space_identity'],request=bootstrap['request']),
                reason='Host.create and compile_input require concrete robot signals and backend checks',
                scientific_candidate=False, candidate_pool_member=False))
    if family_sensitivity is not None:
        from tools.research.optimal_capability import freeze_family_variables
        if not family_mode:raise ValueError('FAMILY_SENSITIVITY_REQUIRES_FAMILY_SPACE')
        study['family_sensitivity_variables']=freeze_family_variables(family_space,family_sensitivity)
    if local_search is not None:
        from tools.research.contracts import LocalControlSearchSettings
        if not isinstance(local_search,list) or not local_search:
            raise ValueError('EXPLICIT_LOCAL_SEARCH_METHOD_SETTINGS_REQUIRED')
        local_search=[plain(LocalControlSearchSettings.model_validate(v)) for v in local_search]
        if ('control_correction' not in study['capabilities'] or any(
                v['knots_s'][-1]>cfg['task']['timing']['duration_s'] for v in local_search)):
            raise ValueError('LOCAL_SEARCH_CAPABILITY_AND_TASK_HORIZON_REQUIRED')
        study['local_control_search']=local_search
    if correction is not None:
        from tools.research.contracts import ControlCorrectionSettings
        correction=plain(ControlCorrectionSettings.model_validate(correction))
        if ('control_correction' not in study['capabilities'] or
                correction['knots_s'][-1]>cfg['task']['timing']['duration_s']):
            raise ValueError('DECLARED_CORRECTION_CAPABILITY_AND_TASK_KNOTS_REQUIRED')
        study['correction_search']=correction
    if additions:
        study['final_evaluation_identity']=digest(dict(policy=policy,backend=cfg['policy']['backend'],
            task=study['canonical_task'],controller=cfg['policy']['controller'],model=cfg['policy']['dynamics_model']))
    if decisions is not None:
        if decisions.get('version')!='research_decision_v1' or set(decisions)-{'version','history','mathematics','control_seeds','context_limits'}:
            raise ValueError('VERSIONED_RESEARCH_DECISIONS_REQUIRED')
        for key,value in decisions.get('context_limits',{}).items():
            if key not in ('candidates','recent','pareto','samples','evidence') or type(value) is not int or not 1<=value<=100:
                raise ValueError('BOUNDED_RESEARCH_CONTEXT_LIMIT_REQUIRED')
        study['research_decisions']=decisions
    if readiness is not None:
        report=read((path.parent/readiness).resolve())
        if report.get('scientific_evidence') is not False or report.get('status') not in ('ready','dependency_unavailable','engine_start_failed','gateway_failed','timeout'):
            raise ValueError('EXPLICIT_ENGINEERING_READINESS_REPORT_REQUIRED')
        study['tool_readiness']=dict(sorosim_matlab=report)
    if methods is not None:study['mathematical_methods']=methods
    study['resolved_identity'] = digest(study)
    return study


def family_bootstrap(space, execution):
    """A family-derived Host input, never a scientific reference or candidate."""
    from extensions.tendon_family.family_space import parse_build
    from extensions.tendon_family.generated_serial import generate_family
    build = parse_build(dict(space=space, request=dict(family_space_identity=digest(space),
        segment_count=min(space['executable_segment_counts']),
        tendon_count=space['executable_tendon_count_bounds'][0])))
    design, mesh, physics = generate_family(build)
    robot = dict(family='tendon_robot_family',channels=['actuator_commands'],units='SI',
        frame='world_base_x_forward_yz_cross_section',sources=['frozen family assembly'],
        assumptions=space['assumptions'],unsupported=space['unsupported'],
        structure=dict(contract='family.design',version='1.0.0',data=design))
    initial = {k:{j:0. for j in physics['dofs']} for k in ('qpos_rad','qvel_rad_s')}
    initial['unspecified'] = 'zero'
    return dict(robot=robot,discretization=dict(contract='family.discretization',version='1.0.0',data=mesh),
        **execution, provenance=dict(source='frozen family assembly',scientific_candidate=False)), dict(
        builder=dict(extension_id='candidate.family',version='6.0.0' if space['version']=='serial_family_space_v2' else '5.0.0',parameters=dict(
            contract='family.serial_space_build_v2' if space['version']=='serial_family_space_v2' else 'family.serial_space_build',version='1.0.0',data=plain(build))),
        initializer=initial,request=plain(build.request))
