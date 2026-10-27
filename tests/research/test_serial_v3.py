"""V3 physical construction fixtures. No provider, physics integration or task pass."""
from copy import deepcopy
import gc, shutil, unittest
from uuid import uuid4
from unittest.mock import patch
import numpy as np
from schemas.platform import ProjectConfig, SessionInput
from tools.research import core, design
from tools.research.config import ROOT
from tools.research.state import state
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
