"""Offline accounting and exact-citation audit of preserved Stage 3.50 products."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from schemas.platform_handoff import EvidenceSelector
from tools.platform_handoff import validate_selector
from tools.platform_store import Store
from tools.state_io import atomic_json, read


def audit(configuration):
    config = read(configuration)
    base = Path(config['run_directory'])
    destination = Path(config['evidence_directory'])
    runs = []
    for path in sorted(base.glob('*/outcome.json')):
        outcome = read(path)
        store = Store(path.parent)
        freeze = read(path.parent / 'freeze.json')
        citations = []
        failures = []
        attempts = {}
        for role, run_id in freeze['hosts'].items():
            phase = 'preparation'
            for event in store.events(run_id):
                if event['kind'] == 'model_request':
                    payload = store.artifact(event['inputs'][0])
                    phase = json.loads(payload['messages'][1]['content'])['role_context']['phase']
                    attempts[phase] = attempts.get(phase, 0) + 1
                if event['kind'] == 'model_decision':
                    value = store.artifact(event['outputs'][0])
                    decisions = value if isinstance(value, list) else value.get('batch', [value])
                    for decision in decisions:
                        # The event artifact can be the decoded response envelope.
                        if 'decision' in decision:
                            decision = decision['decision']
                        args = decision.get('arguments', {})
                        if 'fact_selectors' not in args:
                            continue
                        errors = []
                        count = 0
                        for fact, selectors in args['fact_selectors'].items():
                            for selector in selectors:
                                count += 1
                                try:
                                    validate_selector(store, EvidenceSelector.model_validate(selector))
                                except Exception as exc:
                                    errors.append(dict(fact=fact, error=str(exc)))
                        citations.append(dict(phase=phase, role=role, request_id=decision.get('request_id'),
                            facts=len(args['fact_selectors']), selectors=count, errors=errors))
            with store.connect(True) as db:
                for row in db.execute('SELECT receipt FROM calls WHERE run_id=? AND receipt IS NOT NULL', (run_id,)):
                    receipt = json.loads(row[0])
                    if receipt['execution_status'] != 'completed':
                        failures.append(dict(tool=receipt['tool_id'], request=receipt['request_id'],
                            status=receipt['execution_status'], error=receipt.get('error')))
        accepted = []
        for key, ref in outcome['chain'].items():
            if key not in ('initial_report', 'revised_report'):
                continue
            report = store.artifact(ref)
            count = 0
            for selectors in report['fact_selectors'].values():
                for selector in selectors:
                    validate_selector(store, EvidenceSelector.model_validate(selector))
                    count += 1
            accepted.append(dict(product=key, reference=ref, facts=len(report['fact_selectors']),
                selectors=count, exact_mismatches=0, availability='Accepted by live receipt-ledger validator'))
        tokens = {k: sum(u.get(k, 0) for u in outcome['provider_usage'])
                  for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
        runs.append(dict(label=path.parent.name, mode=outcome['mode'], status=outcome['status'],
            stop_reason=outcome['stop_reason'], classification=outcome['classification'],
            feedback_complete=outcome['feedback_complete'], numerical_check_status=outcome['numerical_check_status'],
            used=outcome['usage']['used'], limits=outcome['usage']['limit'], elapsed_s=outcome['elapsed_s'],
            numerical_work=outcome['numerical_work']['used'], tokens=tokens, attempts_by_phase=attempts,
            accepted_reports=accepted, draft_citations=citations, failed_tool_receipts=failures,
            protocol_corrections=outcome['protocol_corrections'], monetary_cost=None))
    used = {k: sum(r['used'][k] for r in runs) for k in config['overall_stage_limits']}
    assert all(used[k] <= cap for k, cap in config['overall_stage_limits'].items())
    result = dict(runs=runs, used=used, limits=config['overall_stage_limits'],
        tokens={k: sum(r['tokens'][k] for r in runs) for k in ('prompt_tokens','completion_tokens','total_tokens')},
        numerical_work={k: sum(r['numerical_work'][k] for r in runs) for k in ('local_solves','prediction_evaluations')},
        elapsed_workflow_s=sum(r['elapsed_s'] for r in runs), monetary_cost=None,
        qualification='Exact-source and receipt checks only. Scientific prose requires separate implementer review; counts are not quality scores. Historical stages excluded.')
    atomic_json(destination / 'workload_audit.json', result)
    return result


if __name__ == '__main__':
    result = audit(ROOT / 'examples/stage350_experiment.json')
    print(json.dumps(dict(runs=len(result['runs']), used=result['used'], tokens=result['tokens'])))
