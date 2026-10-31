"""Offline C2 contract/compiler/wire checks. All numerical outputs are fabricated."""
from copy import deepcopy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from jsonschema import Draft202012Validator
from tools.platform_store import plain
from tools.research import agent, analysis, core
from tools.research.contracts import AnalysisRequest, ScientificQuestion
from tools.research.config import ROOT, resolve
from tools.research.control_correction import corrected_tensions
from tools.research.nonlinear_capability import T1, T2, T1_OPERATION, T2_OPERATION
from tools.research.scientific_intent import compile_question
from tools.research.state import state, update, save
from tools.research.task_constraints import mathematical_method_view
from tools.state_io import read, atomic_json
from tests.research.test_p63a_math_interface import generate, t1_request, diagnose, offline_dispatch, synthetic_t1
from tests.research.test_p63b3_action_interface import provision
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_p63c2_scientific_intent import question_host


def mechanism_question(operation='differentiate', **changes):
    return dict(version='scientific_question_v2',operation=operation,effect_semantics='mechanism_effect',
        parameter_paths=['segments.0.length_m'],target=dict(quantity='tip_acceleration_input_map',reduction='norm'),
        operating_point='frozen_task_initial_state',control_treatment='fixed_absolute_tensions',
        requested_budget=5,**changes)


