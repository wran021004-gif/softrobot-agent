"""Focused D0-D2 checks for state projection and executable GVS-LQR composition."""
import unittest
import json
from pathlib import Path

import numpy as np

from examples.platform_tendon_family import example_design, design_space, session
from extensions.tendon_family.backends import MatlabBackend, MujocoBackend, physics_for
from extensions.tendon_family.gvs_lqr import GVSLQRController
from extensions.tendon_family.gvs_projection import discretize, project
from extensions.tendon_family.gvs import forward_kinematics
from extensions.tendon_family.geometry import geometry
from extensions.tendon_family.scene import assemble
from schemas.platform import Payload, SessionInput
from tools.platform_registry import registry
from tools.platform_tasks import compile_input


def lqr_input(duration=.03,execution_mode='actuator_realistic'):
    design=example_design();value=session('family_mujoco',design,design_space(design))
    value['task']['environment']['data']['external_forces']=[]
    value['task']['environment']['data']['environment']['gravity_m_s2']=[0.,0.,0.]
    value['task']['timing']['duration_s']=duration
    value['task']['sampling']['window_s']=[0.,duration]
    value['policy']['controller']={'extension_id':'controller.gvs_lqr','version':'1.0.0','parameters':{
        'contract':'family.gvs_lqr_control','version':'1.0.0','data':{
            'equilibrium_q':[0.]*8,'equilibrium_tensions_n':[0.]*6,
            'curvature_weight':1.,'state_rate_weight':.1,'tendon_tension_weight':1.,
            'tension_execution_mode':execution_mode}}}
    return design,value


