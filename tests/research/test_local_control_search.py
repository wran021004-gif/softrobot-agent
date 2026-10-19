"""Fabricated response tests; no physics or provider launches."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest
import numpy as np
from tools.research.local_control_search import search, trust_radius, SearchStopped
from tools.research.control_correction import constrained_response_step, correction_basis
from tools.research.feedback import task_gap
from tools.research.physical_replay import evaluate_schedule, schedule_identity
from tools.state_io import digest


def start(name='a',design='design'):
    return dict(id=name,limits=[8]*4,task_options=dict(target=[0,0,0],holding_start=.3,position_limit=.01,speed_limit=.02),
        schedule=dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',provenance={'fixture':True},
            trajectory=dict(times_s=[k*.01 for k in range(36)],tensions_n=[[4.]*4 for _ in range(35)],
                tendon_order=['a','b','c','d'],task_identity='task',design_identity=design,model_identity='model')))


class LocalSearchTests(unittest.TestCase):
    def evaluator(self,*,invalid=False,passes=False,reverse=False):
        self.calls=[]
        def evaluate(s,source,meta):
            u=np.asarray(source['trajectory']['tensions_n']);self.calls.append(u)
            velocity=.04+(-1 if reverse else 1)*.2*(u[-1,3]-4)
            episode=dict(complete=not invalid,holding_coverage_complete=True,numerical_failure=None,
                terminal_position_error_m=0.,holding_max_position_error_m=0.,holding_max_speed_m_s=abs(velocity))
            result=dict(independent_evaluation_executed=True,episodes=[episode],passed=passes or abs(velocity)<=.02,
                acceptance=dict(terminal_position_limit_m=.01,position_limit_m=.01,holding_speed_limit_m_s=.02))
            return dict(reference=digest(u.tolist()),task_gap=task_gap(result),cost_s=1.,
                outputs=dict(times_s=[k*.01 for k in range(36)],tip_positions_m=[[0,0,0]]*36,
                    tip_velocities_m_s=[[velocity,0,0]]*36))
        return evaluate

    def test_response_uses_all_constraints_and_actual_pass(self):
        result=search([start()],self.evaluator(),dict(method='response',evaluation_requests=15,initial_radius_n=.2))
        self.assertEqual(result['stop_reason'],'first_original_task_pass')
        self.assertTrue(result['best']['task_gap']['accepted'])
        self.assertLessEqual(len(self.calls),15)
        self.assertTrue(all(np.min(u)>=0 and np.max(u)<=8 for u in self.calls))

    def test_pattern_finds_descent_deterministically(self):
        result=search([start()],self.evaluator(),dict(method='pattern',evaluation_requests=4,initial_radius_n=.2))
        self.assertEqual(result['stop_reason'],'first_original_task_pass')
        self.assertEqual(len(self.calls),3)

    def test_first_pass_stops_even_remaining_starts(self):
        result=search([start(),start('b')],self.evaluator(passes=True),{})
        self.assertEqual(len(self.calls),1);self.assertTrue(result['best']['task_gap']['accepted'])

    def test_invalid_start_gets_no_rankable_gap(self):
        result=search([start()],self.evaluator(invalid=True),{})
        self.assertIsNone(result['best']);self.assertIsNone(result['candidates'][0]['task_gap']['normalized_gap'])
        self.assertEqual(result['stop_reason'],'no_valid_start')

    def test_finite_budget_includes_derivative_probes(self):
        result=search([start()],self.evaluator(),dict(evaluation_requests=3))
        self.assertEqual(len(self.calls),3);self.assertEqual(result['stop_reason'],'evaluation_request_budget')

    def test_model_adverse_prediction_does_not_veto_evaluation(self):
        with patch('tools.research.local_control_search.constrained_response_step',return_value=dict(
                success=True,delta=np.zeros(12),predicted_gap=5.,numerical_status='fixture')):
            result=search([start()],self.evaluator(),dict(evaluation_requests=14))
        proposed=result['candidates'][-1]
        self.assertEqual(proposed['label'],'local_response_proposal')
        self.assertLess(proposed['predicted_improvement'],0)
        self.assertLess(proposed['next_trust_radius_n'],proposed['trust_radius_n'])

    def test_prediction_failure_shrinks_region(self):
        self.assertEqual(trust_radius(.1,1,-1,2),.05)
        self.assertEqual(trust_radius(.1,1,.1,2),.05)
        self.assertAlmostEqual(trust_radius(.1,1,1,2),.15)

    def test_multistart_keeps_designs_and_checks_task(self):
        evaluate=self.evaluator();seen=[]
        def capture(s,source,meta):
            seen.append((s['id'],source['trajectory']['design_identity']));return evaluate(s,source,meta)
        search([start(),start('b','different')],capture,dict(evaluation_requests=2))
        self.assertEqual(seen,[('a','design'),('b','different')])
        b=start('b');b['schedule']['trajectory']['task_identity']='other'
        with self.assertRaisesRegex(ValueError,'COMPARABLE'):search([start(),b],evaluate,{})

    def test_explicit_force_constraints_and_epigraph(self):
        y=np.array([[2.,0,0],[0,2.,0]]);jac=np.zeros((2,3,2));jac[0,0,0]=1;jac[1,1,1]=1
        r=constrained_response_step(y,jac,[0,0],[[.2,.2]],np.eye(2),[8,8],1.,2.)
        self.assertTrue(r['success']);self.assertTrue(np.all(r['delta']>=-.20000001))
        self.assertAlmostEqual(r['predicted_gap'],.8,places=6)
        self.assertFalse(r['global_optimality_proved'])

    def test_solver_failure_is_not_structural_exclusion(self):
        with patch('tools.research.local_control_search.constrained_response_step',return_value=dict(success=False,numerical_status='fixture failure')):
            result=search([start()],self.evaluator(),dict(evaluation_requests=20))
        self.assertTrue(result['stop_reason'].startswith('numerical_failure'))
        self.assertIn('infeasibility remains unknown',result['interpretation'])

    def test_callback_store_limit_stops_without_swallowing_other_errors(self):
        def exhausted(*args):raise SearchStopped('Store backend ceiling')
        self.assertEqual(search([start()],exhausted,{})['stop_reason'],'Store backend ceiling')
        with self.assertRaisesRegex(ValueError,'binding'):
            search([start()],Mock(side_effect=ValueError('binding')), {})

    def test_basis_matches_interpolation(self):
        b=correction_basis([0,.1,.2],[0,.1,.2],4)
        np.testing.assert_array_equal(b,np.eye(12))


class StoreReuseTests(unittest.TestCase):
    def test_settled_result_recovered_without_dispatch_or_budget_change(self):
        cfg=dict(robot={'id':'r'},task={'id':'t'},seed=17,policy={k:{} for k in ('backend','discretization','dynamics_model')})
        source=start()['schedule'];result=dict(candidate='c',source_reference='s',charged_numerical_s=2.)
        store=Mock();store.artifact.side_effect=lambda ref:{'r':result,'s':source,'c':{'configuration':cfg}}[ref]
        host=SimpleNamespace(store=store)
        with patch('tools.research.physical_replay.verify_candidate',return_value={'configuration':cfg}),patch(
                'tools.research.physical_replay.binding'),patch('tools.research.physical_replay.state',return_value={'physical_replays':['r']}),patch(
                'tools.research.core.dispatch') as dispatch:
            recovered,cached=evaluate_schedule(host,'c',deepcopy(source),Mock())
        self.assertTrue(cached);self.assertEqual(recovered['charged_numerical_s'],2.)
        dispatch.assert_not_called();store.reserve.assert_not_called()

    def test_exact_sequence_and_design_change_identity(self):
        cfg=dict(robot={},task={},seed=17,policy={k:{} for k in ('backend','discretization','dynamics_model')})
        tr=start()['schedule']['trajectory'];key=schedule_identity(cfg,tr)
        tr['tensions_n'][0][0]=np.nextafter(4.,5.)
        self.assertNotEqual(key,schedule_identity(cfg,tr))
        tr=start()['schedule']['trajectory'];cfg['robot']={'id':'changed'}
        self.assertNotEqual(key,schedule_identity(cfg,tr))


if __name__=='__main__':unittest.main()
