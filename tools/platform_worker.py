"""Isolated deterministic worker process; trusted code, NOT a hostile-code sandbox."""
import json
from pathlib import Path
import sys
import time
from schemas.platform import BackendResult, WorkOrder, WorkerOutput
from tools.state_io import read, atomic_json


class RestrictedClient:
    """Trusted application boundary, not OS isolation. Writes only child session."""
    def __init__(self, host, order):
        self._host, self.order = host, order

    def invoke(self, tool_id, arguments, request_id, reason='worker computation'):
        policy = self._host.store.session(self._host.run_id)['snapshot']['input']['policy']
        if tool_id not in self.order.allowed_tools:
            raise ValueError('WORKER_TOOL_NOT_GRANTED')
        return self._host.invoke(dict(request_id=request_id, tool_id=tool_id,
            tool_version=policy['tool_bindings'][tool_id], arguments=arguments, reason=reason))

    def read(self, reference, request_id='read-input'):
        if reference != self.order.input_snapshot:
            raise ValueError('WORKER_FIXED_INPUT_REQUIRED')
        receipt = self.invoke('evidence.read', dict(reference=reference.model_dump(mode='json')), request_id)
        return self.result(receipt)

    def result(self, receipt):
        if receipt['execution_status'] != 'completed':
            raise ValueError(receipt.get('error'))
        return self._host.store.artifact(receipt['output'])

    def usage(self):
        return self._host.store.remaining(self._host.run_id)['used']


def main():
    # Request contains no import paths. The installed worker ID resolves in the registry.
    path = Path(sys.argv[1]).resolve()
    request = read(path)
    order = WorkOrder.model_validate(request['order'])
    from tools.platform_registry import registry
    reg = registry()
    definition, parameters = reg.bind(order.worker, 'worker')
    from tools.platform_registry import dependency_identity
    # Input bytes were checked and copied by coordinator; no project writes permitted
    # by this worker API. OS permissions are NOT restricted by this contract.
    try:
        if dependency_identity(definition) != request['implementation']:
            raise ValueError('WORKER_IMPLEMENTATION_CHANGED')
        raw = read(path.parent / 'input.json')
        from tools.platform_store import encode
        import hashlib
        if hashlib.sha256(encode(raw).encode('utf8')).hexdigest() != order.input_snapshot.artifact_id:
            raise ValueError('WORKER_INPUT_HASH_MISMATCH')
        from tools.platform_host import Host
        client = RestrictedClient(Host(request['root'], request['child_run'], actor='worker:' + order.work_id), order)
        output = definition.resolve()(order, parameters, raw, client)
        definition.output_schema.model_validate(output)
        atomic_json(path.parent / 'output.json', output.model_dump(mode='json'))
    except Exception as exc:
        atomic_json(path.parent / 'failure.json', dict(error=str(exc)))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
