"""F2 engineering fixtures and read-only saved B evidence; no live Provider."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from tools.platform_store import plain, zero
from tools.state_io import digest
from tools.research import reporter
from tools.research.agent import record
from tools.research.state import state, update, save
from tools.research.session_handoff import recover_feedback
from tools.research.research_context import agent_decision_brief, mathematical_decision_view
from tools.research.task_constraints import analysis_capabilities, describe_analysis_requirements
from tests.research.test_s129_agent_reporting import AgentReportingTests, reporter_response
from tests.research.test_task_analysis_contract import TaskAnalysisTests
from tests.research.test_trajectory_feasibility import fixture


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):AgentReportingTests.setUpClass()

    def setUp(self):
        self.fixture=AgentReportingTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.h=self.fixture.h
        spec=deepcopy(state(self.h)['spec']);spec['research_decisions']={'fixture':True}
        update(self.h,spec=spec,candidates={})

    def saved_pair(self):
        pair=json.loads(Path('evidence/s129_math_capability/gvs_pair.json').read_text())
        for value in pair['supporting_artifacts'].values():save(self.h,value,'saved_B_engineering_artifact')
        refs=[save(self.h,pair[k],'saved_B_engineering_result') for k in ('baseline','changed')]
        self.assertEqual(refs,[pair['baseline_result'],pair['changed_result']])
        update(self.h,analysis_results=refs)
        return pair,refs

    def test_saved_b_quantities_reach_new_agent_packet_with_exact_sources(self):
        pair,refs=self.saved_pair()
        for ref in refs:reporter.scientific_feedback(self.h,dict(reference=ref),{})
        packet=agent_decision_brief(self.h)
        self.assertNotIn('scoped_claim',packet.get('latest_scientific_feedback') or {})
        views=[r['findings'][0]['mathematics'] for r in packet['latest_reports']]
        self.assertEqual(len(views),2)
        for view,key in zip(views,('baseline','changed')):
            self.assertEqual(view['capability']['best_found_violation'],pair[key]['trajectory']['best_found_violation'])
            self.assertFalse(view['capability']['verification_scope']['optimality'])
            self.assertEqual(view['capability']['solver_termination']['converged'],0)
            self.assertEqual(view['capability']['solver_termination']['max_iterations'],100)
            self.assertTrue(view['scope']['constraint_coverage'])
            self.assertTrue(view['problem_definition'])
            self.assertTrue(view['unresolved'])
            for quantity in view['quantities']:
                if quantity['source']:
                    from tools.research.core import read_evidence
                    self.assertEqual(read_evidence(self.h,quantity['source'],record_read=False),quantity['value'])
        comparisons=views[1]['capability']['score_comparisons']['comparisons']
        self.assertAlmostEqual(comparisons[0]['delta'],.1000004343)
        self.assertEqual(comparisons[0]['computed_score_direction'],'worse')
        self.assertAlmostEqual(comparisons[1]['delta'],-.0170110762)
        self.assertEqual(comparisons[1]['computed_score_direction'],'better')
        from tools.research.core import read_evidence
        for comparison in comparisons:
            actual=[read_evidence(self.h,source,record_read=False) for source in comparison['source_references']]
            self.assertEqual(actual,[comparison['baseline_score'],comparison['candidate_score']])
        wire=json.dumps(views)
        for key in ('"states"','"discrete_dynamics"','"applied_input_n"'):self.assertNotIn(key,wire)

    def test_v3_brief_keeps_saved_facts_and_closeout_navigation(self):
        from tools.research.research_context import research_decision_brief_v3
        pair,refs=self.saved_pair()
        for ref in refs:reporter.scientific_feedback(self.h,dict(reference=ref),{})
        base=agent_decision_brief(self.h);brief=research_decision_brief_v3(base)
        self.assertEqual(brief['version'],'research_decision_brief_v3')
        self.assertEqual(brief['research_state']['task_identity'],base['task_identity'])
        self.assertEqual(brief['budget']['model_calls'],base['budget']['provider_budget']['remaining_total'])
        self.assertEqual(brief['evidence_access']['stop_index'],base['stop_result_index'])
        self.assertIn('formally read',brief['evidence_access']['select_requirement'])
        self.assertTrue(brief['action_menu'])
        import re
        self.assertIsNone(re.search(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])',json.dumps(brief['action_menu'])))
        violation=next(f for f in brief['verified_facts'] if f['name']=='best_found_violation')
        self.assertEqual(violation['value'],pair['changed']['trajectory']['best_found_violation'])
        self.assertEqual(violation['source']['reference'],refs[-1])
        self.assertNotIn('analysis_protocol',brief)
        self.assertNotIn('mathematical_capabilities',brief)
        self.assertEqual(brief['reporter_summary']['report_reference'],base['latest_reports'][-1]['report_reference'])

    def test_receipt_recovery_selects_old_math_not_newest_and_never_reexecutes(self):
        pair,refs=self.saved_pair();raw=pair['baseline'];query=raw['requested_operation']
        use=dict(name='research_analysis',toolUseId='old-math',input=query)
        key='native-old-math-analysis'
        row,_=self.h.store.reserve(self.h.run_id,key,digest(query),self.h.actor,zero())
        self.h.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=self.h.actor,
            tool_id='research.candidate_analysis',tool_version='1.0.0',execution_status='completed',charged=zero()),raw)
        record(self.h,'model_original_tool_request',dict(tool_use=use))
        agent=SimpleNamespace(messages=[dict(role='assistant',content=[dict(toolUse=use)])],
            _session_manager=SimpleNamespace(session_id='offline-main',save_snapshot=AsyncMock()))
        ledger=self.h.store.remaining();science=deepcopy(state(self.h)['analysis_results'])
        with patch('tools.research.analysis.dispatch',side_effect=AssertionError('No worker replay')):
            self.assertEqual(asyncio.run(recover_feedback(self.h,agent)),1)
            result=agent.messages[-1]['content'][0]['toolResult']
            value=json.loads(result['content'][0]['text'])
            self.assertEqual(value['scientific_result_reference'],refs[0])
            self.assertEqual(result['toolUseId'],'old-math')
            # A second interruption uses persisted original feedback byte-for-byte.
            agent.messages=agent.messages[:1]
            self.assertEqual(asyncio.run(recover_feedback(self.h,agent)),1)
            self.assertEqual(agent.messages[-1]['content'][0]['toolResult'],result)
        self.assertEqual(self.h.store.remaining(),ledger)
        self.assertEqual(state(self.h)['analysis_results'],science)

    def test_saved_b_source_catalog_roundtrips_without_summary_aliases(self):
        from tools.research.core import read_evidence
        from schemas.research_reporting import EvidenceLocation, ScientificReport
        pair,refs=self.saved_pair();before=deepcopy(state(self.h))
        delivery=reporter.investigate(self.h,dict(question='Compare saved B scores and uncertainty',references=refs))
        base=delivery['report_reference'];saved=self.h.store.artifact(base)
        wire=reporter._wire(self.h,base,saved);payload=json.loads(wire['messages'][-1]['content'])
        catalog=payload['source_catalog']
        self.assertEqual(list(catalog),['S'+str(i+1) for i in range(len(catalog))])
        required={'/trajectory/problem_definition','/trajectory/best_found_violation',
            '/trajectory/structural_comparison/fixed_control/best_found_violation',
            '/trajectory/structural_comparison','/trajectory/starts','/trajectory/replay/records'}
        self.assertTrue(required.issubset({v['pointer'] for v in catalog.values()}))
        self.assertNotIn('/trajectory/score_semantics',{v['pointer'] for v in catalog.values()})
        for source in catalog.values():read_evidence(self.h,source,record_read=False)
        self.assertEqual(state(self.h),before)
        malformed=ScientificReport.model_validate(saved['report'])
        malformed.results[0].detail_sources.append(EvidenceLocation(reference=refs[0],pointer='/trajectory/score_semantics'))
        with self.assertRaises(KeyError):reporter._source_catalog(self.h,malformed,[])
        chosen=[key for key,value in catalog.items() if value['pointer'] in required]
        def respond(request):
            actual=json.loads(json.loads(request.content)['messages'][-1]['content'])
            self.assertEqual(actual['source_catalog'],catalog)
            return httpx.Response(200,json=dict(choices=[dict(finish_reason='stop',message=dict(
                content=json.dumps(dict(interpretations=[dict(kind='new_information',text='Offline B fixture',source_ids=chosen)]))))]))
        asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(respond)))
        final=reporter.entries(self.h)[-1][1]
        self.assertEqual(final['interpretation_status'],'available',final['error'])
        self.assertEqual(final['report']['interpretations'][0]['sources'],[catalog[key] for key in chosen])
        self.assertNotIn('source_ids',final['report']['interpretations'][0])
        self.assertEqual({k:v for k,v in final['report'].items() if k!='interpretations'},
            {k:v for k,v in saved['report'].items() if k!='interpretations'})
        for ref,key in zip(refs,('baseline','changed')):self.assertEqual(self.h.store.artifact(ref),pair[key])

    def test_signed_deltas_secants_and_recovery_have_explicit_denominators(self):
        from tools.research.core import read_evidence
        from tools.research.capability import signed_score_comparisons
        pair,refs=self.saved_pair();card=plain(reporter._card(self.h,refs[1]))
        values=mathematical_decision_view(card)['capability']['score_comparisons']
        decomposition=values['decomposition']
        for name,expected in dict(fixed_control_degradation=.11701151052081904,
                control_reoptimization_improvement=.017011076246496892,
                residual_reoptimized_degradation=.10000043427432215,
                recovery_fraction=.14537951156070436,residual_fraction=.8546204884392956).items():
            self.assertAlmostEqual(decomposition[name],expected,places=14)
        self.assertEqual(decomposition['fraction_denominator'],'fixed_control_degradation')
        scope=values['comparison_scope'];raw=pair['changed']['trajectory']['structural_comparison']
        for mode,row in values['normalized_secants'].items():
            self.assertEqual(row['value'],read_evidence(self.h,row['source'],record_read=False))
            self.assertAlmostEqual(row['value'],raw['quantities'][mode+'_delta']['value']/scope['step']*scope['normalization_scale'])
            self.assertNotEqual(row['value'],raw['quantities'][mode+'_delta']['value'])
        self.assertEqual(values['optimality_status'],'uncertified')
        self.assertIn('no optimal structural ranking or MuJoCo',values['limitation'])
        summary=deepcopy(card['deterministic_summary']['task_capability'])
        summary.pop('quantity_semantics')  # Persisted pre-fix L2 remains readable.
        self.assertEqual(signed_score_comparisons(summary,refs[1]),values)
        summary['structural_comparison']['fixed_control_violation']=summary['structural_comparison']['baseline_violation']
        self.assertNotIn('recovery_fraction',signed_score_comparisons(summary,refs[1])['decomposition'])

    def test_math_comparison_uses_recorded_scope_in_both_orders_and_exact_paths(self):
        from tools.research.core import read_evidence
        pair,refs=self.saved_pair()
        for order in (refs,refs[::-1]):
            report=reporter.assemble(self.h,order,question='Compare computed values')
            relation=report.relations[0]
            self.assertTrue(relation.comparable)
            self.assertIsNone(relation.single_factor_attribution)
            self.assertIn('no certified optimal ranking',' '.join(relation.reasons))
            self.assertNotIn('Complete physical outcomes',' '.join(relation.reasons))
            for source in relation.sources:read_evidence(self.h,plain(source),record_read=False)
        summary=reporter._card(self.h,refs[1]).deterministic_summary['task_capability']
        self.assertIn('Smaller is better',summary['score_semantics'])
        comparison=summary['structural_comparison']
        self.assertEqual(read_evidence(self.h,dict(reference=refs[1],pointer=comparison['fixed_control_value_pointer']),
            record_read=False),comparison['fixed_control_violation'])
        self.assertEqual(len(read_evidence(self.h,dict(reference=refs[1],pointer=summary['solver_starts_pointer']),
            record_read=False)),3)
        # The observed live hallucinated alias remains rejected, never repaired silently.
        with self.assertRaises(KeyError):
            read_evidence(self.h,dict(reference=refs[1],pointer='/trajectory/structural_comparison/fixed_control_violation'),
                record_read=False)
        independent=deepcopy(pair['changed']);independent['trajectory'].pop('structural_comparison')
        ref=save(self.h,independent);update(self.h,analysis_results=[*refs,ref])
        relation=reporter.assemble(self.h,[refs[0],ref],question='Unpaired model estimates').relations[0]
        self.assertIsNone(relation.comparable)
        view=mathematical_decision_view(plain(reporter._card(self.h,ref)))
        self.assertEqual(view['capability']['score_comparisons']['status'],'not_comparable')
        independent['trajectory']['structural_comparison']=deepcopy(pair['changed']['trajectory']['structural_comparison'])
        independent['trajectory']['structural_comparison']['status']='inconclusive'
        ref=save(self.h,independent);update(self.h,analysis_results=[*refs,ref])
        view=mathematical_decision_view(plain(reporter._card(self.h,ref)))
        self.assertEqual(view['capability']['score_comparisons']['status'],'not_comparable')

    def test_multi_result_receipt_and_missing_binding(self):
        _,refs=self.saved_pair()
        receipt=dict(request_id='original',execution_id='original-exec',output=refs[0])
        result=reporter.scientific_feedback(self.h,dict(scientific_results=refs),receipt=receipt)
        self.assertEqual([v['reference'] for v in result['scientific_result_index']],refs)
        for row in result['scientific_result_index']:
            saved=self.h.store.artifact(row['report_reference'])
            self.assertEqual(saved['report']['results'][0]['identity']['result']['reference'],row['reference'])
        same=reporter.scientific_feedback(self.h,dict(scientific_results=refs),receipt=receipt)
        self.assertEqual(same['scientific_result_index'],result['scientific_result_index'])
        raw=dict(status='completed',original_fact='keep me')
        missing=reporter.scientific_feedback(self.h,raw,receipt={**receipt,'output':save(self.h,raw)})
        self.assertEqual(missing['operation_outcome'],raw)
        self.assertEqual(missing['error'],'EXACT_SCIENTIFIC_RESULT_BINDING_UNAVAILABLE')
        self.assertNotIn('report',missing)

    def test_priority_keeps_reports_and_limits_duplicate_physics_calls(self):
        before=state(self.h);raw=self.fixture.physical()
        # Pair comparisons need a complete current candidate identity and its
        # configuration reference, not the minimal single-card fixture.
        value=deepcopy(self.h.store.artifact(raw));value['candidate']=self.fixture.case.candidate
        ref=save(self.h,value,'physical_comparison_fixture');update(self.h,physical_replays=[ref])
        first=reporter.scientific_feedback(self.h,dict(reference=ref),before)
        other=deepcopy(self.h.store.artifact(ref));other['fixture_repetition']='second'
        second=save(self.h,other);update(self.h,physical_replays=[ref,second])
        repeated=reporter.scientific_feedback(self.h,dict(reference=second),before)
        calls=[]
        def respond(request):calls.append(request);return reporter_response(request)
        asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(respond)))
        self.assertEqual(len(calls),1)
        reports=reporter.entries(self.h)
        skipped=next(v for _,v in reports if v['interpretation_for']==repeated['report_reference'])
        self.assertEqual(skipped['interpretation_status'],'skipped')
        self.assertEqual(skipped['report'],self.h.store.artifact(repeated['report_reference'])['report'])
        investigation=reporter.investigate(self.h,dict(question='Explicitly compare the repetition',references=[second]))
        asyncio.run(reporter.complete_reports(self.h,httpx.MockTransport(respond)))
        self.assertEqual(len(calls),2)
        self.assertTrue(any(v['interpretation_for']==investigation['report_reference'] and
            v['interpretation_status']=='available' for _,v in reporter.entries(self.h)))


class CrossTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):TaskAnalysisTests.setUpClass()

    def test_catalogue_reuses_execution_coverage_and_budget(self):
        f=TaskAnalysisTests();f.setUp()
        req=describe_analysis_requirements(f.cfg,f.binding)
        rows=analysis_capabilities(f.cfg,req,f.q.protocol,remaining_evaluations=2)
        by={r['operation']:r for r in rows}
        self.assertEqual(by['task_capability']['status'],'applicable')
        self.assertTrue(by['task_capability']['full_task_supported'])
        self.assertFalse(by['design_sensitivity']['budget_allowed'])
        self.assertEqual(by['input_sensitivity']['status'],'not_applicable')
        self.assertEqual(by['instantaneous_braking_v1']['status'],'not_applicable')
        self.assertTrue(all(r['wall_cost']=='unknown' for r in rows))
        unsupported=req.model_copy(update=dict(constraints=[req.constraints[0].model_copy(update=dict(
            kind='unsupported',unsupported_requirement=dict(contact_event=True)))]))
        self.assertTrue(all(r['status']=='not_applicable' for r in analysis_capabilities(f.cfg,unsupported,f.q.protocol)))

    def test_synthetic_moving_reference_preserved_by_both_kernels(self):
        from extensions.math_analysis.task_capability import task_capability
        from extensions.math_analysis.trajectory import trajectory_feasibility
        model,req,p=fixture();original=plain(req)
        for kernel in (task_capability,trajectory_feasibility):
            out=kernel(model,req,p)
            self.assertEqual(out['status'],'feasible_witness')
            self.assertTrue(out['full_requested_coverage'])
            self.assertEqual({r['signal'] for r in out['replay']['records']},{'test_output'})
            self.assertEqual(plain(req),original)
            model.operating_point.update(actual_time_s=1.,remaining_task_s=2.)
            partial=kernel(model,req,p)
            self.assertFalse(partial['full_requested_coverage'])
            model.operating_point.update(actual_time_s=0.,remaining_task_s=3.)
            unknown=req.model_copy(update=dict(constraints=[req.constraints[0].model_copy(update=dict(
                signal=req.constraints[0].signal.model_copy(update=dict(name='contact_impulse'))))]))
            self.assertEqual(kernel(model,unknown,p)['status'],'not_applicable')


if __name__=='__main__':unittest.main()
