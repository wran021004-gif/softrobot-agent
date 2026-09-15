"""Read-only legacy association; never fabricate platform identities in old files."""
from pathlib import Path
from tools.state_io import read
from tools.artifact_tools import file_hash


def inspect_history(root):
    root = Path(root).resolve()
    state_path = root / 'state.json'
    if not state_path.is_file():
        raise ValueError('HISTORY_STATE_MISSING')
    state = read(state_path)
    checked, errors, mutable = [], [], []
    for ref, entry in state.get('evidence', {}).items():
        if not isinstance(entry, dict):
            errors.append(dict(ref=ref, error='UNSUPPORTED_HISTORICAL_REFERENCE_FORMAT'))
            continue
        path = (root / entry.get('path', ref)).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            errors.append(dict(ref=ref, error='MISSING_OR_OUTSIDE_ROOT'))
            continue
        actual = file_hash(path)
        expected = entry.get('sha256')
        if path.name in ('state.json', 'budget.json', 'working_memory.json') and path.parent == root:
            mutable.append(dict(ref=ref, recorded_sha256=expected, current_sha256=actual,
                status='mutable_working_state_not_immutable_evidence'))
            continue
        if expected and actual != expected:
            errors.append(dict(ref=ref, error='HASH_MISMATCH'))
        checked.append(dict(ref=ref, recorded_sha256=expected, current_sha256=actual,
                            integrity='verified' if expected == actual else 'historical_hash_not_recorded'))
    return dict(source_root=str(root), source_state_sha256=file_hash(state_path), version=state.get('version'),
        references=checked, mutable_working_state=mutable, errors=errors, readonly=True, new_fields_backfilled=False,
        resume='Use original entry with its original source/runtime requirements; platform import grants no old budget')
