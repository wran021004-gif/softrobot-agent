"""Private subprocess worker; the public API is Workbench.submit, never this module."""
import sys
from pathlib import Path
from schemas.workbench import WorkbenchResult
from tools.state_io import read, atomic_json


def main():
    root, folder = (Path(p).resolve() for p in sys.argv[1:])
    from tools.workbench import owner
    with owner(root, '.worker.lock'):
        work(root, folder)


def work(root, folder):
    job = read(folder / 'job.json')
    try:
        from tools.workbench_actions import execute
        result = execute(job['tool'], job['arguments'], root, folder, read(root / 'state.json'))
    except Exception as exc:
        result = WorkbenchResult(status='failed', tool=job['tool'], failure_code='TOOL_ERROR',
                                 message=f'{type(exc).__name__}: {exc}')
    atomic_json(folder / 'result.json', result.model_dump(mode='json'))


if __name__ == '__main__':
    main()
