"""P2-A: one bounded real V3 native T1, never auto-runs or retries."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
from pathlib import Path
import json
from tools.research import core, analysis
from tools.research.config import ROOT
from tools.research.state import state
from tools.state_io import atomic_json
from tests.research.test_cross_task_integration import plan


def main():
    folder=ROOT/'runs/p2-v3-positive-high-engineering-20261028'
    folder.mkdir(parents=True,exist_ok=True)
    host=core.prepare(ROOT/'configs/research/study_p2_v3_native_positive_high.json',directory=folder/'private-store')
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):
        raise RuntimeError('Existing pending work: recover and inspect; no automatic relaunch')
    spec=state(host)['spec']
    request=dict(version='serial_family_generation_v3',family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=6)
    candidate=core.dispatch(host,plan('generate',generation=request),'p2-a-generate')['result']['candidate']
    seed=core.dispatch(host,plan('initialize_control',candidate,control_seed=dict(candidate=candidate,tensions_n=[[.2]*6])),'p2-a-control')['result']
    query=dict(candidate=seed['candidate'],operation='mujoco_nonlinear_task_capability_v1',model_source='mujoco',
        operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
        control_optimization=dict(source=seed['source'],settings=dict(version='local_control_search_v2',
            correction_window_s=[0.,.6],knots_s=[0.,.2,.4,.58],evaluation_requests=51,iterations=1)))
    out=analysis.dispatch(host,query,'p2-a-native',guard=core.guard,origin='engineering_preflight')
    raw=host.store.artifact(out['reference'])
    result=dict(study_id=host.run_id,implementation=state(host)['freeze'],candidate=candidate,seed=seed,
        analysis_reference=out['reference'],status=raw.get('status'),reason=raw.get('reason'),
        error=raw.get('error'),boundary=raw.get('boundary'),binding=raw.get('binding'),
        nonlinear_capability=raw.get('nonlinear_capability'),native_cost=next((raw[k].get('cost') for k in
            ('native_dynamics','native_progress','native_diagnostic') if raw.get(k,{}).get('cost')),None),
        control_schedule_reference=raw.get('control_schedule_reference'),
        mathematical_evaluations=state(host).get('mathematical_evaluations'),numerical_s=state(host)['numerical_s'],
        resource_use=core.resource_use(host),store=str(host.store.root),
        caveat='Engineering observation; independent task acceptance unmeasured.')
    atomic_json(folder/'summary.json',result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
