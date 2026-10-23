"""Synthetic projection contracts and saved F3 facts; no Provider or science worker."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from tools.platform_store import plain
from tools.research import analysis, reporter
from tools.research.core import read_evidence
from tools.research.evidence_views import result_card
from tools.research.research_context import (mathematical_decision_view, compact_action_trace,
    compact_intent, agent_decision_brief, research_intent)
from tools.research.state import save, state, update
from tools.research.task_constraints import mathematical_method_view, mathematical_catalog
from tests.research import test_s130_mainline as fixtures


class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.MainlineTests.setUpClass()

    def setUp(self):
        self.f=fixtures.MainlineTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.h=self.f.h

    def test_both_conic_versions_through_complete_projection_chain(self):
        saved=json.loads(Path('evidence/s132_tracking/validation.json').read_text(encoding='utf-8'))
        for path in (None,'free','bend','diagonal_cannot_follow_bend'):
            raw=self.f.conic()
            if path:
                # Fabricated schema compatibility fixture, not a new robot result.
                raw['trajectory'].update(deepcopy(saved['conic_cases'][path]))
                raw['trajectory']['coverage']=[dict(constraint_id='synthetic_path',analyzed_indices=[0,1])]
                raw['task_analysis']['constraints'][0].update(kind='path_bound',reference=[],path_vertices_m=[[0,0,0],[1,0,0]])
            original=deepcopy(raw);ref=self.f.register(raw)
            tool=analysis.compact_result(raw,ref)
            card=plain(result_card(self.h,ref));view=mathematical_decision_view(card)
            report=reporter.assemble(self.h,[ref]);wire=reporter._wire(self.h,ref,dict(report=plain(report),request=None))
            json.loads(wire['messages'][-1]['content'])
            reporter.scientific_feedback(self.h,dict(reference=ref),{})
            r,s=reporter.current_reports(self.h)[-1]
            handoff=reporter.reporter_handoff_summary(self.h,r,s)
            for projected in (tool['task_capability'],view['capability'],handoff['findings'][0]['mathematics']['capability']):
                self.assertEqual(projected['replayed_violation'],raw['trajectory']['replayed_violation'])
                self.assertEqual(projected['optimality_status'],'numerically_checked')
                self.assertEqual(projected['strict_optimality'],'unavailable')
                if path:
                    self.assertEqual(projected['path_progress'],raw['trajectory']['path_progress'])
                    self.assertEqual(projected['internal_conic_solves'],raw['trajectory']['internal_conic_solves'])
                    if path!='free':
                        self.assertEqual(projected['path_assignment_comparison'],raw['trajectory']['path_assignment_comparison'])
                        self.assertEqual(projected['path_assignment_ties'],raw['trajectory']['path_assignment_ties'])
                    self.assertIn('not infeasibility',projected['untimed_scope'])
                    self.assertEqual(projected['coverage'],raw['trajectory']['coverage'])
                for key,pointer in projected['sources'].items():
                    self.assertEqual(read_evidence(self.h,dict(reference=ref,pointer=pointer),record_read=False),raw['trajectory'][key])
            for quantity in card['mathematics']['quantities']:
                if quantity['source']:
                    self.assertEqual(read_evidence(self.h,quantity['source'],record_read=False),quantity['value'])
            self.assertEqual(next(q['status'] for q in view['quantities'] if q['name']=='optimal_value'),'unavailable')
            self.assertNotEqual(card['mathematics']['claim']['conclusion'],'model_infeasibility_certificate')
            self.assertEqual(raw,original)

    def test_all_task_metrics_and_search_best_survive_l1(self):
        ref=self.f.f.physical();raw=self.h.store.artifact(ref)
        raw['acceptance']['components'].update({
            'evaluator:tracking_max_error':dict(value=.003,limit=.004,unit='m',passed=True),
            'evaluator:path_coverage':dict(value=.002,limit=.004,unit='m',passed=True),
            'evaluator:progress_regression':dict(value=0.,limit=0.,unit='dimensionless',passed=True)})
        ref=save(self.h,raw,'synthetic_tracking_metric_fixture')
        report=reporter.assemble(self.h,[ref]);saved=dict(report=plain(report),interpretation_status='available',error=None)
        handoff=reporter.reporter_handoff_summary(self.h,ref,saved)
        expected={k for k,r in raw['acceptance']['components'].items() if type(r.get('value')) in (int,float)}
        metrics=handoff['findings'][0]['metrics'];self.assertEqual({m['name'] for m in metrics},expected)
        for m in metrics:self.assertEqual(read_evidence(self.h,m['source'],record_read=False),m['value'])
        step=dict(label='baseline',reference=ref,candidate=raw['candidate'],source=raw['source_reference'],
            task_gap=dict(accepted=True,normalized_gap=0),original_acceptance=raw['acceptance'])
        search=save(self.h,dict(candidates=[step],best=step,starts=[],start_feedback=[],stop_reason='first_original_task_pass',
            cost_feedback=dict(new_physical_evaluations=18,charged_numerical_s=19.9)),'synthetic_search_fixture')
        saved['report']=plain(reporter.assemble(self.h,[search]))
        fact=reporter.reporter_handoff_summary(self.h,search,saved)['findings'][0]
        self.assertEqual(fact['control_search']['best']['evaluation'],ref)
        self.assertTrue(fact['metrics'])
        self.assertEqual(fact['control_search']['stop_reason']['value'],'first_original_task_pass')
        self.assertEqual(next(r['amount'] for r in fact['resources'] if r['name']=='new_physical_evaluations'),18)

    def test_saved_f3_pass_delivers_three_hard_metrics_with_original_sources(self):
        folder=Path('evidence/f3_formal/closeout_20261023')
        audit=json.loads((folder/'audit.json').read_text(encoding='utf-8'))
        artifacts=json.loads((folder/'artifacts.json').read_text(encoding='utf-8'))
        for value in artifacts.values():save(self.h,value,'saved_F3_fixture_copy')
        ref=audit['references']['selected']
        report=reporter.assemble(self.h,[ref]);saved=dict(report=plain(report),interpretation_status='skipped',error=None)
        delivered=reporter.reporter_handoff_summary(self.h,ref,saved)['findings'][0]['metrics']
        main={m['scientific_metric']:m for m in delivered if 'scientific_metric' in m}
        self.assertEqual(set(main),{'terminal_position_error','holding_max_position_error','holding_max_speed'})
        self.assertTrue(all(m['passed'] for m in main.values()))
        self.assertAlmostEqual(main['holding_max_speed']['value'],.0191342833,places=9)
        for m in main.values():
            self.assertEqual(read_evidence(self.h,m['source'],record_read=False),m['value'])
            self.assertEqual(read_evidence(self.h,m['threshold_source'],record_read=False),m['threshold'])

    def test_saved_tracking_contract_keeps_each_metric_without_reach_fields(self):
        saved=json.loads(Path('evidence/s132_tracking/validation.json').read_text(encoding='utf-8'))
        raw=self.h.store.artifact(self.f.f.physical())
        for case in saved['evaluator_cases']:
            components={'evaluator:'+c['name']:dict(value=c['observed'],limit=c['limit'],unit=c['units'],passed=c['satisfied'])
                for c in case['constraints']}
            raw['acceptance']=dict(task_family='task.tracking',accepted=case['task_success'],components=components)
            ref=save(self.h,raw,'saved_tracking_contract_fixture')
            report=reporter.assemble(self.h,[ref])
            fact=reporter.reporter_handoff_summary(self.h,ref,dict(report=plain(report),interpretation_status='skipped',error=None))['findings'][0]
            self.assertEqual({m['name'] for m in fact['metrics']},set(components))
            self.assertTrue(all('scientific_metric' not in m for m in fact['metrics']))
            for metric in fact['metrics']:
                self.assertEqual(metric['passed'],components[metric['name']]['passed'])
                self.assertEqual(read_evidence(self.h,metric['source'],record_read=False),metric['value'])

    def test_corrected_interpretations_are_historical_and_investigation_reads_correction(self):
        ref=self.f.f.physical();report=plain(reporter.assemble(self.h,[ref]))
        report['interpretations']=[dict(kind='hypothesis',text='Synthetic outdated mechanism',sources=[dict(reference=ref,pointer='')])]
        saved=dict(report=report,interpretation_status='available',error=None)
        correction=save(self.h,dict(historical_control_updates=[dict(reference=ref,reason='synthetic correction')]),'synthetic_correction')
        update(self.h,engineering_feedback_correction=correction)
        before=deepcopy(saved);delivery=reporter.reporter_handoff_summary(self.h,ref,saved)
        self.assertEqual(delivery['reporter_status'],'available')
        self.assertEqual(delivery['current_interpretation_status'],'superseded_pending_reinterpretation')
        self.assertEqual(delivery['interpretations'],[]);self.assertEqual(saved,before)
        request=reporter.investigate(self.h,dict(question='Check corrected mechanism',references=[ref]))
        new=self.h.store.artifact(request['report_reference'])
        self.assertEqual(new['request']['reads'][0]['pointer'],'/historical_control_updates/0')
        new['report']['interpretations']=report['interpretations'];new['interpretation_status']='available'
        refreshed=reporter.reporter_handoff_summary(self.h,request['report_reference'],new)
        self.assertEqual(refreshed['current_interpretation_status'],'available')
        self.assertEqual(refreshed['interpretations'],report['interpretations'])
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],0)

    def test_recent_five_keep_sources_without_repeating_parent_hypothesis(self):
        trace=dict(total=9,recent=[dict(action='control_search',method='search',candidate=self.f.base['candidate'],
            execution_status='completed',outcome=dict(status='evaluated'),result_references=[self.f.base['candidate']],
            source=dict(reference=self.f.base['candidate'],pointer=''),agent_hypothesis=dict(hypothesis='parent '*1000)) for _ in range(5)])
        short=compact_action_trace(trace)
        self.assertEqual(len(short['recent']),5)
        self.assertNotIn('parent',json.dumps(short))
        self.assertTrue(all(r['source']==trace['recent'][0]['source'] for r in short['recent']))
        item=dict(plan_reference=self.f.base['candidate'],agent_hypothesis=dict(hypothesis='current explicit question',weakening_observation='counter observation'))
        intent=compact_intent(dict(latest_decision=item,last_research=item))
        self.assertEqual(intent['latest_decision']['agent_hypothesis']['weakening_observation'],'counter observation')
        self.assertEqual(intent['last_research']['same_as'],'research_intent.latest_decision')

    def test_candidate_bound_method_details_and_current_candidate_selection(self):
        first=self.f.f.case.candidate;c=self.h.store.artifact(first)
        stale=deepcopy(c);stale.update(identity='c'*64,profile_identity='old-profile')
        second=save(self.h,stale,'synthetic_stale_candidate')
        model=save(self.h,dict(candidate=first,implementation=state(self.h)['freeze'],status='computed',
            model=dict(synthetic=True),protocol=state(self.h)['spec']['analysis_protocol']),'synthetic_model_presence_only')
        update(self.h,candidates={c['identity']:first,stale['identity']:second},analysis_results=[model])
        one=read_evidence(self.h,dict(reference=first,view='mathematical_capabilities'),record_read=False)
        two=read_evidence(self.h,dict(reference=second,view='mathematical_capabilities'),record_read=False)
        self.assertEqual(one['candidate'],first);self.assertEqual(two['candidate'],second)
        self.assertTrue(one['methods']['controllability']['model_built'])
        self.assertFalse(two['methods']['controllability']['model_built'])
        self.assertEqual(two['methods']['controllability']['execution_status'],'blocked')
        for key,row in one['methods'].items():
            self.assertEqual(read_evidence(self.h,row['detail_query'],record_read=False),row)
            self.assertIn('candidate',row['request_template'])
            self.assertTrue(row['description'])
            if not row['required_parameters']:
                from tools.research.contracts import AnalysisRequest
                AnalysisRequest.model_validate(row['request_template'])
        schema=read_evidence(self.h,one['methods']['controllability']['schema_query'],record_read=False)
        self.assertIn('protocol',schema['required'])
        item=dict(plan_reference=first,candidate=first,agent_hypothesis=dict(decision=dict(selected_method='controllability')))
        with patch('tools.research.research_context.context',return_value={}),patch(
                'tools.research.research_context.decision_brief',return_value={}),patch(
                'tools.research.research_context.research_intent',return_value=dict(latest_decision=item,last_research=item)),patch(
                'tools.research.research_context.research_action_trace',return_value=dict(recent=[])),patch(
                'tools.research.reporter.current_reports',return_value=[]),patch(
                'tools.research.evidence_views.result_card',return_value=None):
            update(self.h,analysis_results=[])
            brief=agent_decision_brief(self.h)
        self.assertEqual(brief['mathematical_capabilities']['candidate'],first)
        self.assertEqual(brief['selected_mathematical_method']['candidate'],first)

    def test_tracking_kernel_support_does_not_advertise_robot_execution(self):
        first=self.f.f.case.candidate;c=deepcopy(self.h.store.artifact(first))
        c['configuration']['task']=json.loads(Path('tasks/tracking_linear_development.json').read_text(encoding='utf-8'))['task']
        c.update(identity='b'*64,profile_identity='old-profile')
        ref=save(self.h,c,'synthetic_tracking_readiness_fixture')
        update(self.h,candidates={c['identity']:ref})
        view=mathematical_method_view(self.h,ref)
        path=mathematical_catalog(view)['methods']['sampled-affine-conic-minimax-v1']
        self.assertTrue(path['kernel_supported'])
        self.assertFalse(path['model_built']);self.assertFalse(path['full_task_supported'])
        self.assertEqual(path['execution_status'],'blocked')
        self.assertIn('tracking_robot_model_construction_unsupported',path['missing'])
        self.assertEqual(view['method'],'controlled-capability-sensitivity-v1')


if __name__=='__main__':unittest.main()
