"""Byte-bounded JSON evidence pages and request encoding for the dynamic campaign."""
import hashlib
import json


TARGET_BYTES = 50000
MAX_REQUEST_BYTES = 60000
PAGE_VERSION = 'dynamic_evidence_v1'
PROMPT_VERSION = 'dynamic_evidence_reading_v1'
READING_GUIDANCE = '''
[dynamic_evidence_reading_v1]
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
    effective = base + '\n' + READING_GUIDANCE
    version = dict(version=PROMPT_VERSION, base_ref='inputs/system_prompt.md',
                   base_sha256=hashlib.sha256(base.encode('utf-8')).hexdigest(),
                   effective_sha256=hashlib.sha256(effective.encode('utf-8')).hexdigest(),
                   appended_guidance=READING_GUIDANCE)
    return effective, version


class RequestTooLarge(ValueError):
    def __init__(self, metrics):
        self.metrics = metrics
        super().__init__(f"Bounded model request {metrics['total_bytes']} exceeds {MAX_REQUEST_BYTES} bytes; protected content retained")
