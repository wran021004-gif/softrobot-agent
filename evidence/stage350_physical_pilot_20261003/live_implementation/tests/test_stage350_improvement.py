"""Focused integration fixture: scripted provider and replayed backend bytes, no live science."""
import gc
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from schemas.platform import BackendResult
from tools.platform_store import Store
from tools.state_io import read
from tools.diagnostic_workflow import ROOT, save
from tools.improvement_workflow import ImprovementWorkflow
from tools.diagnostic_improvement import prepare_improvement, transfer_accepted_report
from tools.diagnostic_native import FlatDiagnosticAdapter
from extensions.tendon_family.control_evidence import ControlEvidence
from extensions.tendon_family.backends import MujocoBackend
from tests.test_shared_diagnosis import native


class ImprovementTests(TestCase):
    def test_builder_execution_evaluation_and_explicit_provenance(self):
        temp=TemporaryDirectory(dir=ROOT/'runs')
        try:
            source_store=Store(ROOT/'runs/stage341_autonomous_20261001')
            source=ControlEvidence(source_store).resolve('5991de53e82747439e87ba8569667e1b')
            def fake_backend(backend,folder,timeout_s):
                folder.mkdir(parents=True)
                for name,ref in source['files'].items():(folder/name).write_bytes(source_store.artifact(ref,raw=True))
                return BackendResult.model_validate(source_store.artifact(dict(artifact_id=source['metadata']['artifact_id'],media_type='application/json')))
            for mode,disposition in [('single_context','adopt'),('dual_context','adopt'),('dual_context','defer')]:
                with self.subTest(mode=mode,disposition=disposition):
                    config=read(ROOT/'examples/stage350_experiment.json');config.update(evidence_directory=str(Path(temp.name)/'exports'),baseline_facts={'fixture_only':True})
                    w=ImprovementWorkflow(Path(temp.name)/(mode+disposition),mode,experiment=config);w.prepare(dict(test_fixture=True))
                    # Merely storing an apparent report cannot authorize a decision/build.
                    forged=save(w.store,dict(report=dict(source=w.binding)))
                    with self.assertRaisesRegex(ValueError,'ACCEPTED_DIAGNOSIS_REQUIRED'):
                        prepare_improvement(w.host('design'),forged,dict(disposition='defer',rationale='fixture',expected_measurable_effect='none'))
                    phases=[]
                    def respond(adapter,payload,turn):
                        self.assertLessEqual(len(json.dumps(payload).encode()),200000)
                        role=json.loads(payload['messages'][1]['content'])['role_context'];phase=role['phase'];phases.append(phase)
                        if phase=='request':return native('diagnosis.request',dict(question='Fixture question',scope=['Read retained baseline; separate geometry decision later.'],stopping_conditions=['Final decision']))
                        if phase=='initial' and not role.get('evidence_views'):
                            result=native('diagnosis.inspect_evidence',dict(view='prediction'))
                            result['choices'][0]['message']['tool_calls']+=native('diagnosis.inspect_evidence',dict(view='plans'))['choices'][0]['message']['tool_calls'];return result
                        if phase in ('initial','revision'):
                            feedback=role.get('check_feedback',[])
                            ref=feedback[0]['result'] if feedback else w.summary
                            pointer='/detail/terminal_error_m' if feedback else '/detail/summary/terminal_error_m'
                            handle=next(k for k,v in w.store.session(role['memory_identity'])['state']['fact_catalog'].items()
                                if v['selector']['reference']==ref and v['selector']['pointer']==pointer)
                            return native('diagnosis.submit',dict(report=dict(subject='control',facts=[dict(fact_id='f',statement='Fixture value only')],
                                attribution=[dict(cause='unresolved',status='insufficient_evidence',fact_ids=['f'],reason='Fixture, no scientific conclusion')],
                                limitations=['Fixture backend bytes are historical, not a new physical result.']),fact_handles={'f':[handle]},missing_evidence=[],recommendations=[]))
                        if phase=='improvement':
                            self.assertIn('design_decide_improvement',{t['function']['name'] for t in payload['tools']})
                            self.assertEqual(w.store.remaining()['used']['backend_solves'],0)
                            return native('design.decide_improvement',dict(disposition=disposition,changes={'components/near/length_m':.162} if disposition=='adopt' else {},
                                rationale='Fixture delta, not a model recommendation',expected_measurable_effect='No physical inference from fixture'))
                        return native('design.respond_diagnosis',dict(disposition='defer',reasoning='Fixture delivery; no success claim',next_action='finish'))
                    with patch.object(FlatDiagnosticAdapter,'respond',respond),patch('extensions.tendon_family.gvs_profile.prepare_execution'),\
                            patch.object(MujocoBackend,'compile'),patch.object(MujocoBackend,'initialize'),patch.object(MujocoBackend,'run',fake_backend),patch.object(MujocoBackend,'close'):
                        outcome=w.run()
                    self.assertEqual(outcome['status'],'completed',outcome['stop_reason'])
                    self.assertTrue(outcome['feedback_complete'])
                    self.assertEqual(outcome['usage']['used']['backend_solves'],int(disposition=='adopt'))
                    self.assertEqual(outcome['numerical_work']['used'],dict(local_solves=0,prediction_evaluations=0))
                    self.assertIn('revision',phases)
                    if disposition=='adopt':
                        result=w.complete_result;self.assertEqual(result['status'],'evaluated',result)
                        self.assertEqual(result['evaluation_data']['source_execution_id'],result['execution_id'])
                        self.assertEqual(result['factual_result']['configuration'],result['configuration'])
                        candidate=w.store.artifact(w.preparation.configuration)
                        self.assertEqual(candidate['effective']['task'],source['configuration']['task'])
                        self.assertEqual(candidate['effective']['policy']['controller'],source['configuration']['policy']['controller'])
                        self.assertEqual(candidate['sources']['source_report'],w.chain['initial_report']['artifact_id'])
                    with self.assertRaisesRegex(ValueError,'PARAMETER_NOT_AUTHORIZED'):
                        prepare_improvement(w.host('design'),w.chain['initial_report'],dict(disposition='adopt',changes={'control/terminal_tip_speed_weight':.1},rationale='unsupported fixture',expected_measurable_effect='none'))
                    if mode=='dual_context':
                        state=w.store.session(w.host('design').run_id)['state']
                        self.assertTrue(state['accepted_report_transfers'])
                        self.assertFalse(any(h['kind']=='diagnosis_report' for h in state.get('handoff_history',[])))
        finally:
            gc.collect();temp.cleanup()
