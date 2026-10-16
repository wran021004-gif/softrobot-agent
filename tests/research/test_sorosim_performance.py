"""Matched old/current routing and complete NLP evaluations; no shortened horizon."""
from copy import deepcopy
from pathlib import Path
import hashlib
import subprocess
import unittest
import numpy as np
from tools.state_io import read
from sorosim_s35_probe import ROOT,RAW,save
from extensions.tendon_family.sorosim_session import SorosimSession

BASELINE='8f4c642b'


def run(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    # Historical implementation lives only in this experiment, not production.
    reference=folder/'reference';reference.mkdir()
    old=subprocess.check_output(['git','show',BASELINE+':matlab/sorosim_control/sr_routing.m'],cwd=ROOT)
    (reference/'sr_routing.m').write_bytes(old)
    save(folder,'provenance',dict(baseline_commit=BASELINE,baseline_routing_sha256=hashlib.sha256(old).hexdigest(),
        current_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'matlab/sorosim_control').glob('*.m')},
        budget=dict(full_nmpc_solves=0,physical_steps=0),scope='Alternating warmed kernels and unique complete trajectory callbacks; no solver-level timing claim.'))
    spec=read(RAW/'control_spec.json')['specification'];points=read(ROOT/'evidence/sorosim_s35/attempt02/physical.json')['probes']
    updates=read(RAW/'nmpc_updates.json');session=SorosimSession()
    try:
        with session:
            session.construct(spec);save(folder,'environment',dict(environment=session.environment,dependency=session.dependency))
            cases=[]
            for i,p in enumerate(points):
                c=deepcopy(read(ROOT/'evidence/sorosim_control/s3_callbacks.json')['result']['context'])
                c.update(measured=p['x'],elapsed=updates[i]['time_s'],previous=updates[i]['mathematical_facts']['previous_input'])
                facts=updates[i]['mathematical_facts'];scale=np.array(facts['state_scale'])
                z=np.r_[(np.array(facts['states'])/scale).ravel(),(np.array(facts['tensions'])/8).ravel()]
                cases.append(dict(kind='performance',x=p['x'],u=p['u'],a=np.linspace(-10,20,12).tolist(),context=c,z=z.tolist()))
            initial=read(ROOT/'evidence/sorosim_control/s3_callbacks.json')['result']
            cases.append(dict(cases[0],context=initial['context'],z=initial['initial_vector']))
            save(folder,'cases',cases)
            for i,case in enumerate(cases):
                for mode in (('baseline','optimized') if i%2==0 else ('optimized','baseline')):
                    if mode=='baseline':session.engine.addpath(str(reference.resolve()),'-begin',nargout=0)
                    session.engine.eval('clear sr_routing sr_derivatives sr_nmpc_callbacks sr_diagnose',nargout=0)
                    result=session.evaluate('diagnose',case);save(folder,f'{mode}_{i}',result)
                    if mode=='baseline':session.engine.rmpath(str(reference.resolve()),nargout=0)
                    print(i,mode,np.median(result['warmed_s'],axis=0).tolist(),flush=True)
    except BaseException as exc:
        save(folder,'failure',dict(error_type=type(exc).__name__,error=str(exc)));raise
    finally:save(folder,'timings',session.timings)


def verify(folder):
    rows=[]
    for i in range(4):
        old=read(folder/f'baseline_{i}.json');new=read(folder/f'optimized_{i}.json');errors={}
        for part,keys in [('routing',['lengths','force_map','tendon_force','force_state_derivative','tip_velocity_q']),
            ('derivatives',['mass_matrix','residual','Rq','Rqd','Ru','tip_position','tip_velocity']),
            ('evaluation',['objective','gradient','constraints','jacobian'])]:
            for key in keys:
                a=np.asarray(old[part][key]);b=np.asarray(new[part][key]);error=float(np.max(np.abs(a-b)))
                errors[part+'/'+key]=dict(absolute_max=error,relative_norm=float(np.linalg.norm(a-b)/max(1e-30,np.linalg.norm(a))))
                np.testing.assert_allclose(a,b,atol=2e-8,rtol=2e-5,err_msg=f'{i}:{part}/{key}')
        assert max(new['directional_relative'])<2e-4
        before=np.array(old['warmed_s']);after=np.array(new['warmed_s'])
        rows.append(dict(case=i,errors=errors,baseline_median_s=np.median(before,axis=0).tolist(),
            optimized_median_s=np.median(after,axis=0).tolist(),speedup=(np.median(before,axis=0)/np.median(after,axis=0)).tolist(),
            baseline_range_s=np.ptp(before,axis=0).tolist(),optimized_range_s=np.ptp(after,axis=0).tolist()))
    save(folder,'comparison',dict(cases=rows,timing_columns=['routing_with_tangent','derivatives','unique_full_trajectory'],
        complete_solver_speedup='not measured',scientific_problem_changed=False))


class PerformanceTests(unittest.TestCase):
    def test_saved_matched_equivalence_and_speedup(self):
        folder=ROOT/'evidence/sorosim_performance/attempt01'
        result=read(folder/'comparison.json')
        for row in result['cases']:
            self.assertGreater(row['speedup'][0],1.1)
            self.assertGreater(row['speedup'][2],1.1)
            self.assertLess(row['errors']['evaluation/jacobian']['relative_norm'],2e-5)
            self.assertLess(row['errors']['evaluation/objective']['absolute_max'],1e-9)
        self.assertEqual(result['complete_solver_speedup'],'not measured')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
    if a.run:run(a.run)
    elif a.verify:verify(a.verify)
    else:unittest.main(argv=['test_sorosim_performance'])
