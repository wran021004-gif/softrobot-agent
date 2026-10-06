from unittest import TestCase
from copy import deepcopy
from pathlib import Path
from tools.state_io import read
from extensions.optimization.ipopt import _FeasibleIterate
from extensions.optimization.contracts import FeasibleReturnPolicy
from extensions.tendon_family.gvs_bounded_nmpc import BoundedReachNMPCController
from tools.platform_registry import registry
import casadi as ca
import time

class ControlSuccessorTests(TestCase):
    def test_diagnostic_cap_without_changing_default_timed_policy(self):
        cb=_FeasibleIterate(1,0);args=[ca.DM([0]) if n=='x' else ca.DM(1) if n=='f' else ca.DM([]) for n in cb.names]
        bounds=([-1],[1],[],[])
        cb.reset(*bounds,time.perf_counter(),policy=FeasibleReturnPolicy(),seed_objective=1.)
        self.assertEqual(cb.eval(args),[0]);self.assertIsNone(cb.stop_reason)
        cb.reset(*bounds,time.perf_counter(),seed_objective=1.,work_cap=1)
        self.assertEqual(cb.eval(args),[0]);self.assertEqual(cb.eval(args),[1]);self.assertEqual(cb.stop_reason,'diagnostic_work_cap')

    def test_v8_registration_and_reject_unbounded_recipe(self):
        reg=registry();v7=reg.get('controller.gvs_nmpc','7.0.0','controller');v8=reg.get('controller.gvs_nmpc','8.0.0','controller')
        self.assertEqual(v7.binding,'extensions.tendon_family.gvs_nmpc:DeadlineReachNMPCController')
        self.assertNotEqual(v7.binding,v8.binding)
        root=Path(__file__).resolve().parents[1]
        p=deepcopy(read(root/'evidence/milestone5_matched_20261006/protocol.json')['candidates'][0]['configuration']['policy']['controller']['parameters']['data'])
        with self.assertRaisesRegex(ValueError,'V8_FROZEN'):BoundedReachNMPCController(p,.01)
        p['recipe'].update(horizon=2,max_iterations=2,max_cpu_s=1.,feasible_return=dict(minimum_s=.001,budget_s=.005,relative_improvement=.1))
        c=BoundedReachNMPCController(p,.01);self.assertTrue(c.parameters.regenerate_warm_states)

    def test_saved_time_alignment_and_budget_rules(self):
        from examples.milestone_bound_successor import M5
        d=read(M5/'saved_diagnosis_corrected.json')
        first=d['cases'][0]['rows'][0];self.assertEqual(first['full_state_linf'],0.)
        self.assertLess(d['cases'][0]['rows'][2]['full_state_linf'],1e-10)
        p=read(M5/'protocol.json');self.assertEqual(p['local_numerical_protocol']['version'],'fixed_backend_transition_validation@2.0.0')
        self.assertEqual(sum(v['limit']['backend_solves'] for v in p['protected_validation']),6)
        self.assertEqual(p['thresholds']['complete_control_update_deadline_s'],.01)

    def test_full_history_dispatch_cannot_silently_run_v7_for_v8(self):
        from extensions.tendon_family.milestone5_feedback_runtime import bound_controller
        from examples.milestone_bound_successor import M5
        from schemas.platform import SessionInput
        inp=SessionInput.model_validate(read(M5/'measure8_original075.json')['configuration'])
        self.assertIsInstance(bound_controller(inp),BoundedReachNMPCController)
