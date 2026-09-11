"""Resolve existing truth by reference; resolution never approves or promotes it."""
from dataclasses import dataclass
import hashlib
import importlib
import inspect
from pathlib import Path
from typing import Callable
import yaml

from schemas.task_contract import TaskContract
from schemas.task_spec import TaskSpec
from schemas.environment_spec import EnvironmentSpec
from schemas.settings import RunSettings, SimulatorSpec
from tools.spec_tools import ROOT, load_yaml, validate_frozen_environment


def load_task_contract(path) -> TaskContract:
    path = Path(path)
    return TaskContract.model_validate(load_yaml(path / 'contract.yaml' if path.is_dir() else path))


@dataclass(frozen=True)
class ResolvedTaskContract:
    contract: TaskContract
    manifest_path: Path
    manifest_hash: str
    source_paths: dict[str, Path]
    source_hashes: dict[str, str]
    task: TaskSpec | None
    environment: EnvironmentSpec | None
    grammar: dict
    run_settings: RunSettings
    simulator_settings: SimulatorSpec
    evaluator: Callable | None
    unresolved: tuple[str, ...] = ()

    def reference_view(self):
        """Artifact view contains references/hashes only, never copied truth values."""
        return {
            'contract_id': self.contract.contract_id, 'status': self.contract.status,
            'contract_source': self.manifest_path.relative_to(ROOT).as_posix(),
            'task_type': self.contract.task_type, 'contract_hash': self.manifest_hash,
            'source_paths': {key: p.relative_to(ROOT).as_posix() for key, p in self.source_paths.items()},
            'source_hashes': self.source_hashes, 'evaluator_id': self.contract.evaluator,
            'gate_policy_id': 'schemas.gate.gate_action', 'benchmark_id': self.contract.benchmark_id,
            'executable': self.contract.status != 'PROPOSED_NOT_APPROVED',
            'unresolved': list(self.unresolved),
            'source_snapshot': 'source_snapshot.zip (paths relative to repository root)',
        }


