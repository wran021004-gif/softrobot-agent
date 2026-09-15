"""Default control-only candidate adapter; extensions own other design semantics."""


def apply_control(inp, parameters, changes):
    for key, value in changes.items():
        group, name = key.split('.', 1)
        if group != 'controller':
            raise ValueError('PARAMETER_ADAPTER_REQUIRED: ' + key)
        inp.policy.controller.parameters.data[name] = value
    return inp
