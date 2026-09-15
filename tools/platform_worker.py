"""Isolated deterministic worker process; trusted code, NOT a hostile-code sandbox."""
import json
from pathlib import Path
import sys
import time
from schemas.platform import BackendResult, WorkOrder, WorkerOutput
from tools.state_io import read, atomic_json


def run_signal_worker(order, parameters, raw):
    started = time.time()
    result = BackendResult.model_validate(raw)
    time.sleep(parameters.delay_s)
    if parameters.inject == 'failure':
        raise ValueError('INJECTED_WORKER_FAILURE')
    signal = next((s for s in result.signals if s.spec.name == parameters.signal), None)
    return WorkerOutput(work_id=order.work_id, base_candidate=order.base_candidate, source=order.input_snapshot,
        signal=parameters.signal, status='observed' if signal else 'missing_data',
        sample_indices=list(range(len(signal.values))) if signal else [], values=signal.values if signal else [],
        claim_key='injected_shared_claim' if parameters.inject == 'conflict' else parameters.signal,
        conclusion=('conflicting_' + parameters.signal) if parameters.inject == 'conflict' else ('saved_samples_present' if signal else 'missing_data'),
        started_at=started, ended_at=time.time())


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
        output = definition.resolve()(order, parameters, raw)
        definition.output_schema.model_validate(output)
        atomic_json(path.parent / 'output.json', output.model_dump(mode='json'))
    except Exception as exc:
        atomic_json(path.parent / 'failure.json', dict(error=str(exc)))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