class MechanismQuestionV2Tests(unittest.TestCase):
    """Synthetic numerical fixtures; real native check is a separate bounded command."""
    def prepare(self):
        h=provision();spec=deepcopy(state(h)['spec'])
        spec['research_decisions']['analysis_interface']='scientific_question_v2'
        spec['mathematical_methods']['mechanism_structure_v1']='Synthetic interface fixture only'
        update(h,spec=spec);c=generate(h);diagnose(h,c,'scientific_question')
        return h,c

    def compile(self,h,q):return compile_question(h,q,tool_use_id='synthetic-v2')

    def test_v2_schema_binding_and_v1_gate(self):
        from tools.research.contracts import MechanismQuestionV2
        from tools.research.scientific_intent import question_contract
        h,c=self.prepare();q=mechanism_question();before=deepcopy(state(h))
        out=self.compile(h,q);self.assertEqual(out['status'],'ready')
        self.assertEqual(out['request']['candidate'],c)
        self.assertEqual(out['request']['protocol'],before['spec']['analysis_protocol'])
        self.assertEqual(state(h)['mathematical_evaluations'],before['mathematical_evaluations'])
        Draft202012Validator(AnalysisRequest.model_json_schema()).validate(out['request'])
        self.assertIs(question_contract(state(h)['spec']),MechanismQuestionV2)
        legacy=question_host();old=generate(legacy);diagnose(legacy,old,'scientific_question')
        self.assertEqual(self.compile(legacy,q)['status'],'needs_choice')
        self.assertNotIn('mechanism_structure_v1',mathematical_method_view(legacy,old)['methods'])

    def test_semantics_discrete_groups_budget_and_no_silent_substitution(self):
        h,c=self.prepare()
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',side_effect=AssertionError('NO_NATIVE_WORK')):
            for semantics in ('closed_loop_performance','re_equilibrated_passive_response'):
                q=mechanism_question();q['effect_semantics']=semantics
                self.assertEqual(self.compile(h,q)['status'],'unsupported')
            for path in ('segment_count','tendon_count','segments.0.cells','tendon_parameters.length_servo_gain_n_m'):
                q=mechanism_question();q['parameter_paths']=[path]
                self.assertEqual(self.compile(h,q)['status'],'unsupported')
            q=mechanism_question();q.update(parameter_paths=[],parameter_group='segment_lengths')
            self.assertEqual(self.compile(h,q)['status'],'blocked')
            q=mechanism_question();q['requested_budget']=4
            self.assertEqual(self.compile(h,q)['status'],'blocked')
            q=mechanism_question();q['target']='holding_max_speed_m_s'
            self.assertEqual(self.compile(h,q)['reason'],'TASK_TARGET_REQUIRES_M1_OR_M2_TASK_RESPONSE')
            q=mechanism_question();q['operating_point']='preserved_physical_state'
            self.assertEqual(self.compile(h,q)['reason'],'WORKING_POINT_MAPPING_NOT_IMPLEMENTED')
            q=mechanism_question();q['target']['reduction']='identity'
            self.assertEqual(self.compile(h,q)['status'],'unsupported')
        self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_existing_parameter_grant_and_direct_dispatch_gate_remain_authoritative(self):
        h,c=self.prepare();q=mechanism_question();request=self.compile(h,q)['request']
        spec=deepcopy(state(h)['spec']);spec['family_sensitivity_variables']['variables']=['segments.1.length_m']
        update(h,spec=spec)
        self.assertEqual(self.compile(h,q)['reason'],'ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED')
        spec['mathematical_methods'].pop('mechanism_structure_v1');update(h,spec=spec)
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')):
            out=analysis.dispatch(h,request,'v2-ungranted',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(out['reason'],'EXPLICIT_V2_FROZEN_MECHANISM_GRANT_AND_SCOPE_REQUIRED')
        self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_inspection_compare_and_scientific_choices_inherit_diagnose(self):
        h,c=self.prepare();other=generate(h,(.165,.11))
        q=mechanism_question('inspect');q.update(parameter_paths=[],requested_budget=1,target=dict(quantity='mass_matrix'))
        out=self.compile(h,q);self.assertEqual(out['status'],'ready')
        self.assertEqual(out['required_evaluations'],1)
        q['operation']='compare';q['requested_budget']=2;q['comparison_candidates']=[other]
        out=self.compile(h,q);self.assertEqual(out['status'],'ready');self.assertEqual(out['required_evaluations'],2)
        from tests.research.test_p63b5_native_entry import plan
        selected=plan(c);selected['decision'].update(requested_budget=5,selected_variables=['segments.0.length_m'])
        with patch.object(core,'guard'):core.dispatch(h,selected,'v2-bound-plan')
        q=mechanism_question();q.pop('parameter_paths');q.pop('requested_budget')
        out=self.compile(h,q);self.assertEqual(out['status'],'ready')
        self.assertEqual(out['request']['mechanism_study']['parameter_paths'],['segments.0.length_m'])

    def test_registered_units_dimensions_frames_and_active_tendon_scope(self):
        from extensions.math_analysis.mechanism_registry import observe,catalog
        from tools.research.contracts import MechanismTarget
        mechanics=dict(time_s=0.,qpos_rad=[0.]*3,qvel_rad_s=[0.]*3,
            coordinates=dict(dof_order=['a','b','c'],tendon_order=['t0','t1','t2']),
            input_bounds_n=[[0.,8.]]*3,actual_tensions_n=[1.]*3,
            tip_jacobian_m_rad=np.eye(3).tolist(),tendon_jacobian_m_rad=np.eye(3).tolist(),
            input_force_map_nm_n=(-np.eye(3)).tolist(),mass_matrix_kg_m2=np.eye(3).tolist(),
            tip_acceleration_input_map_m_s2_n=np.diag([1.,2.,3.]).tolist(),mass_balance_residual_inf_nm=0.,
            function_metrics=dict(drive_singular_values_m_s2_n=[3.,2.,1.],instantaneous_speed_derivative_range_m_s2=None))
        for quantity,unit in [('mass_matrix','kg*m^2'),('tip_jacobian','m/rad'),('input_force_map','N*m/N')]:
            out=observe(mechanics,dict(quantity=quantity));self.assertEqual(out['unit'],unit)
            self.assertEqual(out['metadata']['actual_shape'],[3,3]);self.assertIn('named hinges',out['metadata']['frame'])
        out=observe(mechanics,dict(quantity='tip_acceleration_input_map',reduction='directional_norm',direction_world=[0.,1.,0.]))
        self.assertEqual(out['value'],2.);self.assertEqual(out['unit'],'m/s^2/N')
        self.assertEqual(observe(mechanics,dict(quantity='tendon_row_projection'))['value'],[0.]*3)
        self.assertEqual(observe(mechanics,dict(quantity='instantaneous_braking'))['status'],'not_applicable')
        self.assertIn('constrained_motion_subspace',catalog()['primitives'])
        self.assertEqual(observe(mechanics,dict(quantity='constrained_motion_subspace'))['reason'],'MECHANISM_PHYSICAL_MODE_MISMATCH')
        for bad in (dict(quantity='__import__("os")'),dict(quantity='tip_jacobian',reduction='directional_norm',direction_world=[2.,0.,0.])):
            with self.assertRaises(ValueError):MechanismTarget.model_validate(bad)
        mechanics['mass_matrix_kg_m2']=[[1.]]
        with self.assertRaisesRegex(ValueError,'DIMENSION'):observe(mechanics,dict(quantity='mass_matrix'))

    def test_two_scales_are_local_secants_and_direction_can_remain_unresolved(self):
        from extensions.math_analysis.differentiation_router import differentiate,stencil
        parameter=dict(current_value=.16,minimum=.08,maximum=.24,unit='m',continuous_perturbation=True)
        seen=[]
        def sample(x):
            seen.append(x);return dict(record_index=len(seen),observation=dict(value=x*x,unit='m'))
        baseline=sample(.16)
        r=differentiate(parameter,baseline,sample,goal='increase')
        np.testing.assert_allclose(r['derivatives'],[.32,.32],atol=1e-12)
        self.assertEqual(len(seen),5);self.assertTrue(r['consistency']['passed'])
        self.assertGreater(r['suggested_delta'],0);self.assertFalse(r['strict_derivative'] or r['descent_certificate'])
        self.assertTrue(all(.08<=x<=.24 for x in seen))
        def flat(x):return dict(record_index=0,observation=dict(value=1.,unit='1'))
        self.assertIsNone(differentiate(parameter,flat(.16),flat,goal='increase')['suggested_delta'])
        self.assertEqual(stencil({**parameter,'current_value':.08})['scheme'],'one_sided_second_order_two_scales')

    def test_production_orchestration_rebuilds_and_rechecks_proposal_with_synthetic_native(self):
        from tools.research.structure_research import calculate,prepare_context
        h,c=self.prepare();candidate=h.store.artifact(c);q=mechanism_question('optimize');q['requested_budget']=6
        request=AnalysisRequest.model_validate(self.compile(h,q)['request'])
        class SyntheticNative:
            def __init__(self,cfg):
                self.length=next(p['length_m'] for p in cfg['robot']['structure']['data']['components'] if p['id']=='segment_0')
                self.physics=dict(identity='synthetic-native-'+str(self.length));self.order=['q'];self.tendons=['t']
                self.scene=dict(qpos_rad=[0.],qvel_rad_s=[0.])
                self.cost=dict(model_builds=1,mechanics_evaluations=0,physics_steps=0,rollouts=0)
            def restore(self,point,**kw):return None
            def reconstruct(self,point):return point,None
            def checkpoint(self,data):return dict(fixture='Synthetic state; no engine')
            def mechanics(self,data,u):
                self.cost['mechanics_evaluations']+=1
                return dict(time_s=0.,qpos_rad=[0.],qvel_rad_s=[0.],
                    coordinates=dict(dof_order=['q'],tendon_order=['t']),actual_tensions_n=[1.],input_bounds_n=[[0.,8.]],
                    tip_acceleration_input_map_m_s2_n=[[self.length],[0.],[0.]],mass_matrix_kg_m2=[[self.length]])
        context=prepare_context(state(h)['spec'],candidate,request.mechanism_study,[])
        before=deepcopy(state(h)['candidates'])
        point=dict(actual_time_s=0.,u=[1.],native_replay={})
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',SyntheticNative):
            result=calculate(candidate['configuration'],dict(candidate=c),request,point,context)
        self.assertEqual(result['status'],'computed');raw=result['structure_research']
        self.assertLessEqual(raw['cost']['model_builds'],6);self.assertIn('local_search',raw)
        self.assertGreater(raw['structure_direction']['delta'],0)
        self.assertFalse(raw['structure_direction']['formal_candidate_created'])
        self.assertEqual(state(h)['candidates'],before)

    def test_l0_l1_wire_and_reporter_preserve_direction_as_diagnostic_only(self):
        from tools.research.research_context import agent_decision_brief,mathematical_decision_view
        from tools.research.evidence_views import result_card
        from tools.research import reporter
        from schemas.research_reporting import ScientificReport
        from schemas.platform_analysis import TaskAnalysisRequirement
        from tests.research.test_information_flow import packet
        h,c=self.prepare();compiled=self.compile(h,mechanism_question())
        def contained(command,log,timeout,**kw):
            request=read(Path(command[-1]));q=AnalysisRequest.model_validate(request['query'])
            direction=dict(parameter_path='segments.0.length_m',parameter_unit='m',delta=-.0008,suggested_value=.1592,
                full_task_improvement_verified=False,formal_candidate_created=False,proposal_only=True)
            raw=dict(operation='differentiate',target=dict(quantity='tip_acceleration_input_map',reduction='norm'),
                baseline=dict(value=3.),records=[dict(observation=dict(value=3.,unit='m/s^2/N'))],
                structure_direction=direction,sensitivity=dict(direction_status='locally_consistent'),
                unsupported_conclusions=['task success','strict derivative'],cost=dict(model_builds=5,physics_steps=0,rollouts=0))
            value=analysis.scoped_result(dict(status='computed',operation=q.operation,binding=request['binding'],
                structure_research=raw,task_acceptance='unmeasured',fixture='Synthetic fixture; no actual numerical work'),
                TaskAnalysisRequirement.model_validate(request['task_analysis']),
                request['analysis_applicability'],q)
            atomic_json(Path(command[-1]).with_name('result.json'),value)
            return SimpleNamespace(returncode=0)
        candidates=deepcopy(state(h)['candidates'])
        with patch('tools.service_execution._run_contained',side_effect=contained):
            out=analysis.dispatch(h,compiled['request'],'v2-synthetic',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(state(h)['mathematical_evaluations'],5);self.assertEqual(state(h)['candidates'],candidates)
        ref=out['reference'];raw=deepcopy(h.store.artifact(ref));card=result_card(h,ref)
        self.assertEqual(card.evidence_summary.claim_kind,'NUMERICAL_DIAGNOSTIC')
        projected=mathematical_decision_view(plain(card))
        self.assertEqual(projected['structure_research']['structure_direction']['delta'],-.0008)
        brief=agent_decision_brief(h);l0=brief['mechanism_research'];self.assertTrue(l0['evidenced_direction'])
        self.assertTrue(brief['mathematical_research'])
        for forbidden in ('qpos_rad','mass_matrix','segments.0.length_m','solver'):self.assertNotIn(forbidden,json.dumps(l0))
        l1=core.read_evidence(h,l0['details_query'],record_read=False)
        self.assertTrue(l1['parameters']);self.assertTrue(l1['mechanisms']['primitives'])
        report=reporter.assemble(h,[ref]);self.assertEqual(report.results[0].mathematics.claim.conclusion,'diagnostic')
        with self.assertRaises(ValueError):ScientificReport.model_validate({**plain(report),'structure_direction':dict(delta=999.)})
        self.assertEqual(h.store.artifact(ref),raw)
        wires=run_fixture(h,[None]);wire=wires[0]
        schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']=='research_analysis')
        self.assertIn('operation',schema['properties']);self.assertNotIn('candidate',schema['properties'])
        self.assertEqual(packet(wire)['tool_continuation']['analysis_handoff']['interface'],'scientific_question_v2')


if __name__=='__main__':unittest.main()
