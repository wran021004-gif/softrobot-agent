from tools.tool_registry import service_tools
from tools.platform_registry import Extension
from schemas.platform_operations import ServiceData

CONTRACTS = []
EXTENSIONS = [Extension(d.tool_id, 'tool', d.version, d.schema, d.output_schema or ServiceData,
    d.binding, d.description, sources=d.sources, cache=d.cache, legacy_service=d,
    side_effects='saved derivation; no numerical solves') for d in service_tools().values()]
