"""Prepare and run the bounded DeepSeek reach_free study with two GVS-LQR execution modes."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from tools.state_io import atomic_json, read


TOOLS={
    'route.advance':'1.0.0','route.inspect':'1.0.0','simulation.run':'1.0.0',
    'evaluation.run':'1.0.0','evidence.read':'1.0.0','session.control':'1.0.0',
    'diagnostics.saved_trajectory':'2.0.0','visualization.render_simulation_video':'2.0.0',
    'kinematics.pcc_describe':'1.0.0','kinematics.pcc_forward':'2.0.0',
    'dynamics.gvs_describe':'1.0.0','dynamics.gvs_evaluate':'2.0.0',
    'dynamics.gvs_build_system':'2.0.0','statics.gvs_equilibrium':'1.0.0',
    'linearization.linearize':'2.0.0','control.lqr_describe':'2.0.0',
    'control.lqr_synthesize':'1.0.0','optimization.describe':'1.0.0',
    'optimization.assemble':'1.0.0','optimization.solve':'1.0.0'}


def controller(point,mode):
    return {'extension_id':'controller.gvs_lqr','version':'1.0.0','parameters':{
        'contract':'family.gvs_lqr_control','version':'1.0.0','data':{
            'equilibrium_q':point['q0'],'equilibrium_tensions_n':point['u0'],
            'curvature_weight':1.,'state_rate_weight':.1,'tendon_tension_weight':100.,
            'operating_point_source':'gvs_inverse_tip_static','tension_execution_mode':mode}}}


def prepare(root,base_input,comparison_path):
    from examples.platform_fixtures import project
    from tools.platform_config import load
    from tools.platform_store import Store

    root=Path(root).resolve();inputs=root/'inputs';inputs.mkdir(parents=True,exist_ok=False)
    value=read(base_input);comparison=read(comparison_path);point=comparison['operating_point']
    value['run_id']='reach-free-gvs-lqr-route'
    value['policy']['candidate_builder']['parameters']['data']['control_parameters']={}
    deepseek=load('configs/deepseek.yaml')
    value['policy']['model']=dict(adapter='deepseek',model=deepseek['model'],base_url=deepseek['base_url'],
        thinking=deepseek['thinking'],max_tokens=deepseek['max_tokens'],timeout_s=deepseek['timeout_s'],
        context_bytes=deepseek['max_input_bytes'],max_turns=32)
    value['policy']['budget'].update(model_calls=32,tool_calls=120,backend_solves=8,wall_s=3600.)
    value['policy']['allowed_tools']=[];value['policy']['tool_bindings']=TOOLS
    dynamics=deepcopy(value['policy']['dynamics_model']);mujoco=deepcopy(value['policy']['backend'])
    old_combinations=value['policy']['route']['data']['combinations']
    combinations={
        'gvs_lqr_ideal_tension':dict(dynamics_model=dynamics,backend=mujoco,controller=controller(point,'ideal_tension')),
        'gvs_lqr_actuator_realistic':dict(dynamics_model=dynamics,backend=mujoco,controller=controller(point,'actuator_realistic'))}
    for name in ('family_mujoco','matlab_spatial'):
        if name in old_combinations: combinations['tip_feedback_'+name]=old_combinations[name]
    project_value=project();project_value['budget'].update(model_calls=32,tool_calls=120,backend_solves=8,wall_s=3600.)
    store=Store(root);store.create(project_value)
    with store.transaction() as db: comparison_ref=store.put(db,comparison)
    value['policy']['route']={'contract':'family.route_policy','version':'1.0.0','data':{
        'source':'Frozen reach_free input plus the completed controlled GVS-LQR execution-mode comparison.',
        'combinations':combinations,'max_trials':4,
        'guidance':('Select legal combinations and use scientific evidence autonomously. The controlled comparison is available as '
            f'EvidenceRef {comparison_ref.model_dump(mode="json")}. It found exact ideal force tracking but does not mandate a mode or sequence. '
            'Stop immediately after a valid frozen-evaluator task success; otherwise deliver the best valid evaluated candidate.')}}
    atomic_json(inputs/'route.json',value);atomic_json(inputs/'project.json',project_value)
    atomic_json(inputs/'comparison_ref.json',comparison_ref.model_dump(mode='json'))
    atomic_json(inputs/'operating_point.json',point)
    return dict(input=str(inputs/'route.json'),project=str(inputs/'project.json'),comparison_ref=comparison_ref.model_dump(mode='json'),
        model=value['policy']['model'],budget=value['policy']['budget'],combinations=list(combinations))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','start','resume','status','result'])
    parser.add_argument('root');parser.add_argument('--base-input');parser.add_argument('--comparison')
    args=parser.parse_args(argv);root=Path(args.root).resolve()
    if args.action=='prepare':
        if not args.base_input or not args.comparison: raise ValueError('--base-input and --comparison are required')
        out=prepare(root,args.base_input,args.comparison)
    else:
        from extensions.tendon_family.route import create, view
        from tools.platform_host import Host
        host=Host(root,'reach-free-gvs-lqr-route')
        if args.action=='start':
            if not os.environ.get('DEEPSEEK_API_KEY'): raise ValueError('MODEL_KEY_MISSING: DEEPSEEK_API_KEY is required')
            create(root,read(root/'inputs/route.json'));host.run();out=view(host)
        elif args.action=='resume':
            if not os.environ.get('DEEPSEEK_API_KEY'): raise ValueError('MODEL_KEY_MISSING: DEEPSEEK_API_KEY is required')
            host.run();out=view(host)
        else:
            out=view(host)
            if args.action=='result': out=dict(final=out['route']['final'],usage=out['usage'],counts=out['counts'],stop_reason=out['stop_reason'])
        if args.action in ('start','resume'): atomic_json(root/'route_status.json',out)
    print(json.dumps(out,ensure_ascii=False,indent=2));return 0


if __name__=='__main__': raise SystemExit(main())
