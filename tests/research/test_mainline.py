"""Focused boundary fixtures; no new mathematical solve or complete episode."""
from copy import deepcopy
from pathlib import Path
import json,subprocess,tempfile,time,unittest
from types import SimpleNamespace
from unittest.mock import patch
from schemas.platform import ProjectConfig,SessionInput
from tools.platform_store import Store,plain,zero
from tools.state_io import digest
from tools.research.config import resolve,ROOT
from tools.research.design import full_science
from tools.research.state import state,update,save
from tools.research import core,feedback,analysis,rl
from tools.research.contracts import Search,AnalysisRequest


class MainlineTests(unittest.TestCase):
    def setUp(self):
        # Python's Windows 0700 temporary-directory ACL excludes sandbox readers.
        # A normal workspace directory inherits the workspace access contract.
        from uuid import uuid4
        import shutil
        folder=ROOT/'runs'/('fixture-'+uuid4().hex)
        folder.mkdir(parents=True)
        def cleanup():
            resolved=folder.resolve()
            if resolved.parent!=(ROOT/'runs').resolve():
                raise ValueError('Fixture cleanup must stay inside workspace runs')
            shutil.rmtree(resolved)
        self.tmp=SimpleNamespace(name=str(folder),cleanup=cleanup)
        self.spec=resolve(ROOT/'configs/research/study.json');self.cfg=deepcopy(self.spec['configuration'])
        self.host=SimpleNamespace(store=Store(Path(self.tmp.name)),run_id=self.cfg['run_id'],actor='fixture')
        fixture_id=Path(self.tmp.name).name
        self.host.store.create(ProjectConfig(project_id=fixture_id,grant_id=fixture_id,authorization_source='code-only fixture',budget=self.cfg['policy']['budget'],exclusive_resources={'backend.family_mujoco':1}))
        self.host.store.create_session(dict(input=self.cfg))
        update(self.host,spec=self.spec,base_configuration=self.cfg,nominal_configuration=self.cfg,
            profile=dict(identity='fixture',recipe=self.cfg['policy']['controller']['parameters']['data']['recipe']),
            results=[],rl_evaluations=[],candidates={},plans=[],retrievals=[],analysis_results=[],search_results=[],pending=None,
            selected=None,research_status='ready',numerical_s=0,numerical_reserved_s=0,started_unix=time.time(),cutoff_unix=time.time()+10000)
        science=full_science(self.cfg);p=self.spec['reference_parameters'];profile=state(self.host)['profile']
        identity=digest(dict(parameters=p,configuration=science,evaluation_profile=profile))
        c=dict(candidate_id=identity,identity=identity,parameters=p,resolved_parameters=p,configuration=self.cfg,
            scientific_configuration=science,configuration_reference=save(self.host,self.cfg),task_identity=digest(self.cfg['task']),
            source_identity=digest(self.cfg),profile_identity='fixture')
        self.candidate=save(self.host,c);update(self.host,candidates={identity:self.candidate},reference_candidate=self.candidate,rl_task=save(self.host,self.cfg['task']))
        self.result=save(self.host,dict(status='evaluated',candidate=self.candidate,profile_identity='fixture',scientific_configuration=science,
            study=self.host.run_id,role='development',execution_id='development',numerical_s=1.,acceptance=dict(accepted=True,metrics={})))
        update(self.host,results=[self.result])

    def tearDown(self):
        import gc
        gc.collect();self.tmp.cleanup()

    def plan(self,action='select'):
        return dict(action=action,selected_execution=self.result,hypothesis='fixture',expected_observation='fixture',weakening_observation='fixture',
            fixed_conditions='fixture',stopping_condition='fixture',interpretation='fixture')

    def test_zero_selection_requires_read_and_seals_without_execution(self):
        self.assertFalse(feedback.eligibility(self.host,self.result)['eligible'])
        core.read_evidence(self.host,dict(reference=self.result,pointer='/status'))
        self.assertFalse(feedback.eligibility(self.host,self.result)['eligible'])
        core.read_evidence(self.host,dict(reference=self.result))
        with patch.object(core,'guard'),patch.object(core,'execute') as execute:
            out=core.dispatch(self.host,self.plan(),'select-fixture')
            execute.assert_not_called()
        self.assertTrue(out['result']['task_passed']);self.assertEqual(state(self.host)['research_status'],'stopped')
        self.assertEqual(out['result']['confirmation_status'],'not_required')
        self.assertFalse(feedback.confirmation_progress(self.host)['confirmed'])
        self.assertEqual(feedback.confirmation_progress(self.host)['correct_operation']['action'],'select')
        self.assertFalse(core.claims(self.host)['reproducibility_assessed'])

    def test_historical_incomplete_cached_proxy_cannot_select(self):
        core.read_evidence(self.host,dict(reference=self.result))
        for edits in [dict(study='historical'),dict(status='incomplete'),dict(cached_operation_receipt=True),dict(acceptance=dict(accepted=False))]:
            value=self.host.store.artifact(self.result);value.update(edits);ref=save(self.host,value)
            update(self.host,results=[ref],evaluation_reads=[ref])
            self.assertFalse(feedback.eligibility(self.host,ref)['eligible'])

    def test_positive_confirmation_retains_failure_and_identity(self):
        self.spec['confirmation']['fresh_independent_repetitions']=1;update(self.host,spec=self.spec,evaluation_reads=[self.result])
        self.assertTrue(feedback.eligibility(self.host,self.result)['eligible'])
        failed=self.host.store.artifact(self.result);failed.update(role='confirmation',execution_id='failed-confirmation',acceptance=dict(accepted=False))
        failure=save(self.host,failed);update(self.host,results=[self.result,failure],selected=self.result)
        progress=feedback.confirmation_progress(self.host)
        self.assertEqual(progress['failures'],1);self.assertFalse(progress['confirmed'])
        self.assertFalse(feedback.eligibility(self.host,self.result)['eligible'])

    def test_selection_receipt_reuse_adds_no_execution_or_charge(self):
        core.read_evidence(self.host,dict(reference=self.result))
        with patch.object(core,'guard'),patch.object(core,'execute') as execute:
            core.dispatch(self.host,self.plan(),'exact-fixture');used=self.host.store.remaining()['used']
            reused=core.dispatch(self.host,self.plan(),'exact-fixture')
            execute.assert_not_called()
        self.assertEqual(self.host.store.remaining()['used'],used)
        self.assertEqual(reused['operation_reuse']['additional_scientific_executions'],0)

    def test_analysis_recovery_and_receipt_prevent_duplicate_charge_or_worker(self):
        from tools.state_io import atomic_json
        from tools.service_execution import _run_contained
        q=plain(AnalysisRequest(candidate=self.candidate,operation='controllability',operating_point='target_equilibrium',
            protocol=self.spec['analysis_protocol'],scoring_window_s=.35))
        key='recovery-fixture-analysis';cap=0.
        self.host.store.reserve(self.host.run_id,key,digest(q),self.host.actor,{**zero(),'wall_s':cap})
        folder=Path(self.tmp.name)/'analysis';folder.mkdir()
        atomic_json(folder/'boundary.json',dict(termination_confirmed=True,elapsed_s=.4,returncode=0))
        atomic_json(folder/'result.json',dict(status='computed',proxy_values={'held_position_min_eigenvalue':1.},internal_calculations=[]))
        (folder/'worker.log').write_text('fixture, no solve')
        update(self.host,pending=dict(folder=str(folder),worker_request_id=key,request=q,origin='fixture',implementation='fixture',reserved_s=cap),
            numerical_reserved_s=cap,mathematical_evaluations=1)
        first=analysis.recover(self.host);used=self.host.store.remaining()['used'];spent=state(self.host)['numerical_s']
        with patch('tools.service_execution._run_contained') as worker,patch.object(core,'guard') as guarded:
            second=analysis.dispatch(self.host,q,'recovery-fixture',guard=guarded)
            worker.assert_not_called();guarded.assert_not_called()
        self.assertEqual(second['reference'],first['reference']);self.assertEqual(state(self.host)['numerical_s'],spent)
        self.assertEqual(self.host.store.remaining()['used'],used);self.assertEqual(state(self.host)['mathematical_evaluations'],1)

    def test_explicit_score_window_and_mixed_control_capability(self):
        p=self.spec['reference_parameters'];q=dict(variables=['segments.near.length_m'],bounds={'segments.near.length_m':[.152,.168]},
            fixed=p,objective='held_position_min_eigenvalue',operating_point='target_equilibrium',protocol=self.spec['analysis_protocol'],scoring_window_s=.35,max_evaluations=2)
        self.assertEqual(Search.model_validate(q).scoring_window_s,.35)
        q.update(variables=['holding_tip_speed_weight'],bounds={'holding_tip_speed_weight':[.025,.10]})
        with self.assertRaisesRegex(ValueError,'CONTROL_VARIABLES_REQUIRE_BACKEND'):Search.model_validate(q)
        metadata=analysis.score_semantics(SimpleNamespace(scoring_window_s=.35),dict(candidate_id='fixture'),SimpleNamespace(input_scale_n=8,output_scale_m=.01),{})
        self.assertIn('held input',metadata['held_position_min_eigenvalue']['supported_interpretation'])
        self.assertIn('damping margin or decay rate',metadata['held_position_min_eigenvalue']['unsupported_conclusions'])

    def orphan_fixture(self):
        owner='orphan-fixture';folder=self.host.store.root/'executions'/owner
        folder.mkdir(parents=True)
        cfg={**self.cfg,'run_id':owner}
        self.host.store.create_session(dict(input=cfg,parent_run_id=self.host.run_id))
        self.host.store.reserve(owner,'complete-simulation','fixture',self.host.actor,{**zero(),'backend_solves':1})
        update(self.host,pending=dict(owner=owner,configuration=cfg,candidate=self.candidate,
            launch_intent=True,started_unix=time.time()-5))
        command='python -m tools.research.execution_worker '+str(folder/'request.json')
        inventory=dict(captured_unix=time.time(),processes=[dict(ProcessId=123,ParentProcessId=122,CommandLine=command)])
        return folder,inventory

    def test_unknown_orphan_without_proof_remains_blocked(self):
        self.orphan_fixture();before=self.host.store.remaining()
        with patch('tools.service_execution._run_contained') as worker:
            with self.assertRaisesRegex(ValueError,'UNKNOWN_WORKER_TERMINATION'):
                core.finish_execution(self.host,recovery=True)
            worker.assert_not_called()
        self.assertEqual(before,self.host.store.remaining())
        self.assertIsNotNone(state(self.host)['pending'])

    def test_orphan_inventory_must_bind_original_worker_request(self):
        from tools.research.execution import record_orphan_exit
        folder,inventory=self.orphan_fixture();inventory['processes'][0]['CommandLine']='python unrelated.py'
        ref=save(self.host,inventory)
        with patch('tools.service_execution.process_exit_observation') as probe:
            with self.assertRaisesRegex(ValueError,'ORIGINAL_WORKER_IDENTITY_REQUIRED'):
                record_orphan_exit(self.host,ref)
            probe.assert_not_called()
        self.assertFalse((folder/'recovery_boundary.json').exists())

    def test_live_or_inaccessible_orphan_cannot_be_settled(self):
        from tools.research.execution import record_orphan_exit
        folder,inventory=self.orphan_fixture();ref=save(self.host,inventory)
        for message in ('PROCESS_STILL_PRESENT_OR_PID_REUSED','PROCESS_EXIT_UNCONFIRMED'):
            with patch('tools.service_execution.process_exit_observation',side_effect=ValueError(message)):
                with self.assertRaisesRegex(ValueError,message):record_orphan_exit(self.host,ref)
            self.assertFalse((folder/'recovery_boundary.json').exists())

    def test_verified_orphan_exit_is_idempotent_and_preserves_reserved_counts(self):
        from tools.research.execution import record_orphan_exit
        folder,inventory=self.orphan_fixture();ref=save(self.host,inventory);before=self.host.store.remaining()
        with patch('tools.service_execution.process_exit_observation',return_value=dict(pid=123,exited=True)) as probe:
            first=record_orphan_exit(self.host,ref);second=record_orphan_exit(self.host,ref)
            self.assertEqual(probe.call_count,1)
        self.assertEqual(first,second)
        self.assertIsNone(first['returncode'])
        self.assertIn('upper bound',first['elapsed_semantics'])
        self.assertFalse((folder/'boundary.json').exists())
        self.assertEqual(before,self.host.store.remaining())
        self.assertIsNone(self.host.store.lookup('orphan-fixture','complete-simulation')['receipt'])

    def test_confirmed_orphan_seals_incomplete_without_relaunch_or_budget_reset(self):
        from tools.research.execution import record_orphan_exit
        folder,inventory=self.orphan_fixture();s=state(self.host)
        candidate=self.host.store.artifact(self.candidate);candidate['evaluation_version']=1
        ref=save(self.host,candidate)
        update(self.host,freeze='offline_fixture',nmpc_launches=1,
            profile={**s['profile'],'science_hashes':{}},results=[],
            pending={**s['pending'],'candidate':ref,'profile_identity':'fixture','role':'development',
                'selected_execution':None,'operation_key':'orphan-operation','reserved_s':0.})
        with patch('tools.service_execution.process_exit_observation',return_value=dict(pid=123,exited=True)):
            record_orphan_exit(self.host,save(self.host,inventory))
        with patch('tools.service_execution._run_contained') as worker:
            result=core.finish_execution(self.host,recovery=True)
            again=core.recover(self.host)
            worker.assert_not_called()
        self.assertEqual(result['status'],'execution_incomplete')
        self.assertEqual(result['operation_cost']['additional_scientific_executions'],0)
        self.assertIsNone(result['acceptance'])
        self.assertIsNone(state(self.host)['pending'])
        self.assertEqual(state(self.host)['nmpc_launches'],1)
        self.assertEqual(self.host.store.remaining()['used']['backend_solves'],1)
        self.assertIsNone(again['execution'])

    def test_disabled_time_and_environment(self):
        runtime=self.spec['runtime']
        update(self.host,rl_runs={},spec=self.spec,numerical_s=1e12)
        self.assertEqual(rl.evaluation_capacity(self.host)['admitted'],1)
        with patch.object(rl.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{}')) as invoked:
            rl.invoke(self.host,'evaluate','fixture')
        args=invoked.call_args
        self.assertEqual(args.args[0][0],runtime['rl_python'])
        self.assertIsNone(args.kwargs['timeout'])
        self.assertEqual(args.kwargs['env']['OPENBLAS_NUM_THREADS'],'1')
        self.assertIn('SOFTROBOT_RL_RUNS',args.kwargs['env'])

    def test_owned_rl_worker_inherits_run_directory(self):
        from tools.rl import run
        directory=Path(self.tmp.name)/'owned'/'worker';directory.mkdir(parents=True)
        run.write_json(directory/'config.json',dict(budget=dict(active_seconds=10)))
        worker_state=dict(consumed=dict(active_seconds=0))
        with patch.object(run.subprocess,'Popen',return_value=SimpleNamespace(pid=1234)) as started,patch.object(run,'process_birth',return_value=1):
            run.launch(directory,worker_state,self.spec['runtime']['rl_python'])
        env=started.call_args.kwargs['env']
        self.assertEqual(env['SOFTROBOT_RL_RUNS'],str(directory.parent))
        self.assertEqual(env['OMP_NUM_THREADS'],'1')

    def test_physical_reference_and_rl_seed_have_single_input_owner(self):
        raw=json.loads((ROOT/'configs/research/study.json').read_text())
        runtime=json.loads((ROOT/'configs/research/runtime.json').read_text())
        self.assertNotIn('segments',raw['reference_parameters']);self.assertNotIn('rl_defaults',runtime)
        robot=json.loads((ROOT/'configs/research/robot.json').read_text())['robot']['structure']['data']
        for part in robot['components']:
            if part['kind']=='flexible_segment':
                self.assertEqual(self.spec['reference_parameters']['segments'][part['id']]['length_m'],part['length_m'])
        self.assertEqual(self.spec['control']['rl_defaults']['seed'],self.cfg['seed'])

    def test_fixed_total_search_and_static_or_saved_horizon_contracts(self):
        from tools.research.search import coordinate_layout
        q=Search(variables=['segments.near.length_m','segments.distal1.length_m'],
            bounds={'segments.near.length_m':[.152,.168],'segments.distal1.length_m':[.1045,.1155]},
            fixed=self.spec['reference_parameters'],objective='held_position_min_eigenvalue',operating_point='target_equilibrium',
            protocol=self.spec['analysis_protocol'],scoring_window_s=.35,max_evaluations=2)
        layout=coordinate_layout(q,dict(fixed_total_m=.27))
        self.assertEqual(len(layout['names']),1);self.assertIsNotNone(layout['dependent_length'])
        braking=AnalysisRequest(candidate=self.candidate,execution=self.result,update_id=34,operation='braking',operating_point='saved_state',protocol=self.spec['analysis_protocol'])
        self.assertIsNone(braking.scoring_window_s)
        with self.assertRaisesRegex(ValueError,'EXPLICIT_SCORE_WINDOW_REQUIRED'):
            AnalysisRequest(candidate=self.candidate,operation='controllability',protocol=self.spec['analysis_protocol'])

    def test_native_residual_reference_requires_exact_channel_order(self):
        from extensions.tendon_family import backends,scene
        order=[t['id'] for t in self.cfg['robot']['structure']['data']['tendons']]
        trajectory=dict(tendon_order=order,tensions_n=[[.2]*len(order)]*35,times_s=[k*.01 for k in range(36)])
        request=save(self.host,dict(configuration=self.cfg))
        value=dict(operation='solve',design_candidate=self.candidate,trajectory=trajectory,original_request=request)
        ref=save(self.host,value);update(self.host,mechanics_results=[ref])
        with patch.object(backends,'physics_for',return_value=dict(tendons=[dict(entity=t) for t in order])),patch.object(scene,'assemble',return_value=dict(task_identity=digest(self.cfg['task']))):
            self.assertTrue(rl.compatible_references(self.host)[0]['available'])
            value['trajectory']['tendon_order']=list(reversed(order))
            update(self.host,mechanics_results=[save(self.host,value)])
            self.assertFalse(rl.compatible_references(self.host)[0]['available'])

    def test_tracked_file_inventory_and_import_closure(self):
        files=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
        banned=['tools/nmpc_settling.py','tools/research_v2.py','tools/strands_pilot.py','tools/strands_pilot_r3.py','schemas/research_core.py','tools/design_optimization.py']
        self.assertFalse(set(files)&set(banned))
        self.assertFalse(any(p.startswith(('examples/','tools/legacy/','archive/','legacy/')) for p in files))
        from tools.research import agent
        from tools.platform_registry import registry
        registered=registry();self.assertIsNotNone(registered.get('controller.gvs_nmpc','11.0.0'))
        from tools.research_tasks import task_adapter
        self.assertEqual(task_adapter(self.cfg).task['family'],'task.reach')
        from tools.platform_registry import dependency_closure
        closure=dependency_closure(registered.extensions.values(),registered)
        self.assertTrue({'controller.gvs_nmpc@11.0.0','backend.family_mujoco@1.1.0','optimization_assembler.gvs_trajectory@1.0.0'}<=set(closure))
        self.assertTrue(all(v['sources'] for v in closure.values()))
        from extensions.tendon_family.contracts import Data
        self.assertIs(registered.contracts[('family.backend_data','1.0.0')],Data)
        import sys
        self.assertFalse(any(p[:-3].replace('/','.') in sys.modules for p in banned))


class C0ReadinessTests(unittest.TestCase):
    """Synthetic lifecycle workers; the cold-start check uses zero physics steps."""
    def fixture(self,repetitions=0):
        f=MainlineTests();f.setUp();self.addCleanup(f.tearDown)
        spec=state(f.host)['spec'];spec.update(capabilities=['analysis','control_correction','physical_replay'],
            allowed_plan_actions=['initialize_control','physical_replay','select','confirm','stop'],require_task_guidance=False)
        spec['confirmation']['fresh_independent_repetitions']=repetitions
        spec['nmpc_limits']['executions']=0;spec['budgets']['physical_launches']=2
        profile=state(f.host)['profile'];profile['version']=1
        update(f.host,spec=spec,profile=profile,results=[],candidates={},physical_replays=[],freeze='synthetic-c0')
        from tools.research.design import construct
        parameters=deepcopy(spec['reference_parameters']);parameters['segments']['near']['young_pa']*=1.005
        f.candidate=construct(f.host,parameters,dict(origin='Synthetic C0 independent generated structure'))
        f.cfg=f.host.store.artifact(f.candidate)['configuration']
        return f

    def plan(self,f,action,**kwargs):
        value=f.plan(action)
        if action not in ('select','confirm'):value.pop('selected_execution')
        value.update(kwargs);return value

    def worker(self,command,log,timeout):
        from tools.state_io import read,atomic_json
        request=read(Path(command[-1]));u=request['trajectory']['tensions_n'];n=len(u[0])
        target=request['configuration']['task']['goal']['data']['target_m']
        samples=[dict(time_s=i*.01,tip_m=target,tip_velocity_m_s=[0.,0.,0.],speed_m_s=0.,
            actual_tension_n=[0.]*n if i==0 else u[i-1]) for i in range(36)]
        atomic_json(Path(command[-1]).with_name('result.json'),dict(status='completed',samples=samples,
            physics_steps=700,tendon_order=request['trajectory']['tendon_order'],synthetic_fixture=True))
        return SimpleNamespace(returncode=0)

    def seed(self,f):
        value=core.dispatch(f.host,self.plan(f,'initialize_control',control_seed=dict(candidate=f.candidate)),'c0-seed')
        return value['result']['source']

    def test_fixed_select_zero_and_positive_confirmation_recovery(self):
        from contextlib import ExitStack
        from tools.research.budget import closeout_operations,capacity
        for repetitions in (0,1):
            with self.subTest(repetitions=repetitions),ExitStack() as stack:
                f=self.fixture(repetitions)
                stack.enter_context(patch.object(core,'guard'))
                stack.enter_context(patch('tools.research.physical_replay.guard'))
                nmpc=stack.enter_context(patch.object(core,'execute',side_effect=AssertionError('NO_NMPC')))
                worker=stack.enter_context(patch('tools.service_execution._run_contained',side_effect=self.worker))
                source=self.seed(f)
                result=core.dispatch(f.host,self.plan(f,'physical_replay',physical_replay=dict(candidate=f.candidate,source=source)),'c0-development')['result']
                f.result=result['reference'];core.read_evidence(f.host,dict(reference=f.result))
                self.assertTrue(feedback.eligibility(f.host,f.result,selection=True)['eligible'])
                core.dispatch(f.host,self.plan(f,'select'),'c0-select')
                self.assertEqual(state(f.host)['selected'],f.result)
                if not repetitions:
                    self.assertEqual(state(f.host)['research_status'],'stopped');self.assertEqual(worker.call_count,1)
                    continue
                self.assertIn('confirm',closeout_operations(f.host)['research_plan'])
                from tools.research import execution
                with patch.object(execution,'guard'),self.assertRaisesRegex(ValueError,'REQUIRES_PHYSICAL_REPLAY'):
                    execution.execute(f.host,f.candidate,'wrong-nmpc-route',role='confirmation',selected=f.result)
                remaining=f.host.store.remaining();remaining['remaining']['tool_calls']=1
                with patch.object(f.host.store,'remaining',return_value=remaining):
                    self.assertEqual(capacity(f.host,1,True,root_operation=True,route='fixed_tension')['admitted'],1)
                    remaining['remaining']['tool_calls']=0
                    self.assertEqual(capacity(f.host,1,True,root_operation=False,route='fixed_tension')['admitted'],1)
                complete=f.host.store.complete
                def interrupted(row,*args,**kwargs):
                    if row['request_id']=='c0-confirm':raise RuntimeError('Synthetic parent interruption after worker settlement')
                    return complete(row,*args,**kwargs)
                with patch.object(f.host.store,'complete',side_effect=interrupted),self.assertRaisesRegex(RuntimeError,'Synthetic parent'):
                    core.dispatch(f.host,self.plan(f,'confirm'),'c0-confirm')
                used=deepcopy(f.host.store.remaining()['used'])
                recovered=core.recover(f.host)
                self.assertEqual(recovered['sealed_workflows'],['c0-confirm'])
                self.assertEqual(f.host.store.remaining()['used'],used)
                self.assertTrue(feedback.confirmation_progress(f.host)['confirmed'])
                self.assertEqual(feedback.confirmation_progress(f.host)['current_study_confirmations'],1)
                self.assertEqual(state(f.host)['research_status'],'stopped')
                core.dispatch(f.host,self.plan(f,'confirm'),'c0-confirm')
                self.assertEqual(f.host.store.remaining()['used'],used)
                self.assertEqual(worker.call_count,2);nmpc.assert_not_called()

    def test_fixed_repeat_admission_and_failed_confirmation_are_not_reset(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            f=self.fixture(1)
            stack.enter_context(patch.object(core,'guard'));stack.enter_context(patch('tools.research.physical_replay.guard'))
            stack.enter_context(patch('tools.service_execution._run_contained',side_effect=self.worker))
            source=self.seed(f)
            result=core.dispatch(f.host,self.plan(f,'physical_replay',physical_replay=dict(candidate=f.candidate,source=source)),'c0-development')['result']
            f.result=result['reference'];core.read_evidence(f.host,dict(reference=f.result))
            self.assertFalse(feedback.experiment_preflight(f.host,f.candidate,'fixed_tension',source_ref=source)['admitted'])
            core.dispatch(f.host,self.plan(f,'select'),'c0-select')
            for status in ('evaluated','execution_incomplete'):
                failed=deepcopy(result);failed.pop('reference');failed.update(role='confirmation',selected_execution=f.result,
                    operation_key='failed-confirmation',execution_id='one-failed-launch',status=status)
                failed['acceptance']['accepted']=False
                ref=save(f.host,failed);update(f.host,physical_replays=[f.result,ref])
                progress=feedback.confirmation_progress(f.host)
                self.assertFalse(progress['confirmed']);self.assertEqual(progress['remaining'],0)
                self.assertEqual(progress['failures']+progress['invalid_executions'],1)
                self.assertFalse(feedback.eligibility(f.host,f.result,selection=False)['eligible'])
            other=deepcopy(failed);other['source_reference']=save(f.host,dict(f.host.store.artifact(source),provenance=dict(renamed=True)))
            from tools.research.contracts import PhysicalReplayRequest
            from tools.research.physical_replay import dispatch
            with self.assertRaisesRegex(ValueError,'EXACT_SELECTED_CONTROL_SOURCE'):
                dispatch(f.host,PhysicalReplayRequest(candidate=f.candidate,source=other['source_reference']),'different-operation-key',role='confirmation',selected=f.result)

    def test_frozen_initial_state_and_control_start_without_history(self):
        f=self.fixture()
        from tools.research.numerics import native_point
        from tools.research.physical_replay import binding
        from tools.research.task_constraints import describe_analysis_requirements,model_assessment,check_analysis_applicability
        with patch.object(core,'guard'):
            source=self.seed(f)
        cfg=f.cfg;tr=f.host.store.artifact(source)['trajectory'];binding(cfg,tr)
        query=AnalysisRequest(candidate=f.candidate,model_source='mujoco',operation='native_dynamics_v1',
            operating_point='standardized_initial_pretension',protocol=f.spec['analysis_protocol'])
        point=native_point(f.host,query,cfg)
        self.assertEqual(point['native_replay']['rows'],[]);self.assertEqual(point['actual_time_s'],0.)
        self.assertEqual(state(f.host)['results'],[]);self.assertEqual(state(f.host)['physical_replays'],[])
        bound=dict(candidate=f.candidate,effective_configuration_identity=digest(cfg),task_identity=digest(cfg['task']),
            tendon_order=tr['tendon_order'],tension_bounds_n=[[0.,8.]]*6,target_m=cfg['task']['goal']['data']['target_m'])
        value=analysis.calculate(cfg,bound,query,point)
        self.assertEqual(value['status'],'computed');cost=value['native_analysis']['cost']
        self.assertTrue(value['binding']['physical_design_identity'])
        self.assertEqual(value['task_acceptance'],'unmeasured')
        self.assertEqual(value['scoped_claim']['conclusion'],'diagnostic')
        self.assertEqual(cost['model_builds'],1);self.assertEqual(cost['physics_steps'],0);self.assertEqual(cost['rollouts'],0)
        print('C0_ZERO_STEP_NATIVE_COST',json.dumps(cost))
        raw=plain(query);raw.update(operation='mujoco_direct_control_v1',control_optimization=dict(source=source,
            settings=dict(version='local_control_search_v2',correction_window_s=[0.,.35],knots_s=[0.,.18,.34],evaluation_requests=20,iterations=1)))
        optimized=AnalysisRequest.model_validate(raw);requirements=describe_analysis_requirements(cfg,bound)
        fit=check_analysis_applicability(requirements,optimized,model_assessment(SessionInput.model_validate(cfg),requirements,optimized.operation,model_source='mujoco'),exact_point=point)
        self.assertEqual(fit['status'],'applicable');self.assertFalse(fit['full_task_supported'])
        self.assertEqual(f.host.store.remaining()['used']['backend_solves'],0)

    def test_confirmation_count_is_frozen_and_shared_capacity_bounded(self):
        from tools.state_io import read,atomic_json
        value=read(ROOT/'configs/research/study.json')
        for name in ('robot','task','control','runtime'):value[name]=str((ROOT/'configs/research'/value[name]).resolve())
        f=self.fixture();path=Path(f.tmp.name)/'positive-confirmation.json'
        value['confirmation']['fresh_independent_repetitions']=1;atomic_json(path,value)
        self.assertEqual(resolve(path)['confirmation']['fresh_independent_repetitions'],1)
        value['confirmation']['fresh_independent_repetitions']=value['budgets']['physical_launches'];atomic_json(path,value)
        with self.assertRaisesRegex(ValueError,'SHARED_DEVELOPMENT_PLUS_REPEAT_CAPACITY'):resolve(path)

    def test_archived_math_controls_evaluation_relations_and_reads_are_bound(self):
        import tarfile
        from tools.state_io import read
        from tools.research.evidence_views import result_card
        from tools.research import reporter
        from tests.research.test_research_reporting import offline_host
        summary=read(ROOT/'evidence/mujoco_direct_stage_b/summary.json')
        with tarfile.open(ROOT/'evidence/mujoco_direct_stage_b/study/immutable_artifacts.tar.gz') as archive:
            values={Path(m.name).stem:json.load(archive.extractfile(m)) for m in archive.getmembers() if m.name.endswith('.json')}
        physical=[summary['replays'][name]['reference'] for name in ('baseline','optimized')]
        host,current=offline_host(values,physical_replays=physical,analysis_results=[summary['optimization_reference']])
        before=deepcopy(values);before_state=deepcopy(current)
        for ref in [summary['optimization_reference'],*physical]:
            card=plain(result_card(host,ref));trajectory=values[card['identity']['control_source']['artifact_id']]['trajectory']
            self.assertEqual(card['identity']['design_identity'],trajectory['design_identity'])
            self.assertIsNotNone(card['identity']['model_identity'])
        for ref in physical:
            view=feedback.result_view(host,ref)
            self.assertEqual(view['controller'],dict(route='fixed_tension',source=values[ref['artifact_id']]['source_reference']))
        report=plain(reporter.assemble(host,physical,question='C0 archival interface comparison'))
        self.assertTrue(report['relations'][0]['comparable'])
        self.assertFalse(any('Unknown design_identity' in r or 'Unknown model_identity' in r for r in report['relations'][0]['reasons']))
        raw=core.read_evidence(host,dict(reference=summary['replays']['optimized']['raw_reference'],pointer='/samples',view='range',start=30,count=6),record_read=False)
        self.assertEqual(len(raw['items']),6)
        self.assertEqual(values,before);self.assertEqual(current,before_state)


if __name__=='__main__':unittest.main()
