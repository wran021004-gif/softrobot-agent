"""Spatial braking cost checked against directional finite-difference kinematics."""
import unittest
import casadi as ca
import numpy as np
from schemas.platform import SessionInput
from schemas.platform_math import SystemContext
from extensions.tendon_family.contracts import GVSModelParameters
from extensions.tendon_family.gvs import GVSModel
from extensions.tendon_family.gvs_casadi import functions_for, expression_from_system
from extensions.tendon_family.gvs_profile import reach_input, load_profile
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace


class BrakingTests(unittest.TestCase):
    def test_task_window_moves_fixed_inputs_without_rebuilding_graph(self):
        inp = SessionInput.model_validate(reach_input('timing-check',
            timing=dict(duration_s=.4), recipe=dict(horizon=3,holding_tip_speed_weight=100.),
            settling=dict(window_s=.04,position_limit_m=.01,speed_limit_m_s=.02)))
        nominal=load_profile()['numerical']['nominal']
        control=inp.policy.controller.parameters.data
        w=TrajectoryWorkspace(inp.task,inp.robot,control['recipe'],
            nominal['q0']+[0.]*len(nominal['q0']),nominal['u0'],settling=control['settling'])
        graph=w.problem.objective_function.data['expression_digest']
        with self.assertRaisesRegex(ValueError,'CURRENT_EXECUTION_TIME'):w._set_prediction_time(None)
        before=w._set_prediction_time(.32)
        self.assertEqual(before['holding_active'],[0.,0.,0.])
        boundary=w._set_prediction_time(.33)
        self.assertAlmostEqual(boundary['holding_start_s'],.36)
        self.assertEqual(boundary['holding_active'],[0.,0.,1.])
        self.assertEqual(w.problem.variables['holding/3']['bounds'],[1.,1.])
        after=w._set_prediction_time(.39)
        self.assertEqual(after['holding_active'],[1.,1.,1.])
        self.assertEqual(graph,w.problem.objective_function.data['expression_digest'])
        self.assertEqual(w.problem.initial_guess['holding/1'],1.)
        # Same graph, different task duration/window; lead is a cost schedule,
        # never a change to the authoritative sampled acceptance window.
        w.parameters=w.parameters.model_copy(update=dict(holding_brake_lead_s=.02))
        lead=w._set_prediction_time(.32)
        self.assertAlmostEqual(lead['braking_start_s'],.34)
        self.assertAlmostEqual(lead['holding_start_s'],.36)
        self.assertEqual(lead['holding_active'],[0.,1.,1.])
        self.assertEqual(graph,w.problem.objective_function.data['expression_digest'])
        w.parameters=w.parameters.model_copy(update=dict(holding_brake_lead_s=1.))
        self.assertEqual(w._set_prediction_time(0.)['holding_active'],[1.,1.,1.])

    def test_spatial_speed_cost_matches_finite_difference_and_keeps_constraints(self):
        inp = SessionInput.model_validate(reach_input('brake-check', recipe=dict(horizon=1)))
        nominal = load_profile()['numerical']['nominal']
        x = nominal['q0'] + [0.]*len(nominal['q0']); u = nominal['u0']
        recipe = inp.policy.controller.parameters.data['recipe']
        old = TrajectoryWorkspace(inp.task, inp.robot, recipe, x, u)
        new = TrajectoryWorkspace(inp.task, inp.robot,
            dict(recipe, terminal_tip_speed_weight=1., tip_speed_scale_m_s=.02), x, u)
        n = len(x)//2; q = np.asarray(x[:n]); v = np.linspace(-2., 3., n)
        values = dict(old.problem.initial_guess)
        for j in range(n):
            values[f'x/1/{j}'] = q[j]/new.state_scales[j]
            values[f'x/1/{j+n}'] = v[j]/new.state_scales[j+n]
        def evaluate(w):
            f = ca.Function.deserialize(w.problem.objective_function.data['serialized_function'])
            return f([values[k] for k in w.problem.variables])
        before, gb = evaluate(old); after, ga = evaluate(new)
        p = GVSModelParameters(basis=new.parameters.basis)
        f = functions_for(expression_from_system(GVSModel(p).build_system(inp.robot,p,None,
            SystemContext(x0=x,u0=u,scene=inp.task.environment))))
        tip = ca.Function('fd_tip',[f.q_symbol],[f.tip_position_expression])
        eps = 1e-4
        speed = (np.asarray(tip(q+eps*v))-np.asarray(tip(q-eps*v)))/(2*eps)
        # Rotation preserves the speed norm; translation does not affect it.
        self.assertAlmostEqual(float(after-before),float(np.sum((speed/.02)**2)),places=7)
        np.testing.assert_array_equal(ga,gb)
        self.assertEqual(old.problem.variables,new.problem.variables)
        self.assertEqual(old.parameters.terminal_tip_speed_weight,0.)


if __name__ == '__main__': unittest.main()
