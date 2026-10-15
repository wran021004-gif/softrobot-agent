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

    def test_optional_analysis_scales_cover_candidate_coordinate_entities(self):
        protocol=self.spec['analysis_protocol']
        self.assertEqual(self.spec['analysis_length_scale_source'],'frozen_family_domain_defaults_v1')
        for n,result in self.results.items():
            order=result['resolved']['controller_preparation']['coordinate_order']
            for name in order:
                entity=name.split('.',1)[0]
                self.assertGreater(1/protocol['baseline_lengths_m'][entity],0)
        self.assertEqual(len(protocol['baseline_lengths_m']),9)
        self.assertEqual(protocol['baseline_lengths_m']['segment_8'],.14)

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

    def test_rl_input_canonical_task_without_training(self):
        from tools.research.rl import prepare_input
        from tools.research.contracts import RLRequest
        from tools.research.state import save
        # Isolated input preparation only; no stage admission, launch or training.
        task=save(self.host,self.spec['canonical_task'],'test_canonical_task_fixture')
        update(self.host,rl_task=task)
        request=RLRequest(operation='start',candidate=self.results[1]['candidate'],mode='direct',
            rationale='Offline input compatibility fixture; no training authorized')
        cfg,ref=prepare_input(self.host,request)
        self.assertEqual(ref,task)
        self.assertEqual(len(cfg['control_object']['joint_names']),8)
        self.assertEqual(cfg['task']['original'],self.candidates[1]['configuration']['task'])


@unittest.skipUnless(os.environ.get('SOFTROBOT_M3C2_CONTROL')=='1',
    'Opt-in single-use M3-C2 engineering scope: exactly three admitted short cases')
