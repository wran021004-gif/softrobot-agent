"""Byte-bounded JSON evidence pages and request encoding for the dynamic campaign."""
import hashlib
import json


TARGET_BYTES = 50000
MAX_REQUEST_BYTES = 60000
PAGE_VERSION = 'dynamic_evidence_v1'
PROMPT_VERSION = 'dynamic_selected_design_v3'
READING_GUIDANCE = '''
[dynamic_selected_design_v3: overrides historical workflow/language instructions]
Write ALL newly generated natural language in English: reason, working_memory
findings/unresolved/next_action, diagnostic statement, and stop reason. Keep exact
evidence paths, entity IDs, units and numeric values. Historical records may be
Chinese; do not translate or alter them and do not imitate their output language.
Read candidate summaries first and identify the specific missing evidence. Use
read_evidence with an exact JSON pointer, small limit and max_bytes=4000 (cap 8000).
Pages preserve source indices: content[i] in an array is source offset+i; cite
evidence_ref plus that original pointer/index, entity, time interval and raw value.
Follow next_read for another page. A directory means an oversized nested item:
read its child pointers, then use resume_container for the remaining siblings.
String pages use character offsets. Never mistake a preview for the whole file.
Consume the current page before reading again; write concise conclusions and
exact evidence references to working_memory, including the next unread location.
Do not repeatedly read the root or restart a completed experiment to recover facts.
Before each read, state in reason the specific question it will answer. has_more
only says more data exists; it does NOT require reading every page. Use an exact
pointer or diagnose_trajectory for an entity/time question instead of scanning
history. Different offsets and child pointers are normal; reread an unchanged
slice only with a stated reason. Once evidence is sufficient, diagnose, select an
experiment, verify, or finish. Historical baseline steps apply ONLY to missing
evidence. c057, c065 and c066 are historical MuJoCo successes; c066 has the smallest
reported error. They predate this runtime experiment and are not your discoveries.
When experiment llm_reach_v1 is present, its c032 baseline and new descendants
define progress. Choose your own hypothesis, small authorized variable subset,
batch size and search settings in an optimize_matlab tool call; deterministic
tools generate trial parameter values. Keep the force limit at 20 N. Start with
at most 24 new MATLAB trials; total ceilings are 24 requests (including corrections),
40 MATLAB trials, 3 MuJoCo trials and 1800 activity seconds, subject to remaining
campaign budget and closeout reserves. These are ceilings, not consumption goals.
Use a fresh search_id prefixed llm_reach_v1_. Consume actual optimization feedback
and record your interpretation in working_memory before selecting a resulting
candidate for MuJoCo. Use that feedback for a justified continuation OR closeout;
no extra search is required if the first verification succeeds. Record a precise
checked diagnosis for an experiment candidate and stop_design with evidence.
Historical success/cache reuse does not count as fresh experiment completion.
Report workflow completion, fresh numerical completion and MuJoCo success separately.
At closeout, set stop_design.selected_candidate_id to YOUR final design choice;
use null only when no design can be selected. Give a brief English reason for
that choice. Historical best and your final selection are separate facts.
'''


def encoded_size(value):
    # Identical to request_completion's complete wire JSON, including escaping.
    return len(json.dumps(value, ensure_ascii=False).encode('utf-8'))


def child_pointer(pointer, key):
    return pointer + '/' + str(key).replace('~', '~0').replace('/', '~1')


def resolve_pointer(value, pointer):
    if pointer and not pointer.startswith('/'):
        raise ValueError('JSON pointer must be empty or start with /')
    for part in pointer.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not part.isdigit():
                raise ValueError('Array pointer requires an original nonnegative index')
            value = value[int(part)]
        else:
            value = value[part]
    return value


