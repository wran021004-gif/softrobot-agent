"""Small offline regressions for existing handoff evidence projection."""
import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
from tools.research.session_handoff import feedback_delivery


class SelectedFeedbackTests(unittest.TestCase):
    def project(self, value, view='full', status='success'):
        result=dict(status=status,content=[dict(text=json.dumps(value))])
        original=dict(tool_use=dict(toolUseId='fixture-tool',name='evidence_read',
            input=dict(reference={'artifact_id':'fixture'},view=view,pointer='/diagnostic')),result=result)
        host=Mock();host.run_id='fixture'
        host.store.session.return_value=dict(state=dict(spec={}))
        host.store.events.return_value=[dict(kind='model_original_tool_feedback',outputs=['fixture-feedback'])]
        host.store.artifact.return_value=original
        delivery=feedback_delivery(host,['fixture-tool'])['items'][0]
        host.store.reserve.assert_not_called();host.store.transaction.assert_not_called()
        return delivery

    def test_large_selected_object_retains_scalars_and_small_metrics(self):
        value=dict(J=.125,initial_J=.25,stop_reason='fixture_iteration_limit',
            best_metrics=dict(error_m=.01),large_array=[dict(values=list(range(500)))]*8,
            task_acceptance='unmeasured')
        row=self.project(value)
        self.assertEqual(row['delivery'],'summary_only')
        facts=row['facts'];shown=facts['selected_value']
        self.assertEqual(shown['J'],value['J'])
        self.assertEqual(shown['stop_reason'],value['stop_reason'])
        self.assertEqual(shown['best_metrics'],value['best_metrics'])
        self.assertIn('large_array',facts['omitted_keys'])
        self.assertLessEqual(len(json.dumps(facts).encode()),3000)

    def test_summary_keeps_preview_semantics_and_small_feedback_stays_exact(self):
        value=dict(value=dict(J=.125,large_array=[dict(values=list(range(500)))]*8),
            reference={'artifact_id':'fixture'},view='deterministic_summary')
        facts=self.project(value,'summary')['facts']
        self.assertEqual(facts['selected_value']['J'],.125)
        self.assertIn('preview semantics',facts['scope'])
        self.assertEqual(self.project(dict(J=.125))['delivery'],'exact_feedback')

    def test_large_error_keeps_original_reason_expectation_and_input(self):
        error=dict(status='rejected',error_code='fixture_window',field='window',
            reason='Actual window starts at 1; state is at 0.',expected='Cover [0, task duration].',
            evidence_navigation=dict(large_details=list(range(5000))))
        row=self.project(error,status='error')
        self.assertEqual(row['facts']['reason'],error['reason'])
        self.assertEqual(row['facts']['expected'],error['expected'])
        self.assertEqual(row['query']['pointer'],'/diagnostic')

    def test_exact_static_read_reuses_projection_but_preserves_full_data(self):
        from unittest.mock import patch
        from tests.research.test_research_reporting import offline_host, ref
        from tools.research import core
        value=dict(metrics=dict(J=.125),samples=list(range(40)))
        reference=ref(value);values={reference['artifact_id']:value}
        host,current=offline_host(values,physical_replays=[reference])
        q=dict(reference=reference,view='full',pointer='')
        def update(h,**fields):current.update(fields)
        with patch.object(core,'update',side_effect=update):
            first=core.read_evidence(host,q,record_read=False)
            self.assertEqual(current['evaluation_reads'],[])
            # A public cache hit must still record the public read marker.
            second=core.read_evidence(host,q)
            self.assertEqual(first,second);self.assertIn(reference,current['evaluation_reads'])
            second['metrics']['J']=999
            self.assertEqual(core.read_evidence(host,q)['metrics']['J'],.125)
            self.assertEqual(core.read_evidence(host,{**q,'pointer':'/samples','view':'range','count':2})['items'],[0,1])
            self.assertEqual(core.read_evidence(host,{**q,'view':'fields','fields':['metrics']}),dict(metrics=value['metrics']))
            changed=dict(metrics=dict(J=.25));version=ref(changed);values[version['artifact_id']]=changed
            self.assertEqual(core.read_evidence(host,{**q,'reference':version})['metrics']['J'],.25)
            host.store.artifact.side_effect=ValueError('EVIDENCE_MISSING_OR_CHANGED')
            with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING_OR_CHANGED'):core.read_evidence(host,q)

    def test_report_projection_preserves_unresolved_and_weakened_interpretations(self):
        from tools.research.research_context import compact_scientific_delivery
        findings=[dict(kind=k,text='Fixture scoped interpretation',sources=[])
            for k in ('hypothesis','unresolved_question','further_investigation')]
        brief=dict(latest_reports=[dict(interpretations=findings,findings=[])])
        shown=compact_scientific_delivery(brief,decision_only=True)
        self.assertEqual(shown['latest_reports'][0]['interpretations'],findings)


