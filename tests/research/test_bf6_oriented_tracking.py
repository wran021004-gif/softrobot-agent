"""Loaded-scan contract fixtures and compiled-inertia checks; zero integration steps."""
from copy import deepcopy
import unittest
import numpy as np
from schemas.platform import SessionInput
from tools.research.config import ROOT,resolve
from tools.research_tasks import task_adapter,assemble_acceptance,_outcome_issue,_source_issue
from tools.research.physical_replay import evaluate_playback
from tools.research.control_correction import task_measure,constraint_vectors
from tools.research.contracts import AnalysisRequest
from tools.research.native_analysis import assessment,applicability
from extensions.reference.contracts import OrientedTrackingGoal
from extensions.tendon_family.backends import check_rigid_tool_definition,check_rigid_tool_model
from extensions.tendon_family.mujoco_analysis import NativeModel

RAW=dict(artifact_id='a'*64,media_type='application/json')
EV=dict(artifact_id='b'*64,media_type='application/json')
PROFILE=dict(artifact_id='c'*64,media_type='application/json')


class OrientedTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=resolve(ROOT/'configs/research/study_bf6_sensor_oriented_tracking.json')

    def setUp(self):
        self.cfg=deepcopy(self.spec['configuration']);self.adapter=task_adapter(self.cfg)
        self.goal=OrientedTrackingGoal.model_validate(self.cfg['task']['goal']['data']);self.times=np.arange(31)*.02

    def raw(self):
        return dict(status='completed',physics_steps=600,tendon_order=[t['id'] for t in self.cfg['robot']['structure']['data']['tendons']],
            fixture='Fabricated independent evaluator fixture; no physics execution',rigid_tool_binding=dict(matched=True),
            samples=[dict(time_s=float(t),tip_m=self.goal.at_time(float(t))[0],tip_tool_axis_world=self.goal.axis_at_time(float(t)),
                tip_velocity_m_s=[0.,0.,0.],speed_m_s=0.,actual_tension_n=[.2]*6) for t in self.times])

    def accept(self,raw):
        ev,profile=evaluate_playback(self.cfg,raw,RAW,'bf6-fixture')
        profile.update(execution_id='synthetic-fixture',evaluation=EV,simulation=RAW)
        result=assemble_acceptance(self.cfg,ev,profile,evaluation_reference=EV,profile_reference=PROFILE)
        return ev,result

    def test_reference_and_native_coverage_are_timed_and_complete(self):
        for t in [0,.15,.3,.45,.6]:self.assertAlmostEqual(np.linalg.norm(self.goal.axis_at_time(t)),1)
        np.testing.assert_allclose(self.goal.axis_at_time(.3),self.goal.axis_vertices_world[1])
        req=self.adapter.analysis_requirements({})
        self.assertEqual([c.indices for c in req.constraints],[list(range(1,31))]*2)
        self.assertEqual([c.constraint_id for c in req.constraints],['timed_tracking','tool_axis_direction'])
        q=AnalysisRequest.model_validate(dict(candidate=RAW,operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=self.spec['analysis_protocol'],
            control_optimization=dict(source=RAW,settings=dict(version='local_control_search_v2',correction_window_s=[0,.6],knots_s=[0,.2,.4,.58],evaluation_requests=151,iterations=6))))
        fit=applicability(req,q,assessment(SessionInput.model_validate(self.cfg),req),dict(actual_time_s=0))
        self.assertEqual(fit['status'],'applicable');self.assertEqual(len(fit['constraint_coverage']),2)
        np.testing.assert_allclose(req.constraints[0].reference,self.adapter.reference_at(self.times[1:])[0])

    def test_real_compiled_rigid_load_and_no_force_substitute(self):
        native=NativeModel(self.cfg)
        self.assertEqual(native.cost['physics_steps'],0)
        self.assertTrue(native.tool_load_binding['matched']);self.assertAlmostEqual(native.tool_load_binding['mass_kg'],.02)
        np.testing.assert_allclose(native.tool_load_binding['inertia_com_local_kg_m2'],self.goal.rigid_tool.inertia_com_local_kg_m2,rtol=0,atol=1e-12)
        native.model.body_mass[native.model.body('payload').id]=.01
        with self.assertRaisesRegex(ValueError,'COMPILED_MUJOCO_RIGID_TOOL_BINDING_MISMATCH'):
            check_rigid_tool_model(SessionInput.model_validate(self.cfg),native.model)
        cfg=deepcopy(self.cfg);cfg['task']['environment']['data']['external_forces']=[dict(robot_id='robot',entity='payload',point='center_of_mass',frame='world',force_n=[0.,0.,-.0981],start_s=0,end_s=.6)]
        with self.assertRaisesRegex(ValueError,'EXTERNAL_FORCE_SUBSTITUTION'):
            check_rigid_tool_definition(SessionInput.model_validate(cfg))

    def test_independent_acceptance_and_original_position_evaluator(self):
        ev,a=self.accept(self.raw());self.assertTrue(ev.task_success);self.assertTrue(a['accepted'])
        self.assertEqual(len(a['components']),9);self.assertIsNone(_outcome_issue(a));self.assertIsNone(_source_issue(a))
        from extensions.reference.implementation import oriented_position_task,evaluate_tracking
        from tools.platform_registry import registry
        # Exact reuse of the existing timed evaluator, including its RMS diagnostics.
        from schemas.platform import BackendResult,Payload,Signal
        task=SessionInput.model_validate(self.cfg).task;raw=self.raw()
        p=next(s for s in task.observations if s.name=='tip_position')
        result=BackendResult(solver_status='completed',backend_id='backend.family_mujoco',model_id='mujoco_serial_bending_v1',
            signals=[Signal(spec=p,times_s=self.times[1:].tolist(),values=[r['tip_m'] for r in raw['samples'][1:]])],
            data=Payload(contract='family.backend_data',data={}),limitations=[],initial_state=task.initializer.parameters,seed=17)
        old=evaluate_tracking(oriented_position_task(task),result,RAW,registry(),'bf6-fixture')
        self.assertEqual(ev.metrics[:3],old.metrics);self.assertEqual(ev.constraints[0],old.constraints[0])

    def test_intermediate_position_or_axis_failure_cannot_hide_at_endpoint(self):
        raw=self.raw();raw['samples'][12]['tip_m'][1]+=.013
        _,a=self.accept(raw);self.assertFalse(a['accepted']);self.assertFalse(a['components']['evaluator:tracking_max_error']['passed'])
        raw=self.raw();raw['samples'][12]['tip_tool_axis_world']=(-np.asarray(raw['samples'][12]['tip_tool_axis_world'])).tolist()
        _,a=self.accept(raw);self.assertFalse(a['accepted']);self.assertFalse(a['components']['evaluator:tool_axis_direction']['passed'])
        self.assertTrue(a['components']['evaluator:tracking_max_error']['passed'])

    def test_missing_axis_wrong_grid_or_load_binding_cannot_pass(self):
        raw=self.raw()
        for r in raw['samples']:r.pop('tip_tool_axis_world')
        ev,a=self.accept(raw);self.assertEqual(ev.validity,'incomplete');self.assertIsNone(a['accepted'])
        raw=self.raw();raw['samples'][12]['time_s']+=.001
        ev,a=self.accept(raw);self.assertEqual(ev.validity,'invalid');self.assertIsNone(a['accepted'])
        raw=self.raw();raw.pop('rigid_tool_binding')
        _,a=self.accept(raw);self.assertIsNone(a['accepted'])

    def test_response_keeps_both_real_timed_constraints(self):
        raw=self.raw();out=dict(times_s=self.times.tolist(),tip_positions_m=[r['tip_m'] for r in raw['samples']],
            tip_tool_axes_world=[r['tip_tool_axis_world'] for r in raw['samples']])
        measure=task_measure(out,**self.adapter.control_search_options());self.assertEqual(measure['normalized_gap'],0)
        self.assertEqual(constraint_vectors(out,**self.adapter.control_search_options()).shape,(60,3))
        out['tip_tool_axes_world'][12]=(-np.asarray(out['tip_tool_axes_world'][12])).tolist()
        self.assertGreater(task_measure(out,**self.adapter.control_search_options())['normalized_gap'],0)
        bad=self.goal.model_dump(mode='json');bad['axis_vertices_world'][1]=[-1.,0.,0.]
        with self.assertRaises(ValueError):OrientedTrackingGoal.model_validate(bad)


if __name__=='__main__':unittest.main()
