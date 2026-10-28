"""Offline C1 boundaries: real compiler/models, no provider, rollout or training."""
from copy import deepcopy
import os
import shutil
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
import numpy as np
from schemas.platform import ProjectConfig, SessionInput
from schemas.platform_math import SystemContext
from tools.platform_store import plain
from tools.state_io import read, digest, atomic_json
from tools.research import core, design, analysis
from tools.research.config import ROOT, resolve
from tools.research.state import state, update
from tools.research.contracts import Plan
from extensions.tendon_family.family_space import FamilySpace, GenerationRequest
from extensions.tendon_family import generated_serial as family


def plan(request):
    return dict(action='generate',generation=request,hypothesis='Offline family construction fixture',
        expected_observation='Physically compiled candidate',weakening_observation='Invalid or unsupported geometry',
        fixed_conditions='Frozen task and family domain',stopping_condition='Bounded compatibility checks only',
        interpretation='No scientific task success measured')


class FamilySpaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'runs'/('family-fixture-'+uuid4().hex)
        def cleanup():
            import gc
            gc.collect()
            if cls.folder.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
            if cls.folder.exists():shutil.rmtree(cls.folder)
        cls.addClassCleanup(cleanup)
        cls.folder.mkdir(parents=True)
        # Isolated editable sources let this test prove freezing with real JSON edits.
        defaults=read(ROOT/'configs/research/family_study_defaults.json')
        for key in ('task','control','runtime'):
            defaults[key]=str((ROOT/'configs/research'/defaults[key]).resolve())
        atomic_json(cls.folder/'family_study_defaults.json',defaults)
        cls.family_source=cls.folder/'family_space_v1.json'
        atomic_json(cls.family_source,read(ROOT/'configs/research/family_space_v1.json'))
        atomic_json(cls.folder/'study_family_space_dev.json',read(ROOT/'configs/research/study_family_space_dev.json'))
        cls.study_source=cls.folder/'study_family_space_dev.json'
        fixture=lambda **v: ProjectConfig(**{**v,'project_id':cls.folder.name,'grant_id':cls.folder.name})
        with patch.object(core,'ProjectConfig',side_effect=fixture), patch.object(core,'construct',side_effect=AssertionError('No scientific reference')), patch(
                'extensions.tendon_family.gvs.GVSModel.build_system',side_effect=AssertionError('No model build in prepare')):
            cls.host=core.prepare(cls.study_source,cls.folder)
        cls.spec=state(cls.host)['spec']
        update(cls.host,freeze='offline-unbound-C1-test-fixture')
        # Exercise normal before-generation status, packet, export and recovery.
        from tools.research.agent import decision_packet
        packet=decision_packet(cls.host)
        assert packet['reference_candidate'] is None and packet['candidates']==[]
        assert packet['study']['family_space_identity']==cls.spec['family_space_identity']
        core.export(cls.host,cls.folder/'before-export');core.recover(cls.host)
        assert not state(cls.host)['candidates']
        cls.responses={};cls.candidates={}
        cls.requests={str(n):dict(tendon_count=n) for n in (1,3,5,6,7)}
        cls.requests.update(
            mixed=dict(tendon_count=5,spans=[dict(last_segment=0,count=2,phase_rad=.3),
                dict(last_segment=1,count=3,phase_rad=.8,angular_offsets_rad=[0.,.13,-.08],radius_m=.021,
                    guide_s=[.4],guide_angle_offset_rad=.06,anchor_angle_offset_rad=-.09)]),
            distal=dict(tendon_count=1,spans=[dict(first_segment=1,last_segment=1,count=1,phase_rad=.4)]))
        cls.started=time.perf_counter()
        for name,values in cls.requests.items():
            request=cls.request(**values)
            with patch.object(core,'guard'):
                response=core.dispatch(cls.host,plan(request),'family-'+name)
            result=response['result']
            if result['status']!='generated':raise AssertionError(result)
            cls.responses[name]=result
            cls.candidates[name]=design.verify_candidate(cls.host,result['candidate'])
        cls.construction_s=time.perf_counter()-cls.started

    @classmethod
    def request(cls,**values):
        return dict(family_space_identity=cls.spec['family_space_identity'],**values)

    def generate(self,**values):
        return design.generate_candidate(self.host,self.request(**values),dict(origin='offline_test'))

    def test_expressiveness_and_unsupported_vs_invalid(self):
        space=FamilySpace.model_validate(self.spec['family_space'])
        self.assertEqual(space.segment_count_bounds,(1,9));self.assertEqual(space.tendon_count_bounds,(1,12))
        for count in (1,3,9):
            result=self.generate(tendon_count=1,segment_count=count)
            self.assertEqual(result['status'],'not_yet_supported');self.assertIn('segment_count='+str(count),result['unsupported_capability'])
            self.assertIsNone(result['candidate'])
        self.assertEqual(self.generate(tendon_count=8)['status'],'not_yet_supported')
        self.assertEqual(self.generate(tendon_count=13)['status'],'invalid')
        for values in (dict(tendon_count=1,segments={2:dict(length_m=.1)}),
                       dict(tendon_count=1,spans=[dict(last_segment=2,count=1)]),
                       dict(tendon_count=3,spans=[dict(last_segment=0,count=2)])):
            with self.assertRaises(ValueError):GenerationRequest.model_validate(self.request(**values))
        for field,invalid in [('segment_count_bounds',[0,9]),('executable_segment_counts',[1,2]),
                              ('executable_tendon_count_bounds',[1,13])]:
            data=plain(space);data[field]=invalid
            with self.assertRaises(ValueError):FamilySpace.model_validate(data)
        with self.assertRaises(ValueError):Plan.model_validate({**plan(self.request(tendon_count=1)),'candidate':self.responses['1']['candidate']})

    def test_routes_order_dimensions_and_identity(self):
        identities=[]
        for name,c in self.candidates.items():
            result=self.responses[name];r=result['resolved'];nu=self.requests[name]['tendon_count']
            self.assertEqual(len(r['tendons']),nu);self.assertEqual(len(r['actuators']),nu)
            self.assertEqual([a['transmission'][0]['tendon'] for a in r['actuators']],r['tendon_order'])
            dims=r['dimensions'];self.assertEqual(dims['inputs'],nu)
            self.assertEqual(r['controller_preparation']['warm_input_shape'],[10,nu])
            self.assertEqual(dims['state'],2*dims['gvs_coordinates'])
            self.assertEqual(len(c['initialization_provenance']['effective']['qpos_rad']),dims['physical_dofs'])
            self.assertEqual(c['task_identity'],self.spec['canonical_task_identity'])
            self.assertEqual(c['configuration']['task']['goal'],self.spec['configuration']['task']['goal'])
            self.assertEqual(c['configuration']['task']['timing'],self.spec['configuration']['task']['timing'])
            identities.append(c['identity'])
        self.assertEqual(len(identities),len(set(identities)))
        mixed=self.responses['mixed']['resolved']
        self.assertEqual([t['points'][-1]['attachment']['part'] for t in mixed['tendons']],['segment_0']*2+['segment_1']*3)
        self.assertNotEqual(mixed['dimensions']['state'],24)
        self.assertEqual(self.responses['distal']['resolved']['tendons'][0]['points'][0]['attachment']['part'],'mid_guide')
        before=len(state(self.host)['candidates'])
        reused=self.generate(tendon_count=3)
        self.assertEqual(reused['candidate'],self.responses['3']['candidate'])
        explicit=self.generate(tendon_count=3,spans=[dict(last_segment=1,count=3,radius_m=.018,guide_s=[.5],anchor_s=1.)])
        self.assertEqual(explicit['candidate'],reused['candidate'])
        self.assertEqual(len(state(self.host)['candidates']),before)
        for span in (dict(last_segment=1,count=3,phase_rad=.2),dict(last_segment=1,count=3,radius_m=.02),dict(last_segment=0,count=3)):
            other=self.generate(tendon_count=3,spans=[span])
            self.assertEqual(other['status'],'generated');self.assertNotEqual(other['candidate'],reused['candidate'])
            self.assertNotEqual(other['resolved']['tendons'],reused['resolved']['tendons'])

    def test_physical_overrides_and_rejections(self):
        sections=[dict(kind='circle',parameters=dict(radius_m=.008))]
        result=self.generate(tendon_count=1,segments={0:dict(length_m=.19,young_pa=9e6,sections=sections)},
            control_weights=dict(holding_tip_speed_weight=.3),tendon_parameters=dict(force_limit_n=4.,pretension_n=.5))
        self.assertEqual(result['status'],'generated')
        first,second=result['resolved']['segments']
        self.assertEqual(first['length_m'],.19);self.assertEqual(first['physics']['young_pa'],9e6)
        self.assertEqual(first['sections'][0]['section']['kind'],'circle');self.assertEqual(second['length_m'],.11)
        c=design.verify_candidate(self.host,result['candidate'])
        self.assertEqual(c['configuration']['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight'],.3)
        route=deepcopy(self.responses['1']['resolved']['tendons'][0]['points']);route[-1]['attachment']['s']=.9
        self.assertEqual(self.generate(tendon_count=1,route_overrides={0:route})['status'],'generated')
        for values in (dict(segments={0:dict(length_m=.3)}),dict(control_weights=dict(holding_tip_speed_weight=2.)),
                       dict(tendon_parameters=dict(force_limit_n=1.,pretension_n=2.)),dict(spans=[dict(count=1,last_segment=1,radius_m=.1)]),
                       dict(spans=[dict(count=2,last_segment=1,angular_offsets_rad=[0.,-np.pi])])):
            count=2 if 'spans' in values and values['spans'][0]['count']==2 else 1
            self.assertEqual(self.generate(tendon_count=count,**values)['status'],'invalid')
        bad=deepcopy(route);bad[-1]['attachment']['position_m']=[0.,1.,0.]
        self.assertEqual(self.generate(tendon_count=1,route_overrides={0:bad})['status'],'invalid')

    def test_frozen_recovery_analysis_boundary_and_zero_side_effects(self):
        # Mutable source files are never consulted by generation, recovery or export.
        with patch('tools.research.config.read',side_effect=AssertionError('No source reload')):
            self.assertEqual(self.generate(tendon_count=1)['candidate'],self.responses['1']['candidate'])
            core.recover(self.host);core.export(self.host,self.folder/'after-export')
        with patch.object(core,'construct',side_effect=AssertionError('Recovery must not create a reference')):
            core.prepare(self.study_source,self.folder)
        original=read(self.family_source)
        try:
            changed=deepcopy(original);changed['routing_domains']['radius_m']['default']=.021
            atomic_json(self.family_source,changed)
            self.assertEqual(self.generate(tendon_count=1)['candidate'],self.responses['1']['candidate'])
            self.assertEqual(state(self.host)['spec']['family_space_identity'],self.spec['family_space_identity'])
        finally:atomic_json(self.family_source,original)
        self.assertIsNone(state(self.host)['reference_candidate'])
        # Candidate-bound mathematics reaches its ordinary frozen budget boundary,
        # rather than requiring a nominal candidate or disabling registration.
        query=dict(candidate=self.responses['1']['candidate'],operation='equilibrium',operating_point='target_equilibrium',protocol=self.spec['analysis_protocol'])
        with self.assertRaisesRegex(ValueError,'ANALYSIS_AND_CONFIRMATION_BUDGET_CANNOT_FIT'):
            analysis.dispatch(self.host,query,'analysis-denied',guard=lambda *a:None)
        with self.assertRaises(ValueError):
            core.dispatch(self.host,{**plan(self.request(tendon_count=1)),'action':'execute','generation':None,
                'candidate':self.responses['1']['candidate']},'no-backend')
        used=self.host.store.remaining()['used']
        self.assertEqual(used['model_calls'],0);self.assertEqual(used['backend_solves'],0);self.assertEqual(used['worker_calls'],0)
        self.assertEqual(state(self.host)['pilot']['live_model_requests'],0)
        self.assertGreater(state(self.host)['construction_numerical_s'],0)

    def test_representative_real_model_and_xml(self):
        import mujoco
        from extensions.tendon_family.gvs import GVSModel
        from extensions.tendon_family.contracts import GVSModelParameters
        from extensions.tendon_family.gvs_casadi import functions_for, expression_from_system
        from extensions.tendon_family.compiler import resolve as compile_physics
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.mjcf import compile_xml
        diagnostics={}
        for name in ('1','mixed','7'):
            c=self.candidates[name];inp=SessionInput.model_validate(c['configuration']);r=self.responses[name]['resolved']
            dims=r['dimensions'];n=dims['gvs_coordinates'];nu=dims['inputs']
            started=time.perf_counter();parameters=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
            system=GVSModel(parameters).build_system(inp.robot,parameters,None,SystemContext(x0=[0.]*(2*n),u0=[.2]*nu,scene=inp.task.environment))
            functions=functions_for(expression_from_system(system));evaluated=functions.evaluate(np.zeros(2*n),[.2]*nu)
            J=evaluated['tendon_length_jacobian']
            self.assertEqual(J.shape,(nu,n));self.assertTrue(np.isfinite(J).all())
            row=dict(dimensions=dims,jacobian_shape=list(J.shape),model_construction_s=time.perf_counter()-started)
            if name=='1':
                A,B,drift=functions.linearize(np.zeros(2*n),[.2]*nu)
                self.assertEqual(B.shape,(2*n,nu));self.assertTrue(np.isfinite(B).all())
                row['input_matrix_shape']=list(B.shape)
            physics=compile_physics(inp.robot.structure.data,inp.policy.discretization.data)
            xml=self.folder/(name+'.xml');compile_xml(physics,assemble(inp,physics),None,xml)
            model=mujoco.MjModel.from_xml_path(str(xml))
            self.assertEqual(model.nu,nu);self.assertEqual(model.ntendon,nu)
            np.testing.assert_array_equal(model.actuator_trnid[:,0],np.arange(nu))
            row.update(candidate=c['identity'],physics_identity=physics['identity'],xml_actuators=model.nu,physics_steps=0)
            diagnostics[name]=row
        if os.environ.get('M3C1_EVIDENCE'):
            atomic_json(ROOT/os.environ['M3C1_EVIDENCE'],dict(label='Offline construction evidence; no task evaluation',
                family_space_identity=self.spec['family_space_identity'],diagnostics=diagnostics,
                candidates={k:dict(identity=c['identity'],request=self.requests[k],dimensions=self.responses[k]['resolved']['dimensions']) for k,c in self.candidates.items()},
                construction_s=self.construction_s,resources=dict(provider_requests=0,complete_nmpc=0,rl_training=0,full_task_evaluation=0,model_builds=3,physics_steps=0)))

    def test_legacy_configuration_identity(self):
        old=resolve(ROOT/'configs/research/study.json');cfg=old['configuration']
        baseline=read(ROOT/'tests/research/fixtures/r2_harness_boundary.json')['baseline_configuration_identity']
        self.assertEqual(digest(cfg),baseline['resolved_sha256'])
        self.assertEqual(design.resolved_configuration(cfg,cfg,old['reference_parameters'],old['study_id']),cfg)
        legacy=plan(self.request(tendon_count=1));legacy.pop('generation');legacy.update(action='propose',parameters=old['reference_parameters'])
        self.assertNotIn('generation',plain(Plan.model_validate(legacy)))
        self.assertEqual(set(self.spec['analysis_protocol']['baseline_lengths_m']),{'segment_0','segment_1'})

    def test_no_legacy_robot_reads_or_bootstrap_candidate(self):
        from tools.research import config
        def checked_read(path):
            if path.name == 'robot.json':
                raise AssertionError('Family preparation must not read historical robot')
            return read(path)
        with patch.object(config, 'read', side_effect=checked_read):
            spec = resolve(self.study_source)
            recovered = core.prepare(self.study_source, self.folder)
        self.assertEqual(spec, self.spec)
        self.assertFalse((self.folder/'robot.json').exists())
        self.assertIsNone(state(recovered)['reference_candidate'])
        self.assertFalse(spec['implementation_scaffold']['scientific_candidate'])
        self.assertNotIn('robot', spec['configuration_provenance']['references'])
        self.assertEqual(len(spec['configuration']['robot']['structure']['data']['tendons']),1)

    def test_compact_summary_exact_evidence_and_claims(self):
        import json
        from tools.research.agent import decision_packet
        from tools.research.state import readable_results
        packet = decision_packet(self.host)
        summary = packet['study']['family_space']
        self.assertNotIn('assembly',summary)
        self.assertLess(len(json.dumps(summary)),len(json.dumps(self.spec['family_space']))*.6)
        ref=summary['full_specification']
        self.assertIn(ref,readable_results(state(self.host),self.host))
        self.assertEqual(core.read_evidence(self.host,dict(reference=ref)),self.spec['family_space'])
        core.recover(self.host)
        self.assertEqual(core.read_evidence(self.host,dict(reference=ref)),self.spec['family_space'])
        self.assertEqual(summary['segment_count_bounds'],self.spec['family_space']['segment_count_bounds'])
        facts=core.claims(self.host)
        self.assertTrue(facts['candidate_generated_from_family_space'])
        self.assertIsNone(facts['selected_structurally_new'])
        self.assertFalse(facts['task_passed'])
        self.assertGreater(len(facts['design_changes_between_candidates']),0)