def evidence_page(document, evidence_ref, pointer='', offset=0, limit=10, max_bytes=4000):
    """Bound the entire returned page; never truncate serialized JSON or reindex it."""
    if not 1000 <= max_bytes <= 8000 or offset < 0 or not 1 <= limit <= 50:
        raise ValueError('Invalid evidence page bounds')
    value = resolve_pointer(document, pointer)
    kind = 'array' if isinstance(value, list) else 'object' if isinstance(value, dict) else 'string' if isinstance(value, str) else 'scalar'
    total = len(value) if kind != 'scalar' else 1
    start = min(offset, total)

    def cursor(at_pointer, at_offset=0):
        return dict(evidence_ref=evidence_ref, pointer=at_pointer, offset=at_offset,
                    limit=limit, max_bytes=max_bytes)

    def envelope(content, count):
        end = start + count
        return dict(page_version=PAGE_VERSION, evidence_ref=evidence_ref, cite_as=evidence_ref,
                    pointer=pointer, kind=kind, offset=start, returned_count=count,
                    returned_range=dict(start=start, end_exclusive=end), total=total,
                    next_offset=end, has_more=end < total,
                    next_read=cursor(pointer, end) if end < total else None,
                    content=content)

    if kind == 'string':
        # Page the source string itself, not its JSON encoding. Binary search also
        # accounts for UTF-8 and escaped quotes/control characters in the envelope.
        lo, hi = 0, total - start
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if encoded_size(envelope(value[start:start+mid], mid)) <= max_bytes:
                lo = mid
            else:
                hi = mid - 1
        page = envelope(value[start:start+lo], lo)
        if (lo == 0 and start < total) or encoded_size(page) > max_bytes:
            raise ValueError('Evidence pointer/metadata cannot fit max_bytes')
        return page

    keys = list(range(total)) if kind == 'array' else list(value) if kind == 'object' else [None]
    content = [] if kind == 'array' else {} if kind == 'object' else None
    page = envelope(content, 0)
    for key in keys[start:start+limit]:
        item = value if kind == 'scalar' else value[key]
        proposed = content + [item] if kind == 'array' else {**content, key: item} if kind == 'object' else item
        trial = envelope(proposed, page['returned_count'] + 1)
        if encoded_size(trial) <= max_bytes:
            content, page = proposed, trial
            continue
        if page['returned_count']:
            break
        # No data item was consumed. Descend instead of returning the same empty
        # page; retain an explicit sibling continuation after reading this child.
        at = child_pointer(pointer, key) if kind != 'scalar' else pointer
        page.update(content=None, mode='directory', blocked_pointer=at,
                    next_read=cursor(at), has_more=True,
                    resume_container=cursor(pointer, start+1) if start+1 < total else None,
                    directory=[])
        entries = item.items() if isinstance(item, dict) else enumerate(item) if isinstance(item, list) else []
        for child, nested in entries:
            entry = dict(pointer=child_pointer(at, child), type=type(nested).__name__)
            if isinstance(nested, (dict, list, str)):
                entry['length'] = len(nested)
            trial = {**page, 'directory': page['directory'] + [entry]}
            if len(page['directory']) >= 8 or encoded_size(trial) > max_bytes:
                break
            page = trial
        break
    if encoded_size(page) > max_bytes:
        raise ValueError('Evidence pointer/metadata cannot fit max_bytes')
    return page


def prompt_with_version(base):
    replacements = {
        'statement 中文区分观察和假设。': 'Write the diagnostic statement in English, distinguishing observation from hypothesis.',
        '先读 history/c002_diagnosis.json，再检查/执行 c000 的 MATLAB 动态基线和 MuJoCo 对照。': 'Review historical baseline evidence only if it is still missing; do not restart completed baseline work.',
        '从明确 V2 候选开始选择约4-6个连续变量 optimize_matlab；先保持20N，优先控制 bend_z_rad/bias_fraction/servo kp、质量、EI/粘性、路由。': 'Select your own small subset of authorized continuous variables for optimize_matlab from a V2 parent; keep 20 N for this experiment.',
        'max_evaluations 先用24至40': 'choose max_evaluations within the experiment remainder, initially at most 24',
    }
    effective = base
    for old, new in replacements.items():
        effective = effective.replace(old, new)
    effective += '\n' + READING_GUIDANCE
    version = dict(version=PROMPT_VERSION, base_ref='inputs/system_prompt.md',
                   base_sha256=hashlib.sha256(base.encode('utf-8')).hexdigest(),
                   effective_sha256=hashlib.sha256(effective.encode('utf-8')).hexdigest(),
                   appended_guidance=READING_GUIDANCE, replacements=replacements)
    return effective, version


