"""Reproduce the public build/analysis proof without a backend or provider call."""
import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from schemas.platform import SessionInput
from tools.platform_host import Host
from tools.platform_store import Store,plain
from tools.state_io import atomic_json
from extensions.tendon_family.route import create
from extensions.tendon_family.gvs import gvs_evaluate_tool_v2
from extensions.tendon_family.contracts import GVSDynamicsRequestV3
from examples.gvs_tracking import live_input

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();root=args.output
if root.exists():raise ValueError('USE_FRESH_PROOF_DIRECTORY')
v=live_input(json.loads((Path(__file__).parent/'frozen_input.json').read_text()))
v['run_id']='tracking-analysis-proof'
v['policy']['budget']=dict(tool_calls=6,model_calls=0,backend_solves=0,worker_calls=0,wall_s=7200)
store=Store(root)
store.create(dict(project_id=v['run_id'],grant_id=v['run_id'],authorization_source='Authorized candidate analysis proof; no backend/provider',budget=v['policy']['budget']))
create(root,v);host=Host(root,v['run_id'])
def call(name,arguments,request):
    receipt=host.invoke(dict(tool_id=name,arguments=arguments,request_id=request,reason='Verify public candidate-bound mathematics',cache='new'))
    atomic_json(root/(request+'_receipt.json'),receipt)
    if receipt['execution_status']!='completed':raise RuntimeError(receipt)
    return host.store.artifact(receipt['output'])
call('route.advance',dict(action='build',node_id='changed-build',combination='tracking',changes={'components/near/length_m':.162},reason='Changed-length binding proof',next_step='Compare bound mathematics with direct evaluation'),'build')
query=dict(source_node='changed-build',state=dict(q=[0.]*12,qdot=[0.]*12),input=dict(tendon_tensions_n={t['id']:0. for t in v['robot']['structure']['data']['tendons']}),samples_per_segment=2)
bound=call('analysis.gvs_candidate_evaluate',query,'analysis')
effective=SessionInput.model_validate(host.store.artifact(bound['binding']['configuration']))
request=GVSDynamicsRequestV3(**{k:w for k,w in query.items() if k!='source_node'},basis=effective.policy.controller.parameters.data['recipe']['basis'])
direct=plain(gvs_evaluate_tool_v2(SimpleNamespace(input=effective,reg=host.reg),request))
baseline=plain(gvs_evaluate_tool_v2(SimpleNamespace(input=SessionInput.model_validate(v),reg=host.reg),request))
assert bound['calculation']==direct
atomic_json(root/'proof.json',dict(binding=bound['binding'],calculation=bound['calculation'],direct_exact_match=True,
    baseline_tip_m=baseline['tip']['position_m'],changed_tip_m=direct['tip']['position_m'],usage=host.store.remaining()))
print('Public candidate-bound calculation exactly matches direct effective configuration.')
