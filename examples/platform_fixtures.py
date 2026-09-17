"""Explicit development definitions for tests/docs; does not execute backends."""
from copy import deepcopy
from uuid import uuid4
from tools.spec_tools import ROOT


def payload(contract, data):
    return dict(contract=contract, version='1.0.0', data=data)


def binding(name, contract='reference.empty', data=None):
    return dict(extension_id=name, version='1.0.0', parameters=payload(contract, data or {}))


def budget(**values):
    return dict(tool_calls=values.get('tool_calls', 60), model_calls=values.get('model_calls', 0),
        backend_solves=values.get('backend_solves', 0), worker_calls=values.get('worker_calls', 6), wall_s=values.get('wall_s', 300.))


def project(grant=None):
    return dict(project_id='platform-development', grant_id=grant or 'development-' + uuid4().hex, purpose='development',
        authorization_source='用户本次框架整理授权；独立开发接口验证，不使用历史研究预算',
        budget=budget(tool_calls=200, worker_calls=20, wall_s=600.), exclusive_resources=dict(matlab_engine=1, reference_device=1))


def reference_input(run_id='signal-hold'):
    signal = dict(name='tendon_length', entity='tendon_0', dimension=1, units='m', frame='actuator', phase='post_step')
    return dict(run_id=run_id, seed=17,
        task=dict(task_id='signal-hold-dev', task_version='1.0.0', name='离散长度信号保持开发示例', status='development_valid',
            source='明确工程参考模型：x[k+1]=x[k]+0.5*(command-x[k])，仅验证接口；无物理标定', family='task.signal_hold',
            goal=payload('reference.hold_goal', dict(length_m=0.3)),
            environment=payload('reference.environment', dict(environment_id='empty-reference', gravity_m_s2=[0., 0., 0.], objects=[], source='合成空环境')),
            robot_families=['reference_signal_robot'], actuator_channels=['tendon_target_lengths_m'],
            initializer=binding('initialize.length', 'reference.initialize', dict(length_m=0.29, jitter_m=0.001)),
            timing=dict(timestep_s=0.01, control_period_s=0.01, sample_period_s=0.01, duration_s=0.1, termination=['duration', 'numerical_failure', 'cancelled']),
            evaluator=binding('evaluate.hold', 'reference.hold_evaluation', dict(max_deviation_m=0.01)),
            objectives=[dict(metric='rms_deviation', direction='minimize', units='m', weight=1.)],
            failure_policy='retain_invalid_and_constraint_failures', observations=[signal],
            sampling=dict(split='development', seeds=[17], window_s=[0., 0.1], aggregation='per_instance')),
        robot=dict(family='reference_signal_robot', structure=payload('reference.robot', dict(length_m=0.3, response_fraction=0.5, model_identity='discrete_length_response_fixture')),
            channels=['tendon_target_lengths_m'], units='SI', frame='actuator', assumptions=['离散一阶信号模型，仅接口验证'], sources=['examples/platform_fixtures.py'], unsupported=['physical_dynamics', 'gravity', 'friction', 'contact']),
        policy=dict(policy_id='reference-development', editable={'controller.command_m': [0.25, 0.35]},
            tool_bindings={'diagnostics.sample_exceeds': '1.0.0'},
            backend=binding('backend.reference'), controller=binding('controller.length_reference', 'reference.control', dict(command_m=0.3)),
            search=binding('search.scalar_sequence', 'reference.search', dict(parameter='controller.command_m', candidates=[0.3, 0.31])),
            model=dict(adapter='offline', model='offline-contract-fixture', max_turns=12),
            allowed_tools=['analysis.vector_norm', 'simulation.run', 'evaluation.run', 'evidence.read', 'diagnostics.sample_exceeds',
                'memory.save', 'memory.search', 'skills.search', 'skills.propose', 'skills.validate', 'workers.submit', 'workers.status', 'workers.cancel', 'workers.accept', 'session.control'],
            budget=budget(), timeout_s=10., allow_development_skills=True))


