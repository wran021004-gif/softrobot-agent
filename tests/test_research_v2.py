"""Focused finite-interface checks; backend substitute is never science evidence."""
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
import numpy as np
from schemas.platform import SessionInput
from tools.platform_store import Store,plain
from tools.platform_host import Host
from tools.research_v2 import configuration,TOOLS
from tools.research_execution import prepare_execution_request,construct_candidate,invoke
from tools.platform_registry import registry
from extensions.tendon_family import finite_templates as finite
from extensions.tendon_family.compiler import resolve
from extensions.tendon_family.geometry import geometry
from tools.state_io import atomic_json,digest


class FiniteV2Tests(TestCase):
    def setUp(self):
        self.cfg=configuration();self.reg=registry()

    def candidate(self,key,changes=None):
        return SessionInput.model_validate(prepare_execution_request(self.cfg,{'template':key,**(changes or {})},candidate_id='fixture-'+key)['candidate']['effective'])

    def host(self,cfg=None):
        temp=TemporaryDirectory(dir=Path('runs').resolve())
        self.assertTrue(Path(temp.name).resolve().is_relative_to(Path('runs').resolve()))
        def cleanup():
            import gc
            gc.collect()
            temp.cleanup()
        self.addCleanup(cleanup)
        folder=Path(temp.name).resolve();cfg=deepcopy(cfg or self.cfg)
        cfg['policy']['tool_bindings'].update({t:'1.0.0' for t in ('research.capability_catalog','research.select_template','research.candidate_dimensions')})
        cfg['policy']['allowed_tools']=list(cfg['policy']['tool_bindings'])
        store=Store(folder/'store')
        self.enterContext(patch('tools.platform_store.ROOT',folder))
        store.create(dict(project_id='offline-v2-'+uuid4().hex,grant_id='fixture-'+uuid4().hex,
            authorization_source='Offline focused fixture; real solver and provider blocked',budget=cfg['policy']['budget'],
            exclusive_resources={'backend.family_mujoco':1}))
        host=Host(store.root,cfg['run_id']);host.create(cfg);host.resume()
        return host

    def test_native_actual_capacity_and_direct_business_schema(self):
        from tools.research_v2 import native_configuration
        from tools.investigation_contract import BusinessFieldsAdapter
        from tools.platform_models import payload_for
        from tools.context_assembly import check_outgoing_request
        cfg=native_configuration();host=self.host(cfg)
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state']
            state['role_context']=dict(role='design',phase='finite_capability_use',instructions='Choose a finite template through the actual public entry.',shared_provider_capacity=True)
            host.store.update_state(db,host.run_id,state)
        adapter=BusinessFieldsAdapter();payload=payload_for(host,adapter)
        audit=check_outgoing_request(payload,cfg['policy']['model'],'research_decision')
        self.assertEqual(payload['max_tokens'],32768)
        self.assertEqual(cfg['policy']['model']['context_bytes'],4194304)
        self.assertTrue(any(t['function']['description'].startswith('research.select_template@') for t in payload['tools']))
        item=next(t for t in payload['tools'] if t['function']['description'].startswith('research.select_template@'))
        self.assertIn('template',item['function']['parameters']['properties'])
        self.assertNotIn('arguments',item['function']['parameters']['properties'])
        cfg['policy']['model']['context_guard']['context_limit_tokens']=100
        with self.assertRaises(ValueError):check_outgoing_request(payload,cfg['policy']['model'],'research_decision')

    def test_preservation_discovery_selection_order_bounds_and_old_versions(self):
        original=finite.catalog()['scientific_source'];t0=self.candidate('T0')
        self.assertEqual(plain(t0.robot),original['robot']);self.assertEqual(plain(t0.task),original['task'])
        self.assertEqual(plain(t0.policy.discretization),original['policy']['discretization'])
        self.assertEqual(t0.policy.controller.parameters.data,original['policy']['controller']['parameters']['data'])
        host=self.host()
        menu=invoke(host,'research.capability_catalog',{},request_id='catalog')
        self.assertEqual(menu['execution_status'],'completed',menu)
        self.assertIn('template',host.store.artifact(menu['output'])['detail']['usable_pool'])
        choice=invoke(host,'research.select_template',{'template':'T1'},request_id='select')
        self.assertEqual(choice['execution_status'],'completed',choice)
        chosen=host.store.artifact(choice['output'])['detail']
        self.assertEqual(chosen['method'],'search.family_explicit@1.0.0')
        from tools.platform_search import parameter_search
        with self.assertRaisesRegex(ValueError,'CHOICES'):
            parameter_search(self.cfg,'search.family_coordinate@1.0.0',{'template':{'kind':'discrete','choices':['T0','T1']}})
        prepared=invoke(host,'research.prepare_candidate',dict(candidate_id='public-T1',changes=chosen['changes']),request_id='prepare')
        self.assertEqual(prepared['execution_status'],'completed',prepared)
        cfg=host.store.artifact(prepared['output'])['configuration']
        dimensions=invoke(host,'research.candidate_dimensions',dict(configuration=cfg),request_id='dimensions')
        detail=host.store.artifact(dimensions['output'])['detail']
        self.assertEqual(detail['tendon_input_order'],['near_t0','near_t1','near_t2','near_t3','far_t0','far_t1','far_t2','far_t3'])
        self.assertEqual(detail['force_limits_n'],[8.]*8)
        np.testing.assert_array_equal(detail['transmission'],np.eye(8))
        self.assertEqual(detail['numerical_initialization']['nominal']['u0'],[.2]*8)
        self.assertFalse(detail['numerical_initialization']['provenance']['reused'])
        old=plain(self.candidate('T2'));old['policy']['controller']['version']='9.0.0'
        from extensions.tendon_family.gvs_profile import checked_reach
        with self.assertRaises((ValueError,KeyError)):checked_reach(old)
        old=deepcopy(self.cfg);old['policy']['candidate_builder']['version']='1.2.0'
        with self.assertRaisesRegex(ValueError,'CAPABILITY_UNAVAILABLE'):construct_candidate(old,{'template':'T1'})
        with self.assertRaisesRegex(ValueError,'INACTIVE'):self.candidate('T1',{'components/middle/length_m':.055})
        with self.assertRaisesRegex(ValueError,'OUT_OF_BOUNDS'):self.candidate('T2',{'components/far/length_m':.11})
        limited=deepcopy(self.cfg);limited['policy']['candidate_builder']['parameters']['data']['templates'].pop('T3')
        limited['policy']['candidate_builder']['parameters']['data']['template_discretizations'].pop('T3')
        with self.assertRaisesRegex(ValueError,'TEMPLATE_NOT_AUTHORIZED'):construct_candidate(limited,{'template':'T3'})

    def test_named_nonzero_mapping_dimensions_and_independent_route_derivatives(self):
        from extensions.tendon_family.gvs_projection import discretization_jacobian
        from extensions.tendon_family.gvs_basis import resolve_basis
        from extensions.tendon_family.routing_radius import locations
        from extensions.tendon_family.candidate import read_parameter
        for key in ('T2','T3'):
            inp=self.candidate(key);design=inp.robot.structure.data;mesh=inp.policy.discretization.data
            info=finite.dimensions(inp);self.assertEqual(info['dimensions']['reduced_state'],36)
            self.assertEqual(info['dimensions']['backend_position'],48)
            mapped=finite.semantic_initialization(design,mesh,inp.policy.controller.parameters.data['recipe']['basis'],
                bends={'near':[.02,-.01],'distal':[-.015,.025]},rates={'near':[.1,-.05],'distal':[.04,-.06]})
            self.assertEqual(mapped['segment_integrals']['middle']['bend_rad'],[-.0075,.0125])
            self.assertEqual(mapped['segment_integrals']['far']['bend_rad'],[-.0075,.0125])
            self.assertLess(mapped['projection']['projection_residual_max_rad_m'],1e-12)
            self.assertLess(mapped['projection']['rate_projection_residual_max_rad_m_s'],1e-12)
            self.assertGreater(np.linalg.norm(list(mapped['initial']['qpos_rad'].values())),0)
            scaled=self.candidate(key,{'design/near_routing_radius_scale':1.01,'design/middle_routing_radius_scale':.99})
            source=finite.catalog()['templates'][key]['design']
            owners=locations(source)
            self.assertTrue(any(r['owner']=='middle' and '/guide_holes/' in r['path'] for r in owners))
            for row in owners:
                scale=1.01 if row['owner']=='near' else .99 if row['owner']=='middle' else 1.
                np.testing.assert_allclose(read_parameter(scaled.robot.structure.data,row['path']),[row['point'][0],*(np.array(row['point'][1:])*scale)],atol=1e-14)
            continued=construct_candidate(plain(scaled),{'control/recipe/holding_tip_speed_weight':.075})
            self.assertEqual(continued.robot,scaled.robot)
            physics=resolve(design,mesh);basis=resolve_basis(design,inp.policy.controller.parameters.data['recipe']['basis'])
            matrix=discretization_jacobian(physics,basis)
            q=np.asarray(mapped['projection']['q_gvs']);angles=matrix@q
            exact=geometry(physics,angles)['Jlength']@matrix
            h=1e-5;columns=[]
            for index in range(len(q)):
                delta=np.zeros_like(q);delta[index]=h
                columns.append((geometry(physics,matrix@(q+delta))['lengths']-geometry(physics,matrix@(q-delta))['lengths'])/(2*h))
            numerical=np.column_stack(columns)
            np.testing.assert_allclose(exact,numerical,rtol=2e-6,atol=2e-9)
            tension=np.linspace(.1,.5,len(exact));np.testing.assert_allclose(-exact.T@tension,-numerical.T@tension,rtol=2e-6,atol=2e-9)

    def test_public_execution_evaluation_profile_ownership_and_receipt_recovery(self):
        """Explicit static backend substitute: real public chain, no physics claim."""
        host=self.host()
        def configure(controller,physics,plan):
            controller.physics=physics;controller.plan=plan;controller.observations=[]
        def substitute(backend,timeout_s):
            from extensions.tendon_family.mjcf import compile_xml
            p,s=backend.physics,backend.scene
            compile_xml(p,s,backend.config,backend.folder/'robot.xml')
            g=geometry(p,np.zeros(len(p['dofs'])));rows=[];observations=[]
            for index in range(35):
                obs=dict(time_s=index*.01,optimization_nonconverged=False,solver_failed=False,
                    solver_error=None,failure_response_used=False,deadline_missed=False,update_wall_s=0.,
                    graph_construction_s=0.,plan_accepted=True,optimization_constraint_violation=0.)
                observations.append(obs)
                rows.append(dict(time_s=(index+1)*.01,solver_time_s=index*.01,tip_m=g['tip'].tolist(),
                    qpos_rad=s['qpos_rad'],qvel_rad_s=s['qvel_rad_s'],tendon_length_m=g['lengths'].tolist(),
                    tendon_length_change_m=[0.]*len(p['tendons']),tendon_length_rate_m_s=[0.]*len(p['tendons']),
                    tension_n=[.2]*len(p['tendons']),desired_tension_n=[.2]*len(p['tendons']),
                    solver_qfrc_actuator_nm=[0.]*len(p['dofs']),external_torque_nm=[0.]*len(p['dofs'])))
            backend.timings['solve']=0.
            return rows,observations,True,'STATIC_OFFLINE_BACKEND_SUBSTITUTE',0
        with patch('extensions.tendon_family.gvs_nmpc.DeadlineReachNMPCController.configure',configure),patch(
                'extensions.tendon_family.backends.MujocoBackend.solve',substitute),patch(
                'tools.platform_models.DeepSeekAdapter._transport',side_effect=AssertionError('No provider in offline fixture')):
            prepared=invoke(host,'research.prepare_candidate',dict(candidate_id='fixture-T3',changes={'template':'T3'}),request_id='prepare')
            self.assertEqual(prepared['execution_status'],'completed',prepared)
            sim=invoke(host,'simulation.run',dict(candidate_id='fixture-T3',changes={'template':'T3'}),request_id='simulate')
            self.assertEqual(sim['execution_status'],'completed',sim)
            recovered=invoke(host,'simulation.run',dict(candidate_id='fixture-T3',changes={'template':'T3'}),request_id='simulate')
            self.assertEqual(recovered['execution_id'],sim['execution_id'])
            self.assertEqual(host.store.remaining()['used']['backend_solves'],1)
            ev=invoke(host,'evaluation.run',dict(result=sim['output'],execution_id=sim['execution_id']),request_id='evaluate')
            self.assertEqual(ev['execution_status'],'completed',ev)
            profile=invoke(host,'control.profile_report',dict(simulation_request_id='simulate',evaluation_request_id='evaluate'),request_id='profile')
            self.assertEqual(profile['execution_status'],'completed',profile)
            cfg=host.store.artifact(prepared['output'])['configuration']
            detail=host.store.artifact(profile['output'])['detail']
            self.assertEqual(detail['configuration'],cfg)
            self.assertEqual(detail['execution_scope']['robot']['identity'],digest(host.store.artifact(cfg)['effective']['robot']))
            joint=invoke(host,'research.task_acceptance',dict(configuration=cfg,evaluation=ev['output'],profile=profile['output']),request_id='joint')
            self.assertEqual(joint['execution_status'],'completed',joint)
            self.assertEqual(host.store.artifact(joint['output'])['detail']['status'],'valid_failure')
            self.assertEqual(host.store.artifact(ev['output'])['validity'],'valid')
            wrong=deepcopy(host.store.artifact(cfg));wrong['baseline_identity']='0'*64
            from extensions.tendon_family.gvs_reporting import report_configuration
            with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):report_configuration(wrong,SessionInput.model_validate(host.store.session(host.run_id)['snapshot']['input']))
