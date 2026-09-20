"""Prepare, start, inspect and resume a frozen route through the platform Host."""
import argparse
import json
from pathlib import Path
from tools.state_io import read,atomic_json


def prepare(root,offline=False):
    from examples.platform_family_optimization import prepare as prepare_opt
    from tools.platform_config import load
    prepare_opt(root); root=Path(root)
    value=read(root/'inputs/optimization.json')['session']; value['run_id']='family-route'
    execution=read(root/'inputs/execution.json')
    config=load('configs/deepseek.yaml')
    value['policy']['model']=dict(adapter='offline' if offline else 'deepseek',model=config['model'],
        base_url=config['base_url'],thinking=config['thinking'],max_tokens=config['max_tokens'],
        timeout_s=config['timeout_s'],context_bytes=config['max_input_bytes'],max_turns=16)
    value['policy']['budget'].update(model_calls=16,backend_solves=4,tool_calls=60,wall_s=3600.)
    value['policy']['allowed_tools']=[]
    value['policy']['tool_bindings']={
        'route.advance':'1.0.0','route.inspect':'1.0.0','simulation.run':'1.0.0',
        'evaluation.run':'1.0.0','evidence.read':'1.0.0','session.control':'1.0.0',
        'diagnostics.saved_trajectory':'2.0.0','visualization.render_simulation_video':'2.0.0',
        'kinematics.pcc_describe':'1.0.0','kinematics.pcc_forward':'2.0.0',
        'dynamics.gvs_describe':'1.0.0','dynamics.gvs_evaluate':'2.0.0',
        'dynamics.gvs_build_system':'2.0.0','statics.gvs_equilibrium':'1.0.0',
        'linearization.linearize':'2.0.0','control.lqr_describe':'2.0.0',
        'control.lqr_synthesize':'1.0.0','optimization.describe':'1.0.0',
        'optimization.assemble':'1.0.0','optimization.solve':'1.0.0'}
    value['policy']['route']=dict(contract='family.route_policy',version='1.0.0',data=dict(
        source='User editable route.json assembled from inputs/experiment, design, space, execution, control; route.json becomes authority at start.',
        combinations={name:dict(dynamics_model=execution['dynamics_model'],backend=backend,controller=value['policy']['controller'])
            for name,backend in execution['backends'].items()},max_trials=3))
    atomic_json(root/'inputs/route.json',value)
    project=read(root/'inputs/project.json');project['budget'].update(model_calls=16,tool_calls=60,backend_solves=4,wall_s=3600.)
    atomic_json(root/'inputs/project.json',project)
    return dict(input=str(root/'inputs/route.json'),project=str(root/'inputs/project.json'),
        adapter=value['policy']['model']['adapter'],note='Edit route.json before start. Frozen inputs cannot be changed on resume.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','start','status','resume','result','call','diagnose','video'])
    parser.add_argument('root');parser.add_argument('--run-id',default='family-route')
    parser.add_argument('--input');parser.add_argument('--request');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--decisions',help='Explicit offline protocol fixture, not real LLM decisions')
    args=parser.parse_args(argv);root=Path(args.root).resolve()
    from tools.platform_store import Store
    from tools.platform_host import Host
    from extensions.tendon_family.route import create,view
    if args.action=='prepare':out=prepare(root,args.offline)
    else:
        host=Host(root,args.run_id)
        adapter=None
        if args.decisions:
            from tools.platform_models import OfflineAdapter
            adapter=OfflineAdapter(read(args.decisions)['decisions'])
        if args.action=='start':
            value=read(Path(args.input) if args.input else root/'inputs/route.json')
            if value['run_id']!=args.run_id: raise ValueError('RUN_ID_MISMATCH')
            import os
            if value['policy']['model']['adapter']=='deepseek' and not os.environ.get('DEEPSEEK_API_KEY'):
                raise ValueError('MODEL_KEY_MISSING: configure existing service environment, then start again')
            if not host.store.db.exists(): host.store.create(read(root/'inputs/project.json'))
            create(root,value);host.run(adapter);out=view(host)
        elif args.action=='resume':host.run(adapter);out=view(host)
        elif args.action in ('diagnose','video'):
            from extensions.tendon_family.crosscheck import invoke
            final=view(host)['route']['final']
            if not final or not final.get('candidate_id'): raise ValueError('FINAL_CANDIDATE_REQUIRED')
            child=Host(root,final['run_id'])
            sim=final.get('simulation')
            if sim is None:  # Compatibility with historical optimization deliveries.
                sim=next(t for t in child.store.session(child.run_id)['state']['search']['trials'] if t['candidate_id']==final['candidate_id'])['simulation']
            tool='diagnostics.saved_trajectory' if args.action=='diagnose' else 'visualization.render_simulation_video'
            receipt=invoke(child,'saved-'+args.action+'-'+final['candidate_id'],tool,dict(result=sim['output'],execution_id=sim['execution_id']))
            product=host.store.artifact(receipt['output'])
            files={}
            for name,ref in product['files'].items():
                if name.endswith(('.mp4','.png')):
                    destination=root/'products'/name;destination.parent.mkdir(parents=True,exist_ok=True)
                    destination.write_bytes(host.store.artifact(ref,raw=True));files[name]=str(destination)
            out=dict(receipt=receipt,product=product,report=host.store.artifact(product['report']),files=files)
            atomic_json(root/(args.action+'.json'),out)
        elif args.action=='call':
            if not args.request: raise ValueError('--request required')
            out=host.invoke(read(args.request))
        else:
            out=view(host)
            if args.action=='result':out=dict(final=out['route']['final'],usage=out['usage'],counts=out['counts'],stop_reason=out['stop_reason'])
        atomic_json(root/'route_status.json',view(host)) if args.action in ('start','resume','call') else None
    print(json.dumps(out,ensure_ascii=False,indent=2))
    # Robot tolerance (final.task_success) is separate from protocol/execution failure.
    if args.action in ('start','resume') and out['status'] in ('failed','needs_input'):
        return 1
    if args.action in ('start','resume') and (out['route'].get('final') or {}).get('delivery_status')=='incomplete':
        return 2
    if args.action=='call' and out['execution_status']!='completed': return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
