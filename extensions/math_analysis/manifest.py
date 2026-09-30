"""Trusted numerical tools using the existing extension registry."""
from tools.platform_registry import Extension
from schemas.platform_analysis import (MetricsRequest, LinearizeRequest, SavedLinearizeRequestV2, SavedCaseRequest, CompareRequest,
    CandidateLinearizeRequest, BoundedEndpointRequest, DesignScreenRequest, MathOptimizeRequest,
    MathOptimizationResult, AnalysisResult)
from extensions.tendon_family.manifest import GVS_SOURCES

CONTRACTS=[]

SOURCES=(*GVS_SOURCES,'schemas/platform_analysis.py','extensions/math_analysis/kernels.py',
    'extensions/math_analysis/tools.py','extensions/math_analysis/matlab.py','extensions/math_analysis/manifest.py',
    'extensions/tendon_family/math_analysis.py','extensions/tendon_family/saved_cases.py',
    'extensions/tendon_family/candidate_analysis.py','extensions/tendon_family/model_applicability.py',
    'schemas/platform_diagnostics.py')
MATLAB_ASSETS=('matlab/analyze_linear_model.m','matlab/analyze_bounded_endpoint.m',
    'matlab/bounded_residual_certificate.m')
EXTENSIONS=[]
for name,schema,binding,description,deps in (
    ('analysis.control_metrics',MetricsRequest,'extensions.math_analysis.tools:control_metrics','Batch output-aware local metrics from saved models and a frozen protocol',('numpy','scipy','matlab.engine')),
    ('analysis.linearize_saved_case',LinearizeRequest,'extensions.tendon_family.math_analysis:linearize_saved','World-tip AD linearization at up to five saved points plus one bounded equilibrium attempt',('numpy','scipy','casadi')),
    ('analysis.saved_case',SavedCaseRequest,'extensions.tendon_family.math_analysis:saved_case','Read bound saved execution observations and deterministic facts',('numpy',)),
    ('analysis.compare_case_metrics',CompareRequest,'extensions.math_analysis.tools:compare_case_metrics','Compare case metrics without causal attribution or classification',('numpy',))):
    caps=dict(category='analysis',role='public_tool',route_visible=True,backend_solves=0)
    if name=='analysis.control_metrics': caps['preflight']='extensions.math_analysis.tools:preflight'
    EXTENSIONS.append(Extension(name,'tool','1.0.0',schema,AnalysisResult,binding,description,
        sources=SOURCES,assets=MATLAB_ASSETS,dependencies=deps,
        side_effects='artifact_store',cache=True,capabilities=caps))

# Changed boundary behavior is explicitly versioned. MATLAB is selected at
# invocation preflight, so SciPy discovery has no optional Engine dependency.
for name,schema,binding,description,deps in (
    ('analysis.control_metrics',MetricsRequest,'extensions.math_analysis.tools:control_metrics','Continuous-model local metrics with exact aligned held horizons and optional MATLAB implementation',('numpy','scipy')),
    ('analysis.linearize_saved_case',SavedLinearizeRequestV2,'extensions.tendon_family.math_analysis:linearize_saved','World-tip position and full moving-state velocity linearization at requested saved points',('numpy','scipy','casadi')),
    ('analysis.saved_case',SavedCaseRequest,'extensions.tendon_family.math_analysis:saved_case','Phase-aware saved divergence facts with separate backend finite differences and GVS velocity',('numpy','casadi')),
):
    caps=dict(category='analysis',role='public_tool',route_visible=True,backend_solves=0)
    if name=='analysis.control_metrics': caps['preflight']='extensions.math_analysis.tools:preflight'
    EXTENSIONS.append(Extension(name,'tool','2.0.0',schema,AnalysisResult,binding,description,
        sources=SOURCES,assets=MATLAB_ASSETS,dependencies=deps,
        side_effects='artifact_store',cache=True,capabilities=caps))

EXTENSIONS.extend([
    Extension('analysis.linearize_candidate','tool','1.0.0',CandidateLinearizeRequest,AnalysisResult,
        'extensions.tendon_family.math_analysis:linearize_candidate',
        'Configuration-only position/velocity local models for an explicit owned completed build node',
        sources=SOURCES,dependencies=('numpy','scipy','casadi'),side_effects='artifact_store',cache=True,
        capabilities=dict(category='analysis',role='public_tool',route_visible=True,backend_solves=0)),
    Extension('analysis.bounded_endpoint','tool','1.0.0',BoundedEndpointRequest,AnalysisResult,
        'extensions.math_analysis.tools:bounded_endpoint_analysis',
        'Exact-ZOH task-time bounded position correction and terminal braking diagnostics',
        sources=SOURCES,dependencies=('numpy','scipy'),side_effects='artifact_store',cache=True,
        capabilities=dict(category='analysis',role='public_tool',route_visible=True,backend_solves=0)),
    Extension('design.screen','tool','1.0.0',DesignScreenRequest,AnalysisResult,
        'extensions.math_analysis.tools:design_screen',
        'Structured deterministic candidate screen over shared local metrics, bounds and applicability',
        sources=SOURCES,dependencies=('numpy',),side_effects='artifact_store',cache=True,
        capabilities=dict(category='analysis',role='public_tool',route_visible=True,backend_solves=0)),
    Extension('design.optimize_math','tool','1.0.0',MathOptimizeRequest,MathOptimizationResult,
        'extensions.tendon_family.optimization:optimize_math',
        'Deterministic bounded search over near/far length, section scale and material scenario. Primary is controller-start frozen local exact-ZOH position residual/tolerance; secondary is position-feasible witness energy. Terminal braking and other sampled configurations are excluded. Cumulative Route evaluation accounting; advisory, not a nonlinear reach/settling/real-time/global-optimality prediction.',
        sources=SOURCES,dependencies=('numpy','scipy','casadi'),side_effects='artifact_store',cache=True,
        capabilities=dict(category='parameter_search',role='public_tool',route_visible=True,backend_solves=0,
            provider_calls=0,nmpc_solves=0,maximum_distinct_evaluations=24)),
])
