"""Focused force contracts; no mj_step and no scientific feasibility claims."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
import mujoco
import numpy as np

from extensions.tendon_family.backends import _bind_mujoco_forces, _apply_mujoco_forces
from extensions.tendon_family.mujoco_analysis import NativeModel
from tools.research.native_analysis import assessment
from tools.state_io import read
from schemas.platform import SessionInput

ROOT=Path(__file__).resolve().parents[2]


class ExternalForceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=read(ROOT/'evidence/b3_r1_history_assisted_050/design_package.json')['configuration']
        cls.cfg['task']['environment']['data']['external_forces']=[dict(
            entity='payload',point='center_of_mass',frame='world',force_n=[0.,.02,-.03],start_s=.1,end_s=.25)]
        cls.native=NativeModel(cls.cfg)

    def test_tick_boundaries_sum_and_clear_world_com_couple(self):
        model=SimpleNamespace(opt=SimpleNamespace(timestep=.0005),body=lambda name:SimpleNamespace(id={'a':2,'b':1}[name]))
        scene=dict(forces=[dict(entity='a',force_n=[0.,1.,-2.],start_s=.01,end_s=.02),
            dict(entity='a',force_n=[1.,0.,0.],start_s=.015,end_s=.02)])
        forces=_bind_mujoco_forces(model,scene)
        data=SimpleNamespace(time=0.,xfrc_applied=np.ones((3,6)))
        for t,expected in [(0.,[0,0,0]),(.01-1e-17,[0,1,-2]),(.015,[1,1,-2]),(.02-1e-17,[0,0,0])]:
            data.time=t;_apply_mujoco_forces(model,data,forces)
            np.testing.assert_array_equal(data.xfrc_applied[2,:3],expected)
            self.assertFalse(np.any(data.xfrc_applied[:,3:]))
            self.assertFalse(np.any(data.xfrc_applied[:2]))

    def test_assessment_accepts_only_existing_force_contract_and_grid(self):
        req=SimpleNamespace(required_physics=['external_applied_forces'])
        self.assertEqual(assessment(SessionInput.model_validate(self.cfg),req)['uses']['native_numerics']['status'],'ACCEPT')
        for field,value in [('frame','body'),('point','tip_site'),('entity','unknown'),('start_s',.101),('end_s',.51),('force_n',[float('nan'),0,0])]:
            cfg=deepcopy(self.cfg);cfg['task']['environment']['data']['external_forces'][0][field]=value
            fit=assessment(SessionInput.model_validate(cfg),req)
            self.assertEqual(fit['uses']['native_numerics']['status'],'REJECT',(field,fit))

    def test_restore_uses_frozen_force_and_rejects_extra_generalized_force(self):
        n=self.native;d=mujoco.MjData(n.model);d.time=.1;n.forward(d)
        point=n.checkpoint(d)
        restored=n.restore(point);bid=n.model.body('payload').id
        np.testing.assert_array_equal(restored.xfrc_applied[bid,:3],[0,.02,-.03])
        # Restored engine user buffers cannot replace the frozen task schedule.
        d.xfrc_applied[:]=999
        restored=n.restore(n.checkpoint(d))
        np.testing.assert_array_equal(restored.xfrc_applied[bid,:3],[0,.02,-.03])
        d.qfrc_applied[0]=1
        with self.assertRaisesRegex(ValueError,'UNSCHEDULED_GENERALIZED_FORCE'):n.restore(n.checkpoint(d))
        self.assertEqual(n.cost['physics_steps'],0)

    def test_mechanics_includes_com_generalized_force_without_tip_couple(self):
        n=self.native;d=mujoco.MjData(n.model);d.time=.1
        result=n.mechanics(d,[.2]*len(n.aids));bid=n.model.body('payload').id
        jac=np.zeros((3,n.model.nv));mujoco.mj_jacBodyCom(n.model,d,jac,None,bid)
        expected=jac.T@np.array([0,.02,-.03])
        np.testing.assert_allclose(result['generalized_forces_nm']['external_body'],expected[n.vi],rtol=0,atol=1e-14)
        self.assertGreater(np.linalg.norm(expected),0)
        self.assertGreater(np.linalg.norm(d.site_xpos[n.tip]-d.xipos[bid]),.001)
        forces=result['generalized_forces_nm']
        np.testing.assert_allclose(np.asarray(result['mass_matrix_kg_m2'])@result['qacc_rad_s2'],
            np.asarray(forces['passive'])+forces['actuator']+np.asarray(forces['applied'])+forces['external_body']
            -np.asarray(forces['bias'])+forces['constraint'],rtol=1e-10,atol=1e-12)
        self.assertFalse(np.any(d.xfrc_applied[:,3:]))
        self.assertTrue(result['validity']['external_applied_force'])

    def test_reconstruct_rejects_changed_frozen_force_before_steps(self):
        n=self.native;scene=deepcopy(n.scene);scene['forces'][0]['force_n']=[1,0,0]
        with self.assertRaisesRegex(ValueError,'FROZEN_SCENE_MISMATCH'):
            n.reconstruct(dict(physics_identity=n.physics['identity'],native_replay=dict(scene=scene,rows=[])))
        self.assertEqual(n.cost['physics_steps'],0)

    def test_task_only_pair_composes_with_original_limits_and_same_robot(self):
        from tools.research.config import patch
        from extensions.tendon_family.scene import assemble_physical
        from extensions.tendon_family.backends import physics_for
        zero=read(ROOT/'tasks/b2_load_hold_zero_v1.json')
        change=read(ROOT/'tasks/b2_load_hold_v1.json');change.pop('extends')
        force=patch(zero,change)
        for task in (zero,force):
            cfg=deepcopy(self.cfg);cfg['task']=task['task'];cfg['seed']=task['seed']
            cfg['policy']['controller']['parameters']['data']['settling']=task['settling']
            inp=SessionInput.model_validate(cfg);assemble_physical(inp,physics_for(inp))
        self.assertEqual(zero['settling'],force['settling'])
        self.assertEqual(zero['settling']['position_limit_m'],.01)
        self.assertEqual(zero['settling']['speed_limit_m_s'],.02)
        for field in ('goal','timing','evaluator','initializer','observations'):
            self.assertEqual(zero['task'][field],force['task'][field])


if __name__=='__main__':unittest.main()
