"""Shared durable JSON and content identity, independent of any campaign."""
import hashlib
import json
import os
from pathlib import Path


def io_path(path):
    """Filesystem access only; keep logical paths/identities in saved records."""
    value=os.fspath(path)
    if os.name=='nt':
        value=os.path.abspath(value)
        if not value.startswith('\\\\?\\'):
            value=('\\\\?\\UNC\\'+value[2:]) if value.startswith('\\\\') else '\\\\?\\'+value
    return Path(value)


def read(path):
    return json.loads(io_path(path).read_text(encoding='utf-8'))


def effective_input(configuration):
    """Extract saved input envelopes without loading schemas or source files.

    Accept SessionInput, effective/compiled envelopes, frozen Study snapshots,
    and task-only dictionaries. Consumers own their completeness requirements.
    """
    value = configuration.model_dump(mode='json') if hasattr(configuration, 'model_dump') else configuration
    for key in ('effective', 'input', 'configuration'):
        if key in value:
            return effective_input(value[key])
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def atomic_json(path, value):
    path = io_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    temporary.replace(path)