class AnalysisContinuationTests(unittest.TestCase):
    """Synthetic historical feedback; no model, Store write, or physics."""
    def host(self, rows):
        values={str(i):value for i,value in enumerate(rows)}
        events=[dict(kind='model_original_tool_feedback',sequence=i,outputs=[str(i)]) for i in range(len(rows))]
        return SimpleNamespace(run_id='fixture',store=SimpleNamespace(
            events=lambda _:deepcopy(events),artifact=lambda ref:deepcopy(values[ref])))

    def feedback(self, tool, payload, result, key='fixture'):
        return dict(tool_use=dict(name=tool,toolUseId=key,input=payload),
            result=dict(status='success',content=[dict(text=json.dumps(result))]))

    def test_exact_cost_survives_reads_and_repeated_rejection_without_changing_cap(self):
        from tools.research.research_context import tool_continuation
        question=dict(operation='differentiate',effect_semantics='finite_time_task_response',
            parameter_paths=['segments.7.young_pa'],target='finite_time_task_violation',requested_budget=4)
        rejection=dict(status='insufficient_budget',reason='MECHANISM_QUESTION_BUDGET_CANNOT_FIT',
            scientific_execution_started=False,minimum_evaluations=5,requested_evaluations=4)
        row=self.feedback('research_analysis',dict(structure=question),rejection)
        reads=[self.feedback('evidence_read',dict(subject='current_task'),{},str(i)) for i in range(5)]
        rows=[row,*reads,row];before=deepcopy(rows)
        view=tool_continuation(self.host(rows))
        item=view['admission_feedback']['rejections'][0]
        self.assertEqual(item['facts']['minimum_evaluations'],5)
        self.assertEqual(item['facts']['requested_evaluations'],4)
        self.assertEqual(item['facts']['question'],question)
        self.assertEqual(item['repetitions'],2)
        self.assertEqual(len(view['admission_feedback']['rejections']),1)
        self.assertEqual(rows,before)
        self.assertNotIn('source',item['facts'])

    def test_completed_baseline_failure_remains_bound_to_question_across_routes(self):
        from tools.research.research_context import tool_continuation
        ref=dict(artifact_id='fixture-result',media_type='application/json')
        question=dict(operation='differentiate',parameter_paths=['segments.7.young_pa'],requested_budget=5)
        failure=dict(status='execution_incomplete',reason='DYNAMIC_STAGE_NOT_QUALIFIED:loaded',worker_started=True)
        rows=[self.feedback('research_analysis',dict(structure=question),
            dict(scientific_result_reference=ref,execution_feedback=failure)),
            self.feedback('research_route',dict(tool='research_investigate'),{}),
            self.feedback('research_route',dict(tool='research_analysis'),{})]
        entry=tool_continuation(self.host(rows))['recent'][0]
        self.assertEqual(entry['question'],question)
        self.assertEqual(entry['execution_feedback'],failure)
        self.assertEqual(entry['result_reference'],ref)
        self.assertNotIn('accepted',entry)


if __name__=='__main__':unittest.main()
