"""Focused engineering validation; every scientific/transport execution is blocked."""
from copy import deepcopy
from pathlib import Path
import shutil
from types import SimpleNamespace
from uuid import uuid4
from unittest import TestCase
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from contextlib import ExitStack
import io
import json
import numpy as np

from schemas.platform import SessionInput
from tools.platform_registry import registry
from tools.platform_store import Store,plain,zero
from tools.state_io import read,digest
from tools.research_mainline3 import configuration,SOURCE,fixed_pipeline
from tools.research_execution import construct_candidate,prepare_execution_request,replay_analysis
from tools.parameter_catalog import effective_catalog,study_input
from extensions.tendon_family.compiler import resolve
from extensions.tendon_family.routing_radius import locations,envelope

ROOT=Path(__file__).resolve().parents[1]


class Mainline3EngineeringTests(TestCase):
    def setUp(self):
        self.cfg=configuration();self.reg=registry()
        self.blockers=ExitStack()
        # These boundaries must never be crossed in this engineering suite.
        for target in ('extensions.optimization.ipopt.IpoptSolver.solve',
                       'scipy.optimize.least_squares','scipy.optimize.minimize',
                       'scipy.integrate.solve_ivp','tools.platform_models.DeepSeekAdapter._transport',
                       'extensions.tendon_family.backends.MujocoBackend.solve'):
            self.blockers.enter_context(patch(target,side_effect=AssertionError('PROHIBITED_EXECUTION: '+target)))
        self.addCleanup(self.blockers.close)

    def build(self,changes,cfg=None):return plain(construct_candidate(cfg or self.cfg,changes,self.reg))

    def test_actual_radius_geometry_ownership_identity_and_input_order(self):
        source=self.cfg['policy']['candidate_builder']['parameters']['data']['semantic_source']
        changes={'design/near_routing_radius_scale':1.01,'design/far_routing_radius_scale':.99}
        candidate=self.build(changes);design=candidate['robot']['structure']['data']
        from extensions.tendon_family.candidate import read_parameter
        for row in locations(source):
            point=read_parameter(design,row['path']);scale=changes['design/'+row['owner']+'_routing_radius_scale']
            np.testing.assert_allclose(point,[row['point'][0],*(np.array(row['point'][1:])*scale)])
        self.assertEqual(design['actuators'],source['actuators'])
        from extensions.tendon_family.design_decisions import physical_effects
        self.assertTrue(any(row['category']=='routing' for row in physical_effects(source,design)))
        self.assertTrue(set(self.reg.get('controller.gvs_nmpc','7.0.0').sources)<=
            set(self.reg.get('controller.gvs_nmpc','9.0.0').sources))
        self.assertEqual([c.get('hole_radius_m') for c in design['components']],
                         [c.get('hole_radius_m') for c in source['components']])
        # The distal route's base/proximal/boundary points all belong to near.
        distal=[r for r in locations(source) if 'far_t0' in r['path']]
        self.assertEqual([r['owner'] for r in distal],['near','near','far','far'])
        self.assertTrue(all(r['owner']=='near' for r in locations(source) if '/guide_holes/' in r['path']))
        again=self.build({'design/near_routing_radius_scale':.99},candidate)
        for row in locations(source):
            if row['owner']=='near':
                np.testing.assert_allclose(read_parameter(again['robot']['structure']['data'],row['path']),
                    [row['point'][0],*(np.array(row['point'][1:])*.99)])
        p=resolve(design,candidate['policy']['discretization']['data'])
        old=resolve(self.cfg['robot']['structure']['data'],self.cfg['policy']['discretization']['data'])
        self.assertNotEqual(p['identity'],old['identity']);self.assertEqual(p['dofs'],old['dofs'])
        self.assertEqual([t['entity'] for t in p['tendons']],[t['entity'] for t in old['tendons']])
        np.testing.assert_array_equal(p['transmission'],old['transmission'])
        from extensions.tendon_family.geometry import geometry
        g=geometry(p,np.zeros(len(p['dofs'])));before=geometry(old,np.zeros(len(old['dofs'])))
        self.assertEqual(g['Jlength'].shape,(6,48))
        self.assertFalse(np.allclose(g['Jlength'],before['Jlength']))
        # Genuine MJCF/MuJoCo model compilation, without stepping or forward solves.
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.mjcf import compile_xml
        import mujoco
        inp=SessionInput.model_validate(candidate);scene=assemble(inp,p)
        stream=io.BytesIO();compile_xml(p,scene,self.reg.parse(inp.policy.backend.parameters),stream)
        model=mujoco.MjModel.from_xml_string(stream.getvalue().decode())
        self.assertEqual(model.nv,48);self.assertEqual(model.ntendon,6)
        self.assertEqual([model.tendon(t['entity']).name for t in p['tendons']],[t['entity'] for t in p['tendons']])

    def test_geometry_bounds_nonuniform_layout_and_historical_controller_rejection(self):
        source=self.cfg['policy']['candidate_builder']['parameters']['data']['semantic_source']
        bounds=envelope(source,'near');self.assertGreater(bounds['exclusive_minimum'],0)
        self.assertLess(bounds['exclusive_maximum'],2)
        from extensions.tendon_family.routing_radius import transform,normalize
        with self.assertRaisesRegex(ValueError,'ROUTING_GEOMETRY_BOUND'):
            transform(deepcopy(source),source,{'near':bounds['exclusive_minimum']})
        with self.assertRaisesRegex(ValueError,'GRANT_EXCEEDS_ROUTING_GEOMETRY'):
            study_input(self.cfg,{'design/near_routing_radius_scale':dict(bounds=[.01,2.])},builder_version='1.2.0')
        changed=self.build({'design/near_routing_radius_scale':1.01})
        original=deepcopy(changed);changed['robot']['structure']['data']['tendons'][0]['points'][0]['attachment']['position_m'][1]*=1.01
        with self.assertRaisesRegex(ValueError,'UNIFORM_SEGMENT'):
            normalize(changed['robot']['structure']['data'],source)
        original['policy']['controller']['version']='7.0.0'
        from extensions.tendon_family.gvs_profile import checked_reach
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_PHYSICS'):
            checked_reach(original)

    def test_actual_numerical_symbolic_preparation_and_public_request(self):
        prepared=prepare_execution_request(self.cfg,{'design/far_routing_radius_scale':.99},candidate_id='offline-radius')
        inp=SessionInput.model_validate(prepared['candidate']['effective'])
        from extensions.tendon_family.gvs_profile import reach_numerical
        numerical=reach_numerical(inp)
        self.assertEqual(len(numerical['coordinate_order']),12);self.assertEqual(len(numerical['tendon_order']),6)
        self.assertEqual(np.asarray(numerical['warm_guess']['states']).shape,(11,24))
        self.assertEqual(np.asarray(numerical['warm_guess']['tensions']).shape,(10,6))
        self.assertFalse(numerical['provenance']['historical_states_reused'])
        self.assertFalse(numerical['provenance']['nominal_is_current_target_solution'])
        # Actual public preparation hook and artifact persistence, without configure/command.
        host,_=self.isolated_host()
        from schemas.platform import ToolRequest
        from tools.platform_host import InvocationContext
        from extensions.tendon_family.gvs_nmpc import DeadlineReachNMPCController
        from extensions.tendon_family.gvs_profile import prepare_execution
        request=ToolRequest(tool_id='research.prepare_candidate',request_id='offline-import',
            arguments=dict(candidate_id='offline-radius'),reason='Offline numerical import hook only')
        row,_=host.store.reserve(host.run_id,request.request_id,digest(plain(request)),host.actor,zero(),kind='offline_engineering')
        ctx=InvocationContext(host,row,request)
        controller=DeadlineReachNMPCController(inp.policy.controller.parameters.data,inp.task.timing.control_period_s)
        prepare_execution(ctx,controller,inp)
        self.assertEqual(controller.preparation['status'],'completed')
        self.assertFalse(controller.preparation['warm_guess_is_execution_evidence'])
        self.assertEqual(host.store.artifact(controller.preparation['source']),numerical)
        from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
        workspace=TrajectoryWorkspace(inp.task,inp.robot,inp.policy.controller.parameters.data['recipe'],
            numerical['measured_initial_state'],numerical['nominal']['u0'],
            settling=inp.policy.controller.parameters.data['settling'])
        self.assertEqual(workspace.n,12);self.assertEqual(workspace.m,6)
        self.assertEqual(len(workspace.problem.constraints),240)
        self.assertEqual(workspace.tendons,numerical['tendon_order'])
        self.assertEqual(prepared['scientific_preparation']['warm_trajectory_regeneration'],'pending_execution')
        self.assertEqual(inp.policy.controller.parameters.data,
            read(SOURCE)['effective']['policy']['controller']['parameters']['data'])
        self.reg.get('simulation.run','1.0.0').input_schema.model_validate(prepared['request']['arguments'])
        # Existing candidate-analysis graph construction is real, without calculating a working point.
        from extensions.tendon_family.math_analysis import make_graph_from_input
        graph=make_graph_from_input(inp,dict(x=numerical['measured_initial_state'],u=numerical['nominal']['u0']))
        self.assertEqual(len(graph[1].x0),24)
        self.assertEqual(graph[3].size_out(0),(3,1))

    def test_catalog_dispatch_permissions_joint_subset_and_tracking_separation(self):
        from tools.research_capabilities import effective_capabilities
        catalog=effective_capabilities(self.cfg,remaining={**zero(),'tool_calls':5})
        self.assertIn('design/near_routing_radius_scale',catalog['parameters']['usable_pool'])
        op=next(o for o in catalog['operations'] if o['id']=='simulation.run')
        self.assertIn('resource_unavailable',op['unavailability_reasons'])
        op=next(o for o in catalog['operations'] if o['id']=='analysis.linearize_configuration')
        self.assertIn('not_authorized',op['unavailability_reasons'])
        for operation in catalog['operations']:
            definition=self.reg.get(operation['id'],operation['version'])
            self.assertEqual(operation['input_contract'],definition.input_schema.__name__)
        changed=self.build({'design/near_routing_radius_scale':1.01,'control/recipe/terminal_tip_speed_weight':.075})
        from tools.candidate_parameters import comparison_scope
        self.assertEqual(comparison_scope(self.cfg),comparison_scope(changed))
        from examples.gvs_tracking import tracking_input
        tracking=tracking_input(reference=dict(interpolation='quintic',start_s=0.,end_s=.4,
            start_m=[.3,0,.15],end_m=[.29,.02,.15],provenance='synthetic fixed reference'))
        # Tracking has no source-relative section/material grant; install length-only declarations.
        space=tracking['policy']['candidate_builder']['parameters']['data']
        space['semantic_source']=deepcopy(tracking['robot']['structure']['data'])
        space['semantic_decisions']={}
        tracking['policy']['candidate_builder']['version']='1.2.0'
        space['parameters']={'components/near/length_m':dict(type='number',bounds=[.15,.17])}
        tracking['policy']['editable']={'components/near/length_m':[.15,.17]}
        from tools.research_tasks import task_adapter
        candidate=construct_candidate(tracking,{'components/near/length_m':.165})
        self.assertEqual(task_adapter(plain(candidate)).check_compatibility()['technical_compatibility']['status'],'supported')
        self.assertEqual(effective_catalog(tracking)['usable_pool'],['components/near/length_m'])
        with self.assertRaisesRegex(ValueError,'TASK_ENVELOPE'):
            construct_candidate(tracking,{'design/far_routing_radius_scale':1.01})

    def isolated_host(self,model_ceiling=5,session_budget=None,operation_allowances=None):
        from tools.platform_host import Host
        folder=ROOT/'runs'/('mainline3-offline-'+uuid4().hex)
        folder.mkdir()
        def cleanup():
            import gc
            gc.collect()
            if not folder.resolve().is_relative_to((ROOT/'runs').resolve()):raise ValueError('TEST_CLEANUP_OUT_OF_SCOPE')
            shutil.rmtree(folder)
        self.addCleanup(cleanup)
        cfg=deepcopy(self.cfg);cfg['run_id']='mainline3-engineering'
        cfg['policy']['allowed_tools']=['research.capabilities','research.prepare_candidate','research.investigate',
            'research.investigation_status','research.investigation_disposition','research.investigation_read','evidence.read']
        cfg['policy']['tool_bindings']={t:'1.0.0' for t in cfg['policy']['allowed_tools']}
        cfg['policy']['budget']=session_budget or {**zero(),'tool_calls':30,'model_calls':8,'wall_s':1200.}
        cfg['policy']['operation_allowances']=operation_allowances or {};cfg['policy']['timeout_s']=30.
        store=Store(folder/'store')
        self.blockers.enter_context(patch('tools.platform_store.ROOT',folder))
        store.create(dict(project_id='offline-'+uuid4().hex,grant_id='fixture-'+uuid4().hex,
            authorization_source='Synthetic offline software fixture; real providers and scientific execution blocked',
            budget=cfg['policy']['budget'],exclusive_resources={}))
        host=Host(store.root,cfg['run_id']);host.create(cfg);host.resume()
        historical=read(ROOT/'runs/stage336_manual_20261001_090616/stage336_audit.json')
        with store.transaction() as db:
            ref=plain(store.put(db,historical['execution']['factual_result']))
            state=store.session(host.run_id,db)['state'];state['role_context']=dict(investigation_grant=dict(
                max_count=5,max_concurrency=2,allowed_tools=['evidence.read'],evidence=[ref],
                per_node_budget={**zero(),'model_calls':1,'tool_calls':1,'wall_s':60.},
                total_budget={**zero(),'model_calls':model_ceiling,'tool_calls':5,'wall_s':300.}))
            store.update_state(db,host.run_id,state)
        return host,ref

    def order(self,key,ref,**extra):
        return dict(investigation_id=key,question='Read saved terminal position error; distinguish acceptance and execution validity',
            evidence=[ref],queries=[dict(reference=ref,pointer='/terminal_error_m',byte_limit=2048,limit=8)],
            allowed_tools=['evidence.read'],budget={**zero(),'model_calls':1,'tool_calls':1,'wall_s':60.},
            timeout_s=30.,stop_conditions=['Return one bounded report','No new scientific computation'],**extra)

    def report(self,ref,children=()):
        from tools.research_investigations import InvestigationReturn
        return InvestigationReturn(facts=[dict(statement='Saved terminal error',reference=ref,pointer='/terminal_error_m',
            value=.06672099201814737)],interpretation='Saved failure does not identify a dominant cause',
            unknowns=['Changed-radius performance remains unvalidated'],children=list(children))

    def test_integrated_discovery_build_fixed_orchestration_saved_evidence_and_disposition(self):
        host,ref=self.isolated_host()
        from tools.research_execution import invoke
        discovered=invoke(host,'research.capabilities',{},request_id='catalog')
        self.assertEqual(discovered['execution_status'],'completed',discovered.get('error'))
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state'];state['role_context']['decision_only']=True
            host.store.update_state(db,host.run_id,state)
        from tools.research_scheduler import capabilities
        capabilities_now=capabilities(host.store,host.run_id,[])
        self.assertIn('design/near_routing_radius_scale',capabilities_now['legal']['structure_search']['paths'])
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state'];state['role_context']['decision_only']=False
            host.store.update_state(db,host.run_id,state)
        built=invoke(host,'research.prepare_candidate',dict(candidate_id='integrated',changes={'design/near_routing_radius_scale':1.01}),request_id='build')
        self.assertEqual(built['execution_status'],'completed',built.get('error'))
        prepared=host.store.artifact(built['output'])
        # Exercise the actual owned-configuration and protocol binding wrapper.
        # Scientific working-point construction/linearization is the only substitute.
        from schemas.platform_analysis import TaskAnalysisProtocol,AnalysisResult
        from tools.research_execution import linearize_configuration
        protocol_value=TaskAnalysisProtocol(baseline_lengths_m={'near':.16,'far':.12},frequency_rad_s=[.1,1.,10.])
        with host.store.transaction() as db:bound_protocol=plain(host.store.put(db,protocol_value))
        captured={}
        def scientific_boundary(ctx,inp,binding,protocol,reference):
            captured.update(binding=binding)
            return AnalysisResult(kind='isolated_scientific_preparation_substitute',protocol=reference,
                bindings=[binding],records=[],evidence=[prepared['configuration']],
                limitations=['No actual working-point equilibrium, derivative evaluation or scientific analysis was run'])
        ctx=SimpleNamespace(input=SessionInput.model_validate(host.store.session(host.run_id)['snapshot']['input']),
            artifact=host.store.artifact,reg=self.reg,run_id=host.run_id)
        from tools.research_execution import ConfigurationAnalysis
        with patch('extensions.tendon_family.math_analysis.linearize_candidate_configuration',side_effect=scientific_boundary):
            analysis=linearize_configuration(ctx,ConfigurationAnalysis(configuration=prepared['configuration'],
                expected_content_identity=prepared['content_identity'],protocol=bound_protocol))
        self.assertEqual(captured['binding']['task_identity'],digest(plain(ctx.input.task)))
        self.assertEqual(analysis.kind,'isolated_scientific_preparation_substitute')
        protocol={'artifact_id':'a'*64,'media_type':'application/json'};target={'artifact_id':'b'*64,'media_type':'application/json'}
        calls=[]
        def substitute(tool,args,key):
            # Actual public input schemas, with isolated orchestration returns.
            version='2.0.0' if tool=='analysis.control_metrics' else '1.0.0'
            self.reg.get(tool,version).input_schema.model_validate(args)
            calls.append(tool)
            with host.store.transaction() as db:
                output=host.store.put(db,prepared if tool=='research.prepare_candidate' else dict(label='isolated scientific execution substitute'))
            return dict(execution_status='completed',execution_id='substitute-'+key,output=plain(output),charged=zero())
        result=fixed_pipeline(host,changes={'design/near_routing_radius_scale':1.01},protocol=protocol,target=target,
            execute_backend=True,executor=substitute)
        self.assertEqual(len(calls),7);self.assertEqual(result['scientific_validation'],'pending')
        from tools.research_investigations import InvestigationDispatcher
        dispatcher=InvestigationDispatcher(host);order=self.order('direct',ref)
        native=lambda payload:dict(choices=[dict(message=dict(tool_calls=[dict(function=dict(
            name='investigation_return',arguments=json.dumps(plain(self.report(ref)))))]))])
        report=dispatcher.dispatch(order,transport=native)
        self.assertEqual(report.status,'completed',report.reason)
        self.assertEqual(dispatcher.dispatch(order,transport=lambda p:self.fail('duplicate dispatch')).status,'completed')
        fact=plain(self.report(ref).facts[0])
        with self.assertRaisesRegex(ValueError,'PRINCIPAL_MUST_INSPECT'):
            dispatcher.disposition(dict(investigation_id='direct',report=plain(report.result),disposition='accept',
                adopted_claims=[dict(statement='Retain saved observation',supporting_facts=[fact],
                    scope=[dict(statement='Saved scope',reference=ref,pointer='/result_type',value='free_reach')],
                    support_explanation='This original observation supports the bounded saved report')],reason='Saved fact supported'))
        receipt=invoke(host,'research.investigation_read',dict(reference=ref,pointer='/terminal_error_m'),request_id='principal-read')
        self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
        self.assertEqual(dispatcher.disposition(dict(investigation_id='direct',disposition='defer',
            evidence_used=[fact],reason='Saved facts inspected; causal and changed-radius questions remain pending')).status,'completed')
        self.assertEqual(host.store.remaining()['used']['backend_solves'],0)
        # Future interface commands must expose rejected dispatches and incomplete synthesis.
        from tools.research_mainline3 import live_interface_scenario
        rejected=dict(execution_status='rejected',error='Isolated denied-request fixture')
        with patch('tools.research_mainline3.invoke',return_value=rejected):
            self.assertEqual(live_interface_scenario(host,'coordinated')['status'],'rejected')
        with host.store.transaction() as db:report_ref=plain(host.store.put(db,plain(report)))
        completed=dict(execution_status='completed',output=report_ref)
        with patch('tools.research_mainline3.invoke',side_effect=[completed,completed,rejected]):
            self.assertEqual(live_interface_scenario(host,'direct')['status'],'rejected')

    def test_coordinator_child_narrowing_bounded_returns_and_atomic_siblings(self):
        host,ref=self.isolated_host(model_ceiling=2)
        from tools.research_investigations import InvestigationDispatcher
        dispatcher=InvestigationDispatcher(host)
        child1=self.order('child-error',ref,parent_id='coordinator')
        child2=self.order('child-cost',ref,parent_id='coordinator')
        child2['question']='Read saved timing and deadline misses; do not infer real-time feasibility'
        child2['queries']=[dict(reference=ref,pointer='/deadline_misses')]
        coordinator=self.order('coordinator',ref,role='coordinator')
        result=dispatcher.dispatch(coordinator,transport=lambda p:self.report(ref,[child1,child2]))
        self.assertEqual(result.status,'completed',result.reason)
        denied=deepcopy(child1);denied['evidence']=[dict(artifact_id='c'*64,media_type='application/json')]
        with self.assertRaisesRegex(ValueError,'CHILD_NOT_REQUESTED'):
            dispatcher.dispatch(denied,transport=lambda p:self.fail('scope escape'))
        # Two siblings compete for exactly one remaining model-call reservation.
        entered=Event();release=Event()
        def transport(payload):entered.set();release.wait(10);return self.report(ref)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(dispatcher.dispatch,child1,transport=transport)
            self.assertTrue(entered.wait(10))
            self.assertEqual(dispatcher.recover('child-error').status,'running')
            with self.assertRaisesRegex(ValueError,'TOTAL_GRANT_EXCEEDED'):
                dispatcher.dispatch(child2,transport=lambda p:self.fail('shared balance spent twice'))
            release.set();self.assertEqual(first.result().status,'completed')
        self.assertEqual(host.store.remaining()['used']['model_calls'],2)
        second_host,second_ref=self.isolated_host()
        second=InvestigationDispatcher(second_host)
        _,wire,reads,measurement=second.prepare(self.order('sealed-response',second_ref))
        from tools.research_investigations import InvestigationOrder
        order=plain(InvestigationOrder.model_validate(self.order('sealed-response',second_ref)))
        row,_=second_host.store.reserve(second_host.run_id,'investigation-sealed-response',digest(order),
            'investigation-dispatcher',order['budget'])
        with second_host.store.transaction() as db:
            state=second_host.store.session(second_host.run_id,db)['state']
            state.setdefault('investigations',{})['sealed-response']=dict(order=order,status='running',reads=reads)
            second_host.store.update_state(db,second_host.run_id,state)
            saved=second_host.store.put(db,dict(report=plain(self.report(second_ref)),elapsed_s=.01))
            second_host.store.event(db,second_host.run_id,'investigation_response','validated',
                request=row['request_id'],execution=row['execution_id'],outputs=[saved])
        self.assertEqual(second.dispatch(order,transport=lambda p:self.fail('saved-result redispatch')).status,'completed')
        from tools.research_investigations import InvestigationReturn
        with self.assertRaises(ValueError):InvestigationReturn(interpretation='x',unknowns=['x']*9)

    def test_unconfirmed_recovery_no_redispatch_and_confirmed_failure(self):
        host,ref=self.isolated_host()
        from tools.research_investigations import InvestigationDispatcher
        dispatcher=InvestigationDispatcher(host);order=self.order('uncertain',ref)
        def timeout(payload):raise TimeoutError('fixture timeout; no provider request')
        result=dispatcher.dispatch(order,transport=timeout)
        self.assertEqual(result.status,'unconfirmed')
        row=host.store.lookup(host.run_id,'investigation-uncertain')
        self.assertEqual(json.loads(row['charged'])['model_calls'],1)
        self.assertEqual(dispatcher.dispatch(order,transport=lambda p:self.fail('uncertain redispatch')).status,'unconfirmed')
        invalid=self.report(ref)
        invalid=invalid.model_copy(update={'facts':[invalid.facts[0].model_copy(update={'value':0})]})
        result=dispatcher.dispatch(self.order('invalid',ref),transport=lambda p:invalid)
        self.assertEqual(result.status,'failed')
        self.assertIn('VALUE_MISMATCH',result.reason)

    def test_historical_analysis_exact_binding_and_invalidation(self):
        store=Store(ROOT/'runs/stage336_manual_20261001_090616')
        value=store.artifact(dict(artifact_id='fecccc31a1f81a66e76ed3484e80cf2ecbf74fd27875bb25ea445460ca370cf5'))
        binding=value['bindings'][0]
        # Existing immutable analysis envelope, read only; no recomputation.
        replay=replay_analysis(value,expected_binding=binding,protocol=value['protocol'],upstream=value['evidence'])
        self.assertFalse(replay['scientific_computation'])
        wrong=deepcopy(binding);wrong['scientific_configuration_identity']='changed-radius'
        with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):
            replay_analysis(value,expected_binding=wrong,protocol=value['protocol'])