def request_progress(book):
    """Read cursors come from persisted results, not model-authored prose."""
    from tools.state_io import read
    reads = []
    for attempt in reversed(book.state['attempts']):
        if attempt['tool'] not in ('read_evidence', 'diagnose_trajectory'):
            continue
        result = read(book.root / attempt['result_ref'])
        if result.get('status') != 'completed':
            continue
        args, data = attempt['arguments'], result['data']
        if attempt['tool'] == 'read_evidence':
            offset = data.get('offset', args.get('offset', 0))
            content = data.get('content')
            count = data.get('returned_count', len(content) if isinstance(content, (list, dict)) else 1)
            row = dict(evidence_ref=data.get('evidence_ref', args['evidence_ref']),
                       pointer=data.get('pointer', args.get('pointer', '')), offset=offset,
                       returned_range=data.get('returned_range', dict(start=offset, end_exclusive=offset+count)),
                       next_read=data.get('next_read'), resume_container=data.get('resume_container'))
            decision = next((d for d in reversed(book.state['decisions']) if d.get('result_ref') == attempt['result_ref']), {})
            row['source_sha256'] = decision.get('evidence_hashes', {}).get(row['evidence_ref'])
        else:
            row = dict(evidence_ref=data.get('raw_fields_ref', attempt['result_ref']),
                       entity=args['entity'], t_start_s=args['t_start_s'], t_end_s=args['t_end_s'])
        row['result_ref'] = attempt['result_ref']
        reads.append(row)
        if len(reads) == 3:
            break
    notice = None
    if len(reads) > 1 and reads[0].get('source_sha256'):
        signature = lambda r: tuple(str(r.get(k)) for k in ('evidence_ref', 'pointer', 'offset', 'returned_range', 'source_sha256'))
        if any(signature(reads[0]) == signature(r) for r in reads[1:]):
            notice = 'An unchanged evidence slice was read again. State why another reread is needed, or act on the findings.'
    memory = book.state['working_memory']
    exp = book.experiment_summary()
    questions = {
        'baseline_review': ['Which baseline evidence explains the remaining c032 error?', 'Which small authorized variable subset tests your hypothesis?'],
        'optimization': ['What did the actual MATLAB search improve or fail to improve?'],
        'verification': ['Which newly generated candidate should receive MuJoCo verification?'],
        'diagnosis': ['What exact entity/time/value explains the experiment verification result?'],
        'closeout': ['Does quantitative feedback justify stopping or another small adjustment?'],
    }
    phase = exp['phase'] if exp else 'diagnosis'
    return dict(phase=phase, objective=exp['objective'] if exp else 'Answer the remaining reach evidence questions, then close out with checked facts.',
                questions=questions[phase], unresolved=[str(x)[:180] for x in memory.get('unresolved', [])[:3]],
                recent_reads=list(reversed(reads)), findings=[str(x)[:200] for x in memory.get('findings', [])[:3]],
                next_decision=str(memory.get('next_action', ''))[:200], repeated_read_notice=notice)


class RequestTooLarge(ValueError):
    def __init__(self, metrics):
        self.metrics = metrics
        super().__init__(f"Bounded model request {metrics['total_bytes']} exceeds {MAX_REQUEST_BYTES} bytes; protected content retained")
