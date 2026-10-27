"""Geometry and independent acceptance fixtures; never scientific execution evidence."""
from copy import deepcopy
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from schemas.platform import SessionInput
from tools.platform_tasks import compile_input
from tools.research.config import ROOT,resolve
from tools.research.contracts import AnalysisRequest
from tools.research.physical_replay import evaluate_playback
from tools.research.control_correction import task_measure,constraint_vectors
from tools.research.native_analysis import assessment,applicability
from tools.research.feedback import task_gap
from tools.research_tasks import task_adapter,assemble_acceptance,_outcome_issue,_source_issue
from extensions.reference.implementation import tool_axis_angles
from extensions.reference.contracts import ToolAxisGoal
from extensions.tendon_family.mujoco_analysis import NativeModel

RAW=dict(artifact_id='a'*64,media_type='application/json')
EV=dict(artifact_id='b'*64,media_type='application/json')
PROFILE=dict(artifact_id='c'*64,media_type='application/json')


class ToolAxisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=resolve(ROOT/'configs/research/study_bf5_tool_axis_preparation.json')

    def setUp(self):
        self.cfg=deepcopy(self.spec['configuration']);self.adapter=task_adapter(self.cfg)
        self.goal=self.cfg['task']['goal']['data'];self.times=np.arange(31)*.02

    def raw(self):
        return dict(status='completed',physics_steps=600,tendon_order=[t['id'] for t in self.cfg['robot']['structure']['data']['tendons']],
            fixture='Fabricated contract fixture; no integration',
            samples=[dict(time_s=float(t),tip_m=list(self.goal['target_m']),tip_tool_axis_world=list(self.goal['target_axis_world']),
                tip_velocity_m_s=[0.,0.,0.],speed_m_s=0.,actual_tension_n=[.2]*6) for t in self.times])

    def accept(self,raw):
        ev,profile=evaluate_playback(self.cfg,raw,RAW,'bf5-synthetic')
        profile.update(execution_id='synthetic-fixture',evaluation=EV,simulation=RAW)
        accepted=assemble_acceptance(self.cfg,ev,profile,evaluation_reference=EV,profile_reference=PROFILE)
        return ev,profile,accepted

    def test_axis_geometry_and_invalid_units(self):
        np.testing.assert_allclose(tool_axis_angles([[1,0,0],[0,1,0],[-1,0,0]],[1,0,0]),[0,math.pi/2,math.pi])
        with self.assertRaises(ValueError):tool_axis_angles([[2,0,0]],[1,0,0])
        with self.assertRaises(ValueError):ToolAxisGoal(target_m=[0,0,0],axis_local=[0,0,0],target_axis_world=[1,0,0])
        # Roll about local x leaves the tool axis unchanged.
        theta=.9;R=np.array([[1,0,0],[0,math.cos(theta),-math.sin(theta)],[0,math.sin(theta),math.cos(theta)]])
        self.assertEqual(tool_axis_angles([(R@np.array([1,0,0])).tolist()],[1,0,0])[0],0)

    def test_native_motion_projects_declared_local_axis(self):
        R=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
        native=SimpleNamespace(model=SimpleNamespace(nv=2),tip=0,tool_axis_local=np.array([0.,1.,0.]))
        d=SimpleNamespace(time=.6,site_xpos=np.array([[1.,2.,3.]]),site_xmat=R.reshape(1,9),qvel=np.zeros(2))
        with patch('extensions.tendon_family.mujoco_analysis.mujoco.mj_jacSite'):
            motion,_=NativeModel.motion(native,d)
        np.testing.assert_array_equal(motion['tip_tool_axis_world'],[-1,0,0])

    def test_both_independent_conditions_are_required(self):
        ev,profile,accepted=self.accept(self.raw())
        self.assertTrue(ev.task_success);self.assertTrue(accepted['accepted'])
        self.assertIsNone(_outcome_issue(accepted));self.assertIsNone(_source_issue(accepted))
        gap=task_gap(dict(status='evaluated',acceptance=accepted));self.assertTrue(gap['valid_complete']);self.assertEqual(gap['normalized_gap'],0)
        raw=self.raw();raw['samples'][-1]['tip_tool_axis_world']=(-np.asarray(self.goal['target_axis_world'])).tolist()
        ev,_,a=self.accept(raw)
        self.assertFalse(ev.task_success);self.assertFalse(a['accepted']);self.assertEqual(a['status'],'valid_failure')
        self.assertTrue(a['components']['evaluator:tool_position']['passed'])
        self.assertFalse(a['components']['evaluator:tool_axis_direction']['passed'])
        raw=self.raw();raw['samples'][-2]['tip_m'][1]+=.009
        ev,_,a=self.accept(raw)
        self.assertFalse(a['accepted']);self.assertFalse(a['components']['evaluator:tool_position']['passed'])
        self.assertTrue(a['components']['evaluator:tool_axis_direction']['passed'])

    def test_missing_axis_or_grid_is_not_position_only_success(self):
        raw=self.raw()
        for r in raw['samples']:r.pop('tip_tool_axis_world')
        ev,_,a=self.accept(raw)
        self.assertEqual(ev.validity,'incomplete');self.assertIsNone(a['accepted'])
        raw=self.raw();raw['samples'][-1]['time_s']-=.001
        ev,_,a=self.accept(raw)
        self.assertEqual(ev.validity,'invalid');self.assertIsNone(a['accepted'])

    def test_response_cone_and_real_radian_measure(self):
        axis=np.asarray(self.goal['target_axis_world']);side=np.cross(axis,[0.,0.,1.]);side/=np.linalg.norm(side)
        theta=math.radians(4);tilted=axis*math.cos(theta)+side*math.sin(theta)
        out=dict(times_s=self.times.tolist(),tip_positions_m=[self.goal['target_m']]*31,tip_tool_axes_world=[tilted.tolist()]*31)
        options=self.adapter.control_search_options();measure=task_measure(out,**options)
        self.assertAlmostEqual(measure['max_tool_axis_angle_error_rad'],theta)
        self.assertAlmostEqual(measure['normalized_gap'],1/3)
        norms=np.linalg.norm(constraint_vectors(out,**options),axis=1)
        self.assertGreater(max(norms),1);self.assertEqual(min(norms),0)

    def test_definition_and_native_only_applicability(self):
        self.assertTrue(compile_input(self.cfg)['approval']['capabilities_ready'])
        req=self.adapter.analysis_requirements({})
        self.assertEqual([c.indices for c in req.constraints],[[29,30],[29,30]])
        self.assertEqual([c.signal.name for c in req.constraints],['tip_position','tip_tool_axis'])
        settings=dict(version='local_control_search_v2',correction_window_s=[0,.6],knots_s=[0,.2,.4,.58],evaluation_requests=51,iterations=2)
        q=AnalysisRequest.model_validate(dict(candidate=RAW,operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=self.spec['analysis_protocol'],control_optimization=dict(source=RAW,settings=settings)))
        fit=applicability(req,q,assessment(SessionInput.model_validate(self.cfg),req),dict(actual_time_s=0))
        self.assertEqual(fit['status'],'applicable');self.assertEqual(len(fit['constraint_coverage']),2)
        from extensions.tendon_family.backends import NativeSequenceMujocoBackend
        with self.assertRaisesRegex(ValueError,'TOOL_AXIS_REQUIRES_EXPLICIT'):
            NativeSequenceMujocoBackend.solve(None,None)
        # Unsupported affine analysis retains the axis and cannot silently certify position alone.
        from tools.research.task_constraints import check_analysis_applicability
        other=q.model_copy(update=dict(model_source='controller',operation='equilibrium',control_optimization=None))
        fit=check_analysis_applicability(req,other,dict(model_id='model.gvs',uses={}),exact_point=dict(actual_time_s=0))
        self.assertEqual(fit['status'],'not_applicable')


if __name__=='__main__':unittest.main()
