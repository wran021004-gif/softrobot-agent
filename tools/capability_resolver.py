"""Metadata-only resolution; never executes a PLANNED tool or invents physics."""
from enum import Enum
from pydantic import ValidationError
from schemas.common import Contract
from schemas.design_spec import DesignSpec
from capabilities.registry import get_robot_family_grammar, get_tool_manifest, list_tool_bundles


class CapabilityState(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARAMETRICALLY_SUPPORTED = "PARAMETRICALLY_SUPPORTED"
    IMPLEMENTATION_REQUIRED = "IMPLEMENTATION_REQUIRED"
    OUT_OF_GRAMMAR = "OUT_OF_GRAMMAR"
    PHYSICS_ASSUMPTION_REQUIRED = "PHYSICS_ASSUMPTION_REQUIRED"


class Resolution(Contract):
    state: CapabilityState
    reason: str


def resolve_capability(design, requested_tools=(), physics_profile="legacy_v1_surrogate", *,
                       model_level="M1", control_level="C1", grammar=None) -> Resolution:
    try:
        design = DesignSpec.model_validate(design)
        grammar = grammar if grammar is not None else get_robot_family_grammar(design.robot_family)
    except (ValidationError, KeyError):
        return Resolution(state=CapabilityState.OUT_OF_GRAMMAR, reason="Invalid design or unregistered family")
    fields = grammar["design_fields"]
    for name, field in fields.items():
        value = getattr(design, name)
        # Legacy supported_values is the current legal boundary until Human publishes allowed_values.
        allowed = field.get("allowed_values", field.get("supported_values"))
        if allowed is not None and value not in allowed:
            return Resolution(state=CapabilityState.OUT_OF_GRAMMAR, reason=f"{name} outside approved grammar")
    if physics_profile != "legacy_v1_surrogate":
        return Resolution(state=CapabilityState.PHYSICS_ASSUMPTION_REQUIRED, reason="Requested physics profile has no approved contract")
    if model_level not in ("M0", "M1") or control_level not in ("C0", "C1"):
        return Resolution(state=CapabilityState.IMPLEMENTATION_REQUIRED, reason="Requested model/control level is not implemented")
    if design.sections != 1:
        return Resolution(state=CapabilityState.IMPLEMENTATION_REQUIRED, reason="Grammar permits design but V1 compiler implements sections=1 only")
    manifests = {}
    for bundle in list_tool_bundles():
        manifests.update(get_tool_manifest(bundle)["tools"])
    for name in requested_tools:
        if manifests.get(name, {}).get("implementation_status") != "IMPLEMENTED":
            return Resolution(state=CapabilityState.IMPLEMENTATION_REQUIRED, reason=f"Tool {name} is not implemented")
    parametric = any(getattr(design, name) != field.get("example_value", getattr(design, name)) for name, field in fields.items())
    return Resolution(state=CapabilityState.PARAMETRICALLY_SUPPORTED if parametric else CapabilityState.SUPPORTED,
                      reason="Executable V1 structure; no claim of scientific feasibility or task success")
