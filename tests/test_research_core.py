"""Focused contract/budget checks; no physical fixture runs or hidden NLP solves."""
from copy import deepcopy
from tempfile import TemporaryDirectory
import time
from unittest import TestCase
from unittest.mock import patch
from schemas.research_core import Search, Plan, RLRequest
from schemas.platform import SessionInput
from tools import research_core as core
from tools.design_optimization import solve, validate_problem, continuous_space
from tools.state_io import read
from tools.platform_store import plain


class CoreTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(dir=core.ROOT/'runs',prefix='core-fixtures-')
        spec=read(core.DEFAULT_SPEC);spec['study_id']='core-fixture-'+str(int(time.time()));spec['started_unix']=time.time()
        cls.spec_path=core.Path(cls.temp.name)/'spec.json';core.atomic_json(cls.spec_path,spec)
        cls.host=core.prepare(cls.spec_path,core.Path(cls.temp.name)/'business')
        core.update(cls.host,freeze='fixture-implementation')

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
        h=self.host;initial_launches=h.store.remaining()['used']['backend_solves']
        c=core.verify_candidate(h,core.state(h)['reference_candidate'])
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
            with self.assertRaisesRegex(ValueError,'selected scientific configuration mismatch'):
                core.dispatch(h,plan,'fixture-invalid-selection')
            self.assertIsNone(core.state(h)['selected'])
            wrong['scientific_configuration']=c['scientific_configuration'];wrong['acceptance']={'accepted':False}
            failed_ref=core.save(h,wrong);core.update(h,results=[ref,failed_ref])
            plan['selected_execution']=failed_ref
            with self.assertRaisesRegex(ValueError,'result did not pass complete original task evaluation'):
                core.dispatch(h,plan,'fixture-nonpassing-selection')
            self.assertIsNone(core.state(h)['selected'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],initial_launches)

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
        def boundary(command,log,seconds):
            from tools.research_core_execution_worker import execute
            request=read(command[-1]);core.atomic_json(core.Path(command[-1]).with_name('result.json'),execute(request))
            return core.subprocess.CompletedProcess(command,0)
        with patch.object(core,'guard'),patch('tools.service_execution._run_contained',side_effect=boundary),patch('tools.execution_completion.complete_execution',side_effect=completed):
            a=core.execute(h,previous['reference_candidate'],'fixture-fresh-1')
            b=core.execute(h,previous['reference_candidate'],'fixture-fresh-2')
        self.assertEqual(a['candidate_id'],b['candidate_id'])
        self.assertNotEqual(a['execution_id'],b['execution_id']);self.assertNotEqual(a['owner_run_id'],b['owner_run_id'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],start_usage+2)
        core.update(h,**previous)

    def test_search_recovery_packages_evidence_without_next_launch(self):
        h=self.host;previous=deepcopy(core.state(h))
        plan=dict(action='search',search=dict(variables=['d'],bounds={'d':[-1,1]},max_evaluations=1),**{k:'fixture' for k in
            ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')})
        original=core.save(h,dict(request_id='search-recovery',original_plan=plan))
        h.store.reserve(h.run_id,'search-recovery','fixture',h.actor,core.zero())
        core.update(h,plans=[original],results=[],pending=None)
        try:
            with patch.object(core,'run_search',side_effect=AssertionError('No new solve or rollout')):
                value=core.recover(h)
            self.assertEqual(value['sealed_workflows'],['search-recovery'])
        finally:core.update(h,**previous)

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


    def test_summary_public_snapshot_reuse_and_protected_read(self):
        from tools import research_core_rl as bridge
        h=self.host;original=deepcopy(core.state(h))
        summary=dict(run_id='fixture',status='failed',checkpoint=None,consumed={'attempted_actions':0},observed_at_unix=1)
        entry=dict(status={'worker_alive':False,'consumed':{'attempted_actions':0}},allocation={'actions':512,'active_seconds':10},evaluations=0,replays=0)
        spec=deepcopy(original['spec']);spec['capabilities']=['rl'];spec['rl_limits']={'evaluation_episodes':5}
        core.update(h,spec=spec,rl_task=core.save(h,original['base_configuration']['task']),rl_runs={'fixture':entry},rl_training_summaries=[],rl_evidence_reads=[])
        try:
            with patch.object(core,'guard'),patch.object(bridge,'reconcile',return_value=dict(entry['status'],training_summary=summary)):
                a=bridge.dispatch(h,dict(operation='status',run_id='fixture',rationale='read failure'),'summary-a')
                summary['observed_at_unix']=2
                b=bridge.dispatch(h,dict(operation='status',run_id='fixture',rationale='read failure'),'summary-b')
            ref=a['training_summary_reference'];self.assertEqual(ref,b['training_summary_reference'])
            self.assertEqual(b['training_summary'],h.store.artifact(ref))
            progress=core.save(h,{'phase':'solver_entered','options':{'max_wall_s':None}})
            mechanics=core.save(h,{'checkpoint_reference':progress})
            core.update(h,mechanics_results=[mechanics])
            core.update(h,rl_evidence_reads=[])
            with patch.object(h.store,'remaining',return_value={'remaining':{'model_calls':4}}):
                self.assertEqual(core.read_evidence(h,dict(reference=ref,pointer='/consumed')),{'attempted_actions':0})
                self.assertEqual(core.read_evidence(h,dict(reference=progress,pointer='/phase')),'solver_entered')
                self.assertIn(ref,core.state(h)['rl_evidence_reads'])
                self.assertEqual(core.read_evidence(h,dict(reference=ref))['consumed'],{'attempted_actions':0})
                with self.assertRaisesRegex(ValueError,'PROTECTED'):core.read_evidence(h,dict(reference=original['reference_candidate']))
            self.assertIn(ref,core.readable_results(core.state(h)))
            self.assertIn(ref,core.state(h)['rl_evidence_reads'])
            self.assertEqual(bridge.packet(h)['training_summaries'][0]['reference'],ref)
            spec=deepcopy(original['spec']);spec['capabilities']=['rl'];core.update(h,spec=spec,mechanics_results=[])
            plan=dict(action='stop',next_step='diagnose',supporting_evidence=[ref],**{k:'No checkpoint; failure evidence supports diagnosis' for k in ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')})
            with patch.object(core,'guard'):
                self.assertTrue(core.dispatch(h,plan,'summary-stop')['result']['accepted_stop'])
        finally:core.update(h,**original)


class RLIntegrationTests(TestCase):
    def test_bridge_reconciliation_is_idempotent(self):
        from tools import research_core_rl as bridge
        class Store:
            def __init__(self):self.state={'rl_runs':{'r':{'allocation':{'actions':64,'active_seconds':10}}}}
            def transaction(self):
                from contextlib import nullcontext
                return nullcontext(None)
            def session(self,*args):return {'state':self.state}
            def update_state(self,db,run_id,state):self.state=state
        store=Store();host=__import__("types").SimpleNamespace(store=store,run_id='study')
        value=dict(consumed={'attempted_actions':32,'attempted_physics_steps':151,'active_seconds':3},worker_alive=True)
        with patch.object(bridge.run,'status',return_value=value):
            bridge.reconcile(host,'r');bridge.reconcile(host,'r')
        self.assertEqual(store.state['rl_runs']['r']['status']['consumed']['attempted_actions'],32)
        self.assertIsNotNone(store.state['rl_runs']['r']['active_reservation']);self.assertEqual(store.state['numerical_s'],3)


    def test_owned_generated_candidate_frozen_task_overrides_and_duplicate_receipt(self):
        from schemas.research_core import RLRequest
        from tools import research_core_rl as bridge
        from uuid import uuid4
        with TemporaryDirectory(dir=core.ROOT/'runs',prefix='rl-fixtures-') as folder:
            spec=read(core.ROOT/'examples/rl_strands/specification.json')
            spec['study_id']='rl-fixture-'+uuid4().hex[:8]
            spec['started_unix']=time.time()
            path=core.Path(folder)/'spec.json';core.atomic_json(path,spec)
            h=core.prepare(path,core.Path(folder)/'business')
            ref=core.construct(h,dict(d=.7),dict(origin='fixture'))
            q=RLRequest(operation='start',candidate=ref,mode='direct',rationale='fixture',
                training_overrides=dict(n_steps=32,batch_size=16,n_epochs=2),reward_overrides=dict(smoothness=.01),
                allocation=dict(actions=64,active_seconds=10))
            cfg,task_ref=bridge.prepare_input(h,q)
            core.atomic_json(core.Path(folder)/'input.json',cfg)
            import subprocess,os
            env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
            code="from tools.rl.run import read_json; from tools.rl.env import TensionEnv; import sys; e=TensionEnv(read_json(sys.argv[1])); print(e.settings()['action_dimension']); e.reset(); e.close()"
            completed=subprocess.run([str(bridge.run.PYTHON),'-c',code,str(core.Path(folder)/'input.json')],cwd=core.ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertEqual(completed.stdout.strip(),'6')
            self.assertEqual(cfg['candidate']['reference'],ref)
            self.assertIn('near_cell_0_y',cfg['control_object']['joint_names'])
            self.assertEqual(cfg['task']['acceptance']['holding_steps'],list(range(30,36)))
            self.assertEqual(cfg['ppo']['n_steps'],32);self.assertEqual(cfg['reward']['smoothness'],.01)
            self.assertEqual(h.store.artifact(task_ref),cfg['task']['original'])
            with patch.object(core,'guard'),patch.object(bridge,'invoke',return_value=dict(status='starting')) as invoke:
                first=bridge.dispatch(h,q.model_dump(exclude_unset=True),'fixture-start')
                second=bridge.dispatch(h,q.model_dump(exclude_unset=True),'fixture-start')
                self.assertEqual(first,second);invoke.assert_called_once()
                self.assertEqual(h.store.remaining()['used']['backend_solves'],1)
                q=q.model_copy(update={'training_overrides':q.training_overrides.model_copy(update={'n_epochs':3})})
                with self.assertRaisesRegex(ValueError,'ceiling'):bridge.dispatch(h,q.model_dump(exclude_unset=True),'different-start')
            self.assertEqual(len(core.state(h)['rl_runs']),1)
            core.update(h,rl_evaluations=[core.save(h,{'passed':False})])
            self.assertFalse(core.claims(h)['task_passed'])
            self.assertIn('evaluations',core.packet(h)['rl'])
            import gc
            gc.collect()

    def test_numerical_subprocess_preserves_windows_systemroot_case_insensitively(self):
        from tools import research_core_rl as bridge
        import os
        with patch.object(bridge.subprocess,'run') as launch:
            launch.return_value=__import__('types').SimpleNamespace(returncode=0,stdout='{}')
            bridge.invoke('status','fixture')
            environment=launch.call_args.kwargs['env']
            if os.name=='nt':self.assertEqual(environment['SystemRoot'],os.environ['SYSTEMROOT'])
            self.assertEqual(environment['OMP_NUM_THREADS'],'1')
            self.assertNotIn('DEEPSEEK_API_KEY',environment)
        # Reproduce the formerly failing Torch import through the corrected environment.
        import subprocess
        env={k:os.environ[k] for k in ('SystemRoot','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT') if k in os.environ}
        env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        actual=subprocess.run([str(bridge.run.PYTHON),'-c','import torch, asyncio; torch.set_num_threads(1); print(torch.get_num_threads())'],
            cwd=core.ROOT,env=env,capture_output=True,text=True)
        self.assertEqual(actual.returncode,0,actual.stderr)
        self.assertEqual(actual.stdout.strip(),'1')

    def test_failed_dispatched_evaluation_never_claims_zero_consumption(self):
        from tools import research_core_rl as bridge
        s=dict(spec={'mode':'rl_interface'},rl_runs={'r':dict(candidate={'artifact_id':'c'},task={'artifact_id':'t'},configuration={'artifact_id':'f'})},rl_evaluations=[])
        values={};ref={'artifact_id':'0'*64,'media_type':'application/json'}
        def save(host,value,kind):values[ref['artifact_id']]=value;return ref
        host=__import__('types').SimpleNamespace(run_id='study',store=__import__('types').SimpleNamespace(artifact=lambda reference:values[reference['artifact_id']]))
        with patch.object(core,'state',return_value=s),patch.object(core,'save',side_effect=save),patch.object(core,'update',side_effect=lambda host,**value:s.update(value)):
            first=bridge.unavailable_evaluation(host,'r','operation','unexpected child exit',uncertain=True)
            second=bridge.unavailable_evaluation(host,'r','operation','duplicate')
            self.assertEqual(first,second)
            self.assertIsNone(first['counts']);self.assertIsNone(first['independent_evaluation_executed'])
            self.assertTrue(first['consumption_uncertain'])
            self.assertEqual(len(s['rl_evaluations']),1)
            self.assertEqual(core.claims(host)['interface_evaluations'],0)


class FormalControlTests(TestCase):
    def test_allocation_schema_positive_and_phase_caps(self):
        from schemas.research_core import RLAllocation
        self.assertEqual(RLAllocation(actions=200000,active_seconds=800).actions,200000)
        for value in (0,float('inf'),float('nan')):
            with self.assertRaises(ValueError):RLAllocation(actions=1024,active_seconds=value)

    def test_nmpc_gate_uses_existing_exact_configuration_and_cap(self):
        from types import SimpleNamespace
        cfg={'task':'fixed','controller':'selected'}
        state=dict(spec={'nmpc_execution_cap_s':1800,'nmpc_timing_evidence':[dict(scientific_configuration_identity=core.digest(cfg),complete_execution_s=1900,source='saved-timing')]})
        with patch.object(core,'state',return_value=state),patch.object(core,'verify_candidate',return_value={'scientific_configuration':cfg}):
            gate=core.nmpc_timing(SimpleNamespace(),'candidate')
            self.assertTrue(gate['available']);self.assertEqual(gate['reservation_s'],1800)
            state['spec']['nmpc_timing_evidence'][0]['complete_execution_s']=600
            self.assertTrue(core.nmpc_timing(SimpleNamespace(),'candidate')['available'])
            state['spec']['nmpc_timing_evidence'][0]['scientific_configuration_identity']='different'
            self.assertTrue(core.nmpc_timing(SimpleNamespace(),'candidate')['available'])

    def test_rl_confirmation_exact_generation_without_training_or_nmpc(self):
        from tools import research_core_rl as bridge
        from types import SimpleNamespace
        selected={'run_id':'owned','checkpoint':'step-exact','policy_sha256':'frozen'}
        host=SimpleNamespace(store=SimpleNamespace(artifact=lambda ref:selected))
        with patch.object(bridge,'dispatch',return_value={'passed':True}) as call,patch.object(core,'execute',side_effect=AssertionError('NMPC forbidden')):
            bridge.confirm(host,{'artifact_id':'selected'},'confirm-1')
        args=call.call_args.args
        self.assertEqual(args[1]['operation'],'evaluate');self.assertEqual(args[1]['checkpoint'],'step-exact')
        self.assertEqual(call.call_args.kwargs['selected'],{'artifact_id':'selected'})

    def test_rl_reserve_reads_confirmation_count_and_deadline(self):
        from tools import research_core_rl as bridge
        from types import SimpleNamespace
        s=dict(spec={'confirmation':{'fresh_independent_repetitions':2},'rl_evaluation_allowance_s':10,'rl_limits':{'evaluation_episodes':5},'budgets':{'numerical_s':1000,'protected_provider_requests':0}},rl_runs={'r':{'evaluations':2}},cutoff_unix=time.time()+100,numerical_s=0,numerical_reserved_s=0)
        h=SimpleNamespace(store=SimpleNamespace(remaining=lambda:{'remaining':{'wall_s':100,'model_calls':100}}))
        with patch.object(core,'state',return_value=s):
            self.assertEqual(bridge.evaluation_capacity(h,5)['admitted'],1)
            self.assertEqual(bridge.evaluation_capacity(h,2,True)['admitted'],2)
            s['spec']['confirmation']['fresh_independent_repetitions']=1
            self.assertEqual(bridge.evaluation_capacity(h,5)['admitted'],2)

    def test_unavailable_evaluation_is_unmeasured(self):
        from tools.research_core_feedback import result_view
        from types import SimpleNamespace
        r=dict(candidate={'artifact_id':'c'},task={'artifact_id':'t'},run_id='r',configuration={'artifact_id':'cfg'},independent_evaluation_executed=False,passed=False,episodes=[],failure_stage='launch/dependency import')
        h=SimpleNamespace(store=SimpleNamespace(artifact=lambda ref:r))
        with patch.object(core,'verify_candidate',return_value={'configuration':{'task':{}}}),patch('tools.research_core_feedback.mechanics_context',return_value=[]):
            v=result_view(h,'result')
        self.assertFalse(v['passed']);self.assertEqual(v['task_performance'],'unmeasured');self.assertEqual(v['failure_stage'],'launch/dependency import')


    def test_formal_preparation_initializes_rl_without_interface_mode(self):
        from uuid import uuid4
        from tools import research_core_rl as bridge
        with TemporaryDirectory(dir=core.ROOT/'runs',prefix='formal-fixture-') as folder:
            spec=read(core.ROOT/'examples/design_control/phase_B.json')
            spec.update(study_id='formal-'+uuid4().hex[:8],started_unix=time.time())
            path=core.Path(folder)/'spec.json';core.atomic_json(path,spec)
            h=core.prepare(path,core.Path(folder)/'business');s=core.state(h)
            self.assertEqual(s['rl_runs'],{});self.assertEqual(h.store.artifact(s['rl_task']),s['base_configuration']['task'])
            self.assertTrue(core.enabled(spec,'mathematics'));self.assertTrue(core.enabled(spec,'nmpc'));self.assertTrue(core.enabled(spec,'rl'))
            self.assertEqual(core.confirmation_count(s),2)
            self.assertEqual(bridge.packet(h)['capabilities']['compatible_references'],[])
            c=core.verify_candidate(h,s['reference_candidate'])
            source=core.save(h,dict(operation='solve',candidate=dict(d=0.,tensions_n=[[.2]*6]*35,times_s=[k*.01 for k in range(36)],tendon_order=['near_t0','near_t1','near_t2','far_t0','far_t1','far_t2']),original_request=core.save(h,dict(configuration=c['configuration'])),trajectory_reference=core.save(h,{'fixture':'tensions'})))
            core.update(h,mechanics_results=[source])
            from tools import research_core_mechanics as mechanics
            with patch.object(core,'execute',side_effect=AssertionError('handoff cannot launch')):
                relation=mechanics.handoff(h,source)
            refs=bridge.compatible_references(h)
            self.assertTrue(refs[0]['available']);self.assertEqual(refs[0]['reference']['candidate_identity'],c['identity'])
            v=h.store.artifact(source);v['candidate']['tendon_order'].reverse()
            incompatible=core.save(h,v);core.update(h,mechanics_results=[source,incompatible])
            mechanics.handoff(h,incompatible)
            self.assertFalse(bridge.compatible_references(h)[1]['available'])
            request=dict(operation='start',candidate=s['reference_candidate'],mode='direct',allocation=dict(actions=200192,active_seconds=800),rationale='exceeds authorized per-trial ceiling')
            with patch.object(core,'guard'),patch.object(bridge,'invoke',side_effect=AssertionError('must not launch')):
                with self.assertRaisesRegex(ValueError,'per-trial'):bridge.dispatch(h,request,'over-cap')
            aligned,unused=bridge.prepare_input(h,RLRequest(operation='start',candidate=s['reference_candidate'],mode='direct',allocation=dict(actions=200000,active_seconds=800),rationale='round down within ceiling'))
            self.assertEqual(aligned['budget']['actions'],199936)
            self.assertEqual(aligned['requested_allocation']['actions'],200000)
            self.assertEqual(core.state(h)['rl_runs'],{})
            import gc;gc.collect()


    def test_core_rl_confirmation_uses_older_exact_policy_and_keeps_failure(self):
        import hashlib
        from uuid import uuid4
        from tools import research_core_rl as bridge
        from schemas.research_core import RLRequest
        with TemporaryDirectory(dir=core.ROOT/'runs',prefix='confirm-fixture-') as folder:
            root=core.Path(folder);spec=read(core.ROOT/'examples/design_control/phase_B.json')
            spec.update(study_id='confirm-'+uuid4().hex[:8],started_unix=time.time())
            path=root/'spec.json';core.atomic_json(path,spec);h=core.prepare(path,root/'business');s=core.state(h)
            cfg,task=bridge.prepare_input(h,RLRequest(operation='start',candidate=s['reference_candidate'],mode='direct',allocation=dict(actions=2048,active_seconds=20),rationale='fixture'))
            run_id='owned-fixture';directory=root/'runtime'/run_id;directory.mkdir(parents=True)
            core.atomic_json(directory/'config.json',cfg);core.atomic_json(directory/'checkpoint.json',dict(current='newest',previous='newer'))
            policy=directory/'checkpoints'/'selected-old'/'policy.zip';policy.parent.mkdir(parents=True);policy.write_bytes(b'exact selected policy');core.atomic_json(policy.with_name('metadata.json'),{})
            configref=core.save(h,cfg)
            entry=dict(candidate=s['reference_candidate'],task=task,configuration=configref,allocation=cfg['budget'],evaluations=1,replays=0)
            dev=dict(candidate=entry['candidate'],task=task,configuration=configref,run_id=run_id,checkpoint='selected-old',policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),independent_evaluation_executed=True,passed=True,episodes=[dict(complete=True)],role='development')
            selected=core.save(h,dev);core.update(h,rl_runs={run_id:entry},rl_evaluations=[selected])
            plan=dict(action='confirm',selected_execution=selected,**{k:'fixture' for k in ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')})
            results=[dict(dev,passed=True),dict(dev,passed=False)]
            with patch.object(core,'guard'),patch.object(core,'execute',side_effect=AssertionError('RL must never use NMPC')),patch.object(bridge.run,'RUNS',root/'runtime'),patch.object(bridge,'reconcile',return_value={'worker_alive':False}),patch.object(bridge,'invoke',side_effect=results) as invoke:
                core.dispatch(h,plan,'confirmation-1');core.dispatch(h,plan,'confirmation-2')
                self.assertEqual(invoke.call_count,2)
                for call in invoke.call_args_list:
                    self.assertEqual(call.args[0],'evaluate');self.assertEqual(call.args[3],policy)
                with self.assertRaisesRegex(ValueError,'already recorded'):core.dispatch(h,plan,'confirmation-3')
            self.assertEqual(core.claims(h)['independent_confirmation_count'],2)
            self.assertEqual(core.claims(h)['confirmation_failures'],1);self.assertFalse(core.claims(h)['task_passed'])
            self.assertEqual(core.state(h)['selected'],selected)
            import gc;gc.collect()


    def test_followup_source_is_readonly_and_failed_report_is_idempotent(self):
        from tools import research_core_rl as bridge
        from schemas.research_core import RLRequest
        from types import SimpleNamespace
        import hashlib
        with TemporaryDirectory(dir=core.ROOT/'runs',prefix='followup-fixture-') as folder:
            root=core.Path(folder);spec=read(core.ROOT/'examples/research_core/rl_evaluation_followup.json')
            binding=spec.pop('rl_evaluation_source');spec.update(study_id='followup-fixture-'+root.name,started_unix=time.time(),mode='formal_research',capabilities=['rl'],allowed_plan_actions=['stop','confirm']);spec['rl_limits']['evaluation_episodes']=3;spec['confirmation']['fresh_independent_repetitions']=2;spec['budgets'].update(numerical_s=1800,activity_s=1800,delivery_reserve_s=300,protected_provider_requests=12)
            path=root/'spec.json';core.atomic_json(path,spec);h=core.prepare(path,root/'business');s=core.state(h)
            cfg,task=bridge.prepare_input(h,RLRequest(operation='start',candidate=s['reference_candidate'],mode='direct',allocation=dict(actions=700,active_seconds=10),rationale='fixture only'))
            self.assertEqual(cfg['requested_allocation']['actions'],700);self.assertEqual(cfg['budget']['actions'],512)
            directory=root/'runtime'/binding['run_id'];policy=directory/'checkpoints'/binding['checkpoint']/'policy.zip'
            policy.parent.mkdir(parents=True);policy.write_bytes(b'fixture policy')
            binding['policy_sha256']=hashlib.sha256(policy.read_bytes()).hexdigest()
            core.atomic_json(policy.with_name('metadata.json'),dict(config_sha256=binding['config_sha256'],policy_file_sha256=binding['policy_sha256'],inherited={'num_timesteps':512}))
            core.atomic_json(directory/'config.json',cfg);core.atomic_json(directory/'checkpoint.json',dict(current=binding['checkpoint']))
            core.atomic_json(directory/'state.json',dict(status='completed',consumed={'attempted_actions':512},workers=[]))
            oldentry=dict(candidate=s['reference_candidate'],task=task,configuration=core.save(h,cfg),status=dict(worker_alive=False,status='completed',consumed={'attempted_actions':512}),allocation=cfg['budget'],evaluations=1,replays=0)
            sealed=dict(research_status='stopped',rl_runs={binding['run_id']:oldentry},rl_evaluations=[])
            old=SimpleNamespace(session=lambda _: {'state':sealed},artifact=h.store.artifact)
            original=deepcopy(sealed);spec['rl_evaluation_source']=binding;core.update(h,spec=spec)
            with patch('tools.platform_store.Store',return_value=old),patch.object(bridge.run,'RUNS',root/'runtime'),patch.object(bridge.run,'worker_alive',return_value=False):
                bridge.bind_source(h)
                report=dict(passed=True,episodes=[dict(complete=True,passed=True,terminal_position_error_m=.005)])
                q=dict(operation='evaluate',run_id=binding['run_id'],checkpoint=binding['checkpoint'],rationale='fixture')
                with patch.object(core,'guard'),patch.object(bridge.run,'status',side_effect=AssertionError('no source reconciliation')),patch.object(bridge,'invoke',return_value=report) as invoke:
                    bridge.dispatch(h,dict(operation='status',run_id=binding['run_id'],rationale='fixture'),'status')
                    result=bridge.dispatch(h,q,'evaluation');self.assertEqual(bridge.dispatch(h,q,'evaluation'),result)
                    self.assertEqual(invoke.call_count,1);self.assertEqual(invoke.call_args.args[3],policy)
                    self.assertTrue(core.Path(invoke.call_args.args[5]).is_relative_to(h.store.root))
                    self.assertEqual(invoke.call_args.kwargs['timeout_s'],120)
                    self.assertTrue(result['independent_evaluation_executed']);self.assertTrue(result['episodes'][0]['complete'])
                    for operation in ('start','resume','stop','diagnose'):
                        request=dict(operation=operation,run_id=binding['run_id'],rationale='fixture') if operation!='start' else dict(operation=operation,candidate=s['reference_candidate'],mode='direct',allocation={'actions':512,'active_seconds':10},rationale='fixture')
                        with self.assertRaisesRegex(ValueError,'scope'):bridge.dispatch(h,request,operation)
                    with self.assertRaisesRegex(ValueError,'pinned'):bridge.dispatch(h,dict(q,checkpoint='other'),'wrong')
                self.assertEqual(core.verify_candidate(h,result['candidate'])['identity'],h.store.artifact(oldentry['candidate'])['identity'])
                core.read_evidence(h,{'reference':result['reference']})
                plan=dict(action='confirm',selected_execution=result['reference'],**{k:'Exact pinned fixture' for k in ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')})
                with patch.object(core,'guard'),patch.object(bridge,'invoke',return_value=report) as confirmation:
                    core.dispatch(h,plan,'fresh-1');core.dispatch(h,plan,'fresh-2')
                    self.assertEqual(confirmation.call_count,2)
                    for call in confirmation.call_args_list:
                        self.assertEqual(call.args[3],policy);self.assertTrue(core.Path(call.args[5]).is_relative_to(h.store.root))
                self.assertEqual(core.claims(h)['independent_confirmation_count'],2)
                self.assertEqual(sealed,original);self.assertEqual(core.state(h)['rl_runs'][binding['run_id']]['evaluations'],3)
                self.assertEqual(core.state(h)['rl_runs'][binding['run_id']]['allocation']['actions'],0)
                entry=core.state(h)['rl_runs'];entry[binding['run_id']]['evaluations']=0;core.update(h,rl_runs=entry,selected=None)
                with patch.object(core,'guard'),patch.object(bridge,'invoke',side_effect=RuntimeError('fixture packaging exception')):
                    with self.assertRaisesRegex(RuntimeError,'packaging'):bridge.dispatch(h,q,'failed-packaging')
                row=h.store.lookup(h.run_id,'failed-packaging');self.assertEqual(core.json.loads(row['receipt'])['execution_status'],'failed')
                failure=h.store.artifact(core.state(h)['rl_evaluations'][-1]);self.assertTrue(failure['consumption_uncertain'])
                self.assertIsNone(failure['independent_evaluation_executed']);self.assertEqual(failure['episodes'],[])
            import gc;gc.collect()

    def test_followup_subprocess_timeout_and_public_campaign_removal(self):
        from tools import research_core_rl as bridge
        from types import SimpleNamespace
        import inspect
        with patch.object(bridge.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{}')) as launch,patch.object(bridge.time,'time',return_value=100):
            bridge.invoke('evaluate','fixture',deadline=500,timeout_s=150)
            self.assertEqual(launch.call_args.kwargs['timeout'],120)
            bridge.invoke('evaluate','fixture',deadline=137,timeout_s=120)
            self.assertEqual(launch.call_args.kwargs['timeout'],37)
        self.assertNotIn('phase_A_dependency',inspect.getsource(core.converse));self.assertNotIn('phase_A_evidence',inspect.getsource(core.packet))
        self.assertNotIn('Phase A',core.FORMAL_INSTRUCTIONS);self.assertNotIn('Phase B',core.FORMAL_INSTRUCTIONS)
        self.assertEqual(core.confirmation_count({'spec':read(core.ROOT/'examples/design_control/phase_B.json')}),2)


class SchedulingCloseoutTests(TestCase):
    def test_wait_terminal_milestone_deadline_without_provider_or_summaries(self):
        import asyncio
        from unittest.mock import AsyncMock
        from tools import research_core_rl as bridge
        h=object();s=dict(spec={},research_status='ready',cutoff_unix=time.time()+100,rl_runs={'fixture':{}})
        with patch.object(core,'state',return_value=s),patch.object(core,'execution_deadline',return_value=time.time()+100),patch.object(bridge,'reconcile',side_effect=[dict(worker_alive=True,status='running'),dict(worker_alive=False,status='failed')]) as status,patch.object(core.asyncio,'sleep',new_callable=AsyncMock) as sleep,patch.object(bridge.run,'training_summary',side_effect=AssertionError('no snapshots')),patch('tools.strands_pilot_r3.LiveBoundary.handle_async_request',side_effect=AssertionError('no provider')):
            asyncio.run(core.wait_training(h));self.assertEqual(sleep.await_count,1)
            self.assertEqual(status.call_args.kwargs,{'lightweight':True})
        s['spec']['rl_wait_milestones']={'fixture':512}
        with patch.object(core,'state',return_value=s),patch.object(core,'execution_deadline',return_value=time.time()+100),patch.object(bridge,'reconcile',return_value=dict(worker_alive=True,status='running')),patch.object(core,'read',side_effect=[dict(current='published'),dict(inherited={'num_timesteps':512})]),patch.object(core.asyncio,'sleep',new_callable=AsyncMock) as sleep:
            asyncio.run(core.wait_training(h));sleep.assert_not_awaited()
        s['spec']={};s['cutoff_unix']=time.time()-1
        with patch.object(core,'state',return_value=s),patch.object(core,'execution_deadline',return_value=time.time()-1),patch.object(bridge,'reconcile',return_value=dict(worker_alive=True,status='running')),patch.object(bridge,'dispatch') as stop:
            asyncio.run(core.wait_training(h));self.assertEqual(stop.call_args.args[1]['operation'],'stop')

    def test_configured_protection_and_complete_training_closeout_reserve(self):
        from types import SimpleNamespace
        from tools import research_core_rl as bridge
        s=dict(spec=read(core.ROOT/'examples/research_core/joint_design_control.json'),started_unix=time.time(),cutoff_unix=time.time()+4000,rl_runs={'existing':{}},numerical_s=0,numerical_reserved_s=0)
        remaining=dict(model_calls=16,tool_calls=160,wall_s=14000)
        h=SimpleNamespace(store=SimpleNamespace(remaining=lambda: {'remaining':remaining}))
        with patch.object(core,'state',return_value=s),patch.object(bridge,'evaluation_capacity',return_value={'admitted':1}):
            self.assertTrue(core.protected(h))
            for action in ('stop','confirm'):core.admit_closeout(h,'research_plan',{'action':action})
            for operation in ('status','stop','evaluate'):core.admit_closeout(h,'research_rl',{'operation':operation})
            for name,field,actions in [('research_plan','action',['mechanics','execute','search']),('research_rl','operation',['start','resume'])]:
                for action in actions:
                    with self.assertRaisesRegex(ValueError,'PROTECTED'):core.admit_closeout(h,name,{field:action})
            with self.assertRaisesRegex(ValueError,'CLOSEOUT'):bridge.training_capacity(h,{'active_seconds':1200})
            remaining['model_calls']=17;remaining['tool_calls']=11
            with self.assertRaisesRegex(ValueError,'CLOSEOUT'):bridge.training_capacity(h,{'active_seconds':1200})
            remaining['tool_calls']=12
            bridge.training_capacity(h,{'active_seconds':1200})
            s['spec']['budgets']['protected_provider_requests']=9
            with self.assertRaisesRegex(ValueError,'CLOSEOUT'):bridge.training_capacity(h,{'active_seconds':1200})


class ConfirmationCompletionTests(TestCase):
    def test_unique_historical_and_current_counts_identity_and_failure(self):
        from types import SimpleNamespace
        from tools import research_core_feedback as feedback
        ref=lambda n:dict(artifact_id=n,media_type='application/json')
        selected,historical,new,ordinary=map(ref,('selected','historical','new','ordinary'))
        identity={'candidate':'c','task':'t','controller':'exact-checkpoint'}
        records={n:dict(role='confirmation',selected_execution=selected,execution_id=n,study='source' if n=='historical' else 'current') for n in ('historical','new')}
        records['ordinary']=dict(role='development',execution_id='ordinary')
        views={n:dict(solution_identity=identity,complete=True,passed=True) for n in ('selected','historical','new','ordinary')}
        s=dict(spec={'confirmation':{'fresh_independent_repetitions':2}},selected=selected,results=[],historical_confirmations=[historical,historical],rl_evaluations=[ordinary])
        host=SimpleNamespace(store=SimpleNamespace(artifact=lambda r:records[r['artifact_id']]))
        with patch.object(core,'state',return_value=s),patch.object(feedback,'result_view',side_effect=lambda h,r:views[r['artifact_id']]):
            p=feedback.confirmation_progress(host);self.assertEqual((p['historical_confirmations'],p['current_study_confirmations'],p['remaining']),(1,0,1))
            self.assertFalse(p['confirmed']);s['rl_evaluations']+=[new,new]
            p=feedback.confirmation_progress(host);self.assertTrue(p['confirmed']);self.assertEqual(p['current_study_confirmations'],1)
            views['new']['solution_identity']={'controller':'different'}
            self.assertEqual(feedback.confirmation_progress(host)['remaining'],1)
            views['new']['solution_identity']=identity;views['new']['passed']=False
            p=feedback.confirmation_progress(host);self.assertFalse(p['confirmed']);self.assertEqual(p['failures'],1)
            views['new']['complete']=False
            p=feedback.confirmation_progress(host);self.assertEqual(p['invalid_executions'],1);self.assertEqual(p['failures'],0)

    def test_completion_binding_readonly_and_one_confirmation_capacity(self):
        from tools import research_core_rl as bridge
        with TemporaryDirectory(dir=core.ROOT/'runs',prefix='completion-fixture-') as folder:
            spec=read(core.ROOT/'examples/research_core/confirmation_completion.json');spec.update(study_id='completion-fixture-'+core.Path(folder).name,started_unix=time.time())
            path=core.Path(folder)/'spec.json';core.atomic_json(path,spec)
            h=core.prepare(path,core.Path(folder)/'business');s=core.state(h)
            self.assertEqual(core.claims(h)['confirmation_progress']['historical_confirmations'],1)
            self.assertEqual(bridge.evaluation_capacity(h,2,True)['admitted'],1)
            self.assertEqual(bridge.evaluation_capacity(h,1)['admitted'],0)
            bridge.bind_source(h)
            self.assertEqual(core.claims(h)['independent_confirmation_count'],1)
            q=dict(operation='evaluate',run_id=spec['rl_evaluation_source']['run_id'],checkpoint=spec['rl_evaluation_source']['checkpoint'],rationale='wrong confirmation operation')
            with patch.object(core,'guard'),patch.object(bridge,'invoke',side_effect=AssertionError('ordinary evaluation must not run')):
                with self.assertRaisesRegex(ValueError,'research_plan.*confirm.*41a7df9f'):bridge.dispatch(h,q,'wrong')
            spec['ordinary_evaluation_limit']=1;core.update(h,spec=spec)
            with patch.object(core,'guard'),patch.object(bridge,'evaluation_capacity',return_value={'admitted':1}),patch.object(bridge,'invoke',side_effect=AssertionError('frozen ordinary evaluation forbidden')):
                with self.assertRaisesRegex(ValueError,'research_plan.*confirm'):bridge.dispatch(h,q,'wrong-after-freeze')
            formal=read(core.ROOT/'examples/research_core/autonomous_design_control.json')
            formal.update(study_id='linked-history-fixture-'+core.Path(folder).name,started_unix=time.time())
            formal_path=core.Path(folder)/'formal.json';core.atomic_json(formal_path,formal)
            linked=core.prepare(formal_path,core.Path(folder)/'linked')
            for ref in formal['historical_evidence']['references'].values():
                self.assertIn(ref,core.state(linked)['scoped_context']);linked.store.artifact(ref)
            self.assertEqual(s['selected'],spec['rl_evaluation_source']['selected_execution'])
            import gc;gc.collect()

    def test_unverified_mechanics_remains_unverified(self):
        from types import SimpleNamespace
        from tools import research_core_feedback as feedback
        candidate=dict(artifact_id='c',media_type='application/json');source=dict(artifact_id='math',media_type='application/json')
        relation=dict(candidate=candidate,mechanics_attempt=source,offline_trajectory='trajectory',original_task_feasible=True,relaxed_nlp_feasible=True)
        records={'handoff':relation,'math':dict(status='solved')}
        h=SimpleNamespace(store=SimpleNamespace(artifact=lambda r:records[r['artifact_id']]))
        with patch.object(core,'state',return_value={'handoffs':[dict(artifact_id='handoff')],'mechanics_results':[]}):
            view=feedback.mechanics_context(h,candidate)[0]
            self.assertEqual(view['independent_mathematical_verification'],'not performed');self.assertTrue(view['exploratory_closed_loop'])

    def test_nmpc_first_use_admitted_under_enforced_cap(self):
        from types import SimpleNamespace
        cfg={'task':'fixed'};s=dict(spec={'nmpc_execution_cap_s':1800,'nmpc_budgeted_first_use':True},results=[])
        with patch.object(core,'state',return_value=s),patch.object(core,'verify_candidate',return_value={'scientific_configuration':cfg}):
            gate=core.nmpc_timing(SimpleNamespace(),'candidate')
            self.assertTrue(gate['available']);self.assertIsNone(gate['complete_execution_s'])
            self.assertEqual(gate['reservation_s'],1800)

    def test_rejected_allocation_returns_actual_remaining_capacity(self):
        from types import SimpleNamespace
        from tools import research_core_rl as bridge
        spec=read(core.ROOT/'examples/research_core/autonomous_design_control.json')
        entries={str(n):dict(request_identity='fixture',allocation={'actions':199936,'active_seconds':1200}) for n in range(2)}
        h=SimpleNamespace(run_id='fixture',store=SimpleNamespace(lookup=lambda *a:None))
        state=dict(spec=spec,rl_runs=entries)
        q=dict(operation='start',candidate={'artifact_id':'c'*64},mode='direct',allocation={'actions':400000,'active_seconds':1800},rationale='over allocated seconds')
        with patch.object(core,'state',return_value=state),patch.object(core,'guard'),patch.object(core,'admit_closeout'),patch.object(bridge,'prepare_input',return_value=({},{})),patch.object(bridge,'invoke',side_effect=AssertionError('must not start')),patch.object(bridge,'evaluation_capacity',return_value={}):
            with self.assertRaisesRegex(ValueError,'remaining.*trials.*1.*allocated_active_seconds.*1200.*no training started'):
                bridge.dispatch(h,q,'over-allocation')


class ExecutionBoundaryTests(TestCase):
    def test_real_contained_normal_and_child_timeout(self):
        import subprocess, os
        from tools.service_execution import _run_contained
        with TemporaryDirectory(dir=core.ROOT/'runs',prefix='tree-fixture-') as folder:
            path=core.Path(folder);pids=path/'pids.json'
            with (path/'worker.log').open('w') as log:
                done=_run_contained([str(core.PYTHON),'-c','from tools.service_execution import contain_worker_children; job=contain_worker_children()'],log,10)
                self.assertEqual(done.returncode,0)
                code="import os,sys,time,subprocess,json; from tools.service_execution import contain_worker_children; job=contain_worker_children(); child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); open(sys.argv[1],'w').write(json.dumps([os.getpid(),child.pid])); time.sleep(60)"
                with self.assertRaises(subprocess.TimeoutExpired) as caught:
                    _run_contained([str(core.PYTHON),'-c',code,str(pids)],log,3)
            self.assertTrue(caught.exception.termination_confirmed)
            self.assertTrue(pids.exists(),(path/'worker.log').read_text())
            for pid in read(pids):
                if os.name=='nt':
                    import ctypes as c
                    from ctypes import wintypes as w
                    kernel=c.WinDLL('kernel32',use_last_error=True)
                    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
                    kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];kernel.CloseHandle.argtypes=[w.HANDLE]
                    handle=kernel.OpenProcess(0x100000,False,pid)
                    if handle:
                        try:self.assertEqual(kernel.WaitForSingleObject(handle,0),0)
                        finally:kernel.CloseHandle(handle)
                else:
                    try:os.kill(pid,0)
                    except ProcessLookupError:pass
                    else:self.fail('Owned process still alive')

    def test_timeout_failure_receipt_and_no_replay_exact_reservation(self):
        import json
        from tools import research_core_execution_worker as worker
        for stage in ('simulation','evaluation',None,'uncertain'):
            with self.subTest(stage=stage),TemporaryDirectory(dir=core.ROOT/'runs',prefix='timeout-fixture-') as folder:
                path=core.Path(folder);spec=read(core.DEFAULT_SPEC)
                spec.update(study_id='timeout-'+path.name,started_unix=time.time(),nmpc_execution_cap_s=12)
                core.atomic_json(path/'spec.json',spec);h=core.prepare(path/'spec.json',path/'store')
                core.update(h,freeze='fixture',numerical_reserved_s=5.)
                before=core.state(h);saved=[]
                def launch(command,log,timeout):
                    self.assertEqual(core.state(h)['pending']['reserved_s'],12)
                    request=read(command[-1]);child=core.Host(h.store.root,request['owner'],actor=h.actor)
                    if stage is not None:
                        child.create(request['configuration'],parent_run_id=h.run_id)
                        if stage=='evaluation':
                            row,_=h.store.reserve(child.run_id,'complete-simulation','fixture-sim',h.actor,{**core.zero(),'backend_solves':1})
                            saved.append(h.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],caller=h.actor,tool_id='simulation.run',tool_version='1.0.0',execution_status='completed',charged=core.zero()),{'fixture':True},elapsed=.01))
                        name='evaluation' if stage=='evaluation' else 'simulation'
                        h.store.reserve(child.run_id,'complete-'+name,'fixture-'+name,h.actor,{**core.zero(),'wall_s':10})
                    exc=core.subprocess.TimeoutExpired(command,timeout);exc.termination_confirmed=stage!='uncertain';raise exc
                with patch.object(core,'guard'),patch('tools.service_execution._run_contained',side_effect=launch) as launched,patch.object(worker,'execute',side_effect=AssertionError('no physical execution')):
                    result=core.execute(h,before['reference_candidate'],'timeout')
                    if stage=='uncertain':
                        self.assertEqual(result['status'],'execution_unresolved');self.assertEqual(core.state(h)['numerical_reserved_s'],17)
                        again=core.finish_execution(h,recovery=True);self.assertEqual(again['status'],'execution_unresolved')
                    else:
                        self.assertEqual(result['status'],'execution_incomplete');self.assertIsNone(result['acceptance'])
                        self.assertEqual(core.state(h)['numerical_reserved_s'],5.)
                        detail=h.store.artifact(result['reference']);self.assertEqual(detail['execution']['task_performance'],'unmeasured')
                        if stage:
                            receipt=json.loads(h.store.lookup(result['owner_run_id'],'complete-'+stage)['receipt'])
                            self.assertEqual(receipt['execution_status'],'failed');self.assertEqual(receipt['error'],'TIMEOUT')
                        else:self.assertEqual(detail['execution']['stage'],'execution')
                        if saved:self.assertEqual(json.loads(h.store.lookup(result['owner_run_id'],'complete-simulation')['receipt']),saved[0])
                        with self.assertRaisesRegex(ValueError,'NO_PENDING'):core.finish_execution(h,recovery=True)
                    launched.assert_called_once()
                __import__('gc').collect()

    def test_exact_historical_import_is_publicly_usable_without_experiment(self):
        from tools import research_core_mechanics as mechanics,research_core_rl as bridge
        with TemporaryDirectory(dir=core.ROOT/'runs',prefix='import-fixture-') as folder:
            path=core.Path(folder);spec=read(core.ROOT/'examples/research_core/contained_autonomous_study.json')
            spec.update(study_id='import-'+path.name,started_unix=time.time());core.atomic_json(path/'spec.json',spec)
            with patch('tools.execution_completion.complete_execution',side_effect=AssertionError('no rollout')),patch.object(mechanics,'dispatch',side_effect=AssertionError('no solve')):
                h=core.prepare(path/'spec.json',path/'store');source=spec['historical_evidence']['references']
                self.assertEqual(core.verify_candidate(h,source['joint_candidate'])['parameters']['d'],-.2394244339763736)
                self.assertEqual(mechanics.source(h,source['mathematical_source'])['operation'],'solve')
                self.assertTrue(bridge.compatible_references(h)[0]['available'])
                context=__import__('tools.research_core_feedback',fromlist=['mechanics_context']).mechanics_context(h,source['joint_candidate'])[0]
                self.assertEqual(context['independent_mathematical_verification'],'failed')
                self.assertEqual(context['failed_verification_metrics'][0]['time_s'],.2925)
                self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
                self.assertEqual(core.state(h)['offline_nlp'],0)
                for ref in spec['historical_evidence']['references'].values(): core.read_evidence(h,{'reference':ref})
            __import__('gc').collect()

    def test_optional_trial_cap_remaining_and_explicit_smaller_request(self):
        from tools import research_core_rl as bridge
        with TemporaryDirectory(dir=core.ROOT/'runs',prefix='allocation-fixture-') as folder:
            path=core.Path(folder);spec=read(core.ROOT/'examples/research_core/contained_autonomous_study.json')
            spec.pop('historical_evidence');spec.update(supplied_evidence=[],study_id='allocation-'+path.name,started_unix=time.time())
            spec['rl_limits'].update(training_actions=1024,training_active_seconds=100)
            core.atomic_json(path/'spec.json',spec);h=core.prepare(path/'spec.json',path/'store');candidate=core.state(h)['reference_candidate']
            q=dict(operation='start',candidate=candidate,mode='direct',training_overrides=dict(n_steps=32,batch_size=16,n_epochs=2),allocation=dict(actions=64,active_seconds=10),rationale='fixture')
            with patch.object(core,'guard'),patch.object(bridge,'invoke',return_value={'status':'starting'}) as launch:
                for i in range(4):
                    if i==1: spec['rl_limits'].pop('training_runs');core.update(h,spec=spec)
                    q['rationale']='explicit trial '+str(i);bridge.dispatch(h,q,'trial-'+str(i))
                feedback=bridge.allocation_feedback(h);self.assertIsNone(feedback['remaining_allocatable']['trials'])
                self.assertEqual(feedback['cumulative_allocated'],dict(actions=256,active_seconds=40))
                q['allocation']['active_seconds']=70
                with self.assertRaisesRegex(ValueError,'allocated_active_seconds.*60'):bridge.dispatch(h,q,'oversized')
                self.assertEqual(launch.call_count,4)
                q['allocation']['active_seconds']=60;bridge.dispatch(h,q,'fitting')
                self.assertEqual(launch.call_count,5);self.assertEqual(bridge.allocation_feedback(h)['remaining_allocatable']['allocated_active_seconds'],0)
                spec['rl_limits']['training_runs']=5;core.update(h,spec=spec)
                q['allocation']['active_seconds']=1
                with self.assertRaisesRegex(ValueError,'ceiling'):bridge.dispatch(h,q,'finite-cap')
                self.assertEqual(len(core.state(h)['rl_runs']),5)
                self.assertEqual(core.state(h)['charged_starts'],5)
                spec['shared_start_limit']=6;core.update(h,spec=spec)
                self.assertEqual(bridge.evaluation_capacity(h)['admitted'],0)
                self.assertEqual(core.capacity(h)['admitted'],0)
                # Terminal failure with no policy can STOP after explicit reads;
                # no impossible evaluation or replacement training is invoked.
                runs=core.state(h)['rl_runs'];summaries=[]
                for run_id,entry in runs.items():
                    ref=core.save(h,dict(run_id=run_id,status='failed',checkpoint=None,task_performance='unmeasured'))
                    entry.update(training_summary=ref,status=dict(worker_alive=False));summaries.append(ref)
                core.update(h,rl_runs=runs,rl_training_summaries=summaries)
                for ref in summaries:core.read_evidence(h,dict(reference=ref))
                plan=dict(action='stop',next_step='stop',supporting_evidence=summaries,**{k:'Terminal failure, task performance unmeasured' for k in ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation')})
                result=core.dispatch(h,plan,'failure-stop')
                self.assertTrue(result['result']['accepted_stop']);self.assertEqual(launch.call_count,5)
                self.assertFalse(core.claims(h)['task_passed'])
            __import__('gc').collect()