def reach_input(run_id='reach-shifted', backend='mujoco'):
    from tools.spec_tools import load_task_package, load_yaml
    from tools.design_compiler import build_robot_ir
    from schemas.design_spec import DesignSpec
    from schemas.exploration import ExplorationControl
    old_task, env = load_task_package()
    design = DesignSpec(robot_family='tendon_driven_continuum', sections=1, segments=8, total_length_m=0.3,
        body_radius_m=0.02, tendon_count=4, tendon_routing_radius_m=0.018)
    ir = build_robot_ir(design)
    value = reference_input(run_id)
    task = value['task']
    task.update(task_id=run_id, name='更换目标与时长的到达开发示例', family='task.reach',
        source='原 reach_free 环境与 0.01 m 容差；开发目标 [0.30,0,0.08]，40 步；不改变历史科研定义',
        goal=payload('reference.reach_goal', dict(target_m=[0.3, 0., 0.08])), environment=payload('legacy.environment', env.model_dump(mode='json')),
        robot_families=['tendon_driven_continuum'], initializer=binding('initialize.legacy_zero'),
        evaluator=binding('evaluate.reach', 'reference.reach_evaluation', dict(tolerance_m=old_task.position_error_max_m)),
        timing=dict(timestep_s=0.002, control_period_s=0.002, sample_period_s=0.002, duration_s=0.08, termination=['duration', 'numerical_failure']),
        objectives=[dict(metric='position_error', direction='minimize', units='m')],
        observations=[dict(name='tip_position', entity='tip', dimension=3, units='m', frame='world', phase='post_step')],
        sampling=dict(split='development', seeds=[17], window_s=[0., 0.08]))
    value['robot'] = dict(family='tendon_driven_continuum', structure=payload('legacy.robot_ir', ir.model_dump(mode='json')),
        channels=['tendon_target_lengths_m'], units='SI', frame=ir.coordinate_frame, assumptions=['原未标定分段替代模型，数值保持原来源'],
        sources=list(ir.physics_contracts), unsupported=['physical_calibration', 'pressure', 'torque_command'])
    value['policy'].update(policy_id='short-reach-development', editable={}, backend=binding('backend.' + backend),
        controller=binding('controller.legacy_length', 'legacy.control', ExplorationControl(mode='C1').model_dump(mode='json')),
        search=None, budget=budget(backend_solves=1), timeout_s=10.)
    if backend == 'matlab':
        task['observations'][0]['phase'] = 'sampled_state'
    return value


def write_examples():
    import yaml
    root = ROOT / 'configs/platform'
    root.mkdir(exist_ok=True)
    for name, value in [('signal_hold', reference_input()), ('reach_shifted', reach_input())]:
        directory = root / name
        directory.mkdir(exist_ok=True)
        task = value.pop('task')
        env = task.pop('environment')
        task['environment_file'] = 'environment.yaml'
        for label, item in [('task', task), ('environment', env), ('robot', value.pop('robot')), ('policy', value.pop('policy'))]:
            (directory / (label + '.yaml')).write_text(yaml.safe_dump(item, allow_unicode=True, sort_keys=False), encoding='utf8')
        value.update(task_file='task.yaml', robot_file='robot.yaml', policy_file='policy.yaml')
        (directory / 'session.yaml').write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding='utf8')
    config = project('unified-platform-local-development-v1')
    config['budget']['backend_solves'] = 1
    (root / 'project.yaml').write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding='utf8')
    (root / 'offline.yaml').write_text(yaml.safe_dump(dict(decisions=[
        dict(tool_id='analysis.vector_norm', arguments=dict(values_m=[3., 4.]), reason='新数学扩展验收'),
        dict(tool_id='evidence.read', arguments=dict(reference='$last_output', pointer='/norm_m'), reason='读取实际数学输出'),
        dict(tool_id='simulation.run', arguments={}, reason='执行开发参考任务'),
        dict(tool_id='evaluation.run', arguments=dict(result='$last_output'), reason='使用冻结评价器'),
        dict(tool_id='session.control', arguments=dict(status='stopped', reason='离线接口验收完成'), reason='明确停止')]), allow_unicode=True, sort_keys=False), encoding='utf8')


if __name__ == '__main__':
    write_examples()
