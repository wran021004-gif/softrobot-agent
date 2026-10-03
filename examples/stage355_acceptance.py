"""Focused offline gate with forbidden live paths and byte-preserving evidence."""
from contextlib import ExitStack
import hashlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.runtime_identity import require_softagent_runtime
from tools.state_io import atomic_json

MODULES=['tests.test_stage355_working_state','tests.test_stage354_references',
         'tests.test_stage353_completion','tests.test_stage351_settling','tests.test_stage352_context']


def run(names, output):
    runtime=require_softagent_runtime()
    import mujoco
    runtime['mujoco_version']=mujoco.__version__
    stream=io.StringIO()
    with ExitStack() as guards:
        live_attempts=[0,0,0]
        for index,target in enumerate(('tools.model_transports.deepseek.request_completion',
                       'extensions.tendon_family.backends.MujocoBackend.run',
                       'extensions.tendon_family.gvs_trajectory.TrajectoryWorkspace.solve')):
            def forbidden(*args, _index=index, _target=target, **kwargs):
                live_attempts[_index]+=1
                raise AssertionError('FORBIDDEN_LIVE_EXECUTION: '+_target)
            # A function preserves support for existing autospec fixture mocks.
            guards.enter_context(patch(target,new=forbidden))
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    destination=ROOT/'evidence/stage355_milestone1_20261003';destination.mkdir(exist_ok=True)
    log=stream.getvalue()
    if (destination/(output+'.json')).exists():
        index=2
        while (destination/(output+str(index)+'.json')).exists():index+=1
        output+=str(index)
    (destination/(output+'.txt')).write_bytes(log.encode('utf8'))
    atomic_json(destination/(output+'.json'),dict(runtime=runtime,
        command='"C:\\Users\\gugugaga\\miniconda3\\envs\\softagent\\python.exe" examples/stage355_acceptance.py '+(' '.join(names) if names!=MODULES else ''),
        modules=names,tests_run=result.testsRun,passed=result.wasSuccessful(),
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        forbidden_live_attempts=live_attempts,new_provider_requests=0,new_backend_simulations=0,new_numerical_optimization_runs=0,workers=0,subagents=0,
        scope='Offline saved-store reads, payload construction and small isolated fixtures. Evaluator/profile fixture work is local; no paid validation.'))
    print(log.encode('ascii',errors='backslashreplace').decode('ascii'))
    return result.wasSuccessful()


if __name__=='__main__':
    names=sys.argv[1:] or MODULES
    sys.exit(0 if run(names,'focused_checks' if names==MODULES else 'affected_rerun') else 1)
