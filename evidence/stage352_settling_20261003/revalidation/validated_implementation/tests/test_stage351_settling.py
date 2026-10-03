"""Focused control-grant and feedback fixtures; no provider or numerical solves."""
from copy import deepcopy
import gc
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from schemas.platform import SessionInput,BackendResult
from tools.platform_store import Store,plain
from tools.platform_tools import _candidate
from tools.platform_registry import registry
from tools.state_io import read
from tools.diagnostic_workflow import ROOT
from tools.diagnostic_improvement import actual_diff,prepare_improvement,complete_execution
from tools.improvement_workflow import execution_host,BASELINE_LIMITS
from tools.settling_campaign import control_grant,SettlingWorkflow,compare_results,campaign_metrics
from tools.diagnostic_native import FlatDiagnosticAdapter
from extensions.tendon_family.candidate import REACH_WEIGHT_PATHS,candidate_facts
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.diagnostic_evidence import selected_ranges
from extensions.tendon_family.backends import MujocoBackend
from tests.test_shared_diagnosis import native


class SettlingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=read(ROOT/'examples/stage351_experiment.json')
        cls.source_store=Store(cls.config['source_store'])
        cls.source=ControlEvidence(cls.source_store).resolve(cls.config['execution_id'])
        cls.effective=control_grant(cls.source['configuration'])

    def test_exact_paths_grants_and_frozen_science(self):
        inp=SessionInput.model_validate(self.effective)
        self.assertEqual(inp.robot.model_dump(),SessionInput.model_validate(self.source['configuration']).robot.model_dump())
        self.assertEqual(inp.policy.controller,SessionInput.model_validate(self.source['configuration']).policy.controller)
        changes=dict(zip(REACH_WEIGHT_PATHS,[.0001,1.]))
        changed=_candidate(inp,changes,registry());diff=actual_diff(plain(inp),plain(changed))
        self.assertEqual({r['pointer'] for r in diff},{'/policy/controller/parameters/data/'+p.removeprefix('control/') for p in changes})
        facts=candidate_facts(inp,plain(changed),{'artifact_id':'fixture','media_type':'application/json'},'fixture')
        self.assertEqual({p['path']:p['effective_value'] for p in facts['parameters']},changes)
        for change in [{'components/near/length_m':.16},{'control/recipe/horizon':8},
                {REACH_WEIGHT_PATHS[0]:.00001},{REACH_WEIGHT_PATHS[0]:1.01},{REACH_WEIGHT_PATHS[0]:True}]:
            with self.subTest(change=change),self.assertRaises(ValueError):_candidate(inp,change,registry())
        absent=inp.model_copy(deep=True);absent.policy.editable.clear()
        with self.assertRaisesRegex(ValueError,'PARAMETER_NOT_AUTHORIZED'):_candidate(absent,changes,registry())

    def test_summary_coverage_joint_success_and_tradeoff(self):
        rows=[{'speed':.64},{'speed':1.581},{'speed':1.48}]
        result=selected_ranges(rows,['speed'],coverage={'times':[.30,.31,.35]},references=[{'artifact_id':'source'}])
        self.assertEqual(result['ranges']['speed'],dict(count=3,minimum=.64,maximum=1.581))
        facts=read(ROOT/'runs/stage350_physical_pilot_20261003/baseline/outcome.json')['result']['factual_result']
        self.assertFalse(campaign_metrics(facts)['joint_reach_holding_passed'])
        changed=deepcopy(facts);changed['sampled_settling']['max_speed_m_s']=.01;changed['terminal_error_m']=.015
        self.assertEqual(compare_results(facts,changed)['classification'],'physical_tradeoff')
        changed['terminal_error_m']=.005;changed['sampled_settling']['max_error_m']=.009
        self.assertTrue(campaign_metrics(changed)['joint_reach_holding_passed'])
        self.assertEqual(compare_results(facts,changed)['classification'],'joint_acceptance_gained')

    def test_changed_recipe_execution_and_feedback_both_memories(self):
        temp=TemporaryDirectory(dir=ROOT/'runs')
        try:
            source=self.source;source_store=self.source_store;compiled=[]
            def fake_backend(backend,folder,timeout_s):
                folder.mkdir(parents=True)
                for name,ref in source['files'].items():(folder/name).write_bytes(source_store.artifact(ref,raw=True))
                return BackendResult.model_validate(source_store.artifact(dict(artifact_id=source['metadata']['artifact_id'],media_type='application/json')))
            def compile_backend(backend,inp,reg):compiled.append(plain(inp))
            with patch('extensions.tendon_family.gvs_profile.prepare_execution'),patch.object(MujocoBackend,'compile',compile_backend),\
                    patch.object(MujocoBackend,'initialize'),patch.object(MujocoBackend,'run',fake_backend),patch.object(MujocoBackend,'close'):
                baseline_store=Store(Path(temp.name)/'baseline')
                fixture_id='fixture351-'+uuid4().hex
                baseline_store.create(dict(project_id=fixture_id,grant_id=fixture_id,budget=BASELINE_LIMITS,authorization_source='Offline fixture'))
                executor=execution_host(baseline_store,'baseline-fixture',self.effective,BASELINE_LIMITS)
                original=complete_execution(executor,self.effective,'fixture-baseline')
                manifest=ControlEvidence(baseline_store).resolve(original['execution_id'])['manifest']
                for mode in ('single_context','dual_context'):
                    with self.subTest(mode=mode):
                        config={**self.config,'source_store':str(baseline_store.root),'execution_id':original['execution_id'],
                            'source_manifest':manifest,'evidence_directory':str(Path(temp.name)/'export'),'baseline_facts':original['factual_result']}
                        w=SettlingWorkflow(Path(temp.name)/mode,mode,experiment=config);w.prepare(dict(test_fixture=True))
                        def respond(adapter,payload,turn):
                            self.assertLessEqual(len(json.dumps(payload).encode()),200000)
                            role=json.loads(payload['messages'][1]['content'])['role_context'];phase=role['phase']
                            if phase=='request':return native('diagnosis.request',dict(question='Fixture question',scope=['Read baseline'],stopping_conditions=['Final delivery']))
                            if phase=='initial' and not role.get('evidence_views'):
                                result=native('diagnosis.inspect_evidence',dict(view='prediction'))
                                result['choices'][0]['message']['tool_calls']+=native('diagnosis.inspect_evidence',dict(view='motion'))['choices'][0]['message']['tool_calls'];return result
                            if phase in ('initial','revision'):
                                feedback=role.get('check_feedback',[]);ref=feedback[0]['result'] if feedback else w.summary
                                pointer='/detail/terminal_error_m' if feedback else '/detail/summary/terminal_error_m'
                                handle=next(k for k,v in w.store.session(role['memory_identity'])['state']['fact_catalog'].items()
                                    if v['selector']['reference']==ref and v['selector']['pointer']==pointer)
                                return native('diagnosis.submit',dict(report=dict(subject='control',facts=[dict(fact_id='f',statement='Fixture value only')],
                                    attribution=[dict(cause='unresolved',status='insufficient_evidence',fact_ids=['f'],reason='No scientific inference from fixture')],
                                    limitations=['Historical backend bytes are a fixture, not a new experiment.']),fact_handles={'f':[handle]},missing_evidence=[],recommendations=[]))
                            if phase=='improvement':
                                schema=next(t['function']['parameters'] for t in payload['tools'] if t['function']['name']=='design_decide_improvement')
                                self.assertEqual(set(schema['properties']['changes']['properties']),set(REACH_WEIGHT_PATHS))
                                return native('design.decide_improvement',dict(disposition='adopt',changes={REACH_WEIGHT_PATHS[0]:.01},
                                    rationale='Fixture delta',expected_measurable_effect='No scientific claim'))
                            self.assertIsNotNone(role['improvement_feedback_content']['campaign_comparison'])
                            return native('design.respond_diagnosis',dict(disposition='defer',reasoning='Fixture delivery',next_action='finish'))
                        with patch.object(FlatDiagnosticAdapter,'respond',respond):outcome=w.run()
                        self.assertEqual(outcome['status'],'completed',outcome['stop_reason'])
                        self.assertTrue(outcome['feedback_complete'])
                        self.assertEqual(outcome['usage']['used']['backend_solves'],1)
                        self.assertEqual(compiled[-1]['policy']['controller']['parameters']['data']['recipe']['terminal_tip_speed_weight'],.01)
                        self.assertEqual(compiled[-1]['robot'],self.effective['robot']);self.assertEqual(compiled[-1]['task'],self.effective['task'])
                        self.assertEqual(w.complete_result['preparation_configuration'],plain(w.preparation.configuration))
                        self.assertEqual(w.complete_result['source_report'],w.chain['initial_report'])
                        with self.assertRaisesRegex(ValueError,'EFFECTIVE_CHANGE_REQUIRED'):
                            prepare_improvement(w.host('design'),w.chain['initial_report'],dict(disposition='adopt',changes={REACH_WEIGHT_PATHS[0]:0.},rationale='fixture',expected_measurable_effect='none'))
                        with self.assertRaisesRegex(ValueError,'PARAMETER_NOT_AUTHORIZED'):
                            prepare_improvement(w.host('design'),w.chain['initial_report'],dict(disposition='adopt',changes={'components/near/length_m':.16},rationale='fixture',expected_measurable_effect='none'))
        finally:gc.collect();temp.cleanup()
