"""Small deterministic validators for Human-approved surrogate exploration."""
from pathlib import Path
from schemas.design_spec import DesignSpec
from tools.spec_tools import ROOT, load_yaml


def load_envelope(grammar):
    source = grammar.get('exploration_envelope_source')
    if not source:
        raise ValueError('ENVELOPE_REQUIRED: grammar has no approved exploration envelope')
    path = (ROOT / source).resolve()
    if not path.is_relative_to((ROOT/'capabilities').resolve()):
        raise ValueError('ENVELOPE_REQUIRED: authority must reside under capabilities')
    envelope = load_yaml(path)
    if envelope.get('owner') != 'Human' or envelope.get('scientific_status') != 'HUMAN_APPROVED_SURROGATE_EXPLORATION_ONLY':
        raise ValueError('ENVELOPE_REQUIRED: missing Human authorization')
    if envelope.get('robot_family') != grammar['family_name']:
        raise ValueError('OUT_OF_ENVELOPE: robot family mismatch')
    return envelope, path


def validate_relations(candidate, relations):
    # Deliberately no expression evaluation or constraint language.
    for relation in relations:
        left, right = relation['left'], relation['right']
        if relation['operator'] != 'lt' or left not in DesignSpec.model_fields or right not in DesignSpec.model_fields:
            raise ValueError('UNSUPPORTED_RELATIONAL_CONSTRAINT')
        if not getattr(candidate, left) < getattr(candidate, right):
            raise ValueError(f'RELATIONAL_CONSTRAINT_VIOLATION: {left} < {right}')


def validate_envelope_design(candidate, envelope):
    candidate = DesignSpec.model_validate(candidate)
    if candidate.robot_family != envelope['robot_family']:
        raise ValueError('OUT_OF_ENVELOPE: robot family')
    for name, field in envelope['fields'].items():
        value = getattr(candidate, name)
        if 'supported_values' in field:
            if value not in field['supported_values']:
                raise ValueError(f'UNSUPPORTED_SECTIONS: {name} must be one')
        elif not field['lower_bound'] <= value <= field['upper_bound']:
            raise ValueError(f'OUT_OF_ENVELOPE: {name}')
    validate_relations(candidate, envelope['relational_constraints'])
    return candidate


def envelope_variables(envelope, names, purpose='DESIGN_SEARCH'):
    from agents.contracts.optimization import VariablePolicy
    if len(names) != len(set(names)):
        raise ValueError('Duplicate optimization variables')
    if purpose == 'NUMERICAL_SENSITIVITY' and tuple(names) != ('segments',):
        raise ValueError('NUMERICAL_SENSITIVITY_ONLY: vary segments alone')
    policies = []
    for name in names:
        field = envelope['fields'].get(name)
        if field is None:
            raise ValueError(f'PHYSICS_ASSUMPTION_REQUIRED: unauthorized variable {name}')
        status = field['optimization_status']
        if status not in ('AUTHORIZED', 'AUTHORIZED_DISCRETE'):
            if not (status == 'NUMERICAL_SENSITIVITY_ONLY' and purpose == 'NUMERICAL_SENSITIVITY'):
                raise ValueError(f'{status}: {name}')
        policies.append(VariablePolicy(name=name, category='ROBOT_DESIGN', unit=field['unit'],
            optimizable=True, lower_bound=field['lower_bound'], upper_bound=field['upper_bound'],
            constraints=tuple(field['constraints']), provenance=envelope['approval_source'],
            scientific_status='human_approved'))
    return tuple(policies)
