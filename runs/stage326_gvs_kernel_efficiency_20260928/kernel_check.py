"""Check only the changed implicit residual and its exact AD at saved states."""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import casadi as ca
import numpy as np
from schemas.platform import SessionInput
from schemas.platform_math import SystemContext
from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.gvs import GVSModel
from extensions.tendon_family.gvs_casadi import expression_from_system, functions_for
from extensions.tendon_family.gvs_trajectory import implicit_step_residual

folder = Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).resolve().parent
label = sys.argv[1]
target = folder / (label+'_kernel.json')
if target.exists():
    raise ValueError('KERNEL_EVIDENCE_ALREADY_EXISTS')
saved = json.loads((ROOT/'runs/stage325_tracking_efficiency_20260928/selected_states.json').read_text())
plans = json.loads((folder/'baseline.json').read_text())['records']
inp = SessionInput.model_validate(saved['input'])
p = GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
sample = saved['samples'][0]
started = time.perf_counter()
system = GVSModel(p).build_system(inp.robot, p, None, SystemContext(
    x0=sample['measured_x'], u0=sample['previous_u'], scene=inp.task.environment))
functions = functions_for(expression_from_system(system))
n=len(sample['measured_x'])//2
h=inp.task.timing.control_period_s/inp.policy.controller.parameters.data['recipe']['substeps']
f = implicit_step_residual(functions, n, len(sample['previous_u']), h)
jac = f.jacobian()
construction = time.perf_counter()-started
kernels = [k for k in f.find_functions(-1) if k.name() == 'gvs_force_balance']
sizes = []
for k in kernels:
    # Diagnostic only: count repeated expressions removed by this one direction.
    inputs = k.mx_in()
    compact = ca.Function('compact_'+k.name(), inputs, k.call(inputs, True, False),
                          {'cse': True, 'der_options': {'cse': True}})
    sizes.append(dict(name=k.name(), nodes=k.n_nodes(), cse_nodes=compact.n_nodes()))
records = []
for sample, plan in zip(saved['samples'], plans, strict=True):
    args = [sample['measured_x'], plan['selected_states'][1], plan['selected_tensions'][0]]
    jac(*args, ca.DM.zeros(2*n))
    stamp = time.perf_counter(); value = np.asarray(f(*args)); residual_s = time.perf_counter()-stamp
    stamp = time.perf_counter(); derivatives = [np.asarray(v) for v in jac(*args, ca.DM.zeros(2*n))]; jacobian_s = time.perf_counter()-stamp
    records.append(dict(time_s=sample['time_s'], residual=value.tolist(),
        jacobians=[v.tolist() for v in derivatives], residual_s=residual_s, jacobian_s=jacobian_s))
result = dict(label=label, construction_s=construction, kernel_nodes=sizes, records=records,
              local_optimization_solves=0, provider_requests=0, backend_rollouts=0)
if label == 'modified':
    old = json.loads((folder/'baseline_kernel.json').read_text())
    differences = []
    for a,b in zip(old['records'],records,strict=True):
        av,bv=np.asarray(a['residual']),np.asarray(b['residual'])
        np.testing.assert_allclose(bv,av,rtol=1e-10,atol=1e-10)
        maximum = 0.
        for aj,bj in zip(a['jacobians'],b['jacobians'],strict=True):
            aj,bj=np.asarray(aj),np.asarray(bj)
            np.testing.assert_allclose(bj,aj,rtol=1e-9,atol=1e-9)
            maximum=max(maximum,float(np.max(abs(bj-aj))))
        differences.append(dict(time_s=b['time_s'],residual_max_abs=float(np.max(abs(bv-av))),jacobian_max_abs=maximum))
    result['equivalence'] = dict(passed=True, differences=differences)
target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
