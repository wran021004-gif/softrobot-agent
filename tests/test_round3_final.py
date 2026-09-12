"""Focused new envelope, actuation, shape and study-selection behavior."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import yaml
from capabilities.registry import get_robot_family_grammar, get_tool_manifest
from schemas.design_spec import DesignSpec
from schemas.settings import RunSettings
from schemas.tool_result import ToolResult
from tools.actuation_tools import analyze_actuation
from tools.artifact_tools import create_run, finalize_run, file_hash
from tools.design_compiler import build_robot_ir
from tools.design_envelope import load_envelope, validate_envelope_design, envelope_variables
from tools.experiment_policy_tools import validate_experiment_policy
from tools.experiment_tools import _execute, _optimize
from tools.pcc_math import analytic_target_matching_length, tip_and_jacobian
from tools.round3_studies import policy_for_subset, joint_candidates, StudyLedger, read
from tools.shape_tools import compare_shape_model_sim
from tools.mujoco_tools import compile_mujoco, run_task
from tools.spec_tools import ROOT, load_task_package
from controllers.open_loop_length import OpenLoopLength
from tests.test_architecture import design, BASELINE
from tests.test_round3 import SyntheticModel


class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.envelope,_ = load_envelope(get_robot_family_grammar('tendon_driven_continuum'))
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'engineer_policy.yaml'

    def policy(self,**updates):
        value = policy_for_subset('configs/design_tendon_arm.yaml',['total_length_m'])
        value.update(updates)
        self.path.write_text(yaml.safe_dump(value),encoding='utf-8')
        return validate_experiment_policy(self.path)

    def test_wide_envelope_and_representation_categories(self):
        for length in (.05,.8):
            validate_envelope_design(design(total_length_m=length),self.envelope)
        for update in ({'total_length_m':.049},{'total_length_m':.801},{'sections':2},
                       {'segments':25},{'segments':3},{'tendon_count':2},{'tendon_count':9},
                       {'body_radius_m':.051},{'tendon_routing_radius_m':.001}):
            with self.subTest(update=update),self.assertRaises(ValueError):
                validate_envelope_design(design(**update),self.envelope)
        validate_envelope_design(design(body_radius_m=.05),self.envelope)
        for name,blocker in [('body_radius_m','BLOCKED_BY_MECHANICS_COUPLING'),('segments','NUMERICAL_SENSITIVITY_ONLY')]:
            with self.assertRaisesRegex(ValueError,blocker):
                envelope_variables(self.envelope,(name,))

    def test_task_subset_needs_no_new_human_approval_and_hashes_authority(self):
        p = self.policy(variables=[dict(name='total_length_m',unit='m',lower_bound=.29,upper_bound=.5,constraints=['positive'])])
        p.validate_candidate(design(total_length_m=.3))
        with self.assertRaises(ValueError):
            p.validate_candidate(design(total_length_m=.6))
        self.assertTrue(any(path.name=='envelope.yaml' for path in p.input_hashes))
        self.assertTrue(any(path.name=='round3_final_human_authorization.md' for path in p.input_hashes))
        self.assertEqual(p.policy.approval_source,self.envelope['approval_source'])
        with self.assertRaises(ValueError):
            self.policy(variables=[dict(name='total_length_m',unit='m',lower_bound=.04,upper_bound=.8,constraints=['positive'])])

    def test_relational_constraint_and_unselected_fields_before_backend(self):
        p = self.policy()
        for candidate in (design(body_radius_m=.01),design(tendon_routing_radius_m=.018,body_radius_m=.018)):
            with self.assertRaisesRegex(ValueError,'RELATIONAL_CONSTRAINT'):
                p.validate_candidate(candidate)
        with self.assertRaises(ValueError):
            p.validate_candidate(design(tendon_count=5))

    def test_segments_only_for_numerical_sensitivity_and_no_optimizer(self):
        value = policy_for_subset('configs/design_tendon_arm.yaml',['segments'],purpose='NUMERICAL_SENSITIVITY')
        p = self.policy(**value)
        for n in [4,6,8,12,16,24]:
            p.validate_candidate(design(segments=n))
        with self.assertRaises(ValueError):
            p.validate_candidate(design(segments=12,total_length_m=.3))
        from types import SimpleNamespace
        with self.assertRaisesRegex(ValueError,'NUMERICAL_SENSITIVITY_ONLY'):
            _optimize(SimpleNamespace(experiment=p))

    def test_routes_new_physics_and_historical_policy(self):
        for updates in ({'allowed_model_levels':['M2']},{'allowed_controller_levels':['C2']},
                        {'physics_profile':'invented_EI'},{'repair_iteration_budget':1}):
            with self.subTest(updates=updates),self.assertRaises(ValueError):
                self.policy(**updates)
        old = validate_experiment_policy(ROOT/'configs/experiments/round3_1_reach_free.yaml')
        old.validate_candidate(design(total_length_m=.35))
        with self.assertRaises(ValueError):
            old.validate_candidate(design(total_length_m=.3))


class GeometryTests(unittest.TestCase):
    def plan(self,ir,theta=1.1,phi=.7):
        return ToolResult(tool='plan_pcc_reach',status='pass',metrics={'theta_rad':theta,'phi_rad':phi,
            'tendon_target_lengths_m':[ir.total_length_m-ir.tendon_routing_radius_m*theta*math.cos(r.angle_rad-phi) for r in ir.tendon_routes]})

    def test_analytic_pcc_target_match_and_straight_limit(self):
        for target in ([.25,0,.15],[.4,0,0],[0,.3,0],[.2,-.1,.1]):
            value = analytic_target_matching_length(target)
            tip,_ = tip_and_jacobian(value['total_length_m'],[value['theta_rad']*math.cos(value['phi_rad']),value['theta_rad']*math.sin(value['phi_rad'])])
            np.testing.assert_allclose(tip,target,atol=1e-14)

    def test_actuation_values_and_jacobian_finite_differences(self):
        ir = build_robot_ir(design(tendon_count=5))
        m = analyze_actuation(ir,self.plan(ir)).metrics
        jac = np.asarray(m['tendon_jacobian_m_per_rad'])
        bend = np.array([1.1*math.cos(.7),1.1*math.sin(.7)])
        def lengths(b):
            return np.array([ir.total_length_m-ir.tendon_routing_radius_m*(b[0]*math.cos(r.angle_rad)+b[1]*math.sin(r.angle_rad)) for r in ir.tendon_routes])
        for i in range(2):
            step = np.zeros(2); step[i]=1e-6
            np.testing.assert_allclose((lengths(bend+step)-lengths(bend-step))/(2e-6),jac[:,i],atol=1e-10)
        np.testing.assert_allclose(m['signed_tendon_strokes_m'],lengths(bend)-ir.total_length_m)
        self.assertEqual(m['scope'],'GEOMETRIC_ACTUATION_ONLY')
        self.assertFalse({'required_tendon_force','motor_torque','physical_actuation_feasibility'} & m.keys())
        self.assertEqual(get_tool_manifest('model')['tools']['analyze_actuation']['implementation_status'],'IMPLEMENTED')

    def test_radius_and_count_sweeps_geometric_invariance(self):
        scales = []
        for radius in [.002,.004,.006,.008,.010,.012,.015,.018]:
            ir = build_robot_ir(design(tendon_routing_radius_m=radius))
            m = analyze_actuation(ir,self.plan(ir)).metrics
            scales.append(m['maximum_tendon_stroke_m']/radius)
            self.assertEqual(m['jacobian_rank'],2)
            self.assertAlmostEqual(m['condition_number'],1.)
        np.testing.assert_allclose(scales,[scales[0]]*len(scales))
        for count in range(3,9):
            ir = build_robot_ir(design(tendon_count=count))
            m = analyze_actuation(ir,self.plan(ir)).metrics
            self.assertEqual(len(m['tendon_jacobian_m_per_rad']),count)
            np.testing.assert_allclose(m['singular_values_m_per_rad'],[.015*math.sqrt(count/2)]*2)
        straight = build_robot_ir(design())
        m = analyze_actuation(straight,self.plan(straight,theta=0)).metrics
        self.assertEqual(m['maximum_tendon_stroke_m'],0)
        self.assertEqual(m['jacobian_rank'],2)

    def test_joint_search_is_seeded_bounded_multivariable_and_includes_baseline(self):
        base = design().model_dump()
        first = joint_candidates(base,.3,.018,6,.306,limit=20)
        self.assertEqual(first,joint_candidates(base,.3,.018,6,.306,limit=20))
        self.assertIn(base,first)
        envelope,_ = load_envelope(get_robot_family_grammar(base['robot_family']))
        for candidate in first:
            validate_envelope_design(candidate,envelope)
        self.assertEqual(len(first),20)
        self.assertGreater(len({c['tendon_count'] for c in first}),2)


class ShapeTests(unittest.TestCase):
    def sources(self,actual):
        context = {'run_id':'test','robot_ir_hash':'test','task_hash':'test','environment_hash':'test','coordinate_frame':'test'}
        model = ToolResult(tool='pcc_centerline',status='pass',metrics={'scope':'MODEL_SHAPE_EVIDENCE',
            'comparison_context':context,'normalized_arc_length':[0.,.5,1.],'tendon_target_lengths_m':[.4]},
            artifacts={'centerline_m':[[0,0,0],[.2,0,0],[.4,0,0]]})
        sim = ToolResult(tool='run_task',status='pass',metrics={'comparison_context':context,'task_success':True,
            'tendon_target_lengths_m':[.4],'execution_evidence':{'actuators':[{'command_min_m':.4,'command_max_m':.4}]}},
            artifacts={'final_centerline_m':actual})
        return model,sim

    def test_normalized_sampling_discrepancies_and_no_causal_threshold(self):
        m,s = self.sources([[0,0,0],[.1,0,0],[.4,0,0]])
        result = compare_shape_model_sim(m,s)
        self.assertAlmostEqual(result.metrics['maximum_centerline_discrepancy_m'],0.,places=14)
        m,s = self.sources([[0,0,.1],[.4,0,.1]])
        result = compare_shape_model_sim(m,s)
        self.assertAlmostEqual(result.metrics['centerline_rms_discrepancy_m'],.1)
        self.assertEqual(result.metrics['failure_attribution'],'UNKNOWN')
        self.assertIsNone(result.metrics['threshold'])
        self.assertEqual(len(result.metrics['per_sample_differences']),65)

    def test_debug_mismatched_or_varying_commands_rejected(self):
        m,s = self.sources([[0,0,0],[.4,0,0]])
        for key,value in [('scope','DEBUG_ONLY'),('comparison_context',{'run_id':'other'}),('tendon_target_lengths_m',[.3])]:
            changed=m.model_copy(update={'metrics':{**m.metrics,key:value}})
            self.assertEqual(compare_shape_model_sim(changed,s).metrics['evidence_status'],'unavailable')

    def test_short_rollout_shape_observation_preserves_execution(self):
        task,_ = load_task_package()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            path = Path(tmp)/'robot.xml'
            compile_mujoco(design(),task,path)
            settings=RunSettings(steps=12,random_seed=0,provenance='TEST_ONLY short software rollout')
            controller=OpenLoopLength(BASELINE['tendon_target_lengths_m'])
            original=run_task(path,task,controller,settings)
            observed=run_task(path,task,controller,settings,record_shape=True)
            self.assertEqual(original.metrics,observed.metrics)
            self.assertEqual(original.artifacts['final_state'],observed.artifacts['final_state'])
            self.assertEqual(len(observed.artifacts['final_centerline_m']),9)
            self.assertEqual(observed.artifacts['final_centerline_m'][-1],observed.metrics['tip_position_m'])


class StudyIntegrationTests(unittest.TestCase):
    def test_model_artifacts_reuse_provenance_and_hard_geometry_rejection(self):
        class ResearchModel(SyntheticModel):
            def pcc_centerline(self,ir,plan,samples=65):
                theta,phi = plan.metrics['theta_rad'],plan.metrics['phi_rad']
                points = [[0.,0.,0.]]
                for i in range(1,samples):
                    p,_ = tip_and_jacobian(ir.total_length_m*i/(samples-1),
                        [theta*i/(samples-1)*math.cos(phi),theta*i/(samples-1)*math.sin(phi)])
                    points.append(p)
                return ToolResult(tool='pcc_centerline',status='pass',metrics={'scope':'MODEL_SHAPE_EVIDENCE',
                    'comparison_context':plan.metrics['comparison_context'],
                    'normalized_arc_length':[i/(samples-1) for i in range(samples)],
                    'tendon_target_lengths_m':plan.metrics['tendon_target_lengths_m']},artifacts={'centerline_m':points})
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp)
            policy=root/'policy.yaml'
            policy.write_text(yaml.safe_dump(policy_for_subset('configs/design_tendon_arm.yaml',['total_length_m'],total=3,mujoco=0)),encoding='utf-8')
            ledger=StudyLedger(ResearchModel,root)
            def first(session):
                row=ledger.evaluate(session,design(),'M1')
                self.assertEqual(row['status'],'MODEL_ONLY')
                self.assertEqual(row['actuation']['jacobian_rank'],2)
                rejected=ledger.evaluate(session,design(total_length_m=.1),'M1')
                self.assertEqual(rejected['disposition'],'REJECTED_HARD_GEOMETRY')
                self.assertEqual(rejected['canonical_task_status'],'NOT_RUN')
                self.assertFalse((root/rejected['run_id']/'robot.xml').exists())
                return {'first':row['run_id']}
            parent=_execute(policy,'study',first,run_root=root,matlab_factory=ResearchModel)
            self.assertEqual(parent.record.final_status,'PASS',read(parent.path/'study_summary.json'))
            def second(session):
                row=ledger.evaluate(session,design(),'M1')
                self.assertTrue(row['reused'])
                self.assertEqual(row['source_parent_experiment_id'],parent.record.run_id)
                self.assertEqual(session.results,[])
                return {'reuse':row['run_id']}
            other=_execute(policy,'study',second,run_root=root,matlab_factory=ResearchModel)
            self.assertEqual(other.record.final_status,'PASS',read(other.path/'study_summary.json'))
            self.assertEqual(read(other.path/'experiment_summary.json')['evaluations'],0)
            self.assertEqual(len(list(other.path.glob('reused_*.json'))),1)


if __name__ == '__main__':
    unittest.main()
