"""Explicit read-only adapter; original evaluator and tool definitions are unchanged."""
from schemas.platform import EvaluationResult
from tools.platform_registry import Extension
from .saved import SavedEvaluation

CONTRACTS=[('evaluation.saved_request','1.0.0',SavedEvaluation)]
EXTENSIONS=[Extension('evaluation.saved','tool','1.0.0',SavedEvaluation,EvaluationResult,
    'extensions.saved_evaluation.saved:evaluate_saved',
    'Evaluate a sealed same-project execution in a new session with the identical task, backend and unchanged producer dependencies. No simulation or snapshot modification.',
    sources=('extensions/saved_evaluation/saved.py','extensions/saved_evaluation/manifest.py'),
    contract_dependencies=(('evaluation.saved_request','1.0.0'),),
    side_effects='new evaluation receipt and provenance event only',
    capabilities=dict(category='evaluation_comparison',role='public_tool',backend_solves=0))]
