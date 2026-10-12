"""Budget boundaries use watchdogs and activity time without scientific dispatch."""
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from tools import research_core as core
from tools.state_io import digest


class AdmissionTests(TestCase):
    def setUp(self):
        self.state=dict(spec=dict(mode='engineering_numerical',require_configuration_cost_estimate=True,budgets=dict(numerical_s=28800,delivery_reserve_s=1800),
            execution_allowances=dict(simulation_s=8500),mechanics_allowances=dict(replay_s=450),
            execution_required_integrations=1),numerical_s=0.,numerical_reserved_s=0.,
            cutoff_unix=50000.,profile=dict(recipe=dict(max_iterations=6,horizon=10,substeps=16)),
            execution_cost_estimate=dict(recipe_identity=digest(dict(max_iterations=6,horizon=10,substeps=16)),total_watchdog_s=9000))
        self.host=SimpleNamespace(store=SimpleNamespace(remaining=lambda:dict(remaining=dict(backend_solves=4,tool_calls=100,wall_s=43200))))

    def admission(self):
        with patch.object(core,'state',return_value=self.state),patch.object(core.time,'time',return_value=10000):
            return core.capacity(self.host)

    def test_development_requires_execution_repetition_and_integration(self):
        self.state['numerical_s']=28800-18000-449
        self.assertEqual(self.admission()['admitted'],0)
        self.state['numerical_s']-=1
        self.assertEqual(self.admission()['admitted'],1)
        self.assertEqual(self.admission()['confirmation_time_reserve_s'],9000)

    def test_activity_budget_separately_protects_delivery_and_integration(self):
        self.state.update(numerical_reserved_s=450,validation_reservation=dict(seconds=450))
        self.state['cutoff_unix']=10000+18000+449
        self.assertEqual(self.admission()['admitted'],0)
        self.state['cutoff_unix']+=1
        self.assertEqual(self.admission()['admitted'],1)
        self.assertEqual(self.admission()['delivery_activity_reserve_s'],1800)

    def test_changed_iterations_horizon_or_resolution_invalidates_estimate(self):
        for name in ('max_iterations','horizon','substeps'):
            changed=deepcopy(self.state);changed['profile']['recipe'][name]+=1
            with patch.object(core,'state',return_value=changed):
                self.assertEqual(core.allowance(changed),8500)
                candidate=dict(configuration={},scientific_configuration={})
                with patch.object(core,'guard'),patch.object(core,'verify_candidate',return_value=candidate):
                    with self.assertRaisesRegex(ValueError,'REESTIMATE_REQUIRED'):
                        core.execute(self.host,{},'must-not-launch')


class FixedScheduleTests(TestCase):
    def test_local_mesh_keeps_commands_boundaries_and_transcription_matched(self):
        import casadi as ca
        import numpy as np
        from extensions.tendon_family import gvs_codesign as code
        q=ca.MX.sym('q');d=ca.MX.sym('d');x=ca.MX.sym('x',2);u=ca.MX.sym('u');acc=ca.MX.sym('acc')
        expr=SimpleNamespace(coordinate_order=['q'],tendon_order=['u'])
        functions=SimpleNamespace(q_symbol=q,design_input=d,tip_position_expression=ca.vertcat(q,0,0),
            implicit_residual=ca.Function('toy_force',[x,u,acc,d],[acc-u]))
        cfg=dict(task=dict(environment=dict(data=dict(mount=dict(quaternion_wxyz=[1,0,0,0],position_m=[0,0,0]))),
            goal=dict(data=dict(target_m=[0,0,0]))))
        counts=[1]*35;counts[29]=4
        with patch.object(code,'expression',return_value=expr),patch.object(code,'parameterized',return_value=functions):
            w=code.Workspace(cfg,integration_method='implicit_midpoint',interval_substeps=counts)
            tensions=np.arange(35)[:,None]/35
            rollout=w.rollout(tensions,0.)
            self.assertEqual(len(rollout['states']),39)
            np.testing.assert_allclose(w.times[np.r_[0,np.cumsum(counts)]],np.arange(36)*.01,atol=1e-15)
            self.assertAlmostEqual(rollout['states'][-1][1],.01*tensions.sum(),places=12)
            self.assertEqual(list(w.command_indices[29:33]),[29]*4)
            problem=w.assemble('A','saved_schedule',saved_tensions=tensions)
            f=ca.Function.deserialize(problem.objective_function.data['serialized_function'])
            outputs=f([problem.initial_guess[k] for k in problem.variables])
            residuals=np.asarray(outputs[1]).ravel()[:w.steps*2]
            self.assertLess(abs(residuals).max(),1e-7)

    def test_diagnostic_rollout_must_have_the_same_source(self):
        from tools.research_core_numerics import offline_diagnostic
        request=dict(candidate={},store_root='unused',source_mechanics={'artifact_id':'a'*64},
            diagnostic_parameters={'rollout_reference':{'artifact_id':'b'*64}})
        store=SimpleNamespace(artifact=lambda ref:dict(source_mechanics={'artifact_id':'c'*64},rollout=dict(failure=None)))
        with patch('tools.platform_store.Store',return_value=store):
            with self.assertRaisesRegex(ValueError,'MATCHED_COMPLETE_FIXED_SCHEDULE'):
                offline_diagnostic(request)
