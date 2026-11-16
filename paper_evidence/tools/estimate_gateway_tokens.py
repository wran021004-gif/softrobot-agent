"""Offline text-token estimates for the saved Gateway decision sessions; no inference."""
import csv
import importlib.metadata
import json
import os
import statistics
import sys
from collections import defaultdict

import decision_supplements as replay
from build_evidence import OUT, WORK, source, B, ARCH, write_csv, write_json


BASE = 'architecture_metrics/'
SESSION_TABLE = BASE + 'gateway_token_sessions.csv'
REQUEST_TABLE = BASE + 'gateway_token_requests.csv'
ENCODING = 'o200k_base'
METHOD = 'gateway-text-tokens-v1'


def rows(path):
    p = OUT / path
    return list(csv.DictReader(p.open(encoding='utf-8-sig'))) if p.exists() else []


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


class CaptureClient:
    """Capture the established serializer's output without any network access."""
    def post(self, url, *, content, headers):
        self.raw = content
        return self

    status_code = 200

    def json(self):
        return {}


def initial_payload(d):
    records, _ = replay.corpus(d['task_id'], d['checkpoint_id'])
    messages = [
        dict(role='system', content=replay.SYSTEM),
        dict(role='user', content='FROZEN_TASK\n' + json.dumps(records[0], ensure_ascii=False)),
        dict(role='user', content='At this frozen checkpoint, what physical uncertainty should be resolved next and what concrete feasible research decision best discriminates it?'),
    ]
    if d['experiment'] == 'context_gateway':
        if d['condition'] == 'Flat':
            messages.append(dict(role='user', content='COMPLETE_FROZEN_CORPUS\n' + compact(records)))
        else:
            messages.append(dict(role='user', content='CURRENT_RESEARCH_PACKET\n' + compact(replay.l0(records))))
    else:
        c = d['condition']
        roles = (['knowledge'] if c[1] == '+' else []) + (['skill'] if c[3] == '+' else [])
        experiences = source(B, ARCH + 'knowledge_skill/snapshots/' + d['task_id'] + '.json')['experience_records']
        allowed = [x for x in experiences if x['role'] in roles]
        messages.append(dict(role='user', content='FROZEN_CURRENT_EVIDENCE\n' + compact(records)))
        messages.append(dict(role='user', content='AVAILABLE_EXPERIENCE_RESOURCES\n' + json.dumps(allowed, ensure_ascii=False)))
    capture = CaptureClient()
    replay.send(capture, 'offline-no-credential', messages, replay.tools_schema())
    return capture.raw, json.loads(capture.raw)


def message_bytes(message):
    # One extra comma when this message is appended to the serialized array.
    return len(compact(message).encode('utf-8')) + 1


def feedback_bytes(error, turn):
    if error.get('error', '').startswith('text_call_parse:'):
        content = 'Submit research_plan now. A final decision is required within the remaining request budget.'
    else:
        content = 'FROZEN_TOOL_RESULT\n' + compact(error)
    count = message_bytes(dict(role='user', content=content))
    if turn == 3:
        count += message_bytes(dict(role='user', content='One request remains. Submit the final research_plan using the evidence now available.'))
    return count


