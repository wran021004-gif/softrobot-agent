"""Focused algebraic checks for constant model-space tendon-tension execution."""
import unittest

import numpy as np
from pydantic import ValidationError

from examples.platform_tendon_family import example_design, design_space, session
from extensions.tendon_family.backends import physics_for
from extensions.tendon_family.control import Controller
from extensions.tendon_family.contracts import Control
from extensions.tendon_family.geometry import geometry
from extensions.tendon_family.scene import assemble
from extensions.tendon_family.signals import observation_specs
from schemas.platform import SessionInput
from tools.platform_registry import registry


class TensionBridge(unittest.TestCase):
    def input(self, tensions):
        design=example_design()
        value=session('family_mujoco',design,design_space(design))
        value['policy']['controller']['parameters']['data']={
            'mode':'tension_reference','desired_tendon_tensions_n':tensions}
        return design,SessionInput.model_validate(value)

    def configured(self,tensions):
        _,inp=self.input(tensions);p=physics_for(inp);scene=assemble(inp,p)
        controller=Controller(Control.model_validate(inp.policy.controller.parameters.data),
            inp.task.timing.control_period_s)
        controller.configure(p,scene['control'])
        g=geometry(p,np.zeros(len(p['dofs'])),scene['assembly']['mount'])
        return inp,p,scene,controller,g

    def test_frozen_order_force_clipping_and_signal(self):
        design,inp=self.input([9.,.4,.8,.7,1.1,.3])
        p=physics_for(inp);plan=assemble(inp,p)['control']
        self.assertEqual(plan['reference']['tendon_order'],[t.id for t in design.tendons])
        self.assertEqual(plan['reference']['desired_tensions_n'][0],8.)
        self.assertEqual(plan['reference']['requested_tensions_n'][0],9.)
        self.assertEqual(plan['reference']['force_limit_saturated'],[True,False,False,False,False,False])
        desired=[s for s in observation_specs(inp,registry()) if s.name=='desired_tendon_tension']
        self.assertEqual([s.entity for s in desired],[t.id for t in design.tendons])
        with self.assertRaisesRegex(ValueError,'TENSION_REFERENCE_DIMENSION_MISMATCH'):
            _,short=self.input([1.]);assemble(short,physics_for(short))
        with self.assertRaises(ValidationError): Control(mode='tension_reference',desired_tendon_tensions_n=[-1.])

    def test_servo_direction_velocity_travel_and_existing_modes(self):
        inp,p,scene,controller,g=self.configured([0.]*6)
        pretension_target=np.array(p['reference_lengths_m'])-np.array([t['pretension_n']/t['kp_n_m'] for t in p['tendons']])
        zero_target=controller.command(0.,g,np.zeros(len(p['dofs'])),np.zeros(len(p['dofs'])))
        self.assertTrue(np.all(zero_target>pretension_target))
        np.testing.assert_allclose(controller.last['predicted_tension_n'],0.,atol=1e-12)

        inp,p,scene,controller,g=self.configured([8.]*6)
        first=controller.command(0.,g,np.zeros(len(p['dofs'])),np.zeros(len(p['dofs'])))
        self.assertTrue(np.all(first<pretension_target))
        speed=np.array([a['velocity_limit'] for a in p['actuators']])
        limits=np.array([a['limits'] for a in p['actuators']])
        self.assertTrue(np.all(np.abs(controller.u)<=speed*inp.task.timing.control_period_s+1e-15))
        self.assertTrue(np.all(controller.u>=limits[:,0]) and np.all(controller.u<=limits[:,1]))
        self.assertTrue(all(controller.last['actuator_saturated']))
        for step in range(1,40): controller.command(step*.01,g,np.zeros(len(p['dofs'])),np.zeros(len(p['dofs'])))
        np.testing.assert_allclose(controller.last['predicted_tension_n'],8.,atol=1e-10)

        normal=session('family_mujoco',example_design(),design_space(example_design()))
        normal_inp=SessionInput.model_validate(normal);normal_p=physics_for(normal_inp)
        self.assertEqual(assemble(normal_inp,normal_p)['control']['algorithm']['id'],'tip_resolved_rate_feedback_v1')

    def test_coupled_transmission_uses_signs_and_minimum_norm_solution(self):
        p=dict(transmission=[[1.],[-1.]],reference_lengths_m=[1.,1.],
            actuators=[dict(id='shared',limits=[-.1,.1],velocity_limit=10.,units='m',transmission=[])],
            tendons=[dict(entity='positive',kp_n_m=100.,pretension_n=0.,force_limit_n=10.),
                     dict(entity='negative',kp_n_m=100.,pretension_n=0.,force_limit_n=10.)])
        plan=dict(reference=dict(desired_tensions_n=[1.,0.],requested_tensions_n=[1.,0.],
            force_limit_saturated=[False,False],commands={},target_world_m=None))
        controller=Controller(Control(mode='tension_reference',desired_tendon_tensions_n=[1.,0.]),.01)
        controller.configure(p,plan)
        g=dict(lengths=np.array([1.,1.]),tip=np.zeros(3),Jtip=np.zeros((3,0)),Jlength=np.zeros((2,0)))
        target=controller.command(0.,g,np.zeros(0),np.zeros(0))
        self.assertEqual(len(controller.u),1)
        self.assertLess(controller.u[0],0.)
        self.assertLess(target[0],1.);self.assertGreater(target[1],1.)
        self.assertTrue(controller.last['tension_command_unrealizable'][0])
        self.assertFalse(controller.last['tension_command_unrealizable'][1])


if __name__=='__main__': unittest.main()
