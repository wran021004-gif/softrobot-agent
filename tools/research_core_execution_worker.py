"""One contained complete execution; recovery never launches this worker."""
import sys
from pathlib import Path
from tools.service_execution import contain_worker_children
from tools.state_io import read, atomic_json


def execute(request):
    from tools.platform_host import Host
    from tools.execution_completion import complete_execution
    from extensions.tendon_family.control_evidence import RECORD_UPDATE_IDS, COMPLETE_UPDATE_INPUTS
    child=Host(Path(request['root']),request['owner'],actor=request['actor'])
    child.create(request['configuration'],parent_run_id=request['study'])
    trace=RECORD_UPDATE_IDS.set(tuple(request['recording']['update_ids']))
    capture=COMPLETE_UPDATE_INPUTS.set(request['recording']['complete_update_inputs'])
    try: return complete_execution(child,request['configuration'],request['candidate_id'])
    finally:
        RECORD_UPDATE_IDS.reset(trace); COMPLETE_UPDATE_INPUTS.reset(capture)


def main():
    job=contain_worker_children()  # Retain the handle throughout the worker lifetime.
    path=Path(sys.argv[1]); request=read(path)
    try: value=execute(request)
    except Exception as exc:
        value=dict(status='execution_incomplete',error=type(exc).__name__,reason=str(exc))
    atomic_json(path.with_name('result.json'),value)


if __name__=='__main__': main()
