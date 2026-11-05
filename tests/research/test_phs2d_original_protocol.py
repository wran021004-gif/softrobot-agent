"""Protocol and physical path admission; fixtures are not scientific evidence."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from extensions.reference.contracts import PassiveResponseGoalV2
from extensions.tendon_family.family_space import parse_space,parse_build,parameter_capabilities,resolved_request
from extensions.tendon_family.generated_serial import generate_family
from extensions.math_analysis.differentiation_router import withhold_gradient
from tools.platform_store import plain
from tools.state_io import digest
from tools.research.design import set_parameter
from tools.research.structure_research import dynamic_cost,parameters

ROOT=Path(__file__).resolve().parents[2]
def read(name):return json.loads((ROOT/name).read_text())

class OriginalProtocolTests(unittest.TestCase):
    def test_continuous_serialization_preserved(self):
        task=read('tasks/phs2d_admission_continuous_v1.json')['task']
        goal=plain(PassiveResponseGoalV2.model_validate(task['goal']['data']))
        self.assertNotIn('execution_protocol',goal)
        self.assertNotIn('unloaded_multistart',goal)

    def test_original_requires_fresh_initializer_and_cold_reset(self):
        goal=read('tasks/phs2d_original_ten_v1_1.json')['task']['goal']['data']
        self.assertTrue(PassiveResponseGoalV2.model_validate(goal).unloaded_multistart)
        for edit in [dict(allow_saved_state=True),dict(initial_source='qualified_unloaded'),dict(reset='same_complete_initial_state_each_episode'),dict(force_sampling='interval_end')]:
            with self.assertRaises(ValueError):PassiveResponseGoalV2.model_validate({**goal,**edit})

    def test_exact_complete_cost_and_stencil_cost(self):
        full=dict(task=read('tasks/phs2d_original_ten_v1_1.json')['task'])
        rep=dict(task=read('tasks/phs2d_original_representative_v1_1.json')['task'])
        continuous=dict(task=read('tasks/phs2d_admission_continuous_v1.json')['task'])
        self.assertEqual(dynamic_cost(full,1)['physics_steps'],352000)
        self.assertEqual(dynamic_cost(rep,1)['physics_steps'],96000)
        self.assertEqual(dynamic_cost(full,5)['physics_steps'],1760000)
        self.assertEqual(dynamic_cost(continuous,1)['physics_steps'],640000)

    def build(self):
        s=read('configs/research/family_space_phs2d_route_research_v2.json')
        r=dict(version='serial_family_generation_v2',family_space_identity=digest(s),segment_count=9,tendon_count=4)
        return s,resolved_request(s,r)

    def test_registered_holes_rebuild_real_geometry(self):
        s,r=self.build();rows=parameter_capabilities(s,r)
        path='guide_hole_positions_m.guide_1.tendon_0_hole.1'
        row=next(x for x in rows if x['parameter_id']==path)
        self.assertEqual(row['physical_component']['kind'],'physical_guide_hole')
        self.assertTrue(row['continuous_perturbation'])
        before=generate_family(parse_build(dict(space=s,request=r)))[0]
        new=deepcopy(r);set_parameter(new,path,row['current_value']+.0001)
        after=generate_family(parse_build(dict(space=s,request=new)))[0]
        part=lambda d:next(x for x in d['components'] if x['id']=='guide_1')
        self.assertNotEqual(part(before)['guide_holes'],part(after)['guide_holes'])
        self.assertEqual(len(after['tendons']),4)
        self.assertEqual(len([x for x in after['components'] if x['kind']=='flexible_segment']),9)
        self.assertFalse(any(x['parameter_id'].endswith('.0') and x['parameter_id'].startswith('guide_hole_positions_m') for x in rows))

    def test_no_domain_widening_or_axial_hole_derivative(self):
        old=read('configs/research/family_space_phs2d_admission_20261105_v1.json')
        self.assertEqual(plain(parse_space(old)),old)
        invalid=deepcopy(old);invalid['guide_hole_coordinate_domains_m']={'0':dict(minimum=-.001,maximum=.001,default=0.)}
        with self.assertRaisesRegex(ValueError,'ONLY_LOCAL_YZ'):parse_space(invalid)

    def test_route_domain_and_missing_authorization(self):
        s,r=self.build();path='guide_hole_positions_m.guide_1.tendon_0_hole.1'
        cfg=dict(task=dict(physical_problem=dict(mode='passive_unilateral_equilibrium')))
        candidate=dict(generation_version=r['version'],parameters=r,configuration=cfg)
        spec=dict(family_space=s,capabilities=['analysis'],mathematical_methods=dict(mechanism_structure_v1='fixture'),family_sensitivity_variables=dict(version='family_sensitivity_v2',variables=['segments.*.young_pa']))
        row=next(x for x in parameters(spec,candidate) if x['parameter_id']==path)
        self.assertFalse(row['mechanism_differentiation']['supported'])
        spec['family_sensitivity_variables']['variables']=[path]
        self.assertTrue(next(x for x in parameters(spec,candidate) if x['parameter_id']==path)['mechanism_differentiation']['supported'])
        set_parameter(r,path,1.)
        with self.assertRaisesRegex(ValueError,'OUTSIDE_FAMILY_DOMAIN'):generate_family(parse_build(dict(space=s,request=r)))

    def test_selected_parent_changes_use_registered_hole(self):
        from unittest.mock import patch
        from tools.research.structure_intent import compile_generation
        s,r=self.build();path='guide_hole_positions_m.guide_1.tendon_0_hole.1'
        candidate=dict(generation_version=r['version'],parameters=r,configuration=dict(task=dict(physical_problem={})))
        spec=dict(family_space=s,research_decisions=dict(analysis_interface='scientific_question_v4'),capabilities=['analysis'])
        value=dict(decision=dict(selected_candidate=dict(artifact_id='a'*64)),generation=dict(changes={path:.001}))
        with patch('tools.research.structure_intent.state',return_value=dict(spec=spec)),patch('tools.research.design.verify_candidate',return_value=candidate):
            result=compile_generation(None,value)
        self.assertEqual(result['generation']['guide_hole_positions_m']['guide_1']['tendon_0_hole'][1],.001)
        self.assertEqual(result['generation']['segment_count'],9)
        generate_family(parse_build(dict(space=s,request=result['generation'])))

    def test_switch_never_publishes_a_gradient(self):
        response=dict(derivatives=[1.,1.],normalized_derivatives=[2.,2.],samples=[dict(derivative=1.,normalized_derivative=2.)],
            consistency=dict(passed=True),implicit_sensitivity=dict(status='regular_implicit_gradient',gradient_trustworthy=True))
        withhold_gradient(response,'active_set_switch')
        self.assertEqual(response['derivatives'],[None,None])
        self.assertFalse(response['implicit_sensitivity']['gradient_trustworthy'])
        self.assertIsNone(response['samples'][0]['derivative'])
        self.assertFalse(response['consistency']['passed'])

    def test_real_solid_plate_rejects_oblique_cable_penetration(self):
        from extensions.tendon_family.passive import PassiveModel
        from extensions.tendon_family.route_validation import validate_routes
        s,r=self.build()
        # Legal hole center, but the approach crosses the solid plate outside
        # its cylindrical clearance. This is a test fixture, not a study result.
        r['guide_hole_positions_m']['guide_1']['tendon_0_hole'][1]=-.01
        design,_,physics=generate_family(parse_build(dict(space=s,request=r)))
        problem=read('tasks/phs2d_original_ten_v1_2.json')['task']['physical_problem']
        native=PassiveModel(physics,problem);native.design_components=design['components']
        result=validate_routes(native,[[0.]*native.model.nv])
        self.assertEqual(result['status'],'illegal')
        self.assertTrue(any(x['reason']=='cable_solid_intersection' for x in result['issues']))

if __name__=='__main__':unittest.main()
