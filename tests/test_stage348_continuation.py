"""Focused continuation/provenance and builder seam fixtures, not live science."""
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from tests import test_shared_diagnosis as fixtures
from tools.diagnostic_workflow import DiagnosticWorkflow, ROOT, SUFFIX_LIMITS, save
from tools.diagnostic_native import FlatDiagnosticAdapter
from tools.state_io import read


native=fixtures.native


class Stage348Tests(TestCase):
    setUp=fixtures.SharedWorkflowTests.setUp
    cleanup=fixtures.SharedWorkflowTests.cleanup
    workflow=fixtures.SharedWorkflowTests.workflow
    def test_suffix_uses_original_feedback_and_only_two_phases(self):
        experiment=read(ROOT/'examples/stage348_experiment.json')
        experiment['evidence_directory']=str(Path(self.temp.name)/'exports')
        w=DiagnosticWorkflow(Path(self.temp.name)/'suffix','dual_context',suffix=True,experiment=experiment)
        w.prepare(dict(test_fixture=True));seen=[]
        def respond(adapter,payload,turn):
            role=json.loads(payload['messages'][1]['content'])['role_context'];seen.append(role['phase'])
            if role['phase']=='response_final':
                return native('design.respond_diagnosis',dict(disposition='defer',reasoning='Fixture: local result leaves closed-loop effects unresolved.',next_action='finish'))
            ref=role['check_feedback'][0]['result']
            # Reuse a preserved submitted selector, not a hand-authored result.
            raw=read(ROOT/'evidence/stage347_diagnostic_development_20261002/pilot_v4/resolved_calls.json')
            submitted=next(r['invocation']['arguments'] for r in raw if r['invocation'].get('tool_id')=='diagnosis.submit' and r['invocation']['arguments'].get('previous_report'))
            submitted={k:v for k,v in submitted.items() if k not in ('request','previous_report','check_results')}
            self.assertTrue(any(s['reference']==ref for ss in submitted['fact_selectors'].values() for s in ss))
            return native('diagnosis.submit',submitted)
        with patch.object(FlatDiagnosticAdapter,'respond',respond),patch('tools.diagnostic_workflow.execute_check_feedback',side_effect=AssertionError('no new check')):
            outcome=w.run()
        self.assertEqual(outcome['status'],'completed',outcome['stop_reason'])
        self.assertEqual(seen,['revision','response_final'])
        self.assertEqual(outcome['usage']['limit'],SUFFIX_LIMITS)
        self.assertEqual(outcome['numerical_work']['used'],dict(local_solves=0,prediction_evaluations=0))
        self.assertEqual(w.chain['feedback'],experiment['continuation_feedback'])
        self.assertEqual(w.store.artifact(w.chain['feedback'])['receipt']['execution_id'],experiment['continuation_execution'])
        self.assertEqual(w.store.artifact(w.chain['revised_report'])['check_results'],[w.chain['feedback']])
        with self.assertRaisesRegex(RuntimeError,'LIVE_ATTEMPT_ALREADY_STARTED'):w.run()

    def test_bridge_passes_fixture_delta_to_registered_builder(self):
        from examples.gvs_design_input import multiphysics_input
        from tools.diagnostic_improvement import prepare_improvement
        from tools.platform_store import plain
        w=self.workflow();h=w.host('diagnostic')
        baseline=multiphysics_input('fixture-only')
        configuration=save(w.store,dict(effective=baseline))
        binding=save(w.store,dict(configuration=configuration,execution_id='fixture-source'))
        report=save(w.store,dict(report=dict(source=binding)))
        with w.store.transaction() as db:
            state=w.store.session(h.run_id,db)['state'];state['handoff_history']=[dict(kind='diagnosis_report',reference=report)]
            w.store.update_state(db,h.run_id,state)
        before=w.store.remaining()['used']
        decision=dict(disposition='adopt',changes={'components/near/length_m':.162},rationale='Fixture delta',expected_measurable_effect='Fixture hypothesis only')
        prepared=prepare_improvement(h,report,decision)
        self.assertEqual(prepared.status,'prepared_no_execution');self.assertEqual(prepared.source_execution,'fixture-source')
        candidate=w.store.artifact(prepared.configuration)
        self.assertEqual(candidate['sources']['source_report'],report['artifact_id'])
        self.assertEqual(candidate['effective']['task'],baseline['task'])
        self.assertTrue(prepared.actual_diff);self.assertIsNone(prepared.execution_receipt)
        self.assertEqual(w.store.remaining()['used'],before)
        with self.assertRaisesRegex(ValueError,'PARAMETER_NOT_AUTHORIZED'):
            prepare_improvement(h,report,{**decision,'changes':{'invented':1}})
