"""Focused contract/budget checks; no physical fixture runs or hidden NLP solves."""
from copy import deepcopy
from tempfile import TemporaryDirectory
import time
from unittest import TestCase
from unittest.mock import patch
from schemas.research_core import Search, Plan
from schemas.platform import SessionInput
from tools import research_core as core
from tools.design_optimization import solve, validate_problem, continuous_space
from tools.state_io import read
from tools.platform_store import plain


class CoreTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(dir=core.ROOT/'runs',prefix='core-fixtures-')
        spec=read(core.DEFAULT_SPEC);spec['study_id']='core-fixture-'+str(int(time.time()))
        cls.spec_path=core.Path(cls.temp.name)/'spec.json';core.atomic_json(cls.spec_path,spec)
        cls.host=core.prepare(cls.spec_path,core.Path(cls.temp.name)/'business')

    @classmethod
    def tearDownClass(cls):
        import gc
        gc.collect()  # sqlite context managers leave closure to object lifetime on Windows.
        cls.temp.cleanup()

    def test_full_identity_and_shared_direct_search_construction(self):
        h=self.host;s=core.state(h)
        a=core.construct(h,dict(d=.5,holding_tip_speed_weight=.075,terminal_tip_speed_weight=.1),dict(origin='direct'))
        b=core.construct(h,dict(d=.5,holding_tip_speed_weight=.075,terminal_tip_speed_weight=.1),dict(origin='search'))
        self.assertEqual(a,b)
        c=core.verify_candidate(h,a)
        self.assertEqual(c['resolved_parameters']['lengths_m'],[.16275,.10725])
        self.assertTrue(c['configuration']['policy']['controller']['parameters']['data']['recipe']['recover_returned_tensions'])
        self.assertIn('material',c['resolved_parameters']);self.assertIn('pretension_n',c['resolved_parameters'])
        d=core.construct(h,dict(d=.5,holding_tip_speed_weight=.075,terminal_tip_speed_weight=.05),dict(origin='direct'))
        self.assertNotEqual(a,d)
        old=deepcopy(s['profile'])
        changed=deepcopy(old);changed['version']+=1;changed['identity']=core.digest(changed)
        core.update(h,profile=changed)
        try:
            with self.assertRaisesRegex(ValueError,'OLD_EVALUATION_PROFILE'):core.verify_candidate(h,a)
        finally:core.update(h,profile=old)

    def test_batch_reserves_every_launch_and_both_confirmations(self):
        h=self.host;s=core.state(h);a=core.allowance(s)
        ledger=h.store.remaining()
        with patch.object(h.store,'remaining',return_value=ledger):
            self.assertEqual(core.capacity(h,8)['admitted'],3)
            ledger['remaining']['backend_solves']=3
            self.assertEqual(core.capacity(h,8)['admitted'],1)
            ledger['remaining']['tool_calls']=11
            self.assertEqual(core.capacity(h,8)['admitted'],1)
            self.assertEqual(core.capacity(h,8,root_operation=True)['admitted'],0)
            ledger['remaining']['tool_calls']=4
            self.assertEqual(core.capacity(h,1,True,root_operation=True)['admitted'],1)
            ledger['remaining']['tool_calls']=3
            self.assertEqual(core.capacity(h,1,True,root_operation=True)['admitted'],0)
            ledger['remaining']['tool_calls']=128
            core.update(h,numerical_s=s['spec']['budgets']['numerical_s']-2*a+1)
            self.assertEqual(core.capacity(h,8)['admitted'],0)
            self.assertEqual(core.capacity(h,1,True)['admitted'],1)
        core.update(h,numerical_s=s['numerical_s'])

    def test_control_only_math_explores_weights_and_preserves_recovery(self):
        query=Search(variables=['holding_tip_speed_weight','terminal_tip_speed_weight'],
            bounds={k:(.025,.1) for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')},max_evaluations=5)
        problem=core.search_problem(self.host,query,5)
        with self.assertRaisesRegex(ValueError,'INHERITED_NMPC'):validate_problem(problem)
        profile=core.state(self.host)['profile'];validated,topology=validate_problem(problem,profile)
        self.assertEqual(len(topology),1)
        names=list(continuous_space(validated,topology[0])[1])
        self.assertEqual(names,['holding_tip_speed_weight','terminal_tip_speed_weight'])
        seen=[]
        def evaluator(p,values,candidate_id):
            seen.append(values)
            return dict(status='evaluated',acceptance=dict(accepted=False,status='valid_failure',metrics=dict(
                terminal_error_m=.02,holding_max_error_m=.02,holding_max_speed_m_s=.03)),evidence=dict(substituted=True))
        result=solve(problem,evaluator=evaluator,evaluation_profile=profile)
        self.assertEqual(len(result.evaluated),5)
        self.assertGreater(len({v['holding_tip_speed_weight'] for v in seen}),1)
        self.assertGreater(len({v['terminal_tip_speed_weight'] for v in seen}),1)
        self.assertEqual({tuple(v['lengths_m']) for v in seen},{(.16,.11)})

    def test_schema_and_draft_retrieval(self):
        with self.assertRaises(ValueError):Search(variables=['d'],bounds={'d':(-2,1)})
        with self.assertRaises(ValueError):Search(variables=['d','d'],bounds={'d':(-1,1)})
        with self.assertRaises(ValueError):Plan(action='confirm',hypothesis='x',expected_observation='x',
            weakening_observation='x',fixed_conditions='x',stopping_condition='x',interpretation='x')
        self.assertEqual(core.experience(self.host,dict(task='unrelated'))['results'],[])
        retrieved=core.experience(self.host,dict(operation='read',key='case'))
        self.assertTrue(retrieved['results'][0]['original_evidence_references'])
        self.assertFalse(retrieved['supplied_startup_context'])
        self.assertIn(retrieved['reference'],core.state(self.host)['retrievals'])

    def test_confirmation_rejects_complete_configuration_mismatch_before_launch(self):
        h=self.host;c=core.verify_candidate(h,core.state(h)['reference_candidate'])
        wrong=dict(candidate=core.state(h)['reference_candidate'],profile_identity=c['profile_identity'],
            scientific_configuration=deepcopy(c['scientific_configuration']),acceptance={'accepted':True})
        wrong['scientific_configuration']['seed']=18
        ref=core.save(h,wrong)
        with patch.object(core,'guard'):
            with self.assertRaisesRegex(ValueError,'CONFIRMATION_REQUIRES_SELECTED_COMPLETE'):
                core.execute(h,wrong['candidate'],'fixture-confirm',role='confirmation',selected=ref)
            core.update(h,results=[ref],selected=None)
            plan=dict(action='confirm',selected_execution=ref,**{k:'fixture' for k in
                ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')})
            with self.assertRaisesRegex(ValueError,'CONFIRMATION_REQUIRES_SELECTED_COMPLETE'):
                core.dispatch(h,plan,'fixture-invalid-selection')
            self.assertIsNone(core.state(h)['selected'])
            wrong['scientific_configuration']=c['scientific_configuration'];wrong['acceptance']={'accepted':False}
            failed_ref=core.save(h,wrong);core.update(h,results=[ref,failed_ref])
            plan['selected_execution']=failed_ref
            with self.assertRaisesRegex(ValueError,'SELECTED_PASSING_EXECUTION_REQUIRED'):
                core.dispatch(h,plan,'fixture-nonpassing-selection')
            self.assertIsNone(core.state(h)['selected'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_complete_record_path_does_not_require_trace_or_dual_guess(self):
        from extensions.optimization.ipopt import IpoptSolver
        from extensions.tendon_family.control_evidence import COMPLETE_UPDATE_INPUTS
        self.assertFalse(COMPLETE_UPDATE_INPUTS.get())
        problem=type('Problem',(),{'variables':{'x':{'type':'number','bounds':[None,None]}},'initial_guess':{'x':3.}})()
        lo,hi,x0=IpoptSolver._bounds(problem,['x'])
        self.assertEqual(x0,[3.]);self.assertEqual(lo,[-float('inf')]);self.assertEqual(hi,[float('inf')])

    def test_fresh_execution_identity_and_shared_launch_accounting(self):
        h=self.host;previous=deepcopy(core.state(h));start_usage=h.store.remaining()['used']['backend_solves']
        def completed(child,cfg,candidate_id):
            row,_=h.store.reserve(child.run_id,'complete-simulation',core.digest(cfg),h.actor,{**core.zero(),'backend_solves':1})
            receipt=h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=h.actor,
                tool_id='simulation.run',tool_version='1.0.0',execution_status='failed',charged=core.zero()),dict(substituted=True))
            return dict(status='execution_incomplete',execution_id=row['execution_id'],receipts={'simulation':receipt})
        with patch.object(core,'guard'),patch('tools.execution_completion.complete_execution',side_effect=completed):
            a=core.execute(h,previous['reference_candidate'],'fixture-fresh-1')
            b=core.execute(h,previous['reference_candidate'],'fixture-fresh-2')
        self.assertEqual(a['candidate_id'],b['candidate_id'])
        self.assertNotEqual(a['execution_id'],b['execution_id']);self.assertNotEqual(a['owner_run_id'],b['owner_run_id'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],start_usage+2)
        core.update(h,**previous)

    def test_material_migration_keeps_costs_and_requires_new_reference(self):
        h=self.host;previous=deepcopy(core.state(h))
        core.update(h,freeze='previous-commit',numerical_s=123.,results=[core.save(h,{'sealed_previous_result':True})])
        hashes=core.science_hashes();hashes['extensions/optimization/ipopt.py']='changed-solver-source'
        with patch.object(core.subprocess,'check_output',side_effect=['','new-commit']),patch.object(core,'science_hashes',return_value=hashes):
            core.bind(h,'demonstrated solver correction')
        updated=core.state(h)
        self.assertEqual(updated['numerical_s'],123.);self.assertEqual(len(updated['results']),1)
        self.assertEqual(updated['profile']['version'],previous['profile']['version']+1)
        self.assertNotEqual(updated['reference_candidate'],previous['reference_candidate'])
        self.assertTrue(updated['core_repairs'][-1]['improvement_requires_new_comparable_reference'])
        core.update(h,**previous)

    def test_length_search_and_control_only_nonzero_fixed_length(self):
        h=self.host;profile=core.state(h)['profile']
        query=Search(variables=['d'],bounds={'d':(-1.,1.)},max_evaluations=3)
        p=core.search_problem(h,query,3);seen=[]
        def evaluator(problem,values,candidate_id):
            seen.append(values)
            return dict(status='evaluated',acceptance=dict(accepted=False,status='valid_failure',metrics=dict(
                terminal_error_m=.02,holding_max_error_m=.02,holding_max_speed_m_s=.03)),evidence=dict(substituted=True))
        result=solve(p,evaluator=evaluator,evaluation_profile=profile)
        self.assertEqual(len(result.evaluated),3)
        self.assertEqual({r['holding_tip_speed_weight'] for r in seen},{.1})
        self.assertEqual({r['terminal_tip_speed_weight'] for r in seen},{.1})
        self.assertGreater(len({tuple(r['lengths_m']) for r in seen}),1)
        for r in seen:
            d=(r['lengths_m'][0]-.16)/.0055
            self.assertAlmostEqual(r['lengths_m'][1],.11-.0055*d)
        q=Search(variables=['holding_tip_speed_weight'],bounds={'holding_tip_speed_weight':(.025,.1)},
            fixed={'d':.5,'holding_tip_speed_weight':.1,'terminal_tip_speed_weight':.1})
        p=core.search_problem(h,q,3);p,_=validate_problem(p,profile)
        self.assertEqual(p.lengths.baseline_by_count['2'],[.16275,.10725])
        self.assertFalse(p.lengths.free)

    def test_local_result_reference_serialization_without_numerical_rerun(self):
        from types import SimpleNamespace
        h=self.host;previous=deepcopy(core.state(h))
        ref=core.save(h,dict(execution_id='substituted-local-source',profile_identity=previous['profile']['identity']))
        core.update(h,results=[ref])
        def worker(args,**kwargs):
            core.atomic_json(args[-1],dict(first_input_n=[.2]*6,status='substituted_no_numerical_solve'))
            return SimpleNamespace(returncode=0,stdout=b'')
        with patch.object(core,'guard'),patch('extensions.tendon_family.control_evidence.ControlEvidence.resolve',return_value={'configuration':previous['base_configuration']}), \
            patch('extensions.tendon_family.control_evidence.ControlEvidence.read_file',return_value=[{'complete_update_record':{'saved_actual_input':True}}]), \
            patch.object(core.subprocess,'run',side_effect=worker):
            result=core.local_diagnostic(h,dict(execution=ref,update_id=0,repetitions=1),'fixture-local-serialization')
        self.assertEqual(result['rows'][0]['source_execution'],ref)
        row=h.store.lookup(h.run_id,'fixture-local-serialization-local-0')
        self.assertIsNotNone(row['receipt']);self.assertEqual(core.state(h)['numerical_reserved_s'],0.)
        core.update(h,**previous)

    def test_nonzero_length_initialization_and_restricted_bounds(self):
        from tools.design_optimization import structures
        h=self.host;profile=core.state(h)['profile']
        for bounds,initial_d in [((-1.,1.),.5),((.5,1.),.75),((-1.,-.5),-.75)]:
            q=Search(variables=['d'],bounds={'d':bounds},fixed={'d':initial_d,
                'holding_tip_speed_weight':.1,'terminal_tip_speed_weight':.1},max_evaluations=2)
            p=core.search_problem(h,q,2);s=structures(p)[0];allocation,latent=continuous_space(p,s)
            latent.update(allocation.encode([.16+.0055*initial_d,.11-.0055*initial_d]));seen=[]
            def evaluator(problem,values,candidate_id):
                seen.append(values)
                return dict(status='evaluated',acceptance=dict(accepted=False,status='valid_failure',metrics=dict(
                    terminal_error_m=.02,holding_max_error_m=.02,holding_max_speed_m_s=.03)),evidence=dict(substituted=True))
            solve(p,evaluator=evaluator,evaluation_profile=profile,initial_latents={core.digest(s):latent})
            self.assertAlmostEqual(seen[0]['lengths_m'][0],.16+.0055*initial_d)
            for values in seen:
                d=(values['lengths_m'][0]-.16)/.0055
                self.assertGreaterEqual(d,bounds[0]-1e-12);self.assertLessEqual(d,bounds[1]+1e-12)

    def test_failed_preparation_keeps_actual_inputs_without_stale_vector(self):
        import numpy as np
        from types import SimpleNamespace
        from extensions.tendon_family.gvs_nmpc import GVSNMPCController
        from extensions.tendon_family.control_evidence import COMPLETE_UPDATE_INPUTS
        controller=GVSNMPCController(core.state(self.host)['profile']['recipe'],.01)
        controller.workspace=SimpleNamespace(solver=SimpleNamespace(last_input_record={'stale_previous_input':True}),
            solve=lambda *args,**kwargs:(_ for _ in ()).throw(ValueError('preparation_failed')),last=None,graph_s=0.)
        controller.seed=None;controller.previous=np.array([.2]*6);controller.observations=[]
        controller.record_update_ids=[];controller.coordinate_order=['q'];controller.plan={'identity':'fixture-plan'}
        controller.physics={};controller.unusable_updates=0
        token=COMPLETE_UPDATE_INPUTS.set(True)
        try:
            with patch('extensions.tendon_family.gvs_nmpc.execute_ideal_tension',return_value=(np.array([.2]*6),{})):
                controller.command(0.,{'tip':np.array([0.,0.,0.]),'gvs_projection':{'projection_residual_max_rad_m':0.}},[0.],[0.])
        finally:COMPLETE_UPDATE_INPUTS.reset(token)
        record=controller.observations[0]['failed_update_input_record']
        self.assertEqual(record['previous_applied_input_n'],[.2]*6)
        self.assertEqual(record['measured_state'],[0.,0.]);self.assertIsNone(record['initialization'])
