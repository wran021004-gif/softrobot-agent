"""Declaration-only imports: no NumPy, MuJoCo, MATLAB or network startup."""
from schemas.platform import VERSION, TaskDefinition, Payload, BackendResult, EvaluationResult, WorkerOutput
from schemas.environment_spec import EnvironmentSpec
from schemas.robot_ir import RobotIR
from schemas.exploration import ExplorationControl
from tools.platform_registry import Extension
from extensions.reference import contracts as c

CONTRACTS = [('reference.empty', VERSION, c.Empty), ('reference.reach_goal', VERSION, c.ReachGoal),
    ('reference.reach_evaluation', VERSION, c.ReachEvaluation), ('reference.hold_goal', VERSION, c.HoldGoal),
    ('reference.hold_evaluation', VERSION, c.HoldEvaluation), ('reference.environment', VERSION, c.ReferenceEnvironment),
    ('reference.robot', VERSION, c.ReferenceRobot), ('reference.initialize', VERSION, c.InitialParameters),
    ('reference.initial_state', VERSION, c.InitialState), ('reference.control', VERSION, c.LengthControl),
    ('reference.control_state', VERSION, c.ControlState), ('reference.backend_data', VERSION, c.ReferenceData),
    ('reference.search', VERSION, c.ScalarSearch), ('reference.search_state', VERSION, c.SearchState),
    ('reference.worker', VERSION, c.WorkerParameters), ('legacy.environment', VERSION, EnvironmentSpec),
    ('legacy.robot_ir', VERSION, RobotIR), ('legacy.control', VERSION, ExplorationControl),
    ('legacy.backend_data', VERSION, c.LegacyData), ('legacy.initial_state', VERSION, c.LegacyInitial)]


def ext(name, kind, inp, out, binding, description, **kw):
    return Extension(name, kind, VERSION, inp, out, binding, description, **kw)


SOURCE = ('extensions/reference/contracts.py', 'extensions/reference/implementation.py', 'extensions/reference/manifest.py')
EXTENSIONS = [
    ext('task.reach', 'task', TaskDefinition, c.Empty, 'extensions.reference.implementation:reach_task', '已有到达语义的开发任务'),
    ext('task.signal_hold', 'task', TaskDefinition, c.Empty, 'extensions.reference.implementation:hold_task', '离散长度信号保持开发示例；无末端目标点'),
    ext('initialize.length', 'initializer', c.InitialParameters, Payload, 'extensions.reference.implementation:initialize', '显式种子的长度初始化', sources=SOURCE),
    ext('initialize.legacy_zero', 'initializer', c.Empty, Payload, 'extensions.reference.implementation:initialize_legacy', '原编译初态和零速度'),
    ext('evaluate.reach', 'evaluator', c.ReachEvaluation, EvaluationResult, 'extensions.reference.implementation:evaluate_reach', '末端距离评价，阈值来自任务'),
    ext('evaluate.hold', 'evaluator', c.HoldEvaluation, EvaluationResult, 'extensions.reference.implementation:evaluate_hold', '评价窗口内最大与 RMS 偏差', sources=SOURCE),
    ext('controller.length_reference', 'controller', c.LengthControl, c.ControlOutput, 'extensions.reference.implementation:LengthController', '参考长度指令生命周期', sources=SOURCE,
        capabilities=dict(channel='tendon_target_lengths_m', observations=[], editable=['controller.command_m'], state_contract='reference.control_state', reset=True, restore=True)),
    ext('controller.legacy_length', 'controller', ExplorationControl, c.ControlOutput, 'extensions.reference.legacy:LegacyController', '旧 C1/C2 参数与数值控制适配',
        capabilities=dict(channel='tendon_target_lengths_m', observations=['tip_position'], editable=[], state_contract='legacy_controller_export', reset=True, restore=False)),
    ext('search.scalar_sequence', 'search', c.ScalarSearch, Payload, 'extensions.reference.implementation:ScalarSequenceSearch', '确定性候选序列参考搜索器；算法拥有状态', sources=SOURCE,
        capabilities=dict(multiobjective=False, checkpoint='reference.search_state', random_state='reserved nullable typed integer state')),
    ext('backend.reference', 'backend', c.Empty, BackendResult, 'extensions.reference.implementation:ReferenceBackend', '廉价确定性参考后端，非真实物理、非 Genesis', sources=SOURCE,
        capabilities=dict(reference=True, families=['task.signal_hold'], robots=['reference_signal_robot'], channels=['tendon_target_lengths_m'],
            environments=['reference.environment'], signals=['tendon_length', 'contact_count'], signal_phases=['post_step'], controllers=['controller.length_reference'],
            operations=['compile', 'initialize', 'step', 'run', 'observe', 'export', 'cancel', 'close'],
            cancellation='cooperative step boundary', timeout='step loop; no external startup')),
    ext('backend.mujoco', 'backend', c.Empty, BackendResult, 'extensions.reference.legacy:MujocoBackend', '保留 MuJoCo 一次性求解适配', dependencies=('mujoco',),
        capabilities=dict(families=['task.reach'], robots=['tendon_driven_continuum'], channels=['tendon_target_lengths_m'], environments=['legacy.environment'],
            signals=['tip_position'], signal_phases=['post_step'], controllers=['controller.legacy_length'], operations=['compile', 'initialize', 'run', 'export', 'close'],
            cancellation='unsupported external interactive cancellation', timeout='existing rollout cooperative deadline; startup/export/close not hard bounded')),
    ext('backend.matlab', 'backend', c.Empty, BackendResult, 'extensions.reference.legacy:MatlabBackend', '保留 MATLAB 平面动力学一次性求解适配', dependencies=('matlab.engine', 'mujoco'), resources=('matlab_engine',),
        capabilities=dict(families=['task.reach'], robots=['tendon_driven_continuum'], channels=['tendon_target_lengths_m'], environments=['legacy.environment'],
            signals=['tip_position'], signal_phases=['sampled_state'], controllers=['controller.legacy_length'], operations=['compile', 'initialize', 'run', 'export', 'close'],
            omissions=['out_of_plane DOFs', 'friction', 'self_collision', 'MuJoCo contact solver'],
            cancellation='future cancellation request only', timeout='RHS/future; engine startup and shutdown not hard bounded')),
    ext('backend.genesis', 'backend', c.Empty, BackendResult, None, '待实现：必须检查目标版本并完成模型、信号与执行通道适配', dependencies=('genesis',)),
    ext('worker.signal', 'worker', c.WorkerParameters, WorkerOutput, 'tools.platform_worker:run_signal_worker', '读取同一固定证据的确定性本地工作者',
        sources=('tools/platform_worker.py', 'extensions/reference/contracts.py'), capabilities=dict(allowed_tools=['evidence.read'], output_contract='WorkerOutput@1.0.0', cancellation='local process terminate')),
    ext('analysis.vector_norm', 'tool', c.MathNorm, c.MathNormResult, 'extensions.reference.implementation:vector_norm', '带单位与坐标的向量范数；接入不改核心循环', sources=SOURCE, cache=True),
]

