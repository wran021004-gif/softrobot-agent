"""One deterministic full public execution; not a design search or provider run."""
import os
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
from examples.gvs_design_input import multiphysics_input
from examples.gvs_nmpc_route_experiment import prepare
from extensions.tendon_family.crosscheck import invoke
from tools.state_io import atomic_json,read
from tools.platform_store import plain
from extensions.tendon_family.gvs_basis import resolve_basis

folder=Path(__file__).resolve().parent
value=multiphysics_input('stage329-plumbing')
value['policy']['budget'].update(model_calls=1,backend_solves=1,wall_s=3600.)
atomic_json(folder/'plumbing_input.json',value)
atomic_json(folder/'frozen_input.json',multiphysics_input())
host=prepare(folder/'plumbing_execution',ROOT,folder/'plumbing_input.json')
start=time.perf_counter()
def action(name,**kwargs):
    result=invoke(host,name,'route.advance',dict(node_id=name,reason='Deterministic plumbing verification only',
        next_step='Verify candidate attribution and completed pipeline',**kwargs))
    atomic_json(folder/(name+'_receipt.json'),result)
    detail=host.store.artifact(result['output'])['detail']
    print(name,detail,flush=True)
    return detail
b=action('plumbing_build',action='build',combination='candidate_gvs_nmpc',candidate_id='plumbing_representative',
    changes={'components/near/length_m':.162,'design/section_scale':1.02,'design/material_scenario':'compliant'})
node=host.store.session(host.run_id)['state']['route']['nodes'][-1]
built=host.store.artifact(node['result']); effective=host.store.artifact(built['configuration'])
n=len(resolve_basis(effective['robot']['structure']['data'],effective['policy']['controller']['parameters']['data']['recipe']['basis']).coordinate_order)
analysis=invoke(host,'plumbing_analysis','analysis.gvs_candidate_evaluate',dict(source_node='plumbing_build',
    state=dict(q=[0.]*n,qdot=[0.]*n),input=dict(tendon_tensions_n={t['id']:0. for t in effective['robot']['structure']['data']['tendons']})))
atomic_json(folder/'plumbing_analysis.json',host.store.artifact(analysis['output']))
action('plumbing_run',action='run',source_node='plumbing_build',evidence=[node['result']])
node=host.store.session(host.run_id)['state']['route']['nodes'][-1]
trial=host.store.artifact(node['result'])
atomic_json(folder/'plumbing_trial.json',trial)
action('plumbing_diagnose',action='diagnose',source_node='plumbing_run',evidence=[node['result']])
comparison=invoke(host,'plumbing_compare','analysis.compare_candidates',{})
atomic_json(folder/'plumbing_comparison.json',host.store.artifact(comparison['output']))
from extensions.tendon_family.candidate import candidate_facts
from extensions.tendon_family.compiler import resolve
from schemas.platform import SessionInput
candidate=host.store.artifact(trial['configuration'])['effective']
physics=resolve(candidate['robot']['structure']['data'],candidate['policy']['discretization']['data'])
report=trial['profile_report_summary']
backend=next((folder/'plumbing_execution'/'sessions'/trial['run_id']/'executions').glob('*/backend'))
saved_physics=read(backend/'resolved_physics.json')
control=read(backend/'control_spec.json')
checks=dict(complete_valid=report['valid_complete_execution'],multi_category=trial['candidate_facts']['multi_category_coverage'],
    same_physics=physics['identity']==saved_physics['identity']==report['numerical_preparation']['physics_identity'],
    same_prediction_robot=control['robot']==candidate['robot'],
    same_analysis_robot=read(folder/'plumbing_analysis.json')['binding']['robot_identity']==report['execution_scope']['robot']['identity'],
    same_execution=report['execution_id']==trial['simulation']['execution_id'],
    same_candidate=report['candidate_id']==trial['candidate_id'],
    aligned_predictions=report['one_step_prediction_summary']['aligned_count']==report['updates'])
atomic_json(folder/'plumbing_confirmation.json',dict(checks=checks,confirmed=all(checks.values()),
    task_success=trial['task_success'],terminal_error_m=report['terminal_error_m'],
    measured_wall_s=time.perf_counter()-start,usage=host.store.remaining()['used'],
    evidence=dict(trial='plumbing_trial.json',analysis='plumbing_analysis.json',comparison='plumbing_comparison.json')))
print('CONFIRMATION',checks,flush=True)
assert all(checks.values()), checks
