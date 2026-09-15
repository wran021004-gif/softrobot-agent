"""Trusted repository extension declarations; discovery never starts engines.

Only developers install Python packages. Config/model values cannot name modules.
"""
from dataclasses import dataclass, field
from importlib import import_module, util, metadata
from pathlib import Path
import ast
import sys
from schemas.common import Contract
from schemas.platform import Payload, Binding, VERSION
from tools.spec_tools import ROOT
from tools.state_io import digest
from tools.artifact_tools import file_hash


@dataclass(frozen=True)
class Extension:
    extension_id: str
    kind: str
    version: str
    input_schema: type[Contract]
    output_schema: type[Contract]
    binding: str | None
    description: str
    dependencies: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    cache: bool = False
    side_effects: str = 'none'
    capabilities: dict = field(default_factory=dict)
    legacy_service: object | None = None

    def resolve(self):
        if not self.binding:
            raise ValueError('IMPLEMENTATION_REQUIRED: ' + self.extension_id)
        module, name = self.binding.split(':')
        return getattr(import_module(module), name)


class Registry:
    def __init__(self, definitions=(), contracts=()):
        self.extensions = {}
        self.contracts = {}
        for name, version, schema in contracts:
            self.add_contract(name, version, schema)
        for definition in definitions:
            self.add(definition)

    def add_contract(self, name, version, schema):
        key = (name, version)
        if key in self.contracts:
            raise ValueError('DUPLICATE_CONTRACT: ' + repr(key))
        self.contracts[key] = schema

    def add(self, definition):
        key = (definition.extension_id, definition.version)
        if key in self.extensions:
            raise ValueError('DUPLICATE_EXTENSION: ' + repr(key))
        self.extensions[key] = definition

    def get(self, name, version=VERSION, kind=None):
        definition = self.extensions.get((name, version))
        if definition is None:
            raise ValueError(f'IMPLEMENTATION_REQUIRED: {name}@{version}; 登记实现及输入输出契约到 extensions/<包>/manifest.py')
        if kind and definition.kind != kind:
            raise ValueError('EXTENSION_KIND_MISMATCH: ' + name)
        return definition

    def parse(self, payload):
        payload = Payload.model_validate(payload)
        schema = self.contracts.get((payload.contract, payload.version))
        if schema is None:
            raise ValueError(f'CONTRACT_IMPLEMENTATION_REQUIRED: {payload.contract}@{payload.version}')
        return schema.model_validate_json(__import__('json').dumps(payload.data, allow_nan=False), strict=True)

    def bind(self, binding, kind):
        binding = Binding.model_validate(binding)
        definition = self.get(binding.extension_id, binding.version, kind)
        parsed = self.parse(binding.parameters)
        if type(parsed) is not definition.input_schema:
            raise ValueError('BINDING_PARAMETER_CONTRACT_MISMATCH: ' + binding.extension_id)
        return definition, parsed

    def inspect(self, definition, allowed=None):
        reasons = []
        exists = False
        if definition.binding:
            module, name = definition.binding.split(':')
            path = ROOT / (module.replace('.', '/') + '.py')
            if path.is_file():
                nodes = ast.parse(path.read_text(encoding='utf8')).body
                exists = any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name for n in nodes)
        if not exists:
            reasons.append('IMPLEMENTATION_REQUIRED')
        missing = []
        for dep in definition.dependencies:
            # Top-level availability does not launch or import optional runtimes.
            if dep == 'matlab.engine':
                try:
                    metadata.distribution('matlabengine')
                except metadata.PackageNotFoundError:
                    missing.append(dep)
            elif util.find_spec(dep.split('.')[0]) is None:
                missing.append(dep)
        if missing:
            reasons.append('DEPENDENCY_MISSING: ' + ', '.join(missing))
        permitted = allowed is not None and definition.extension_id in allowed
        if not permitted:
            reasons.append('NOT_GRANTED' if allowed is not None else 'NO_SESSION_POLICY')
        return dict(extension_id=definition.extension_id, kind=definition.kind, version=definition.version,
                    declared=True, implementation_exists=exists, dependencies_available=not missing,
                    permitted=permitted, executable=exists and not missing and permitted,
                    runtime_probe='not_started', reasons=reasons, description=definition.description,
                    input_schema=definition.input_schema.model_json_schema(), output_schema=definition.output_schema.model_json_schema(),
                    capabilities=definition.capabilities, resources=list(definition.resources),
                    dependencies=list(definition.dependencies), side_effects=definition.side_effects)

    def catalog(self, allowed=None):
        return [self.inspect(d, allowed) for _, d in sorted(self.extensions.items())]


def registry():
    result = Registry()
    # Each trusted package owns its declarations; deterministic names and conflicts.
    for manifest in sorted((ROOT / 'extensions').glob('*/manifest.py')):
        package = import_module('extensions.' + manifest.parent.name + '.manifest')
        for name, version, schema in package.CONTRACTS:
            result.add_contract(name, version, schema)
        for definition in package.EXTENSIONS:
            result.add(definition)
    return result


def dependency_identity(definition):
    paths = set(definition.sources)
    if definition.binding:
        paths.add(definition.binding.split(':')[0].replace('.', '/') + '.py')
    paths.update(('schemas/platform.py', 'schemas/common.py', 'tools/platform_registry.py', 'tools/platform_host.py', 'tools/platform_store.py'))
    if definition.legacy_service is not None:
        paths.update(('tools/tool_registry.py', 'tools/service_execution.py', 'tools/service_worker.py',
                      'schemas/public_tools.py', 'extensions/services/manifest.py'))
    # Undeclared transitive sets are conservative, with an explicit reason.
    conservative = not definition.sources
    if conservative:
        for folder in ('tools', 'schemas', 'controllers', 'extensions', 'physics_contracts', 'matlab', 'configs'):
            paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob('*')
                         if p.is_file() and p.suffix in ('.py', '.yaml', '.xml', '.m'))
    versions = {}
    for dep in ('pydantic', *definition.dependencies):
        try:
            versions[dep] = metadata.version('matlabengine' if dep == 'matlab.engine' else dep)
        except metadata.PackageNotFoundError:
            versions[dep] = None
    return dict(sources={p: file_hash(ROOT / p) for p in sorted(paths)},
                python=sys.version, packages=versions, version=definition.version,
                input_schema=definition.input_schema.model_json_schema(), output_schema=definition.output_schema.model_json_schema(),
                declaration=dict(kind=definition.kind, binding=definition.binding, capabilities=definition.capabilities,
                    resources=list(definition.resources), cache=definition.cache, side_effects=definition.side_effects),
                conservative_reason='transitive dependencies not bounded; source/config tree invalidates' if conservative else None)
