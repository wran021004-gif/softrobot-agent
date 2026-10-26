"""Fabricated boundary fixtures only; no scientific integration."""
from pathlib import Path
from unittest.mock import patch
import unittest

import mujoco
import numpy as np

from examples import bf_benchmark_search as bf
from tools.state_io import read
from tests.research.test_b2_fixed_search import fixture_directory


class BenchmarkDriverTests(unittest.TestCase):
    def setUp(self):
        self.plan=read(bf.b2.ROOT/'configs/research/bf1_multidirectional_screen_v1.json')
        self.candidate=dict(label='fixture',generation=dict(segment_count=2,tendon_count=6,
            spans=[dict(last_segment=1,count=6,radius_m=.018)]))

    def test_all_conditions_keep_generated_structure_and_legal_sequence(self):
        with patch.object(mujoco,'mj_step',side_effect=AssertionError('zero integration')):
            rows=bf.configurations(self.plan,self.candidate)
            self.assertEqual(len(rows),3)
            for _,cfg in rows:
                self.assertEqual(len(cfg['robot']['structure']['data']['tendons']),6)
                _,_,_,_,context=bf.b2.prepared(cfg,self.plan,.2)
                bf.binding(cfg,context['schedule']['trajectory'])

    def test_short_initialization_uses_original_solver_without_inherited_control(self):
        cfg=bf.configurations(self.plan,self.candidate)[0][1]
        response=dict(step_consistency_passed=True,baseline=dict(tip_position_m=[.30,0.,.15]),
            position_input_jacobian_m_n=(np.ones((3,6))*.001).tolist())
        with fixture_directory() as folder, \
                patch.object(mujoco,'mj_step',side_effect=AssertionError('zero integration')), \
                patch.object(bf,'input_response',return_value=response), \
                patch.object(bf.NativeModel,'rollout',return_value=dict(tip_position_m=[.30,0.,.15])):
            seed=bf.initialized(cfg,self.plan,.2,Path(folder))
            self.assertEqual(len(seed),6)
            self.assertTrue(all(0<=x<=8 for x in seed))
            saved=read(Path(folder)/'seed.json')
            self.assertEqual(saved['cost']['physics_step_attempts'],0)

    def test_independent_failed_condition_retains_original_components(self):
        cfg=bf.configurations(self.plan,self.candidate)[-1][1]
        _,_,_,_,context=bf.b2.prepared(cfg,self.plan,.2)
        raw=dict(status='completed',physics_steps=700,tendon_order=context['schedule']['trajectory']['tendon_order'],
            samples=[dict(time_s=k*.01,tip_m=[0.,0.,0.],tip_velocity_m_s=[0.,0.,0.],
                speed_m_s=0.,actual_tension_n=[.2]*6) for k in range(36)])
        with fixture_directory() as folder, \
                patch.object(mujoco,'mj_step',side_effect=AssertionError('zero integration')), \
                patch.object(bf,'playback_tensions',return_value=raw):
            result=bf.independent(cfg,context['schedule'],Path(folder))
            self.assertEqual(result['acceptance']['status'],'valid_failure')
            self.assertFalse(result['acceptance']['components']['holding_position']['passed'])
            self.assertTrue(result['acceptance']['sources']['profile']['artifact_id'])


if __name__=='__main__':unittest.main()
