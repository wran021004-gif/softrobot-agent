"""Focused new risks: task binding, guess provenance, frozen reporting, v2 scope."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from schemas.platform import SessionInput, EvidenceRef
from tools.state_io import digest
from extensions.tendon_family.gvs_profile import (reach_input,profile_input,checked_profile,
    checked_reach,reach_numerical,reach_assessment,execution_scope,prepare_execution,SampledSettling)
from extensions.tendon_family.gvs_reporting import summarize


class ParameterizedReachTests(unittest.TestCase):
    def test_task_parameters_preparation_and_dependency_identity(self):
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.gvs_nmpc import ReachNMPCController,resolve_gvs_nmpc_control,workspace_key
        baseline=SessionInput.model_validate(reach_input('a'))
        joint=physics_for(baseline)['dofs'][0]
        inp=SessionInput.model_validate(reach_input('b',target_m=[.29,.05,.19],
            initial=dict(qpos_rad={joint:.001},qvel_rad_s={joint:.002}),
            timing=dict(duration_s=.4),recipe=dict(horizon=8,holding_brake_lead_s=.02),
            settling=dict(window_s=.04,position_limit_m=.009,speed_limit_m_s=.015)))
        p=checked_reach(inp)
        from tools.platform_tools import simulation_preflight
        from tools.platform_registry import registry
        from schemas.platform_operations import Simulate
        preflight=simulation_preflight(inp,Simulate(),registry())
        self.assertEqual(preflight['cost']['backend_solves'],1)
        self.assertEqual(execution_scope(preflight['prepared'].effective),execution_scope(inp))
        self.assertNotEqual(execution_scope(inp),execution_scope(baseline))
        self.assertNotEqual(workspace_key(inp.task,inp.robot,p.recipe),workspace_key(baseline.task,baseline.robot,checked_reach(baseline).recipe))
        plan=resolve_gvs_nmpc_control(inp,physics_for(inp))
        self.assertEqual(plan['task']['goal']['data']['target_m'],[.29,.05,.19])
        self.assertEqual(plan['effective_parameters']['horizon'],8)
        self.assertEqual(plan['effective_parameters']['holding_brake_lead_s'],.02)
        saved=[]
        def save(value,kind):
            saved.append((kind,value));return EvidenceRef(artifact_id=digest(value))
        controller=ReachNMPCController(inp.policy.controller.parameters.data,.01)
        prepare_execution(SimpleNamespace(save_artifact=save),controller,inp)
        self.assertEqual(controller.preparation['execution_scope'],execution_scope(inp))
        self.assertEqual(controller.preparation['status'],'completed')
        self.assertEqual(len(controller.profile['numerical']['warm_guess']['tensions']),8)
        self.assertFalse(controller.preparation['nominal_is_current_target_solution'])
        self.assertEqual(controller.preparation['nominal_target_world_m'],[.29,.035,.19])
        artifacts={digest(value):value for _,value in saved}
        historical=artifacts[controller.preparation['historical_source']['artifact_id']]
        self.assertEqual(historical['coordinate_order'],controller.preparation['coordinate_order'])
        self.assertEqual(historical['nominal']['u0'],controller.profile['numerical']['nominal']['u0'])
        cold=inp.model_copy(deep=True)
        cold.policy.controller.parameters.data['numerical_source']='initial_state_pretension'
        material=reach_numerical(cold)
        self.assertFalse(material['provenance']['reused'])
        self.assertGreater(max(abs(v) for v in material['nominal']['q0']),0.)

    def test_scope_evidence_and_fixed_baseline(self):
        from extensions.tendon_family import gvs_profile
        inp=SessionInput.model_validate(reach_input('a',target_m=[.29,.05,.19]))
        assessment=reach_assessment(inp)
        self.assertEqual(assessment['technical_compatibility']['status'],'supported')
        self.assertEqual(assessment['historical_evidence']['status'],'unvalidated_configuration')
        self.assertFalse(assessment['historical_evidence']['historical_task_match'])
        old=SessionInput.model_validate(profile_input('old'));original=checked_profile(old)
        changed=old.model_copy(deep=True);changed.task.goal.data['target_m'][1]=.05
        with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):checked_profile(changed)
        wrong=inp.model_copy(deep=True);wrong.robot.structure.data['tendons'][0]['force_limit_n']+=1
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_PHYSICS'):checked_reach(wrong)
        bad=copy.deepcopy(original);bad['numerical']['tendon_order'].reverse()
        with patch.object(gvs_profile,'load_profile',return_value=bad):
            with self.assertRaisesRegex(ValueError,'NUMERICAL_IDENTITY'):reach_numerical(inp)

    def test_report_uses_frozen_acceptance(self):
        inp=SessionInput.model_validate(reach_input('report'))
        rows=[dict(time_s=k*.01,tip_m=[.29,.035,.19],tension_n=[1.]) for k in range(36)]
        motion=[dict(time_s=r['time_s'],tip_error_m=.008,tip_speed_m_s=.025,
            rate_projection_residual_rad_m_s=0.,contacts=0) for r in rows]
        result=dict(solver_status='completed',data=dict(data=dict(timings_s={})))
        evaluation=dict(validity='valid',task_success=True)
        old=summarize(inp.task,result,evaluation,rows,[],motion,[5.])
        new=summarize(inp.task,result,evaluation,rows,[],motion,[5.],
            SampledSettling(window_s=.03,position_limit_m=.009,speed_limit_m_s=.03))
        self.assertFalse(old['sampled_settling']['passed'])
        self.assertTrue(new['sampled_settling']['passed'])
        self.assertEqual(new['sampled_settling']['window_s'],.03)
        self.assertEqual(new['official_task_success'],old['official_task_success'])


if __name__=='__main__':unittest.main()
