"""Generic explicit optimization declarations."""
from schemas.platform_math import OptimizationResult
from tools.platform_registry import Extension

from . import contracts as c


CONTRACTS = [
    ('optimization.casadi_nlp_expression', '1.0.0', c.CasadiNLPExpression),
    ('optimization.casadi_nlp_selector', '1.0.0', c.CasadiNLPSelector),
    ('optimization.ipopt_parameters', '1.0.0', c.IpoptParameters),
    ('optimization.describe_request', '1.0.0', c.OptimizationDescribeRequest),
    ('optimization.description', '1.0.0', c.OptimizationDescription),
    ('optimization.assemble_request', '1.0.0', c.OptimizationAssembleRequest),
    ('optimization.assembly_result', '1.0.0', c.OptimizationAssemblyResult),
    ('optimization.solve_request', '1.0.0', c.OptimizationSolveRequest),
]
SOURCES = (
    'extensions/optimization/contracts.py',
    'extensions/optimization/ipopt.py',
    'extensions/optimization/manifest.py',
    'schemas/platform_math.py',
    'schemas/platform_protocols.py',
    'tools/platform_optimization.py',
)
DEPS = tuple((name, version) for name, version, _ in CONTRACTS) + (
    ('platform.system_context', '1.0.0'),
    ('platform.optimization_problem', '1.0.0'),
    ('platform.optimization_result', '1.0.0'),
)


EXTENSIONS = [
    Extension(
        'solver.ipopt', 'solver', '1.0.0', c.IpoptParameters, OptimizationResult,
        'extensions.optimization.ipopt:IpoptSolver',
        'Solve explicit differentiable OptimizationProblem expressions with CasADi IPOPT.',
        dependencies=('numpy', 'casadi'), sources=SOURCES, contract_dependencies=DEPS,
        capabilities=dict(category='optimization', role='adapter', expression='casadi_nlp_function_v1',
                          backend_solves=0, search=False),
    ),
    Extension(
        'optimization.describe', 'tool', '1.0.0', c.OptimizationDescribeRequest, c.OptimizationDescription,
        'extensions.optimization.ipopt:optimization_describe_tool',
        'Describe trusted PCC reach and GVS inverse templates plus the IPOPT evidence workflow.',
        dependencies=('casadi',), sources=SOURCES, contract_dependencies=DEPS, cache=True,
        extension_dependencies=(
            ('optimization_assembler.pcc_reach', '1.0.0'),
            ('optimization_assembler.gvs_inverse', '1.0.0'),
        ),
        capabilities=dict(category='optimization', role='public_tool', route_visible=True, backend_solves=0),
    ),
    Extension(
        'optimization.assemble', 'tool', '1.0.0', c.OptimizationAssembleRequest, c.OptimizationAssemblyResult,
        'extensions.optimization.ipopt:optimization_assemble_tool',
        'Assemble a trusted template from frozen task/robot facts and save its OptimizationProblem.',
        dependencies=('casadi',), sources=SOURCES, contract_dependencies=DEPS,
        side_effects='artifact_store',
        extension_dependencies=(
            ('optimization_assembler.pcc_reach', '1.0.0'),
            ('optimization_assembler.gvs_inverse', '1.0.0'),
            ('optimization_assembler.gvs_trajectory', '1.0.0'),
        ),
        capabilities=dict(category='optimization', role='public_tool', route_visible=True,
                          evidence_input=True, evidence_output=True, backend_solves=0),
    ),
    Extension(
        'optimization.solve', 'tool', '1.0.0', c.OptimizationSolveRequest, OptimizationResult,
        'extensions.optimization.ipopt:optimization_solve_tool',
        'Solve an OptimizationProblem by EvidenceRef with IPOPT and save compact diagnostics.',
        dependencies=('numpy', 'casadi'), sources=SOURCES, contract_dependencies=DEPS,
        side_effects='artifact_store', extension_dependencies=(('solver.ipopt', '1.0.0'),),
        capabilities=dict(category='optimization', role='public_tool', route_visible=True,
                          evidence_input=True, evidence_output=True, backend_solves=0),
    ),
]
