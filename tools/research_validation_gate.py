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


def generate(bundle, review=None, *, limits=None):
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
    read_closures = []
    for key, node in sorted(nodes.items()):
        request = 'investigation-' + key
        own = [e for e in events if e.get('request_id') == request or e.get('request_id','').startswith(request+'-material-')]
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
                    decoded = json.loads(native[0]['function']['arguments'])
                    contract=bundle.get('snapshot',{}).get('input',{}).get('policy',{}).get('model',{}).get('parameters',{}).get('investigation_contract')
                    arguments = decoded if contract in ('business_fields_v2','selectable_facts_v3') else decoded['arguments']
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
                    # A requested/read page alone is not a completed model loop.
                    later=[e for e in starts if e['sequence']>event['sequence']]
                    delivered=[]
                    for send in later:
                        payload=artifacts[send['outputs'][0]['artifact_id']].get('payload',{})
                        for message in payload.get('messages',[]):
                            if message.get('role')=='user':
                                try:packet=json.loads(message.get('content',''))
                                except (ValueError,TypeError):continue
                                if any(item.get('native_calls')==native and item.get('result')==record['page'] for item in packet.get('confirmed_followup_evidence',[])):
                                    delivered.append(send['sequence'])
                            if message.get('role')!='tool' or not native or message.get('tool_call_id')!=native[0].get('id'):continue
                            try:body=json.loads(message.get('content',''))
                            except (ValueError,TypeError):continue
                            if body==record['page']:delivered.append(send['sequence'])
                    report=artifacts.get((node.get('result') or {}).get('artifact_id'),{})
                    used=[f for f in (*report.get('facts',[]),*report.get('counterevidence',[]))
                        if f['reference']==record['reference'] and visible(f['pointer'],f['value'],record)
                        and not any(p['read']['reference']==f['reference'] and visible(f['pointer'],f['value'],p['read']) for p in prefetch)]
                    closure=dict(investigation_id=key, sequence=event['sequence'],
                        reference=record['reference'], pointer=record['pointer'],
                        native_response_sequence=entry['native_response_sequence'],
                        delivered_in_attempt_sequences=delivered,report_uses_novel_facts=used,
                        closed=bool(delivered and used and node['status']=='completed'))
                    read_closures.append(closure)
                    if closure['closed']:qualifying.append(closure)
        rows.append(dict(investigation_id=key, role=node['order']['role'], status=node['status'],
            report=node.get('result'), initial_prefetch=prefetch,
            investigator_selected_original_reads=followup, selected_directory_reads=metadata,
            unmatched_reads=unmatched, provider_attempts=len(starts),
            provider_responses=sum(e['kind'] == 'investigation_provider_response' for e in own),
            usage=node.get('usage'), disposition=node.get('disposition_record')))
        report=artifacts.get((node.get('result') or {}).get('artifact_id'),{})
        observed=[x['read'] for x in (*prefetch,*followup)]
        if node['order']['role']=='principal':observed+=state.get('principal_investigation_reads',[])
        for fact in (*report.get('facts',[]),*report.get('counterevidence',[])):
            ref=fact['reference'];original=artifacts.get(ref['artifact_id'])
            scoped=ref in node['order']['evidence']
            seen=any(r['reference']==ref and visible(fact['pointer'],fact['value'],r) for r in observed)
            from tools.platform_handoff import pointer as resolve
            try:correct=encode(resolve(original,fact['pointer']))==encode(fact['value'])
            except (KeyError,IndexError,TypeError,ValueError):correct=False
            identity=fact.get('source_identity',{})
            correct &= all(isinstance(original,dict) and original.get(k)==v for k,v in identity.items())
            if not (scoped and seen and correct):errors.append('REPORT_SOURCE_VALUE_SCOPE_OR_VISIBILITY:' + key)
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
        if call.get('charged'):
            for k, v in call['charged'].items():charged[k] += v
        if call['status'] in ('running', 'unknown'):
            unresolved.append(dict(request_id=call['request_id'], status=call['status'], reserved=call['reserved']))
    budget = bundle['project']['budget']
    accounting = attempts == charged['model_calls'] and not unresolved
    accounting &= all(charged[k] <= budget[k] for k in budget)
    accounting &= all(n.get('usage', {}).get('model_calls', 0) == r['provider_attempts']
                      for n, r in zip((nodes[r['investigation_id']] for r in rows), rows))
    accounting &= bundle.get('session_status')=='stopped'
    modern=bundle.get('snapshot',{}).get('input',{}).get('policy',{}).get('model',{}).get('parameters',{}).get('investigation_contract') in ('business_fields_v2','selectable_facts_v3')
    model_cap,evidence_cap,time_cap=(8,12,900) if modern else (6,8,600)
    if limits:
        model_cap,evidence_cap,time_cap=limits['node_models'],limits['node_evidence'],limits['node_elapsed_s']
    bounds=all(r['provider_attempts']<=model_cap and r.get('usage',{}).get('tool_calls',0)<=evidence_cap for r in rows)
    principal=[r for r in rows if r['role']=='principal']
    bounds &= all(r.get('usage',{}).get('tool_calls',0)+sum(e['kind']=='principal_inspection' and artifacts[e['outputs'][0]['artifact_id']].get('inspection_origin')!='principal_node_evidence_read' for e in events)<=evidence_cap for r in principal)
    coordinated=bundle['mode']=='coordinated'
    bounds &= len(nodes)<=(limits['node_count'] if limits else (4 if coordinated else 3)) and not charged['backend_solves'] and not charged['worker_calls'] and attempts<=(limits['phase_models'] if limits else ((32 if coordinated else 8) if modern else (24 if coordinated else 18)))
    bounds &= all(n['order'].get('timeout_s',180)<=time_cap and (n.get('progress',{}).get('elapsed_s') or 0)<=n['order'].get('timeout_s',180)+5 for n in nodes.values())
    model=bundle.get('snapshot',{}).get('input',{}).get('policy',{}).get('model',{})
    requests=[artifacts[e['outputs'][0]['artifact_id']].get('payload',{}) for e in events if e['kind']=='investigation_provider_attempt']
    compatible=bool(model and requests) and all(p.get('model')==model.get('model')=='deepseek-flash'
        and p.get('thinking')=={'type':'enabled'} and p.get('reasoning_effort')=='high'
        and p.get('tool_choice')=='auto' and p.get('max_tokens')==min(model.get('investigation_max_tokens',3000),model.get('max_tokens',3000)) for p in requests)
    acceptance_count=sum(d['record']['decision']['disposition']=='accept' for d in dispositions)
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
        bounded_authority='pass' if bounds else 'fail',
        approved_request_settings='pass' if compatible and model.get('base_url')=='https://api.deepseek.com' else 'unverified',
        material_correctness='pass' if material else 'unverified')
    return dict(version='mainline3_saved_gate@1.0.0', input_identity=digest(bundle),
        review_identity=digest(review) if review else None, mode=bundle['mode'],
        gates=gates, passed=all(v == 'pass' for v in gates.values()),
        dependent_phase='permitted' if all(v == 'pass' for v in gates.values()) else 'unexecuted_failed_prerequisite',
        qualifying_followup_reads=qualifying, nodes=rows,
        novel_original_read_closures=read_closures,
        acceptance_coverage='covered' if acceptance_count else 'unverified; no accepted report',
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
