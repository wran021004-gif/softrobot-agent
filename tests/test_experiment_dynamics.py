"""Focused checks, no dynamics integration and no optional engine startup."""
import unittest
from pathlib import Path
import numpy as np
from examples.platform_spatial_example import session_input, CHANGES
from extensions.experiment_dynamics.physics import resolve_physics
from extensions.experiment_dynamics.scene import assemble, applied_forces
from extensions.experiment_dynamics.spatial import SpatialModel
from extensions.experiment_dynamics.contracts import SpatialParameters
from extensions.experiment_dynamics.backends import SpatialBackend, PlanarBackend, LengthController
from extensions.robot_domain.contracts import RodDesign
from schemas.platform import SessionInput
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from tools.platform_tasks import compile_input
from tools.design_compiler import build_robot_ir


class ExperimentDynamicsTests(unittest.TestCase):
    def setUp(self):
        self.reg = registry()
        self.inp = _candidate(SessionInput.model_validate(session_input('math_spatial')),CHANGES,self.reg)
        self.ir = build_robot_ir(self.reg.parse(self.inp.robot.structure))
        self.physics = resolve_physics(self.ir)
        self.scene = assemble(self.inp,self.physics)
        self.model = SpatialModel(self.physics,self.scene,SpatialParameters())

    def test_resolution_scene_and_old_interfaces(self):
        rod = self.ir.resolved_rod
        for i,p in enumerate(self.physics.parts):
            self.assertEqual(p.mass_kg,rod.mass_kg[i])
            np.testing.assert_array_equal(np.diag(p.inertia_com_local_kg_m2),rod.inertia_diagonal_kg_m2[i])
            self.assertEqual(p.stiffness_nm_rad,(rod.stiffness_nm_rad[i],)*2)
            self.assertEqual(p.com_local_m,(.02,0.,0.))
        self.assertNotEqual(self.physics.identity,resolve_physics(RodDesign()).identity)
        peer = session_input('scene_mujoco')
        peer = _candidate(SessionInput.model_validate(peer),CHANGES,self.reg)
        self.assertEqual(self.scene,assemble(peer,self.physics))
        self.assertEqual(applied_forces(self.scene,.006),{'segment_7':(0.,.2,.1)})
        self.assertEqual(applied_forces(self.scene,.014),{})
        bad = self.inp.model_dump(mode='json')
        bad['task']['environment']['data']['environment']['objects'].append(dict(kind='ball',name='ball',position_m=[0.,0.,0.]))
        with self.assertRaisesRegex(ValueError,'SCENE_OBJECT_UNSUPPORTED: ball:ball'):
            assemble(SessionInput.model_validate(bad),self.physics)
        from examples.platform_fixtures import reference_input
        self.assertEqual(compile_input(reference_input())['input']['policy']['backend']['extension_id'],'backend.reference')
        planar = SessionInput.model_validate(session_input('math_planar'))
        PlanarBackend.check(planar,self.reg.parse(planar.policy.backend.parameters),self.reg.parse(planar.policy.controller.parameters))
        with self.assertRaisesRegex(ValueError,'PLANAR_V1_SCOPE'):
            PlanarBackend.check(self.inp,None,self.reg.parse(self.inp.policy.controller.parameters))
        # Old bindings stay separate and still resolve to the old adapters.
        self.assertEqual(self.reg.get('backend.matlab').resolve().__name__,'MatlabBackend')
        self.assertEqual(self.reg.get('backend.mujoco').resolve().__name__,'MujocoBackend')

    def test_coupled_mechanics_and_virtual_work(self):
        q = np.linspace(-.04,.07,16); v = np.linspace(.1,-.2,16)
        geometry = self.model.geometry(q,v)
        eps = 1e-6
        numeric = np.column_stack([(self.model.geometry(q+np.eye(16)[j]*eps)['lengths']-
            self.model.geometry(q-np.eye(16)[j]*eps)['lengths'])/(2*eps) for j in range(16)])
        np.testing.assert_allclose(geometry['Jlength'],numeric,atol=1e-10)
        command = geometry['lengths']-.003
        terms = self.model.terms(q,v,command,{'segment_7':(0.,.2,.1)})
        np.testing.assert_allclose(terms['mass'],terms['mass'].T,atol=1e-14)
        self.assertGreater(np.linalg.eigvalsh(terms['mass']).min(),0.)
        self.assertGreater(np.linalg.norm(terms['mass'][::2,1::2]),1e-6)
        self.assertAlmostEqual(v@terms['drive'],-terms['tension']@(geometry['Jlength']@v),places=12)
        self.assertAlmostEqual(v@terms['external'],np.array((0.,.2,.1))@(geometry['links'][-1]['J']@v),places=12)
        # Exact gyroscopic/Coriolis power identity: v.b = 1/2 v.Mdot.v.
        plus = self.model.terms(q+eps*v,v,command,{})['mass']
        minus = self.model.terms(q-eps*v,v,command,{})['mass']
        self.assertAlmostEqual(v@terms['bias'],.5*v@((plus-minus)/(2*eps))@v,places=10)
        self.assertGreater(np.linalg.norm(self.model.acceleration(q,v,command,{})[1::2]),1e-3)
        slack = self.model.terms(q,v,geometry['lengths']+.001,{})
        np.testing.assert_array_equal(slack['tension'],0.)

    def test_signals_feedback_and_preflight(self):
        snapshot = compile_input(session_input('math_spatial'),self.reg)
        self.assertNotIn('mujoco',snapshot['dependencies']['backend.math_spatial@1.0.0']['packages'])
        from extensions.experiment_dynamics.signals import observation_specs
        specs = observation_specs(self.inp,self.reg)
        self.assertEqual(len([s for s in specs if s.name == 'joint_position']),16)
        self.assertEqual(next(s for s in specs if s.name == 'tendon_tension').phase,'pre_step_solver')
        for mode in ('C1','C2'):
            from schemas.exploration import ExplorationControl
            c = LengthController(ExplorationControl(mode=mode),.002)
            c.configure(self.ir,self.scene,Path(__file__).resolve())
            tip = self.model.geometry(np.zeros(16))['nodes'][-1]
            command = c.command(0.,0,dict(tip_position_m=tip.tolist()))
            self.assertEqual(command.shape,(4,))
            self.assertTrue(np.isfinite(command).all())
            if mode == 'C2':
                self.assertEqual(len(c.actual.updates),1)
                np.testing.assert_allclose(c.actual.updates[0]['observed_tip_m'],[.32,0.,0.],atol=1e-14)


if __name__ == '__main__': unittest.main()