class RealVariableSegmentControl(unittest.TestCase):
    def test_bound_progressive_models_and_single_updates(self):
        import mujoco
        from types import SimpleNamespace
        from tools.platform_store import plain,zero
        from tools.research.state import save,guard,science_hashes,core_hashes
        from extensions.tendon_family.gvs import GVSModel
        from extensions.tendon_family.contracts import GVSModelParameters
        from extensions.tendon_family.gvs_casadi import functions_for,expression_from_system
        from extensions.tendon_family.control_evidence import COMPLETE_UPDATE_INPUTS
        from schemas.platform_math import SystemContext
        from tests.research.test_family_space import plan
        h=core.prepare(ROOT/'configs/research/variable_segments_control.json')
        self.assertFalse(any(e['kind']=='m3c2_started' for e in h.store.events(h.run_id)),
            'Single-use engineering study; read or recover attempts, never rerun')
        core.bind(h)
        save(h,dict(scope='Three single updates, 20 physical steps each; no task evaluation',
            implementation=state(h)['freeze'],science_hashes=science_hashes(),core_hashes=core_hashes()),'m3c2_started')
        reports={};models={};started=time.perf_counter()
        class IntervalComplete(Exception):pass
        for n in range(1,10):
            request=dict(version='serial_family_generation_v2',family_space_identity=state(h)['spec']['family_space_identity'],
                segment_count=n,tendon_count=3)
            if n>3:request['segments']={i:dict(cells=4) for i in range(n)}
            response=core.dispatch(h,plan(request),'generate-'+str(n))['result']
            self.assertEqual(response['status'],'generated',response)
            c=design.verify_candidate(h,response['candidate']);inp=SessionInput.model_validate(c['configuration'])
            dims=response['resolved']['dimensions'];p=GVSModelParameters(basis=inp.policy.controller.parameters.data['recipe']['basis'])
            model_start=time.perf_counter()
            system=GVSModel(p).build_system(inp.robot,p,None,SystemContext(x0=[0.]*dims['state'],
                u0=[t['pretension_n'] for t in inp.robot.structure.data['tendons']],scene=inp.task.environment))
            expression=expression_from_system(system)
            model=dict(candidate=response['candidate'],candidate_identity=c['identity'],dimensions=dims,
                gvs_model_built=True,gvs_dynamics_evaluated=False,controller_update_tested=False,
                complete_task_evaluated=False,coordinate_order=expression.coordinate_order,
                tendon_order=expression.tendon_order,resolved_basis=plain(expression.resolved_basis),
                model_identity=digest(plain(expression)),model_build_s=time.perf_counter()-model_start)
            models[n]=model
            if n>3:
                model['numerical_boundary']='Recipe/basis construction only; no symbolic dynamics graph or control solve'
                continue
            guard(h,True)
            row,_=h.store.reserve(h.run_id,'short-control-'+str(n),digest(c),h.actor,
                {**zero(),'tool_calls':1,'backend_solves':1})
            case_start=time.perf_counter();backend=None;physical=dict(steps=0);report={}
            try:
                f=functions_for(expression);values=f.evaluate(system.x0,system.u0)
                self.assertTrue(all(np.isfinite(v).all() for v in values.values()))
                self.assertEqual(values['tendon_length_jacobian'].shape,(3,dims['gvs_coordinates']))
                np.testing.assert_allclose(values['tendon_generalized_force'],
                    -values['tendon_length_jacobian'].T@np.array(system.u0).reshape(-1,1),atol=1e-12)
                singular=np.linalg.svd(values['mass_matrix'],compute_uv=False)
                model.update(gvs_dynamics_evaluated=True,jacobian_shape=list(values['tendon_length_jacobian'].shape),
                    force_mapping_shape=list(values['tendon_length_jacobian'].T.shape),mass_rank=int(np.linalg.matrix_rank(values['mass_matrix'])),
                    mass_singular_values=singular.tolist(),mass_condition=float(singular[0]/singular[-1]),
                    numerical_terms={k:dict(shape=list(v.shape),finite=True,norm=float(np.linalg.norm(v))) for k,v in values.items()},
                    numerical_graph_and_evaluation_s=time.perf_counter()-case_start)
                backend_def,_=h.reg.bind(inp.policy.backend,'backend');control_def,cp=h.reg.bind(inp.policy.controller,'controller')
                controller=control_def.resolve()(cp,inp.task.timing.control_period_s)
                backend=backend_def.resolve()()
                control_def.hook('prepare_execution')(SimpleNamespace(save_artifact=lambda v,k:save(h,v,k)),controller,inp)
                backend.compile(inp,h.reg)
                init,ip=h.reg.bind(inp.task.initializer,'initializer')
                backend.initialize(init.resolve()(ip,inp.seed),controller)
                backend.folder=h.store.root/('case-'+str(n));backend.folder.mkdir(exist_ok=True)
                original_command=controller.command;original_step=mujoco.mj_step
                def command(*args):
                    if controller.observations:raise IntervalComplete()
                    return original_command(*args)
                def step(m,d,*args,**kwargs):
                    if physical['steps']>=20:raise AssertionError('Authorized physical step cap exceeded')
                    original_step(m,d,*args,**kwargs)
                    physical.update(steps=physical['steps']+1,time_s=float(d.time),qpos=d.qpos.tolist(),qvel=d.qvel.tolist(),
                        applied_tension_n=(-d.actuator_force).tolist(),nu=m.nu,actuator_tendon_indices=m.actuator_trnid[:,0].tolist())
                token=COMPLETE_UPDATE_INPUTS.set(True)
                try:
                    with patch.object(controller,'command',side_effect=command),patch.object(mujoco,'mj_step',side_effect=step):
                        with self.assertRaises(IntervalComplete):backend.solve(None)
                finally:COMPLETE_UPDATE_INPUTS.reset(token)
                self.assertEqual(physical['steps'],20);self.assertAlmostEqual(physical['time_s'],.01)
                self.assertEqual(len(controller.observations),1)
                self.assertTrue(np.isfinite(physical['qpos']).all() and np.isfinite(physical['qvel']).all())
                applied=np.array(physical['applied_tension_n'])
                self.assertTrue(((applied>=-1e-12)&(applied<=controller.limits+1e-12)).all())
                model['controller_update_tested']=True
                report=dict(status='completed_single_interval',candidate=response['candidate'],
                    controller_binding=plain(inp.policy.controller),physics_identity=backend.physics['identity'],
                    preparation=controller.preparation,numerical=controller.profile['numerical'],
                    observations=controller.observations,last=controller.last,physical=physical,
                    workspace_graph_s=controller.workspace.graph_s,complete_task=False,task_acceptance='not_assessed')
            except Exception as exc:
                report=dict(status='failed',candidate=response['candidate'],exception=str(exc),physical=physical,
                    complete_task=False,task_acceptance='not_assessed')
            finally:
                if backend is not None:backend.close()
                report['elapsed_s']=time.perf_counter()-case_start
                reports[n]=report
                save(h,report,'m3c2_case')
                h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=h.actor,
                    tool_id='engineering.m3c2',tool_version='1.0.0',execution_status='completed' if report['status']=='completed_single_interval' else 'failed',charged=zero()),
                    report,elapsed=report['elapsed_s'])
                atomic_json(ROOT/'evidence/m3c2_variable_segments/short_control.json',dict(
                    implementation_commit=state(h)['freeze'],models=models,cases=reports,ledger=h.store.remaining(),
                    resources=dict(provider_requests=0,rl_training_stages=0,complete_task_evaluations=0,
                        short_cases=len(reports),physical_steps=sum(r['physical']['steps'] for r in reports.values()))))
                print('M3C2 SHORT',n,report['status'],report.get('last',{}).get('solver_outcome'),report['elapsed_s'],flush=True)
        summary=dict(models=models,cases=reports,elapsed_s=time.perf_counter()-started,
            implementation_commit=state(h)['freeze'],ledger=h.store.remaining())
        atomic_json(ROOT/'evidence/m3c2_variable_segments/short_control.json',dict(**summary,
            resources=dict(provider_requests=0,rl_training_stages=0,complete_task_evaluations=0,
                short_cases=len(reports),physical_steps=sum(r['physical']['steps'] for r in reports.values()))))
        terminal=save(h,summary,'m3c2_complete')
        update(h,numerical_s=state(h)['numerical_s']+sum(r['elapsed_s'] for r in reports.values()),
            research_status='stopped',closed_unix=time.time(),final_disposition=terminal)
        self.assertFalse(state(h)['pending'])
        core.export(h)
        self.assertEqual(len(reports),3)
        self.assertTrue(all(r['status']=='completed_single_interval' for r in reports.values()),reports)


if __name__=='__main__':unittest.main()
