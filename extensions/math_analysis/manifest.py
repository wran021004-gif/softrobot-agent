"""Trusted numerical tools using the existing extension registry."""
from tools.platform_registry import Extension
from schemas.platform_analysis import MetricsRequest, LinearizeRequest, SavedCaseRequest, CompareRequest, AnalysisResult
from extensions.tendon_family.manifest import GVS_SOURCES

CONTRACTS=[]

SOURCES=(*GVS_SOURCES,'schemas/platform_analysis.py','extensions/math_analysis/kernels.py',
    'extensions/math_analysis/tools.py','extensions/math_analysis/matlab.py','extensions/math_analysis/manifest.py',
    'extensions/tendon_family/math_analysis.py','extensions/tendon_family/saved_cases.py',
    'schemas/platform_diagnostics.py')
EXTENSIONS=[]
for name,schema,binding,description,deps in (
    ('analysis.control_metrics',MetricsRequest,'extensions.math_analysis.tools:control_metrics','Batch output-aware local metrics from saved models and a frozen protocol',('numpy','scipy','matlab.engine')),
    ('analysis.linearize_saved_case',LinearizeRequest,'extensions.tendon_family.math_analysis:linearize_saved','World-tip AD linearization at up to five saved points plus one bounded equilibrium attempt',('numpy','scipy','casadi')),
    ('analysis.saved_case',SavedCaseRequest,'extensions.tendon_family.math_analysis:saved_case','Read bound saved execution observations and deterministic facts',('numpy',)),
    ('analysis.compare_case_metrics',CompareRequest,'extensions.math_analysis.tools:compare_case_metrics','Compare case metrics without causal attribution or classification',('numpy',))):
    caps=dict(category='analysis',role='public_tool',route_visible=True,backend_solves=0)
    if name=='analysis.control_metrics': caps['preflight']='extensions.math_analysis.tools:preflight'
    EXTENSIONS.append(Extension(name,'tool','1.0.0',schema,AnalysisResult,binding,description,
        sources=SOURCES,assets=('matlab/analyze_linear_model.m',),dependencies=deps,
        side_effects='artifact_store',cache=True,capabilities=caps))
