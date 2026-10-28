"""Native passive static mechanics fixtures; zero integration, not research evidence."""
import unittest
import numpy as np
from tools.research.config import resolve
from tools.research.phs2d import generation
from tools.state_io import read
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.passive import PassiveModel
from extensions.tendon_family.passive_equilibrium import solve,consistency,StaticProblem,tangent


class EquilibriumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=resolve('configs/research/study_phs2d_round2_v1.json')
        req=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=2,**generation())
        _,_,physics=generate_family(dict(space=spec['family_space'],request=req));p=read('configs/research/phs2d_protocol_v3.json')
        cls.n=PassiveModel(physics,p,physics['reference_lengths_m'],'runs/phs2d-round2/test-fixture')

    def test_gradient_and_virtual_work(self):
        v=consistency(self.n)
        self.assertLess(v['objective_gradient_error'],1e-7);self.assertLess(v['tendon_gradient_error'],1e-7)
        self.assertLess(v['force_consistency_error'],1e-10)

    def test_equilibrium_kkt_branch_and_loaded_geometric_hessian(self):
        raw=solve(self.n,multistart=True);eq=raw['equilibrium']
        self.assertEqual(raw['status'],'qualified_local_minimum');self.assertTrue(raw['multistart_same_branch'])
        self.assertLess(eq['stationarity_inf_nm'],1e-6);self.assertGreaterEqual(min(eq['tensions_n']),0.)
        self.assertGreater(min(eq['reduced_eigenvalues']),0)
        q=np.array(eq['qpos'])+.01*np.sin(np.arange(self.n.model.nv))
        a=StaticProblem(self.n,.5,0.);b=StaticProblem(self.n,.5,.1);v=np.cos(np.arange(len(q)));step=1e-5
        H,_=b.hessian(q,np.zeros(self.n.model.ntendon));H0,_=a.hessian(q,np.zeros(self.n.model.ntendon))
        self.assertGreater(np.linalg.norm(H-H0),1e-7)
        np.testing.assert_allclose(H@v,(b.gradient(q+step*v)-b.gradient(q-step*v))/(2*step),atol=1e-6)
        import json
        json.dumps(raw,allow_nan=False)  # Original numpy-bool persistence regression.


if __name__=='__main__':unittest.main()
