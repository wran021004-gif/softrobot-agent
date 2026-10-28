"""Zero-integration contract/virtual-work checks; these are not research results."""
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
import numpy as np
import mujoco
from tools.research.config import resolve
from tools.research.phs2d import generation
from tools.state_io import read
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.passive import PassiveModel,material_point
from extensions.tendon_family.mjcf import compile_xml
from tools.research.phs2d_evaluation import evaluate


class PassiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('runs/phs2d/tests').mkdir(parents=True,exist_ok=True)
        s=resolve('configs/research/study_phs2d_v1.json')
        q=dict(version='serial_family_generation_v2',family_space_identity=s['family_space_identity'],segment_count=2,**generation())
        _,_,cls.physics=generate_family(dict(space=s['family_space'],request=q))
        cls.p=read('configs/research/phs2d_protocol_v1.json')

    def test_force_virtual_work_and_tendon_derivatives(self):
        with tempfile.TemporaryDirectory(dir='runs/phs2d/tests') as folder:
            n=PassiveModel(self.physics,self.p,self.physics['reference_lengths_m'],folder);m=n.model;d=mujoco.MjData(m)
            d.qpos[:]=.02*np.sin(np.arange(m.nv));mujoco.mj_forward(m,d)
            q=d.qpos.copy();v=np.cos(np.arange(m.nv));h=1e-6
            Jl=n.tendon_jac(d);_,J=n.apply_force(d,.37,.1)
            self.assertLess(abs(d.qfrc_applied@v-.1*(J@v)[0]),1e-12)
            sampled=[]
            for sign in (-1,1):
                d.qpos[:]=q+sign*h*v;mujoco.mj_forward(m,d)
                sampled.append((n.point(d,material_point(self.physics,.37))[0],d.ten_length.copy()))
            np.testing.assert_allclose((sampled[1][0]-sampled[0][0])/(2*h),J@v,atol=1e-8)
            np.testing.assert_allclose((sampled[1][1]-sampled[0][1])/(2*h),Jl@v,atol=1e-8)
            n.apply_force(d,.37,0.);self.assertFalse(np.any(d.qfrc_applied));self.assertEqual(m.nu,0)
            row=n.snapshot(d,.37,.1)
            self.assertTrue(row['constraint_rows'])
            self.assertTrue(all(r['multiplier_n']>=0 and r['upper_sign_error']<1e-10 for r in row['constraint_rows']))

    def test_active_modes_preserved_and_payout_validation(self):
        with tempfile.TemporaryDirectory(dir='runs/phs2d/tests') as folder:
            n=PassiveModel(self.physics,self.p,self.physics['reference_lengths_m'],folder)
            for mode in ('ideal_tension','actuator_realistic'):
                scene=deepcopy(n.scene);scene['control']['tension_execution_mode']=mode
                path=compile_xml(self.physics,scene,None,Path(folder)/(mode+'.xml'))
                m=mujoco.MjModel.from_xml_path(str(path))
                self.assertEqual(m.nu,2);self.assertFalse(np.any(m.tendon_limited))
            scene=deepcopy(n.scene);scene['control']['payout_lengths_m']={}
            with self.assertRaisesRegex(ValueError,'EXACT_POSITIVE'):
                compile_xml(self.physics,scene,None,Path(folder)/'invalid.xml')

    def test_material_boundary_and_no_rigid_success(self):
        left=material_point(self.physics,.5-1e-6);right=material_point(self.physics,.5)
        self.assertNotEqual(left['body'],right['body']);self.assertAlmostEqual(right['position_m'][0],0.)
        positions=np.zeros((22,3)).tolist()
        base=dict(status='stable',samples=[dict(positions=positions)])
        loaded=dict(status='stable',samples=[dict(positions=positions,force_point=[.001,0,0])])
        result=evaluate(self.p,base,loaded,.5)
        self.assertEqual(result['status'],'valid_failure');self.assertGreater(result['violations']['middle'],0)
        loaded['status']='unsettled_or_constraint_failure'
        self.assertEqual(evaluate(self.p,base,loaded,.5)['status'],'invalid')


if __name__=='__main__':unittest.main()
