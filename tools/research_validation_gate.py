"""Deterministic, offline launch gate over saved Mainline 3 evidence.

No Host creation, provider request, public read, or scientific operation occurs.
Prefetch and principal inspection never demonstrate investigator follow-up.
"""
import argparse
import hashlib
import json
from pathlib import Path

from tools.platform_store import encode, zero
from tools.state_io import atomic_json, digest, read


def visible(pointer, value, page_read):
    from tools.platform_handoff import pointer as resolve
    prefix = page_read['pointer']
    page = page_read['page']
    if page.get('kind') != 'content':
        return False
    if pointer != prefix and not pointer.startswith(prefix + '/'):
        return False
    suffix = pointer[len(prefix):]
    content = page['content']
    try:
        if isinstance(content, list) and suffix:
            head, *tail = suffix[1:].split('/')
            index = int(head) - page.get('offset', 0)
            if not 0 <= index < len(content):
                return False
            content = content[index]
            suffix = '/' + '/'.join(tail) if tail else ''
        elif not suffix and isinstance(content, (list, str)):
            if page.get('offset', 0) or page.get('next_offset') is not None:
                return False
        return encode(resolve(content, suffix)) == encode(value)
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def generate(bundle, review=None):
    events = sorted(bundle['events'], key=lambda e: e['sequence'])
    artifacts = bundle['artifacts']
    state = bundle['state']
    nodes = state.get('investigations', {})
    errors = []
    for key, body in artifacts.items():
        if hashlib.sha256(encode(body).encode('utf8')).hexdigest() != key:
            errors.append('ARTIFACT_IDENTITY_MISMATCH:' + key)
    rows = []
    qualifying = []
    for key, node in sorted(nodes.items()):
        request = 'investigation-' + key
        own = [e for e in events if e.get('request_id') == request]
        starts = [e for e in own if e['kind'] == 'investigation_provider_attempt']
        first = min((e['sequence'] for e in starts), default=float('inf'))
        prefetch, followup, metadata, unmatched = [], [], [], []
        for event in own:
            if event['kind'] != 'investigator_read' or event['status'] != 'completed':
                continue
            record = artifacts[event['outputs'][0]['artifact_id']]
            entry = dict(sequence=event['sequence'], read=record)
            if event['sequence'] < first:
                prefetch.append(entry)
                continue
            prior = [e for e in own if e['kind'] == 'investigation_provider_response'
                     and e['sequence'] < event['sequence']]
            response = artifacts[prior[-1]['outputs'][0]['artifact_id']] if prior else {}
            native = response.get('choices', [{}])[0].get('message', {}).get('tool_calls', [])
            matched = False
            if len(native) == 1 and native[0]['function']['name'] != 'investigation_return':
                try:
                    arguments = json.loads(native[0]['function']['arguments'])['arguments']
                    query = record['query']
                    matched = (arguments.get('reference') == query['reference']
                               and arguments.get('pointer', '') == query['pointer']
                               and all(arguments.get(k, query[k]) == query[k]
                                       for k in ('offset', 'limit', 'byte_limit') if k in query))
                except (KeyError, ValueError, TypeError):
                    pass
            entry['native_response_sequence'] = prior[-1]['sequence'] if matched else None
            entry['absent_from_initial_prefetch'] = not any(
                p['read']['reference'] == record['reference']
                and visible(record['pointer'], record['page'].get('content'), p['read'])
                for p in prefetch)
            if not matched:
                unmatched.append(entry)
            elif record.get('metadata_only'):
                metadata.append(entry)
            else:
                followup.append(entry)
                if node['order']['role'] == 'investigator' and entry['absent_from_initial_prefetch']:
                    qualifying.append(dict(investigation_id=key, sequence=event['sequence'],
                        reference=record['reference'], pointer=record['pointer'],
                        native_response_sequence=entry['native_response_sequence']))
        rows.append(dict(investigation_id=key, role=node['order']['role'], status=node['status'],
            report=node.get('result'), initial_prefetch=prefetch,
            investigator_selected_original_reads=followup, selected_directory_reads=metadata,
            unmatched_reads=unmatched, provider_attempts=len(starts),
            provider_responses=sum(e['kind'] == 'investigation_provider_response' for e in own),
            usage=node.get('usage'), disposition=node.get('disposition_record')))
        if unmatched:
            errors.append('UNMATCHED_POST_SEND_READ:' + key)
    investigators = [n for n in nodes.values() if n['order']['role'] == 'investigator']
    completed = len(investigators) == 2 and all(n['status'] == 'completed' for n in investigators)
    dispositions = []
    inspected = True
    for node in investigators:
        ref = node.get('disposition_record')
        record = artifacts.get((ref or {}).get('artifact_id'))
        if record:
            dispositions.append(dict(reference=ref, record=record))
            if record['decision']['disposition'] == 'accept':
                inspected &= bool(record['inspection_links']) and bool(record['decision']['adopted_claims'])
                inspected &= record['bound_report'] == node.get('result')
                ids = {r['inspection_id'] for r in state.get('principal_investigation_reads', [])}
                inspected &= all(set(link['inspection_ids']) <= ids for link in record['inspection_links'])
    attempts = sum(e['kind'] == 'investigation_provider_attempt' for e in events)
    responses = sum(e['kind'] == 'investigation_provider_response' for e in events)
    charged = zero()
    unresolved = []
    for call in bundle['calls']:
        for k, v in call['charged'].items():
            charged[k] += v
        if call['status'] in ('running', 'unknown'):
            unresolved.append(dict(request_id=call['request_id'], status=call['status'], reserved=call['reserved']))
    budget = bundle['project']['budget']
    accounting = attempts == charged['model_calls'] and not unresolved
    accounting &= all(charged[k] <= budget[k] for k in budget)
    accounting &= all(n.get('usage', {}).get('model_calls', 0) == r['provider_attempts']
                      for n, r in zip((nodes[r['investigation_id']] for r in rows), rows))
    expected_reports = sorted(n['result']['artifact_id'] for n in investigators if n.get('result'))
    material = bool(review and review.get('bundle_identity') == digest(bundle)
                    and sorted(review.get('reports', [])) == expected_reports
                    and review.get('material_correctness') == 'pass')
    gates = dict(actual_provider_interaction='pass' if bundle['transport'] == 'real_configured_deepseek' and attempts and responses == attempts else 'unverified',
        investigator_selected_followup='pass' if qualifying else 'unverified',
        source_scope_and_provenance='pass' if not errors and investigators else 'fail',
        completed_reports='pass' if completed else 'fail',
        formal_principal_dispositions='pass' if completed and len(dispositions) == 2 else 'fail',
        independently_inspected_acceptance='pass' if inspected and len(dispositions) == 2 else 'fail',
        lifecycle_and_accounting='pass' if accounting else 'fail',
        material_correctness='pass' if material else 'unverified')
    return dict(version='mainline3_saved_gate@1.0.0', input_identity=digest(bundle),
        review_identity=digest(review) if review else None, mode=bundle['mode'],
        gates=gates, passed=all(v == 'pass' for v in gates.values()),
        dependent_phase='permitted' if all(v == 'pass' for v in gates.values()) else 'unexecuted_failed_prerequisite',
        qualifying_followup_reads=qualifying, nodes=rows,
        principal_inspections=state.get('principal_investigation_reads', []), dispositions=dispositions,
        accounting=dict(provider_attempts=attempts, provider_responses=responses,
            charged=charged, budget=budget, unresolved_reservations=unresolved,
            token_records=[artifacts[e['outputs'][0]['artifact_id']] for e in events
                           if e['kind'] == 'investigation_token_accounting'], billing_cost='unknown'),
        errors=errors, semantic_assessment='Separate factual/material review required; formal status and exit code are insufficient.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--review', type=Path)
    args = parser.parse_args()
    result = generate(read(args.bundle), read(args.review) if args.review else None)
    atomic_json(args.output, result)
    print(encode(dict(passed=result['passed'], gates=result['gates'], charged=result['accounting']['charged'])))


if __name__ == '__main__':
    main()