def apply_estimates():
    """Join derived fields; never replace any Provider actual-usage column."""
    data = rows(SESSION_TABLE)
    if not data:
        return
    by_session = {(r['experiment'], r['session_id']): r for r in data}
    fields = ['input_tokens_text_estimate', 'output_tokens_text_estimate',
              'initial_input_text_tokens', 'retained_final_decision_text_tokens', 'token_count_method']
    for name, experiment in [('context_cross_task.csv', 'context_gateway'), ('knowledge_skill_supplement.csv', 'knowledge_skill')]:
        table = rows(BASE + name)
        for row in table:
            token = by_session[(experiment, row['checkpoint_id'] + '-' + row['condition'])]
            row.update({k: token[k] for k in fields})
        write_csv(BASE + name, table)
    request_key = {(r['experiment'], r['session_id'], r['request_index']): r for r in rows(REQUEST_TABLE)}
    table = rows(BASE + 'supplement_request_usage.csv')
    for row in table:
        token = request_key[(row['experiment'], row['session_id'], row['request_index'])]
        row.update({k: token[k] for k in ['input_tokens_text_estimate', 'output_tokens_text_estimate', 'token_count_method']})
    write_csv(BASE + 'supplement_request_usage.csv', table)
    table = rows('figure_data/fig08_context_comparison.csv')
    for row in table:
        if row['protocol_id'] == 'E2-X6-Gateway-20261116':
            token = by_session[('context_gateway', row['checkpoint_id'] + '-' + row['condition'])]
            row.update({k: token[k] for k in fields})
    write_csv('figure_data/fig08_context_comparison.csv', table)
    write_csv('figure_data/fig08_context_token_estimates.csv', [dict(figure_id='fig08', **r) for r in data if r['experiment'] == 'context_gateway'])
    write_csv('figure_data/fig07_knowledge_skill_token_estimates.csv', [dict(figure_id='fig07', **r) for r in data if r['experiment'] == 'knowledge_skill'])
    definitions = [
        ('input_tokens_text_estimate', 'Local Input Text Tokens', 'N_in_text', 'Sum of per-request initial message-content count or later request byte-ratio estimate'),
        ('output_tokens_text_estimate', 'Local Output Text Tokens', 'N_out_text', 'Sum of canonical final text and reconstructed/imputed draft estimates; see method'),
        ('initial_input_text_tokens', 'Initial Input Text Tokens', 'N_initial_text', 'o200k_base count of reconstructed first-request message contents; no chat framing'),
        ('retained_final_decision_text_tokens', 'Retained Final Decision Text Tokens', 'N_final_text', 'o200k_base count of canonical normalized final decision in text-tool wrapper; UNKNOWN without valid final decision'),
    ]
    registry = [r for r in rows('registry/metric_registry.csv') if r['metric_id'] not in {x[0] for x in definitions}]
    for key, name, symbol, definition in definitions:
        registry.append(dict(metric_id=key, canonical_name=name, symbol=symbol, unit='text tokens',
            higher_or_lower_is_better='descriptive; quality and failures reported separately', calculation_definition=definition,
            applicable_task_family='new Gateway Context/K/S decision-only sessions', threshold_source='no acceptance threshold',
            source_reference='supplementary_experiments/gateway_token_method.json', display_precision=0))
    write_csv('registry/metric_registry.csv', registry)
    manifest = [r for r in rows('source_manifest.csv') if r['run_id'] != METHOD]
    manifest.append(dict(study_id='E2-X6-Gateway-20261116;KS16-decision-only-20261116', task_id='T01;T04;T07;T08;T09;T10',
        source_branch='paper/evidence-synthesis-20261116', source_path='supplementary_experiments/gateway_token_method.json',
        run_id=METHOD, candidate_id='UNKNOWN', condition_id='all 28 Main sessions',
        source_locator='supplementary_experiments/gateway_token_method.json', notes='offline local text-token estimates; actual usage unchanged'))
    write_csv('source_manifest.csv', manifest)


