"""Small counted communication check; never imports experiment evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):os.environ[name] = '1'
from tools.state_io import read, atomic_json
from tools.model_transports.deepseek import request_completion, sanitize_provider_text
from examples.gvs_nmpc_route_experiment import load_credential

DIRECTORY = ROOT/'evidence/stage352_settling_20261003'
PROVIDER = ROOT/'evidence/stage346_shared_diagnosis_20261002/pilot/freeze.json'
LIMITS = dict(model_calls=2, tool_calls=5, wall_s=180., backend_solves=0, worker_calls=0)


def main(credential, transient_check=None):
    path = DIRECTORY/'preflight.json'
    record = read(path) if path.exists() else dict(attempts=[], limits=LIMITS,
        classification='Connectivity validation only; never experiment memory', monetary_cost=None)
    if record['attempts'] and (not transient_check or record['attempts'][-1]['status'] != 'failed'):
        raise ValueError('SECOND_ATTEMPT_REQUIRES_FAILED_PRIMARY_AND_DOCUMENTED_CHECK')
    used = sum(row['charged_wall_s'] for row in record['attempts'])
    if len(record['attempts']) >= 2 or used >= 180.:raise ValueError('PREFLIGHT_CEILING_EXHAUSTED')
    guard = DIRECTORY/f'preflight_attempt_{len(record["attempts"])+1}.json'
    if guard.exists():raise ValueError('ATTEMPT_ALREADY_STARTED_PRESERVE_RECORD')
    config = read(PROVIDER)['provider_configuration']
    config['adapter_version'] = '4.0.0'
    expected = dict(base_url='https://api.deepseek.com', model='deepseek-flash', thinking='enabled', reasoning_effort='high', max_tokens=65536)
    if any(config[k] != v for k,v in expected.items()):raise ValueError('PROVIDER_SETTINGS_CHANGED')
    config['timeout_s'] = min(config['timeout_s'], 85., 180.-used)
    load_credential(credential)
    key = os.environ['DEEPSEEK_API_KEY']
    payload = dict(model=config['model'], messages=[dict(role='user', content='Reply briefly with: Connection verified.')],
        max_tokens=config['max_tokens'], thinking=dict(type=config['thinking']), reasoning_effort=config['reasoning_effort'], stream=False)
    attempt = dict(number=len(record['attempts'])+1, started=datetime.now(timezone.utc).isoformat(),
        timeout_s=config['timeout_s'], corrective_action_or_transient_check=transient_check, request=payload,
        provider_configuration=config, adapter_version='4.0.0', status='started')
    atomic_json(guard, attempt)
    started = time.monotonic()
    try:
        response = request_completion(config, payload, key)
        attempt.update(status='completed', response=json.loads(sanitize_provider_text(json.dumps(response, ensure_ascii=False), key, limit=None)),
            provider_usage=response.get('usage'), error=None)
    except Exception as exc:
        attempt.update(status='failed', response=None, provider_usage=None,
            error=sanitize_provider_text(str(exc), key), exception_type=type(exc).__name__,
            provider_response=getattr(exc, 'provider_response', None))
    attempt['elapsed_s'] = time.monotonic()-started
    attempt['charged_wall_s'] = attempt['elapsed_s']
    atomic_json(guard, attempt)
    record['attempts'].append(attempt)
    record.update(status=attempt['status'], communication_validated=attempt['status']=='completed',
        used=dict(model_calls=len(record['attempts']), tool_calls=len(record['attempts']),
            wall_s=sum(row['charged_wall_s'] for row in record['attempts']), backend_solves=0, worker_calls=0),
        cost_note='One conservative tool charge per direct preflight request; failed attempts count. Missing provider usage and monetary cost are unknown.')
    atomic_json(path, record)
    print(json.dumps(dict(status=record['status'], used=record['used'], error=attempt['error'],
        provider_response=attempt.get('provider_response'), response=attempt['response']), ensure_ascii=False), flush=True)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credential', type=Path, required=True)
    parser.add_argument('--transient-check')
    args = parser.parse_args()
    main(args.credential, args.transient_check)
