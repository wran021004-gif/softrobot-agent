"""Contained numerical subprocess execution with Windows kill-on-close jobs."""
import subprocess,sys,os
from tools.paths import ROOT
def _run_contained(command, log, timeout_s):
    """Kill the owned worker tree; no shell or unrelated-process enumeration."""
    import signal
    from uuid import uuid4
    job_name='Local\\softrobot-worker-'+uuid4().hex
    environment=os.environ.copy();environment['SOFTROBOT_WORKER_JOB_NAME']=job_name
    process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),start_new_session=os.name!='nt',env=environment)
    try:
        code=process.wait(timeout=timeout_s)
        return subprocess.CompletedProcess(command,code)
    except subprocess.TimeoutExpired as exc:
        exc.termination_confirmed=False
        if os.name=='nt':
            _terminate_worker_job(process,job_name)
        else:
            os.killpg(process.pid,signal.SIGKILL)
        process.wait(timeout=5)
        exc.termination_confirmed=True
        raise
    finally:
        if os.name!='nt':
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass

def _terminate_worker_job(process,job_name):
    import ctypes as c
    from ctypes import wintypes as w
    import time
    class Accounting(c.Structure):
        _fields_=[('user',c.c_longlong),('kernel',c.c_longlong),('period_user',c.c_longlong),
            ('period_kernel',c.c_longlong),('faults',w.DWORD),('total',w.DWORD),('active',w.DWORD),('terminated',w.DWORD)]
    kernel=c.WinDLL('kernel32',use_last_error=True)
    kernel.OpenJobObjectW.argtypes=[w.DWORD,w.BOOL,w.LPCWSTR];kernel.OpenJobObjectW.restype=w.HANDLE
    kernel.TerminateJobObject.argtypes=[w.HANDLE,w.UINT]
    kernel.QueryInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.c_void_p]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    job=kernel.OpenJobObjectW(0x0004|0x0008,False,job_name)
    if not job:
        # Containment is installed before any child creation. The leader can be
        # killed here, but without a job query the boundary remains uncertain.
        process.kill();process.wait(timeout=5)
        raise RuntimeError('WORKER_JOB_UNAVAILABLE: termination cannot be verified')
    try:
        if not kernel.TerminateJobObject(job,1): raise OSError(c.get_last_error())
        limit=time.monotonic()+5
        while True:
            info=Accounting()
            if not kernel.QueryInformationJobObject(job,1,c.byref(info),c.sizeof(info),None): raise OSError(c.get_last_error())
            if info.active==0: return
            if time.monotonic()>=limit: raise RuntimeError('WORKER_JOB_TERMINATION_UNCERTAIN')
            time.sleep(.01)
    finally: kernel.CloseHandle(job)

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
    job=kernel.CreateJobObjectW(None,os.environ.get('SOFTROBOT_WORKER_JOB_NAME','Local\\softrobot-worker-'+str(os.getpid())))
    if not job:raise OSError('PROCESS_CONTAINMENT_UNAVAILABLE: '+str(c.get_last_error()))
    limits=Extended();limits.basic.flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(job,9,c.byref(limits),c.sizeof(limits)) or not kernel.AssignProcessToJobObject(job,kernel.GetCurrentProcess()):
        error=c.get_last_error();kernel.CloseHandle(job)
        raise OSError('PROCESS_CONTAINMENT_UNAVAILABLE: '+str(error))
    # Deliberately not closed here: closing while this worker runs kills the job.
    return job

