"""CLI actions over the public optimization and saved-data interfaces."""
from pathlib import Path
from tools.state_io import read,atomic_json
from tools.platform_store import Store,plain
from tools.platform_host import Host


def prepare(root):
    from examples.platform_tendon_family import prepare as prepare_family
    from extensions.tendon_family.preparation import prepare_candidate
    prepare_family(root)
    root=Path(root)
    inp=prepare_candidate(root,'continuous','family_mujoco')['input']
    inp['run_id']='family-optimization'
    inp['policy']['budget'].update(tool_calls=16,backend_solves=3,wall_s=2400.)
    inp['policy']['tool_bindings'].update({'diagnostics.saved_trajectory':'2.0.0','visualization.render_simulation_video':'2.0.0'})
    space=inp['policy']['candidate_builder']['parameters']['data']
    space['control_parameters']={'control/feedback_gain':dict(type='number',bounds=[2.,8.])}
    value=dict(session=inp,template='tube_distal',variables={'components/near/length_m':[.14,.20]},max_trials=3,step=.2)
    atomic_json(root/'inputs/optimization.json',value)
    return dict(request=str(root/'inputs/optimization.json'),regular_solve_budget=4)


def invoke(host,name,tool,arguments):
    inp=host.store.session(host.run_id)['snapshot']['input']
    receipt=host.invoke(dict(request_id=name,tool_id=tool,tool_version=inp['policy']['tool_bindings'][tool],
        arguments=arguments,cache='reuse',reason='Authorized bounded optimization and saved evidence verification'))
    if receipt['execution_status']!='completed': raise ValueError(str(receipt))
    return receipt


def command(root,action,request=None,t_start_s=None,t_end_s=None,fps=25,azimuth_deg=135.,elevation_deg=-20.):
    root=Path(root).resolve()
    if action=='prepare-opt':return prepare(root)
    request=Path(request) if request else root/'inputs/optimization.json'
    value=read(request)
    if action=='build-opt':
        from extensions.tendon_family.optimization import prepare_optimization
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.execution import resolve_execution
        from extensions.tendon_family.mjcf import compile_xml
        from tools.platform_registry import registry
        _,inp=prepare_optimization(value); reg=registry(); physics=physics_for(inp); scene=assemble(inp,physics)
        atomic_json(root/'optimization_baseline.json',plain(inp))
        if inp.policy.backend.extension_id=='backend.family_mujoco':
            compile_xml(physics,scene,reg.bind(inp.policy.backend,'backend')[1],root/'optimization_baseline.xml')
            import mujoco
            mujoco.MjModel.from_xml_path(str(root/'optimization_baseline.xml'))
        return dict(status='built',execution=resolve_execution(inp,reg),backend_solves=0)
    store=Store(root)
    if action=='optimize':
        from extensions.tendon_family.optimization import optimize
        if not store.db.exists():store.create(read(root/'inputs/project.json'))
        return optimize(root,value)
    outcome=read(root/(value['session']['run_id']+'_optimization.json')); best=outcome['best']
    if best is None:return dict(status='no_valid_candidate',stop_reason=outcome['stop_reason'])
    host=Host(root,outcome['run_id']); simulation=best['simulation']
    if action=='best':return dict(best=best,configuration=store.artifact(best['configuration']))
    if action in ('diagnose','video'):
        tool='diagnostics.saved_trajectory' if action=='diagnose' else 'visualization.render_simulation_video'
        args=dict(result=simulation['output'],execution_id=simulation['execution_id'],t_start_s=t_start_s,t_end_s=t_end_s)
        if action=='video':args.update(fps=fps,azimuth_deg=azimuth_deg,elevation_deg=elevation_deg)
        from tools.state_io import digest
        receipt=invoke(host,action+'-'+digest(args)[:12],tool,args)
        product=store.artifact(receipt['output']); report=store.artifact(product['report'])
        files={}
        for name,ref in product['files'].items():
            if name.endswith(('.mp4','.png')):
                destination=root/'products'/name; destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(store.artifact(ref,raw=True)); files[name]=str(destination)
        output=dict(receipt=receipt,product=product,report=report,files=files)
        atomic_json(root/(action+'.json'),output); return output
    if action=='crosscheck':
        from extensions.tendon_family.crosscheck import crosscheck
        original=store.artifact(best['configuration'])['effective']['policy']['backend']['extension_id']
        backend='matlab_spatial' if original=='backend.family_mujoco' else 'family_mujoco'
        output=crosscheck(root,outcome['run_id'],best['candidate_id'],best['configuration'],
            read(root/'inputs/execution.json')['backends'][backend])
        output['reference_evaluation']=best['evaluation_data']
        atomic_json(root/'crosscheck.json',output);return output
    raise ValueError('UNKNOWN_OPTIMIZATION_ACTION: '+action)
