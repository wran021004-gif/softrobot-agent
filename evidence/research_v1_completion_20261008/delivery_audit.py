"""Offline delivery accounting from sealed artifacts; no provider or science."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from tools.research_v1_delivery import check_freeze
from tools.state_io import atomic_json, digest, read

ROOT = Path(__file__).resolve().parent
STAGES = ROOT / 'stages'


def stamp(value):
    return datetime.fromisoformat(value).timestamp()


def union_seconds(intervals):
    result = 0.0
    end = float('-inf')
    for start, stop in sorted(intervals):
        result += max(0, stop - max(start, end))
        end = max(end, stop)
    return result


def main():
    manifest, _ = check_freeze(STAGES)
    bundle = read(STAGES / 'direct_bundle.json')
    gate = read(STAGES / 'direct_gate.json')
    events = sorted(bundle['events'], key=lambda e: e['sequence'])
    artifacts = bundle['artifacts']
    nodes = bundle['state']['investigations']
    pending, intervals, attempts, responses = {}, [], [], []
    tokens = Counter()
    for event in events:
        key = (event['run_id'], event['request_id'])
        if event['kind'] == 'investigation_provider_attempt':
            pending[key] = event
            attempts.append(event)
        elif event['kind'] == 'investigation_provider_response':
            start = pending.pop(key)
            body = artifacts[event['outputs'][0]['artifact_id']]
            responses.append(event)
            intervals.append(dict(request_id=key[1], run_id=key[0],
                start=start['timestamp'], end=event['timestamp'],
                elapsed_s=stamp(event['timestamp']) - stamp(start['timestamp']),
                finish_reason=body['choices'][0]['finish_reason']))
            for field in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                tokens[field] += body.get('usage', {}).get(field, 0)
    assert not pending and len(attempts) == len(responses) == gate['accounting']['charged']['model_calls']
    original = [r for r in intervals if r['run_id'] == 'mainline3-direct']
    reach = [(stamp(r['start']), stamp(r['end'])) for r in original if r['request_id'] == 'investigation-reach-question']
    timing = [(stamp(r['start']), stamp(r['end'])) for r in original if r['request_id'] == 'investigation-timing-question']
    overlap = sum(max(0, min(a[1], b[1]) - max(a[0], b[0])) for a in reach for b in timing)
    principal_response = next(e for e in responses if e['request_id'] == 'investigation-principal-synthesis')
    principal_raw = artifacts[principal_response['outputs'][0]['artifact_id']]
    args = json.loads(principal_raw['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
    for key in ('reach-question', 'timing-question'):
        atomic_json(STAGES / (key + '_report.json'), artifacts[nodes[key]['result']['artifact_id']])
    atomic_json(STAGES / 'principal_invalid_response.json', principal_raw)
    measures = [artifacts[e['outputs'][0]['artifact_id']]['measurement'] for e in attempts]
    phases = {}
    for mode in ('coordinated', 'fixed'):
        stage = manifest['phases'][mode]
        assert not (STAGES / (mode + '_launch.json')).exists()
        assert not Path(stage['output']).exists()
        phases[mode] = dict(status='unexecuted_failed_direct_prerequisite',
            limit=stage['project_budget'], used=dict.fromkeys(stage['project_budget'], 0),
            remaining=stage['project_budget'])
    lifecycle = read(STAGES / 'direct_lifecycle.json')
    repair_lifecycle = read(STAGES / 'direct_repair_lifecycle.json')
    clock = read(STAGES / 'engineering_clock.json')
    repair = read(STAGES / 'repair1_authorization.json')
    generated_at = datetime.now().astimezone().isoformat()
    application_wall = lifecycle['application_wall_s'] + repair_lifecycle['application_wall_s']
    elapsed = stamp(generated_at) - stamp(clock['preparation_started_at'])
    result = dict(version='v1_stop_delivery_audit@1.0.0', generated_at=generated_at,
        activity_id=manifest['activity_id'], bundle_identity=digest(bundle), gate_identity=digest(gate),
        conclusion='Stopped with evidence; V1 live acceptance incomplete; V2 entry blocked',
        stop_reason='Principal native investigation_return has invalid outer wrapper; two paid protocol corrections exhausted',
        direct=dict(status='stopped_failed_gate', gates=gate['gates'], ledger=read(STAGES / 'direct_ledger.json'),
            provider_attempts=len(attempts), received_responses=len(responses),
            tokens=dict(tokens), token_source='Returned provider usage; not byte estimates', billing_cost='unknown',
            paid_protocol_corrections=sum(e['kind'] == 'investigation_protocol_correction' for e in events),
            implementation_repairs_used=manifest['repairs_used'],
            nodes={k:dict(status=n['status'], usage=n['usage'], report=n.get('result'),
                original_started_unix=n['started_unix'], recorded_elapsed_s=n.get('progress', {}).get('elapsed_s'),
                total_node_wall_s=n.get('progress', {}).get('total_node_wall_s')) for k, n in nodes.items()},
            formal_dispositions=len(gate['dispositions']),
            failed_principal_response=principal_response['outputs'][0],
            failed_principal_argument_keys=sorted(args), invalid_return_executed=False,
            protocol_repair_available=False, transport_retries=0),
        dependent_phases=phases,
        capacity=dict(all_final_requests_passed=all(m['passed'] for m in measures),
            maximum_wire_utf8_bytes=max(m['utf8_bytes'] for m in measures),
            maximum_estimated_input_tokens=max(m['estimated_input_tokens'] for m in measures),
            maximum_provider_prompt_tokens=max(artifacts[e['outputs'][0]['artifact_id']]['usage']['prompt_tokens'] for e in responses),
            generation_tokens=32768, report_bytes=65536, input_budget_tokens=160000,
            estimator='Conservative UTF-8 byte upper estimate plus framing, distinct from provider tokens',
            report_sizes={k:len(json.dumps(artifacts[nodes[k]['result']['artifact_id']], ensure_ascii=False).encode('utf8')) for k in ('reach-question', 'timing-question')}),
        clocks=dict(application_initial_wall_s=lifecycle['application_wall_s'],
            application_repair_continuation_wall_s=repair_lifecycle['application_wall_s'],
            application_wall_sum_s=application_wall, ledger_cumulative_wall_s=gate['accounting']['charged']['wall_s'],
            provider_roundtrips_sum_s=sum(r['elapsed_s'] for r in intervals),
            provider_roundtrips_union_s=union_seconds([(stamp(r['start']), stamp(r['end'])) for r in intervals]),
            actual_two_investigator_provider_overlap_s=overlap,
            initial_engineering_preparation_including_tests_and_wait_s=stamp(clock['frozen_at'])-stamp(clock['preparation_started_at']),
            repair_authorization_to_refreeze_s=stamp(manifest['repair1_frozen_at'])-stamp(repair['timestamp']),
            historical_engineering_snapshot=read(ROOT / 'pending_delivery_accounting.json'),
            known_offline_test_runner_wall_s=289.754 + 6.130,
            elapsed_from_engineering_start_to_delivery_snapshot_s=elapsed,
            nonapplication_elapsed_including_review_repair_delivery_and_wait_s=elapsed-application_wall,
            qualification='Inclusive elapsed contains approval and review waits; no exact active engineering CPU cost or monetary bill is available.'),
        provider_intervals=intervals,
        closure=dict(all_submitted_threads_collected=lifecycle['all_submitted_threads_collected'] and repair_lifecycle['all_submitted_threads_collected'],
            unresolved_new_reservations=gate['accounting']['unresolved_reservations'],
            old_history_and_unknown_escrow_unchanged=True, frozen_code_dependencies_and_sources_unchanged=True,
            automatic_review_rejections=1, later_chat_confirmation_received=True,
            scientific_or_acceptance_changes=False, manual_model_report_substitution=False,
            additional_semantic_review_model_calls=0),
        publication=dict(target='https://github.com/wran021004-gif/softrobot-agent.git', branch='feat/gvs-dynamics',
            method='normal push only; final remote SHA verified separately after commit'))
    atomic_json(STAGES / 'delivery_audit.json', result)
    print(json.dumps({k:result[k] for k in ('conclusion', 'capacity', 'clocks')}, ensure_ascii=True))


if __name__ == '__main__':
    main()
