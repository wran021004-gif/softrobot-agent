"""Three focused engineering-contract tests; synthetic outputs are not evidence."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import numpy as np
from tests.research import mujoco_reoptimized_structure_probe as probe
from tools.research.physical_replay import binding,evaluate_playback
from tools.research_tasks import assemble_acceptance
from tools.state_io import digest


class StructureProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.variants,cls.origin=probe.inputs()

    def test_generator_and_source_bind_each_own_zero_state(self):
        base=self.variants['d_zero'];identities=[]
        for label,item in self.variants.items():
            cfg=item['configuration'];tr=item['schedule']['trajectory']
            self.assertEqual(cfg['task'],base['configuration']['task'])
            parameters=deepcopy(base['parameters'])
            parameters['segments']['distal1']['young_pa']=probe.MODULI[label]
            self.assertEqual(item['parameters'],parameters)
            self.assertEqual(tr['tensions_n'],base['schedule']['trajectory']['tensions_n'])
            self.assertEqual(tr['tendon_order'],['near_t0','near_t1','near_t2','far_t0','far_t1','far_t2'])
            self.assertFalse(item['schedule']['provenance']['inherited_acceptance'])
            inp,physics,scene=binding(cfg,tr)
            self.assertFalse(any(scene['qpos_rad']) or any(scene['qvel_rad_s']))
            self.assertEqual(tr['design_identity'],physics['design_identity'])
            identities.append(tr['design_identity'])
        self.assertEqual(len(set(identities)),3)
        wrong=deepcopy(self.variants['d_minus']['schedule']['trajectory'])
        with self.assertRaises(ValueError):binding(self.variants['d_plus']['configuration'],wrong)

    def test_same_search_budget_no_success_early_stop(self):
        class SyntheticNative:
            limits=np.tile([0.,8.],(6,1))
            def __init__(self):self.cost=dict(rollouts=0,physics_steps=0);self.starts=[]
            def rollout_sequence(self,start,times,tensions):
                self.starts.append(start);self.cost['rollouts']+=1;self.cost['physics_steps']+=700
                speed=.01+.001*np.asarray(tensions).mean()
                return dict(times_s=times,tip_positions_m=[[.29,.035,.19]]*36,
                    tip_velocities_m_s=[[speed,0.,0.]]*36)
        for label,item in self.variants.items():
            with patch.object(probe,'atomic_json'):
                native=SyntheticNative();start=object();records=[]
                _,_,out=probe.optimize(native,start,item['schedule'],probe.options(item['configuration']),
                    probe.RUN/label/'synthetic',lambda:records.append(deepcopy(native.cost)),lambda:None)
                self.assertEqual(out['cost']['evaluation_callbacks'],26)
                self.assertEqual(out['iterations'],1)
                self.assertEqual(out['stop_reason'],'iteration_limit')
                self.assertEqual(len(records),26)
                self.assertEqual(native.cost['physics_steps'],26*700)
                self.assertTrue(all(s is start for s in native.starts))
                self.assertLess(out['initial']['signed_maximum_excess'],0.)

    def test_registered_acceptance_uses_new_backend_samples_and_no_gradient_claim(self):
        cfg=self.variants['d_zero']['configuration']
        samples=[dict(time_s=k*.01,tip_m=[.31,.035,.19],tip_velocity_m_s=[.03,0.,0.],
            speed_m_s=.03,actual_tension_n=[0.]*6) for k in range(36)]
        raw=dict(status='completed',physics_steps=700,samples=samples,
            tendon_order=self.variants['d_zero']['schedule']['trajectory']['tendon_order'])
        raw_ref=dict(artifact_id=digest(raw))
        evaluation,profile=evaluate_playback(cfg,raw,raw_ref,digest(cfg))
        acceptance=assemble_acceptance(cfg,evaluation,profile,motion=samples)
        self.assertEqual(evaluation.source.artifact_id,raw_ref['artifact_id'])
        self.assertFalse(acceptance['accepted'])
        self.assertFalse(acceptance['components']['task_evaluator']['passed'])
        self.assertFalse(acceptance['components']['holding_speed']['passed'])
        rows={k:dict(fixed=dict(signed_maximum_excess=v),warm_best=None)
            for k,v in [('d_minus',.2),('d_zero',.1),('d_plus',0.)]}
        estimate=probe.response_estimate(rows)
        self.assertAlmostEqual(estimate['fixed_per_mpa'],-.2/1.08)
        self.assertIsNone(estimate['reoptimized_per_mpa'])
        self.assertFalse(estimate['derivative_valid'])


if __name__=='__main__':unittest.main()