def resolve_task_contract(path) -> ResolvedTaskContract:
    path = Path(path)
    path = (path / 'contract.yaml' if path.is_dir() else path).resolve()
    manifest_bytes = path.read_bytes()
    contract = TaskContract.model_validate(yaml.safe_load(manifest_bytes))
    # ./ is package-relative; other references are repository-relative. No search
    # fallback: moving a package cannot silently select a different authority.
    def source(name):
        result = ((path.parent / name) if name.startswith('./') else (ROOT / name)).resolve()
        result.relative_to(ROOT)
        if not result.is_file():
            raise ValueError(f'Missing TaskContract source: {name}')
        return result

    paths = {key: source(value) for key, value in contract.model_dump().items()
             if key.endswith('_source') and value is not None}
    for index, name in enumerate(contract.physics_contract_sources):
        paths[f'physics_contract_{index}'] = source(name)
    module_name, _, symbol = contract.evaluator.rpartition('.')
    try:
        evaluator = getattr(importlib.import_module(module_name), symbol)
        if not callable(evaluator) or contract.task_type not in getattr(evaluator, 'supported_task_types', ()):
            raise ValueError('TaskContract evaluator does not support task_type')
        paths['evaluator_source'] = Path(inspect.getsourcefile(evaluator)).resolve()
        paths['evaluator_source'].relative_to(ROOT)
    except (ImportError, AttributeError, TypeError) as exc:
        raise ValueError('TaskContract evaluator is not an implemented task evaluator') from exc
    content = {key: p.read_bytes() for key, p in paths.items()}
    hashes = {key: hashlib.sha256(data).hexdigest() for key, data in content.items()}
    load = lambda key: yaml.safe_load(content[key])
    task_data, env_data = load('task_source'), load('environment_source')
    if task_data['task_type'] != contract.task_type or task_data['environment_id'] != env_data['environment_id']:
        raise ValueError('TaskContract task type / environment identity mismatch')
    grammar = load('design_grammar_source')
    if not grammar.get('family_name') or not grammar.get('design_fields'):
        raise ValueError('TaskContract requires a Design Grammar, not a concrete DesignSpec')

    # This small Harness supports the existing policy/protocol/physics only. Bind
    # those implementations explicitly; never accept an ignored alternative.
    for key, expected in {'gate_policy_source': 'schemas/gate.py', 'gate_mapping_source': 'tools/harness.py',
                          'evaluation_protocol_source': 'tools/harness.py'}.items():
        if paths[key] != (ROOT / expected).resolve():
            raise ValueError(f'IMPLEMENTATION_REQUIRED: unsupported {key}')
    from tools.design_compiler import CONTRACTS
    expected_physics = {(ROOT / 'physics_contracts' / name).resolve() for name in (*CONTRACTS, 'legacy_v1_surrogate.yaml')}
    if {p for key, p in paths.items() if key.startswith('physics_contract_')} != expected_physics:
        raise ValueError('PHYSICS_ASSUMPTION_REQUIRED: TaskContract physics does not match implemented V1')

    unresolved = ()
    task = environment = None
    if contract.status == 'PROPOSED_NOT_APPROVED':
        # Draft YAML is intentionally not executable TaskSpec/EnvironmentSpec.
        # Do not strip approval markers or invent a typed approved environment.
        if not contract.acceptance_source or any(load(key).get('truth_status') != 'PROPOSED_NOT_APPROVED'
                for key in ('task_source', 'environment_source', 'acceptance_source')):
            raise ValueError('Proposal contract must reference explicitly unapproved candidate sources')
        if paths['initial_condition_source'] != paths['acceptance_source']:
            raise ValueError('Proposal initial condition must reference its pending acceptance source')
        unresolved = ('Human approval of exact benchmark values and acceptance',
                      'Exact initial configuration and initialization support remain unresolved')
    else:
        task, environment = TaskSpec.model_validate(task_data), EnvironmentSpec.model_validate(env_data)
        if contract.environment_representation_source is None:
            raise ValueError('Executable contract must reference its existing environment representation')
        validate_frozen_environment(environment, paths['environment_representation_source'])
        if paths['initial_condition_source'] != (ROOT / 'tools/mujoco_tools.py').resolve():
            raise ValueError('IMPLEMENTATION_REQUIRED: unsupported initial-state implementation')
        if contract.acceptance_source:
            if paths['acceptance_source'] not in (paths['task_source'], (ROOT / 'schemas/task_spec.py').resolve()):
                raise ValueError('IMPLEMENTATION_REQUIRED: independent executable acceptance source')
        if contract.status == 'DEVELOPMENT_ONLY':
            if environment.truth_status != 'NON_CANONICAL_DEVELOPMENT_ONLY':
                raise ValueError('Development contract requires development environment truth status')
        elif environment.truth_status not in ('HUMAN_OWNED', 'HUMAN_APPROVED'):
            raise ValueError('FROZEN contract cannot reference development or proposed environment')
        if contract.status == 'FROZEN' and contract.task_type == 'reach_window':
            if environment.truth_status != 'HUMAN_APPROVED' or task.acceptance is None:
                raise ValueError('Frozen window requires approved environment and explicit acceptance')

    if contract.benchmark_id is not None:
        if contract.status != 'FROZEN' or contract.benchmark_source is None:
            raise ValueError('Only a FROZEN contract can bind an existing benchmark')
        benchmark = load('benchmark_source')
        entries = [entry for entry in benchmark['tasks'] if
                   (ROOT / entry['package'] / 'task.yaml').resolve() == paths['task_source'] and
                   (ROOT / entry['package'] / 'environment.yaml').resolve() == paths['environment_source']]
        if (benchmark['benchmark_id'] != contract.benchmark_id or len(entries) != 1 or
                entries[0].get('truth_status') != 'FROZEN' or entries[0]['evaluator'] != contract.evaluator):
            raise ValueError('Frozen TaskContract sources/evaluator differ from registered benchmark')
    elif contract.benchmark_source is not None or (contract.status == 'FROZEN' and env_data.get('truth_status') != 'HUMAN_APPROVED'):
        raise ValueError('FROZEN requires registered Human-owned truth or explicitly HUMAN_APPROVED standalone truth')

    return ResolvedTaskContract(contract, path, hashlib.sha256(manifest_bytes).hexdigest(), paths, hashes,
        task, environment, grammar, RunSettings.model_validate(load('run_settings_source')),
        SimulatorSpec.model_validate(load('simulator_settings_source')),
        evaluator if task is not None else None, unresolved)
