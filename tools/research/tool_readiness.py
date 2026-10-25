"""Contained engineering checks and admission; no scientific experiments or engine pool."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from tools.state_io import atomic_json, read, digest
from tools.platform_store import zero, plain
from tools.research.state import state, save, update

MATLAB_ACTIONS = ('execute','mechanics','replay','cross_replay','refine','matched_state','nmpc_prediction_diagnostic','search')


def execution_environment(spec):
    """Read-only pre-authorization check of Host and the actual math interpreter."""
    from tools.research.optimal_capability import dependencies,CONIC
    from importlib.metadata import version
    expected=Path(spec['runtime']['research_python']).resolve()
    exact=Path(sys.executable).resolve()==expected
    conic=dependencies()
    threads={k:dict(expected=v,actual=os.environ.get(k)) for k,v in spec.get('numerical_environment',{}).items()}
    ready=exact and all(v['actual']==v['expected'] for v in threads.values()) and (conic['available'] or not spec.get('mathematical_methods',{}).get(CONIC))
    return dict(status='ready' if ready else 'not_ready',host_python=sys.executable,expected_research_python=str(expected),
        exact_execution_interpreter=exact,mathematical_worker_python=sys.executable,conic=conic,threads=threads,
        packages={k:version(k) for k in ('numpy','scipy','casadi','mujoco','pydantic','strands-agents','strands-harness')},
        scope='Imports and interpreter/thread admission only; no NMPC, PPO, physics or Provider request')


def probe(session_factory=None):
    from extensions.tendon_family.sorosim_session import SorosimSession, dependency_identity
    result=dict(tool='sorosim_matlab',checked_unix=time.time(),status='not_checked',steps=[],
        environment=dict(python=sys.executable,version=sys.version,cwd=str(Path.cwd()),
            **{k:os.environ.get(k) for k in ('SOROSIM_ROOT','PYTHONPATH','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')}),
        scientific_evidence=False,task_acceptance='unmeasured')
    stage='dependency'
    session=None
    try:
        import scipy, casadi, matlab.engine
        result['versions']=dict(scipy=scipy.__version__,casadi=casadi.__version__,engine=matlab.engine.__file__)
        result['dependency']=dependency_identity(os.environ['SOROSIM_ROOT'])
        result['steps'].append('dependencies')
        stage='engine_start'
        session=(session_factory or SorosimSession)()
        with session:
            result['steps'].extend(['engine_start','environment_gateway'])
            result['gateway']=session.environment
            stage='simple_calculation'
            if float(session.engine.sqrt(4.))!=2.:raise ValueError('MATLAB_SIMPLE_CALCULATION_FAILED')
            result['steps'].append('simple_calculation')
            stage='shutdown'
        result['steps'].append('shutdown')
        result['status']='ready'
    except Exception as exc:
        if stage=='engine_start' and session is not None and session.startup_stage=='gateway':stage='gateway'
        result.update(status={'dependency':'dependency_unavailable','engine_start':'engine_start_failed'}.get(stage,'gateway_failed'),
            failed_stage=stage,error=type(exc).__name__,reason=str(exc),traceback=traceback.format_exc())
        if isinstance(exc,UnicodeDecodeError):
            result['encoding_failure']=dict(encoding=exc.encoding,start=exc.start,end=exc.end,raw_hex=exc.object.hex(),
                diagnostic_gb18030=exc.object.decode('gb18030',errors='replace'))
    if session is not None:result['timings']=session.timings
    return result


def check(host, timeout_s=90):
    """One Store-owned engineering attempt; unknown attempts cannot be relaunched."""
    s=state(host)
    if s['spec']['mode']!='engineering_numerical' or s.get('freeze'):
        raise ValueError('READINESS_REQUIRES_UNFROZEN_ENGINEERING_SESSION')
    key='s8-tool-readiness'
    row,fresh=host.store.reserve(host.run_id,key,digest(dict(timeout_s=timeout_s)),host.actor,
        {**zero(),'tool_calls':1},resources=('backend.family_mujoco',))
    if not fresh:
        if not row['receipt']:raise ValueError('UNKNOWN_READINESS_OUTCOME_NO_RETRY')
        return host.store.artifact(json.loads(row['receipt'])['output'])
    folder=host.store.root/'readiness';folder.mkdir(exist_ok=True)
    from tools.service_execution import _run_contained
    started=time.perf_counter()
    try:
        with (folder/'worker.log').open('w',encoding='utf8') as log:
            done=_run_contained([s['spec']['runtime']['research_python'],'-m',__name__,str(folder/'result.json')],log,timeout_s)
        result=read(folder/'result.json') if (folder/'result.json').exists() else dict(status='gateway_failed',reason='worker_result_missing')
        result['boundary']=dict(termination_confirmed=True,returncode=done.returncode)
    except subprocess.TimeoutExpired as exc:
        result=dict(status='timeout',boundary=dict(termination_confirmed=exc.termination_confirmed),reason=str(exc))
    result.update(elapsed_s=time.perf_counter()-started,scientific_evidence=False,
        log_reference=save(host,dict(text=(folder/'worker.log').read_text(encoding='utf8',errors='replace')),'readiness_log'))
    host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
        tool_id='research.tool_readiness',tool_version='1.0.0',execution_status='completed',charged=zero()),result)
    atomic_json(folder/'report.json',result)
    return result


def availability(host):
    s=state(host)
    return s.get('tool_failures',{}).get('sorosim_matlab') or s['spec'].get('tool_readiness',{}).get('sorosim_matlab')


def require(host, action):
    status=availability(host)
    controller=state(host)['spec']['configuration']['policy']['controller']['extension_id']
    if controller=='controller.sorosim_matlab_nmpc' and status and status['status']!='ready' and (action in MATLAB_ACTIONS or action=='analysis'):
        raise ValueError('ENGINEERING_TOOL_UNAVAILABLE: sorosim_matlab '+status['status'])


def observe_failure(host, raw, reference):
    """Preserve a charged engineering failure and disable further startup attempts."""
    reason=json.dumps(raw)
    if any(x in reason for x in ('UnicodeDecodeError','MATLAB_SESSION_CLOSED','MatlabEngineError','EngineError','SOROSIM_ROOT_REQUIRED')):
        s=state(host)
        update(host,tool_failures={**s.get('tool_failures',{}),'sorosim_matlab':dict(
            status='engine_start_failed',failure_reference=plain(reference),scientific_infeasibility=False)})


if __name__=='__main__':
    from tools.service_execution import contain_worker_children
    job=contain_worker_children()
    atomic_json(Path(sys.argv[1]),probe())
