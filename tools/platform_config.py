"""Portable data-file composition. Never import or execute task-config code."""
from pathlib import Path
import yaml


def load(path):
    path = Path(path).resolve()
    value = yaml.safe_load(path.read_text(encoding='utf8'))
    if not isinstance(value, dict):
        raise ValueError('CONFIG_OBJECT_REQUIRED')
    for name in ('task', 'environment', 'robot', 'policy'):
        key = name + '_file'
        if key in value:
            if name in value:
                raise ValueError('CONFIG_DUPLICATE_INLINE_AND_FILE: ' + name)
            reference = value.pop(key)
            if not isinstance(reference, str) or not reference.strip():
                raise ValueError('REQUIRED_CONFIG_FILE: ' + key + ' 必须填写相对于配置文件的路径')
            target = (path.parent / reference).resolve()
            value[name] = load(target)
    return value
