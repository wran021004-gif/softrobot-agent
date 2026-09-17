"""Declarations only; this package is the independent integration exercise."""
from tools.platform_registry import Extension
from schemas.platform import SessionInput, ModelResponse, Payload, TaskDefinition, EvaluationResult, BackendResult, WorkerOutput
from extensions.convergence import contracts as c

SOURCE = ('extensions/convergence/contracts.py', 'extensions/convergence/implementation.py', 'extensions/convergence/manifest.py')
CONTRACTS = [('convergence.' + name, '1.0.0', schema) for name, schema in [
    ('empty', c.Empty), ('adapter', c.AdapterParameters), ('terminal_goal', c.TerminalGoal),
    ('terminal_evaluation', c.TerminalEvaluation), ('worker', c.WorkerParameters),
    ('math_report', c.MathReport), ('diagnostic_report', c.DiagnosticReport),
    ('search', c.StatefulParameters), ('search_state', c.StatefulState)]]


def ext(name, kind, inp, out, function, **kw):
    kw['capabilities'] = {**kw.get('capabilities', {}), 'role': 'teaching_example',
        'category': {'candidate_builder': 'robot_design', 'backend': 'simulation', 'controller': 'control',
            'search': 'parameter_search', 'task': 'evaluation_comparison', 'evaluator': 'evaluation_comparison',
            'tool': 'mathematical_models'}.get(kind, 'platform_services')}
    return Extension(name, kind, '1.0.0', inp, out, 'extensions.convergence.implementation:' + function,
        'Independent offline development example; no physical calibration', sources=SOURCE, **kw)


SIGNALS = [dict(name='tendon_length', entity='tendon_0', dimension=1, units='m', frame='actuator', phase='post_step'),
           dict(name='contact_count', entity='contact', dimension=1, units='count', frame='world', phase='post_step')]
EXTENSIONS = [
    ext('model.observing', 'model_adapter', c.AdapterParameters, ModelResponse, 'ObservingAdapter',
        extension_dependencies=(('offline', '1.0.0'),), capabilities=dict(real_requests=False, text=True, images=False, timeout='bounded local code', cancellation='between decisions')),
    ext('candidate.synthetic', 'candidate_builder', c.Empty, SessionInput, 'apply_design',
        capabilities=dict(editable=['controller.command_m', 'structure.response_fraction'])),
    ext('backend.limited_synthetic', 'backend', c.Empty, BackendResult, 'LimitedBackend',
        extension_dependencies=(('backend.reference', '1.0.0'),), capabilities=dict(reference=True,
            robots=['reference_signal_robot'], channels=['tendon_target_lengths_m'], environments=['reference.environment'],
            signals=['tendon_length', 'contact_count'], signal_specs=SIGNALS, signal_phases=['post_step'],
            operations=['compile', 'initialize', 'run', 'close'], timeout='step loop', cancellation='step boundary')),
    ext('task.terminal', 'task', TaskDefinition, c.Empty, 'terminal_task'),
    ext('evaluate.terminal', 'evaluator', c.TerminalEvaluation, EvaluationResult, 'terminal_evaluate'),
    ext('search.stateful', 'search', c.StatefulParameters, Payload, 'StatefulSearch', capabilities=dict(multiobjective=False)),
    ext('worker.math', 'worker', c.WorkerParameters, WorkerOutput, 'math_worker',
        extension_dependencies=(('analysis.vector_norm', '1.0.0'),), capabilities=dict(output_contract='WorkerOutput@2.0.0', result_checker='extensions.convergence.implementation:check_math')),
    ext('worker.inventory', 'worker', c.WorkerParameters, WorkerOutput, 'diagnostic_worker',
        capabilities=dict(output_contract='WorkerOutput@2.0.0', result_checker='extensions.convergence.implementation:check_diagnostic')),
]

from dataclasses import replace
EXTENSIONS += [ext('analysis.versioned_value', 'tool', c.Value, c.Value, 'value_v1'),
    replace(ext('analysis.versioned_value', 'tool', c.Value, c.Value, 'value_v2'), version='2.0.0')]

from schemas.platform import ToolRequest
EXTENSIONS.append(ext('strategy.evidence', 'strategy', c.Empty, ToolRequest, 'EvidenceStrategy'))

EXTENSIONS = [replace(d, contract_dependencies=tuple((n, v) for n, v, schema in CONTRACTS
              if schema is d.input_schema or schema is d.output_schema)) for d in EXTENSIONS]
