"""Resolve editable study inputs once and construct the existing SessionInput boundary."""
from copy import deepcopy
from pathlib import Path
import math
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import read,digest

ROOT=Path(__file__).resolve().parents[2]


def resolve(path):
    path=Path(path).resolve(); study=read(path)
    robot=read(path.parent/study.pop('robot'))
    task=read(path.parent/study.pop('task'))
    runtime=read(path.parent/study.pop('runtime'))
    b=study['budgets']
    hard=dict(provider_requests=24,public_operations=60,mathematical_evaluations=12,
        local_solves=2,local_solve_s=600,numerical_s=10800,activity_s=14400)
    if any(not 0<=b[k]<=v for k,v in hard.items()):raise ValueError('ASSIGNMENT_CEILING_EXCEEDED')
    if not 0<=b['protected_provider_requests']<=b['provider_requests']:
        raise ValueError('PROTECTED_REQUESTS_ARE_PART_OF_TOTAL')
    if not 0<=b['delivery_reserve_s']<=b['activity_s']:
        raise ValueError('CLOSEOUT_RESERVE_IS_PART_OF_ACTIVITY')
    if study['nmpc_limits']['executions']>2 or not 0<study['nmpc_execution_cap_s']<=3600:
        raise ValueError('NMPC_ASSIGNMENT_CEILING')
    if not 0<study['standalone_watchdog_s']<=300:raise ValueError('LOCAL_SOLVE_HARD_CAP')
    limits=study['rl_limits']
    for k,v in dict(training_runs=1,training_actions=1000000,training_active_seconds=1200,evaluation_episodes=2).items():
        if not 0<=limits[k]<=v:raise ValueError('RL_ASSIGNMENT_CEILING: '+k)
    if study['confirmation']['fresh_independent_repetitions']<0:raise ValueError('NONNEGATIVE_CONFIRMATION_COUNT_REQUIRED')
    if study['topology_scope']!=dict(flexible_segments=2,independent_ideal_tensions=6):
        raise ValueError('CURRENT_TWO_SEGMENT_SIX_TENSION_SCOPE')
    if set(runtime['threads'])!={'OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'} or set(runtime['threads'].values())!={'1'}:
        raise ValueError('SINGLE_THREAD_NUMERICS_REQUIRED')
    for name in ('research_python','rl_python'):
        if not Path(runtime[name]).is_file():raise ValueError('INTERPRETER_MISSING: '+name)
    provider=runtime['provider']
    if not provider.get('base_url') or not provider.get('model'):raise ValueError('EXPLICIT_PROVIDER_REQUIRED')
    cfg=dict(run_id=study['study_id'],seed=task['seed'],robot=robot['robot'],task=task['task'],policy={})
    controller=deepcopy(study['controller_defaults'])
    controller['parameters']['data']['settling']=deepcopy(task['settling'])
    params=study['reference_parameters']
    for name in ('holding_tip_speed_weight','terminal_tip_speed_weight'):
        controller['parameters']['data']['recipe'][name]=params[name]
    cfg['policy'].update(controller=controller,backend=robot['backend'],dynamics_model=robot['dynamics_model'],
        discretization=robot['discretization'],candidate_builder=dict(extension_id='candidate.family',version='3.0.0',
            parameters=dict(contract='family.generator_space',version='1.0.0',data=dict(
                source_design=robot['robot']['structure']['data'],source_mesh=robot['discretization']['data'],segments=params['segments']))),
        model=provider,policy_id='research-mainline',allowed_tools=['evidence.read'],tool_bindings={'evidence.read':'1.0.0'},
        operation_allowances={'evidence.read':dict(timeout_s=30.,reserve_s=30.)},editable={},
        budget=dict(model_calls=b['provider_requests'],tool_calls=b['public_operations'],backend_solves=b['physical_launches'],worker_calls=0,wall_s=b['activity_s']),
        timeout_s=b['activity_s'])
    cfg=plain(SessionInput.model_validate(cfg))
    recipe=controller['parameters']['data']['recipe']
    if controller['version']!='11.0.0' or recipe['stopping_policy']!='research_work_v1' or recipe['max_iterations']!=120 or recipe['tolerance']!=1e-6 or recipe['max_cpu_s'] is not None or recipe['feasible_return'] is not None:
        raise ValueError('VERIFIED_NMPC_POLICY_REQUIRED')
    lengths={p['id']:p['length_m'] for p in robot['robot']['structure']['data']['components'] if p['kind']=='flexible_segment'}
    protocol=study['analysis_protocol']
    protocol.update(baseline_lengths_m=lengths,duration_s=task['task']['timing']['duration_s'],period_s=task['task']['timing']['control_period_s'])
    if study['scoring_window_s'] not in protocol['windows_s']:raise ValueError('SCORING_WINDOW_MUST_BE_DECLARED')
    cap=runtime['rl_evaluation_hard_cap_s']
    if not math.isfinite(cap) or not 0<cap<=120:raise ValueError('RL_EVALUATION_EXISTING_HARD_CAP_REQUIRED')
    study.update(configuration=cfg,runtime=runtime,numerical_environment=runtime['threads'],
        rl_evaluation_allowance_s=cap,rl_diagnostic_allowance_s=runtime['rl_diagnostic_hard_cap_s'],
        source_provenance=robot['provenance'],nominal_source='explicit_frozen_robot',
        configuration_entry=str(path.relative_to(ROOT)),budget_semantics=dict(
            protected_provider_requests='subset of provider_requests',delivery_reserve_s='subset of activity_s',
            rl_evaluation='per-process hard cap also bounded by remaining total numerical and activity time'))
    study['resolved_identity']=digest(study)
    return study
