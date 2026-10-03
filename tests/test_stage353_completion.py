"""Saved-case continuation, accounting boundaries and required context retention."""
from copy import deepcopy
import gc
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from schemas.platform import ModelInput,BackendResult
from tools.platform_store import Store,zero,encode
from tools.state_io import read,digest
from tools.improvement_workflow import execution_host
from tools.execution_completion import complete_execution,import_completed_simulation,structured_feedback
from tools.platform_diagnosis_coordinator import configure_role
from tools.diagnostic_native import BoundSavedStateAdapter
from tools.diagnostic_workflow import ROOT
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.backends import MujocoBackend


class CompletionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=read(ROOT/'examples/stage353_experiment.json')
        cls.source_store=Store(cls.config['historical_store'])
        cls.source=ControlEvidence(cls.source_store).resolve(cls.config['historical_execution'])

    def setUp(self):
        self.temp=TemporaryDirectory(dir=ROOT/'runs')
        self.addCleanup(self.cleanup)

    def cleanup(self):
        gc.collect();self.temp.cleanup()

    def host(self,wall=1600.,backend=0):
        identity='fixture-'+uuid4().hex[:12];store=Store(Path(self.temp.name)/identity)
        budget=dict(tool_calls=10,model_calls=0,backend_solves=backend,worker_calls=0,wall_s=wall)
        store.create(dict(project_id=identity,grant_id=identity,budget=budget,authorization_source='Offline saved-data test fixture'))
        return execution_host(store,identity,self.source['configuration'],budget,operation_allowances=self.config['operation_allowances'])

    def imported(self,**kwargs):
        host=self.host(**kwargs);import_completed_simulation(host,self.source_store,self.source['execution_id']);return host

    def complete(self,host,**kwargs):
        return complete_execution(host,self.source['configuration'],self.source['metadata']['candidate'],**kwargs)

    def test_continuation_after_simulation_evaluation_and_repeat(self):
        host=self.imported();before=host.store.remaining()['used']
        with patch.object(MujocoBackend,'run',side_effect=AssertionError('No simulation on continuation')):
            stopped=self.complete(host,stop_after='simulation')
            self.assertEqual(stopped['completed_stage'],'simulation');self.assertEqual(host.store.remaining()['used'],before)
            stopped=self.complete(host,stop_after='evaluation')
            after_eval=host.store.remaining()['used'];self.assertEqual(after_eval['tool_calls'],before['tool_calls']+1)
            result=self.complete(host);after=host.store.remaining()['used']
            self.assertEqual(result['status'],'evaluated');self.assertEqual(after['tool_calls'],after_eval['tool_calls']+1)
            self.assertEqual(self.complete(host),result);self.assertEqual(host.store.remaining()['used'],after)
            import_completed_simulation(host,self.source_store,self.source['execution_id'])
            self.assertEqual(host.store.remaining()['used'],after)
        self.assertEqual(after['backend_solves'],0)
        self.assertEqual(result['structured_feedback']['actual_applied_control_updates'],35)
        self.assertEqual(result['structured_feedback']['holding']['sample_count'],6)
        self.assertEqual(result['evaluation_data']['evaluator_version'],'1.0.0')
        self.assertAlmostEqual(result['factual_result']['terminal_error_m'],.01775855176510572)
        self.assertEqual(result['design_statement']['owner_run_id'],self.source['owner'])

    def test_historical_boundary_and_real_insufficient_budget(self):
        for cost,success in [(702.766,True),(1590.,False)]:
            with self.subTest(cost=cost):
                host=self.imported();host.resume()
                configure_role(host,'executor','Accounting boundary fixture',phase_budget=dict(limit=dict(tool_calls=5,wall_s=1600.)))
                row,_=host.store.reserve(host.run_id,'fixture-prior-work','fixture',host.actor,{**zero(),'wall_s':1.})
                host.store.complete(row,dict(request_id='fixture-prior-work',execution_id=row['execution_id'],caller=host.actor,
                    tool_id='fixture.prior_work',tool_version='1.0.0',execution_status='completed',charged=zero()),elapsed=cost)
                result=self.complete(host)
                self.assertEqual(result['status']=='evaluated',success)
                if not success:
                    self.assertIn('BUDGET_EXHAUSTED',result['receipts']['evaluation']['error'])
                    self.assertIsNone(host.store.lookup(host.run_id,'complete-evaluation'))
                else:
                    for request,reserve in [('complete-evaluation',30.),('complete-profile',60.)]:
                        row=host.store.lookup(host.run_id,request);self.assertEqual(json.loads(row['reserved'])['wall_s'],reserve)

    def test_unknown_artifacts_do_not_authorize_reexecution(self):
        host=self.host(backend=1);host.resume()
        row,_=host.store.reserve(host.run_id,'complete-simulation','fixture',host.actor,{**zero(),'backend_solves':1,'tool_calls':1,'wall_s':900.})
        with host.store.transaction() as db:
            host.store.event(db,host.run_id,'simulation','completed',execution=row['execution_id'],outputs=[host.store.put(db,{'fixture':'unsealed'})])
        before=host.store.remaining()['used']
        with patch.object(MujocoBackend,'run',side_effect=AssertionError('Uncertain work must not replay')):
            result=self.complete(host)
        self.assertEqual(result['status'],'execution_unresolved');self.assertTrue(result['retained_evidence'])
        self.assertEqual(host.store.remaining()['used'],before)

    def test_identity_integrity_and_version_refusal(self):
        host=self.imported();self.complete(host,stop_after='simulation')
        with self.assertRaisesRegex(ValueError,'IDENTITY_MISMATCH'):
            complete_execution(host,self.source['configuration'],'different-candidate')
        with patch.object(host,'compatibility',return_value={'compatible':False,'changed':['evaluation.run@1.0.0']}):
            with self.assertRaisesRegex(ValueError,'DEPENDENCIES_CHANGED'):self.complete(host)
        ref=self.source['metadata']['candidate_input']
        with host.store.transaction() as db:db.execute('UPDATE artifacts SET body=? WHERE id=?',(b'{}',ref['artifact_id']))
        with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING_OR_CHANGED'):self.complete(host)

    def test_normal_and_resumed_saved_bytes_agree(self):
        baseline=self.source['configuration'];host=self.host(backend=1)
        def replay(backend,folder,timeout_s):
            self.assertEqual(timeout_s,900.)
            folder.mkdir(parents=True)
            for name,ref in self.source['files'].items():(folder/name).write_bytes(self.source_store.artifact(ref,raw=True))
            return BackendResult.model_validate(self.source_store.artifact(dict(artifact_id=self.source['metadata']['artifact_id'],media_type='application/json')))
        with patch('extensions.tendon_family.gvs_profile.prepare_execution'),patch.object(MujocoBackend,'compile'),\
                patch.object(MujocoBackend,'initialize'),patch.object(MujocoBackend,'run',autospec=True,side_effect=replay) as run,patch.object(MujocoBackend,'close'):
            # Stop after tool receipt commit, before the stage record is written.
            from tools import execution_completion
            with patch.object(execution_completion,'source_for',side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):self.complete(host)
            result=self.complete(host);self.assertEqual(run.call_count,1)
        resumed=self.complete(self.imported())
        for key in ('terminal','holding','actual_applied_control_updates','initialization_selected','newly_optimized_selected','deadline_misses'):
            self.assertEqual(result['structured_feedback'][key],resumed['structured_feedback'][key])
        self.assertEqual(result['evaluation_data']['metrics'],resumed['evaluation_data']['metrics'])
        self.assertEqual(host.store.remaining()['used']['backend_solves'],1)

    def test_400k_context_keeps_mandatory_identity_feedback(self):
        folder=ROOT/'evidence/stage352_settling_20261003/host_repair'
        inp=ModelInput.model_validate(read(folder/'preserved_revision_model_input.json'))
        state=read(folder/'preserved_revision_fact_state.json');config=deepcopy(inp.context['policy']['model'])
        config['context_bytes']=400000
        # Near-cap retained task content, not a change to scientific measurements.
        inp.context['role_context']['instructions']+='\n'+'Retained context. '*10500
        with patch('tools.platform_store.Store') as store:
            store.return_value.session.return_value={'state':state}
            payload=BoundSavedStateAdapter().encode(inp,config)
        size=len(encode(payload).encode());self.assertGreater(size,350000);self.assertLessEqual(size,400000)
        role=json.loads(payload['messages'][1]['content'])['role_context']
        for key in ('identities','binding','instructions','check_feedback','improvement_feedback_content','previous_report_content'):
            if key in inp.context['role_context']:self.assertEqual(role[key],inp.context['role_context'][key])
        self.assertEqual(config['max_tokens'],65536)
        self.assertLess(size+8192+config['length_recovery']['max_tokens'],1000000)

    def test_stage353_configuration_prepares_both_organizations(self):
        from tools.settling_campaign import SettlingWorkflow
        from tools.platform_models import payload_for
        for mode in ('single_context','dual_context'):
            config={**self.config,'evidence_directory':str(Path(self.temp.name)/'exports')}
            w=SettlingWorkflow(Path(self.temp.name)/mode,mode,experiment=config)
            w.prepare({'test_fixture':True})
            for role in ('design','diagnostic'):
                model=w.store.session(w.host(role).run_id)['snapshot']['input']['policy']['model']
                self.assertEqual(model['context_bytes'],400000)
                self.assertEqual(model['context_guard'],config['context_guard'])
                self.assertEqual(model['parameters'],{})
            w.validate_frozen_configuration()
