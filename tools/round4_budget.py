"""Single-writer, durable reservations. Crashed attempts are charged, never replayed automatically."""
from contextlib import contextmanager
from pathlib import Path
import os
from tools.closeout_state import atomic_json, read, digest
from tools.artifact_tools import file_hash

LIMITS = dict(length_screen=24, length_mujoco=28, development_mujoco=12, mechanics=24)


class Budget:
    def __init__(self, root, *, retry_interrupted=False):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'budget.json'
        self.retry_interrupted = retry_interrupted

    @contextmanager
    def lock(self):
        path = self.root / '.writer.lock'
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode())
            yield
        finally:
            os.close(fd)
            path.unlink()

    def reserve(self, kind, key, context, *, stage='development'):
        with self.lock():
            value = read(self.path) if self.path.exists() else dict(limits=LIMITS, attempts=[])
            if value['limits'] != LIMITS:
                raise ValueError('Budget limits changed')
            matches = [r for r in value['attempts'] if r['key'] == key and r['kind'] == kind]
            if matches:
                row = matches[-1]
                if digest(row['context']) != digest(context) or row['stage'] != stage:
                    raise ValueError('Cached attempt input/context changed; no silent reuse')
                if row['status'] == 'completed':
                    if file_hash(row['artifact']) != row['sha256']:
                        raise ValueError('Sealed result changed')
                    return row, True
                if row['status'] != 'reserved' or not self.retry_interrupted:
                    raise ValueError('Attempt already charged; explicit --resume required: ' + key)
                # An explicit candidate-boundary resume consumes another attempt.
                # The old reservation remains charged and is never silently reset.
                row['status'] = 'interrupted'
            used = [r for r in value['attempts'] if r['kind'] == kind]
            if len(used) >= LIMITS[kind]:
                raise ValueError('Budget exhausted: ' + kind)
            stage_cap = {'length_screen': {'coarse':20, 'fine':4}, 'length_mujoco': {'coarse':20, 'fine':8}}
            if kind in stage_cap and sum(r['stage'] == stage for r in used) >= stage_cap[kind][stage]:
                raise ValueError('Stage budget exhausted')
            row = dict(id=len(value['attempts']), kind=kind, key=key, context=context, stage=stage,
                status='reserved', retry_of=matches[-1]['id'] if matches else None)
            value['attempts'].append(row)
            atomic_json(self.path, value)
            return row, False

    def complete(self, row, artifact):
        with self.lock():
            value = read(self.path)
            current = value['attempts'][row['id']]
            if current['status'] != 'reserved':
                raise ValueError('Cannot overwrite completed attempt')
            current.update(status='completed', artifact=str(Path(artifact).resolve()), sha256=file_hash(artifact))
            atomic_json(self.path, value)

    def call(self, kind, key, context, artifact, action, *, stage='development'):
        row, cached = self.reserve(kind, key, context, stage=stage)
        if cached:
            return read(row['artifact'])
        try:
            result = action()
        except Exception as exc:
            result = dict(status='error', reason=str(exc), exception=type(exc).__name__)
        atomic_json(artifact, result)
        self.complete(row, artifact)
        return result
