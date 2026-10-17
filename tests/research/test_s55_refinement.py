"""Frozen-grid and incomplete-root boundaries for S5.5 fixed-input refinement."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.platform_host import Host
from tools.research.contracts import Plan
from extensions.tendon_family.sorosim_codesign import refine_fixed_sequence, calculate, compare_refinements


ROOT=Path(__file__).resolve().parents[2]
STUDY='sorosim-s5-agent-feedback-20261016'
CANDIDATE={'artifact_id':'47cb1f9ece26104d21d836c8068bdc4852b764cb186e5b53b7ea53f7f2793b3d',
    'media_type':'application/json'}
SOURCE={'artifact_id':'45815dc9cbf9266b3406a91657d1f9d7a163ac96557a5a4dce750d41f16780f9',
    'media_type':'application/json'}


class RefinementBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host=Host(ROOT/'runs/research'/STUDY,STUDY)
        cls.configuration=host.store.artifact(CANDIDATE)['configuration']
        cls.source=host.store.artifact(SOURCE)

    def test_typed_substeps_and_frozen_grid(self):
        plan=dict(action='refine',refinement=dict(candidate=CANDIDATE,source=SOURCE,substeps=4),
            hypothesis='frozen-grid fixture',expected_observation='root output',
            weakening_observation='root failure',fixed_conditions='same 35 inputs',
            stopping_condition='one bounded attempt',interpretation='test only')
        self.assertEqual(Plan.model_validate(plan).refinement.substeps,4)
        for count in (16,32,64):
            plan['refinement']['substeps']=count
            self.assertEqual(Plan.model_validate(plan).refinement.substeps,count)
        plan['refinement']['substeps']=3
        with self.assertRaises(ValueError):Plan.model_validate(plan)
        self.assertEqual(len(self.source['trajectory']['tensions_n']),35)
        self.assertEqual(len(self.source['trajectory']['times_s']),36)
        changed=deepcopy(self.source)
        changed['trajectory']['times_s'][20]+=.0001
        with self.assertRaisesRegex(ValueError,'REFINEMENT_GRID_OR_INITIAL_STATE_MISMATCH'):
            refine_fixed_sequence(self.configuration,CANDIDATE,changed,4)

    def test_failed_root_is_not_task_success(self):
        source=self.source
        class Session:
            environment={}
            dependency={}
            timings={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def construct(self,spec):pass
            def evaluate(self,operation,request):
                assert operation=='diagnose' and request['kind']=='fixed_sequence'
                assert request['substeps']==2 and len(request['tensions_n'])==35
                assert len(request['times_s'])==36
                return dict(status='root_failed',complete=False,initial_state=request['x'],
                    states=[request['x']],failed_root=dict(interval=1,substep=1,residual_inf=.1))
        with patch('extensions.tendon_family.sorosim_codesign.SorosimSession',Session):
            result=refine_fixed_sequence(self.configuration,CANDIDATE,source,2)
        self.assertFalse(result['complete'])
        self.assertFalse(result['original_task_satisfied'])
        self.assertEqual(result['raw']['failed_root']['interval'],1)

    def test_comparison_uses_velocity_vectors_and_exact_times(self):
        row=dict(complete=True,times_s=[0.,.01,.14,.16,.25,.29,.30,.35],
            tip_positions_m=[[0.,0.,0.]]*8,tip_velocities_m_s=[[1.,0.,0.]]*8)
        other=deepcopy(row);other['tip_velocities_m_s']=[[0.,1.,0.]]*8
        self.assertAlmostEqual(compare_refinements(row,other)['maximum_velocity_m_s'],2**.5)
        other['times_s'][-1]+=.0001
        with self.assertRaisesRegex(ValueError,'IDENTICAL_OUTPUT_GRIDS'):
            compare_refinements(row,other)

    def test_full_warm_trajectory_is_candidate_bound(self):
        captured=[]
        class Session:
            environment={}
            dependency={}
            timings={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def construct(self,spec):pass
            def evaluate(self,operation,request):
                captured.append(request)
                return dict(status='check_only')
        warm=deepcopy(self.source['trajectory'])
        request=dict(configuration=self.configuration,design_candidate=CANDIDATE,
            operation='solve',check_only=True,warm_trajectory=warm,
            arguments=dict(substeps=1,initialization='saved_candidate_trajectory',
                objective_mode='task_capability',position_weight=1.,speed_weight=1.,
                secondary_coefficient=0.))
        with patch('extensions.tendon_family.sorosim_codesign.SorosimSession',Session):
            calculate(request)
        self.assertEqual(captured[0]['warm_trajectory']['states'],warm['states'])
        self.assertEqual(captured[0]['warm_trajectory']['slacks'],warm['slacks'])
        wrong=deepcopy(request);wrong['warm_trajectory']['model_identity']='different'
        with self.assertRaisesRegex(ValueError,'CODESIGN_WARM_IDENTITY_MISMATCH'):
            calculate(wrong)

    def test_saved_controls_rematerialize_without_copying_coarse_states(self):
        captured=[]
        class Session:
            environment={};dependency={};timings={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def construct(self,spec):pass
            def evaluate(self,operation,request):
                captured.append(request);return dict(status='check_only')
        request=dict(configuration=self.configuration,design_candidate=CANDIDATE,
            operation='solve',check_only=True,warm_trajectory=self.source['trajectory'],
            arguments=dict(substeps=4,initialization='saved_candidate_controls',
                objective_mode='maximum_original_violation',position_weight=1.,speed_weight=1.,
                secondary_coefficient=0.,max_iterations=60))
        with patch('extensions.tendon_family.sorosim_codesign.SorosimSession',Session):calculate(request)
        self.assertNotIn('warm_trajectory',captured[0])
        self.assertEqual(captured[0]['control']['initial_tensions'],self.source['trajectory']['tensions_n'])
        self.assertEqual(captured[0]['control']['recipe']['substeps'],4)
        self.assertEqual(len(captured[0]['control']['initial_tensions']),35)
        changed=deepcopy(request);changed['warm_trajectory']['tendon_order'].reverse()
        with self.assertRaisesRegex(ValueError,'WARM_IDENTITY_MISMATCH'):
            calculate(changed)

    def test_physical_intervention_changes_one_controller_factor(self):
        from tools.research.config import resolve
        old=resolve(ROOT/'configs/research/study_sorosim_s5_nmpc.json')['configuration']
        new=resolve(ROOT/'configs/research/study_sorosim_s56_physics.json')['configuration']
        self.assertEqual(old['task'],new['task'])
        a=old['policy']['controller']['parameters']['data']['recipe']
        b=new['policy']['controller']['parameters']['data']['recipe']
        self.assertEqual([k for k in a if a[k]!=b[k]],['holding_brake_lead_s'])
        self.assertEqual(b['holding_brake_lead_s'],.02)


if __name__=='__main__':unittest.main()
