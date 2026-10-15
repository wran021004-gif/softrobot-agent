"""Configuration, count, publication and success fixtures; no scientific workers."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_mainline as fixtures
from tools.research import core, rl
from tools.research.state import state, update, save
from tools.research.config import rl_configuration, ROOT
from tools.research.budget import observe_pass, protected
from tools.rl import run
from tools.rl.continuation import config_digest, published_checkpoint, validate_compatibility
from tools.platform_store import zero


class CountContinuationTests(fixtures.MainlineTests):
    # Reuse only fixture construction; inherited tests run in their owning class.
    def test_nested_sparse_patch_and_effective_validation(self):
        defaults=self.spec['control']['rl_defaults']
        selected=rl_configuration(defaults,{'policy_kwargs':{'log_std_init':-2.}})
        self.assertEqual(selected['ppo']['policy_kwargs']['net_arch'],defaults['ppo']['policy_kwargs']['net_arch'])
        with self.assertRaises((ValueError,TypeError)):
            rl_configuration(defaults,{'n_steps':None})
        with self.assertRaisesRegex(ValueError,'UNKNOWN_CONFIGURATION_FIELD'):
            rl_configuration(defaults,{'unknown':1})
        self.assertIsNone(rl_configuration(defaults,{'target_kl':None})['ppo']['target_kl'])
        self.assertEqual(defaults['ppo']['policy_kwargs']['log_std_init'],-3.)

    def test_ten_stages_shared_by_start_continue_and_not_resume_or_reuse(self):
        update(self.host,rl_runs={},freeze='fixture')
        cfg=deepcopy(self.spec['control']['rl_defaults'])
        cfg.update(requested_allocation=cfg['budget'])
        start=dict(operation='start',candidate=self.candidate,mode='direct',allocation={'actions':2048},rationale='fixture')
        with patch.object(rl.state_api if hasattr(rl,'state_api') else __import__('tools.research.state',fromlist=['guard']),'guard'), \
             patch.object(rl,'prepare_input',return_value=(cfg,state(self.host)['rl_task'])), \
             patch.object(rl,'prepare_continuation',return_value=(cfg,state(self.host)['rl_task'])), \
             patch.object(rl,'invoke',return_value={'status':'starting'}) as launch:
            first=rl.dispatch(self.host,start,'stage-0')
            parent=next(iter(state(self.host)['rl_runs']))
            for i in range(1,10):
                request=start if i%2==0 else dict(operation='continue',run_id=parent,checkpoint='published-fixture',allocation={'actions':2048},rationale='fixture')
                request={**request,'rationale':str(i)}
                rl.dispatch(self.host,request,'stage-'+str(i))
            self.assertEqual(state(self.host)['admitted_training_stages'],10)
            self.assertEqual(launch.call_count,10)
            used=self.host.store.remaining()['used']
            rl.dispatch(self.host,start,'stage-0')
            self.assertEqual(self.host.store.remaining()['used'],used)
            with self.assertRaisesRegex(ValueError,'TRAINING_STAGE_LIMIT'):
                rl.dispatch(self.host,{**start,'rationale':'eleventh'},'stage-10')
            self.assertEqual(launch.call_count,10)
            with patch.object(rl,'reconcile',return_value={'worker_alive':False,'remaining':{'actions':512}}):
                rl.dispatch(self.host,dict(operation='resume',run_id=parent,rationale='original recovery'),'resume-stage')
            self.assertEqual(state(self.host)['admitted_training_stages'],10)

    def test_unknown_worker_reservation_charged_once(self):
        folder=Path(self.tmp.name)/'unknown-worker'
        folder.mkdir()
        run.write_json(folder/'state.json',dict(status='running',worker_token='t',consumed={'attempted_actions':100,'active_seconds':2.},reservation={'attempted_actions':256}))
        with patch.object(run,'worker_alive',return_value=False):
            first=run.reconcile(folder)
            second=run.reconcile(folder)
        self.assertEqual(first['consumed']['attempted_actions'],356)
        self.assertEqual(first,second)
        self.assertTrue(first['consumption_uncertain'])

    def test_verified_unused_allocation_released_without_erasing_actual(self):
        stage='terminal-fixture'
        folder=self.host.store.root/'rl'/stage
        folder.mkdir(parents=True)
        consumed={'attempted_actions':512,'active_seconds':3.}
        run.write_json(folder/'state.json',dict(status='stopped',worker_token=None,consumed=consumed,reservation={},consumption_uncertain=False))
        update(self.host,rl_runs={stage:dict(allocation={'actions':4096,'active_seconds':None},active_reservation={'actions':4096},evaluations=0)})
        rl.reconcile(self.host,stage,lightweight=True)
        first=state(self.host)
        self.assertIsNone(first['rl_runs'][stage]['active_reservation'])
        rl.reconcile(self.host,stage,lightweight=True)
        self.assertEqual(state(self.host)['numerical_s'],first['numerical_s'])
        self.assertEqual(state(self.host)['rl_runs'][stage]['status']['consumed'],consumed)

    def test_publication_requires_pointer_original_hash_and_stage_schedule(self):
        folder=Path(self.tmp.name)/'checkpoints-fixture'
        destination=folder/'checkpoints'/'exact'
        destination.mkdir(parents=True)
        cfg={'budget':{'actions':1024}}
        (destination/'policy.zip').write_bytes(b'fixture bytes; never loaded as weights')
        metadata=dict(config_sha256=config_digest(cfg),policy_file_sha256=hashlib.sha256((destination/'policy.zip').read_bytes()).hexdigest(),inherited=dict(num_timesteps=512,schedule=dict(total_timesteps=1024,progress_remaining=.5)))
        run.write_json(destination/'metadata.json',metadata)
        run.write_json(folder/'checkpoint.json',{'current':None,'previous':None})
        with self.assertRaisesRegex(ValueError,'NOT_PUBLISHED'):
            published_checkpoint(folder,cfg,'exact')
        run.write_json(folder/'checkpoint.json',{'current':'exact','previous':None})
        published_checkpoint(folder,cfg,'exact')
        with self.assertRaisesRegex(ValueError,'SOURCE_CONFIGURATION'):
            published_checkpoint(folder,{'budget':{'actions':2048}},'exact')
        (destination/'policy.zip').write_bytes(b'partial')
        with self.assertRaisesRegex(ValueError,'PARTIAL_OR_CHANGED'):
            published_checkpoint(folder,cfg,'exact')

    def test_continuation_rejects_architecture_but_permits_supported_changes(self):
        source={**deepcopy(self.spec['control']['rl_defaults']),**{k: {'identity':k} for k in ('candidate','control_object','task')}}
        changed=deepcopy(source)
        changed['ppo'].update(learning_rate={'kind':'linear','initial':.001,'final':.0001},n_steps=512,batch_size=128,n_epochs=2,ent_coef=.01)
        validate_compatibility(source,changed)
        changed['ppo']['policy_kwargs']['net_arch']['pi']=[16]
        with self.assertRaisesRegex(ValueError,'INITIALIZATION_ONLY'):
            validate_compatibility(source,changed)

    def test_fresh_pass_blocks_queued_science_and_search(self):
        value=self.host.store.artifact(self.result)
        value['acceptance']['metrics']=dict(terminal_error_m=.003,holding_max_error_m=.004,holding_max_speed_m_s=.01)
        reference=save(self.host,value)
        update(self.host,results=[reference],freeze='fixture')
        observe_pass(self.host,reference)
        self.assertEqual(state(self.host)['success_gate']['evidence'],reference)
        self.assertTrue(protected(self.host))
        from tools.research.state import guard
        with self.assertRaisesRegex(ValueError,'FRESH_TASK_PASS'):
            guard(self.host,True)
        with patch('tools.research.execution.verify_candidate') as dispatch:
            with self.assertRaisesRegex(ValueError,'FRESH_TASK_PASS'):
                core.execute(self.host,self.candidate,'queued')
            dispatch.assert_not_called()
        # Selection still requires a public read despite the persisted pass.
        from tools.research.feedback import eligibility
        self.assertFalse(eligibility(self.host,reference)['eligible'])
        self.assertEqual(state(self.host)['spec']['confirmation']['fresh_independent_repetitions'],0)

    def test_large_elapsed_cost_preserves_count_admission(self):
        row,_=self.host.store.reserve(self.host.run_id,'large-elapsed','fixture',self.host.actor,{**zero(),'tool_calls':1})
        self.host.store.complete(row,dict(request_id='large-elapsed',execution_id=row['execution_id'],caller=self.host.actor,tool_id='fixture',tool_version='1.0.0',execution_status='completed',charged=zero()),{},elapsed=1e12)
        self.assertIsNone(self.host.store.remaining()['remaining']['wall_s'])
        self.assertEqual(self.host.store.remaining()['used']['wall_s'],1e12)
        self.host.store.reserve(self.host.run_id,'next','fixture',self.host.actor,{**zero(),'tool_calls':1})

    def test_readonly_cli_never_resolves_sources(self):
        from tools.research import __main__ as cli
        s=state(self.host)
        s['spec']['runtime']['rl_python']='Z:/missing/python.exe'
        update(self.host,spec=s['spec'])
        with patch('tools.research.config.resolve',side_effect=AssertionError('source resolution forbidden')), \
             patch.object(cli,'Host',return_value=self.host), patch('sys.argv',['research','status','--run-id',self.host.run_id]), \
             patch('sys.stdout',new_callable=io.StringIO) as stream:
            cli.main()
        self.assertEqual(json.loads(stream.getvalue())['specification']['runtime']['rl_python'],'Z:/missing/python.exe')

    def test_host_disabled_allowance_accepts_completed_large_elapsed(self):
        from tools.platform_host import Host
        from tools.platform_registry import Registry, Extension
        from schemas.common import Contract
        class Empty(Contract):
            pass
        cfg=deepcopy(self.cfg)
        cfg['policy'].update(allowed_tools=['fixture.work'],tool_bindings={'fixture.work':'1.0.0'},
            operation_allowances={'fixture.work':dict(timeout_s=None,reserve_s=None)})
        with self.host.store.transaction() as db:
            snapshot=self.host.store.put(db,dict(input=cfg,input_identity='fixture'))
            db.execute('UPDATE sessions SET snapshot=?,status=? WHERE run_id=?',(snapshot.artifact_id,'running',self.host.run_id))
        definition=Extension('fixture.work','tool','1.0.0',Empty,Empty,'tools.platform_tools:read_evidence','fixture')
        host=Host(self.host.store.root,self.host.run_id,actor='fixture',reg=Registry([definition]))
        host.folder.mkdir(parents=True)
        with patch.object(host,'compatibility',return_value={'compatible':True}), \
             patch.object(host.reg,'inspect',return_value={'executable':True}), \
             patch.object(Extension,'resolve',return_value=lambda ctx,args: Empty()), \
             patch('tools.platform_host.time.monotonic',side_effect=[0.,1e12]):
            result=host.invoke(dict(request_id='host-null',tool_id='fixture.work',tool_version='1.0.0',arguments={},reason='fixture'))
        self.assertEqual(result['execution_status'],'completed',result)
        self.assertEqual(result['charged']['wall_s'],1e12)

    def test_search_stops_before_second_candidate_on_backend_pass(self):
        from tools.research.search import run_search
        value=self.host.store.artifact(self.result)
        value['operation_key']='other-operation'
        value['acceptance']['metrics']=dict(terminal_error_m=.003,holding_max_error_m=.004,holding_max_speed_m_s=.01)
        reference=save(self.host,value)
        update(self.host,results=[reference],searches={})
        query=dict(variables=['holding_tip_speed_weight'],bounds={'holding_tip_speed_weight':[.025,.10]},
            fixed=self.spec['reference_parameters'],evaluation_mode='backend_task',objective='joint_reach_hold',
            operating_point='target_equilibrium',protocol=self.spec['analysis_protocol'],scoring_window_s=.35,max_evaluations=2)
        def execute(*args,**kwargs):
            observe_pass(self.host,reference)
            return {'reference':reference}
        with patch('tools.research.search.construct',return_value=self.candidate), \
             patch('tools.research.search.verify_candidate',return_value=self.host.store.artifact(self.candidate)), \
             patch('tools.research.search.rank',return_value=(0,0,0)), \
             patch('tools.research.search.time.time',return_value=1.):
            result=run_search(self.host,query,'search-pass',guard=lambda *a:None,execute=execute,capacity=lambda *a:{'admitted':2})
        self.assertEqual(len(result['result']['evaluated']),1)
        self.assertEqual(result['result']['termination_reason'],'fresh_task_pass_requires_closeout')

    def test_source_edits_do_not_change_prepared_execution_export_or_recovery(self):
        from uuid import uuid4
        from tools.research.config import resolve
        folder=Path(self.tmp.name)/'editable'
        folder.mkdir()
        root=json.loads((ROOT/'configs/research/study.json').read_text())
        for key,path in (('robot','configs/research/robot.json'),('task','tasks/reach_hold.json'),
                         ('runtime','configs/research/runtime.json'),('control','configs/research/control.json')):
            (folder/(key+'.json')).write_bytes((ROOT/path).read_bytes())
            root[key]=key+'.json'
        root['study_id']='frozen-'+uuid4().hex
        (folder/'study.json').write_text(json.dumps(root))
        h=core.prepare(folder/'study.json',directory=folder/'owned')
        frozen=deepcopy(state(h)['spec'])
        for source in folder.glob('*.json'):
            source.write_text('invalid mutable source')
        update(h,freeze='fixture')
        with patch('tools.research.config.resolve',side_effect=AssertionError('frozen commands must not resolve source')):
            self.assertEqual(core.packet(h)['specification'],frozen)
            core.export(h,destination=folder/'export')
            core.recover(h)
            request=dict(operation='start',candidate=state(h)['reference_candidate'],rationale='frozen fixture')
            with patch('tools.research.state.guard'),patch.object(rl,'invoke',return_value={'status':'starting'}):
                output=rl.dispatch(h,request,'frozen-start')
            effective=h.store.artifact(output['effective_configuration'])
        self.assertEqual(effective['ppo'],frozen['control']['rl_defaults']['ppo'])
        self.assertEqual(effective['budget']['actions'],frozen['control']['rl_defaults']['budget']['actions'])
        self.assertEqual(effective['task']['original'],frozen['configuration']['task'])

    def test_resume_rejects_changed_settings_without_admission(self):
        from tools.research.contracts import RLRequest
        with self.assertRaisesRegex(ValueError,'RETAIN_FROZEN'):
            RLRequest(operation='resume',run_id='existing',training_overrides={'learning_rate':.001},rationale='fixture')

    def test_boot_failure_retains_admitted_stage_and_no_policy_performance(self):
        update(self.host,rl_runs={},freeze='fixture')
        cfg=deepcopy(self.spec['control']['rl_defaults'])
        cfg['requested_allocation']=deepcopy(cfg['budget'])
        with patch('tools.research.state.guard'), \
             patch.object(rl,'prepare_input',return_value=(cfg,state(self.host)['rl_task'])), \
             patch.object(rl,'invoke',side_effect=RuntimeError('fixture dependency boot failure')):
            with self.assertRaisesRegex(RuntimeError,'dependency boot'):
                rl.dispatch(self.host,dict(operation='start',candidate=self.candidate,mode='direct',allocation={'actions':2048},rationale='fixture boot'),'boot-failure')
            stage=next(iter(state(self.host)['rl_runs']))
            terminal=rl.dispatch(self.host,dict(operation='status',run_id=stage,rationale='inspect failed boot'),'boot-status')
        self.assertEqual(state(self.host)['admitted_training_stages'],1)
        self.assertIsNone(terminal['training_summary']['checkpoint'])
        self.assertEqual(terminal['task_performance'],'unmeasured')

    def test_proxy_historical_incomplete_and_reward_never_trigger_gate(self):
        edits=[dict(owning_study='historical',study='historical'),dict(status='execution_incomplete'),
            dict(status='training',reward=1e9),dict(cached_operation_receipt=True),dict(acceptance={'accepted':False})]
        for fields in edits:
            value=self.host.store.artifact(self.result)
            value['acceptance']['metrics']=dict(terminal_error_m=.003,holding_max_error_m=.004,holding_max_speed_m_s=.01)
            value.update(fields)
            reference=save(self.host,value)
            update(self.host,results=[reference])
            observe_pass(self.host,reference)
            self.assertNotIn('success_gate',state(self.host))

    def test_complete_failed_nmpc_reference_stays_available_for_same_candidate(self):
        from extensions.tendon_family import backends,scene,control_evidence
        order=[t['id'] for t in self.cfg['robot']['structure']['data']['tendons']]
        value=self.host.store.artifact(self.result)
        value.update(acceptance={'accepted':False},execution={'receipts':{'simulation':{'execution_id':'source'}}})
        update(self.host,results=[save(self.host,value)])
        source={'configuration':self.cfg,'metadata':{'artifact_id':save(self.host,{'solver_status':'completed'})['artifact_id']}}
        observations=[dict(time_s=k*.01,actual_tension_n=[.2]*6) for k in range(35)]
        with patch.object(backends,'physics_for',return_value={'tendons':[dict(entity=t) for t in order]}), \
             patch.object(scene,'assemble',return_value={'task_identity':'fixture'}), \
             patch.object(control_evidence.ControlEvidence,'resolve',return_value=source), \
             patch.object(control_evidence.ControlEvidence,'read_file',return_value=observations):
            reference=rl.compatible_references(self.host)[0]
        self.assertTrue(reference['available'])
        self.assertEqual(reference['candidate'],self.candidate)
        self.assertEqual(reference['source_kind'],'nmpc')

    def test_containment_disabled_wait_and_manual_owned_tree_cancellation(self):
        from tools import service_execution
        process=SimpleNamespace(wait=unittest.mock.Mock(return_value=0),pid=12345)
        with patch.object(service_execution.subprocess,'Popen',return_value=process):
            result=service_execution._run_contained(['fixture'],io.StringIO(),None)
        self.assertEqual(result.returncode,0)
        process.wait.assert_called_once_with(timeout=None)
        process.wait=unittest.mock.Mock(side_effect=[KeyboardInterrupt(),0])
        with patch.object(service_execution.subprocess,'Popen',return_value=process), \
             patch.object(service_execution,'_terminate_worker_job') as terminate:
            with self.assertRaises(KeyboardInterrupt):
                service_execution._run_contained(['fixture'],io.StringIO(),None)
            terminate.assert_called_once()


# Inheritance shares setup only; avoid discovering the mainline suite twice.
for name in list(vars(fixtures.MainlineTests)):
    if name.startswith('test_') and name not in CountContinuationTests.__dict__:
        setattr(CountContinuationTests,name,None)
