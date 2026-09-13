"""Persist short model notes and a factual read ledger without extra model calls."""
from schemas.workbench import EvidenceArguments
from tools.state_io import digest, atomic_json, read


def remember(book, decision, result):
    memory = book.state.setdefault('working_memory', dict(reads={}, notes=None))
    proposal = decision['proposal']
    if proposal.get('working_memory') and decision.get('status') in ('accepted', 'reused'):
        memory['notes'] = {**proposal['working_memory'], 'decision': decision['sequence'],
                           'authority': 'model_notes_not_evaluator_truth'}
    if proposal.get('tool') != 'read_evidence' or not result or result.get('status') != 'completed':
        return None
    args = EvidenceArguments.model_validate(proposal['arguments']).model_dump()
    ref = book.state['evidence'][args['evidence_id']]
    key = digest({**args, 'evidence_id': ref['path']})
    data = result['data']
    entry = memory['reads'].setdefault(key, dict(selector=args, candidate_id=data.get('candidate_id') or ref.get('candidate_id'),
                                                sequences=[], result_ref=None))
    if decision['sequence'] not in entry['sequences']:
        entry['sequences'].append(decision['sequence'])
    entry.update(result_ref=decision.get('result_ref') or next((a.get('result_ref') for a in book.state['attempts'] if a['decision'] == decision['sequence']), None),
                 next_offset=data.get('next_offset'), next_byte_offset=data.get('next_byte_offset'),
                 content_format=data.get('content_format'), observed=observations(data.get('content')))
    if len(entry['sequences']) > 1:
        return dict(code='REPEATED_READ', previous_decisions=entry['sequences'][:-1],
                    message='同一字段/页已读取，没有新增实验信息。使用已有发现推进修改、比较或停止；若仍缺诊断，直接读取候选 diagnostic_entries，勿重读目录首页。',
                    next_offset=entry['next_offset'], next_byte_offset=entry['next_byte_offset'])
    return None


def observations(value, prefix=''):
    """Record a few actually returned scalar facts, never infer omitted fields."""
    if not isinstance(value, dict):
        return []
    facts = []
    for k, v in value.items():
        if isinstance(v, dict):
            facts.extend(observations(v, prefix + k + '.'))
        elif v is None or isinstance(v, (str, int, float, bool)) or (isinstance(v, list) and len(v) <= 3 and all(isinstance(n, (float, int)) for n in v)):
            facts.append(f'{prefix}{k}={str(v)[:160]}')
    return facts[:8]


def rebuild(book):
    book.state['working_memory'] = dict(reads={}, notes=None)
    for decision in book.state['decisions']:
        attempt = next((a for a in book.state['attempts'] if a['decision'] == decision['sequence']), None)
        ref = decision.get('result_ref') or (attempt.get('result_ref') if attempt else None)
        remember(book, decision, read(book.root / ref) if ref else None)
    save_memory(book)


def save_memory(book):
    atomic_json(book.root / 'working_memory.json', book.state.get('working_memory', {}))
    book.register(book.root / 'working_memory.json', 'working_memory')


def memory_context(state):
    memory = state.get('working_memory', {})
    return dict(notes=memory.get('notes'), reads=[{**r, 'times_read': len(r['sequences'])} for r in memory.get('reads', {}).values()],
                guidance='记录中 observed 只含实际读取的字段；model notes 是有证据引用的简短判断，不改写评价。已读取且完整的结果不必重读。')
