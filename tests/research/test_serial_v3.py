"""V3 physical construction fixtures. No provider, physics integration or task pass."""
from copy import deepcopy
import gc, shutil, unittest
from uuid import uuid4
from unittest.mock import patch
import numpy as np
from schemas.platform import ProjectConfig, SessionInput
from tools.research import core, design
from tools.research.config import ROOT
from tools.research.state import state,update
from tools.platform_store import plain
from extensions.tendon_family.family_space import GenerationRequestV3


class V3RoutingTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'runs'/('v3-fixture-'+uuid4().hex)
        fixture=lambda **v:ProjectConfig(**{**v,'project_id':self.folder.name,'grant_id':self.folder.name})
        with patch.object(core,'ProjectConfig',side_effect=fixture):
            self.host=core.prepare(ROOT/'configs/research/study_serial_v3_dev.json',self.folder)
        self.spec=state(self.host)['spec']
        self.addCleanup(self.cleanup)

    def cleanup(self):
        gc.collect()
        if self.folder.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
        if self.folder.exists():shutil.rmtree(self.folder)

    def request(self,n=2):
        def seg(radius,angle):return dict(radius_m=radius,angle_rad=angle,guide_s=.5)
        routes=[dict(anchor_segment=0,anchor_s=1.,segments=[seg(.018,0.)]),
            dict(anchor_segment=1,anchor_s=1.,segments=[seg(.018,2.1),seg(.020,2.2)]),
            dict(anchor_segment=1,anchor_s=1.,segments=[seg(.018,-2.1),seg(.019,-2.)])]
        return dict(version='serial_family_generation_v3',family_space_identity=self.spec['family_space_identity'],
            segment_count=n,tendon_count=3,**(dict(routes=routes) if n==2 else {}))

    def test_build_models_binding_and_clearance(self):
        from extensions.tendon_family.compiler import resolve
        from extensions.tendon_family.geometry import geometry
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.mjcf import compile_xml
        import mujoco
        single=design.generate_candidate(self.host,self.request(1),dict(origin='offline_fixture'))
        self.assertEqual(single['status'],'generated',single)
        result=design.generate_candidate(self.host,self.request(),dict(origin='offline_fixture'))
        self.assertEqual(result['status'],'generated',result)
        candidate=design.verify_candidate(self.host,result['candidate']);cfg=candidate['configuration']
        self.assertEqual(candidate['generation_version'],'serial_family_generation_v3')
        self.assertEqual(cfg['policy']['candidate_builder']['version'],'7.0.0')
        tendons=result['resolved']['tendons']
        self.assertTrue(all(t['points'][0]['attachment']['part']=='fixed_base' for t in tendons))
        self.assertEqual([t['points'][-1]['attachment']['part'] for t in tendons],['segment_0','segment_1','segment_1'])
        self.assertEqual([p['role'] for p in tendons[1]['points']].count('start'),1)
        self.assertNotEqual(tendons[1]['points'][1]['attachment']['position_m'],tendons[1]['points'][-1]['attachment']['position_m'])
        inp=SessionInput.model_validate(cfg);physics=resolve(cfg['robot']['structure']['data'],result['resolved']['discretization'])
        from extensions.tendon_family.generated_serial import authorize
        from extensions.tendon_family.family_space import parse_build
        authorize(inp,parse_build(cfg['policy']['candidate_builder']['parameters']['data']),{})
        g=geometry(physics,[0.]*len(physics['dofs']))
        self.assertEqual(g['Jlength'].shape,(3,len(physics['dofs'])))
        self.assertEqual([t['entity'] for t in physics['tendons']],result['resolved']['tendon_order'])
        xml=self.folder/'v3.xml';compile_xml(physics,assemble(inp,physics),None,xml)
        model=mujoco.MjModel.from_xml_path(str(xml));self.assertEqual(model.nu,3)
        np.testing.assert_array_equal(model.actuator_trnid[:,0],np.arange(3))
        self.assertTrue(np.all(np.isfinite(g['Jlength'])))
        self.assertFalse(state(self.host).get('success_gate'))
        self.assertEqual(self.host.store.remaining()['used']['backend_solves'],0)
        bad=self.request();bad['routes'][1]['segments'][1]['angle_rad']=2.1+np.pi
        invalid=design.generate_candidate(self.host,bad,dict(origin='offline_fixture'))
        self.assertEqual(invalid['status'],'invalid');self.assertIn('CLEARANCE',invalid['reason'])
        bad=self.request();bad['routes'][1]['segments'].pop(0)
        with self.assertRaises(ValueError):GenerationRequestV3.model_validate(bad)
        bad=self.request();bad['route_overrides']={0:tendons[0]['points'][1:]}
        with self.assertRaises(ValueError):GenerationRequestV3.model_validate(bad)
        bad=self.request();bad['routes'][0]['anchor_segment']=2
        with self.assertRaises(ValueError):GenerationRequestV3.model_validate(bad)

    def test_force_support_uses_bound_geometry_and_native_channels(self):
        import mujoco
        from tools.research.contracts import AnalysisRequest
        from tools.research.numerics import native_point
        from tools.research.analysis import calculate
        from tools.research.task_constraints import mathematical_method_view
        from extensions.tendon_family.mujoco_analysis import NativeModel
        result=design.generate_candidate(self.host,self.request(),dict(origin='offline_fixture'))
        self.assertEqual(result['status'],'generated',result)
        c=design.verify_candidate(self.host,result['candidate']);cfg=c['configuration']
        nm=NativeModel(cfg);w=[0.]*len(nm.order);w[0]=1.
        query=AnalysisRequest.model_validate(dict(candidate=result['candidate'],operation='tendon_force_capability_v1',
            model_source='mujoco',operating_point='standardized_initial_pretension',
            protocol=self.spec['analysis_protocol'],tendon_force_direction=w))
        point=native_point(self.host,query,cfg)
        binding=dict(candidate=result['candidate'],candidate_id=c['candidate_id'],configuration=c['configuration_reference'],
            effective_configuration_identity=point['configuration_identity'],task_identity=c['effective_task_identity'],
            tendon_order=nm.tendons,tension_limits_n=nm.limits[:,1].tolist(),tension_bounds_n=nm.limits.tolist(),
            coordinate_order=nm.order,source_identity=c['source_identity'],evaluation_profile_identity=c['profile_identity'])
        out=calculate(cfg,binding,plain(query),point)
        self.assertEqual(out['status'],'computed');facts=out['tendon_force_capability']
        d=mujoco.MjData(nm.model);d.qpos[nm.qi]=point['qpos_rad'];mujoco.mj_forward(nm.model,d)
        jac=np.zeros((nm.model.ntendon,nm.model.nv));mujoco.mju_sparse2dense(jac,d.ten_J,nm.model.ten_J_rownnz,nm.model.ten_J_rowadr,nm.model.ten_J_colind)
        np.testing.assert_allclose(facts['jacobian_m_rad'],jac[nm.tids][:,nm.vi],atol=1e-10,rtol=1e-8)
        coeff=-jac[nm.tids][:,nm.vi]@np.asarray(w)
        expected=np.maximum(coeff*nm.limits[:,0],coeff*nm.limits[:,1]).sum()
        self.assertAlmostEqual(facts['directional_support_nm'],expected)
        self.assertEqual(facts['tendon_order'],nm.tendons)
        self.assertEqual(out['internal_calculations'][0]['physics_steps'],0)
        view=mathematical_method_view(self.host,result['candidate'])
        self.assertIn('tendon_force_capability_v1',view['methods'])
        self.assertEqual(view['methods']['tendon_force_capability_v1']['request_template']['model_source'],'mujoco')
        self.assertFalse(state(self.host).get('success_gate'))
        # One real contained, accounted geometry analysis; no physics integration.
        from tools.research import analysis
        spec=deepcopy(state(self.host)['spec']);spec['budgets']['mathematical_evaluations']=1
        update(self.host,spec=spec,freeze='offline-v3-force-fixture')
        receipt=analysis.dispatch(self.host,plain(query),'v3-force',guard=lambda *args:None)
        self.assertEqual(receipt['scientific_computation']['status'],'computed',receipt)
        self.assertEqual(state(self.host)['mathematical_evaluations'],1)
        self.assertAlmostEqual(receipt['tendon_force_capability']['directional_support_nm'],expected)
        repeated=analysis.dispatch(self.host,plain(query),'v3-force',guard=lambda *args:None)
        self.assertEqual(repeated['operation_reuse']['additional_analysis_evaluations'],0)
        self.assertEqual(self.host.store.remaining()['used']['backend_solves'],0)

    def test_legacy_v2_distal_start_is_not_reinterpreted(self):
        from tools.research.config import resolve
        from tools.state_io import digest
        from extensions.tendon_family.family_space import parse_build
        from extensions.tendon_family.generated_serial import generate_family
        space=resolve(ROOT/'configs/research/study_variable_segments_dev.json')['family_space']
        request=dict(version='serial_family_generation_v2',family_space_identity=digest(space),segment_count=2,tendon_count=1,
            spans=[dict(first_segment=1,last_segment=1,count=1)])
        robot,_,_=generate_family(parse_build(dict(space=space,request=request)))
        self.assertEqual(robot['tendons'][0]['points'][0]['attachment']['part'],'guide_1')



if __name__=='__main__':unittest.main()
