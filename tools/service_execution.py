"""Reusable service binding execution and immutable identity/cache policy."""
import subprocess
import sys
import os
from tools.spec_tools import ROOT
from tools.artifact_tools import file_hash
from tools.state_io import digest, atomic_json, read


def identity(definition, arguments, evidence):
    from tools.workbench import runtime
    module=definition.binding.split(':')[0].replace('.','/')+'.py'
    paths=set(definition.sources) | {module,'tools/tool_registry.py','tools/service_execution.py',
        'tools/service_worker.py','tools/public_services.py','tools/public_feedback.py','schemas/public_tools.py'}
    hashes={p:file_hash(ROOT/p) for p in sorted(paths)}
    value=dict(tool_id=definition.tool_id,version=definition.version,
        input_schema=definition.schema.model_json_schema(),output_schema=definition.output_schema.model_json_schema() if definition.output_schema else None,arguments=arguments,
        sources=hashes,evidence=evidence,runtime=runtime())
    return digest(value),hashes


def execute(definition, root, registry, arguments, folder):
    from tools.tool_registry import execute_binding
    if definition.isolation=='inline':
        return execute_binding(definition,root,registry,arguments)
    # A process is killable: unlike a future/thread timeout it cannot keep working
    # after the invocation is sealed. Current process tools produce data only.
    request=folder/'worker_request.json'
    atomic_json(request,dict(tool_id=definition.tool_id,root=str(root),registry=registry,arguments=arguments))
    try:
        with (folder/'worker.log').open('w',encoding='utf8') as log:
            command=[sys.executable,'-m','tools.service_worker',str(request)]
            if definition.process_tree:
                completed=_run_contained(command,log,definition.timeout_s)
            else:
                completed=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=definition.timeout_s,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError('TIMEOUT: worker deadline exceeded; termination requested; reservation retained') from exc
    result=read(folder/'worker_result.json') if (folder/'worker_result.json').exists() else {}
    if completed.returncode or 'error' in result:raise ValueError(result.get('error','WORKER_FAILED: inspect worker.log'))
    from tools.public_services import checked_path
    returned=result.get('registry',{})
    for ref,item in registry.items():
        if returned.get(ref)!=item:raise ValueError('EVIDENCE_CHANGED_BY_WORKER')
    for ref,item in returned.items():
        if ref not in registry:
            checked_path(root,returned,ref)
            registry[ref]=item
    return result['data']


def _run_contained(command, log, timeout_s):
    """Kill the owned worker tree; no shell or unrelated-process enumeration."""
    import signal
    process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),start_new_session=os.name!='nt')
    try:
        code=process.wait(timeout=timeout_s)
        return subprocess.CompletedProcess(command,code)
    except subprocess.TimeoutExpired:
        if os.name=='nt':process.kill()  # Worker job handle closes, killing its descendants.
        else:os.killpg(process.pid,signal.SIGKILL)
        process.wait(timeout=5)
        raise
    finally:
        if os.name!='nt':
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass


def contain_worker_children():
    """Windows kill-on-close job, installed BEFORE any rendering/engine startup.

    The worker owns the handle until process exit (including forced termination).
    Detached services outside the job are not covered. POSIX uses a parent-owned
    process group instead. Failure to attach prevents backend startup.
    """
    if os.name!='nt':return
    import ctypes as c
    from ctypes import wintypes as w
    class Basic(c.Structure):
        _fields_=[('process_time',c.c_longlong),('job_time',c.c_longlong),('flags',w.DWORD),
            ('min_working',c.c_size_t),('max_working',c.c_size_t),('active',w.DWORD),
            ('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
    class Extended(c.Structure):
        _fields_=[('basic',Basic),('io',c.c_ulonglong*6),('process_memory',c.c_size_t),
            ('job_memory',c.c_size_t),('peak_process',c.c_size_t),('peak_job',c.c_size_t)]
    kernel=c.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR];kernel.CreateJobObjectW.restype=w.HANDLE
    kernel.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD]
    kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
    kernel.GetCurrentProcess.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE]
    job=kernel.CreateJobObjectW(None,None)
    if not job:raise OSError('PROCESS_CONTAINMENT_UNAVAILABLE: '+str(c.get_last_error()))
    limits=Extended();limits.basic.flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(job,9,c.byref(limits),c.sizeof(limits)) or not kernel.AssignProcessToJobObject(job,kernel.GetCurrentProcess()):
        error=c.get_last_error();kernel.CloseHandle(job)
        raise OSError('PROCESS_CONTAINMENT_UNAVAILABLE: '+str(error))
    # Deliberately not closed here: closing while this worker runs kills the job.
    return job
