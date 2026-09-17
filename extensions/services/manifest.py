from tools.tool_registry import service_tools
from tools.platform_registry import Extension
from schemas.platform_operations import ServiceData

CONTRACTS = []
EXTENSIONS = [Extension(d.tool_id, 'tool', d.version, d.schema, d.output_schema or ServiceData,
    d.binding, d.description, sources=d.sources, cache=d.cache, legacy_service=d,
    capabilities=dict(category='mathematical_models' if d.tool_id.startswith('analysis.') else
        'platform_services' if d.tool_id.startswith('evidence.') else 'signals_diagnostics', role='public_tool',
        input_mode='legacy registered path' if d.input_refs else 'typed numerical input'),
    side_effects='saved derivation; no numerical solves') for d in service_tools().values()]
