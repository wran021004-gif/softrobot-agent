"""Small mathematical checks for the explicitly sampled controller path."""
import unittest
import numpy as np
from examples.platform_tendon_family import example_design
from extensions.tendon_family.compiler import resolve
from extensions.tendon_family.contracts import LQRParameters
from extensions.tendon_family.gvs_basis import resolve_basis
from extensions.tendon_family.gvs_projection import cell_average_basis, discretize, project, LEGACY_PROJECTOR_ID
from extensions.tendon_family.gvs_sampled import zero_order_hold, DiscreteLQRController
from schemas.platform import SignalSpec
from schemas.platform_math import LinearizedModel


class SampledMath(unittest.TestCase):
    def test_mujoco_velocity_reset_is_numerical_failure(self):
        import mujoco
        from extensions.tendon_family.backends import _mujoco_state_failed
        model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><joint type="hinge"/><geom type="sphere" size=".1"/></body></worldbody></mujoco>')
        data=mujoco.MjData(model)
        before=data.time;mujoco.mj_step(model,data)
        self.assertFalse(_mujoco_state_failed(data,before))
        data.qvel[0]=1e20;before=data.time;mujoco.mj_step(model,data)
        self.assertTrue(np.isfinite(data.qpos).all())
        self.assertTrue(np.isfinite(data.qvel).all())
        self.assertGreater(data.warning[mujoco.mjtWarning.mjWARN_BADQVEL].number,0)
        self.assertTrue(_mujoco_state_failed(data,before))

    def test_small_angle_pose_against_matrix_exponential(self):
        import casadi as ca
        from scipy.linalg import expm
        from extensions.tendon_family.gvs_casadi import _segment_pose
        q=ca.MX.sym('q',2);pose=ca.Function('small_pose',[q],[_segment_pose(.006,q[0],q[1])])
        jac=ca.Function('small_pose_jac',[q],[ca.jacobian(ca.reshape(pose(q),16,1),q)])
        def trusted(k):
            twist=np.array([[0.,-k[1],k[0],1.],[k[1],0.,0.,0.],[-k[0],0.,0.,0.],[0.,0.,0.,0.]])
            return expm(.006*twist)
        for k in (np.zeros(2),np.array([1e-6,-2e-6]),np.array([.05,.03])):
            np.testing.assert_allclose(pose(k),trusted(k),atol=1e-14)
            fd=np.column_stack([((trusted(k+e*1e-4)-trusted(k-e*1e-4))/(2e-4)).reshape(-1,order='F') for e in np.eye(2)])
            np.testing.assert_allclose(jac(k),fd,atol=1e-12)

    def test_singular_zoh_affine_and_discrete_feedback(self):
        state=SignalSpec(name='position',entity='x',dimension=1,units='m',frame='world',phase='continuous')
        control=SignalSpec(name='tension',entity='t',dimension=1,units='N',frame='path',phase='continuous')
        model=LinearizedModel(state_definition=[state],input_definition=[control],output_definition=[],
            x0=[0.],u0=[0.],A=[[0.]],B=[[2.]],drift=[3.],time_domain='continuous')
        sampled=zero_order_hold(model,.01)
        np.testing.assert_allclose(sampled.A,[[1.]])
        np.testing.assert_allclose(sampled.B,[[.02]])
        np.testing.assert_allclose(sampled.drift,[.03])
        controller=DiscreteLQRController(LQRParameters(Q=[[1.]],R=[[1.]],tendon_order=['t'],force_limits_n=[8.]))
        with self.assertRaisesRegex(ValueError,'NOT_EQUILIBRIUM'): controller.configure_model(sampled)
        controller.configure_model(sampled.model_copy(update={'drift':[0.]}))
        self.assertLess(controller.spectral_radius,1.)

    def test_integrated_knot_crossing_round_trip(self):
        design=example_design();basis=resolve_basis(design,{'strategy':'structural_linear'})
        local=basis.segments[0]
        np.testing.assert_allclose(cell_average_basis(basis,local,1/3,2/3)[0,:3],[1/12,5/6,1/12],atol=1e-14)
        physics=resolve(design,{'cells':{s.segment:3 for s in basis.segments}})
        q=np.linspace(-.4,.5,basis.dimension);v=q/10
        state=project(physics,basis,*discretize(physics,basis,q,v))
        np.testing.assert_allclose(state['q_gvs'],q,atol=1e-12)
        np.testing.assert_allclose(state['qdot_gvs'],v,atol=1e-12)
        legacy=discretize(physics,basis,q,v,convention=LEGACY_PROJECTOR_ID)
        np.testing.assert_allclose(project(physics,basis,*legacy,convention=LEGACY_PROJECTOR_ID)['q_gvs'],q,atol=1e-12)


if __name__=='__main__':unittest.main()
