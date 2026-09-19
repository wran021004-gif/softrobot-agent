"""Application assembly for public default adapters; declaration imports only."""
from schemas.common import Contract
from schemas.platform import SessionInput, ModelResponse, ToolRequest
from schemas import platform_math as math_contracts
from schemas import platform_learning as learning_contracts
from schemas import platform_diagnostics as diagnostic_contracts
from tools.platform_registry import Extension


class Empty(Contract):
    pass


CONTRACTS = [('platform.empty', '1.0.0', Empty)]
CONTRACTS += [('platform.' + name, '1.0.0', schema) for name, schema in [
    ('mathematical_model', math_contracts.MathematicalModel),
    ('dynamic_system', math_contracts.DynamicSystem),
    ('linearized_model', math_contracts.LinearizedModel),
    ('model_requirement', math_contracts.ModelRequirement),
    ('system_context', math_contracts.SystemContext),
    ('optimization_specification', math_contracts.OptimizationSpecification),
    ('optimization_problem', math_contracts.OptimizationProblem),
    ('optimization_result', math_contracts.OptimizationResult),
    ('rl_problem', learning_contracts.RLProblem),
    ('reward_definition', learning_contracts.RewardDefinition),
    ('rl_training_specification', learning_contracts.RLTrainingSpecification),
    ('training_job', learning_contracts.TrainingJob),
    ('training_metric', learning_contracts.TrainingMetric),
    ('policy_artifact', learning_contracts.PolicyArtifact),
    ('training_result', learning_contracts.TrainingResult),
    ('gate_result', diagnostic_contracts.GateResult),
    ('diagnostic_report', diagnostic_contracts.DiagnosticReport),
]]
EXTENSIONS = [
    Extension('candidate.controller', 'candidate_builder', '1.0.0', Empty, SessionInput,
        'tools.platform_candidates:apply_control', 'Apply existing typed controller parameters',
        sources=('tools/platform_candidates.py', 'schemas/platform_operations.py')),
    Extension('offline', 'model_adapter', '1.0.0', Empty, ModelResponse,
        'tools.platform_models:OfflineAdapter', 'Offline scripted compatibility fixture',
        sources=('tools/platform_models.py',), capabilities=dict(real_requests=False, text=True, images=False, timeout='synchronous local', cancellation='between decisions')),
    Extension('deepseek', 'model_adapter', '1.0.0', Empty, ModelResponse,
        'tools.platform_models:DeepSeekAdapter', 'Existing text/tool model service transport',
        sources=('tools/platform_models.py', 'tools/model_transports/deepseek.py'), capabilities=dict(real_requests=True, text=True, images=False, timeout='network request deadline', cancellation='between requests')),
    Extension('strategy.tool', 'strategy', '1.0.0', Empty, ToolRequest,
        'tools.platform_models:ToolStrategy', 'One typed tool request per decision', sources=('tools/platform_models.py',)),
]

from dataclasses import replace
EXTENSIONS = [replace(d, capabilities={**d.capabilities,
    'category': 'robot_design' if d.kind == 'candidate_builder' else 'platform_services',
    'role': 'adapter'}) for d in EXTENSIONS]
