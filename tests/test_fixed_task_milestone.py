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
    def test_diagnostic_rollout_must_have_the_same_source(self):
        from tools.research_core_numerics import offline_diagnostic
        request=dict(candidate={},store_root='unused',source_mechanics={'artifact_id':'a'*64},
            diagnostic_parameters={'rollout_reference':{'artifact_id':'b'*64}})
        store=SimpleNamespace(artifact=lambda ref:dict(source_mechanics={'artifact_id':'c'*64},rollout=dict(failure=None)))
        with patch('tools.platform_store.Store',return_value=store):
            with self.assertRaisesRegex(ValueError,'MATCHED_COMPLETE_FIXED_SCHEDULE'):
                offline_diagnostic(request)
