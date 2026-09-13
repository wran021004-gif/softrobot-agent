"""Focused software risks only. No rollout, Engine, API or full-suite discovery."""
import copy
import gzip
import json
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
import numpy as np
import mujoco
from schemas.design_spec import DesignSpec
from schemas.exploration import ExplorationPhysics,ExplorationControl
from tools.design_compiler import build_robot_ir,ensure_robot_ir
from tools.spec_tools import ROOT,load_task_package
from tools.mujoco_tools import compile_mujoco
from tools.state_io import digest,atomic_json
from tools.trajectory_diagnosis import diagnose


class Round9Risks(unittest.TestCase):
    def setUp(self):
        # Windows managed sandbox cannot reopen tempfile's private 0700 dirs.
        # Retain tiny fixture artifacts for inspection under the workspace.
        self.root=ROOT/'runs/round9_tests'/uuid.uuid4().hex;self.root.mkdir(parents=True)
    def design(self):
        return DesignSpec(robot_family='tendon_driven_continuum',sections=1,segments=8,total_length_m=.3,
            body_radius_m=.02,tendon_count=4,tendon_routing_radius_m=.018,
            exploration_physics=ExplorationPhysics(natural_total_angle_rad=.8,tip_ei_ratio=.5))
    def test_shared_mapping_and_unilateral_servo(self):
        ir=build_robot_ir(self.design());task,env=load_task_package();p=self.root/'robot.xml'
        self.assertEqual(compile_mujoco(ir,task,p,env).status,'pass');m=mujoco.MjModel.from_xml_path(str(p));d=mujoco.MjData(m)
        self.assertEqual(m.nq,16);self.assertTrue(np.all(d.qpos==0))
        self.assertTrue(np.allclose(m.qpos_spring[::2],-.1))
        self.assertTrue(np.allclose(m.qpos_spring[1::2],0))
        self.assertAlmostEqual(sum(m.body_mass),.3*ir.mechanics.line_density_kg_m)
        self.assertTrue(np.allclose(m.jnt_stiffness[::2],ir.resolved_rod.stiffness_nm_rad))
        d.ctrl[:]=.31;mujoco.mj_forward(m,d);self.assertTrue(np.allclose(d.actuator_force,0))
        d.ctrl[:]=.2;mujoco.mj_forward(m,d);self.assertTrue(np.allclose(d.actuator_force,-20))
        changed=ir.model_copy(update={'resolved_rod':ir.resolved_rod.model_copy(update={'mass_kg':(.1,)*8})})
        with self.assertRaises(ValueError):ensure_robot_ir(changed)
    def test_control_identity_and_envelope(self):
        d=self.design().model_dump(mode='json');a=ExplorationControl().model_dump();b={**a,'mode':'C2'}
        self.assertNotEqual(digest(dict(design=d,control=a)),digest(dict(design=d,control=b)))
        invalid=self.design().model_copy(update={'tendon_routing_radius_m':.03})
        with self.assertRaises(ValueError):build_robot_ir(invalid)
        with self.assertRaises(ValueError):ExplorationPhysics(elastic_tendon_stiffness=1000)
    def test_durable_budget_interruption_and_reuse(self):
        from tools.dynamic_campaign import DynamicCampaign
        b=DynamicCampaign.__new__(DynamicCampaign);b.root=self.root;b.tick=time.monotonic()
        b.state=dict(working_memory={});b.ledger=dict(limits={'matlab_dynamic':2,'active_wall_s':100},
            used={'matlab_dynamic':0,'active_wall_s':0},entries=[])
        with patch('tools.dynamic_campaign.LEDGER',self.root/'grant_ledger.json'):
            receipt,new=b.reserve('matlab_dynamic','trial-A');self.assertTrue(new)
            receipt['status']='interrupted';b.save()
            _,new=b.reserve('matlab_dynamic','trial-A');self.assertFalse(new)
            self.assertEqual(b.ledger['used']['matlab_dynamic'],1)
            b.reserve('matlab_dynamic','trial-B')
            with self.assertRaises(ValueError):b.reserve('matlab_dynamic','trial-C')
            self.assertEqual(json.loads((self.root/'budget.json').read_text())['used']['matlab_dynamic'],2)
    def fixture(self):
        rows=[dict(time_s=(i+1)*.002,solver_time_s=i*.002,tip_m=[.3,0,0],qpos_rad=[0],qvel_rad_s=[0],
            command_m=[.315],solver_tendon_length_m=[.3],solver_actuator_force_n=[-1e-5],solver_contact_count=0,
            centerline_m=[[0,0,0],[.3,0,0]],tendon_routes_m=[[[0,0,-.018],[.3,0,-.018]]]) for i in range(51)]
        path=self.root/'trajectory.json.gz'
        with gzip.open(path,'wt',encoding='utf8') as f:json.dump(rows,f)
        meta=dict(run_id='fixture',candidate_id='c000',backend='matlab',model_id='fixture',force_limit_n=20,kp=1000,
            reference_length_m=.3,offsets=[[0,-.018]],joint_names=['joint_0_y'],natural=[0],stiffness=[.1],damping=[.1])
        return path,meta
    def test_entity_time_no_push_is_not_max_pull(self):
        path,meta=self.fixture();d=diagnose(path,meta,fields=['contacts'])
        self.assertIn('NO_PUSH_END',[e['event_type'] for e in d['events']]);self.assertNotIn('MAX_PULL',[e['event_type'] for e in d['events']])
        self.assertIn('RELEASE_WITH_SMALL_PATH_CHANGE',[e['event_type'] for e in d['events']])
        tendon=d['queries'][0];joint=d['queries'][1]
        self.assertEqual(tendon['t_start_s'],0);self.assertEqual(joint['t_start_s'],.002)
        self.assertEqual(d['raw_fields']['contacts'][0]['value'],'NOT_RECORDED')
    def test_replay_reads_only_saved_coordinates(self):
        from tools.dynamic_view import render_candidate
        path,meta=self.fixture();atomic_json(self.root/'result.json',dict(complete=True))
        c=dict(candidate_id='c000',design={'total_length_m':.3},control={},results={'matlab':{'result_ref':'result.json'}})
        with patch('tools.reach_dynamics.DynamicsBackends.simulate',side_effect=AssertionError('No simulation during replay')):
            output=render_candidate(self.root,c,'matlab')
        text=output.read_text(encoding='utf8');self.assertIn('requestAnimationFrame',text);self.assertIn('solver_time_s',text)
    def test_legacy_serialization_identity(self):
        from tools.spec_tools import load_yaml
        original=load_yaml(ROOT/'configs/design_tendon_arm.yaml')
        self.assertEqual(DesignSpec.model_validate(original).model_dump(mode='json'),original)

if __name__=='__main__':unittest.main()
