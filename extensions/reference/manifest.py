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
    kw.setdefault('sources', SOURCE if 'SOURCE' in globals() else ())
    category = {'task': 'evaluation_comparison', 'evaluator': 'evaluation_comparison', 'initializer': 'scene_assembly',
        'controller': 'control', 'search': 'parameter_search', 'backend': 'simulation', 'worker': 'platform_services'}.get(kind,
        {'simulation': 'simulation', 'evaluation': 'evaluation_comparison', 'diagnostics': 'signals_diagnostics',
         'analysis': 'mathematical_models'}.get(name.split('.')[0], 'platform_services'))
    kw['capabilities'] = {**kw.get('capabilities', {}), 'category': category,
        'role': 'unimplemented' if binding is None else 'public_tool' if kind == 'tool' else 'adapter'}
    return Extension(name, kind, VERSION, inp, out, binding, description, **kw)


SOURCE = ('extensions/reference/contracts.py', 'extensions/reference/implementation.py', 'extensions/reference/manifest.py')
EXTENSIONS = [
    ext('task.reach', 'task', TaskDefinition, c.Empty, 'extensions.reference.implementation:reach_task', 'Development task using existing reach semantics'),
    ext('task.signal_hold', 'task', TaskDefinition, c.Empty, 'extensions.reference.implementation:hold_task', 'Discrete length signal hold development example; no tip target'),
    ext('initialize.length', 'initializer', c.InitialParameters, Payload, 'extensions.reference.implementation:initialize', 'Length initialization with an explicit seed', sources=SOURCE),
    ext('initialize.legacy_zero', 'initializer', c.Empty, Payload, 'extensions.reference.implementation:initialize_legacy', 'Original compiled initial state and zero velocity'),
    ext('evaluate.reach', 'evaluator', c.ReachEvaluation, EvaluationResult, 'extensions.reference.implementation:evaluate_reach', 'Tip distance evaluation with the threshold from the task'),
    ext('evaluate.hold', 'evaluator', c.HoldEvaluation, EvaluationResult, 'extensions.reference.implementation:evaluate_hold', 'Maximum and RMS deviation within the evaluation window', sources=SOURCE),
    ext('controller.length_reference', 'controller', c.LengthControl, c.ControlOutput, 'extensions.reference.implementation:LengthController', 'Reference length command lifecycle', sources=SOURCE,
        capabilities=dict(channel='tendon_target_lengths_m', observations=[], editable=['controller.command_m'], state_contract='reference.control_state', reset=True, restore=True)),
    ext('controller.legacy_length', 'controller', ExplorationControl, c.ControlOutput, 'extensions.reference.legacy:LegacyController', 'Legacy C1/C2 parameter and numerical control adapter',
        capabilities=dict(channel='tendon_target_lengths_m', observations=['tip_position'], editable=[], state_contract='legacy_controller_export', reset=True, restore=False)),
    ext('search.scalar_sequence', 'search', c.ScalarSearch, Payload, 'extensions.reference.implementation:ScalarSequenceSearch', 'Deterministic candidate sequence reference searcher; algorithm owns its state', sources=SOURCE,
        capabilities=dict(multiobjective=False, checkpoint='reference.search_state', random_state='reserved nullable typed integer state')),
    ext('backend.reference', 'backend', c.Empty, BackendResult, 'extensions.reference.implementation:ReferenceBackend', 'Low-cost deterministic reference backend; no real physics or Genesis', sources=SOURCE,
        capabilities=dict(signal_specs=[dict(name='tendon_length', entity='tendon_0', dimension=1, units='m', frame='actuator', phase='post_step'), dict(name='contact_count', entity='contact', dimension=1, units='count', frame='world', phase='post_step')], reference=True, families=['task.signal_hold'], robots=['reference_signal_robot'], channels=['tendon_target_lengths_m'],
            environments=['reference.environment'], signals=['tendon_length', 'contact_count'], signal_phases=['post_step'], controllers=['controller.length_reference'],
            operations=['compile', 'initialize', 'step', 'run', 'observe', 'export', 'cancel', 'close'],
            cancellation='cooperative step boundary', timeout='step loop; no external startup')),
    ext('backend.mujoco', 'backend', c.Empty, BackendResult, 'extensions.reference.legacy:MujocoBackend', 'Preserved MuJoCo one-shot solve adapter', dependencies=('mujoco',),
        capabilities=dict(conversion='legacy reach/compiler conversion', families=['task.reach'], robots=['tendon_driven_continuum'], channels=['tendon_target_lengths_m'], environments=['legacy.environment'],
            signals=['tip_position'], signal_phases=['post_step'], controllers=['controller.legacy_length'], operations=['compile', 'initialize', 'run', 'export', 'close'],
            cancellation='unsupported external interactive cancellation', timeout='existing rollout cooperative deadline; startup/export/close not hard bounded')),
    ext('backend.matlab', 'backend', c.Empty, BackendResult, 'extensions.reference.legacy:MatlabBackend', 'Preserved MATLAB planar dynamics one-shot solve adapter', dependencies=('matlab.engine', 'mujoco'), resources=('matlab_engine',),
        capabilities=dict(conversion='legacy reach/compiler conversion', families=['task.reach'], robots=['tendon_driven_continuum'], channels=['tendon_target_lengths_m'], environments=['legacy.environment'],
            signals=['tip_position'], signal_phases=['sampled_state'], controllers=['controller.legacy_length'], operations=['compile', 'initialize', 'run', 'export', 'close'],
            omissions=['out_of_plane DOFs', 'friction', 'self_collision', 'MuJoCo contact solver'],
            cancellation='future cancellation request only', timeout='RHS/future; engine startup and shutdown not hard bounded')),
    ext('backend.genesis', 'backend', c.Empty, BackendResult, None, 'Not implemented: check the target version and implement model, signal and execution channel adapters', dependencies=('genesis',)),
    ext('worker.signal', 'worker', c.WorkerParameters, WorkerOutput, 'extensions.reference.workers:run_signal_worker', 'Deterministic local worker reading the same fixed evidence',
        sources=('extensions/reference/workers.py', 'tools/platform_worker.py', 'extensions/reference/contracts.py'), capabilities=dict(allowed_tools=['evidence.read'], output_contract='WorkerOutput@2.0.0', result_checker='extensions.reference.workers:check_signal', cancellation='local process terminate')),
    ext('analysis.vector_norm', 'tool', c.MathNorm, c.MathNormResult, 'extensions.reference.implementation:vector_norm', 'Vector norm with units and frame; integration leaves the core loop unchanged', sources=SOURCE, cache=True),
]

