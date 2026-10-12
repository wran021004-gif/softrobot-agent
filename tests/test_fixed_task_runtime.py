"""Cost admission must not transfer shortened-horizon speedups to early updates."""
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from tools import fixed_task_runtime as runtime


class RuntimeCostTests(TestCase):
    def setUp(self):
        self.history=[dict(time_s=0.,effective_horizon=10,update_wall_s=100.),
            dict(time_s=.1,effective_horizon=10,update_wall_s=100.),
            dict(time_s=.29,effective_horizon=6,update_wall_s=60.),
            dict(time_s=.34,effective_horizon=1,update_wall_s=10.)]

    def test_shortened_horizon_speedup_cannot_reduce_early_cost(self):
        measured=[dict(time_s=.1,effective_horizon=10,update_wall_s=150.),
            dict(time_s=.29,effective_horizon=6,update_wall_s=30.)]
        result=runtime.stratified_cost(self.history,measured,10)
        self.assertEqual(result['full_horizon_ratio'],1.5)
        self.assertEqual(result['shortened_horizon_ratio'],1.)
        self.assertEqual([r['predicted_s'] for r in result['per_update_estimates']],[150.,150.,60.,10.])

    def test_cold_start_is_separate_and_deadline_horizon_must_match(self):
        measured=[dict(time_s=0.,effective_horizon=10,update_wall_s=300.),
            dict(time_s=.1,effective_horizon=10,update_wall_s=100.)]
        result=runtime.stratified_cost(self.history,measured,10)
        self.assertEqual([r['predicted_s'] for r in result['per_update_estimates']],[300.,100.,60.,10.])
        wrong=deepcopy(measured);wrong[1]['effective_horizon']=6
        with self.assertRaisesRegex(ValueError,'EFFECTIVE_HORIZON'):runtime.stratified_cost(self.history,wrong,10)

    def test_active_reservation_cannot_be_changed_by_prospective_estimate(self):
        state=dict(pending=dict(owner='live'),execution_cost_estimate=dict(total_watchdog_s=4858))
        with patch.object(runtime.core,'state',return_value=state),patch.object(runtime.core,'save') as save,patch.object(runtime.core,'update') as update:
            with self.assertRaisesRegex(ValueError,'SETTLE_ACTIVE'):runtime.record_cost(SimpleNamespace(),{},apply=True)
            save.assert_not_called();update.assert_not_called()
            runtime.record_cost(SimpleNamespace(),{},apply=False)
            self.assertNotIn('execution_cost_estimate',update.call_args.kwargs)