class GVSProjectorAndController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg=registry();cls.design=example_design()
        value=session('family_mujoco',cls.design,design_space(cls.design))
        cls.inp=SessionInput.model_validate(value);cls.physics=physics_for(cls.inp)

    def test_projector_round_trip_zero_and_spatial_state(self):
        states=[(np.zeros(8),np.zeros(8)),(
            np.array([.3,-.1,-.2,.08,-.4,.15,.25,-.12]),
            np.array([.03,-.02,.01,.04,-.05,.02,-.01,.03]))]
        for q,qdot in states:
            with self.subTest(q=q.tolist()):
                backend_q,backend_v=discretize(self.physics,self.design,q,qdot)
                result=project(self.physics,self.design,backend_q,backend_v)
                np.testing.assert_allclose(result['q_gvs'],q,atol=1e-12)
                np.testing.assert_allclose(result['qdot_gvs'],qdot,atol=1e-12)
                self.assertLess(result['projection_residual_max_rad_m'],1e-12)
                self.assertLess(result['rate_projection_residual_max_rad_m_s'],1e-12)
                if np.any(q):
                    backend_tip=geometry(self.physics,backend_q)['tip']
                    gvs_tip=forward_kinematics(self.design,q,samples_per_segment=2)['tip_position_m']
                    np.testing.assert_allclose(backend_tip,gvs_tip,atol=2e-4)

    def test_matlab_tension_shared_input_defaults_missing_commands(self):
        design=example_design();value=session('matlab_spatial',design,design_space(design))
        value['policy']['controller']['parameters']['data']={
            'mode':'tension_reference','desired_tendon_tensions_n':[.1]*6}
        inp=SessionInput.model_validate(value);backend=MatlabBackend();backend.compile(inp,self.reg)
        shared=backend.shared_input(10.)
        self.assertEqual(shared['control']['command_vector'],[0.]*6)

    def test_executable_composition_and_model_lqr_separation(self):
        design,value=lqr_input();compiled=SessionInput.model_validate(compile_input(value)['input'])
        physics=physics_for(compiled);plan=assemble(compiled,physics)['control']
        controller=GVSLQRController(compiled.policy.controller.parameters.data,compiled.task.timing.control_period_s)
        controller.configure(physics,plan)
        zero=np.zeros(len(physics['dofs']));zero_geometry=geometry(physics,zero)
        controller.command(0.,zero_geometry,zero,zero)
        np.testing.assert_allclose(controller.last['raw_desired_tension_n'],controller.u0,atol=1e-12)
        controller.configure(physics,plan)
        delta=np.array([.01,-.005,.004,0.,-.006,.003,0.,-.002]+[0.]*8)
        q,v=discretize(physics,design,delta[:8],delta[8:])
        g=geometry(physics,q)
        controller.command(0.,g,q,v)
        expected=controller.u0-controller.K@delta
        np.testing.assert_allclose(controller.last['raw_desired_tension_n'],expected,atol=1e-10)
        self.assertTrue(np.all(np.asarray(controller.last['desired_tension_n'])>=0.))
        self.assertTrue(np.all(np.asarray(controller.last['desired_tension_n'])<=8.))
        speed=np.array([a['velocity_limit'] for a in physics['actuators']])
        self.assertTrue(np.all(np.abs(controller.u)<=speed*controller.period_s+1e-15))
        self.assertEqual(len(controller.last['projected_gvs_q']),8)
        self.assertIn('gvs_projection_residual_max_rad_m',controller.last)
        self.assertEqual(plan['mapping']['bridge'],'execute_tension_reference')
        self.assertFalse(self.reg.get('controller.lqr','1.0.0','controller').capabilities['backend_executable'])
        self.assertTrue(self.reg.get('controller.gvs_lqr','1.0.0','controller').capabilities['backend_executable'])

    def test_short_mujoco_closed_loop_is_finite(self):
        _,value=lqr_input();inp=SessionInput.model_validate(compile_input(value)['input'])
        backend=MujocoBackend();controller=GVSLQRController(inp.policy.controller.parameters.data,inp.task.timing.control_period_s)
        backend.compile(inp,self.reg);backend.initialize(Payload(contract='family.initial',data={}),controller)
        directory=Path('runs/gvs_lqr_smoke_test/backend').resolve()
        result=backend.run(directory,30.)
        self.assertEqual(result.solver_status,'completed')
        self.assertEqual(backend.scene['control']['mode'],'gvs_lqr')
        self.assertTrue(all(np.isfinite(row['qpos_rad']).all() and np.isfinite(row['qvel_rad_s']).all()
            for row in backend.controller.observations))
        self.assertTrue(all('projected_gvs_q' in row and 'desired_tension_n' in row
            and 'actuator_saturated' in row for row in backend.controller.observations))

    def test_short_ideal_tension_mujoco_is_direct_finite_and_observable(self):
        _,value=lqr_input(execution_mode='ideal_tension')
        inp=SessionInput.model_validate(compile_input(value)['input'])
        backend=MujocoBackend();controller=GVSLQRController(
            inp.policy.controller.parameters.data,inp.task.timing.control_period_s)
        backend.compile(inp,self.reg);backend.initialize(Payload(contract='family.initial',data={}),controller)
        directory=Path('runs/gvs_lqr_ideal_smoke_test/backend').resolve()
        result=backend.run(directory,30.)
        self.assertEqual(result.solver_status,'completed')
        self.assertEqual(backend.scene['control']['tension_execution_mode'],'ideal_tension')
        xml=(directory/'robot.xml').read_text(encoding='utf-8')
        self.assertIn('_direct_tension',xml);self.assertNotIn('_length_servo',xml)
        commands=json.loads((directory/'actual_commands.json').read_text(encoding='utf-8'))
        observations=json.loads((directory/'controller_observations.json').read_text(encoding='utf-8'))
        self.assertTrue(all('actuator_command' not in row and 'target_lengths_m' not in row for row in commands+observations))
        names={signal.spec.name for signal in result.signals}
        self.assertTrue({'desired_tendon_tension','tendon_tension','tendon_length',
            'tendon_length_change','tendon_length_rate'} <= names)
        self.assertNotIn('actuator_command',names);self.assertNotIn('tendon_target_length',names)
        self.assertIsNone(controller.u)
        self.assertTrue(all(np.isfinite(signal.values).all() for signal in result.signals))
        desired={s.spec.entity:np.asarray(s.values) for s in result.signals if s.spec.name=='desired_tendon_tension'}
        actual={s.spec.entity:np.asarray(s.values) for s in result.signals if s.spec.name=='tendon_tension'}
        for entity in desired: np.testing.assert_allclose(actual[entity],desired[entity],atol=1e-12)


if __name__=='__main__': unittest.main()
