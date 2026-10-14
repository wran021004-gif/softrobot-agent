"""Focused boundary fixtures; no new mathematical solve or complete episode."""
from copy import deepcopy
from pathlib import Path
import json,subprocess,tempfile,time,unittest
from types import SimpleNamespace
from unittest.mock import patch
from schemas.platform import ProjectConfig
from tools.platform_store import Store,plain,zero
from tools.state_io import digest
from tools.research.config import resolve,ROOT
from tools.research.design import full_science
from tools.research.state import state,update,save
from tools.research import core,feedback,analysis,rl
from tools.research.contracts import Search


class MainlineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.spec=resolve(ROOT/'configs/research/study.json');self.cfg=deepcopy(self.spec['configuration'])
        self.host=SimpleNamespace(store=Store(Path(self.tmp.name)),run_id=self.cfg['run_id'],actor='fixture')
        fixture_id=Path(self.tmp.name).name
        self.host.store.create(ProjectConfig(project_id=fixture_id,grant_id=fixture_id,authorization_source='code-only fixture',budget=self.cfg['policy']['budget']))
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

    def test_explicit_score_window_and_mixed_control_capability(self):
        p=self.spec['reference_parameters'];q=dict(variables=['segments.near.length_m'],bounds={'segments.near.length_m':[.152,.168]},
            fixed=p,objective='held_position_min_eigenvalue',operating_point='target_equilibrium',protocol=self.spec['analysis_protocol'],scoring_window_s=.35,max_evaluations=2)
        self.assertEqual(Search.model_validate(q).scoring_window_s,.35)
        q.update(variables=['holding_tip_speed_weight'],bounds={'holding_tip_speed_weight':[.025,.10]})
        with self.assertRaisesRegex(ValueError,'CONTROL_VARIABLES_REQUIRE_BACKEND'):Search.model_validate(q)
        metadata=analysis.score_semantics(SimpleNamespace(scoring_window_s=.35),dict(candidate_id='fixture'),SimpleNamespace(input_scale_n=8,output_scale_m=.01),{})
        self.assertIn('held input',metadata['held_position_min_eigenvalue']['supported_interpretation'])
        self.assertIn('damping margin or decay rate',metadata['held_position_min_eigenvalue']['unsupported_conclusions'])

    def test_rl_hard_cap_remaining_time_and_environment(self):
        runtime=self.spec['runtime'];update(self.host,rl_runs={},spec=self.spec,numerical_s=self.spec['budgets']['numerical_s']-119)
        self.assertEqual(rl.evaluation_capacity(self.host)['admitted'],0)
        with patch.object(rl.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{}')) as invoked:
            rl.invoke(self.host,'evaluate','fixture',deadline=time.time()+1000,timeout_s=17)
        args=invoked.call_args
        self.assertEqual(args.args[0][0],runtime['rl_python']);self.assertLessEqual(args.kwargs['timeout'],17)
        self.assertEqual(args.kwargs['env']['OPENBLAS_NUM_THREADS'],'1')
        self.assertIn('SOFTROBOT_RL_RUNS',args.kwargs['env'])

    def test_tracked_file_inventory_and_import_closure(self):
        files=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
        banned=['tools/nmpc_settling.py','tools/research_v2.py','tools/strands_pilot.py','tools/strands_pilot_r3.py','schemas/research_core.py','tools/design_optimization.py']
        self.assertFalse(set(files)&set(banned))
        self.assertFalse(any(p.startswith(('examples/','tools/legacy/','archive/','legacy/')) for p in files))
        from tools.research import agent
        from tools.platform_registry import registry
        registered=registry();self.assertIsNotNone(registered.get('controller.gvs_nmpc','11.0.0'))
        import sys
        self.assertFalse(any(p[:-3].replace('/','.') in sys.modules for p in banned))


if __name__=='__main__':unittest.main()
