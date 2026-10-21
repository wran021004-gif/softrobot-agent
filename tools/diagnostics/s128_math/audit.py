"""Offline metadata audit only. No research imports, workers, or provider calls.

Usage: python tools/diagnostics/s128_math/audit.py --store <sealed-study-dir>
The SQLite connection is explicitly read-only; only the derived output is written.
Raw messages, reasoning, HTTP payloads and scientific arrays are never exported.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf8'))


def differences(left, right, pointer=''):
    if type(left) is not type(right):
        return [dict(pointer=pointer, s12=left, s128=right)]
    if isinstance(left, dict):
        return [row for key in sorted(left.keys() | right.keys())
                for row in differences(left.get(key), right.get(key), pointer+'/'+key)]
    if isinstance(left, list):
        if len(left) != len(right):
            return [dict(pointer=pointer+'/length', s12=len(left), s128=len(right))]
        return [row for i, (a, b) in enumerate(zip(left, right))
                for row in differences(a, b, pointer+'/'+str(i))]
    return [] if left == right else [dict(pointer=pointer, s12=left, s128=right)]


def structure(candidate, reference):
    cfg = candidate['configuration']
    robot = cfg['robot']['structure']['data']
    return dict(reference=reference, parameters=candidate['parameters'],
                effective_task_identity=identity(cfg['task']),
                segments=[p for p in robot['components'] if p['kind']=='flexible_segment'],
                tendon_order=[t['id'] for t in robot['tendons']],
                pretension_n=[t['pretension_n'] for t in robot['tendons']],
                force_limits_n=[t['force_limit_n'] for t in robot['tendons']])


def audit(folder):
    # The existing schema parser supplies defaults; no candidate/model is built.
    from extensions.tendon_family.family_space import parse_space
    connection = sqlite3.connect((folder/'platform.sqlite').resolve().as_uri()+'?mode=ro', uri=True)
    connection.execute('PRAGMA query_only=ON')
    try:
        with connection:  # One read transaction gives all queries the same snapshot.
            connection.execute('BEGIN')
            rows = list(connection.execute('SELECT run_id,state FROM sessions WHERE run_id=?',
                                           ('s128-cold-live-20261021',)))
            run_id, state_text = rows[0]
            state = json.loads(state_text)
            event_texts = [r[0] for r in connection.execute('SELECT body FROM events ORDER BY seq')]
            events = [json.loads(v) for v in event_texts]

            def artifact(ref):
                body = connection.execute('SELECT body FROM artifacts WHERE id=?',
                                          (ref['artifact_id'],)).fetchone()[0]
                return json.loads(body)

            request_rows, packet_rows, tool_calls = [], [], Counter()
            prediction_summaries, mechanics_summaries = [], []
            schemas = {}
            for event in events:
                kind = event['kind']
                if kind == 'r3_request':
                    envelope = artifact(event['outputs'][0])
                    request = artifact(envelope['request'])
                    definitions = {t['function']['name']: t['function'] for t in request['tools']}
                    analysis = definitions.get('research_analysis')
                    schema_id = identity(analysis) if analysis else None
                    if analysis:
                        schema = analysis['parameters']
                        schemas[schema_id] = dict(description=analysis['description'],
                            required=schema['required'], operations=schema['properties']['operation']['enum'],
                            operating_points=schema['properties']['operating_point']['enum'])
                    request_rows.append(dict(sequence=event['sequence'], envelope=event['outputs'][0],
                        request=envelope['request'], advertised_tools=list(definitions),
                        analysis_schema_identity=schema_id,
                        plan_actions=definitions['research_plan']['parameters']['properties']['action']['enum']))
                elif kind == 'model_decision_packet':
                    packet = artifact(event['outputs'][0]); research = packet['research']
                    actions = research['available_research_actions']
                    packet_rows.append(dict(sequence=event['sequence'], reference=event['outputs'][0],
                        remaining_mathematical=research['budget']['science_budget']['remaining_mathematical'],
                        readiness=research['tool_readiness']['status'],
                        capabilities=research['capabilities'],
                        mathematical_response_rows=sum(a.get('method')=='mathematical_response' for a in actions),
                        mathematical_response_statuses=dict(Counter(a['status'] for a in actions
                            if a.get('method')=='mathematical_response')),
                        direct_analysis_action_rows=sum(a['action'] in ('analysis','research_analysis') for a in actions),
                        analysis_protocol_visible='analysis_protocol' in packet))
                elif kind == 'model_original_tool_request':
                    tool_calls[artifact(event['outputs'][0])['tool_use']['name']] += 1
                elif kind == 'one_step_prediction_comparisons':
                    comparisons = artifact(event['outputs'][0])
                    vector_fields = ('predicted_tip_m','measured_tip_m',
                                     'predicted_tip_velocity_m_s','measured_tip_velocity_m_s')
                    valid = [row for row in comparisons if all(isinstance(row[k],list)
                        and len(row[k])==3 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in row[k])
                        for k in vector_fields)]
                    prediction_summaries.append(dict(reference=event['outputs'][0], samples=len(comparisons),
                        raw_recorded_maxima_unvalidated={k:max(row[k] for row in comparisons) for k in
                            ('tip_difference_m','velocity_difference_m_s','applied_input_difference_n')},
                        valid_vector_rows=len(valid),
                        valid_vector_maxima={k:max(row[k] for row in valid) for k in
                            ('tip_difference_m','velocity_difference_m_s','applied_input_difference_n')} if valid else None,
                        invalid_vector_rows=[dict(pointer='/'+str(i),start_s=row['start_s'],
                            invalid_fields=[k for k in vector_fields if not isinstance(row[k],list) or len(row[k])!=3])
                            for i,row in enumerate(comparisons) if row not in valid],
                        scope='Only finite dimension-3 vectors support output comparison. Scalar-broadcast error magnitudes are not physical evidence; projection, integration and model error are not separated.'))
                elif kind == 'mathematical_result':
                    value = artifact(event['outputs'][0]); facts = value['mathematical_facts']
                    mechanics_summaries.append(dict(reference=event['outputs'][0], candidate=value['design_candidate'],
                        operation=value['operation'], status=value['status'],
                        facts={k:facts[k] for k in ('converged','iterations','function_evaluations',
                            'objective','original_feasible','relaxed_feasible','model_identity')},
                        conclusions=[dict(conclusion=claim['conclusion'],verification_status=claim['verification_status'],
                            numerical_result_pointer=claim['numerical_result_pointer']) for claim in value['verified_conclusions']]))

            s12 = load(ROOT/'evidence/s12_mirror/study/design_package.json')
            candidates = [structure(artifact(ref), ref) for ref in state['candidates'].values()]
            sample = artifact(next(iter(state['candidates'].values())))['configuration']
            baseline = s12['configuration']
            candidate_tasks = []
            for ref in state['candidates'].values():
                task = artifact(ref)['configuration']['task']
                initial = task['initializer']['parameters']['data']
                candidate_tasks.append(dict(candidate=ref, exact_task_equal_s12=task==baseline['task'],
                    differences=differences(baseline['task'],task),
                    named_initial_joints=len(initial['qpos_rad']),
                    all_named_initial_values_zero=all(v==0 for field in ('qpos_rad','qvel_rad_s') for v in initial[field].values())))
            requests_with_analysis = sum(r['analysis_schema_identity'] is not None for r in request_rows)
            result = dict(version='s128_math_readonly_audit_v1', study_id=run_id,
                baseline='67c8fd9c6e79d5479a0c7ba2def00a44ffe74e70',
                source_commit=state['freeze'],
                source_state_sha256=hashlib.sha256(state_text.encode()).hexdigest(),
                source_events_identity=identity(event_texts),
                source_archive_sha256=hashlib.sha256((folder/'export/immutable_artifacts.tar.gz').read_bytes()).hexdigest(),
                source_paths_are_local_only=True,
                comparisons=dict(family_space_identity=state['spec']['family_space_identity'],
                    configured_space_equal=load(ROOT/'configs/research/family_space_s7.json')==state['spec']['family_space'],
                    configured_space_equal_after_existing_parser=parse_space(load(ROOT/'configs/research/family_space_s7.json')).model_dump(mode='json')==state['spec']['family_space'],
                    exact_s12_frozen_space_equal=baseline['policy']['candidate_builder']['parameters']['data']['space']==state['spec']['family_space'],
                    s12_canonical_task_equal=s12['canonical_task']==state['spec']['canonical_task'],
                    s12_effective_task_equal=baseline['task']==sample['task'],
                    s12_effective_task_identity=identity(baseline['task']),
                    s128_canonical_task_identity=state['spec']['canonical_task_identity'],
                    backend_equal=baseline['policy']['backend']==sample['policy']['backend'],
                    policy_discretization_equal=baseline['policy']['discretization']==sample['policy']['discretization'],
                    controller_differences_for_sample=differences(baseline['policy']['controller'],sample['policy']['controller'])),
                s12_structure=structure(dict(configuration=baseline,parameters=s12['design_parameters']),s12['candidate']),
                s128_structures=candidates,
                candidate_task_comparisons=candidate_tasks,
                advertisement_summary=dict(provider_requests=len(request_rows),
                    requests_advertising_analysis=requests_with_analysis,
                    analysis_schema_variants=len(schemas), analysis_schemas=schemas,
                    native_tool_calls=dict(tool_calls), packets=len(packet_rows),
                    readiness_states=dict(Counter(p['readiness'] for p in packet_rows)),
                    remaining_mathematical=sorted(set(p['remaining_mathematical'] for p in packet_rows)),
                    mathematical_response_statuses=dict(sum((Counter(p['mathematical_response_statuses']) for p in packet_rows), Counter())),
                    direct_analysis_action_rows=sum(p['direct_analysis_action_rows'] for p in packet_rows)),
                saved_one_step_comparisons=prediction_summaries, mechanics_results=mechanics_summaries,
                analysis_results=state['analysis_results'], mathematical_evaluations=state['mathematical_evaluations'],
                request_advertisements=request_rows, packet_metadata=packet_rows,
                source_unchanged_during_read=(state_text==connection.execute('SELECT state FROM sessions WHERE run_id=?',(run_id,)).fetchone()[0]
                    and event_texts==[r[0] for r in connection.execute('SELECT body FROM events ORDER BY seq')]),
                scope='Saved metadata and exact JSON comparisons only. No capability execution, model validation, causal policy inference or new scientific evaluation.')
            return result
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'evidence/s128_math/diagnostics.json')
    args = parser.parse_args()
    result = audit(args.store)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    print(json.dumps(result['advertisement_summary'], ensure_ascii=False))
    print('Exact comparison:', json.dumps(result['comparisons'], ensure_ascii=False))
