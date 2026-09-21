"""Bounded reach_free study: trusted GVS inverse equilibrium -> executable GVS-LQR -> MuJoCo."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import numpy as np


def operating_point(value):
    """Use the existing GVS inverse/IPOPT path on the nominal (force-window-free) equilibrium."""
    from extensions.optimization.ipopt import IpoptSolver
    from extensions.tendon_family.contracts import GVSInverseAssemblerParameters, GVSEquilibriumRequest
    from extensions.tendon_family.gvs_casadi import gvs_equilibrium_tool
    from extensions.tendon_family.gvs import coordinate_order, forward_kinematics
    from extensions.tendon_family.pcc import quaternion_wxyz_to_rotation
    from extensions.tendon_family.scientific_optimization import gvs_authorization
    from schemas.platform import Binding, Payload, SessionInput
    from schemas.platform_math import ConstraintSelection, ObjectiveSelection, OptimizationSpecification, SystemContext
    from tools.platform_optimization import assemble_optimization
    from tools.platform_registry import registry

    nominal=deepcopy(value);nominal['task']['environment']['data']['external_forces']=[]
    inp=SessionInput.model_validate(nominal);design=inp.robot.structure.data;reg=registry()
    coordinates=coordinate_order(design);tendons=[t['id'] for t in design['tendons']]
    q_paths=['q/'+name for name in coordinates];tension_paths=['tendon_tensions_n/'+name for name in tendons]
    binding=Binding(extension_id='optimization_assembler.gvs_inverse',parameters=Payload(
        contract='family.gvs_inverse_assembler_parameters',data=GVSInverseAssemblerParameters(template='inverse_tip_static').model_dump(mode='json')))
    parameters=reg.bind(binding,'optimization_assembler')[1]
    space=gvs_authorization(inp.robot,reg.parse(inp.policy.candidate_builder.parameters).model_dump(mode='json'),parameters)
    initial={name:0. for name in q_paths};initial.update(dict(zip(tension_paths,[1.2,.4,.8,.7,1.1,.3])))
    problem=assemble_optimization(reg,binding,task=inp.task,robot=inp.robot,space=space,
        mathematical_model=reg.mathematical_model(Binding(extension_id='model.gvs',parameters=Payload(contract='family.gvs_model',data={}))),
        specification=OptimizationSpecification(variables=q_paths+tension_paths,
            objectives=[ObjectiveSelection(template_id='tip_position_error_squared')],
            constraints=[ConstraintSelection(template_id='static_equilibrium'),ConstraintSelection(template_id='tendon_force_bounds')],
            initial_guess=initial),context=SystemContext(x0=[],u0=[],scene=inp.task.environment))
    solved=IpoptSolver({'max_iterations':500,'tolerance':1e-9}).solve(problem)
    if solved.status!='converged' or solved.constraint_violation>1e-7:
        raise ValueError('GVS_INVERSE_OPERATING_POINT_FAILED: '+json.dumps(solved.model_dump(mode='json')))
    q0=[solved.optimum[name] for name in q_paths];u0=[solved.optimum[name] for name in tension_paths]
    from types import SimpleNamespace
    refined=gvs_equilibrium_tool(SimpleNamespace(input=inp,reg=reg),GVSEquilibriumRequest(
        tendon_tensions_n=dict(zip(tendons,u0)),initial_q=q0,tolerance=1e-16,max_iterations=20))
    if not refined.converged: raise ValueError('GVS_EQUILIBRIUM_REFINEMENT_FAILED')
    q0=refined.q_equilibrium
    local=forward_kinematics(design,q0,samples_per_segment=2)['tip_position_m']
    assembly=inp.task.environment.data;rotation=quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])
    world=(rotation@local+np.asarray(assembly['mount']['position_m'])).tolist()
    return dict(q0=q0,u0=u0,coordinate_order=coordinates,tendon_order=tendons,
        objective_value=solved.objective_value,constraint_violation=solved.constraint_violation,
        refined_equilibrium_residual_norm=refined.residual_norm,refinement_iterations=refined.iterations,
        iterations=solved.iterations,predicted_tip_world_m=world,
        nominalization='Force-free nominal equilibrium; final task and MuJoCo retain the task-defined forces unchanged.')


def run(root,tendon_weight=1.):
    from examples.platform_fixtures import project
    from examples.platform_tendon_family import example_design, design_space, session
    from schemas.platform import EvaluationResult
    from tools.platform_host import Host
    from tools.platform_store import Store
    from tools.state_io import atomic_json, read

    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
    design=example_design();value=session('family_mujoco',design,design_space(design))
    value['run_id']='gvs-lqr-reach'
    value['policy']['budget'].update(model_calls=0,tool_calls=100,backend_solves=6,wall_s=3600.)
    value['policy']['controller']={'extension_id':'controller.gvs_lqr','version':'1.0.0','parameters':{
        'contract':'family.gvs_lqr_control','version':'1.0.0','data':{
            'curvature_weight':1.,'state_rate_weight':.1,'tendon_tension_weight':tendon_weight,
            'operating_point_source':'gvs_inverse_tip_static'}}}
    value['policy']['tool_bindings'].update({'simulation.run':'1.0.0','evaluation.run':'1.0.0'})
    project_value=project();project_value['budget'].update(model_calls=0,tool_calls=100,backend_solves=6,wall_s=3600.)
    Store(root).create(project_value)
    host=Host(root,value['run_id']);host.create(value)
    simulation=host.invoke({'request_id':'gvs-lqr-simulation','tool_id':'simulation.run','tool_version':'1.0.0',
        'reason':'Validate the trusted GVS inverse equilibrium and executable GVS-LQR composition on frozen reach_free MuJoCo.',
        'arguments':{'candidate_id':'gvs_lqr_baseline','changes':{}},'cache':'reuse'})
    if simulation['execution_status']!='completed': raise ValueError('SIMULATION_FAILED: '+str(simulation))
    evaluation=host.invoke({'request_id':'gvs-lqr-evaluation','tool_id':'evaluation.run','tool_version':'1.0.0',
        'reason':'Evaluate the actual MuJoCo result against the unchanged frozen reach_free criterion.',
        'arguments':{'result':simulation['output'],'execution_id':simulation['execution_id']}})
    if evaluation['execution_status']!='completed': raise ValueError('EVALUATION_FAILED: '+str(evaluation))
    outcome=EvaluationResult.model_validate(host.store.artifact(evaluation['output']))
    control_spec=read(root/'sessions'/value['run_id']/'executions'/simulation['execution_id']/'backend'/'control_spec.json')
    result=dict(operating_point=control_spec['reference']['derivation'],controller=value['policy']['controller'],simulation=simulation,evaluation=evaluation,
        outcome=outcome.model_dump(mode='json'),usage=host.store.remaining(value['run_id']))
    atomic_json(root/'study.json',result);atomic_json(root/'input.json',value)
    print(json.dumps(result,indent=2));return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root')
    parser.add_argument('--tendon-weight',type=float,default=1.)
    args=parser.parse_args(argv);return 0 if run(args.root,args.tendon_weight) else 1


if __name__=='__main__': raise SystemExit(main())
