"""Candidate-bound evidence aliases, discoverable catalog and bounded JSON reads."""
import json
from pathlib import Path
from tools.state_io import atomic_json, read


def refresh_index(book):
    state = book.state
    for c in state['candidates']:
        if c['path'] in state['evidence']:
            state['evidence'][c['path']]['candidate_id'] = c['candidate_id']
        for attempt in state['attempts']:
            if attempt.get('result', {}).get('data', {}).get('candidate', {}).get('candidate_id') == c['candidate_id']:
                for ref in state['evidence'].values():
                    if ref['path'].startswith(attempt['folder'] + '/'):
                        ref['candidate_id'] = c['candidate_id']
    for cid in [c['candidate_id'] for c in state['candidates']]:
        for attempt in state['attempts']:
            if attempt['arguments'].get('candidate_id') != cid or not attempt.get('result_ref'):
                continue
            canonical = 'eval:' + cid if attempt['tool'] == 'evaluate_candidate' else None
            if canonical:
                book.register(book.root / attempt['result_ref'], canonical)
            for ref in state['evidence'].values():
                if ref['path'].startswith(attempt['folder'] + '/'):
                    ref['candidate_id'] = cid
                    if canonical:
                        ref['evaluation_id'] = canonical
            if canonical:
                state['evidence'][canonical].update(candidate_id=cid, evaluation_id=canonical)
    entries = []
    for eid, ref in list(state['evidence'].items()):
        if eid.startswith('catalog:'):
            continue
        path = book.root / ref['path']
        entry = dict(evidence_id=eid, candidate_id=ref.get('candidate_id'),
                     evaluation_id=ref.get('evaluation_id'),
                     readable=path.suffix == '.json', bytes=path.stat().st_size)
        if entry['readable']:
            value = read(path)
            entry['fields'] = list(value)[:16] if isinstance(value, dict) else ['array' if isinstance(value, list) else 'scalar']
        entries.append(entry)
    entries.sort(key=lambda e: (not e['evidence_id'].startswith('eval:'), 'diagnostic' not in e['evidence_id'], not e['readable'], e['evidence_id']))
    folder = book.root / 'evidence_index'
    folder.mkdir(exist_ok=True)
    for name, rows in [('all', entries), *[(c['candidate_id'], [e for e in entries if e['candidate_id'] == c['candidate_id']]) for c in state['candidates']]]:
        path = folder / (name + '.json')
        atomic_json(path, dict(entries=rows, read_help='read_evidence(pointer=/entries, offset=0, limit=10); 用返回的 evidence_id 与字段 JSON Pointer 继续读取'))
        book.register(path, 'catalog:' + name)


def read_slice(root, state, arguments):
    eid = arguments['evidence_id']
    ref = state['evidence'][eid]
    value = read(root / ref['path'])
    pointer = arguments.get('pointer', '')
    # The basic evaluation is a complete small view, never the first ten keys
    # of a larger object (which previously hid the diagnostics).
    canonical = ref.get('evaluation_id')
    view = 'raw'
    if canonical and ref['path'] == state['evidence'][canonical]['path'] and pointer in ('', '/data'):
        value = evaluation_overview(value['data'], canonical)
        pointer = ''
        view = 'complete_evaluation_overview'
    if pointer and not pointer.startswith('/'):
        raise ValueError('INVALID_JSON_POINTER: must start with /')
    try:
        for token in pointer.split('/')[1:] if pointer else []:
            token = token.replace('~1', '/').replace('~0', '~')
            value = value[int(token)] if isinstance(value, list) else value[token]
    except (KeyError, IndexError, ValueError, TypeError):
        raise ValueError('JSON_POINTER_NOT_FOUND: ' + pointer) from None
    offset, limit = arguments.get('offset', 0), arguments.get('limit', 10)
    total = len(value) if isinstance(value, (dict, list)) else None
    cap = arguments.get('max_bytes', 3000)
    if eid.startswith('catalog:') and pointer in ('', '/entries'):
        entries = value['entries'] if isinstance(value, dict) else value
        page = []
        for entry in entries[offset:offset + limit]:
            if len(json.dumps(page + [entry], ensure_ascii=False).encode('utf-8')) > cap:
                break
            page.append(entry)
        size = len(json.dumps(page, ensure_ascii=False).encode('utf-8'))
        return dict(evidence_id=eid, cite_as=eid, candidate_id=eid.split(':')[1], pointer='/entries',
                    offset=offset, total_items=len(entries), next_offset=offset + len(page) if offset + len(page) < len(entries) else None,
                    next_byte_offset=None, content=page, content_format='json', content_bytes=size,
                    required_entry_bytes=len(json.dumps(entries[offset], ensure_ascii=False).encode('utf-8')) if not page and offset < len(entries) else None,
                    message='目录只返回完整条目，按 next_offset 继续；空页时提高 max_bytes 至 required_entry_bytes。')
    if view == 'complete_evaluation_overview':
        total = None
    elif isinstance(value, dict) and offset == 0 and len(json.dumps(value, ensure_ascii=False).encode('utf-8')) <= cap:
        total = None  # A small field map fits in full; no artificial key pagination.
    elif isinstance(value, dict):
        value = dict(list(value.items())[offset:offset + limit])
    elif isinstance(value, list):
        value = value[offset:offset + limit]
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    start = arguments.get('byte_offset', 0)
    # Returned offsets always land on UTF-8 boundaries.
    if start > len(raw) or (start < len(raw) and raw[start] & 0xC0 == 0x80):
        raise ValueError('INVALID_BYTE_OFFSET: use next_byte_offset')
    fragment = raw[start:start + cap].decode('utf-8', errors='ignore')
    end = start + len(fragment.encode('utf-8'))
    complete = start == 0 and end == len(raw)
    return dict(evidence_id=eid, candidate_id=ref.get('candidate_id'),
                evaluation_id=ref.get('evaluation_id'), cite_as=ref.get('evaluation_id') or eid,
                pointer=arguments.get('pointer', ''), view=view, offset=offset, total_items=total,
                next_offset=offset + limit if total is not None and offset + limit < total else None,
                byte_offset=start, next_byte_offset=end if end < len(raw) else None,
                content=value if complete else fragment, content_format='json' if complete else 'json_text_fragment',
                content_bytes=end-start, selected_bytes=len(raw))


def diagnostic_entries(data, eid):
    return {name: dict(evidence_id=eid, pointer='/data/diagnostics/' + name) for name in data.get('diagnostics', {})}


def evaluation_overview(data, eid):
    fields = ('candidate_id', 'canonical_task_status', 'position_error_m', 'predicted_position_error_m',
              'actual_tip_m', 'model_tip_m', 'failure_attribution', 'trajectory_available', 'failure_code')
    return {**{k: data[k] for k in fields if k in data}, 'evaluation_id': eid,
            'diagnostic_entries': diagnostic_entries(data, eid),
            'note': '完整基本评价摘要；详细诊断从上述 pointer 直接读取，诊断不构成已证明的因果归因。'}