for name, inp, out, function, description in [
    ('simulation.run', c.Simulate, BackendResult, 'simulate', 'Execute the frozen task and selected candidate, charging one backend attempt. Saves results and trajectory; use evaluation.run to score the result.'),
    ('evaluation.run', c.Evaluate, EvaluationResult, 'evaluate', 'Evaluate an existing saved simulation result with the frozen task evaluator. No solve; returns validity, metrics and task_success separately.'),
    ('evidence.read', c.ReadEvidence, c.EvidencePage, 'read_evidence', 'Read immutable saved evidence with JSON Pointer and offset paging. An oversized subtree returns a labeled pointer overview, not original content. Follow its pointers using the same source reference and next_offset at the same pointer. No solve or evaluation is performed.'),
    ('diagnostics.sample_exceeds', c.DiagnosticQuery, c.DiagnosticResult, 'diagnose', 'Versioned threshold diagnostics from saved signals'),
    ('memory.search', c.MemoryQuery, c.MemoryResults, 'memory_search', 'Search records across runs and verify provenance'),
    ('memory.save', c.MemorySave, c.SavedMemory, 'memory_save', 'Save notes or observations with provenance'),
    ('skills.search', c.SkillQuery, c.SkillRecords, 'skills_search', 'Read applicable strategies from the existing skill lifecycle'),
    ('skills.propose', c.SkillProposal, c.SkillRecords, 'skills_propose', 'Submit proposals to the development candidate library without human approval'),
    ('skills.validate', c.SkillValidation, c.SkillRecords, 'skills_validate', 'Register validation records consistent with evidence'),
    ('session.control', c.Stop, c.Stopped, 'stop', 'Stop or pause for missing information, missing capability or execution failure. For normal evaluated route delivery use route.advance(action="finish") instead.'),
    ('workers.submit', c.SubmitWork, c.WorkStatus, 'worker_submit', 'Start a bounded local worker'),
    ('workers.status', c.WorkQuery, c.WorkStatus, 'worker_status', 'Query worker status'),
    ('workers.cancel', c.WorkQuery, c.WorkStatus, 'worker_cancel', 'Request local worker cancellation'),
    ('workers.accept', c.WorkQuery, c.WorkStatus, 'worker_accept', 'Coordinator checks and accepts independent output'),
]:
    EXTENSIONS.append(ext(name, 'tool', inp, out, 'tools.platform_tools:' + function, description,
        sources=('tools/platform_tools.py', 'tools/platform_candidates.py', 'schemas/platform_operations.py', 'tools/platform_workers.py', 'tools/platform_worker.py', 'tools/platform_skills.py'),
        cache=name == 'simulation.run',
        capabilities=dict(preflight='tools.platform_tools:simulation_preflight',
            cache_reuse='tools.platform_tools:simulation_reuse') if name == 'simulation.run' else {},
        side_effects='current session/project only' if name not in ('evidence.read', 'memory.search', 'skills.search', 'workers.status') else 'none'))

