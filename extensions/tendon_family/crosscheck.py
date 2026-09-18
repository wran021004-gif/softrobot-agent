"""Independent review through the same normalized, immutable session boundary."""
from copy import deepcopy
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.state_io import digest
from .optimization import ensure_session


def invoke(host, name, tool, arguments, *, parent=None):
    bindings=host.store.session(host.run_id)['snapshot']['input']['policy']['tool_bindings']
    receipt=host.invoke(dict(request_id=name,tool_id=tool,tool_version=bindings[tool],
        arguments=arguments,cache='reuse',reason='Public route execution using frozen inputs'),parent=parent)
    if receipt['execution_status']=='unknown': raise TimeoutError('UNCONFIRMED: '+str(receipt))
    if receipt['execution_status']!='completed': raise ValueError(str(receipt))
    return receipt


def crosscheck(root, source_run, candidate, configuration, backend, *, parent_run_id=None, parent_event_id=None, actor='local-human'):
    store=Store(root)
    inp=deepcopy(store.artifact(configuration)['effective'])
    if inp['policy']['backend']['extension_id']==backend['extension_id']:
        raise ValueError('INDEPENDENT_BACKEND_REQUIRED')
    inp['policy'].update(backend=backend,search=None,route=None)
    inp['policy']['budget'].update(backend_solves=1,tool_calls=6,wall_s=1000.)
    # Include actual input and provenance, not a candidate label or just backend name.
    inp['run_id']=source_run+'-crosscheck'
    from tools.platform_tasks import compile_input
    normalized=compile_input(inp)['input']
    identity=digest(dict(input=normalized,source=configuration,candidate=candidate,parent=parent_run_id))
    inp['run_id']=source_run[:60]+'-cc-'+identity[:20]
    host=Host(root,inp['run_id'],actor=actor)
    ensure_session(host,inp,parent_run_id=parent_run_id,parent_event_id=parent_event_id)
    with store.transaction() as db:
        state=store.session(host.run_id,db)['state']
        if 'crosscheck_source' not in state:
            state['crosscheck_source']=dict(source_run=source_run,candidate_id=candidate,configuration=configuration,identity=identity)
            store.update_state(db,host.run_id,state)
            ref=store.put(db,state['crosscheck_source'])
            store.event(db,host.run_id,'crosscheck','prepared',parent=parent_event_id,inputs=[configuration],outputs=[ref],candidate=candidate)
    sim=invoke(host,'crosscheck-simulation','simulation.run',dict(candidate_id=candidate,changes={}))
    ev=invoke(host,'crosscheck-evaluation','evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']))
    metadata=store.session(host.run_id)['state']['result_executions'][sim['execution_id']]
    return dict(run_id=host.run_id,source_run=source_run,candidate_id=candidate,source_configuration=configuration,
        configuration=metadata['candidate_input'],backend=backend,simulation=sim,evaluation_ref=ev['output'],
        evaluation=store.artifact(ev['output']),usage=store.remaining(host.run_id)['used'],
        meaning='Independent backend review; excluded from optimization ranking')
