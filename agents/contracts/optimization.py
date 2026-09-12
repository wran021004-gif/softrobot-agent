"""Human-owned optimization authorization; no optimizer or caller-supplied bounds."""
import math
from typing import Literal
from pydantic import Field, model_validator
from schemas.common import Contract
from schemas.design_spec import DesignSpec
from capabilities.registry import get_robot_family_grammar


class VariablePolicy(Contract):
    name: str
    category: Literal["ROBOT_DESIGN"]
    unit: str = Field(min_length=1)
    optimizable: bool = Field(strict=True)
    lower_bound: float | None
    upper_bound: float | None
    constraints: tuple[Literal["positive", "integer"], ...]
    provenance: str = Field(min_length=1)
    scientific_status: Literal["human_approved", "human_approval_required"]

    @model_validator(mode="after")
    def approved_bounds(self):
        if self.optimizable and (self.scientific_status != "human_approved"
                or self.lower_bound is None or self.upper_bound is None
                or self.lower_bound > self.upper_bound):
            raise ValueError("PHYSICS_ASSUMPTION_REQUIRED: explicit Human-approved bounds required")
        return self


def validate_optimization_variables(family: str, names: tuple[str, ...]) -> tuple[VariablePolicy, ...]:
    """Reload the authoritative grammar on every check; examples grant no permission."""
    return _variables_from_grammar(get_robot_family_grammar(family), names)


def _variables_from_grammar(grammar, names, *, experiment_source=None):
    """Shared arithmetic; only trusted file resolvers provide grammar objects."""
    if len(set(names)) != len(names):
        raise ValueError("Duplicate optimization variables")
    if names and (grammar.get("optimization_policy", {}).get("owner") != "Human"
                  or not grammar["optimization_policy"].get("objective_source")):
        raise ValueError("PHYSICS_ASSUMPTION_REQUIRED: Human objective authority required")
    policies = []
    for name in names:
        field = grammar["design_fields"].get(name, {})
        scoped = field.get('experiment_optimization', {}).get(experiment_source)
        if grammar.get('exploration_envelope_source') and scoped is None:
            from tools.design_envelope import load_envelope, envelope_variables
            envelope, _ = load_envelope(grammar)
            policies.extend(envelope_variables(envelope, (name,)))
            continue
        # Only actual numeric DesignSpec fields may enter this morphology boundary.
        if name not in DesignSpec.model_fields or field.get("type") not in ("int", "float"):
            raise ValueError(f"Optimization variable denied: {name}")
        metadata = field.get("optimization")
        # A file-specific Human authorization does not grant general optimization.
        if experiment_source is not None:
            metadata = field.get("experiment_optimization", {}).get(experiment_source, metadata)
        if metadata is None:
            raise ValueError(f"PHYSICS_ASSUMPTION_REQUIRED: no policy for {name}")
        policy = VariablePolicy(name=name, unit=field.get("unit", ""), **metadata)
        if not policy.optimizable:
            raise ValueError(f"PHYSICS_ASSUMPTION_REQUIRED: {name} is not approved for optimization")
        policies.append(policy)
    return tuple(policies)


def validate_optimization_candidate(original: DesignSpec, candidate: DesignSpec, names: tuple[str, ...]) -> None:
    """Future executor must call immediately before accepting each candidate.

    No bounds/objective arguments: neither Engineer nor optimizer can widen policy.
    Full DesignSpec and the existing grammar/resolver still apply after this check.
    """
    original = DesignSpec.model_validate(original.model_dump())
    candidate = DesignSpec.model_validate(candidate.model_dump())
    policies = validate_optimization_variables(original.robot_family, names)
    _candidate_with_policies(original, candidate, policies)


def _candidate_with_policies(original, candidate, policies, *, grammar=None):
    effective_grammar = grammar or get_robot_family_grammar(original.robot_family)
    if effective_grammar.get('exploration_envelope_source'):
        from tools.design_envelope import load_envelope, validate_envelope_design
        envelope, _ = load_envelope(effective_grammar)
        validate_envelope_design(candidate, envelope)
    names = tuple(policy.name for policy in policies)
    for name in DesignSpec.model_fields:
        if name not in names and getattr(original, name) != getattr(candidate, name):
            raise ValueError(f"Unselected design field changed: {name}")
    for policy in policies:
        value = getattr(candidate, policy.name)
        if not math.isfinite(value) or not policy.lower_bound <= value <= policy.upper_bound:
            raise ValueError(f"Outside Human-approved bounds: {policy.name}")
        if "positive" in policy.constraints and value <= 0:
            raise ValueError(f"Positive constraint violated: {policy.name}")
        if "integer" in policy.constraints and int(value) != value:
            raise ValueError(f"Integer constraint violated: {policy.name}")
    from tools.capability_resolver import resolve_capability, CapabilityState
    if resolve_capability(candidate, grammar=grammar).state not in (CapabilityState.SUPPORTED, CapabilityState.PARAMETRICALLY_SUPPORTED):
        raise ValueError("Candidate is outside executable grammar")