def compute():
    tokenizer = WORK / 'paper_experiment_data/architecture_ablation/reporter_on_off'
    sys.path.insert(0, str(tokenizer / 'tokenizer_runtime'))
    os.environ['TIKTOKEN_CACHE_DIR'] = str(tokenizer / 'tokenizer_cache')
    import tiktoken
    enc = tiktoken.get_encoding(ENCODING)
    count = lambda text: len(enc.encode(text, disallowed_special=()))
    sessions = []
    for experiment in ['context_gateway', 'knowledge_skill']:
        for p in sorted((OUT / 'supplementary_experiments' / experiment / 'sessions').glob('*.json')):
            if 'failure' in p.name:
                continue
            d = json.loads(p.read_text('utf-8'))
            assert not d['reads'], 'New retrievals would require a different recovery method.'
            raw, payload = initial_payload(d)
            assert len(raw) == d['requests'][0]['request_bytes'], (d['session_id'], len(raw), d['requests'][0]['request_bytes'])
            initial_tokens = sum(count(m['content']) for m in payload['messages'])
            final_text = compact(dict(tool='research_plan', arguments=d['decision'])) if isinstance(d.get('decision'), dict) else None
            final_tokens = count(final_text) if final_text else None
            final_escaped_bytes = message_bytes(dict(role='assistant', content=final_text)) if final_text else None
            sessions.append(dict(record=d, source=p.relative_to(OUT.parent).as_posix(), initial_tokens=initial_tokens,
                                 initial_bytes=len(raw), final_tokens=final_tokens,
                                 output_ratio=final_tokens / final_escaped_bytes if final_tokens else None))
    # Failed sessions retain no valid final text: calibrate their earlier draft byte
    # increments using the median retained-final token/escaped-byte ratio of this task.
    ratios = defaultdict(list)
    for s in sessions:
        if s['output_ratio']:
            ratios[s['record']['task_id']].append(s['output_ratio'])
    request_rows = []
    session_rows = []
    for s in sessions:
        d = s['record']
        ratio = s['output_ratio'] or statistics.median(ratios[d['task_id']])
        drafts = []
        for i, request in enumerate(d['requests']):
            input_tokens = s['initial_tokens'] if i == 0 else round(s['initial_tokens'] * request['request_bytes'] / s['initial_bytes'])
            if i + 1 < len(d['requests']):
                assert i < len(d['errors']), d['session_id']
                delta = d['requests'][i + 1]['request_bytes'] - request['request_bytes']
                feedback = feedback_bytes(d['errors'][i], i + 1)
                assert delta > feedback, (d['session_id'], i, delta, feedback)
                output_tokens = round((delta - feedback) * ratio)
                drafts.append(output_tokens)
                output_method = 'next_request_byte_growth_minus_recorded_feedback'
            elif s['final_tokens'] is not None:
                output_tokens = s['final_tokens']
                output_method = 'canonical_retained_final_decision'
            else:
                assert drafts, d['session_id']
                output_tokens = round(statistics.median(drafts))
                output_method = 'unretained_last_reply_imputed_from_same_session_draft_median'
            request_rows.append(dict(experiment=d['experiment'], task_id=d['task_id'], checkpoint_id=d['checkpoint_id'],
                session_id=d['session_id'], condition=d['condition'], request_index=i + 1,
                request_bytes=request['request_bytes'], input_tokens_text_estimate=input_tokens,
                output_tokens_text_estimate=output_tokens,
                input_method='reconstructed_initial_message_content' if i == 0 else 'request_bytes_scaled_by_initial_content_token_ratio',
                output_method=output_method, initial_request_bytes_match=True,
                tokenizer_encoding=ENCODING, token_count_method=METHOD,
                source_reference=s['source'] + '#/requests/' + str(i)))
        own = [r for r in request_rows if r['experiment'] == d['experiment'] and r['session_id'] == d['session_id']]
        session_rows.append(dict(experiment=d['experiment'], task_id=d['task_id'], checkpoint_id=d['checkpoint_id'],
            session_id=d['session_id'], condition=d['condition'], session_status=d['status'], main_request_count=len(own),
            input_tokens_text_estimate=sum(r['input_tokens_text_estimate'] for r in own),
            output_tokens_text_estimate=sum(r['output_tokens_text_estimate'] for r in own),
            initial_input_text_tokens=s['initial_tokens'], retained_final_decision_text_tokens=s['final_tokens'],
            tokenizer_encoding=ENCODING, token_count_method=METHOD, source_reference=s['source']))
    write_csv(REQUEST_TABLE, request_rows)
    write_csv(SESSION_TABLE, session_rows)
    pairs = []
    for checkpoint in dict.fromkeys(r['checkpoint_id'] for r in session_rows if r['experiment'] == 'context_gateway'):
        flat = next(r for r in session_rows if r['session_id'] == checkpoint + '-Flat')
        hierarchy = next(r for r in session_rows if r['session_id'] == checkpoint + '-Hierarchical')
        pairs.append(dict(checkpoint_id=checkpoint, task_id=flat['task_id'],
            flat_initial_input_text_tokens=flat['initial_input_text_tokens'], hierarchical_initial_input_text_tokens=hierarchy['initial_input_text_tokens'],
            flat_input_tokens_text_estimate=flat['input_tokens_text_estimate'], hierarchical_input_tokens_text_estimate=hierarchy['input_tokens_text_estimate'],
            cumulative_input_reduction_fraction=1 - hierarchy['input_tokens_text_estimate'] / flat['input_tokens_text_estimate'],
            flat_main_request_count=flat['main_request_count'], hierarchical_main_request_count=hierarchy['main_request_count'],
            flat_status=flat['session_status'], hierarchical_status=hierarchy['session_status'], token_count_method=METHOD))
    write_csv(BASE + 'gateway_context_token_pairs.csv', pairs)
    write_json('supplementary_experiments/gateway_token_method.json', dict(method_id=METHOD, tokenizer_encoding=ENCODING,
        tiktoken_version=importlib.metadata.version('tiktoken'), created_for='post-hoc offline text-token estimation; no new inference',
        population='28 Main decision sessions / 62 returned requests; reviewer calls and failed transport attempts excluded',
        initial_input='Reconstruct complete messages with original source records and serializer; verify exact request byte count; tokenize message content only.',
        later_input='initial_content_tokens * recorded_request_bytes / initial_request_bytes, rounded to nearest integer',
        earlier_output='Token/escaped-byte ratio of retained canonical final decision times next-request byte growth minus recorded feedback; failed sessions use same-task median calibration.',
        final_output='Canonical retained decision in text-tool wrapper; last reply of each of two failed sessions imputed from median of its earlier draft estimates.',
        limitations='Text-token proxies only. Chat framing, backend processing, hidden reasoning, actual tokenizer, caching and billing are unavailable. Draft wording/formatting were not retained. No service-usage values are replaced.',
        initial_request_byte_matches=len(sessions), source_tables=[REQUEST_TABLE, SESSION_TABLE]))
    lines = ['# Gateway text-token counts', '',
        'These post-hoc local tokenizer estimates supplement, and do not replace, Provider actual usage. Values use o200k_base with one method for all 28 sessions and 62 returned Main requests. No new model calls were made. Reviewer calls and transport failures are excluded.', '',
        'Every first request was reconstructed from frozen source records, including the original Core schema and any shared-subtree encoding. All 28 serialized byte counts match the saved execution records. Initial message content is tokenized directly. Later request input is estimated by scaling its recorded bytes by its own initial content-token/byte ratio.', '',
        'Earlier output is estimated from growth of the next request after subtracting recorded user/tool feedback, calibrated by retained final decision token/escaped-byte ratios. Final valid output uses the normalized canonical decision in its text-tool wrapper. The unretained last replies of the two failed sessions use their own previous-draft median. These are especially uncertain output estimates; intermediate draft text cannot be recovered.', '',
        'Counts exclude service chat framing, hidden reasoning and unknown backend transformations; they cannot establish actual usage, billing, cache effects or model context capacity. Failed sessions remain included. Cumulative differences also reflect unequal repair-request counts. Compare historical measured usage in a separate panel.', '',
        '| Checkpoint | Flat input | Hierarchical input | Cumulative reduction | Requests F/H |',
        '|---|---:|---:|---:|---:|']
    for r in pairs:
        lines.append(f"| {r['checkpoint_id']} | {r['flat_input_tokens_text_estimate']:,} | {r['hierarchical_input_tokens_text_estimate']:,} | {r['cumulative_input_reduction_fraction']:.2%} | {r['flat_main_request_count']}/{r['hierarchical_main_request_count']} |")
    flat = sum(r['flat_input_tokens_text_estimate'] for r in pairs)
    hierarchy = sum(r['hierarchical_input_tokens_text_estimate'] for r in pairs)
    lines += ['', f'Across these six pairs: Flat {flat:,}; Hierarchical {hierarchy:,}; ratio of summed input counts gives {1-hierarchy/flat:.2%} reduction. This describes this selected sample and delivery protocol, not measured service efficiency or statistical noninferiority.', '',
              '| Experiment | Sessions | Requests | Input | Output |', '|---|---:|---:|---:|---:|']
    totals = {}
    for experiment in ['context_gateway', 'knowledge_skill']:
        own = [r for r in session_rows if r['experiment'] == experiment]
        total_input = sum(r['input_tokens_text_estimate'] for r in own)
        total_output = sum(r['output_tokens_text_estimate'] for r in own)
        total_requests = sum(r['main_request_count'] for r in own)
        lines.append(f'| {experiment} | {len(own)} | {total_requests} | {total_input:,} | {total_output:,} |')
        totals[experiment] = dict(input=total_input, output=total_output, requests=total_requests)
    (OUT / (BASE + 'gateway_token_summary.md')).write_text('\n'.join(lines) + '\n', 'utf-8')
    apply_estimates()
    print(json.dumps(dict(initial_byte_matches=len(sessions), requests=len(request_rows), totals=totals,
                          context_flat=flat, context_hierarchical=hierarchy, context_reduction=1-hierarchy/flat)))


if __name__ == '__main__':
    compute()
