"""Current-study reservation gate around the established numerical operations."""
import sys
import time
import traceback
from tools.state_io import read, atomic_json
from tools.platform_store import Store


def main():
    request = read(sys.argv[1]); store = Store(request['store_root'])
    s = store.session(request['study_id'])['state']; pending = s.get('pending') or {}
    row = store.lookup(request['study_id'], request['request_id'])
    if (not row or row['receipt'] or pending.get('kind') != 'mechanics' or
        pending.get('worker_request_id') != request['request_id'] or pending.get('input') != sys.argv[1]):
        raise ValueError('CURRENT_STUDY_ACTIVE_NUMERICAL_RESERVATION_REQUIRED')
    started = time.perf_counter()
    from tools.casadi_feedback_worker import solve, recover, clean
    try:
        if request['operation'] == 'solve':
            value = solve(request['configuration'], request['arguments'], 'reverse',
                request.get('saved_tensions'), request['progress'],
                dict(study_id=request['study_id'], request_id=request['request_id'],
                     implementation=request['implementation'], execution_id=row['execution_id'],offline_solver_s=request.get('offline_solver_s',570.)))
        elif request['operation'] == 'recover': value = recover(read(request['progress']))
        elif request['operation'] in ('integrate','inspect'):
            from tools.research_core_numerics import offline_diagnostic
            value=offline_diagnostic(request)
        else:
            from tools.casadi_codesign_worker import replay
            value = replay(request['configuration'], request['candidate'])
    except Exception as exc:
        value = dict(status='engineering_error', exception_type=type(exc).__name__,
                     termination_reason=str(exc), traceback=traceback.format_exc(),
                     costs_s=dict(total=time.perf_counter()-started))
    atomic_json(sys.argv[2], clean(value))


if __name__ == '__main__': main()
