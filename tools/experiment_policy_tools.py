"""Validate file-owned authority before any experimental numerical execution."""
from dataclasses import dataclass
from pathlib import Path
from schemas.experiment_policy import ExperimentPolicy
from schemas.design_spec import DesignSpec
from tools.spec_tools import ROOT, load_yaml, validate_design
from tools.artifact_tools import file_hash
from tools.task_contract_tools import resolve_task_contract
from agents.contracts.optimization import _variables_from_grammar, _candidate_with_policies


class ApprovalRequired(ValueError):
    pass


def repository_path(value):
    path = (ROOT / value).resolve()
    path.relative_to(ROOT)
    if not path.is_file():
        raise ValueError(f"Missing policy source: {value}")
    return path


@dataclass(frozen=True)
class ValidatedExperiment:
    path: Path
    policy: ExperimentPolicy
    policy_hash: str
    baseline: DesignSpec
    resolved: object
    input_hashes: dict
    envelope: dict | None = None

    def check_unchanged(self):
        if any(file_hash(path) != expected for path, expected in self.input_hashes.items()):
            raise ValueError("Experiment authority/input changed during execution")

    def validate_candidate(self, candidate):
        self.check_unchanged()
        candidate = DesignSpec.model_validate(candidate.model_dump() if isinstance(candidate, DesignSpec) else candidate)
        names = tuple(v.name for v in self.policy.variables)
        if self.envelope is not None:
            from tools.design_envelope import envelope_variables
            approved = envelope_variables(self.envelope, names, self.policy.purpose)
        else:
            approved = _variables_from_grammar(self.resolved.grammar, names,
                experiment_source=self.path.relative_to(ROOT).as_posix())
        _candidate_with_policies(self.baseline, candidate, approved, grammar=self.resolved.grammar)
        for v in self.policy.variables:
            if not v.lower_bound <= getattr(candidate, v.name) <= v.upper_bound:
                raise ValueError(f"Outside experiment bounds: {v.name}")
        return candidate


def load_experiment_policy(path):
    return ExperimentPolicy.model_validate(load_yaml(path))


def validate_experiment_policy(path) -> ValidatedExperiment:
    path = Path(path).resolve()
    path.relative_to(ROOT)
    policy = load_experiment_policy(path)
    if policy.approval_status == "HUMAN_APPROVAL_REQUIRED":
        raise ApprovalRequired("BLOCKED_FOR_HUMAN_APPROVAL: approve variables, bounds, routes, controller parameters and budgets")
    # File location is the existing Human-owned repository boundary, not authentication.
    owner_root = ROOT / ("tests/fixtures" if policy.scientific_status == "TEST_ONLY" else "configs/experiments")
    closeout = policy.authorization_mode == 'CLOSEOUT_SCOPED'
    subset = policy.authorization_mode == 'ENVELOPE_SUBSET' or closeout
    policy_roots = (ROOT/'configs/experiments', ROOT/'proposals/engineer', ROOT/'runs') if subset else (owner_root,)
    if not any(path.is_relative_to(root.resolve()) for root in policy_roots):
        raise ValueError("Experiment policy must reside in its owned source directory")
    resolved = resolve_task_contract(repository_path(policy.task_contract_source))
    if resolved.contract.contract_id != policy.task_contract_id or resolved.contract.status == "PROPOSED_NOT_APPROVED":
        raise ValueError("Experiment TaskContract identity/status mismatch")
    if policy.scientific_status == "TEST_ONLY" and resolved.contract.status != "DEVELOPMENT_ONLY":
        raise ValueError("TEST_ONLY policy cannot execute a frozen/formal task")
    grammar_path = resolved.source_paths['design_grammar_source']
    grammar_root = ROOT / ("tests/fixtures" if policy.scientific_status == "TEST_ONLY" else "capabilities")
    if not grammar_path.is_relative_to(grammar_root.resolve()):
        raise ValueError("Experimental grammar must reside in its Human/test-owned boundary")
    approval = repository_path(policy.approval_source)
    if not approval.is_relative_to(owner_root.resolve()):
        raise ValueError("Approval source must share the Human/test-owned boundary")
    baseline_path = repository_path(policy.baseline_design)
    baseline = validate_design(load_yaml(baseline_path))
    envelope = None
    extra_inputs = []
    if subset:
        from tools.design_envelope import load_envelope, envelope_variables, validate_envelope_design
        envelope, envelope_path = load_envelope(resolved.grammar)
        extra_inputs.append(envelope_path)
        if closeout:
            from tools.closeout_authority import validate_closeout_authority
            extra_inputs.extend(validate_closeout_authority(policy, path, envelope))
        if policy.scientific_status != 'HUMAN_APPROVED' or (not closeout and approval != repository_path(envelope['approval_source'])):
            raise ValueError('ENVELOPE_REQUIRED: reference the existing Human envelope approval')
        if (not set(policy.allowed_model_levels) <= set(envelope['allowed_model_levels']) or
                not set(policy.allowed_controller_levels) <= set(['C1', 'C2'] if closeout else envelope['allowed_controller_levels'])):
            raise ValueError('CAPABILITY_NOT_AUTHORIZED: envelope model/controller route')
        if policy.physics_profile != envelope['physics_profile'] or (not closeout and policy.feedback_parameters is not None):
            raise ValueError('PHYSICS_ASSUMPTION_REQUIRED: new physics/controller')
        if policy.repair_iteration_budget or policy.repair_actions:
            raise ValueError('REPAIR_NOT_AUTHORIZED: envelope exploration has no repair route')
        validate_envelope_design(baseline, envelope)
        approved = envelope_variables(envelope, tuple(v.name for v in policy.variables), policy.purpose)
    else:
        approved = _variables_from_grammar(resolved.grammar, tuple(v.name for v in policy.variables),
            experiment_source=path.relative_to(ROOT).as_posix())
        if resolved.grammar.get('exploration_envelope_source'):
            from tools.design_envelope import load_envelope
            _, envelope_path = load_envelope(resolved.grammar)
            extra_inputs.append(envelope_path)
    for selected, authority in zip(policy.variables, approved):
        if selected.unit != authority.unit:
            raise ValueError(f"Variable unit mismatch: {selected.name}")
        if not authority.lower_bound <= selected.lower_bound <= selected.upper_bound <= authority.upper_bound:
            raise ValueError(f"Experiment widens grammar bounds: {selected.name}")
        if not set(authority.constraints).issubset(selected.constraints):
            raise ValueError(f"Experiment omits grammar constraints: {selected.name}")
        field = resolved.grammar['design_fields'][selected.name]
        if field['unit'] != selected.unit:
            raise ValueError("TaskContract grammar unit mismatch")
    inputs = {p: file_hash(p) for p in (path, approval, baseline_path, resolved.manifest_path, *resolved.source_paths.values(), *extra_inputs)}
    result = ValidatedExperiment(path, policy, file_hash(path), baseline, resolved, inputs, envelope)
    result.validate_candidate(baseline)
    return result
