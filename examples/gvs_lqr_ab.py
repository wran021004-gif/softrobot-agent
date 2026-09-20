"""Controlled reach_free comparison of ideal and actuator-realistic GVS-LQR execution."""
import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import numpy as np

from examples.gvs_lqr_reach import operating_point


def signal_final(result,name,entity='tip'):
    signal=next(s for s in result['signals'] if s['spec']['name']==name and s['spec']['entity']==entity)
    return signal['values'][-1]


def run(root,base_input=None):
    from examples.platform_fixtures import project
    from examples.platform_tendon_family import example_design, design_space, session
    from tools.platform_host import Host
    from tools.platform_store import Store
    from tools.state_io import atomic_json, read

    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
    if base_input:
        baseline=json.loads(Path(base_input).read_text(encoding='utf-8'))
        baseline['policy']['route']=None
        # The frozen route's feedback-gain authorization belongs to controller.family
        # and is inapplicable to controller.gvs_lqr; physical/discretization bounds stay unchanged.
        baseline['policy']['candidate_builder']['parameters']['data']['control_parameters']={}
    else:
        baseline=session('family_mujoco',example_design(),design_space(example_design()))
    point=operating_point(baseline)
    project_value=project();project_value['budget'].update(model_calls=0,tool_calls=12,backend_solves=2,wall_s=3600.)
    store=Store(root);store.create(project_value);runs={}
    for mode in ('ideal_tension','actuator_realistic'):
        value=deepcopy(baseline);value['run_id']='gvs-lqr-ab-'+mode.replace('_','-')
        value['policy']['budget'].update(model_calls=0,tool_calls=6,backend_solves=1,wall_s=1800.)
        value['policy']['controller']={'extension_id':'controller.gvs_lqr','version':'1.0.0','parameters':{
            'contract':'family.gvs_lqr_control','version':'1.0.0','data':{
                'equilibrium_q':point['q0'],'equilibrium_tensions_n':point['u0'],
                'curvature_weight':1.,'state_rate_weight':.1,'tendon_tension_weight':100.,
                'operating_point_source':'gvs_inverse_tip_static','tension_execution_mode':mode}}}
        value['policy']['tool_bindings'].update({'simulation.run':'1.0.0','evaluation.run':'1.0.0'})
        host=Host(root,value['run_id']);host.create(value)
        simulation=host.invoke({'request_id':'ab-simulation','tool_id':'simulation.run','tool_version':'1.0.0',
            'reason':'Controlled GVS-LQR execution-mode comparison on the frozen reach_free task.',
            'arguments':{'candidate_id':'gvs_lqr_ab','changes':{}},'cache':'reuse'})
        if simulation['execution_status']!='completed': raise ValueError('SIMULATION_FAILED: '+str(simulation))
        evaluation=host.invoke({'request_id':'ab-evaluation','tool_id':'evaluation.run','tool_version':'1.0.0',
            'reason':'Apply the unchanged reach evaluator to this controlled MuJoCo rollout.',
            'arguments':{'result':simulation['output'],'execution_id':simulation['execution_id']}})
        if evaluation['execution_status']!='completed': raise ValueError('EVALUATION_FAILED: '+str(evaluation))
        result=store.artifact(simulation['output']);outcome=store.artifact(evaluation['output'])
        backend=root/'sessions'/value['run_id']/'executions'/simulation['execution_id']/'backend'
        with gzip.open(backend/'trajectory.json.gz','rt',encoding='utf-8') as stream: rows=json.load(stream)
        control_spec=read(backend/'control_spec.json')
        final_tip=signal_final(result,'tip_position')
        error=next(m['value'] for m in outcome['metrics'] if m['name']=='position_error')
        tracking=np.asarray([r['tension_tracking_error_n'] for r in rows])
        lengths=np.asarray([r['tendon_length_change_m'] for r in rows])
        summary=dict(run_id=value['run_id'],candidate_id=outcome['candidate_id'],execution_mode=mode,
            execution_id=simulation['execution_id'],result=simulation['output'],evaluation=evaluation['output'],
            lqr_gain_identity=control_spec['algorithm']['gain_identity'],
            solver_status=simulation['solver_status'],task_success=outcome['task_success'],final_tip_m=final_tip,
            position_error_m=error,max_abs_tension_tracking_error_n=float(np.max(np.abs(tracking))),
            max_projection_residual_rad_m=max(r['gvs_projection_residual_max_rad_m'] for r in rows),
            max_abs_tendon_length_change_m=float(np.max(np.abs(lengths))),
            lqr_clipping_steps=sum(any(r['lqr_tension_saturated']) for r in rows),
            force_clipping_steps=sum(any(r['force_limit_saturated']) for r in rows),
            actuator_saturation_steps=(sum(any(r['actuator_saturated']) for r in rows) if mode=='actuator_realistic' else None),
            nonfinite_states=not all(np.isfinite(r['qpos_rad']).all() and np.isfinite(r['qvel_rad_s']).all() for r in rows),
            control_spec=str(backend/'control_spec.json'),trajectory=str(backend/'trajectory.json.gz'))
        runs[mode]=summary
    ideal=runs['ideal_tension'];realistic=runs['actuator_realistic']
    if ideal['lqr_gain_identity']!=realistic['lqr_gain_identity']:
        raise ValueError('AB_LQR_GAIN_MISMATCH')
    conclusion=('actuator_realization_major' if ideal['position_error_m'] < .5*realistic['position_error_m']
        else 'model_manifold_or_local_controller_dominant')
    comparison=dict(protocol='same robot, GVS equilibrium, LQR gain, initial backend state and horizon; only tension execution mode differs',
        operating_point=point,runs=runs,error_ratio_ideal_over_realistic=ideal['position_error_m']/realistic['position_error_m'],
        classification=conclusion,project_usage=store.remaining())
    atomic_json(root/'comparison.json',comparison)
    print(json.dumps(comparison,indent=2));return comparison


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root')
    parser.add_argument('--base-input',help='Frozen SessionInput JSON whose task, robot, environment and timing are preserved.')
    args=parser.parse_args(argv);run(args.root,args.base_input);return 0


if __name__=='__main__': raise SystemExit(main())
