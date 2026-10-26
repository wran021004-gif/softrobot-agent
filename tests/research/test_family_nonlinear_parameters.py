"""Real FamilySpace rebuilds and explicit synthetic T1 fixtures; no provider/rollouts."""
from copy import deepcopy
import gc
import shutil
import unittest
from uuid import uuid4
from unittest.mock import patch

from schemas.platform import ProjectConfig
from tools.platform_store import plain
from tools.state_io import atomic_json,digest,read
from tools.research import core,design,optimal_capability as opt
from tools.research.config import ROOT
from tools.research.state import state,update,save
from tools.research.contracts import AnalysisRequest
from tools.research.nonlinear_capability import saved_context,response,T1,T2,T2_OPERATION
from tools.research.physical_replay import model_context


class FamilyNonlinearTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'runs'/('family-nonlinear-fixture-'+uuid4().hex)
        cls.folder.mkdir(parents=True)
        def cleanup():
            gc.collect()
            if cls.folder.resolve().parent!=(ROOT/'runs').resolve():raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
            if cls.folder.exists():shutil.rmtree(cls.folder)
        cls.addClassCleanup(cleanup)
        cfg=read(ROOT/'configs/research/study_variable_segments_dev.json')
        cfg.update(family_space='family_space_s7.json',
            family_sensitivity_variables=dict(version='family_sensitivity_v2',variables=['segments.*.length_m','segments.*.young_pa',
                'segments.*.physical_parameters.*','segments.*.sections.*.parameters.*','segments.*.sections.*.kind',
                'spans.*.radius_m','spans.*.phase_rad','spans.*.anchor_s','spans.*.guide_s.*','spans.*.angular_offsets_rad.*',
                'spans.*.guide_angle_offset_rad','spans.*.anchor_angle_offset_rad','segment_count','tendon_count','spans','route_overrides.*',
                'route_overrides.*.*.attachment.s','tendon_parameters.*','control_weights.*']),
            mathematical_methods={T1:'Offline synthetic contract fixture',T2:'Offline synthetic contract fixture'})
        cfg['budgets']['mathematical_evaluations']=12
        path=ROOT/'configs/research'/('nonlinear-fixture-'+uuid4().hex+'.json');atomic_json(path,cfg)
        cls.addClassCleanup(lambda:path.unlink(missing_ok=True))
        fixture=lambda **v:ProjectConfig(**{**v,'project_id':cls.folder.name,'grant_id':cls.folder.name})
        with patch.object(core,'ProjectConfig',side_effect=fixture):cls.host=core.prepare(path,cls.folder/'store')
        update(cls.host,freeze='explicit-offline-nonlinear-fixture',analysis_results=[])
        cls.initial=deepcopy(state(cls.host))

    def setUp(self):
        update(self.host,**deepcopy(self.initial));self.raws={}
        self.base_ref,self.base=self.generate(dict(version='serial_family_generation_v2',family_space_identity=state(self.host)['spec']['family_space_identity'],
            segment_count=2,tendon_count=3,segments={'0':{'cells':4},'1':{'cells':4}}))
        self.params=opt.family_parameters(state(self.host)['spec'],self.base,'segments.0.young_pa')[0]
        self.baseline=self.t1(self.base_ref,self.base,3.)

    def generate(self,params):
        result=design.generate_candidate(self.host,params,dict(origin='explicit_offline_test_fixture'))
        self.assertEqual(result['status'],'generated',result)
        return result['candidate'],design.verify_candidate(self.host,result['candidate'])

    def t1(self,ref,c,j):
        cfg=c['configuration'];_,physics,scene,model=model_context(cfg)
        period=cfg['task']['timing']['control_period_s'];n=round(cfg['task']['timing']['duration_s']/period)
        tr=dict(model_identity=model['identity'],design_identity=physics['design_identity'],task_identity=digest(cfg['task']),
            tendon_order=model['tendon_order'],times_s=[k*period for k in range(n+1)],tensions_n=[[1.]*len(model['tendon_order']) for _ in range(n)])
        t=dict(method=T1,J=j,initial_J=j+.5,settings={'explicit_synthetic_fixture':True},callbacks=4,iterations_started=1,
            response_steps_completed=1,local_responses=[dict(diagnostic='resolved_local_response')],stop_reason='iteration_limit',
            input_saturation=dict(lower=False,upper=False),coefficient_boundary=False)
        raw=dict(status='computed',implementation=state(self.host)['freeze'],candidate=ref,protocol=state(self.host)['spec']['analysis_protocol'],
            binding=dict(candidate=ref,effective_configuration_identity=digest(cfg)),nonlinear_capability=t,
            native_dynamics=dict(original_schedule=dict(trajectory=tr),optimized_schedule=dict(trajectory=deepcopy(tr)),
                initial_state=dict(actual_time_s=0.,configuration_identity=digest(cfg),dof_order=physics['dofs'],tendon_order=model['tendon_order'],
                    qpos_rad=scene['qpos_rad'],qvel_rad_s=scene['qvel_rad_s'],phase='interval_start_native',input_units='N',provenance={'rule':'own_zero'}),
                cost=dict(model_builds=1,rollouts=4,physics_steps=2800)))
        r=save(self.host,raw,'explicit_synthetic_t1_fixture');self.raws[r['artifact_id']]=raw
        update(self.host,analysis_results=[*state(self.host).get('analysis_results',[]),r]);return r

    def direction(self,variables,step,unit,name='direction'):
        refs=[self.baseline]
        for coordinate in (-step,step):
            params=deepcopy(self.params)
            for path,coefficient in variables.items():design.set_parameter(params,path,design.parameter_value(params,path)+coordinate*coefficient)
            ref,c=self.generate(params);refs.append(self.t1(ref,c,3.-coordinate/step*.25))
        return dict(direction_id=name,variables=variables,coordinates=[0.,-step,step],coordinate_unit=unit,t1_results=refs)

    def query(self,directions):
        return AnalysisRequest(candidate=self.base_ref,operation=T2_OPERATION,model_source='mujoco',operating_point='standardized_initial_pretension',
            protocol=state(self.host)['spec']['analysis_protocol'],nonlinear_response=dict(version='nonlinear_response_v2',directions=directions))

    def test_dynamic_current_paths_inactive_and_discrete_classification(self):
        rows=core.read_evidence(self.host,dict(reference=self.base_ref,view='capabilities'),record_read=False)
        ids={r['parameter_id']:r for r in rows}
        self.assertFalse(any(p.startswith('segments.2.') or p.startswith('spans.1.') or p.startswith('route_overrides.') for p in ids))
        for p in ['segments.0.young_pa','segments.1.length_m','segments.0.physical_parameters.density_kg_m3','spans.0.guide_s.0','spans.0.angular_offsets_rad.2']:
            self.assertTrue(ids[p]['continuous_perturbation']);self.assertIsNotNone(ids[p]['current_value'])
        for p in ['tendon_parameters.diameter_m','tendon_parameters.length_servo_gain_n_m','control_weights.holding_tip_speed_weight']:
            self.assertFalse(ids[p]['continuous_perturbation']);self.assertEqual(ids[p]['analysis_status'],'not_applicable')
        self.assertEqual(ids['segment_count']['analysis_status'],'finite_comparison_only')
        with self.assertRaisesRegex(ValueError,'NOT_CONTINUOUS'):opt.family_parameters(state(self.host)['spec'],self.base,'segment_count')

    def test_rebuild_material_route_section_and_physical_categories(self):
        rows=opt.family_analysis_parameters(state(self.host)['spec'],self.base)
        section=next(r['parameter_id'] for r in rows if r['category']=='geometry' and r['continuous_perturbation'])
        edits={'segments.0.young_pa':10000.,'segments.1.length_m':.0001,section:.00001,
            'segments.0.physical_parameters.density_kg_m3':1.,'segments.0.physical_parameters.viscosity_y_nm2_s':.00001,
            'segments.0.physical_parameters.curvature_y_rad_m':.001,'spans.0.radius_m':.00001,'spans.0.phase_rad':.001,
            'spans.0.guide_s.0':.001,'spans.0.anchor_s':-.001,'spans.0.angular_offsets_rad.0':.001,
            'spans.0.guide_angle_offset_rad':.001,'spans.0.anchor_angle_offset_rad':.001,'tendon_parameters.force_limit_n':-.01}
        from tools.research.native_analysis import structure_context
        from types import SimpleNamespace
        for path,delta in edits.items():
            with self.subTest(path=path):
                params=deepcopy(self.params);design.set_parameter(params,path,design.parameter_value(params,path)+delta)
                ref,c=self.generate(params)
                self.assertNotEqual(c['configuration']['robot']['structure']['data'],self.base['configuration']['robot']['structure']['data'])
                self.assertEqual(len(structure_context(self.base,[(ref,c)],SimpleNamespace(variable=path),spec=state(self.host)['spec'])),1)

    def test_multiple_independent_and_coupled_directions_share_baseline(self):
        dirs=[self.direction({'segments.0.young_pa':1.},10000.,'Pa','material'),
            self.direction({'spans.0.radius_m':1.},.00001,'m','route'),
            self.direction({'segments.0.length_m':1.,'segments.1.length_m':-1.},.0001,'m','fixed_total_length')]
        q=self.query(dirs);ctx=saved_context(self.host,q)
        self.assertTrue(all('not_comparable' not in c for c in ctx['directions']),ctx)
        out=response(ctx)
        self.assertEqual(out['cost']['reused_t1_results'],7);self.assertEqual(out['cost']['physics_steps'],0)
        self.assertEqual(out['directions'][2]['derivative_scope'],'coupled_path_secant')
        self.assertTrue(all(r['status']=='computed_diagnostic' and r['direction_status']=='unresolved' for r in out['directions']))
        self.assertEqual(len(out['referenced_t1_costs']),7)

    def test_mismatched_controls_initialization_and_task_are_rejected(self):
        q=self.query([self.direction({'segments.0.young_pa':1.},10000.,'Pa')])
        ref=plain(q.nonlinear_response.directions[0].t1_results[1]);original=self.host.store.artifact(ref)
        for field in ('input','initial_state','settings'):
            raw=deepcopy(original)
            if field=='input':raw['native_dynamics']['original_schedule']['trajectory']['tensions_n'][0][0]=1.1
            elif field=='initial_state':raw['native_dynamics']['initial_state']['qpos_rad'][0]=.01
            else:raw['nonlinear_capability']['settings']={'changed':True}
            replacement=save(self.host,raw,'explicit_invalid_t1_fixture');update(self.host,analysis_results=[*state(self.host)['analysis_results'],replacement])
            bad=q.model_copy(deep=True);bad.nonlinear_response.directions[0].t1_results[1]=replacement
            self.assertIn('not_comparable',saved_context(self.host,bad)['directions'][0])

    def test_route_override_removes_polar_effect_and_exposes_existing_stations(self):
        params=deepcopy(self.params);params.update(segment_count=1,segments={'0':params['segments']['0']})
        params['spans'][0]['last_segment']=0
        _,one=self.generate(params)
        params['route_overrides']={str(i):deepcopy(t['points']) for i,t in enumerate(one['configuration']['robot']['structure']['data']['tendons'])}
        for points in params['route_overrides'].values():points[-1]['attachment']['s']-=.001
        ref,c=self.generate(params);rows={r['parameter_id']:r for r in opt.family_analysis_parameters(state(self.host)['spec'],c)}
        self.assertFalse(rows['spans.0.radius_m']['continuous_perturbation'])
        self.assertTrue(any(p.startswith('route_overrides.0.') and r['continuous_perturbation'] for p,r in rows.items()))
        with self.assertRaisesRegex(ValueError,'NO_EFFECT'):opt.family_parameters(state(self.host)['spec'],c,'spans.0.radius_m')

    def test_discrete_channel_change_is_finite_contrast_without_derivative(self):
        params=deepcopy(self.params);params['tendon_count']=4;params['spans'][0]['count']=4;params['spans'][0]['angular_offsets_rad']=[0.]*4
        ref,c=self.generate(params);other=self.t1(ref,c,2.5)
        q=self.query([dict(direction_id='channels',mode='finite_comparison',comparison_variables=['tendon_count'],t1_results=[self.baseline,other])])
        ctx=saved_context(self.host,q);self.assertNotIn('not_comparable',ctx['directions'][0],ctx)
        out=response(ctx)['directions'][0]
        self.assertEqual(out['derivative_scope'],'no_continuous_derivative');self.assertFalse(out['fixed_control_comparable'])
        self.assertNotIn('reoptimized',out)

    def test_versioned_schema_retains_single_parameter_serialization(self):
        legacy=dict(variable='segments.0.young_pa',unit='Pa',t1_results=[self.baseline]*3)
        from tools.research.contracts import NonlinearStructureResponse
        self.assertEqual(plain(NonlinearStructureResponse(**legacy)),legacy)
        bad=self.direction({'segments.0.young_pa':1.},10000.,'Pa');bad['coordinates']=[0,-1,2]
        with self.assertRaises(ValueError):self.query([bad])
        spec=state(self.host)['spec'];spec['family_sensitivity_variables']={'version':'family_sensitivity_v1','variables':['segments.0.young_pa']}
        with self.assertRaisesRegex(ValueError,'AUTHORIZED'):opt.family_parameters(spec,self.base,'spans.0.radius_m')


if __name__=='__main__':unittest.main()