class FamilyClaimFixtures(unittest.TestCase):
    """Synthetic claim fixtures; never scientific execution evidence."""
    def test_zero_one_two_and_selected(self):
        from types import SimpleNamespace
        objects={}
        host=SimpleNamespace(store=SimpleNamespace(artifact=lambda ref:objects[ref]))
        s=dict(candidates={},spec={},search_results=[],selected=None)
        progress=dict(confirmed=False,required_total=0)
        self.assertFalse(core.family_claims(host,s,progress)['candidate_generated_from_family_space'])
        for i in range(2):
            ref='synthetic-'+str(i)
            objects[ref]=dict(configuration=dict(robot=dict(structure=dict(geometry=i))),physical_validation='compiled')
            s['candidates'][ref]=ref
            facts=core.family_claims(host,s,progress)
            self.assertEqual(len(facts['design_changes_between_candidates']),i)
            self.assertIsNone(facts['new_design_and_control_confirmed'])
        objects['fixture-result']=dict(candidate='synthetic-1')
        s['selected']='fixture-result'
        with patch('tools.research.feedback.result_view',return_value=dict(passed=True,label='synthetic fixture')):
            facts=core.family_claims(host,s,progress)
        self.assertEqual(facts['selected_candidate'],'synthetic-1')
        self.assertTrue(facts['task_passed'])
        self.assertFalse(facts['reproducibility_assessed'])
