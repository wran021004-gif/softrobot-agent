"""Exact XML-load evidence; native failures stay in the existing contained worker."""
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from tools.research.state import state, update, save, ROOT
from tools.state_io import digest, read, atomic_json


def environment():
    import mujoco
    native=Path(mujoco.__file__).parent
    libraries={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(native.iterdir()) if p.suffix in ('.dll','.pyd')}
    return dict(python=str(Path(sys.executable).resolve()),python_version=platform.python_version(),
        python_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),native_libraries=libraries,
        platform=platform.platform(),machine=platform.machine(),mujoco=mujoco.__version__,
        loader='MjModel.from_xml_path/main_thread',
        threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')})


def capability(host, candidate_ref):
    """Called only at physical execution admission, never for every screening design."""
    from schemas.platform import SessionInput
    from tools.research.design import verify_candidate, numerical_binding
    from extensions.tendon_family.backends import physics_for
    from extensions.tendon_family.scene import assemble
    from extensions.tendon_family.mjcf import compile_xml
    from extensions.tendon_family.contracts import MujocoParameters
    from tools.service_execution import _run_contained
    c=verify_candidate(host,candidate_ref);s=state(host);cfg=c['configuration']
    binding=dict(candidate=candidate_ref,**numerical_binding(cfg,s['spec']),
        backend=cfg['policy']['backend'],environment=environment())
    identity=digest(binding)
    old=s.get('runtime_capabilities',{}).get(identity)
    if old:
        return dict(reference=old,**host.store.artifact(old),reused=True)
    folder=host.store.root/'runtime_capability'/identity
    folder.mkdir(parents=True,exist_ok=True)
    # Durable intent prevents a second probe after interrupted/uncertain native work.
    if (folder/'intent.json').exists() and not (folder/'boundary.json').exists():
        return dict(status='runtime_unresolved',binding=binding,task_success=None,
            reason='Unsettled XML probe; no automatic relaunch')
    started=time.perf_counter()
    inp=SessionInput.model_validate(cfg);physics=physics_for(inp)
    xml=folder/'robot.xml'
    compile_xml(physics,assemble(inp,physics),MujocoParameters.model_validate(cfg['policy']['backend']['parameters']['data']),xml)
    xml_hash=hashlib.sha256(xml.read_bytes()).hexdigest()
    recorded=ROOT/'evidence/m3c3_mixed_family_search/windows_loader_boundary.json'
    known=read(recorded) if recorded.exists() else {}
    previous=next((r for r in known.get('observations',[]) if r['native_exit_code']==-1073741571 and r['xml_sha256']==xml_hash and
        r['environment']==binding['environment'] and r['backend']==binding['backend']),None)
    if (folder/'boundary.json').exists():
        boundary=read(folder/'boundary.json')
    elif previous:
        boundary=dict(returncode=previous['native_exit_code'],termination_confirmed=True,
            reused_recorded_failure=True,evidence=previous['source_evidence'],elapsed_s=0.)
    else:
        if s.get('runtime_probe_launches',0)>=s['spec']['fidelity_policy']['runtime_preflight_limit']:
            return dict(status='runtime_unresolved',binding=binding,task_success=None,reason='Frozen XML preflight count exhausted')
        atomic_json(folder/'intent.json',dict(binding=binding,xml_sha256=xml_hash))
        update(host,runtime_probe_launches=s.get('runtime_probe_launches',0)+1)
        try:
            with (folder/'worker.log').open('w',encoding='utf8') as log:
                done=_run_contained([sys.executable,'-X','faulthandler','-m',__name__,str(xml)],log,30)
            boundary=dict(returncode=done.returncode,termination_confirmed=True)
        except subprocess.TimeoutExpired as exc:
            boundary=dict(returncode=None,termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
        except Exception as exc:
            boundary=dict(returncode=None,termination_confirmed=False,error=str(exc))
        boundary['elapsed_s']=time.perf_counter()-started
    atomic_json(folder/'boundary.json',boundary)
    loaded=boundary.get('returncode')==0 and boundary['termination_confirmed']
    determined=boundary['termination_confirmed'] and boundary.get('returncode') is not None
    analyses=[host.store.artifact(r) for r in s.get('analysis_results',[]) if host.store.artifact(r).get('candidate')==candidate_ref]
    executions=[host.store.artifact(r) for r in s['results'] if host.store.artifact(r).get('candidate')==candidate_ref]
    value=dict(version='runtime_capability_v1',binding=binding,xml_sha256=xml_hash,
        status='runtime_available' if loaded else 'runtime_unavailable' if determined else 'runtime_unresolved',
        levels=dict(design_valid=True,physics_compiled=True,numerical_model_available=True if any(a.get('model') for a in analyses) else None,
            runtime_backend_loadable=loaded if determined else None,
            control_preparation_available=True,controller_update_verified=True if any((r.get('profile') or {}).get('applied_control_updates',0)>0 for r in executions) else None,
            complete_task_evaluated=any(r['status']=='evaluated' for r in executions)),
        failed_boundary=None if loaded else 'native_mujoco_xml_load',boundary=boundary,
        native_status_hex=f"0x{boundary['returncode'] & 0xffffffff:08X}" if boundary.get('returncode') is not None else None,
        alternative_runtime_verified=known.get('alternative_loader_check'),
        task_success=None,physical_infeasibility_proven=False,
        worker_log=(folder/'worker.log').read_text(encoding='utf8',errors='replace') if (folder/'worker.log').exists() else None)
    if previous:
        value['recorded_failure_context']=save(host,known,'recorded_runtime_failure_context')
    ref=save(host,value,'runtime_capability')
    current=state(host)
    update(host,runtime_capabilities={**current.get('runtime_capabilities',{}),identity:ref},
        numerical_s=current['numerical_s']+time.perf_counter()-started)
    return dict(reference=ref,**value,reused=bool(previous))


if __name__=='__main__':
    from tools.service_execution import contain_worker_children
    job=contain_worker_children()
    import mujoco
    model=mujoco.MjModel.from_xml_path(sys.argv[1])
    print(dict(nv=model.nv,nu=model.nu),flush=True)
