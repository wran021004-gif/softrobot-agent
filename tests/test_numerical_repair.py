"""Focused policy, integrator and admission checks without scientific launches."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import casadi as ca
import numpy as np
from extensions.tendon_family.contracts import GVSTrajectoryParameters
from extensions.tendon_family.gvs_trajectory import implicit_step_residual,TrajectoryWorkspace
from schemas.casadi_feedback import Candidate
from tools import numerical_repair as repair


class RepairTests(TestCase):
    def test_midpoint_force_balance_is_second_order_and_shared(self):
        x=ca.MX.sym('x',2);u=ca.MX.sym('u');a=ca.MX.sym('a')
        force=ca.Function('oscillator',[x,u,a],[a+4*x[0]-u])
        residual=implicit_step_residual(SimpleNamespace(implicit_residual=force),1,1,.01,'implicit_midpoint')
        # Exact algebraic midpoint for q''=-4q. This tests physical midpoint,
        # both q/v scales, and shared residual independently of implementation.
        old=np.array([1.,0.]);h=.01
        new=np.array([(1-h*h)/(1+h*h),-4*h/(1+h*h)])
        np.testing.assert_allclose(np.asarray(residual(old,new,0)).ravel(),0,atol=1e-10)
        self.assertLess(np.linalg.norm(new-[np.cos(2*h),-2*np.sin(2*h)]),3e-6)
        self.assertEqual(Candidate(substeps=8,integration_method='implicit_midpoint').substeps,8)

    def test_research_policy_uses_real_workspace_effective_options(self):
        from tools.nmpc_settling import baseline_configuration
        from schemas.platform import SessionInput
        cfg=SessionInput.model_validate(baseline_configuration());recipe=dict(cfg.policy.controller.parameters.data['recipe'])
        recipe.update(stopping_policy='research_work_v1',max_iterations=12,max_cpu_s=5.)
        with patch('tools.platform_optimization.assemble_optimization',return_value=SimpleNamespace()):
            ws=TrajectoryWorkspace(cfg.task,cfg.robot,recipe,[0.]*24,[.2]*6,settling=cfg.policy.controller.parameters.data['settling'])
        self.assertIsNone(ws.solver.parameters.max_cpu_s);self.assertIsNone(ws.solver.parameters.max_wall_s)
        self.assertIsNone(ws.solver.parameters.feasible_return)
        self.assertEqual(ws.solver.parameters.max_iterations,12);self.assertTrue(ws.solver.parameters.retain_feasible_iterate)
        historical=GVSTrajectoryParameters.model_validate(cfg.policy.controller.parameters.data['recipe'])
        self.assertEqual(historical.stopping_policy,'historical_timed_v1');self.assertIsNotNone(historical.feasible_return)

    def test_diagnostic_and_historical_success_cannot_open_length_design(self):
        d=-.43979400623619647
        values={'old':dict(operation='solve',imported_historical_evidence=True,original_task_feasible=True,
            hard_max_normalized_violation=0.,candidate={'d':d}),
            'bdf':dict(operation='integrate',replay={'gates_passed':True},source_mechanics='old'),
            'failed':dict(fresh_execution=True,acceptance={'accepted':False},profile_identity='p')}
        host=SimpleNamespace(store=SimpleNamespace(artifact=lambda r:values[r]))
        state=dict(spec={'reference_parameters':{'d':d}},mechanics_results=['bdf'],results=['failed'],profile={'identity':'p'})
        with patch.object(repair.core,'state',return_value=state):self.assertFalse(repair.length_admission(host)['passed'])
        values['old']['imported_historical_evidence']=False
        with patch.object(repair.core,'state',return_value=state):self.assertFalse(repair.length_admission(host)['passed'])


if __name__=='__main__':
    import unittest
    unittest.main()
