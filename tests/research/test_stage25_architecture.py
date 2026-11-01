"""Focused V4/admission tests and small real native observations; no campaign."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import numpy as np
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from extensions.math_analysis.mechanism_registry import PRIMITIVES,mechanism_ids,observe
from extensions.tendon_family.contracts import ConstrainedObservation
from extensions.tendon_family.passive import PassiveModel
from extensions.tendon_family.passive_equilibrium import mechanics
from tools.research import core,analysis
from tools.research.scientific_intent import compile_question,question_schema
from tools.research.state import state
from tools.research_tasks import task_adapter
from tests.research.test_constrained_mechanics import physical_fixture,prepared_host,passive_question,ROOT
from tests.research.test_p63g3_action_handoff import diagnosis

OUT=ROOT/'runs/stage25_validation'


def target_for(quantity):
    result=dict(quantity=quantity,reduction='norm')
    if quantity in ('directional_drive','directional_acceleration_bounds','directional_tendon_row_residual','motion_decoupling','directional_material_response'):
        result['direction_world']=[0.,1.,0.]
    if quantity in ('constraint_output_row_residual','all_tendon_output_row_residual'):
        result['projection_world']=[[0.,0.,1.]]
    return result


class Stage25ArchitectureTests(unittest.TestCase):
    def test_registry_schema_compiler_and_physical_admission(self):
        h,c=prepared_host();candidate=h.store.artifact(c)
        with patch.object(core,'guard'):core.dispatch(h,diagnosis(c,'mechanism_research'),'stage25-diagnose')
        schema=question_schema(state(h)['spec'],candidate,action='mechanism_research')
        Draft202012Validator.check_schema(schema);validator=Draft202012Validator(schema)
        ids=schema['$defs']['PhysicalMechanismTarget']['properties']['quantity']['enum']
        self.assertEqual(ids,mechanism_ids('passive_unilateral_equilibrium'))
        self.assertNotIn('material_point_force_response',ids);self.assertNotIn('constraint_tip_row_residual',ids)
        self.assertNotIn('control',schema['properties'])
        for quantity in ids:
            q=passive_question(quantity=quantity);q['structure']['target']=target_for(quantity)
            with self.subTest(quantity=quantity):
                validator.validate(q)
                self.assertEqual(compile_question(h,q,tool_use_id='inspect-'+quantity)['status'],'ready')
        for effect in ('mechanism_effect','re_equilibrated_passive_response'):
            q=passive_question('differentiate','tangent_compliance',5);q['structure']['effect_semantics']=effect
            q['structure']['target'].pop('goal')
            self.assertTrue(list(validator.iter_errors(q)))
            self.assertEqual(compile_question(h,q,tool_use_id='missing-goal')['reason'],'EXPLICIT_MECHANISM_GOAL_REQUIRED')
        q=passive_question('differentiate','constraint_active_set',5)
        self.assertTrue(list(validator.iter_errors(q)))
        self.assertIn('MECHANISM_OPERATION_NOT_IMPLEMENTED',compile_question(h,q,tool_use_id='discrete-gradient')['reason'])
        q=passive_question(quantity='constraint_output_row_residual');q['structure']['target'].pop('material_s')
        self.assertTrue(list(validator.iter_errors(q)))
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        from tests.research.test_r3_b_stage1 import integrated_host
        a,ac=integrated_host();active=question_schema(state(a)['spec'],a.store.artifact(ac),'mechanism_research')
        self.assertEqual(active['$defs']['PhysicalMechanismTarget']['properties']['quantity']['enum'],mechanism_ids('active_ideal_tension'))
        choices=active['$defs']['ScientificStructureV4']['properties']
        self.assertNotIn('closed_loop_performance',choices['effect_semantics']['enum'])
        self.assertNotIn('re_equilibrated_passive_response',choices['effect_semantics']['enum'])
        self.assertNotIn('closed_loop',choices['control_treatment']['enum'])

    def test_directional_lower_upper_and_unit_contracts(self):
        row=ConstrainedObservation(name='directed',quantity='material_displacement',load_condition='lateral',
            minimum=-.001,maximum=.002,reduction='component',direction_world=[0.,0.,1.],unit='m')
        self.assertEqual(row.physical_unit,'m')
        for change in (dict(minimum=.003),dict(direction_world=[0.,0.,2.]),dict(unit='N')):
            with self.assertRaises(ValidationError):ConstrainedObservation.model_validate({**row.model_dump(),**change})
        with self.assertRaises(ValidationError):ConstrainedObservation(name='bad',quantity='tip_displacement',load_condition='lateral',reduction='projection_norm',projection_world=[[0,1,0],[0,1,0]])
        old=dict(name='historical',quantity='material_displacement',load_condition='lateral',material_s=.5,maximum=.001)
        self.assertEqual(ConstrainedObservation.model_validate(old).model_dump(),old)

    def test_passive_task_actions_and_no_fabricated_dynamic_constraint(self):
        h,c=prepared_host();cfg=h.store.artifact(c)['configuration'];adapter=task_adapter(cfg)
        self.assertFalse(adapter.ppo_applicability()['supported'])
        self.assertIsNone(adapter.execution_requirements()['protocol_id'])
        self.assertEqual(adapter.describe()['family'],'passive_unilateral_equilibrium')
        requirement=adapter.analysis_requirements({})
        self.assertFalse(requirement.constraints);self.assertEqual(requirement.horizon_semantics,'static_load_cases')
        from tools.research.agent import decision_packet,plan_schema
        packet=decision_packet(h);brief=packet['research']
        self.assertFalse(packet['candidate_profile_bindings'][0]['executable_under_current_profile'])
        self.assertTrue({'generate','diagnose','stop'}<=set(brief['actions']))
        self.assertFalse(set(brief['actions'])&{'initialize_control','execute','physical_replay','select'})
        schema=plan_schema(['diagnose'],study=state(h)['spec'])
        self.assertEqual(schema['properties']['next_research_action']['anyOf'][0]['enum'],['mechanism_research'])

    def test_real_native_coverage_and_unilateral_projection(self):
        _,_,_,_,physics,problem=physical_fixture();native=PassiveModel(physics,problem)
        record=mechanics(native,'lateral',.5,direction_world=[0.,1.,0.])
        self.assertTrue(record['constraint_state']['qualified']);self.assertNotIn('material_point_force_response',record)
        observations={}
        for quantity in mechanism_ids('passive_unilateral_equilibrium'):
            value=observe(record,target_for(quantity));observations[quantity]=value
            self.assertEqual(value['status'],'computed',(quantity,value))
        self.assertEqual(observe(record,dict(quantity='material_point_force_response'))['value'],record['tangent_compliance'])
        self.assertEqual(record['equilibrium']['solver_settings']['version'],'passive_equilibrium_v1')
        geometric=observe(record,target_for('all_tendon_output_row_residual'))
        boundary=deepcopy(record);boundary['equilibrium']['equilibrium']['positive']=[False]
        effective=observe(boundary,target_for('constraint_output_row_residual'))
        self.assertAlmostEqual(effective['value'],1.)
        self.assertLess(geometric['value'],1.)
        from tests.research.test_r3_b_stage1 import integrated_host
        from extensions.tendon_family.mujoco_analysis import NativeModel
        a,ac=integrated_host();active=NativeModel(a.store.artifact(ac)['configuration'])
        data=active.restore(dict(dof_order=active.order,tendon_order=active.tendons,qpos_rad=active.scene['qpos_rad'],qvel_rad_s=active.scene['qvel_rad_s'],actual_time_s=0.),comparable=True)
        actual=active.mechanics(data,active.limits[:,0],material_s=.35)
        self.assertEqual(observe(actual,dict(quantity='material_point_jacobian',reduction='norm',material_s=.35))['status'],'computed')
        self.assertGreater(np.linalg.norm(actual['input_force_map_nm_n']),0.)
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'coverage_numerics.json').write_text(json.dumps(dict(scope='Real native geometry and hard unilateral equilibrium, no integration or task acceptance',
            passive=dict(mechanics=record,observations=observations,cost=native.cost),active=dict(mechanics=actual,cost=active.cost)),indent=2),encoding='utf8')

    def test_real_frozen_multiload_worker_and_diagnostic_bounds(self):
        fixture=physical_fixture();problem=fixture[-1]
        problem['loads'].append(dict(name='vertical',material_s=.5,force_world_n=[0.,0.,.01]))
        problem['observations']=[dict(name='minimum_y',quantity='material_displacement',load_condition='lateral',
            material_s=.5,reduction='component',direction_world=[0.,1.,0.],minimum=.0001,unit='m'),
            dict(name='tip_plane',quantity='tip_displacement',load_condition='lateral',projection_world=[[0.,1.,0.],[0.,0.,1.]],reduction='projection_norm',maximum=.001),
            dict(name='ratio_free',quantity='displacement_difference',load_condition='lateral',material_s=.5,material_scale=2.,maximum=0.)]
        with patch('tests.research.test_constrained_mechanics.physical_fixture',return_value=fixture):h,c=prepared_host()
        with patch.object(core,'guard'):core.dispatch(h,diagnosis(c,'mechanism_research'),'loads-diagnose')
        q=passive_question('compare','re_equilibrated_position_response',1)
        q['structure'].update(comparison_load_conditions=['vertical','unloaded'],load_aggregation='maximum')
        Draft202012Validator(question_schema(state(h)['spec'],h.store.artifact(c),'mechanism_research')).validate(q)
        compiled=compile_question(h,q,tool_use_id='compare-frozen-loads');self.assertEqual(compiled['status'],'ready',compiled)
        result=analysis.dispatch(h,compiled['request'],'stage25-real-multiload',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(result['status'],'computed',result)
        saved=h.store.artifact(state(h)['analysis_results'][-1]);raw=saved['structure_research'];cases=raw['load_comparison']['cases']
        self.assertEqual([r['load_condition'] for r in cases],['lateral','vertical','unloaded'])
        self.assertTrue(raw['load_comparison']['assembly_unchanged']);self.assertEqual(raw['cost']['model_builds'],1)
        self.assertEqual(raw['cost']['equilibrium_solves'],3);self.assertEqual(raw['cost']['physics_steps'],0)
        self.assertEqual(cases[0]['mechanics']['components']['constraint_payout_m'],cases[1]['mechanics']['components']['constraint_payout_m'])
        self.assertFalse(cases[0]['task_observations'][0]['within_mathematical_limit'])
        self.assertTrue(cases[0]['task_observations'][1]['within_mathematical_limit'])
        self.assertEqual(result['task_acceptance'],'unmeasured');self.assertEqual(state(h)['mathematical_evaluations'],1)
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'multiload.json').write_text(json.dumps(dict(question=q,result=saved,study_cost=state(h)['analysis_costs']),indent=2),encoding='utf8')


if __name__=='__main__':unittest.main()
