"""Physical serial-family contracts; no controller, provider or physics steps."""
from copy import deepcopy
import json
import os
import shutil
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
import numpy as np
from schemas.platform import ProjectConfig, SessionInput
from tools.research import core,design
from tools.research.config import ROOT,resolve
from tools.research.state import state,update
from tools.state_io import atomic_json,digest,read
from extensions.tendon_family.family_space import FamilySpaceV2,GenerationRequestV2


class VariableSegmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'runs'/('serial-fixture-'+uuid4().hex)
        def cleanup():
            import gc
            gc.collect()
            if cls.folder.resolve().parent!=(ROOT/'runs').resolve():
                raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
            if cls.folder.exists():shutil.rmtree(cls.folder)
        cls.addClassCleanup(cleanup)
        fixture=lambda **v:ProjectConfig(**{**v,'project_id':cls.folder.name,'grant_id':cls.folder.name})
        from tools.research import config
        def checked(path):
            if path.name=='robot.json':raise AssertionError('No legacy physics read')
            return read(path)
        with patch.object(core,'ProjectConfig',side_effect=fixture),patch.object(config,'read',side_effect=checked):
            cls.host=core.prepare(ROOT/'configs/research/study_variable_segments_dev.json',cls.folder)
        cls.spec=state(cls.host)['spec']
        assert state(cls.host)['reference_candidate'] is None
        assert state(cls.host)['candidates']=={}
        cls.results={};cls.candidates={}
        for n in range(1,10):
            result=cls.generate(segment_count=n,tendon_count=3,segments={i:dict(cells=4) for i in range(n)})
            if result['status']!='generated':raise AssertionError((n,result))
            cls.results[n]=result
            cls.candidates[n]=design.verify_candidate(cls.host,result['candidate'])

    @classmethod
    def generate(cls,**values):
        request=dict(version='serial_family_generation_v2',family_space_identity=cls.spec['family_space_identity'],**values)
        return design.generate_candidate(cls.host,request,dict(origin='offline_M3C2_fixture'))

    def test_all_serial_counts_and_xml_without_steps(self):
        import mujoco
        from extensions.tendon_family.compiler import resolve as compile_physics
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.mjcf import compile_xml
        rows={}
        for n,c in self.candidates.items():
            started=time.perf_counter()
            r=self.results[n]['resolved'];cfg=c['configuration'];inp=SessionInput.model_validate(cfg)
            d=cfg['robot']['structure']['data'];parts={p['id']:p for p in d['components']}
            self.assertEqual(len(r['segments']),n)
            self.assertEqual(len(parts),3*n-1)
            self.assertEqual(parts['segment_0']['connection']['part'],'fixed_base')
            self.assertEqual(parts['payload']['connection']['part'],'segment_'+str(n-1))
            for i in range(1,n):
                self.assertEqual(parts[f'guide_{i}']['connection']['part'],f'segment_{i-1}')
                self.assertEqual(parts[f'connector_{i}']['connection']['part'],f'guide_{i}')
                self.assertEqual(parts[f'segment_{i}']['connection']['part'],f'connector_{i}')
            self.assertEqual(set(r['discretization']['cells']),{f'segment_{i}' for i in range(n)})
            dims=r['dimensions'];self.assertEqual(dims['physical_dofs'],8*n)
            self.assertEqual(dims['inputs'],3)
            self.assertEqual(dims['state'],2*dims['gvs_coordinates'])
            self.assertEqual(c['task_identity'],self.spec['canonical_task_identity'])
            self.assertEqual(len(c['initialization_provenance']['effective']['qpos_rad']),8*n)
            physics=compile_physics(d,r['discretization'])
            xml=self.folder/(str(n)+'.xml');compile_xml(physics,assemble(inp,physics),None,xml)
            print('M3C2 XML compile',n,flush=True)
            model=mujoco.MjModel.from_xml_path(str(xml))
            self.assertEqual(model.nu,3);self.assertEqual(model.nv,8*n)
            np.testing.assert_array_equal(model.actuator_trnid[:,0],np.arange(3))
            rows[n]=dict(candidate=c['identity'],physics_identity=physics['identity'],dimensions=dims,
                capability=r['capabilities'],xml_compiled=True,physics_steps=0,elapsed_s=time.perf_counter()-started)
        if os.environ.get('M3C2_EVIDENCE'):
            atomic_json(ROOT/os.environ['M3C2_EVIDENCE'],dict(cases=rows,
                family_space_identity=self.spec['family_space_identity'],label='Real physical compilation; no rollout/task evaluation',
                construction_numerical_s=state(self.host)['construction_numerical_s']))

    def test_mixed_spans_cells_materials_and_equivalent_reuse(self):
        result=self.generate(segment_count=5,tendon_count=4,segments={4:dict(length_m=.12,young_pa=8e6,cells=4)},
            spans=[dict(first_segment=0,last_segment=0,count=1),
                dict(first_segment=0,last_segment=2,count=1,phase_rad=.8),
                dict(first_segment=1,last_segment=4,count=1,phase_rad=1.6),
                dict(first_segment=4,last_segment=4,count=1,phase_rad=2.4)])
        self.assertEqual(result['status'],'generated',result)
        r=result['resolved']
        self.assertEqual([t['points'][0]['attachment']['part'] for t in r['tendons']],
            ['fixed_base','fixed_base','guide_1','guide_4'])
        self.assertEqual([t['points'][-1]['attachment']['part'] for t in r['tendons']],
            ['segment_0','segment_2','segment_4','segment_4'])
        self.assertEqual(r['discretization']['cells']['segment_4'],4)
        self.assertEqual(r['segments'][4]['physics']['young_pa'],8e6)
        self.assertEqual(r['segments'][4]['length_m'],.12)
        before=len(state(self.host)['candidates'])
        equivalent=self.generate(segment_count=3,tendon_count=3,segments={i:dict(cells=4) for i in range(3)},spans=[dict(last_segment=2,count=3,radius_m=.018,guide_s=[.5],anchor_s=1.)])
        self.assertEqual(equivalent['candidate'],self.results[3]['candidate'])
        self.assertEqual(len(state(self.host)['candidates']),before)
        core.recover(self.host)
        self.assertEqual(design.verify_candidate(self.host,self.results[9]['candidate']),self.candidates[9])

    def test_invalid_and_unvalidated_capabilities(self):
        for values in (dict(segment_count=10,tendon_count=1),dict(segment_count=3,tendon_count=1,segments={2:dict(cells=33)}),
                       dict(segment_count=1,tendon_count=1,spans=[dict(last_segment=0,count=1,radius_m=.1)])):
            self.assertEqual(self.generate(**values)['status'],'invalid')
        self.assertEqual(self.generate(segment_count=3,tendon_count=8)['status'],'not_yet_supported')
        for n,r in self.results.items():
            self.assertFalse(r['resolved']['capabilities']['gvs_dynamics_evaluated'])
            self.assertFalse(r['resolved']['capabilities']['controller_update_tested'])
        with self.assertRaises(ValueError):
            GenerationRequestV2.model_validate(dict(family_space_identity='fixture',segment_count=3,tendon_count=1,
                spans=[dict(first_segment=2,last_segment=3,count=1)]))

    def test_v1_physical_identities_and_legacy_study(self):
        from extensions.tendon_family.generated_serial import generate_family
        from extensions.tendon_family.family_space import FamilyBuild
        from extensions.tendon_family.family_space import parse_space
        from tools.platform_store import plain
        space=plain(parse_space(read(ROOT/'configs/research/family_space_v1.json')))
        recorded=read(ROOT/'evidence/m3c1_family_space/construction.json')
        for name in ('1','mixed','7'):
            request=dict(family_space_identity=digest(space),**recorded['candidates'][name]['request'])
            _,_,physics=generate_family(FamilyBuild(space=space,request=request))
            self.assertEqual(physics['identity'],recorded['diagnostics'][name]['physics_identity'])
        self.assertEqual(digest(resolve(ROOT/'configs/research/study.json')['configuration']),
            '31af3e097ad29fef1ffd74c5178a6267fc5ffe35889c63e98f531dd42c0df69e')


if __name__=='__main__':unittest.main()
