"""Offline S12.8 budget diagnostics: SQLite read-only, stdlib, no science imports.

Usage: python tests/research/s128_budget_diagnostics.py --store <sealed-study-dir>
Writes only derived metadata to evidence/s128_budget; never exports model reasoning.
"""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(store, out):
    db_path = store / 'platform.sqlite'
    before = sha(db_path)
    db = sqlite3.connect(db_path.as_uri() + '?mode=ro&immutable=1', uri=True)
    db.execute('PRAGMA query_only=ON')

    def artifact(ref):
        body = db.execute('SELECT body FROM artifacts WHERE id=?', (ref['artifact_id'],)).fetchone()[0]
        assert hashlib.sha256(body).hexdigest() == ref['artifact_id']
        return json.loads(body)

    state = json.loads(db.execute('SELECT state FROM sessions WHERE run_id=?',
                                 ('s128-cold-live-20261021',)).fetchone()[0])
    assert state['research_status'] == 'stopped' and not state['pending']
    events = [json.loads(r[0]) for r in db.execute('SELECT body FROM events ORDER BY seq')]
    acceptance_path = ROOT / 'evidence/s128_acceptance/reconstruction.json'
    acceptance = json.loads(acceptance_path.read_text(encoding='utf-8'))
    verified = {r['reference']['artifact_id']: r for r in acceptance['physical'] + acceptance['nmpc']}
    decisions = json.loads((ROOT / 'evidence/s128_research/decisions.json').read_text(encoding='utf-8'))
    searches = [artifact(r) for r in state['control_search_results']]
    labels = {r['reference']['artifact_id']: (i, r['label']) for i, s in enumerate(searches)
              for r in s['candidates'] if not r['cache_hit']}
    search_metadata = {}
    for search in searches:
        lookup = {r['reference']['artifact_id']: r for r in search['candidates']}
        for row in search['candidates']:
            if row['cache_hit']:
                continue
            base = lookup[row['prediction_base']['artifact_id']]
            changed = [j for j, (x, y) in enumerate(zip(base['coefficients_n'], row['coefficients_n'])) if x != y]
            if row['label'] == 'finite_difference':
                assert len(changed) == 1
            search_metadata[row['reference']['artifact_id']] = dict(
                probe_coefficient=changed[0] if row['label'] == 'finite_difference' else None,
                base_gap=base['task_gap']['normalized_gap'],
                actual_improvement=row['actual_improvement'], predicted_improvement=row['predicted_improvement'])
    rows = []
    packets = []
    decision = None
    best = float('inf')
    cumulative_s = 0.
    for event in events:
        if event['kind'] == 'model_original_tool_request':
            use = artifact(event['outputs'][0])['tool_use']
            if use['name'] == 'research_plan':
                decision = use['input'].get('decision', {}).get('hypothesis_id')
        if event['kind'] == 'model_decision_packet':
            value = artifact(event['outputs'][0])['research']
            packets.append(dict(event_sequence=event['sequence'], reference=event['outputs'][0],
                                best_gap=(value['best_valid'] or {}).get('task_gap', {}).get('normalized_gap'),
                                remaining_physical=value['budget']['science_budget']['remaining_physical']))
        if event['kind'] not in ('physical_playback_result', 'experiment_result'):
            continue
        ref = event['outputs'][0]
        record = artifact(ref)
        checked = verified[ref['artifact_id']]
        assert checked['task_gap']['valid_complete'] and not checked['accepted']
        gap = checked['task_gap']['normalized_gap']
        metrics = checked['metrics']
        assert abs(gap - max(0., metrics['terminal_error_m']/.01-1,
                            metrics['holding_max_error_m']/.01-1,
                            metrics['holding_max_speed_m_s']/.02-1)) < 1e-12
        if event['kind'] == 'physical_playback_result':
            steps = artifact(record['raw_reference'])['physics_steps']
            cost_s = record['charged_numerical_s']
            method = 'physical_response_seed' if decision.startswith(('H13-', 'H15-')) else 'direct_replay'
            search_index, label = labels.get(ref['artifact_id'], (None, None))
            if search_index is not None:
                method = 'response_search_H18' if search_index == 0 else 'response_search_H28'
        else:
            backend = artifact(record['profile']['simulation'])
            steps = backend['data']['data']['numerical_steps']
            cost_s = record['numerical_s']
            method, label = 'nmpc', None
        assert steps == 700
        best = min(best, gap)
        cumulative_s += cost_s
        rows.append(dict(evaluation=len(rows)+1, event_sequence=event['sequence'],
                         timestamp_utc=event['timestamp'], hypothesis_id=decision, method=method,
                         label=label, candidate=record['candidate']['artifact_id'],
                         reference=ref['artifact_id'], physics_steps=steps, numerical_s=cost_s,
                         cumulative_evaluation_s=cumulative_s, gap=gap, best_gap=best,
                         terminal_error_m=metrics['terminal_error_m'],
                         holding_max_error_m=metrics['holding_max_error_m'],
                         holding_max_speed_m_s=metrics['holding_max_speed_m_s'],
                         last_model_packet_sequence=packets[-1]['event_sequence'],
                         last_model_packet_best_gap=packets[-1]['best_gap'],
                         **search_metadata.get(ref['artifact_id'], dict(probe_coefficient=None, base_gap=None,
                              actual_improvement=None, predicted_improvement=None))))
    assert len(rows) == len(verified) == 79 and len({r['reference'] for r in rows}) == 79
    assert sum(r['physics_steps'] for r in rows) == 55300
    by_ref = {r['reference']: r for r in rows}
    action_spans = {}
    for prefix in ('H9-', 'H13-', 'H15-', 'H18-', 'H28-', 'H29-', 'H31-'):
        start = next(e for e in events if e['kind'] == 'model_original_tool_request'
                     and artifact(e['outputs'][0])['tool_use']['input'].get('decision', {})
                     .get('hypothesis_id', '').startswith(prefix))
        use_id = artifact(start['outputs'][0])['tool_use']['toolUseId']
        end = next(e for e in events if e['kind'] == 'model_original_tool_feedback'
                   and artifact(e['outputs'][0])['tool_use']['toolUseId'] == use_id)
        action_spans[prefix[:-1]] = dict(start_sequence=start['sequence'], end_sequence=end['sequence'],
            start_utc=start['timestamp'], end_utc=end['timestamp'],
            elapsed_s=(datetime.fromisoformat(end['timestamp'])-datetime.fromisoformat(start['timestamp'])).total_seconds())
    iterations = []
    for index, search in enumerate(searches):
        previous_time = datetime.fromisoformat(action_spans['H18' if index == 0 else 'H28']['start_utc'])
        center = search['candidates'][0]['task_gap']['normalized_gap']
        chunk = []
        for item in search['candidates'][1:]:
            chunk.append(item)
            if item['label'] != 'local_response_proposal':
                continue
            first, last = (by_ref[chunk[j]['reference']['artifact_id']]['evaluation'] for j in (0, -1))
            gap = item['task_gap']['normalized_gap']
            end_time = datetime.fromisoformat(rows[last-1]['timestamp_utc'])
            iterations.append(dict(search='H18' if index == 0 else 'H28',
                iteration=1+sum(r['search'] == ('H18' if index == 0 else 'H28') for r in iterations),
                first_evaluation=first, last_evaluation=last,
                new_physical_evaluations=sum(not r['cache_hit'] for r in chunk),
                physics_steps=700*sum(not r['cache_hit'] for r in chunk),
                charged_numerical_s=sum(r['cost_s'] for r in chunk),
                enclosing_event_span_s=(end_time-previous_time).total_seconds(),
                center_gap=center, proposal_gap=gap, center_improvement=item['actual_improvement'],
                best_prefix_gap=rows[last-1]['best_gap'],
                predicted_improvement=item['predicted_improvement'],
                rho=item['actual_improvement']/item['predicted_improvement'],
                trust_radius_n=item['trust_radius_n'], next_trust_radius_n=item['next_trust_radius_n'],
                local_solver_iterations=item['local_solver']['iterations']))
            previous_time = end_time
            center = min(r['task_gap']['normalized_gap'] for r in search['candidates']
                         if r['reference']['artifact_id'] in {v['reference'] for v in rows[:last]})
            chunk = []
        for key in ('new_physical_evaluations', 'charged_numerical_s'):
            actual = sum((not r['cache_hit']) if key.startswith('new_') else r['cost_s']
                         for r in search['candidates'])
            assert abs(actual - search['cost_feedback'][key]) < 1e-9
    groups = defaultdict(list)
    for row in rows:
        groups[row['method']].append(row)
    methods = {name: dict(evaluations=len(group), physics_steps=sum(r['physics_steps'] for r in group),
                         numerical_s=sum(r['numerical_s'] for r in group),
                         evaluation_numbers=[r['evaluation'] for r in group]) for name, group in groups.items()}
    checkpoints = []
    for n in (20, 30, 40, 50, 60):
        row = rows[n-1]
        prefix = rows[:n]
        previous_proposals = [i for i in iterations if i['last_evaluation'] <= n and i['search'] == 'H18']
        checkpoints.append(dict(evaluation=n, latest_gap=row['gap'], prefix_best_gap=row['best_gap'],
            cumulative_evaluation_s=row['cumulative_evaluation_s'], physics_steps=700*n,
            physical_remaining_if_batch_returned=80-n,
            last_model_packet_sequence=row['last_model_packet_sequence'],
            last_model_packet_best_gap=row['last_model_packet_best_gap'],
            completed_H18_iterations=len(previous_proposals),
            H18_new_evaluations=sum(r['method'] == 'response_search_H18' for r in prefix),
            H18_charged_numerical_s=sum(r['numerical_s'] for r in prefix if r['method'] == 'response_search_H18')))
    nmpc = []
    for ref in state['results']:
        result = artifact(ref)
        profile = result['profile']
        nmpc.append(dict(reference=ref, numerical_s=result['numerical_s'],
                         **{k: profile[k] for k in ('simulation_wall_s', 'mean_update_s',
                             'applied_control_updates', 'backend_timings_s')}))
    h18_request = next(e for e in decisions['decisions'] if e['hypothesis_id'].startswith('H18-'))
    h19_request = next(e for e in decisions['decisions'] if e['hypothesis_id'].startswith('H19-'))
    assert not any(h18_request['sequence'] < e['sequence'] < 1247
                   for e in events if e['kind'] == 'r3_request')
    for sequence in (713, 1247):
        packet_event = next(e for e in events if e['sequence'] == sequence)
        request_event = next(e for e in events if e['kind'] == 'r3_request' and e['sequence'] > sequence)
        wire = artifact(artifact(request_event['outputs'][0])['request'])
        system = ''.join(m['content'] for m in wire['messages'] if m['role'] == 'system')
        sent_packet = json.JSONDecoder().raw_decode(system.split('CURRENT_RESEARCH_PACKET\n')[1])[0]
        assert sent_packet == artifact(packet_event['outputs'][0])
    feedback = artifact(next(e for e in events if e['sequence'] == 1246)['outputs'][0])
    original = ''.join(b.get('text', '') for b in feedback['result']['content'])
    delivered = next(m['content'] for m in wire['messages'] if m['role'] == 'tool'
                     and m['tool_call_id'] == feedback['tool_use']['toolUseId'])
    assert original == delivered and 'cost_feedback' in delivered and 'local_responses' in delivered
    receipt_costs = defaultdict(lambda: dict(calls=0, wall_s=0., backend_solves=0))
    for receipt, charged in db.execute('SELECT receipt,charged FROM calls'):
        assert receipt is not None
        tool = json.loads(receipt)['tool_id']
        cost = json.loads(charged)
        receipt_costs[tool]['calls'] += 1
        receipt_costs[tool]['wall_s'] += cost['wall_s']
        receipt_costs[tool]['backend_solves'] += cost['backend_solves']
    sealed_cost = json.loads((ROOT/'evidence/s128_costs/counts.json').read_text(encoding='utf-8'))
    assert abs(sum(c['wall_s'] for c in receipt_costs.values())-sealed_cost['ledger']['used']['wall_s']) < 1e-8
    assert sum(c['backend_solves'] for c in receipt_costs.values()) == 79
    summary = dict(study_id='s128-cold-live-20261021', baseline='67c8fd9c6e79d5479a0c7ba2def00a44ffe74e70',
        store_sha256=before, acceptance_sha256=sha(acceptance_path),
        archive_sha256=sha(store/'export/immutable_artifacts.tar.gz'),
        cost_definition='Physical replay worker boundary; NMPC enclosing numerical_s. Wall elapsed, not CPU seconds.',
        evaluations=len(rows), physics_steps=55300, evaluation_numerical_s=cumulative_s,
        methods=methods, iterations=iterations, checkpoints=checkpoints,
        public_action_spans=action_spans, receipt_costs_by_tool=dict(receipt_costs),
        H28_unfinished_tail=dict(evaluations=len(chunk), numerical_s=sum(r['cost_s'] for r in chunk)),
        nmpc=nmpc, searches=[dict(cost_feedback=s['cost_feedback'], local_responses=s['local_responses']) for s in searches],
        H18_window=dict(request_sequence=h18_request['sequence'], next_decision_sequence=h19_request['sequence'],
                         packets_verified_against_sent_wire=True, batch_feedback_delivered_in_full=True,
                         before_packet=next(p for p in packets if p['event_sequence']==713),
                         after_packet=next(p for p in packets if p['event_sequence']==1247)),
        offline_nlp_s=artifact(state['mechanics_results'][0])['charged_numerical_s'],
        state_time_fields={k: v for k,v in state.items() if k.endswith('_s')},
        raw_reasoning_exported=False, new_provider_requests=0, new_scientific_executions=0)
    db.close()
    assert sha(db_path) == before
    assert summary['archive_sha256'] == 'acb3ab8f6cabbdf9239c5bc0e80784dd09356e53a2aa3194873b08d96fc29604'
    summary['store_bytes_unchanged'] = True
    out.mkdir(parents=True, exist_ok=True)
    with (out/'evaluation_curve.csv').open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (out/'diagnostics.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('evaluations', 'physics_steps', 'evaluation_numerical_s',
                                             'store_bytes_unchanged')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    args = parser.parse_args()
    analyze(args.store.resolve(), ROOT/'evidence/s128_budget')
