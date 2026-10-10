"""Focused replay and frozen-interface regressions; no optimizer invocation."""
from types import SimpleNamespace
import unittest
import casadi as ca
import numpy as np
from extensions.tendon_family.gvs_codesign import integrate
from tools.casadi_codesign_service import specification
from tools.platform_registry import registry


class CasadiCodesignTests(unittest.TestCase):
    def test_existing_analysis_tuple_and_fixed_linearizer(self):
        from tests.test_gvs_casadi import GVSCasadiTests
        GVSCasadiTests.setUpClass()
        f=GVSCasadiTests.functions
        x,u,xdot=f._linearization_symbols
        self.assertEqual((x.numel(),u.numel(),xdot.numel()),(16,6,16))
        A,B,drift=f.linearize(np.zeros(16),np.full(6,.2))
        self.assertEqual(A.shape,(16,16))
        self.assertEqual(B.shape,(16,6))
        self.assertTrue(np.isfinite(drift).all())

    def test_replay_uses_zero_state_and_continuity_at_switches(self):
        # Analytic double integrator isolates replay initialization/switching.
        # The deliberately false optimizer states must never reset integration.
        functions=SimpleNamespace(function=lambda x,u,d:[ca.vertcat(x[1],u[0])])
        q=ca.MX.sym('q');v=ca.MX.sym('v');d=ca.MX.sym('d')
        tip=ca.Function('test_tip',[q,d],[ca.vertcat(q,0,0)])
        velocity=ca.Function('test_speed',[q,v,d],[ca.vertcat(v,0,0)])
        u=np.r_[np.full(10,.2),np.full(25,.4)]
        candidate=dict(d=0.,states=np.tile([9.,7.],(36,1)).tolist(),
            times_s=np.linspace(0,.35,36).tolist(),tensions_n=u[:,None].tolist(),coordinate_order=['q'])
        result,trace=integrate(functions,tip,velocity,candidate,[0.,0.,0.])
        np.testing.assert_array_equal(trace['states'][0],[0.,0.])
        expected_v=.2*.1+.4*.25
        expected_q=.5*.2*.1**2+(.2*.1)*.25+.5*.4*.25**2
        np.testing.assert_allclose(trace['states'][-1],[expected_q,expected_v],atol=1e-10)
        self.assertIsNone(result['integration_failure'])
        self.assertFalse(result['gates_passed'])
        self.assertEqual(len(trace['times_s']),701)

    def test_frozen_pair_and_typed_registry(self):
        a,b=specification('A'),specification('B')
        for key in ('trajectory','normalized_objective','solver','initializations'):
            self.assertEqual(a[key],b[key])
        self.assertEqual(a['design']['normalized_decision']['bounds'],[0.,0.])
        self.assertEqual(b['design']['normalized_decision']['bounds'],[-1.,1.])
        self.assertNotIn('planned',b['mathematical_method'])
        reg=registry()
        for name in ('check','solve','replay'):
            definition=reg.get('math.casadi_codesign_'+name,'1.0.0','tool')
            self.assertTrue(callable(definition.resolve()))
