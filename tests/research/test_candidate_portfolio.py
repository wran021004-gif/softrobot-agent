"""Synthetic fixtures only: no simulator, MATLAB or archive loads."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import numpy as np
from tools.research.holding_diagnostic import applied_schedule
from tools.research.candidate_portfolio import portfolio, ranking_key, compatible_schedule


class CandidatePortfolioTests(unittest.TestCase):
    def setUp(self):
        self.options=dict(phase='post_control_interval',period=.01,timestep=.0005,
            intervals=35,order=['a','b','c','d'],expected_order=['a','b','c','d'],limits=[8]*4)
        self.rows=[dict(time_s=(k+1)*.01,control_start_s=k*.01,control_update_index=k,
            actual_tension_n=[k/10,1,2,3],valid_plan=k!=34,fallback=k==34) for k in range(35)]

    def test_fallback_is_actual_input_not_a_plan(self):
        u=applied_schedule(self.rows,**self.options)
        self.assertEqual(len(u),35);self.assertEqual(u[-1],[3.4,1,2,3])

    def test_initial_row_is_not_an_action(self):
        initial=dict(time_s=0,control_update_index=-1,actual_tension_n=[0]*4)
        self.assertEqual(applied_schedule([initial,*self.rows],**self.options),applied_schedule(self.rows,**self.options))

    def test_missing_duplicate_shifted_index_and_start_rejected(self):
        for field,value in [('time_s',.012),('control_update_index',1),('control_start_s',.001),
                ('time_s',float('nan')),('control_start_s',float('nan')),('engine_time_s',.1),('engine_time_s',float('nan'))]:
            rows=deepcopy(self.rows);rows[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):applied_schedule(rows,**self.options)
        with self.assertRaises(ValueError):applied_schedule(self.rows[:-1],**self.options)

    def test_order_phase_nonfinite_bounds(self):
        for changes in [dict(order=['b','a','c','d']),dict(phase='pre_step')]:
            with self.assertRaises(ValueError):applied_schedule(self.rows,**{**self.options,**changes})
        for bad in [float('nan'),float('inf'),-1,8.01]:
            rows=deepcopy(self.rows);rows[0]['actual_tension_n'][0]=bad
            with self.assertRaises(ValueError):applied_schedule(rows,**self.options)

    def test_dense_physics_steps_require_constant_held_actions(self):
        rows=[dict(time_s=(k+(j+1)/20)*.01,control_update_index=k,
            actual_tension_n=[k/10,1,2,3]) for k in range(35) for j in range(20)]
        opts={**self.options,'phase':'post_physics_step'}
        self.assertEqual(applied_schedule(rows,**opts),applied_schedule(self.rows,**self.options))
        rows[5]['actual_tension_n'][0]+=.001
        with self.assertRaisesRegex(ValueError,'NONCONSTANT'):applied_schedule(rows,**opts)

    def test_commanded_action_must_equal_applied(self):
        self.rows[0]['commanded_tension_n']=[0]*4
        with self.assertRaisesRegex(ValueError,'COMMAND_APPLIED'):applied_schedule(self.rows,**self.options)

    def row(self,name,position,speed,gap,valid=True,passed=False,task='same'):
        return dict(source_result=name,task_identity=task,metric_identity='limits',
            metrics=dict(terminal_position_error_m=position,holding_max_position_error_m=position,holding_max_speed_m_s=speed),
            task_gap=dict(normalized_gap=gap,components=dict(p=position,v=speed),valid_complete=valid,accepted=passed))

    def test_validity_and_acceptance_precede_residual(self):
        rows=[self.row('invalid',0,0,0,False,True),self.row('valid',2,2,100),self.row('pass',3,3,200,True,True)]
        self.assertEqual([r['source_result'] for r in sorted(rows,key=ranking_key)],['pass','valid','invalid'])

    def test_pareto_and_task_partitions(self):
        rows=[self.row('position',1,3,2),self.row('speed',3,1,2),self.row('dominated',4,4,3),self.row('other',0,0,0,task='different')]
        groups=portfolio(rows)['groups'];self.assertEqual(len(groups),2)
        group=next(g for g in groups if len(g['ranked'])==3)
        self.assertEqual(set(group['position_speed_pareto']),{'position','speed'})

    def test_unavailable_and_changed_design_do_not_transfer(self):
        with self.assertRaisesRegex(ValueError,'REPLAY_UNAVAILABLE'):
            compatible_schedule(dict(replay_status='replay_unavailable'),{})
        with self.assertRaisesRegex(ValueError,'ROBOT_OR_TASK'):
            compatible_schedule(dict(replay_status='pending_independent_replay',robot_identity='other'),dict(robot={},task={}))

    def test_same_robot_changed_integrator_or_seed_does_not_transfer(self):
        from tools.research.physical_replay import schedule_identity
        from tools.state_io import digest
        from tests.research.test_local_control_search import start
        cfg=dict(robot={},task={},seed=17,policy={k:{} for k in ('backend','discretization','dynamics_model')})
        schedule=start()['schedule']
        row=dict(replay_status='pending_independent_replay',robot_identity=digest({}),task_identity=digest({}),
            bound_schedule_identity=schedule_identity(cfg,schedule['trajectory']),schedule=schedule)
        with patch('tools.research.physical_replay.binding'):
            self.assertEqual(compatible_schedule(row,cfg),schedule)
        for field in ('seed','backend','discretization'):
            changed=deepcopy(cfg)
            if field=='seed':changed[field]=18
            else:changed['policy'][field]={'changed':True}
            with self.assertRaisesRegex(ValueError,'PHYSICAL_MODEL_OR_SEED'):compatible_schedule(row,changed)


if __name__=='__main__':unittest.main()