for name, inp, out, function, description in [
    ('simulation.run', c.Simulate, BackendResult, 'simulate', '执行当前冻结任务与候选'),
    ('evaluation.run', c.Evaluate, EvaluationResult, 'evaluate', '显式评价保存结果并产生新身份'),
    ('evidence.read', c.ReadEvidence, c.EvidencePage, 'read_evidence', '只读不可变证据及分页'),
    ('diagnostics.sample_exceeds', c.DiagnosticQuery, c.DiagnosticResult, 'diagnose', '基于保存信号的带版本阈值诊断'),
    ('memory.search', c.MemoryQuery, c.MemoryResults, 'memory_search', '检索跨运行记录并校验来源'),
    ('memory.save', c.MemorySave, c.SavedMemory, 'memory_save', '保存有来源的笔记或观测记录'),
    ('skills.search', c.SkillQuery, c.SkillRecords, 'skills_search', '读取现有技能生命周期中的适用策略'),
    ('skills.propose', c.SkillProposal, c.SkillRecords, 'skills_propose', '提案进入开发候选库，无人工批准'),
    ('skills.validate', c.SkillValidation, c.SkillRecords, 'skills_validate', '登记与证据相符的验证记录'),
    ('session.control', c.Stop, c.Stopped, 'stop', '停止、暂停、缺少信息或能力'),
    ('workers.submit', c.SubmitWork, c.WorkStatus, 'worker_submit', '启动有边界的本地工作者'),
    ('workers.status', c.WorkQuery, c.WorkStatus, 'worker_status', '查询工作者状态'),
    ('workers.cancel', c.WorkQuery, c.WorkStatus, 'worker_cancel', '请求取消本地工作者'),
    ('workers.accept', c.WorkQuery, c.WorkStatus, 'worker_accept', '协调者检查并接收独立输出'),
]:
    EXTENSIONS.append(ext(name, 'tool', inp, out, 'tools.platform_tools:' + function, description,
        cache=name == 'simulation.run',
        capabilities=dict(preflight='tools.platform_tools:simulation_preflight') if name == 'simulation.run' else {},
        side_effects='current session/project only' if name not in ('evidence.read', 'memory.search', 'skills.search', 'workers.status') else 'none'))
