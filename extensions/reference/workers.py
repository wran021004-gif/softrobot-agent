"""Reference signal payload and checker; no domain assumptions in coordinator."""
import time
from schemas.platform import BackendResult, WorkerOutput, Payload, LegacyWorkerOutput
from tools.platform_store import plain


def run_signal_worker(order, parameters, raw, client):
    started = time.time()
    client.read(order.input_snapshot)
    result = BackendResult.model_validate(raw)
    time.sleep(parameters.delay_s)
    if parameters.inject == 'failure':
        raise ValueError('INJECTED_WORKER_FAILURE')
    signal = next((s for s in result.signals if s.spec.name == parameters.signal), None)
    payload = LegacyWorkerOutput(work_id=order.work_id, base_candidate=order.base_candidate, source=order.input_snapshot,
        signal=parameters.signal, status='observed' if signal else 'missing_data',
        sample_indices=list(range(len(signal.values))) if signal else [], values=signal.values if signal else [],
        claim_key='injected_shared_claim' if parameters.inject == 'conflict' else parameters.signal,
        conclusion='conflicting_' + parameters.signal if parameters.inject == 'conflict' else 'saved_samples_present' if signal else 'missing_data',
        started_at=started, ended_at=time.time())
    return WorkerOutput(work_id=order.work_id, base_candidate=order.base_candidate, source=order.input_snapshot,
        status='completed', result=Payload(contract='reference.signal_report', data=plain(payload)), usage=client.usage(),
        claim_key=payload.claim_key, conclusion=payload.conclusion, started_at=started, ended_at=time.time())


def check_signal(order, output, source, reg, evidence):
    payload = reg.parse(output.result)
    parameters = reg.parse(order.worker.parameters)
    raw = BackendResult.model_validate(source)
    signal = next((s for s in raw.signals if s.spec.name == parameters.signal), None)
    if payload.signal != parameters.signal or payload.values != (signal.values if signal else []):
        raise ValueError('WORKER_SAMPLE_EVIDENCE_MISMATCH')
    if payload.sample_indices != (list(range(len(signal.values))) if signal else []):
        raise ValueError('WORKER_SAMPLE_EVIDENCE_MISMATCH')
