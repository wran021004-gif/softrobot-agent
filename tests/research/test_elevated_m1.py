"""Elevated v2 contracts; fabricated acceptance is never scientific evidence."""
from copy import deepcopy
import threading
import unittest
from unittest.mock import patch
import numpy as np
import mujoco
from tools.research.config import ROOT, resolve, _reference
from tools.research.conditions import configuration_for_condition, shared_physics, joint_assessment
from tools.research.design import family_configuration
from extensions.tendon_family.mjcf import load_model
from extensions.tendon_family.mujoco_analysis import NativeModel

LEAF='study_m1_elevated_free_space_v2.json'

class ElevatedM1Tests(unittest.TestCase):
    def test_translation_and_shared_conditions(self):
        spec=resolve(ROOT/'configs/research'/LEAF)
        self.assertEqual(spec['family_space']['executable_segment_counts'],list(range(1,10)))
        self.assertEqual(spec['family_space']['executable_tendon_count_bounds'],[1,7])
        self.assertEqual(spec['topology_scope']['executable_segment_counts'],list(range(1,10)))
        for c in spec['task_conditions']:
            old=_reference(ROOT/f"tasks/bf7_shared_reach_v1_{c['condition_id']}.json",'task',{'references':{}})['task']
            new=_reference(ROOT/f"tasks/m1_elevated_free_space_v2_{c['condition_id']}.json",'task',{'references':{}})['task']
            expected=deepcopy(old)
            for k in ('task_id','task_version','name','source'):expected[k]=new[k]
            expected['environment']['data']['mount']['position_m'][2]=2.5
            expected['goal']['data']['target_m'][2]=round(old['goal']['data']['target_m'][2]+2.35,12)
            self.assertEqual(new,expected)
            self.assertTrue(np.allclose(np.array(new['goal']['data']['target_m'])-new['environment']['data']['mount']['position_m'],np.array(old['goal']['data']['target_m'])-old['environment']['data']['mount']['position_m'],atol=1e-14,rtol=0))
            cfg=configuration_for_condition(spec['configuration'],c)
            self.assertEqual(shared_physics(cfg),shared_physics(spec['configuration']))
            self.assertEqual(cfg['policy']['backend']['parameters']['data']['contact_model'],'mujoco_frictionless_normal_v1')

    def test_nine_segments_compile_without_reducing_cells(self):
        spec=resolve(ROOT/'configs/research'/LEAF)
        cfg,*_=family_configuration(spec['configuration'],spec['family_space'],dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=9,tendon_count=4),'engineering-nine-fixture')
        before=threading.stack_size();native=NativeModel(cfg)
        self.assertEqual(threading.stack_size(),before)
        self.assertEqual(native.model.nv,216)
        self.assertEqual(list(cfg['policy']['discretization']['data']['cells'].values()),[12]*9)
        self.assertEqual(native.cost['physics_steps'],0)

    def test_loader_preserves_model_and_propagates_compile_error(self):
        xml='<mujoco><worldbody><body><joint type="hinge"/><geom type="sphere" size=".01"/></body></worldbody></mujoco>'
        old=mujoco.MjModel.from_xml_string(xml);new=load_model(xml=xml)
        for name in ('body_mass','body_inertia','jnt_stiffness','dof_damping','body_pos'):
            np.testing.assert_array_equal(getattr(new,name),getattr(old,name))
        before=threading.stack_size()
        with self.assertRaises(ValueError):load_model(xml='<invalid>')
        self.assertEqual(threading.stack_size(),before)

    def test_original_joint_select_and_condition_source_admission(self):
        from tests.research import test_cross_task_integration as fixtures
        from tools.research import core
        from tools.research.state import state, update
        from tools.research.feedback import eligibility
        spec=resolve(ROOT/'configs/research'/LEAF)
        with fixtures.fixture_directory() as folder, patch.object(fixtures,'resolve',return_value=spec):
            h=fixtures.fixture_host(folder,physical_launches=3)
            with patch('tools.research.core.guard'),patch('tools.research.state.guard'),patch('tools.research.physical_replay.guard'):
                root=core.dispatch(h,fixtures.plan('generate',generation=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],segment_count=1,tendon_count=3)),'generate')['result']['candidate']
                results=[];seeds=[]
                for i,c in enumerate(spec['task_conditions']):
                    seed=core.dispatch(h,fixtures.plan('initialize_control',root,control_seed=dict(candidate=root,condition_id=c['condition_id'],tensions_n=[[.2+i*.1]*3])),'seed-'+str(i))['result']
                    if seeds:
                        with self.assertRaisesRegex(ValueError,'MISMATCH'):
                            core.dispatch(h,fixtures.plan('physical_replay',seed['candidate'],physical_replay=dict(candidate=seed['candidate'],source=seeds[0]['source'])),'wrong-source-'+str(i))
                    seeds.append(seed)
                    with patch('tools.service_execution._run_contained',side_effect=fixtures.perfect_tracking_worker):
                        r=core.dispatch(h,fixtures.plan('physical_replay',seed['candidate'],physical_replay=dict(candidate=seed['candidate'],source=seed['source'])),'replay-'+str(i))['result']
                    results.append(r['reference']);core.read_evidence(h,dict(reference=r['reference'],view='full'))
                    if i<2:self.assertFalse(eligibility(h,results,selection=True)['eligible'])
                self.assertEqual(len({v['source']['artifact_id'] for v in seeds}),3)
                self.assertTrue(joint_assessment(h,results,require_reads=False)['aggregation']['all_scheduled_accepted'])
                self.assertFalse(eligibility(h,results,selection=True)['eligible'])
                from tests.research.test_general_task_adaptation import deliver_certificates
                update(h,pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
                deliver_certificates(h,results)
                self.assertTrue(eligibility(h,results,selection=True)['eligible'])
                selected=core.dispatch(h,fixtures.plan('select',selected_execution=results),'select')
                self.assertTrue(selected['result']['selected'])
                self.assertEqual(h.store.remaining()['used']['backend_solves'],3)
                self.assertIsNone(state(h)['pending'])