from dataclasses import replace
# Worker envelope is a breaking change; no patch-version disguise.
EXTENSIONS = [replace(d, version='2.0.0') if d.kind == 'worker' else d for d in EXTENSIONS]

from schemas.platform import LegacyWorkerOutput
CONTRACTS.append(("reference.signal_report", VERSION, LegacyWorkerOutput))

# Exact representation and signal semantics; legacy conversion remains explicit.
EXTENSIONS = [replace(d, capabilities={**d.capabilities, 'robot_contracts': ['reference.robot'] if d.extension_id == 'backend.reference' else ['legacy.robot_ir', 'domain.rod_design'],
    **({'signal_specs': [dict(name='tip_position', entity='tip', dimension=3, units='m', frame='world',
         phase='sampled_state' if d.extension_id == 'backend.matlab' else 'post_step')]} if d.extension_id in ('backend.matlab', 'backend.mujoco') else {})})
    if d.kind == 'backend' and d.binding else d for d in EXTENSIONS]

LEGACY_SOURCES = ('extensions/reference/legacy.py', 'extensions/robot_domain/signals.py', 'extensions/robot_domain/contracts.py', 'tools/reach_dynamics.py', 'tools/mujoco_tools.py',
    'tools/matlab_tools.py', 'tools/task_context.py', 'tools/spec_tools.py', 'tools/design_compiler.py',
    'tools/capability_resolver.py', 'controllers/registry.py', 'controllers/base.py', 'controllers/factories.py',
    'controllers/open_loop_length.py', 'controllers/pcc_tip_feedback.py', 'schemas/exploration.py',
    'schemas/robot_ir.py', 'schemas/design_spec.py', 'schemas/task_spec.py', 'schemas/environment_spec.py', 'schemas/settings.py',
    'extensions/experiment_dynamics/physics.py', 'extensions/experiment_dynamics/contracts.py')
LEGACY_ASSETS = ('tasks/reach_free/task.yaml', 'tasks/reach_free/environment.yaml', 'tasks/reach_free/mujoco.xml',
    'configs/simulator.yaml', 'configs/run.yaml', 'physics_contracts/legacy_v1_surrogate.yaml', 'matlab/tdcr_planar_dynamic.m')
EXTENSIONS = [replace(d, sources=tuple(dict.fromkeys((*d.sources, *LEGACY_SOURCES))), assets=LEGACY_ASSETS)
              if d.extension_id in ('backend.mujoco', 'backend.matlab', 'controller.legacy_length') else d for d in EXTENSIONS]
EXTENSIONS = [replace(d, contract_dependencies=tuple((n, v) for n, v, schema in CONTRACTS
              if schema is d.input_schema or schema is d.output_schema)) for d in EXTENSIONS]

from extensions.robot_domain.signals import declarations
EXTENSIONS = [replace(d, capabilities={**d.capabilities,
    'signals': sorted({s['name'] for s in declarations(d.extension_id.split('.')[-1])} | {'tendon_tension'} |
        ({'contact_normal_force', 'contact_tangent_force', 'contact_position', 'contact_gap'} if d.extension_id == 'backend.mujoco' else set())),
    'signal_templates': declarations(d.extension_id.split('.')[-1]),
    'signal_specs_resolver': 'extensions.robot_domain.signals:observation_specs',
    'signal_phases': ['sampled_state'] if d.extension_id == 'backend.matlab' else ['post_step', 'pre_step_solver'],
    'force_convention': 'actuator_force negative=pull; tendon_tension=-actuator_force; contact normal positive=compression',
    'entity_expansion': 'actual IR joints/tendons/segments; MuJoCo contact_sample_i_point_j is one saved occurrence',
    'missing_signals': 'absent, never filled with zeros',
    'model': 'existing uncalibrated single-section legacy_v1 or equivalent_rod_v2',
    'semantics': 'state time_s; force/command solver_time_s; contact occurrence time_s'})
    if d.extension_id in ('backend.matlab', 'backend.mujoco') else d for d in EXTENSIONS]
