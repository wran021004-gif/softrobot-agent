"""Archived failure and a few real model compilations; no passive solve or rollout."""
from copy import deepcopy
from io import BytesIO
from pydantic import ValidationError
import json
import unittest
import numpy as np

from schemas.platform import SessionInput
from tools.research.config import ROOT, resolve
from tools.research.design import family_configuration, numerical_binding
from extensions.tendon_family.family_space import parse_space, validate_request, GenerationRequestV2, parameter_capabilities, resolved_request, search_domains, decision_summary
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.mjcf import compile_xml, load_model
from extensions.tendon_family.scene import assemble_physical

PROFILE=ROOT/'configs/research/study_passive_open_interface_audit_v2.json'


class PassiveInterfaceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.spec=resolve(PROFILE)

    def request(self):
        return dict(version='serial_family_generation_v2',family_space_identity=self.spec['family_space_identity'],
            segment_count=2,tendon_count=2,segments={'0':dict(cells=1),'1':dict(cells=1)})

    def model(self,request):
        cfg,_,physics=family_configuration(self.spec['configuration'],self.spec['family_space'],request,'offline-parameter-audit')
        scene=assemble_physical(SessionInput.model_validate(cfg),physics)
        goal=cfg['task']['goal']['data']
        scene['control']=dict(tension_execution_mode='passive_fixed_payout_v1',solreflimit=goal['solreflimit'],solimplimit=goal['solimplimit'])
        xml=BytesIO();compile_xml(physics,scene,None,xml)
        return cfg,physics,load_model(xml=xml.getvalue().decode())

    def test_archived_failure_and_unchanged_complete_task(self):
        archived=json.loads((ROOT/'evidence/passive_interface_audit_20261107/c_failure.json').read_bytes())
        self.assertEqual(archived['failure']['stage'],'initial_forward')
        self.assertEqual(archived['failure']['initial_state_size'],128)
        self.assertFalse(archived['matrix_evidence']['project_elastic_hessian_constructed'])
        cost=archived['cost'][0]
        for k in ('gradient_calls','hessian_columns','optimizer_iterations','KKT_solves','physics_steps'):
            self.assertEqual(cost[k],0)
        g=archived['initial_geometry'];self.assertEqual(g['contact_count'],172)
        np.testing.assert_allclose(g['length_residual_m'],.808)
        old=resolve(ROOT/'configs/research/study_passive_research_capabilities_v1.json')
        self.assertEqual(self.spec['canonical_task'],old['canonical_task'])
        from tools.research_tasks import complete_phs_conditions
        from tools.research.structure_research import finite_time_discovery
        self.assertTrue(complete_phs_conditions(self.spec['configuration']['task']))
        self.assertNotEqual(finite_time_discovery(self.spec['configuration'])['status'],'not_applicable')
        self.assertEqual(self.spec['configuration']['task']['evaluator'],old['configuration']['task']['evaluator'])
        self.assertEqual(decision_summary(self.spec['family_space'],None,[])['executable_domain']['segment_counts'],None)

    def test_representative_parameters_reach_real_model(self):
        base=self.request();cfg,p,m=self.model(base)
        self.assertEqual((m.nv,m.nu),(4,0))
        np.testing.assert_allclose(list(p['fixed_payout_lengths_m'].values()),p['reference_lengths_m'])
        self.assertTrue(numerical_binding(cfg,self.spec)['numerical_model_identity'])
        changed=deepcopy(base)
        polygon=dict(kind='polygon',parameters={},outer_yz_m=[[-.003,-.003],[.005,-.003],[.005,.003],[-.003,.003]],holes_yz_m=[],angle_rad=0.)
        changed['segments']={'0':dict(cells=2,length_m=.15,young_pa=6e6,physical_parameters=dict(density_kg_m3=2200,curvature_y_rad_m=1.,viscosity_y_nm2_s=.001)),
            '1':dict(cells=3,sections=[polygon,deepcopy(polygon)])}
        cfg2,p2,m2=self.model(changed)
        self.assertEqual((m2.nv,m2.nu),(10,0))
        parts={x['entity']:x for x in p2['parts']}
        root=parts['segment_0_cell_0'];old=next(x for x in p['parts'] if x['entity']=='segment_0_cell_0')
        self.assertAlmostEqual(root['mass_kg']/old['mass_kg'],1.25)
        np.testing.assert_allclose(np.array(root['stiffness_nm_rad'])/old['stiffness_nm_rad'],3.2)
        self.assertAlmostEqual(root['damping_nm_s_rad'][0]/old['damping_nm_s_rad'][0],3.2)
        poly=parts['segment_1_cell_0']['section_properties']
        self.assertAlmostEqual(poly['area_m2'],.008*.006)
        np.testing.assert_allclose(poly['centroid_yz_m'],[.001,0.],atol=1e-18)
        self.assertGreater(np.linalg.norm(m2.qpos_spring),0.)
        for part in p2['parts']:
            bid=m2.body(part['entity']).id
            self.assertAlmostEqual(m2.body_mass[bid],part['mass_kg'])
            np.testing.assert_allclose(m2.body_ipos[bid],part['com_local_m'],atol=1e-16)
            self.assertAlmostEqual(sum(m2.body_inertia[bid]),np.trace(part['inertia_com_local_kg_m2']))
            if part.get('dofs'):
                np.testing.assert_allclose(m2.jnt_stiffness[part['dofs']],part['stiffness_nm_rad'])
                np.testing.assert_allclose(m2.dof_damping[part['dofs']],part['damping_nm_s_rad'])
        # Initial coordinates remain the frozen task's zeros; natural curvature
        # is the elastic reference, not permission to change initialization.
        self.assertTrue(all(v==0 for v in cfg2['task']['initializer']['parameters']['data']['qpos_rad'].values()))
        routed=deepcopy(base)
        routed.update(segment_count=3,tendon_count=3,segments={str(i):dict(cells=1) for i in range(3)})
        # Obtain typed source points through the generator, without inventing a model builder.
        design,_,initial=generate_family(dict(space=self.spec['family_space'],request=routed))
        route=deepcopy(design['tendons'][1]['points'])
        route[-1]['attachment'].update(part='payload',s=0.,position_m=[0.,-.005,0.])
        routed.update(route_overrides={'1':route},guide_hole_positions_m={'guide_1':{'tendon_1_hole':[0.,-.020,0.]}})
        tube=dict(kind='tube',parameters=dict(outer_radius_m=.008,inner_radius_m=.004),outer_yz_m=[],holes_yz_m=[],angle_rad=0.)
        routed['segments']['0']['sections']=[tube]
        routed['segments']['1']['interpolation']='step'
        cfg3,p3,m3=self.model(routed)
        self.assertAlmostEqual(next(x for x in p3['parts'] if x['entity']=='segment_0_cell_0')['section_properties']['area_m2'],np.pi*(.008**2-.004**2))
        self.assertFalse(np.allclose(p3['reference_lengths_m'],initial['reference_lengths_m']))
        self.assertEqual(cfg3['robot']['structure']['data']['tendons'][1]['points'][-1]['attachment']['part'],'payload')
        self.assertEqual(m3.nu,0)
        self.assertEqual((m3.nv,m3.ntendon),(6,3))
        self.assertEqual(next(c for c in cfg3['robot']['structure']['data']['components'] if c['id']=='segment_1')['interpolation'],'step')
        resolved=resolved_request(self.spec['family_space'],routed)
        np.testing.assert_allclose(list(resolved['payout_lengths_m'].values()),p3['reference_lengths_m'])
        rows=parameter_capabilities(self.spec['family_space'],routed)
        self.assertTrue(any(r['parameter_id']=='segments.0.physical_parameters.density_kg_m3' and r['effective_in_current_execution'] for r in rows))
        # Positive counts beyond the old caps are admitted, without building a
        # large chain or promising its physical qualification.
        validate_request(parse_space(self.spec['family_space']),GenerationRequestV2.model_validate(dict(version='serial_family_generation_v2',family_space_identity=self.spec['family_space_identity'],segment_count=33,tendon_count=65)))
        invalid=deepcopy(base);invalid['spans']=[dict(first_segment=1,last_segment=1,count=2)]
        with self.assertRaisesRegex(ValueError,'BASE_ONLY'):generate_family(dict(space=self.spec['family_space'],request=invalid))

    def test_open_search_bounds_and_passive_admission(self):
        from tools.research.contracts import FamilyMixedSearch
        from tools.research.search import request_guidance
        from tools.research.mixed_moves import initial,generation,next_move,candidate_seed
        space=self.spec['family_space'];grant=self.spec['family_search']
        q=FamilyMixedSearch.model_validate(dict(version='family_mixed_search_v1',family_space_identity=self.spec['family_space_identity'],
            variable_groups=['payout'],segment_counts=[2],tendon_counts=[2],screening_fidelity='diagnostic',objective='equilibrium_qualification',
            operating_point='standardized_initial_pretension',max_proposals=1,max_evaluations=1,evaluation_mode='passive_equilibrium',diagnostic_load_conditions=['unloaded']))
        with self.assertRaisesRegex(ValueError,'FINITE_SEARCH_BOUNDS_REQUIRED'):search_domains(space,q,grant)
        q=q.model_copy(update=dict(bounds={'payout':(.1,1.)}));search_domains(space,q,grant)
        point=initial(space,q);request=generation(space,q,point)
        generate_family(dict(space=space,request=request))
        moved,_,_=next_move(space,q,point,0,.25)
        self.assertNotEqual(moved['payout_lengths_m'],point['payout_lengths_m'])
        seed=self.request();seed['segments']['1']['interpolation']='step'
        with self.assertRaisesRegex(ValueError,'segment interpolation'):
            candidate_seed(space,q,dict(parameters=seed))
        old_style=deepcopy(self.spec);old_style['research_decisions'].pop('structure_search_interface')
        guidance=request_guidance(old_style)
        self.assertNotIn('CONIC',json.dumps(guidance))
        self.assertNotIn('evaluation_mode',guidance['search']['omit_legacy_fields'])
        from tests.research.test_passive_capabilities import passive_host
        from tools.research.design import generate_candidate
        from tools.research import analysis
        from tools.research.state import state
        with passive_host() as h:
            spec=state(h)['spec'];request=self.request();request['family_space_identity']=spec['family_space_identity']
            candidate=generate_candidate(h,request,dict(origin='offline-model-source-boundary'))['candidate']
            # The existing common contract already rejects this combination;
            # do not add another mode check in dispatch or weaken active basis binding.
            with self.assertRaisesRegex(ValidationError,'MUJOCO_REQUIRES_EXPLICIT_NATIVE_METHOD_AND_MODEL_SOURCE'):
                analysis.dispatch(h,dict(candidate=candidate,operation='mechanism_structure_v1',model_source='gvs',operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
                    mechanism_study=dict(operation='inspect',point_semantics='re_equilibrated',target=dict(quantity='constraint_active_set'),effect_semantics='mechanism_effect',load_condition='unloaded',max_evaluations=1)),
                    'offline-passive-wrong-source',guard=lambda *a:None,origin='engineering_preflight')
            self.assertEqual(state(h)['mathematical_evaluations'],0)
