"""Real FamilySpace rebuilds and explicit synthetic T1 fixtures; no provider/rollouts."""
from copy import deepcopy
from pathlib import Path
import gc
import os
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
        cfg['native_control_limits']=dict(evaluation_requests=3,iterations=1,knots_s=2)
        cfg['budgets']['mathematical_evaluations']=12
        if os.environ.get('SOFTROBOT_NATIVE_PARAMETER_SMOKE')=='1':
            task_path=ROOT/'tasks'/('nonlinear-smoke-'+uuid4().hex+'.json')
            atomic_json(task_path,dict(extends='reach_hold.json',task=dict(timing=dict(timestep_s=.002))))
            cls.addClassCleanup(lambda:task_path.unlink(missing_ok=True))
            cfg['task']='../../tasks/'+task_path.name
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
        if self._testMethodName!='test_capped_real_worker_smoke':self.baseline=self.t1(self.base_ref,self.base,3.)

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
        t.update(initial_metrics=dict(terminal_position_error_m=(j+1)*.001,holding_max_speed_m_s=(j+1)*.01),
            best_metrics=dict(terminal_position_error_m=j*.001,holding_max_speed_m_s=j*.01,
                worst_constraint=dict(kind='holding_speed',time_s=.3,normalized_signed_excess=j)),
            metric_units=dict(terminal_position_error_m='m',holding_max_speed_m_s='m/s'))
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

    def test_evidence_matrix_and_original_l1_sources_remain_readable(self):
        from tools.research import analysis
        from tools.research.evidence_views import result_card
        from tools.research.research_context import mathematical_decision_view
        q=self.query([self.direction({'segments.0.young_pa':1.},10000.,'Pa','material'),
            self.direction({'spans.0.radius_m':1.},.00001,'m','routing')])
        cfg=self.base['configuration'];binding=dict(candidate=self.base_ref,candidate_id=self.base['candidate_id'],
            effective_configuration_identity=digest(cfg),task_identity=digest(cfg['task']))
        value=analysis.calculate(cfg,binding,plain(q),design_context=saved_context(self.host,q))
        value.update(candidate=self.base_ref,implementation=state(self.host)['freeze'],charged_analysis_evaluations=1,charged_numerical_s=.01)
        ref=save(self.host,value,'explicit_synthetic_t2_fixture');update(self.host,analysis_results=[*state(self.host)['analysis_results'],ref])
        matrix=value['nonlinear_response']['directions'][0]['metric_responses']
        self.assertEqual({m['unit'] for m in matrix},{'m','m/s'})
        for m in matrix:
            for kind in ('fixed_control','reoptimized_control'):
                for source,number in zip(m[kind]['sources'],m[kind]['values']):
                    self.assertEqual(core.read_evidence(self.host,source,record_read=False),number)
        card=plain(result_card(self.host,ref));view=mathematical_decision_view(card)
        self.assertIn('nonlinear_response',view);self.assertEqual(view['nonlinear_response']['direction_count'],2)
        self.assertNotIn('observations',view['nonlinear_response']);self.assertNotIn('observed_task_pass',card['evidence_summary']['supported_inferences'])
        self.assertEqual(core.read_evidence(self.host,dict(reference=ref,view='working_set',pointer='/mathematical_decision_view/nonlinear_response'),record_read=False),view['nonlinear_response'])
        for quantity in card['mathematics']['quantities']:
            self.assertEqual(core.read_evidence(self.host,quantity['source'],record_read=False),quantity['value'])
        for resource in card['resources']:
            if resource['amount'] is not None:self.assertEqual(core.read_evidence(self.host,resource['source'],record_read=False),resource['amount'])

    def test_catalog_exposes_exact_admitted_requests(self):
        from tools.research.task_constraints import mathematical_method_view
        self.query([self.direction({'segments.0.young_pa':1.},10000.,'Pa','material'),
            self.direction({'spans.0.radius_m':1.},.00001,'m','route')])
        prepared=mathematical_method_view(self.host,self.base_ref)['methods'][T2]
        self.assertGreaterEqual(len(prepared['ready_requests']),2)
        batch=AnalysisRequest.model_validate(prepared['batch_request'])
        self.assertEqual(len(batch.nonlinear_response.directions),2)
        self.assertTrue(all('not_comparable' not in d for d in saved_context(self.host,batch)['directions']))
        self.assertEqual(state(self.host)['mathematical_evaluations'],0)

    @unittest.skipUnless(os.environ.get('SOFTROBOT_NATIVE_PARAMETER_SMOKE')=='1','Explicit capped engineering smoke only')
    def test_capped_real_worker_smoke(self):
        from tools.research import analysis
        from tools.research.contracts import ControlSeedRequest
        from tools.research.physical_replay import seed_control
        from tools.research.state import core_hashes,science_hashes
        from tools.research.evidence_views import result_card
        from tools.research.research_context import mathematical_decision_view
        from tools.research.task_constraints import mathematical_method_view
        source_hashes=dict(core=core_hashes(),science=science_hashes())
        update(self.host,freeze='engineering-native-parameter-smoke-'+digest(source_hashes))
        params=deepcopy(self.params);params.update(segment_count=1,segments={'0':params['segments']['0']})
        params['spans'][0]['last_segment']=0
        self.base_ref,self.base=self.generate(params);self.params=opt.family_parameters(state(self.host)['spec'],self.base,'segments.0.young_pa')[0]
        variants=[(self.base_ref,self.base)];directions=[]
        section=next(r['parameter_id'] for r in opt.family_analysis_parameters(state(self.host)['spec'],self.base)
            if r['category']=='geometry' and r['continuous_perturbation'])
        for path,step,unit in [('segments.0.young_pa',10000.,'Pa'),('spans.0.radius_m',.00001,'m')]:
            indices=[]
            for delta in (-step,step):
                params=deepcopy(self.params);design.set_parameter(params,path,design.parameter_value(params,path)+delta)
                variants.append(self.generate(params));indices.append(len(variants)-1)
            directions.append(dict(direction_id=path,variables={path:1.},coordinate_unit=unit,coordinates=[0.,-step,step],indices=indices))
        duration=state(self.host)['spec']['analysis_protocol']['duration_s']
        steps_per_rollout=round(duration/self.base['configuration']['task']['timing']['timestep_s'])
        self.assertEqual(len(variants),5);self.assertEqual(steps_per_rollout,175)
        cap=dict(t1_candidates=5,callbacks_per_candidate=3,physics_steps=2625,mathematical_evaluations=6,independent_physical_replays=0,provider_requests=0)
        settings=dict(version='local_control_search_v2',knots_s=[0.,duration-.01],correction_window_s=[0.,duration],
            evaluation_requests=3,iterations=1,active_coefficients=[0])
        t1_refs=[];costs=[]
        # This is an explicitly bounded engineering fixture, not a formal Study
        # or Agent invocation. The original dispatch owns admission/worker/Store.
        for index,(candidate,c) in enumerate(variants):
            source=seed_control(self.host,ControlSeedRequest(candidate=candidate,tensions_n=[[1.,1.,1.]]))
            out=analysis.dispatch(self.host,dict(candidate=candidate,operation='mujoco_nonlinear_task_capability_v1',model_source='mujoco',
                operating_point='standardized_initial_pretension',protocol=state(self.host)['spec']['analysis_protocol'],
                control_optimization=dict(source=source['source'],settings=settings)),
                'bounded-native-parameter-'+str(index),guard=lambda *a:None,origin='engineering_preflight')
            ref=out['reference'];raw=self.host.store.artifact(ref)
            if out['status']!='computed':
                print('NATIVE_SMOKE_FAILURE',raw.get('error'),raw.get('reason'),flush=True)
                destination=ROOT/'evidence'/('mujoco_parameter_smoke_failure_'+self.host.run_id)
                core.export(self.host,destination)
            self.assertEqual(out['status'],'computed',dict(error=raw.get('error'),reason=raw.get('reason')))
            self.assertLessEqual(raw['nonlinear_capability']['callbacks'],3)
            t1_refs.append(ref);costs.append(raw['native_dynamics']['cost'])
        for d in directions:d['t1_results']=[t1_refs[0],*[t1_refs[i] for i in d.pop('indices')]]
        q=plain(self.query(directions));before=state(self.host)
        t2=analysis.dispatch(self.host,q,'bounded-native-parameter-t2',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(t2['status'],'computed',t2)
        raw=self.host.store.artifact(t2['reference'])
        output=os.environ.get('SOFTROBOT_NATIVE_PARAMETER_EXPORT')
        if output:
            destination=(ROOT/output).resolve()
            self.assertEqual(destination.parent,ROOT/'evidence')
            self.assertFalse(destination.exists(),'Preserve completed evidence; use another destination')
            core.export(self.host,destination)  # Save all successful numerical work before projection checks.
        self.assertEqual(raw['nonlinear_response']['cost']['physics_steps'],0)
        self.assertEqual(raw['nonlinear_response']['cost']['reused_t1_results'],5)
        self.assertEqual(state(self.host)['mathematical_evaluations'],6)
        numerical_before_reuse=state(self.host)['numerical_s']
        reuse=analysis.dispatch(self.host,q,'bounded-native-parameter-t2',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(reuse['operation_reuse']['additional_analysis_evaluations'],0)
        self.assertEqual(state(self.host)['numerical_s'],numerical_before_reuse)
        self.assertLessEqual(sum(c['physics_steps'] for c in costs),cap['physics_steps'])
        self.assertEqual(self.host.store.remaining()['used']['backend_solves'],0)
        self.assertEqual(self.host.store.remaining()['used']['model_calls'],0)
        self.assertEqual(len(raw['nonlinear_response']['comparison_summary']),2)
        self.assertTrue(all(d['direction_status']=='unresolved' for d in raw['nonlinear_response']['directions']))
        catalog=mathematical_method_view(self.host,self.base_ref)['methods'][T2]
        self.assertIsNotNone(catalog['batch_request'])
        card=plain(result_card(self.host,t2['reference']));view=mathematical_decision_view(card)
        query=dict(reference=t2['reference'],view='working_set',pointer='/mathematical_decision_view/nonlinear_response')
        self.assertEqual(core.read_evidence(self.host,query,record_read=False),view['nonlinear_response'])
        self.assertEqual(len(raw['nonlinear_response']['referenced_t1_costs']),5)
        self.assertAlmostEqual(sum(c['numerical_s'] for c in state(self.host)['analysis_costs']),
            sum(self.host.store.artifact(r)['charged_numerical_s'] for r in [*t1_refs,t2['reference']]))
        output=os.environ.get('SOFTROBOT_NATIVE_PARAMETER_EXPORT')
        if output:
            destination=(ROOT/output).resolve()
            self.assertEqual(destination.parent,ROOT/'evidence')
            self.assertTrue(destination.exists())
            snapshot=dict(label='Capped real MuJoCo engineering smoke; no formal Study, provider or independent task acceptance',
                source_hashes=source_hashes,cap=cap,actual=dict(t1_costs=costs,total_physics_steps=sum(c['physics_steps'] for c in costs),
                    mathematical_evaluations=state(self.host)['mathematical_evaluations'],numerical_s=state(self.host)['numerical_s'],
                    t2_preparation_s=raw.get('admission_preparation_numerical_s'),t2_worker_s=raw['boundary']['elapsed_s']),
                baseline_candidate=self.base_ref,t1_results=t1_refs,t2_result=t2['reference'],request=q,
                exact_l1_query=query,decision_view=view,capability_rows=opt.family_analysis_parameters(state(self.host)['spec'],self.base),
                comparison_summary=raw['nonlinear_response']['comparison_summary'])
            atomic_json(destination/'example.json',snapshot)
            from tools.research.numerics import archived
            self.assertEqual(archived(output,t2['reference']),raw)
        print('NATIVE_PARAMETER_SMOKE',dict(physics_steps=sum(c['physics_steps'] for c in costs),rollouts=sum(c['rollouts'] for c in costs),
            mathematical_evaluations=state(self.host)['mathematical_evaluations'],t2_new_integrations=0),flush=True)

    def test_failed_native_callback_retains_confirmed_partial_cost(self):
        from tools.research.native_control import calculate
        from tools.research.contracts import LocalControlSearchSettings
        from tools.research.task_constraints import describe_analysis_requirements
        from types import SimpleNamespace
        import numpy as np
        events=[];raw=self.host.store.artifact(self.baseline)
        class FailedNative:
            limits=np.tile([0.,8.],(3,1))
            def __init__(self,cfg):self.cost=dict(model_builds=1,rollouts=0,physics_steps=0)
            def reconstruct(self,point):return point,object()
            def rollout_sequence(self,*args):
                self.cost.update(rollouts=1,physics_steps=17)
                raise ValueError('EXPLICIT_SYNTHETIC_PARTIAL_CALLBACK_FAILURE')
        settings=LocalControlSearchSettings(version='local_control_search_v2',knots_s=[0.,.34],correction_window_s=[0.,.35],
            evaluation_requests=3,iterations=1,active_coefficients=[0])
        q=SimpleNamespace(control_optimization=SimpleNamespace(settings=settings),protocol=SimpleNamespace(period_s=.01))
        point=dict(actual_time_s=0.,native_replay=dict(rows=[]))
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',FailedNative):
            with self.assertRaisesRegex(ValueError,'SYNTHETIC_PARTIAL'):
                calculate(self.base['configuration'],{},q,point,describe_analysis_requirements(self.base['configuration'],{}),
                    dict(schedule={**raw['native_dynamics']['original_schedule'],'provenance':{'explicit_synthetic_fixture':True}}),checkpoint=lambda name,value:events.append(value))
        self.assertEqual(events[-1]['cost']['physics_steps'],17)
        self.assertEqual(events[-1]['callback_status'],'incomplete')
        self.assertEqual(events[-1]['completed_rollouts'],0)

    def test_failed_worker_settlement_keeps_partial_cost_in_original_ledger(self):
        from tools.research import analysis
        from tools.research.contracts import ControlSeedRequest
        from tools.research.physical_replay import seed_control
        from types import SimpleNamespace
        source=seed_control(self.host,ControlSeedRequest(candidate=self.base_ref,tensions_n=[[1.,1.,1.]]))
        def worker(argv,log,timeout):
            path=Path(argv[-1])
            atomic_json(path.with_name('result.json'),dict(status='execution_incomplete',reason='explicit_synthetic_partial_failure'))
            atomic_json(path.with_name('numerical_native_progress_0001.json'),dict(callback_status='incomplete',completed_rollouts=0,
                cost=dict(model_builds=1,rollouts=1,physics_steps=17,kernel_wall_s=.001)))
            return SimpleNamespace(returncode=0)
        query=dict(candidate=self.base_ref,operation='mujoco_nonlinear_task_capability_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=state(self.host)['spec']['analysis_protocol'],
            control_optimization=dict(source=source['source'],settings=dict(version='local_control_search_v2',
                knots_s=[0.,.34],correction_window_s=[0.,.35],evaluation_requests=3,iterations=1,active_coefficients=[0])))
        with patch('tools.service_execution._run_contained',side_effect=worker):
            out=analysis.dispatch(self.host,query,'explicit-synthetic-worker-failure',guard=lambda *a:None,origin='engineering_preflight')
        raw=self.host.store.artifact(out['reference'])
        self.assertEqual(raw['physics_steps_lower_bound'],17)
        self.assertEqual(raw['internal_calculations'][0]['physics_steps'],17)
        self.assertEqual(raw['operation'],query['operation'])
        self.assertEqual(state(self.host)['analysis_costs'][-1]['internal_calculations'][0]['physics_steps'],17)
        before=deepcopy(state(self.host));reuse=analysis.dispatch(self.host,query,'explicit-synthetic-worker-failure',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(reuse['operation_reuse']['additional_analysis_evaluations'],0)
        self.assertEqual(state(self.host),before)

    def test_discrete_section_has_legal_choices_and_no_derivative(self):
        path='segments.0.sections.0.kind';params=deepcopy(self.params)
        params['segments']['0']['sections'][0].update(kind='circle',parameters=dict(radius_m=.008))
        ref,c=self.generate(params);other=self.t1(ref,c,2.)
        query=self.query([dict(direction_id='section-kind',mode='finite_comparison',comparison_variables=[path],t1_results=[self.baseline,other])])
        context=saved_context(self.host,query);self.assertNotIn('not_comparable',context['directions'][0],context)
        result=response(context)['directions'][0]
        self.assertIn('circle',result['parameters'][path]['choices'])
        self.assertEqual(result['derivative_scope'],'no_continuous_derivative')
        self.assertTrue(result['fixed_control_comparable'])

    def test_model_scope_and_control_method_changes_do_not_merge(self):
        direction=self.direction({'segments.0.young_pa':1.},10000.,'Pa')
        for edit in ('mesh','controller'):
            params=deepcopy(self.params)
            params['segments']['0']['young_pa']-=10000.
            if edit=='mesh':params['segments']['0']['cells']=5
            else:params['controller_recipe']=dict(holding_tip_speed_weight=.2)
            ref,c=self.generate(params);replacement=self.t1(ref,c,2.)
            modified=deepcopy(direction);modified['t1_results'][1]=replacement
            self.assertIn('not_comparable',saved_context(self.host,self.query([modified]))['directions'][0])

    def test_versioned_schema_retains_single_parameter_serialization(self):
        legacy=dict(variable='segments.0.young_pa',unit='Pa',t1_results=[self.baseline]*3)
        from tools.research.contracts import NonlinearStructureResponse
        self.assertEqual(plain(NonlinearStructureResponse(**legacy)),legacy)
        bad=self.direction({'segments.0.young_pa':1.},10000.,'Pa');bad['coordinates']=[0,-1,2]
        with self.assertRaises(ValueError):self.query([bad])
        spec=state(self.host)['spec'];spec['family_sensitivity_variables']={'version':'family_sensitivity_v1','variables':['segments.0.young_pa']}
        with self.assertRaisesRegex(ValueError,'AUTHORIZED'):opt.family_parameters(spec,self.base,'spans.0.radius_m')


if __name__=='__main__':unittest.main()
