"""Reusable service binding execution and immutable identity/cache policy."""
import subprocess
import sys
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
            completed=subprocess.run([sys.executable,'-m','tools.service_worker',str(request)],cwd=ROOT,
                stdout=log,stderr=subprocess.STDOUT,timeout=definition.timeout_s,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError('TIMEOUT: isolated worker terminated; reservation retained') from exc
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
