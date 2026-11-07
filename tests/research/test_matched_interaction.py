"""Synthetic bilinear fixtures, never physical or Provider evidence."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from extensions.math_analysis.differentiation_router import matched_points,interaction_evidence
from tools.research.contracts import AnalysisRequest
from tools.research.scientific_intent import compile_question
from tools.research.state import state,update
from tools.research.structure_research import prepare_context,calculate
from tests.research.test_structure_mechanism_aplus import prepare,SyntheticNative
from tests.research.test_p63a_math_interface import diagnose


class BilinearNative(SyntheticNative):
    """Intentionally fabricated response with a known interaction coefficient."""
    def __init__(self,cfg):
        super().__init__(cfg)
        self.lengths=[p['length_m'] for p in cfg['robot']['structure']['data']['components'] if p['kind']=='flexible_segment']

    def mechanics(self,data,u):
        result=super().mechanics(data,u);a,b=self.lengths[:2]
        result['mass_matrix_kg_m2']=[[3*a+2*b+5*a*b]]
        return result


def compiled_fixture():
    h,c=prepare();spec=deepcopy(state(h)['spec'])
    spec['research_decisions']['analysis_interface']='scientific_question_v4';update(h,spec=spec)
    diagnose(h,c,'scientific_question')
    q=dict(version='scientific_question_v4',domain='structure',structure=dict(operation='interact',
        effect_semantics='mechanism_effect',parameter_paths=['segments.0.length_m','segments.1.length_m'],
        target=dict(quantity='mass_matrix',reduction='norm'),operating_point='frozen_task_initial_state',
        control_treatment='fixed_absolute_tensions',requested_budget=4))
    compiled=compile_question(h,q,tool_use_id='synthetic-four-point')
    assert compiled['status']=='ready',compiled
    return h,c,AnalysisRequest.model_validate(compiled['request'])


class InteractionTests(unittest.TestCase):
    def test_compiler_admits_exact_four_points_and_existing_worker_matches_conditions(self):
        h,c,q=compiled_fixture();candidate=h.store.artifact(c)
        context=prepare_context(state(h)['spec'],candidate,q.mechanism_study,[])
        self.assertEqual(context['evaluations'],4)
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',BilinearNative):
            raw=calculate(candidate['configuration'],dict(candidate=c),q,
                dict(actual_time_s=0.,u=[1.],qpos_rad=[0.],qvel_rad_s=[0.]),context)
        evidence=raw['structure_research'];interaction=evidence['interaction'];records=evidence['records']
        self.assertEqual(raw['status'],'computed',raw.get('reason'))
        self.assertEqual(len(records),4);self.assertEqual(evidence['cost']['evaluation_attempts'],4)
        self.assertEqual(len({r['matching_identity'] for r in records}),1)
        self.assertEqual(interaction['status'],'computed_local_interaction')
        self.assertEqual(evidence['method_selection']['method'],'matched_two_parameter_four_point_v1')
        self.assertEqual(evidence['method_selection']['direction_status'],'local_finite_interaction_estimate')
        self.assertEqual(evidence['parameterized_problem']['sensitivity_problem']['level'],'M0')
        x0,y0=records[0]['parameter_values'].values();x1=list(records[1]['parameter_values'].values())[0]
        y1=list(records[2]['parameter_values'].values())[1]
        self.assertAlmostEqual(interaction['interaction_effect'],5*(x1-x0)*(y1-y0))
        self.assertFalse(interaction['strict_derivative'])
        too_small=q.mechanism_study.model_copy(update=dict(max_evaluations=3))
        with self.assertRaisesRegex(ValueError,'requires 4'):prepare_context(state(h)['spec'],candidate,too_small,[])

    def fixture_records(self):
        parameters=[dict(parameter_id=p,current_value=1.,minimum=0.,maximum=10.,continuous_perturbation=True) for p in ('x','y')]
        points=matched_points(parameters);records=[]
        for i,p in enumerate(points):
            x,y=p['parameter_values'].values()
            records.append(dict(record_index=i,parameter_values=p['parameter_values'],matching_identity='matched-fixture',
                observation=dict(status='computed',value=3*x+2*y+5*x*y,unit='fixture_unit'),
                mechanics=dict(constraint_state=dict(qualified=True),equilibrium=dict(equilibrium=dict(active=[0],positive=[0])))))
        return points,records

    def test_independent_and_interaction_effects(self):
        points,records=self.fixture_records();result=interaction_evidence(points,records)
        self.assertAlmostEqual(result['independent_effects']['delta1'],.8)
        self.assertAlmostEqual(result['independent_effects']['delta2'],.7)
        self.assertAlmostEqual(result['interaction_effect'],.05)
        self.assertIsNone(result['error_bound'])

    def test_branch_change_is_a_finite_contrast_invalid_or_unmatched_is_incomplete(self):
        points,records=self.fixture_records()
        records[-1]['mechanics']['equilibrium']['equilibrium']['active']=[1]
        result=interaction_evidence(points,records)
        self.assertTrue(result['branch_changed']);self.assertFalse(result['strict_derivative'])
        for modification in ('invalid','mismatch','missing'):
            changed=deepcopy(records)
            if modification=='invalid':changed[-1]['observation'].update(status='unavailable',value=None)
            elif modification=='mismatch':changed[-1]['matching_identity']='different-control-fixture'
            else:changed.pop()
            result=interaction_evidence(points,changed)
            self.assertEqual(result['status'],'incomplete');self.assertIsNone(result['interaction_effect'])
            self.assertIsNone(result['independent_effects'])


if __name__=='__main__':unittest.main()
