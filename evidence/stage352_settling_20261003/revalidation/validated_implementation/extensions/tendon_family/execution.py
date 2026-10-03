"""Resolve an explicit dynamics model against a registered execution backend."""
from tools.state_io import digest
from schemas.platform import Payload
from .contracts import DynamicsModel


def model_definition(parameters):
    """Registry target for the implemented mathematical-model definition."""
    return Payload(contract='family.dynamics_model',data=parameters.model_dump(mode='json'))


def resolve_execution(inp, reg):
    backend, numerical = reg.bind(inp.policy.backend,'backend')
    supported = backend.capabilities.get('models',{})
    if inp.policy.dynamics_model is not None:
        model, definition = reg.bind(inp.policy.dynamics_model,'dynamics_model')
        relation = supported.get(model.extension_id)
        if relation is None:
            raise ValueError('DYNAMICS_MODEL_BACKEND_UNSUPPORTED: '+model.extension_id+' -> '+backend.extension_id)
        source = 'ExperimentPolicy.dynamics_model'
    else:
        # Compatibility only: old snapshots encoded the implementation model
        # in family.parameters. There must be exactly one matching relation.
        implementation = getattr(numerical,'model',None)
        matches=[(name,value) for name,value in supported.items()
                 if value.get('implementation_model_id')==implementation]
        if len(matches)!=1:
            raise ValueError('DYNAMICS_MODEL_SELECTION_REQUIRED')
        name,relation=matches[0]
        model=reg.get(name,kind='dynamics_model')
        definition=DynamicsModel()
        source='legacy backend parameter model compatibility'
    expected=relation['implementation_model_id']
    declared=getattr(numerical,'model',expected)
    if declared!=expected:
        raise ValueError('BACKEND_MODEL_IDENTITY_MISMATCH')
    model_data=definition.model_dump(mode='json')
    numerical_data=numerical.model_dump(mode='json')
    result=dict(dynamics_model_id=model.extension_id,dynamics_model_version=model.version,
        dynamics_model=model_data,dynamics_model_identity=digest(dict(extension_id=model.extension_id,version=model.version,parameters=model_data)),
        backend_id=backend.extension_id,backend_version=backend.version,
        implementation_model_id=expected,implementation=relation['implementation'],
        numerical_configuration=numerical_data,selection_source=source,
        contact_semantics=relation['contact_semantics'])
    result['identity']=digest(result)
    return result
